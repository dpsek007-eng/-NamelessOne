# -*- coding: utf-8 -*-
"""잔상 스프라이트 생성기 — 부품 조합식.
   실루엣 = 설정. 잔상은 탑이 기억하는 만큼만 형태를 갖춘다.
   레이어: 체형(역할) → 의복(계층) → 소품(생업) → 강조색 → 흐려짐"""
from PIL import Image, ImageDraw
import sys
sys.path.insert(0,'tools')

W,H = 48,64

def _norm(xy):
    """좌표 순서 정규화 — 오프셋 계산으로 뒤집혀도 그려지게"""
    try:
        (x0,y0),(x1,y1)=xy[0],xy[1]
    except TypeError:
        x0,y0,x1,y1=xy
    return [min(x0,x1),min(y0,y1),max(x0,x1),max(y0,y1)]

class _SafeDraw:
    """rectangle / ellipse 의 좌표를 항상 정규화한다"""
    def __init__(self,dd): object.__setattr__(self,"_d",dd)
    def rectangle(self,xy,**k): self._d.rectangle(_norm(xy),**k)
    def ellipse(self,xy,**k): self._d.ellipse(_norm(xy),**k)
    def arc(self,xy,*a,**k): self._d.arc(_norm(xy),*a,**k)
    def __getattr__(self,n): return getattr(self._d,n)
def hx(c): return tuple(int(c[i:i+2],16) for i in (1,3,5))

# 계층별 의복 실루엣
ROBE={"왕실":"long","귀족":"cape","술사":"hood","성직":"hood","관리":"coat","상인":"coat",
      "장인":"tunic","농어민":"tunic","병졸":"armor","하인":"tunic","유랑":"rag"}
# 생업 소품 (없으면 None)
PROP={"종탑":"rope","대장간":"hammer","물장수":"bucket","서고":"book","사경":"book","점성":"rod",
 "기사":"sword","성기사":"sword","마법사":"staff","정령술사":"bowl","연금":"flask","성녀":"cloth",
 "목공":"plane","채석":"chisel","담장":"chisel","화덕":"loaf","부엌":"ladle","약방":"herb",
 "재봉":"needle","등대":"lamp","망루":"lamp","문지기":"bar","전령":"letter","악기":"lute",
 "밭":"seed","어망":"net","양치기":"staff","마구간":"rein","무두질":"hide","방직":"spool",
 "도공":"bowl","숯막":"coal","산파":"cloth","장의":"cloth","마방":"wheel","양조":"jar",
 "유랑":"bundle","궁정":"seal","영주":"seal","징세":"book","상단":"chest","광부":"pick",
 "사냥":"bow","벌치기":"jar","유리 세공":"flask","세탁":"cloth","사제":"book"}

# 계층별 옷단 높이 — 낮을수록 긴 옷 (다리가 가려진다)
HEM={"long":57,"hood":56,"cape":50,"coat":46,"armor":41,"tunic":40,"rag":44}

def sprite(cls, trade, role, color, fade=0.12, scale=6):
    im=Image.new("RGBA",(W,H),(0,0,0,0)); d=_SafeDraw(ImageDraw.Draw(im))
    ink=(26,29,33,255); ink2=(58,64,71,255); acc=hx(color)+(255,)
    robe=ROBE.get(cls,"tunic"); prop=PROP.get(trade); hem=HEM[robe]

    # ── 다리 (옷단보다 아래만 보인다) ──
    if hem<52:
        if role=="도피":
            d.polygon([(20,hem-2),(23,hem-2),(21,61),(17,61)],fill=ink)
            d.polygon([(25,hem-2),(28,hem-2),(30,61),(26,61)],fill=ink)
        else:
            d.rectangle([20,hem-2,23,61],fill=ink); d.rectangle([25,hem-2,28,61],fill=ink)

    # ── 팔 (몸통보다 먼저 그려 어깨에 묻히게) ──
    hand=(38,17)
    if role=="저항":
        d.polygon([(30,23),(39,15),(42,18),(33,27)],fill=ink2); d.polygon([(18,23),(15,23),(13,41),(17,41)],fill=ink2)
        hand=(40,15)
    elif role=="탐구":
        d.polygon([(30,23),(37,12),(40,14),(33,26)],fill=ink2); d.polygon([(18,23),(15,23),(13,40),(17,40)],fill=ink2)
        hand=(38,12)
    elif role=="헌신":
        d.polygon([(30,24),(39,30),(37,34),(28,29)],fill=ink2); d.polygon([(18,24),(9,30),(11,34),(20,29)],fill=ink2)
        hand=(39,31)
    elif role=="수호":
        d.polygon([(17,22),(13,23),(12,43),(16,43)],fill=ink2); d.polygon([(31,22),(35,23),(36,43),(32,43)],fill=ink2)
        hand=(35,26)
    else:
        d.polygon([(18,23),(15,23),(13,42),(17,42)],fill=ink2); d.polygon([(30,24),(37,33),(34,36),(28,27)],fill=ink2)
        hand=(36,33)

    # ── 몸통 · 의복 (어깨 16 → 허리 13 → 옷단) ──
    hw={"long":11,"hood":11,"cape":12,"coat":10,"armor":9,"tunic":9,"rag":10}[robe]
    body=[(16,21),(32,21),(29,32),(24+hw,hem),(24-hw,hem),(19,32)]
    if robe=="rag":
        body=[(17,21),(31,21),(30,33),(34,hem),(29,hem-4),(24,hem+2),(19,hem-3),(14,hem)]
    d.polygon(body,fill=ink)

    # ── 머리 ──
    d.rectangle([22,16,26,22],fill=ink)                 # 목
    d.ellipse([19,7,29,18],fill=ink)                    # 머리
    if robe=="hood":                                     # 두건 — 낮게
        d.polygon([(18,17),(24,4),(30,17),(30,20),(18,20)],fill=ink)
    if robe in("long","cape"):                           # 어깨 장식 — 왕실·귀족
        d.polygon([(14,21),(34,21),(32,26),(16,26)],fill=acc)
    if robe=="armor":                                    # 흉갑선 — 병졸
        d.rectangle([19,26,29,28],fill=acc)

    # ── 소품 (강조색) ──
    ox,oy=hand[0]-38,hand[1]-24
    # 든 팔(저항·탐구)은 손이 높아 소품이 허공에 뜬다. 몸통 옆 범위로 묶는다.
    oy=max(-4, min(oy+8, 6)); ox=max(-6, min(ox, 4))
    def _n(a,b,c,e):   # 좌표 순서 정규화 — 오프셋 후 뒤집혀도 안전하게
        return [min(a,c),min(b,e),max(a,c),max(b,e)]
    def R(x0,y0,x1,y1,f): d.rectangle(_n(x0+ox,y0+oy,x1+ox,y1+oy),fill=f)
    def E(x0,y0,x1,y1,**k): d.ellipse(_n(x0+ox,y0+oy,x1+ox,y1+oy),**k)
    def G(pts,f): d.polygon([(x+ox,y+oy) for x,y in pts],fill=f)
    P={"rope":lambda:d.rectangle([33,5,35,38],fill=acc),
       "hammer":lambda:(d.rectangle([36,12,39,30],fill=ink),d.rectangle([32,9,42,15],fill=acc)),
       "bucket":lambda:(d.polygon([(32,30),(42,30),(40,41),(34,41)],fill=acc),d.arc([32,30,42,34],180,360,fill=ink)),
       "book":lambda:d.polygon([(32,26),(42,24),(42,30),(32,32)],fill=acc),
       "rod":lambda:(d.rectangle([36,8,38,30],fill=ink),d.ellipse([33,4,41,12],outline=acc,width=2)),
       "sword":lambda:(d.polygon([(36,6),(39,6),(39,30),(37,34),(35,30)],fill=acc),d.rectangle([33,32,42,31],fill=ink)),
       "staff":lambda:(d.rectangle([36,4,38,40],fill=ink),d.ellipse([33,2,41,10],fill=acc)),
       "bowl":lambda:d.polygon([(32,30),(42,30),(39,34),(35,34)],fill=acc),
       "flask":lambda:(d.polygon([(35,24),(39,24),(42,32),(32,32)],fill=acc),d.rectangle([36,20,38,25],fill=ink)),
       "cloth":lambda:d.polygon([(31,26),(41,24),(42,36),(32,38)],fill=acc),
       "plane":lambda:d.polygon([(31,30),(43,28),(43,31),(31,33)],fill=acc),
       "chisel":lambda:(d.polygon([(36,14),(39,14),(39,32),(37,32),(35,32)],fill=acc)),
       "loaf":lambda:d.ellipse([31,28,43,34],fill=acc),
       "ladle":lambda:(d.rectangle([37,14,39,32],fill=ink),d.ellipse([33,30,43,34],fill=acc)),
       "herb":lambda:(d.polygon([(34,22),(40,22),(38,34),(36,34)],fill=acc)),
       "needle":lambda:(d.rectangle([37,16,38,32],fill=acc)),
       "lamp":lambda:(R(37,-12,39,-2,ink),G([(34,-2),(43,-2),(41,8),(36,8)],acc)),
       "bar":lambda:R(33,4,44,7,acc),
       "letter":lambda:d.polygon([(32,28),(42,26),(42,30),(32,32)],fill=acc),
       "lute":lambda:(d.ellipse([32,28,43,36],fill=acc),d.rectangle([37,14,38,30],fill=ink)),
       "seed":lambda:d.polygon([(33,30),(41,30),(42,36),(32,36)],fill=acc),
       "net":lambda:[d.line([(31+i*3,26),(34+i*3,36)],fill=acc,width=1) for i in range(4)],
       "rein":lambda:(d.arc([30,20,44,36],270,90,fill=acc,width=2)),
       "hide":lambda:d.polygon([(31,24),(42,26),(40,36),(32,34)],fill=acc),
       "spool":lambda:(d.rectangle([34,26,41,32],fill=acc),d.rectangle([32,26,34,32],fill=ink)),
       "coal":lambda:d.polygon([(33,30),(40,28),(42,34),(32,34)],fill=acc),
       "wheel":lambda:d.ellipse([30,24,44,34],outline=acc,width=3),
       "jar":lambda:(d.polygon([(33,26),(41,26),(42,34),(32,34)],fill=acc),d.rectangle([35,23,39,27],fill=ink)),
       "bundle":lambda:(d.rectangle([36,10,38,30],fill=ink),d.polygon([(31,28),(43,28),(41,36),(33,36)],fill=acc)),
       "seal":lambda:(d.ellipse([33,26,43,32],fill=acc),d.rectangle([37,20,39,28],fill=ink)),
       "chest":lambda:(d.rectangle([31,28,43,36],fill=acc),d.rectangle([31,32,43,30],fill=ink)),
       "pick":lambda:(d.rectangle([36,14,38,30],fill=ink),d.arc([30,8,44,20],180,360,fill=acc,width=3)),
       "bow":lambda:(d.arc([32,10,44,38],270,90,fill=acc,width=2),d.line([(40,12),(40,36)],fill=ink))}
    if prop and prop in P: P[prop]()

    # ── 흐려짐 — 아래에서 위로 사라진다 ──
    px=im.load()
    for y in range(H):
        t=(y-(H-16))/16.0
        if t<=0: continue
        for x in range(W):
            r,g,b,a=px[x,y]
            if a: px[x,y]=(r,g,b,max(0,int(a*(1-min(1,t)))))
    return im.resize((W*scale,H*scale),Image.NEAREST)
