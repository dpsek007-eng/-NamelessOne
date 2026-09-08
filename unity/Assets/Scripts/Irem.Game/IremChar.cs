// 몸 한 벌 + 옷 한 벌 = 잔상 하나.
//
// 옷 FBX 에도 뼈 53개가 딸려 온다. 그 뼈는 몸의 뼈와 이름도 위치도 같지만
// 다른 트랜스폼이다. 그대로 두면 몸이 움직여도 옷은 제자리에 선 채로 남는다 —
// 애니메이션은 몸의 뼈만 돌리기 때문이다. 그래서 입힐 때 옷의
// SkinnedMeshRenderer 가 가리키는 뼈 배열을 몸의 뼈로 통째로 갈아 끼운다.
// 이름으로 찾는다. 두 리그가 같은 MPFB game_engine 에서 나왔으므로 이름이 같고,
// 같은 몸에 맞춰 뽑았으므로 바인드 포즈도 같다. 그래서 갈아 끼우기만 하면 된다.
//
// 이 방식이라야 옷 55벌에 몸 5벌을 곱한 275가지를 미리 굽지 않는다.
using System.Collections.Generic;
using UnityEngine;

namespace Irem.Game
{
    [ExecuteAlways]
    [DisallowMultipleComponent]
    public sealed class IremChar : MonoBehaviour
    {
        // 짙은 실루엣 하나 + 강조색 하나. `docs/22-아트.md`
        // 강조색은 계층이 아니라 개체별이다 — data/characters.json 의 key_color.
        //
        // 몸을 옷보다 한 단 더 어둡게 둔다. 둘이 같은 색이면 팔과 몸통이
        // 겹칠 때 한 덩어리가 된다 — 아트 문서가 "팔은 몸통보다 밝은 톤"
        // 이라고 못 박은 것과 같은 이유다.
        public Color skin   = new Color(0.051f, 0.043f, 0.039f, 1f);
        public Color cloth  = new Color(0.133f, 0.106f, 0.086f, 1f);
        public Color accent = new Color(0.788f, 0.635f, 0.153f, 1f);

        static readonly int ColourId = Shader.PropertyToID("_Colour");
        MaterialPropertyBlock _mpb;

        void OnEnable()  => Repaint();
        void OnValidate() => Repaint();

        /// 머티리얼을 만들지 않고 색만 갈아 끼운다.
        /// 슬롯 0 은 천, 슬롯 1 은 강조색 — 옷을 구울 때 그렇게 넣었다.
        /// 강조색 띠가 없는 계층은 슬롯이 하나뿐이라 1번 자리는 그냥 비어 있다.
        public void Repaint()
        {
            _mpb ??= new MaterialPropertyBlock();
            foreach (var r in GetComponentsInChildren<Renderer>(true))
            {
                // 옷 메시의 이름은 garment_<체형>_<계층> 이다 (chars/src/make_garments.py).
                // 그 외는 몸이다.
                bool worn = r.name.StartsWith("garment",
                                System.StringComparison.OrdinalIgnoreCase);
                int n = r.sharedMaterials.Length;
                for (int i = 0; i < n; i++)
                {
                    r.GetPropertyBlock(_mpb, i);
                    _mpb.SetColor(ColourId, i == 1 ? accent : (worn ? cloth : skin));
                    r.SetPropertyBlock(_mpb, i);
                }
            }
        }

        /// 옷을 몸에 입힌다. garment 는 옷 FBX 를 인스턴스로 세운 것.
        /// 다 끝나면 옷의 뼈대와 껍데기 오브젝트는 사라지고,
        /// 옷 메시만 몸 밑으로 들어간다.
        public static bool Wear(GameObject body, GameObject garment, Material silhouette)
        {
            if (body == null || garment == null) return false;

            var bones = new Dictionary<string, Transform>(128);
            foreach (var t in body.GetComponentsInChildren<Transform>(true))
                bones[t.name] = t;          // 같은 이름이 겹치면 나중 것이 이긴다.
                                            // 뼈 이름 53개는 몸 안에서 유일하다.

            var wear  = garment.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            var moved = new HashSet<Transform>();
            if (wear.Length == 0)
            {
                Debug.LogError($"[이렘] {garment.name} 에 스킨드 메시가 없다.");
                return false;
            }

            foreach (var smr in wear)
            {
                var src = smr.bones;
                var dst = new Transform[src.Length];
                for (int i = 0; i < src.Length; i++)
                {
                    if (src[i] == null || !bones.TryGetValue(src[i].name, out dst[i]))
                    {
                        Debug.LogError($"[이렘] {garment.name}: 몸에 '{src[i]?.name}' 뼈가 없다. "
                                       + "몸과 옷을 같은 리그로 구웠는지 확인할 것.");
                        return false;
                    }
                }

                var rootName = smr.rootBone != null ? smr.rootBone.name : null;
                smr.bones = dst;
                if (rootName != null && bones.TryGetValue(rootName, out var rb))
                    smr.rootBone = rb;

                if (silhouette != null) Paint(smr, silhouette);

                // 몸 밑으로 옮긴다. 로컬 값을 그대로 두어야(false) 제자리에 선다 —
                // 옷 FBX 의 루트도 몸 FBX 의 루트도 원점이므로 값이 같다.
                smr.transform.SetParent(body.transform, false);
                moved.Add(smr.transform);
            }

            // 남은 것은 옷의 뼈대와 빈 껍데기뿐이다. 지운다.
            // 다만 메시가 FBX 루트에 바로 붙어 있었다면 그 루트가 곧 메시이므로 살린다.
            if (!moved.Contains(garment.transform)) DestroyNow(garment);
            return true;
        }

        /// 몸의 껍질에도 같은 머티리얼을 씌운다.
        public static void Skin(GameObject body, Material silhouette)
        {
            if (silhouette == null) return;
            foreach (var r in body.GetComponentsInChildren<Renderer>(true))
                Paint(r, silhouette);
        }

        /// 슬롯 수를 메시의 서브메시로 센다.
        /// 들여올 때 머티리얼을 아예 안 받으므로(IremCharImport) sharedMaterials 가
        /// 비어 있을 수 있다. 길이 0 짜리 배열을 도로 넣으면 그 메시는 안 그려진다.
        static void Paint(Renderer r, Material mat)
        {
            int n = r.sharedMaterials.Length;

            Mesh mesh = null;
            var smr = r as SkinnedMeshRenderer;
            if (smr != null) mesh = smr.sharedMesh;
            else
            {
                var mf = r.GetComponent<MeshFilter>();
                if (mf != null) mesh = mf.sharedMesh;
            }
            if (mesh != null) n = Mathf.Max(n, mesh.subMeshCount);
            if (n <= 0) return;
            var mats = new Material[n];
            for (int i = 0; i < n; i++) mats[i] = mat;
            r.sharedMaterials = mats;
        }

        // 에디터에서 신을 지을 때는 Destroy 가 다음 프레임에나 돈다.
        // 그러면 빈 껍데기가 신에 저장되어 버린다. 즉시 지운다.
        static void DestroyNow(Object o)
        {
            if (Application.isPlaying) Object.Destroy(o);
            else Object.DestroyImmediate(o);
        }
    }
}
