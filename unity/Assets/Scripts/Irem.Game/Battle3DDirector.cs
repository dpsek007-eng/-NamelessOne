// 전투 층을 3D 로 보여 준다. 계산은 Battle 이 이미 끝냈고 여기서는 같은 사건 목록을
// 시간에 맞춰 재생만 한다 — 2D BattleDirector 와 같은 사건, 같은 순서, 같은 결과다.
//
// Battle.cs · Mind.cs · Setup.cs 는 한 줄도 건드리지 않았다. 2D BattleDirector 도 그대로
// 남아 있다. 2D 가 지금 도는 게임이고, 실루엣 판정 도구이기도 하다.
//
// 세 가지가 2D 와 다르다.
//
// 1. 칸 하나가 1m 다. Ground3D.Cell(x,y) = (x,0,-y) 이므로 24×8 판이 24m×8m 다.
//    2D 는 칸을 48×64 픽셀에 0.62 를 곱한 크기로 쓴다(ArtLoad) — 그 비율은 스프라이트
//    때문이고 3D 에는 이유가 없다. 지형 그림은 2D 가 쓰는 것을 그대로 쓴다.
//
// 2. 몸이 스프라이트가 아니라 FBX 다. 그래서 몸·옷 슬러그가 필요한데 Unit 에도
//    CharDef 에도 없다. 역할→몸, (역할,계층)→옷 규칙은 tools/export_unity.py 에 있고
//    그 결과가 garden.json 의 AgentDef 다. 규칙을 C# 에 다시 적지 않고(docs/10),
//    garden.json 을 가져와 id 로 찾는다. 아래 AgentFor() 가 그 일이고, 못 찾을 때
//    무엇으로 대신하는지 거기 적어 두었다.
//
// 3. 그리는 순서가 없다. 깊이가 가려 준다. SetOrder 는 3D 에서 할 일이 없다.
//
// 빛을 세우지 않는다 — GardenDirector 와 같은 이유다(Irem/Silhouette 가 제 빛을 갖고 있다).
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Irem.Data;
using Irem.Sim;

namespace Irem.Game
{
    public sealed class Battle3DDirector : MonoBehaviour, IBattleStage
    {
        public BattleTables T;
        public GardenTables Cast;        // 몸·옷 슬러그가 여기에만 있다
        public FloorDef Floor;
        public Battle B;
        public float StepSeconds = 0.42f;
        public int TileVariants = 5;

        /// 내려보는 각. 뜰(35°)보다 낮게 둔다 — 전투는 줄이 보여야 하고,
        /// 여덟 줄뿐이라 높이 올리면 지도가 된다. 정한 값이다 — 잰 값이 아니다.
        public const float Pitch = 26f;
        /// 한 화면에 넣는 가로 칸 수. 판 전체(24칸)를 우겨 넣으면 잔상이 점만 해진다 —
        /// 2D 가 높이에 맞추고 옆으로 따라가는 것과 같은 판단이다.
        const float Window = 15f;

        readonly Dictionary<int, ShadeView3D> _views = new();
        readonly Dictionary<int, int> _hp = new();
        BattleHud _hud;
        Camera _cam;
        Vector3 _camHome;
        float _shake;
        float _dist, _camZx;             // 눈 거리 · 바라보는 자리의 z
        float _mapW, _mapH;
        int _i;
        float _t;

        public bool Paused { get; private set; }
        public int ShownTurn { get; private set; }
        public string SpeedLabel => Mathf.RoundToInt(0.42f / Mathf.Max(0.01f, StepSeconds)).ToString();
        public float TagLift => 1.78f;   // 발밑이 몸의 자리다. 머리 위로 올린다.
        public IShadeView ViewOf(int idx) => _views.TryGetValue(idx, out var v) ? v : null;
        public int ShownHp(int idx) => _hp.TryGetValue(idx, out var h) ? h : 0;
        public void TogglePause() => Paused = !Paused;
        public void CycleSpeed() => StepSeconds = StepSeconds > 0.12f ? StepSeconds / 2f : 0.42f;

        public static Vector3 CellPos(int x, int y) => Ground3D.Cell(x, y);

        public void Begin(BattleTables t, GardenTables cast, FloorDef f, Battle b, Camera cam)
        {
            T = t; Cast = cast; Floor = f; B = b; _cam = cam;
            foreach (var u in B.Units) _hp[u.Idx] = u.Max;
            _mapW = B.Map.W; _mapH = B.Map.H;
            Ground3D.Build(transform, B.Map.W, B.Map.H, B.Map.At, TileVariants, "땅");
            SpawnUnits();
            FrameCamera();
            Atmosphere();
            var hg = new GameObject("Hud");
            hg.transform.SetParent(transform, false);
            _hud = hg.AddComponent<BattleHud>();
            _hud.Build(_cam, B, Floor, this);
        }

        // ── 몸 ───────────────────────────────────────────────────────
        /// 이 유닛의 몸·옷을 어디서 가져오는가.
        ///
        ///   1. garden.json 에 같은 id 가 있으면 그것. 이름 있는 잔상은 여기서 맞는다.
        ///   2. 없으면 같은 역할의 첫 잔상. 저항(적)과 미상(피난민)은 id 가
        ///      foe_* · ref0..3 이라 1번으로 못 찾는다. 다섯 역할이 garden.json 에
        ///      다 있으므로 여기서는 언제나 맞는다 — 다만 남의 몸을 빌려 쓰는 것이다.
        ///      빌린 몸이라는 점은 색으로 구분한다(진영색으로 다시 칠한다).
        ///   3. 그것도 없으면 세우지 않는다. 없는 몸을 만들어 내지 않는다.
        AgentDef AgentFor(Unit u)
        {
            var a = Cast?.Agent(u.Art);
            if (a != null) return a;
            if (Cast?.agents == null) return null;
            foreach (var x in Cast.agents) if (x.role == u.Role) return x;
            return null;
        }

        void SpawnUnits()
        {
            var root = new GameObject("잔상").transform;
            root.SetParent(transform, false);
            int miss = 0;
            foreach (var u in B.Units)
            {
                var def = AgentFor(u);
                if (def == null) { miss++; continue; }
                var go = CastLoad.Build(def, root);
                if (go == null) { miss++; continue; }
                go.name = u.Name ?? u.Art;

                // 빌린 몸이면 진영색으로 다시 칠한다. 적이 아군과 같은 색이면 누가 누군지 모른다.
                if (u.Foe || u.Refugee)
                {
                    var ch = go.GetComponent<IremChar>();
                    if (ch != null)
                    {
                        ch.accent = u.Foe ? Pal.Bad : Pal.Ember;
                        ch.Repaint();
                    }
                }

                // 발밑 그림자와 진영 고리 — 2D 가 스프라이트로 깔던 것을 눕혔다
                Ground3D.Decal(go.transform, "shadow", Shapes.Blob(48, 0.75f),
                               new Color(0, 0, 0, 0.42f), 0.66f, 0.02f);
                Ground3D.Decal(go.transform, "ring", Shapes.Blob(48, 0.28f),
                               (u.Refugee ? Pal.Ember : u.Foe ? Pal.Bad : Pal.Slate).A(0.34f),
                               0.86f, 0.01f);

                var v = go.GetComponent<ShadeView3D>();
                v.Warp(CellPos(u.X, u.Y));
                v.Face(!u.Foe);              // 적은 왼쪽을, 아군은 오른쪽을 본다
                _views[u.Idx] = v;
            }
            if (miss > 0)
                Debug.LogWarning($"[이렘] 3D 전투에서 {miss}명의 몸을 못 세웠다. "
                               + "garden.json 을 넘겼는지, 몸 FBX 가 들어왔는지 확인할 것.");
        }

        // ── 카메라 ───────────────────────────────────────────────────
        /// 세로(여덟 줄)는 전부 넣고, 가로는 Window 칸만 넣고 무리를 따라간다.
        void FrameCamera()
        {
            _cam.orthographic = false;
            _cam.fieldOfView = 40f;
            _cam.nearClipPlane = 0.3f;
            _cam.farClipPlane = 260f;
            _cam.backgroundColor = new Color32(0x14, 0x12, 0x10, 255);
            _cam.transform.rotation = Quaternion.Euler(Pitch, 0, 0);

            float vr = Mathf.Tan(_cam.fieldOfView * 0.5f * Mathf.Deg2Rad);
            float hr = vr * Mathf.Max(0.5f, _cam.aspect);
            float dh = (_mapH * 0.5f * Mathf.Cos(Pitch * Mathf.Deg2Rad) + 2.0f)
                     / Mathf.Max(0.05f, vr);
            float dw = (Mathf.Min(Window, _mapW) * 0.5f + 1.0f) / Mathf.Max(0.05f, hr);
            _dist = Mathf.Max(dh, dw);
            _camZx = -(_mapH - 1) / 2f;                  // 바라보는 자리의 z
            _camHome = Eye(new Vector3(ClampX(_mapW / 2f), 0, _camZx));
            _cam.transform.position = _camHome;
        }

        Vector3 Eye(Vector3 look) => look - _cam.transform.forward * _dist;

        /// 바라보는 자리에서 보이는 가로 반폭. 땅이 기울어 있으므로 깊이마다 다르다 —
        /// 바라보는 자리에서 잰 값이고, 판 끝을 정확히 맞추는 값이 아니다.
        float HalfW()
            => _dist * Mathf.Tan(_cam.fieldOfView * 0.5f * Mathf.Deg2Rad)
                     * Mathf.Max(0.5f, _cam.aspect);

        float ClampX(float x)
        {
            float half = HalfW();
            return _mapW <= half * 2 ? (_mapW - 1) / 2f
                                     : Mathf.Clamp(x, half - 1.5f, _mapW - half + 1.5f);
        }

        /// 화면은 살아 있는 아군 무리를 따라간다 — 2D 와 같은 규칙이다.
        void FollowCrowd(float dt)
        {
            var live = B.Units.Where(u => !u.Foe && !u.Refugee && ShownHp(u.Idx) > 0
                                          && _views.ContainsKey(u.Idx)).ToList();
            if (live.Count == 0) return;
            float x = ClampX((float)live.Average(u => (double)_views[u.Idx].Pos.x));
            var look = new Vector3(Mathf.Lerp(LookX(), x, 1 - Mathf.Exp(-dt * 2.2f)), 0, _camZx);
            _camHome = Eye(look);
            if (_shake <= 0) _cam.transform.position = _camHome;
        }
        float LookX() => (_camHome + _cam.transform.forward * _dist).x;

        /// 공기 — 재가 날린다. 화면이 정지 화면처럼 보이지 않게(2D 와 같은 것을 눕혔다).
        void Atmosphere()
        {
            var go = new GameObject("Ash");
            go.transform.SetParent(transform, false);
            go.transform.position = new Vector3(_mapW / 2f, 7f, _camZx);
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
            sh.scale = new Vector3(_mapW + 6f, 0.5f, _mapH + 6f);
            var noise = ps.noise;
            noise.enabled = true; noise.strength = 0.35f; noise.frequency = 0.28f;
            var r = ps.GetComponent<ParticleSystemRenderer>();
            r.material = new Material(Shader.Find("Sprites/Default"));
            ps.Play();
        }

        // ── 재생 ─────────────────────────────────────────────────────
        void Update()
        {
            float dt = Time.deltaTime;
            if (B != null) FollowCrowd(dt);
            if (_shake > 0)
            {
                _shake -= dt * 3.4f;
                float k = Mathf.Max(0, _shake);
                // 흔들림은 화면 기준이다 — 카메라의 오른쪽·위로 흔든다(2D 는 x·y 였다)
                _cam.transform.position = _camHome
                    + _cam.transform.right * (Mathf.Sin(Time.time * 62f) * k * 0.30f)
                    + _cam.transform.up * (Mathf.Cos(Time.time * 73f) * k * 0.22f);
                if (_shake <= 0) _cam.transform.position = _camHome;
            }
            if (Paused || B == null) return;
            _t += dt;
            while (_t >= StepSeconds && _i < B.Events.Count)
            {
                _t -= StepSeconds;
                Step(B.Events[_i++]);
                if (_i >= B.Events.Count) _hud.ShowResult();
            }
        }

        /// 2D BattleDirector.Step 과 같은 표다. 다른 것은 세 줄뿐이다 —
        /// 자리를 3D 로 잡고, 돌아서는 것을 좌우 반전이 아니라 회전으로 하고,
        /// 그리는 순서를 건드리지 않는다.
        void Step(in Irem.Sim.Event e)
        {
            ShadeView3D V(int i) => i >= 0 && _views.TryGetValue(i, out var v) ? v : null;
            string Nm(int i) => i >= 0 ? (B.Units[i].Short ?? B.Units[i].Name) : "";

            switch (e.K)
            {
                case Ev.Turn:
                    ShownTurn = e.N; break;

                case Ev.Move:
                {
                    V(e.T)?.MoveRig(CellPos(e.X, e.Y), StepSeconds * 0.8f);
                    if (!string.IsNullOrEmpty(e.S)) _hud.Say($"{Nm(e.T)} — {Why(e.S)}");
                    break;
                }
                case Ev.Hit:
                {
                    var av = V(e.A); var tv = V(e.T);
                    if (av != null && tv != null) av.FaceTo(tv.Pos);
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
                {
                    var av = V(e.A); var tv = V(e.T);
                    if (av != null && tv != null) av.FaceTo(tv.Pos);
                    av?.Play("attack", true);
                    _hp[e.T] = e.Hp;
                    _hud.Pop(e.T, "+" + e.D, Pal.Ok);
                    _hud.Say($"{Nm(e.A)} → {Nm(e.T)}  +{e.D}");
                    break;
                }
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
                    V(e.A)?.Play("look", true);      // 3D 에는 「돌아본다」가 있다
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

        /// 2D 와 같은 표다. 여기서 낱말을 바꾸면 같은 사건이 두 화면에서 다른 말로 나온다.
        static string Why(string w) => w switch
        {
            "advance" => "앞으로", "retreat" => "물러선다", "guard" => "막아선다",
            "keepdist" => "거리를 둔다", "heal" => "다가간다", "close" => "붙는다",
            "post" => "자리로 돌아간다", _ => "이동",
        };
    }
}
