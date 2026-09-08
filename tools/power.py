# -*- coding: utf-8 -*-
"""전투력 산출 + 성장 세 축의 정의.

이 파일이 `docs/02-캐릭터-시스템.md` 4장의 코드판이다.
레벨 계수가 `gen_floors.py` 안에만 있으면 다른 도구가 제각각 다시 쓰게 되므로,
세 축을 전부 여기 모아 두고 나머지는 임포트만 한다.

    레벨    상한 = 도달 최고층      level_mult / level_cap
    선명도  상한 = 본디             star_pool  (스탯은 ★5에서 멈춘다)
    개화    -                       수치가 아니라 방향이라 여기 없다
"""
import json

# 잔존 배율을 7 → 4 로 낮추면서 재산출한 가중치 (역할 간 편차 0.7%).
# 7배 시절에는 HP가 공격력의 7배라 한 명 쓰러뜨리는 데 7대가 필요했고,
# 그 결과 전투력 수치가 실제 승패를 예측하지 못했다.
POWER = {"잔존":0.26, "의지":1.05, "자취":1.00, "공명":1.00}
HP_SCALE = 4

# ── 축 2. 선명도 ──────────────────────────────────────────────
# 등급별 스탯 풀 기준선 (잔존은 4배 스케일이므로 나눠서 환산).
# ★6~10 이 없는 것은 빠뜨린 것이 아니다. `docs/04-본디.md`:
#   "스탯은 ★5에서 멈춘다. ★6~10 은 배수가 아니라 특성이 열린다."
# 여기에 6~10 을 채워 넣으면 그 결정이 조용히 되돌아간다.
RARITY_POOL = {1:180, 2:235, 3:305, 4:400, 5:540}
STAT_STAR_CAP = 5

def star_pool(star):
    """선명도 star 의 스탯 풀. 6 이상은 5와 같다."""
    return RARITY_POOL[min(star, STAT_STAR_CAP)]

# 전투력 = 1.0240 x 스탯풀. data/characters.json 23명에서 잰 값이다
# (★1 1.0207 ~ ★5 1.0260, 전체 평균 1.0240). 지어낸 계수가 아니다.
POOL_TO_POWER = 1.0240

def star_power(star):
    """레벨 0 기준, 선명도 star 한 명의 전투력"""
    return POOL_TO_POWER * star_pool(star)

# ── 축 1. 레벨 ────────────────────────────────────────────────
# 레벨 1당 스탯 배율 증가. 이 계수 하나가 탑 난이도 곡선 전체를 지탱한다 —
# 빼고 돌리면 요구치가 평평해져서 본디 1도 3000층까지 버틴다(tools/cap_sim.py).
LV_STEP = 0.028

def level_cap(highest_floor):
    """레벨 상한 = 도달 최고층. 미리 쌓아 둘 수 없고, 나중에 얻은 잔상도 즉시 여기까지 온다."""
    return max(0, int(highest_floor))

def level_mult(level):
    return 1.0 + LV_STEP * level

# ── 각성 ──────────────────────────────────────────────────────
# 성급은 각성으로만 오른다. 성급 1 = 각성 5단계 = 기록 5조각.
AWAKEN_PER_STAR = 5

def frags_for_star(star):
    """선명도 star 에 이르기까지 읽어낸 기록 조각의 총량"""
    return AWAKEN_PER_STAR * star

# ── 초반 상한 ────────────────────────────────────────────────
# 규칙상 선명도는 본디까지 오르지만, **초반에 열어 두는 천장은 ★6 이다.**
# 본디가 8 인 잔상을 뽑아도 지금은 6까지만 읽힌다. 못 읽는 것이 아니라
# 아직 안 열린 것이다 — `13-확장구조.md` 가 말한 대로 병목이 재화가 아니라 글이다.
#
# ★6 하나만 열어도 「스탯이 아니라 특성」(`04-본디.md`)이 성립한다. 특성이 하나면
# 플레이어가 그 하나를 이해하고, 다섯이면 표를 읽는다.
STAR_CAP_EARLY = 6

# ── 진급석 ────────────────────────────────────────────────────
# `19-방치와-등반.md` 의 표. 성급 한 구간의 총량이고, 그 안의 각성 5조각에 균등하게 나뉜다.
#
# 이 표는 `04-본디.md` 의 R=1.35 곡선과 증가율이 다르다(약 x2.3). 한동안 어느 쪽으로
# 통일할지 열어 두었는데, 둘이 **서로 다른 것을 재고 있어서** 통일할 필요가 없었다.
#
#   겹치기(잔상)  출발이 어디였나를 잰다 — ★5 출발 84명 vs ★1 출발 512명 (608%)
#   진급석        어디까지 갔나를 잰다   — 출발과 무관하게 ★10 까지 약 3,200 으로 수렴
#
# 표가 가파른 덕분에 마지막 두 계단이 총액을 지배하고, 그래서 출발 등급이 지워진다.
# "흐렸던 사람일수록 겹칠 사람이 많이 든다. 하지만 또렷해지는 값은 누구에게나 같다."
STONE = {1:2, 2:5, 3:12, 4:28, 5:64, 6:150, 7:340, 8:800, 9:1800}

def stone_for_star(star):
    """성급 star → star+1 에 드는 진급석 총량"""
    return STONE[star]

def stone_per_frag(star):
    """그 구간의 조각 하나당 진급석 (구간 안에서는 균등)"""
    return STONE[star] / AWAKEN_PER_STAR

def power(st): return sum(st[k]*w for k,w in POWER.items())
def pool(st):  return st["잔존"]/HP_SCALE + st["의지"] + st["자취"] + st["공명"]

if __name__=="__main__":
    # 자체 점검 — 결정이 조용히 뒤집히는 것을 막는다
    assert max(RARITY_POOL) == STAT_STAR_CAP, "RARITY_POOL 에 ★6 이상이 들어왔다 (04-본디.md 위반)"
    assert star_pool(10) == star_pool(5),     "★10 스탯이 ★5 와 달라졌다"
    assert STAR_CAP_EARLY > STAT_STAR_CAP,    "초반 상한이 스탯 상한 이하면 특성이 하나도 안 열린다"

    d=json.load(open('data/characters.json',encoding='utf-8'))
    print(f"{'이름':<18}{'등급':>4}{'역할':>6}{'전투력':>8}{'실제풀':>8}{'기준':>7}{'편차':>8}")
    print("-"*62)
    bad=[]
    for c in sorted(d['characters'], key=lambda x:(-x['rarity'], x.get('floor') or 999)):
        st=c['stats']; p=power(st); pl=pool(st); ref=RARITY_POOL[c['rarity']]
        dev=(pl-ref)/ref*100
        flag=" ←" if abs(dev)>15 else ""
        if abs(dev)>15: bad.append((c['name'],c['rarity'],dev))
        print(f"{c['name']:<18}{c['rarity']:>4}{c['role']:>6}{p:>8.0f}{pl:>8.0f}{ref:>7}{dev:>7.0f}%{flag}")
    print()
    if bad:
        print(f"⚠ 기준 대비 ±15% 초과 {len(bad)}명 — 등급이 스탯을 설명하지 못한다")
        for n,r,dv in bad: print(f"    {n} (★{r}) {dv:+.0f}%")

    print("\n" + "="*62)
    print("성장 세 축")
    print("="*62)
    print(f"{'선명도':>6} {'스탯풀':>7} {'전투력':>8} {'누적 조각':>10}")
    for s in range(1, 11):
        mark = "  ← 여기서 스탯이 멈춘다" if s == STAT_STAR_CAP else ""
        if s > STAT_STAR_CAP:  mark = "  (특성만)"
        if s == STAR_CAP_EARLY: mark += "  ← 초반 천장"
        if s > STAR_CAP_EARLY:  mark += "  · 아직 안 열림"
        print(f"★{s:<5} {star_pool(s):>7} {star_power(s):>8.0f} {frags_for_star(s):>10}{mark}")
    print(f"\n진급석 (19-방치와-등반.md · 성급 한 구간의 총량):")
    run=0
    for n in range(1,10):
        run+=STONE[n]
        tag=" ← 초반은 여기까지" if n+1==STAR_CAP_EARLY else ""
        print(f"   {n}→{n+1}성 {STONE[n]:>5}   (조각당 {stone_per_frag(n):>6.1f})   누적 {run:>5}{tag}")
    print(f"   초반 천장 ★{STAR_CAP_EARLY} 까지는 전체의 "
          f"{sum(STONE[n] for n in range(1,STAR_CAP_EARLY))/sum(STONE.values())*100:.1f}% 만 쓴다.")

    print(f"\n레벨 배율 (상한 = 도달 최고층, 1 + {LV_STEP} x 레벨):")
    print("   " + "   ".join(f"{f}층 x{level_mult(level_cap(f)):.2f}" for f in (10,30,60,100,200,400)))
