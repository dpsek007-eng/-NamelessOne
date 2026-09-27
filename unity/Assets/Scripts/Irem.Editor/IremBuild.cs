// [이렘/웹으로 굽기] — 뜰을 WebGL 로 굽는다.
//
//   Unity -batchmode -quit -nographics -buildTarget WebGL \
//         -executeMethod Irem.Editor.IremBuild.WebGL
//
// 왜 뜰 신 하나만 굽는가. IremBoot 가 신 이름을 보고 무엇을 세울지 정한다 —
// 이름이 「뜰」이면 편성 화면 대신 뜰을 돈다(IremBoot.GardenScene). 그래서 구울 신을
// 고르는 것이 곧 무엇을 보여 줄지 고르는 것이다.
//
// viewer/garden.html 과 같은 것을 보여 주지만 다른 물건이다. 저쪽은 구운 사건 목록을
// three.js 가 재생하는 것이고, 이쪽은 유니티가 제 손으로 계산해서 도는 것이다.
// 저쪽이 통과해도 이쪽은 모른다 — 그래서 이것을 굽는다.
using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEngine;

namespace Irem.Editor
{
    public static class IremBuild
    {
        const string Scene = "Assets/Scenes/뜰.unity";
        const string Out   = "build/web";

        [MenuItem("이렘/웹으로 굽기")]
        public static void WebGL()
        {
            // 1) 뜰 신을 먼저 짓는다. 없는 채로 구우면 검은 화면이 나오고,
            //    검은 화면은 고장과 구별되지 않는다(IremGardenScene 머리말).
            IremGardenScene.Build();

            // 2) 이 신 하나만 굽는다. 편성 화면은 웹으로 보여 줄 것이 아니다.
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(Scene, true) };

            // 3) 압축을 끈다. 압축해서 구우면 서버가 Content-Encoding 머리를 붙여 줘야 하고,
            //    붙이지 않으면 브라우저가 파일을 못 푼다. 정적 서버로 그냥 내주려고 끈다.
            PlayerSettings.WebGL.compressionFormat = WebGLCompressionFormat.Disabled;
            PlayerSettings.runInBackground = true;

            if (EditorUserBuildSettings.activeBuildTarget != BuildTarget.WebGL)
                EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.WebGL,
                                                                BuildTarget.WebGL);

            var dir = Path.Combine(Directory.GetCurrentDirectory(), Out);
            Directory.CreateDirectory(dir);

            var rep = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { Scene },
                locationPathName = dir,
                target = BuildTarget.WebGL,
                options = BuildOptions.None,
            });

            var s = rep.summary;
            long mb = s.totalSize / (1024 * 1024);
            if (s.result == BuildResult.Succeeded)
                Debug.Log($"[이렘] 구웠다 {Out} — {mb}MB, {s.totalTime.TotalMinutes:F1}분, "
                        + $"오류 {s.totalErrors}, 경고 {s.totalWarnings}");
            else
                Debug.LogError($"[이렘] 굽기 실패 — {s.result}, 오류 {s.totalErrors}");

            if (Application.isBatchMode)
                EditorApplication.Exit(s.result == BuildResult.Succeeded ? 0 : 1);
        }
    }
}
