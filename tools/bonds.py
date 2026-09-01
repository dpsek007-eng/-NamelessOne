# -*- coding: utf-8 -*-
"""인연 — 뜰에 함께 있는 잔상 사이에서 자동으로 발생하는 관계.
   관계 인연(손집필)은 data/characters.json 에 있고, 여기는 조건으로 발생하는 것들이다."""

# ── 계층 인연 ─────────────────────────────────────────────
# 신분 차에서 나오는 관계. 쌍마다 손으로 쓴다 (10쌍뿐이라 감당된다).
CLASS_PAIRS=[
 dict(id="tenancy", a="귀족", b="농어민", title="소작", n=(1,1),
  story="영주는 소작인의 이름을 외우고 있었다.\n소작인은 영주의 이름을 몰랐다.\n뜰에서 둘은 같은 밭을 맨다.",
  reward="밭·광부 계열 생산량 +18%"),
 dict(id="roster", a="귀족", b="병졸", title="명단", n=(1,2),
  story="기사는 병졸의 이름을 부르며 싸웠다.\n병졸 하나가 그 이름을 자기 아이에게 붙였다.\n그 아이는 이 층에 없다.",
  reward="병졸 계열 잔상 의지 +12% · 기사 자취 +10%"),
 dict(id="doorway", a="성직", b="유랑", title="문간", n=(1,1),
  story="신전은 문을 잠근 적이 없다.\n유랑민은 남의 집 문 앞에서 자지 않았다.\n둘 다 이유를 말하지 않는다.",
  reward="★1~★2 잔상 전체 생산량 +20%"),
 dict(id="attendance", a="왕실", b="하인", title="시중", n=(1,1),
  story="궁정 사람은 왕의 이름을 부를 수 있는 몇 안 되는 사람이었다.\n하인은 궁정 사람의 이름을 몰랐다.\n뜰에서는 둘 다 이름이 없다.",
  reward="뜰 전체 생산량 +10% · 두 잔상 공명 +15%"),
 dict(id="dismissal", a="술사", b="관리", title="반려", n=(1,1),
  story="술사가 「별것 아니다」라고 했고, 관리가 그것을 받아 적었다.\n종이는 위로 올라갔다가 붉은 도장이 찍혀 돌아왔다.\n둘 다 그 종이가 지금 어디 있는지 모른다.",
  reward="기억 조각 +25% · 명부 단서 해금 속도 상승",
  note="이델의 여덟 번째 보고서와 연결된다. 이델을 보유한 상태면 추가 기록이 열린다."),
 dict(id="onroad", a="상인", b="유랑", title="길 위", n=(1,1),
  story="상인은 길에서 만난 사람을 태워 주었다.\n유랑민은 내릴 때 인사를 하지 않았다.\n둘 다 그것을 예의라고 생각했다.",
  reward="방치 보상 수령 상한 +3시간"),
 dict(id="delivery", a="장인", b="상인", title="납품", n=(2,1),
  story="장인은 값을 깎지 않았고 상인은 깎아 달라 하지 않았다.\n마지막 거래는 값을 치르지 못한 채 끝났다.",
  reward="유품·진급석 +15%"),
 dict(id="samerice", a="병졸", b="하인", title="같은 밥", n=(1,1),
  story="성 안에서 둘은 같은 것을 먹었다. 남은 것이었다.\n서로를 아랫사람이라고 부르지 않은 유일한 사이였다.",
  reward="두 잔상 잔존 +14%"),
 dict(id="twoanswers", a="술사", b="성직", title="다른 답", n=(1,1),
  story="같은 질문에 하나는 「주기」라고 했고 하나는 「징조」라고 했다.\n둘 다 틀렸다.\n뜰에서 둘은 아직 그 이야기를 하지 않는다.",
  reward="탐구 역할 전체 공명 +12%"),
 dict(id="counted", a="성직", b="관리", title="세는 일", n=(1,1),
  story="한쪽은 죽은 이의 이름을 불렀고 한쪽은 그 수를 적었다.\n숫자와 이름이 맞지 않는 날이 있었다.\n누가 틀렸는지는 밝히지 못했다.",
  reward="명부 완성 보상 +20%",
  note="「세는 사람들」 관계 인연과 중첩 가능"),
]

# ── 생업 인연 ─────────────────────────────────────────────
# 특정 생업 쌍. 계층보다 좁고 구체적이다.
TRADE_PAIRS=[
 dict(id="vow", a="성녀", b="성기사", title="맹세",
  story="성기사는 매일 아침 맹세를 되뇌었다.\n성녀는 그것을 한 번도 들은 척하지 않았다.",
  reward="성녀 회복량 +20% · 성기사 자취 +18%"),
 dict(id="stars", a="점성", b="서고", title="기록",
  story="점성술사가 잰 수치를 서기가 옮겨 적었다.\n옮기는 동안 소수점 하나가 사라졌다.\n둘 다 알지 못했다.",
  reward="기억 조각 +22%"),
 dict(id="naming", a="장의", b="사경", title="이름을 적는 일",
  story="한쪽은 죽은 이의 이름을 관에 붙였고 한쪽은 그것을 경전 여백에 옮겼다.\n이름을 모르는 사람은 특징을 적었다. 둘 다 같은 방식이었다.",
  reward="명부 등재 시 추가 보상 · 두 잔상 공명 +15%"),
 dict(id="bell_light", a="종탑", b="등대", title="신호",
  story="하나는 소리로 알렸고 하나는 빛으로 알렸다.\n마지막 날 둘 다 멈추지 않았다.",
  reward="울림 생산량 +25%"),
 dict(id="fire", a="화덕", b="숯막", title="같은 불",
  story="숯을 굽는 사람과 빵을 굽는 사람은 서로를 본 적이 없다.\n불은 같은 불이었다.",
  reward="식량·유품 +18%"),
]

# ── 시대 인연 ─────────────────────────────────────────────
ERA_BOND=dict(n=4, title="그때 거기 있었던 사람들",
 story="{era}를 함께 지난 사람들이다.\n서로 아는 사이는 아니었다. 같은 하늘을 봤을 뿐이다.",
 reward="구역 전체 생산량 +12%")

# ── 최후 인연 ─────────────────────────────────────────────
ROLE_BOND={
 "수호":dict(n=3,title="같은 자리에 남은 사람들",story="셋 다 물러서지 않았다. 셋 다 같은 자리에서 발견되었다.",reward="수호 역할 자취 +15%"),
 "저항":dict(n=3,title="돌아선 사람들",story="셋 다 도망치라는 말을 들었다. 셋 다 돌아섰다.",reward="저항 역할 의지 +15%"),
 "헌신":dict(n=3,title="자기 몫을 남긴 사람들",story="셋 다 마지막까지 자기 것을 챙기지 않았다.",reward="헌신 역할 회복량 +15%"),
 "탐구":dict(n=3,title="끝맺지 못한 기록",story="셋 다 무언가를 적다가 멈췄다. 세 기록 모두 마지막 문장이 없다.",reward="탐구 역할 공명 +15%"),
 "도피":dict(n=3,title="돌아가지 않은 사람들",story="셋 다 뒤를 보지 않았다. 셋 다 더 멀리 가지 못했다.",reward="도피 역할 회피율 +15%"),
}

# 한 구역에서 동시에 켤 수 있는 인연 수. 나머지는 「발견됨」으로 표시만 된다.
ACTIVE_SLOTS=4
PRIORITY={"관계":0,"생업":1,"계층":2,"최후":3,"시대":4}   # 구체적인 것이 우선

def find_bonds(shades):
    """뜰 한 구역의 잔상 목록을 받아 성립하는 인연을 반환한다.
       shade는 dict이며 cls / trade / era / role 키를 갖는다.
       반환값은 성립 목록일 뿐이고, 실제 발동은 ACTIVE_SLOTS 개까지만이다."""
    out=[]
    cls=[s.get("cls") for s in shades]
    trd=[s.get("trade") for s in shades]
    era=[s.get("era") for s in shades]
    rol=[s.get("role") for s in shades]

    for p in CLASS_PAIRS:
        na,nb=p["n"]
        if p["a"]==p["b"]:
            if cls.count(p["a"])>=na+nb: out.append(("계층",p,None))
        elif cls.count(p["a"])>=na and cls.count(p["b"])>=nb:
            out.append(("계층",p,None))
    for p in TRADE_PAIRS:
        if p["a"] in trd and p["b"] in trd: out.append(("생업",p,None))
    # 시대 인연은 구역 최다 시대 하나만 성립한다 (같은 문구가 여러 번 뜨지 않게)
    ecnt={e:era.count(e) for e in set(era) if e}
    if ecnt:
        top=max(ecnt, key=ecnt.get)
        if ecnt[top]>=ERA_BOND["n"]: out.append(("시대",ERA_BOND,top))
    # 최후 인연은 구역 인원에 비례한다. 18명 구역에서 3명은 너무 쉽다.
    need=max(3, round(len(shades)*0.30))
    for r,b in ROLE_BOND.items():
        if rol.count(r)>=need: out.append(("최후",dict(b,n=need),None))
    out.sort(key=lambda x: PRIORITY.get(x[0],9))
    return out

def split_active(bonds, slots=ACTIVE_SLOTS):
    """앞의 slots개만 발동, 나머지는 발견 상태. 실제 게임에서는 플레이어가 고른다."""
    return bonds[:slots], bonds[slots:]

def render(kind,b,arg):
    t=b["title"] if kind!="시대" else b["title"]
    st=b["story"].format(era=arg) if arg else b["story"]
    return kind,t,st,b["reward"],b.get("note")
