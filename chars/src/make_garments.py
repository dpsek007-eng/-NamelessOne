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
def build_body(role):
    """make_bodies 와 같은 순서. 다만 헬퍼를 남긴 채로 굽는다."""
    MB.wipe()
    bm = HumanService.create_human(
        mask_helpers=True, detailed_helpers=True, extra_vertex_groups=True,
        feet_on_ground=True,
        macro_detail_dict={**BODIES[role], "race": dict(RACE)})
    arm = HumanService.add_builtin_rig(bm, RIG, import_weights=True)
    HumanService.refit(bm)
    MB.bake_shape(bm, keep_helpers=True)
    bm.name = bm.data.name = f"body_{BODY_SLUG[role]}"
    arm.name = arm.data.name = f"rig_{BODY_SLUG[role]}"
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
    """머티리얼 두 칸. 0번은 천, 1번은 강조색 자리."""
    ob.data.materials.append(mat_cloth)
    ob.data.materials.append(mat_accent)
    band = sp["accent"]
    if not band:
        return 0
    lo = L["z0"] + band[0] * L["height"]
    hi = L["z0"] + band[1] * L["height"]
    n = 0
    for p in ob.data.polygons:
        z = sum(ob.data.vertices[i].co.z for i in p.vertices) / len(p.vertices)
        if lo <= z <= hi:
            p.material_index = 1
            n += 1
    return n


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
    """뼈에 물린다. 웨이트는 케이지에서 따라왔으므로 모디파이어만 붙이면 된다."""
    ob.parent = arm
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
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    if args.shots:
        os.makedirs(args.shots, exist_ok=True)
        setup_shot()

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

            cloth = bpy.data.materials.new("cloth")
            accent = bpy.data.materials.new("accent")

            parts = [carve(bm, arm, sp, L)]
            if sp["hood"]:
                h = add_hood(bm, sp, L)
                if h:
                    parts.append(h)
            if sp["cape"]:
                c = add_cape(bm, sp, L)
                if c:
                    parts.append(c)

            name = f"{bslug}_{sp['slug']}"
            for p in parts:
                paint(p, sp, L, cloth, accent)
            ob = join(parts, f"garment_{name}")
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
                               parts=len(parts)))
            print(f"  {name:20s} {cls:4s} {sp['robe']:6s} "
                  f"정점 {v:5,}  삼각 {tris:6,}  강조면 {acc_faces:4d}", flush=True)

    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)
    print(f"[make_garments] {len(report)}벌 → {args.out}", flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(argv)
