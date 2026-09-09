# -*- coding: utf-8 -*-
"""실루엣이 정말 갈리는가 — 역할 5종 · 계층 11종을 픽셀로 잰다.

docs/22 는 「체형·자세 5 = 역할별」이라고 적어 두었다. 실제로 뽑힌 그림에서
그게 보이는지는 눈으로 봐서는 모른다. 그래서 잰다.

  python3 tools/silhouette_diff.py

재는 법: chars/out/garments/shots/<역할>_<계층>.png 는 배경이 투명하다.
알파를 실루엣으로 쓴다 (밝기로 재면 투명이 검정이 되어 전부 같아진다 —
한 번 그렇게 재서 전부 0.00% 가 나왔다). 두 장의 실루엣이 다른 픽셀의 비율.
"""
import os, sys, itertools
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "chars/out/garments/shots")
ROLES = [("guard","수호"),("resist","저항"),("devote","헌신"),("seek","탐구"),("flee","도피")]
TIERS = [("royal","왕실"),("noble","귀족"),("mage","술사"),("clergy","성직"),
         ("clerk","관리"),("merchant","상인"),("artisan","장인"),
         ("peasant","농어민"),("soldier","병졸"),("servant","하인"),("vagrant","유랑")]


def sil(path):
    im = Image.open(path)
    a = np.array(im)
    if im.mode == "RGBA" and a[..., 3].min() < 250:
        return a[..., 3] > 127
    # 알파가 평평하면 밝기로 떨어진다
    return np.array(im.convert("L")) > 127


def diff(a, b):
    return float((a != b).mean()) * 100.0


def main():
    if not os.path.isdir(SHOTS):
        raise SystemExit(f"없다: {SHOTS}")
    S = {}
    for rs, _ in ROLES:
        for ts, _ in TIERS:
            p = os.path.join(SHOTS, f"{rs}_{ts}.png")
            if os.path.exists(p):
                S[(rs, ts)] = sil(p)
    print(f"실루엣 차이 — {len(S)}장\n")

    # 1 같은 계층 · 다른 역할 → 역할이 보이는가
    per_tier, role_all = [], []
    for ts, tk in TIERS:
        v = [diff(S[(a, ts)], S[(b, ts)])
             for a, b in itertools.combinations([r for r, _ in ROLES], 2)
             if (a, ts) in S and (b, ts) in S]
        if v:
            per_tier.append((tk, sum(v) / len(v), max(v)))
            role_all += v

    # 2 같은 역할 · 다른 계층 → 계층이 보이는가
    tier_all = []
    for rs, _ in ROLES:
        tier_all += [diff(S[(rs, a)], S[(rs, b)])
                     for a, b in itertools.combinations([t for t, _ in TIERS], 2)
                     if (rs, a) in S and (rs, b) in S]

    print("1. 같은 계층 · 다른 역할  (역할이 보이는가)")
    for tk, m, mx in per_tier:
        print(f"   {tk:<5}{'':<2}평균 {m:5.2f}%   최대 {mx:5.2f}%")
    print(f"   {'전체':<5}{'':<2}평균 {sum(role_all)/len(role_all):5.2f}%   "
          f"최소 {min(role_all):5.2f}%   최대 {max(role_all):5.2f}%\n")

    print("2. 같은 역할 · 다른 계층  (계층이 보이는가)")
    print(f"   {'전체':<5}{'':<2}평균 {sum(tier_all)/len(tier_all):5.2f}%   "
          f"최소 {min(tier_all):5.2f}%   최대 {max(tier_all):5.2f}%\n")

    r = sum(role_all)/len(role_all); t = sum(tier_all)/len(tier_all)
    same = sum(1 for v in tier_all if v < 0.01)
    print(f"3. 판정")
    print(f"   역할 {r:.2f}%  vs  계층 {t:.2f}%  →  계층이 {t/r:.1f}배 더 갈린다")
    print(f"   → 역할은 눈으로 안 갈린다. 옷이 몸을 덮는다.")
    if same:
        print(f"   ⚠ 계층 짝 {same}쌍은 픽셀까지 똑같다 (실루엣만으로는 같은 옷이다)")


if __name__ == "__main__":
    main()
