// 계산은 Irem.Sim 이 끝냈다. 여기서는 사건 목록을 시간에 맞춰 보여 줄 뿐이다.
// 글자와 판은 BattleHud(uGUI) 가 맡고, 여기서는 세계를 그린다.
using System.Collections;
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
        readonly Dictionary<int, int> _hp = new();
        BattleHud _hud;
        Camera _cam;
        Vector3 _camHome;
        float _shake;
        int _i;
        float _t;

        public bool Paused { get; private set; }
        public int ShownTurn { get; private set; }
        public string SpeedLabel => Mathf.RoundToInt(0.42f / StepSeconds).ToString();
        public ShadeView ViewOf(int idx) => _views.TryGetValue(idx, out var v) ? v : null;
        public int ShownHp(int idx) => _hp.TryGetValue(idx, out var h) ? h : 0;
        public void TogglePause() => Paused = !Paused;
        public void CycleSpeed() => StepSeconds = StepSeconds > 0.12f ? StepSeconds / 2f : 0.42f;

        public Vector3 CellPos(int x, int y)
            => new(x * (float)ArtLoad.FW / ArtLoad.PPU,
                  -y * (float)ArtLoad.FH / ArtLoad.PPU * 0.62f, 0);

        public void Begin(BattleTables t, FloorDef f, Battle b, Camera cam)
        {
            T = t; Floor = f; B = b; _cam = cam;
            foreach (var u in B.Units) _hp[u.Idx] = u.Max;
            BuildField();
            SpawnUnits();
            FrameCamera();
            Atmosphere();
            var hg = new GameObject("Hud");
            hg.transform.SetParent(transform, false);
            _hud = hg.AddComponent<BattleHud>();
            _hud.Build(_cam, B, Floor, this);
        }

        // ── 세계 ─────────────────────────────────────────────────────
        void BuildField()
        {
            var root = new GameObject("Field").transform;
            root.SetParent(transform, false);
            for (int y = 0; y < B.Map.H; y++)
                for (int x = 0; x < B.Map.W; x++)
                {
                    Ground(root, "plain", x, y, -20);
                    char ch = B.Map.At(x, y);
                    if (ch != '.') Ground(root, null, x, y, -10, ch);
                }
        }

        void Ground(Transform root, string forceKind, int x, int y, int order, char ch = '.')
        {
            string name = forceKind != null
                ? forceKind + "_" + (Mathf.Abs(x * 7 + y * 13) % TileVariants)
                : ArtLoad.TileName(ch, x, y, TileVariants);
            var sp = ArtLoad.Tile(name);
            if (sp == null) return;
            var go = new GameObject($"t{x}_{y}");
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

                // 발밑 그림자 — 이것 하나로 땅에 서 있는 것처럼 보인다
                var sh = new GameObject("shadow");
                sh.transform.SetParent(go.transform, false);
                sh.transform.localPosition = new Vector3(0, 0.10f, 0);
                sh.transform.localScale = new Vector3(0.62f, 0.22f, 1);
                var shr = sh.AddComponent<SpriteRenderer>();
                shr.sprite = Shapes.Blob(48, 0.75f);
                shr.color = new Color(0, 0, 0, 0.42f);
                shr.sortingOrder = 99 + u.Y * 2;

                // 진영 고리
                var rg = new GameObject("ring");
                rg.transform.SetParent(go.transform, false);
                rg.transform.localPosition = new Vector3(0, 0.10f, 0);
                rg.transform.localScale = new Vector3(0.78f, 0.30f, 1);
                var rgr = rg.AddComponent<SpriteRenderer>();
                rgr.sprite = Shapes.Blob(48, 0.28f);
                rgr.color = (u.Refugee ? Pal.Ember : u.Foe ? Pal.Bad : Pal.Slate).A(0.30f);
                rgr.sortingOrder = 98 + u.Y * 2;

                var body = new GameObject("body");
                body.transform.SetParent(go.transform, false);
                var sr = body.AddComponent<SpriteRenderer>();
                sr.sortingOrder = 100 + u.Y * 2;
                var v = body.AddComponent<ShadeView>();
                v.Bind(ArtLoad.Sheet(u.Art ?? "unnamed_000", T.nf), T);
                v.Face(!u.Foe);
                go.transform.position = CellPos(u.X, u.Y);
                v.Warp(go.transform.position);
                v.Rig = go.transform;
                _views[u.Idx] = v;
            }
        }

        float _mapW, _mapH, _camY;

        void FrameCamera()
        {
            _mapW = B.Map.W * (float)ArtLoad.FW / ArtLoad.PPU;
            _mapH = B.Map.H * (float)ArtLoad.FH / ArtLoad.PPU * 0.62f;
            _cam.orthographic = true;
            // 지도 전체를 우겨 넣으면 잔상이 점만 해진다. 높이에 맞추고 옆으로 따라간다.
            _cam.orthographicSize = _mapH / 2 + 1.2f;
            _camY = -_mapH / 2 + 1.5f;
            _camHome = new Vector3(Mathf.Clamp(_mapW / 2, HalfW(), _mapW - HalfW()), _camY, -10);
            _cam.transform.position = _camHome;
            _cam.backgroundColor = new Color32(0x14, 0x12, 0x10, 255);
        }
        float HalfW() => _cam.orthographicSize * Mathf.Max(0.1f, _cam.aspect);

        /// 화면은 살아 있는 아군 무리를 따라간다
        void FollowCrowd(float dt)
        {
            var live = B.Units.Where(u => !u.Foe && !u.Refugee && ShownHp(u.Idx) > 0
                                          && _views.ContainsKey(u.Idx)).ToList();
            if (live.Count == 0) return;
            float x = live.Average(u => _views[u.Idx].Rig.position.x);
            float half = HalfW();
            float tx = _mapW <= half * 2 ? _mapW / 2 : Mathf.Clamp(x, half - 1.5f, _mapW - half + 1.5f);
            _camHome = new Vector3(Mathf.Lerp(_camHome.x, tx, 1 - Mathf.Exp(-dt * 2.2f)), _camY, -10);
            if (_shake <= 0) _cam.transform.position = _camHome;
        }

        /// 공기 — 재가 날린다. 화면이 정지 화면처럼 보이지 않게.
        void Atmosphere()
        {
            var go = new GameObject("Ash");
            go.transform.SetParent(transform, false);
            go.transform.position = _camHome + new Vector3(0, _cam.orthographicSize, 5);
            var ps = go.AddComponent<ParticleSystem>();
            var main = ps.main;
            main.startLifetime = 9f;
            main.startSpeed = 0.35f;
            main.startSize = new ParticleSystem.MinMaxCurve(0.05f, 0.14f);
            main.startColor = new ParticleSystem.MinMaxGradient(
                new Color(0.85f, 0.82f, 0.76f, 0.16f), new Color(0.75f, 0.70f, 0.62f, 0.34f));
            main.gravityModifier = 0.012f;
            main.maxParticles = 220;
            main.simulationSpace = ParticleSystemSimulationSpace.World;
            var em = ps.emission; em.rateOverTime = 22;
            var sh = ps.shape;
            sh.shapeType = ParticleSystemShapeType.Box;
            sh.scale = new Vector3(_cam.orthographicSize * _cam.aspect * 2.2f, 0.5f, 1);
            var noise = ps.noise;
            noise.enabled = true; noise.strength = 0.35f; noise.frequency = 0.28f;
            var r = ps.GetComponent<ParticleSystemRenderer>();
            r.material = new Material(Shader.Find("Sprites/Default"));
            r.sortingOrder = 900;
            ps.Play();
        }

        // ── 재생 ─────────────────────────────────────────────────────
        void Update()
        {
            if (B != null) FollowCrowd(Time.deltaTime);
            if (_shake > 0)
            {
                _shake -= Time.deltaTime * 3.4f;
                float k = Mathf.Max(0, _shake);
                _cam.transform.position = _camHome +
                    new Vector3(Mathf.Sin(Time.time * 62f) * k * 0.30f,
                                Mathf.Cos(Time.time * 73f) * k * 0.22f, 0);
                if (_shake <= 0) _cam.transform.position = _camHome;
            }
            if (Paused || B == null) return;
            _t += Time.deltaTime;
            while (_t >= StepSeconds && _i < B.Events.Count)
            {
                _t -= StepSeconds;
                Step(B.Events[_i++]);
                if (_i >= B.Events.Count) _hud.ShowResult();
            }
        }

        void Step(in Irem.Sim.Event e)
        {
            ShadeView V(int i) => i >= 0 && _views.TryGetValue(i, out var v) ? v : null;
            string Nm(int i) => i >= 0 ? (B.Units[i].Short ?? B.Units[i].Name) : "";

            switch (e.K)
            {
                case Ev.Turn:
                    ShownTurn = e.N; break;

                case Ev.Move:
                {
                    var v = V(e.T);
                    if (v != null)
                    {
                        v.MoveRig(CellPos(e.X, e.Y), StepSeconds * 0.8f);
                        v.SetOrder(100 + e.Y * 2);
                    }
                    if (!string.IsNullOrEmpty(e.S)) _hud.Say($"{Nm(e.T)} — {Why(e.S)}");
                    break;
                }
                case Ev.Hit:
                {
                    var av = V(e.A); var tv = V(e.T);
                    if (av != null && tv != null)
                        av.Face(tv.Rig.position.x >= av.Rig.position.x);
                    av?.Play("attack", true);
                    tv?.Play("hurt", true);
                    tv?.Flash(new Color(1f, 0.55f, 0.5f));
                    _hp[e.T] = e.Hp;
                    _hud.Pop(e.T, "-" + e.D, Pal.Bad);
                    _shake = Mathf.Min(1f, _shake + 0.35f);
                    _hud.Say($"{Nm(e.A)} → {Nm(e.T)}  {e.D}");
                    break;
                }
                case Ev.Heal:
                    V(e.A)?.Play("attack", true);
                    _hp[e.T] = e.Hp;
                    _hud.Pop(e.T, "+" + e.D, Pal.Ok);
                    _hud.Say($"{Nm(e.A)} → {Nm(e.T)}  +{e.D}");
                    break;
                case Ev.Env:
                    _hp[e.T] = e.Hp;
                    V(e.T)?.Play("hurt", true);
                    V(e.T)?.Flash(new Color(1f, 0.7f, 0.4f));
                    _hud.Pop(e.T, "-" + e.D, Pal.Ember);
                    _hud.Say($"{Nm(e.T)}  {e.S} -{e.D}");
                    break;
                case Ev.Fall:
                    _hp[e.T] = 0;
                    V(e.T)?.Play("fall", true);
                    _hud.Say($"{Nm(e.T)} 흐려졌다");
                    break;
                case Ev.Think:
                    _hud.Bubble(e.A, e.S);
                    break;
                case Ev.Spot:
                    _hud.Bubble(e.A, "!", 0.9f);
                    break;
                case Ev.Ring:
                    _hud.Say($"종을 쳤다 {e.N}/{B.Goal.N}"); break;
                case Ev.Escape:
                    _hp[e.T] = 0;
                    V(e.T)?.Play("fall", true);
                    _hud.Say($"빠져나갔다 {e.N}/{B.Goal.N}"); break;
            }
        }

        static string Why(string w) => w switch
        {
            "advance" => "앞으로", "retreat" => "물러선다", "guard" => "막아선다",
            "keepdist" => "거리를 둔다", "heal" => "다가간다", "close" => "붙는다",
            "post" => "자리로 돌아간다", _ => "이동",
        };
    }
}
