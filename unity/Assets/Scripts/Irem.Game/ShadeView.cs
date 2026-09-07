// 잔상 한 명의 몸. 시트에서 프레임을 골라 쓴다.
//
//   에이전트가 무엇을 하기로 했는지에 따라 동작이 바뀐다.
//   걸으면 걷고, 치면 치고, 맞으면 움츠리고, 흐려질 때는 무너진다.
//   서 있을 때도 숨은 쉰다.
using UnityEngine;
using Irem.Data;

namespace Irem.Game
{
    [RequireComponent(typeof(SpriteRenderer))]
    public sealed class ShadeView : MonoBehaviour
    {
        public Sprite[] Frames;
        public BattleTables T;

        public Transform Rig;                 // 그림자·고리와 함께 움직이는 부모
        SpriteRenderer _sr;
        Color _base = Color.white;
        float _flash;
        ClipDef _clip;
        int _f;
        float _acc, _hold;
        bool _dead;
        Vector3 _target;
        float _moveLeft;

        public string Clip => _clip?.name ?? "idle";
        public bool Facing { get; private set; } = true;      // true = 오른쪽

        void Awake()
        {
            _sr = GetComponent<SpriteRenderer>();
            _target = transform.position;
        }

        public void Bind(Sprite[] frames, BattleTables t)
        {
            Frames = frames; T = t;
            _clip = T.Clip("idle");
            _f = 0; _acc = 0; _hold = 0; _dead = false;
            Apply();
        }

        /// force = 이 동작이 끝날 때까지 다른 것으로 안 바뀐다
        public void Play(string name, bool force = false)
        {
            if (_dead) return;
            var c = T?.Clip(name); if (c == null) return;
            if (_hold > 0 && !force) return;
            if (_clip != null && _clip.name == name && c.loop) return;
            _clip = c; _f = 0; _acc = 0;
            _hold = c.loop ? 0f : (float)c.n / Mathf.Max(1, c.fps);
            if (name == "walk") _hold = 0.34f;
            if (name == "fall") _dead = true;
            Apply();
        }

        /// 칸에서 칸으로 미끄러져 간다. 순간이동하면 살아 있는 것으로 보이지 않는다.
        public void MoveRig(Vector3 p, float seconds = 0.30f)
        {
            var t = Rig != null ? Rig : transform;
            if (p.x > t.position.x + 0.01f) Facing = true;
            else if (p.x < t.position.x - 0.01f) Facing = false;
            _target = p; _moveLeft = Mathf.Max(0.02f, seconds);
            Play("walk", true);
        }
        public void Warp(Vector3 p)
        {
            var t = Rig != null ? Rig : transform;
            t.position = p; _target = p; _moveLeft = 0;
        }
        public void SetOrder(int o) { if (_sr != null) _sr.sortingOrder = o; }

        /// 맞은 순간 하얗게 튄다 — 이것이 없으면 맞았는지 알 수 없다
        public void Flash(Color c)
        {
            _base = c; _flash = 0.18f;
            if (_sr != null) _sr.color = c;
        }
        public void Face(bool right) => Facing = right;

        void Apply()
        {
            if (Frames == null || Frames.Length == 0 || _clip == null) return;
            int i = Mathf.Clamp(_clip.from + _f, 0, Frames.Length - 1);
            _sr.sprite = Frames[i];
            var s = transform.localScale;
            s.x = Mathf.Abs(s.x) * (Facing ? 1 : -1);
            transform.localScale = s;
        }

        void Update()
        {
            float dt = Time.deltaTime;

            if (_flash > 0)
            {
                _flash -= dt;
                if (_sr != null)
                    _sr.color = Color.Lerp(Color.white, _base, Mathf.Clamp01(_flash / 0.18f));
            }

            if (_moveLeft > 0)
            {
                var tr = Rig != null ? Rig : transform;
                float k = Mathf.Min(1f, dt / _moveLeft);
                tr.position = Vector3.Lerp(tr.position, _target, k);
                _moveLeft -= dt;
                if (_moveLeft <= 0) tr.position = _target;
            }

            if (_clip == null) return;
            float step = 1f / Mathf.Max(1, _clip.fps);
            _acc += dt;
            while (_acc >= step)
            {
                _acc -= step;
                if (_f < _clip.n - 1) _f++;
                else if (_clip.loop) _f = 0;
            }
            if (_hold > 0)
            {
                _hold -= dt;
                if (_hold <= 0 && !_dead) { _hold = 0; _clip = T.Clip("idle"); _f = 0; _acc = 0; }
            }
            Apply();
        }
    }
}
