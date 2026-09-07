// 계산은 Irem.Sim 이 끝냈다. 여기서는 사건 목록을 시간에 맞춰 보여 줄 뿐이다.
// 이름표와 체력줄은 IMGUI 로 그린다 — 어떤 렌더 파이프라인에서도 나온다.
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Irem.Data;
using Irem.Sim;

namespace Irem.Game
{
    public sealed class BattleDirector : MonoBehaviour
    {
        public BattleTables T;
        public FloorDef Floor;
        public Battle B;
        public float StepSeconds = 0.42f;
        public int TileVariants = 5;

        readonly Dictionary<int, ShadeView> _views = new();
        readonly Dictionary<int, string> _bubble = new();
        readonly Dictionary<int, float> _bubbleT = new();
        readonly List<string> _ticker = new();
        int _i;
        float _t;
        bool _paused;
        Camera _cam;
        GUIStyle _nm, _bub, _hdr;

        public Vector3 CellPos(int x, int y)
            => new Vector3(x * (float)ArtLoad.FW / ArtLoad.PPU,
                          -y * (float)ArtLoad.FH / ArtLoad.PPU * 0.62f, 0);

        public void Begin(BattleTables t, FloorDef f, Battle b, Camera cam)
        {
            T = t; Floor = f; B = b; _cam = cam;
            BuildField();
            SpawnUnits();
            FrameCamera();
        }

        void BuildField()
        {
            var root = new GameObject("Field").transform;
            root.SetParent(transform, false);
            for (int y = 0; y < B.Map.H; y++)
                for (int x = 0; x < B.Map.W; x++)
                {
                    Ground(root, "plain", x, y, -1);
                    char ch = B.Map.At(x, y);
                    if (ch != '.') Ground(root, null, x, y, 0, ch);
                }
        }

        void Ground(Transform root, string forceKind, int x, int y, int order, char ch = '.')
        {
            string name = forceKind != null
                ? forceKind + "_" + (Mathf.Abs(x * 7 + y * 13) % TileVariants)
                : ArtLoad.TileName(ch, x, y, TileVariants);
            var sp = ArtLoad.Tile(name);
            if (sp == null) return;
            var go = new GameObject($"t{x}_{y}_{name}");
            go.transform.SetParent(root, false);
            go.transform.position = CellPos(x, y);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sp; sr.sortingOrder = order;
            float cw = (float)ArtLoad.FW / ArtLoad.PPU;
            float chh = (float)ArtLoad.FH / ArtLoad.PPU * 0.62f;
            go.transform.localScale = new Vector3(cw / sp.bounds.size.x, chh / sp.bounds.size.y, 1);
        }

        void SpawnUnits()
        {
            foreach (var u in B.Units)
            {
                var go = new GameObject(u.Name);
                go.transform.SetParent(transform, false);
                var sr = go.AddComponent<SpriteRenderer>();
                sr.sortingOrder = 100 + u.Y * 2;
                var v = go.AddComponent<ShadeView>();
                var frames = ArtLoad.Sheet(SheetId(u), T.nf);
                v.Bind(frames, T);
                v.Warp(CellPos(u.X, u.Y));
                v.Face(!u.Foe);
                _views[u.Idx] = v;
            }
        }

        static string SheetId(Unit u) => u.Art ?? "unnamed_000";

        void FrameCamera()
        {
            float w = B.Map.W * (float)ArtLoad.FW / ArtLoad.PPU;
            float h = B.Map.H * (float)ArtLoad.FH / ArtLoad.PPU * 0.62f;
            _cam.orthographic = true;
            _cam.transform.position = new Vector3(w / 2 - 1.5f, -h / 2 + 1.5f, -10);
            _cam.orthographicSize = Mathf.Max(h / 2 + 1, w / 2 / _cam.aspect + 1);
            _cam.backgroundColor = new Color32(0x2A, 0x27, 0x23, 255);
        }

        void Update()
        {
            foreach (var k in _bubbleT.Keys.ToList())
            {
                _bubbleT[k] -= Time.deltaTime;
                if (_bubbleT[k] <= 0) { _bubbleT.Remove(k); _bubble.Remove(k); }
            }
            if (_paused || B == null) return;
            _t += Time.deltaTime;
            while (_t >= StepSeconds && _i < B.Events.Count)
            {
                _t -= StepSeconds;
                Step(B.Events[_i++]);
            }
        }

        void Step(in Irem.Sim.Event e)
        {
            ShadeView V(int i) => i >= 0 && _views.TryGetValue(i, out var v) ? v : null;
            switch (e.K)
            {
                case Ev.Turn:
                    Say($"── {e.N}턴 ──"); break;
                case Ev.Move:
                {
                    var u = B.Units[e.T];
                    V(e.T)?.MoveTo(CellPos(e.X, e.Y), StepSeconds * 0.8f);
                    var sr = V(e.T)?.GetComponent<SpriteRenderer>();
                    if (sr != null) sr.sortingOrder = 100 + e.Y * 2;
                    if (!string.IsNullOrEmpty(e.S)) Say($"{u.Name} — {Why(e.S)}");
                    break;
                }
                case Ev.Hit:
                {
                    var a = B.Units[e.A]; var t = B.Units[e.T];
                    var av = V(e.A); var tv = V(e.T);
                    if (av != null && tv != null) av.Face(tv.transform.position.x >= av.transform.position.x);
                    av?.Play("attack", true);
                    tv?.Play("hurt", true);
                    Say($"{a.Name} → {t.Short ?? t.Name} {e.D}");
                    break;
                }
                case Ev.Heal:
                    V(e.A)?.Play("attack", true);
                    Say($"{B.Units[e.A].Name} → {B.Units[e.T].Name} +{e.D}");
                    break;
                case Ev.Fall:
                    V(e.T)?.Play("fall", true);
                    Say($"{B.Units[e.T].Name} 흐려졌다");
                    break;
                case Ev.Think:
                    _bubble[e.A] = e.S; _bubbleT[e.A] = 2.2f;
                    Say($"{B.Units[e.A].Name} 「{e.S}」");
                    break;
                case Ev.Spot:
                    _bubble[e.A] = "!"; _bubbleT[e.A] = 0.9f;
                    break;
                case Ev.Ring:  Say($"종을 쳤다 {e.N}/{B.Goal.N}"); break;
                case Ev.Escape:
                    V(e.T)?.Play("fall", true);
                    Say($"빠져나갔다 {e.N}/{B.Goal.N}"); break;
                case Ev.Env:
                    V(e.T)?.Play("hurt", true);
                    Say($"{B.Units[e.T].Name} {e.S} -{e.D}"); break;
            }
        }

        static string Why(string w) => w switch
        {
            "advance" => "앞으로", "retreat" => "물러선다", "guard" => "막아선다",
            "keepdist" => "거리를 둔다", "heal" => "다가간다", "close" => "붙는다",
            "post" => "자리로 돌아간다", _ => "이동",
        };

        void Say(string s)
        {
            _ticker.Add(s);
            if (_ticker.Count > 9) _ticker.RemoveAt(0);
        }

        void EnsureStyles()
        {
            if (_nm != null) return;
            _nm  = new GUIStyle(GUI.skin.label) { fontSize = 11, alignment = TextAnchor.MiddleCenter };
            _bub = new GUIStyle(GUI.skin.box)   { fontSize = 11, alignment = TextAnchor.MiddleCenter };
            _hdr = new GUIStyle(GUI.skin.label) { fontSize = 13 };
            _nm.normal.textColor = new Color(0.82f, 0.84f, 0.86f);
            _hdr.normal.textColor = new Color(0.90f, 0.88f, 0.84f);
        }

        void OnGUI()
        {
            if (B == null || _cam == null) return;
            EnsureStyles();

            foreach (var u in B.Units)
            {
                if (!_views.TryGetValue(u.Idx, out var v) || v == null) continue;
                var wp = v.transform.position;
                var sp = _cam.WorldToScreenPoint(wp);
                if (sp.z < 0) continue;
                float sx = sp.x, sy = Screen.height - sp.y;

                // 체력줄
                if (u.Alive)
                {
                    float pct = Mathf.Clamp01((float)u.Hp / u.Max);
                    var r = new Rect(sx - 16, sy + 2, 32, 3);
                    GUI.color = new Color(0, 0, 0, 0.7f); GUI.DrawTexture(r, Texture2D.whiteTexture);
                    GUI.color = u.Foe ? new Color(0.79f, 0.30f, 0.30f) : new Color(0.42f, 0.60f, 0.74f);
                    GUI.DrawTexture(new Rect(r.x, r.y, r.width * pct, r.height), Texture2D.whiteTexture);
                    GUI.color = Color.white;
                }
                // 이름
                var lab = u.Short ?? u.Name;
                var nr = new Rect(sx - 45, sy + 5, 90, 15);
                GUI.color = new Color(0, 0, 0, u.Alive ? 0.55f : 0.25f);
                GUI.DrawTexture(new Rect(sx - lab.Length * 4 - 3, sy + 6, lab.Length * 8 + 6, 13), Texture2D.whiteTexture);
                GUI.color = Color.white;
                _nm.normal.textColor = u.Foe ? new Color(0.85f, 0.66f, 0.66f)
                                             : new Color(0.82f, 0.84f, 0.86f);
                if (!u.Alive) _nm.normal.textColor *= 0.5f;
                GUI.Label(nr, lab, _nm);

                // 생각
                if (_bubble.TryGetValue(u.Idx, out var th))
                {
                    var br = new Rect(sx - 70, sy - 66, 140, 20);
                    GUI.color = new Color(0.05f, 0.06f, 0.08f, 0.92f);
                    GUI.DrawTexture(br, Texture2D.whiteTexture);
                    GUI.color = Color.white;
                    _bub.normal.textColor = new Color(0.89f, 0.85f, 0.76f);
                    GUI.Label(br, th, _bub);
                }
            }

            // 머리말과 기록
            GUI.color = new Color(0, 0, 0, 0.55f);
            GUI.DrawTexture(new Rect(0, 0, Screen.width, 26), Texture2D.whiteTexture);
            GUI.DrawTexture(new Rect(0, Screen.height - 148, 340, 148), Texture2D.whiteTexture);
            GUI.color = Color.white;
            GUI.Label(new Rect(10, 4, Screen.width - 20, 20),
                $"{Floor.n}층 · {Floor.name}   {B.Goal.Name}   " +
                (B.Done ? (B.Win ? "층을 열었다 — " : "실패 — ") + B.Reason : $"{B.Round}턴"), _hdr);
            for (int i = 0; i < _ticker.Count; i++)
                GUI.Label(new Rect(8, Screen.height - 144 + i * 15, 330, 15), _ticker[i], _nm);

            if (GUI.Button(new Rect(Screen.width - 210, 30, 60, 24), _paused ? "이어서" : "멈춤")) _paused = !_paused;
            if (GUI.Button(new Rect(Screen.width - 144, 30, 60, 24), "빠르게"))
                StepSeconds = StepSeconds > 0.12f ? StepSeconds / 2f : 0.42f;
            if (GUI.Button(new Rect(Screen.width - 78, 30, 68, 24), "다시")) IremBoot.Restart();
        }
    }
}
