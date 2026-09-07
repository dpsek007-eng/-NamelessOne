// 프로젝트를 열면 이 창이 뜬다.
//
//   씬 뷰에는 카메라와 빈 오브젝트만 있어서 볼 것이 없고,
//   편성 화면은 재생을 눌러야 Game 탭에 나온다.
//   그것을 모르면 "열었는데 아무것도 안 나온다" 가 된다. 그래서 여기 적어 둔다.
using System.Linq;
using UnityEditor;
using UnityEngine;
using Irem.Data;
using Irem.Game;

namespace Irem.Editor
{
    public sealed class IremWindow : EditorWindow
    {
        const string ShownKey = "Irem.WindowShown";
        string _status = "";
        bool _ok;

        [InitializeOnLoadMethod]
        static void OpenOnce()
        {
            if (Application.isBatchMode) return;
            if (SessionState.GetBool(ShownKey, false)) return;
            SessionState.SetBool(ShownKey, true);
            EditorApplication.delayCall += () =>
            {
                Open();
                Debug.Log("이렘 — 편성 화면은 <b>재생(▶)</b> 을 눌러야 <b>Game</b> 탭에 나옵니다. " +
                          "씬 뷰에는 볼 것이 없습니다. [이렘] 메뉴 참고.");
            };
        }

        [MenuItem("이렘/열기 _F1", priority = 0)]
        public static void Open()
        {
            var w = GetWindow<IremWindow>(false, "이렘", true);
            w.minSize = new Vector2(360, 300);
            w.Refresh();
            w.Show();
        }

        void OnEnable() => Refresh();

        void Refresh()
        {
            var ta = Resources.Load<TextAsset>("Irem/tables");
            if (ta == null)
            {
                _ok = false;
                _status = "표가 없습니다 — Assets/Resources/Irem/tables.json\n" +
                          "tools/export_unity.py 를 돌리십시오.";
                return;
            }
            var T = JsonUtility.FromJson<BattleTables>(ta.text);
            int missing = T.chars.Count(c => ArtLoad.SheetTex(c.id) == null);
            var font = IremUI.Face(12);
            _ok = missing == 0 && font != null;
            _status =
                $"잔상 {T.chars.Length}명 · 층 {T.floors.Length}개 · 프레임 {T.nf}\n" +
                (missing == 0 ? "그림 전부 있음" : $"그림 빠진 것 {missing}개") + "\n" +
                (font != null ? "한글 폰트 " + font.name
                              : "한글 폰트를 못 찾음 — 글자가 네모로 보입니다");
        }

        void OnGUI()
        {
            GUILayout.Space(10);
            var title = new GUIStyle(EditorStyles.boldLabel) { fontSize = 20 };
            GUILayout.Label("  이렘의 탑", title);
            GUILayout.Label("  잔상 편성 · 전투 시험판", EditorStyles.miniLabel);
            GUILayout.Space(12);

            EditorGUILayout.HelpBox(_status, _ok ? MessageType.Info : MessageType.Error);
            GUILayout.Space(8);

            EditorGUILayout.HelpBox(
                "편성 화면은 재생(▶) 을 눌러야 나옵니다.\n" +
                "그리고 씬(Scene) 탭이 아니라 게임(Game) 탭에 그려집니다.\n" +
                "씬 뷰에는 카메라와 빈 오브젝트뿐이라 볼 것이 없습니다.",
                MessageType.Warning);
            GUILayout.Space(10);

            GUI.enabled = _ok && !EditorApplication.isPlaying;
            if (GUILayout.Button("▶  재생 — 편성 화면 열기", GUILayout.Height(44)))
            {
                var gv = System.Type.GetType("UnityEditor.GameView,UnityEditor");
                if (gv != null) GetWindow(gv, false, "Game", true);   // Game 탭을 앞으로
                EditorApplication.EnterPlaymode();
            }
            GUI.enabled = true;

            GUILayout.Space(6);
            using (new EditorGUILayout.HorizontalScope())
            {
                if (GUILayout.Button("씬 열기", GUILayout.Height(26)))
                {
                    IremSelfTest.EnsureScene();
                    UnityEditor.SceneManagement.EditorSceneManager
                        .OpenScene("Assets/Scenes/이렘.unity");
                }
                if (GUILayout.Button("Game 탭 앞으로", GUILayout.Height(26)))
                {
                    var gv = System.Type.GetType("UnityEditor.GameView,UnityEditor");
                    if (gv != null) GetWindow(gv, false, "Game", true);
                }
                if (GUILayout.Button("자체 점검", GUILayout.Height(26)))
                {
                    IremSelfTest.Run();
                    Refresh();
                }
            }

            GUILayout.Space(10);
            GUILayout.Label("  재생 뒤 — 층을 고르고 · 슬롯을 누르고 · 잔상을 고른 뒤 · 등반",
                            EditorStyles.miniLabel);
            GUILayout.Label("  이 창은 [이렘 → 열기] 또는 F1 로 다시 부를 수 있습니다",
                            EditorStyles.miniLabel);
        }
    }

    /// 씬 뷰가 비어 보이지 않게, 원점에 안내를 띄운다.
    static class IremSceneHint
    {
        [DrawGizmo(GizmoType.NonSelected | GizmoType.Selected)]
        static void Draw(IremHint _, GizmoType __)
        {
            if (EditorApplication.isPlaying) return;
            var st = new GUIStyle(EditorStyles.boldLabel)
            {
                fontSize = 16, alignment = TextAnchor.MiddleCenter,
                normal = { textColor = new Color(0.86f, 0.72f, 0.45f) },
            };
            Handles.Label(Vector3.zero, "▶ 재생을 누르면\nGame 탭에 편성 화면이 뜹니다", st);
        }
    }
}
