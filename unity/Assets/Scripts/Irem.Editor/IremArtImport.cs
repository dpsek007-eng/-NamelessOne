// 잔상 그림은 픽셀이다. 유니티가 기본값으로 뭉개면 다른 그림이 된다.
// Assets/Resources/Irem 아래 들어오는 것은 전부 점 필터·무압축으로 고정한다.
using UnityEditor;
using UnityEngine;

namespace Irem.Editor
{
    public sealed class IremArtImport : AssetPostprocessor
    {
        void OnPreprocessTexture()
        {
            if (!assetPath.Replace('\\', '/').Contains("/Resources/Irem/")) return;
            var t = (TextureImporter)assetImporter;
            t.textureType         = TextureImporterType.Sprite;
            t.spriteImportMode    = SpriteImportMode.Single;   // 자르기는 런타임에서 한다
            t.filterMode          = FilterMode.Point;
            t.mipmapEnabled       = false;
            t.alphaIsTransparency = true;
            t.spritePixelsPerUnit = 16;
            t.wrapMode            = TextureWrapMode.Clamp;
            t.textureCompression  = TextureImporterCompression.Uncompressed;
            t.maxTextureSize      = 4096;
        }
    }

    public static class IremMenu
    {
        [MenuItem("이렘/전투 보기 %#i")]
        public static void Rebuild()
        {
            if (Application.isPlaying) Irem.Game.IremBoot.Restart();
            else EditorApplication.EnterPlaymode();
        }

        /// 빈 신을 하나 만들어 저장한다. IremBoot 가 재생할 때 나머지를 다 세운다.
        [MenuItem("이렘/신 만들기")]
        public static void MakeScene()
        {
            var dir = "Assets/Scenes";
            if (!AssetDatabase.IsValidFolder(dir)) AssetDatabase.CreateFolder("Assets", "Scenes");
            var sc = UnityEditor.SceneManagement.EditorSceneManager.NewScene(
                UnityEditor.SceneManagement.NewSceneSetup.DefaultGameObjects,
                UnityEditor.SceneManagement.NewSceneMode.Single);
            UnityEditor.SceneManagement.EditorSceneManager.SaveScene(sc, dir + "/이렘.unity");
            Debug.Log("Assets/Scenes/이렘.unity 를 만들었습니다. 재생을 누르면 전투가 섭니다.");
        }

        /// 층은 편성 화면에서 고른다. 이 메뉴는 거기로 돌려보낼 뿐이다.
        [MenuItem("이렘/편성 화면으로")]
        public static void ToRoster()
        {
            if (Application.isPlaying) Irem.Game.IremBoot.ShowRoster();
            else EditorApplication.EnterPlaymode();
        }
    }
}
