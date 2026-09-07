// 한글 TMP 폰트 에셋을 만든다.
//
//   OS 폰트에 기대면 안 된다 — 안드로이드·iOS 빌드에서 그 폰트가 있으리라는 보장이 없다.
//   나눔글꼴(OFL)을 프로젝트에 넣고, 동적(Dynamic) 아틀라스로 굽는다.
//   동적이면 2350자를 미리 다 굽지 않고 쓰는 글자만 그때그때 올린다.
using System.IO;
using TMPro;
using UnityEditor;
using UnityEngine;
using UnityEngine.TextCore.LowLevel;

namespace Irem.Editor
{
    public static class IremFont
    {
        public const string Dir  = "Assets/Resources/Irem/Fonts";
        public const string Sans = Dir + "/NanumGothic SDF.asset";
        public const string Serif = Dir + "/NanumMyeongjo SDF.asset";

        /// TMP 는 프로젝트에 TMP_Settings 가 있어야 폰트 에셋을 만들 수 있다.
        /// 없으면 CreateFontAsset 안에서 널 참조로 죽는다. 먼저 넣어 준다.
        public static void EnsureTMPResources()
        {
            if (TMP_Settings.instance != null) return;
            // 배치 모드에서는 ImportPackage 가 비동기라 -quit 전에 끝나지 않는다.
            // 저장소에는 이미 풀어 둔 Assets/TextMesh Pro 가 들어 있다.
            Debug.LogError("Assets/TextMesh Pro 가 없습니다. " +
                "Window → TextMeshPro → Import TMP Essential Resources 를 하거나, " +
                "저장소의 Assets/TextMesh Pro 폴더를 되살리십시오.");
        }

        [MenuItem("이렘/폰트 만들기")]
        public static void Build()
        {
            EnsureTMPResources();
            Make("Assets/Fonts/NanumGothic.ttf", Sans);
            Make("Assets/Fonts/NanumMyeongjo.ttf", Serif);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log("이렘 — TMP 폰트 에셋을 만들었습니다.");
        }

        public static bool Ensure()
        {
            EnsureTMPResources();
            bool made = false;
            if (AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(Sans) == null)  { Make("Assets/Fonts/NanumGothic.ttf", Sans); made = true; }
            if (AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(Serif) == null) { Make("Assets/Fonts/NanumMyeongjo.ttf", Serif); made = true; }
            if (made) { AssetDatabase.SaveAssets(); AssetDatabase.Refresh(); }
            return AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(Sans) != null;
        }

        static void Make(string ttf, string outPath)
        {
            var src = AssetDatabase.LoadAssetAtPath<Font>(ttf);
            if (src == null) { Debug.LogError("폰트가 없습니다: " + ttf); return; }

            if (!Directory.Exists(Dir)) Directory.CreateDirectory(Dir);

            var fa = TMP_FontAsset.CreateFontAsset(
                src,
                samplingPointSize: 64,
                atlasPadding: 6,
                renderMode: GlyphRenderMode.SDFAA,
                atlasWidth: 1024, atlasHeight: 1024,
                atlasPopulationMode: AtlasPopulationMode.Dynamic,
                enableMultiAtlasSupport: true);
            if (fa == null) { Debug.LogError("폰트 에셋을 만들지 못했습니다: " + ttf); return; }

            fa.name = Path.GetFileNameWithoutExtension(outPath);
            var old = AssetDatabase.LoadAssetAtPath<TMP_FontAsset>(outPath);
            if (old != null) AssetDatabase.DeleteAsset(outPath);
            AssetDatabase.CreateAsset(fa, outPath);

            // 아틀라스 텍스처와 머티리얼도 같은 에셋 안에 넣는다
            if (fa.atlasTextures != null)
                foreach (var t in fa.atlasTextures)
                    if (t != null && !AssetDatabase.Contains(t))
                    { t.name = fa.name + " Atlas"; AssetDatabase.AddObjectToAsset(t, fa); }
            if (fa.material != null && !AssetDatabase.Contains(fa.material))
            { fa.material.name = fa.name + " Material"; AssetDatabase.AddObjectToAsset(fa.material, fa); }

            EditorUtility.SetDirty(fa);
            Debug.Log("  ○ 폰트 에셋 " + outPath);
        }
    }
}
