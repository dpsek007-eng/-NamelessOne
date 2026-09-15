# -*- coding: utf-8 -*-
"""한 사람만 제대로 — 얼굴·관절·동작을 눈으로 보게 만든다.

    blender --background --python chars/src/make_demo.py -- \
            --role 수호 --cls 병졸 --out chars/out/demo

내는 것은 GLB 한 개다. 안에 세 가지가 같이 들어간다.

  · **얼굴**  옷을 안 입은 몸을 따로 넣는다. 머리가 메시로 들어 있어서
              돌려 보면 이목구비가 보인다. 옷을 끄고 켜는 건 뷰어가 한다.
  · **관절**  뼈 53개. 원래 내보내던 GLB 와 같은 뼈대다 (game_engine).
  · **동작**  액션 네 벌을 NLA 트랙에 얹어 내보낸다. glTF 애니메이션 네 개가 된다.

**얼굴 뼈는 없다.** 53개가 전부 몸통·팔다리·손가락이고 턱도 눈도 없다.
그래서 표정은 못 움직인다. 움직이는 것은 고개까지다. 이건 리그의 한계지
이 스크립트의 한계가 아니다 — 표정을 넣으려면 셰이프키를 따로 굽거나
얼굴 뼈가 있는 리그로 갈아야 한다.

내보낼 때 export_animations 를 켜는 곳은 여기뿐이다. make_bodies.export 는
꺼 두고 있다 (몸·옷은 정지 자산이라 애니메이션이 짐만 된다).
"""
import argparse, json, math, os, sys

import bpy
from mathutils import Vector, Quaternion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_bodies as MB
import make_garments as MG
import garments as G
from bodies import SLUG as BODY_SLUG, BODIES


# ---------------------------------------------------------------- 회전 도우미
def qrot(pb, axis, deg):
    """아마추어 공간의 축으로 돌린다.

    포즈 뼈의 회전은 **뼈 자기 축** 기준이라, 뼈마다 어느 쪽이 앞인지가 다르다.
    허벅지에 「X 로 20도」라고 적으면 뼈에 따라 앞으로 차기도 하고 옆으로
    벌리기도 한다. 그래서 매번 아마추어 축(X 좌우 · Y 앞뒤 · Z 위)으로 적고
    여기서 뼈 축으로 옮긴다. 읽는 사람이 방향을 상상하지 않아도 되게.
    """
    m = pb.bone.matrix_local.to_3x3()
    ax = (m.inverted() @ Vector(axis))
    if ax.length < 1e-9:
        return Quaternion((1, 0, 0, 0))
    return Quaternion(ax.normalized(), math.radians(deg))


def key(arm, frame, poses):
    """poses = {뼈이름: [(축, 각도), ...]} · 위치는 ("loc", (x,y,z))"""
    for name, ops in poses.items():
        pb = arm.pose.bones.get(name)
        if pb is None:
            raise SystemExit(f"그런 뼈가 없다: {name}")
        pb.rotation_mode = "QUATERNION"
        q = Quaternion((1, 0, 0, 0))
        loc = None
        for op in ops:
            if op[0] == "loc":
                loc = op[1]
            else:
                q = q @ qrot(pb, op[0], op[1])
        pb.rotation_quaternion = q
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        if loc is not None:
            pb.location = loc
            pb.keyframe_insert("location", frame=frame)


def new_action(arm, name):
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    if arm.animation_data is None:
        arm.animation_data_create()
    arm.animation_data.action = act
    return act


def stash(arm, act, name):
    """NLA 트랙 한 개에 액션 한 벌. glTF 를 NLA_TRACKS 로 내보내면
    트랙 이름이 그대로 애니메이션 이름이 된다."""
    arm.animation_data.action = None
    tr = arm.animation_data.nla_tracks.new()
    tr.name = name
    tr.strips.new(name, int(act.frame_range[0]), act)


X, Y, Z = (1, 0, 0), (0, 1, 0), (0, 0, 1)

# 축은 상상하지 않고 재서 정했다. 뼈 여섯 개를 55도씩 여섯 방향으로 돌려
# 정면에서 한 장씩 뽑아 보고 골랐다 (docs/22 「관절을 눈으로 확인했다」).
#   upperarm  Y+  팔을 위로 (오른팔은 Y−)   X+  앞으로
#   lowerarm  Y+  팔꿈치 굽힘 (오른팔 기준)
#   thigh     X−  앞으로 차기               Y   벌리기
#   calf      X+  무릎 굽힘 (발뒤꿈치가 뒤로) ← X− 는 반대로 꺾인다
#   손가락     Y+  주먹 (오른손 기준)
# 왼쪽 뼈는 Y·Z 부호가 뒤집힌다. 좌우 대칭이라 그렇다.

FINGERS = [f"{f}_{s}_{lr}" for lr in ("l", "r")
           for f in ("index", "middle", "ring", "pinky") for s in ("01", "02", "03")]


def base_pose():
    """모든 동작이 이 자세 위에 얹힌다.

    두 가지 때문에 필요하다.
    1. MPFB 기본 자세는 팔을 크게 벌린 A자다. 그대로 두면 서 있는 것이 아니라
       측정용 자세로 보인다. 팔을 20도 몸쪽으로 당기고 손가락을 살짝 쥔다.
    2. **NLA 누수를 막는다.** 액션이 안 건드린 뼈는 트랙을 갈아도 직전 값이
       그대로 남는다. 처음에 이걸 몰라서, 다리를 안 건드리는 「숨」에도
       걷기의 마지막 프레임에서 접힌 무릎이 그대로 붙어 나왔다.
       그래서 **네 동작이 전부 같은 뼈 집합을 키운다.** 안 쓰는 뼈도 0으로 찍는다.
    """
    p = {
        "pelvis": [("loc", (0.0, 0.0, 0.0))],
        "spine_01": [(X, 0.0)], "spine_02": [(X, 0.0)], "spine_03": [(X, 0.0)],
        "neck_01": [(X, 0.0)], "head": [(X, 0.0)],
        "clavicle_l": [(Y, 0.0)], "clavicle_r": [(Y, 0.0)],
        "upperarm_l": [(Y, 20.0)], "upperarm_r": [(Y, -20.0)],
        "lowerarm_l": [(Y, -12.0)], "lowerarm_r": [(Y, 12.0)],
        "hand_l": [(X, 0.0)], "hand_r": [(X, 0.0)],
        "thigh_l": [(X, 0.0)], "thigh_r": [(X, 0.0)],
        "calf_l": [(X, 0.0)], "calf_r": [(X, 0.0)],
        "foot_l": [(X, 0.0)], "foot_r": [(X, 0.0)],
    }
    for b in FINGERS:
        p[b] = [(Y, 24.0 if b.endswith("_r") else -24.0)]
    return p


def merge(*layers):
    """뒤에 오는 것이 앞의 것을 덮는다. 없는 뼈는 base 값을 그대로 쓴다."""
    out = base_pose()
    for lay in layers:
        for k, v in lay.items():
            out[k] = v
    return out


# ---------------------------------------------------------------- 동작 네 벌
def clip_breath(arm):
    """숨 — 96프레임 한 바퀴. 서 있는 동안 늘 돈다. 크게 움직이면 안 된다."""
    act = new_action(arm, "숨")
    N = 96
    for i in range(N + 1):
        w = 2 * math.pi * i / N
        t, s = math.sin(w), math.sin(w - 0.6)   # 어깨는 가슴보다 조금 늦다
        key(arm, i + 1, merge({
            "spine_01": [(X, -0.5 * t)],
            "spine_02": [(X, -1.3 * t)],
            "spine_03": [(X, -1.0 * t)],
            "clavicle_l": [(Y, -1.4 * s)],
            "clavicle_r": [(Y, 1.4 * s)],
            "upperarm_l": [(Y, 20.0 + 1.2 * s)],
            "upperarm_r": [(Y, -20.0 - 1.2 * s)],
            "neck_01": [(X, 0.7 * t)],
            "head": [(X, 0.4 * t), (Z, 1.1 * math.sin(w * 0.5))],
            "pelvis": [("loc", (0.0, 0.0035 * t, 0.0))],
        }))
    return act


def clip_walk(arm):
    """걷기 — 32프레임 한 바퀴. 관절이 접히는지 보려고 넣는다."""
    act = new_action(arm, "걷기")
    N = 32
    for i in range(N + 1):
        p = 2 * math.pi * i / N
        sl, sr = math.sin(p), math.sin(p + math.pi)
        # 무릎은 한쪽으로만 접힌다. 뒤로 보내는 구간에서만 굽힌다.
        kl = max(0.0, -math.sin(p - 1.0)) ** 1.5
        kr = max(0.0, -math.sin(p + math.pi - 1.0)) ** 1.5
        key(arm, i + 1, merge({
            "pelvis": [("loc", (0.0, 0.018 * abs(math.sin(p)) - 0.009, 0.0)),
                       (Y, 2.5 * math.sin(p))],
            "spine_01": [(Z, -3.0 * sl)],
            "spine_03": [(Z, 4.5 * sl)],
            "thigh_l": [(X, -24.0 * sl)], "calf_l": [(X, 46.0 * kl)],
            "thigh_r": [(X, -24.0 * sr)], "calf_r": [(X, 46.0 * kr)],
            "foot_l": [(X, -10.0 * kl)], "foot_r": [(X, -10.0 * kr)],
            "upperarm_l": [(Y, 20.0), (X, 16.0 * sr)],
            "upperarm_r": [(Y, -20.0), (X, 16.0 * sl)],
            "lowerarm_l": [(Y, -12.0 - 10.0 * max(0.0, sr))],
            "lowerarm_r": [(Y, 12.0 + 10.0 * max(0.0, sl))],
            "head": [(Z, 1.8 * sl)],
        }))
    return act


def clip_swing(arm):
    """휘두름 — 48프레임. 손에 든 것을 내리치는 짓.

    자세를 비율로 못 적는다. 드는 길과 내리치는 길이 서로 다른 축을 쓰기
    때문이다. 그래서 박자마다 자세를 통째로 적는다.

    내리치는 박자를 여섯 벌 뽑아 보고 골랐다 (/tmp/st). 처음에 쓰던
    (upperarm_r Y-34, X+40) 은 팔을 **카메라 쪽으로** 내미는 짓이라,
    정면 정사영에서는 앞뒤가 안 보여서 그냥 서 있는 것으로 읽혔다.
    앞으로 미는 X 를 걷고 Y 를 -62 까지 내려, 팔이 몸 앞을 가로질러
    화면 안에서 실제로 움직이게 했다. 정면 고정 카메라로 앞으로 뻗는
    짓은 못 보여 준다 — 이 동작이 읽히는 것은 높이 든 박자와의 낙차다.

    Y 를 -62 까지 내렸더니 손이 넓적다리 **안으로** 들어가 손가락만
    밖으로 삐져나왔다. -54 로 올리고 앞으로 미는 X 를 13 으로 줘서
    손이 다리 앞을 지나가게 했다.
    """
    act = new_action(arm, "휘두름")
    beats = [
        (1, {}),                                                    # 선다
        (13, {                                                      # 든다
            "spine_03": [(Z, -14.0), (X, -5.0)], "spine_01": [(Z, -6.0)],
            "clavicle_r": [(Y, 6.0)],
            "upperarm_r": [(Y, 72.0), (X, -22.0)], "lowerarm_r": [(Y, 62.0)],
            "hand_r": [(X, -14.0)],
            "upperarm_l": [(Y, 26.0), (X, -14.0)],
            "neck_01": [(Z, -7.0)], "head": [(Z, -9.0), (X, -5.0)],
            "thigh_r": [(X, 7.0)], "thigh_l": [(X, -6.0)], "calf_l": [(X, 9.0)],
        }),
        (18, {                                                      # 더 든다 (예비 동작)
            "spine_03": [(Z, -17.0), (X, -8.0)], "spine_01": [(Z, -7.0)],
            "clavicle_r": [(Y, 8.0)],
            "upperarm_r": [(Y, 80.0), (X, -30.0)], "lowerarm_r": [(Y, 70.0)],
            "hand_r": [(X, -18.0)],
            "upperarm_l": [(Y, 28.0), (X, -16.0)],
            "neck_01": [(Z, -8.0)], "head": [(Z, -10.0), (X, -6.0)],
            "thigh_r": [(X, 8.0)], "thigh_l": [(X, -7.0)], "calf_l": [(X, 10.0)],
        }),
        (25, {                                                      # 내리친다
            "spine_03": [(Z, 24.0), (X, 10.0)], "spine_01": [(Z, 12.0)],
            "clavicle_r": [(Y, -4.0)],
            "upperarm_r": [(Y, -54.0), (X, 13.0)], "lowerarm_r": [(Y, 16.0)],
            "hand_r": [(X, 12.0)],
            "upperarm_l": [(Y, 12.0), (X, 22.0)], "lowerarm_l": [(Y, -26.0)],
            "neck_01": [(Z, 6.0)], "head": [(Z, 8.0), (X, 12.0)],
            "thigh_l": [(X, -14.0)], "calf_l": [(X, 16.0)], "thigh_r": [(X, 10.0)],
        }),
        (31, {                                                      # 되튄다
            "spine_03": [(Z, 9.0), (X, 6.0)],
            "upperarm_r": [(Y, -36.0), (X, 9.0)], "lowerarm_r": [(Y, 26.0)],
            "upperarm_l": [(Y, 16.0), (X, 12.0)], "lowerarm_l": [(Y, -20.0)],
            "head": [(Z, 4.0), (X, 6.0)],
            "thigh_l": [(X, -8.0)], "calf_l": [(X, 9.0)],
        }),
        (48, {}),                                                   # 제자리로
    ]
    for f, over in beats:
        key(arm, f, merge(over))
    return act


def clip_look(arm):
    """돌아본다 — 72프레임. 얼굴을 보려고 넣는 것이라 목만 크게 돈다."""
    act = new_action(arm, "돌아본다")
    for f, a in [(1, 0.0), (18, -1.0), (30, -1.0), (48, 1.0), (60, 1.0), (72, 0.0)]:
        key(arm, f, merge({
            "spine_03": [(Z, 5.0 * a)],
            "neck_01": [(Z, 20.0 * a), (X, -3.0 * abs(a))],
            "head": [(Z, 24.0 * a), (Y, -5.0 * a), (X, -4.0 * abs(a))],
            "clavicle_l": [(Y, 2.5 * a)], "clavicle_r": [(Y, 2.5 * a)],
        }))
    return act


CLIPS = [("숨", clip_breath), ("걷기", clip_walk),
         ("휘두름", clip_swing), ("돌아본다", clip_look)]


# ---------------------------------------------------------------- 내보내기
def export_anim(objs, path_noext):
    """make_bodies.export 와 같은 축·배율. 다른 것은 애니메이션을 켠 것뿐이다."""
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(
        filepath=path_noext + ".glb",
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_apply=False,
        export_skins=True,
        export_animations=True,
        export_animation_mode="NLA_TRACKS",
        export_bake_animation=True,
        export_optimize_animation_size=False,
        export_lights=True,
    )


def one(role, cls, out, frames=None):
    """한 사람 — 몸·옷·리그·동작 네 벌을 GLB 한 장으로.

    쉰다섯을 한 번에 돌 때도 이 함수를 그냥 되부른다. 매 바퀴 MB.wipe() 가
    장면을 비우지만 액션은 사용자가 0 이 되어도 블렌더가 한 바퀴 더 들고
    있으므로, 여기서 직접 지운다. 안 지우면 쉰다섯 바퀴에 액션이 220개
    쌓이고, 이름이 「숨.001」처럼 밀려 트랙 이름이 어긋난다.
    """
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)

    args = argparse.Namespace(role=role, cls=cls, out=out, frames=frames)
    os.makedirs(args.out, exist_ok=True)

    sp = G.spec(args.cls)
    bm, arm = MG.build_body(args.role)
    L = MG.landmarks(bm, arm)

    # 옷을 먼저 깎는다. 케이지(helper-*)가 아직 몸에 붙어 있어야 한다.
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
    gar = MG.join(parts, f"garment_{BODY_SLUG[args.role]}_{sp['slug']}")
    MG.bind(gar, arm)

    # 이제 몸에서 케이지를 떼어낸다. 안 떼면 옷 만들 때 쓴 상자가
    # 몸에 붙어 나가서, 옷을 꺼도 몸이 안 보인다.
    bpy.context.view_layer.objects.active = bm
    for m in [m for m in bm.modifiers if m.type == "MASK"]:
        bpy.ops.object.modifier_apply(modifier=m.name)
    bm.name = bm.data.name = f"body_{BODY_SLUG[args.role]}"
    skin = bpy.data.materials.new("skin")
    skin.diffuse_color = (0.68, 0.55, 0.47, 1.0)
    bm.data.materials.clear()
    bm.data.materials.append(skin)
    MG.bind(bm, arm)

    # 동작 네 벌
    made = []
    for name, fn in CLIPS:
        act = fn(arm)
        stash(arm, act, name)
        made.append((name, int(act.frame_range[1] - act.frame_range[0]) + 1))

    # 액션을 만드는 동안 포즈 뼈에 값이 남는다. NLA 로 내보내기 전에 쉼자세로
    # 되돌린다 — 트랙마다 구울 때 안 키운 뼈가 이 값을 그대로 물고 나간다.
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
    bpy.context.view_layer.update()

    name = f"{BODY_SLUG[args.role]}_{sp['slug']}"
    export_anim([bm, gar, arm], os.path.join(args.out, name))

    report = dict(role=args.role, cls=args.cls, slug=name,
                  bones=len(arm.data.bones),
                  face_bones=[b.name for b in arm.data.bones
                              if any(k in b.name for k in ("jaw", "eye", "brow", "lip"))],
                  body_tris=MG.solidify_check(bm)[2],
                  garment_tris=MG.solidify_check(gar)[2],
                  height_m=round(L["height"], 4),
                  clips=[dict(name=n, frames=f) for n, f in made])
    print(f"[make_demo] {name}  뼈 {report['bones']}  "
          f"얼굴뼈 {len(report['face_bones'])}  동작 {len(made)}벌  "
          f"몸 {report['body_tris']:,} 옷 {report['garment_tris']:,}", flush=True)

    if args.frames:
        shoot_frames(arm, bm, gar, L, args.frames, name)
    return report


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--role", default=None, help="하나만 뽑을 때")
    ap.add_argument("--cls", default=None)
    ap.add_argument("--roles", default=None, help="쉼표로. 안 주면 다섯 전부")
    ap.add_argument("--classes", default=None, help="쉼표로. 안 주면 열하나 전부")
    ap.add_argument("--out", default="chars/out/demo")
    ap.add_argument("--frames", default=None,
                    help="확인용 PNG 를 낼 곳. 주면 동작마다 몇 장 뽑는다")
    ap.add_argument("--skip-done", action="store_true",
                    help="이미 GLB 가 있으면 건너뛴다. 밤새 돌다 끊겼을 때 이어 돌리려고")
    args = ap.parse_args(argv)

    roles = ([args.role] if args.role else
             (args.roles.split(",") if args.roles else list(BODIES)))
    classes = ([args.cls] if args.cls else
               (args.classes.split(",") if args.classes else list(G.ROBE)))
    os.makedirs(args.out, exist_ok=True)

    rows = []
    ip = os.path.join(args.out, "index.json")
    if os.path.exists(ip):
        with open(ip, encoding="utf-8") as f:
            rows = json.load(f).get("rows", [])
    have = {r["slug"]: r for r in rows}

    n = len(roles) * len(classes)
    print(f"[make_demo] {len(roles)}역할 x {len(classes)}계층 = {n}벌 → {args.out}",
          flush=True)
    for role in roles:
        for cls in classes:
            slug = f"{BODY_SLUG[role]}_{G.SLUG[cls]}"
            if args.skip_done and os.path.exists(os.path.join(args.out, slug + ".glb")):
                print(f"  건너뜀 {slug}", flush=True)
                continue
            have[slug] = one(role, cls, args.out, args.frames)
            rows = [have[s] for s in sorted(have)]
            with open(ip, "w", encoding="utf-8") as f:
                json.dump(dict(rows=rows), f, ensure_ascii=False, indent=1)

    # 한 사람 시연은 수호·병졸을 쓴다. 뷰어가 report.json 을 본다.
    show = have.get("guard_soldier") or (rows[0] if rows else None)
    if show:
        with open(os.path.join(args.out, "report.json"), "w", encoding="utf-8") as f:
            json.dump(show, f, ensure_ascii=False, indent=2)
    print(f"[make_demo] 표에 {len(rows)}벌", flush=True)


def shoot_frames(arm, bm, gar, L, out, name):
    """눈으로 확인할 장. 동작마다 여섯 장씩, 옷을 끈 채로 뽑는다 —
    관절이 접히는지 보려는 것이라 옷에 가리면 안 된다."""
    os.makedirs(out, exist_ok=True)
    MG.setup_shot(res=(320, 480))
    bpy.context.scene.display.shading.color_type = "MATERIAL"
    bpy.context.scene.display.shading.light = "STUDIO"
    gar.hide_render = True
    for tr in arm.animation_data.nla_tracks:
        for t2 in arm.animation_data.nla_tracks:
            t2.mute = (t2 != tr)
        st = tr.strips[0]
        f0, f1 = int(st.frame_start), int(st.frame_end)
        for k in range(6):
            f = f0 + round((f1 - f0) * k / 6.0)
            bpy.context.scene.frame_set(f)
            MG.shoot(os.path.join(out, f"{name}_{tr.name}_{k}.png"),
                     L["height"], L["z0"])
    for t2 in arm.animation_data.nla_tracks:
        t2.mute = False
    gar.hide_render = False
    print(f"[make_demo] 확인용 {len(list(arm.animation_data.nla_tracks))*6}장 → {out}", flush=True)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    main(argv)
