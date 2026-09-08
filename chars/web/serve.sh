#!/usr/bin/env bash
# 서버컴에는 화면이 없다. 이걸 띄우고 다른 컴퓨터 브라우저로 들어와서 본다.
#   ./chars/web/serve.sh          # 8765 포트
#   ./chars/web/serve.sh 9000
# 뿌리는 chars/ 다. web/ 안에서 ../out/*.glb 를 읽어야 하기 때문이다.
set -e
PORT=${1:-8765}
cd "$(dirname "$0")/.."
IP=$(hostname -I | awk '{print $1}')
echo "   http://$IP:$PORT/web/"
echo "   (같은 컴퓨터면 http://localhost:$PORT/web/)"
exec python3 -m http.server "$PORT" --bind 0.0.0.0
