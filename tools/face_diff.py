# -*- coding: utf-8 -*-
"""얼굴이 역할을 나르는가 — 실루엣에 물어본 것을 얼굴에 다시 물어본다.

실루엣에서는 역할이 2.13% 밖에 안 갈렸다 (`tools/silhouette_diff.py`).
옷이 몸을 덮어서다. 그러면 얼굴이 그 자리를 대신할 수 있는가.

  python3 tools/face_diff.py --clip          ← 이걸 쓴다
  python3 tools/face_diff.py [--whole] [--sheet]   픽셀로 재는 옛 방식

**픽셀로 재는 방식은 버렸다.** 처음엔 잘라낸 얼굴을 픽셀로 뺐다. 역할도
계층도 잡음 바닥에 붙어 나왔다 (역할 1.00배 · 계층 1.10배). 그런데 눈으로
보면 성직 열은 다섯 줄이 전부 민머리다. **보이는 것을 못 잡는 자는 자가
아니다.** 얼굴이 장마다 다른 자리·다른 크기로 있어서, 픽셀을 그대로 빼면
사람이 다른 것만 재게 된다. 코드는 대조용으로 남겨 뒀다.

--clip 은 CLIP 이미지 임베딩으로 잰다. 계층을 잡음의 3.07배로 잡아낸다 —
눈금이 맞는다. 그래서 역할 값도 믿을 수 있다.

재는 법이 실루엣 때와 다른 점이 둘 있다.

1. **얼굴 상자로 잘라낸다.** 머리쓰개와 옷을 그대로 두고 재면 계층이
   이길 게 뻔하다 (성직은 민머리, 술사는 두건이다). 상자 안만 재야
   「얼굴 자체가 역할을 나르는가」를 묻는 게 된다.
2. **칸마다 6장을 평균한다.** 칸마다 딴사람이 나오므로 한 장씩 견주면
   역할이 아니라 사람이 달라서 생긴 차이를 재게 된다. 평균을 내면
   개인은 지워지고 그 칸에 **계통적으로** 남는 것만 남는다.
3. **잡음 바닥을 같이 잰다.** 6장을 셋씩 두 묶음으로 갈라 같은 칸끼리
   견준다. 역할도 계층도 안 다른 짝이니, 여기서 나오는 값이 "아무것도
   안 달라도 나오는 차이" 다. 역할 값이 이보다 크지 않으면 아무 말도
   할 수 없다. 세 값 모두 **3장 평균**으로 재야 견줄 수 있어서, 표는
   전부 반쪽 묶음으로 짠다 (6장 평균은 그림에만 쓴다).

밝기는 z 정규화로 지운다. 광원이 한쪽인데 장마다 세기가 달라서, 안 지우면
얼굴이 아니라 조명 밝기를 재게 된다.
"""
import os, sys, json, itertools
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACES = os.path.join(ROOT, "pipeline3d/out/faces")
ROLES = [("guard","수호"),("resist","저항"),("devote","헌신"),("seek","탐구"),("flee","도피")]
TIERS = [("royal","왕실"),("noble","귀족"),("mage","술사"),("clergy","성직"),
         ("clerk","관리"),("merchant","상인"),("artisan","장인"),
         ("peasant","농어민"),("soldier","병졸"),("servant","하인"),("vagrant","유랑")]
N = 128          # 잘라낸 얼굴을 이 크기로 맞춘다
CROP = 1.9       # 상자 너비의 몇 배를 자를지. 턱과 이마가 들어가되 두건은 덜 들어오게


def crop(path, box, whole=False):
    """얼굴 상자를 가운데 두고 정사각으로 자른 뒤 z 정규화한다.

    whole=True 면 안 자르고 화폭 전체를 쓴다. 머리쓰개와 옷이 들어온다.
    상자 안만 잰 값과 견주면 「계층이 얼굴에 있는지 머리쓰개에 있는지」가
    갈린다.
    """
    im = Image.open(path).convert("L")
    W, H = im.size
    if whole:
        v = np.asarray(im.resize((N, N), Image.BICUBIC), dtype=np.float32)
        return (v - v.mean()) / (v.std() + 1e-6)
    cx, cy = (box["x"] + box["w"] / 2) * W, (box["y"] + box["h"] / 2) * H
    s = box["w"] * W * CROP / 2
    # 얼굴이 가장자리에 붙어 있으면 정사각이 화폭 밖으로 나간다. 검게 메우면
    # 그 검정을 재게 되므로, 크기를 줄이고 가운데를 안쪽으로 민다.
    s = min(s, W / 2, H / 2)
    cx = min(max(cx, s), W - s)
    cy = min(max(cy, s), H - s)
    a = im.resize((N, N), Image.BICUBIC, box=(cx - s, cy - s, cx + s, cy + s))
    v = np.asarray(a, dtype=np.float32)
    return (v - v.mean()) / (v.std() + 1e-6)


def diff(a, b):
    """정규화된 두 평균 얼굴의 평균 절대차 (표준편차 단위)."""
    return float(np.abs(a - b).mean())


def cos(a, b):
    """CLIP 벡터끼리는 코사인 거리로 잰다 (0 = 같다)."""
    a = a / (np.linalg.norm(a) + 1e-9)
    b = b / (np.linalg.norm(b) + 1e-9)
    return float(1.0 - a @ b)


def load_clip(facedir):
    z = np.load(os.path.join(facedir, "clip.npz"))
    return {str(f): v for f, v in zip(z["files"], z["vecs"])}


def main():
    bp = os.path.join(FACES, "boxes.json")
    if not os.path.exists(bp):
        raise SystemExit("boxes.json 이 없다. 먼저 tools/focus_stack.py --boxes")
    with open(bp, encoding="utf-8") as f:
        boxes = json.load(f)
    whole = "--whole" in sys.argv
    use_clip = "--clip" in sys.argv
    if use_clip:
        cp = os.path.join(FACES, "clip.npz")
        if not os.path.exists(cp):
            raise SystemExit("clip.npz 가 없다. 먼저 도커에서 embed_faces.py")
        VEC = load_clip(FACES)
        globals()["diff"] = cos

    cells, half, thin = {}, {}, []
    for rs, _ in ROLES:
        for ts, _ in TIERS:
            names = [fn for fn in sorted(boxes.items()) if False]  # 자리지기
            if use_clip:
                # CLIP 은 얼굴 검출과 무관하다. 검출 실패한 장도 그대로 쓴다.
                got = [VEC[fn] for fn in sorted(VEC)
                       if fn.startswith(f"{rs}_{ts}_v")]
            else:
                got = [crop(os.path.join(FACES, fn), b, whole)
                       for fn, b in sorted(boxes.items())
                       if fn.startswith(f"{rs}_{ts}_v") and b["found"]]
            if len(got) < 2:
                continue
            cells[(rs, ts)] = np.mean(got, axis=0)
            # 짝수번째 / 홀수번째로 가른다. 고르는 데 임의가 안 들어가게.
            half[(rs, ts)] = (np.mean(got[0::2], axis=0), np.mean(got[1::2], axis=0))
            if len(got) < 4:
                thin.append(f"{rs}_{ts}({len(got)}장)")
    where = ("CLIP 이미지 임베딩 (코사인 거리)" if use_clip else
             "화폭 전체 (머리쓰개·옷 포함)" if whole else f"상자 안만 (너비의 {CROP}배)")
    print(f"얼굴 차이 — {len(cells)}칸. 6장을 셋씩 두 묶음으로 갈라, "
          f"세 값을 모두 3장 평균으로 잰다 · {where}\n")

    floor = [diff(a, b) for a, b in half.values()]
    A = {k: v[0] for k, v in half.items()}

    per_tier, role_all = [], []
    for ts, tk in TIERS:
        v = [diff(A[(a, ts)], A[(b, ts)])
             for a, b in itertools.combinations([r for r, _ in ROLES], 2)
             if (a, ts) in A and (b, ts) in A]
        if v:
            per_tier.append((tk, sum(v)/len(v), max(v)))
            role_all += v
    tier_all = []
    for rs, _ in ROLES:
        tier_all += [diff(A[(rs, a)], A[(rs, b)])
                     for a, b in itertools.combinations([t for t, _ in TIERS], 2)
                     if (rs, a) in A and (rs, b) in A]

    fl = sum(floor)/len(floor)
    print("0. 잡음 바닥  (같은 칸을 반씩 갈라 견준다 — 역할도 계층도 안 다르다)")
    print(f"   {'전체':<5}{'':<2}평균 {fl:5.3f}   최소 {min(floor):5.3f}   최대 {max(floor):5.3f}\n")

    print("1. 같은 계층 · 다른 역할  (얼굴이 역할을 나르는가)")
    for tk, m, mx in per_tier:
        print(f"   {tk:<5}{'':<2}평균 {m:5.3f}   최대 {mx:5.3f}")
    print(f"   {'전체':<5}{'':<2}평균 {sum(role_all)/len(role_all):5.3f}   "
          f"최소 {min(role_all):5.3f}   최대 {max(role_all):5.3f}\n")
    print("2. 같은 역할 · 다른 계층  (얼굴이 계층을 나르는가)")
    print(f"   {'전체':<5}{'':<2}평균 {sum(tier_all)/len(tier_all):5.3f}   "
          f"최소 {min(tier_all):5.3f}   최대 {max(tier_all):5.3f}\n")

    r = sum(role_all)/len(role_all); t = sum(tier_all)/len(tier_all)
    print("3. 판정")
    print(f"   잡음 {fl:.3f}   역할 {r:.3f} ({r/fl:.2f}배)   계층 {t:.3f} ({t/fl:.2f}배)")
    if r <= fl * 1.05:
        print("   → 역할은 잡음 바닥에 붙어 있다. 얼굴도 역할을 안 나른다.")
    elif t > r * 1.2:
        print(f"   → 역할이 바닥 위로 올라오긴 했지만 계층이 {t/r:.2f}배 더 갈린다.")
    else:
        print(f"   → 역할이 바닥 위로 올라왔고, 계층과 {t/r:.2f}배 차이다. "
              "실루엣({4.1}배)보다 훨씬 좁다.".replace("{4.1}", "4.1"))
    print("   ※ 단위는 % 가 아니라 " + ("코사인 거리다." if use_clip else "표준편차다.") +
          " 실루엣의 % 와 직접 견주면 안 된다.")
    print("     견줄 것은 이 표 안의 세 값뿐이다.")

    # 4. 플레이어는 평균을 안 본다. 한 장을 본다.
    #    평균끼리 견주면 개인차가 지워지므로 계통이 실제보다 세게 보인다.
    #    카드 한 장에서 역할이 읽히는가는 장 대 장으로 물어야 한다.
    if use_clip:
        raw = {}
        for rs, _ in ROLES:
            for ts, _ in TIERS:
                v = [VEC[fn] for fn in sorted(VEC) if fn.startswith(f"{rs}_{ts}_v")]
                if v:
                    raw[(rs, ts)] = v
        same = [cos(a, b) for v in raw.values() for a, b in itertools.combinations(v, 2)]
        rl = [cos(a, b) for ts, _ in TIERS
              for r1, r2 in itertools.combinations([r for r, _ in ROLES], 2)
              if (r1, ts) in raw and (r2, ts) in raw
              for a in raw[(r1, ts)] for b in raw[(r2, ts)]]
        tr = [cos(a, b) for rs, _ in ROLES
              for t1, t2 in itertools.combinations([t for t, _ in TIERS], 2)
              if (rs, t1) in raw and (rs, t2) in raw
              for a in raw[(rs, t1)] for b in raw[(rs, t2)]]
        m = lambda a: sum(a) / len(a)
        print("\n4. 한 장 대 한 장  (플레이어는 평균이 아니라 카드 한 장을 본다)")
        print(f"   같은 칸 두 장        {m(same):.3f}   ({len(same)}쌍)")
        print(f"   같은 계층 · 다른 역할  {m(rl):.3f}   같은 칸의 {m(rl)/m(same):.2f}배   ({len(rl)}쌍)")
        print(f"   같은 역할 · 다른 계층  {m(tr):.3f}   같은 칸의 {m(tr)/m(same):.2f}배   ({len(tr)}쌍)")
        print(f"   → 역할이 다른 두 장은 같은 역할 두 장보다 {m(rl)/m(same)-1:.0%} 밖에 안 다르다.")
        print(f"     계층은 {m(tr)/m(same)-1:.0%} 다르다.")
    if thin:
        print(f"   ⚠ 검출이 모자란 칸: {', '.join(thin)}")

    if "--sheet" in sys.argv and not use_clip:
        sheet = Image.new("L", (11 * N, 5 * N))
        for i, (rs, _) in enumerate(ROLES):
            for j, (ts, _) in enumerate(TIERS):
                if (rs, ts) not in cells:
                    continue
                v = cells[(rs, ts)]
                v = np.clip(v * 48 + 128, 0, 255).astype(np.uint8)
                sheet.paste(Image.fromarray(v), (j * N, i * N))
        out = os.path.join(ROOT, "art/face_mean.png")
        sheet.save(out)
        print(f"\n평균 얼굴 55칸 → {os.path.relpath(out, ROOT)}  "
              "(가로 계층 11 · 세로 역할 5, 개인은 지워지고 계통만 남는다)")


if __name__ == "__main__":
    main()
