// 시험판과 유니티가 같은 표를 읽는다. 표가 갈라지면 둘 다 틀린 것이다.
// JsonUtility 는 사전을 못 읽는다. 그래서 전부 배열로 편다.
using System;
using System.Collections.Generic;

namespace Irem.Data
{
    [Serializable] public class ClipDef  { public string name; public int from, n, fps; public bool loop; }
    [Serializable] public class TerrDef  { public string ch, name; public int mv; public float dmg; public bool block; public float def; }
    [Serializable] public class CondDef  { public string t, v; public int n; }
    [Serializable] public class RouteDef { public string id; public float pw; public CondDef[] cond; }

    [Serializable]
    public class CharDef
    {
        public string id, name, role, era, cls, trade, col, tag, traitName, traitLine, skill;
        public int r, floor, hp, atk, def, spd, pw;
        public bool gen;
        public string[] wKeys; public float[] wVals;     // 성향의 무게

        public Dictionary<string, double> Weights()
        {
            var d = new Dictionary<string, double>();
            if (wKeys == null || wVals == null) return d;
            for (int i = 0; i < wKeys.Length && i < wVals.Length; i++) d[wKeys[i]] = wVals[i];
            return d;
        }
    }

    [Serializable]
    public class FloorDef
    {
        public int n, teams, slot, need, baseReq;
        public string name, era, note, mapNote, goalKind, goalName;
        public int goalN;
        public string[] env, map;
        public RouteDef[] routes;
    }

    [Serializable]
    public class FoeDef { public string name; public int rng, mv, spd; public float hp, atk; }

    [Serializable]
    public class BattleTables
    {
        public int nf;
        public ClipDef[] clips;
        public TerrDef[] terrain;
        public CharDef[] chars;
        public FloorDef[] floors;
        public FoeDef[] foes;

        public ClipDef Clip(string n)
        {
            foreach (var c in clips) if (c.name == n) return c;
            return clips.Length > 0 ? clips[0] : null;
        }
        public Dictionary<char, object> _unused;   // 예약
    }
}
