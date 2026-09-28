# -*- coding: utf-8 -*-
"""구워 놓은 몸을 서로 잰다. 「달라 보인다」를 적지 않으려고 낸다.

    blender -b --python chars/src/body_diff.py -- seek_clerk counting_child

재는 것은 `bodies.py` 머리주석의 표와 같은 세 가지다 — 키, 부피/키³, 어깨/키.
그 표를 그 값으로 뽑았으니 여기서 다른 값을 쓰면 견줄 수가 없다.
부피는 몸만 센다 (옷은 두께가 따로라 덩치를 흐린다).
"""
import os, sys, math
import bpy, bmesh

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAST = os.path.join(ROOT, "chars", "out", "cast")


def wipe():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.armatures, bpy.data.objects, bpy.data.materials):
        for x in list(blk):
            if x.users == 0:
                blk.remove(x)


def volume(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    v = bm.calc_volume(signed=False)
    bm.free()
    return v


def measure(slug):
    wipe()
    path = os.path.join(CAST, slug + ".glb")
    if not os.path.exists(path):
        return None
    bpy.ops.import_scene.gltf(filepath=path)
    body = arm = None
    for o in bpy.data.objects:
        if o.type == "ARMATURE":
            arm = o
        elif o.type == "MESH" and o.name.startswith("body"):
            body = o
    if body is None or arm is None:
        return None

    co = [body.matrix_world @ v.co for v in body.data.vertices]
    # 내보낼 때는 Y-up 이었지만 (make_demo export_yup) 읽어 들일 때 glTF
    # 임포터가 블렌더의 Z-up 으로 되돌린다. 그래서 키는 z 다. 처음에 y 로
    # 재서 1.82m 짜리 몸이 0.45m 로 나왔고, 비율만 맞아 그럴듯해 보였다.
    h = max(c.z for c in co) - min(c.z for c in co)
    B = {b.name: (arm.matrix_world @ b.head_local) for b in arm.data.bones}
    sh = (B["upperarm_l"] - B["upperarm_r"]).length
    vol = volume(body)
    return dict(slug=slug, height=h, vol_l=vol * 1000.0,
                vol_over_h3=vol * 1000.0 / (h ** 3), shoulder=sh, sh_over_h=sh / h)


def main(argv):
    slugs = argv or sorted(f[:-4] for f in os.listdir(CAST) if f.endswith(".glb"))
    rows = [r for r in (measure(s) for s in slugs) if r]
    print()
    print(f"{'몸':18s} {'키(m)':>8s} {'부피(L)':>9s} {'부피/키³':>9s} {'어깨(m)':>8s} {'어깨/키':>8s}")
    for r in rows:
        print(f"{r['slug']:18s} {r['height']:8.4f} {r['vol_l']:9.2f} "
              f"{r['vol_over_h3']:9.2f} {r['shoulder']:8.4f} {r['sh_over_h']:8.4f}")
    if len(rows) == 2:
        a, b = rows
        print()
        print(f"{b['slug']} 는 {a['slug']} 대비  "
              f"키 {(b['height']/a['height']-1)*100:+.1f}%  "
              f"부피 {(b['vol_l']/a['vol_l']-1)*100:+.1f}%  "
              f"어깨/키 {(b['sh_over_h']/a['sh_over_h']-1)*100:+.1f}%")
    print()


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
