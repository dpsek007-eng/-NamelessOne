# -*- coding: utf-8 -*-
"""실험 팔 한 판을 한 장으로 — 눈으로 세려고 만든다.

숫자만 보고 판정하면 팔 3 같은 일이 또 난다. 「전신」이라고 적어 두고
90장 중 35장만 전신으로 나왔는데, 역할 비는 문턱을 넘겼다. **약이
들어갔는지는 세어 보는 수밖에 없다.**

  python3 tools/arm_sheet.py figure2            → /tmp/arm_figure2.png
  python3 tools/arm_sheet.py figure2 --split 2  → 반으로 갈라 두 장

칸 하나가 한 줄, 장 여섯이 가로로 놓인다. 줄 이름이 왼쪽 위에 붙는다.
"""
import argparse, os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = ["guard", "resist", "devote", "seek", "flee"]
TIERS = ["peasant", "clerk", "merchant"]
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("arm", help="pose · figure · figurenh · figure2 · '' (기준)")
    ap.add_argument("--w", type=int, default=150)
    ap.add_argument("--split", type=int, default=1, help="세로로 몇 장에 나눌지")
    ap.add_argument("--tiers", default=",".join(TIERS))
    a = ap.parse_args()

    d = os.path.join(ROOT, "pipeline3d/out",
                     "faces_" + a.arm if a.arm else "faces")
    if not os.path.isdir(d):
        raise SystemExit(f"{d} 가 없다.")
    tiers = [t.strip() for t in a.tiers.split(",")]
    cells = [(f"{r}_{t}", r, t) for t in tiers for r in ROLES]
    W, PAD = a.w, 16
    im = Image.new("RGB", (W * 6, PAD + len(cells) * W), (14, 16, 19))
    try:
        f = ImageFont.truetype(FONT, 12)
    except OSError:
        f = ImageFont.load_default()
    dr = ImageDraw.Draw(im)
    miss = 0
    for i, (cid, r, t) in enumerate(cells):
        y = PAD + i * W
        for v in range(6):
            p = os.path.join(d, f"{cid}_v{v}.png")
            if os.path.exists(p):
                im.paste(Image.open(p).convert("RGB").resize((W, W), Image.LANCZOS),
                         (W * v, y))
            else:
                miss += 1
        dr.text((3, y + 2), f"{r[:3]}·{t[:4]}", fill=(255, 240, 120), font=f)
    name = a.arm or "base"
    if a.split <= 1:
        out = f"/tmp/arm_{name}.png"
        im.save(out); print(out)
    else:
        h = im.size[1] // a.split
        for k in range(a.split):
            top = k * h
            bot = im.size[1] if k == a.split - 1 else (k + 1) * h
            out = f"/tmp/arm_{name}_{k}.png"
            im.crop((0, top, im.size[0], bot)).save(out); print(out)
    if miss:
        print(f"  ⚠ 빠진 장 {miss}개", file=sys.stderr)


if __name__ == "__main__":
    main()
