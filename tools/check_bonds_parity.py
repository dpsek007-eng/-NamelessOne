# -*- coding: utf-8 -*-
"""인연 파이썬 ↔ C# 일치. 규칙을 두 언어로 적으면 조용히 갈라진다 — 생성기에서 겪은 일이다(docs/10).
   같은 23명을 tools/bonds.py:find_bonds() 와 Irem.Sim/Bonds.Find() 에 똑같이 먹여
   성립 목록·순서·발동 여부가 글자까지 같은지 본다."""
import json, sys, subprocess
sys.path.insert(0, 'tools')
import bonds

T = json.load(open('unity/Assets/Resources/Irem/garden.json', encoding='utf-8'))
src = json.load(open('data/characters.json', encoding='utf-8'))
rel = [b for b in src['bonds'] if b['type'] == '관계']
zone = [dict(id=a['id'], cls=a['cls'], trade=a['trade'], era=a['era'], role=a['role'])
        for a in T['agents']]

found = bonds.find_bonds(zone, rel)
on, wait = bonds.split_active(found)
need = max(3, round(len(zone) * 0.30))
py = []
for kind, b, arg in found:
    rid = bonds.rule_id(kind, b, arg)
    py.append(f"{kind}\t{rid}\t{'발동' if (kind,b,arg) in on else '대기'}\t"
              f"{need if kind=='최후' else 0}\t{arg or ''}")

cs = [l for l in (sys.argv[1] and open(sys.argv[1], encoding='utf-8').read().splitlines() or [])
      if l and not l.startswith('#')]

bad = 0
for i in range(max(len(py), len(cs))):
    a = py[i] if i < len(py) else '(없음)'
    b = cs[i] if i < len(cs) else '(없음)'
    if a != b:
        bad += 1
        print(f"[다름] {i}\n  파이썬 {a}\n  C#     {b}")
print(f"인원 {len(zone)} · 성립 {len(found)}종 · 발동 {len(on)}종 · 대기 {len(wait)}종 · 최후 기준 {need}명")
print(f"파이썬 {len(py)}줄 · C# {len(cs)}줄 · 다른 줄 {bad}")
sys.exit(1 if bad or len(py) != len(cs) else 0)
