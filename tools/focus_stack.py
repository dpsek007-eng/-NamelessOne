# -*- coding: utf-8 -*-
"""초점 층 — 초상 한 장을 선명도 여섯 단계로 만든다.

focus_curve.py 가 정한 값(흐림·이목구비·이중상·어긋남)을 실제 그림에 건다.
게임 안에서는 셰이더 한 번이면 되지만, 지금은 그 값이 정말 「없다」가 아니라
「안 맞는다」로 보이는지 눈으로 확인해야 하므로 PNG 로 굽는다.

  python3 tools/focus_stack.py <초상.png> [--out 폴더] [--borrowed]
  python3 tools/focus_stack.py --all           out/faces 전부 (v0 만)

세 가지를 이 순서로 쌓는다. viewer/index.html 의 합성 순서와 같아야 한다.
같지 않으면 웹에서 본 것과 구운 것이 달라지고, 어느 쪽이 맞는지 알 수 없다.

  1 이목구비   이목구비 자리만 뭉갠 판 위에 원본을 feature 만큼 덮는다
  2 흐림       전체에 가우시안
  3 이중상     어긋난 사본 둘을 ghost 만큼 깔고 그 위에 본판

이목구비 자리는 정면 초상이라는 전제로 찾는다. OpenCV 정면 검출을 쓰고,
못 찾으면 화폭 기준 표준 위치로 떨어진다 (그 경우 로그에 적는다 —
자리가 틀린 채로 뭉개면 이목구비가 아니라 뺨이 사라진다).
"""
import argparse, os, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from focus_curve import (blur, feature, ghost, ghost_off, focus, CAP,
                         GHOST_RESID, STEPS)

import numpy as np
from PIL import Image, ImageFilter, ImageDraw

REF = 512.0          # 문서의 px 값은 512 기준이다
BORROW_OFF = 1.0     # 빌린 특성이 ★6 에서도 남기는 어긋남 (px, 512 기준)


# 정면 검출기를 하나만 쓰면 유화풍 초상에서 20%쯤 놓친다 (실측).
# 셋을 순서대로 대 보고, 조건도 한 번 느슨하게 다시 댄다.
_CASCADES = ("haarcascade_frontalface_alt2.xml",
             "haarcascade_frontalface_default.xml",
             "haarcascade_frontalface_alt.xml")


def face_box(img):
    """(x, y, w, h, 찾았는가). 정면 초상이라는 전제."""
    import cv2
    a = np.array(img.convert("L"))
    a = cv2.equalizeHist(a)          # 유화풍은 명암이 눌려 있어 검출이 잘 안 된다
    lo = a.shape[0] // 10
    for nb, sf in ((5, 1.1), (3, 1.05)):
        for c in _CASCADES:
            cc = cv2.CascadeClassifier(cv2.data.haarcascades + c)
            hits = cc.detectMultiScale(a, sf, nb, minSize=(lo, lo))
            if len(hits):
                # 여럿 잡히면 가장 큰 것. 초상에는 사람이 하나뿐이어야 한다.
                x, y, w, h = max(hits, key=lambda r: r[2] * r[3])
                return int(x), int(y), int(w), int(h), True
    # 못 찾았을 때: 가슴 위 정면 초상의 표준 자리
    W, H = img.size
    w = int(W * 0.42); h = int(H * 0.42)
    return (W - w) // 2, int(H * 0.16), w, h, False


def feature_mask(size, box, feather):
    """이목구비(눈~입) 자리에 부드러운 타원 마스크."""
    x, y, w, h = box
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).ellipse(
        [x + w * 0.06, y + h * 0.30, x + w * 0.94, y + h * 0.92], fill=255)
    return m.filter(ImageFilter.GaussianBlur(feather))


def stage(src, mask, f, borrowed=False, scale=1.0):
    """초점 f 에서의 한 장."""
    b  = blur(f) * scale
    ft = feature(f)
    gh = ghost(f)
    go = ghost_off(f) * scale
    if borrowed:
        # 빌린 특성은 초점이 다 맞아도 상이 하나로 안 합쳐진다 (docs/04).
        gh = max(gh, GHOST_RESID)
        go = max(go, BORROW_OFF * scale)

    # 1 이목구비 — 눈~입 자리만 (1-ft) 만큼 뭉갠다. 바깥은 건드리지 않는다.
    #   ft=0.25 이면 그 자리의 3/4 이 뭉개진 채다. 얼굴이 없는 게 아니라
    #   이목구비가 아직 안 맞는 것 — 윤곽·머리·옷은 처음부터 다 보인다.
    smear = src.filter(ImageFilter.GaussianBlur(max(1.0, src.size[0] * 0.045)))
    base  = Image.composite(smear, src, mask.point(lambda v: int(v * (1.0 - ft))))

    # 2 흐림 — 전체
    if b > 0.01:
        base = base.filter(ImageFilter.GaussianBlur(b))

    # 3 이중상 — 어긋난 사본 둘을 gh 만큼 섞는다.
    #   뷰어는 배경이 비어 있어 사본을 밑에 깔지만, 구운 초상은 배경이
    #   불투명하다. 밑에 깔면 본판이 덮어 아무것도 안 보이고, 화면 합성으로
    #   올리면 밝은 배경에서 값이 죽는다. 배경 밝기에 안 걸리는 가중평균으로
    #   섞는다 — 「탑이 여럿을 하나로 기억한다」는 그림이 이것이다.
    if gh <= 0.001:
        return base
    a = np.asarray(base, dtype=np.float32)
    other = np.zeros_like(a)
    for dx, dy in ((-go * 2, -go), (go * 2, go * 0.6)):
        other += np.asarray(base.transform(
            base.size, Image.AFFINE, (1, 0, -dx, 0, 1, -dy),
            resample=Image.BICUBIC), dtype=np.float32) / 2.0
    out = a * (1.0 - gh) + other * gh
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))


def build(path, outdir, borrowed=False):
    src = Image.open(path).convert("RGB")
    scale = src.size[0] / REF
    x, y, w, h, found = face_box(src)
    mask = feature_mask(src.size, (x, y, w, h), max(2.0, w * 0.06))
    name = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(outdir, exist_ok=True)

    made = []
    for star in range(1, CAP + 1):
        f = focus(star, 0)
        img = stage(src, mask, f, borrowed, scale)
        p = os.path.join(outdir, f"{name}_s{star}.png")
        img.save(p)
        made.append(p)

    # 대조표 — 여섯 장을 한 줄로
    tw = 384
    sheet = Image.new("RGB", (tw * CAP, tw), (16, 16, 16))
    for i, p in enumerate(made):
        sheet.paste(Image.open(p).resize((tw, tw), Image.LANCZOS), (tw * i, 0))
    sp = os.path.join(outdir, f"{name}_sheet.png")
    sheet.save(sp)
    return name, found, sp


KO_FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"


def record(root, cid="seren_v0", w=300):
    """검사 기록 한 장 — 위 고유 / 아래 빌린, ★1~★6.

    구운 그림은 무겁고 이진이라 저장소에 안 넣는다 (.gitignore).
    대신 이 한 장을 남긴다. chars/out/garments/sheet.png 와 같은 뜻이다.
    """
    from PIL import ImageFont
    src = os.path.join(root, "pipeline3d/out/faces", cid + ".png")
    a = os.path.join(root, "art/focus"); b = os.path.join(root, "art/focus_borrowed")
    build(src, a, borrowed=False)
    build(src, b, borrowed=True)
    im = Image.new("RGB", (w * CAP, w * 2 + 24), (14, 16, 19))
    for r, d in enumerate((a, b)):
        for i in range(CAP):
            im.paste(Image.open(os.path.join(d, f"{cid}_s{i+1}.png"))
                     .resize((w, w), Image.LANCZOS), (w * i, 24 + w * r))
    try:
        f = ImageFont.truetype(KO_FONT, 15)
    except OSError:
        f = ImageFont.load_default()
    dr = ImageDraw.Draw(im)
    for i in range(CAP):
        dr.text((w * i + 8, 4), f"★{i+1}", fill=(205, 205, 210), font=f)
    dr.text((w * CAP - 240, 4), "위 고유 · 아래 빌린 (이중상 0.15 잔류)",
            fill=(150, 152, 158), font=f)
    p = os.path.join(root, "art/focus_record.png")
    im.save(p)
    print(f"검사 기록 → {p}")


def write_boxes(facedir):
    """초상마다 얼굴 상자를 재서 0~1 로 적어 둔다.

    뷰어(브라우저)에는 얼굴 검출기가 없다. 여기서 한 번 재고 표로 넘긴다.
    표가 없으면 뷰어는 화폭 기준 표준 자리로 떨어진다 — 자리가 틀리면
    이목구비가 아니라 뺨이 뭉개지므로, 표가 있는 쪽이 낫다.
    """
    rows, miss = {}, 0
    for f in sorted(glob.glob(os.path.join(facedir, "*_v*.png"))):
        im = Image.open(f).convert("RGB")
        x, y, w, h, found = face_box(im)
        W, H = im.size
        rows[os.path.basename(f)] = {
            "x": round(x / W, 4), "y": round(y / H, 4),
            "w": round(w / W, 4), "h": round(h / H, 4), "found": found}
        if not found:
            miss += 1
    import json
    with open(os.path.join(facedir, "boxes.json"), "w", encoding="utf-8") as fp:
        json.dump(rows, fp, ensure_ascii=False, indent=1)
    print(f"얼굴 상자 {len(rows)}장 → boxes.json  (검출 실패 {miss}장)")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?")
    ap.add_argument("--boxes", action="store_true", help="얼굴 상자만 재서 boxes.json")
    ap.add_argument("--record", nargs="?", const="seren_v0", default=None,
                    help="검사 기록 한 장 (art/focus_record.png)")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--faces", default="pipeline3d/out/faces")
    ap.add_argument("--out", default="art/focus")
    ap.add_argument("--borrowed", action="store_true", help="빌린 특성 — 이중상이 안 사라진다")
    a = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if a.record:
        record(root, a.record)
        return
    if a.boxes:
        write_boxes(a.faces if os.path.isabs(a.faces) else os.path.join(root, a.faces))
        return
    srcs = [a.src] if a.src else []
    if a.all:
        srcs = sorted(glob.glob(os.path.join(root, a.faces, "*_v0.png")))
    if not srcs:
        raise SystemExit("초상을 대라. (예: tools/focus_stack.py pipeline3d/out/faces/seren_v0.png)")

    outdir = a.out if os.path.isabs(a.out) else os.path.join(root, a.out)
    miss = 0
    for s in srcs:
        name, found, sheet = build(s, outdir, a.borrowed)
        if not found:
            miss += 1
        print(f"  {name:<22} 얼굴 {'검출' if found else '표준자리(미검출)'}  → {os.path.basename(sheet)}")
    print(f"\n{len(srcs)}종 × ★1~★{CAP} = {len(srcs)*CAP}장 + 대조표 {len(srcs)}장 → {outdir}")
    if miss:
        print(f"⚠ {miss}종은 정면 검출 실패 — 표준 자리로 뭉갰다. 눈으로 봐야 한다")


if __name__ == "__main__":
    main()
