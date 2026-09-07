# -*- coding: utf-8 -*-
"""잔상 리그 — 관절로 된 몸. 정지 그림이 아니라 자세를 받아 그린다.

   숨(idle) · 걸음(walk) · 침(attack) · 맞음(hurt) · 흐려짐(fall)
   한 캐릭터가 한 장의 시트로 나온다. 같은 시트를 유니티가 잘라 쓴다.
"""
from PIL import Image, ImageDraw
import base64, io, math, json
import art
from art import (hx, mix, dark, lite, A, INK, CLS_PAL, SKIN, HAIR, R, seed_of,
                 ROBE, HEM, POSE, ROLE_ARMS, TRADE_PROP)


def _norm(xy):
    (x0, y0), (x1, y1) = (xy[0], xy[1]) if isinstance(xy[0], (tuple, list)) \
        else ((xy[0], xy[1]), (xy[2], xy[3]))
    return [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]


class _SafeDraw:
    """자세가 접히면 좌표 순서가 뒤집힌다. 그릴 때 도로 세운다."""
    def __init__(self, dd): object.__setattr__(self, "_d", dd)
    def rectangle(self, xy, **k): self._d.rectangle(_norm(xy), **k)
    def ellipse(self, xy, **k):   self._d.ellipse(_norm(xy), **k)
    def arc(self, xy, *a, **k):   self._d.arc(_norm(xy), *a, **k)
    def __getattr__(self, n):     return getattr(self._d, n)

W, H = 48, 64

CLIPS = [                      # 이름, 프레임 수, 초당 프레임, 반복
    ("idle",   6, 6,  True),
    ("walk",   8, 12, True),
    ("attack", 6, 14, False),
    ("hurt",   3, 12, False),
    ("fall",   5, 8,  False),
]
NF = sum(c[1] for c in CLIPS)          # 28 프레임


# ── 몸의 치수 ──────────────────────────────────────────────────────
def look_of(cid, cls, trade, role, key_color, rarity=3):
    """이 잔상의 생김새를 한 번만 정해 둔다. 프레임마다 바뀌면 안 된다."""
    p  = POSE.get(cid, {})
    rr = R(seed_of(cid))
    build = p.get("build", "norm")
    B = art.BUILD[build]
    base, trim = (hx(c) for c in CLS_PAL.get(cls, CLS_PAL["하인"]))
    def jog(c, k=26):
        return tuple(max(8, min(247, c[i] + rr.r(-k, k) - (0 if i == 1 else rr.r(0, 6))))
                     for i in range(3))
    base, trim = jog(base), jog(trim, 20)
    robe = ROBE.get(cls, "tunic")
    prop = p.get("prop", TRADE_PROP.get(trade)) if "prop" in p else TRADE_PROP.get(trade)
    return dict(
        cid=cid, build=build, stoop=p.get("stoop", 0), slump=1 if p.get("slump") else 0,
        tilt=p.get("tilt", 0), faceless=p.get("faceless", False), sleeve=p.get("sleeve", False),
        arms=p.get("arms") or ROLE_ARMS.get(role, "down"), prop=prop, role=role, rarity=rarity,
        robe=robe, base=base, trim=trim, acc=hx(key_color),
        skin=hx(rr.pick(SKIN)), hair=hx(rr.pick(HAIR)), hstyle=rr.n() % 4,
        hcy=B["hcy"], hr=B["hr"], shy=B["shy"], shw=B["shw"], wy=B["wy"], ft=B["ft"],
        hem=min(HEM[robe], B["ft"] - 1, 50 if build == "child" else 99),
        hw={"long": 10, "hood": 10.5, "cape": 11, "coat": 9.5, "armor": 9,
            "tunic": 8.5, "apron": 9, "rag": 9.5}[robe]
            + (-2 if build == "child" else 1.5 if build == "bulk" else 0),
    )


def limb(d, a, b, w, col, ol):
    dx, dy = b[0]-a[0], b[1]-a[1]
    L = math.hypot(dx, dy) or 1
    nx, ny = -dy/L*w/2, dx/L*w/2
    d.polygon([(a[0]+nx, a[1]+ny), (b[0]+nx, b[1]+ny), (b[0]-nx, b[1]-ny), (a[0]-nx, a[1]-ny)],
              fill=A(col), outline=A(ol))

def arm(d, sh, el, hd, cloth, skin, w=4.6):
    limb(d, sh, el, w, cloth, INK)
    limb(d, el, hd, w*0.82, skin, INK)


# ── 한 프레임 ──────────────────────────────────────────────────────
def draw(L, P):
    """L=생김새, P=자세. P 의 좌표는 전부 절대값이다."""
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d  = _SafeDraw(ImageDraw.Draw(im))     # 자세가 뒤집혀도 좌표가 도로 서게
    base, trim, acc = L["base"], L["trim"], L["skin"]
    skin, hair = L["skin"], L["hair"]
    robe, hem, hw = L["robe"], L["hem"], L["hw"]
    accc = L["acc"]
    cx  = 24
    fade = P.get("fade", 0.0)

    hip_l, hip_r = P["hipL"], P["hipR"]
    kne_l, kne_r = P["kneeL"], P["kneeR"]
    ft_l,  ft_r  = P["footL"], P["footR"]
    shy, wy = P["chest"][1], P["pelvis"][1]
    hcx, hcy = P["head"]

    legc = dark(mix(base, hx("#43382C"), .5), .30)
    boot = dark(mix(trim, hx("#4A3A2A"), .55), .35)

    # ── 뒤쪽 다리 ──
    if hem < L["ft"] - 3:
        limb(d, hip_l, kne_l, 4.4, dark(legc, .18), INK)
        limb(d, kne_l, ft_l, 4.0, dark(legc, .18), INK)
    d.rectangle([ft_l[0]-4, ft_l[1]-2, ft_l[0]+3, ft_l[1]+1], fill=A(dark(boot, .2)), outline=A(INK))

    # ── 앞쪽 다리 ──
    if hem < L["ft"] - 3:
        limb(d, hip_r, kne_r, 4.4, legc, INK)
        limb(d, kne_r, ft_r, 4.0, legc, INK)
    d.rectangle([ft_r[0]-3, ft_r[1]-2, ft_r[0]+4, ft_r[1]+1], fill=A(boot), outline=A(INK))

    # ── 뒷팔 ──
    armc = lite(base, .10)
    arm(d, P["shB"], P["elbowB"], P["handB"], dark(armc, .28), dark(skin, .18))

    # ── 몸통 ──
    lean = P.get("lean", 0)
    shw  = L["shw"]
    body = [(P["chest"][0]-shw, shy), (P["chest"][0]+shw, shy),
            (cx+shw-1+lean, wy-3), (cx+hw+lean, hem), (cx-hw+lean, hem), (cx-shw+1+lean, wy-3)]
    if robe == "rag":
        body = [(P["chest"][0]-shw, shy), (P["chest"][0]+shw, shy), (cx+shw, wy-3),
                (cx+hw+3, hem-1), (cx+hw-3, hem-5), (cx+1, hem+2), (cx-hw+2, hem-4), (cx-hw-2, hem)]
    d.polygon(body, fill=A(base), outline=A(INK))
    d.polygon([(cx+2, shy+1), (P["chest"][0]+shw-1, shy+1), (cx+shw-2+lean, wy-3),
               (cx+hw-1+lean, hem-1), (cx+2, hem-1)], fill=A(dark(base, .22)))

    if robe == "cape":
        d.polygon([(P["chest"][0]-shw-1, shy-1), (P["chest"][0]+shw+1, shy-1),
                   (P["chest"][0]+shw+3, shy+13), (P["chest"][0]-shw-3, shy+13)],
                  fill=A(trim), outline=A(INK))
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

    if robe in ("hood", "long", "cape"):
        d.line([(P["chest"][0]-shw+2, shy+3), (cx+hw-3, wy-1)], fill=A(accc), width=2)
    else:
        d.rectangle([cx-hw+lean+1, wy-3, cx+hw+lean-1, wy-2], fill=A(accc))
        d.rectangle([cx-2+lean, wy-4, cx+2+lean, wy-1], fill=A(dark(accc, .25)), outline=A(INK))

    # ── 앞팔 ──
    arm(d, P["shF"], P["elbowF"], P["handF"], armc, skin, 4.8)
    hd = P["handF"]
    d.ellipse([hd[0]-2.4, hd[1]-2.4, hd[0]+2.4, hd[1]+2.4], fill=A(skin), outline=A(INK))
    if L["arms"] == "wrap":
        for h2 in (P["handF"], P["handB"]):
            d.ellipse([h2[0]-3, h2[1]-3, h2[0]+3, h2[1]+3], fill=A(lite(trim, .5)), outline=A(INK))

    # ── 소품 — 손을 따라간다 ──
    draw_prop(d, L, P)

    # ── 머리 ──
    hr = L["hr"]
    d.ellipse([hcx-hr, hcy-hr-1, hcx+hr, hcy+hr+1], fill=A(skin), outline=A(INK))
    d.rectangle([hcx-2, hcy+hr-1, hcx+2, shy+1], fill=A(dark(skin, .18)))
    st = L["hstyle"]
    if L.get("wraith"):
        for k in range(L.get("spikes", 0)):
            x0 = hcx - hr + 2 + k*(2*hr-4)/max(1, L["spikes"]-1 or 1)
            d.line([(x0, hcy-hr+1), (x0 + (k-1)*2.0, hcy-hr-7)], fill=A(L["trim"]), width=2)
        d.rectangle([hcx-hr+1, hcy-2, hcx+hr-1, hcy+3], fill=A(dark(L["base"], .55)))
        for ex in (hcx-3, hcx+2):
            d.rectangle([ex, hcy, ex+1.4, hcy+1.6], fill=A(L["eye"]))
        if L.get("ember"):
            rr2 = R(seed_of(L["cid"]))
            for _ in range(6):
                x, y = rr2.r(int(cx-8), int(cx+8)), rr2.r(int(shy+4), int(hem-2))
                d.line([(x, y), (x + rr2.r(-2, 2), y + rr2.r(2, 4))], fill=A(hx("#C4531F")))
    elif robe == "hood":
        d.polygon([(hcx-hr-2, hcy+hr), (hcx-hr-1, hcy-hr-1), (hcx, hcy-hr-3),
                   (hcx+hr+1, hcy-hr-1), (hcx+hr+2, hcy+hr)], fill=A(base), outline=A(INK))
        d.polygon([(hcx-hr+1, hcy+hr-1), (hcx-hr+1, hcy-2), (hcx+hr-1, hcy-2),
                   (hcx+hr-1, hcy+hr-1)], fill=A(dark(base, .55)))
        d.ellipse([hcx-hr+1, hcy-1, hcx+hr-1, hcy+hr], fill=A(skin))
    elif st == 0:
        d.polygon([(hcx-hr, hcy-1), (hcx-hr+1, hcy-hr-1), (hcx+hr-1, hcy-hr-1),
                   (hcx+hr, hcy-1), (hcx+hr-2, hcy-3), (hcx-hr+2, hcy-3)],
                  fill=A(hair), outline=A(dark(hair, .4)))
    elif st == 1:
        d.polygon([(hcx-hr-1, hcy+hr+4), (hcx-hr-1, hcy-hr), (hcx, hcy-hr-2),
                   (hcx+hr+1, hcy-hr), (hcx+hr+1, hcy+hr+4), (hcx+hr-1, hcy+hr+2),
                   (hcx+hr-2, hcy-1), (hcx-hr+2, hcy-1), (hcx-hr+1, hcy+hr+2)],
                  fill=A(hair), outline=A(dark(hair, .4)))
    elif st == 2:
        d.polygon([(hcx-hr, hcy-1), (hcx-hr+1, hcy-hr-1), (hcx+hr-1, hcy-hr-1),
                   (hcx+hr, hcy-1), (hcx+hr-2, hcy-3), (hcx-hr+2, hcy-3)],
                  fill=A(hair), outline=A(dark(hair, .4)))
        d.ellipse([hcx-hr-4, hcy-3, hcx-hr, hcy+2], fill=A(hair), outline=A(dark(hair, .4)))
    else:
        d.polygon([(hcx-hr-1, hcy-1), (hcx-hr, hcy-hr-1), (hcx+hr, hcy-hr-1), (hcx+hr+1, hcy-1)],
                  fill=A(trim), outline=A(INK))
        d.polygon([(hcx-hr-1, hcy-1), (hcx-hr-4, hcy+4), (hcx-hr, hcy+1)], fill=A(dark(trim, .25)))

    # 얼굴 — 감으면 흐려진 것이다
    if L.get("wraith"):
        pass
    elif not L["faceless"]:
        ey = hcy + (1 if L["build"] == "child" else 0)
        if P.get("eyes", 1):
            for ex in (hcx-2, hcx+2):
                d.point((ex, ey), fill=A(INK)); d.point((ex, ey+1), fill=A(INK))
        else:
            d.line([(hcx-3, ey), (hcx-1, ey)], fill=A(INK))
            d.line([(hcx+1, ey), (hcx+3, ey)], fill=A(INK))
        if L["role"] == "저항": d.line([(hcx-3, ey-2), (hcx-1, ey-1)], fill=A(dark(hair, .2)))
        if L["stoop"] >= 3:    d.line([(hcx-2, ey+4), (hcx+2, ey+4)], fill=A(dark(skin, .45)))
    else:
        d.rectangle([hcx-hr+1, hcy-2, hcx+hr-1, hcy+2], fill=A(dark(skin, .55)))

    # 선명도가 낮으면 아래가 흐리다. 흐려지는 중이면 전체가 흐리다.
    if L["rarity"] <= 2 or fade > 0:
        px = im.load()
        for y in range(H):
            f = max(0.0, min(1.0, (y - 34) / 26.0)) * (0.55 if L["rarity"] <= 2 else 0)
            f = 1 - (1 - f) * (1 - fade)
            if f <= 0: continue
            for x in range(W):
                r, g, b, a = px[x, y]
                if a: px[x, y] = (r, g, b, int(a * (1 - f)))
    return im


def draw_prop(d, L, P):
    prop = L["prop"]
    if not prop: return
    hxp, hyp = P["handF"]
    bxp, byp = P["handB"]
    shy = P["chest"][1]
    cx = 24
    wood, iron, paper = hx("#6B4A2C"), hx("#8A929C"), hx("#DCD5C2")
    ang = P.get("propang", 0.0)                     # 손목 각도 — 칠 때 돈다
    def rot(dx, dy):
        c, s = math.cos(ang), math.sin(ang)
        return (hxp + dx*c - dy*s, hyp + dx*s + dy*c)
    if prop == "rope":
        d.line([(hxp, hyp-2), (hxp+1, 8)], fill=A(hx("#B9A377")), width=2)
        d.line([(hxp+1, 8), (hxp-6, 6)], fill=A(hx("#B9A377")), width=2)
    elif prop == "bar":
        limb(d, rot(-1, 6), rot(3, -14), 3.4, wood, INK)
        a = rot(1.5, -12); d.rectangle([a[0]-2, a[1]-2, a[0]+3, a[1]+1], fill=A(iron), outline=A(INK))
    elif prop == "spear":
        limb(d, rot(-2, 12), rot(2, -18), 2.6, wood, INK)
        t, l, r = rot(2, -18), rot(5, -12), rot(-1, -12)
        d.polygon([t, l, r], fill=A(iron), outline=A(INK))
    elif prop == "papers":
        d.rectangle([hxp-5, hyp-6, hxp+4, hyp+2], fill=A(paper), outline=A(INK))
        d.line([(hxp-3, hyp-4), (hxp+2, hyp-4)], fill=A(hx("#9A9384")))
        d.line([(hxp-3, hyp-1), (hxp+2, hyp-1)], fill=A(hx("#9A9384")))
    elif prop in ("book", "tablet", "letter"):
        c = hx("#7A4A3A") if prop == "book" else paper
        d.rectangle([hxp-4, hyp-5, hxp+4, hyp+3], fill=A(c), outline=A(INK))
        d.rectangle([hxp-4, hyp-5, hxp-2, hyp+3], fill=A(dark(c, .3)))
    elif prop == "broom":
        limb(d, rot(-12, 6), rot(11, -5), 2.4, wood, INK)
        a, b, c = rot(11, -6), rot(16, -11), rot(15, -1)
        d.polygon([a, b, c], fill=A(hx("#9A8A5E")), outline=A(INK))
    elif prop == "yoke":
        limb(d, (cx-13, shy-3), (cx+13, shy-3), 2.6, wood, INK)
        for sx in (cx-13, cx+13):
            d.line([(sx, shy-2), (sx, shy+5)], fill=A(hx("#8A7A5E")))
            d.rectangle([sx-4, shy+5, sx+4, shy+12], fill=A(hx("#6E5A3E")), outline=A(INK))
            d.rectangle([sx-4, shy+6, sx+4, shy+7], fill=A(hx("#4E6E7A")))
    elif prop == "hammer":
        limb(d, rot(0, 8), rot(1, -9), 2.6, wood, INK)
        a = rot(1, -11); d.rectangle([a[0]-5, a[1]-2, a[0]+5, a[1]+2], fill=A(iron), outline=A(INK))
    elif prop == "loaf":
        d.ellipse([hxp-5, hyp-4, hxp+5, hyp+3], fill=A(hx("#C08A4E")), outline=A(INK))
        d.line([(hxp-2, hyp-2), (hxp+2, hyp)], fill=A(hx("#8A5E2E")))
    elif prop == "coal":
        d.ellipse([hxp-2, hyp-2, hxp+2, hyp+2], fill=A(hx("#2A2622")), outline=A(INK))
    elif prop == "lamp":
        d.line([(hxp, hyp), (hxp, hyp+4)], fill=A(iron))
        d.rectangle([hxp-3, hyp+4, hxp+3, hyp+10], fill=A(hx("#D9A94E")), outline=A(INK))
    elif prop == "chisel":
        limb(d, rot(0, -1), rot(6, -7), 2.4, iron, INK)
    elif prop == "plane":
        d.rectangle([hxp-5, hyp-3, hxp+5, hyp+2], fill=A(wood), outline=A(INK))
    elif prop == "herb":
        d.line([(hxp, hyp), (hxp+2, hyp-7)], fill=A(hx("#5E7A4A")), width=2)
        d.ellipse([hxp, hyp-9, hxp+5, hyp-5], fill=A(hx("#6E8A54")))
    elif prop == "lute":
        d.ellipse([hxp-6, hyp-3, hxp+3, hyp+7], fill=A(hx("#8A5E32")), outline=A(INK))
        limb(d, (hxp+2, hyp+1), (hxp+10, hyp-8), 2.2, wood, INK)
    elif prop == "bow":
        a, b, c2 = rot(-3, -14), rot(-6, 0), rot(-3, 14)
        d.arc([a[0]-2, a[1], c2[0]+2, c2[1]], 250, 110, fill=A(hx("#7A6A52")), width=2)
        d.line([a, c2], fill=A(hx("#9A8A6E")))
    elif prop == "pack":
        d.rectangle([cx-L["shw"]-3, shy+3, cx-L["shw"]+3, shy+14], fill=A(hx("#5E4E3A")), outline=A(INK))
    elif prop == "ribbon":
        for k, sx in ((0, bxp), (1, hxp)):
            d.line([(sx, P["chest"][1]-4), (sx+(2 if k else -2), P["chest"][1]+6)],
                   fill=A(L["acc"]), width=2)
    elif prop == "flag":
        top = (cx+2 + P.get("flagdx", 0), 4)
        limb(d, (cx+2, 62), top, 2.4, wood, INK)
        w = P.get("flagwave", 0)
        d.polygon([(top[0]+1, top[1]+1), (top[0]+14, top[1]+4+w), (top[0]+13, top[1]+16+w),
                   (top[0]+1, top[1]+14)], fill=A(L["acc"]), outline=A(INK))


# ── 자세 ──────────────────────────────────────────────────────────
#   손이 가는 자리는 성향과 하는 일이 정한다. 프레임은 거기서 흔들릴 뿐이다.
BACK_T = {"out":(-8,2),"point":(-3,8),"spread":(-9,-3),"fore":(-2,9),"yoke":(-6,-1),
          "behind":(-3,12),"cradle":(-4,11),"guard":(-5,13),"shoulder":(-5,13),
          "carry":(-5,12),"wrap":(-5,11),"hold":(-6,7),"pole":(-5,3),"write":(-6,10),
          "lean":(-6,10),"down":(-4,14)}
FRONT_T = {"out":(10,1),"point":(11,2),"spread":(9,-4),"fore":(8,7),"yoke":(6,-1),
           "behind":(1,13),"cradle":(2,12),"guard":(5,9),"shoulder":(2,-4),
           "carry":(4,11),"wrap":(1,12),"hold":(6,8),"pole":(2,1),"write":(6,-2),
           "lean":(5,9),"down":(4,14)}

def _elbow(sh, hd, out):
    """팔꿈치는 어깨와 손 사이에서 바깥으로 조금 굽는다"""
    mx, my = (sh[0]+hd[0])/2, (sh[1]+hd[1])/2
    dx, dy = hd[0]-sh[0], hd[1]-sh[1]
    L = math.hypot(dx, dy) or 1
    return (mx - dy/L*out, my + dx/L*out)

def _ease(a, b, t):  return a + (b-a) * (t*t*(3-2*t))

def pose(L, clip, i, n):
    t   = i / n
    cx  = 24
    shw, wy, ft, hcy, shy = L["shw"], L["wy"], L["ft"], L["hcy"], L["shy"]
    stoop, slump, tilt = L["stoop"], L["slump"], L["tilt"]

    bob = lean = 0.0; headdx = headdy = 0.0
    fdx = fdy = bdx = bdy = 0.0                 # 손 추가 이동
    legf = legb = 0.0                           # 다리 스윙
    kneef = kneeb = 0.0
    propang = 0.0; fade = 0.0; eyes = 1
    flagwave = 0.0; shrug = 0.0
    body_dx = 0.0

    if clip == "idle":                          # 숨을 쉰다
        br = math.sin(2*math.pi*t)
        bob   = -0.7*br - 0.3
        shrug = -0.5*br
        headdy = -0.45*br + 0.25*math.sin(4*math.pi*t)
        fdy = bdy = 0.5*br
        fdx = 0.3*br; bdx = -0.3*br
        flagwave = 0.8*math.sin(2*math.pi*t + 0.6)
        propang = 0.03*br

    elif clip == "walk":                        # 걷는다
        ph = 2*math.pi*t
        legf =  math.sin(ph) * 7.5
        legb =  math.sin(ph + math.pi) * 7.5
        kneef = max(0, math.sin(ph + 0.9)) * 4.5
        kneeb = max(0, math.sin(ph + math.pi + 0.9)) * 4.5
        bob   = -abs(math.sin(2*ph)) * 1.3 - 0.4
        lean  = 0.8
        fdx   =  math.cos(ph + math.pi) * 4.5
        fdy   = -abs(math.cos(ph)) * 1.2
        bdx   =  math.cos(ph) * 4.5
        headdy = -0.5*abs(math.sin(2*ph))
        flagwave = 1.6*math.sin(ph)
        propang = 0.10*math.sin(ph)

    elif clip == "attack":                      # 친다 — 당겼다가 내지른다
        if t < 0.34:                            # 당김
            k = t/0.34
            lean = _ease(0, -2.2, k); body_dx = _ease(0, -2.0, k)
            fdx  = _ease(0, -6.0, k); fdy = _ease(0, -3.0, k)
            propang = _ease(0, -0.85, k)
            headdx = _ease(0, -0.8, k)
        elif t < 0.55:                           # 내지름
            k = (t-0.34)/0.21
            lean = _ease(-2.2, 3.4, k); body_dx = _ease(-2.0, 4.5, k)
            fdx  = _ease(-6.0, 12.0, k); fdy = _ease(-3.0, 1.0, k)
            propang = _ease(-0.85, 0.55, k)
            headdx = _ease(-0.8, 1.6, k)
            legf = _ease(0, 5.0, k)
        else:                                    # 되돌아옴
            k = (t-0.55)/0.45
            lean = _ease(3.4, 0, k); body_dx = _ease(4.5, 0, k)
            fdx  = _ease(12.0, 0, k); fdy = _ease(1.0, 0, k)
            propang = _ease(0.55, 0, k)
            headdx = _ease(1.6, 0, k)
            legf = _ease(5.0, 0, k)
        bdx = -fdx*0.35

    elif clip == "hurt":                         # 맞는다
        k = t
        body_dx = _ease(-4.0, 0, k)
        lean    = _ease(-2.4, 0, k)
        headdx  = _ease(-2.0, 0, k)
        headdy  = _ease(1.6, 0, k)
        fdx = _ease(-5.0, 0, k); bdx = _ease(-4.0, 0, k)
        fdy = _ease(-4.0, 0, k); bdy = _ease(-3.0, 0, k)
        eyes = 0

    elif clip == "fall":                         # 흐려진다
        k = t
        bob    = _ease(0, 9.0, k)
        lean   = _ease(0, -4.0, k)
        headdy = _ease(0, 3.5, k)
        headdx = _ease(0, -2.5, k)
        kneef = kneeb = _ease(0, 7.0, k)
        legf  = _ease(0, -4.0, k); legb = _ease(0, 4.0, k)
        fdy = bdy = _ease(0, 5.0, k)
        fade   = _ease(0.0, 0.82, k)
        eyes   = 0

    # 뼈대
    chest  = (cx + stoop*0.5 + body_dx + tilt*1.2, shy + bob + shrug)
    pelvis = (cx + body_dx*0.4, wy + bob*0.6)
    head   = (cx + stoop*0.9 + body_dx*1.15 + headdx + tilt*2, hcy + stoop + bob + headdy)
    shB    = (chest[0] - shw - 1, chest[1] + 2 + slump)
    shF    = (chest[0] + shw + 1, chest[1] + 2)
    bt = BACK_T.get(L["arms"], BACK_T["down"]); ftg = FRONT_T.get(L["arms"], FRONT_T["down"])
    handB = (shB[0] + bt[0] + bdx, shB[1] + bt[1] + bdy)
    handF = (shF[0] + ftg[0] + fdx, shF[1] + ftg[1] + fdy)

    hipL = (pelvis[0] - 3, pelvis[1]); hipR = (pelvis[0] + 3, pelvis[1])
    footL = (hipL[0] + legb, ft + bob*0.15)
    footR = (hipR[0] + legf, ft + bob*0.15)
    kneeL = ((hipL[0]+footL[0])/2 - kneeb*0.3, (hipL[1]+footL[1])/2 - kneeb)
    kneeR = ((hipR[0]+footR[0])/2 - kneef*0.3, (hipR[1]+footR[1])/2 - kneef)

    return dict(chest=chest, pelvis=pelvis, head=head, lean=lean,
                shB=shB, shF=shF,
                elbowB=_elbow(shB, handB, -2.0), elbowF=_elbow(shF, handF, 2.0),
                handB=handB, handF=handF,
                hipL=hipL, hipR=hipR, kneeL=kneeL, kneeR=kneeR, footL=footL, footR=footR,
                propang=propang, fade=fade, eyes=eyes, flagwave=flagwave,
                flagdx=body_dx*0.6)


def sheet(L):
    """한 잔상의 모든 프레임을 가로 한 줄로. 유니티는 이걸 잘라 쓴다."""
    im = Image.new("RGBA", (W*NF, H), (0, 0, 0, 0))
    i = 0
    for name, n, _fps, _loop in CLIPS:
        for k in range(n):
            im.paste(draw(L, pose(L, name, k, n)), (i*W, 0)); i += 1
    return im


def clip_table():
    out, i = {}, 0
    for name, n, fps, loop in CLIPS:
        out[name] = {"from": i, "n": n, "fps": fps, "loop": loop}
        i += n
    return out


def uri(im):
    b = io.BytesIO(); im.save(b, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(b.getvalue()).decode()


# ── 수호자 · 피난민 ────────────────────────────────────────────────
WRAITH = {
    "재":    dict(build="bulk", robe="rag",  base="#7C736B", trim="#5A524B",
                  acc="#E8843A", eye="#E8843A", spikes=0, ember=True),
    "잔해":  dict(build="thin", robe="rag",  base="#5A5F66", trim="#43474D",
                  acc="#C9A227", eye="#C9A227", spikes=3, prop="bow"),
    "그림자": dict(build="thin", robe="rag",  base="#2E323A", trim="#20242B",
                  acc="#7FB2D9", eye="#7FB2D9", spikes=4),
}

def foe_look(kind):
    w = WRAITH[kind]
    B = art.BUILD[w["build"]]
    return dict(
        cid="foe_"+kind, build=w["build"], stoop=0, slump=0, tilt=0,
        faceless=False, sleeve=False, arms="down", prop=w.get("prop"),
        role="저항", rarity=5, robe=w["robe"],
        base=hx(w["base"]), trim=hx(w["trim"]), acc=hx(w["acc"]),
        skin=hx(w["base"]), hair=hx(w["trim"]), hstyle=-1,
        wraith=True, eye=hx(w["eye"]), spikes=w["spikes"], ember=w.get("ember", False),
        hcy=B["hcy"], hr=B["hr"]+0.4, shy=B["shy"], shw=B["shw"], wy=B["wy"], ft=B["ft"],
        hem=44, hw={"bulk": 11.5, "thin": 9.5}[w["build"]],
    )

def refugee_look(i):
    rr = R(seed_of("ref%d" % i))
    cls = rr.pick(["농어민", "하인", "장인", "유랑"])
    return look_of("ref%d" % i, cls, "없음", "도피",
                   rr.pick(["#7A7168", "#8A8071", "#6E7A5E"]), 2)
