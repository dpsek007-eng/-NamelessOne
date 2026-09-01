# -*- coding: utf-8 -*-
"""승급(합성) 시뮬레이터 — n성 2명을 합쳐 (n+1)성 1명.
   대상은 본디 > 현재성 이어야 하고, 재료는 같은 성이면 아무나 된다."""
import random, statistics

PULL={5:.02,4:.08,3:.20,2:.30,1:.40}
BONDI={5:{5:.45,6:.33,7:.15,8:.05,9:.017,10:.003},4:{4:.42,5:.30,6:.15,7:.08,8:.035,9:.012,10:.003},
       3:{3:.38,4:.28,5:.16,6:.09,7:.05,8:.025,9:.010,10:.005},
       2:{2:.35,3:.28,4:.15,5:.09,6:.06,7:.035,8:.020,9:.010,10:.005},
       1:{1:.35,2:.30,3:.15,4:.08,5:.05,6:.03,7:.02,8:.010,9:.007,10:.003}}
def pick(d):
    x,a=random.random(),0.0
    for k,v in sorted(d.items()):
        a+=v
        if x<=a: return k
    return max(d)

def fuse_all(inv):
    """가능한 승급을 전부 수행. inv[r] = 본디 리스트"""
    moved=True
    while moved:
        moved=False
        for r in range(1,10):
            promo=[b for b in inv[r] if b>r]      # 승급 가능한 대상
            if not promo or len(inv[r])<2: continue
            promo.sort(reverse=True)
            base=promo[0]
            inv[r].remove(base)
            if not inv[r]: inv[r].append(base); continue
            mat=min(inv[r])                        # 본디 낮은 쪽을 재료로
            inv[r].remove(mat)
            inv[r+1].append(base)
            moved=True
    return inv

def run(target=10, cap=200000):
    inv={r:[] for r in range(1,11)}
    pulls=0
    while pulls<cap:
        pulls+=1
        r=pick(PULL); inv[r].append(pick(BONDI[r]))
        if pulls%10==0:
            fuse_all(inv)
            if inv[target]: return pulls
    fuse_all(inv)
    return pulls if inv[target] else None

print("="*66)
print("승급 규칙: n성 + n성 → (n+1)성  (대상은 본디 > n 이어야 함)")
print("="*66)
print("\n1성 하나를 10성까지 올리려면 필요한 1성 환산 개수:")
for n in range(1,6):
    print(f"   {n}성에서 출발 → 재료 {2**(10-n):>4}개의 {n}성  (1성 환산 {2**9:>3}개)")

ev = sum(p*2**(r-1) for r,p in PULL.items())
print(f"\n뽑기 1회의 기대 가치: {ev:.2f} (1성 환산)")
print(f"10성 1명 = 1성 환산 {2**9}개  →  이론상 최소 {2**9/ev:.0f}회")

random.seed(20260901)
runs=[run() for _ in range(400)]
ok=[r for r in runs if r]
print("\n" + "="*66)
print(f"시뮬레이션 400회 — 첫 10성 달성까지 걸린 뽑기 횟수")
print("="*66)
print(f"   중앙값 {statistics.median(ok):>7.0f}회")
print(f"   평균   {statistics.mean(ok):>7.0f}회")
print(f"   상위25%{sorted(ok)[len(ok)//4]:>7.0f}회 (운 좋은 경우)")
print(f"   하위25%{sorted(ok)[3*len(ok)//4]:>7.0f}회 (운 나쁜 경우)")
print(f"\n   본디 10 자체가 {1/0.00375:.0f}회당 1명이라 이쪽이 진짜 병목이다.")
print("   재료는 넘치는데 그릇이 없는 상황 → 플레이어가 계속 뽑을 이유가 된다.")
