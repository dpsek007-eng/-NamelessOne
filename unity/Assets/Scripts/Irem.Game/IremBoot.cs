// 빈 신에서 재생을 누르면 이것이 전부 세운다.
// 신 파일(.unity)을 손으로 쓰지 않는다 — 손으로 쓴 YAML 은 깨지기 쉽다.
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Irem.Data;
using Irem.Sim;

namespace Irem.Game
{
    public static class IremBoot
    {
        public const int DefaultFloor = 24;
        static GameObject _root;
        static BattleTables _T;
        static GardenTables _G;
        static FloorDef _last;

        /// 전투를 3D 로 볼 것인가. 기본은 2D 다 — 2D 가 지금 도는 게임이고
        /// 실루엣 판정 도구이기도 하다. 3D 쪽은 몸 FBX 와 동작 FBX 가 들어와 있어야 돈다.
        ///
        /// 에디터에서는 메뉴([이렘/전투를 3D 로])가 켠 값을 기억한다. 재생을 누르면
        /// 정적 필드가 날아가므로(도메인 다시 읽기) 켠 값을 EditorPrefs 에 둔다.
        public static bool Solid =
#if UNITY_EDITOR
            UnityEditor.EditorPrefs.GetBool(SolidPref, false);
#else
            false;
#endif
        public const string SolidPref = "이렘.전투3D";

        /// 확인용으로 지은 신에서는 아무것도 세우지 않는다.
        /// 편성 화면이 전체 화면을 덮어서 늘어놓은 잔상을 다 가려 버린다.
        public const string CharScene = "캐릭터";

        /// 뜰 신. 이름이 이것이면 편성 화면 대신 뜰을 돌린다([이렘/뜰 신]이 짓는다).
        public const string GardenScene = "뜰";

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        public static void Boot()
        {
            var scene = UnityEngine.SceneManagement.SceneManager.GetActiveScene().name;
            if (scene == CharScene) return;
            if (scene == GardenScene) { ShowGarden(); return; }
            ShowRoster();
        }

        /// 표는 한 번만 읽는다
        public static BattleTables Tables()
        {
            if (_T != null) return _T;
            var ta = Resources.Load<TextAsset>("Irem/tables");
            if (ta == null)
            {
                Debug.LogError("Assets/Resources/Irem/tables.json 이 없습니다. " +
                               "tools/export_unity.py 를 먼저 돌리십시오.");
                return null;
            }
            _T = JsonUtility.FromJson<BattleTables>(ta.text);
            return _T;
        }

        /// 뜰의 표. 전투 표와 따로 읽는다 — 전투만 하는 사람이 뜰 표를 기다릴 이유가 없다.
        /// 없으면 없다고 말하고 null 을 돌려준다. 없는 것을 만들어 내지 않는다.
        public static GardenTables GardenTable()
        {
            if (_G != null) return _G;
            var ta = Resources.Load<TextAsset>("Irem/garden");
            if (ta == null)
            {
                Debug.LogError("Assets/Resources/Irem/garden.json 이 없습니다. " +
                               "tools/export_unity.py 를 먼저 돌리십시오.");
                return null;
            }
            _G = JsonUtility.FromJson<GardenTables>(ta.text);
            return _G;
        }

        static Camera Fresh(string name)
        {
            if (_root != null) Object.Destroy(_root);
            _root = new GameObject(name);
            var cam = Camera.main;
            if (cam == null)
            {
                var cgo = new GameObject("Camera");
                cgo.transform.SetParent(_root.transform, false);
                cam = cgo.AddComponent<Camera>();
                cgo.tag = "MainCamera";
            }
            cam.clearFlags = CameraClearFlags.SolidColor;
            return cam;
        }

        /// 편성 화면. 여기서 시작한다.
        public static void ShowRoster(FloorDef floor = null)
        {
            var T = Tables(); if (T == null) return;
            var cam = Fresh("이렘 · 편성");
            var go = new GameObject("Roster");
            go.transform.SetParent(_root.transform, false);
            go.AddComponent<RosterUI>()
              .Begin(T, floor ?? _last ?? T.floors.FirstOrDefault(f => f.n == DefaultFloor) ?? T.floors[0], cam);
        }

        /// 사람이 짠 편성으로 등반한다
        public static void StartBattle(FloorDef floor, System.Collections.Generic.List<
                                       System.Collections.Generic.List<CharDef>> teams)
            => Build(floor, teams, (ulong)System.DateTime.Now.Ticks);

        public static void Restart()
        {
            if (_last != null) Build(_last, null, (ulong)System.DateTime.Now.Ticks);
            else ShowRoster();
        }

        public static void Build(FloorDef floor,
                                 System.Collections.Generic.List<
                                 System.Collections.Generic.List<CharDef>> teams, ulong seed)
        {
            var T = Tables(); if (T == null) return;
            _last = floor;
            var cam = Fresh("이렘 · 전투");

            var B = Setup.BuildBattle(T, floor, seed, teams);
            B.Run();

            var dgo = new GameObject("Director");
            dgo.transform.SetParent(_root.transform, false);
            if (Solid)
            {
                // 3D 는 몸·옷 슬러그가 필요하고 그것은 뜰 표에만 있다(Battle3DDirector 머리말).
                var G = GardenTable();
                if (G != null)
                {
                    dgo.AddComponent<Battle3DDirector>().Begin(T, G, floor, B, cam);
                    return;
                }
                Debug.LogWarning("[이렘] 뜰 표가 없어 전투를 2D 로 보여 준다.");
            }
            dgo.AddComponent<BattleDirector>().Begin(T, floor, B, cam);
        }

        /// 0층 — 뜰. 여기서는 시간이 흐르지 않는다(docs/03-뜰.md).
        /// 끝이 없으므로 결과 화면이 없고, 재생이 계산을 따라잡으면 한 걸음을 더 굴린다.
        public static void ShowGarden(ulong seed = 42)
        {
            var G = GardenTable(); if (G == null) return;
            var cam = Fresh("이렘 · 뜰");
            var g = GardenSetup.Build(G, seed);
            var dgo = new GameObject("Director");
            dgo.transform.SetParent(_root.transform, false);
            dgo.AddComponent<GardenDirector>().Begin(G, g, cam);
        }

    }
}
