# -*- coding: utf-8 -*-
"""초점 곡선 — 선명도를 그림으로 옮긴다.

「선명도」는 지금까지 숫자였다. 문자 그대로 읽으면 초점이다.
이 도구는 성급/각성 진행도를 초점 0~1 로 바꾸고,
그 초점이 초상화에서 어떤 값으로 나타나는지를 낸다.

★6 에서 초점이 「누구 얼굴로」 맞는지는 여기서 정하지 않는다.
그것은 trait_odds.p_own 이 이미 재고 있다 — 여기서는 가져다 쓴다.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trait_odds import p_own, p_reach, CAP

# --- 정한 수 (계산이 아니다. 아트 파라미터라 손으로 정한다) ---
BLUR_MAX      = 6.0    # ★1 초상의 흐림 반경 (px, 512 기준)
FEATURE_FLOOR = 0.25   # ★1 에서도 이목구비는 이만큼 보인다. 0 으로 두지 않는다
GHOST_MAX     = 0.40   # ★1 이중상(잔상)의 진하기
GHOST_OFF_MAX = 3.0    # ★1 이중상의 어긋난 거리 (px)
GHOST_RESID   = 0.15   # ★6 을 「빌린」으로 찍었을 때 끝까지 남는 이중상

STEPS = (CAP - 1) * 5          # ★1 → 상한까지의 각성 단계 수


def progress(star, awaken=0):
    """성급 star, 그 안에서 각성 awaken 단계일 때의 누적 단계"""
    return (star - 1) * 5 + awaken


def focus(star, awaken=0):
    """0.0 = 초점 없음, 1.0 = 완전히 맞음"""
    return min(1.0, max(0.0, progress(star, awaken) / STEPS))


def blur(f):     return round(BLUR_MAX * (1.0 - f), 2)
def feature(f):  return round(FEATURE_FLOOR + (1.0 - FEATURE_FLOOR) * (f ** 0.5), 3)
def ghost(f):    return round(GHOST_MAX * (1.0 - f), 3)
def ghost_off(f):return round(GHOST_OFF_MAX * (1.0 - f), 2)


def ghost_end(r, cap=CAP):
    """★6 에 도착했을 때 이중상이 남아 있을 확률 = 고유가 아닐 확률.
    지어낸 수가 아니라 trait_odds 의 p_own 을 뒤집은 것이다."""
    return 1.0 - p_own(r, cap)


def pad(t, w):
    """한글은 두 칸을 먹으므로 문자 수가 아니라 폭으로 맞춘다"""
    return t + " " * max(0, w - sum(2 if ord(c) > 0x1100 else 1 for c in t))


def _selfcheck():
    assert 0.0 < FEATURE_FLOOR < 1.0
    assert 0.0 < GHOST_RESID < GHOST_MAX
    assert focus(1, 0) == 0.0, "★1 은 초점 0 에서 시작한다"
    assert focus(CAP, 0) == 1.0, "상한에서 초점이 1 이 된다"
    # 단조성 — 되돌아가는 구간이 있으면 안 된다
    prev = -1.0
    for s in range(1, CAP + 1):
        for a in range(5):
            f = focus(s, a)
            assert f >= prev, (s, a)
            prev = f
    assert blur(1.0) == 0.0 and feature(1.0) == 1.0 and ghost(1.0) == 0.0
    assert feature(0.0) == FEATURE_FLOOR, "★1 에도 얼굴은 있다"
    # 이중상 잔류 확률은 등급이 낮을수록 높아야 한다
    g = [ghost_end(r) for r in range(1, CAP + 1)]
    assert all(g[i] >= g[i + 1] - 1e-9 for i in range(len(g) - 1)), g
    assert abs(g[-1]) < 1e-9, "상한 태생은 이중상이 남지 않는다"


_selfcheck()

if __name__ == "__main__":
    print(f"초점 곡선 — 선명도 ★1~★{CAP} · 각성 {STEPS}단계\n")

    print("1. 성급별 초점과 초상 파라미터")
    print("   성급  각성  초점    흐림    이목구비  이중상  어긋남")
    for s in range(1, CAP + 1):
        f = focus(s, 0)
        print(f"   ★{s}    {progress(s):>2}   {f:.2f}   {blur(f):>4.2f}px   "
              f"{feature(f)*100:>5.1f}%    {ghost(f):.2f}   {ghost_off(f):.2f}px")

    print("\n2. 뽑자마자 보이는 초점 — 「볼 것이 없다」가 되지 않는가")
    for s in range(1, CAP + 1):
        f = focus(s, 0)
        bar = "#" * int(round(feature(f) * 20))
        print(f"   태생 ★{s}  초점 {f:.2f}  이목구비 {feature(f)*100:>5.1f}%  {bar}")
    print(f"   → 전승(★5)은 뽑는 순간 초점 {focus(5):.2f}. 손그림 초상이 거의 그대로 보인다")
    print(f"   → ★1 도 이목구비 {feature(0.0)*100:.0f}% 는 그려져 있다. 얼굴이 없는 게 아니라 안 맞는 것이다")

    print("\n3. ★6 에 도착했을 때 — 초점은 맞는데 누구 얼굴인가")
    print("   태생  ★6도달   고유(제 얼굴)  이중상 잔류   좋은 ★6")
    for r in range(1, CAP + 1):
        print(f"   ★{r}    {p_reach(r)*100:>5.1f}%    {p_own(r)*100:>5.1f}%       "
              f"{ghost_end(r)*100:>5.1f}%      {p_reach(r)*p_own(r)*100:>5.2f}%")
    print(f"   빌린 쪽 이중상은 0 으로 안 간다. {GHOST_RESID:.2f} 가 끝까지 남는다")

    print("   (도달×고유 확률은 tools/trait_odds.py 3번과 같은 수다)")

    print("\n4. 남는 문제")
    print("   - 흐림/이목구비/이중상 5개 값은 손으로 정한 아트 파라미터다. 계산이 아니다")
    print("   - 초점은 초상에만 건다. 48x64 필드 스프라이트는 실루엣+상징물로 계속 식별한다")
    print(f"   - 상한이 ★8 로 열리면 STEPS 가 {STEPS}→35 로 늘어 곡선이 통째로 늘어진다")
