#!/usr/bin/env bash
# 구운 몸과 옷을 유니티로 옮긴다.
#
# chars/out 은 .gitignore 에 들어 있다 — 소스에서 다시 나오는 것이므로.
# 그런데 유니티는 Assets 안에 있는 것만 본다. 그래서 여기로 복사한다.
# 이쪽은 커밋한다. 프로젝트를 받은 사람이 블렌더 없이도 열 수 있어야 한다.
#
# GLB 가 아니라 FBX 를 넣는다. 유니티는 glTF 를 기본으로 읽지 못한다.
set -euo pipefail
cd "$(dirname "$0")/.."

B=unity/Assets/Art/Chars/Bodies
G=unity/Assets/Art/Chars/Garments
mkdir -p "$B" "$G"

cp -f chars/out/bodies/*.fbx   "$B"/
cp -f chars/out/garments/*.fbx "$G"/

echo "몸 $(ls "$B"/*.fbx | wc -l)벌 · 옷 $(ls "$G"/*.fbx | wc -l)벌 옮겼다."
echo "유니티에서 [이렘/캐릭터 확인 신] 을 누르면 55벌이 늘어선 신이 선다."
