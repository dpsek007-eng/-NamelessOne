# -*- coding: utf-8 -*-
"""외형 뷰어 서버 — 서버컴이 헤드리스라 브라우저로 본다.

  python3 tools/serve.py [포트]
  → http://<서버IP>:8000/viewer/

산출물을 훑어 viewer/manifest.json 을 매번 새로 쓴다.
목록을 손으로 적어 두면 파일이 늘 때 조용히 틀린다.
"""
import json, os, sys, socket, http.server, socketserver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROLES = [("guard", "수호"), ("resist", "저항"), ("devote", "헌신"),
         ("seek", "탐구"), ("flee", "도피")]
TIERS = [("royal","왕실"),("noble","귀족"),("mage","술사"),("clergy","성직"),
         ("clerk","관리"),("merchant","상인"),("artisan","장인"),
         ("peasant","농어민"),("soldier","병졸"),("servant","하인"),("vagrant","유랑")]


def ls(rel, ext):
    d = os.path.join(ROOT, rel)
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.lower().endswith(ext))


def faces():
    """초상. index.json 이 아니라 **디스크에 실제로 있는 파일**로 짠다.

    생성이 도는 중에도 서버를 띄울 수 있어야 해서다. index.json 은 다 끝나야
    쓰이므로, 그것만 믿으면 도는 동안에는 한 장도 안 보인다.
    """
    d = os.path.join(ROOT, "pipeline3d/out/faces")
    if not os.path.isdir(d):
        return []
    boxes = {}
    bp = os.path.join(d, "boxes.json")
    if os.path.exists(bp):
        with open(bp, encoding="utf-8") as f:
            boxes = json.load(f)
    # index.json 은 생성이 다 끝나야 쓰인다. 도는 중에도 이름이 보이도록
    # data/characters.json 과 역할x계층 표에서 먼저 채운다.
    meta = {}
    cp = os.path.join(ROOT, "data/characters.json")
    if os.path.exists(cp):
        with open(cp, encoding="utf-8") as f:
            for c in json.load(f)["characters"]:
                meta[c["id"]] = {"ko": c["name"], "kind": "named",
                                 "rarity": c.get("rarity")}
    for rs, rk in ROLES:
        for ts, tk in TIERS:
            meta[f"{rs}_{ts}"] = {"ko": f"{rk}·{tk}", "kind": "part"}
    ip = os.path.join(d, "index.json")
    if os.path.exists(ip):
        with open(ip, encoding="utf-8") as f:
            for r in json.load(f).get("rows", []):
                meta.setdefault(r["id"], {}).update(r)
    # 구도가 장마다 다르다 (실측: 얼굴 너비 0.1~0.8). 어느 장을 대표로 쓸지는
    # tools/focus_stack.py --pick 이 재서 골라 둔다. 없으면 v0 이 대표가 된다.
    pick = {}
    pp = os.path.join(d, "pick.json")
    if os.path.exists(pp):
        with open(pp, encoding="utf-8") as f:
            pick = {k: v["image"] for k, v in json.load(f).items()}
    groups = {}
    for fn in ls("pipeline3d/out/faces", ".png"):
        cid = fn.rsplit("_v", 1)[0]
        groups.setdefault(cid, []).append(fn)
    out = []
    for cid, fns in sorted(groups.items()):
        m = meta.get(cid, {})
        best = pick.get(cid)
        fns = sorted(fns, key=lambda f: (f != best, f))
        out.append({
            "id": cid,
            "ko": m.get("ko", cid),
            "kind": m.get("kind", "named"),
            "rarity": m.get("rarity"),
            "picked": best,
            "images": [{"url": f"/pipeline3d/out/faces/{f}",
                        "box": boxes.get(f)} for f in fns],
        })
    return out


ARMS = [("", "기준", "머리와 어깨 · 지금 쓰는 것"),
        ("pose", "자세", "화폭을 상반신까지"),
        ("figure", "전신", "전신 + hands 를 품"),
        ("figurenh", "전신-손", "전신 · hands 는 도로 막음"),
        ("figure2", "화폭", "전신 + 화폭을 막는 말로 누름"),
        ("action", "행동", "역할 말을 몸이 하는 짓으로")]


def arms():
    """역할 실험의 팔들. 뽑아 둔 것만 올린다.

    GPU 를 못 쓰는 날에도 결과를 눈으로 볼 수 있어야 한다. 숫자는 docs 에
    적혀 있지만, 약이 들어갔는지는 결국 그림을 세어 봐야 안다.
    """
    out = []
    for slug, ko, note in ARMS:
        d = "pipeline3d/out/faces_" + slug if slug else "pipeline3d/out/faces"
        if not os.path.isdir(os.path.join(ROOT, d)):
            continue
        cells = []
        for ts, tk in TIERS:
            for rs, rk in ROLES:
                fns = [f"{rs}_{ts}_v{v}.png" for v in range(6)]
                fns = [f for f in fns if os.path.exists(os.path.join(ROOT, d, f))]
                if fns:
                    cells.append({"id": f"{rs}_{ts}", "ko": f"{rk}·{tk}",
                                  "urls": [f"/{d}/{f}" for f in fns]})
        if cells:
            out.append({"slug": slug or "base", "ko": ko, "note": note,
                        "cells": cells,
                        "n": sum(len(c["urls"]) for c in cells)})
    return out


def build_manifest():
    m = {
        "sprites": [{"name": f[:-4], "url": f"/art/shades/{f}"}
                    for f in ls("art/shades", ".png")],
        "shots": [],
        "bodies": [{"slug": f[:-4], "url": f"/chars/out/bodies/{f}",
                    "ko": dict(ROLES).get(f[:-4], f[:-4])}
                   for f in ls("chars/out/bodies", ".glb")],
        "garments": [{"name": f[:-4], "url": f"/chars/out/garments/{f}"}
                     for f in ls("chars/out/garments", ".glb")],
        "props": [{"name": f[:-4], "url": f"/pipeline3d/out/props/{f}"}
                  for f in ls("pipeline3d/out/props", ".glb")],
        "faces": faces(),
        "arms": arms(),
        "roles": [{"slug": s, "ko": k} for s, k in ROLES],
        "tiers": [{"slug": s, "ko": k} for s, k in TIERS],
    }
    have = set(ls("chars/out/garments/shots", ".png"))
    for rs, rk in ROLES:
        for ts, tk in TIERS:
            f = f"{rs}_{ts}.png"
            if f in have:
                m["shots"].append({"role": rs, "role_ko": rk, "tier": ts,
                                   "tier_ko": tk,
                                   "url": f"/chars/out/garments/shots/{f}"})
    return m


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    man = build_manifest()
    with open(os.path.join(ROOT, "viewer", "manifest.json"), "w") as fp:
        json.dump(man, fp, ensure_ascii=False, indent=1)
    for k in ("sprites", "shots", "bodies", "garments", "props", "faces"):
        print(f"  {k:<9} {len(man[k])}")
    for a in man["arms"]:
        print(f"  팔 {a['ko']:<8} {a['n']}장")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]; s.close()
    except OSError:
        ip = "127.0.0.1"

    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=ROOT, **kw)
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()
        def log_message(self, *a):
            pass

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), H) as httpd:
        print(f"\n  http://{ip}:{port}/viewer/\n")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
