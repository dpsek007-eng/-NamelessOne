# -*- coding: utf-8 -*-
"""전승 23명이 역할 다섯 벌을 저마다 덮어쓰는 값을 읽고 검사한다.

`bodies.py` 는 역할 다섯 벌을 정하고 머리주석에 「전승 23명은 이 값을 각자
덮어쓴다」고 적어 뒀다. 그 덮어쓰기가 `data/shades.json` 이고, 이 파일이
그것을 읽는 유일한 자리다 — 블렌더도 뷰어도 여기를 거친다.

한 사람이 남과 달라지는 길이 두 층이다.

  macro  몸집. MPFB 매크로를 덮어쓰고 블렌더로 다시 굽는다.
  bones  자세와 비대칭. 굽지 않는다. 클립이 계산된 **뒤에** 뼈에 얹는다.

두 번째 층이 왜 굽는 층이 아닌가는 `make_demo.py:base_pose()` 주석에
이미 있다 — NLA 누수를 막으려고 네 동작이 전부 같은 뼈 집합을 0 까지
찍는다. 그러니 쉼자세에 굽은 등을 구워 넣어도 클립이 매 프레임 펴 버린다.

검사는 여기서 다 한다. 틀린 값이 블렌더까지 가면 여덟 분을 돌리고 나서
알게 되고, 뷰어까지 가면 눈으로 봐도 모른다.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PATH = os.path.join(ROOT, "data", "shades.json")

# MPFB 매크로 이름. bodies.BODIES 의 키와 같아야 한다 (race 는 딕셔너리라 뺀다).
MACRO_KEYS = {"gender", "age", "muscle", "weight",
              "height", "proportions", "cupsize", "firmness"}

# 뼈 53개. chars/out/bodies/report.json 의 bone_names 를 그대로 옮긴 것이고,
# load() 가 그 파일이 있으면 그것과 대조한다.
BONES = {
    "Root", "pelvis", "spine_01", "spine_02", "spine_03",
    "clavicle_l", "upperarm_l", "lowerarm_l", "hand_l",
    "clavicle_r", "upperarm_r", "lowerarm_r", "hand_r",
    "neck_01", "head",
    "thigh_l", "calf_l", "foot_l", "ball_l",
    "thigh_r", "calf_r", "foot_r", "ball_r",
}
for _lr in ("l", "r"):
    for _f in ("index", "middle", "ring", "pinky", "thumb"):
        for _s in ("01", "02", "03"):
            BONES.add(f"{_f}_{_s}_{_lr}")


def load(path=PATH, strict=True):
    """읽고 검사해서 {id: entry} 를 준다. 검사에 걸리면 SystemExit."""
    with open(path, encoding="utf-8") as fp:
        doc = json.load(fp)
    shades = doc["shades"]

    bones = BONES
    rp = os.path.join(ROOT, "chars", "out", "bodies", "report.json")
    if os.path.exists(rp):
        with open(rp, encoding="utf-8") as fp:
            real = set(json.load(fp)[0]["bone_names"])
        if real != BONES:
            raise SystemExit(
                f"뼈 이름표가 구운 몸과 다르다: 여기만 {sorted(BONES - real)} / "
                f"몸에만 {sorted(real - BONES)}")
        bones = real

    ids = None
    cp = os.path.join(ROOT, "data", "characters.json")
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as fp:
            d = json.load(fp)
        ids = {c["id"] for c in (d["characters"] if isinstance(d, dict) else d)}

    for cid, e in shades.items():
        w = f"{cid}:"
        if ids is not None and cid not in ids:
            raise SystemExit(f"{w} data/characters.json 에 없는 사람이다")
        # 근거 없이 몸을 고치지 않는다. 그 사람 글에서 가져온 줄이 있어야 한다.
        if strict and not e.get("src"):
            raise SystemExit(f"{w} src 가 없다 — 근거 없는 몸은 넣지 않는다")
        if strict and not e.get("why"):
            raise SystemExit(f"{w} why 가 없다 — 왜 그 값인지 적지 않은 값은 못 읽는다")

        for k, v in e.get("macro", {}).items():
            if k not in MACRO_KEYS:
                raise SystemExit(f"{w} 그런 매크로가 없다: {k} (있는 것 {sorted(MACRO_KEYS)})")
            if not isinstance(v, (int, float)) or not 0.0 <= v <= 1.0:
                raise SystemExit(f"{w} macro.{k} 는 0~1 이어야 한다: {v!r}")

        for b, ops in e.get("bones", {}).items():
            if b not in bones:
                raise SystemExit(f"{w} 그런 뼈가 없다: {b}")
            if not ops:
                raise SystemExit(f"{w} {b} 에 아무것도 없다")
            for op, val in ops.items():
                if op not in ("rot", "scale"):
                    raise SystemExit(f"{w} {b}.{op} — rot 이나 scale 만 쓴다")
                if not (isinstance(val, list) and len(val) == 3):
                    raise SystemExit(f"{w} {b}.{op} 는 세 값이어야 한다: {val!r}")
                if op == "rot" and any(abs(x) > 60 for x in val):
                    # 60도를 넘기면 자세가 아니라 동작이다. 동작은 클립이 한다.
                    raise SystemExit(f"{w} {b}.rot 이 60도를 넘는다: {val!r}")
                if op == "scale" and any(x <= 0.3 or x > 2.0 for x in val):
                    raise SystemExit(f"{w} {b}.scale 이 0.3~2.0 밖이다: {val!r}")
    return shades


def macro_for(role_macro, entry):
    """역할 기본값 위에 그 사람 것을 얹는다. 적은 항목만 덮는다."""
    out = dict(role_macro)
    out.update((entry or {}).get("macro", {}))
    return out


def needs_bake(entry):
    """몸을 다시 구워야 하는가. 자세뿐이면 굽지 않는다."""
    return bool((entry or {}).get("macro"))


if __name__ == "__main__":
    s = load()
    bake = [k for k, v in s.items() if needs_bake(v)]
    print(f"[shades] {len(s)}명 검사 통과")
    for cid, e in s.items():
        m = ", ".join(f"{k}={v}" for k, v in e.get("macro", {}).items()) or "-"
        print(f"  {cid:16s} macro[{m}]  뼈 {len(e.get('bones', {}))}개")
    print(f"[shades] 다시 구울 몸 {len(bake)}벌: {', '.join(bake) or '없다'}")
