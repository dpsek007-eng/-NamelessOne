# -*- coding: utf-8 -*-
"""동작만 담은 FBX 한 장 — 유니티의 3D 잔상을 움직이게 하는 유일한 길.

    blender --background --python chars/src/make_clips.py
    blender --background --python chars/src/make_clips.py -- --verify

## 왜 이 파일이 따로 있는가

동작 네 벌은 이미 `make_demo.py` 에 있다. 그런데 그것은 **GLB 안에만** 들어간다.
유니티에는 glTF 임포터가 없다 (`Packages/manifest.json` 에 없다). 그리고
`make_bodies.export` 는 FBX 를 내면서 `bake_anim=False` 로 애니메이션을 끈다 —
몸·옷은 정지 자산이라 그게 맞다. 그래서 **유니티가 읽을 수 있는 동작 파일이
하나도 없다.** `IremCharImport` 가 `importAnimation = False` 인 것도 그 때문이다.

여기서 그 구멍만 메운다. 몸도 옷도 넣지 않는다 — 아마추어와 액션만이다.
몸 다섯이 뼈 이름 53개를 똑같이 쓴다는 것을 `make_bodies` 가 확인해 두었으므로
(「뼈 이름 53개가 5종 모두 같다」), 동작 한 벌을 다섯이 나눠 쓴다.

## 클립을 다시 쓰지 않는다

네 벌은 `make_demo` 에서 **import 해서 그대로** 쓴다. 베끼면 GLB 뷰어와
유니티가 조용히 갈라진다. 축을 어느 방향으로 돌리는지가 저 파일에 측정으로
적혀 있고 (`docs/22` 「관절을 눈으로 확인했다」), 그 근거를 옮길 방법이 없다.

## 이름이 둘인 이유

유니티 쪽 런타임 어휘는 이미 영어다. `tables.json` 의 clips 가
`idle/walk/attack/hurt/fall` 이고 `BattleDirector` 가 `Play("attack")` 로 부른다.
그래서 **FBX 트랙 이름은 영어로 둔다.** 그러면 2D 스프라이트와 3D 몸이
같은 낱말로 불린다 — `IShadeView.Play("walk")` 하나로 둘 다 움직인다.
블렌더 액션 이름은 한국어 그대로다 (GLB 와 같아야 한다). 짝은 CLIPS 표에 있다.

## 두 벌을 새로 쓴다

2D 는 다섯 벌인데 3D 는 네 벌이라, `hurt` 와 `fall` 에 맞는 동작이 없었다.
없는 것을 다른 동작으로 둘러대면 화면에서 거짓말이 된다 — 맞았는데 두리번거리고
죽었는데 숨을 쉰다. 그래서 `맞음` 과 `쓰러짐` 을 여기서 쓴다. `make_demo` 는
건드리지 않는다 (GLB 쉰다섯 벌을 다시 굽지 않는다).

`돌아본다` 는 2D 에 짝이 없다. 뜰에서 쓴다 — 누가 지나가면 돌아본다.
"""
import argparse, json, os, sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_bodies as MB
import make_garments as MG
import make_demo as MD
from make_demo import X, Y, Z, key, merge, new_action, stash

OUT = "unity/Assets/Art/Chars/Clips/motion.fbx"

# 어느 몸에서 리그를 뜨는가. 유니티 쪽 `IremCharImport` 가 이 FBX 의 아바타를
# `Bodies/guard.fbx` 에서 복사하므로, 같은 몸에서 떠야 뼈 위치가 어긋나지 않는다.
SRC_ROLE = "수호"


# ---------------------------------------------------------------- 새 동작 두 벌
def clip_hurt(arm):
    """맞음 — 18프레임. 한 번 뒤로 밀리고 돌아온다.

    짧아야 한다. `BattleDirector` 는 한 걸음을 0.42초에 재생하므로
    (`StepSeconds`), 맞는 동작이 그보다 길면 다음 사건에 잘린다.
    18프레임은 24fps 로 0.75초, 30fps 로 0.6초다. 잘리는 것을 전제로
    **앞쪽 절반에 움직임을 다 넣는다** — 뒤가 잘려도 읽힌다.

    허리를 뒤로 젖히는 것이 아니라 **접는다.** 맞은 사람은 펴지 않는다.
    """
    act = new_action(arm, "맞음")
    for f, over in [
        (1, {}),
        (4, {                                                   # 충격
            "spine_01": [(X, 9.0)], "spine_02": [(X, 12.0)], "spine_03": [(X, 14.0)],
            "neck_01": [(X, 10.0)], "head": [(X, 16.0), (Z, -6.0)],
            "clavicle_l": [(Y, -7.0)], "clavicle_r": [(Y, 7.0)],
            "upperarm_l": [(Y, 34.0), (X, -18.0)], "lowerarm_l": [(Y, -30.0)],
            "upperarm_r": [(Y, -34.0), (X, -18.0)], "lowerarm_r": [(Y, 30.0)],
            "thigh_l": [(X, 6.0)], "thigh_r": [(X, 4.0)],
            "calf_l": [(X, 11.0)], "calf_r": [(X, 8.0)],
            "pelvis": [("loc", (0.0, -0.026, 0.0)), (X, 5.0)],
        }),
        (9, {                                                   # 버틴다
            "spine_02": [(X, 6.0)], "spine_03": [(X, 7.0)],
            "neck_01": [(X, 5.0)], "head": [(X, 8.0), (Z, -3.0)],
            "upperarm_l": [(Y, 26.0), (X, -8.0)], "lowerarm_l": [(Y, -20.0)],
            "upperarm_r": [(Y, -26.0), (X, -8.0)], "lowerarm_r": [(Y, 20.0)],
            "calf_l": [(X, 5.0)], "calf_r": [(X, 4.0)],
            "pelvis": [("loc", (0.0, -0.012, 0.0))],
        }),
        (18, {}),                                               # 제자리로
    ]:
        key(arm, f, merge(over))
    return act


def clip_fall(arm):
    """쓰러짐 — 40프레임. 돌지 않는다. 무릎이 먼저 꺾이고 접힌다.

    뒤로 넘어가게 만들지 않았다. 잔상은 바닥에 눕지 않는다 — 셰이더가
    발부터 알파를 먹이므로 (`Silhouette.shader` 의 `_FadeTop`, 물체 원점 기준),
    **주저앉으면서 흐려지는** 것이 이 게임의 사라짐이다. 누우면 원점이
    발이 아니라 옆구리가 되어 페이드가 엉뚱한 데서 시작한다.

    마지막 프레임을 유지해야 한다. 되돌아오면 죽은 사람이 일어난다.
    `loop: false` 로 쓰는 것을 전제로 40프레임 끝을 그대로 둔다.
    """
    act = new_action(arm, "쓰러짐")
    for f, over in [
        (1, {}),
        (6, {                                                   # 힘이 빠진다
            "spine_02": [(X, 5.0)], "spine_03": [(X, 7.0)],
            "neck_01": [(X, 6.0)], "head": [(X, 9.0)],
            "clavicle_l": [(Y, -5.0)], "clavicle_r": [(Y, 5.0)],
            "upperarm_l": [(Y, 12.0)], "upperarm_r": [(Y, -12.0)],
            "lowerarm_l": [(Y, -6.0)], "lowerarm_r": [(Y, 6.0)],
            "calf_l": [(X, 7.0)], "calf_r": [(X, 5.0)],
            "pelvis": [("loc", (0.0, -0.035, 0.0))],
        }),
        (16, {                                                  # 무릎이 꺾인다
            "spine_01": [(X, 10.0)], "spine_02": [(X, 16.0)], "spine_03": [(X, 20.0)],
            "neck_01": [(X, 14.0)], "head": [(X, 22.0), (Z, 5.0)],
            "clavicle_l": [(Y, -9.0)], "clavicle_r": [(Y, 9.0)],
            "upperarm_l": [(Y, 8.0), (X, -10.0)], "lowerarm_l": [(Y, -22.0)],
            "upperarm_r": [(Y, -8.0), (X, -10.0)], "lowerarm_r": [(Y, 22.0)],
            "thigh_l": [(X, -34.0), (Y, 8.0)], "thigh_r": [(X, -30.0), (Y, -7.0)],
            "calf_l": [(X, 62.0)], "calf_r": [(X, 56.0)],
            "foot_l": [(X, -14.0)], "foot_r": [(X, -12.0)],
            "pelvis": [("loc", (0.0, -0.26, 0.0)), (X, 8.0)],
        }),
        (28, {                                                  # 접힌다
            "spine_01": [(X, 16.0)], "spine_02": [(X, 24.0)], "spine_03": [(X, 30.0)],
            "neck_01": [(X, 18.0)], "head": [(X, 30.0), (Z, 7.0)],
            "clavicle_l": [(Y, -11.0)], "clavicle_r": [(Y, 11.0)],
            "upperarm_l": [(Y, 4.0), (X, -4.0)], "lowerarm_l": [(Y, -34.0)],
            "upperarm_r": [(Y, -4.0), (X, -4.0)], "lowerarm_r": [(Y, 34.0)],
            "thigh_l": [(X, -52.0), (Y, 12.0)], "thigh_r": [(X, -48.0), (Y, -10.0)],
            "calf_l": [(X, 92.0)], "calf_r": [(X, 86.0)],
            "foot_l": [(X, -20.0)], "foot_r": [(X, -18.0)],
            "pelvis": [("loc", (0.0, -0.44, 0.0)), (X, 12.0)],
        }),
        (40, {                                                  # 멈춘다 (이 자세로 끝난다)
            "spine_01": [(X, 17.0)], "spine_02": [(X, 26.0)], "spine_03": [(X, 32.0)],
            "neck_01": [(X, 19.0)], "head": [(X, 33.0), (Z, 8.0)],
            "clavicle_l": [(Y, -11.0)], "clavicle_r": [(Y, 11.0)],
            "upperarm_l": [(Y, 3.0), (X, -2.0)], "lowerarm_l": [(Y, -36.0)],
            "upperarm_r": [(Y, -3.0), (X, -2.0)], "lowerarm_r": [(Y, 36.0)],
            "thigh_l": [(X, -55.0), (Y, 13.0)], "thigh_r": [(X, -51.0), (Y, -11.0)],
            "calf_l": [(X, 96.0)], "calf_r": [(X, 90.0)],
            "foot_l": [(X, -21.0)], "foot_r": [(X, -19.0)],
            "pelvis": [("loc", (0.0, -0.47, 0.0)), (X, 13.0)],
        }),
    ]:
        key(arm, f, merge(over))
    return act


# 유니티 이름 · 블렌더 액션 이름 · 만드는 함수 · 도는가
#
# 앞 다섯은 `tables.json` 의 clips 와 낱말이 같다. 2D 스프라이트와 3D 몸이
# 같은 이름으로 불려야 `IShadeView` 하나로 둘을 다룰 수 있다.
CLIPS = [
    ("idle",   "숨",       MD.clip_breath, True),
    ("walk",   "걷기",     MD.clip_walk,   True),
    ("attack", "휘두름",   MD.clip_swing,  False),
    ("hurt",   "맞음",     clip_hurt,      False),
    ("fall",   "쓰러짐",   clip_fall,      False),
    ("look",   "돌아본다", MD.clip_look,   False),   # 3D 전용. 뜰에서 쓴다
]


def export_clips(arm, path):
    """`make_bodies.export` 와 같은 축·배율. 다른 것은 애니메이션을 켠 것뿐이다.

    소품·몸·옷이 같은 장면에 들어오므로 축이 어긋나면 하나만 눕는다.
    그래서 플래그를 글자 그대로 맞춘다. `object_types` 에서 MESH 를 뺀 것은
    여기 메시가 아예 없기 때문이다.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(
        filepath=path,
        use_selection=True,
        apply_scale_options="FBX_SCALE_NONE",
        bake_space_transform=False,
        axis_forward="-Z", axis_up="Y",
        object_types={"ARMATURE"},
        use_mesh_modifiers=False,
        add_leaf_bones=False,
        primary_bone_axis="Y", secondary_bone_axis="X",
        armature_nodetype="NULL",
        # 여기가 make_bodies 와 갈리는 유일한 곳이다.
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=True,    # NLA 트랙 하나 = FBX 테이크 하나
        bake_anim_use_all_actions=False,  # 켜면 액션까지 따로 나가 테이크가 두 배가 된다
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=0.0,    # 키를 줄이면 GLB 와 달라진다
        path_mode="COPY",
    )


def build(out):
    MB.wipe()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)

    bm, arm = MG.build_body(SRC_ROLE)
    L = MG.landmarks(bm, arm)
    height = round(L["height"], 4)
    bones = [b.name for b in arm.data.bones]

    # 몸은 리그를 앉히는 데만 쓴다. 내보내기 전에 지운다 — 동작 파일에
    # 메시가 들어가면 유니티가 잔상 하나마다 쓰지도 않는 몸을 더 들고 있는다.
    bpy.data.objects.remove(bm, do_unlink=True)

    made = []
    for uname, kname, fn, loop in CLIPS:
        act = fn(arm)
        assert act.name == kname, f"액션 이름이 다르다: {act.name} != {kname}"
        stash(arm, act, uname)          # 트랙 이름이 FBX 테이크 이름이 된다
        n = int(act.frame_range[1] - act.frame_range[0]) + 1
        made.append(dict(unity=uname, action=kname, frames=n, loop=loop))

    # 액션을 만드는 동안 포즈 뼈에 값이 남는다. NLA 로 굽기 전에 되돌린다 —
    # 트랙마다 구울 때 그 트랙이 안 키운 뼈가 이 값을 물고 나간다.
    # (make_demo 가 같은 이유로 같은 일을 한다. base_pose 가 전 뼈를 키우므로
    #  실제로 새는 뼈는 없지만, 전제가 깨지면 조용히 틀리는 쪽이라 남겨 둔다.)
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()

    export_clips(arm, out)

    rep = dict(src_role=SRC_ROLE, src_height_m=height, bones=len(bones),
               path=out, bytes=os.path.getsize(out), clips=made)
    with open(os.path.splitext(out)[0] + ".report.json", "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=2)
    print(f"[make_clips] {out}  뼈 {len(bones)}  동작 {len(made)}벌  "
          f"{rep['bytes']:,}바이트", flush=True)
    for c in made:
        print(f"    {c['unity']:7s} {c['action']:8s} {c['frames']:3d}프레임"
              f"  {'돈다' if c['loop'] else '한 번'}", flush=True)
    return rep


def _fcurves(act):
    """블렌더 5.x 는 액션에서 `fcurves` 를 떼고 레이어·슬롯 아래로 옮겼다.
    커브 수는 「동작이 비어 있지 않다」를 재는 값이라 버리지 않고 양쪽을 본다."""
    if hasattr(act, "fcurves"):
        return len(act.fcurves)
    n = 0
    for lay in getattr(act, "layers", []):
        for st in getattr(lay, "strips", []):
            for cb in getattr(st, "channelbags", []):
                n += len(cb.fcurves)
    return n


def verify(out):
    """구운 FBX 를 다시 읽어 실제로 몇 벌이 들어갔는지 센다.

    내보내기가 성공했다는 말만으로는 모른다. 블렌더의 FBX 임포터는
    테이크 하나마다 액션 하나를 만들므로, 액션 수가 곧 테이크 수다.
    유니티가 읽을 수와 같다.
    """
    MB.wipe()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    bpy.ops.import_scene.fbx(filepath=out)

    acts = sorted(bpy.data.actions, key=lambda a: a.name)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    want = {c[0]: c for c in CLIPS}

    print(f"[verify] {out}", flush=True)
    print(f"[verify] 아마추어 {len(arms)}개"
          f"  뼈 {len(arms[0].data.bones) if arms else 0}개"
          f"  액션 {len(acts)}벌", flush=True)

    bad = []
    for a in acts:
        f0, f1 = a.frame_range
        n = int(f1 - f0) + 1
        hit = [k for k in want if k in a.name]
        print(f"    {a.name:28s} {n:3d}프레임  {_fcurves(a):4d}커브"
              f"  {'← ' + hit[0] if hit else '← 짝 없음'}", flush=True)
        if _fcurves(a) == 0:
            bad.append(f"커브가 없다 (이름만 있고 안 움직인다): {a.name}")
        if not hit:
            bad.append(f"이름에서 클립을 못 찾겠다: {a.name}")
        else:
            exp = want[hit[0]][2]
            # 프레임 수는 내보내기에서 ±1 밀릴 수 있다. 3 이상 벌어지면 다른 동작이다.
            with open(os.path.splitext(out)[0] + ".report.json", encoding="utf-8") as f:
                rep = json.load(f)
            e = next(c["frames"] for c in rep["clips"] if c["unity"] == hit[0])
            if abs(n - e) > 2:
                bad.append(f"{hit[0]}: 프레임이 {e} 여야 하는데 {n}")
    if len(acts) != len(CLIPS):
        bad.append(f"동작이 {len(CLIPS)}벌이어야 하는데 {len(acts)}벌이다")
    if arms and len(arms[0].data.bones) != 53:
        bad.append(f"뼈가 53개여야 하는데 {len(arms[0].data.bones)}개다")

    if bad:
        for b in bad:
            print(f"  안 됨: {b}", flush=True)
        raise SystemExit(1)
    print(f"[verify] {len(acts)}벌 전부 확인", flush=True)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--verify", action="store_true", help="이미 구운 FBX 를 다시 읽어 센다")
    args = ap.parse_args(argv)
    if args.verify:
        verify(args.out)
    else:
        build(args.out)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(argv)
