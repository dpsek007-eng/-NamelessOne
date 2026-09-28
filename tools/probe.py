#!/usr/bin/env python3
"""뜰이 도는 동안 몸 스물셋을 재 본다. 화면을 눈으로 보고 적지 않으려고 만든 자다.

  python3 tools/probe.py http://127.0.0.1:8080/viewer/garden.html --wait 60

페이지가 낸 구멍(window.IREM)으로 각자의 지금 동작·클립 안의 자리·박자를 읽는다.
shot.py 와 같은 길로 크롬을 띄운다 — 화면 없이, GPU 없이 (이 기계는 서버다).
"""
import argparse, asyncio, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request
from websockets.asyncio.client import connect

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shot import targets, free_port, CHROME          # 같은 크롬, 같은 깃발을 쓴다

JS = """(() => {
  const out = [];
  for (const [idx, v] of window.IREM.views)
    out.push({ idx, name: v.def.name, clip: v.name,
               t: v.act ? +v.act.time.toFixed(3) : -1,
               dur: v.act ? +v.act.getClip().duration.toFixed(3) : -1,
               tempo: v.tempo, phase: v.phase, breath: v.breath });
  return JSON.stringify(out);
})()"""


async def probe(ws_url, url, wait, shots, gap):
    n = 0
    async with connect(ws_url, max_size=None, open_timeout=60) as ws:
        async def call(method, **params):
            nonlocal n
            n += 1
            await ws.send(json.dumps({"id": n, "method": method, "params": params}))
            while True:
                m = json.loads(await ws.recv())
                if m.get("id") == n:
                    if "error" in m: raise SystemExit(f"{method}: {m['error']}")
                    return m.get("result", {})
        await call("Page.enable")
        await call("Page.navigate", url=url)
        await asyncio.sleep(wait)
        rows = []
        for i in range(shots):
            if i: await asyncio.sleep(gap)
            r = await call("Runtime.evaluate", expression=JS, returnByValue=True)
            rows.append(json.loads(r["result"]["value"]))
        return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--wait", type=float, default=60.0, help="재기 전에 기다리는 실제 초")
    ap.add_argument("--shots", type=int, default=3, help="몇 번 재는가")
    ap.add_argument("--gap", type=float, default=1.0, help="잴 때마다 두는 사이 (초)")
    a = ap.parse_args()

    port, prof = free_port(), tempfile.mkdtemp(prefix="probe-")
    p = subprocess.Popen(CHROME + [f"--remote-debugging-port={port}",
                                   f"--user-data-dir={prof}", "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        rows = asyncio.run(probe(targets(port, 60), a.url, a.wait, a.shots, a.gap))
    finally:
        p.terminate()
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill()
        shutil.rmtree(prof, ignore_errors=True)

    for i, r in enumerate(rows):
        if not r: print(f"[{i}] 아무것도 못 읽었다 (window.IREM 이 없다)"); continue
        clips = {}
        for x in r: clips.setdefault(x["clip"], []).append(x)
        print(f"[{i}] 스물셋 —", " · ".join(f"{k} {len(v)}명" for k, v in sorted(clips.items())))
        for k, v in sorted(clips.items()):
            if len(v) < 2: continue
            # 같은 동작을 하는 사람들이 클립 안 어디에 있는가. 겹치면 같은 태엽이다.
            pos = sorted(round(x["t"] / x["dur"], 3) for x in v if x["dur"] > 0)
            same = len(pos) - len(set(pos))
            print(f"      {k:6s} 클립 안의 자리 {min(pos):.3f}~{max(pos):.3f} · "
                  f"똑같은 자리에 선 사람 {same}명")
    print("\n※ 「똑같은 자리에 선 사람」이 0명이면 같은 동작이라도 저마다 다른 곳을 지나고 있다.\n"
          "   그 수가 사람 수만큼 나오면 스물셋이 아니라 같은 태엽 스물셋이다.")


if __name__ == "__main__":
    main()
