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

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        public static void Boot() => Build(DefaultFloor, 0xC0FFEEUL);

        public static void Restart() => Build(DefaultFloor, (ulong)System.DateTime.Now.Ticks);

        public static void Build(int floorNo, ulong seed)
        {
            if (_root != null) Object.Destroy(_root);
            _root = new GameObject("이렘");

            var ta = Resources.Load<TextAsset>("Irem/tables");
            if (ta == null)
            {
                Debug.LogError("Assets/Resources/Irem/tables.json 이 없습니다. " +
                               "tools/export_unity.py 를 먼저 돌리십시오.");
                return;
            }
            var T = JsonUtility.FromJson<BattleTables>(ta.text);
            var floor = T.floors.FirstOrDefault(f => f.n == floorNo) ?? T.floors[0];

            var cam = Camera.main;
            if (cam == null)
            {
                var cgo = new GameObject("Camera");
                cgo.transform.SetParent(_root.transform, false);
                cam = cgo.AddComponent<Camera>();
                cgo.tag = "MainCamera";
            }
            cam.clearFlags = CameraClearFlags.SolidColor;

            var B = Setup.BuildBattle(T, floor, seed);
            B.Run();

            var dgo = new GameObject("Director");
            dgo.transform.SetParent(_root.transform, false);
            var dir = dgo.AddComponent<BattleDirector>();
            dir.Begin(T, floor, B, cam);
        }

    }
}
