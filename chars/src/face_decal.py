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

    # 머리카락 색 표본 — fbox 바로 위 띠는 모발(수호는 투구)이다.
    # 배경 오염을 줄이려고 가로는 얼굴 가운데 절반만, 세로는 이마
    # 위 4~22% 띠만 쓰고, 채널별 중앙값을 취한다 (평균은 배경
    # 몇 픽셀에 끌려간다).
    b_hi, b_lo = HAIR_STYLE.get(char_id, {}).get("band", (0.22, 0.04))
    hb_x0 = fx + 0.25 * fw
    hb_x1 = fx + 0.75 * fw
    hb_y1 = fy - b_lo * fh
    hb_y0 = max(y0 * scale, fy - b_hi * fh)
    ch = dict(ch)
    if hb_y1 - hb_y0 > 4:
        band = img.crop((hb_x0, hb_y0, hb_x1, hb_y1)).convert("RGB")
        px = list(band.getdata())
        # 금속(투구)은 중앙값이 그늘에 끌려 탁해진다 — 밝은 쪽
        # 분위수를 쓴다 (수호 q=0.75, 나머지 0.5=중앙값)
        q = HAIR_STYLE.get(char_id, {}).get("q", 0.5)
        ch["hair_rgb"] = [sorted(c[i] for c in px)[int((len(px) - 1) * q)]
                          for i in range(3)]
    print(f"[face_decal] 크롭 {char_id}: {face.size[0]}x{face.size[1]}px → {out_path}"
          f"  머리색 {ch.get('hair_rgb')}", flush=True)
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
    # 보인다 — 감마로 어두운 부분만 들어올린다 (밝은 곳은 거의
    # 그대로다). 0.75 는 눈가·입꼬리가 여전히 멍처럼 남았다 (실측:
    # 데칼 얼굴 스크린샷) — 0.68 로 더 올린다.
    lut = [round(255 * (i / 255) ** 0.68) for i in range(256)]
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

    # --- 이목구비 줄 재기 (눈·콧구멍·입) ---
    # 초상마다 비율이 달라 한 점 핀으로는 안 맞는다 (실측 guard:
    # 그림 눈이 3D 눈보다 ~2cm 아래 뺨에 찍혀 "안 붙어" 보이고,
    # 입은 콧구멍 정렬에 1:1 로 딸려 올라가 "너무 위"였다).
    # 세 줄을 각각 재서 기록하고 build 가 UV 를 구간별로 리매핑해
    # 3D 안구 높이·코끝·치아선에 각각 맞춘다.
    lum = list(canvas.convert("L").getdata())
    alp = list(canvas.getchannel("A").getdata())

    def _dark_row(x0f, x1f, y0f, y1f, pick):
        """띠 안 어두운 픽셀 가중합 프로필에서 특징 줄을 찾는다.

        pick="first"/"last": 임계(0.4×peak)를 넘는 첫/마지막 덩어리의
        최대점. 캔버스 세로 비율을 돌려준다 (못 찾으면 None).
        """
        x0, x1 = int(canvas_w * x0f), int(canvas_w * x1f)
        y0, y1 = int(canvas_h * y0f), int(canvas_h * y1f)
        vals = sorted(lum[r * canvas_w + c]
                      for r in range(y0, y1) for c in range(x0, x1)
                      if alp[r * canvas_w + c] > 200)
        if not vals:
            return None
        med = vals[len(vals) // 2]
        rows = []
        for r in range(y0, y1):
            s = 0
            for c in range(x0, x1):
                i = r * canvas_w + c
                if alp[i] > 200 and lum[i] < med - 25:
                    s += med - 25 - lum[i]
            rows.append(s)
        peak = max(rows)
        if peak <= 0:
            return None
        thr = peak * 0.4
        clusters = []          # (덩어리 시작 줄, 최대점 줄)
        r = 0
        while r < len(rows):
            if rows[r] > thr:
                start = best = r
                while r < len(rows) and rows[r] > thr:
                    if rows[r] > rows[best]:
                        best = r
                    r += 1
                clusters.append((start, best))
            else:
                r += 1
        if pick == "first":
            # 띠 첫 줄에 붙은 덩어리는 띠 위쪽 어둠(코 밑 그림자)의
            # 꼬리다 — 실측 guard: 입 띠 첫 덩어리가 인중 그림자였다.
            clear = [b for s, b in clusters if s > 0]
            best = clear[0] if clear else clusters[0][1]
        else:
            best = clusters[-1][1]
        return (y0 + best) / canvas_h

    # 눈: 넓은 띠에서 '마지막' 덩어리 — 첫 덩어리는 눈썹이다.
    # (눈썹·눈이 한 덩어리로 붙으면 그 안의 최대점 = 동공/속눈썹 줄)
    eye_frac = _dark_row(0.25, 0.75, 0.30, 0.555, "last")
    # 콧구멍: 눈 밑 좁은 중앙 띠의 '첫' 덩어리. 0.53 시작은 rean 처럼
    # 눈이 낮은 초상에서 눈 검은자를 오인했다 (실측 0.533) — 0.56 부터.
    nose_frac = _dark_row(0.42, 0.58, 0.56, 0.80, "first")
    # 입: 콧구멍 아래 첫 덩어리 = 입술 틈 (턱 그림자는 더 아래)
    mouth_frac = None
    if nose_frac:
        mouth_frac = _dark_row(0.35, 0.65, nose_frac + 0.03,
                               min(0.95, nose_frac + 0.18), "first")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    canvas.save(out_path)
    meta_path = out_path[:-4] + "_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(dict(eye_frac=eye_frac or eye_y_ratio,
                       nose_frac=nose_frac, mouth_frac=mouth_frac,
                       hair_rgb=ch.get("hair_rgb")), f)
    if os.environ.get("FD_DEBUG"):
        dbg = canvas.copy()
        dd = ImageDraw.Draw(dbg)
        for frac, col in ((eye_frac, (0, 200, 0, 255)),
                          (nose_frac, (255, 0, 0, 255)),
                          (mouth_frac, (255, 0, 255, 255))):
            if frac:
                yy = int(frac * canvas_h)
                dd.line((0, yy, canvas_w, yy), fill=col, width=3)
        dd.line((0, paste_cy, canvas_w, paste_cy), fill=(0, 128, 255, 255), width=1)
        dbg.save(out_path[:-4] + "_feat_debug.png")
    print(f"[face_decal] 데칼 {canvas_w}x{canvas_h} → {out_path}"
          f"  눈 {eye_frac} 콧구멍 {nose_frac} 입 {mouth_frac}", flush=True)
    return canvas


# ---------------------------------------------------------------------------
# 2단계: Blender 에서 데칼을 머리 앞에 붙이고 GLB 로 내보내기
# ---------------------------------------------------------------------------

# 캐릭터별 머리 모양 — 초상 관찰 (2026-09-15 /tmp/portraits_row.png):
# 수호=금빛 투구, 세렌=긴 갈색 머리, 레안=뒤로 넘긴 짧은 머리,
# 유안=짧은 머리+수염, 미로=곱슬 갈색. 색은 crop 이 초상에서 잰다.
HAIR_STYLE = {
    # 수호는 fbox 바로 위가 보라색 챙이라 (실측 /tmp/hairband.png)
    # 그 위 금빛 돔(30~50%)에서 색을 잰다
    "north_gatekeeper": dict(kind="helmet", offset=0.010, band=(0.50, 0.30),
                             q=0.75),
    "seren": dict(kind="long", offset=0.014),
    "rean": dict(kind="short", offset=0.012),
    "yuan": dict(kind="short", offset=0.010),
    "miro": dict(kind="short", offset=0.014),
}


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

    # MASK 적용 전에 3D 눈·입 높이를 잰다 — 안구 헬퍼 중심 z 가
    # 눈높이, 윗니·아랫니 중간이 입선이다 (UV 리매핑의 과녁).
    # MASK 를 적용하면 헬퍼 지오메트리가 삭제돼 잴 수 없다 (실측:
    # 적용 후엔 그룹만 남고 정점 0개).
    def _grp_z(name):
        if name not in bm.vertex_groups:
            return None
        gx = bm.vertex_groups[name].index
        zs = [v.co.z for v in bm.data.vertices
              for g in v.groups if g.group == gx and g.weight > 0.1]
        return sum(zs) / len(zs) if zs else None

    _ez = [z for z in (_grp_z("helper-l-eye"), _grp_z("helper-r-eye")) if z]
    eye_z = sum(_ez) / len(_ez) if _ez else None
    _tz = [z for z in (_grp_z("helper-upper-teeth"),
                       _grp_z("helper-lower-teeth")) if z]
    mouth_z = sum(_tz) / len(_tz) if _tz else None
    print(f"[face_decal] 3D 눈높이 {eye_z} 입선 {mouth_z}", flush=True)

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
    # 귀 정점 — 투구 선택용. 빌드 끝에선 v.groups 웨이트가 0 으로
    # 읽힌다 (실측: bmesh deform 도 동일) — 지금 인덱스를 잡아둔다.
    ear_info = [(v.index, v.co.y) for v in bm.data.vertices
                if _w(v, egi) > 0.3]
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

    # --- 두상 슬림 — 두상이 그림보다 무겁다 ---
    # 실측(맨몸 정면 스크린샷 vs 초상 크롭): 매크로 weight·muscle 이
    # 얼굴에도 적용돼 볼·턱이 넓은데, 초상 다섯은 전부 갸름하다.
    # 두 겹으로 좁힌다:
    #   1) 두개골 전체 5% — 귀도 같이 (귀만 빼면 밑동에 계단이 생긴다).
    #      실측: 하관만 좁히면 광대·두개골 폭(스크린샷 y 0.55~0.62,
    #      334px)이 그대로라 여전히 무겁게 읽힌다.
    #   2) 하관(광대 아래~턱) 추가 10% — 여긴 귀 밖이라 ear weight
    #      램프로 잇는다. 합쳐서 턱은 최대 ~15%.
    # 아래(목) 경계는 3cm 램프로 몸에 잇는다.
    z_hi = tip_co.z + 0.02      # 광대 위 — 여기부터 위는 전체 슬림만
    z_lo = tip_co.z - 0.10      # 턱 밑 — 여기부터 아래는 목, 그대로
    SLIM_ALL, SLIM_JAW = 0.05, 0.10
    n_slim = 0
    for v in mv:
        if _w(v, hgi) <= 0.05 and _w(v, egi) <= 0.05:
            continue
        base = SLIM_ALL * min(1.0, max(0.0, (v.co.z - z_lo + 0.03) / 0.03))
        jaw = min((z_hi - v.co.z) / 0.03, (v.co.z - z_lo) / 0.03, 1.0)
        jaw = SLIM_JAW * max(0.0, jaw) * max(0.0, 1.0 - _w(v, egi) / 0.3)
        s = base + jaw
        if s <= 0:
            continue
        v.co.x = tip_co.x + (v.co.x - tip_co.x) * (1.0 - s)
        n_slim += 1
    print(f"[face_decal] 두상 슬림 {n_slim}개 정점 (전체 {SLIM_ALL:.0%} + 하관 {SLIM_JAW:.0%})",
          flush=True)

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
    # 4차: 입술 융기 — 비눗막(300회)은 입에는 안 된다: 눈과 달리
    # 입은 안쪽 주머니(구강)가 선택 경계에 걸려 막이 안으로 꺼진다
    # (실측: 입 자리가 움푹 파이고 데칼에 흰 띠 접힘). 대신 상자
    # 위(인중)·아래(턱) 테두리에서 x 기둥별로 가장 앞선 y 를 재고,
    # 상자 안 겉면 정점을 그 사이 직선(막)에 눕힌다 — 막보다 8mm
    # 이상 뒤(구강 안쪽)는 두고, 코 상자도 둔다.
    mv = bm.data.vertices   # EDIT 왕복 뒤 재조회
    ztop, zbot = tip_co.z - 0.010, tip_co.z - 0.050
    xw = 0.035
    front = fy0 + 0.5 * rng

    def _xbin(x):
        return round((x - tip_co.x) / 0.007)

    rim_t, rim_b = {}, {}
    for i, y in head_info:
        v = mv[i]
        if y >= front or abs(v.co.x - tip_co.x) > xw or i in nose_ids:
            continue
        b = _xbin(v.co.x)
        if ztop < v.co.z <= ztop + 0.012:
            rim_t[b] = min(rim_t.get(b, 9.0), v.co.y)
        elif zbot - 0.012 <= v.co.z < zbot:
            rim_b[b] = min(rim_b.get(b, 9.0), v.co.y)

    lip_moved = []
    for i, y in head_info:
        v = mv[i]
        if (y >= front or i in nose_ids or abs(v.co.x - tip_co.x) > xw
                or not zbot <= v.co.z <= ztop):
            continue
        b = _xbin(v.co.x)
        yt, yb = rim_t.get(b), rim_b.get(b)
        if yt is None or yb is None:
            continue
        target = yt + (yb - yt) * (ztop - v.co.z) / (ztop - zbot)
        if v.co.y < target + 0.008:   # 겉면만 — 구강 안쪽은 앵커도 이동도 없다
            v.co.y = target
            lip_moved.append(i)
    _smooth_sel(lip_moved, 0.5, 4)    # 막 경계를 살짝 잇는다
    print(f"[face_decal] 입술 막 {len(lip_moved)}개 정점", flush=True)
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

    # --- 세로 정렬: 그림 눈·콧구멍·입 줄을 3D 눈·코끝·입선에 맞춘다 ---
    # 한 점(눈 0.49 가정) 핀만으로는 초상 비율이 다를 때 전부 어긋난다
    # (실측 guard: 그림 눈이 3D 눈보다 ~2cm 아래 뺨에 → "안 붙어"
    # 보임, 입은 콧구멍 정렬에 1:1 로 딸려 올라가 "너무 위"). 그림
    # 쪽은 crop 이 잰 세 줄, 3D 쪽은 안구/치아 헬퍼 z 와 코끝 —
    # 격자 UV 의 V 를 조각별 선형으로 리매핑한다. 격자 정점은 안
    # 움직이고 어느 높이에 어느 그림 줄이 보이는지만 바꾼다.
    meta_path = decal_path[:-4] + "_meta.json"
    eye_q = nose_q = mouth_q = hair_rgb = None
    if os.path.exists(meta_path):
        with open(meta_path, encoding="utf-8") as f:
            _m = json.load(f)
        eye_q = _m.get("eye_frac")
        nose_q = _m.get("nose_frac")
        mouth_q = _m.get("mouth_frac")
        hair_rgb = _m.get("hair_rgb")
    plane_top = head_cz + plane_h / 2
    # 콧구멍은 코끝보다 살짝(4mm) 아래 밑면에 있다
    p_nose = (plane_top - (tip_co.z - 0.004)) / plane_h
    p_eye = (plane_top - eye_z) / plane_h if eye_z else None
    p_mouth = (plane_top - mouth_z) / plane_h if mouth_z else None
    pins = [(q, p) for q, p in ((eye_q, p_eye), (nose_q, p_nose),
                                (mouth_q, p_mouth)) if q and p]
    # 그림/판 둘 다 단조증가여야 한다 — 꼬이면 정렬을 통째로 접는다
    ok = all(pins[i][0] < pins[i + 1][0] and pins[i][1] < pins[i + 1][1]
             for i in range(len(pins) - 1))
    if pins and ok:
        def _remap(t):
            # 양 끝 밖은 1:1 평행이동 — 구간을 늘리면 이목구비 크기가
            # 변한다 (실측: (1,1) 재신장에 입술이 20% 커짐). 넘치는
            # 구간은 타원 마스크 밖 투명 영역이라 클램프해도 안 보인다.
            if t <= pins[0][1]:
                return max(0.0, pins[0][0] + (t - pins[0][1]))
            for (q0, p0), (q1, p1) in zip(pins, pins[1:]):
                if t <= p1:
                    return q0 + (q1 - q0) * (t - p0) / (p1 - p0)
            return min(1.0, pins[-1][0] + (t - pins[-1][1]))
        uvl = face_ob.data.uv_layers.active.data
        for loop in face_ob.data.loops:
            uv = uvl[loop.index].uv
            uv.y = 1.0 - _remap(1.0 - uv.y)   # V=1 이 그림 위끝
        print("[face_decal] 이목구비 정렬 그림→판: " + "  ".join(
            f"{q:.3f}→{p:.3f}" for q, p in pins), flush=True)
    else:
        print(f"[face_decal] 정렬 제어점이 꼬여 건너뜀: "
              f"{[(round(q, 3), round(p, 3)) for q, p in pins]}", flush=True)

    # --- 투명 스커트 제거 ---
    # 타원 마스크 밖(알파≈0) 격자면은 그릴 게 없는데도 실루엣을
    # 감싸며 림에서 접혀, 알파 0 이어도 스페큘러가 지그재그 하이라이트
    # 솔기로 보인다 (실측: 3/4 근접 뺨의 톱니 줄). 네 모서리+중심
    # UV 알파가 전부 낮은 면은 지운다.
    import bmesh
    _img = bpy.data.images.load(decal_path, check_existing=True)
    _iw, _ih = _img.size
    _px = _img.pixels[:]

    def _alpha(u, vv):
        x = min(_iw - 1, max(0, int(u * _iw)))
        y = min(_ih - 1, max(0, int(vv * _ih)))
        return _px[(y * _iw + x) * 4 + 3]

    uvl = face_ob.data.uv_layers.active.data
    drop = []
    for poly in face_ob.data.polygons:
        uvs = [uvl[li].uv for li in poly.loop_indices]
        cu = sum(t.x for t in uvs) / len(uvs)
        cv = sum(t.y for t in uvs) / len(uvs)
        a = max(_alpha(t.x, t.y) for t in uvs)
        if max(a, _alpha(cu, cv)) < 0.02:
            drop.append(poly.index)
    if drop:
        fb = bmesh.new()
        fb.from_mesh(face_ob.data)
        fb.faces.ensure_lookup_table()
        bmesh.ops.delete(fb, geom=[fb.faces[i] for i in drop],
                         context="FACES")
        fb.to_mesh(face_ob.data)
        fb.free()
    print(f"[face_decal] 투명 면 {len(drop)}개 지움", flush=True)

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

    # 코 그늘 정형 — 코 밑은 광선 사각지대라 NEAREST 구조 정점이
    # 코 밑면·인중에 뭉쳐 쌓인다 (인접 줄 사이 y 가 1cm 뛴다).
    # 콧구멍 정렬로 그 자리에 콧구멍~윗입술 그림 띠가 오면서 뭉침이
    # 부채살 줄무늬 + 가로 솔기로 드러났다 (실측 guard 인중).
    # 그 정점만 이웃과 고르게 편 뒤(15회) 표면에 다시 붙인다.
    fb = bmesh.new()
    fb.from_mesh(face_ob.data)
    fb.verts.ensure_lookup_table()
    under = [v.index for v in fb.verts
             if abs(v.co.x - head_cx) < 0.03
             and tip_co.z - 0.03 < v.co.z < tip_co.z - 0.005]
    uverts = [fb.verts[i] for i in under]
    for _ in range(15):
        bmesh.ops.smooth_vert(fb, verts=uverts, factor=0.5,
                              use_axis_x=True, use_axis_y=True,
                              use_axis_z=True)
    fb.to_mesh(face_ob.data)
    fb.free()
    if under:
        vg_u = face_ob.vertex_groups.new(name="under_nose")
        vg_u.add(under, 1.0, "REPLACE")
        sw3 = face_ob.modifiers.new("NoseShadow", "SHRINKWRAP")
        sw3.target = proxy
        sw3.wrap_method = "NEAREST_SURFACEPOINT"
        sw3.offset = 0.002
        sw3.vertex_group = "under_nose"
        bpy.ops.object.modifier_apply(modifier=sw3.name)
    print(f"[face_decal] 코 그늘 정형 {len(under)}개 정점", flush=True)

    # 접힘 절제 — 실루엣을 감싸다 NEAREST 로 구조된 가장자리 정점은
    # 정면 투영된 이웃과 어긋난 채 접혀, 뺨 옆에 깊이 절벽이 격자
    # 계단 모양 톱니 금으로 남는다 (실측: 3/4 근접 뺨 지그재그 —
    # 스무딩 10회+재수축(림 정형)으로도, 가장자리 링 비탈로도,
    # 알파 비례 밀착으로도 안 사라졌다 head6~11: 접힌 면은 어디로
    # 옮겨도 법선이 구겨진 채라 어둡게 갈라진다). 그림도 거의 없는
    # 면이니 — 구조된 정점과 1-이웃이 닿는 면을 통째로 잘라낸다.
    if missed:
        fb = bmesh.new()
        fb.from_mesh(face_ob.data)
        fb.verts.ensure_lookup_table()
        rim = set(missed)
        for i in missed:
            for e in fb.verts[i].link_edges:
                rim.add(e.other_vert(fb.verts[i]).index)
        # 단 그림이 실린 면(알파 0.5 이상)은 남긴다 — 입술 옆에도
        # 구조된 정점이 있어, 무조건 자르면 입가 데칼이 뜯긴다
        # (실측 head12: 아랫입술 밑 흰 구멍).
        _img3 = bpy.data.images.load(decal_path, check_existing=True)
        _iw3, _ih3 = _img3.size
        _px3 = _img3.pixels[:]
        uvl3 = face_ob.data.uv_layers.active.data
        doomed = []
        for poly in face_ob.data.polygons:
            if not any(vi in rim for vi in poly.vertices):
                continue
            amax = 0.0
            for li in poly.loop_indices:
                t = uvl3[li].uv
                x = min(_iw3 - 1, max(0, int(t.x * _iw3)))
                y = min(_ih3 - 1, max(0, int(t.y * _ih3)))
                amax = max(amax, _px3[(y * _iw3 + x) * 4 + 3])
            if amax < 0.5:
                doomed.append(poly.index)
        fb.faces.ensure_lookup_table()
        bmesh.ops.delete(fb, geom=[fb.faces[i] for i in doomed],
                         context="FACES")
        fb.to_mesh(face_ob.data)
        fb.free()
        print(f"[face_decal] 접힌 면 {len(doomed)}개 절제", flush=True)

    # 남은 잔주름을 편다 — 단 코(맨 앞 1.5cm)는 빼고.
    # 전체에 걸면 굴곡이 제일 큰 코가 도로 펴져 옆모습이 밋밋해진다.
    # 코 '밑'(코끝보다 8mm 아래)은 앞쪽이어도 편다 — 코 그늘에서
    # NEAREST 로 구조된 정점이 지그재그로 접혀 인중에 검은 가시
    # 자국을 남긴다 (실측 guard).
    ymin = min(v.co.y for v in face_ob.data.vertices)
    flat_ids = [v.index for v in face_ob.data.vertices
                if v.co.y > ymin + 0.015 or v.co.z < tip_co.z - 0.008]
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

    # 가장자리 붙이기 — 데칼은 offset 2mm + Displace 1.5mm 로 살에서
    # 3.5mm 떠 있다. 몸은 매끈한데 데칼 껍데기가 뺨 실루엣을 넘어가는
    # 자리(정면 투영과 NEAREST 구조의 경계 접힘)에 깊이 절벽이 생겨
    # 격자 계단 모양 톱니 금이 보인다 (실측: ?body 몸만 찍으면 없다 —
    # 데칼이 범인. 열린 가장자리 링을 3~5링 비탈로 낮춰도(head7~10)
    # 그대로였다 — 절벽은 가장자리가 아니라 안쪽 접힘이다).
    # 해법: 거리(링)가 아니라 '텍스처 알파'로 붙인다 — 알파가 옅은
    # (타원 블러 페이드) 정점일수록 살 위 0.3mm 까지 끌어붙이면
    # 그림이 사라지기 전에 껍데기가 살 높이로 얇아져, 실루엣을
    # 넘는 자리엔 절벽이 남지 않는다. 알파 0.6 이상(그림 본체)은
    # 손대지 않는다. (살 '속'(-2mm)으로 넣으면 비탈이 살갗을 뚫는
    # 교차선이 계단째 톤을 끊는다 — 실측 head8. 살 위까지만.)
    _img2 = bpy.data.images.load(decal_path, check_existing=True)
    _iw2, _ih2 = _img2.size
    _px2 = _img2.pixels[:]
    uvl2 = face_ob.data.uv_layers.active.data
    v_alpha = {}
    for poly in face_ob.data.polygons:
        for li, vi in zip(poly.loop_indices, poly.vertices):
            t = uvl2[li].uv
            x = min(_iw2 - 1, max(0, int(t.x * _iw2)))
            y = min(_ih2 - 1, max(0, int(t.y * _ih2)))
            a = _px2[(y * _iw2 + x) * 4 + 3]
            v_alpha[vi] = max(v_alpha.get(vi, 0.0), a)
    fade = [(vi, min(1.0, 1.0 - a / 0.6)) for vi, a in v_alpha.items()
            if a < 0.6]
    if fade:
        vg_e = face_ob.vertex_groups.new(name="edge_tuck")
        for vi, w in fade:
            vg_e.add([vi], w, "REPLACE")
        sw5 = face_ob.modifiers.new("EdgeTuck", "SHRINKWRAP")
        sw5.target = proxy
        sw5.wrap_method = "NEAREST_SURFACEPOINT"
        sw5.offset = 0.0003
        sw5.vertex_group = "edge_tuck"
        bpy.ops.object.modifier_apply(modifier=sw5.name)
        print(f"[face_decal] 페이드 {len(fade)}개 정점 알파 비례로 살에 붙임",
              flush=True)

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

    # --- 머리카락 셸 --- ("왜케 안이쁘지 머리카락은 없어?")
    # 두피 정점(head weight>0.3, ears 제외, 헤어라인 위)을 복제해
    # 법선으로 부풀린 껍데기. 헤어라인은 정수리 기준으로 앞은 이마
    # 위, 뒤는 뒷통수 아래까지 y 에 따라 선형으로 내려간다. 색은
    # crop 이 초상의 이마 위 띠에서 잰 중앙값 (수호는 투구 금색이
    # 자연히 잡힌다).
    import bmesh as _bmesh_h
    style = HAIR_STYLE.get(char_id, dict(kind="short", offset=0.012))
    kind = style["kind"]
    h_off = style["offset"]
    mv2 = bm.data.vertices
    z_top = max(mv2[i].co.z for i, _ in head_info)
    if kind == "helmet":
        # 정수리만 덮으면 갈색 빵모자로 보인다 (실측 guard 1차) —
        # 투구답게 눈썹 위 2.5cm 까지 내려 이마·관자놀이를 덮는다
        front_z = (eye_z + 0.018) if eye_z else z_top - 0.075
        back_z = z_top - 0.12
    else:
        # 앞 0.045 는 이마가 휑하다 (실측 seren 1차) — 0.058 로 내림
        front_z, back_z = z_top - 0.058, z_top - 0.095

    def _hairline(y, x=None):
        t = (y - fy0) / max(1e-6, fy1 - fy0)
        fz = front_z
        if kind != "helmet" and x is not None:
            # 일자 앞머리는 바가지머리로 보인다 (실측 seren 2차) —
            # 가운데는 올리고 관자놀이 쪽은 내려 가르마 아치를 만든다
            s = min(1.0, abs(x - head_cx) / 0.09) ** 1.5
            fz = z_top - 0.050 - 0.028 * s
        return fz + (back_z - fz) * max(0.0, min(1.0, t))

    # head_info 가 이미 head>0.3 ∧ ears<0.3 정점 목록이다 — bmesh
    # deform 레이어는 이 시점엔 head 웨이트를 0 으로 읽는다 (실측:
    # dfl 존재해도 head=0). 인덱스 집합으로 고른다 (from_mesh 는
    # 정점 순서를 보존한다).
    if kind == "helmet":
        # 투구는 귀 위까지 덮는다 — 귀를 빼면 테두리에 귀 구멍이 남는다
        cand = head_info + ear_info
    else:
        cand = head_info
    keep_ids = {i for i, y in cand
                if mv2[i].co.z >= _hairline(y, mv2[i].co.x)}
    hbm = _bmesh_h.new()
    hbm.from_mesh(bm.data)
    doomed_hv = [v for v in hbm.verts if v.index not in keep_ids]
    _bmesh_h.ops.delete(hbm, geom=doomed_hv, context="VERTS")

    # 헤어라인 경계는 z 문턱 절단이라 계단 톱니가 남는다 (실측
    # seren 1차: 이마에 사각 이빨) — 경계 링만 스무딩으로 둥글린다
    bnd_v = list({vv for e in hbm.edges if e.is_boundary for vv in e.verts})
    if kind == "helmet":
        # 투구 테는 매끈한 금속 테여야 한다 — 경계 정점 z 를
        # 헤어라인 평면에 딱 맞춰 계단을 없앤다
        for v in bnd_v:
            v.co.z = _hairline(v.co.y, v.co.x)
    else:
        for _ in range(8):
            _bmesh_h.ops.smooth_vert(hbm, verts=bnd_v, factor=0.5,
                                     use_axis_x=True, use_axis_y=True,
                                     use_axis_z=True)

    # 부풀리기 — 헤어라인 쪽은 살에 붙게 테이퍼 (절벽 방지)
    hbm.normal_update()
    for v in hbm.verts:
        hl = _hairline(v.co.y, v.co.x)
        t = (v.co.z - hl) / max(1e-6, z_top - hl)
        w = 0.25 + 0.75 * max(0.0, min(1.0, t))
        v.co += v.normal * (h_off * w)

    # 긴 머리 — 뒷·옆 경계 링을 두 번 아래로 뽑아 커튼을 만든다
    if kind == "long":
        # 귀 앞까지 잡으면 얇은 띠가 뺨 옆에 매달린다 (실측 seren
        # 1차) — 뒤통수 절반만. 안으로 조이지 말고 뒤로 늘어뜨린다.
        y_mid = (fy0 + fy1) / 2
        cur = [e for e in hbm.edges if e.is_boundary
               and all(vv.co.y > y_mid + 0.02 for vv in e.verts)]
        for k, dz in enumerate((0.07, 0.10)):
            ret = _bmesh_h.ops.extrude_edge_only(hbm, edges=cur)
            new_v = {g for g in ret["geom"]
                     if isinstance(g, _bmesh_h.types.BMVert)}
            for vv in new_v:
                vv.co.z -= dz
                vv.co.x = head_cx + (vv.co.x - head_cx) * (1.0, 0.96)[k]
                vv.co.y += (0.012, 0.008)[k]
            cur = [g for g in ret["geom"]
                   if isinstance(g, _bmesh_h.types.BMEdge)
                   and all(nv in new_v for nv in g.verts)]

    _bmesh_h.ops.recalc_face_normals(hbm, faces=hbm.faces)
    hair_me = bpy.data.meshes.new("hair")
    hbm.to_mesh(hair_me)
    hbm.free()
    hair_ob = bpy.data.objects.new("hair", hair_me)
    bpy.context.collection.objects.link(hair_ob)
    for poly in hair_me.polygons:
        poly.use_smooth = True

    rgb = hair_rgb or [60, 50, 45]
    lin = [pow(c / 255.0, 2.2) for c in rgb]
    hmat = bpy.data.materials.new("hair")
    hmat.use_nodes = True
    h_bsdf = hmat.node_tree.nodes.get("Principled BSDF")
    h_bsdf.inputs["Base Color"].default_value = (*lin, 1.0)
    if kind == "helmet":
        # 0.85 는 환경맵 없는 뷰어에서 갈색으로 죽는다 — 0.5 로
        h_bsdf.inputs["Metallic"].default_value = 0.5
        h_bsdf.inputs["Roughness"].default_value = 0.35
    else:
        h_bsdf.inputs["Roughness"].default_value = 0.6
    hair_me.materials.append(hmat)

    hair_ob.parent = arm
    vgh = hair_ob.vertex_groups.new(name="head")
    for v in hair_me.vertices:
        vgh.add([v.index], 1.0, 'REPLACE')
    hmod = hair_ob.modifiers.new("Armature", "ARMATURE")
    hmod.object = arm
    print(f"[face_decal] 머리 {kind} 정점 {len(hair_me.vertices)}개"
          f" 색 {rgb}", flush=True)

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

    # face_ob·hair_ob 를 export 대상에 포함
    MD.export_anim([bm, gar, face_ob, hair_ob, arm], out_path)

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
