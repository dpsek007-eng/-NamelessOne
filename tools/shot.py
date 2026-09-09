#!/usr/bin/env python3
"""움직이는 화면을 그대로 찍는다.

크롬의 --screenshot 은 --virtual-time-budget 에 기대는데, 이 페이지처럼
requestAnimationFrame 이 멈추지 않으면 가상시간이 끝내 흐르지 않아 셔터가
영영 안 눌린다(예산 500 도 1500 도 40000 도 똑같이 매달렸다. 2D 탭은 2초).
그래서 가상시간을 쓰지 않고, 실제 시간만큼 기다린 뒤 CDP 로 직접 찍는다.

  python3 tools/shot.py http://127.0.0.1:8000/viewer/#one /tmp/a.png --wait 90
"""
import argparse, asyncio, base64, json, os, shutil, socket, subprocess, sys, tempfile, time, urllib.request

from websockets.asyncio.client import connect


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


def targets(port, timeout):
    """크롬이 디버깅 창구를 열 때까지 기다렸다가 페이지 하나를 집는다."""
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=2) as r:
                for t in json.load(r):
                    if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                        return t["webSocketDebuggerUrl"]
        except Exception:
            pass
        time.sleep(1)
    raise SystemExit("크롬이 디버깅 창구를 안 열었다")


async def take(ws_url, url, out, wait, width, height):
    n = 0
    async with connect(ws_url, max_size=None, open_timeout=60) as ws:
        async def call(method, **params):
            nonlocal n
            n += 1
            await ws.send(json.dumps({"id": n, "method": method, "params": params}))
            while True:
                m = json.loads(await ws.recv())
                if m.get("id") == n:
                    if "error" in m:
                        raise SystemExit(f"{method}: {m['error']}")
                    return m.get("result", {})

        await call("Emulation.setDeviceMetricsOverride", width=width, height=height,
                   deviceScaleFactor=1, mobile=False)
        await call("Page.enable")
        await call("Page.navigate", url=url)
        # 가상시간이 아니라 진짜 시간. 이 기계가 느린 만큼 기다려 준다.
        await asyncio.sleep(wait)
        r = await call("Page.captureScreenshot", format="png", captureBeyondViewport=False)
        raw = base64.b64decode(r["data"])
    with open(out, "wb") as f:
        f.write(raw)
    return len(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url"); ap.add_argument("out")
    ap.add_argument("--wait", type=float, default=60.0, help="찍기 전에 기다리는 실제 초")
    ap.add_argument("--width", type=int, default=1400)
    ap.add_argument("--height", type=int, default=900)
    a = ap.parse_args()

    port = free_port()
    prof = tempfile.mkdtemp(prefix="shot-")
    ch = subprocess.Popen([
        "google-chrome", "--headless=new", "--disable-gpu",
        "--enable-unsafe-swiftshader", "--use-gl=swiftshader", "--no-sandbox",
        "--disable-dev-shm-usage", f"--user-data-dir={prof}",
        f"--remote-debugging-port={port}",
        f"--window-size={a.width},{a.height}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        ws_url = targets(port, 120)
        size = asyncio.run(take(ws_url, a.url, a.out, a.wait, a.width, a.height))
        print(f"찍었다 {a.out} {size} bytes")
    finally:
        ch.terminate()
        try:
            ch.wait(timeout=15)
        except subprocess.TimeoutExpired:
            ch.kill()
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    main()
