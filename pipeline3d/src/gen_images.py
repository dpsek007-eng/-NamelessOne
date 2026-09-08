# -*- coding: utf-8 -*-
"""1단계 — 소품 47종의 컨셉 이미지. irem-imagegen 컨테이너 안에서 돈다.

기본 모델은 **SDXL base 1.0** 이다. FLUX.1-schnell 로 가려다 물렸다.
schnell 은 가중치가 Apache-2.0 인데도 저장소가 게이트라서 토큰 없이는
받아지지 않는다 (401 GatedRepoError). 토큰이 있으면 그대로 쓸 수 있게
--model 로 열어 두었다. run.sh 가 HF_TOKEN 을 넘겨 준다.

sdxl-turbo 는 게이트가 아니지만 비상용 연구 라이선스라 뺐다.
SDXL base 1.0 은 OpenRAIL++-M 이고 상업 이용을 허용한다.

TripoSR 은 이미지 한 장에서 뒷면까지 지어내는 물건이라, 입력이 나쁘면
결과가 나쁜 정도가 아니라 형태가 무너진다. 그래서 조건을 세 가지 건다.
  · 물건 하나만
  · 배경은 평평한 회색 (rembg 가 잘라내기 좋다)
  · 잘리지 않고 화면 안에 다 들어온다
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import props as P

SDXL = "stabilityai/stable-diffusion-xl-base-1.0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/work/out/images")
    ap.add_argument("--model", default=SDXL)
    ap.add_argument("--steps", type=int, default=None,
                    help="안 주면 모델에 맞춰 고른다 (SDXL 30, schnell 4)")
    ap.add_argument("--guidance", type=float, default=None)
    ap.add_argument("--size", type=int, default=1024)
    ap.add_argument("--variants", type=int, default=3,
                    help="소품마다 몇 장 뽑을지. 골라 쓰려고 여러 장 뽑는다")
    ap.add_argument("--seed", type=int, default=20260908)
    ap.add_argument("--only", default=None, help="쉼표로 구분한 id 앞자리 (예: 02,32,38)")
    args = ap.parse_args()

    import torch

    is_flux = "flux" in args.model.lower()
    steps = args.steps if args.steps is not None else (4 if is_flux else 30)
    # schnell 은 증류 모델이라 guidance 를 쓰지 않는다. 0 이 아니면 망가진다.
    guidance = args.guidance if args.guidance is not None else (0.0 if is_flux else 6.5)

    everything = P.load()
    rows = everything
    if args.only:
        keep = {s.strip() for s in args.only.split(",")}
        rows = [r for r in rows if f"{r['i']:02d}" in keep or r["id"] in keep]

    os.makedirs(args.out, exist_ok=True)
    print(f"[gen_images] {args.model}  {steps}스텝 g={guidance}", flush=True)
    print(f"[gen_images] {len(rows)}종 × {args.variants}장 → {args.out}", flush=True)

    if is_flux:
        from diffusers import FluxPipeline
        pipe = FluxPipeline.from_pretrained(args.model, torch_dtype=torch.bfloat16)
        extra = {}
    else:
        from diffusers import StableDiffusionXLPipeline
        pipe = StableDiffusionXLPipeline.from_pretrained(
            args.model, torch_dtype=torch.float16, variant="fp16", use_safetensors=True
        )
        # SDXL 은 negative prompt 를 받는다. FLUX 는 안 받는다.
        extra = {}
    pipe.to("cuda")
    pipe.set_progress_bar_config(disable=True)

    # --- 77토큰 검사 -------------------------------------------------------
    # SDXL 의 CLIP 은 77토큰에서 말없이 자른다. 경고 한 줄이 로그에 흘러가고
    # 끝이라, 뒤쪽 지시가 통째로 사라진 채 141장이 나온 뒤에야 알게 된다.
    # 한 번 그렇게 날렸다. 이제는 그림을 뽑기 전에 47종을 전부 재고,
    # 하나라도 넘치면 여기서 세운다.
    if not is_flux:
        tk = pipe.tokenizer
        over = []
        for r in everything:
            pos = f"{r['en']}. {P.STYLE}"
            neg = P.NEGATIVE + (", " + r["neg"] if r.get("neg") else "")
            for lbl, text in (("prompt", pos), ("negative", neg)):
                k = len(tk(text).input_ids)
                if k > 77:
                    over.append(f"{r['id']} {lbl} {k}토큰 (넘침 {k - 77})")
        if over:
            raise SystemExit(
                "말이 77토큰을 넘는다. 잘린 채로 뽑으면 뒤쪽 지시가 사라진다:\n  "
                + "\n  ".join(over)
            )
        print("[gen_images] 47종 말 길이 검사 통과", flush=True)
    # -----------------------------------------------------------------------

    for r in rows:
        prompt = f"{r['en']}. {P.STYLE}"
        if not is_flux:
            # FLUX 는 negative prompt 를 받지 않는다. SDXL 만 건다.
            neg = P.NEGATIVE + (", " + r["neg"] if r.get("neg") else "")
            extra["negative_prompt"] = neg
        for v in range(args.variants):
            path = os.path.join(args.out, f"{r['id']}_v{v}.png")
            if os.path.exists(path):
                print(f"  건너뜀 {os.path.basename(path)}", flush=True)
            else:
                g = torch.Generator("cuda").manual_seed(args.seed + r["i"] * 100 + v)
                img = pipe(
                    prompt=prompt,
                    height=args.size, width=args.size,
                    num_inference_steps=steps,
                    guidance_scale=guidance,
                    generator=g,
                    **extra,
                ).images[0]
                img.save(path)
                print(f"  {os.path.basename(path)}", flush=True)

    # 표는 --only 로 걸러낸 것이 아니라 **실제로 있는 파일 전부**로 다시 쓴다.
    # 걸러낸 것만 적으면 몇 개를 다시 돌릴 때마다 표에서 나머지가 사라지고,
    # 다음 단계가 그만큼을 못 본다.
    index = []
    for r in everything:
        for v in range(args.variants):
            f = f"{r['id']}_v{v}.png"
            if os.path.exists(os.path.join(args.out, f)):
                index.append({**r, "variant": v, "image": f})
    with open(os.path.join(args.out, "index.json"), "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"[gen_images] 끝 — 이번에 {len(rows)}종, 표에 {len(index)}장", flush=True)


if __name__ == "__main__":
    main()
