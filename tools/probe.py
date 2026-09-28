#!/usr/bin/env python3
"""뜰이 도는 동안 몸 스물셋을 재 본다. 화면을 눈으로 보고 적지 않으려고 만든 자다.

  python3 tools/probe.py http://127.0.0.1:8080/viewer/garden.html --wait 60

페이지가 낸 구멍(window.IREM)으로 각자의 지금 동작·클립 안의 자리·박자를 읽는다.
shot.py 와 같은 길로 크롬을 띄운다 — 화면 없이, GPU 없이 (이 기계는 서버다).
"""
import argparse, math, asyncio, json, os, shutil, socket, subprocess, sys, tempfile, time
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

# 자세를 재는 자. 뼈를 이름으로 찾아 지금 각도와 굵기를 그대로 읽는다.
# 「굽어 보인다」고 적지 않으려고 낸다 — 굽은 등은 각도가 있거나 없다.
STANCE = """(() => {
  const BONES = ['spine_01','spine_02','spine_03','neck_01','head',
                 'clavicle_l','clavicle_r','upperarm_l','upperarm_r',
                 'lowerarm_l','lowerarm_r','hand_l','hand_r'];
  const out = [];
  for (const [idx, v] of window.IREM.views) {
    let sk = null;
    v.root.traverse(o => { if (!sk && o.isSkinnedMesh) sk = o.skeleton; });
    if (!sk) continue;
    const row = { idx, id: v.def.id, name: v.def.name, clip: v.name,
                  stance: v.stance ? v.stance.length : 0, bones: {}, off: {} };
    // 자세가 스스로 낸 몫만 따로 적는다. 뼈에서 읽은 각도는 클립 몫이 섞여 있어
    // 적힌 값과 바로 견줄 수 없다. 이 쪽은 층이 계산한 사원수 그대로라 견줄 수 있다.
    for (const e of (v.stance || [])) {
      const d = {};
      if (e.q) d.deg = +(2 * Math.acos(Math.min(1, Math.abs(e.q.w))) * 180 / Math.PI).toFixed(2);
      if (e.scale) d.sx = +e.scale.x.toFixed(3);
      row.off[e.bone.name] = d;
    }
    for (const n of BONES) {
      const b = sk.bones.find(x => x.name === n);
      if (!b) continue;
      // 축·각도로 적는다. 사원수 네 값보다 읽기 쉽고, 견주기도 이 쪽이 쉽다.
      const q = b.quaternion;
      const deg = 2 * Math.acos(Math.min(1, Math.abs(q.w))) * 180 / Math.PI;
      row.bones[n] = { deg: +deg.toFixed(2), sx: +b.scale.x.toFixed(3) };
    }
    out.push(row);
  }
  return JSON.stringify(out);
})()"""


# 발이 땅을 잡는가. 걷는 동안 디딘 발은 세계 좌표에서 **멈춰 있어야** 한다.
# 몸만 나아가고 발이 같이 끌려가면 그게 미끄러지는 것이고, 사람이 아니라
# 미끄러지는 인형으로 보인다. 한 프레임씩 재서 디딘 발(그 프레임에 덜 움직인 쪽)의
# 이동량을 몸의 이동량으로 나눈다. 0 이면 땅을 잡았고 1 이면 통째로 끌려간 것이다.
FEET = """(() => new Promise(res => {
  const V = [...window.IREM.views.values()];
  const pick = v => {
    let sk = null;
    v.root.traverse(o => { if (!sk && o.isSkinnedMesh) sk = o.skeleton; });
    if (!sk) return null;
    const f = n => sk.bones.find(b => b.name === n);
    const l = f('foot_l'), r = f('foot_r');
    return (l && r) ? { v, l, r } : null;
  };
  const who = V.map(pick).filter(Boolean);
  const acc = who.map(() => ({ foot: 0, body: 0, walk: 0, n: 0 }));
  const pos = o => { o.updateWorldMatrix(true, false);
                     const e = o.matrixWorld.elements;
                     return [e[12], e[14]]; };
  let prev = who.map(w => [pos(w.l), pos(w.r), pos(w.v.root)]);
  let n = 0;
  const N = %d;
  const tick = () => {
    const cur = who.map(w => [pos(w.l), pos(w.r), pos(w.v.root)]);
    for (let i = 0; i < who.length; i++) {
      const d = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
      const dl = d(cur[i][0], prev[i][0]), dr = d(cur[i][1], prev[i][1]);
      const db = d(cur[i][2], prev[i][2]);
      const a2 = acc[i];
      a2.n++;
      if (who[i].v.name === 'walk') a2.walk++;
      if (db > 1e-5) { a2.foot += Math.min(dl, dr); a2.body += db; }
    }
    prev = cur;
    if (++n < N) requestAnimationFrame(tick);
    else res(JSON.stringify(who.map((w, i) => ({
      id: w.v.def.id, name: w.v.def.name, clip: w.v.name,
      frames: acc[i].n, walkFrames: acc[i].walk,
      body: +acc[i].body.toFixed(4), foot: +acc[i].foot.toFixed(4),
      slip: acc[i].body > 1e-4 ? +(acc[i].foot / acc[i].body).toFixed(3) : -1,
    }))));
  };
  requestAnimationFrame(tick);
}))()""" % 240


# 걸음폭 — 프레임이 느려도 같은 값이 나오게 잰다.
# 화면 새로 고침(rAF)에 기대지 않고 동작 시계를 직접 고정 간격으로 밀면서
# 발이 몸 기준으로 앞뒤로 얼마나 오가는지 본다. 그 오간 길이가 한 걸음이고,
# 한 바퀴(왼발-오른발)면 그 두 배만큼 땅을 지나가야 맞다.
STRIDE = """(() => {
  const V = [...window.IREM.views.values()];
  const out = [];
  for (const v of V) {
    let sk = null;
    v.root.traverse(o => { if (!sk && o.isSkinnedMesh) sk = o.skeleton; });
    if (!sk) continue;
    const foot = sk.bones.find(b => b.name === 'foot_l');
    if (!foot) continue;
    v.play('walk', true);
    v.mixer.update(0);
    const a = v.act && v.act.getClip();
    if (!a) continue;
    const dur = a.duration, N = 240, dt = dur / N;
    const tmp = v.root.position.clone();
    const lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    for (let i = 0; i <= N; i++) {
      v.mixer.update(i ? dt : 0);
      foot.updateWorldMatrix(true, false);
      const e = foot.matrixWorld.elements;
      tmp.set(e[12], e[13], e[14]);
      v.root.worldToLocal(tmp);
      const c = [tmp.x, tmp.y, tmp.z];
      for (let k = 0; k < 3; k++) { if (c[k] < lo[k]) lo[k] = c[k];
                                    if (c[k] > hi[k]) hi[k] = c[k]; }
    }
    const rng = [hi[0]-lo[0], hi[1]-lo[1], hi[2]-lo[2]];
    let ax = 0; for (let k = 1; k < 3; k++) if (rng[k] > rng[ax]) ax = k;
    out.push({ id: v.def.id, name: v.def.name, dur: +dur.toFixed(3),
               axis: 'xyz'[ax], swing: +rng[ax].toFixed(4),
               lift: +rng[1].toFixed(4),
               rng: rng.map(x => +x.toFixed(4)) });
    if (out.length >= 3) break;
  }
  return JSON.stringify(out);
})()"""


async def probe(ws_url, url, wait, shots, gap, stance=False, feet=False, stride=False):
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
            r = await call("Runtime.evaluate",
                           expression=(STRIDE if stride else
                                       FEET if feet else
                                       STANCE if stance else JS),
                           returnByValue=True, awaitPromise=True)
            if os.environ.get("PROBE_RAW"):
                print("RAW:", json.dumps(r, ensure_ascii=False)[:1200])
            if "exceptionDetails" in r:
                print("브라우저가 던졌다:", json.dumps(r["exceptionDetails"],
                                                  ensure_ascii=False)[:600])
                rows.append(None); continue
            v = r.get("result", {}).get("value")
            rows.append(json.loads(v) if isinstance(v, str) else v)
        return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--wait", type=float, default=60.0, help="재기 전에 기다리는 실제 초")
    ap.add_argument("--shots", type=int, default=3, help="몇 번 재는가")
    ap.add_argument("--gap", type=float, default=1.0, help="잴 때마다 두는 사이 (초)")
    ap.add_argument("--stride", action="store_true",
                    help="걸음폭 — 발이 몸 기준으로 오가는 길이 (프레임과 무관)")
    ap.add_argument("--feet", action="store_true",
                    help="디딘 발이 땅을 잡는가 — 발 이동량 / 몸 이동량")
    ap.add_argument("--stance", action="store_true",
                    help="동작이 아니라 자세를 잰다 — 뼈 각도와 굵기 (data/shades.json)")
    a = ap.parse_args()

    port, prof = free_port(), tempfile.mkdtemp(prefix="probe-")
    p = subprocess.Popen(CHROME + [f"--remote-debugging-port={port}",
                                   f"--user-data-dir={prof}", "about:blank"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        rows = asyncio.run(probe(targets(port, 60), a.url, a.wait, a.shots, a.gap,
                                 stance=a.stance, feet=a.feet, stride=a.stride))
    finally:
        p.terminate()
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill()
        shutil.rmtree(prof, ignore_errors=True)

    if a.stride:
        return report_stride(rows)
    if a.feet:
        return report_feet(rows)
    if a.stance:
        return report_stance(rows)

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


def report_stride(rows):
    """걸음폭. 뜰이 한 칸 1m 를 STEP 초에 지나가므로 다리도 그만큼 내야 한다."""
    STEP, CELL = 0.34, 1.0                      # viewer/garden.html · GardenDirector
    for i, r in enumerate(rows):
        if not r:
            print(f"[{i}] 아무것도 못 읽었다")
            continue
        for x in r:
            # 한 바퀴에 두 걸음이다. 발이 몸 기준으로 오간 길이가 한 걸음 몫이고,
            # 그 두 배가 한 바퀴 동안 지나가야 하는 땅이다.
            leg = 2 * x["swing"] / x["dur"]
            body = CELL / STEP
            print(f"      {x['name']:12s} 한 바퀴 {x['dur']:.3f}초 · "
                  f"발이 오간 길이 {x['swing']:.3f}m({x['axis']}축) · 발 든 높이 {x['lift']:.3f}m")
            print(f"      {'':12s} 다리가 내는 속도 {leg:.2f} m/s  ↔  뜰이 옮기는 속도 "
                  f"{body:.2f} m/s   → {body/leg:.2f}배 빠르다")
    print("\n※ 다리가 내는 속도보다 뜰이 빠르면 그 차이만큼 발이 땅에서 미끄러진다.\n"
          "   같으면 디딘 발이 땅에 붙어 있다.")


def report_feet(rows):
    """디딘 발이 땅을 잡는가. 1 이면 통째로 끌려갔다."""
    for i, r in enumerate(rows):
        if not r:
            print(f"[{i}] 아무것도 못 읽었다 (window.IREM 이 없다)")
            continue
        mv = [x for x in r if x["slip"] >= 0]
        if not mv:
            print(f"[{i}] 그 동안 움직인 사람이 없다")
            continue
        mv.sort(key=lambda x: -x["slip"])
        avg = sum(x["slip"] for x in mv) / len(mv)
        print(f"[{i}] 움직인 사람 {len(mv)}/{len(r)}명 · 미끄럼 중앙값 "
              f"{sorted(x['slip'] for x in mv)[len(mv)//2]:.3f} · 평균 {avg:.3f}")
        for x in mv[:6]:
            print(f"      {x['name']:12s} {x['clip']:6s} "
                  f"몸 {x['body']:.3f}m · 디딘 발 {x['foot']:.3f}m · 미끄럼 {x['slip']:.3f}"
                  f"  (걷기 프레임 {x['walkFrames']}/{x['frames']})")
    print("\n※ 디딘 발은 세계 좌표에서 멈춰 있어야 한다. 0 이면 땅을 잡았고,\n"
          "   1 이면 몸이 간 만큼 발도 그대로 끌려갔다 — 미끄러지는 인형이다.")


def _qw(rot):
    """축마다 하나씩 곱한 사원수의 w. viewer 의 stance() 와 같은 순서로 곱한다."""
    w, x, y, z = 1.0, 0.0, 0.0, 0.0
    for k, deg in enumerate(rot):
        if not deg:
            continue
        h = math.radians(deg) / 2
        cw, s2 = math.cos(h), math.sin(h)
        ax = [0.0, 0.0, 0.0]
        ax[k] = s2
        bx, by, bz = ax
        w, x, y, z = (w * cw - x * bx - y * by - z * bz,
                      w * bx + x * cw + y * bz - z * by,
                      w * by - x * bz + y * cw + z * bx,
                      w * bz + x * by - y * bx + z * cw)
    return w


def report_stance(rows):
    """자세가 실제로 뼈에 닿았는가. 적힌 사람과 안 적힌 사람을 나란히 놓는다."""
    want = {}
    sp = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "data", "shades.json")
    if os.path.exists(sp):
        with open(sp, encoding="utf-8") as fp:
            want = json.load(fp)["shades"]

    for i, r in enumerate(rows):
        if not r:
            print(f"[{i}] 아무것도 못 읽었다 (window.IREM 이 없다)")
            continue
        has = [x for x in r if x["stance"] > 0]
        print(f"[{i}] 스물셋 중 자세가 얹힌 사람 {len(has)}명 "
              f"(data/shades.json 에 적힌 사람 {len(want)}명)")
        for x in sorted(r, key=lambda y: -y["stance"]):
            if not x["stance"]:
                continue
            e = want.get(x["id"], {})
            named = sorted((e.get("bones") or {}).keys())
            off = x.get("off") or {}
            cell = []
            for n in named:
                w = (e.get("bones") or {})[n]
                got = off.get(n, {})
                # 적힌 값 대 층이 낸 값. 회전은 크기 하나로 접어 견준다 —
                # 한 축만 쓴 자리는 이것이 곧 그 각도다.
                if w.get("rot") and any(w["rot"]):
                    deg0 = math.degrees(math.acos(min(1.0, abs(
                        _qw(w["rot"])))) * 2)
                    ok = "=" if abs(deg0 - got.get("deg", 0)) < 0.05 else "≠"
                    cell.append(f"{n} 적힘{deg0:.1f}{ok}낸값{got.get('deg', 0):.1f}도")
                if w.get("scale"):
                    ok = "=" if abs(w["scale"][0] - got.get("sx", 0)) < 0.005 else "≠"
                    cell.append(f"{n} 굵기 적힘{w['scale'][0]:.2f}{ok}낸값{got.get('sx', 0):.2f}")
            print(f"      {x['name']:10s} {x['clip']:6s} 뼈 {x['stance']}개 — "
                  + " · ".join(cell))
        # 아무것도 안 적힌 사람 하나를 같이 낸다. 견줄 것이 없으면 숫자가 큰지 작은지 모른다.
        plain = next((x for x in r if not x["stance"]), None)
        if plain:
            b = plain["bones"]
            keys = [k for k in ("spine_01", "spine_02", "spine_03", "upperarm_r") if k in b]
            print(f"      {plain['name']:10s} {plain['clip']:6s} 뼈 0개 — "
                  + " · ".join(f"{k} {b[k]['deg']:.1f}도"
                               + (f" 굵기 {b[k]['sx']:.2f}" if abs(b[k]["sx"] - 1) > 0.01 else "")
                               for k in keys) + "   ← 견줄 사람")
    print("\n※ 각도는 그 뼈가 쉼자세에서 얼마나 돌아 있는가다. 클립이 돌린 몫과 자세가 돌린\n"
          "   몫이 합쳐진 값이라, 같은 동작·같은 역할끼리 견주어야 자세 몫이 읽힌다.\n"
          "   굵기는 클립이 건드리지 않으므로 적힌 값이 그대로 나와야 한다.")


if __name__ == "__main__":
    main()
