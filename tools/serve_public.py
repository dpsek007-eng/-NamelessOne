# -*- coding: utf-8 -*-
"""바깥으로 내줄 것만 골라 담아 내주는 서버.

tools/serve.py 는 저장소 뿌리를 통째로 내준다 — .git 까지 들어 있다. 그것을 바깥
문에 붙이면 저장소를 공개하는 것이다. 그래서 바깥 문은 이 파일을 쓴다: 필요한 것만
따로 담고, 목록 보여주기를 막고, 127.0.0.1 에만 묶는다(밖으로는 터널이 낸다).

  python3 tools/serve_public.py [포트]          # 기본 8080
  docker run -d --name tul-tunnel --network host cloudflare/cloudflared:latest \
    tunnel --no-autoupdate --url http://127.0.0.1:8080

담는 것:
  · 뜰 재생 페이지 — viewer/garden.{html,json} + 몸 GLB + 소품 GLB + 타일 PNG
  · 유니티가 구운 것 — unity/build/web 이 있으면 /unity/ 로 붙는다 (없으면 그냥 건너뛴다)

무엇을 담을지는 garden.json 이 말해 준다. 목록을 손으로 적어 두면 사람이 늘 때
조용히 틀린다(tools/serve.py 머리말과 같은 이유).
"""
import http.server, json, os, shutil, socketserver, sys

REPO  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGE = os.environ.get("TUL_STAGE", "/tmp/tul-web")
TILES = "unity/Assets/Resources/Irem/Tiles"


def stage():
    """내줄 것만 복사해 둔다. 저장소를 직접 내주지 않으려고 한 번 옮긴다."""
    shutil.rmtree(STAGE, ignore_errors=True)

    def put(rel):
        dst = os.path.join(STAGE, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(os.path.join(REPO, rel), dst)

    put("viewer/garden.html"); put("viewer/garden.json")
    with open(os.path.join(REPO, "viewer/garden.json"), encoding="utf-8") as f:
        G = json.load(f)

    # 그 사람만의 몸·자세. 없으면 페이지가 조용히 역할 몸으로 돌아간다 —
    # 조용한 것이 문제라 여기서 챙긴다. 근거(src)까지 같이 나가지만
    # 그 글은 이미 저장소에 공개돼 있는 캐릭터 설정이다.
    SH = {}
    if os.path.exists(os.path.join(REPO, "data/shades.json")):
        put("data/shades.json")
        with open(os.path.join(REPO, "data/shades.json"), encoding="utf-8") as f:
            SH = json.load(f)["shades"]

    # 몸집을 덮어쓴 사람은 제 GLB 를 쓴다 (viewer/garden.html bodyOf 와 같은 규칙).
    def body_of(c):
        e = SH.get(c["id"]) or {}
        return c["id"] if e.get("macro") else c["slug"]

    miss = []
    for rel in ([f"chars/out/cast/{s}.glb" for s in {body_of(c) for c in G["cast"]}]
              + [f"pipeline3d/out/props/{s}.glb" for s in {s["prop"] for s in G["stations"]}]):
        put(rel) if os.path.exists(os.path.join(REPO, rel)) else miss.append(rel)
    for f in os.listdir(os.path.join(REPO, TILES)):
        if f.endswith(".png"):
            put(f"{TILES}/{f}")

    # 유니티가 구운 것. 없으면 없는 대로 둔다 — 없는 것을 있다고 적지 않는다.
    src = os.path.join(REPO, "unity/build/web")
    unity = os.path.isdir(src) and os.path.exists(os.path.join(src, "index.html"))
    if unity:
        shutil.copytree(src, os.path.join(STAGE, "unity"), dirs_exist_ok=True)

    with open(os.path.join(STAGE, "index.html"), "w", encoding="utf-8") as f:
        f.write(INDEX.replace("<!--UNITY-->", UNITY_ROW if unity else UNITY_NONE))

    n = sum(len(fs) for _, _, fs in os.walk(STAGE))
    sz = sum(os.path.getsize(os.path.join(r, f))
             for r, _, fs in os.walk(STAGE) for f in fs)
    print(f"  담았다 {n}개 · {sz/1e6:.1f}MB · 유니티 빌드 {'있다' if unity else '없다'}")
    if miss:
        print("  빠진 것:", *miss, sep="\n    ")
    return unity


INDEX = """<!doctype html><html lang=ko><meta charset=utf-8>
<title>이렘의 탑 — 뜰</title><meta name=viewport content="width=device-width,initial-scale=1">
<style>body{background:#141210;color:#e8e2d8;font:15px/1.7 system-ui,sans-serif;
margin:0;display:grid;place-items:center;min-height:100vh}
main{max-width:34rem;padding:24px}h1{font-size:20px;margin:0 0 4px}
a{display:block;border:1px solid #4a423a;border-radius:8px;padding:14px 16px;
margin:12px 0;color:#e8e2d8;text-decoration:none}a:hover{border-color:#c98b3a}
b{color:#c98b3a}small{color:#8b8279}</style>
<main><h1>이렘의 탑 — 뜰</h1>
<small>잔상 스물셋이 제 생업 일터에서 일하고 서로 말을 건다.</small>
<a href="/viewer/garden.html"><b>사건 목록을 재생한다</b> (three.js)<br>
<small>계산은 Irem.Sim/Garden.cs 가 끝냈다. 이 쪽은 재생만 한다.</small></a>
<!--UNITY--></main>"""
UNITY_ROW = """<a href="/unity/"><b>유니티가 도는 것을 본다</b> (WebGL)<br>
<small>중계가 아니다. 유니티 런타임이 당신 브라우저에서 직접 돈다.</small></a>"""
UNITY_NONE = """<p><small>유니티 WebGL 은 아직 굽지 않았다
(unity/build/web 이 오면 여기 뜬다).</small></p>"""


class H(http.server.SimpleHTTPRequestHandler):
    # .wasm 을 octet-stream 으로 내주면 브라우저가 흘려 넣기(streaming)로 못 읽는다.
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".wasm": "application/wasm", ".data": "application/octet-stream",
                      ".glb": "model/gltf-binary", ".json": "application/json"}

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=STAGE, **kw)

    def list_directory(self, path):
        # 상태줄은 latin-1 만 담는다. 사유는 ASCII 로, 말은 본문에 적는다.
        self.send_error(403, "Forbidden", "목록은 내주지 않는다")
        return None

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *a):
        pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    stage()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), H) as s:
        print(f"\n  http://127.0.0.1:{port}/   (바깥으로는 터널이 낸다)\n", flush=True)
        s.serve_forever()


if __name__ == "__main__":
    main()
