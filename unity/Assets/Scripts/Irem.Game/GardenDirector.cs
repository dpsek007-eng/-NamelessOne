// 뜰을 보여 준다. 계산은 Garden 이 이미 끝냈고, 여기서는 사건 목록을 시간에 맞춰 재생만 한다
// (BattleDirector 와 같은 구조다 — 그것이 Battle.cs 첫 줄에 적힌 규칙이다).
//
// 세 가지가 전투와 다르다.
//
// 1. 3D 다. 칸 하나가 1m 이고 CellPos(x,y) = (x, 0, -y) 다. 스프라이트가 아니라
//    몸 FBX 를 세우고(CastLoad) ShadeView3D 가 동작을 섞는다. 그리는 순서가 없다 —
//    깊이가 가려 준다.
//
// 2. 한 박자에 사건 하나가 아니라 「한 걸음」을 통째로 재생한다. 뜰은 걸음마다
//    잔상 스물셋이 각자 움직이므로 사건이 수십 개씩 나온다. 사건 하나에 한 박자를
//    주면 한 걸음이 여덟 초가 되어 걷는 것처럼 보이지 않는다.
//
// 3. 끝이 없다. 전투는 사건 목록이 끝나면 결과를 띄우지만, 뜰은 시간이 흐르지 않을 뿐
//    끝나지도 않는다. 재생이 계산을 따라잡으면 Garden.Tick() 을 한 번 더 부른다.
//
// 빛을 세우지 않는다. Irem/Silhouette 셰이더가 제 빛 방향을 갖고 있고(단색 실루엣),
// 땅은 아예 빛을 받지 않는 타일이다. 씬에 광원을 넣으면 실루엣이 깨진다.
using System.Collections.Generic;
using UnityEngine;
using Irem.Data;
using Irem.Sim;

namespace Irem.Game
{
    public sealed class GardenDirector : MonoBehaviour
    {
        public GardenTables T;
        public Garden G;

        /// 한 걸음의 길이. 걷는 동작이 0.34초짜리라(ShadeView3D) 그것에 맞춰 둔 값이다.
        public float StepSeconds = 0.34f;
        public int TileVariants = 5;

        /// 내려보는 각. 정한 값이다 — 잰 값이 아니다. 낮추면 뜰이 넓어 보이고
        /// 올리면 지도처럼 보인다.
        public const float Pitch = 35f;
        const float NearDist = 9f;              // 한 사람을 따라갈 때의 거리

        readonly Dictionary<int, ShadeView3D> _views = new();
        GardenHud _hud;
        Camera _cam;
        Vector3 _home;
        float _wide;
        int _i;                                 // 재생한 사건 수
        float _t;
        int _follow = -1;

        static readonly int ColourId = Shader.PropertyToID("_Colour");
        static readonly int FadeOnId = Shader.PropertyToID("_FadeOn");
        static readonly Color StoneCol = new Color(0.106f, 0.098f, 0.090f, 1f);

        public bool Paused { get; private set; }
        public int ShownTurn { get; private set; }
        public int WorkSteps { get; private set; }
        public int Spoken { get; private set; }
        public string Summary { get; private set; } = "";
        public int Following => _follow;

        public string SpeedLabel => Mathf.RoundToInt(0.34f / Mathf.Max(0.01f, StepSeconds)).ToString();
        public IShadeView ViewOf(int idx) => _views.TryGetValue(idx, out var v) ? v : null;
        public void TogglePause() => Paused = !Paused;
        public void CycleSpeed() => StepSeconds = StepSeconds > 0.10f ? StepSeconds / 2f : 0.34f;
        /// 같은 사람을 다시 누르면 놓는다
        public void Follow(int idx) => _follow = _follow == idx ? -1 : idx;

        /// 칸 하나가 1m. 땅 만드는 법과 같은 자리를 써야 하므로 Ground3D 것을 부른다.
        public static Vector3 CellPos(int x, int y) => Ground3D.Cell(x, y);

        Vector3 Center => new Vector3((T.w - 1) / 2f, 0, -(T.h - 1) / 2f);

        public void Begin(GardenTables t, Garden g, Camera cam)
        {
            T = t; G = g; _cam = cam;
            BuildGround();
            BuildStations();
            SpawnCast();
            FrameCamera();
            var hg = new GameObject("Hud");
            hg.transform.SetParent(transform, false);
            _hud = hg.AddComponent<GardenHud>();
            _hud.Build(_cam, T, G, this);
        }

        // ── 땅 ───────────────────────────────────────────────────────
        char At(int x, int y)
        {
            if (T.map == null || y < 0 || y >= T.map.Length) return '.';
            var row = T.map[y];
            return x < 0 || x >= row.Length ? '.' : row[x];
        }

        /// 땅은 Ground3D 가 깐다 — 전투 층도 같은 것을 쓴다.
        void BuildGround() => Ground3D.Build(transform, T.w, T.h, At, TileVariants);

        // ── 일터 ─────────────────────────────────────────────────────
        /// 일터 열넷에 소품을 세운다. 건물을 새로 모델링하지 않는다 —
        /// pipeline3d 가 구운 FBX 를 그대로 쓴다.
        ///
        /// 소품이 어느 쪽을 보고 구워졌는지는 유니티에서 열어 봐야 안다.
        /// 그래서 지금은 전부 뜰 가운데를 보게 돌려 둔다. 열어 보고 어긋나면 그때 잰다.
        void BuildStations()
        {
            var root = new GameObject("일터").transform;
            root.SetParent(transform, false);
            if (T.stations == null) return;

            foreach (var s in T.stations)
            {
                var fbx = CastLoad.Prop(s.prop);
                if (fbx == null) continue;        // 소품이 없으면 이름표만 남는다(GardenHud)
                var go = Instantiate(fbx, root);
                go.name = s.name;
                var p = CellPos(s.x, s.y);
                go.transform.position = p;
                var d = Center - p; d.y = 0;
                if (d.sqrMagnitude > 0.01f) go.transform.rotation = Quaternion.LookRotation(d);
                Stone(go);
            }
        }

        /// 소품도 잔상과 같은 실루엣으로 칠한다. 다만 발밑 흐려짐은 끈다 —
        /// 흐려지는 것은 사람이고, 건물은 거기 그냥 있다.
        void Stone(GameObject go)
        {
            var sil = CastLoad.Silhouette;
            if (sil == null) return;
            IremChar.Skin(go, sil);
            var mpb = new MaterialPropertyBlock();
            mpb.SetColor(ColourId, StoneCol);
            mpb.SetFloat(FadeOnId, 0f);
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
                r.SetPropertyBlock(mpb);
        }

        // ── 잔상 ─────────────────────────────────────────────────────
        void SpawnCast()
        {
            var root = new GameObject("잔상").transform;
            root.SetParent(transform, false);
            foreach (var s in G.Cast)
            {
                var go = CastLoad.Build(s.Def, root);
                if (go == null) continue;
                // 발밑 그림자. 이것 하나로 땅에 서 있는 것처럼 보인다 —
                // 뜰에는 진영이 없으므로 고리는 깔지 않는다.
                Ground3D.Decal(go.transform, "shadow", Shapes.Blob(48, 0.75f),
                               new Color(0, 0, 0, 0.42f), 0.66f, 0.02f);

                var v = go.GetComponent<ShadeView3D>();
                v.Breathe(s.Phase, s.Tempo, s.Breath);   // 저마다 다른 박자로 숨을 쉰다
                v.Warp(CellPos(s.X, s.Y));
                v.FaceTo(Center);
                _views[s.Idx] = v;
            }
            if (_views.Count != G.Cast.Count)
                Debug.LogWarning($"[이렘] 뜰에 세운 잔상 {_views.Count}명 / {G.Cast.Count}명. "
                               + "몸 FBX 를 못 읽은 잔상이 있다.");
        }

        // ── 카메라 ───────────────────────────────────────────────────
        void FrameCamera()
        {
            _cam.orthographic = false;
            _cam.fieldOfView = 42f;
            _cam.nearClipPlane = 0.3f;
            _cam.farClipPlane = 260f;
            _cam.backgroundColor = new Color32(0x14, 0x12, 0x10, 255);
            _cam.transform.rotation = Quaternion.Euler(Pitch, 0, 0);
            _wide = WholeGarden();
            _home = Eye(Center, _wide);
            _cam.transform.position = _home;
        }

        Vector3 Eye(Vector3 look, float d) => look - _cam.transform.forward * d;

        /// 뜰 전체가 들어가는 거리. 가로는 화면의 가로 반각으로, 세로는
        /// 내려보는 각만큼 누운 깊이로 잰다.
        float WholeGarden()
        {
            float vr = Mathf.Tan(_cam.fieldOfView * 0.5f * Mathf.Deg2Rad);
            float hr = vr * Mathf.Max(0.5f, _cam.aspect);
            float dw = (T.w * 0.5f + 1.5f) / Mathf.Max(0.05f, hr);
            float dh = (T.h * 0.5f * Mathf.Cos(Pitch * Mathf.Deg2Rad) + 1.5f) / Mathf.Max(0.05f, vr);
            return Mathf.Max(dw, dh);
        }

        void Steer(float dt)
        {
            if (_cam == null || T == null) return;
            var look = Center; float d = _wide;
            if (_follow >= 0 && _views.TryGetValue(_follow, out var v) && v != null)
            {
                look = v.Pos + Vector3.up * 0.9f;
                d = NearDist;
            }
            var want = Eye(look, d);
            _cam.transform.position = Vector3.Lerp(_cam.transform.position, want,
                                                   1 - Mathf.Exp(-dt * 2.4f));
        }

        // ── 재생 ─────────────────────────────────────────────────────
        void Update()
        {
            float dt = Time.deltaTime;
            Steer(dt);
            if (Paused || G == null) return;
            _t += dt;
            int guard = 0;
            while (_t >= StepSeconds && guard++ < 8)
            {
                _t -= StepSeconds;
                PlayStep();
            }
        }

        /// 한 걸음을 통째로 재생한다. 다음 Gv.Turn 이 나오면 거기서 멈춘다 —
        /// 그 다음 걸음은 다음 박자의 몫이다.
        ///
        /// 밖에서도 부를 수 있게 열어 둔다. 재생을 누르지 않으면 Update 가 돌지 않으므로
        /// 자체 점검(IremSelfTest)이 이것을 직접 불러 한 걸음씩 굴려 본다.
        public void PlayStep()
        {
            if (_i >= G.Log.Count) { G.Tick(); Trim(); }
            int guard = 0;
            while (_i < G.Log.Count && guard < 4096)
            {
                var e = G.Log[_i];
                if (e.K == Gv.Turn && guard > 0) break;
                _i++; guard++;
                Step(e);
            }
        }

        /// 뜰은 끝이 없다. 재생한 사건을 버리지 않으면 목록이 한없이 자란다.
        /// Garden 은 Log 에 덧붙이기만 하므로 앞을 잘라도 뒤가 어긋나지 않는다.
        void Trim()
        {
            if (_i < 4096) return;
            G.Log.RemoveRange(0, _i);
            _i = 0;
        }

        void Step(in GardenEvent e)
        {
            ShadeView3D V(int i) => i >= 0 && _views.TryGetValue(i, out var v) ? v : null;
            string Nm(int i) => i >= 0 && i < G.Cast.Count ? G.Cast[i].Name : "";

            switch (e.K)
            {
                case Gv.Turn:
                    ShownTurn = e.N;
                    break;

                case Gv.Walk:
                    V(e.A)?.MoveRig(CellPos(e.X, e.Y), StepSeconds * 0.85f);
                    break;

                case Gv.Work:
                    // 손이 하던 일을 한다. 「휘두름」이 그 몸짓이다 —
                    // 종을 치고 쇠를 두드리고 빵을 넣는 것이 다 그 하나의 동작이다.
                    WorkSteps++;
                    // 밀어붙이지 않는다 — 휘두르는 중이면 그냥 둔다(ShadeView3D.Play).
                    V(e.A)?.Play("attack");
                    break;

                case Gv.Rest:
                case Gv.Stand:
                    // 앉는 동작이 없다(동작은 여섯 벌뿐이다). 숨만 쉬게 둔다.
                    V(e.A)?.Play("idle");
                    break;

                case Gv.Meet:
                {
                    var a = V(e.A); var b = V(e.T);
                    if (a != null && b != null) { a.FaceTo(b.Pos); b.FaceTo(a.Pos); }
                    a?.Play("look", true);
                    _hud?.Say($"{Nm(e.A)} ↔ {Nm(e.T)} — {Why(e.S)}");
                    break;
                }
                case Gv.Avoid:
                    V(e.A)?.Play("look", true);
                    _hud?.Say($"{Nm(e.A)} — {Nm(e.T)}를 피한다");
                    break;

                case Gv.Say:
                    _hud?.Bubble(e.A, e.S);
                    break;

                case Gv.Think:
                    _hud?.Bubble(e.A, e.S, 1.6f);
                    break;

                case Gv.Bond:
                    if (e.A < 0)
                    {
                        // 구역을 다시 잰 결과. 성립·발동·대기 수가 여기 들어 있다.
                        Summary = e.S ?? "";
                        _hud?.Say(Summary);
                        _hud?.ShowBonds();
                    }
                    else
                    {
                        Spoken++;
                        _hud?.Say($"{Nm(e.A)} ↔ {Nm(e.T)} — {e.S}");
                        _hud?.Bubble(e.T, e.S, 3.2f);
                    }
                    break;
            }
        }

        /// 왜 마주 섰는가. Garden 이 넘긴 낱말을 그대로 옮긴다.
        static string Why(string w) => w switch
        {
            "meet" => "마주 섰다", "miss" => "그리워서 다가갔다", _ => "마주 섰다",
        };
    }
}
