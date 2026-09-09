# -*- coding: utf-8 -*-
"""초상 514장을 CLIP 이미지 임베딩으로 바꾼다.

왜 픽셀로 안 재고 이걸 쓰는가. 픽셀 평균차로 재 봤더니 역할도 계층도
잡음 바닥에 붙어 나왔다 (`tools/face_diff.py`). 그런데 눈으로 보면 성직
열은 다섯 줄이 전부 민머리다. **보이는 것을 못 잡는 자는 자가 아니다.**
얼굴이 장마다 다른 자리·다른 크기로 있어서 픽셀을 그대로 빼면 사람이
다른 것만 재게 된다.

CLIP 은 「민머리」 「두건」 「옆을 본다」 같은 것을 한 벡터에 담는다.
자리가 조금 어긋나도 같은 뜻이면 가까이 온다. 계층으로 눈금을 검증할 수
있다 — 계층이 안 갈리면 그 자도 버린다.

  ./run.sh shell irem-imagegen:latest python /work/src/embed_faces.py
"""
import argparse, glob, os
import numpy as np

CLIP = "openai/clip-vit-base-patch32"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--faces", default="/work/out/faces")
    ap.add_argument("--model", default=CLIP)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or os.path.join(args.faces, "clip.npz")

    import torch
    from PIL import Image
    from transformers import CLIPModel, CLIPImageProcessor

    files = sorted(os.path.basename(f) for f in glob.glob(os.path.join(args.faces, "*_v*.png")))
    if not files:
        raise SystemExit(f"초상이 없다: {args.faces}")
    print(f"[embed] {len(files)}장 → {args.model}", flush=True)

    model = CLIPModel.from_pretrained(args.model).to("cuda").eval()
    proc = CLIPImageProcessor.from_pretrained(args.model)

    vecs = []
    B = 32
    for i in range(0, len(files), B):
        batch = [Image.open(os.path.join(args.faces, f)).convert("RGB") for f in files[i:i+B]]
        px = proc(images=batch, return_tensors="pt")["pixel_values"].to("cuda")
        with torch.no_grad():
            v = model.get_image_features(pixel_values=px)
        v = v / v.norm(dim=-1, keepdim=True)
        vecs.append(v.cpu().numpy().astype(np.float32))
        print(f"  {min(i+B, len(files))}/{len(files)}", flush=True)
    np.savez(out, files=np.array(files), vecs=np.concatenate(vecs))
    print(f"[embed] 끝 — {out}", flush=True)


if __name__ == "__main__":
    main()
