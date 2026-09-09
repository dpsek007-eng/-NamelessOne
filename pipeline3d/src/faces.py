# -*- coding: utf-8 -*-
"""초상 표 — 얼굴을 뽑기 위한 말.

`docs/22-아트.md` 「초점」 절이 요구한 것을 그림으로 만든다.
소품(props.py)과 같은 규칙을 따른다 — 77토큰 안에 들어가야 하고,
말이 잘리면 뒤쪽 지시가 통째로 사라진다.

두 종류를 뽑는다.

  named  data/characters.json 의 23명. 이름이 있는 사람들이다.
         docs/22 는 「전승 40명은 손으로 그린다」고 했다. 이건 그 손그림을
         대신하는 것이 아니라 **발주서에 붙일 그림**이다.

  parts  역할 5 x 계층 11 = 55. 무명 잔상의 조합용 바탕이다.
         이쪽이 실제로 게임에 들어간다.

성별은 대부분 적지 않는다. 잔상은 온갖 사람이고, 적지 않으면 씨앗마다
갈린다. 글이 성별을 정해 둔 사람만 (어머니, 아이) 적는다.
"""

# 얼굴은 초상에만 붙는다 (docs/22). 그래서 구도가 고정이다 —
# 정면·가슴 위·한쪽 광원. 이 고정이 나중에 초점 레이어를 만들 때 값을 한다.
# 이목구비 위치가 장마다 같아야 흐릴 자리를 찾을 수 있기 때문이다.
STYLE = (
    "head and shoulders portrait of one person facing viewer, "
    "painterly oil painting, muted desaturated colours, "
    "single soft light from one side, plain dark background, "
    "medieval, weathered skin, solemn, mouth closed"
)

NEGATIVE = (
    "photograph, photorealistic, 3d render, cgi, anime, smiling, teeth, "
    "modern clothing, glasses, jewelry, text, watermark, signature, frame, "
    "two people, crowd, hands, cropped head, blurry, low quality, deformed"
)

# --- 역할 5종 — 얼굴에 남은 자세 ------------------------------------------
# 몸이 아니라 얼굴과 어깨만 보이므로, 역할은 시선과 목의 방향으로 나타난다.
# 실루엣 쪽에서 역할이 2.13% 밖에 안 갈린 것이 이 지점에서 만회되어야 한다.
ROLE_FACE = {
    "guard":  ("수호", "square jaw, steady level gaze straight ahead, broad neck"),
    "resist": ("저항", "clenched jaw, brow drawn low, eyes fixed hard on viewer"),
    "devote": ("헌신", "tired soft eyes lowered slightly, lined face, head tilted down"),
    "seek":   ("탐구", "narrow attentive eyes looking slightly off to one side, thin face"),
    "flee":   ("도피", "wide wary eyes glancing sideways, tense thin neck, half turned"),
}

# --- 계층 11종 — 얼굴에 남은 살림 ------------------------------------------
TIER_FACE = {
    "royal":    ("왕실", "pale unmarked skin, fine circlet, high collar"),
    "noble":    ("귀족", "groomed hair, embroidered collar, unworked skin"),
    "mage":     ("술사", "deep hood shadowing the brow, ink stained temple"),
    "clergy":   ("성직", "shaven head, plain grey cowl, calm heavy lids"),
    "clerk":    ("관리", "neat tied hair, ink smudge on cheek, plain dark collar"),
    "merchant": ("상인", "well fed face, fur trimmed collar, shrewd eyes"),
    "artisan":  ("장인", "burn scars on cheek, soot in the creases, cloth headband"),
    "peasant":  ("농어민", "sun darkened weathered skin, coarse undyed cloth"),
    "soldier":  ("병졸", "cropped hair, old scar across the brow, dented gorget"),
    "servant":  ("하인", "hair covered by a plain kerchief, downcast careful face"),
    "vagrant":  ("유랑", "matted hair, hollow cheeks, ragged wrapped shoulders"),
}

# --- 이름 있는 23명 --------------------------------------------------------
# data/characters.json 의 visual.silhouette 과 life/death 를 얼굴로 옮긴 것.
# 기계 번역이 아니라 손으로 옮겼다. 얼굴은 몸보다 틀리면 더 눈에 띈다.
NAMED = {
    "seren":             "old woman, bell ringer, deep lines, cloth wound around her throat, exhausted patient eyes",
    "kabril":            "broad shouldered gatekeeper, heavy brow, iron grey beard, unmoving stare",
    "idel":              "gaunt young archivist, sharp restless eyes, ink stained fingers at his collar",
    "miro":              "lean youth, hair falling over one eye, glancing away, ready to run",
    "north_gatekeeper":  "middle aged watchman, worn collar of a city guard coat, tired steady face",
    "baker_18f":         "baker, flour dusted brow, old burn scars up the neck, kind heavy face",
    "someones_mother":   "woman, hollow eyed, hair loose and unkempt, arms empty, grief worn face",
    "unnamed_000":       "a face with no distinguishing marks, plain, staring straight ahead, forgettable",
    "ash_sweeper":       "ash streaked face, cloth tied over the mouth pulled down, reddened eyes",
    "counting_child":    "child, smudge of charcoal on the cheek, counting under the breath, serious",
    "last_watercarrier": "yoke worn shoulders, cracked lips, cloth wrapped around the neck, parched",
    "dorn":              "thick necked fighter, one shoulder higher, broken nose, spear haft at his shoulder",
    "left_behind":       "young traveller with nothing, empty pack straps on the shoulders, blank stare",
    "cart_pusher":       "leaning forward, corded neck, jaw set, sweat darkened brow",
    "yuan":              "scholar with rolled sleeves, sharp examining eyes, thin mouth, a writing board at the hip",
    # 「긴 장대를 쥔」 이라고 적었더니 장대를 담으려고 카메라가 물러나
    # 8장 전부 반신이 됐다 (얼굴 너비 0.265, 표본 중앙값 0.467). 초점은
    # 눈~입 자리에 거는 것이라 얼굴이 작으면 배경이 뭉개진다. 장대를 뺐다.
    # 두 부대의 소매는 어깨 위에서도 보인다.
    "flagbearer":        "standard bearer, chin lifted, one shoulder in dark cloth and the other pale, weathered young face",
    "name_writer":       "charcoal in one hand, eyes turned to the wall beside him, absorbed",
    "pathpointer":       "one arm raised out of frame and never lowered, strained shoulder, fixed expression",
    "rean":              "upright, hands behind the back, unarmed, calm level unafraid gaze",
    "ledger_keeper":     "stooped clerk, spectacle marks on the nose, ledger under the arm, wary",
    "crack_child":       "small child leaning forward, hands behind the back, wide frightened eyes",
    "festival_maker":    "arms open, decorative cords on the sleeves, forced bright face over grief",
    "alley_filler":      "one shoulder dropped, callused hands at the collar, blunt patient face",
}

# 글이 성별·나이를 정해 둔 사람. 나머지는 씨앗에 맡긴다.
ERA_WEAR = {"균열기": "faint dust", "붕괴기": "grime and old blood", "종말기": "ash and deep exhaustion"}


def named_rows(chars):
    """data/characters.json 의 characters 리스트를 받아 초상 행으로."""
    rows = []
    for c in chars:
        d = NAMED.get(c["id"])
        if not d:
            continue
        rows.append({
            "id": c["id"], "kind": "named", "ko": c["name"],
            "title": c.get("title", ""), "rarity": c["rarity"],
            "role": c.get("role", ""), "era": c.get("era", ""),
            "en": d,
            "wear": ERA_WEAR.get(c.get("era", ""), ""),
            "key_color": (c.get("visual") or {}).get("key_color", ""),
        })
    return rows


def part_rows():
    """역할 x 계층 55종."""
    rows = []
    for rs, (rk, rd) in ROLE_FACE.items():
        for ts, (tk, td) in TIER_FACE.items():
            rows.append({
                "id": f"{rs}_{ts}", "kind": "part", "ko": f"{rk}·{tk}",
                "role": rk, "tier": tk, "en": f"{td}, {rd}",
                "wear": "", "key_color": "",
            })
    return rows


def prompt_of(r):
    bits = [r["en"]]
    if r.get("wear"):
        bits.append(r["wear"])
    return ", ".join(bits) + ". " + STYLE
