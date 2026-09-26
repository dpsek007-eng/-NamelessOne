// [이렘/뜰 신] — 0층 뜰을 여는 신을 짓는다.
//
// 캐릭터 확인 신과 다르게, 여기서는 뜰을 에디터에서 미리 세우지 않는다. 이유 둘이다.
//
//   1. 뜰은 움직이는 것이 전부다. 잔상 스물셋이 걸어가 일하는 것을 보려면
//      Update 가 돌아야 하고, 그것은 재생을 눌러야 돈다. 미리 세워 둔 뜰은
//      멈춰 선 스물셋일 뿐이라 「굳었다」와 구별되지 않는다.
//   2. 스킨 메시 스물셋을 신 파일에 굽으면 손으로 읽을 수 없는 .unity 가 수십 MB 로
//      커진다. 이 저장소는 신을 코드로 짓는다(IremBoot 머리말).
//
// 그래서 이 메뉴는 빈 신 하나(카메라 + 안내)를 「뜰」이라는 이름으로 저장하고,
// 재생을 누르면 IremBoot 가 그 이름을 보고 뜰을 돌린다.
//
// 대신 짓기 전에 필요한 것이 다 있는지 여기서 본다. 없는 채로 재생을 누르면
// 검은 화면이 뜨고, 검은 화면은 고장과 구별되지 않는다.
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Irem.Data;
using Irem.Game;

namespace Irem.Editor
{
    public static class IremGardenScene
    {
        const string Dir   = "Assets/Scenes";
        const string Scene = Dir + "/뜰.unity";

        [MenuItem("이렘/뜰 신")]
        public static void Build()
        {
            int bad = Ready();

            if (!AssetDatabase.IsValidFolder(Dir)) AssetDatabase.CreateFolder("Assets", "Scenes");
            var sc = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // 카메라만 둔다. 뜰이 이것을 잡아 원근으로 바꾸고 각도를 준다(GardenDirector).
            var camGo = new GameObject("카메라");
            var cam = camGo.AddComponent<Camera>();
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color32(0x14, 0x12, 0x10, 255);
            camGo.tag = "MainCamera";

            // 빛은 두지 않는다 — Irem/Silhouette 이 제 빛 방향을 들고 있고 땅은 빛을 안 받는다.
            // 씬에 광원을 넣으면 실루엣이 깨진다(GardenDirector 머리말).

            var hint = new GameObject("이렘 · 재생을 누르면 뜰이 돕니다");
            hint.AddComponent<IremHint>();

            EditorSceneManager.MarkSceneDirty(sc);
            EditorSceneManager.SaveScene(sc, Scene);
            AssetDatabase.Refresh();

            Debug.Log(bad == 0
                ? $"[이렘] {Scene} — 재생을 누르면 뜰이 돈다. "
                + "멈춤·속도·놓기·인연 단추가 오른쪽 아래에 있고, 이름표를 누르면 그 사람을 따라간다."
                : $"[이렘] {Scene} 는 지었지만 빠진 것이 {bad}건이다. 위 오류를 먼저 볼 것 — "
                + "그대로 재생하면 화면이 비거나 몸이 안 선다.");
        }

        /// 뜰에 필요한 것이 다 있는가. 있는 것만 있다고 말한다.
        public static int Ready()
        {
            int bad = 0;
            void No(string s) { bad++; Debug.LogError("[이렘] " + s); }

            var ta = Resources.Load<TextAsset>("Irem/garden");
            if (ta == null)
                No("Assets/Resources/Irem/garden.json 이 없다. tools/export_unity.py 를 돌릴 것.");
            else
            {
                var T = JsonUtility.FromJson<GardenTables>(ta.text);
                if (T == null || T.agents == null || T.agents.Length == 0)
                    No("garden.json 에 잔상이 없다.");
                else
                {
                    Debug.Log($"  ○ 뜰 표 — 잔상 {T.agents.Length}, 일터 {T.stations?.Length}, "
                            + $"인연 규칙 {T.bonds?.Length}, 지도 {T.w}×{T.h}");
                    // 몸·옷 FBX 가 실제로 있는가. 하나만 없어도 그 사람이 안 선다.
                    var missBody = T.agents.Select(a => a.body).Distinct()
                                    .Where(b => CastLoad.Body(b) == null).ToArray();
                    var missWear = T.agents.Select(a => a.garment).Distinct()
                                    .Where(g => CastLoad.Garment(g) == null).ToArray();
                    if (missBody.Length > 0) No("몸 FBX 가 없다: " + string.Join(", ", missBody));
                    if (missWear.Length > 0) No("옷 FBX 가 없다: " + string.Join(", ", missWear));

                    // 일터 소품은 없어도 뜰이 돈다 — 이름표만 남는다. 그래서 경고다.
                    var missProp = (T.stations ?? new StationDef[0])
                                    .Where(s => CastLoad.Prop(s.prop) == null)
                                    .Select(s => s.name).ToArray();
                    if (missProp.Length > 0)
                        Debug.LogWarning("[이렘] 일터 소품이 없다(이름표만 선다): "
                                       + string.Join(", ", missProp));
                }
            }

            var clips = CastLoad.Clips;
            if (clips == null || clips.Length == 0)
                No($"{CastLoad.ClipFbx} 에서 동작을 하나도 못 읽었다. "
                 + "blender --background --python chars/src/make_clips.py 를 돌릴 것.");
            else
            {
                var want = new[] { "idle", "walk", "attack", "hurt", "fall", "look" };
                var have = clips.Select(c => c.name).ToArray();
                var miss = want.Where(w => !have.Contains(w)).ToArray();
                if (miss.Length > 0)
                    No("동작이 빠졌다: " + string.Join(", ", miss)
                     + " (들어온 것: " + string.Join(", ", have) + ")");
                else Debug.Log($"  ○ 동작 {have.Length}벌 — {string.Join(", ", have)}");
            }

            if (CastLoad.Silhouette == null) No("Irem/Silhouette 셰이더가 없다.");
            if (ArtLoad.TileTex("plain_0") == null) No("땅 타일 plain_0 이 없다.");
            return bad;
        }

        // ── 전투를 3D 로 ────────────────────────────────────────────
        // 재생을 누르면 정적 필드가 날아가므로 켠 값을 EditorPrefs 에 둔다.
        [MenuItem("이렘/전투를 3D 로")]
        public static void ToggleSolid()
        {
            bool on = !EditorPrefs.GetBool(IremBoot.SolidPref, false);
            EditorPrefs.SetBool(IremBoot.SolidPref, on);
            IremBoot.Solid = on;
            Debug.Log(on
                ? "[이렘] 전투를 3D 로 보여 준다. 몸 FBX 와 동작 FBX 가 있어야 돈다."
                : "[이렘] 전투를 2D 로 보여 준다(기본).");
        }

        [MenuItem("이렘/전투를 3D 로", true)]
        public static bool ToggleSolidCheck()
        {
            Menu.SetChecked("이렘/전투를 3D 로", EditorPrefs.GetBool(IremBoot.SolidPref, false));
            return true;
        }
    }
}
