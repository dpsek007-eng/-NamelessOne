// 뜰의 표. BattleData.cs 와 같은 규칙이다 —
// JsonUtility 는 사전을 못 읽으므로 전부 배열로 편다. 엔진도 JSON 라이브러리도 참조하지 않는다.
//
// 이 표는 tools/export_unity.py 가 쓴다. 손으로 고치지 않는다.
// 원본은 data/characters.json(잔상·관계 인연) · data/garden.json(지도·일터) ·
// tools/trades.py(생업→일터·계층) · tools/bonds.py(자동 인연 규칙) 네 곳이다.
using System;
using System.Collections.Generic;

namespace Irem.Data
{
    /// 뜰에 사는 잔상 하나. 전투의 CharDef 와 겹치는 것이 많지만 쓰는 곳이 다르다 —
    /// 여기엔 전투 수치가 없고, 대신 일터와 옷·몸의 파일 이름이 있다.
    [Serializable]
    public class AgentDef
    {
        public string id, name, role, era, cls, trade, place;
        public string body, garment;        // Art/Chars/Bodies/{body}.fbx · Garments/{garment}.fbx
        public string col, tag, idleLine;
        public string deed;                 // 뜰에서 하는 일 한 줄 (characters.json garden.desc)
        public int r, floor;
        public string[] wKeys; public float[] wVals;     // 성향의 무게 — Mind.From 이 읽는다
        public StanceBone[] stance;         // 그 사람만의 자세 (data/shades.json)

        public Dictionary<string, double> Weights()
        {
            var d = new Dictionary<string, double>();
            if (wKeys == null || wVals == null) return d;
            for (int i = 0; i < wKeys.Length && i < wVals.Length; i++) d[wKeys[i]] = wVals[i];
            return d;
        }
    }

    /// 그 사람의 자세 한 뼈. data/shades.json 의 bones 한 줄이 그대로 온다.
    ///
    /// 왜 자세가 몸에 안 구워져 있는가: 동작 네 벌이 뼈를 전부 절대값으로 찍는다
    /// (chars/src/make_demo.py base_pose — 「NLA 누수를 막는다」). 쉼자세를 굽어
    /// 놓아도 클립이 첫 프레임에 덮어쓴다. 그래서 자세는 클립이 끝난 **뒤에**
    /// 얹는 층이다 (ShadeView3D.LateUpdate · viewer/garden.html 의 mixer.update 뒤).
    ///
    /// rot 은 아마추어 축 기준 도(degree)다. 셋 다 블렌더 축으로 적혀 있고
    /// (x 앞뒤굽힘 · y 좌우기울임 · z 비틀림), 유니티 축으로 옮기는 자리는
    /// CastLoad.Stance 한 곳뿐이다.
    [Serializable]
    public class StanceBone
    {
        public string bone;
        public float[] rot;                 // 3개. 없으면 회전을 안 건다
        public float[] scale;               // 3개. 없으면 굵기를 안 건다
    }

    /// 일터 한 곳. name 은 tools/trades.py 의 place 와 같아야 한다 —
    /// 생업에서 일터를 찾는 유일한 열쇠다.
    [Serializable]
    public class StationDef
    {
        public string name, prop, desc;
        public int x, y;
        // 여기서부터가 「무엇이 서 있는가」다. tools/places.py 가 적고
        // 브라우저(viewer/garden.html)와 Ground3D 가 똑같이 세운다.
        public float z0;          // 밑바닥 높이
        public float[] face;      // 일하는 사람이 보는 쪽 [dx, dy] — 칸 단위
        public float[] work;      // 연장이 놓이는 자리 [x, y, z] — 일터 칸에서 본 상대 좌표
        public PartDef[] parts;
    }

    /// 구조물의 덩이 하나. 넷뿐이다 — box · cyl · roof · pyr.
    ///   box  p = 바닥 한가운데, s = [가로x, 세로y, 높이z]
    ///   cyl  p = 밑동 한가운데, s = [반지름, 높이], n = 몇 각
    ///   roof 박공지붕. a = "x" 면 용마루가 동서로 눕는다
    ///   pyr  사각뿔
    /// k 는 재질 자리: 0 돌 · 1 나무 · 2 쇠붙이·불빛
    [Serializable]
    public class PartDef
    {
        public string t, a;
        public int k, n;
        public float[] p, s;
    }

    /// 인연 규칙 하나. 다섯 종류를 한 꼴로 편다.
    ///   관계 — members 에 적힌 잔상이 전부 있으면 성립 (둘일 때도 있고 셋일 때도 있다)
    ///          shy 가 켜져 있으면 members[0] 이 나머지를 처음엔 피한다
    ///   생업 — a·b 두 생업이 다 있으면
    ///   계층 — a 가 na 명 이상, b 가 nb 명 이상 (a==b 면 합쳐서 na+nb 명)
    ///   최후 — role 이 max(3, 인원×ratio) 명 이상
    ///   시대 — 구역 최다 시대가 n 명 이상. 최다 하나만 성립한다
    [Serializable]
    public class BondRule
    {
        public string id, kind, title, story, reward, note;
        public string[] members;
        public string a, b, role;
        public int na, nb, n;
        public float ratio;
        public bool shy;                    // 처음엔 피한다 — 데이터가 그렇다고 적어 둔 인연만
    }

    /// 대사 뱅크 한 줄. tools/lines.py 가 미리 굽는다. 게임은 실행 중에 API 를 부르지 않는다.
    [Serializable]
    public class LineRow
    {
        public string id, bank;
        public string[] lines;
    }

    [Serializable]
    public class GardenTables
    {
        public int w, h;
        public string[] map;
        public TerrDef[] terrain;
        public AgentDef[] agents;
        public StationDef[] stations;
        public BondRule[] bonds;
        public LineRow[] lines;
        public int idleX, idleY;            // 일터 없는 잔상이 서 있는 자리
        public int activeSlots;             // 동시에 켤 수 있는 인연 수 (tools/bonds.py ACTIVE_SLOTS)

        public StationDef Station(string name)
        {
            if (stations == null) return null;
            foreach (var s in stations) if (s.name == name) return s;
            return null;
        }
        public AgentDef Agent(string id)
        {
            if (agents == null) return null;
            foreach (var a in agents) if (a.id == id) return a;
            return null;
        }
        /// 그 잔상의 그 상황 대사들. 없으면 빈 배열 — 없는 것을 만들어 내지 않는다.
        public string[] Bank(string id, string bank)
        {
            if (lines != null)
                foreach (var l in lines)
                    if (l.id == id && l.bank == bank) return l.lines ?? new string[0];
            return new string[0];
        }
    }
}
