# -*- coding: utf-8 -*-
"""생업 47종의 소품 표 — 3D 로 뽑을 것들.

`tools/trades.py` 의 TRADES 가 원본이다. 여기서는 그 47종에 세 가지를 더한다.

    en    영어 묘사        이미지 생성기에 넣는 말. 한국어로는 안 나온다
    m     실물 최대 길이   미터. 블렌더에서 크기를 맞출 때 쓴다
    hold  손에 드는가      grip 이면 손 앵커에 붙고, place 면 바닥에 놓인다

크기를 적어 두는 이유는, 생성기가 크기를 모르기 때문이다. 곡괭이와 인장이
같은 상자 안에서 나온다. 유니티에 그대로 넣으면 인장이 곡괭이만 해진다.
"""

# obj(한국어) -> (영어 묘사, 실물 최대 길이 m, grip/place)
PROPS = {
    "물통":            ("a worn wooden water pail with an iron handle, staves darkened by use", 0.35, "grip"),
    "불다 만 유리":     ("a long iron glassblowing pipe with a lump of molten glass "
        "swelling at one end, the glass uneven and half formed", 0.30, "grip",
        "light bulb, lightbulb, filament, lamp, screw base, electric, wire"),
    "이 빠진 망치":     ("a blacksmith's hammer with a chipped, nicked steel head and a worn wooden haft", 0.35, "grip"),
    "마른 약초 다발":   ("a bundle of dried medicinal herbs bound with coarse twine, brittle leaves", 0.30, "grip"),
    "닳은 대패":       ("a worn wooden hand plane, its sole polished smooth, blade dulled", 0.25, "grip"),
    "씨앗 주머니":      ("a small coarse linen seed pouch closed with a drawstring, bulging with grain", 0.20, "grip"),
    "실이 감긴 바늘쌈": ("a rolled cloth needle case wrapped with threads, needles pushed through the fabric", 0.12, "grip"),
    "그을린 등피":      ("a soot-blackened glass lamp chimney, brass collar tarnished", 0.25, "grip"),
    "닳은 고삐":       ("worn leather horse reins, coiled, the strap cracked and darkened by sweat", 0.40, "grip"),
    "쐐기 박힌 정":     ("a stonemason's iron chisel with a steel wedge driven into its split head", 0.25, "grip"),
    "줄이 끊긴 현악기": ("a lute-like wooden string instrument with snapped strings curling loose from the pegs", 0.70, "grip"),
    "손잡이가 닳은 국자": ("a large iron ladle, its wooden handle worn thin and smooth in the middle", 0.35, "grip"),
    "식은 화덕":       ("a small domed clay bread oven, cold, its mouth blackened with old soot", 1.20, "place"),
    "닳은 종 밧줄":     ("a thick frayed bell rope, coiled, cloth wound around the grip section", 0.50, "grip"),
    "닳은 붓":         ("a worn calligraphy brush, bamboo shaft, bristles splayed and stained with ink", 0.25, "grip"),
    "이 빠진 흙손":     ("a bricklayer's trowel, one flat triangular steel blade with a "
        "chipped edge and a cracked wooden handle", 0.28, "grip",
        "two tools, tool set, knife, cleaver, several blades"),
    "부러진 빗장":      ("a single long heavy rusted iron bar lying alone, thick square "
        "section, one end a jagged break where it snapped", 0.90, "grip",
        "door, gate, doorway, hinge, wall, grille, lock, window"),
    "봉인이 뜯기지 않은 서신": ("a folded parchment letter closed with an unbroken red wax seal", 0.20, "grip"),
    "녹슨 종":         ("a small rusted bronze watchtower bell with a worn iron clapper", 0.40, "place"),
    "굳은 가죽 한 장":  ("a stiff dried leather hide rolled into a loose curl and standing "
        "upright, thick and rigid, edges curled", 0.80, "grip",
        "flat sheet, texture, close-up, swatch, filling the frame, seamless"),
    "해진 그물":        ("a tattered fishing net gathered into a bundle, several holes torn in the mesh", 0.60, "grip"),
    "마개가 빠진 항아리": ("a round earthenware brewing jar with its stopper missing, glaze crazed", 0.50, "place"),
    "실패":            ("a wooden thread bobbin wound with coarse yarn, some of it unravelling", 0.15, "grip"),
    "금 간 그릇":       ("a ceramic bowl with a long crack running down one side, glaze chipped at the rim", 0.25, "grip"),
    "꺼진 숯":         ("a cluster of extinguished charcoal lumps, matte black, powdery at the edges", 0.20, "place"),
    "깨끗한 천":        ("a clean folded white linen cloth, crisp, softly creased", 0.30, "grip"),
    "마르지 않은 붓":   ("an ink brush still wet with black ink, a drop hanging from the bristles", 0.25, "grip"),
    "부러진 바퀴살":    ("a short thick tapered wooden rod lying alone, one end snapped off "
        "with raw splintered wood, old and weathered", 0.50, "grip",
        "wheel, cart, wagon, rim, hub, circle, round, tool, handle"),
    "닳은 지팡이":      ("a shepherd's crook, a long wooden staff worn smooth, the hook slightly split", 1.50, "grip"),
    "빈 벌통":         ("an empty coiled-straw skep beehive, dome shaped, loose strands at the base", 0.50, "place"),
    "닳은 인장":        ("a small worn royal seal stamp, carved stone set in a bronze grip", 0.10, "grip"),
    "빛바랜 문장":      ("a faded painted heraldic crest on a wooden plaque, colours washed out", 0.50, "grip"),
    "이 빠진 검":       ("a straight double-edged steel sword, the blade perfectly straight, "
        "several deep notches along the edge, leather grip worn", 1.00, "grip",
        "curved blade, scimitar, falchion, sabre, katana"),
    "닳은 경전":        ("a worn leather-bound scripture book, corners rounded, pages darkened at the edges", 0.30, "grip"),
    "찢어진 세첩":      ("a torn tax ledger booklet, pages half ripped out, string binding loose", 0.30, "grip"),
    "비어 있는 궤":     ("an empty wooden merchant chest, lid open, iron banding rusted", 0.70, "place"),
    "해진 빨래방망이":  ("a worn wooden laundry beating paddle, one edge frayed and splintered", 0.50, "grip"),
    "해진 봇짐":        ("a tattered cloth travel bundle tied to a stick, patched in several places", 0.50, "grip"),
    "이 빠진 곡괭이":   ("a medieval pickaxe, a long straight wooden handle with a narrow "
        "curved iron pick head mounted crosswise at the top, one tip chipped",
        0.90, "grip",
        "axe blade, broad blade, hatchet, cleaver, sword, spear, scythe, "
        "blade with no handle"),
    "시위 끊긴 활":     ("a wooden bow with a snapped bowstring hanging loose from one nock", 1.20, "grip"),
    "금 간 지팡이":     ("a tall wooden wizard's staff with a long crack spiralling up the shaft", 1.60, "grip"),
    "마른 물그릇":      ("a shallow stone water bowl, completely dry, a pale mineral ring inside", 0.25, "grip"),
    "금이 간 관측경":   ("a brass telescope with a cracked front lens, tube dented and tarnished", 0.60, "grip"),
    "깨진 증류기":      ("a broken glass alembic still, its neck snapped, copper base scorched", 0.40, "place"),
    "닳은 흰 천":       ("a worn white linen veil loosely folded into a small heap resting "
        "alone, thin frayed edges", 0.50, "grip",
        "flat, texture, close-up, filling the frame, curtain, backdrop, seamless"),
    "이 빠진 성검":     ("an ornate holy sword with a notched blade, gilding worn from the crossguard", 1.10, "grip"),
    "마르지 않은 먹":   ("an inkstone with undried black ink pooled in it, an ink stick resting on the edge", 0.15, "grip"),
}

# 생성기에 붙이는 공통 말.
#
# 길이가 곧 내용이다. SDXL 의 CLIP 은 77토큰에서 자른다 — 묘사 + STYLE 이
# 그 안에 다 들어가야 한다. 처음엔 STYLE 이 79토큰이었고, 묘사와 합치면
# 130토큰이 되어 뒤쪽 절반이 통째로 사라졌다. 사라진 것이 하필
# "배경 · 구도 · 시점" 이라 물건이 아무 데서나 아무렇게나 나왔다.
# 곡괭이가 도끼로 나오던 것도 이것이었다 — 막으려던 negative 가 잘려 있었다.
#
#   묘사 최대 24토큰(46종) + STYLE 40토큰 = 64토큰. 들어간다.
#
# 그래서 여기서 뺀 말들(no people/hands/text/watermark, high detail)은
# 버린 것이 아니라 NEGATIVE 로 옮긴 것이다. 거기가 원래 자리다.
STYLE = (
    "product photograph of exactly one single object alone, "
    "centered, entire object visible in frame, three-quarter view, "
    "plain flat light grey background, soft even studio lighting, "
    "medieval fantasy, aged and worn, sharp focus"
)

# 이쪽도 77토큰이다. 소품별 negative 를 뒤에 붙일 자리를 남겨 둔다.
NEGATIVE = (
    "two objects, a pair, duplicate, side by side, multiple objects, set, collection, "
    "cropped, cut off, scene, room, table, floor, "
    "people, hands, text, watermark, blurry, low quality"
)


def slug(idx: int, trade_name: str) -> str:
    """파일 이름. 한글은 안 쓴다 — 유니티 에셋 이름과 셸을 둘 다 편하게 하려고."""
    import unicodedata
    ascii_hint = "".join(c for c in unicodedata.normalize("NFKD", trade_name)
                        if c.isascii() and c.isalnum())
    return f"{idx:02d}_{ascii_hint}" if ascii_hint else f"{idx:02d}"


def load():
    """tools/trades.py 를 읽어 47종을 표와 맞춘다. 하나라도 어긋나면 세운다."""
    import os, sys
    here = os.path.abspath(__file__)
    root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    # 컨테이너 안에서는 pipeline3d 만 /work 로 올라오므로 저장소 tools 가
    # 위로 두 단계 올라간 자리에 없다. run.sh 가 /repo/tools 로 따로 물린다.
    cands = [os.environ.get("IREM_TOOLS"), os.path.join(root, "tools"), "/repo/tools"]
    for c in cands:
        if c and os.path.exists(os.path.join(c, "trades.py")):
            sys.path.insert(0, c)
            break
    else:
        raise SystemExit(f"trades.py 를 못 찾았다. 찾아본 자리: {cands}")
    import trades

    out, missing = [], []
    for i, t in enumerate(trades.TRADES):
        obj = t["obj"]
        if obj not in PROPS:
            missing.append((i, t["n"], obj))
            continue
        row = PROPS[obj]
        # 네 번째 칸은 이 소품에만 거는 negative 다. 없으면 빈 문자열.
        # 공용 negative 에 넣을 수 없는 것들이 있다 — 곡괭이에 "axe" 를 막고
        # 싶어도 02번은 진짜 망치고, 물건마다 막을 것이 다르다.
        en, m, hold = row[0], row[1], row[2]
        neg = row[3] if len(row) > 3 else ""
        out.append({
            "i": i, "trade": t["n"], "obj": obj, "cls": t["cls"],
            "en": en, "m": m, "hold": hold, "neg": neg,
            "id": f"{i:02d}_{_romanize(t['n'])}",
        })
    if missing:
        raise SystemExit(f"표에 없는 소품 {len(missing)}종: {missing}")
    extra = set(PROPS) - {t["obj"] for t in trades.TRADES}
    if extra:
        raise SystemExit(f"trades.py 에 없는데 표에만 있는 소품: {sorted(extra)}")
    return out


_ROMAN = {
    "물장수": "watercarrier", "유리 세공": "glassblower", "대장간": "smithy",
    "약방": "apothecary", "목공": "carpenter", "밭": "field", "재봉": "tailor",
    "등대": "lighthouse", "마구간": "stable", "채석": "quarry", "악기": "musician",
    "부엌": "kitchen", "화덕": "bakery", "종탑": "belltower", "서고": "archive",
    "담장": "mason", "문지기": "gatekeeper", "전령": "courier", "망루": "watchtower",
    "무두질": "tanner", "어망": "fisher", "양조": "brewer", "방직": "weaver",
    "도공": "potter", "숯막": "charcoaler", "산파": "midwife", "장의": "undertaker",
    "마방": "cartwright", "양치기": "shepherd", "벌치기": "beekeeper", "궁정": "court",
    "영주": "lord", "기사": "knight", "사제": "priest", "징세": "taxman",
    "상단": "merchant", "세탁": "launderer", "유랑": "wanderer", "광부": "miner",
    "사냥": "hunter", "마법사": "mage", "정령술사": "spiritcaller", "점성": "astrologer",
    "연금": "alchemist", "성녀": "saint", "성기사": "paladin", "사경": "scribe",
}


def _romanize(n: str) -> str:
    return _ROMAN.get(n, "prop")


if __name__ == "__main__":
    rows = load()
    print(f"소품 {len(rows)}종 — 표가 맞는다")
    for r in rows:
        print(f"  {r['id']:22s} {r['obj']:20s} {r['m']:>5.2f}m  {r['hold']}")
