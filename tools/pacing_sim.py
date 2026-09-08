# -*- coding: utf-8 -*-
"""1막 페이싱 — 30층까지 며칠 걸리는가. (조각 모형)

이 파일이 옛 규칙에 가장 깊이 박혀 있었다. 고친 곳은 셋이다.

  1. 전투력   BASE 표에 ★6~10 이 있었다. 스탯은 ★5 에서 멈추므로
              `power.star_power` 를 부른다. 대신 레벨이 붙는다 —
              상한이 도달 최고층이라 클리어할 때마다 로스터 전원이 오른다.
  2. 성급     「n성 2명 + 진급석 → (n+1)성」 루프를 지웠다.
              성급은 각성 5조각을 채워야 오른다.
  3. 조각     조각 하나에 겹치기 여러 번이 든다(`fusion_sim.py`).
              그래서 잔상이 재화이자 병목이 된다.
"""
import json, math, random, sys, collections
sys.path.insert(0,'tools')
from power import (star_power, level_mult, level_cap,
                   AWAKEN_PER_STAR, STAR_CAP_EARLY, stone_per_frag)
from fusion_sim import overlays_per_frag, R

BASIC={1:.60,2:.30,3:.10}
BONDI={1:{1:.35,2:.30,3:.15,4:.08,5:.05,6:.03,7:.02,8:.01,9:.007,10:.003},
       2:{2:.35,3:.28,4:.15,5:.09,6:.06,7:.035,8:.02,9:.01,10:.005},
       3:{3:.38,4:.28,5:.16,6:.09,7:.05,8:.025,9:.01,10:.005},
       4:{4:.42,5:.30,6:.15,7:.08,8:.035,9:.012,10:.003},
       5:{5:.45,6:.33,7:.15,8:.05,9:.017,10:.003},
       6:{6:.48,7:.32,8:.14,9:.05,10:.01},7:{7:.50,8:.32,9:.13,10:.05},
       8:{8:.55,9:.32,10:.13},9:{9:.70,10:.30},10:{10:1.0}}
PULL_COST=10          # 부름 1회 = 울림 10
CAP_H=12; SESSIONS=2  # 하루 12시간 상한 × 2회 접속

# ── 각성 1조각의 비용 ─────────────────────────────────────────
# 두 재화가 다 든다. 유품은 `04-본디.md` 의 R=1.35 를 따르고(여기서 새 곡선을 만들면
# 04 와 갈라진다), 눈금만 옛 수치에 맞춘다. 진급석은 아래대로 `19` 표를 그대로 쓴다.
#
# ⚠ 그 눈금을 한 번 잘못 읽었다. 남겨 두는 이유는 같은 실수가 쉬워서다.
#
#   `21-페이싱.md` 의 「각성 누적 유품 40/90/180/340/600 = 1250」은
#   옛 규칙에서 **한 사람의 각성 전체**(0~5, 일생에 한 번) 값이다.
#   새 규칙에서 각성 단계는 5 가 아니라 45 다 — 성급 9구간 × 5조각.
#   이것을 성급 한 구간의 값으로 읽으면 사다리 총액이 1250 → 49,621 로 40배가 된다.
#
#   실제로 그렇게 돌려 봤다. 1막 중앙값이 18일 → 32일이 되고 25층에서 11일을 섰다.
#   그 11일 동안 막은 것은 **전부 유품**이었고, `19-방치와-등반.md` 가
#   「성급 상승 속도를 조절하는 주 레버」라고 못박은 진급석은 4,696 이 남아돌았다.
#   설계상 레버인 쪽이 놀고, 레버가 아닌 쪽이 문을 잠그고 있었다.
#
#   그래서 같은 1250 을 사다리 전체에 놓는다. 눈금을 옮긴 것이지 수를 지어낸 것이 아니다.
#
# 진급석은 `19-방치와-등반.md` 의 표를 그대로 쓴다 (`power.STONE`).
# 그 표는 성급마다 x2.3 으로 오르고 `04` 의 곡선은 x1.35 인데, 둘을 통일하지 않는다 —
# 재는 것이 다르기 때문이다(`fusion_sim.py` 6번 항목).
#
#   겹치기  출발이 어디였나를 잰다.  ★1 출발이 ★5 출발의 608%
#   진급석  어디까지 갔나를 잰다.    출발과 무관하게 ★10 까지 약 3,200 으로 수렴
LADDER = sum(AWAKEN_PER_STAR * (R ** (n - 1)) for n in range(1, 10))   # 사다리 45조각의 가중합
RELIC_PER_FRAG_1 = 1250 / LADDER        # 옛 각성 누적 40+90+180+340+600 을 사다리 전체에

def relic_cost(star): return RELIC_PER_FRAG_1 * (R ** (star - 1))
def stone_cost(star): return stone_per_frag(star)     # 19 표 ÷ 5 (구간 안에서는 균등)

def pick(d):
    x,a=random.random(),0.0
    for k,v in sorted(d.items()):
        a+=v
        if x<=a: return k
    return max(d)

class Shade:
    """r = 현재 선명도 · o = 뽑을 때의 선명도(출발) · b = 본디 · fr = 현재 성급 안의 조각 0~4"""
    __slots__=("r","o","b","fr")
    def __init__(s,r,b): s.r,s.o,s.b,s.fr=r,r,b,0
    def power(s,lv): return star_power(s.r)*level_mult(lv)

def era_bonus(f, res):
    if f<=20:  return 2.0 if res=="유품" else 0.6
    if f<=40:  return 2.0 if res=="진급석" else 0.6
    if f<=60:  return 2.0 if res=="기억조각" else 0.6
    return 2.0 if res=="울림" else 0.6

def run(days=40, seed=1, verbose=False):
    random.seed(seed)
    floors=json.load(open('data/floors.json',encoding='utf-8'))['floors']
    F={f["floor"]:f for f in floors}
    inv=[Shade(pick(BASIC), 0) for _ in range(3)]
    for s in inv: s.b=pick(BONDI[s.r])
    res=collections.Counter({"유품":0,"기억조각":0,"진급석":0,"울림":0})
    cleared=4; log=[]
    block=collections.Counter()   # 조각을 못 읽은 날의 사유
    stall=collections.Counter()   # 층 앞에서 멈춘 사유
    for day in range(1, days+1):
        lv=level_cap(cleared)          # 축 1. 레벨 상한 = 도달 최고층
        # ── 방치 산출 ──
        placed=min(len(inv), 8+cleared//5)
        h=CAP_H*SESSIONS
        res["유품"]   += placed*1.5*h
        res["기억조각"]+= placed*0.8*h
        res["진급석"] += placed*0.5*h
        res["울림"]   += placed*0.25*h
        # 순회: 클리어한 일반층 중 가장 높은 층
        tour=[f for f in range(5,cleared+1) if F[f]["teams"]==1]
        if tour:
            tf=max(tour); runs=20*h
            if sum(sorted((s.power(lv) for s in inv),reverse=True)[:F[tf]["slot"]]) >= F[tf]["base_power"]*1.2:
                for k in res:
                    res[k]+= runs*tf*0.030*era_bonus(tf,k)
        # ── 소환 ──
        while res["울림"]>=PULL_COST and len(inv)<200:
            res["울림"]-=PULL_COST
            r=pick(BASIC); sh=Shade(r,pick(BONDI[r])); inv.append(sh)
        # ── 각성 ── (승급 블록은 없다. 성급은 각성 5조각으로만 오른다)
        #
        # 실제 플레이어처럼: 앞으로 10층 안의 최대 편성 인원은 남겨 둔다.
        # 겹치기는 잔상을 소모하므로 머릿수가 순감하고, 관문 인원을 깎아먹으면
        # 다음 관문에서 막힌다(`21-페이싱.md`). 벼랑이 계단이 되었을 뿐
        # 함정 자체는 남아 있다.
        look=[F[f]["members_required"] for f in range(cleared+1, min(cleared+11,31)) if f in F]
        reserve=max(look) if look else 0

        moved=True
        while moved:
            moved=False
            # 본디가 남은 사람 중 가장 강한 쪽부터 읽어낸다
            # 본디가 남았어도 초반 천장(★6) 위로는 읽히지 않는다 — 아직 안 열린 문장이다
            for t in sorted((x for x in inv if x.r < min(x.b, STAR_CAP_EARLY)),
                            key=lambda x:(-x.b, -x.r)):
                fodder = math.ceil(overlays_per_frag(t.r, t.o))   # 이 조각에 드는 겹치기 수
                relic, stone = relic_cost(t.r), stone_cost(t.r)
                if len(inv)-1-fodder < reserve: block["인원(예비)"]+=1; continue
                if res["유품"]   < relic: block["유품"]+=1;   continue
                if res["진급석"] < stone: block["진급석"]+=1; continue
                # 재료는 본디가 낮은 쪽부터 — 더 읽어낼 것이 적은 사람이다
                pool=sorted((x for x in inv if x is not t), key=lambda x:(x.b, x.r))
                if len(pool) < fodder: block["재료"]+=1; continue
                for x in pool[:fodder]: inv.remove(x)
                res["유품"]-=relic; res["진급석"]-=stone
                t.fr+=1
                if t.fr>=AWAKEN_PER_STAR: t.fr=0; t.r+=1     # 확인 버튼 없이 저절로 오른다
                moved=True
                break
        # ── 등반 ──
        while cleared<30:
            nf=F[cleared+1]
            if nf["teams"]==0: cleared+=1; continue
            need=nf["members_required"]
            if len(inv)<need: stall["편성 인원"]+=1; break
            ps=sorted((s.power(lv) for s in inv),reverse=True)[:need]
            best=min(r["power"] for r in nf["routes"])   # 최적 열쇠 경로 가정
            if sum(ps) >= nf["base_power"]*best: cleared+=1; log.append((day,cleared))
            else: stall["전투력"]+=1; break
        if cleared>=30:
            return day, len(inv), collections.Counter(s.r for s in inv), log, block, stall
    return None, len(inv), collections.Counter(s.r for s in inv), log, block, stall

print("="*66); print("1막 30층 도달까지 — 20회 시뮬레이션"); print("="*66)
outs=[run(seed=i) for i in range(20)]
done=[o[0] for o in outs if o[0]]
if done:
    done.sort()
    print(f"  중앙값 {done[len(done)//2]}일   최소 {min(done)}일   최대 {max(done)}일   ({len(done)}/20 도달)")
d,n,rar,log,block,stall = run(seed=3)
print(f"\n대표 진행 (seed 3) — {d}일 소요, 최종 잔상 {n}명")
print("  등급 분포:", dict(sorted(rar.items(), reverse=True)))
print("\n  일자별 도달 층:")
byday=collections.defaultdict(list)
for day,f in log: byday[day].append(f)
for day in sorted(byday):
    fs=byday[day]; print(f"    {day:>2}일차  →  {fs[-1]:>2}층  ({len(fs)}개 층)")

# ── 무엇이 막았는가 ──────────────────────────────────────────
# 페이싱 수치보다 이쪽이 중요하다. 일수는 산출을 만지면 움직이지만,
# 무엇이 문을 잠그고 있는지는 구조가 결정한다.
print("\n  층 앞에서 멈춘 사유:")   # 왜 못 올랐는가
tot=sum(stall.values()) or 1
for k,v in stall.most_common():
    print(f"    {k:<10} {v:>3}회 ({v/tot:>4.0%})")
print("\n  조각을 못 읽은 사유:")   # 왜 안 세졌는가
tot=sum(block.values()) or 1
for k,v in block.most_common():
    print(f"    {k:<10} {v:>4}회 ({v/tot:>4.0%})")
print(f"""
  두 표를 이어 읽어야 한다. 층 앞에서 막은 것은 전투력이지만, 전투력이 안 오른
  이유는 조각을 못 읽어서고, 조각을 못 읽은 이유는 100% 머릿수다.
  **재화는 한 번도 막지 않았다.**

  잔상이 {n}명에서 더 늘지 않는 것이 이 곡선의 전부다.
  다음 관문이 15명을 요구하므로 예비 15명을 남겨야 하고, 소환으로 하루 1~2명이
  들어오면 그만큼만 겹칠 수 있다. 재화는 남는다 — 마지막 날 유품이 쌓여 있다.

  **1막의 병목은 재화가 아니라 머릿수다.** `21-페이싱.md` 이 2배 승급 시절에
  잡아낸 함정이 조각 모형에서도 그대로 남았다. 벼랑이 계단이 되었을 뿐이다.""")
