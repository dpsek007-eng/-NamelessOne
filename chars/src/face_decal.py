# -*- coding: utf-8 -*-
"""얼굴 데칼 — 2D 초상에서 얼굴을 잘라 3D 머리 앞에 붙인다.

    # 1단계: 얼굴 데칼 이미지 생성 (PIL)
    python3 chars/src/face_decal.py --crop --char north_gatekeeper

    # 2단계: Blender 에서 3D 머리에 데칼 붙여서 GLB 내보내기
    blender --background --python chars/src/face_decal.py -- \
            --char north_gatekeeper --role 수호 --cls 병졸 --out chars/out/demo

초점(포커스) 시스템과 달리, 이 데칼은 3D 캐릭터의 머리에 붙는 것이다.
머리 뼈(head)에 부모를 두어서, 캐릭터가 고개를 돌리면 얼굴도 따라돈다.

二人은 MPFB 머리가 눈·코·입을 메시로 가지고 있어서, 데칼이
그 위에 얹히면 이목구비가 보인다. 뼈가 53개 다 몸통·팔다리뿐이라
표정은 못 움직이지만, 최소한 "얼굴이 있는 3D 캐릭터"는 된다.
"""
import argparse, json, math, os, sys

# ---------------------------------------------------------------------------
# 1단계: 얼굴 크롭 + 데칼 이미지 생성
# ---------------------------------------------------------------------------

def crop_face(roster_path, atlas_path, char_id, out_path, scale=2):
    """roster.json + atlas 에서 얼굴을 잘라낸다.

    scale=2 이면 384px 셀을 768px 로 키워서 크롭한다.
    """
    from PIL import Image

    with open(roster_path, encoding="utf-8") as f:
        roster = json.load(f)

    cell = roster["cell"]  # 384
    cols = roster["cols"]  # 5

    ch = None
    for c in roster["chars"]:
        if c["id"] == char_id:
            ch = c
            break
    if ch is None:
        raise SystemExit(f"캐릭터 '{char_id}' 를 못 찾았다")

    fbox = ch["fbox"]  # [x, y, w, h] — 셀 내 상대 좌표 (0~1)
    col, row = ch["col"], ch["row"]

    # 셀 절대 좌표
    x0 = col * cell
    y0 = row * cell

    # fbox → 픽셀
    fx = x0 + fbox[0] * cell
    fy = y0 + fbox[1] * cell
    fw = fbox[2] * cell
    fh = fbox[3] * cell

    img = Image.open(atlas_path)

    # 스케일 업
    if scale > 1:
        fx *= scale; fy *= scale; fw *= scale; fh *= scale
        img = img.resize((img.width * scale, img.height * scale), Image.LANCZOS)

    # 정사각형으로 크롭 (fbox 는 정사각형)
    side = max(fw, fh)
    # 중앙 기준
    cx = fx + fw / 2
    cy = fy + fh / 2
    box = (cx - side / 2, cy - side / 2, cx + side / 2, cy + side / 2)

    face = img.crop(box)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    face.save(out_path)
    print(f"[face_decal] 크롭 {char_id}: {face.size[0]}x{face.size[1]}px → {out_path}",
          flush=True)
    return face, ch


def make_decal(face_img, ch, out_path, head_w=197, head_h=249):
    """크롭한 얼굴을 스킨색 캔버스에 붙여서 데칼 PNG 를 만든다.

    캔버스는 3D 머리의 전면 실루엣 비율(head_w x head_h)로 잡는다.
    얼굴은 눈 높이에 맞춰서 위쪽 40% 지점에 배치한다 — MPFB 머리의
    눈선이 대략 위에서 42% 지점이기 때문이다.
    """
    from PIL import Image

    # 스킨색 (make_demo.py skin.diffuse_color 와 같다)
    SKIN = (173, 140, 120)

    # 캔버스는 머리 비율의 4배 해상도 — 197x249 그대로 쓰면
    # 얼굴에 픽셀 블록이 그대로 보인다 (크롭 원본이 768px 이다).
    RES = 4
    canvas_w = head_w * RES
    canvas_h = head_h * RES
    # 배경은 투명 — 얼굴 타원만 남긴다. 카드처럼 붙는 게 아니라
    # 얼굴 부분만 머리 앞에 뜨게 하기 위함이다.
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 초상에 구워진 그림자(모자·관자놀이)가 3D 조명 아래서는 멍처럼
    # 보인다 — 감마 0.75 로 어두운 부분만 들어올린다 (밝은 곳은 거의
    # 그대로다).
    lut = [round(255 * (i / 255) ** 0.75) for i in range(256)]
    if face_img.mode != "RGB":
        face_img = face_img.convert("RGB")
    face_img = face_img.point(lut * 3)

    # 얼굴을 머리 비율에 맞게 리사이즈
    # 얼굴은 머리 너비의 약 75% 를 차지한다
    target_fw = int(canvas_w * 0.75)
    # 얼굴 지오메트리를 뭉갠 뒤로는 몸의 입술 위치에 맞출 필요가
    # 없다 — 초상 비율을 거의 그대로 쓴다 (1.25 는 입이 턱까지 내려갔다).
    V_STRETCH = 1.05
    target_fh = int(target_fw * V_STRETCH)
    face_resized = face_img.resize((target_fw, target_fh), Image.LANCZOS).convert("RGBA")

    # 타원 알파 마스크 — 가장자리를 부드럽게 깎는다.
    # 초상 위쪽엔 모자·머리카락이 걸리므로 타원 윗변을 내려서 자른다.
    from PIL import ImageDraw, ImageFilter
    mask = Image.new("L", (target_fw, target_fh), 0)
    d = ImageDraw.Draw(mask)
    # 0.10 은 관자놀이의 모자 그림자가 눈 옆 검은 삼각형으로 남았다
    pad = int(target_fw * 0.13)   # 좌우 옆머리카락·관자놀이 음영을 자른다
    bot = int(target_fh * 0.04)   # 아래는 턱·입술을 살린다
    # 윗변은 눈썹 바로 위 — 0.32 는 눈썹을 지나 블러가 눈까지 지웠고,
    # 0.20 은 모자챙 그림자(0.18~0.25)가 이마에 검은 띠로 남았다 (실측:
    # 크롭에서 눈선이 36%, 눈썹이 ~26% 지점이다).
    top = int(target_fh * 0.24)
    d.ellipse((pad, top, target_fw - pad, target_fh - bot), fill=255)
    # 블러 4% 는 눈썹·눈까지 번져 유령처럼 흐려졌다 — 2.5% 로 좁힌다.
    mask = mask.filter(ImageFilter.GaussianBlur(int(target_fw * 0.025)))
    face_resized.putalpha(mask)

    # 배치: 크롭의 눈선(위에서 36%)이 머리의 눈높이에 오게 붙인다.
    # 이미지 '중심'을 눈높이에 두면 눈이 캔버스 39% 지점으로 올라가
    # 타원 가장자리에 걸렸다 (실측).
    EYE_IN_CROP = 0.36   # roster 크롭에서 눈선의 세로 위치
    # 0.465 는 눈이 눈썹 아래 급경사에 얹혀 세로로 눌려 보였다 —
    # 뭉갬을 40회로 올린 뒤로는 자국이 없어서 평평한 0.49 로 되돌린다.
    eye_y_ratio = 0.49
    paste_cx = canvas_w // 2
    paste_cy = int(canvas_h * eye_y_ratio)

    px = paste_cx - face_resized.width // 2
    py = paste_cy - int(EYE_IN_CROP * target_fh)

    canvas.paste(face_resized, (px, py), face_resized)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path)
    print(f"[face_decal] 데칼 {canvas_w}x{canvas_h} → {out_path}", flush=True)
    return canvas


# ---------------------------------------------------------------------------
# 2단계: Blender 에서 데칼을 머리 앞에 붙이고 GLB 로 내보내기
# ---------------------------------------------------------------------------

def build_faced_glb(char_id, role, cls, decal_path, out_dir, head_w_m=0.197, head_h_m=0.249):
    """Blender 에서 body + face plane + rig + animations 를 GLB 로.

    얼굴 데칼은 flat quad 로 만들어서 머리 앞에 붙인다.
    머리 뼈(head)에 부모를 두어서 고개가 돌아가면 같이 돈다.
    """
    import bpy

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import make_garments as MG
    import make_bodies as MB
    import garments as G
    import make_demo as MD
    from bodies import SLUG as BODY_SLUG

    os.makedirs(out_dir, exist_ok=True)

    # --- 몸 + 옷 + 리그 + 동작 (make_demo.one 과 같은 순서) ---
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)

    sp = G.spec(cls)
    bm, arm = MG.build_body(role)
    L = MG.landmarks(bm, arm)

    # 옷
    cloth = bpy.data.materials.new("cloth")
    accent = bpy.data.materials.new("accent")
    parts = [MG.carve(bm, arm, sp, L)]
    if sp["hood"]:
        h = MG.add_hood(bm, sp, L)
        if h:
            parts.append(h)
    if sp["cape"]:
        c = MG.add_cape(bm, sp, L)
        if c:
            parts.append(c)
    for p in parts:
        MG.paint(p, sp, L, cloth, accent)
    gar = MG.join(parts, f"garment_{BODY_SLUG[role]}_{sp['slug']}")
    MG.bind(gar, arm)

    # 몸에서 케이지 제거 + 스킨 머티리얼
    bpy.context.view_layer.objects.active = bm
    for m in [m for m in bm.modifiers if m.type == "MASK"]:
        bpy.ops.object.modifier_apply(modifier=m.name)
    bm.name = bm.data.name = f"body_{BODY_SLUG[role]}"

    # --- 안구·치아·혀 헬퍼 제거 ---
    # 이 지오메트리가 데칼을 뚫고 나온다 (눈의 흰 반구, 입 밑 이빨 알갱이).
    # 눈·입은 데칼 그림이 대신하므로 3D 쪽은 지운다.
    DEL_GROUPS = ["helper-l-eye", "helper-r-eye",
                  "helper-upper-teeth", "helper-lower-teeth", "helper-tongue",
                  "helper-l-eyelashes-1", "helper-l-eyelashes-2",
                  "helper-r-eyelashes-1", "helper-r-eyelashes-2",
                  "JointCubes", "HelperGeometry"]
    didx = {bm.vertex_groups[n].index for n in DEL_GROUPS
            if n in bm.vertex_groups}
    if os.environ.get("FD_DEBUG"):
        print("  [debug] 버텍스그룹 전체:",
              sorted(g.name for g in bm.vertex_groups), flush=True)
        for n in DEL_GROUPS:
            if n in bm.vertex_groups:
                gx = bm.vertex_groups[n].index
                cnt = sum(1 for v in bm.data.vertices
                          for g in v.groups if g.group == gx and g.weight > 0.1)
                print(f"  [debug] {n}: {cnt}개", flush=True)
            else:
                print(f"  [debug] {n}: 그룹 없음", flush=True)
    if didx:
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        n_sel = 0
        for v in bm.data.vertices:
            if any(g.group in didx and g.weight > 0.1 for g in v.groups):
                v.select = True
                n_sel += 1
        print(f"[face_decal] 헬퍼 정점 {n_sel}개 지움", flush=True)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.delete(type="VERT")
        bpy.ops.object.mode_set(mode="OBJECT")

    # --- 얼굴 앞면을 뭉갠다 — 마네킹처럼 ---
    # 몸의 눈꺼풀 융기·입술 틈·콧날이 데칼 그림과 싸운다: 눈꺼풀이
    # 그린 눈을 가리고, 입술 틈이 폴드를 만들어 입이 비뚤어지고,
    # 콧날 경사가 텍스처를 늘인다 (실측). 얼굴은 그림이 전담하고
    # 지오메트리는 매끈한 달걀면만 남긴다.
    hgi = bm.vertex_groups["head"].index
    egi = bm.vertex_groups["ears"].index if "ears" in bm.vertex_groups else -1

    def _w(v, idx):
        if idx < 0:
            return 0.0
        for g in v.groups:
            if g.group == idx:
                return g.weight
        return 0.0

    # 정점 참조는 EDIT<->OBJECT 왕복에서 무효가 된다(세그폴트) —
    # 인덱스만 들고 다니고, 선택할 때마다 새로 잡는다.
    head_info = [(v.index, v.co.y) for v in bm.data.vertices
                 if _w(v, hgi) > 0.3 and _w(v, egi) < 0.3]
    ys = [y for _, y in head_info]
    fy0, fy1 = min(ys), max(ys)
    if os.environ.get("FD_DEBUG"):
        # 눈썹 아치 상자 (앞면, 눈 위): 어떤 정점이고 왜 안 녹나
        hi_set = {i for i, _ in head_info}
        arc = [v for v in bm.data.vertices
               if 1.675 < v.co.z < 1.715 and 0.012 < abs(v.co.x) < 0.055
               and v.co.y < -0.10]
        print(f"  [debug] 아치 상자 정점 {len(arc)}개", flush=True)
        import collections
        why = collections.Counter()
        for v in arc:
            if v.index in hi_set:
                why["head_info 포함(녹음)"] += 1
            elif _w(v, hgi) <= 0.3:
                gs = sorted(((bm.vertex_groups[g.group].name, round(g.weight, 2))
                             for g in v.groups), key=lambda t: -t[1])[:3]
                why[f"head<=0.3 상위그룹 {gs}"] += 1
            else:
                why["ears>=0.3"] += 1
        for k, c in why.most_common(8):
            print(f"  [debug]   {c:4d} × {k}", flush=True)

    def _smooth_sel(idxs, factor, repeat):
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        mv = bm.data.vertices
        for i in idxs:
            mv[i].select = True
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.vertices_smooth(factor=factor, repeat=repeat)
        bpy.ops.object.mode_set(mode="OBJECT")

    # 코만 남기고 앞면 전부를 녹인다. 예전엔 "맨 앞 12% 깊이"를
    # 통째로 예외로 뒀는데, 실측하니 그 깊이 대역이 높이 16cm
    # (1.59~1.75m)를 덮어 눈썹·눈꺼풀 융기(1.69~1.75, ~230정점)까지
    # 안 녹고 데칼을 뚫고 나왔다 — 그린 눈 위에 창백한 아치가 겹쳤다.
    # 코는 깊이가 아니라 상자다: 머리 맨 앞 정점(코끝) 주변
    # 높이 ±3cm, 좌우 ±2.5cm.
    rng = fy1 - fy0
    nose_keep = fy0 + 0.12 * rng
    mv = bm.data.vertices
    tip_i = min(head_info, key=lambda t: t[1])[0]
    tip_co = mv[tip_i].co.copy()
    nose_ids = {i for i, y in head_info
                if y < nose_keep
                and abs(mv[i].co.z - tip_co.z) < 0.03
                and abs(mv[i].co.x - tip_co.x) < 0.025}
    # 1차: 얼굴 핵심(앞 55%)을 강하게 — 눈구멍·눈꺼풀·입술을 녹인다
    core = [i for i, y in head_info
            if y < fy0 + 0.55 * rng and i not in nose_ids]
    _smooth_sel(core, 0.5, 40)
    # 코는 아예 녹이지 않는다 — 계단 자국의 진범은 플랫 셰이딩이었다
    # (shade_smooth 로 해결). 4회짜리 2차 패스도 코 돌출을 눈에 띄게
    # 줄이므로 코를 뺀다.
    # 2차: 좀 더 넓게(앞 70%) 약하게 — 뭉갠 경계를 부드럽게 잇는다
    wide = [i for i, y in head_info
            if y < fy0 + 0.70 * rng and i not in nose_ids]
    _smooth_sel(wide, 0.5, 4)
    # 3차: 눈 아몬드만 소프필름으로. 40회 스무딩은 폭 2cm 눈구멍
    # 융기를 못 지운다 (라플라시안은 넓은 형상일수록 느리게 붕괴 —
    # 데칼 없이 몸만 찍어 확인: 창백한 아몬드 두 개가 그대로).
    # 작은 선택만 돌리면 미선택 이웃이 고정 경계가 되어 수백 회에
    # 비눗막처럼 수렴한다 — 눈 상자(코끝 기준 위 2.5~7cm,
    # 좌우 0.8~6cm)만 300회.
    mv = bm.data.vertices   # EDIT 왕복 뒤 이전 참조는 죽어 있다 — 재조회
    eye_ids = [i for i, y in head_info
               if y < fy0 + 0.5 * rng
               and tip_co.z + 0.025 <= mv[i].co.z <= tip_co.z + 0.07
               and 0.008 <= abs(mv[i].co.x - tip_co.x) <= 0.06]
    _smooth_sel(eye_ids, 0.5, 300)
    print(f"[face_decal] 눈 아몬드 비눗막 {len(eye_ids)}개 정점", flush=True)
    print(f"[face_decal] 얼굴 앞면 뭉갬 — 핵심 {len(core)} / 경계 {len(wide)} 정점",
          flush=True)

    # --- 스킨 머티리얼 — make_demo 와 같은 flat color ---
    # 데칼 텍스처를 몸 UV 에 그대로 입히면 몸 전체가 오염된다.
    # 몸은 민색으로 두고, 얼굴은 별도 평면으로 붙인다.
    skin = bpy.data.materials.new("skin")
    skin.diffuse_color = (0.68, 0.55, 0.47, 1.0)
    # Blender 5.x 는 새 머티리얼에 노드가 켜져 있다 — Principled 의
    # Base Color 도 같이 맞춰야 glTF 로 살색이 나간다.
    if skin.node_tree:
        pn = skin.node_tree.nodes.get("Principled BSDF")
        if pn:
            pn.inputs["Base Color"].default_value = (0.68, 0.55, 0.47, 1.0)
    bm.data.materials.clear()
    bm.data.materials.append(skin)
    MG.bind(bm, arm)

    # --- 머리 실물 재기 — head 그룹 정점의 bbox ---
    # MPFB 는 -Y 가 앞이다. 평면은 얼굴 앞(y 최소)보다 살짝 더 앞에 세운다.
    grp = bm.vertex_groups.get("head")
    if grp is None:
        raise SystemExit("head 버텍스그룹이 없다")
    gi = grp.index
    co = [v.co for v in bm.data.vertices
          for g in v.groups if g.group == gi and g.weight > 0.5]
    hx0 = min(c.x for c in co); hx1 = max(c.x for c in co)
    hy0 = min(c.y for c in co)
    hz0 = min(c.z for c in co); hz1 = max(c.z for c in co)
    head_cx = (hx0 + hx1) / 2
    head_cz = (hz0 + hz1) / 2
    head_w_m = hx1 - hx0
    head_h_m = hz1 - hz0

    # 데칼 격자: 머리 너비 x 높이 (약간 크게). 평평한 판을 띄우면
    # 옆에서 붕 떠 보인다 — 격자로 만들어 얼굴 곡면에 밀착시킨다.
    plane_w = head_w_m * 1.05
    plane_h = head_h_m * 1.05

    bpy.ops.mesh.primitive_grid_add(
        x_subdivisions=96, y_subdivisions=96, size=1,   # 48 은 면 왜곡이 블록으로 보였다
        location=(head_cx, hy0 - 0.05, head_cz),
        rotation=(math.pi / 2, 0, 0))   # XY 평면 → 세워서 -Y(앞)를 본다
    face_ob = bpy.context.view_layer.objects.active
    face_ob.name = f"face_{char_id}"
    face_ob.scale = (plane_w, plane_h, 1.0)
    bpy.ops.object.transform_apply(scale=True, rotation=True)

    # 몸에는 눈구멍·입이 뻥 뚫려 있다 (실측: 민머리 렌더에 검은 구멍).
    # PROJECT 광선이 그 구멍으로 들어가 두개골 안쪽에 맺히면 데칼이
    # 깔때기처럼 파인다. 그래서 구멍을 메운 프록시 복제본에 쏜다.
    proxy_data = bm.data.copy()
    proxy = bpy.data.objects.new("shrink_proxy", proxy_data)
    bpy.context.collection.objects.link(proxy)
    import bmesh
    pb = bmesh.new()
    pb.from_mesh(proxy_data)
    caps = bmesh.ops.holes_fill(pb, edges=pb.edges[:], sides=0)
    print(f"[face_decal] 프록시 캡 {len(caps['faces'])}개", flush=True)
    # (프록시를 달걀처럼 통째로 뭉개는 시도는 실패 — 프록시가 몸
    # 표면에서 1~2cm 벗어나 데칼이 껍데기처럼 떠 보였다, 실측.
    # 눈구멍 주머니는 몸 자체의 눈 비눗막 패스가 없앤다.)
    pb.to_mesh(proxy_data)
    pb.free()

    # Shrinkwrap(PROJECT) — 격자를 +Y(뒤)로 쏘아 얼굴 표면에 입힌다.
    # (전체를 NEAREST 로 하면 가장자리 정점이 머리 실루엣 능선에
    # 몰려 부채살로 접힌다 — 코를 뭉갠 뒤에도 마찬가지였다, 실측.)
    # project_limit: 입술 틈 따위로 새어 멀리 날아간 광선은 버린다.
    bpy.context.view_layer.objects.active = face_ob
    sw = face_ob.modifiers.new("Shrinkwrap", "SHRINKWRAP")
    sw.target = proxy
    sw.wrap_method = "PROJECT"
    sw.use_project_y = True
    sw.use_positive_direction = True
    sw.use_negative_direction = False
    sw.project_limit = 0.12
    sw.offset = 0.002   # 4mm 는 Displace 와 합쳐 데칼이 붕 떠 보였다
    bpy.ops.object.modifier_apply(modifier=sw.name)

    # 광선이 빗나간 정점은 판 위에 그대로 남아 옆에서 가시처럼
    # 튀어나온다 — 그 정점'만' NEAREST 로 구조한다. 이웃은 이미
    # 얼굴 위라 가까운 점이 바로 곁이고, 부채살은 안 생긴다.
    plane_y = hy0 - 0.05
    missed = [v.index for v in face_ob.data.vertices
              if abs(v.co.y - plane_y) < 1e-4]
    if missed:
        vg = face_ob.vertex_groups.new(name="missed")
        vg.add(missed, 1.0, "REPLACE")
        sw2 = face_ob.modifiers.new("Rescue", "SHRINKWRAP")
        sw2.target = proxy
        sw2.wrap_method = "NEAREST_SURFACEPOINT"
        sw2.offset = 0.002
        sw2.vertex_group = "missed"
        bpy.ops.object.modifier_apply(modifier=sw2.name)
        print(f"[face_decal] 빗나간 정점 {len(missed)}개 구조", flush=True)

    # 입술 틈으로 들어간 광선은 입안 벽에 맺힌다 (limit 안이라 못
    # 거른다) — 이웃 평균보다 3mm 이상 깊이 박힌 정점을 끌어올린다.
    # 반드시 얼굴 중앙 기둥(입이 있는 곳)만: 전체에 걸면 옆얼굴의
    # 가파른 경사면 정점이 실루엣 림에 접힌 이웃보다 "깊어" 보여
    # 3패스에 걸쳐 데칼 옆면 전체가 앞으로 끌려나온다 — 실측 눈가
    # 12~21mm 부양, "눈이 붕 떠 있다"의 진범.
    fb = bmesh.new()
    fb.from_mesh(face_ob.data)
    dived = 0
    for _ in range(3):
        for v in fb.verts:
            if abs(v.co.x - head_cx) > 0.025:
                continue
            ns = [e.other_vert(v) for e in v.link_edges]
            if not ns:
                continue
            avg = sum(n.co.y for n in ns) / len(ns)
            if v.co.y > avg + 0.003:
                v.co.y = avg
                dived += 1
    fb.to_mesh(face_ob.data)
    fb.free()
    print(f"[face_decal] 입안에 박힌 정점 {dived}개 끌어올림", flush=True)

    # 남은 잔주름을 편다 — 단 코(맨 앞 1.5cm)는 빼고.
    # 전체에 걸면 굴곡이 제일 큰 코가 도로 펴져 옆모습이 밋밋해진다.
    ymin = min(v.co.y for v in face_ob.data.vertices)
    flat_ids = [v.index for v in face_ob.data.vertices
                if v.co.y > ymin + 0.015]
    vg_flat = face_ob.vertex_groups.new(name="flat_zone")
    vg_flat.add(flat_ids, 1.0, "REPLACE")
    sm = face_ob.modifiers.new("Smooth", "SMOOTH")
    sm.factor = 1.0
    sm.iterations = 2
    sm.vertex_group = "flat_zone"
    bpy.ops.object.modifier_apply(modifier=sm.name)

    # 스무딩이 데칼을 눈꺼풀 융기 속으로 끌어들인다 —
    # 법선 방향으로 살짝 되밀어 그린 눈이 가려지지 않게 한다.
    # 4mm 는 데칼이 얼굴에서 붕 떠 보였다 (offset 과 합쳐 8mm).
    dp = face_ob.modifiers.new("Displace", "DISPLACE")
    dp.direction = "NORMAL"
    dp.mid_level = 0.0
    dp.strength = 0.0015
    bpy.ops.object.modifier_apply(modifier=dp.name)

    bpy.data.objects.remove(proxy, do_unlink=True)

    # 격자는 기본이 플랫 셰이딩 — 코 굴곡에서 면마다 음영이 갈라져
    # 블록 자국이 보인다. 반드시 스무스로 바꾼다.
    bpy.ops.object.shade_smooth()

    # 데칼 머티리얼
    decal_mat = bpy.data.materials.new("face_decal")
    decal_mat.use_nodes = True
    dt = decal_mat.node_tree
    dn = dt.nodes
    dl = dt.links

    for n in dn:
        dn.remove(n)

    d_out = dn.new("ShaderNodeOutputMaterial")
    d_out.location = (400, 0)

    d_bsdf = dn.new("ShaderNodeBsdfPrincipled")
    d_bsdf.location = (200, 0)
    dl.new(d_bsdf.outputs["BSDF"], d_out.inputs["Surface"])

    d_tex = dn.new("ShaderNodeTexImage")
    d_tex.location = (-200, 0)
    d_tex.image = bpy.data.images.load(decal_path)
    d_tex.image.alpha_mode = "STRAIGHT"

    dl.new(d_tex.outputs["Color"], d_bsdf.inputs["Base Color"])
    dl.new(d_tex.outputs["Alpha"], d_bsdf.inputs["Alpha"])

    if hasattr(decal_mat, "blend_method"):
        decal_mat.blend_method = "BLEND"   # 타원 가장자리가 부드럽게 섞인다
    face_ob.data.materials.append(decal_mat)

    # 데칼을 머리 뼈에 부모绑定
    face_ob.parent = arm
    # head 뼈에 웨이트 100%
    vg = face_ob.vertex_groups.new(name="head")
    for v in face_ob.data.vertices:
        vg.add([v.index], 1.0, 'REPLACE')

    # 아머티어 모디파이어 추가
    mod = face_ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm

    # --- 동작 네 벌 ---
    made = []
    for name, fn in MD.CLIPS:
        act = fn(arm)
        MD.stash(arm, act, name)
        made.append((name, int(act.frame_range[1] - act.frame_range[0]) + 1))

    # 쉼자세로 복귀
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()

    # --- 내보내기 ---
    slug = f"{BODY_SLUG[role]}_{sp['slug']}"
    out_path = os.path.join(out_dir, slug)

    # face_ob 를 export 대상에 포함
    MD.export_anim([bm, gar, face_ob, arm], out_path)

    report = dict(
        char_id=char_id, role=role, cls=cls, slug=slug,
        decal=decal_path,
        face_plane=f"{plane_w:.3f}x{plane_h:.3f}m",
        head_center=f"({L['head'].x:.3f}, {L['head'].y:.3f}, {L['head'].z:.3f})",
        clips=[dict(name=n, frames=f) for n, f in made],
    )
    print(f"[face_decal] GLB → {out_path}.glb  데칼 {plane_w:.3f}x{plane_h:.3f}m",
          flush=True)
    return report


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------

def main(argv):
    ap = argparse.ArgumentParser(description="얼굴 데칼 → 3D 캐릭터")
    ap.add_argument("--crop", action="store_true",
                    help="1단계: 얼굴 크롭 + 데칼 이미지 생성")
    ap.add_argument("--build", action="store_true",
                    help="2단계: Blender 에서 3D 데칼 부착 + GLB 내보내기")
    ap.add_argument("--char", default="north_gatekeeper",
                    help="캐릭터 ID (roster.json 기준)")
    ap.add_argument("--role", default="수호")
    ap.add_argument("--cls", default="병졸")
    ap.add_argument("--roster", default="art/gallery/roster.json")
    ap.add_argument("--atlas", default="art/gallery/roster.jpg")
    ap.add_argument("--out", default="chars/out/demo")
    ap.add_argument("--tmp", default="/tmp/face_decal")
    ap.add_argument("--scale", type=int, default=2,
                    help="크롭 스케일 (2=768px)")
    args = ap.parse_args(argv)

    if args.crop:
        decal_dir = os.path.join(args.tmp, "decals")
        face_path = os.path.join(decal_dir, f"{args.char}_face.png")
        decal_path = os.path.join(decal_dir, f"{args.char}_decal.png")

        face_img, ch = crop_face(args.roster, args.atlas, args.char,
                                 face_path, scale=args.scale)
        make_decal(face_img, ch, decal_path)
        print(json.dumps(dict(face=face_path, decal=decal_path,
                              char=args.char, fbox=ch["fbox"]),
                         ensure_ascii=False, indent=1))

    if args.build:
        decal_path = os.path.join(args.tmp, "decals", f"{args.char}_decal.png")
        if not os.path.exists(decal_path):
            print(f"[face_decal] 데칼이 없다: {decal_path}", file=sys.stderr)
            print(f"  먼저 --crop 을 돌려라", file=sys.stderr)
            sys.exit(1)

        report = build_faced_glb(args.char, args.role, args.cls,
                                 decal_path, args.out)
        # serve.py 호환: report.json 도 쓴다 (마지막 build 결과)
        report_path = os.path.join(args.out, "report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        # face_report.json 은 현재 빌드 상세 기록
        face_report_path = os.path.join(args.out, "face_report.json")
        with open(face_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    # Blender 는 인자를 "--" 뒤에 붙인다. 직접 실행은 그냥 1부터.
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
    else:
        argv = sys.argv[1:]
    main(argv)
