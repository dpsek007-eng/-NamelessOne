# TripoSR (MIT) — 이미지 한 장 → 메시
#
# 윗물의 Dockerfile 을 그대로 쓰지 않는 이유는 두 가지다.
#   1) RTX 5090 은 Blackwell(sm_120) 이라 cu124/torch 2.5 로는 커널이 없다.
#      "no kernel image is available for execution on the device" 로 죽는다.
#   2) TripoSR 이 못박아 둔 transformers 4.35 는 요즘 huggingface_hub 와 깨진다.
#      쓰는 API 가 ViTModel 하나뿐이라 올려도 안전하다.
FROM nvidia/cuda:12.8.0-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CUDA_HOME=/usr/local/cuda \
    # sm_120 하나만 굽는다. 이 서버 말고 다른 데서 돌릴 일이 없다.
    TORCH_CUDA_ARCH_LIST="12.0" \
    # moderngl 이 텍스처를 구울 때 화면 없이 EGL 로 붙는다
    NVIDIA_DRIVER_CAPABILITIES=all \
    PYOPENGL_PLATFORM=egl

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3.10-dev python3-pip \
        git build-essential cmake ninja-build \
        libgl1 libglib2.0-0 libegl1 libglvnd0 libglx0 libgles2 \
        libxrender1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3.10 /usr/bin/python && \
    python -m pip install --no-cache-dir -U pip setuptools wheel

# torch 를 먼저 넣는다. torchmcubes 가 빌드할 때 torch 를 import 한다.
RUN pip install --no-cache-dir \
        torch==2.7.1 torchvision==0.22.1 \
        --index-url https://download.pytorch.org/whl/cu128

RUN pip install --no-cache-dir \
        omegaconf==2.3.0 \
        "Pillow>=10.1,<11" \
        einops==0.7.0 \
        "transformers==4.46.3" \
        "huggingface-hub>=0.26,<0.30" \
        "trimesh>=4.0.5" \
        "numpy<2" \
        rembg onnxruntime \
        "imageio[ffmpeg]" \
        xatlas==0.0.9 \
        moderngl==5.10.0 \
        pygltflib

# CUDA 마칭큐브. sm_120 으로 굽는다.
RUN pip install --no-cache-dir "git+https://github.com/tatsy/torchmcubes.git"

WORKDIR /work
CMD ["/bin/bash"]
