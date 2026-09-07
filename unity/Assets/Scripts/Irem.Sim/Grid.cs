// 전장 격자 — 지형, 시야, 길찾기. 엔진을 참조하지 않는다.
// proto/battle_proto.html 과 같은 규칙이다. 규칙이 갈라지면 둘 다 틀린 것이다.
using System;
using System.Collections.Generic;

namespace Irem.Sim
{
    public sealed class Terrain
    {
        public string Name = "평지";
        public int Move = 1;            // 지나는 데 드는 값
        public double Dmg;              // 지나면 깎이는 비율
        public bool Block;              // 지날 수 없다
        public double Def;              // 뒤에 서면 덜 맞는다
    }

    public sealed class Grid
    {
        public readonly int W, H;
        readonly char[,] _c;
        public readonly Dictionary<char, Terrain> Terrains;

        public Grid(IReadOnlyList<string> rows, Dictionary<char, Terrain> terrains)
        {
            H = rows.Count; W = rows[0].Length;
            Terrains = terrains;
            _c = new char[W, H];
            for (int y = 0; y < H; y++)
                for (int x = 0; x < W; x++)
                    _c[x, y] = x < rows[y].Length ? rows[y][x] : '.';
        }

        public char At(int x, int y) =>
            (x < 0 || y < 0 || x >= W || y >= H) ? '#' : _c[x, y];

        public Terrain T(int x, int y)
        {
            var ch = At(x, y);
            return Terrains.TryGetValue(ch, out var t) ? t
                 : Terrains.TryGetValue('.', out var p) ? p : new Terrain();
        }

        public bool Passable(int x, int y) => !T(x, y).Block;
        public int Cost(int x, int y) => Math.Max(1, T(x, y).Move);

        /// 브레젠험. 막힌 칸을 지나면 보이지 않는다.
        public bool Line(int x0, int y0, int x1, int y1)
        {
            int dx = Math.Abs(x1 - x0), dy = Math.Abs(y1 - y0);
            int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
            int err = dx - dy, guard = 0;
            while ((x0 != x1 || y0 != y1) && guard++ < 400)
            {
                int e2 = 2 * err;
                if (e2 > -dy) { err -= dy; x0 += sx; }
                if (e2 < dx) { err += dx; y0 += sy; }
                if (x0 == x1 && y0 == y1) break;
                if (T(x0, y0).Block) return false;
            }
            return true;
        }

        static readonly int[] DX = { 1, -1, 0, 0 };
        static readonly int[] DY = { 0, 0, 1, -1 };

        /// 길찾기 — 목표까지의 길을 다 구한 뒤 그 길을 이동력만큼 따라간다.
        /// 가까워 보이는 쪽으로 한 걸음씩 가면 벽 앞에서 멈춘다. 길을 먼저 알아야 한다.
        ///
        /// 큐를 쓰는 SPFA 다. 우선순위 큐를 쓰면 값이 같은 길에서 다른 쪽을 고르고,
        /// 그러면 같은 규칙인데 시험판과 다르게 움직인다. 알고리즘까지 같아야 한다.
        public (int x, int y) Step(int sx, int sy, int tx, int ty, int budget)
        {
            if (sx == tx && sy == ty) return (sx, sy);
            if (!Passable(tx, ty)) return (sx, sy);
            int n = W * H, S = sy * W + sx, G = ty * W + tx;
            var dist = new int[n];
            var prev = new int[n];
            for (int i = 0; i < n; i++) { dist[i] = int.MaxValue; prev[i] = -1; }
            dist[S] = 0;
            var q = new Queue<int>();
            q.Enqueue(S);
            while (q.Count > 0)
            {
                int i2 = q.Dequeue();
                int x = i2 % W, y = i2 / W, d = dist[i2];
                for (int k = 0; k < 4; k++)
                {
                    int nx = x + DX[k], ny = y + DY[k];
                    if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
                    if (!Passable(nx, ny)) continue;
                    int j = ny * W + nx, nd = d + Cost(nx, ny);
                    if (nd >= dist[j]) continue;
                    dist[j] = nd; prev[j] = i2; q.Enqueue(j);
                }
            }
            if (dist[G] == int.MaxValue) return (sx, sy);

            var path = new List<int>();
            for (int c = G; c != S; c = prev[c])
            {
                if (prev[c] < 0) return (sx, sy);
                path.Add(c);
            }
            path.Reverse();
            int best = -1;
            foreach (var c in path) { if (dist[c] <= budget) best = c; else break; }
            return best < 0 ? (sx, sy) : (best % W, best / W);
        }

        /// 붙어 있는 칸인지 — 지도가 통째로 이어져 있는지 검사할 때 쓴다
        public bool Connected(int ax, int ay, int bx, int by)
        {
            var seen = new bool[W * H];
            var st = new Stack<int>();
            st.Push(ay * W + ax); seen[ay * W + ax] = true;
            while (st.Count > 0)
            {
                int i = st.Pop(); int x = i % W, y = i / W;
                if (x == bx && y == by) return true;
                for (int k = 0; k < 4; k++)
                {
                    int nx = x + DX[k], ny = y + DY[k];
                    if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
                    int j = ny * W + nx;
                    if (seen[j] || !Passable(nx, ny)) continue;
                    seen[j] = true; st.Push(j);
                }
            }
            return false;
        }
    }
}
