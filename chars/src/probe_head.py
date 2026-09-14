# -*- coding: utf-8 -*-
"""3D 머리 실물 재기 — 얼굴 프로젝션 베이크 전 준비.

   blender --background --python chars/src/probe_head.py -- --role 수호 --out /tmp

머리(hair 지오메트리 없이 MPFB 머리)의 정면 정사영 실루엣(bbox)과
머리 정점 수·UV 타일 수를 출력하고, 전면 렌더 한 장을 낸다.
"""
import argparse, json, os, sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_garments as MG


def build(role):
    bm, arm = MG.build_body(role)
    return bm, arm


def head_bbox(bm):
    """머리 버텍스그룹(head) 정점의 정면 실루엣 bbox.

    MPFB 사람은 Z가 위, Y가 앞이다. 그대로 올쏘 정면 카메라와 세로 캐런트를
    뽑으면 X(좌우)·Z(상하)가 화면 축이다. 여기서 얼굴 데칼 크기를 잰다.
    """
    grp = bm.vertex_groups.get("head")
    if grp is None:
        raise SystemExit("머리 버텍스그룹이 없다 — extra_vertex_groups 를 켰는지")
    idx = grp.index
    co = []
    for v in bm.data.vertices:
        for g in v.groups:
            if g.group == idx and g.weight > 0.5:
                co.append(v.co)
    if not co:
        raise SystemExit("head 그룹에 0.5 이상 무게 정점이 없다")
    x0 = min(c.x for c in co); x1 = max(c.x for c in co)
    z0 = min(c.z for c in co); z1 = max(c.z for c in co)
    y0 = min(c.y for c in co); y1 = max(c.y for c in co)
    return dict(cx=(x0 + x1) / 2, cy=(y0 + y1) / 2, cz=(z0 + z1) / 2,
                w=x1 - x0, h=z1 - z0, d=y1 - y0, z0=z0, z1=z1)


def uv_info(bm):
    uv = bm.data.uv_layers.active
    tiles = {}
    if uv is None:
        return dict(tiles=None)
    for p in bm.data.polygons:
        for l in p.loop_indices:
            u, v = uv.data[l].uv
            tiles[(int(u), int(v))] = True
    return dict(tiles=sorted(tiles))


def render_head(bm, out_png, bb):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.render.resolution_x, sc.render.resolution_y = 512, 640
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    cam = bpy.data.cameras.new("probe")
    cam_ob = bpy.data.objects.new("probe", cam)
    bpy.context.collection.objects.link(cam_ob)
    bpy.context.scene.camera = cam_ob
    cam.type = "ORTHO"
    cam.ortho_scale = bb["w"] * 1.25
    f = 0.6   # 머리 중심에서 살짝 앞, 가슴쪽
    cam_ob.location = (bb["cx"], bb["cy"] - f, bb["cz"])
    cam_ob.rotation_euler = (1.5708, 0, 0)   # Z축이 화면 위. 정면
    # 다만 workbench(FLAT)로는 재질을 못 본다. 가급적 Cycles 가 낫다.
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = False
    sc.view_layers[0].use_pass_z = False
    bpy.ops.render.render(write_still=True)
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    img = bpy.data.images["Render Result"]
    img.save_render(out_png, scene=sc)
    print(f"[probe] 렌더 {out_png}", flush=True)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", default="수호")
    ap.add_argument("--out", default="/tmp")
    args = ap.parse_args(argv)

    bm, arm = build(args.role)
    bb = head_bbox(bm)
    uv = uv_info(bm)
    n = len(bm.data.vertices)

    report = dict(role=args.role, verts=n, head=bb, uv=uv)
    print(json.dumps(report, ensure_ascii=False, indent=1), flush=True)

    # 눈 위치 근사 — MPFB 머리 비율에서 눈선은 대략 머리 위에서 42% 아래.
    # 정확한 값을 못 잡으니 "아마"로 적는다. 데칼 맞추기는 이걸 기준으로 튠.
    out_png = os.path.join(args.out, "head_front.png")
    render_head(bm, out_png, bb)
    with open(os.path.join(args.out, "probe.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(argv)