// 초점을 옮기는 컴포넌트. 값 하나(초점 0~1)를 셰이더의 _Focus 한 개에 민다.
// `docs/22-아트.md` — "유니티 _Focus | 셰이더 파라미터 1개". 곡선(흐림·이목구비·
// 이중상·어긋남)은 셰이더가 같은 수로 쌓는다. 이 컴포넌트는 값을 만드는 쪽과
// 거는 쪽만 된다.
//
//   focus  0.0 = 안 맞음 (★1)   1.0 = 완전히 맞음 (★6)
//          태생 ★5(전승)는 뽑는 순간 0.80 — 손그림 초상이 거의 그대로 보인다
//   borrowed  빌린 특성 — ★6 에서도 이중상 0.15 가 끝까지 남는다
//   faceRect  이목구비 자리 (UV x,y,w,h) — portrait_assemble --sheet 가
//             만든 parts.face_boxes.json 의두상 상자 값이다. 합성 조립이
//             이목구비를 그 상자에 맞춰 끼우므로 자리를 다시 잴 필요가 없다.
//
// 걸리는 곳은 SpriteRenderer(씬의 초상 카드)와 uGUI Image/Graphic(명부·편성·
// 소환) 둘 다. uGUI 는 이미지마다 머티리얼을 하나 복제한다 — 화면에 초상이
// 수십 개 뜨는 화면이면 모르겠고, 명부 수준은 값이 싸다. Renderer 는
// MaterialPropertyBlock 을 쓴다(필드 실루엣과 같은 규칙).
using UnityEngine;
using UnityEngine.UI;

namespace Irem.Game
{
    [ExecuteAlways]
    public sealed class FocusDriver : MonoBehaviour
    {
        public const int CAP = 6;                   // 상한 성급 (docs/04)
        public const int STEPS = (CAP - 1) * 5;     // ★1 → ★6 각성 단계 수

        [Range(0f, 1f)] public float focus = 1f;
        [Tooltip("빌린 특성 — ★6 에서도 이중상 0.15 가 남는다")] public bool borrowed;
        [Tooltip("이목구비 자리 (UV x,y,w,h). parts.face_boxes.json 의 값")] public Vector4 faceRect = new(0.29f, 0.16f, 0.42f, 0.42f);

        Renderer _ren;
        Graphic _gr;
        MaterialPropertyBlock _block;

        // tools/focus_curve.py 의 focus() 와 같은 수 — 성급·각성을 초점으로.
        public static float FocusOf(int star, int awaken = 0)
        {
            return Mathf.Clamp01(((star - 1) * 5 + awaken) / (float)STEPS);
        }

        void CacheTarget()
        {
            _ren = GetComponent<Renderer>();
            _gr  = _ren == null ? GetComponent<Graphic>() : null;
        }

        void Awake() { CacheTarget(); Apply(); }

        void OnEnable() { Apply(); }

        void OnValidate() { CacheTarget(); Apply(); }

        /// 별점·각성 단계(0~4)를 주면 초점을 계산해 거는 편의 경로.
        /// 예: 태생 ★5 전승 = SetStarAwaken(5) → 0.80
        public void SetStarAwaken(int star, int awaken = 0)
        {
            focus = FocusOf(star, awaken);
            Apply();
        }

        public void SetFocus(float f) { focus = Mathf.Clamp01(f); Apply(); }

        public void Apply()
        {
            CacheTarget();
            var f = Mathf.Clamp01(focus);
            if (_ren != null)
            {
                _block ??= new MaterialPropertyBlock();
                _ren.GetPropertyBlock(_block);
                _block.SetFloat("_Focus", f);
                _block.SetFloat("_Borrowed", borrowed ? 1f : 0f);
                _block.SetVector("_FaceRect", faceRect);
                _ren.SetPropertyBlock(_block);
                return;
            }
            if (_gr != null)
            {
                _gr.material.SetFloat("_Focus", f);
                _gr.material.SetFloat("_Borrowed", borrowed ? 1f : 0f);
                _gr.material.SetVector("_FaceRect", faceRect);
                _gr.SetMaterialDirty();
            }
        }
    }
}