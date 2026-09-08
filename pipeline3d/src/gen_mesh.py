# -*- coding: utf-8 -*-
"""2단계 — 이미지 → 메시. irem-triposr 컨테이너 안에서 돈다.

윗물의 run.py 를 47번 부르지 않는 이유는 모델을 47번 올리기 때문이다.
한 번 올려 두고 돌린다.

내는 것은 OBJ + texture.png 다. xatlas 로 UV 를 펴고 NeRF 색을 아틀라스에
구워 낸다. 정점 색으로 두면 블렌더에서 굽는 일이 한 단계 더 붙는다.
"""
import argparse, json, os, sys, time

import numpy as np
import torch
import xatlas
from PIL import Image

# --- moderngl 을 EGL 로 못박는다 -------------------------------------------
# 텍스처 굽기는 UV 아틀라스를 래스터라이즈한다. 그런데 moderngl 은 standalone
# 컨텍스트를 만들 때 x11 을 먼저 찔러 보고, 컨테이너엔 화면이 없어서 죽는다.
#   Exception: (standalone) XOpenDisplay: cannot open display
# 벤더 파일을 고치는 대신 여기서 backend 를 박는다.
#
# 그리고 컨테이너는 반드시 이렇게 띄운다:
#   docker run --runtime=nvidia -e NVIDIA_VISIBLE_DEVICES=0 \
#              -e NVIDIA_DRIVER_CAPABILITIES=all ...
# `--gpus` 만 주면 compute/utility 만 올라오고 10_nvidia.json 이 없어서
# EGL 이 llvmpipe(소프트웨어)로 떨어진다. 그림은 같지만 훨씬 느리다.
import moderngl as _mgl

_real_create_context = _mgl.create_context


def _egl_create_context(*a, **kw):
    kw.setdefault("backend", "egl")
    return _real_create_context(*a, **kw)


_mgl.create_context = _egl_create_context
# ---------------------------------------------------------------------------

sys.path.insert(0, "/work/vendor/TripoSR")
from tsr.system import TSR
from tsr.utils import remove_background, resize_foreground
from tsr.bake_texture import bake_texture
import tsr.bake_texture as _bt


# --- 윗물 버그 하나 ---------------------------------------------------------
# bake_texture.positions_to_colors 는 래스터라이즈해 온 좌표를 CPU 텐서로 만들어
# CUDA 위의 디코더에 그대로 넣는다.
#   RuntimeError: Expected all tensors to be on the same device,
#                 but found at least two devices, cuda:0 and cpu!
# run.py 가 기본으로 cuda:0 을 쓰므로 --bake-texture 는 윗물에서 그냥 안 돈다.
# 벤더 폴더는 건드리지 않고 여기서 바꿔 끼운다.
def _positions_to_colors(model, scene_code, positions_texture, texture_resolution):
    dev = scene_code.device
    positions = torch.tensor(
        positions_texture.reshape(-1, 4)[:, :-1], device=dev, dtype=torch.float32
    )
    with torch.no_grad():
        queried = model.renderer.query_triplane(model.decoder, positions, scene_code)
    rgb_f = queried["color"].detach().cpu().numpy().reshape(-1, 3)
    rgba_f = np.insert(rgb_f, 3, positions_texture.reshape(-1, 4)[:, -1], axis=1)
    rgba_f[rgba_f[:, -1] == 0.0] = [0, 0, 0, 0]
    return rgba_f.reshape(texture_resolution, texture_resolution, 4)


_bt.positions_to_colors = _positions_to_colors
# ---------------------------------------------------------------------------


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default="/work/out/images")
    ap.add_argument("--out", default="/work/out/mesh")
    ap.add_argument("--model", default="stabilityai/TripoSR")
    ap.add_argument("--mc-resolution", type=int, default=320,
                    help="마칭큐브 격자. 256 이 기본, 올리면 형태가 살고 삼각형이 는다")
    ap.add_argument("--chunk-size", type=int, default=8192)
    ap.add_argument("--texture-resolution", type=int, default=1024)
    ap.add_argument("--foreground-ratio", type=float, default=0.85)
    ap.add_argument("--only", default=None)
    ap.add_argument("--picks", default="/work/picks.json",
                    help="번호->variant 표. 눈으로 고른 한 장만 굽는다. none 이면 전부")
    args = ap.parse_args()

    with open(os.path.join(args.images, "index.json"), encoding="utf-8") as f:
        index = json.load(f)

    # 3장씩 뽑아 놓고 그 중 하나만 쓴다. 고른 것은 picks.json 에 있다.
    # 이 표가 없으면 141장을 다 굽게 되는데, 한 시간이고 대부분 버린다.
    if args.picks and args.picks.lower() != "none":
        with open(args.picks, encoding="utf-8") as f:
            picks = {k: v for k, v in json.load(f).items() if not k.startswith("_")}
        before = len(index)
        index = [r for r in index if picks.get(f"{r['i']:02d}") == r["variant"]]
        got = {f"{r['i']:02d}" for r in index}
        miss = sorted(set(picks) - got)
        if miss:
            raise SystemExit(f"고른 그림이 없다: {miss}")
        print(f"[gen_mesh] 고른 것 {len(index)}장 (전체 {before}장 중)", flush=True)

    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        index = [r for r in index if f"{r['i']:02d}" in keep or r["id"] in keep]

    os.makedirs(args.out, exist_ok=True)
    print(f"[gen_mesh] {len(index)}장 → {args.out}", flush=True)

    model = TSR.from_pretrained(args.model, config_name="config.yaml", weight_name="model.ckpt")
    model.renderer.set_chunk_size(args.chunk_size)
    model.to("cuda")

    import rembg
    session = rembg.new_session()

    made = []
    for r in index:
        name = f"{r['id']}_v{r['variant']}"
        d = os.path.join(args.out, name)
        obj_path = os.path.join(d, "mesh.obj")
        if os.path.exists(obj_path):
            print(f"  건너뜀 {name}", flush=True)
            made.append({**r, "dir": name})
            continue
        os.makedirs(d, exist_ok=True)

        t0 = time.time()
        src = Image.open(os.path.join(args.images, r["image"]))
        img = remove_background(src, session)
        img = resize_foreground(img, args.foreground_ratio)
        a = np.array(img).astype(np.float32) / 255.0
        # 알파를 회색(0.5)에 합성한다. TripoSR 이 학습된 배경이 그 회색이다.
        a = a[:, :, :3] * a[:, :, 3:4] + (1 - a[:, :, 3:4]) * 0.5
        img = Image.fromarray((a * 255.0).astype(np.uint8))
        img.save(os.path.join(d, "input.png"))

        with torch.no_grad():
            codes = model([img], device="cuda")
        meshes = model.extract_mesh(codes, False, resolution=args.mc_resolution)
        mesh = meshes[0]

        bake = bake_texture(mesh, model, codes[0], args.texture_resolution)
        xatlas.export(
            obj_path,
            mesh.vertices[bake["vmapping"]],
            bake["indices"],
            bake["uvs"],
            mesh.vertex_normals[bake["vmapping"]],
        )
        Image.fromarray((bake["colors"] * 255.0).astype(np.uint8)) \
             .transpose(Image.FLIP_TOP_BOTTOM) \
             .save(os.path.join(d, "texture.png"))

        tris = len(bake["indices"])
        print(f"  {name}  {tris:>7,}삼각형  {time.time()-t0:.1f}초", flush=True)
        made.append({**r, "dir": name, "tris": tris})

    with open(os.path.join(args.out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(made, f, ensure_ascii=False, indent=2)
    print(f"[gen_mesh] 끝 — {len(made)}개", flush=True)


if __name__ == "__main__":
    main()
