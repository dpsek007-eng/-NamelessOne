# -*- coding: utf-8 -*-
"""뜰 지도를 짓고 검사해서 data/garden.json 에 쓴다.

   지도를 손으로 적어 두고 「맞겠지」 하면 반드시 한 칸이 어긋난다.
   그래서 여기서 짓고, 여기서 잰다 — 줄 길이·일터가 딛을 수 있는 칸인지·
   성문에서 일터 열네 곳 전부에 걸어갈 수 있는지.

   층 지도(data/maps.json)와 같은 문자를 쓴다. 타일 그림을 그대로 쓸 수 있어야 한다.
   다만 뜰에는 시간이 흐르지 않으므로 깎이는 지형(균열·불)을 쓰지 않는다.
"""
import json, collections

W, H = 28, 18

# 뜰. 서쪽(왼쪽) 한 곳만 열려 있다 — 성문이다.
#         0         1         2
#         0123456789012345678901234567
MAP = [
    "############################",   # 0
    "#..........................#",   # 1
    "#.:.......^^^........#####.#",   # 2   ^^^ 종탑 언덕 · #### 기록관
    "#.:.......^^^........#...#.#",   # 3
    "#.........^^^........#...#.#",   # 4
    "#....................#.#####",   # 5   기록관 문은 아래로 열린다
    "#..........................#",   # 6
    "...........................#",   # 7   ← 성문
    "...........................#",   # 8   ← 성문
    "#..........................#",   # 9
    "#....###......ww...........#",   # 10  ### 화덕 · ww 우물
    "#....#.#......ww...........#",   # 11
    "#....#.#...................#",   # 12
    "#..........................#",   # 13
    "#.......:::........^^......#",   # 14  ::: 아직 복원되지 않은 터 · ^^ 망루
    "#.......:::........^^......#",   # 15
    "#..........................#",   # 16
    "############################",   # 17
]

# 뜰에서 쓰는 지형만. 값은 data/maps.json 의 것과 같다.
TERRAIN = {
    ".": {"n": "평지",   "mv": 1, "block": False, "desc": "그냥 땅"},
    ":": {"n": "잔해",   "mv": 2, "block": False, "desc": "아직 복원되지 않은 터. 넘느라 두 배로 느리다"},
    "#": {"n": "막힘",   "mv": 0, "block": True,  "desc": "담과 건물 벽"},
    "^": {"n": "높은 곳", "mv": 2, "block": False, "desc": "종탑 언덕과 망루"},
    "w": {"n": "물",     "mv": 3, "block": False, "desc": "우물물. 건너지 않는다"},
}

# 일터 열네 곳. 이름은 tools/trades.py 의 place 와 같아야 한다 —
# 캐릭터의 생업에서 일터를 찾는 유일한 열쇠다.
# prop 은 pipeline3d/out/props 의 FBX id. 실측 0.2~0.35m 짜리 유품이다(건물이 아니다).
STATIONS = [
    dict(name="성문",   x=1,  y=7,  prop="16_gatekeeper", desc="뜰 입구. 아무도 들어오지 않는데도 선다"),
    dict(name="길",     x=3,  y=8,  prop="17_courier",    desc="뜰 바깥으로 나가는 길의 시작"),
    dict(name="담",     x=2,  y=2,  prop="15_mason",      desc="무너진 담. 고쳐도 다음 날 또 무너져 있다"),
    dict(name="종탑",   x=11, y=5,  prop="13_belltower",  desc="언덕 위. 하루 두 번 종이 울린다"),
    dict(name="기록관", x=22, y=6,  prop="14_archive",    desc="문이 남쪽으로 열린다"),
    dict(name="거리",   x=14, y=8,  prop="10_musician",   desc="뜰 한가운데. 축제는 열리지 않는다"),
    dict(name="약방",   x=18, y=9,  prop="03_apothecary", desc="이미 죽은 사람들을 살핀다"),
    dict(name="빵집",   x=8,  y=11, prop="12_bakery",     desc="화덕. 서른일곱 개를 굽는다"),
    dict(name="우물",   x=13, y=11, prop="00_watercarrier", desc="아무도 마시지 않아도 긷는다"),
    dict(name="대장간", x=4,  y=13, prop="02_smithy",     desc="무엇을 벼리는지는 묻지 않는다"),
    dict(name="작업장", x=11, y=13, prop="04_carpenter",  desc="만들고 나면 어딘가에 두고 온다"),
    dict(name="망루",   x=19, y=13, prop="18_watchtower", desc="아래를 세지 않는다"),
    dict(name="채석장", x=24, y=14, prop="09_quarry",     desc="쓸 곳이 정해지지 않은 돌"),
    dict(name="등대",   x=26, y=16, prop="07_lighthouse", desc="갈 곳은 하나뿐이다"),
]

# 일터가 없는 잔상이 서 있는 자리. 「뜰 한가운데 서서 플레이어 쪽을 본다」
IDLE_SPOT = dict(x=13, y=9)


def check():
    bad = []
    for y, r in enumerate(MAP):
        if len(r) != W: bad.append(f"{y}줄이 {len(r)}칸이다 ({W}칸이어야 한다)")
        for ch in set(r):
            if ch not in TERRAIN: bad.append(f"{y}줄에 모르는 지형 문자 {ch!r}")
    if len(MAP) != H: bad.append(f"{len(MAP)}줄이다 ({H}줄이어야 한다)")
    if bad: return bad

    def passable(x, y):
        if not (0 <= x < W and 0 <= y < H): return False
        return not TERRAIN[MAP[y][x]]["block"]

    seen = collections.Counter()
    for s in STATIONS:
        seen[(s["x"], s["y"])] += 1
        if not passable(s["x"], s["y"]):
            bad.append(f"일터 {s['name']} 이 딛을 수 없는 칸이다 ({s['x']},{s['y']}) = {MAP[s['y']][s['x']]!r}")
    for c, n in seen.items():
        if n > 1: bad.append(f"일터 {n}곳이 같은 칸 {c} 에 있다")
    if not passable(**IDLE_SPOT): bad.append(f"서 있을 자리가 막혀 있다 {IDLE_SPOT}")

    # 성문에서 전부 걸어갈 수 있는가
    g = next(s for s in STATIONS if s["name"] == "성문")
    st, reach = [(g["x"], g["y"])], {(g["x"], g["y"])}
    while st:
        x, y = st.pop()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            n = (x+dx, y+dy)
            if n not in reach and passable(*n): reach.add(n); st.append(n)
    for s in STATIONS:
        if (s["x"], s["y"]) not in reach:
            bad.append(f"성문에서 {s['name']} 까지 갈 수 없다")
    if (IDLE_SPOT["x"], IDLE_SPOT["y"]) not in reach:
        bad.append("성문에서 서 있을 자리까지 갈 수 없다")
    return bad


def main():
    bad = check()
    for b in bad: print("[틀림]", b)
    if bad: raise SystemExit(1)

    # 생업 → 일터 가 실제로 맞는지 여기서 같이 잰다
    import sys; sys.path.insert(0, "tools")
    import trades as TR
    place = {t["n"]: t["place"] for t in TR.TRADES}
    names = {s["name"] for s in STATIONS}
    cs = json.load(open("data/characters.json", encoding="utf-8"))["characters"]
    homeless, cnt = [], collections.Counter()
    for c in cs:
        g = c["garden"]["생업"]
        if g == "없음": homeless.append(c["id"]); continue
        p = place.get(g)
        if p not in names:
            print(f"[틀림] {c['id']} 의 생업 {g} → 일터 {p} 가 뜰에 없다"); raise SystemExit(1)
        cnt[p] += 1

    out = {
        "설명": "뜰 지도. 18줄 × 28칸. 서쪽 한 곳만 열려 있다. tools/make_garden.py 가 짓는다.",
        "크기": {"w": W, "h": H},
        "지형": TERRAIN,
        "지도": MAP,
        "일터": STATIONS,
        "서있는자리": IDLE_SPOT,
    }
    with open("data/garden.json", "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)
        fp.write("\n")
    free = sum(r.count(".") + r.count(":") + r.count("^") + r.count("w") for r in MAP)
    print(f"뜰 {W}×{H} = {W*H}칸, 딛을 수 있는 칸 {free}, 일터 {len(STATIONS)}곳, 일터 없는 잔상 {len(homeless)}")
    print("  일터별 인원:", ", ".join(f"{k} {v}" for k, v in cnt.most_common()))


if __name__ == "__main__":
    main()
