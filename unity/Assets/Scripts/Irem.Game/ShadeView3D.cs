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
        bool _dead;

        Vector3 _target;
        float _moveLeft;
        float _yaw = 0f, _yawWant = 0f;
        Color _paint = Color.white;
        float _flash;

        public string Clip => _name;
        public bool Facing { get; private set; } = true;
        public Vector3 Pos => transform.position;

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
            if (_name == clip && Loops(clip)) return;    // 도는 동작을 다시 걸면 처음으로 튄다
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
            _mix.ConnectInput(1, _to, 0);
            _mix.SetInputWeight(0, first ? 0f : 1f);
            _mix.SetInputWeight(1, first ? 1f : 0f);

            _name = clip;
            _fade = first ? 1f : 0f;
            _hold = Loops(clip) ? 0f : Mathf.Max(0.05f, c.length);
            if (clip == "walk") _hold = 0.34f;           // 2D 와 같은 값 (ShadeView.Play)
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
                if (_hold <= 0 && !_dead) { _hold = 0; Begin("idle", false); }
            }

            if (_flash > 0)
            {
                _flash -= dt;
                if (_flash <= 0) { if (_char != null) _char.Repaint(); }
                else Tint(Color.Lerp(Color.white, _paint, Mathf.Clamp01(_flash / 0.18f)));
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
