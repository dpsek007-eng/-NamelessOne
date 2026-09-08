# -*- coding: utf-8 -*-
"""★6 특성이 「고유」로 나올 확률 — 출발 등급이 도착점의 질에도 남는다.

지금까지 이 저장소는 **도달**만 등급에 따라 갈리게 해 두었다. 본디가 6 이상일
확률이 ★1은 7%, ★4는 28%. 그런데 일단 ★6에 도착하면 둘이 똑같았다 —
스탯은 ★5에서 멈추고(`04-본디.md`) 특성은 성급이 열어 주므로, 도착한 뒤에는
출발 등급이 흔적도 없이 지워졌다.

    "1성이 6성까지 갔을 때 좋을 확률은 아주 낮고, 1성이 6성까지 갈 수 있을
     확률도 낮다. 태생 4성은 6성까지 가기 쉽고, 가서 더 강해질 확률이 아주 높다.
     항상이라기보다는 확률이."

그래서 문 하나를 더 단다. **★6 특성은 두 갈래로 나온다.**

    고유 특성   그 사람 자신의 기록에서 나온 것
    빌린 특성   겹쳐서 지운 사람들에게서 묻어온 것 (범용·약함)

확률은 새로 지어내지 않는다. **겹치기로 채우지 않은 비율**이 그대로 확률이다.

    P(고유 | 출발 r) = max(바닥, 1 - 겹친명수(r) / 겹친명수(★1))

★1은 128명을 통째로 빌려서 올라오므로 자기 것이 남지 않고, ★6 직뽑은 한 명도
겹치지 않았으므로 전부 자기 것이다. 이 정의에는 새 상수가 바닥값 하나뿐이다.

바닥값은 계산이 아니라 **결정**이다. `04-본디.md` 가 지켜야 한다고 못박은
「★1 본디 10의 꼬리」를 0으로 만들지 않기 위해 남긴다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fusion_sim import shades_for, BONDI
from power import STAR_CAP_EARLY
from summon_value import BASIC, DEEP, DEEP_COST, BOND

CAP = STAR_CAP_EARLY

# ★1이 끝까지 겹쳐 올라와도 자기 것이 5%는 남는다. 유일하게 지어낸 수이고,
# 지어낸 이유는 꼬리를 0으로 만들지 않기 위해서다. 밸런싱 시 여기부터 만진다.
OWN_FLOOR = 0.05


def borrowed(r, cap=CAP):
    """출발 r 이 cap 까지 오는 동안 겹쳐서 지운 잔상 수"""
    return shades_for(min(r, cap), cap)


def p_own(r, cap=CAP):
    """★cap 특성이 고유로 나올 확률"""
    base = borrowed(1, cap)
    return max(OWN_FLOOR, 1.0 - borrowed(r, cap) / base)


def p_reach(r, cap=CAP):
    """본디가 cap 이상일 확률 = 애초에 도착할 수 있는 확률"""
    if r >= cap:
        return 1.0
    return sum(v for k, v in BOND[r].items() if k >= cap)


def p_good(r, cap=CAP):
    """뽑은 한 명이 결국 ★cap 고유 특성에 이를 확률 (두 관문의 곱)"""
    return p_reach(r, cap) * p_own(r, cap)


def per_pull(table, cap=CAP):
    return sum(p * p_good(r, cap) for r, p in table.items())


if __name__ == "__main__":
    assert 0.0 < OWN_FLOOR < 1.0
    assert abs(p_own(CAP) - 1.0) < 1e-9, "직뽑 ★6 은 한 명도 겹치지 않았으므로 100% 고유여야 한다"
    for a, b in zip(range(1, CAP), range(2, CAP + 1)):
        assert p_own(a) <= p_own(b) + 1e-12, f"고유 확률이 ★{a}→★{b} 에서 뒤집힌다"
        assert p_reach(a) <= p_reach(b) + 1e-12, f"도달 확률이 ★{a}→★{b} 에서 뒤집힌다"

    print("=" * 74)
    print(f"1. 두 관문 — 도착할 확률 x 도착해서 자기 것일 확률   (상한 ★{CAP})")
    print("=" * 74)
    print(f"{'출발':>4}{'겹칠 잔상':>11}{'고유 확률':>11}{'본디≥6':>10}{'둘 다':>10}{'★1 대비':>10}")
    base = p_good(1)
    for r in range(1, CAP + 1):
        note = "  ← 바닥값" if p_own(r) == OWN_FLOOR else ""
        print(f"★{r:<3}{borrowed(r):>10.1f}명{p_own(r):>10.1%}{p_reach(r):>10.1%}"
              f"{p_good(r):>10.2%}{p_good(r)/base:>9.0f}배{note}")
    print()
    print("  왼쪽 두 칸이 이 파일이 새로 정하는 것이다. 오른쪽 두 칸은 이미 있던 값이고,")
    print("  둘을 곱해야 「좋은 ★6 하나」가 나올 확률이 된다.")

    print()
    print("=" * 74)
    print("2. 문장으로")
    print("=" * 74)
    for r in (1, 4):
        print(f"  태생 ★{r} 한 명은 {p_reach(r):.0%} 확률로 ★{CAP}까지 가고, 가는 데 "
              f"{borrowed(r):.0f}명을 쓰고,")
        print(f"          도착해도 {p_own(r):.0%} 확률로만 자기 특성을 얻는다 "
              f"→ 합쳐서 {p_good(r):.2%}")
    print(f"\n  ★4 는 ★1 보다 {p_reach(4)/p_reach(1):.0f}배 쉽게 도착하고, "
          f"{borrowed(1)/borrowed(4):.1f}배 싸게 도착하고,")
    print(f"  도착한 뒤 좋을 확률이 {p_own(4)/p_own(1):.0f}배다. 곱하면 {p_good(4)/p_good(1):.0f}배.")
    print("  ★1 에게도 0 은 아니다 — 300번에 한 명꼴로 나온다. 그것이 꼬리다.")

    print()
    print("=" * 74)
    print("3. 소환 1회당 「좋은 ★6」 기대치")
    print("=" * 74)
    b, d = per_pull(BASIC), per_pull(DEEP)
    print(f"  부름      1회 {b:>7.2%}   울림 1당 {b:.4f}")
    print(f"  깊은 부름 1회 {d:>7.2%}   울림 1당 {d/DEEP_COST:.4f}  ({d/DEEP_COST/b:.2f}배)")
    print()
    print("  `summon_value.py` 의 네 눈금은 서로 다른 답을 냈다(재료값은 일반 5배,")
    print("  그릇값은 읽기에 따라 1.18배와 1.49배로 갈렸다). 이 눈금은 그 갈림을 지나")
    print("  깊은 부름 쪽으로 온다 — 고급 소환이 사는 것이 「도달」만이 아니라")
    print("  「도달했을 때의 질」까지가 되기 때문이다.")

    print()
    print("=" * 74)
    print("4. 남는 문제")
    print("=" * 74)
    print("  · 상한이 ★8, ★10 으로 열리면 겹칠 명수가 다시 벌어지므로 이 표를 다시 잰다.")
    print("    정의가 명수 비율이라 자동으로 따라오지만, 바닥값 5%는 손으로 확인해야 한다.")
    print("  · 「빌린 특성」이 몇 종이고 얼마나 약한지는 아직 안 정했다 (`02-캐릭터-시스템.md`).")
    print("  · `04-본디.md` 의 「저등급 출신은 마지막 스킬이 더 강하다」와 정면으로 어긋난다.")
    print("    그 문장은 이 결정으로 대체된다.")
