# -*- coding: utf-8 -*-
"""본디(숨은 성장 한계) 분포 및 육성 비용 검증기."""
import random, collections

# 소환 등급 확률
PULL = {5:0.02, 4:0.08, 3:0.20, 2:0.30, 1:0.40}

# 초기 등급별 본디 분포. 선명도가 낮을수록 분산이 크고 꼬리가 길다.
BONDI = {
 5: {5:.45, 6:.33, 7:.15, 8:.05, 9:.017, 10:.003},
 4: {4:.42, 5:.30, 6:.15, 7:.08, 8:.035, 9:.012, 10:.003},
 3: {3:.38, 4:.28, 5:.16, 6:.09, 7:.05, 8:.025, 9:.010, 10:.005},
 2: {2:.35, 3:.28, 4:.15, 5:.09, 6:.06, 7:.035, 8:.020, 9:.010, 10:.005},
 1: {1:.35, 2:.30, 3:.15, 4:.08, 5:.05, 6:.03, 7:.02, 8:.010, 9:.007, 10:.003},
}

# 단계별 승급 비용: n성 -> (n+1)성.
#   지수 증가만으로는 마지막 단계가 총합을 지배해 출발 등급 차이가 사라진다.
#   그래서 "출발 등급 배수"를 따로 건다 — 기억이 적을수록 복원할 것이 많다.
R, BASE, ORIGIN_PENALTY = 1.35, 1.0, 1.5
def step_cost(n, origin): return BASE * (R ** n) * (ORIGIN_PENALTY ** (5 - origin))
def total_cost(origin, to): return sum(step_cost(n, origin) for n in range(origin, to))

ref = total_cost(5, 10)   # ★5 -> 10성 을 100% 기준으로

print("=" * 62)
print("1. 본디 분포 — 기댓값 vs 꼬리")
print("=" * 62)
print(f"{'초기':>4} {'기댓값':>7} {'P(본디>=8)':>11} {'P(본디=10)':>11}  분포")
for r in (5,4,3,2,1):
    d = BONDI[r]
    ev  = sum(k*v for k,v in d.items())
    p8  = sum(v for k,v in d.items() if k>=8)
    p10 = d.get(10,0)
    bar = "".join(f"{k}:{v*100:.0f}% " for k,v in sorted(d.items()) if v>=.03)
    print(f"★{r:<3} {ev:>7.2f} {p8*100:>10.1f}% {p10*100:>10.2f}%  {bar}")

print()
print("=" * 62)
print("2. 10성 도달 누적 비용 (★5 기준 100%)")
print("=" * 62)
for r in (5,4,3,2,1):
    c = total_cost(r, 10)
    print(f"★{r} -> 10성 : 승급 {10-r}단계, 누적 비용 {c/ref*100:>6.0f}%")

print()
print("=" * 62)
print("3. 소환 시뮬레이션 — 100,000회")
print("=" * 62)
random.seed(20260901)
N = 100_000
def pick(d):
    x, acc = random.random(), 0.0
    for k, v in sorted(d.items()):
        acc += v
        if x <= acc: return k
    return max(d)

hi = collections.Counter()   # 본디 10 달성자의 초기 등급
cnt8 = 0
for _ in range(N):
    r = pick(PULL)
    b = pick(BONDI[r])
    if b >= 8: cnt8 += 1
    if b == 10: hi[r] += 1

print(f"본디 8 이상  : {cnt8:>6}명  ({cnt8/N*100:.2f}%)  — 약 {N//max(cnt8,1)}회당 1명")
t = sum(hi.values())
print(f"본디 10 (만개): {t:>6}명  ({t/N*100:.3f}%)  — 약 {N//max(t,1)}회당 1명")
print("\n  본디 10 달성자는 어느 등급에서 나왔나:")
for r in (5,4,3,2,1):
    n = hi[r]
    print(f"    ★{r} 출신 {n:>4}명 ({n/max(t,1)*100:>5.1f}%)")
