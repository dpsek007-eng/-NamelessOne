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
#
# 스타일은 옛 유화가 아니라 **요즘 게임 초상**을 쓴다. 두 가지를 뺐다.
#   · "painterly oil painting, medieval, weathered skin" — 그림이 19세기
#     박물관 초상으로 새니까. 그리고 "weathered skin" 이 얼굴을 전부
#     60대 이상으로 늙혔다.
#   · "muted desaturated colours" — 무채색 톤이 그림만 옛날 것으로 만든다.
# 나이를 명시하지 않으면 SDXL 은 기본으로 20~40대 성인을 그린다. 그래서
# 나이 말을 넣는 대신 노인 표식(NEGATIVE 의 elderly 등)을 금지하는 쪽으로
# 정하고, 캐릭터마다 말에 적힌 「늙음」을 걷어냈다. 이 규칙은 예외가 둘 —
# '셈하던 아이'와 '균열을 들여다본 아이'는 설정이 아이여서 child 를 남긴다.
#
# 두 번째 결정 (2026-09-14, 판정 기준): 「얼굴은 이쁘고 잘생긴 기본값」.
# 게이머가 모으고 싶은 것은 나이 든 인상이 아니라 깨끗한 젊은 얼굴이다.
# 그럼에도 어두운 이야기는 유지되어야 하므로, 캐릭터의 수고·흉터·그을음·
# 기아 흔적은 전부 얼굴에서 거두고 **몸·목·의복·소도구** 단서로 옮긴다.
# 얼굴에는 진지함·슬픔·결의의 **눈빛**만 남긴다. 이건 실루엣 규칙과 같다 —
# 정체성은 얼굴이 아니라 그림자·옷·손이 지고, 얼굴은 보상이다.
STYLE = (
    "head and shoulders portrait of one person facing viewer, "
    "modern fantasy game character art, digital painting, "
    "single soft light from one side, plain dark background, "
    "even smooth skin, calm solemn expression, mouth closed, "
    "beautiful face"
)

NEGATIVE = (
    "photograph, photorealistic, anime, smiling, teeth, "
    "oil painting, modern clothing, text, two people, hands, "
    "cropped head, low quality, deformed, "
    "elderly, old person, wrinkled, weathered skin, grey hair, white hair, "
    "gaunt, sunken cheeks, hollow eyes, unkempt hair, dirty face, scarred face"
)

# --- 역할 5종 — 얼굴에 남은 자세 ------------------------------------------
# 몸이 아니라 얼굴과 어깨만 보이므로, 역할은 시선과 목의 방향으로 나타난다.
# 실루엣 쪽에서 역할이 2.13% 밖에 안 갈린 것이 이 지점에서 만회되어야 한다.
ROLE_FACE = {
    "guard":  ("수호", "calm level gaze straight ahead, steady brow, composed, clean strong jaw"),
    "resist": ("저항", "defiant clear gaze straight on, head lifted, lips pressed firm"),
    "devote": ("헌신", "soft clear eyes lowered, kind composed face, head tilted down"),
    "seek":   ("탐구", "bright attentive eyes looking to one side, thoughtful, fine features"),
    "flee":   ("도피", "wide clear eyes glancing aside, poised, light agile build"),
}

# --- 계층 11종 — 얼굴에 남은 살림 ------------------------------------------
# 계층 표식(관, 두건, 목가리개)은 남기되, 얼굴에 뭍던 그을음·흉터·기아 는
# 걷어냈다. 계층이 아니라 **사람이** 이쁘고 잘생겨야 하기 때문이다.
TIER_FACE = {
    "royal":    ("왕실", "fair unmarked skin, fine circlet, high collar"),
    "noble":    ("귀족", "groomed hair, embroidered collar, handsome well-kept look"),
    "mage":     ("술사", "deep hood shadowing the brow, luminous bright eyes"),
    "clergy":   ("성직", "shaven head, plain grey cowl, calm steady eyes"),
    "clerk":    ("관리", "neat tied hair, steady bookish eyes, plain dark collar"),
    "merchant": ("상인", "bright shrewd eyes, fur trimmed collar, well-fed cheerful face"),
    "artisan":  ("장인", "soot smudged hand, cloth headband, honest bright face"),
    "peasant":  ("농어민", "sun warmed healthy skin, coarse undyed cloth, steady bright eyes"),
    "soldier":  ("병졸", "cropped hair, steady resolute eyes, dented gorget"),
    "servant":  ("하인", "hair under a clean kerchief, modest downcast face, gentle features"),
    "vagrant":  ("유랑", "loose windswept hair, slender fair face, ragged wrapped shoulders"),
}

# --- 이름 있는 23명 --------------------------------------------------------
# data/characters.json 의 visual.silhouette 과 life/death 를 얼굴로 옮긴 것.
# 기계 번역이 아니라 손으로 옮겼다. 얼굴은 몸보다 틀리면 더 눈에 띈다.
#
# 판정 기준대로, 각 인물의 수고·상처·기아는 얼굴을 떠나 몸·목·의복·소도구
# 단서로 갔다. 예: 세렌의 갈라진 손바닥 → 손(프레임 밖) / 목의 천. 대장장이
# 도른의 부러진 코 → 빠짐, 대신 창자루·팔목. 물장수의 마른 입술 → 목의 천·
# 어깨 멜대. 인물이 알아볼 수 없는 수준으로 닮아야 하는 게 아니라, **그
# 소품·그 눈빛이면 누구인지 알 수 있는** 수준이어야 한다.
NAMED = {
    "seren":             "woman, bell ringer, cloth wound around her throat, clear grey eyes, serene beautiful face, neat hair",
    "kabril":            "broad shouldered gatekeeper, neat short beard, calm self-possessed gaze, even handsome features",
    "idel":              "slender young archivist, keen clear eyes, ink on the fingertips at his collar",
    "miro":              "lean youth, hair falling over one eye, quick bright glance aside, ready to run",
    "north_gatekeeper":  "watchman, worn collar of a city guard coat, steady young face, clear eyes",
    "baker_18f":         "baker, flour dusted brow, warm kind eyes, soft handsome face, apron strap at the shoulder",
    "someones_mother":   "woman, hair loose and soft, empty arms as if cradling, sorrow in clear eyes, gentle face",
    "unnamed_000":       "a plain youthful face with no distinguishing marks, staring straight ahead, forgettable",
    "ash_sweeper":       "soot smudged cheek, cloth mask pulled down to the chin, bright calm eyes",
    "counting_child":    "child, smudge of charcoal on a soft cheek, counting under the breath, serious",
    "last_watercarrier": "water carrier, cloth wrapped around the neck, clear bright eyes, yoke at the shoulder",
    "dorn":              "square jawed blacksmith, intense bright eyes, spear haft at the shoulder, thick necked",
    "left_behind":       "young traveller with nothing, empty pack straps on the shoulders, distant clear gaze, fair features",
    "cart_pusher":       "sturdy strong young man leaning forward, jaw set, knit brow of effort, clear eyes",
    "yuan":              "physician with rolled sleeves, keen clear examining eyes, composed mouth, a writing board at the hip",
    # 「긴 장대를 쥔」 이라고 적었더니 장대를 담으려고 카메라가 물러나
    # 8장 전부 반신이 됐다 (얼굴 너비 0.265, 표본 중앙값 0.467). 초점은
    # 눈~입 자리에 거는 것이라 얼굴이 작으면 배경이 뭉개진다. 장대를 뺐다.
    # 두 부대의 소매는 어깨 위에서도 보인다.
    "flagbearer":        "standard bearer, chin lifted, one shoulder in dark cloth and the other pale, young handsome face",
    "name_writer":       "charcoal in one hand, eyes turned to the wall beside him, absorbed, neat features",
    "pathpointer":       "one arm raised out of frame and never lowered, bright resolute eyes, steady expression",
    "rean":              "upright, hands behind the back, unarmed, calm level unafraid gaze, handsome composed face",
    "ledger_keeper":     "clerk, a ledger bound under the arm, steady patient eyes, neat hands",
    "crack_child":       "small child leaning forward, hands behind the back, wide curious eyes",
    "festival_maker":    "arms open, decorative cords on the sleeves, bright open face, gentle warm eyes",
    "alley_filler":      "square built stone worker, one shoulder relaxed, steady patient eyes, dust on the collar",
}

# 글이 성별·나이를 정해 둔 사람. 나머지는 씨앗에 맡긴다.
ERA_WEAR = {"균열기": "faint dust", "붕괴기": "grime at the collar", "종말기": "ash at the sleeve"}


# --- 두상 6 — 초상 부품 (docs/22 「이목구비 8 종」) -------------------------
# 무명 초상의 겉층이다. tools/rig.py 의 HEAD 그룹과 같은 매핑이다 — 계층이
# 머리형을 정한다. 초점과 무관하게 처음부터 보인다. 부품 조립 때 이목구비
# 원형이 눈~입 자리에 겹쳐지므로, 여기 얼굴 특징은 가려져도 무방하다.
HEADS = {
    "bare":     "bare head, plain neat dark hair",
    "hood":     "deep hood shadowing the brow",
    "helmet":   "plain soldier helmet, mail gorget at the chin",
    "hat":      "neat dark hat, collar turned up",
    "kerchief": "clean kerchief tied over the hair",
    "circlet":  "fine circlet, high collar",
}

# --- 이목구비 8 — 초상 부품 (docs/22 「이목구비 8 종」) ----------------------
# 눈매·입매로 정의한 여덟 얼굴 원형. 전부 「보상은 바람직해야 한다」의 깨끗한
# 젊은 얼굴 안에 있고, 얼굴은 역할을 나르지 않는다(실측). 다섯 종의 겉말이
# 역할 눈빛과 겹치는 것은 결합이 아니라 종의 이름이다.
FACES_8 = {
    "guard":  "calm level gaze straight ahead, steady brow, composed, clean strong jaw",
    "resist": "defiant clear gaze straight on, head lifted, lips pressed firm",
    "devote": "soft clear eyes lowered, kind composed face, head tilted down",
    "seek":   "bright attentive eyes looking to one side, thoughtful, fine features",
    "flee":   "wide clear eyes glancing aside, poised, light agile build",
    "deep":   "deep quiet eyes, sorrow held still, solemn calm mouth",
    "clear":  "bright clear eyes, faint gentle curve at the lips, open serene brow",
    "still":  "still composed face, expressionless mouth, quiet distant gaze",
}


def head_rows():
    """두상 6 — 계층이 아니라 머리형이 곧 정체다."""
    return [{"id": f"head_{k}", "kind": "head", "ko": k,
             "role": "", "tier": "", "en": v, "wear": "", "key_color": ""}
            for k, v in HEADS.items()]


def face_rows():
    """이목구비 8 — 눈매·입매 원형."""
    return [{"id": f"face_{k}", "kind": "face", "ko": k,
             "role": "", "tier": "", "en": v, "wear": "", "key_color": ""}
            for k, v in FACES_8.items()]


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
