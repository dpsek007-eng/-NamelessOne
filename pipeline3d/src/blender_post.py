# -*- coding: utf-8 -*-
"""3단계 — 블렌더 후처리. 생성기가 낸 것을 게임에 넣을 수 있는 것으로 바꾼다.

    blender --background --python blender_post.py -- --mesh out/mesh --out out/props

생성기가 내는 OBJ 는 그대로는 못 쓴다. 다섯 가지가 어긋나 있다.

  1. 삼각형이 십수만 개다        — 폰에서 소품 하나가 캐릭터보다 무겁다
  2. 크기가 없다                — 곡괭이와 인장이 같은 상자에서 나온다
  3. 원점이 한가운데다           — 손에 붙이면 물건 배꼽을 쥔다
  4. 마칭큐브가 남긴 부스러기가 떠 있다
  5. 법선이 뒤집혀 있는 면이 섞인다

여기서 그 다섯을 잡고 GLB · FBX 두 벌로 내보낸다.
"""
import argparse, json, math, os, sys

import bpy
import bmesh
from mathutils import Vector


# ── 뼈대 ────────────────────────────────────────────────────────────────

def wipe():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_obj(path):
    # TripoSR 의 좌표계는 tsr/utils.py:357 에 적혀 있다 —
    #   "right hand coordinate system, x back, y right, z up"
    # 즉 +Z 가 위, 입력 사진을 찍은 카메라가 +X 쪽에 있다(=정면이 +X).
    # 블렌더도 +Z 가 위이고 정면은 −Y 다. 그래서 위는 그대로 두고
    # +X 를 블렌더의 정면으로 돌린다.
    #
    # 의자 예제로 실측해 확인했다 (원본 X 0.599 Y 0.568 Z 1.068):
    #   forward='X',          up='Z'  →  X 0.568  Y 0.599  Z 1.068   맞다
    #   forward='NEGATIVE_Z', up='Y'  →  X 0.599  Y 1.068  Z 0.568   옆으로 눕는다
    bpy.ops.wm.obj_import(filepath=path, forward_axis='X', up_axis='Z')
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not objs:
        raise RuntimeError(f"메시가 없다: {path}")
    if len(objs) > 1:
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active or objs[0]
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    return ob


# ── 1. 청소 ─────────────────────────────────────────────────────────────

def clean(ob, island_floor=0.01):
    """겹친 점을 붙이고, 뜬 부스러기를 지우고, 법선을 밖으로 돌린다."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)

    # 이어진 덩어리로 나눈다. 마칭큐브는 본체에서 떨어진 조각을 남긴다.
    seen, islands = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, group = [v], []
        seen.add(v)
        while stack:
            w = stack.pop()
            group.append(w)
            for e in w.link_edges:
                o = e.other_vert(w)
                if o not in seen:
                    seen.add(o)
                    stack.append(o)
        islands.append(group)

    dropped = 0
    if len(islands) > 1:
        big = max(len(g) for g in islands)
        kill = [v for g in islands if len(g) < big * island_floor for v in g]
        if kill:
            dropped = len(kill)
            bmesh.ops.delete(bm, geom=kill, context='VERTS')

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return dropped


# ── 2. 삼각형 줄이기 ─────────────────────────────────────────────────────

def decimate(ob, budget):
    tris_before = tri_count(ob)
    if tris_before > budget:
        m = ob.modifiers.new("decimate", 'DECIMATE')
        m.decimate_type = 'COLLAPSE'
        m.ratio = budget / tris_before
        bpy.ops.object.modifier_apply(modifier=m.name)
    # 사각형이 섞여 있으면 유니티가 제 맘대로 자른다. 여기서 자른다.
    m = ob.modifiers.new("tri", 'TRIANGULATE')
    m.quad_method = 'SHORTEST_DIAGONAL'
    m.keep_custom_normals = True
    bpy.ops.object.modifier_apply(modifier=m.name)
    return tris_before, tri_count(ob)


def tri_count(ob):
    me = ob.data
    return sum(len(p.vertices) - 2 for p in me.polygons)


# ── 3. 크기 ─────────────────────────────────────────────────────────────

def fit_size(ob, metres):
    """가장 긴 변을 실물 길이에 맞춘다. 생성기는 크기를 모른다."""
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    d = ob.dimensions
    longest = max(d.x, d.y, d.z)
    if longest <= 0:
        raise RuntimeError("크기가 0 이다")
    k = metres / longest
    ob.scale = (k, k, k)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return k


# ── 4. 원점 ─────────────────────────────────────────────────────────────

def set_origin(ob, hold):
    """손에 드는 것은 자루 끝에, 놓는 것은 바닥 한가운데에 원점을 둔다.

    자루가 어느 쪽인지는 굵기로 가린다. 망치도 곡괭이도 붓도, 자루 쪽이 얇다.
    긴 축을 열 칸으로 잘라 칸마다 축에서 떨어진 평균 거리를 재고,
    양 끝 세 칸을 비교해 얇은 쪽을 자루로 본다.
    """
    me = ob.data
    vs = [ob.matrix_world @ v.co for v in me.vertices]
    if not vs:
        return None

    lo = Vector((min(v.x for v in vs), min(v.y for v in vs), min(v.z for v in vs)))
    hi = Vector((max(v.x for v in vs), max(v.y for v in vs), max(v.z for v in vs)))

    if hold == "place":
        pivot = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z))
        which = "bottom"
    else:
        size = hi - lo
        ax = max(range(3), key=lambda i: size[i])          # 가장 긴 축
        a, b = lo[ax], hi[ax]
        if b - a < 1e-9:
            return None
        NB = 10
        bins = [[] for _ in range(NB)]
        for v in vs:
            j = min(NB - 1, int((v[ax] - a) / (b - a) * NB))
            bins[j].append(v)

        other = [i for i in range(3) if i != ax]
        def thickness(group):
            if not group:
                return math.inf
            c0 = sum(v[other[0]] for v in group) / len(group)
            c1 = sum(v[other[1]] for v in group) / len(group)
            return sum(math.hypot(v[other[0]] - c0, v[other[1]] - c1)
                       for v in group) / len(group)

        head = sum(t for t in (thickness(bins[i]) for i in (0, 1, 2)) if t < math.inf)
        tail = sum(t for t in (thickness(bins[i]) for i in (-1, -2, -3)) if t < math.inf)
        # 얇은 쪽이 자루다. 그 끝에서 12% 들어온 자리를 쥔다.
        if head <= tail:
            t, which = 0.12, "low"
            grip_bin = bins[1]
        else:
            t, which = 0.88, "high"
            grip_bin = bins[-2]

        pivot = Vector((0, 0, 0))
        pivot[ax] = a + (b - a) * t
        if grip_bin:
            pivot[other[0]] = sum(v[other[0]] for v in grip_bin) / len(grip_bin)
            pivot[other[1]] = sum(v[other[1]] for v in grip_bin) / len(grip_bin)
        else:
            pivot[other[0]] = (lo[other[0]] + hi[other[0]]) / 2
            pivot[other[1]] = (lo[other[1]] + hi[other[1]]) / 2

    cur = bpy.context.scene.cursor.location.copy()
    bpy.context.scene.cursor.location = pivot
    bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    bpy.context.scene.cursor.location = cur
    ob.location = (0, 0, 0)
    return which


# ── 5. 재질 ─────────────────────────────────────────────────────────────

def material(ob, tex_path, name, tex_size):
    for s in list(ob.data.materials):
        ob.data.materials.clear()
        break
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    img = bpy.data.images.load(tex_path)
    if tex_size and max(img.size) > tex_size:
        img.scale(tex_size, tex_size)
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = img
    node.location = (-400, 0)
    nt.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
    # TripoSR 이 굽는 것은 알베도가 아니라 빛이 섞인 색이다.
    # 금속으로 두면 두 번 반짝인다. 0 으로 두고 거칠게 둔다.
    bsdf.inputs["Metallic"].default_value = 0.0
    bsdf.inputs["Roughness"].default_value = 0.75
    ob.data.materials.append(mat)
    return img


# ── 내보내기 ────────────────────────────────────────────────────────────

def export(ob, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob

    glb = os.path.join(out_dir, f"{name}.glb")
    bpy.ops.export_scene.gltf(
        filepath=glb, export_format='GLB', use_selection=True,
        export_yup=True, export_image_format='AUTO', export_apply=True,
    )
    fbx = os.path.join(out_dir, f"{name}.fbx")
    bpy.ops.export_scene.fbx(
        filepath=fbx, use_selection=True,
        axis_forward='-Z', axis_up='Y',          # 유니티가 읽는 축
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_NONE',
        bake_space_transform=False,
        path_mode='COPY', embed_textures=True,
        mesh_smooth_type='FACE', use_mesh_modifiers=True,
        object_types={'MESH'}, add_leaf_bones=False,
    )
    return glb, fbx


# ── 본체 ────────────────────────────────────────────────────────────────

def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--grip-budget", type=int, default=800)
    ap.add_argument("--place-budget", type=int, default=1600)
    ap.add_argument("--tex-size", type=int, default=512)
    ap.add_argument("--only", default=None)
    args = ap.parse_args(argv)

    with open(os.path.join(args.mesh, "index.json"), encoding="utf-8") as f:
        rows = json.load(f)
    # 후보 고르기는 이미 앞 단계에서 끝났다. out/mesh/index.json 에는 picks.json
    # 으로 걸러낸 한 종당 한 장씩만 들어 있고, 그 variant 번호는 종마다 다르다.
    # 전에는 여기서 variant==0 만 남겼는데, 그러면 v1·v2 를 고른 종이 통째로
    # 사라진다. 표를 그대로 쓴다.
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        rows = [r for r in rows if f"{r['i']:02d}" in keep or r["id"] in keep]

    os.makedirs(args.out, exist_ok=True)
    report = []
    print(f"[blender_post] {len(rows)}개", flush=True)

    for r in rows:
        d = os.path.join(args.mesh, r["dir"])
        obj_path = os.path.join(d, "mesh.obj")
        tex_path = os.path.join(d, "texture.png")
        if not os.path.exists(obj_path):
            print(f"  없음 {r['id']}", flush=True)
            continue

        wipe()
        ob = import_obj(obj_path)
        ob.name = r["id"]

        dropped = clean(ob)
        budget = args.grip_budget if r["hold"] == "grip" else args.place_budget
        t0, t1 = decimate(ob, budget)
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
        k = fit_size(ob, r["m"])
        which = set_origin(ob, r["hold"])
        if os.path.exists(tex_path):
            material(ob, tex_path, r["id"], args.tex_size)
        glb, fbx = export(ob, args.out, r["id"])

        dim = ob.dimensions
        row = {
            "id": r["id"], "obj": r["obj"], "trade": r["trade"], "hold": r["hold"],
            "tris_in": t0, "tris_out": t1, "dropped_verts": dropped,
            "scale": round(k, 6), "grip_end": which,
            "dim_m": [round(dim.x, 3), round(dim.y, 3), round(dim.z, 3)],
            "glb": os.path.basename(glb), "fbx": os.path.basename(fbx),
        }
        report.append(row)
        print(f"  {r['id']:22s} {t0:>7,}→{t1:<5,}삼각형  "
              f"{dim.x:.2f}×{dim.y:.2f}×{dim.z:.2f}m  원점={which}"
              + (f"  부스러기 {dropped}점 버림" if dropped else ""), flush=True)

    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"[blender_post] 끝 — {len(report)}개", flush=True)


main()
