# -*- coding: utf-8 -*-
"""부름/깊은 부름 검증 — 등급 분포, 본디, 승급 경제 영향."""
import random, statistics, collections

BASIC = {1:.60, 2:.30, 3:.10}
DEEP  = {1:.20, 2:.25, 3:.28, 4:.20, 5:.07}   # 1~5성 한정. 6성 이상은 승급으로만
BONDI = {
 1:{1:.35,2:.30,3:.15,4:.08,5:.05,6:.03,7:.02,8:.010,9:.007,10:.003},
 2:{2:.35,3:.28,4:.15,5:.09,6:.06,7:.035,8:.020,9:.010,10:.005},
 3:{3:.38,4:.28,5:.16,6:.09,7:.05,8:.025,9:.010,10:.005},
 4:{4:.42,5:.30,6:.15,7:.08,8:.035,9:.012,10:.003},
 5:{5:.45,6:.33,7:.15,8:.05,9:.017,10:.003},
 6:{6:.48,7:.32,8:.14,9:.05,10:.010},
 7:{7:.50,8:.32,9:.13,10:.050},
}
def pick(d):
    x,a=random.random(),0.0
    for k,v in sorted(d.items()):
        a+=v
        if x<=a: return k
    return max(d)
def eqv(r): return 2**(r-1)

print("="*64); print("1. 1성 환산 기대값"); print("="*64)
for nm,tb in (("부름",BASIC),("깊은 부름",DEEP)):
    ev=sum(p*eqv(r) for r,p in tb.items())
    print(f"  {nm:<8} {ev:>6.2f}")
print(f"\n  먼 울림 1개 = 울림 5개로 환산하면")
print(f"    부름       {sum(p*eqv(r) for r,p in BASIC.items()):.2f} / 울림 1")
print(f"    깊은 부름  {sum(p*eqv(r) for r,p in DEEP.items())/5:.2f} / 울림 1  ← 일반이 근소 우위")

print("\n"+"="*64); print("2. 본디 10 확보 확률"); print("="*64)
for r in (1,3,5,6,7):
    print(f"  ★{r} 출발 → 본디 10 : {BONDI[r].get(10,0)*100:>5.1f}%   "
          f"본디 8 이상 : {sum(v for k,v in BONDI[r].items() if k>=8)*100:>5.1f}%")

def pull(table, pity):
    """천장 포함 소환"""
    out=[]
    for i in range(1, 181):
        r=pick(table)
        for th,mn in pity:
            if i%th==0: r=max(r,mn)
        out.append(r)
    return out

print("\n"+"="*64); print("3. 천장 적용 시 100회 결과 (10,000명 평균)"); print("="*64)
random.seed(20260901)
for nm,tb,pity in (("부름",BASIC,[(30,3)]),("깊은 부름",DEEP,[(60,4),(180,5)])):
    cnt=collections.Counter()
    for _ in range(10000):
        for i in range(1,101):
            r=pick(tb)
            for th,mn in pity:
                if i%th==0: r=max(r,mn)
            cnt[r]+=1
    tot=sum(cnt.values())
    print(f"  {nm}")
    for r in sorted(cnt, reverse=True):
        print(f"    ★{r}  {cnt[r]/tot*100:>5.2f}%  ({cnt[r]/10000:>5.2f}명/100회)")

print("\n"+"="*64); print("4. 승급 경제 — 10성 1명까지 필요한 소환 횟수"); print("="*64)
def run(table, pity, cap=100000):
    inv={r:[] for r in range(1,11)}; n=0
    while n<cap:
        n+=1; r=pick(table)
        for th,mn in pity:
            if n%th==0: r=max(r,mn)
        inv[r].append(pick(BONDI[r]))
        if n%10: continue
        moved=True
        while moved:
            moved=False
            for k in range(1,10):
                promo=[b for b in inv[k] if b>k]
                if not promo or len(inv[k])<2: continue
                base=max(promo); inv[k].remove(base)
                if not inv[k]: inv[k].append(base); continue
                inv[k].remove(min(inv[k])); inv[k+1].append(base); moved=True
        if inv[10]: return n
    return None
for nm,tb,pity in (("부름만",BASIC,[(30,3)]),("깊은 부름만",DEEP,[(60,5),(180,6)])):
    res=[run(tb,pity) for _ in range(200)]
    ok=[x for x in res if x]
    print(f"  {nm:<12} 중앙값 {statistics.median(ok):>6.0f}회   평균 {statistics.mean(ok):>6.0f}회")
print("\n  → 6~7성 직뽑을 없애자 두 경로의 격차가 크게 줄었다.")
print("    고급 소환은 지름길이 아니라 '즉시 전력과 그릇'을 사는 수단이 된다.")
