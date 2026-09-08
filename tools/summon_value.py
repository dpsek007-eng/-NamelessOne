# -*- coding: utf-8 -*-
"""소환 1회의 값 — 조각 모형 기준 재산출.

`18-소환.md` 의 「1성 환산 기대값」은 **옛 2배 승급 모형**의 눈금이었다.
그 시절 규칙은 「n성 2명 → (n+1)성 1명」이라 ★r 한 명이 ★1 2^(r-1) 명과 정확히
같았고, 그래서 한 줄짜리 환산이 성립했다. 조각 모형에서는 성립하지 않는다.
이유가 둘이고, 둘이 서로 반대 방향으로 작용한다.

  1. 재료로 쓰면 성급이 **무의미해진다.**
     `08-승급.md`: "재료: 아무 잔상이나 겹칠 수 있다."
     겹치기는 머릿수를 세지 성급을 세지 않는다(`pacing_sim.py` 의 재료 선택도 그렇다).
     ★5 를 재료로 넣어도 ★1 한 명과 똑같이 1명이다. 옛 눈금은 여기서 16배 부풀려 있었다.

  2. 키울 대상으로 쓰면 성급이 **훨씬 커진다.**
     비용에 출발 등급 배수 1.5^(5-출발) 가 걸려 있어서(`04-본디.md`),
     ★1 을 겹쳐 올린 ★2 와 뽑은 ★2 는 이후 비용이 다르다. 출발은 되돌릴 수 없다.
     그래서 뽑은 ★2 의 값은 「★1 + 13명」이 아니라 「★1 이었다면 더 들었을 명수」다.

한 잔상은 둘 중 하나로만 쓰인다. 값도 하나로 합칠 수 없다.

그릇값은 다시 두 가지로 읽힌다. 어느 쪽이 옳다고 정하지 않고 둘 다 낸다 —
둘이 **서로 다른 답을 주기 때문에** 하나만 내면 결론을 고르는 셈이 된다.

  (가) 상한 도달분만    본디가 상한에 못 미치면 0으로 친다.
                        엔드게임 목표(「그릇 사냥」)의 관점이다.
  (나) 실제 천장 평균    본디대로 min(본디, 상한) 까지 간다고 보고 기대값을 낸다.
                        평범한 한 판의 관점이다.
"""
import sys
sys.path.insert(0, 'tools')
from fusion_sim import shades_for, BONDI
from power import STAR_CAP_EARLY

# 뽑기 표 — `18-소환.md`
BASIC    = {1: .60, 2: .30, 3: .10}
DEEP     = {1: .25, 2: .25, 3: .22, 4: .15, 5: .08, 6: .05}
DEEP_OLD = {1: .25, 2: .25, 3: .22, 4: .15, 5: .08, 6: .04, 7: .01}   # ★7 을 빼기 전

DEEP_COST = 5          # 먼 울림 1개 = 울림 5개 (`18-소환.md` 의 환산 가정)

# fusion_sim 의 BONDI 는 ★1~5 뿐이다. 뽑기 표에 있는 ★6·★7 을 잇는다.
BOND = dict(BONDI)
BOND[6] = {6: .48, 7: .32, 8: .14, 9: .05, 10: .01}
BOND[7] = {7: .50, 8: .32, 9: .13, 10: .05}


def saved(r, ceil):
    """천장 ceil 까지 갈 때, ★r 로 시작하는 것이 ★1 로 시작하는 것보다 아끼는 겹치기 명수.

    자기 자신 1명을 더한다. 상한 위의 등급은 상한만큼만 쳐준다 —
    ★6 상한에서 ★7 은 ★6 보다 나을 것이 없다. 더 읽을 문장이 없기 때문이다.
    """
    return 1 + shades_for(1, ceil) - shades_for(min(r, ceil), ceil)

def p_reach(r, cap):
    if r >= cap: return 1.0
    return sum(v for k, v in BOND[r].items() if k >= cap)

def vessel_cap(r, cap):
    """(가) 상한까지 갈 수 있을 때만 값을 친다"""
    return p_reach(r, cap) * saved(r, cap)

def vessel_exp(r, cap):
    """(나) 본디대로 min(본디, 상한) 까지 간다고 보고 기대값"""
    return sum(p * saved(r, min(b, cap)) for b, p in BOND[r].items())

def ev(table, fn, cap):
    return sum(p * fn(r, cap) for r, p in table.items())

def old_ev(table):
    return sum(p * 2 ** (r - 1) for r, p in table.items())

def verdict(basic, deep):
    per = deep / DEEP_COST
    win = "일반" if basic > per else "깊은 부름"
    return per, win, max(basic, per) / min(basic, per)


if __name__ == "__main__":
    W = 76
    print("=" * W)
    print("소환 1회의 값 — 조각 기준 재산출")
    print("=" * W)
    print("옛 눈금 2^(r-1) 은 「같은 성 2명 = +1성」이던 시절의 환산이다.")
    print("조각 모형에는 값이 하나가 아니라 셋 있다 — 재료값 하나, 그릇값 둘.")

    for cap in (STAR_CAP_EARLY, 10):
        when = "지금" if cap == STAR_CAP_EARLY else "상한이 다 열린 뒤"
        print("\n" + "=" * W)
        print(f"선명도 상한 ★{cap}   ({when})")
        print("=" * W)
        print(f"{'등급':<5}{'재료값':>7}{'★'+str(cap)+'까지':>9}"
              f"{'아끼는 명수':>12}{'본디≥'+str(cap):>9}{'(가)':>9}{'(나)':>9}{'옛 눈금':>9}")
        print("-" * W)
        for r in sorted(DEEP_OLD):
            tag = "  ← 상한 위" if r > cap else ""
            print(f"★{r:<4}{1.0:>7.1f}{shades_for(min(r,cap),cap):>9.1f}{saved(r,cap):>12.1f}"
                  f"{p_reach(r,cap):>8.1%}{vessel_cap(r,cap):>9.1f}{vessel_exp(r,cap):>9.1f}"
                  f"{2**(r-1):>9}{tag}")

        print()
        print(f"{'':<14}{'부름':>9}{'깊은 부름':>11}{'회당 ÷'+str(DEEP_COST):>10}   판정")
        print("-" * W)
        rows = [("옛 눈금",          old_ev(BASIC),               old_ev(DEEP)),
                ("재료값",           1.0,                          1.0),
                ("그릇값 (가)",      ev(BASIC, vessel_cap, cap),   ev(DEEP, vessel_cap, cap)),
                ("그릇값 (나)",      ev(BASIC, vessel_exp, cap),   ev(DEEP, vessel_exp, cap))]
        for nm, b, d in rows:
            per, win, ratio = verdict(b, d)
            print(f"{nm:<14}{b:>9.2f}{d:>11.2f}{per:>10.2f}   {win} {ratio:.2f}배")

    print("\n" + "=" * W)
    print("읽기")
    print("=" * W)
    cap = STAR_CAP_EARLY
    bg, dg = ev(BASIC, vessel_cap, cap), ev(DEEP, vessel_cap, cap)
    be, de = ev(BASIC, vessel_exp, cap), ev(DEEP, vessel_exp, cap)
    print(f"""
  1. 재료를 사는 것이라면 **일반이 5배 유리하다.** 성급이 재료값에 안 붙으므로
     깊은 부름은 5배 값으로 똑같은 1명을 산다. 여기엔 이견의 여지가 없다.
     옛 눈금(일반 {old_ev(BASIC)/(old_ev(DEEP)/DEEP_COST):.2f}배)은 이 격차를 3배 넘게 줄여 보여 주고 있었다.

  2. 그릇을 사는 것이라면 **읽기에 따라 답이 갈린다.**

       (가) 상한까지 갈 사람만 센다   깊은 부름 {dg/DEEP_COST/bg:.2f}배 유리
       (나) 실제 천장까지 평균낸다     일반 {be/(de/DEEP_COST):.2f}배 유리

     깊은 부름이 효율로 이기는 읽기는 (가) 하나뿐이고, (가)가 바로
     **「그릇 사냥」의 정의**다. `18-소환.md` 의 역할 배분은 성립하지만,
     성립하는 폭이 {dg/DEEP_COST/bg:.2f}배로 좁다.

  3. 그러므로 깊은 부름의 값은 **효율표로 방어되지 않는다.**
     확실히 하려면 손댈 곳은 둘이다 — 먼 울림 = 울림 {DEEP_COST}개라는 환산을 낮추거나,
     고등급의 본디 분포를 지금보다 위로 더 기울인다.
     지금은 어느 쪽도 하지 않았다. 고르는 것은 설계 결정이라 여기서 정하지 않는다.
""")

    print("-" * W)
    print("★7 을 뺀 것의 실제 영향")
    print("-" * W)
    for cap in (STAR_CAP_EARLY, 10):
        o, n = ev(DEEP_OLD, vessel_cap, cap), ev(DEEP, vessel_cap, cap)
        oe, ne = ev(DEEP_OLD, vessel_exp, cap), ev(DEEP, vessel_exp, cap)
        d1 = "  동일" if abs(n-o) < 1e-9 else f"{(n-o)/o*100:+5.1f}%"
        d2 = "  동일" if abs(ne-oe) < 1e-9 else f"{(ne-oe)/oe*100:+5.1f}%"
        print(f"  상한 ★{cap:<3} 그릇값(가) {o:>7.2f} → {n:>7.2f} ({d1})   "
              f"(나) {oe:>7.2f} → {ne:>7.2f} ({d2})")
    print(f"""
  상한이 ★{STAR_CAP_EARLY} 인 동안 ★7 은 ★6 과 값이 **같다.** 둘 다 더 읽을 문장이 없다.
  그래서 ★7 을 빼도 그릇값은 한 자리도 안 움직인다.
  옛 눈금에서 6.03 → 5.71 로 떨어져 보였던 것은 **눈금의 착시**였다.
  상한이 ★10 으로 열리면 그때는 실제로 떨어진다. 되돌릴지는 그때 정한다.
""")

    print("-" * W)
    print("⚠ 본디 표가 단조롭지 않다")
    print("-" * W)
    print("  뽑은 등급별 본디 10 확률 —")
    print("    " + "   ".join(f"★{r} {BOND[r].get(10,0)*100:.1f}%" for r in range(1, 8)))
    print("""
  ★3 (0.5%) 이 ★5 (0.3%) 보다 높다. 「고급으로 시작하면 그릇이 커진다」는
  `18-소환.md` 의 주장이 **본디 10 한 칸에서는 뒤집혀 있다.**
  하한은 확실히 올라가므로(★5 는 최소 5) 문서의 논지 자체가 틀린 것은 아니지만,
  상한이 ★10 으로 열리는 시점에는 이 비단조가 그대로 「그릇 사냥」의 반례가 된다.
  본디 분포를 손볼 때 같이 본다.""")
