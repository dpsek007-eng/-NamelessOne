# -*- coding: utf-8 -*-
"""실루엣 PNG 들을 한 장으로 붙인다. 행이 체형, 열이 계층이다.

    python3 chars/src/sheet.py --shots chars/out/garments/shots \
                              --out chars/out/garments/sheet.png

옷을 55벌 내보내 놓고 파일 크기만 보는 것은 깜깜이다. 실루엣으로 읽히는
것이 목적이므로 확인도 실루엣으로 해야 한다. 세로로 훑으면 한 계층이
다섯 몸에서 어떻게 변하는지, 가로로 훑으면 한 몸이 열한 계층을 입었을 때
서로 갈리는지가 한눈에 보인다.
"""
import argparse, os, sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bodies import SLUG as BODY_SLUG
import garments as G

PAD, LAB = 6, 18

# PIL 기본 폰트는 한글이 전부 네모로 나온다. 라벨이 안 읽히면 대조표가
# 아니라 그냥 그림 55장이다. 시스템에 깔린 CJK 폰트를 찾아 쓴다.
FONTS = ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
         "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
         "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"]


def font(size=13):
    for f in FONTS:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except OSError:
                pass
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default="chars/out/garments/shots")
    ap.add_argument("--out", default="chars/out/garments/sheet.png")
    args = ap.parse_args()

    rows = [(k, BODY_SLUG[k]) for k in BODY_SLUG]
    cols = [(k, G.SLUG[k]) for k in G.ROBE]

    got = {}
    for _, b in rows:
        for _, c in cols:
            p = os.path.join(args.shots, f"{b}_{c}.png")
            if os.path.exists(p):
                got[(b, c)] = Image.open(p).convert("RGBA")
    if not got:
        raise SystemExit(f"실루엣이 없다: {args.shots}")
    w, h = next(iter(got.values())).size

    W = PAD + len(cols) * (w + PAD)
    H = LAB + PAD + len(rows) * (h + LAB + PAD)
    sheet = Image.new("RGB", (W, H), (238, 238, 238))
    d = ImageDraw.Draw(sheet)
    ft = font()

    for j, (ck, cs) in enumerate(cols):
        d.text((PAD + j * (w + PAD) + 2, 2), f"{ck}  {cs}", fill=(20, 20, 20), font=ft)
    for i, (rk, rs) in enumerate(rows):
        y = LAB + PAD + i * (h + LAB + PAD)
        for j, (ck, cs) in enumerate(cols):
            im = got.get((rs, cs))
            if im is None:
                continue
            x = PAD + j * (w + PAD)
            bg = Image.new("RGB", (w, h), (255, 255, 255))
            bg.paste(im, (0, 0), im)
            sheet.paste(bg, (x, y))
        d.text((PAD + 2, y + h + 2), f"{rk}  {rs}", fill=(20, 20, 20), font=ft)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    sheet.save(args.out)
    print(f"[sheet] {len(got)}칸 {sheet.size[0]}x{sheet.size[1]} → {args.out}")


if __name__ == "__main__":
    main()
