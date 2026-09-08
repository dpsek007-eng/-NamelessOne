# -*- coding: utf-8 -*-
"""본디에서 멈춘 잔상이 몇 층까지 쓰이는가 — 규칙을 바꾸기 전과 후.

이 파일은 원래 문제를 재기 위해 만들었다.
옛 규칙에서는 선명도만이 스탯을 올렸고 레벨이라는 축이 없었다. 그러면
본디 B 짜리의 전투력은 B성에 닿는 순간 **영구히 얼어붙는다.** 반면
`gen_floors.py` 의 요구치는 층을 따라 계속 오른다. 두 곡선이 갈라지는
지점이 그 사람의 마지막 층이고, 그 층은 계산으로 나온다.

지금은 규칙이 바뀌었다(`docs/02-캐릭터-시스템.md` 4).
    레벨   상한 = 도달 최고층  → 로스터 전원이 층을 따라 같이 오른다
    선명도 상한 = 본디         → 스탯은 ★5 에서 멈춘다
그래서 이 파일은 두 규칙을 다 돌려서 **무엇이 고쳐졌는지**를 같이 찍는다.
고친 뒤에도 표를 남겨 두는 이유는, 레벨 축을 나중에 누가 지우면
아래 A 표가 다시 나타나기 때문이다.

승패 판정은 `docs/02-캐릭터-시스템.md` 의 표를 그대로 쓴다.
    전투력/요구치  0.8 미만 = 0% · 0.8~1.0 = 18% · 1.0 이상 = 84%
그래서 0.8 이 이 사람의 마지막 층이다.
"""
import json, sys, io, contextlib
sys.path.insert(0, 'tools')
from power import (RARITY_POOL, POOL_TO_POWER, STAT_STAR_CAP,
                   star_power, level_mult, level_cap)

# gen_floors 는 임포트만 해도 표를 찍고 data/floors.json 을 다시 쓴다.
# 결과는 결정적이라 덮어써도 같은 파일이지만, 출력은 삼킨다.
with contextlib.redirect_stdout(io.StringIO()):
    import gen_floors as G      # roster_at()/chars/PULL_AVG 를 그대로 빌린다

FLOORS = json.load(open('data/floors.json', encoding='utf-8'))['floors']
PASS = 0.8                      # 이 밑은 승률 0%

# ── 옛 규칙의 스탯 풀 ────────────────────────────────────────
# `power.py` 에는 1~5 밖에 없고, 그것이 지금의 결정이다.
# 옛 규칙을 재현하려면 6~10 이 필요한데 그 값은 코드에 없다.
# 있는 네 구간의 비 1.3056 / 1.2979 / 1.3115 / 1.3500 의 기하평균으로 늘린다.
#   ★ 이건 가정이다. A 표에만 쓰고 어디에도 저장하지 않는다.
_R = (RARITY_POOL[5] / RARITY_POOL[1]) ** 0.25
OLD_POOL = dict(RARITY_POOL)
for n in range(6, 11):
    OLD_POOL[n] = round(OLD_POOL[n - 1] * _R)

def old_power(star):
    """옛 규칙: 성급이 오르는 만큼 스탯이 오르고, 레벨은 없다"""
    return POOL_TO_POWER * OLD_POOL[star]

def new_power(star, floor):
    """지금 규칙: 스탯은 ★5 에서 멈추고, 레벨이 층을 따라온다"""
    return star_power(star) * level_mult(level_cap(floor))

def cheapest(fl, bondi):
    """그 층에서 이 사람들이 실제로 탈 수 있는 가장 싼 경로의 배율.

    약체 경로는 `평균 선명도 3 이하`가 조건이므로 본디 4 이상은 못 탄다 —
    자기가 또렷해졌다는 이유로 싼 길이 닫힌다. 이것도 지금 설계의 결과다.
    """
    best = 1.0
    for r in fl['routes']:
        if any(c['type'] == '약체' for c in r['conditions']) and bondi > 3:
            continue
        best = min(best, r['power'])
    return best

BS = [1, 2, 3, 5, 10]

# gen_floors 는 60층까지만 만든다. 탑은 거기서 끝나지 않으므로
# 같은 규칙(보유 = 전승 + PULL_AVG x 0.7f, 요구 = 상위 15명 합 x 0.78,
# 관문 3팀 15명)을 그대로 위로 늘린다.
def gate_req(f):
    return round(sum(G.roster_at(f)[:15]) * 0.78)

def table(title, pw, note, floors=(60,80,100,140,200,300,500,1000,2000),
          need=15, key=0.60):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)
    print(note)
    print(f"\n{'층':>5} {'요구':>11} " + "".join(f"{'본디'+str(b):>11}" for b in BS))
    print("-" * 78)
    dead = {b: None for b in BS}
    for f in floors:
        req = gate_req(f)
        cells = []
        for b in BS:
            ratio = need * pw(b, f) / (req * key)
            if ratio < PASS and dead[b] is None:
                dead[b] = f
            cells.append(f"{ratio:>9.2f}x" + ("o" if ratio >= PASS else "X"))
        print(f"{f:>5} {req:>11} " + "".join(cells))
    print()
    for b in BS:
        print(f"  본디 {b:>2} : "
              + (f"{dead[b]}층에서 가장 싼 열쇠마저 0% 가 된다" if dead[b]
                 else f"{floors[-1]}층까지 버틴다"))
    return dead

dead_old = table(
    "A. 옛 규칙 — 선명도만 오르고 레벨이 없다",
    lambda b, f: old_power(b),
    "본디에 닿는 순간 전투력이 얼어붙는다. 요구치만 계속 오른다.\n"
    "관문 3팀 15명, 가장 싼 열쇠(0.60)를 탄다고 후하게 쳐 준 결과다.")

dead_new = table(
    "B. 지금 규칙 — 스탯은 ★5 정지, 레벨 상한 = 도달 최고층",
    new_power,
    "레벨 배수가 요구치의 분자·분모에 똑같이 들어가 약분된다.\n"
    "그래서 비가 층에 무관하게 평평하다 — 곡선이 갈라지지 않는다.")

print("\n" + "=" * 78)
print("무엇이 달라졌나")
print("=" * 78)
print(f"{'본디':>5} {'옛 규칙':>16} {'지금 규칙':>18}")
print("-" * 78)
for b in BS:
    o = f"{dead_old[b]}층에서 사망" if dead_old[b] else "버틴다"
    n = f"{dead_new[b]}층에서 사망" if dead_new[b] else "끝까지 쓰인다"
    print(f"★{b:<4} {o:>16} {n:>18}")
print("""
레벨을 모두에게 주면 본디가 낮은 잔상도 층을 따라 올라간다.
성급 차이는 배수로 남지만 그 배수가 층에 따라 벌어지지 않으므로,
못 쓰게 되는 시점이 사라진다. `docs/02` 의 "성장의 끝이 정보의 끝"이
계산에서도 성립한다 — 끝나는 것은 성장이지 쓸모가 아니다.""")

# ── 정면 돌파는 여전히 성급을 요구한다 ─────────────────────────
print("\n" + "=" * 78)
print("경로별 — 누가 어느 문으로 들어가는가 (100층 관문, 층 무관하게 같은 값)")
print("=" * 78)
f = 100
req = gate_req(f)
print(f"{'배율':>6} {'경로':>10} " + "".join(f"{'본디'+str(b):>10}" for b in BS))
print("-" * 78)
for mult, nm in ((1.00, "정면 돌파"), (0.70, "열쇠(비싼)"), (0.60, "열쇠(중간)"), (0.45, "열쇠(싼)")):
    cells = [f"{15*new_power(b,f)/(req*mult):>8.2f}x" + ("o" if 15*new_power(b,f)/(req*mult) >= PASS else "X")
             for b in BS]
    print(f"{mult:>6.2f} {nm:>10} " + "".join(cells))
print("""
정면 돌파만 성급을 가른다. 열쇠는 본디 1 도 연다.
이것이 `docs/06` 의 "돌파는 항상 있되 비효율적이어야 한다"와 맞물린다 —
약한 잔상이 못 쓰이는 것이 아니라, 문을 골라서 들어간다.""")

# ── 약체 경로 단독 점검 ────────────────────────────────────────
# `평균 선명도 3 이하`가 조건이므로 이 길은 본디 1~3 만 탈 수 있다.
# 그런데 그 사람들이 배율 0.60~0.70 을 낼 수 있는가?
print("\n" + "=" * 78)
print("약체 경로 — 약한 사람을 위한 길인데, 약한 사람이 탈 수 있는가")
print("=" * 78)
print(f"{'층':>4} {'인원':>4} {'요구':>8} {'배율':>5}  {'본디1':>9} {'본디2':>9} {'본디3':>9}")
print("-" * 78)
shut = []
for fl in FLOORS:
    w = [r for r in fl['routes'] if any(c['type'] == '약체' for c in r['conditions'])]
    if not w:
        continue
    m = w[0]['power']; need = fl['members_required']; req = fl['base_power']
    rs = [need * new_power(b, fl['floor']) / (req * m) for b in (1, 2, 3)]
    if max(rs) < PASS:
        shut.append(fl['floor'])
    print(f"{fl['floor']:>4} {need:>4} {req:>8} {m:>5.2f}  "
          + " ".join(f"{r:>8.2f}x" + ("o" if r >= PASS else "X") for r in rs))
if shut:
    print(f"""
⚠ {shut} 층: 본디 1~3 만으로는 이 길의 요구치를 못 채운다.
   약체 조건이 본디 4 이상을 막으므로, **탈 수 있는 사람은 못 타고
   탈 힘이 있는 사람은 자격이 없다.** 이 문은 아무도 못 연다.
   배율을 낮추거나 조건을 「평균 선명도 4 이하」로 여는 것 중 하나가 필요하다.""")
else:
    print("\n약체 경로는 본디 1~3 만으로 전부 열린다.")
