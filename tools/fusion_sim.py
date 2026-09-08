# -*- coding: utf-8 -*-
"""겹치기 → 각성 조각 → 성급. 조각 모형의 비용 산출.

옛 모형은 「n성 2명 → (n+1)성 1명」이었다. 그 규칙에서는 ★1 하나를 10성까지
올리는 데 드는 잔상이 2^9 = 512명으로 **자동으로** 나왔다. 규칙이 바뀌었으니
그 수는 더 이상 저절로 나오지 않는다(`docs/08-승급.md`).

두 문서가 각각 다른 것을 못 박아 두었고, 둘 다 지켜야 한다.

  `docs/02` 4-2  각성 1단계 = 기록 1조각.  성급 1 = 5단계.  10성 = 50조각
  `docs/04`      비용은 지수로 오른다.      ★1 출발이 ★5 출발의 608%

조각 수를 지수로 늘리면 02 가 깨지고, 조각 수를 고정하면 04 가 깨진다.
둘을 같이 지키는 읽기는 하나뿐이다.

  > **조각의 수는 고정이고, 조각 하나를 읽어내는 데 드는 겹침이 는다.**

뒤로 갈수록 남은 문장이 흐릿해서 더 여러 번 겹쳐야 읽힌다.
서사와 수식이 같은 말을 한다.

기준선은 `docs/08` 의 「★1 출발 10성 = 512명분」을 유지하는 값으로 잡는다.
"""
import random, statistics, sys
sys.path.insert(0, 'tools')
from power import AWAKEN_PER_STAR, STAR_CAP_EARLY, STONE

# `bondi_sim.py` 의 비용 곡선을 그대로 가져온다. 여기서 다시 정하지 않는다.
R, BASE, ORIGIN_PENALTY = 1.35, 1.0, 1.5
def step_cost(n, origin):   return BASE * (R ** n) * (ORIGIN_PENALTY ** (5 - origin))
def total_cost(origin, to): return sum(step_cost(n, origin) for n in range(origin, to))

ANCHOR_ORIGIN, ANCHOR_SHADES, TOP = 1, 512, 10
SCALE = ANCHOR_SHADES / total_cost(ANCHOR_ORIGIN, TOP)   # 비용단위 → 잔상 명수

def overlays_per_frag(n, origin):
    """성급 n→n+1 구간에서 조각 하나를 읽는 데 드는 겹치기 수"""
    return step_cost(n, origin) * SCALE / AWAKEN_PER_STAR

def shades_for(origin, to=TOP):
    return total_cost(origin, to) * SCALE

PULL = {5:.02, 4:.08, 3:.20, 2:.30, 1:.40}
BONDI = {5:{5:.45,6:.33,7:.15,8:.05,9:.017,10:.003},
         4:{4:.42,5:.30,6:.15,7:.08,8:.035,9:.012,10:.003},
         3:{3:.38,4:.28,5:.16,6:.09,7:.05,8:.025,9:.010,10:.005},
         2:{2:.35,3:.28,4:.15,5:.09,6:.06,7:.035,8:.020,9:.010,10:.005},
         1:{1:.35,2:.30,3:.15,4:.08,5:.05,6:.03,7:.02,8:.010,9:.007,10:.003}}

# 본디가 초반 천장 이상일 확률 — 그릇이 병목인지 아닌지를 가른다
p6 = sum(p * sum(v for k, v in BONDI[r].items() if k >= STAR_CAP_EARLY)
         for r, p in PULL.items())

def pick(d):
    x, a = random.random(), 0.0
    for k, v in sorted(d.items()):
        a += v
        if x <= a: return k
    return max(d)


if __name__ == "__main__":
    # 보고서는 직접 돌릴 때만 찍는다.
    # `pacing_sim.py` 가 이 파일에서 곡선을 가져다 쓰므로,
    # 여기서 모듈 수준으로 출력하면 남의 보고서 위에 이 보고서가 덮인다.
    print("=" * 74)
    print("규칙: 겹치기 → 각성 조각 → (5조각마다) 성급 +1")
    print("=" * 74)
    print(f"조각 수는 고정 — 10성 = {AWAKEN_PER_STAR * TOP}조각. 드는 것은 조각당 겹치기 수다.")
    print(f"기준선: ★{ANCHOR_ORIGIN} 출발 10성 = {ANCHOR_SHADES}명  (04-본디.md 곡선 위에서 눈금만 맞춘 값)")

    print("\n" + "=" * 74)
    print("1. 성급별 — 조각 하나에 몇 명이 드는가")
    print("=" * 74)
    print(f"{'성급':>6} {'조각':>5} " + "".join(f"{'★'+str(o)+' 출발':>13}" for o in (1, 3, 5)))
    print("-" * 74)
    for n in range(1, TOP):
        cells = []
        for o in (1, 3, 5):
            if o > n: cells.append(f"{'-':>13}")
            else:     cells.append(f"{overlays_per_frag(n,o):>7.1f}명/조각")
        print(f"{n}→{n+1:<4} {AWAKEN_PER_STAR:>5} " + "".join(cells))

    print("\n" + "=" * 74)
    print("2. 성급 하나를 올리는 데 머릿수가 얼마나 주는가  (21-페이싱.md)")
    print("=" * 74)
    print("옛 모형과 비교한다. 옛 모형은 「2명 → 1명」이 반복되므로 ★1 환산으로")
    print("성급 n→n+1 에 2^n 명이 들었다. 총합은 둘 다 512명으로 같게 맞춰 두었다.\n")
    print(f"{'성급':>6} {'옛(2배)':>10} {'지금(조각)':>12} {'차이':>10}")
    print("-" * 74)
    old_tot = new_tot = 0
    for n in range(1, TOP):
        old = 2 ** (n - 1)                       # ★1 환산: n성 하나 = 2^(n-1) 명
        new = overlays_per_frag(n, 1) * AWAKEN_PER_STAR
        old_tot += old; new_tot += new
        print(f"{n}→{n+1:<4} {old:>10} {new:>12.0f} {new-old:>+10.0f}")
    print("-" * 74)
    print(f"{'합계':>6} {old_tot:>10} {new_tot:>12.0f}")
    print(f"""
옛 모형은 마지막 한 번에 {2**(TOP-2)}명이 사라졌다. 지금은 {overlays_per_frag(TOP-1,1)*AWAKEN_PER_STAR:.0f}명이고,
그마저 조각 5개로 쪼개져 {overlays_per_frag(TOP-1,1):.0f}명씩 나간다.

**머릿수 급락이 완화된다.** `21-페이싱.md` 이 잡은 「승급하면 관문 인원이
모자란다」 는 함정은 남지만, 벼랑이 계단이 되었다. 경고 UI 는 계속 필요하다 —
다만 표시할 수는 「1명 줄어듭니다」가 아니라 「이 조각에 {overlays_per_frag(TOP-1,1):.0f}명이 듭니다」다.""")

    print("\n" + "=" * 74)
    print("3. 출발 등급별 총 소요 — 04-본디.md 곡선이 지켜지는가")
    print("=" * 74)
    ref = shades_for(5)
    print(f"{'출발':>5} {'조각':>6} {'잔상 명수':>11} {'★5 대비':>9} {'04 문서값':>10}")
    print("-" * 74)
    DOC = {5:100, 4:161, 3:254, 2:395, 1:608}     # docs/04-본디.md 의 표
    okall = True
    for o in (5, 4, 3, 2, 1):
        s = shades_for(o); pct = s / ref * 100
        ok = abs(pct - DOC[o]) < 1.0
        okall &= ok
        print(f"★{o:<4} {AWAKEN_PER_STAR*(TOP-o):>6} {s:>11.0f} {pct:>8.0f}% {DOC[o]:>9}% {'' if ok else '  ← 불일치'}")
    print("\n" + ("곡선 일치 — 단위만 승급 단계에서 겹치기 명수로 바뀌었다."
                  if okall else "⚠ 곡선이 어긋났다. SCALE 또는 step_cost 를 확인할 것."))
    print(f"""
옛 모형에서는 출발이 무엇이든 512명이었다(2배 겹침의 산술적 결과).
지금은 출발 등급이 명수에도 반영된다 — ★5 출발이 {ref:.0f}명, ★1 출발이 {shades_for(1):.0f}명.
**이것은 부작용이 아니라 04 를 명수 축까지 끌고 온 결과다.**
싫다면 조각 비용에서 ORIGIN_PENALTY 를 빼고 그 배수를 진급석에만 남기면 된다
(아래 6번 항목).""")

    print("\n" + "=" * 74)
    print(f"4. 초반 천장 ★{STAR_CAP_EARLY} — 지금 실제로 도달 가능한 곳")
    print("=" * 74)
    print(f"""규칙상 선명도는 본디까지 오르지만, 초반에 열어 두는 천장은 ★{STAR_CAP_EARLY} 다.
본디 8 을 뽑아도 지금은 {STAR_CAP_EARLY}까지만 읽힌다. 아래 표가 실제 초반 비용이고,
★10 열은 천장이 열린 먼 훗날의 값이다.""")
    print()
    print(f"{'출발':>5} {'조각':>6} {'잔상':>8} {'진급석':>8}   │ {'조각':>6} {'잔상':>8} {'진급석':>8}")
    print(f"{'':>5} {'──── ★'+str(STAR_CAP_EARLY)+' 까지 ────':^24}   │ {'──── ★10 까지 ────':^26}")
    print("-" * 74)
    for o in (5, 4, 3, 2, 1):
        e_fr = AWAKEN_PER_STAR * (STAR_CAP_EARLY - o)
        e_st = sum(STONE[n] for n in range(o, STAR_CAP_EARLY))
        t_st = sum(STONE[n] for n in range(o, TOP))
        print(f"★{o:<4} {e_fr:>6} {shades_for(o, STAR_CAP_EARLY):>8.0f} {e_st:>8}   │ "
              f"{AWAKEN_PER_STAR*(TOP-o):>6} {shades_for(o):>8.0f} {t_st:>8}")
    print(f"""
그릇도 같이 헐거워진다. 본디 10 은 뽑기 250회당 1명이지만,
**본디 {STAR_CAP_EARLY} 이상은 {1/p6:.0f}회당 1명**이다({p6*100:.1f}%). 초반에는 그릇이 병목이 아니다.
막는 것은 겹칠 사람 수다 — ★1 을 ★{STAR_CAP_EARLY}까지 읽으려면 {shades_for(1, STAR_CAP_EARLY):.0f}명이 든다.
`21-페이싱.md` 가 1막에서 잰 것이 정확히 이것이다.""")

    print("\n" + "=" * 74)
    print("5. 시뮬레이션 — 첫 ★10 까지 몇 번 뽑아야 하는가 (천장이 열린 뒤)")
    print("=" * 74)
    ev_note = "본디 10 은 뽑기 267회당 1명이다. 재료보다 그릇이 먼저 막힌다."

    NEED = {o: shades_for(o) for o in range(1, 6)}   # 출발 성급별 필요 명수

    def run(cap=400_000):
        """뽑으면서, 본디 10 이 나오고 그를 먹일 잔상이 충분해지는 시점을 잡는다"""
        have = []                       # (출발성급, 본디)
        for p in range(1, cap + 1):
            r = pick(PULL); have.append((r, pick(BONDI[r])))
            if p % 25: continue
            # 가장 싸게 10성이 되는 본디 10 하나를 고른다 (출발 성급이 높을수록 싸다)
            cands = [o for o, b in have if b >= TOP]
            if cands and (p - 1) >= NEED[max(cands)]:
                return p, max(cands)
        return None, None

    random.seed(20260901)
    outs = [run() for _ in range(400)]
    ok = [p for p, _ in outs if p]
    org = [o for _, o in outs if o]
    print(f"400회 중 도달 {len(ok)}회")
    print(f"   중앙값 {statistics.median(ok):>7.0f}회")
    print(f"   평균   {statistics.mean(ok):>7.0f}회")
    print(f"   상위25%{sorted(ok)[len(ok)//4]:>7.0f}회 (운 좋은 경우)")
    print(f"   하위25%{sorted(ok)[3*len(ok)//4]:>7.0f}회 (운 나쁜 경우)")
    print("\n   첫 10성이 된 사람의 출발 성급:")
    for o in (5, 4, 3, 2, 1):
        c = org.count(o)
        print(f"     ★{o} 출발 {c:>4}회 ({c/len(org)*100:>5.1f}%)  — 필요 {NEED[o]:>4.0f}명")
    print(f"\n   {ev_note}")

    print("\n" + "=" * 74)
    print("6. 진급석 — 19-방치와-등반.md 의 표를 쓴다")
    print("=" * 74)
    print(f"{'성급':>6} {'진급석':>8} {'전 단계 대비':>12} {'누적':>8} {'출발★1 잔상':>12}")
    print("-" * 74)
    prev = run_st = None; run_st = 0
    for n in range(1, TOP):
        ratio = STONE[n] / prev if prev else None
        prev = STONE[n]; run_st += STONE[n]
        rs = f"x{ratio:.2f}" if ratio else "-"
        tag = "  ← 초반 천장" if n + 1 == STAR_CAP_EARLY else ""
        print(f"{n}→{n+1:<4} {STONE[n]:>8} {rs:>12} {run_st:>8} "
              f"{overlays_per_frag(n,1)*AWAKEN_PER_STAR:>11.0f}명{tag}")
    print(f"""
이 표는 성급마다 약 x2.3 으로 오른다. `04-본디.md` 의 비용 곡선은 x{R} 다.
한동안 어느 쪽으로 통일할지 열어 두었는데, **통일할 필요가 없었다.**
둘이 서로 다른 것을 재고 있다.

   겹치기(잔상)   출발이 어디였나   ★5 출발 {shades_for(5):.0f}명  vs  ★1 출발 {shades_for(1):.0f}명 ({shades_for(1)/shades_for(5)*100:.0f}%)
   진급석         어디까지 갔나     ★5 출발 {sum(STONE[n] for n in range(5,TOP)):,}  vs  ★1 출발 {sum(STONE[n] for n in range(1,TOP)):,} ({sum(STONE[n] for n in range(1,TOP))/sum(STONE[n] for n in range(5,TOP))*100:.0f}%)

표가 가파른 덕분에 마지막 두 계단이 총액을 지배하고, 그래서 **출발 등급이 지워진다.**
흐렸던 사람일수록 겹칠 사람이 많이 든다. 하지만 또렷해지는 값은 누구에게나 같다.

초반 천장 ★{STAR_CAP_EARLY} 까지는 전체 진급석의 {sum(STONE[n] for n in range(1,STAR_CAP_EARLY))/sum(STONE.values())*100:.1f}% 만 쓴다 —
천장을 여는 것이 곧 비용을 여는 것이다.""")
