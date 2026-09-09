# -*- coding: utf-8 -*-
"""소지품 실험 — 손에 물건을 하나 쥐어 주고 실루엣을 다시 찍는다.

    blender --background --python chars/src/make_props_shot.py -- \
            --props pipeline3d/out/props --out chars/out/propshot

판정 기준은 docs/실험/2026-09-09-소지품이-갈라주는가-판정기준.md 에
그림을 한 장도 뽑기 전에 적어 두었다. 여기서는 거기 적힌 대로만 뽑는다.

  · 역할은 **수호** 하나로 고정 (기준에 그렇게 박아 두었다)
  · 계층은 쥐는 소품(hold=="grip")이 둘 이상인 9계층 = 39종
  · 소품은 hand_r 의 **head 와 tail 의 중점**(손바닥)에 원점을 놓는다.
    긴 축을 월드 +Z 로 세우고 부호는 그대로 둔다 — grip_end 가 "low" 면
    덩치가 손 위로, "high" 면 손 아래로 간다.
  · 옷·몸·카메라·해상도·렌더러는 make_garments 의 것을 그대로 부른다.

맨손도 같은 코드로 한 장씩 찍는다. 그것이 자 확인이다 — 이미 커밋된
chars/out/garments/shots/guard_*.png 와 **픽셀 단위로 같아야** 자가 안 바뀐 것이다.
"""
import argparse, json, math, os, sys

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tools"))

import make_garments as MG
import garments as G
import make_bodies as MB
from bodies import SLUG as BODY_SLUG
import trades as TR

ROLE = "수호"


def grip_props(props_dir):
    """계층 -> 쥐는 소품 목록. 둘 이상인 계층만."""
    by_trade = {t["n"]: t for t in TR.TRADES}
    with open(os.path.join(props_dir, "report.json"), encoding="utf-8") as f:
        rows = json.load(f)
    out = {}
    for r in rows:
        if r["hold"] != "grip":
            continue
        out.setdefault(by_trade[r["trade"]]["cls"], []).append(r)
    return {c: v for c, v in out.items() if len(v) >= 2}


def load_prop(path):
    """GLB 한 장을 들여와 메쉬 하나로 준다. 회전·크기는 여기서 굳힌다."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
        return None
    ob = meshes[0]
    ob.parent = None
    # glTF 는 Y-up 이라 들여올 때 회전이 하나 붙는다. 굳혀서 지역축을 월드축과 맞춘다.
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    for o in new:
        if o is not ob:
            bpy.data.objects.remove(o, do_unlink=True)
    return ob


def stand_up(ob):
    """긴 축을 월드 +Z 로 세운다. 부호는 안 뒤집는다.

    축을 골라 90도 한 번만 돌린다. 임의의 벡터로 맞추면 굴림(roll)이
    소품마다 제멋대로 달라져서, 실루엣 차이에 붙이는 규칙의 잡음이 섞인다.
    """
    co = [v.co for v in ob.data.vertices]
    lo = Vector((min(c.x for c in co), min(c.y for c in co), min(c.z for c in co)))
    hi = Vector((max(c.x for c in co), max(c.y for c in co), max(c.z for c in co)))
    size = hi - lo
    ax = max(range(3), key=lambda i: size[i])
    if ax == 0:
        ob.rotation_euler = Euler((0.0, math.radians(-90), 0.0))   # +X -> +Z
    elif ax == 1:
        ob.rotation_euler = Euler((math.radians(90), 0.0, 0.0))    # +Y -> +Z
    else:
        ob.rotation_euler = Euler((0.0, 0.0, 0.0))
    return ax, tuple(round(v, 4) for v in size)


def palm(arm):
    """hand_r 의 head 와 tail 의 중점 — 손바닥 한가운데."""
    b = arm.data.bones["hand_r"]
    return arm.matrix_world @ ((b.head_local + b.tail_local) * 0.5)


def build(role, cls):
    """make_garments.main 과 같은 순서로 몸 한 벌 + 옷 한 벌."""
    sp = G.spec(cls)
    bm, arm = MG.build_body(role)
    L = MG.landmarks(bm, arm)
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
    ob = MG.join(parts, f"garment_{BODY_SLUG[role]}_{sp['slug']}")
    MG.bind(ob, arm)
    return bm, arm, ob, L, sp


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--props", default="pipeline3d/out/props")
    ap.add_argument("--out", default="chars/out/propshot")
    args = ap.parse_args(argv)

    bare_dir = os.path.join(args.out, "bare")
    hold_dir = os.path.join(args.out, "hold")
    os.makedirs(bare_dir, exist_ok=True)
    os.makedirs(hold_dir, exist_ok=True)
    MG.setup_shot()

    tiers = grip_props(args.props)
    order = [c for c in TR.STRATA if c in tiers]
    n = sum(len(tiers[c]) for c in order)
    print(f"[propshot] 역할 {ROLE} · 계층 {len(order)} · 소품 {n}종", flush=True)

    report = []
    for cls in order:
        bm, arm, gm, L, sp = build(ROLE, cls)
        hand = palm(arm)
        MG.shoot(os.path.join(bare_dir, sp["slug"] + ".png"), L["height"], L["z0"])
        for r in tiers[cls]:
            p = load_prop(os.path.join(args.props, r["glb"]))
            if p is None:
                print(f"  !! {r['id']} 메쉬 없음", flush=True)
                continue
            ax, size = stand_up(p)
            p.location = hand
            MG.shoot(os.path.join(hold_dir, f"{sp['slug']}_{r['id']}.png"),
                     L["height"], L["z0"])
            report.append(dict(cls=cls, tier=sp["slug"], id=r["id"], obj=r["obj"],
                               trade=r["trade"], grip_end=r["grip_end"],
                               long_axis="XYZ"[ax], size=list(size),
                               dim_m=r["dim_m"],
                               png=f"{sp['slug']}_{r['id']}.png"))
            print(f"  {sp['slug']:9s} {r['id']:22s} {r['obj']:12s} "
                  f"긴축 {'XYZ'[ax]} {size}  자루 {r['grip_end']}", flush=True)
            bpy.data.objects.remove(p, do_unlink=True)

    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as f:
        json.dump(dict(role=ROLE, tiers=order, rows=report), f,
                  ensure_ascii=False, indent=1)
    print(f"[propshot] {len(report)}장 → {hold_dir}", flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(argv)
