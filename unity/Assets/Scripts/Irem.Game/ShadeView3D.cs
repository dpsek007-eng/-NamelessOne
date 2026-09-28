// 3D 몸 하나. 동작 여섯 벌을 코드에서 섞는다.
//
// AnimatorController 자산을 만들지 않는다. 손으로 못 읽는 .controller 바이너리를
// 저장소에 넣지 않으려는 것이고(IremFont 가 폰트를, IremCharScene 이 신을
// 코드에서 짓는 것과 같은 판단이다), 무엇보다 섞는 규칙이 코드에 적혀 있어야
// 「왜 이 동작이 저 동작으로 넘어가는가」를 읽을 수 있다.
//
// 대신 UnityEngine.Playables 로 믹서 하나를 세운다. 입력 두 칸뿐이다 —
// 지금 하던 동작과 새로 시작한 동작. 0.25초에 걸쳐 무게를 옮긴다
// (viewer/index.html 이 쓰는 크로스페이드와 같은 값이다).
//
// 2D 와 다른 것이 하나 있다. 좌우 반전이 아니라 Y축으로 돈다. 3D 라서 그렇다.
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

namespace Irem.Game
{
    [RequireComponent(typeof(Animator))]
    public sealed class ShadeView3D : MonoBehaviour, IShadeView
    {
        public const float Fade = 0.25f;      // 크로스페이드 시간
        public float TurnSpeed = 11f;         // 돌아서는 빠르기 (도/초의 비례상수)

        Animator _anim;
        IremChar _char;
        PlayableGraph _graph;
        AnimationMixerPlayable _mix;
        AnimationClipPlayable _from, _to;
        readonly Dictionary<string, AnimationClip> _clips = new();

        string _name = "idle";
        float _fade = 1f;                     // 1 = 새 동작으로 다 넘어갔다
        float _hold;                          // 한 번만 하는 동작이 끝날 때까지
        float _rest;                          // 그 동작이 끝난 뒤 숨 돌리는 참
        bool _dead;

        // 몸의 박자. GardenShade 가 소금에서 낸 값을 받아 쓴다(GardenSetup).
        // 여기서 따로 굴리지 않는다 — 브라우저 쪽도 같은 값을 받으므로,
        // 공식이 두 벌이 되면 같은 뜰이 두 가지로 움직인다(docs/10 계산 한 벌).
        float _phase = 0f, _tempo = 1f, _breath = 0f;

        // 걸음폭 — 발이 몸 기준으로 앞뒤로 오간 길이(m). 한 바퀴에 그 두 배만큼
        // 땅이 지나가야 디딘 발이 제자리에 선다. 0 이면 아직 못 쟀다는 뜻이고
        // 그때는 제 박자를 그대로 쓴다. viewer/garden.html measureStride 와 같은 계산이다.
        float _stride, _speed;

        // 그 사람만의 자세. 클립이 뼈를 다 쓴 뒤에 얹는 층이다 (CastLoad.Stance 가 만든다).
        Stand[] _stand;

        /// 한 뼈에 얹을 몫. 회전은 이미 뼈 축으로 옮겨 놓은 사원수다 —
        /// 축을 옮기는 계산은 CastLoad 에서 한 번만 하고 여기서는 곱하기만 한다.
        public struct Stand
        {
            public Transform bone;
            public Quaternion q;            // 안 걸면 hasQ = false
            public Vector3 scale;
            public bool hasQ, hasScale;
        }

        Vector3 _target;
        float _moveLeft;
        float _yaw = 0f, _yawWant = 0f;
        Color _paint = Color.white;
        float _flash;

        public string Clip => _name;
        public bool Facing { get; private set; } = true;
        public Vector3 Pos => transform.position;

        /// 저마다 다른 박자를 준다. Bind 뒤에, 첫 동작을 걸기 전에 부른다.
        /// 이것이 없으면 스물셋이 같은 프레임에서 같은 속도로 숨을 쉰다.
        public void Breathe(float phase, float tempo, float breath)
        {
            _phase = phase; _tempo = Mathf.Max(0.1f, tempo); _breath = Mathf.Max(0f, breath);
            if (_to.IsValid())
            {
                // 걷기만은 제 박자가 아니라 땅의 속도를 따른다. 박자를 지키면 발이 미끄러진다.
            _to.SetSpeed(clip == "walk" ? WalkScale() : _tempo);
                if (Loops(_name)) _to.SetTime(_phase * _to.GetAnimationClip().length);
            }
        }

        /// 자세를 건다. Bind 뒤에 부른다. 목록이 비면 아무것도 안 얹는다.
        public void Stance(Stand[] stand) => _stand = stand;

        /// 자세가 걸린 뼈 수. 재려고 낸다 (IremSelfTest).
        public int StanceBones => _stand?.Length ?? 0;

        /// 몸을 세운 뒤 한 번 부른다. clips 는 동작 FBX 에서 읽은 것 (CastLoad).
        public void Bind(IEnumerable<AnimationClip> clips)
        {
            _anim = GetComponent<Animator>();
            _char = GetComponent<IremChar>();
            _anim.runtimeAnimatorController = null;      // 컨트롤러 없이 Playables 로만 돈다
            _anim.applyRootMotion = false;               // 자리는 연출자가 정한다
            _anim.cullingMode = AnimatorCullingMode.AlwaysAnimate;

            _clips.Clear();
            foreach (var c in clips)
                if (c != null) _clips[c.name] = c;       // 이름은 IremCharImport.ClipName 이 맞춰 뒀다

            _graph = PlayableGraph.Create("잔상:" + name);
            _graph.SetTimeUpdateMode(DirectorUpdateMode.GameTime);
            _mix = AnimationMixerPlayable.Create(_graph, 2);
            var outp = AnimationPlayableOutput.Create(_graph, "동작", _anim);
            outp.SetSourcePlayable(_mix);
            _graph.Play();

            _target = transform.position;
            Begin("idle", true);
            _fade = 1f;                                  // 첫 동작은 섞을 것이 없다
        }

        void OnDestroy() { if (_graph.IsValid()) _graph.Destroy(); }

        // ── 낯 ───────────────────────────────────────────────────────
        public void Play(string clip, bool force = false)
        {
            if (_dead) return;
            if (!_clips.ContainsKey(clip)) return;       // 없는 동작은 없는 대로 둔다
            if (_hold > 0 && !force) return;
            // 하던 동작을 다시 걸지 않는다. 되풀이하면 첫 프레임으로 되돌아간다.
            // 사건은 걸음마다 「일한다」를 말하는데(실측: 한 걸음에 스물, 한 사람은
            // 599걸음을 내리 일한다) 휘두름은 2.0초짜리다. 그러니 0.34초마다 처음으로
            // 튀었다 — 스물이 같은 프레임에서 함께. 팔을 휘두르는 사람 스물이 아니라
            // 같은 태엽 스물이다.
            if (_name == clip && (Loops(clip) || _hold > 0))
            {
                // 걷기는 걸음마다 다시 불린다. 다리를 되돌리지 않고 시간만 늘린다.
                if (clip == "walk")
                {
                    _hold = StepSeconds;
                    if (_to.IsValid()) _to.SetSpeed(WalkScale());   // 빠르게 보기를 눌렀을 수 있다
                }
                return;
            }
            Begin(clip, false);
        }

        public void MoveRig(Vector3 p, float seconds = 0.30f)
        {
            var d = p - transform.position;
            if (d.sqrMagnitude > 0.0004f)
            {
                _yawWant = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
                Facing = d.x >= 0f;
            }
            _target = p;
            _moveLeft = Mathf.Max(0.02f, seconds);
            // 실제로 땅이 지나가는 속도다. 한 칸을 StepSeconds 가 아니라 그 0.85 에
            // 건너가고 남는 참은 서 있으므로, 걷는 동안은 이쪽이 빠르다.
            _speed = d.magnitude / _moveLeft;
            Play("walk", true);
        }

        public void Warp(Vector3 p)
        {
            transform.position = p; _target = p; _moveLeft = 0;
        }

        /// 2D 의 좌우를 3D 의 각도로 옮긴다. 오른쪽이 +90도다.
        public void Face(bool right)
        {
            Facing = right;
            _yawWant = right ? 90f : -90f;
        }

        /// 어떤 자리를 향해 돈다. 3D 에만 있는 것이라 낯에는 없다.
        public void FaceTo(Vector3 p)
        {
            var d = p - transform.position;
            if (d.sqrMagnitude < 0.0004f) return;
            _yawWant = Mathf.Atan2(d.x, d.z) * Mathf.Rad2Deg;
            Facing = d.x >= 0f;
        }

        /// 맞은 순간 하얗게 튄다. 머티리얼을 만들지 않고 색만 갈아 끼운다(IremChar.Repaint 와 같은 길).
        public void Flash(Color c)
        {
            _paint = c; _flash = 0.18f;
            Tint(c);
        }

        /// 3D 는 깊이로 가린다. 그릴 순서를 정할 일이 없다.
        public void SetOrder(int o) { }

        // ── 속 ───────────────────────────────────────────────────────
        static bool Loops(string clip) => clip == "idle" || clip == "walk";

        /// 한 걸음의 길이. 연출자가 제 값을 넣어 준다(GardenDirector.StepSeconds).
        /// 안 넣어 주면 아직 아무도 안 걸었다는 뜻이라 기본값을 쓴다.
        public float StepSeconds = 0.82f;

        /// 지금 땅이 지나가는 속도에 다리를 맞춘다. 실측(브라우저): 걸음폭 0.786~0.882m,
        /// 한 바퀴 1.375초 → 다리는 1.14~1.28 m/s 를 낸다. 예전에는 한 칸(1m)을
        /// 0.34초에 옮겼으므로 2.94 m/s 였다 — 두 배 반을 끌려갔고, 그래서 다리는
        /// 걷는 시늉만 하고 몸은 미끄러졌다.
        float WalkScale()
        {
            if (!_clips.TryGetValue("walk", out var c) || c == null) return _tempo;
            if (_stride <= 0.05f) _stride = MeasureStride(c);
            if (_stride <= 0.05f) return _tempo;
            float ground = _speed > 0.01f ? _speed : 1f / Mathf.Max(0.05f, StepSeconds);
            return ground * c.length / (2f * _stride);
        }

        /// 걸음폭을 잰다 — 발이 몸 기준으로 앞뒤로 오간 길이. 클립을 직접 찍어서 본다.
        /// **이 서버에서 확인할 수 없다** — 유니티가 없다. 브라우저 쪽은 같은 계산으로
        /// 0.786~0.882m 가 나왔으니, 에디터에서 이 값이 그 근처가 아니면 여기가 틀린 것이다.
        float MeasureStride(AnimationClip c)
        {
            var smr = GetComponentInChildren<SkinnedMeshRenderer>();
            if (smr == null || smr.bones == null) return 0f;
            var foot = System.Array.Find(smr.bones, b => b != null && b.name == "foot_l");
            if (foot == null) return 0f;

            bool on = _anim.enabled; _anim.enabled = false;   // 찍는 동안은 그래프를 멈춘다
            float lo = float.MaxValue, hi = float.MinValue;
            const int N = 48;
            for (int i = 0; i <= N; i++)
            {
                c.SampleAnimation(gameObject, c.length * i / N);
                float z = transform.InverseTransformPoint(foot.position).z;
                if (z < lo) lo = z;
                if (z > hi) hi = z;
            }
            _anim.enabled = on;
            return hi - lo;
        }

        void Begin(string clip, bool first)
        {
            var c = _clips[clip];
            if (!first)
            {
                // 하던 것을 0번 칸으로 내리고 새것을 1번 칸에 올린다.
                if (_from.IsValid()) { _graph.Disconnect(_mix, 0); _from.Destroy(); }
                _from = _to;
                if (_from.IsValid()) _mix.ConnectInput(0, _from, 0);
                if (_to.IsValid()) _graph.Disconnect(_mix, 1);
            }
            _to = AnimationClipPlayable.Create(_graph, c);
            _to.SetApplyFootIK(false);
            // 걷기만은 제 박자가 아니라 땅의 속도를 따른다. 박자를 지키면 발이 미끄러진다.
            _to.SetSpeed(clip == "walk" ? WalkScale() : _tempo);
            // 도는 동작은 저마다 다른 곳에서 시작한다. 안 그러면 스물셋이 한 숨을 쉰다.
            if (Loops(clip)) _to.SetTime(_phase * c.length);
            _mix.ConnectInput(1, _to, 0);
            _mix.SetInputWeight(0, first ? 0f : 1f);
            _mix.SetInputWeight(1, first ? 1f : 0f);

            _name = clip;
            _fade = first ? 1f : 0f;
            _hold = Loops(clip) ? 0f : Mathf.Max(0.05f, c.length) / _tempo;
            // 한 번 휘두르고 나면 숨을 돌린다. 사람마다 다른 참이라 다시 겹치지 않는다.
            _rest = clip == "attack" ? _breath : 0f;
            if (clip == "walk") _hold = StepSeconds;     // 한 걸음 (GardenDirector.StepSeconds)
            if (clip == "fall") _dead = true;
        }

        void Update()
        {
            float dt = Time.deltaTime;

            if (_fade < 1f)
            {
                _fade = Mathf.Min(1f, _fade + dt / Fade);
                _mix.SetInputWeight(0, 1f - _fade);
                _mix.SetInputWeight(1, _fade);
            }

            if (_moveLeft > 0)
            {
                float k = Mathf.Min(1f, dt / _moveLeft);
                transform.position = Vector3.Lerp(transform.position, _target, k);
                _moveLeft -= dt;
                if (_moveLeft <= 0) transform.position = _target;
            }

            // 몸은 도는 데 시간이 걸린다. 즉시 돌면 인형처럼 보인다.
            _yaw = Mathf.LerpAngle(_yaw, _yawWant, 1f - Mathf.Exp(-dt * TurnSpeed));
            transform.rotation = Quaternion.Euler(0, _yaw, 0);

            if (_hold > 0)
            {
                _hold -= dt;
                // 동작이 끝나면 숨으로 돌아가고, 숨 돌리는 참만큼은 다음 일을 받지 않는다.
                if (_hold <= 0 && !_dead)
                {
                    float r = _rest; _hold = 0;
                    Begin("idle", false);
                    _hold = r;
                }
            }

            if (_flash > 0)
            {
                _flash -= dt;
                if (_flash <= 0) { if (_char != null) _char.Repaint(); }
                else Tint(Color.Lerp(Color.white, _paint, Mathf.Clamp01(_flash / 0.18f)));
            }
        }

        /// 자세를 여기서 얹는다 — Update 가 아니라 LateUpdate 다.
        ///
        /// 유니티의 한 프레임 순서는 Update -> 동작 갱신(Playables 평가) -> LateUpdate 다.
        /// Update 에서 얹으면 바로 뒤의 평가가 뼈를 그대로 덮어쓴다. 동작 네 벌이
        /// 뼈를 전부 절대값으로 찍기 때문에(make_demo.py base_pose) 덮어쓰기가 남지
        /// 않는다. 브라우저 쪽도 같은 이유로 mixer.update 뒤에 얹는다
        /// (viewer/garden.html Shade.update).
        void LateUpdate()
        {
            if (_stand == null) return;
            for (int i = 0; i < _stand.Length; i++)
            {
                var st = _stand[i];
                if (st.bone == null) continue;
                if (st.hasQ) st.bone.localRotation *= st.q;
                if (st.hasScale) st.bone.localScale = st.scale;
            }
        }

        static readonly int ColourId = Shader.PropertyToID("_Colour");
        MaterialPropertyBlock _mpb;
        void Tint(Color c)
        {
            _mpb ??= new MaterialPropertyBlock();
            foreach (var r in GetComponentsInChildren<Renderer>(true))
            {
                int n = Mathf.Max(1, r.sharedMaterials.Length);
                for (int i = 0; i < n; i++)
                {
                    r.GetPropertyBlock(_mpb, i);
                    _mpb.SetColor(ColourId, c);
                    r.SetPropertyBlock(_mpb, i);
                }
            }
        }
    }
}
