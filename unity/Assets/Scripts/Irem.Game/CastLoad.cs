// 잔상 한 명을 실제로 세운다. 몸 FBX + 옷 FBX + 동작 여섯 벌.
//
// 몸 5벌·옷 55벌을 곱한 275가지를 미리 굽지 않는다 — 세울 때 입힌다(IremChar.Wear).
// 그래서 여기서 캐시하는 것은 원본 FBX 뿐이고, 인스턴스는 매번 새로 만든다.
//
// 자산을 어디서 읽는가(정직하게 적는다):
//   FBX 는 Assets/Art/ 아래에 있고 Resources 아래가 아니다. 그래서 에디터에서는
//   AssetDatabase 로 읽고, 빌드에서는 Resources 를 본다. 지금 이 저장소에서
//   뜰을 보는 길은 에디터([이렘/뜰 신])이므로 에디터 쪽이 실제로 쓰이는 길이다.
//   빌드에 넣으려면 FBX 를 Resources 아래로 옮기거나 어드레서블이 필요하다 —
//   그때 재고 그때 옮긴다. 지금 없는 것을 미리 만들지 않는다.
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Irem.Data;
#if UNITY_EDITOR
using UnityEditor;
#endif

namespace Irem.Game
{
    public static class CastLoad
    {
        public const string CharDir = "Assets/Art/Chars";
        public const string PropDir = "Assets/Art/Props";
        public const string ClipFbx = CharDir + "/Clips/motion.fbx";
        public const string MatPath = CharDir + "/Silhouette.mat";

        static readonly Dictionary<string, GameObject> _fbx = new();
        static AnimationClip[] _clips;
        static Material _sil;

        /// 실루엣 머티리얼. 없으면 셰이더로 하나 만든다(자산으로 남기지 않는다 —
        /// 자산을 만드는 것은 에디터 도구의 일이다, IremCharScene.EnsureMaterial).
        public static Material Silhouette
        {
            get
            {
                if (_sil != null) return _sil;
#if UNITY_EDITOR
                _sil = AssetDatabase.LoadAssetAtPath<Material>(MatPath);
#endif
                if (_sil == null)
                {
                    var sh = Shader.Find("Irem/Silhouette");
                    if (sh == null)
                    {
                        Debug.LogError("[이렘] Irem/Silhouette 셰이더가 없다. "
                                     + "몸이 회색 덩어리로 보일 것이다.");
                        return null;
                    }
                    _sil = new Material(sh) { enableInstancing = true };
                }
                return _sil;
            }
        }

        /// 동작 여섯 벌. 한 장에 다 들어 있고 몸 다섯이 나눠 쓴다.
        public static AnimationClip[] Clips
        {
            get
            {
                if (_clips != null) return _clips;
                var got = new List<AnimationClip>();
#if UNITY_EDITOR
                got.AddRange(AssetDatabase.LoadAllAssetsAtPath(ClipFbx)
                                          .OfType<AnimationClip>()
                                          .Where(c => !c.name.StartsWith("__preview")));
#endif
                if (got.Count == 0)
                {
                    var all = Resources.LoadAll<AnimationClip>("Irem/Clips");
                    if (all != null) got.AddRange(all);
                }
                if (got.Count == 0)
                    Debug.LogError($"[이렘] {ClipFbx} 에서 동작을 하나도 못 읽었다. "
                                 + "chars/src/make_clips.py 를 돌렸는지, "
                                 + "Bodies 를 먼저 들여왔는지 확인할 것.");
                // 이름 순으로 고정한다 — 읽는 순서가 바뀌어도 같은 목록이어야 한다.
                _clips = got.OrderBy(c => c.name, System.StringComparer.Ordinal).ToArray();
                return _clips;
            }
        }

        public static GameObject Fbx(string path)
        {
            if (_fbx.TryGetValue(path, out var g)) return g;
#if UNITY_EDITOR
            g = AssetDatabase.LoadAssetAtPath<GameObject>(path);
#endif
            if (g == null)
            {
                // Resources 쪽 이름은 확장자가 없다: Irem/Chars/Bodies/guard
                var r = path;
                if (r.StartsWith("Assets/Art/")) r = "Irem/" + r.Substring("Assets/Art/".Length);
                if (r.EndsWith(".fbx")) r = r.Substring(0, r.Length - 4);
                g = Resources.Load<GameObject>(r);
            }
            _fbx[path] = g;
            if (g == null) Debug.LogError($"[이렘] {path} 를 못 읽었다.");
            return g;
        }

        public static GameObject Body(string slug)    => Fbx($"{CharDir}/Bodies/{slug}.fbx");
        public static GameObject Garment(string slug) => Fbx($"{CharDir}/Garments/{slug}.fbx");
        public static GameObject Prop(string name)    => Fbx($"{PropDir}/{name}.fbx");

        /// 잔상 하나를 세운다. 돌아온 오브젝트의 루트가 곧 몸이고, 거기에 ShadeView3D 가 붙어 있다.
        public static GameObject Build(AgentDef a, Transform parent)
        {
            var bodyFbx = Body(a.body);
            if (bodyFbx == null) return null;

            var go = Object.Instantiate(bodyFbx);
            go.name = a.name ?? a.id;
            go.transform.SetParent(parent, false);

            var sil = Silhouette;
            IremChar.Skin(go, sil);

            // 옷. 없으면 몸만 세운다 — 옷이 없다고 사람을 빼지 않는다.
            var gFbx = Garment(a.garment);
            if (gFbx != null)
            {
                var gg = Object.Instantiate(gFbx);
                if (!IremChar.Wear(go, gg, sil)) Object.Destroy(gg);
            }

            var ch = go.GetComponent<IremChar>() ?? go.AddComponent<IremChar>();
            ch.accent = Accent(a.col);
            ch.Repaint();

            // 몸 FBX 가 휴머노이드로 들어왔으므로 Animator 와 아바타가 이미 붙어 있다.
            var an = go.GetComponent<Animator>() ?? go.AddComponent<Animator>();
            an.enabled = true;

            var v = go.AddComponent<ShadeView3D>();
            v.Bind(Clips);
            return go;
        }

        /// characters.json 의 key_color("#RRGGBB"). 읽을 수 없으면 기본 강조색을 쓴다.
        public static Color Accent(string hex)
        {
            if (!string.IsNullOrEmpty(hex) && ColorUtility.TryParseHtmlString(
                    hex[0] == '#' ? hex : "#" + hex, out var c)) return c;
            return new Color(0.788f, 0.635f, 0.153f, 1f);
        }
    }
}
