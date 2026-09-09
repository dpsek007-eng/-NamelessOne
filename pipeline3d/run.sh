#!/usr/bin/env bash
# 도커 실행 인자를 한군데 모아 둔다.
#
# 여기 박아 두는 이유는 --gpus 하나 때문이다.
#   docker run --gpus '"device=0"'   → compute/utility 만 올라온다.
#                                      /usr/share/glvnd/egl_vendor.d 에
#                                      10_nvidia.json 이 없어서 EGL 이
#                                      llvmpipe(소프트웨어)로 떨어진다.
#   docker run --runtime=nvidia ...  → graphics 까지 올라온다. 5090 이 잡힌다.
# 텍스처 굽기가 OpenGL 을 쓰므로 이 차이가 그대로 속도로 온다.
#
# 쓰는 법:
#   ./run.sh images   [추가 인자]     소품 47종 컨셉 이미지
#   ./run.sh faces    [추가 인자]     초상 78종 (전승 23 + 역할x계층 55)
#   ./run.sh mesh     [추가 인자]     이미지 → OBJ + texture.png
#   ./run.sh blender  [추가 인자]     정리 · 실축 · 원점 · GLB/FBX
#   ./run.sh shell <이미지>           들어가서 만져 볼 때
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HERE/out" "$HERE/cache/hf" "$HERE/cache/xdg" "$HERE/cache/u2net"

# 컨테이너가 root 로 쓰면 밖에서 지우지도 못하는 파일이 남는다.
DOCKER_ARGS=(
  --rm
  --runtime=nvidia
  -e "NVIDIA_VISIBLE_DEVICES=${IREM_GPU:-0}"   # GPU 를 나눠 쓸 때: IREM_GPU=1 ./run.sh ...
  -e NVIDIA_DRIVER_CAPABILITIES=all
  -u "$(id -u):$(id -g)"
  -e HOME=/tmp
  -e HF_HOME=/work/cache/hf
  -e XDG_CACHE_HOME=/work/cache/xdg
  -e U2NET_HOME=/work/cache/u2net
  -e PYTHONDONTWRITEBYTECODE=1
  -e "HF_TOKEN=${HF_TOKEN:-}"
  -v "$HERE:/work"
  -v "$(cd "$HERE/.." && pwd)/tools:/repo/tools:ro"
  -v "$(cd "$HERE/.." && pwd)/data:/repo/data:ro"
  -e IREM_TOOLS=/repo/tools
  -w /work
)

cmd="${1:-}"; shift || true
case "$cmd" in
  images)
    exec docker run "${DOCKER_ARGS[@]}" irem-imagegen:latest \
         python /work/src/gen_images.py "$@"
    ;;
  faces)
    exec docker run "${DOCKER_ARGS[@]}" irem-imagegen:latest \
         python /work/src/gen_faces.py "$@"
    ;;
  mesh)
    exec docker run "${DOCKER_ARGS[@]}" irem-triposr:latest \
         python /work/src/gen_mesh.py "$@"
    ;;
  blender)
    # 블렌더는 도커에 넣지 않았다. snap 으로 깔린 5.2.1 이 /media/hdd8 을
    # 그대로 읽고 쓴다. 확인했다.
    exec blender --background --python "$HERE/src/blender_post.py" -- \
         --mesh "$HERE/out/mesh" --out "$HERE/out/props" "$@"
    ;;
  shell)
    img="${1:?쓸 이미지를 대라 (irem-triposr:latest / irem-imagegen:latest)}"; shift
    exec docker run -i "${DOCKER_ARGS[@]}" "$img" "${@:-bash}"
    ;;
  *)
    sed -n '1,20p' "$0" >&2
    exit 2
    ;;
esac
