// 몸·옷·동작을 들여올 때의 규칙. Assets/Art/Chars 아래에 들어오는 FBX 에만 건다.
//
// 세 가지가 기본값으로 두면 반드시 어긋난다.
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
//
// 3. 동작(Clips/). 여기에만 애니메이션이 있다. 몸·옷은 정지 자산이라
//    애니메이션이 짐만 되므로 블렌더에서 bake_anim=False 로 나온다
//    (chars/src/make_bodies.py). 움직이는 것은 chars/src/make_clips.py 가
//    따로 굽는 motion.fbx 한 장뿐이고, 그 안에 메시가 없다 —
//    아마추어와 테이크 여섯뿐이다.
using System.Collections.Generic;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace Irem.Editor
{
    public sealed class IremCharImport : AssetPostprocessor
    {
        const string Root = "/Art/Chars/";

        // 동작 FBX 가 아바타를 베껴 오는 몸. chars/src/make_clips.py 의
        // SRC_ROLE 과 같아야 한다 — 다른 몸에서 뜨면 뼈 위치가 어긋난다.
        public const string ClipAvatarSource = "Assets/Art/Chars/Bodies/guard.fbx";

        // 도는 동작. 나머지는 한 번 하고 멈춘다. tables.json 의 clips 와 같은 판단이다.
        static readonly HashSet<string> Looping = new HashSet<string> { "idle", "walk" };

        // 블렌더가 테이크 이름을 「<아마추어>|<트랙>」 으로 낸다 (실측: rig_guard|attack).
        // 유니티 클립 이름이 그대로 그것이 되면 Play("attack") 가 못 찾는다.
        // 그래서 막대 앞을 떼어 tables.json 의 낱말과 맞춘다.
        public static string ClipName(string take)
        {
            var i = take.LastIndexOf('|');
            return i < 0 ? take : take.Substring(i + 1);
        }

        void OnPreprocessModel()
        {
            var p = assetPath.Replace('\\', '/');
            if (!p.Contains(Root)) return;

            var m = (ModelImporter)assetImporter;
            var isClips = p.Contains(Root + "Clips/");

            m.globalScale        = 1f;          // 블렌더에서 이미 미터로 나온다
            m.useFileScale       = true;
            m.importCameras      = false;
            m.importLights       = false;
            m.importVisibility   = false;
            m.importBlendShapes  = false;       // 몸의 형태는 구워서 내보냈다
            m.importAnimation    = isClips;     // 동작은 여기 한 장에만 있다
            m.materialImportMode = ModelImporterMaterialImportMode.None;
            m.importNormals      = ModelImporterNormals.Import;   // 블렌더의 면/부드러움 그대로
            m.importTangents     = ModelImporterTangents.None;    // 노멀맵을 쓰지 않는다
            m.optimizeGameObjects = false;      // 뼈 트랜스폼이 실제로 있어야 옷을 갈아 끼운다

            if (isClips)
            {
                // 휴머노이드로 들여야 리타기팅이 걸린다. 아바타는 몸에서 베껴 온다 —
                // 여기엔 메시가 없어서 CreateFromThisModel 로는 아바타를 만들 수 없다.
                m.animationType     = ModelImporterAnimationType.Human;
                m.avatarSetup       = ModelImporterAvatarSetup.CopyFromOther;
                m.sourceAvatar      = LoadSourceAvatar();
                m.animationCompression = ModelImporterAnimationCompression.Off;
                // 키를 줄이면 블렌더에서 잰 프레임 수와 달라진다. 자체 점검이
                // 프레임 수로 동작을 확인하므로 압축을 끈다.
                m.resampleCurves    = false;
                NameClips(m);
            }
            else if (p.Contains(Root + "Bodies/"))
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

        static Avatar LoadSourceAvatar()
        {
            var av = AssetDatabase.LoadAllAssetsAtPath(ClipAvatarSource)
                                  .OfType<Avatar>().FirstOrDefault();
            if (av == null)
                Debug.LogError($"[이렘] {ClipAvatarSource} 의 아바타를 못 찾았다. "
                             + "몸을 먼저 들여와야 동작이 리타기팅된다 "
                             + "(Bodies 를 다시 임포트한 뒤 Clips 를 다시 임포트할 것).");
            return av;
        }

        // 테이크 이름을 고치고 도는 것만 loop 를 준다.
        // defaultClipAnimations 는 파일에서 읽은 테이크 목록이다. 손으로 적지 않는다 —
        // 적어 두면 동작을 한 벌 더 굽는 날 조용히 빠진다.
        static void NameClips(ModelImporter m)
        {
            var src = m.defaultClipAnimations;
            if (src == null || src.Length == 0) return;

            var outp = new ModelImporterClipAnimation[src.Length];
            for (int i = 0; i < src.Length; i++)
            {
                var c = src[i];
                c.name = ClipName(c.takeName);
                c.loopTime = Looping.Contains(c.name);
                // 쓰러짐은 마지막 자세로 끝나야 한다. loopPose 를 켜면 유니티가
                // 끝과 시작을 맞추려 들어서 죽은 사람이 일어난다.
                c.loopPose = false;
                outp[i] = c;
            }
            m.clipAnimations = outp;
        }

        // 들여온 결과가 생각과 같은지 여기서 한 번 본다.
        // 뼈가 53개가 아니거나 휴머노이드 짝짓기가 실패하면 조용히 지나가지 않는다 —
        // 조용히 지나가면 나중에 "애니메이션이 안 먹는다"로만 나타난다.
        void OnPostprocessModel(GameObject go)
        {
            var p = assetPath.Replace('\\', '/');
            if (!p.Contains(Root)) return;

            if (p.Contains(Root + "Clips/"))
            {
                CheckClips(go, p);
                return;
            }

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

        // 동작 파일에는 메시가 없다. 대신 확인할 것이 클립 쪽에 있다.
        void CheckClips(GameObject go, string p)
        {
            var m = (ModelImporter)assetImporter;

            var anim = go.GetComponent<Animator>();
            if (anim == null || anim.avatar == null || !anim.avatar.isValid)
                Debug.LogError($"[이렘] {p} 아바타가 없거나 쓸 수 없다. "
                             + $"{ClipAvatarSource} 를 먼저 들여올 것.");

            var clips = m.clipAnimations;
            if (clips == null || clips.Length == 0) clips = m.defaultClipAnimations;
            if (clips == null || clips.Length == 0)
            {
                Debug.LogError($"[이렘] {p} 에 동작이 하나도 없다. "
                             + "blender --background --python chars/src/make_clips.py 를 돌릴 것.");
                return;
            }

            // 블렌더에서 잰 것과 같은 여섯 벌인가. 없는 이름은 런타임에
            // 「그 동작 없음」으로만 나타나므로 여기서 잡는다.
            var want = new[] { "idle", "walk", "attack", "hurt", "fall", "look" };
            var have = clips.Select(c => c.name).ToArray();
            var miss = want.Where(w => !have.Contains(w)).ToArray();
            if (miss.Length > 0)
                Debug.LogError($"[이렘] {p} 동작이 빠졌다: {string.Join(", ", miss)} "
                             + $"(들어온 것: {string.Join(", ", have)})");
            if (have.Length != want.Length)
                Debug.LogWarning($"[이렘] {p} 동작 {have.Length}벌 (여섯이어야 한다): "
                               + string.Join(", ", have));
        }
    }
}
