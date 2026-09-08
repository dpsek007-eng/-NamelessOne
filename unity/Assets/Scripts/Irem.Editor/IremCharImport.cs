// 몸과 옷을 들여올 때의 규칙. Assets/Art/Chars 아래에 들어오는 FBX 에만 건다.
//
// 두 가지가 기본값으로 두면 반드시 어긋난다.
//
// 1. 애니메이션 형식. 몸은 휴머노이드여야 한다. 그래야 뼈 위치가 체형마다
//    달라도 애니메이션 한 벌을 다섯이 나눠 쓴다 (그것이 공용 스켈레톤을
//    고른 이유의 전부다). 블렌더에서 나온 뼈 이름이 pelvis/spine_01/
//    upperarm_l … 이라 유니티가 자동으로 짝을 찾는다.
//    반대로 옷은 제네릭이어야 한다. 옷에도 뼈 53개가 딸려 오지만 그 뼈는
//    쓰지 않고 버린다 — 입힐 때 몸의 뼈로 갈아 끼운다(IremChar.Wear).
//    옷까지 휴머노이드로 만들면 아바타 55개가 쓸데없이 생긴다.
//
// 2. 머티리얼. 블렌더가 붙여 보낸 cloth/accent 를 유니티가 읽으면
//    회색 Standard 두 장이 생긴다. 우리가 쓸 것은 실루엣 머티리얼이므로
//    아예 들여오지 않는다. 슬롯 순서(0 천, 1 강조)만 살아 있으면 된다.
using UnityEditor;
using UnityEngine;

namespace Irem.Editor
{
    public sealed class IremCharImport : AssetPostprocessor
    {
        const string Root = "/Art/Chars/";

        void OnPreprocessModel()
        {
            var p = assetPath.Replace('\\', '/');
            if (!p.Contains(Root)) return;

            var m = (ModelImporter)assetImporter;

            m.globalScale        = 1f;          // 블렌더에서 이미 미터로 나온다
            m.useFileScale       = true;
            m.importCameras      = false;
            m.importLights       = false;
            m.importVisibility   = false;
            m.importBlendShapes  = false;       // 몸의 형태는 구워서 내보냈다
            m.importAnimation    = false;       // 여기엔 애니메이션이 없다
            m.materialImportMode = ModelImporterMaterialImportMode.None;
            m.importNormals      = ModelImporterNormals.Import;   // 블렌더의 면/부드러움 그대로
            m.importTangents     = ModelImporterTangents.None;    // 노멀맵을 쓰지 않는다
            m.optimizeGameObjects = false;      // 뼈 트랜스폼이 실제로 있어야 옷을 갈아 끼운다

            if (p.Contains(Root + "Bodies/"))
            {
                m.animationType = ModelImporterAnimationType.Human;
                m.avatarSetup   = ModelImporterAvatarSetup.CreateFromThisModel;
            }
            else
            {
                m.animationType = ModelImporterAnimationType.Generic;
                m.avatarSetup   = ModelImporterAvatarSetup.NoAvatar;
            }
        }

        // 들여온 결과가 생각과 같은지 여기서 한 번 본다.
        // 뼈가 53개가 아니거나 휴머노이드 짝짓기가 실패하면 조용히 지나가지 않는다 —
        // 조용히 지나가면 나중에 "애니메이션이 안 먹는다"로만 나타난다.
        void OnPostprocessModel(GameObject go)
        {
            var p = assetPath.Replace('\\', '/');
            if (!p.Contains(Root)) return;

            var smr = go.GetComponentInChildren<SkinnedMeshRenderer>();
            if (smr == null)
            {
                Debug.LogError($"[이렘] {p} 에 스킨드 메시가 없다.");
                return;
            }
            if (smr.bones.Length != 53)
                Debug.LogWarning($"[이렘] {p} 뼈 {smr.bones.Length}개 (53 이어야 한다).");

            if (p.Contains(Root + "Bodies/"))
            {
                var anim = go.GetComponent<Animator>();
                if (anim == null || anim.avatar == null || !anim.avatar.isValid)
                    Debug.LogError($"[이렘] {p} 휴머노이드 아바타를 만들지 못했다. "
                                   + "뼈 이름이 바뀌었는지 확인할 것.");
            }
        }
    }
}
