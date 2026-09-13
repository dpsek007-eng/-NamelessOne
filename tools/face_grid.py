# -*- coding: utf-8 -*-
"""초상 격자 — 78종을 한 장에 붙여 눈으로 본다.

픽셀 평균이나 CLIP 으로 재는 게 아니라, 보이는 대로 본다. 격자를 보고
「이 모든 얼굴이 젊고 매끈한가」를 내 눈으로 센다.

쓸 장은 pick.json 의 대표 장 (focus_stack --pick 이 고른 것)과 같게 한다.
--pick 없이 부르면 종마다 v0 을 쓴다. 장 번호를 보고 싶으면 --variant 를
주면 전부 그 번호로 갈아낀다 (씨앗이 id 기반이라 장 번호끼리 비교할 수 있다).
"""
import argparse, json, os
from PIL import Image, ImageDraw, ImageFont


def load(facesdir):
    pj = os.path.join(facesdir, "pick.json")
    pick = {}
    if os.path.exists(pj):
        pick = {k: v["image"] for k, v in json.load(open(pj)).items()}
    ij = os.path.join(facesdir, "index.json")
    if os.path.exists(ij):
        with open(ij, encoding="utf-8") as f:
            return json.load(f)["rows"], pick
    # index.json 은 생성이 끝나야 쓰이므로, 돌고 있는 중엔 파일에서 직접 본다.
    rows = []
    for p in sorted(os.listdir(facesdir)):
        if p.endswith(".png"):
            cid = p.rsplit("_v", 1)[0]
            rows.append({"id": cid, "kind": "named" if "_" not in cid else "part",
                         "ko": cid, "rarity": ""})
    dedup = {}
    for r in rows:
        dedup.setdefault(r["id"], r)
    return list(dedup.values()), pick


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="pipeline3d/out/faces")
    ap.add_argument("--out", default="/tmp/faces_grid.png")
    ap.add_argument("--cell", type=int, default=224)
    ap.add_argument("--cols", type=int, default=13)
    ap.add_argument("--variant", type=int, default=None,
                    help="지정하면 pick 을 무시하고 전부 이 장 번호로 본다")
    ap.add_argument("--name-only", action="store_true",
                    help="이름 있는 23명만")
    ap.add_argument("--part-only", action="store_true",
                    help="역할x계층 55종만")
    args = ap.parse_args()

    index, pick = load(args.dir)
    if args.name_only:
        index = [r for r in index if r["kind"] == "named"]
    elif args.part_only:
        index = [r for r in index if r["kind"] == "part"]

    cells = []
    for r in index:
        img = pick.get(r["id"]) if args.variant is None else None
        if img is None:
            img = f"{r['id']}_v{args.variant if args.variant is not None else 0}.png"
        p = os.path.join(args.dir, img)
        if not os.path.exists(p):
            continue
        im = Image.open(p).convert("RGB").resize((args.cell, args.cell))
        cells.append((r["id"], r["ko"], r.get("rarity", ""), im))

    rows = (len(cells) + args.cols - 1) // args.cols
    W = args.cols * args.cell
    H = rows * (args.cell + 24)
    sheet = Image.new("RGB", (W, H), (18, 18, 22))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("NotoSansCJK-Regular.ttc", 14)
    except OSError:
        font = ImageFont.load_default()
    for i, (cid, ko, rarity, im) in enumerate(cells):
        x = (i % args.cols) * args.cell
        y = (i // args.cols) * (args.cell + 24)
        sheet.paste(im, (x, y))
        draw.text((x + 4, y + args.cell + 3),
                  f"{ko} · {cid}", fill=(220, 220, 230), font=font)
    sheet.save(args.out)
    print(f"{len(cells)}장 → {args.out}  ({W}x{H})")


if __name__ == "__main__":
    main()