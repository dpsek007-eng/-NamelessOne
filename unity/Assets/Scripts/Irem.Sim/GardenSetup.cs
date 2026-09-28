// 뜰 세우기 — 표에 적힌 잔상을 뜰에 세운다. Setup.cs 와 같은 자리다.
//
//   일터는 생업에서 나온다. 「모든 캐릭터는 생전에 하던 일을 뜰에서 그대로 한다」(docs/03-뜰.md).
//   생업 → 일터는 tools/trades.py 의 place 가 유일한 근거이고, 표로 이미 넘어와 있다.
//
//   같은 일터에 넷이 모이는 곳도 있다(기록관). 한 칸에 넷이 설 수는 없으므로
//   일터 칸부터 고리처럼 퍼져 나가며 각자의 자리를 하나씩 잡는다.
//   고리를 도는 순서가 자리를 정하므로 그 순서 자체가 사양이다.
using System;
using System.Collections.Generic;
using Irem.Data;

namespace Irem.Sim
{
    public static class GardenSetup
    {
        public static Grid BuildGrid(GardenTables T)
        {
            var ter = new Dictionary<char, Terrain>();
            if (T.terrain != null)
                foreach (var t in T.terrain)
                    ter[t.ch.Length > 0 ? t.ch[0] : '.'] = new Terrain
                    {
                        Name = t.name, Move = t.mv, Dmg = t.dmg, Block = t.block, Def = t.def,
                    };
            return new Grid(T.map, ter);
        }

        /// 표에 적힌 잔상 전원을 뜰에 세운다. 시드는 서성임에만 쓰인다 —
        /// 자리와 일터는 시드와 무관하게 정해진다. 그래야 같은 배치가 같은 뜰이다.
        public static Garden Build(GardenTables T, ulong seed)
        {
            var g = BuildGrid(T);
            var G = new Garden(T, g, seed);
            var used = new HashSet<int>();

            // 일터 자리부터 잡는다. 표에 적힌 잔상 순서대로 가까운 칸을 가져간다.
            foreach (var a in T.agents)
            {
                var st = T.Station(a.place);
                var s = new GardenShade
                {
                    Idx = G.Cast.Count,
                    Def = a,
                    Heart = Heart.From(a.Weights()),
                    Mv = Setup.MoveOf(a.role),
                    Sight = Setup.SightOf(a.role),
                    // 소금은 섞은 뒤에 뽑는다. Rng 는 씨의 맨 아래 비트를 1 로 세우므로
                    // (Rng.cs: _s = seed | 1) `seed ^ (i+1)` 은 두 사람씩 같은 씨가 됐다.
                    // 실측: 스물셋의 소금이 열한 쌍으로 겹쳐, 두 사람이 같은 걸음에
                    // 같은 자리의 대사를 골랐다. 큰 홀수를 곱해 윗비트까지 벌린다.
                    Salt = (int)(new Rng(seed + 0x9E3779B97F4A7C15UL * (ulong)(G.Cast.Count + 1))
                                 .Next() & 0x7fffffff),
                    Place = st != null ? st.name : "",
                };
                // 박자는 소금에서만 낸다. 시드가 같으면 같은 사람이 같은 박자로 움직인다.
                s.Phase  = (s.Salt % 997) / 997f;                      // 0 ~ 1
                s.Tempo  = 0.86f + (s.Salt / 997 % 29) * 0.01f;        // 0.86 ~ 1.14
                s.Breath = 0.15f + (s.Salt / 29 % 41) * 0.03f;         // 0.15 ~ 1.35초
                int wx, wy;
                if (st != null) Free(g, used, st.x, st.y, s.Mv, out wx, out wy);
                else            Free(g, used, T.idleX, T.idleY, s.Mv, out wx, out wy);
                s.Wx = wx; s.Wy = wy;
                used.Add(wy * g.W + wx);
                G.Cast.Add(s);
            }

            // 잔상은 전부 성문으로 내려온다. 거기서부터 제 일터로 걸어간다.
            var gate = T.Station("성문");
            int gx = gate != null ? gate.x : T.idleX, gy = gate != null ? gate.y : T.idleY;
            var stood = new HashSet<int>();
            foreach (var s in G.Cast)
            {
                Free(g, stood, gx, gy, s.Mv, out int x, out int y);
                s.X = x; s.Y = y;
                stood.Add(y * g.W + x);
            }

            G.Reckon();
            return G;
        }

        static readonly int[] DX = { 0, 1, -1, 0, 0, 1, 1, -1, -1 };
        static readonly int[] DY = { 0, 0, 0, 1, -1, 1, -1, 1, -1 };

        /// (cx,cy) 에서 고리처럼 퍼져 나가며 아직 아무도 안 잡은 딛을 수 있는 칸을 찾는다.
        ///
        /// 한 걸음에 들어설 수 없는 칸은 자리로 잡지 않는다(mv 보다 비싼 칸).
        /// 실측: 우물 옆 물칸(값 3)을 걸음 2인 헌신의 일터로 잡아 두면 그 잔상은
        /// 제 일터에 영원히 들어서지 못한다. 지형 설명이 「우물물. 건너지 않는다」인 이유다.
        static void Free(Grid g, HashSet<int> used, int cx, int cy, int mv, out int ox, out int oy)
        {
            bool Ok(int x, int y) => g.Passable(x, y) && g.Cost(x, y) <= mv
                                     && !used.Contains(y * g.W + x);
            for (int r = 0; r <= 12; r++)
            {
                for (int k = 0; k < (r == 0 ? 1 : DX.Length); k++)
                {
                    int x = cx + DX[k] * r, y = cy + DY[k] * r;
                    if (!Ok(x, y)) continue;
                    ox = x; oy = y; return;
                }
                // 고리 여덟 방향으로 모자라면 정사각 테두리를 훑는다
                for (int y = cy - r; y <= cy + r; y++)
                    for (int x = cx - r; x <= cx + r; x++)
                    {
                        if (Math.Abs(x - cx) != r && Math.Abs(y - cy) != r) continue;
                        if (!Ok(x, y)) continue;
                        ox = x; oy = y; return;
                    }
            }
            ox = cx; oy = cy;      // 뜰이 다 찼다. 겹쳐 세운다 — 일어날 수 없는 일이지만 조용히 넘기지 않는다
        }
    }
}
