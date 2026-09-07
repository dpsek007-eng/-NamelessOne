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
        static FloorDef _last;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        public static void Boot() => ShowRoster();

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
            dgo.AddComponent<BattleDirector>().Begin(T, floor, B, cam);
        }

    }
}
