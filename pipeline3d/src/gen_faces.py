# -*- coding: utf-8 -*-
"""초상 — 얼굴을 뽑는다. irem-imagegen 컨테이너 안에서 돈다.

gen_images.py 와 같은 모델(SDXL base 1.0)·같은 규칙이다. 다른 것은 둘.

  · 소품은 TripoSR 에 넣을 입력이라 「물건 하나·회색 배경·안 잘림」이 조건이었다.
    초상은 3D 로 안 간다. docs/22 「초점」이 정한 대로 초상 UI 에만 붙는다.
    그래서 조건이 「정면·가슴 위·구도 고정」이다. 구도가 장마다 같아야
    나중에 이목구비 자리에 흐림을 걸 수 있다.

  · 뽑는 수가 다르다. 이름 있는 23명은 골라 쓸 것이 많아야 해서 더 뽑고,
    역할x계층 55종은 게임에 실제로 들어가는 바탕이라 고르게 뽑는다.

GPU 를 오늘만 쓸 수 있어서 넉넉히 뽑는다. 고르는 일은 GPU 없이도 된다.
"""
import argparse, json, os, sys, zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import faces as F

SDXL = "stabilityai/stable-diffusion-xl-base-1.0"
CHARS = "/repo/data/characters.json"


def load_rows(chars_path):
    with open(chars_path, encoding="utf-8") as f:
        chars = json.load(f)["characters"]
    named = F.named_rows(chars)
    missing = {c["id"] for c in chars} - {r["id"] for r in named}
    if missing:
        # 사람이 늘었는데 얼굴 말을 안 쓴 것이다. 조용히 빠지면 안 된다.
        raise SystemExit("faces.NAMED 에 없는 사람: " + ", ".join(sorted(missing)))
    return named, F.part_rows()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/work/out/faces")
    ap.add_argument("--chars", default=CHARS)
    ap.add_argument("--model", default=SDXL)
    ap.add_argument("--steps", type=int, default=30)
    ap.add_argument("--guidance", type=float, default=6.0)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--named-variants", type=int, default=8)
    ap.add_argument("--part-variants", type=int, default=6)
    ap.add_argument("--seed", type=int, default=20260909)
    ap.add_argument("--only", default=None, help="쉼표로 구분한 id (예: seren,guard_royal)")
    ap.add_argument("--kind", default=None, choices=["named", "part", "head", "face"])
    ap.add_argument("--check-only", action="store_true", help="말 길이만 재고 끝낸다")
    args = ap.parse_args()

    named, parts = load_rows(args.chars)
    everything = named + parts + F.head_rows() + F.face_rows()
    nvar = {"named": args.named_variants, "part": args.part_variants,
            "head": args.named_variants, "face": args.named_variants}

    rows = everything
    if args.kind:
        rows = [r for r in rows if r["kind"] == args.kind]
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        rows = [r for r in rows if r["id"] in keep]
    if not rows:
        raise SystemExit("뽑을 것이 없다. --only / --kind 를 보라")

    os.makedirs(args.out, exist_ok=True)

    # --- 77토큰 검사 (그림을 한 장도 뽑기 전에) ----------------------------
    # gen_images.py 주석에 남긴 그 사고다. CLIP 은 77토큰에서 말없이 자르고,
    # 잘린 자리는 STYLE 뒷부분 — 「정면·한쪽 광원·평평한 배경」이다.
    # 그게 사라지면 구도가 장마다 달라지고, 구도가 다르면 초점 레이어를
    # 못 만든다. 그림 값보다 여기서 세우는 값이 싸다.
    from transformers import CLIPTokenizer
    tk = CLIPTokenizer.from_pretrained(args.model, subfolder="tokenizer")
    over = []
    for r in everything:
        for lbl, text in (("prompt", F.prompt_of(r)), ("negative", F.NEGATIVE)):
            k = len(tk(text).input_ids)
            if k > 77:
                over.append(f"{r['id']} {lbl} {k}토큰 (넘침 {k - 77})")
    if over:
        raise SystemExit(
            "말이 77토큰을 넘는다. 잘린 채로 뽑으면 구도 지시가 사라진다:\n  "
            + "\n  ".join(over)
        )
    longest = max(len(tk(F.prompt_of(r)).input_ids) for r in everything)
    print(f"[gen_faces] 말 길이 검사 통과 — {len(everything)}종, 최장 {longest}/77토큰", flush=True)
    if args.check_only:
        return

    import torch
    from diffusers import StableDiffusionXLPipeline

    total = sum(nvar[r["kind"]] for r in rows)
    print(f"[gen_faces] {args.model}  {args.steps}스텝 g={args.guidance}", flush=True)
    print(f"[gen_faces] {len(rows)}종 → {total}장 → {args.out}", flush=True)

    pipe = StableDiffusionXLPipeline.from_pretrained(
        args.model, torch_dtype=torch.float16, variant="fp16", use_safetensors=True
    )
    pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)

    # 씨앗은 id 로 정한다. 순서가 바뀌어도 같은 사람은 같은 얼굴이 나온다.
    # gen_images.py 는 r["i"] (순번) 을 썼는데, 초상은 사람이 늘고 줄기 때문에
    # 순번을 쓰면 한 명 추가할 때마다 뒤쪽 얼굴이 전부 갈린다.
    def seed_of(r, v):
        # 파이썬 hash() 는 문자열에 대해 프로세스마다 값이 달라진다.
        # 씨앗에 쓰면 다시 돌릴 때 같은 사람이 다른 얼굴로 나온다. crc32 를 쓴다.
        return args.seed + (zlib.crc32(r["id"].encode()) % 1_000_000) * 100 + v

    made = 0
    for r in rows:
        prompt = F.prompt_of(r)
        for v in range(nvar[r["kind"]]):
            path = os.path.join(args.out, f"{r['id']}_v{v}.png")
            if os.path.exists(path):
                continue
            g = torch.Generator("cuda").manual_seed(seed_of(r, v))
            img = pipe(
                prompt=prompt,
                negative_prompt=F.NEGATIVE,
                height=args.size, width=args.size,
                num_inference_steps=args.steps,
                guidance_scale=args.guidance,
                generator=g,
            ).images[0]
            img.save(path)
            made += 1
            print(f"  {r['id']}_v{v}.png  ({made}/{total})", flush=True)

    # 표는 --only 로 거른 것이 아니라 디스크에 실제로 있는 파일로 다시 쓴다.
    index = []
    for r in everything:
        got = [f"{r['id']}_v{v}.png" for v in range(nvar[r["kind"]])
               if os.path.exists(os.path.join(args.out, f"{r['id']}_v{v}.png"))]
        if got:
            index.append({**r, "prompt": F.prompt_of(r), "images": got})
    with open(os.path.join(args.out, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"style": F.STYLE, "negative": F.NEGATIVE, "rows": index},
                  f, ensure_ascii=False, indent=2)
    n = sum(len(r["images"]) for r in index)
    print(f"[gen_faces] 끝 — 이번에 {made}장, 표에 {len(index)}종 {n}장", flush=True)


if __name__ == "__main__":
    main()
