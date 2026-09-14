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

    canvas_w = head_w
    canvas_h = head_h
    canvas = Image.new("RGBA", (canvas_w, canvas_h), (*SKIN, 255))

    # 얼굴을 머리 비율에 맞게 리사이즈
    # 얼굴은 머리 너비의 약 65% 를 차지한다
    target_fw = int(canvas_w * 0.65)
    face_resized = face_img.resize((target_fw, target_fw), Image.LANCZOS)

    # 배치: 눈선이 머리 위에서 42% → 얼굴 중심을 42% 지점에
    eye_y_ratio = 0.42
    paste_cx = canvas_w // 2
    paste_cy = int(canvas_h * eye_y_ratio)

    px = paste_cx - face_resized.width // 2
    py = paste_cy - face_resized.height // 2

    canvas.paste(face_resized, (px, py))

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

    # --- 스킨 머티리얼에 데칼 텍스처 입히기 ---
    skin = bpy.data.materials.new("skin")
    skin.use_nodes = True
    tree = skin.node_tree
    nodes = tree.nodes
    links = tree.links

    # 기본 노드 정리
    for n in nodes:
        nodes.remove(n)

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (400, 0)

    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.location = (200, 0)
    links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

    # 데칼 텍스처 로드
    tex_img = nodes.new("ShaderNodeTexImage")
    tex_img.location = (-200, 0)
    tex_img.image = bpy.data.images.load(decal_path)
    tex_img.image.alpha_mode = "STRAIGHT"

    links.new(tex_img.outputs["Color"], bsdf.inputs["Base Color"])
    links.new(tex_img.outputs["Alpha"], bsdf.inputs["Alpha"])

    # 알파 블렌딩 활성화
    skin.blend_method = "CLIP" if hasattr(skin, 'blend_method') else None
    # EEVEE alpha — glTF export 에서 자동 변환됨

    bm.data.materials.clear()
    bm.data.materials.append(skin)

    # --- 얼굴 데칼 평면 만들기 ---
    # 3D 머리 좌표: cx=0, cz=head中心z, cy=머리 앞쪽
    head_cz = L["head"].z
    head_cy = L["head"].y  # 약 -0.054

    # 데칼 평면: 머리 너비 x 높이 (약간 크게)
    plane_w = head_w_m * 1.05
    plane_h = head_h_m * 1.05

    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, head_cy - 0.015, head_cz))
    face_ob = bpy.context.view_layer.objects.active
    face_ob.name = f"face_{char_id}"
    face_ob.scale = (plane_w / 2, plane_h / 2, 1.0)
    bpy.ops.object.transform_apply(scale=True)

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

    dl.new(d_tex.outputs["Color"], d_bsdf.inputs["Base Color"])
    dl.new(d_tex.outputs["Alpha"], d_bsdf.inputs["Alpha"])

    decal_mat.blend_method = "CLIP" if hasattr(decal_mat, 'blend_method') else None
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
        report_path = os.path.join(args.out, "face_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    # Blender 는 인자를 "--" 뒤에 붙인다. 직접 실행은 그냥 1부터.
    if "--" in sys.argv:
        argv = sys.argv[sys.argv.index("--") + 1:]
    else:
        argv = sys.argv[1:]
    main(argv)
