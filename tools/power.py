# -*- coding: utf-8 -*-
"""전투력 산출 + 등급별 스탯 총량 정합성 검사."""
import json
# 잔존 배율을 7 → 4 로 낮추면서 재산출한 가중치 (역할 간 편차 0.7%).
# 7배 시절에는 HP가 공격력의 7배라 한 명 쓰러뜨리는 데 7대가 필요했고,
# 그 결과 전투력 수치가 실제 승패를 예측하지 못했다.
POWER = {"잔존":0.26, "의지":1.05, "자취":1.00, "공명":1.00}
# 등급별 스탯 풀 기준선 (잔존은 7배 스케일이므로 나눠서 환산)
RARITY_POOL = {1:180, 2:235, 3:305, 4:400, 5:540}
HP_SCALE = 4

def power(st): return sum(st[k]*w for k,w in POWER.items())
def pool(st):  return st["잔존"]/HP_SCALE + st["의지"] + st["자취"] + st["공명"]

if __name__=="__main__":
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
