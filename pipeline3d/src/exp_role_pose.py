# -*- coding: utf-8 -*-
"""실험 — 구도를 풀면 역할이 얼굴에 실리는가.

**묻는 것.** `tools/face_diff.py --clip` 이 잰 바 역할은 잡음 바닥의
1.32배밖에 안 된다 (계층은 3.07배). `docs/22-아트.md` 가 남겨 둔 세 안 중
「자세를 크게」를 실제로 재 본다.

**가설.** 역할이 안 실리는 것은 역할 말이 약해서가 아니라 **구도가 자세를
지워서**다. 지금 STYLE 은 "head and shoulders ... facing viewer" 다.
가슴 위만 담고 정면을 강제한다. 그런데 역할은 수호/저항/헌신/탐구/도피 —
전부 **몸이 어디를 향하느냐**다. 담을 자리가 없으면 안 실린다.

**손대는 것은 둘뿐이다.**
  1. 구도  "head and shoulders ... facing viewer" → "upper body portrait"
     (정면 강제를 뺀다. 그 외 STYLE 문구는 한 글자도 안 건드린다)
  2. 역할 말  시선·턱 → 어깨·몸통이 향하는 쪽

**같게 두는 것.**
  · 씨앗 — id 의 crc32 로 정하므로 기준 팔의 같은 이름·같은 번호와 **같은 씨앗**이다.
    바뀐 것이 말뿐이라는 뜻이다.
  · 계층 말 (TIER_FACE 그대로), NEGATIVE, 스텝 30, guidance 6.0, 1024, 6장.
  · 계층은 셋만 쓴다 (농어민·관리·상인). 재는 데 드는 GPU 를 줄이려는 것이고,
    기준 팔도 **같은 셋으로 잘라서** 견준다 (face_diff --tiers).

⚠ NEGATIVE 는 손대지 않았다. 거기 "hands" 가 들어 있어서 팔이 덜 나온다.
   이 실험이 안 되더라도 「자세를 크게」가 통째로 부정되는 것은 아니다.
   부정되는 것은 **NEGATIVE 를 그대로 둔 채 구도만 푸는 것**이다.

  IREM_GPU=0 ./pipeline3d/run.sh shell irem-imagegen:latest \
      python /work/src/exp_role_pose.py
"""
import argparse, json, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import faces as F

SDXL = "stabilityai/stable-diffusion-xl-base-1.0"

# 기준 STYLE 에서 "head and shoulders" 와 "facing viewer" 만 뺀다.
POSE_STYLE = (
    "upper body portrait of one person, "
    "painterly oil painting, muted desaturated colours, "
    "single soft light from one side, plain dark background, "
    "medieval, weathered skin, solemn, mouth closed"
)

# 얼굴이 아니라 몸통이 향하는 쪽으로 다시 쓴다.
POSE_ROLE = {
    "guard":  ("수호", "squared shoulders planted facing forward, chin level, chest out"),
    "resist": ("저항", "leaning in, one shoulder driven forward, head lowered, jaw clenched"),
    "devote": ("헌신", "shoulders bowed and rounded, head bent down, arms drawn in"),
    "seek":   ("탐구", "turned three quarters away, head craned forward, peering closely"),
    "flee":   ("도피", "body turned aside mid stride, head snapped back over the shoulder"),
}

# --- 팔 3 「몸을 보인다」 ------------------------------------------------
# 팔 2 는 문턱을 못 넘었다 (한 장 대 한 장 1.16배, 문턱 1.25). 실루엣도
# 얼굴도 같은 자리에서 막혔다 — 실루엣은 옷이 몸을 덮고, 초상은 화폭이 몸을
# 자른다. **몸이 한 번도 안 보인다.** 그러면 남은 물음은 하나다.
#
#   몸이 다 보이면 역할이 읽히는가?
#
# 읽히면 역할은 몸에 있는 것이고 (→ docs/22 의 「옷을 짧게」가 맞는 방향),
# 안 읽히면 역할 말 자체가 약한 것이다 (→ 「역할을 실루엣에서 뺀다」).
FIGURE_STYLE = (
    "full figure standing, whole body visible from head to feet, "
    "painterly oil painting, muted desaturated colours, "
    "single soft light from one side, plain dark background, "
    "medieval, weathered skin, solemn, mouth closed"
)
# 팔 이 NEGATIVE 에서 "hands" 를 뺀다. 팔이 안 나오면 자세를 볼 수가 없다.
# 팔 2 에서는 일부러 안 건드렸다 — 거기서는 그것이 교란이었고, 여기서는
# 그것을 빼는 것이 실험 자체다.
FIGURE_NEGATIVE = ", ".join(
    t for t in (x.strip() for x in
                "photograph, photorealistic, 3d render, cgi, anime, smiling, teeth, "
                "modern clothing, glasses, jewelry, text, watermark, signature, frame, "
                "two people, crowd, hands, cropped head, blurry, low quality, deformed".split(","))
    if t != "hands")

TIERS = ["peasant", "clerk", "merchant"]   # 기본은 셋. --tiers all 이면 11종 전부


def rows(tiers, arm="pose"):
    out = []
    for rs, (rk, rd) in (ACTION_ROLE if arm == "action" else POSE_ROLE).items():
        for ts in tiers:
            tk, td = F.TIER_FACE[ts]
            out.append({"id": f"{rs}_{ts}", "ko": f"{rk}·{tk}",
                        "en": f"{td}, {rd}"})
    return out


# 팔 3 은 화폭과 hands 를 한꺼번에 바꿨다. 통했으니 이제 갈라야 한다.
# figurenh = 전신 화폭 + hands 를 도로 넣은 것. 팔 3 과 딱 한 칸 다르다.
# 팔 3 은 말로만 "전신"이라 했지 90장 중 35장만 전신으로 나왔다. 그것도 고르게
# 안 나왔다 — 헌신과 도피는 18칸 전부 전신인데 수호·저항·탐구는 대부분 흉상으로
# 돌아갔다. **약을 안 준 팔을 놓고 약이 들었다고 말할 수는 없다.** 그래서
# 화폭을 NEGATIVE 로 막는다. 이게 팔 5 다.
FRAME_NEGATIVE = FIGURE_NEGATIVE + (
    ", bust, head and shoulders portrait, close up, cropped at the chest, "
    "cropped at the waist, seated, sitting")

# --- 팔 6 「행동으로 적는다」 --------------------------------------------
# 세 판 다 도피 하나를 빼면 1.20~1.25 로 주저앉았다. 그리고 도피는 세 판 모두
# 18칸 전부 전신으로 나온 **유일한** 역할이다. 헌신이 그 다음이다.
# 둘의 공통점은 역할 말이 몸 전체가 하는 짓을 적었다는 것이다 — 내닫는다,
# 웅크린다. 수호·저항·탐구는 눈·턱·어깨 이야기라 흉상이 나온다.
#
#   화폭을 여는 것은 문체 말이 아니라 **역할 말 자체**일지 모른다.
#
# 그러면 다섯을 전부 몸이 하는 짓으로 고쳐 쓰면 된다. 그게 이 팔이다.
ACTION_ROLE = {
    "guard":  ("수호", "standing firm with both arms spread wide barring the way"),
    "resist": ("저항", "straining forward shoving against something with both arms"),
    "devote": ("헌신", "kneeling on both knees head bowed hands clasped together"),
    "seek":   ("탐구", "crouching low reaching out to touch the ground"),
    "flee":   ("도피", "running away mid stride looking back over the shoulder"),
}

STYLES = {"pose": POSE_STYLE, "figure": FIGURE_STYLE,
          "figurenh": FIGURE_STYLE, "figure2": FIGURE_STYLE,
          "action": FIGURE_STYLE}
NEGATIVES = {"pose": None, "figure": FIGURE_NEGATIVE,
             "figurenh": None, "figure2": FRAME_NEGATIVE,
             "action": FIGURE_NEGATIVE}


def prompt_of(r, arm="pose"):
    return r["en"] + ". " + STYLES[arm]


def negative_of(arm):
    return NEGATIVES[arm] or F.NEGATIVE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="pose", choices=["pose", "figure", "figurenh", "figure2", "action"],
                    help="pose=구도만 · figure=전신+손 · figurenh=전신만 · figure2=화폭을 막은 전신")
    ap.add_argument("--out", default=None)
    ap.add_argument("--model", default=SDXL)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=6.0)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--variants", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20260909)
    ap.add_argument("--tiers", default=",".join(TIERS),
                    help="계층 목록. all 이면 11종 전부")
    ap.add_argument("--check-only", action="store_true")
    a = ap.parse_args()
    if a.out is None:
        a.out = "/work/out/faces_" + a.arm

    tiers = list(F.TIER_FACE) if a.tiers == "all" else \
        [t.strip() for t in a.tiers.split(",")]
    bad = [t for t in tiers if t not in F.TIER_FACE]
    if bad:
        raise SystemExit("모르는 계층: " + ", ".join(bad))
    rs_ = rows(tiers, a.arm)
    os.makedirs(a.out, exist_ok=True)

    # 77토큰 검사 — 기준 팔과 같은 이유로 그림 전에 세운다.
    from transformers import CLIPTokenizer
    tk = CLIPTokenizer.from_pretrained(a.model, subfolder="tokenizer")
    over = [f"{r['id']} {len(tk(prompt_of(r, a.arm)).input_ids)}토큰"
            for r in rs_ if len(tk(prompt_of(r, a.arm)).input_ids) > 77]
    # 막는 말도 CLIP 이 말없이 자른다. figure2 에서 NEGATIVE 를 길게 붙였으니
    # 여기도 재야 한다. 안 재면 화폭을 막으라고 적어 두고 안 막힌 채로 90장이 나온다.
    kneg = len(tk(negative_of(a.arm)).input_ids)
    if kneg > 77:
        over.append(f"(막는 말) {kneg}토큰 — 넘침 {kneg - 77}")
    if over:
        raise SystemExit("말이 77토큰을 넘는다:\n  " + "\n  ".join(over))
    longest = max(len(tk(prompt_of(r, a.arm)).input_ids) for r in rs_)
    print(f"[exp_{a.arm}] 말 길이 검사 통과 — {len(rs_)}종, 최장 {longest}/77토큰", flush=True)
    if a.check_only:
        for r in rs_:
            print(f"  {r['id']:<18} {prompt_of(r, a.arm)}")
        return

    import torch
    from diffusers import StableDiffusionXLPipeline

    total = len(rs_) * a.variants
    print(f"[exp_{a.arm}] {len(rs_)}종 × {a.variants}장 = {total}장 → {a.out}", flush=True)
    pipe = StableDiffusionXLPipeline.from_pretrained(
        a.model, torch_dtype=torch.float16, variant="fp16", use_safetensors=True)
    pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)

    # gen_faces.py 와 **같은 식**이다. 같은 이름·같은 번호면 같은 씨앗이다.
    def seed_of(rid, v):
        return a.seed + (zlib.crc32(rid.encode()) % 1_000_000) * 100 + v

    made = 0
    for r in rs_:
        for v in range(a.variants):
            path = os.path.join(a.out, f"{r['id']}_v{v}.png")
            if os.path.exists(path):
                continue
            g = torch.Generator("cuda").manual_seed(seed_of(r["id"], v))
            img = pipe(prompt=prompt_of(r, a.arm), negative_prompt=negative_of(a.arm),
                       height=a.size, width=a.size,
                       num_inference_steps=a.steps, guidance_scale=a.guidance,
                       generator=g).images[0]
            img.save(path)
            made += 1
            print(f"  {r['id']}_v{v}.png  ({made}/{total})", flush=True)

    with open(os.path.join(a.out, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"arm": a.arm,
                   "style": prompt_of({"en": ""}, a.arm).lstrip(". "),
                   "negative": negative_of(a.arm),
                   "base_style": F.STYLE, "base_negative": F.NEGATIVE, "tiers": tiers,
                   "rows": [{**r, "prompt": prompt_of(r, a.arm)} for r in rs_]},
                  f, ensure_ascii=False, indent=2)
    print(f"[exp_{a.arm}] 끝 — 이번에 {made}장", flush=True)


if __name__ == "__main__":
    main()
