# -*- coding: utf-8 -*-
"""1막(1~30층) 층 사양 생성 + 클리어 가능성 검증."""
import json, sys, collections
sys.path.insert(0,'tools')
from power import power

NAMES={1:"재",2:"빈 집",3:"이름 없는 자",4:"부름",5:"첫 대답",6:"갈 곳",7:"층수 없는 층",
8:"뜰",9:"첫 생업",10:"복원",11:"그릇 둘",12:"굽는 소리",13:"화덕",14:"말",15:"그 뒤",
16:"우물",17:"두 음절",18:"잔해",19:"얇아진 재",20:"칼자국",21:"부서진 것",22:"흩어진 짐",
23:"수레",24:"북문",25:"문 바깥",26:"표식",27:"등진 사람",28:"문의 안과 밖",29:"안쪽",30:"종소리",
# ── 2막 ──
31:"이긴 쪽 없음",32:"색 빠진 깃발",33:"벽의 이름",34:"먼 종소리",35:"같은 방향",
36:"두 갈래",37:"멈춘 종",38:"표식의 수",39:"아직 선 성",40:"경계",
41:"서쪽 종탑",42:"다시 선 종탑",43:"하루 두 번",44:"소리만 남다",45:"첫 균열",
46:"기록관",47:"삼급 서기",48:"일곱 장",49:"끊긴 문장",50:"사본",
51:"열 손가락",52:"웃는 시장",53:"삭감된 예산",54:"또 표식",55:"이어 붙인 자리",
56:"두 번째",57:"묻지 못함",58:"삼킨 골목",59:"피난 준비",60:"균열기의 끝"}
def ERA(f):
    return "종말기" if f<=20 else "붕괴기" if f<=40 else "균열기"

def teams(f):
    """1~4층은 전투 없음(연출). 연계는 15층, 관문은 20층부터."""
    if f<5: return 0
    if f%10==0 and f>=20: return 3
    if f%5==0 and f>=15: return 2
    return 1

def slot(f):
    """팀 정원 — 초반에는 5명을 채울 수 없다"""
    if f<10: return 3
    if f<15: return 4
    return 5

# 층별 열쇠 조건 (대본과 연동)
ROUTES={
 # ── 2막 ──
 33:[("era","층범위:±3",1,0.50),("seek","탐구",1,0.72)],          # 벽에 이름을 적던 병사
 35:[("guard","수호",2,0.70),("devote","헌신",1,0.74)],
 38:[("seek","탐구",2,0.62),("era","층범위:±3",1,0.55)],          # 표식을 세는 일
 39:[("trade","생업:망루",1,0.55),("resist","저항",2,0.66)],     # 레안의 성벽
 40:[("guard","수호",2,0.70),("seek","탐구",1,0.72),("weak","약체",3,0.62)],
 41:[("trade","생업:종탑",1,0.50),("devote","헌신",2,0.66)],     # 세렌의 종
 45:[("seek","탐구",1,0.70),("flee","도피",1,0.74)],
 47:[("trade","생업:서고",1,0.55),("seek","탐구",2,0.64)],       # 이델의 기록관
 50:[("trade","생업:서고",2,0.55),("seek","탐구",2,0.62),("weak","약체",3,0.60)],
 53:[("devote","헌신",2,0.68),("trade","생업:악기",1,0.62)],     # 축제
 55:[("seek","탐구",2,0.60),("era","층범위:±3",1,0.58)],          # 이어 붙인 자리
 58:[("trade","생업:채석",1,0.55),("resist","저항",2,0.66)],     # 골목을 메우던 사람
 60:[("seek","탐구",2,0.66),("devote","헌신",2,0.68),("weak","약체",3,0.60)],
 10:[("trade","생업:담장",1,0.75),("weak","약체",3,0.70)],
 14:[("devote","헌신",1,0.75)],
 15:[("seek","탐구",1,0.75),("guard","수호",1,0.70)],
 20:[("guard","수호",1,0.72),("seek","탐구",1,0.75),("weak","약체",3,0.65)],
 24:[("trade","생업:담장",1,0.45),("guard","수호",1,0.60),("era","층범위:±3",1,0.62)],
 25:[("flee","도피",1,0.70)],
 28:[("guard","수호",2,0.65),("era","층범위:±3",1,0.60)],
 30:[("guard","수호",2,0.70),("seek","탐구",1,0.72),("weak","약체",3,0.62)],
}

d=json.load(open('data/characters.json',encoding='utf-8'))
chars=[c for c in d['characters'] if c.get('floor')]
PULL_AVG=0.4*146+0.3*190+0.2*253+0.08*337+0.02*446   # 무명 잔상 기대 전투력

def roster_at(f):
    """f층 도달 시점의 보유 전력 목록(추정)"""
    owned=[power(c['stats']) for c in chars if c['floor']<=f]
    owned+= [PULL_AVG]*int(f*0.7)          # 뽑기로 얻는 무명 잔상
    lv=1+0.028*f                            # 레벨 성장 계수
    return sorted((p*lv for p in owned), reverse=True)

floors=[]
for f in range(1,61):
    t=teams(f); need=t*slot(f)
    r=roster_at(f)
    best=sum(r[:need]) if len(r)>=need else 0
    req=round(best*0.78)                    # 돌파 경로는 보유 전력의 78%
    if t==0:
        floors.append({"floor":f,"world":1,"era":ERA(f),"name":NAMES[f],
                       "teams":0,"members_required":0,"base_power":0,
                       "routes":[],"note":"전투 없음 · 연출 층"})
        continue
    routes=[{"id":"force","power":1.0,"conditions":[]}]
    for rid,cond,cnt,mult in ROUTES.get(f,[]):
        if cond.startswith("층범위"):
            ctype,cval = "층범위", f"{max(1,f-3)}~{min(99,f+3)}"
        elif ":" in cond: ctype,cval = cond.split(":",1)
        elif cond=="약체": ctype,cval = "약체","평균 선명도 3 이하"
        else:             ctype,cval = "역할",cond
        routes.append({"id":rid,"power":mult,
                       "conditions":[{"type":ctype,"value":cval,"count":cnt}]})
    floors.append({"floor":f,"world":1,"era":ERA(f),"name":NAMES[f],
                   "teams":t,"slot":slot(f),"members_required":need,
                   "base_power":req,"routes":routes})

json.dump({"world":1,"acts":[1,2],"floors":floors},
          open('data/floors.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)

print(f"{'층':>3} {'팀':>2} {'정원':>4} {'인원':>4} {'요구':>7} {'보유':>7} {'여유':>6} {'경로':>4}  이름")
print("-"*68)
ok=True
for fl in floors:
    f=fl["floor"]
    if fl["teams"]==0:
        print(f"{f:>3}  -    -    -       -       -      -    -   {fl['name']}  (연출)")
        continue
    r=roster_at(f); need=fl["members_required"]
    have=sum(r[:need]) if len(r)>=need else 0
    short = len(r)<need
    ratio = have/fl["base_power"] if fl["base_power"] else 0
    mark = " ← 인원부족" if short else ""
    if short: ok=False
    print(f"{f:>3} {fl['teams']:>2} {fl['slot']:>4} {need:>4} {fl['base_power']:>7} "
          f"{have:>7.0f} {ratio:>5.2f}x {len(fl['routes']):>3}개  {fl['name']}{mark}")
print()
print("보유 잔상 수 추이:", ", ".join(f"{f}층={len(roster_at(f))}" for f in (10,20,30,40,50,60)))
print("인원 부족 없음" if ok else "⚠ 인원 부족 층 존재")
