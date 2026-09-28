// 뜰을 보여 준다. 계산은 Garden 이 이미 끝냈고, 여기서는 사건 목록을 시간에 맞춰 재생만 한다
// (BattleDirector 와 같은 구조다 — 그것이 Battle.cs 첫 줄에 적힌 규칙이다).
//
// 세 가지가 전투와 다르다.
//
// 1. 3D 다. 칸 하나가 1m 이고 CellPos(x,y) = (x, 그 칸의 높이, -y) 다. 스프라이트가 아니라
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

        /// 한 걸음의 길이. 0.34초면 한 칸(1m)을 2.94 m/s 로 지나간다 — 그건 걷기가
        /// 아니라 달리기다. 실측(브라우저, tools/probe.py --stride): 걸음폭 0.786~0.882m 에
        /// 한 바퀴 1.375초라 다리는 1.14~1.28 m/s 를 낸다. 그 가운데에 맞춘 값이다.
        public float StepSeconds = 0.82f;

        /// 한 칸을 건너는 데 쓰는 몫. 1 이면 다음 걸음이 올 때까지 쉬지 않고 건넌다.
        /// 0.85 였다. 그러면 0.82초 중 0.70초만 몸이 가고 0.12초는 제자리에 선 채
        /// 다리만 돌았다 — 매 칸 15%. 걸음이 칸마다 한 번씩 걸렸다.
        /// viewer/garden.html 의 WALK_FRAC 과 같은 값이어야 한다.
        public const float WalkFrac = 1f;
        public int TileVariants = 5;

        /// 내려보는 각. 정한 값이다 — 잰 값이 아니다. 낮추면 뜰이 넓어 보이고
        /// 올리면 지도처럼 보인다.
        public const float Pitch = 35f;
        const float NearDist = 9f;              // 한 사람을 따라갈 때의 거리

        readonly Dictionary<int, ShadeView3D> _views = new();
        readonly Dictionary<char, float> _th = new();      // 지형 문자 → 바닥 높이(m)
        readonly Dictionary<string, Vector3> _work = new();// 일터 이름 → 연장이 놓인 자리
        readonly Dictionary<string, float> _top = new();   // 일터 이름 → 그 채의 꼭대기
        float _tall;                                       // 가장 높은 구조물의 꼭대기
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

        public const float Step0 = 0.82f;
        public string SpeedLabel => Mathf.RoundToInt(Step0 / Mathf.Max(0.01f, StepSeconds)).ToString();
        public IShadeView ViewOf(int idx) => _views.TryGetValue(idx, out var v) ? v : null;
        public void TogglePause() => Paused = !Paused;
        public void CycleSpeed() => StepSeconds = StepSeconds > 0.15f ? StepSeconds / 2f : Step0;
        /// 같은 사람을 다시 누르면 놓는다
        public void Follow(int idx) => _follow = _follow == idx ? -1 : idx;

        /// 그 칸의 바닥 높이(m). 지형 표에서 온다 — 여기서 정하지 않는다.
        /// 이것이 없어서 담도 언덕도 우물물도 바닥에 그린 무늬였다.
        public float HAt(int x, int y) => _th.TryGetValue(At(x, y), out var v) ? v : 0f;

        /// 칸 하나가 1m. 땅 만드는 법과 같은 자리를 써야 하므로 Ground3D 것을 부른다.
        public Vector3 CellPos(int x, int y) => Ground3D.Cell(x, y, HAt(x, y));

        /// 그 일터 이름표를 띄울 자리. 구조물 꼭대기보다 조금 위다.
        public Vector3 MarkAt(StationDef s) =>
            new Vector3(s.x, (_top.TryGetValue(s.name, out var t) ? t : s.z0) + 0.55f, -s.y);

        /// 그 일터에서 연장이 놓인 자리. 일하는 사람이 이쪽을 보고 휘두른다.
        public bool WorkAt(string place, out Vector3 p) => _work.TryGetValue(place, out p);

        Vector3 Center => new Vector3((T.w - 1) / 2f, 0, -(T.h - 1) / 2f);

        public void Begin(GardenTables t, Garden g, Camera cam)
        {
            T = t; G = g; _cam = cam;
            _th.Clear();
            foreach (var d in T.terrain ?? new TerrDef[0])
                if (!string.IsNullOrEmpty(d.ch)) _th[d.ch[0]] = d.h;
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
        void BuildGround() => Ground3D.Build(transform, T.w, T.h, At, TileVariants, "땅", HAt);

        // ── 일터 ─────────────────────────────────────────────────────
        /// 일터 열넷에 「서 있는 것」을 세운다.
        ///
        /// 전에는 소품 FBX 하나만 칸 한가운데에 놓았다. 그런데 그 소품은 건물이 아니라
        /// 연장이다 — 실측 0.08~1.15m 짜리 유품이고, 등대는 8cm 다(tools/make_garden.py:56 도
        /// 「건물이 아니다」라고 적어 두었다). 그래서 뜰에는 서 있는 것이 없었고,
        /// 일하는 사람은 허공에 헛손질을 했다.
        ///
        /// 이제 구조물은 tools/places.py 가 적은 덩이 목록에서 나오고(Village),
        /// 소품은 그 구조물의 작업대 위, 손이 지나는 자리에 제 크기대로 얹힌다.
        void BuildStations()
        {
            var root = new GameObject("일터").transform;
            root.SetParent(transform, false);
            _work.Clear(); _top.Clear(); _tall = 0f;
            if (T.stations == null) return;

            foreach (var s in T.stations)
            {
                float top = Village.Build(root, s, CastLoad.Silhouette);
                _top[s.name] = top;
                if (top > _tall) _tall = top;

                var wp = Village.WorkAt(s);
                _work[s.name] = wp;

                var fbx = CastLoad.Prop(s.prop);
                if (fbx == null) continue;        // 소품이 없으면 구조물과 이름표만 남는다
                var go = Instantiate(fbx, root);
                go.name = s.name + ":연장";
                go.transform.position = wp;
                go.transform.rotation = Village.FaceBack(s);
                go.transform.localScale = Vector3.one * ToolScale(go);
                Stone(go);
            }
        }

        /// 연장의 크기. 숫자를 정해 두지 않는다 — 그 FBX 의 실제 크기에서 나온다.
        /// 소품 마흔일곱이 0.08m 부터 1.15m 까지 제각각이라 그대로 두면 하나는 티끌이고
        /// 하나는 사람만 하다. 손에 들 만한 크기 하나로 맞춘다.
        const float ToolSize = 0.42f;
        static float ToolScale(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>(true);
            if (rs.Length == 0) return 1f;
            var b = rs[0].bounds;
            for (int i = 1; i < rs.Length; i++) b.Encapsulate(rs[i].bounds);
            float m = Mathf.Max(b.size.x, Mathf.Max(b.size.y, b.size.z));
            return m > 1e-4f ? ToolSize / m : 1f;
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
                v.StepSeconds = StepSeconds;             // 다리를 땅 속도에 맞추는 데 쓴다
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
            // 구조물이 8m 넘게 선다(종탑·등대). 땅만 재면 꼭대기가 잘린다.
            float dh = (T.h * 0.5f * Mathf.Cos(Pitch * Mathf.Deg2Rad)
                      + _tall * 0.5f * Mathf.Sin(Pitch * Mathf.Deg2Rad) + 1.5f)
                     / Mathf.Max(0.05f, vr);
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
            // 빠르게 보기를 누르면 땅이 빨라진다. 다리도 같이 빨라져야 안 미끄러진다.
            foreach (var sv in _views.Values) if (sv != null) sv.StepSeconds = StepSeconds;
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
                    V(e.A)?.MoveRig(CellPos(e.X, e.Y), StepSeconds * WalkFrac);
                    break;

                case Gv.Work:
                {
                    // 손이 하던 일을 한다. 「휘두름」이 그 몸짓이다 —
                    // 종을 치고 쇠를 두드리고 빵을 넣는 것이 다 그 하나의 동작이다.
                    WorkSteps++;
                    var v = V(e.A);
                    if (v == null) break;
                    // 휘두르기 전에 연장 쪽으로 돈다. 이것이 없으면 허공을 친다.
                    if (e.S != null && _work.TryGetValue(e.S, out var wp)) v.FaceTo(wp);
                    // 밀어붙이지 않는다 — 휘두르는 중이면 그냥 둔다(ShadeView3D.Play).
                    v.Play("attack");
                    break;
                }

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
