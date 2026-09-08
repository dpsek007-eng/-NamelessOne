# -*- coding: utf-8 -*-
"""체형 5종을 만들어 FBX/GLB 로 낸다. 블렌더 안에서 돈다.

    blender --background --python chars/src/make_bodies.py -- --out chars/out/bodies

TripoSR 로 캐릭터를 만들지 않는 이유가 여기 결과에 그대로 나온다.
MPFB 가 내는 몸은 사각면만으로 되어 있고 관절에 엣지루프가 있다.
그래야 자동 웨이트가 먹고 팔꿈치가 접힌다.
"""
import argparse, json, os, sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bodies import BODIES, SLUG, RIG, RACE

# 확장으로 깔면 모듈 경로가 bl_ext.<저장소>.<이름> 이다. 그냥 mpfb 가 아니다.
from bl_ext.blender_org.mpfb.services.humanservice import HumanService
from bl_ext.blender_org.mpfb.services.rigservice import RigService


def wipe():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for blk in (bpy.data.meshes, bpy.data.armatures, bpy.data.objects,
                bpy.data.materials, bpy.data.images):
        for x in list(blk):
            if x.users == 0:
                blk.remove(x)


def bake_shape(obj, keep_helpers=False):
    """체형을 정점 좌표에 굽는다.

    MPFB 는 매크로(키·근육·나이…)를 셰이프키 서른 남짓으로 얹는다.
    그대로 내보내면 나가는 것은 "중립 기본 메시 + 모프타깃"이고,
    유니티는 모프 가중치를 0 으로 읽는다 — 다섯 체형이 전부 같은 몸이 된다.

    실제로 그렇게 나왔다. 내보낸 GLB 다섯의 메시 부피가 208.9L 로
    소수점까지 같았고 어깨너비도 0.340m 로 같았다. 눈으로는 키만 달라
    보여서 넘어갈 뻔했다.

    그래서 depsgraph 로 평가한 결과를 새 메시로 받아 갈아 끼운다.
    아마추어 모디파이어는 잠시 꺼 둔다 — 지금 굽는 것은 체형이지 포즈가 아니다.
    """
    if not obj.data.shape_keys:
        return 0
    n = len(obj.data.shape_keys.key_blocks)
    # 아마추어만 끈다. 지금 굽는 것은 체형이지 포즈가 아니다.
    # 반대로 마스크는 켜 둔 채로 굽는다 — 그래야 헬퍼 지오메트리가
    # 여기서 떨어져 나가고, 내보내는 것은 몸만 남는다.
    # keep_helpers 는 옷을 만들 때 쓴다. 옷의 바탕이 되는 케이지
    # (helper-tights · helper-skirt)가 마스크 뒤에 숨어 있어서,
    # 마스크까지 꺼야 그 정점이 구운 메시에 남는다.
    saved = [(m, m.show_viewport) for m in obj.modifiers
             if m.type == "ARMATURE" or (keep_helpers and m.type == "MASK")]
    for m, _ in saved:
        m.show_viewport = False
    dg = bpy.context.evaluated_depsgraph_get()
    baked = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    for m, v in saved:
        m.show_viewport = v
    old = obj.data
    obj.shape_key_clear()
    obj.data = baked
    baked.name = old.name
    bpy.data.meshes.remove(old)
    return n


def topology(obj):
    me = obj.data
    q = sum(1 for p in me.polygons if len(p.vertices) == 4)
    t = sum(1 for p in me.polygons if len(p.vertices) == 3)
    return len(me.vertices), len(me.polygons), q, t, len(me.polygons) - q - t


def export(objs, path_noext, tex_dir=None):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]

    # 유니티용 FBX. 소품에서 쓴 값과 같게 맞춘다 — 한 장면에 같이 들어가므로
    # 축과 배율이 어긋나면 소품만 100배가 되거나 눕는다.
    bpy.ops.export_scene.fbx(
        filepath=path_noext + ".fbx",
        use_selection=True,
        apply_scale_options="FBX_SCALE_NONE",
        bake_space_transform=False,
        axis_forward="-Z", axis_up="Y",
        object_types={"MESH", "ARMATURE"},
        use_mesh_modifiers=False,      # 아마추어 모디파이어를 구워 버리면 리그가 죽는다
        add_leaf_bones=False,          # 유니티가 쓸데없는 끝뼈를 아바타에 넣는다
        primary_bone_axis="Y", secondary_bone_axis="X",
        armature_nodetype="NULL",
        bake_anim=False,
        path_mode="COPY", embed_textures=True,
        mesh_smooth_type="FACE",
    )
    bpy.ops.export_scene.gltf(
        filepath=path_noext + ".glb",
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=False,
        export_skins=True,
        export_animations=False,
    )


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="chars/out/bodies")
    ap.add_argument("--only", default=None)
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    report = []

    for role, macro in BODIES.items():
        if args.only and role not in args.only.split(",") \
           and SLUG[role] not in args.only.split(","):
            continue
        wipe()
        slug = SLUG[role]

        bm = HumanService.create_human(
            mask_helpers=True,
            # 헬퍼를 켜야 한다. 뼈를 어디 앉힐지 정하는 관절 큐브
            # (joint-l-elbow 같은 버텍스그룹)가 이 헬퍼 안에 들어 있다.
            # 끄면 JointCubes 라는 뭉뚱그린 그룹 하나만 남고, 리그는
            # 맞출 근거가 없어 JSON 기본 좌표에 그대로 앉는다.
            # 헬퍼 자체는 내보내지 않는다 — bake_shape 에서 떨군다.
            detailed_helpers=True,
            extra_vertex_groups=True,   # 손·머리 등 부위 그룹. 나중에 소품 앵커에 쓴다
            feet_on_ground=True,
            # race 는 스칼라가 아니라 딕셔너리다. 빼면 create_human 이
            # KeyError 로 죽는다 — 기본값을 채워 주지 않는다.
            macro_detail_dict={**macro, "race": dict(RACE)},
        )
        bm.name = f"body_{slug}"
        bm.data.name = f"body_{slug}"

        # 순서가 전부다.
        #
        # add_builtin_rig 은 뼈대를 "붙이기만" 한다. 몸에 맞추지는 않는다.
        # 그래서 이것만 하고 내보내면 1.48m 몸과 1.81m 몸이 똑같은 뼈대를
        # 쓴다 — head 뼈가 다섯 다 (0.000, -0.044, +0.697) 로 소수점까지
        # 같았고 어깨 관절 간격도 다섯 다 0.340m 였다. 맞추는 것은 refit 이다.
        #
        # 그리고 refit 은 셰이프키를 읽는다. 그러니 굽는 것은 맨 마지막이다.
        # 반대로 굽고 나서 refit 하면 MPFB 는 중립 몸을 보게 된다.
        arm = HumanService.add_builtin_rig(bm, RIG, import_weights=True)
        arm.name = f"rig_{slug}"
        arm.data.name = f"rig_{slug}"

        HumanService.refit(bm)

        keys = bake_shape(bm)

        v, f, q, t, n = topology(bm)
        h = bm.dimensions[2]
        bones = [b.name for b in arm.data.bones]

        export([bm, arm], os.path.join(args.out, slug))

        row = {
            "role": role, "slug": slug, "macro": macro,
            "verts": v, "faces": f, "quads": q, "tris": t, "ngons": n,
            "height_m": round(h, 4),
            "bones": len(bones),
            "rig": RIG,
            "baked_shapekeys": keys,
            "bone_names": bones,
        }
        report.append(row)
        print(f"  {slug:8s} {role}  키 {h:.3f}m  정점 {v:,}  사각 {q:,}"
              f"  삼각 {t}  n각 {n}  뼈 {len(bones)}", flush=True)

    # 다섯이 정말 같은 뼈 이름을 쓰는지 확인한다. 하나라도 다르면
    # 유니티에서 애니메이션 한 벌을 나눠 쓸 수 없다. 뼈 위치는 체형마다
    # 달라도 되고 그건 아바타 리타기팅이 흡수한다 — 이름이 관건이다.
    if len(report) > 1:
        base = report[0]["bone_names"]
        for row in report[1:]:
            if row["bone_names"] != base:
                a, b = set(base), set(row["bone_names"])
                raise SystemExit(
                    f"뼈 이름이 다르다: {row['slug']} — "
                    f"없는 것 {sorted(a-b)} / 더 있는 것 {sorted(b-a)}")
        print(f"[make_bodies] 뼈 이름 {len(base)}개가 {len(report)}종 모두 같다", flush=True)
    with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=2)
    print(f"[make_bodies] {len(report)}종 → {args.out}", flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(argv)
