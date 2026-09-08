// [이렘/캐릭터 확인 신] — 55벌을 한 화면에 세운다.
//
// 왜 신을 따로 만드는가. 컴파일이 되고 파일이 들어왔다고 옷이 맞는 것이 아니다.
// 지금까지 이 갈래에서 난 고장은 전부 "정점 수도 파일 크기도 정상인데
// 눈으로 보면 틀린" 것들이었다 — 굽지 않은 셰이프키, 안 맞춘 리그,
// 크기만 다른 같은 몸, 밑단만 다른 일곱 벌. 그래서 늘어놓고 본다.
//
// 가로 11칸이 계층, 세로 5줄이 체형이다. 옆칸과 다르지 않으면 그 칸은 실패다.
using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using TMPro;
using Irem.Game;

namespace Irem.Editor
{
    public static class IremCharScene
    {
        const string Dir   = "Assets/Art/Chars";
        const string Mat   = Dir + "/Silhouette.mat";
        const string Scene = "Assets/Scenes/캐릭터.unity";

        // 파일 이름 순서가 아니라 뜻의 순서로 세운다.
        // 체형은 `chars/src/bodies.py` 의 SLUG, 계층은 `chars/src/garments.py` 의 SLUG.
        static readonly (string slug, string ko)[] Bodies =
        {
            ("guard",  "수호"), ("resist", "저항"), ("devote", "헌신"),
            ("seek",   "탐구"), ("flee",   "도피"),
        };

        // 위계 순. 왕실이 왼쪽 끝, 유랑이 오른쪽 끝이다.
        static readonly (string slug, string ko)[] Classes =
        {
            ("royal",   "왕실"), ("noble",   "귀족"), ("mage",    "술사"),
            ("clergy",  "성직"), ("clerk",   "관리"), ("merchant","상인"),
            ("artisan", "장인"), ("soldier", "병졸"), ("peasant", "농어민"),
            ("servant", "하인"), ("vagrant", "유랑"),
        };

        // 늘어놓는 방식은 sheet.png 와 같게 둔다 — 정면에서 본 격자.
        // 앞뒤(Z)로 세우고 카메라를 기울여 볼까 했는데, 직교 카메라에서는 앞줄이
        // 뒷줄을 정확히 가리고, 기울이면 줄마다 크기가 같아 보이질 않는다.
        // 실루엣을 옆칸과 비교하려고 만든 신이므로 비교를 방해하면 안 된다.
        // 공중에 뜨는 것은 상관없다 — 흐려짐이 오브젝트 제 원점을 기준으로 돌기 때문이다.
        const float StepX = 1.15f;  // 옆 사람과 닿지 않을 만큼. 망토가 어깨 1.75배까지 벌어진다
        const float StepY = 2.15f;  // 가장 큰 수호가 1.85m 남짓이다

        [MenuItem("이렘/캐릭터 확인 신")]
        public static void Build()
        {
            var sil = EnsureMaterial();
            if (sil == null) return;   // 셰이더가 없으면 55벌 다 회색 덩어리가 된다

            var sc = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // 빛은 실루엣 셰이더가 제 안에서 방향을 들고 있으므로 쓰지 않는다.
            // 그래도 하나 둔다 — 이 신을 열었다가 다른 셰이더를 붙여 볼 때
            // 아무것도 안 보이면 셰이더 탓인지 빛 탓인지 알 수 없다.
            var lightGo = new GameObject("빛");
            var light = lightGo.AddComponent<Light>();
            light.type = LightType.Directional;
            lightGo.transform.rotation = Quaternion.Euler(50f, -30f, 0f);

            var camGo = new GameObject("카메라");
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags      = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.72f, 0.71f, 0.69f);   // 밝은 바탕. 짙은 실루엣이 읽히게
            cam.orthographic     = true;
            // 가로 11칸(12.6m)·세로 5줄(10.5m)이 다 들어가는 크기.
            // 16:9 에서는 세로가 먼저 찬다 — 가로는 남는다.
            // 위로 여유를 더 두는 이유는 계층 이름이 맨 윗줄 머리 위에 서기 때문이다.
            float w = StepX * (Classes.Length - 1);
            float h = StepY * (Bodies.Length - 1) + 1.9f;
            cam.orthographicSize = h * 0.5f + 1.3f;
            camGo.transform.position = new Vector3(w * 0.5f, h * 0.5f + 0.15f, -12f);
            camGo.tag = "MainCamera";

            var root = new GameObject("잔상");
            int made = 0, failed = 0;

            // 칸 이름을 붙인다. 이름이 없으면 어느 칸이 무엇인지 알 수 없고,
            // 알 수 없으면 "옆칸과 다른가"를 볼 수가 없다.
            IremFont.Ensure();
            var font = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(IremFont.Sans);
            var labels = new GameObject("이름").transform;
            float topY = StepY * (Bodies.Length - 1);
            for (int c = 0; c < Classes.Length; c++)
                Label(labels, Classes[c].ko, new Vector3(c * StepX, topY + 2.35f, 0f),
                      font, TextAlignmentOptions.Center);
            for (int r = 0; r < Bodies.Length; r++)
                Label(labels, Bodies[r].ko,
                      new Vector3(-1.05f, (Bodies.Length - 1 - r) * StepY + 0.9f, 0f),
                      font, TextAlignmentOptions.Right);

            for (int r = 0; r < Bodies.Length; r++)
            {
                var bodyPath = $"{Dir}/Bodies/{Bodies[r].slug}.fbx";
                var bodyFbx  = AssetDatabase.LoadAssetAtPath<GameObject>(bodyPath);
                if (bodyFbx == null)
                {
                    Debug.LogError($"[이렘] {bodyPath} 가 없다. chars/to_unity.sh 를 먼저 돌릴 것.");
                    failed += Classes.Length;
                    continue;
                }

                for (int c = 0; c < Classes.Length; c++)
                {
                    var g = Dress(bodyFbx, Bodies[r], Classes[c], sil);
                    if (g == null) { failed++; continue; }
                    g.transform.SetParent(root.transform, false);
                    // 첫 줄(수호)이 맨 위로 가게 뒤집는다. sheet.png 와 같은 순서다.
                    g.transform.position =
                        new Vector3(c * StepX, (Bodies.Length - 1 - r) * StepY, 0f);
                    made++;
                }
            }

            Directory.CreateDirectory("Assets/Scenes");
            EditorSceneManager.MarkSceneDirty(sc);
            EditorSceneManager.SaveScene(sc, Scene);
            AssetDatabase.Refresh();

            Debug.Log(failed == 0
                ? $"[이렘] {Scene} — 잔상 {made}벌을 세웠다. "
                  + "가로가 계층 11, 세로가 체형 5다. 씬 뷰에서 볼 것 (재생하면 편성 화면이 뜬다)."
                : $"[이렘] {Scene} — {made}벌 섰고 {failed}벌 실패했다. 위 오류를 볼 것.");
        }

        static void Label(Transform parent, string text, Vector3 pos,
                          TMP_FontAsset font, TextAlignmentOptions align)
        {
            var go = new GameObject(text);
            go.transform.SetParent(parent, false);
            go.transform.position = pos;
            var t = go.AddComponent<TextMeshPro>();
            if (font != null) t.font = font;
            t.text            = text;
            t.fontSize        = 4f;
            t.color           = new Color(0.20f, 0.19f, 0.18f);
            t.alignment       = align;
            t.enableWordWrapping = false;
            t.rectTransform.sizeDelta = new Vector2(2.0f, 0.5f);
        }

        static GameObject Dress(GameObject bodyFbx, (string slug, string ko) body,
                                (string slug, string ko) cls, Material sil)
        {
            var gp  = $"{Dir}/Garments/{body.slug}_{cls.slug}.fbx";
            var gfb = AssetDatabase.LoadAssetAtPath<GameObject>(gp);
            if (gfb == null) { Debug.LogError($"[이렘] {gp} 가 없다."); return null; }

            var go = (GameObject)PrefabUtility.InstantiatePrefab(bodyFbx);
            go.name = $"{body.ko}_{cls.ko}";

            // 몸은 옷 밑에 깔린다. 긴 옷에서는 거의 안 보이지만 손·머리·발은 나온다.
            IremChar.Skin(go, sil);

            var gg = (GameObject)PrefabUtility.InstantiatePrefab(gfb);
            // 프리팹 연결을 끊는다 — 뼈를 갈아 끼우는 것은 프리팹 바깥의 변경이라
            // 그대로 두면 유니티가 저장할 때 되돌린다.
            PrefabUtility.UnpackPrefabInstance(gg, PrefabUnpackMode.Completely,
                                               InteractionMode.AutomatedAction);
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely,
                                               InteractionMode.AutomatedAction);

            if (!IremChar.Wear(go, gg, sil))
            {
                Object.DestroyImmediate(gg);
                Object.DestroyImmediate(go);
                return null;
            }

            var ch = go.AddComponent<IremChar>();
            ch.accent = Accent(cls.slug);
            ch.Repaint();
            return go;
        }

        // 확인용 색이다. 실제 강조색은 개체마다 다르다(data/characters.json 의 key_color).
        // 여기서는 옆칸과 갈리는 것이 목적이므로 계층마다 다른 색을 준다.
        static Color Accent(string slug)
        {
            int i = System.Array.FindIndex(Classes, c => c.slug == slug);
            return Color.HSVToRGB(Mathf.Repeat(i * 0.14f, 1f), 0.62f, 0.88f);
        }

        static Material EnsureMaterial()
        {
            var m = AssetDatabase.LoadAssetAtPath<Material>(Mat);
            if (m != null) return m;

            var sh = Shader.Find("Irem/Silhouette");
            if (sh == null)
            {
                Debug.LogError("[이렘] Irem/Silhouette 셰이더를 찾지 못했다. "
                               + Dir + "/Silhouette.shader 를 확인할 것.");
                return null;
            }
            m = new Material(sh) { enableInstancing = true };
            Directory.CreateDirectory(Dir);
            AssetDatabase.CreateAsset(m, Mat);
            AssetDatabase.SaveAssets();
            return m;
        }
    }
}
