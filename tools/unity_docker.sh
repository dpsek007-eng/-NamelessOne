#!/usr/bin/env bash
# 유니티를 도커로 굴린다 — 이 서버에 유니티를 설치하지 않는다(CLAUDE.md: 설치는 도커로).
#
#   tools/unity_docker.sh login      # 1) 면허를 켠다 (계정은 .unity-lic/creds.env 에서 읽는다)
#   tools/unity_docker.sh seats      # 계정에 붙은 좌석을 본다
#   tools/unity_docker.sh selftest   # 2) 유니티 안에서 자체 점검 (여기서 처음 컴파일된다)
#   tools/unity_docker.sh web        # 3) 뜰을 WebGL 로 굽는다 → unity/build/web
#   tools/unity_docker.sh logout     # 이 기계에서 면허를 내린다
#
# 오프라인(수동) 인증은 쓰지 않는다. Unity 가 Personal 좌석에는 막아 두었다 —
# license.unity3d.com/manual 이 「Enterprise · Industry 좌석만 가능하다」고 답한다(2026-09 실측).
# 그래서 온라인 인증만 남았고, 그것은 계정으로만 된다.
#
# 암호는 .unity-lic/creds.env 에만 둔다. .gitignore 가 .unity-lic/ 을 막는다.
# 이 스크립트는 암호를 화면에 찍지 않는다 — 로그에 남으면 그것이 곧 샌 것이다.
set -euo pipefail
cd "$(dirname "$0")/.."
REPO="$PWD"
TAG="${UNITY_TAG:-unityci/editor:6000.5.10f1-webgl-3.2.2}"
LIC="$REPO/.unity-lic"
CRED="$LIC/creds.env"
CLIENT=/opt/unity/Editor/Data/Resources/Licensing/Client/Unity.Licensing.Client
mkdir -p "$LIC"

need_cred() {
  [ -f "$CRED" ] || { cat >&2 <<'MSG'
계정이 없다. 이 서버의 셸에서 (클로드를 거치지 말고) 직접 만들어라 —
거쳐서 치면 암호가 대화 기록에 남는다:

  cd <저장소>
  mkdir -p .unity-lic && chmod 700 .unity-lic
  printf 'UNITY_EMAIL=%s\n' '당신의유니티계정@메일' > .unity-lic/creds.env
  read -rsp '유니티 암호: ' p && printf 'UNITY_PASSWORD=%s\n' "$p" >> .unity-lic/creds.env && unset p
  chmod 600 .unity-lic/creds.env

Pro·Plus 일련번호가 있으면 이 줄을 더해라:  UNITY_SERIAL=XX-XXXX-...
MSG
    exit 2; }
}

# 유니티 한 번 굴리기. 로그는 그대로 흘려보낸다 — 삼키면 왜 멈췄는지 못 본다.
run() {
  docker run --rm \
    -v "$REPO":/w -w /w/unity \
    -v "$LIC":/root/.local/share/unity3d/Unity \
    -e HOME=/root \
    "$TAG" unity-editor -batchmode -nographics -logFile /dev/stdout "$@"
}

# 인증기만 굴리기. --env-file 로 넣어 명령줄에 암호가 안 뜨게 한다
# (ps 에 보이면 같은 기계의 다른 사람이 읽는다).
lic() {
  docker run --rm --env-file "$CRED" \
    -v "$LIC":/root/.local/share/unity3d/Unity \
    -e HOME=/root \
    "$TAG" bash -lc "$CLIENT $* \
      --username \"\$UNITY_EMAIL\" --password \"\$UNITY_PASSWORD\"" 2>&1 \
    | sed -E 's/(password|token)[= ][^ ]*/\1=***/Ig'
}

case "${1:-}" in
  login)
    need_cred
    set +e
    # shellcheck disable=SC1090
    SERIAL=$(grep -E '^UNITY_SERIAL=' "$CRED" | cut -d= -f2-)
    if [ -n "$SERIAL" ]; then lic --activate-all --serial "$SERIAL"
    else                      lic --activate-all --include-personal; fi
    rc=$?; set -e
    echo "── 지금 이 기계가 쥔 권한:"
    docker run --rm -v "$LIC":/root/.local/share/unity3d/Unity -e HOME=/root "$TAG" \
      bash -lc "$CLIENT --showEntitlements" 2>&1 | tail -20
    exit $rc ;;
  seats)   need_cred; lic --show-seats ;;
  logout)  need_cred; lic --deactivate-all ;;
  selftest) run -quit -executeMethod Irem.Editor.IremSelfTest.Run ;;
  web)
    run -quit -buildTarget WebGL -executeMethod Irem.Editor.IremBuild.WebGL
    echo "── 구운 것:"; du -sh unity/build/web 2>/dev/null || echo "  없다" ;;
  *) sed -n '2,10p' "$0"; exit 2 ;;
esac
