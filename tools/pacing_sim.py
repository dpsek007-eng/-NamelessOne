# -*- coding: utf-8 -*-
"""1막 페이싱 — 30층까지 며칠 걸리는가."""
import json, random, sys, collections
sys.path.insert(0,'tools')

BASE={1: 184, 2: 240, 3: 312, 4: 410, 5: 554, 6: 720, 7: 936, 8: 1217, 9: 1582, 10: 2057}
STONE={1:2,2:5,3:12,4:28,5:64,6:150,7:340,8:800,9:1800}
BASIC={1:.60,2:.30,3:.10}
BONDI={1:{1:.35,2:.30,3:.15,4:.08,5:.05,6:.03,7:.02,8:.01,9:.007,10:.003},
       2:{2:.35,3:.28,4:.15,5:.09,6:.06,7:.035,8:.02,9:.01,10:.005},
       3:{3:.38,4:.28,5:.16,6:.09,7:.05,8:.025,9:.01,10:.005},
       4:{4:.42,5:.30,6:.15,7:.08,8:.035,9:.012,10:.003},
       5:{5:.45,6:.33,7:.15,8:.05,9:.017,10:.003},
       6:{6:.48,7:.32,8:.14,9:.05,10:.01},7:{7:.50,8:.32,9:.13,10:.05},
       8:{8:.55,9:.32,10:.13},9:{9:.70,10:.30},10:{10:1.0}}
PULL_COST=10          # 부름 1회 = 울림 10
AWAKEN_COST=[0,40,90,180,340,600]   # 각성 n단계까지 누적 유품
CAP_H=12; SESSIONS=2  # 하루 12시간 상한 × 2회 접속

def pick(d):
    x,a=random.random(),0.0
    for k,v in sorted(d.items()):
        a+=v
        if x<=a: return k
    return max(d)

class Shade:
    __slots__=("r","b","aw")
    def __init__(s,r,b): s.r,s.b,s.aw=r,b,0
    def power(s): return BASE[s.r]*(1+0.10*s.aw)

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
    for day in range(1, days+1):
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
            if sum(sorted((s.power() for s in inv),reverse=True)[:F[tf]["slot"]]) >= F[tf]["base_power"]*1.2:
                for k in res:
                    res[k]+= runs*tf*0.030*era_bonus(tf,k)
        # ── 소환 ──
        while res["울림"]>=PULL_COST and len(inv)<200:
            res["울림"]-=PULL_COST
            r=pick(BASIC); sh=Shade(r,pick(BONDI[r])); inv.append(sh)
        # ── 각성 ──
        for s in sorted(inv,key=lambda x:-x.power()):
            while s.aw<5 and res["유품"]>=AWAKEN_COST[s.aw+1]:
                res["유품"]-=AWAKEN_COST[s.aw+1]; s.aw+=1
        # ── 승급 ──
        # 실제 플레이어처럼: 앞으로 10층 안의 최대 편성 인원을 확보한 뒤에만 승급한다.
        # 승급은 2명 → 1명이라 머릿수가 순감하므로, 관문 인원을 깎아먹으면 안 된다.
        look=[F[f]["members_required"] for f in range(cleared+1, min(cleared+11,31)) if f in F]
        reserve=max(look) if look else 0
        moved=True
        while moved:
            moved=False
            for r in range(1,10):
                grp=[s for s in inv if s.r==r]
                promo=[s for s in grp if s.b>r]
                if len(inv)-1 < reserve: continue
                if len(grp)<2 or not promo or res["진급석"]<STONE[r]: continue
                base=max(promo,key=lambda x:x.b)
                mat=min([s for s in grp if s is not base], key=lambda x:x.b)
                res["진급석"]-=STONE[r]; inv.remove(mat); base.r+=1; base.aw=max(0,base.aw-1)
                moved=True
        # ── 등반 ──
        while cleared<30:
            nf=F[cleared+1]
            if nf["teams"]==0: cleared+=1; continue
            need=nf["members_required"]
            if len(inv)<need: break
            ps=sorted((s.power() for s in inv),reverse=True)[:need]
            best=min(r["power"] for r in nf["routes"])   # 최적 열쇠 경로 가정
            if sum(ps) >= nf["base_power"]*best: cleared+=1; log.append((day,cleared))
            else: break
        if cleared>=30:
            return day, len(inv), collections.Counter(s.r for s in inv), log
    return None, len(inv), collections.Counter(s.r for s in inv), log

print("="*66); print("1막 30층 도달까지 — 20회 시뮬레이션"); print("="*66)
outs=[run(seed=i) for i in range(20)]
done=[o[0] for o in outs if o[0]]
if done:
    done.sort()
    print(f"  중앙값 {done[len(done)//2]}일   최소 {min(done)}일   최대 {max(done)}일   ({len(done)}/20 도달)")
d,n,rar,log = run(seed=3)
print(f"\n대표 진행 (seed 3) — {d}일 소요, 최종 잔상 {n}명")
print("  등급 분포:", dict(sorted(rar.items(), reverse=True)))
print("\n  일자별 도달 층:")
byday=collections.defaultdict(list)
for day,f in log: byday[day].append(f)
for day in sorted(byday):
    fs=byday[day]; print(f"    {day:>2}일차  →  {fs[-1]:>2}층  ({len(fs)}개 층)")
