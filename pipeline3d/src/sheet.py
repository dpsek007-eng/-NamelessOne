# -*- coding: utf-8 -*-
"""대조표 — 뽑은 그림을 한 장에 늘어놓는다. 호스트에서 그냥 돈다.

141장을 한 장씩 여는 것과 한 장을 여는 것은 다르다. 어느 것이 잘못 나왔는지는
나란히 놓고 봐야 보인다. 줄 하나가 소품 하나, 칸이 후보다.

    python3 pipeline3d/src/sheet.py --images pipeline3d/out/images \\
                                    --out pipeline3d/out/sheet.png --rows 12
"""
import argparse, json, os, sys

from PIL import Image, ImageDraw, ImageFont

FONTS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def font(size):
    for f in FONTS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default="pipeline3d/out/images")
    ap.add_argument("--out", default="pipeline3d/out/sheet.png")
    ap.add_argument("--cell", type=int, default=240)
    ap.add_argument("--label", type=int, default=150, help="왼쪽 이름칸 너비")
    ap.add_argument("--rows", type=int, default=0,
                    help="한 장에 몇 줄. 0 이면 전부 한 장에. 나누면 뒤에 -1,-2 가 붙는다")
    args = ap.parse_args()

    with open(os.path.join(args.images, "index.json"), encoding="utf-8") as f:
        index = json.load(f)

    by_id = {}
    for r in index:
        by_id.setdefault(r["id"], {"r": r, "v": {}})["v"][r["variant"]] = r["image"]
    ids = sorted(by_id)
    if not ids:
        raise SystemExit("표가 비었다")
    ncol = max(max(d["v"]) for d in by_id.values()) + 1

    ft = font(15)
    fs = font(12)
    chunk = args.rows or len(ids)
    parts = [ids[i:i + chunk] for i in range(0, len(ids), chunk)]

    for pi, part in enumerate(parts):
        W = args.label + ncol * args.cell
        H = len(part) * args.cell
        sheet = Image.new("RGB", (W, H), (24, 24, 26))
        d = ImageDraw.Draw(sheet)
        for ri, pid in enumerate(part):
            rec = by_id[pid]
            y = ri * args.cell
            d.rectangle([0, y, W, y + args.cell],
                        outline=(60, 60, 64), width=1)
            d.text((8, y + 10), pid, font=ft, fill=(235, 235, 235))
            d.text((8, y + 32), rec["r"]["trade"], font=ft, fill=(180, 200, 230))
            d.text((8, y + 54), rec["r"]["obj"], font=fs, fill=(150, 150, 155))
            d.text((8, y + 74), "%.2fm %s" % (rec["r"]["m"], rec["r"]["hold"]),
                   font=fs, fill=(150, 150, 155))
            for v in range(ncol):
                x = args.label + v * args.cell
                name = rec["v"].get(v)
                if not name:
                    continue
                p = os.path.join(args.images, name)
                if not os.path.exists(p):
                    continue
                im = Image.open(p).convert("RGB")
                im.thumbnail((args.cell - 6, args.cell - 6))
                sheet.paste(im, (x + 3, y + 3))
                d.text((x + 6, y + args.cell - 18), f"v{v}", font=fs,
                       fill=(255, 220, 120))
        out = args.out if len(parts) == 1 else \
            args.out.replace(".png", f"-{pi + 1}.png")
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        sheet.save(out)
        print(f"{out}  {len(part)}줄 × {ncol}칸  {W}×{H}")


if __name__ == "__main__":
    main()
