// 자체 점검 — 유니티 안에서 실제로 돌아가는지 본다.
//   Unity -batchmode -quit -executeMethod Irem.Editor.IremSelfTest.Run
//
// 컴파일이 된다고 도는 것은 아니다. Resources 경로, 텍스처 임포트, 폰트,
// 시트 자르기까지 여기서 걸린다.
using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Irem.Data;
using Irem.Game;
using Irem.Sim;
using TMPro;

namespace Irem.Editor
{
    public static class IremSelfTest
    {
        static int _bad;
        static void OK(string what)   => Debug.Log("  ○ " + what);
        static void NO(string what) { _bad++; Debug.LogError("  ✕ " + what); }
        static void Check(bool cond, string what) { if (cond) OK(what); else NO(what); }

        [MenuItem("이렘/자체 점검")]
        public static void Run()
        {
            _bad = 0;
            Debug.Log("── 이렘 자체 점검 ──");

            // 1) 표
            var ta = Resources.Load<TextAsset>("Irem/tables");
            Check(ta != null, "표 읽기 Assets/Resources/Irem/tables.json");
            if (ta == null) { Done(); return; }
            var T = JsonUtility.FromJson<BattleTables>(ta.text);
            Check(T != null && T.chars != null && T.chars.Length > 0,
                  $"표 해석 — 잔상 {T?.chars?.Length}, 층 {T?.floors?.Length}, 프레임 {T?.nf}");
            Check(T.terrain != null && T.terrain.Length > 0, "지형표");
            Check(T.clips != null && T.clips.Length == 5, "동작표 5개");

            // 2) 그림
            var c0 = T.chars[0];
            var tex = ArtLoad.SheetTex(c0.id);
            Check(tex != null, $"잔상 시트 Resources/Irem/Shades/{c0.id}.png");
            if (tex != null)
                Check(tex.width == 48 * T.nf && tex.height == 64,
                      $"시트 크기 {tex.width}×{tex.height} (기대 {48 * T.nf}×64)");
            var frames = ArtLoad.Sheet(c0.id, T.nf);
            Check(frames != null && frames.Length == T.nf && frames.All(f => f != null),
                  $"시트 자르기 {frames?.Length}프레임");
            Check(ArtLoad.TileTex("plain_0") != null, "지형 타일 plain_0");
            Check(ArtLoad.TileTex("block_0") != null, "지형 타일 block_0");
            int missing = T.chars.Count(c => ArtLoad.SheetTex(c.id) == null);
            Check(missing == 0, $"잔상 {T.chars.Length}명 그림 — 빠진 것 {missing}");
            foreach (var k in new[] { "재", "잔해", "그림자" })
                Check(ArtLoad.SheetTex("foe_" + k) != null, "수호자 그림 " + k);

            // 3) 한글 폰트 — 없으면 글자가 전부 네모로 나온다
            var font = IremUI.Face(13);
            if (font == null) NO("한글 폰트를 못 찾았습니다 (Noto Sans CJK KR / 나눔고딕 등)");
            else OK("한글 폰트 " + font.name);

            // 3-b) 한글 TMP 폰트 — uGUI 는 이것으로 글자를 그린다
            var sans = Resources.Load<TMP_FontAsset>("Irem/Fonts/NanumGothic SDF");
            var serif = Resources.Load<TMP_FontAsset>("Irem/Fonts/NanumMyeongjo SDF");
            Check(sans != null, "TMP 폰트 NanumGothic SDF");
            Check(serif != null, "TMP 폰트 NanumMyeongjo SDF");
            Check(TMP_Settings.instance != null, "TMP 설정 (Assets/TextMesh Pro)");

            // 3-c) 화면을 실제로 지어 본다 — 컴파일이 된다고 서는 것은 아니다
            try
            {
                var probe = new GameObject("__probe");
                var ui = probe.AddComponent<RosterUI>();
                ui.Begin(T, T.floors[0], null);
                int n = probe.GetComponentsInChildren<Transform>(true).Length;
                int labels = probe.GetComponentsInChildren<TextMeshProUGUI>(true).Length;
                int btns = probe.GetComponentsInChildren<UnityEngine.UI.Button>(true).Length;
                Check(n > 100 && labels > 30 && btns > 10,
                      $"편성 화면 조립 — 오브젝트 {n}, 글자 {labels}, 단추 {btns}");
                UnityEngine.Object.DestroyImmediate(probe);
                var es = UnityEngine.Object.FindFirstObjectByType<UnityEngine.EventSystems.EventSystem>();
                if (es != null) UnityEngine.Object.DestroyImmediate(es.gameObject);
            }
            catch (Exception e) { NO("편성 화면 조립 중 예외 — " + e.Message + "\n" + e.StackTrace); }

            // 4) 판정
            try
            {
                var f = T.floors.FirstOrDefault(x => x.n == IremBoot.DefaultFloor) ?? T.floors[0];
                var teams = Setup.AutoFill(T, f);
                Check(teams.Sum(t => t.Count) > 0, $"자동 편성 {teams.Sum(t => t.Count)}명");
                var B = Setup.BuildBattle(T, f, 12345);
                B.Run();
                Check(B.Events.Count > 0,
                      $"{f.n}층 전투 — {B.Round}턴, 사건 {B.Events.Count}개, " +
                      $"{(B.Win ? "승" : "패")} ({B.Reason})");
            }
            catch (Exception e) { NO("전투 중 예외 — " + e.Message + "\n" + e.StackTrace); }

            // 5) 뜰 — 3D 쪽. 표·몸·옷·동작이 다 있어야 한 사람이 선다.
            var gta = Resources.Load<TextAsset>("Irem/garden");
            Check(gta != null, "뜰 표 읽기 Assets/Resources/Irem/garden.json");
            if (gta != null)
            {
                var G = JsonUtility.FromJson<GardenTables>(gta.text);
                Check(G != null && G.agents != null && G.agents.Length > 0,
                      $"뜰 표 해석 — 잔상 {G?.agents?.Length}, 일터 {G?.stations?.Length}, "
                    + $"인연 규칙 {G?.bonds?.Length}, 지도 {G?.w}×{G?.h}");
                Check(IremGardenScene.Ready() == 0, "뜰 자산 — 표·몸·옷·동작·땅");

                // 5-b) 뜰을 실제로 굴려 본다. 순수 C# 쪽이라 유니티가 없어도 도는 곳이지만
                //      (Tools/GardenRunner 가 도커로 재는 자리다) 여기서도 한 번 본다 —
                //      유니티가 읽은 표로 도는지는 유니티에서만 알 수 있다.
                if (G != null && G.agents != null && G.agents.Length > 0)
                {
                    try
                    {
                        var g = GardenSetup.Build(G, 42);
                        for (int i = 0; i < 100; i++) g.Tick();
                        int atWork = g.Cast.Count(s => s.AtWork);
                        int active = g.Found.Count(b => b.Active);
                        Check(g.Log.Count > 0,
                              $"뜰 100걸음 — 사건 {g.Log.Count}건, 일터에 선 잔상 {atWork}/{g.Cast.Count}, "
                            + $"성립한 인연 {g.Found.Count} 가운데 발동 {active}");
                    }
                    catch (Exception e) { NO("뜰 계산 중 예외 — " + e.Message + "\n" + e.StackTrace); }

                    // 5-c) 몸을 실제로 세워 본다. 컴파일이 된다고 스물셋이 서는 것은 아니다.
                    try
                    {
                        var probe = new GameObject("__garden");
                        // 카메라를 준다. 뜰은 카메라를 잡아 각도와 거리를 정하므로
                        // (GardenDirector.FrameCamera) 없으면 세울 수가 없다.
                        var pcam = probe.AddComponent<Camera>();
                        var g = GardenSetup.Build(G, 42);
                        var dir = probe.AddComponent<GardenDirector>();
                        dir.Begin(G, g, pcam);
                        int bodies = 0, bones = 0;
                        foreach (var sm in probe.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                        { bodies++; bones += sm.bones?.Length ?? 0; }
                        int views = probe.GetComponentsInChildren<ShadeView3D>(true).Length;
                        Check(views == g.Cast.Count,
                              $"뜰 조립 — 잔상 {views}/{g.Cast.Count}, 스킨 메시 {bodies}, 뼈 {bones}");

                        // 자세가 실제로 뼈에 닿았는가. 브라우저 쪽은 실측했다 —
                        // 적힌 열여덟 값이 소수점까지 그대로 나왔다(tools/probe.py --stance).
                        // 유니티 쪽은 여기가 유일하게 재는 자리다.
                        int wantStance = G.agents.Count(x => x.stance != null && x.stance.Length > 0);
                        int wantBones  = G.agents.Sum(x => x.stance?.Length ?? 0);
                        int gotStance = 0, gotBones = 0;
                        foreach (var sv in probe.GetComponentsInChildren<ShadeView3D>(true))
                        {
                            int n = sv.StanceBones;
                            if (n > 0) { gotStance++; gotBones += n; }
                        }
                        Check(gotStance == wantStance && gotBones == wantBones,
                              $"자세 — 얹힌 사람 {gotStance}/{wantStance}, 뼈 {gotBones}/{wantBones}");
                        // 부호는 여기서 못 잰다. 세렌의 등이 앞으로 굽는지 뒤로 젖혀지는지는
                        // 눈으로 봐야 한다 — 고칠 자리는 CastLoad.Stance 한 곳이다.
                        for (int i = 0; i < 100; i++) dir.PlayStep();
                        Check(dir.ShownTurn > 0,
                              $"뜰 재생 100걸음 — {dir.ShownTurn}걸음째, 일한 걸음 {dir.WorkSteps}, "
                            + $"말을 건 인연 {dir.Spoken}");
                        UnityEngine.Object.DestroyImmediate(probe);
                        var ges = UnityEngine.Object
                            .FindFirstObjectByType<UnityEngine.EventSystems.EventSystem>();
                        if (ges != null) UnityEngine.Object.DestroyImmediate(ges.gameObject);
                    }
                    catch (Exception e) { NO("뜰 조립 중 예외 — " + e.Message + "\n" + e.StackTrace); }
                }
            }

            // 6) 신 — 없으면 열어도 아무것도 안 보인다
            EnsureScene();
            Done();
        }

        /// 빈 신을 만들고 빌드 설정의 첫 신으로 넣는다.
        /// 신이 없으면 프로젝트를 열었을 때 이름 없는 빈 신이 뜨고,
        /// 재생을 누르기 전에는 화면에 아무것도 없다.
        public static void EnsureScene()
        {
            const string dir = "Assets/Scenes", path = dir + "/이렘.unity";
            if (!AssetDatabase.IsValidFolder(dir)) AssetDatabase.CreateFolder("Assets", "Scenes");

            var sc = AssetDatabase.LoadAssetAtPath<SceneAsset>(path) == null
                ? EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single)
                : EditorSceneManager.OpenScene(path, OpenSceneMode.Single);

            // 재생 전에도 화면에 무엇이 보이게 — 빈 화면은 고장과 구별되지 않는다
            if (UnityEngine.Object.FindFirstObjectByType<Irem.Game.IremHint>() == null)
            {
                var go = new GameObject("이렘 · 재생을 누르십시오");
                go.AddComponent<Irem.Game.IremHint>();
                OK("안내 오브젝트 넣음");
            }
            EditorSceneManager.MarkSceneDirty(sc);
            EditorSceneManager.SaveScene(sc, path);
            AssetDatabase.Refresh();
            OK("신 " + path);

            var list = EditorBuildSettings.scenes.ToList();
            if (!list.Any(s => s.path == path))
            {
                list.Insert(0, new EditorBuildSettingsScene(path, true));
                EditorBuildSettings.scenes = list.ToArray();
                OK("빌드 설정 첫 신으로 등록");
            }
        }

        static void Done()
        {
            if (_bad == 0) Debug.Log("── 점검 통과. 재생을 누르면 편성 화면이 뜹니다. ──");
            else Debug.LogError($"── 점검 실패 {_bad}건 ──");
            if (Application.isBatchMode) EditorApplication.Exit(_bad == 0 ? 0 : 1);
        }
    }
}
