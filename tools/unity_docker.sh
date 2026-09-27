#!/usr/bin/env bash
# 유니티를 도커로 굴린다 — 이 서버에 유니티를 설치하지 않는다(CLAUDE.md: 설치는 도커로).
#
#   tools/unity_docker.sh alf              # 1) 인증 요청 파일(.alf)을 만든다
#   tools/unity_docker.sh activate a.ulf   # 2) 받아 온 면허(.ulf)를 넣는다
#   tools/unity_docker.sh selftest         # 3) 유니티 안에서 자체 점검 (여기서 처음 컴파일된다)
#   tools/unity_docker.sh web              # 4) 뜰을 WebGL 로 굽는다 → unity/build/web
#
# 면허는 .unity-lic/ 에 둔다. .gitignore 가 막는다 — 면허는 저장소에 들어가면 안 된다.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
TAG="${UNITY_TAG:-unityci/editor:6000.5.10f1-webgl-3.2.2}"
LIC="$REPO/.unity-lic"
mkdir -p "$LIC"

run() {   # 유니티 한 번 굴리기. 로그는 그대로 흘려보낸다 — 삼키면 왜 멈췄는지 못 본다.
  docker run --rm \
    -v "$REPO":/w -w /w/unity \
    -v "$LIC":/usr/share/unity3d/config \
    -e HOME=/tmp \
    "$TAG" unity-editor -batchmode -nographics -logFile /dev/stdout "$@"
}

case "${1:-}" in
  alf)
    # 이 파일을 https://license.unity3d.com/manual 에 올리면 .ulf 를 내준다.
    # 암호를 서버에 두지 않으려고 이 길을 쓴다 — 브라우저에서 사람이 한 번만 하면 된다.
    cd "$LIC" && docker run --rm -v "$LIC":/lic -w /lic -e HOME=/tmp "$TAG" \
      unity-editor -batchmode -nographics -quit -logFile /dev/stdout \
      -createManualActivationFile || true
    ls -l "$LIC"/*.alf
    ;;
  activate)
    [ -f "${2:-}" ] || { echo "면허 파일(.ulf)을 달라: $0 activate 받은파일.ulf"; exit 2; }
    cp "$2" "$LIC/Unity_lic.ulf"
    run -quit -manualLicenseFile "/usr/share/unity3d/config/Unity_lic.ulf" || true
    ls -l "$LIC"
    ;;
  selftest)
    run -quit -executeMethod Irem.Editor.IremSelfTest.Run
    ;;
  web)
    run -quit -buildTarget WebGL -executeMethod Irem.Editor.IremBuild.WebGL
    echo "── 구운 것:"; du -sh unity/build/web 2>/dev/null || echo "  없다"
    ;;
  *)
    sed -n '2,9p' "$0"; exit 2 ;;
esac
