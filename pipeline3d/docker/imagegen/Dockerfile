# 컨셉 이미지 — FLUX.1-schnell (Apache-2.0, 상용 가능)
# dev 판이 아니라 schnell 판인 이유는 dev 가 비상용 라이선스이기 때문이다.
# 4스텝이면 나오고, bf16 으로 5090 한 장에 올라간다.
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TORCH_CUDA_ARCH_LIST="12.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3.10-dev python3-pip git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    python -m pip install --no-cache-dir -U pip setuptools wheel

RUN pip install --no-cache-dir \
        torch==2.7.1 torchvision==0.22.1 \
        --index-url https://download.pytorch.org/whl/cu128

RUN pip install --no-cache-dir \
        "diffusers>=0.32" \
        "transformers>=4.46,<5" \
        accelerate safetensors sentencepiece protobuf \
        "huggingface-hub>=0.26,<0.30" \
        "numpy<2" "Pillow>=10.1,<11"

WORKDIR /work
CMD ["/bin/bash"]
