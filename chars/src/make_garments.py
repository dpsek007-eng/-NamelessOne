# -*- coding: utf-8 -*-
"""의복 11계층 x 체형 5종 = 55벌을 만들어 FBX/GLB 로 낸다. 블렌더 안에서 돈다.

    blender --background --python chars/src/make_garments.py -- \
            --out chars/out/garments --shots chars/out/garments/shots

옷을 새로 모델링하지 않는다. MPFB 가 옷 맞추라고 넣어 둔 케이지
(helper-tights 2,674정점 · helper-skirt 720정점)를 깎아서 쓴다.
그 케이지는 이미 뼈 웨이트가 100% 칠해져 있어서, 깎기만 하면
스키닝이 따라온다. 정점을 지워도 버텍스그룹은 남기 때문이다.

체형마다 따로 깎는 이유는 케이지가 몸을 따라 이미 변형돼 있어서다.
1.47m 몸의 케이지와 1.81m 몸의 케이지는 다른 물건이고, 그래서
55벌이 각자 제 몸에 맞는다. 옷 한 벌을 다섯 몸에 늘리는 것보다 이쪽이 싸다.
"""
import argparse, json, math, os, sys

import bmesh
import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_bodies as MB
import garments as G
from bodies import BODIES, SLUG as BODY_SLUG, RIG, RACE

from bl_ext.blender_org.mpfb.services.humanservice import HumanService


# ---------------------------------------------------------------- 몸 만들기
def build_body(role, macro=None, slug=None):
    """make_bodies 와 같은 순서. 다만 헬퍼를 남긴 채로 굽는다.

    macro 를 주면 역할 기본값 대신 그것으로 만든다. 전승 23명이 역할 다섯 벌을
    각자 덮어쓰는 자리다 (`bodies.py` 머리주석 · `data/shades.json`).
    slug 는 이름표다 — 안 주면 역할 슬러그를 쓴다.
    """
    MB.wipe()
    tag = slug or BODY_SLUG[role]
    bm = HumanService.create_human(
        mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True,
        feet_on_ground=True,
        macro_detail_dict={**(macro or BODIES[role]), "race": dict(RACE)})
    arm = HumanService.add_builtin_rig(bm, RIG, import_weights=True)
    HumanService.refit(bm)
    MB.bake_shape(bm, keep_helpers=True)
    bm.name = bm.data.name = f"body_{tag}"
    arm.name = arm.data.name = f"rig_{tag}"
    return bm, arm


def landmarks(bm, arm):
    """옷을 자를 기준점. 전부 이 몸에서 직접 잰다 — 체형마다 다르다."""
    co = [v.co for v in bm.data.vertices]
    z0, z1 = min(c.z for c in co), max(c.z for c in co)
    B = {b.name: (arm.matrix_world @ b.head_local) for b in arm.data.bones}
    sh, wr = B["upperarm_l"], B["hand_l"]
    return dict(
        z0=z0, height=z1 - z0,
        hip=B["pelvis"].z,
        shoulder_x=abs(sh.x),
        wrist_x=abs(wr.x),
        neck_z=B["neck_01"].z,
        clav_z=B["clavicle_l"].z,
        head=B["head"],
        # 팔은 T자가 아니라 A자로 내려가 있다 (어깨 z 0.80·손목 z 0.62 · 키 대비).
        # 소매를 부풀릴 때 이 축을 기준으로 삼는다. x 는 절댓값으로 두고
        # 정점 부호에 따라 좌우로 뒤집어 쓴다.
        sh_axis=Vector((abs(sh.x), sh.y, sh.z)),
        wr_axis=Vector((abs(wr.x), wr.y, wr.z)),
    )


# ---------------------------------------------------------------- 깎기
def carve(bm_obj, arm, sp, L):
    """케이지에서 옷 한 벌을 깎아 낸다."""
    me = bm_obj.data.copy()
    ob = bpy.data.objects.new(f"garment_{sp['slug']}", me)
    bpy.context.collection.objects.link(ob)
    # 버텍스그룹은 오브젝트에 붙어 있다. 웨이트를 살리려면 같이 복사해야 한다.
    for g in bm_obj.vertex_groups:
        ob.vertex_groups.new(name=g.name)

    gi = {g.name: g.index for g in ob.vertex_groups}
    hem_z = L["z0"] + sp["hem"] * L["height"]
    span = max(1e-6, L["wrist_x"] - L["shoulder_x"])

    b = bmesh.new()
    b.from_mesh(me)
    dl = b.verts.layers.deform.active

    def w(v, name):
        return v[dl].get(gi[name], 0.0)

    def hem_at(v):
        """유랑만 밑단이 고르지 않다. 각도에 따라 오르내린다."""
        if not sp["ragged"]:
            return hem_z
        th = math.atan2(v.co.y, v.co.x)
        n = (math.sin(th * 3.0) * 0.50 + math.sin(th * 7.0 + 1.3) * 0.32
             + math.sin(th * 13.0 + 0.4) * 0.18)
        # 0.055 로 두었더니 렌더에서 안 보였다. 옷단 요철이 사람 키의 5%는
        # 되어야 256px 실루엣에서 "뜯겼다"로 읽힌다.
        return hem_z + n * 0.085 * L["height"]

    keep = set()
    for v in b.verts:
        z = v.co.z
        arm_f = (abs(v.co.x) - L["shoulder_x"]) / span   # 0 어깨 · 1 손목
        on_tights = w(v, "helper-tights") > 0.5
        on_skirt = w(v, "helper-skirt") > 0.5

        # 유랑은 한쪽 어깨가 드러난다. 대각선으로 뜯긴 옷이라 좌우가 다르고,
        # 비대칭 실루엣은 좌우대칭인 나머지 여섯과 절대 섞이지 않는다.
        if sp["bare"] and v.co.x < -0.30 * L["shoulder_x"] \
                and z > L["z0"] + 0.735 * L["height"]:
            continue

        if on_tights and z >= hem_at(v) and arm_f <= sp["sleeve"]:
            # 치마를 입는 옷은 엉덩이 아래 몸통 케이지를 버린다.
            # 안 그러면 퍼진 치마 안에 바지 두 짝이 같이 들어간다.
            if not (sp["skirt"] and z < L["hip"]):
                keep.add(v.index)
        if sp["skirt"] and on_skirt and z >= hem_at(v):
            keep.add(v.index)

    bmesh.ops.delete(b, geom=[v for v in b.verts if v.index not in keep],
                     context="VERTS")
    if not b.verts:
        b.free()
        raise SystemExit(f"{sp['slug']}: 남은 정점이 없다. 밑단·소매 값을 보라")

    # 살에서 띄운다. 케이지가 이미 살짝 떠 있고, 그 위에 계층만큼 더 민다.
    # 여기서 소매와 어깨도 같이 만든다 — 밑단만으로는 일곱 모양이 안 갈렸다.
    b.normal_update()
    sh, wr = L["sh_axis"], L["wr_axis"]
    dr, pa = sp["drape"], sp["pauldron"]
    rad = 0.115 * L["height"]
    for v in b.verts:
        n = v.normal.copy()
        v.co += n * sp["puff"]
        sx = 1.0 if v.co.x >= 0.0 else -1.0
        t = (abs(v.co.x) - L["shoulder_x"]) / span

        if dr and t > 0.0:
            # 늘어지는 소매. 팔뼈를 축으로 잡고 둘레로 부풀린 뒤,
            # 축 아래쪽 천은 손목으로 갈수록 더 흘러내린다. 왕실·술사·성직.
            t = min(1.0, t)
            ax = sh.lerp(wr, t)
            r = Vector((0.0, v.co.y - ax.y, v.co.z - ax.z))
            if r.length > 1e-6:
                v.co += r.normalized() * dr * (0.35 + 0.65 * t)
            if v.co.z < ax.z:
                v.co.z -= dr * 2.4 * t * t

        if pa:
            # 어깨 갑옷. 어깨 관절을 중심으로 반지름 안쪽을 부풀려 덩어리를
            # 씌운다. 법선만으로는 위로만 솟아서, x 로도 밀어 어깨를 넓힌다.
            d = (v.co - Vector((sx * sh.x, sh.y, sh.z))).length
            if d < rad:
                f = pa * (1.0 - (d / rad) ** 2)
                v.co += n * f + Vector((sx * f * 0.55, 0.0, f * 0.25))

    # 천 두께. 안쪽으로 준다 — 바깥으로 주면 위에서 민 값과 두 번 더해진다.
    bmesh.ops.solidify(b, geom=list(b.faces), thickness=-sp["thick"])

    b.to_mesh(me)
    b.free()
    for p in me.polygons:
        p.use_smooth = True
    return ob


def add_hood(bm_obj, sp, L):
    """두건 — 술사·성직. 머리와 어깨 살갗을 떠서 부풀리고 얼굴 쪽을 뚫는다.

    처음엔 목 위만 떠서 법선으로 5cm 밀었다. 렌더를 보니 왕실과 머리
    크기가 같았다 — 그건 두건이 아니라 두피였다. 두 가지를 고쳤다.
    아래를 쇄골까지 내려 어깨에 걸치는 덮개를 만들고, 미는 양을
    아래로 갈수록 키웠다. 실루엣에서 읽히는 것은 머리가 아니라
    "머리에서 어깨로 이어지는 하나의 덩어리"다.
    """
    me = bm_obj.data.copy()
    hood = bpy.data.objects.new(f"hood_{sp['slug']}", me)
    bpy.context.collection.objects.link(hood)
    for g in bm_obj.vertex_groups:
        hood.vertex_groups.new(name=g.name)
    gi = {g.name: g.index for g in hood.vertex_groups}
    hc = Vector(L["head"])
    # 어깨까지 내려간다. 쇄골(키의 0.81)보다 조금 아래를 밑선으로 잡는다.
    lo = L["clav_z"] - 0.045 * L["height"]

    b = bmesh.new()
    b.from_mesh(me)
    dl = b.verts.layers.deform.active
    keep = []
    for v in b.verts:
        d = v[dl]
        if d.get(gi["body"], 0.0) <= 0.5:
            continue
        if v.co.z < lo:
            continue
        # 팔은 뺀다. 어깨 덮개지 소매가 아니다.
        if abs(v.co.x) > L["shoulder_x"] * 1.05:
            continue
        # 얼굴 구멍 — 앞쪽(-Y)이면서 정수리보다 아래는 뚫는다.
        if v.co.y < hc.y - 0.010 and hc.z - 0.10 * L["height"] < v.co.z \
                < hc.z + 0.10 * L["height"]:
            continue
        keep.append(v.index)
    bmesh.ops.delete(b, geom=[v for v in b.verts if v.index not in keep],
                     context="VERTS")
    if not b.verts:
        b.free()
        bpy.data.objects.remove(hood)
        return None
    b.normal_update()
    crown = max(v.co.z for v in b.verts)
    for v in b.verts:
        # 머리 중심에서 바깥으로. 법선만 쓰면 얼굴 구멍 가장자리가 안으로 말린다.
        out = (v.co - hc)
        out = out.normalized() if out.length > 1e-6 else v.normal.copy()
        # 아래로 갈수록 크게 민다 — 머리에 붙었다가 어깨로 퍼지는 모양.
        down = max(0.0, min(1.0, (hc.z - v.co.z) / max(1e-6, hc.z - lo)))
        amt = sp["puff"] + 0.042 + 0.075 * down
        v.co += (out * 0.65 + v.normal * 0.35) * amt
        # 정수리를 끌어올려 뾰족하게. 둥근 두피와 갈리는 것은 이 한 뼘이다.
        if v.co.z > hc.z:
            up = (v.co.z - hc.z) / max(1e-6, crown - hc.z)
            v.co.z += 0.045 * L["height"] * min(1.0, up)
    bmesh.ops.solidify(b, geom=list(b.faces), thickness=-sp["thick"])
    b.to_mesh(me)
    b.free()
    for p in me.polygons:
        p.use_smooth = True
    return hood


def add_hair(bm_obj, sp, L):
    """머리카락 — 열한 계층 전부. 두피를 떠서 띄우고 뒤로 흘린다.

    두건과 같은 수법인데 자르는 선이 다르다. 두건은 머리를 **덮으려고**
    쇄골까지 내려가고 얼굴만 뚫는다. 머리카락은 **앞이 높고 뒤가 낮다** —
    이마는 드러나고 목덜미는 덮인다. 그래서 밑선을 상수로 두지 않고
    앞뒤(y)에 따라 기울인다. y 를 경계로 둘로 자르면 귀 옆에 계단이 생긴다.

    왜 넣었나: 다섯 몸이 전부 민머리였다. 옷은 열한 벌로 갈리는데 머리는
    하나도 안 갈려서, 멀리서 보면 같은 인형이 옷만 갈아입은 것으로 보였다.

    미는 양(G.LIFT 1.1cm)이 두건(4.2~7.5cm)보다 훨씬 작은 것은 재어 본 결과다 —
    두건 값으로 밀면 머리 반지름이 수호 12.6cm 에서 19cm 가 된다.
    """
    me = bm_obj.data.copy()
    hair = bpy.data.objects.new(f"hair_{sp['slug']}", me)
    bpy.context.collection.objects.link(hair)
    for g in bm_obj.vertex_groups:
        hair.vertex_groups.new(name=g.name)
    gi = {g.name: g.index for g in hair.vertex_groups}
    hc = Vector(L["head"])

    b = bmesh.new()
    b.from_mesh(me)
    dl = b.verts.layers.deform.active
    skin = [v for v in b.verts if v[dl].get(gi["body"], 0.0) > 0.5]
    if not skin:
        b.free(); bpy.data.objects.remove(hair); return None

    # 머리 크기를 이 몸에서 직접 잰다. 계층 표에 센티미터를 적어 두면
    # 1.47m 몸과 1.85m 몸에서 다른 물건이 된다.
    head = [v for v in skin if v.co.z > hc.z]
    crown = max(v.co.z for v in head)
    hh = crown - hc.z                       # 머리높이 (실측 수호 15.4cm)
    y1 = max(v.co.y for v in head)          # 뒤통수 쪽
    rad = max((Vector((v.co.x, v.co.y, 0.0))
               - Vector((hc.x, hc.y, 0.0))).length for v in head)

    z_front = hc.z + G.FRINGE * hh          # 앞머리선 — 눈썹 위
    z_back = hc.z - sp["hair"] * hh         # 뒤로 흘러내리는 끝

    # 밑선에서 메시를 **실제로 자른다.** 자르지 않고 골라내기만 하면 케이지 격자가
    # 밑선에 맞아 있지 않아 끝이 톱니처럼 뜯긴다 — paint() 가 강조 띠에서 이미 겪고
    # 같은 방법으로 푼 문제다(그 주석 참고). 앞머리는 계단으로, 목덜미는 손가락
    # 여섯 개짜리 층계로 나왔다(렌더로 확인).
    #
    # 자르려면 밑선이 평면이어야 한다. 그래서 뒤쪽 기울기에서 smoothstep 을 뺐다 —
    # 매끄러운 곡선은 평면이 아니라 자를 수가 없고, 자르지 못하면 톱니가 남는다.
    # 곡선 한 번 대신 평면 두 장으로 꺾는다:
    #   앞(y < 머리중심): z = z_front            — 수평
    #   뒤(y >= 머리중심): z = z_front + m(y-hc.y) — 기울어짐
    # 두 장이 y=hc.y 선에서 만나므로 경계가 이어진다. 꺾인 자리는 귀 바로 위,
    # 머리가 가장 넓은 곳이다 — 원래 가르마가 앉는 자리다.
    #
    # 기울기를 **머리 깊이(y1-hc.y)가 아니라 머리 반지름의 절반**에 걸고, 거기서부터는
    # z_back 에 **수평으로 눕힌다**(평면 석 장). 처음엔 머리 깊이에 걸었는데,
    # 뒤에서 렌더를 보니 긴 머리(왕실 0.75 · 유랑 0.85)가 **두 덩이로 갈라져** 어깨에
    # 얹혀 있었다 — 등골을 따라 가운데가 뻥 뚫렸다. 까닭은 첫 번째 결함과 같은 종류다:
    # 밑선이 y 하나로 정해지는데 몸 표면에서 y 가 단조롭지 않다. 목덜미 한가운데는
    # 머리중심과 y 가 거의 같아서 밑선이 아직 앞머리선 높이에 있고(잘린다),
    # 견갑골은 y 가 커서 살아남는다. 그래서 가운데만 사라졌다.
    # 반지름 절반(약 6.3cm)이면 귀 뒤에서 이미 z_back 에 닿으므로 목덜미가 살아남는다.
    ramp = min(0.5 * rad, max(1e-6, y1 - hc.y))
    m_slope = (z_back - z_front) / ramp
    for co, no in ((Vector((0.0, 0.0, z_front)), Vector((0.0, 0.0, 1.0))),
                   (Vector((0.0, hc.y, z_front)),
                    Vector((0.0, -m_slope, 1.0)).normalized()),
                   (Vector((0.0, 0.0, z_back)), Vector((0.0, 0.0, 1.0)))):
        bmesh.ops.bisect_plane(
            b, geom=list(b.verts) + list(b.edges) + list(b.faces),
            plane_co=co, plane_no=no, dist=1e-5)
    skin = [v for v in b.verts if v[dl].get(gi["body"], 0.0) > 0.5]

    keep = set()
    for v in skin:
        # 어깨·팔을 뺀다. 머리통보다 굵은 것은 머리가 아니다 —
        # **다만 내려갈수록 넉넉해진다.** 처음엔 어디서나 rad*1.15 로 끊었더니
        # 긴 머리(귀족 0.70 위)가 목덜미에서 실오라기처럼 가늘어져 **쥐꼬리**가 됐다.
        # 옆에서 렌더를 보고 알았다. 까닭은 간단하다 — 머리통 아래는 목이라
        # 머리통 굵기로 자르면 목 굵기만 남는다. 긴 머리는 목에 매달리는 게 아니라
        # 등에 얹히므로, 밑으로 갈수록 허용 반지름을 키운다(끝에서 1.70배).
        down = 0.0 if v.co.z >= hc.z else \
            max(0.0, min(1.0, (hc.z - v.co.z) / max(1e-6, hc.z - z_back)))
        if (Vector((v.co.x, v.co.y, 0.0)) - Vector((hc.x, hc.y, 0.0))).length \
                > rad * (1.15 + 0.55 * down):
            continue
        # 밑선은 **뒤통수 쪽으로만** 내려간다. 앞쪽은 앞머리선에서 평평하게 끊는다.
        #
        # 처음엔 코끝(y0)에서 뒤통수(y1)까지 한 번에 기울였다. 얼굴이 통째로
        # 덮였다 — 코는 y 로 튀어나와 있지만 눈·뺨·입은 그만큼 안 나와서,
        # 「앞일수록 높다」는 규칙이 얼굴 한가운데를 뒤통수처럼 취급했다.
        # 렌더를 보고서야 알았다(코와 입술이 머리카락이 되어 있었다).
        # 그래서 기준을 코끝이 아니라 **머리중심**으로 옮긴다. 머리중심보다
        # 앞은 전부 t=0 이라 앞머리선 한 장으로 끊기고, 경계에서 t=0 이므로
        # 앞뒤가 이어진다 — 관자놀이에 단이 지지 않는다.
        lo = max(z_back, z_front + m_slope * max(0.0, v.co.y - hc.y))
        if v.co.z < lo - 1e-6:
            continue
        keep.add(v)
    bmesh.ops.delete(b, geom=[v for v in b.verts if v not in keep],
                     context="VERTS")
    if not b.verts:
        b.free(); bpy.data.objects.remove(hair); return None

    b.normal_update()
    for v in b.verts:
        out = v.co - hc
        out = out.normalized() if out.length > 1e-6 else v.normal.copy()
        # 정수리는 법선대로, 목덜미는 바깥으로. 목덜미에서 법선만 쓰면
        # 머리카락이 목 안쪽으로 말려 들어간다.
        down = max(0.0, min(1.0, (hc.z - v.co.z) / max(1e-6, hc.z - z_back)))
        v.co += (v.normal * (1.0 - 0.6 * down) + out * (0.6 * down)) * G.LIFT
    bmesh.ops.solidify(b, geom=list(b.faces), thickness=-G.LIFT * 0.55)
    b.to_mesh(me)
    b.free()
    for p in me.polygons:
        p.use_smooth = True
    return hair


def add_cape(bm_obj, sp, L):
    """망토 — 귀족. 등 쪽 케이지를 떠서 뒤로 흘린다."""
    me = bm_obj.data.copy()
    cape = bpy.data.objects.new(f"cape_{sp['slug']}", me)
    bpy.context.collection.objects.link(cape)
    for g in bm_obj.vertex_groups:
        cape.vertex_groups.new(name=g.name)
    gi = {g.name: g.index for g in cape.vertex_groups}

    # 어깨선에서 시작해 옷단보다 더 내려간다.
    top = L["clav_z"] + 0.02 * L["height"]
    # 옷단까지 내리면 발목 위까지 온다. 그러면 아래가 넓은 상자가 되고
    # 몸에서 떨어진 판때기로 보였다. 무릎께에서 끊는다.
    bottom = L["z0"] + 0.32 * L["height"]

    b = bmesh.new()
    b.from_mesh(me)
    dl = b.verts.layers.deform.active
    keep = []
    for v in b.verts:
        if v[dl].get(gi["helper-tights"], 0.0) <= 0.5:
            continue
        if not (bottom <= v.co.z <= top):
            continue
        if v.co.y < 0.005:            # 등 쪽(+Y)만
            continue
        if abs(v.co.x) > L["shoulder_x"] * 1.35:   # 팔은 뺀다
            continue
        keep.append(v.index)
    bmesh.ops.delete(b, geom=[v for v in b.verts if v.index not in keep],
                     context="VERTS")
    if len(b.verts) < 8:
        b.free()
        bpy.data.objects.remove(cape)
        return None
    b.normal_update()
    for v in b.verts:
        # 어깨에서 멀어질수록 몸에서 떨어진다. 아래로 갈수록 퍼진다.
        t = max(0.0, min(1.0, (top - v.co.z) / max(1e-6, top - bottom)))
        # 0.30 으로 벌렸을 때는 앞에서 보면 관리의 코트와 같았다. 망토는
        # 등 뒤에 있어서, 몸 옆으로 삐져나오지 않으면 정면 실루엣에 없다.
        # 어깨너비의 두 배 가까이 퍼뜨려야 비로소 "망토"로 읽힌다.
        # t 를 그대로 쓰면 아래에서만 급히 벌어져 모서리가 각진다.
        # 0.75 제곱으로 눌러 위에서부터 서서히 퍼뜨린다 — 사다리꼴이 된다.
        f = t ** 0.75
        v.co.y += (0.015 + 0.100 * f)
        v.co.x *= 1.0 + 0.75 * f
    bmesh.ops.solidify(b, geom=list(b.faces), thickness=-sp["thick"])
    b.to_mesh(me)
    b.free()
    for p in me.polygons:
        p.use_smooth = True
    return cape


# ---------------------------------------------------------------- 마무리
def paint(ob, sp, L, mat_cloth, mat_accent):
    """머티리얼 두 칸. 0번은 천, 1번은 강조색 자리.

    면의 무게중심 높이로만 고르면 강조색 경계가 톱니처럼 뜯긴다.
    케이지 격자가 가로줄에 맞춰져 있지 않아서, 띠 높이를 걸친 면들이
    들쭉날쭉 잘리기 때문이다. 웹 뷰어에서 왕실 어깨 장식이 찢어진
    종이처럼 보였다.

    그래서 먼저 띠의 위·아래 높이에서 메시를 실제로 자른다. 자르고 나면
    어떤 면도 경계를 걸치지 않으므로 무게중심으로 골라도 선이 곧다.
    셰이더로 처리하지 않고 지오메트리로 푸는 이유는, 이렇게 해 두면
    유니티든 웹이든 무엇으로 그리든 같은 선이 나오기 때문이다.
    """
    ob.data.materials.append(mat_cloth)
    ob.data.materials.append(mat_accent)
    band = sp["accent"]
    if not band:
        return 0
    lo = L["z0"] + band[0] * L["height"]
    hi = L["z0"] + band[1] * L["height"]

    b = bmesh.new()
    b.from_mesh(ob.data)
    for z in (lo, hi):
        bmesh.ops.bisect_plane(
            b, geom=list(b.verts) + list(b.edges) + list(b.faces),
            plane_co=Vector((0.0, 0.0, z)), plane_no=Vector((0.0, 0.0, 1.0)),
            dist=1e-5)
    b.to_mesh(ob.data)
    b.free()

    n = 0
    for p in ob.data.polygons:
        p.use_smooth = True
        z = sum(ob.data.vertices[i].co.z for i in p.vertices) / len(p.vertices)
        if lo <= z <= hi:
            p.material_index = 1
            n += 1
    return n


def assemble(bm_obj, arm, sp, L, name):
    """옷 한 벌을 조립한다 — 깎고 · 덧대고 · 칠하고 · 머리카락을 얹어 합친다.

    이 함수가 있는 이유는 하나다. 전에는 make_garments 의 55벌 루프와
    make_demo 의 한 벌 굽기가 **같은 순서를 따로 적고 있었다.** 그래서
    머리카락을 넣었을 때 55벌에는 붙고 데모/전승 GLB 에는 안 붙었다.
    이 저장소가 이미 두 번 당한 일이다(뷰어 STEP 과 probe 의 베낀 상수).
    순서를 고칠 일이 생기면 여기 한 곳만 고친다.
    """
    cloth = bpy.data.materials.new("cloth")
    accent = bpy.data.materials.new("accent")
    # 머리카락은 천이 아니다 — 계층 색도 강조 띠도 받으면 안 된다.
    # 그래서 paint() 의 두 칸이 아니라 제 칸을 가진다. 이름으로 갈린다:
    # 뷰어는 재질 **이름**으로 색을 고르고(viewer/garden.html litMat),
    # 유니티는 칸 수만 세어 실루엣 재질로 덮는다(IremChar.Paint).
    # 그래서 칸이 둘에서 셋이 되어도 양쪽 다 고칠 데가 없다.
    hairmat = bpy.data.materials.new("hair")

    parts = [carve(bm_obj, arm, sp, L)]
    if sp["hood"]:
        h = add_hood(bm_obj, sp, L)
        if h:
            parts.append(h)
    if sp["cape"]:
        c = add_cape(bm_obj, sp, L)
        if c:
            parts.append(c)
    for p in parts:
        paint(p, sp, L, cloth, accent)
    # 칠한 **뒤에** 붙인다. paint() 에 넣으면 머리에 강조 띠가 걸린다.
    hr = add_hair(bm_obj, sp, L)
    if hr:
        hr.data.materials.append(hairmat)
        parts.append(hr)
    # 몇 조각을 합쳤는지는 부른 쪽이 report 에 적는다. 셋는 자리가 여기뿐이므로
    # 조각을 물건에 적어서 돌려준다 — 밖에서 다시 세면 또 두 벌이 된다.
    ob = join(parts, name)
    ob["parts"] = len(parts)
    return ob


def join(objs, name):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = ob.data.name = name
    return ob


def bind(ob, arm):
    """뼈에 물린다. 웨이트는 케이지에서 따라왔으므로 모디파이어만 붙이면 된다.

    **이미 붙어 있으면 그것을 쓴다.** 옷은 맨몸이라 새로 붙이면 되지만,
    몸에는 MPFB 의 add_builtin_rig 가 이미 ARMATURE 를 하나 달아 놓았다.
    거기에 하나를 더 붙이면 뼈 회전이 **두 번** 먹는다. 손가락 24도가
    48도가 되고, 휘두름의 80도는 살이 국수처럼 늘어나 터진다.
    실제로 그렇게 터진 것을 확인 시트에서 보고 여기까지 왔다.
    """
    ob.parent = arm
    m = next((x for x in ob.modifiers if x.type == "ARMATURE"), None)
    if m is None:
        m = ob.modifiers.new("Armature", "ARMATURE")
    m.object = arm
    # 뼈가 아닌 그룹(helper-* · joint-* 등)은 내보낼 때 짐만 된다.
    names = {b.name for b in arm.data.bones}
    for g in [g for g in ob.vertex_groups if g.name not in names]:
        ob.vertex_groups.remove(g)


def solidify_check(ob):
    me = ob.data
    q = sum(1 for p in me.polygons if len(p.vertices) == 4)
    t = sum(1 for p in me.polygons if len(p.vertices) == 3)
    tris = q * 2 + t
    return len(me.vertices), len(me.polygons), tris


# ---------------------------------------------------------------- 실루엣 사진
def setup_shot(res=(256, 384)):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sh = sc.display.shading
    sh.light = "FLAT"
    sh.color_type = "SINGLE"
    sh.single_color = (0.0, 0.0, 0.0)
    sh.show_object_outline = False
    sh.show_specular_highlight = False


def shoot(path, height, z0):
    """앞에서 정사영으로 한 장. 실루엣만 본다 — 아트 문서가 그렇게 못박았다."""
    cam_data = bpy.data.cameras.new("shotcam")
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = height * 1.15
    cam = bpy.data.objects.new("shotcam", cam_data)
    bpy.context.collection.objects.link(cam)
    cam.location = (0.0, -5.0, z0 + height * 0.5)
    cam.rotation_euler = (math.radians(90), 0.0, 0.0)
    bpy.context.scene.camera = cam
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam)
    bpy.data.cameras.remove(cam_data)


# ---------------------------------------------------------------- 본체
def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="chars/out/garments")
    ap.add_argument("--shots", default=None, help="실루엣 PNG 를 낼 곳")
    ap.add_argument("--roles", default=None)
    ap.add_argument("--classes", default=None)
    # 화폭 크기. 기본은 지금까지 쓴 자다. 넓힌 자로 다시 잴 때만 바꾼다 —
    # ortho_scale 은 긴 변에 걸리므로 384x384 로 하면 사람 크기는 그대로이고
    # 양옆에 종이만 붙는다. docs/실험/…소지품…결과.md 참고.
    ap.add_argument("--res", default="256x384")
    args = ap.parse_args(argv)
    res = tuple(int(x) for x in args.res.lower().split("x"))

    os.makedirs(args.out, exist_ok=True)
    if args.shots:
        os.makedirs(args.shots, exist_ok=True)
        setup_shot(res)

    roles = list(BODIES)
    if args.roles:
        roles = [r for r in roles if r in args.roles.split(",")
                 or BODY_SLUG[r] in args.roles.split(",")]
    classes = list(G.ROBE)
    if args.classes:
        classes = [c for c in classes if c in args.classes.split(",")
                   or G.SLUG[c] in args.classes.split(",")]

    report = []
    for role in roles:
        bslug = BODY_SLUG[role]
        for cls in classes:
            sp = G.spec(cls)
            bm, arm = build_body(role)
            L = landmarks(bm, arm)

            name = f"{bslug}_{sp['slug']}"
            ob = assemble(bm, arm, sp, L, f"garment_{name}")
            acc_faces = sum(1 for p in ob.data.polygons if p.material_index == 1)
            bind(ob, arm)

            v, f, tris = solidify_check(ob)
            MB.export([ob, arm], os.path.join(args.out, name))

            if args.shots:
                shoot(os.path.join(args.shots, name + ".png"),
                      L["height"], L["z0"])

            report.append(dict(role=role, body=bslug, cls=cls, slug=sp["slug"],
                               robe=sp["robe"], hem=sp["hem"],
                               verts=v, faces=f, tris=tris,
                               accent_faces=acc_faces,
                               parts=int(ob["parts"])))
            print(f"  {name:20s} {cls:4s} {sp['robe']:6s} "
                  f"정점 {v:5,}  삼각 {tris:6,}  강조면 {acc_faces:4d}", flush=True)

    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)
    print(f"[make_garments] {len(report)}벌 → {args.out}", flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(argv)
