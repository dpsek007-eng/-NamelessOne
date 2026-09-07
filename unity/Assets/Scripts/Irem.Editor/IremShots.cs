// 화면을 찍는다. -iremShots 를 붙여 실행하면 재생에 들어가 몇 장 찍고 스스로 끝낸다.
//   컴파일이 되고 오브젝트가 서 있어도, 자리가 어긋나 있으면 눈으로 봐야만 안다.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Irem.Data;
using Irem.Game;
using Irem.Sim;

namespace Irem.Editor
{
    [InitializeOnLoad]
    public static class IremShots
    {
        const string StepKey = "Irem.Shot.Step";
        const string TimeKey = "Irem.Shot.T";
        static string Dir => Environment.GetEnvironmentVariable("IREM_SHOTS") ?? "/tmp/iremshots";
        static double _t0;

        static IremShots()
        {
            if (!Environment.GetCommandLineArgs().Contains("-iremShots")) return;
            EditorApplication.update += Tick;
            _t0 = EditorApplication.timeSinceStartup;
        }

        static void Shot(string name)
        {
            Directory.CreateDirectory(Dir);
            ScreenCapture.CaptureScreenshot(Path.Combine(Dir, name));
            Debug.Log("  ○ 찍음 " + name);
        }

        static void Tick()
        {
            int step = SessionState.GetInt(StepKey, 0);
            double now = EditorApplication.timeSinceStartup;
            double since = now - SessionState.GetFloat(TimeKey, (float)now);

            switch (step)
            {
                case 0:                                   // 씬을 열고, 게임 뷰를 키우고, 재생
                    IremSelfTest.EnsureScene();
                    MaximizeGameView();
                    Next(1, now);
                    EditorApplication.EnterPlaymode();
                    break;

                case 1:
                    if (!EditorApplication.isPlaying) return;
                    Next(2, now);
                    break;

                case 2:                                   // 편성 화면
                    if (since < 2.5) return;
                    Shot("1_roster.png");
                    Next(3, now);
                    break;

                case 3:                                   // 등반
                    if (since < 1.2) return;
                    try
                    {
                        var T = IremBoot.Tables();
                        var f = T.floors.FirstOrDefault(x => x.n == 24) ?? T.floors[0];
                        IremBoot.StartBattle(f, Setup.AutoFill(T, f));
                    }
                    catch (Exception e) { Debug.LogError("등반 실패 — " + e); }
                    Next(4, now);
                    break;

                case 4: if (since < 2.0) return; Shot("2_battle_a.png"); Next(5, now); break;
                case 5: if (since < 3.0) return; Shot("3_battle_b.png"); Next(6, now); break;
                case 6: if (since < 4.0) return; Shot("4_battle_c.png"); Next(7, now); break;
                case 7:
                    if (since < 1.5) return;
                    SessionState.SetInt(StepKey, 0);
                    EditorApplication.Exit(0);
                    break;
            }
        }

        /// 게임 뷰를 창 가득 키운다. 작게 두면 찍어도 무엇이 어긋났는지 안 보인다.
        static void MaximizeGameView()
        {
            var t = Type.GetType("UnityEditor.GameView,UnityEditor");
            if (t == null) return;
            var w = EditorWindow.GetWindow(t, false, "Game", true);
            if (w != null) { w.maximized = true; w.Focus(); }
        }

        static void Next(int s, double now)
        {
            SessionState.SetInt(StepKey, s);
            SessionState.SetFloat(TimeKey, (float)now);
        }
    }
}
