# -*- coding: utf-8 -*-
"""두상 6 × 이목구비 8 부품 조립.

docs/22-아트.md 「이목구비 8 종」이 정한 판정 기준을 만든다:

  ① 하나로 읽힌다 — 두 그림이 아니라 한 사람처럼
  ② 이목구비가 갈린다 — 여덟 원형이 눈매·입매에서 서로 다르다
  ③ 두상이 계층으로 갈린다 — 머리형이 처음부터 보인다
  ⑤ 초점 레이어가 분리된다 — ★ 단계의 뭉갬·흐림·이중상이 조합에도 그대로 걸린다

조립 알고리즘:
  두상(base) 의 얼굴 상자 안에 이목구비(feature) 의 얼굴 상자를
  맞춰 끼운다. 이목구비의 얼굴 상자만 골라 피부톤을 맞추고,
  소프트 엣지로 합친다. 머리형·어깨·배경은 처음부터 보인다.

대표 장은 focus_stack.pick_frames 가 고른 pick.json 을 쓴다 — 규약이
둘이면 안 된다.

쓰는 법:
  python3 tools/portrait_assemble.py --grid                        48칸 격자
  python3 tools/portrait_assemble.py --grid --focus                초점 줄 포함
  python3 tools/portrait_assemble.py --heads head_hood --faces face_clear --out /tmp/a.png
"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import focus_stack
from focus_stack import build as focus_build, face_box, feature_mask

import numpy as np
from PIL import Image, ImageFilter, ImageDraw


def erase_features(base, box):
    """이목구비 자리를 강하게 지운다 — 얼굴 상자 전체를 흐린 피부로.

    합성에서 이목구비 원형이 이 자리를 완전히 덮어쓰므로, 지운 자리는
    엣지(얼굴-머리 경계)에서만 보인다. 엣지에서도 이중으로 안 보이게
    세게 지운다.
    """
    src = base.filter(ImageFilter.GaussianBlur(max(18.0, base.size[0] * 0.035)))
    x, y, w, h = box
    m = Image.new("L", base.size, 0)
    ImageDraw.Draw(m).rectangle([x, y, x + w, y + h], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(max(6.0, w * 0.06)))
    return Image.composite(src, base, m)


def _region_stats(img, box):
    """사각형 안 (평균, 표준편차) — 피부톤 보정용."""
    x, y, w, h = [int(v) for v in box]
    a = np.asarray(img, dtype=np.float32)
    # 가장자리가 너무 딱딱하지 않게 가우시안 가중
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rectangle([x, y, x + w, y + h], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(4.0))
    wt = np.asarray(mask, dtype=np.float32)[..., None] / 255.0
    mean = (a * wt).sum(axis=(0, 1)) / (wt.sum() + 1e-9)
    # 분산도 같이 돌려준다 — 채도·대비 차이를 줄이는 데 쓴다.
    diff = a - mean
    var = ((diff ** 2) * wt).sum(axis=(0, 1)) / (wt.sum() + 1e-9)
    return mean, np.sqrt(np.maximum(var, 1e-9))


def color_match(src, dst_mean, dst_std, src_mean, src_std):
    """대비-평균 보정. uniform 평균 이동은 짙음·옅음 차이를 못 지운다.

    (src - src평균) 을 대비비율로 늘리고 dst평균으로 옮긴다.
    """
    ratio = dst_std / (src_std + 1e-9)
    return np.clip((src - src_mean) * ratio + dst_mean, 0, 255)


def assemble(head_path, face_path):
    """(두상, 이목구비) 파일 두 개 → 합성 초상 한 장."""
    base = Image.open(head_path).convert("RGB")
    fe = Image.open(face_path).convert("RGB")
    bx, by, bw, bh, _ = face_box(base)
    fx, fy, fw, fh, _ = face_box(fe)
    if not (bw and bh and fw and fh):
        raise ValueError(f"얼굴 상자를 못 찾았다 — {os.path.basename(head_path)} / "
                         f"{os.path.basename(face_path)}. 정면 초상이어야 한다.")

    # 1 — 겉층의 얼굴 특징을 강하게 지운다 (엣지에서만 보이는 잔존용)
    out = erase_features(base, (bx, by, bw, bh))

    # 2 — 이목구비 원형의 얼굴 상자만 골라낸다
    face_crop = fe.crop((fx, fy, fx + fw, fy + fh))

    # 3 — 두상 얼굴 상자 크기에 맞춘다
    face_scaled = face_crop.resize((int(bw), int(bh)), Image.LANCZOS)

    # 4 — 피부톤을 맞춘다 (평균 + 대비)
    dst_mean, dst_std = _region_stats(out, (bx, by, bw, bh))
    src_mean, src_std = _region_stats(face_scaled, (0, 0, bw, bh))
    face_arr = color_match(
        np.asarray(face_scaled, dtype=np.float32),
        dst_mean, dst_std, src_mean, src_std,
    )
    face_matched = Image.fromarray(face_arr.astype(np.uint8))

    # 5 — 소프트 엣지로 합친다 — 얼굴 상자 전체, 아크릴 마스크
    edge = max(6.0, bw * 0.04)
    mask = Image.new("L", (int(bw), int(bh)), 255)
    mask = mask.filter(ImageFilter.GaussianBlur(edge))

    out.paste(face_matched, (int(bx), int(by)), mask)
    return out


def pick(facedir):
    """전 종의 대표 장 — focus_stack 규약(pick.json)을 그대로 쓴다."""
    return focus_stack.pick_frames(facedir)


def pair_paths(facedir, picked, head_id, face_id):
    hp = picked[head_id]["image"]
    fp = picked[face_id]["image"]
    return os.path.join(facedir, hp), os.path.join(facedir, fp)


def grid(facedir, focus=False, out="/tmp/parts_grid.png"):
    picked = pick(facedir)
    heads = sorted(g for g in picked if g.startswith("head_"))
    faces = sorted(g for g in picked if g.startswith("face_"))
    cell = 256
    row_h = 96  # 초점 견본 한 칸 높이
    focus_cells = [("head_hood", "face_guard"), ("head_bare", "face_deep")] if focus else []
    H = cell * len(heads)
    if focus_cells:
        H += row_h * 2 + 24
    sheet = Image.new("RGB", (cell * len(faces), H), (18, 18, 22))

    for hi, hd in enumerate(heads):
        for fi, fc in enumerate(faces):
            hp, fp = pair_paths(facedir, picked, hd, fc)
            im = assemble(hp, fp).resize((cell, cell), Image.LANCZOS)
            sheet.paste(im, (fi * cell, hi * cell))

    # 판정 ⑤ — 특정 칸을 ★1~★6 으로 구운 줄을 아래에 붙인다
    if focus_cells:
        from PIL import ImageFont
        tmp = os.path.join(facedir, "__assemble")
        os.makedirs(tmp, exist_ok=True)
        for i, (hd, fc) in enumerate(focus_cells):
            hp, fp = pair_paths(facedir, picked, hd, fc)
            im = assemble(hp, fp)
            name = f"{hd.replace('head_', '')}×{fc.replace('face_', '')}"
            p = os.path.join(tmp, f"{name}.png")
            im.save(p)
            _, found, _ = focus_build(p, tmp)
            y = cell * len(heads) + i * (row_h + 18) + 3
            for star in range(1, 7):
                s = Image.open(os.path.join(tmp, f"{name}_s{star}.png"))
                sheet.paste(s.resize((row_h, row_h), Image.LANCZOS), (3 + (star - 1) * row_h, y))
            tag = "검출" if found else "표준자리"
            try:
                ft = ImageFont.truetype(focus_stack.KO_FONT, 11)
            except OSError:
                ft = ImageFont.load_default()
            ImageDraw.Draw(sheet).text((3, y - 13), f"{name} ({tag})",
                                       fill=(205, 205, 210), font=ft)
    sheet.save(out)
    print(f"부품 격자 → {out}  ({len(heads)}두상 × {len(faces)}이목구비"
          + (f" + 초점 줄 {len(focus_cells)}개)" if focus_cells else ")"))
    return out


def single(facedir, head_id, face_id, out):
    picked = pick(facedir)
    hp, fp = pair_paths(facedir, picked, head_id, face_id)
    assemble(hp, fp).save(out)
    print(f"{head_id} × {face_id} → {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grid", action="store_true", help="두상 6 x 이목구비 8 격자")
    ap.add_argument("--focus", action="store_true", help="격자에 ★1~★6 초점 줄")
    ap.add_argument("--heads", help="이목구비와 합칠 두상 id (--out 필수)")
    ap.add_argument("--faces", help="두상과 합칠 이목구비 id (--out 필수)")
    ap.add_argument("--faces-dir", default="pipeline3d/out/faces")
    ap.add_argument("--out", default="/tmp/parts_grid.png")
    a = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    facedir = a.faces_dir if os.path.isabs(a.faces_dir) else os.path.join(root, a.faces_dir)
    if a.heads and a.faces:
        single(facedir, a.heads, a.faces, a.out)
        return
    if a.grid:
        grid(facedir, a.focus, a.out)
        return
    ap.error("--grid 를 주거나 --heads/--faces 쌍을 줘라 (둘 다 pick.json 이 있어야 한다)")


if __name__ == "__main__":
    main()