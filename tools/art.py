# -*- coding: utf-8 -*-
"""이렘 아트 생성기 — 잔상 스프라이트와 지형 타일.

  실루엣은 설정이다. 계층이 옷을 정하고, 생업이 손에 든 것을 정하고,
  성향이 자세를 정한다. 색은 잔상이 남긴 유일한 온기다.

  출력: 48×64 픽셀 캐릭터, 32×32 지형 타일. 전부 PNG data URI.
"""
from PIL import Image, ImageDraw, ImageFilter
import base64, io, math

W, H = 48, 64
TS = 32                                   # 타일 한 변

# ── 색 ────────────────────────────────────────────────────────────
def hx(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
def mix(a, b, t):
    return tuple(round(a[i] + (b[i]-a[i])*t) for i in range(3))
def dark(c, t=0.35): return mix(c, (12, 14, 17), t)
def lite(c, t=0.30): return mix(c, (255, 250, 238), t)
def A(c, a=255):     return (c[0], c[1], c[2], a)

INK   = (18, 20, 24)
INK2  = (34, 38, 44)

# 계층별 의복 (본색, 장식색)
CLS_PAL = {
    "왕실":  ("#5B3B6E", "#C9A227"), "귀족":  ("#6E3B45", "#C9A227"),
    "술사":  ("#2F4E6E", "#7FB2D9"), "성직":  ("#DCD5C2", "#B8894A"),
    "관리":  ("#3E4A5B", "#8A93A0"), "상인":  ("#7A5A2E", "#C9A227"),
    "장인":  ("#6B4A2F", "#A07A4A"), "농어민": ("#5E6B4A", "#8A9464"),
    "병졸":  ("#48505A", "#9AA3AC"), "하인":  ("#5B5348", "#8A8071"),
    "유랑":  ("#4E4A46", "#7A6E5F"),
}
SKIN = ["#E8C39E", "#DCAE85", "#C08E62", "#9A6B47", "#7A5238", "#F0D5B8"]
HAIR = ["#251E1B", "#3A2A20", "#553A22", "#7A5A32", "#9C8A6A", "#C8BCA6", "#43363F"]

def seed_of(s):
    h = 2166136261
    for ch in s:
        h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
    return h

class R:
    """xorshift32 — id 만 같으면 어디서 돌려도 같은 얼굴이 나온다"""
    def __init__(self, s): self.s = (s | 1) & 0xFFFFFFFF
    def n(self):
        x = self.s
        x ^= (x << 13) & 0xFFFFFFFF; x ^= x >> 17; x ^= (x << 5) & 0xFFFFFFFF
        self.s = x; return x
    def pick(self, l): return l[self.n() % len(l)]
    def r(self, a, b): return a + self.n() % (b - a + 1)

# ── 체형 ──────────────────────────────────────────────────────────
#   head_cy, head_r, sh_y, sh_w, waist_y, feet
BUILD = {
    "child": dict(hcy=27, hr=5.0, shy=34, shw=6.0, wy=45, ft=60),
    "thin":  dict(hcy=16, hr=5.4, shy=25, shw=7.0, wy=41, ft=60),
    "norm":  dict(hcy=15, hr=6.0, shy=24, shw=8.5, wy=41, ft=60),
    "bulk":  dict(hcy=15, hr=6.4, shy=24, shw=11.0, wy=42, ft=60),
}
HEM = {"long": 58, "hood": 56, "cape": 51, "coat": 47, "armor": 42,
       "tunic": 41, "apron": 45, "rag": 45}
ROBE = {"왕실": "long", "귀족": "cape", "술사": "hood", "성직": "hood",
        "관리": "coat", "상인": "coat", "장인": "apron", "농어민": "tunic",
        "병졸": "armor", "하인": "tunic", "유랑": "rag"}

# 캐릭터별 자세 — data/characters.json 의 silhouette 을 그대로 옮긴 것
POSE = {
    "seren":            dict(build="thin", stoop=3, arms="wrap",   prop="rope"),
    "kabril":           dict(build="bulk", stoop=0, arms="guard",  prop="bar"),
    "idel":             dict(build="thin", stoop=1, arms="carry",  prop="papers"),
    "miro":             dict(build="thin", stoop=0, arms="lean",   prop=None, tilt=1),
    "north_gatekeeper": dict(build="norm", stoop=0, arms="out",    prop="spear"),
    "baker_18f":        dict(build="norm", stoop=1, arms="fore",   prop="loaf"),
    "someones_mother":  dict(build="thin", stoop=4, arms="cradle", prop=None),
    "unnamed_000":      dict(build="norm", stoop=0, arms="down",   prop=None, faceless=True),
    "ash_sweeper":      dict(build="norm", stoop=2, arms="hold",   prop="broom"),
    "counting_child":   dict(build="child", stoop=0, arms="carry", prop="coal"),
    "last_watercarrier":dict(build="norm", stoop=1, arms="yoke",   prop="yoke"),
    "dorn":             dict(build="bulk", stoop=0, arms="shoulder", prop="spear"),
    "left_behind":      dict(build="norm", stoop=2, arms="down",   prop="pack"),
    "cart_pusher":      dict(build="norm", stoop=3, arms="fore",   prop=None),
    "yuan":             dict(build="norm", stoop=0, arms="carry",  prop="tablet", sleeve=True),
    "flagbearer":       dict(build="norm", stoop=0, arms="pole",   prop="flag"),
    "name_writer":      dict(build="thin", stoop=1, arms="write",  prop="coal"),
    "pathpointer":      dict(build="norm", stoop=0, arms="point",  prop=None),
    "rean":             dict(build="norm", stoop=0, arms="behind", prop=None),
    "ledger_keeper":    dict(build="thin", stoop=3, arms="carry",  prop="book"),
    "crack_child":      dict(build="child", stoop=3, arms="behind", prop=None),
    "festival_maker":   dict(build="norm", stoop=0, arms="spread", prop="ribbon"),
    "alley_filler":     dict(build="bulk", stoop=1, arms="down",   prop=None, slump=True),
}
# 성향별 기본 자세 (POSE 에 없는 잔상용)
ROLE_ARMS = {"수호": "guard", "저항": "shoulder", "헌신": "cradle",
             "탐구": "carry", "도피": "lean", "미상": "down"}
# 생업 소품
TRADE_PROP = {
    # 47개 생업 전부. 손이 비어 있으면 무엇을 하던 사람인지 알 수 없다.
    "종탑": "rope",     "대장간": "hammer",  "물장수": "yoke",    "서고": "book",
    "문지기": "bar",    "담장": "chisel",    "등대": "lamp",      "망루": "lamp",
    "목공": "plane",    "악기": "lute",      "약방": "herb",      "전령": "letter",
    "채석": "chisel",   "화덕": "loaf",      "유리 세공": "flask", "밭": "hoe",
    "재봉": "spool",    "마구간": "rein",    "부엌": "ladle",     "무두질": "hide",
    "어망": "net",      "양조": "jar",       "방직": "spool",     "도공": "bowl",
    "숯막": "coal",     "산파": "cloth",     "장의": "cloth",     "마방": "wheel",
    "양치기": "crook",  "벌치기": "jar",     "궁정": "seal",      "영주": "seal",
    "기사": "sword",    "사제": "book",      "징세": "book",      "상단": "chest",
    "세탁": "cloth",    "유랑": "bundle",    "광부": "pick",      "사냥": "bow",
    "마법사": "staff",  "정령술사": "bowl",  "점성": "rod",       "연금": "flask",
    "성녀": "relic",    "성기사": "sword",   "사경": "book",
}


def _tri(d, pts, fill, ol):
    d.polygon(pts, fill=A(fill), outline=A(ol))

def arm(d, x0, y0, x1, y1, cloth, skin, sleeve=0.55, w=4.6):
    """어깨→손. 위쪽은 소매, 아래쪽은 맨살. 몸통 밖으로 나와야 팔로 보인다."""
    mx, my = x0 + (x1-x0)*sleeve, y0 + (y1-y0)*sleeve
    limb(d, x0, y0, mx, my, w, cloth, INK)
    limb(d, mx, my, x1, y1, w*0.78, skin, INK)


def limb(d, x0, y0, x1, y1, w, col, ol):
    """두 점을 잇는 두께 있는 팔다리"""
    dx, dy = x1-x0, y1-y0
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy/L*w/2, dx/L*w/2
    d.polygon([(x0+nx, y0+ny), (x1+nx, y1+ny), (x1-nx, y1-ny), (x0-nx, y0-ny)],
              fill=A(col), outline=A(ol))


def sprite(cid, cls, trade, role, key_color, rarity=3):
    p = POSE.get(cid, {})
    rr = R(seed_of(cid))
    build = p.get("build", "norm")
    B = BUILD[build]
    stoop = p.get("stoop", 0)
    arms = p.get("arms") or ROLE_ARMS.get(role, "down")
    prop = p.get("prop", TRADE_PROP.get(trade))
    if "prop" not in p and prop is None:
        prop = TRADE_PROP.get(trade)

    robe = ROBE.get(cls, "tunic")
    base, trim = (hx(c) for c in CLS_PAL.get(cls, CLS_PAL["하인"]))
    def jog(c, k=26):
        return tuple(max(8, min(247, c[i] + rr.r(-k, k) - (0 if i == 1 else rr.r(0, 6))))
                     for i in range(3))
    base, trim = jog(base), jog(trim, 20)
    acc  = hx(key_color)
    skin = hx(rr.pick(SKIN))
    hair = hx(rr.pick(HAIR))
    hem  = HEM[robe]

    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d  = ImageDraw.Draw(im)

    cx   = 24
    hcy  = B["hcy"] + stoop
    hcx  = cx + stoop * 0.9
    shy  = B["shy"] + stoop * 0.5
    shw  = B["shw"]
    wy   = B["wy"]
    ft   = B["ft"]
    hem  = min(hem, ft - 1)
    if build == "child": hem = min(hem, 50)

    lean = p.get("tilt", 0) * 2
    sl   = 1 if p.get("slump") else 0

    # ── 다리 ──
    if hem < ft - 3:
        lc = dark(mix(base, hx(rr.pick(["#4A3A2A", "#3A3E48", "#4E4438", "#2E3630"])), .5), 0.30)
        limb(d, cx-3, wy, cx-4, ft, 4.2, lc, INK)
        limb(d, cx+3, wy, cx+4, ft, 4.2, lc, INK)
    # 발
    boot = dark(mix(trim, hx("#4A3A2A"), .55), 0.35)
    d.rectangle([cx-7, ft-2, cx-1, ft+1], fill=A(boot), outline=A(INK))
    d.rectangle([cx+1, ft-2, cx+7, ft+1], fill=A(boot), outline=A(INK))

    # ── 뒷팔 ──
    armc = lite(base, 0.10)
    ax0, ay0 = cx - shw - 1, shy + 2 + sl
    back = {
        "out":     (cx-shw-8, shy+2), "point": (cx-shw-3, shy+8),
        "spread":  (cx-shw-9, shy-3), "fore":  (cx-shw-2, shy+9),
        "yoke":    (cx-shw-6, shy-1), "behind": (cx-shw-3, shy+12),
        "cradle":  (cx-shw-4, shy+11), "guard": (cx-shw-5, shy+13),
        "shoulder":(cx-shw-5, shy+13), "carry": (cx-shw-5, shy+12),
        "wrap":    (cx-shw-5, shy+11), "hold":  (cx-shw-6, shy+7),
        "pole":    (cx-shw-5, shy+3),  "write": (cx-shw-6, shy+10),
        "lean":    (cx-shw-6, shy+10), "down":  (cx-shw-4, shy+14),
    }.get(arms, (cx-shw-4, shy+14))
    arm(d, ax0, ay0, back[0], back[1], dark(armc, .28), dark(skin, .18))

    # ── 몸통 ──
    hw = {"long": 10, "hood": 10.5, "cape": 11, "coat": 9.5, "armor": 9,
          "tunic": 8.5, "apron": 9, "rag": 9.5}[robe]
    if build == "child": hw -= 2
    if build == "bulk":  hw += 1.5
    body = [(hcx-shw, shy), (hcx+shw, shy), (cx+shw-1+lean, wy-3),
            (cx+hw+lean, hem), (cx-hw+lean, hem), (cx-shw+1+lean, wy-3)]
    if robe == "rag":
        body = [(hcx-shw, shy), (hcx+shw, shy), (cx+shw, wy-3),
                (cx+hw+3, hem-1), (cx+hw-3, hem-5), (cx+1, hem+2),
                (cx-hw+2, hem-4), (cx-hw-2, hem)]
    d.polygon(body, fill=A(base), outline=A(INK))
    # 명암 — 왼쪽에서 빛이 온다
    d.polygon([(cx+2, shy+1), (hcx+shw-1, shy+1), (cx+shw-2+lean, wy-3),
               (cx+hw-1+lean, hem-1), (cx+2, hem-1)], fill=A(dark(base, .22)))

    # 의복 장식
    if robe == "cape":
        d.polygon([(hcx-shw-1, shy-1), (hcx+shw+1, shy-1), (hcx+shw+3, shy+13),
                   (hcx-shw-3, shy+13)], fill=A(trim), outline=A(INK))
    if robe == "armor":
        d.rectangle([cx-shw+1, shy+3, cx+shw-1, shy+5], fill=A(trim))
        d.rectangle([cx-shw+1, shy+8, cx+shw-1, shy+10], fill=A(trim))
    if robe == "coat":
        d.line([(cx, shy+2), (cx, hem-1)], fill=A(dark(base, .5)))
        d.rectangle([cx-1, shy+7, cx+1, shy+9], fill=A(trim))
    if robe == "apron":
        ap = lite(trim, .42)
        d.polygon([(cx-4, shy+6), (cx+4, shy+6), (cx+6, hem-2), (cx-6, hem-2)],
                  fill=A(ap), outline=A(dark(trim, .35)))
        d.line([(cx-4, shy+6), (cx-2, shy+1)], fill=A(dark(ap, .2)))
        d.line([(cx+4, shy+6), (cx+2, shy+1)], fill=A(dark(ap, .2)))
    if robe in ("hood", "long"):
        d.rectangle([cx-hw+lean, hem-4, cx+hw+lean, hem-2], fill=A(trim))

    # 강조색 — 이 잔상만의 색. 허리띠나 어깨끈으로 남는다
    if robe in ("hood", "long", "cape"):
        d.line([(hcx-shw+2, shy+3), (cx+hw-3, wy-1)], fill=A(acc), width=2)
    else:
        d.rectangle([cx-hw+lean+1, wy-3, cx+hw+lean-1, wy-2], fill=A(acc))
        d.rectangle([cx-2+lean, wy-4, cx+2+lean, wy-1], fill=A(dark(acc, .25)), outline=A(INK))
    if p.get("sleeve"):
        d.rectangle([cx-shw, shy+9, cx-shw+4, shy+12], fill=A(lite(skin, .1)))

    # ── 앞팔 ──
    fx0, fy0 = cx + shw + 1, shy + 2
    front = {
        "out":     (cx+shw+10, shy+1), "point": (cx+shw+11, shy+2),
        "spread":  (cx+shw+9, shy-4),  "fore":  (cx+shw+8, shy+7),
        "yoke":    (cx+shw+6, shy-1),  "behind": (cx+shw-2, shy+12),
        "cradle":  (cx+shw+2, shy+12), "guard": (cx+shw+5, shy+9),
        "shoulder":(cx+shw+2, shy-4),  "carry": (cx+shw+4, shy+11),
        "wrap":    (cx+shw+1, shy+12), "hold":  (cx+shw+6, shy+8),
        "pole":    (cx+shw+2, shy+1),  "write": (cx+shw+6, shy-2),
        "lean":    (cx+shw+5, shy+9),  "down":  (cx+shw+4, shy+14),
    }.get(arms, (cx+shw+4, shy+14))
    arm(d, fx0, fy0, front[0], front[1], armc, skin)
    hand = front
    d.ellipse([hand[0]-2.4, hand[1]-2.4, hand[0]+2.4, hand[1]+2.4], fill=A(skin), outline=A(INK))
    if arms == "wrap":       # 천을 감은 손
        d.ellipse([hand[0]-3, hand[1]-3, hand[0]+3, hand[1]+3],
                  fill=A(lite(trim, .5)), outline=A(INK))
        d.ellipse([back[0]-3, back[1]-3, back[0]+3, back[1]+3],
                  fill=A(lite(trim, .5)), outline=A(INK))

    # ── 소품 ──
    hxp, hyp = hand
    wood, iron, paper = hx("#6B4A2C"), hx("#8A929C"), hx("#DCD5C2")
    if prop == "rope":
        d.line([(hxp, hyp-2), (hxp+1, 8)], fill=A(hx("#B9A377")), width=2)
        d.line([(hxp+1, 8), (hxp-6, 6)], fill=A(hx("#B9A377")), width=2)
    elif prop == "bar":
        limb(d, hxp-1, hyp+6, hxp+3, hyp-14, 3.4, wood, INK)
        d.rectangle([hxp-1, hyp-13, hxp+4, hyp-10], fill=A(iron), outline=A(INK))
    elif prop == "spear":
        limb(d, hxp-2, hyp+12, hxp+2, hyp-18, 2.6, wood, INK)
        _tri(d, [(hxp+2, hyp-18), (hxp+5, hyp-12), (hxp-1, hyp-12)], iron, INK)
    elif prop == "papers":
        d.rectangle([hxp-5, hyp-6, hxp+4, hyp+2], fill=A(paper), outline=A(INK))
        d.line([(hxp-3, hyp-4), (hxp+2, hyp-4)], fill=A(hx("#9A9384")))
        d.line([(hxp-3, hyp-1), (hxp+2, hyp-1)], fill=A(hx("#9A9384")))
    elif prop in ("book", "tablet", "letter"):
        d.rectangle([hxp-4, hyp-5, hxp+4, hyp+3], fill=A(hx("#7A4A3A") if prop=="book" else paper),
                    outline=A(INK))
        d.rectangle([hxp-4, hyp-5, hxp-2, hyp+3], fill=A(dark(hx("#7A4A3A"), .3)))
    elif prop == "broom":
        limb(d, hxp-12, hyp+6, hxp+11, hyp-5, 2.4, wood, INK)
        _tri(d, [(hxp+11, hyp-6), (hxp+16, hyp-11), (hxp+15, hyp-1)], hx("#9A8A5E"), INK)
    elif prop == "yoke":
        limb(d, cx-13, shy-3, cx+13, shy-3, 2.6, wood, INK)
        for sx in (cx-13, cx+13):
            d.line([(sx, shy-2), (sx, shy+5)], fill=A(hx("#8A7A5E")))
            d.rectangle([sx-4, shy+5, sx+4, shy+12], fill=A(hx("#6E5A3E")), outline=A(INK))
            d.rectangle([sx-4, shy+6, sx+4, shy+7], fill=A(hx("#4E6E7A")))
    elif prop == "hammer":
        limb(d, hxp, hyp+8, hxp+1, hyp-9, 2.6, wood, INK)
        d.rectangle([hxp-4, hyp-13, hxp+6, hyp-9], fill=A(iron), outline=A(INK))
    elif prop == "loaf":
        d.ellipse([hxp-5, hyp-4, hxp+5, hyp+3], fill=A(hx("#C08A4E")), outline=A(INK))
        d.line([(hxp-2, hyp-2), (hxp+2, hyp)], fill=A(hx("#8A5E2E")))
    elif prop == "coal":
        d.ellipse([hxp-2, hyp-2, hxp+2, hyp+2], fill=A(hx("#2A2622")), outline=A(INK))
    elif prop == "lamp":
        d.line([(hxp, hyp), (hxp, hyp+4)], fill=A(iron))
        d.rectangle([hxp-3, hyp+4, hxp+3, hyp+10], fill=A(hx("#D9A94E")), outline=A(INK))
    elif prop == "chisel":
        limb(d, hxp, hyp-1, hxp+6, hyp-7, 2.4, iron, INK)
    elif prop == "plane":
        d.rectangle([hxp-5, hyp-3, hxp+5, hyp+2], fill=A(wood), outline=A(INK))
    elif prop == "herb":
        d.line([(hxp, hyp), (hxp+2, hyp-7)], fill=A(hx("#5E7A4A")), width=2)
        d.ellipse([hxp, hyp-9, hxp+5, hyp-5], fill=A(hx("#6E8A54")))
    elif prop == "lute":
        d.ellipse([hxp-6, hyp-3, hxp+3, hyp+7], fill=A(hx("#8A5E32")), outline=A(INK))
        limb(d, hxp+2, hyp+1, hxp+10, hyp-8, 2.2, wood, INK)
    elif prop == "pack":
        d.rectangle([cx-shw-3, shy+3, cx-shw+3, shy+14], fill=A(hx("#5E4E3A")), outline=A(INK))
    elif prop == "ribbon":
        for k, sx in ((0, cx-shw-8), (1, cx+shw+8)):
            d.line([(sx, shy-4), (sx+(2 if k else -2), shy+6)], fill=A(acc), width=2)
    elif prop == "flag":
        limb(d, cx+2, 62, cx+2, 4, 2.4, wood, INK)
        d.polygon([(cx+3, 5), (cx+16, 8), (cx+15, 20), (cx+3, 18)],
                  fill=A(acc), outline=A(INK))
        d.line([(cx+5, 9), (cx+13, 11)], fill=A(dark(acc, .35)))

    # ── 머리 ──
    hr = B["hr"]
    d.ellipse([hcx-hr, hcy-hr-1, hcx+hr, hcy+hr+1], fill=A(skin), outline=A(INK))
    # 목
    d.rectangle([hcx-2, hcy+hr-1, hcx+2, shy+1], fill=A(dark(skin, .18)))
    style = rr.n() % 4
    if robe == "hood":
        d.polygon([(hcx-hr-2, hcy+hr), (hcx-hr-1, hcy-hr-1), (hcx, hcy-hr-3),
                   (hcx+hr+1, hcy-hr-1), (hcx+hr+2, hcy+hr)],
                  fill=A(base), outline=A(INK))
        d.polygon([(hcx-hr+1, hcy+hr-1), (hcx-hr+1, hcy-2), (hcx+hr-1, hcy-2),
                   (hcx+hr-1, hcy+hr-1)], fill=A(dark(base, .55)))
        d.ellipse([hcx-hr+1, hcy-1, hcx+hr-1, hcy+hr], fill=A(skin))
    elif style == 0:                                   # 짧은 머리
        d.polygon([(hcx-hr, hcy-1), (hcx-hr+1, hcy-hr-1), (hcx+hr-1, hcy-hr-1),
                   (hcx+hr, hcy-1), (hcx+hr-2, hcy-3), (hcx-hr+2, hcy-3)],
                  fill=A(hair), outline=A(dark(hair, .4)))
    elif style == 1:                                   # 긴 머리
        d.polygon([(hcx-hr-1, hcy+hr+4), (hcx-hr-1, hcy-hr), (hcx, hcy-hr-2),
                   (hcx+hr+1, hcy-hr), (hcx+hr+1, hcy+hr+4), (hcx+hr-1, hcy+hr+2),
                   (hcx+hr-2, hcy-1), (hcx-hr+2, hcy-1), (hcx-hr+1, hcy+hr+2)],
                  fill=A(hair), outline=A(dark(hair, .4)))
    elif style == 2:                                   # 묶은 머리
        d.polygon([(hcx-hr, hcy-1), (hcx-hr+1, hcy-hr-1), (hcx+hr-1, hcy-hr-1),
                   (hcx+hr, hcy-1), (hcx+hr-2, hcy-3), (hcx-hr+2, hcy-3)],
                  fill=A(hair), outline=A(dark(hair, .4)))
        d.ellipse([hcx-hr-4, hcy-3, hcx-hr, hcy+2], fill=A(hair), outline=A(dark(hair, .4)))
    else:                                              # 두건
        d.polygon([(hcx-hr-1, hcy-1), (hcx-hr, hcy-hr-1), (hcx+hr, hcy-hr-1),
                   (hcx+hr+1, hcy-1)], fill=A(trim), outline=A(INK))
        d.polygon([(hcx-hr-1, hcy-1), (hcx-hr-4, hcy+4), (hcx-hr, hcy+1)],
                  fill=A(dark(trim, .25)))

    # 얼굴
    if not p.get("faceless"):
        ey = hcy + (1 if build == "child" else 0)
        d.point((hcx-2, ey), fill=A(INK)); d.point((hcx-2, ey+1), fill=A(INK))
        d.point((hcx+2, ey), fill=A(INK)); d.point((hcx+2, ey+1), fill=A(INK))
        if role == "저항":  d.line([(hcx-3, ey-2), (hcx-1, ey-1)], fill=A(dark(hair, .2)))
        if stoop >= 3:     d.line([(hcx-2, ey+4), (hcx+2, ey+4)], fill=A(dark(skin, .45)))
    else:
        d.rectangle([hcx-hr+1, hcy-2, hcx+hr-1, hcy+2], fill=A(dark(skin, .55)))

    # 선명도 — 낮을수록 아래가 흐려진다
    if rarity <= 2:
        px = im.load()
        for y in range(H):
            f = max(0.0, min(1.0, (y - 34) / 26.0))
            if f <= 0: continue
            for x in range(W):
                r, g, b, a = px[x, y]
                if a: px[x, y] = (r, g, b, int(a * (1 - f * 0.55)))
    return im


# ── 수호자 · 피난민 ────────────────────────────────────────────────
def foe_sprite(kind):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d  = ImageDraw.Draw(im)
    cx = 24
    if kind == "재":                      # 두껍고 느리다. 재가 굳어 사람 모양이 된 것
        body, eye = hx("#787069"), hx("#E8843A")
        rr = R(seed_of("ash"))
        d.polygon([(cx-13, 24), (cx-9, 20), (cx+9, 20), (cx+13, 24),
                   (cx+11, 44), (cx+14, 61), (cx-14, 61), (cx-11, 44)],
                  fill=A(body), outline=A(INK))
        d.polygon([(cx+1, 21), (cx+9, 20), (cx+13, 24), (cx+11, 44), (cx+14, 60), (cx+1, 60)],
                  fill=A(dark(body, .28)))
        limb(d, cx-13, 26, cx-18, 47, 7, dark(body, .12), INK)
        limb(d, cx+13, 26, cx+18, 47, 7, dark(body, .12), INK)
        d.ellipse([cx-8, 6, cx+8, 23], fill=A(body), outline=A(INK))
        d.polygon([(cx-8, 14), (cx-5, 5), (cx+5, 5), (cx+8, 14)], fill=A(dark(body, .3)))
        for _ in range(7):                        # 갈라진 틈의 불씨
            x, y = rr.r(cx-11, cx+11), rr.r(26, 56)
            d.line([(x, y), (x + rr.r(-3, 3), y + rr.r(2, 5))], fill=A(hx("#C4531F"), 210))
        for _ in range(30):
            d.point((rr.r(cx-13, cx+13), rr.r(21, 60)), fill=A(lite(body, .3), 90))
    elif kind == "잔해":                  # 얇지만 아프다. 부서진 것들이 모여 활이 되었다
        body, eye = hx("#5A5F66"), hx("#C9A227")
        d.polygon([(cx-7, 24), (cx+7, 24), (cx+5, 42), (cx+7, 60), (cx-7, 60), (cx-5, 42)],
                  fill=A(body), outline=A(INK))
        limb(d, cx-7, 26, cx-14, 20, 4, dark(body, .15), INK)
        limb(d, cx+7, 26, cx+13, 34, 4, dark(body, .15), INK)
        d.arc([cx-19, 8, cx-5, 40], 250, 110, fill=A(hx("#7A6A52")), width=2)
        d.line([(cx-16, 12), (cx-16, 36)], fill=A(hx("#9A8A6E")))
        d.ellipse([cx-5, 12, cx+5, 25], fill=A(body), outline=A(INK))
        for k in range(3):
            d.line([(cx-4+k*4, 11), (cx-6+k*5, 4)], fill=A(dark(body, .1)), width=2)
    else:                                 # 그림자 — 빠르게 파고든다
        body, eye = hx("#2A2E36"), hx("#7FB2D9")
        d.polygon([(cx-9, 22), (cx+9, 22), (cx+7, 40), (cx+11, 58), (cx+2, 54),
                   (cx-3, 60), (cx-10, 52), (cx-7, 40)], fill=A(body), outline=A(INK))
        limb(d, cx-9, 25, cx-15, 38, 4.5, body, INK)
        limb(d, cx+9, 25, cx+15, 30, 4.5, body, INK)
        d.ellipse([cx-6, 9, cx+6, 24], fill=A(body), outline=A(INK))
        for k in range(4):
            d.line([(cx-6+k*4, 10), (cx-9+k*6, 2)], fill=A(body), width=2)
    # 눈 — 수호자는 눈만 남았다
    ey = 18 if kind != "재" else 20
    d.rectangle([cx-4, ey, cx-2, ey+2], fill=A(eye))
    d.rectangle([cx+2, ey, cx+4, ey+2], fill=A(eye))
    return im

def refugee_sprite(i):
    rr = R(seed_of("ref%d" % i))
    cls = rr.pick(["농어민", "하인", "장인", "유랑"])
    return sprite("ref%d" % i, cls, "없음", "도피", rr.pick(["#7A7168", "#8A8071", "#6E7A5E"]), 2)


# ── 지형 타일 ──────────────────────────────────────────────────────
GROUND = hx("#3A3630")

def _noise(d, rr, x0, y0, x1, y1, col, n, a=70, under=None):
    """반투명 점은 PNG 에 구멍을 낸다. 미리 섞어서 불투명하게 찍는다."""
    base = under or GROUND
    c = A(mix(base, col, a / 255.0))
    for _ in range(n):
        d.point((rr.r(x0, x1), rr.r(y0, y1)), fill=c)

def tile(ch, v=0):
    rr = R(seed_of(ch + "#" + str(v)))
    im = Image.new("RGBA", (TS, TS), (0, 0, 0, 0))
    d  = ImageDraw.Draw(im, "RGBA")
    if ch == ".":                                  # 돌바닥 — 판석
        d.rectangle([0, 0, TS, TS], fill=A(GROUND))
        seam = dark(GROUND, .45)
        rows = [(0, rr.r(11, 15)), (rr.r(11, 15), TS)]
        off = 0
        for (y0, y1) in [(0, rr.r(12, 16))]:
            pass
        cut = rr.r(12, 17)
        bands = [(0, cut), (cut, TS)]
        for bi, (y0, y1) in enumerate(bands):
            xs = [0] + sorted({rr.r(7, TS-7) for _ in range(rr.r(1, 2))}) + [TS]
            for k in range(len(xs)-1):
                sl = mix(GROUND, lite(GROUND, .5) if rr.n() % 2 else dark(GROUND, .35),
                         rr.r(4, 16) / 100.0)
                d.rectangle([xs[k], y0, xs[k+1]-1, y1-1], fill=A(sl))
                d.line([(xs[k], y0), (xs[k], y1-1)], fill=A(seam))
            d.line([(0, y1-1), (TS, y1-1)], fill=A(seam))
        d.line([(0, 0), (TS, 0)], fill=A(seam))
        _noise(d, rr, 0, 0, TS-1, TS-1, lite(GROUND, .45), 26, 46)
        _noise(d, rr, 0, 0, TS-1, TS-1, dark(GROUND, .5), 30, 60)
        # 흩어진 것들 — 자갈, 재, 이끼. 바닥이 비어 보이지 않게
        deco = v % 5
        if deco == 1:
            for _ in range(rr.r(3, 6)):
                x, y = rr.r(2, TS-4), rr.r(2, TS-4)
                d.rectangle([x, y, x+rr.r(1, 2), y+1], fill=A(lite(GROUND, .28)))
        elif deco == 2:
            x, y = rr.r(5, TS-9), rr.r(6, TS-8)
            d.ellipse([x, y, x+rr.r(5, 8), y+rr.r(3, 5)], fill=A(mix(GROUND, hx("#5A5A48"), .5)))
        elif deco == 3:
            x, y = rr.r(3, TS-7), rr.r(3, TS-7)
            d.line([(x, y), (x+rr.r(3, 6), y+rr.r(-3, 3))], fill=A(dark(GROUND, .55)))
        elif deco == 4:
            for _ in range(rr.r(6, 12)):
                d.point((rr.r(0, TS-1), rr.r(0, TS-1)), fill=A(mix(GROUND, hx("#7A7060"), .45)))
    elif ch == "#":                                # 벽 — 지날 수 없다. 두껍게 보여야 한다
        w = hx("#4A443C")
        mor = hx("#171614")
        d.rectangle([0, 0, TS, TS], fill=A(mor))
        for row in range(4):
            y = row * 8
            off = 0 if row % 2 else -8
            for k in range(-1, 3):
                x = off + k*16
                b = mix(w, lite(w, .5) if rr.n() % 2 else dark(w, .4), rr.r(3, 15)/100.0)
                d.rectangle([x+1, y+1, x+14, y+6], fill=A(b))
                d.line([(x+1, y+1), (x+14, y+1)], fill=A(lite(b, .3)))
                d.line([(x+1, y+6), (x+14, y+6)], fill=A(dark(b, .45)))
        _noise(d, rr, 0, 0, TS-1, TS-1, dark(w, .5), 34, 110, under=w)
        d.rectangle([0, 0, TS-1, 1], fill=A(lite(w, .34)))      # 위에서 빛을 받는다
        d.rectangle([0, TS-2, TS-1, TS-1], fill=A(hx("#0C0C0B")))
    elif ch == ":":                                # 잔해 — 무너진 것이 쌓여 있다
        d.rectangle([0, 0, TS, TS], fill=A(GROUND))
        _noise(d, rr, 0, 0, TS-1, TS-1, dark(GROUND, .45), 40, 70)
        r = hx("#635B51")
        chunks = []
        for _ in range(7):
            w = rr.r(6, 12); hh = rr.r(4, 8)
            chunks.append((rr.r(0, TS-w-1), rr.r(2, TS-hh-2), w, hh))
        chunks.sort(key=lambda c: c[1])
        for (x, y, w, hh) in chunks:
            d.ellipse([x+1, y+hh-1, x+w+1, y+hh+2], fill=A(dark(GROUND, .55)))   # 그늘
            c = mix(r, lite(r, .5) if rr.n() % 2 else dark(r, .4), rr.r(5, 22)/100.0)
            d.polygon([(x, y+hh), (x+1, y+2), (x+w//2, y), (x+w, y+3), (x+w-1, y+hh)],
                      fill=A(c), outline=A(dark(c, .55)))
            d.line([(x+2, y+hh-1), (x+w//2, y+1)], fill=A(lite(c, .34)))
        for _ in range(10):                                                      # 부스러기
            x, y = rr.r(1, TS-3), rr.r(1, TS-3)
            d.rectangle([x, y, x+1, y+1], fill=A(dark(r, .3)))
    elif ch == "~":                                # 균열 — 땅이 갈라진 자리
        d.rectangle([0, 0, TS, TS], fill=A(GROUND))
        _noise(d, rr, 0, 0, TS-1, TS-1, dark(GROUND, .5), 30, 70)
        top, bot = [], []
        xs = [0, 5, 10, 16, 22, 27, TS]
        for k, x in enumerate(xs):
            edge = (k == 0 or k == len(xs)-1)
            cy0 = 16 if edge else 16 + rr.r(-5, 5)      # 양끝은 가운데에 물린다
            hw = 2 if edge else rr.r(3, 6)
            top.append((x, cy0 - hw)); bot.append((x, cy0 + hw))
        poly = top + bot[::-1]
        d.polygon(poly, fill=A(mix(GROUND, hx("#5A2A18"), .75)))
        inner = [(px, py+2) for px, py in top] + [(px, py-2) for px, py in bot[::-1]]
        d.polygon(inner, fill=A(hx("#120C0A")))
        for k in range(0, len(top)-1):
            if rr.n() % 3: continue
            px, py = top[k]
            d.line([(px, py+2), (px + rr.r(-2, 2), py+5)], fill=A(hx("#C4531F")))
        for _ in range(4):                                  # 아직 식지 않은 자리
            k = rr.r(0, len(top)-1)
            px = top[k][0]
            d.point((px, (top[k][1]+bot[k][1])//2), fill=A(hx("#E8963A")))
    elif ch == "_":                                # 배수로 — 좁고 낮은 물길
        d.rectangle([0, 0, TS, TS], fill=A(GROUND))
        _noise(d, rr, 0, 0, TS-1, TS-1, dark(GROUND, .5), 24, 60)
        d.rectangle([0, 7, TS, 24], fill=A(dark(GROUND, .55)))          # 파인 자리
        d.line([(0, 7), (TS, 7)], fill=A(lite(GROUND, .3)))
        d.line([(0, 24), (TS, 24)], fill=A(lite(GROUND, .18)))
        wat = hx("#2E4250")
        d.rectangle([0, 11, TS, 21], fill=A(wat))
        for _ in range(3):
            y = rr.r(12, 20); x = rr.r(0, TS-10)
            d.line([(x, y), (x+8, y)], fill=A(lite(wat, .28)))
        d.line([(0, 11), (TS, 11)], fill=A(dark(wat, .35)))
    elif ch == "^":                                # 높은 곳
        s = hx("#6E645A")
        d.rectangle([0, 0, TS, TS], fill=A(GROUND))
        d.rectangle([0, TS-7, TS, TS], fill=A(dark(s, .48)))       # 아래 단
        d.line([(0, TS-7), (TS, TS-7)], fill=A(lite(s, .15)))
        d.rectangle([0, 5, TS, TS-7], fill=A(dark(s, .22)))        # 가운데 단
        d.line([(0, 5), (TS, 5)], fill=A(lite(s, .2)))
        d.rectangle([0, 0, TS, 5], fill=A(s))                      # 윗면
        d.line([(0, 0), (TS, 0)], fill=A(lite(s, .4)))
        _noise(d, rr, 2, 6, TS-3, TS-10, dark(s, .35), 22, 90, under=s)
    elif ch == "o":                                # 엄폐
        d.rectangle([0, 0, TS, TS], fill=A(GROUND))
        _noise(d, rr, 0, 0, TS-1, TS-1, dark(GROUND, .4), 24, 50)
        w = hx("#6E5C44")
        d.rectangle([0, TS-5, TS, TS], fill=A(dark(GROUND, .35)))       # 발치의 흙
        for k in range(5):                                              # 세로 널
            x = k*7 - 1
            top = 4 + rr.r(0, 5)
            d.rectangle([x, top, x+6, TS-2], fill=A(w), outline=A(dark(w, .55)))
            d.line([(x+1, top+2), (x+1, TS-3)], fill=A(lite(w, .3)))
            d.line([(x+5, top+2), (x+5, TS-3)], fill=A(dark(w, .3)))
            d.polygon([(x, top), (x+3, top-4), (x+6, top)], fill=A(w), outline=A(dark(w, .55)))
        for yb in (11, 23):                                             # 가로 띠
            d.rectangle([0, yb, TS, yb+3], fill=A(dark(w, .22)), outline=A(dark(w, .55)))
    elif ch == "w":                                # 물
        d.rectangle([0, 0, TS, TS], fill=A(hx("#2E4552")))
        for _ in range(7):
            y = rr.r(2, TS-3); x = rr.r(0, TS-11)
            d.line([(x, y), (x+9, y)], fill=A(hx("#4E7286"), 170))
        for _ in range(3):
            y = rr.r(2, TS-3); x = rr.r(0, TS-7)
            d.line([(x, y), (x+5, y)], fill=A(hx("#8AB0C2"), 130))
    elif ch == "x":                                # 불 — 아직 꺼지지 않았다
        # 바닥을 통째로 덮으면 검은 사각형이 보인다. 그을음만 얹는다.
        blob = [(rr.r(0, 5), rr.r(0, 6)), (rr.r(11, 20), rr.r(0, 3)), (TS - rr.r(1, 6), rr.r(1, 7)),
                (TS - rr.r(0, 3), rr.r(18, 26)), (rr.r(12, 20), TS - rr.r(0, 4)),
                (rr.r(2, 8), TS - rr.r(1, 5)), (rr.r(0, 3), rr.r(14, 22))]
        d.polygon(blob, fill=(22, 17, 14, 190))
        for _ in range(16):
            x, y = rr.r(1, TS-2), rr.r(1, TS-2)
            d.point((x, y), fill=(38, 28, 22, 130))
        for _ in range(5):
            x, y = rr.r(4, TS-6), rr.r(8, TS-4)
            h = rr.r(6, 13)
            d.polygon([(x, y), (x+3, y-h), (x+6, y)], fill=A(hx("#C4531F"), 220))
            d.polygon([(x+1, y), (x+3, y-h+4), (x+5, y)], fill=A(hx("#E8A03A"), 230))
            d.point((x+3, y-h+2), fill=A(hx("#F5D98A")))
    else:
        return tile(".", v)
    return im


def uri(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()
