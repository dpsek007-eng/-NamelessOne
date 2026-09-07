// 편성과 전투 세우기 — 엔진을 참조하지 않는다.
// 유니티도, 콘솔 검증기도, 같은 코드를 지난다. 그래야 검증이 의미가 있다.
using System;
using System.Collections.Generic;
using System.Linq;
using Irem.Data;

namespace Irem.Sim
{
    public static class Setup
    {
        static int RoundI(float v) => (int)MathF.Round(v, MidpointRounding.AwayFromZero);
        static int RoundI(double v) => (int)Math.Round(v, MidpointRounding.AwayFromZero);

        // ── 편성 ─────────────────────────────────────────────────────
        //   힘만 보고 뽑으면 한 팀만 경로를 열고 나머지는 요구치를 그대로 진다.
        //   팀마다 열쇠를 하나씩 넣고 앞뒤를 맞춘 뒤 남은 자리를 힘으로 채운다.
        public static List<List<CharDef>> AutoFill(BattleTables T, FloorDef f)
        {
            var teams = new List<List<CharDef>>();
            for (int i = 0; i < Math.Max(1, f.teams); i++) teams.Add(new List<CharDef>());
            var pool = T.chars.OrderByDescending(c => c.pw).ToList();
            var used = new HashSet<string>();

            bool Fits(CondDef w, CharDef c)
            {
                switch (w.t)
                {
                    case "역할": return c.role == w.v;
                    case "생업": return c.trade == w.v;
                    case "시대": return c.era == w.v;
                    case "층범위":
                    {
                        var ab = w.v.Split('~');
                        return ab.Length == 2 && int.TryParse(ab[0], out var a)
                               && int.TryParse(ab[1], out var b) && c.floor >= a && c.floor <= b;
                    }
                }
                return false;
            }
            bool Put(int i, CharDef c)
            {
                if (c == null || used.Contains(c.id) || teams[i].Count >= f.slot) return false;
                teams[i].Add(c); used.Add(c.id); return true;
            }

            for (int i = 0; i < teams.Count; i++)
                foreach (var r in (f.routes ?? new RouteDef[0]).OrderBy(r => r.pw))
                {
                    if (r.cond == null || r.cond.Length == 0) continue;
                    if (r.cond.Any(c => c.t == "약체")) continue;
                    var picks = new List<CharDef>(); var tmp = new HashSet<string>();
                    bool ok = r.cond.All(w =>
                    {
                        int need = Math.Max(1, w.n);
                        foreach (var c in pool)
                        {
                            if (used.Contains(c.id) || tmp.Contains(c.id) || !Fits(w, c)) continue;
                            picks.Add(c); tmp.Add(c.id);
                            if (--need == 0) return true;
                        }
                        return false;
                    });
                    if (ok && picks.Count <= f.slot) { foreach (var c in picks) Put(i, c); break; }
                }

            if (f.slot >= 3)
                foreach (var role in new[] { "헌신", "수호" })
                    for (int i = 0; i < teams.Count; i++)
                    {
                        if (teams[i].Any(c => c.role == role)) continue;
                        Put(i, pool.FirstOrDefault(c => !used.Contains(c.id) && c.role == role));
                    }

            foreach (var c in pool)
            {
                if (used.Contains(c.id)) continue;
                int best = -1, bestPw = int.MaxValue;
                for (int i = 0; i < teams.Count; i++)
                {
                    if (teams[i].Count >= f.slot) continue;
                    int pw = teams[i].Sum(x => x.pw);
                    if (pw < bestPw) { bestPw = pw; best = i; }
                }
                if (best < 0) break;
                Put(best, c);
            }
            return teams;
        }

        // ── 전투 세우기 ───────────────────────────────────────────────
        static readonly Dictionary<string, (int rng, int mv, double mult, int sight)> Kit = new()
        {
            ["수호"] = (1, 3, 0.85, 6), ["저항"] = (1, 3, 1.85, 6),
            ["헌신"] = (4, 2, 0.75, 7), ["탐구"] = (5, 2, 1.00, 10),
            ["도피"] = (2, 4, 1.20, 8), ["미상"] = (2, 3, 1.00, 7),
        };
        static readonly Dictionary<string, int> StartX = new()
        { ["수호"] = 2, ["저항"] = 2, ["도피"] = 2, ["헌신"] = 1, ["탐구"] = 0, ["미상"] = 1 };
        static readonly Dictionary<string, int> StartY = new()
        { ["수호"] = 3, ["저항"] = 2, ["도피"] = 5, ["헌신"] = 4, ["탐구"] = 4, ["미상"] = 3 };

        /// 팀을 넘기면 그 편성으로, 안 넘기면 자동 편성으로 세운다.
        public static Battle BuildBattle(BattleTables T, FloorDef f, ulong seed,
                                         List<List<CharDef>> given = null)
        {
            var terr = new Dictionary<char, Terrain>();
            foreach (var t in T.terrain)
                terr[t.ch[0]] = new Terrain { Name = t.name, Move = t.mv, Dmg = t.dmg,
                                              Block = t.block, Def = t.def };

            var B = new Battle(seed)
            {
                Map = new Grid(f.map, terr),
                Goal = new Goal { Kind = f.goalKind, Name = f.goalName, N = f.goalN },
                Env = new HashSet<string>(f.env ?? new string[0]),
            };

            var teams = given ?? AutoFill(T, f);
            var taken = new HashSet<int>();
            int Free(int x, int y)
            {
                for (int r = 0; r < B.Map.W * B.Map.H; r++)
                {
                    int yy = (y + r) % B.Map.H;
                    int xx = Math.Min(B.Map.W - 1, x + r / B.Map.H);
                    int k = yy * B.Map.W + xx;
                    if (B.Map.Passable(xx, yy) && taken.Add(k)) return k;
                }
                return y * B.Map.W + x;
            }

            int reqTotal = 0;
            foreach (var team in teams)
            {
                float pw = BestRoute(f, team)?.pw ?? 1f;
                reqTotal += RoundI((float)f.baseReq / Math.Max(1, f.teams) * pw);

                foreach (var c in team)
                {
                    var kit = Kit.TryGetValue(c.role, out var k) ? k : Kit["미상"];
                    int cell = Free(StartX.TryGetValue(c.role, out var sx) ? sx : 1,
                                    StartY.TryGetValue(c.role, out var sy) ? sy : 1);
                    var u = new Unit
                    {
                        Name = c.name, Short = c.name, Art = c.id, Role = c.role,
                        TraitName = c.traitName, TraitLine = c.traitLine, W = c.Weights(),
                        Hp = c.hp, Max = c.hp, Atk = c.atk, Def = c.def, Spd = c.spd,
                        Range = kit.rng, Move = kit.mv, Mult = kit.mult, Sight = kit.sight,
                        Skill = string.IsNullOrEmpty(c.skill) ? "공격" : c.skill,
                        X = cell % B.Map.W, Y = cell / B.Map.W,
                    };
                    u.Mind = Mind.From(u.W, u.Hp);
                    B.Units.Add(u);
                }
            }

            int n = Math.Max(2, B.Units.Count);
            double soft = (f.goalKind == "도달" || f.goalKind == "타종" ? 0.52
                        : f.goalKind != "전멸" ? 0.86 : 1.0)
                        * (f.teams >= 3 ? 0.68 : 1.0);
            var taken2 = new HashSet<int>();
            for (int i = 0; i < n; i++)
            {
                var k = T.foes[i % T.foes.Length];
                int x = Math.Max(0, B.Map.W - 2 - (i % 3)), y = (1 + i * 2) % B.Map.H;
                int cell = y * B.Map.W + x;
                for (int r = 0; r < B.Map.W * B.Map.H; r++)
                {
                    int cx = cell % B.Map.W, cy = cell / B.Map.W;
                    if (B.Map.Passable(cx, cy) && !taken2.Contains(cell)) break;
                    int yy = (y + r) % B.Map.H, xx = Math.Max(0, x - r / B.Map.H);
                    cell = yy * B.Map.W + xx;
                }
                taken2.Add(cell);
                var u = new Unit
                {
                    Name = f.n + "층의 " + k.name,
                    Short = k.name + (i > 2 ? " " + (i / 3 + 1) : ""),
                    Art = "foe_" + k.name, Role = "저항", Foe = true,
                    Hp = RoundI(reqTotal * 2.7f / n * k.hp),
                    Max = RoundI(reqTotal * 2.7f / n * k.hp),
                    Atk = RoundI(reqTotal * 0.31f / n * (float)soft * k.atk),
                    Def = RoundI(reqTotal * 0.022f / MathF.Sqrt(n)),
                    // 수호자도 성향 값을 쓴다. 시험판의 KIT['저항'] 과 같아야 한다.
                    Spd = k.spd + i, Range = k.rng, Move = k.mv, Sight = 6, Mult = Kit["저항"].mult,
                    X = cell % B.Map.W, Y = cell / B.Map.W,
                };
                u.PostX = u.X; u.PostY = u.Y;
                u.Mind = Mind.From(u.W, u.Hp);
                B.Units.Add(u);
            }

            if (f.goalKind == "대피")
                for (int i = 0; i < f.goalN; i++)
                {
                    var u = new Unit
                    {
                        Name = "피난민 " + (i + 1), Short = "피난민" + (i + 1),
                        Art = "ref" + (i % 4), Refugee = true, Role = "미상",
                        Hp = 300, Max = 300, Def = 40, Spd = 60,
                        X = 0, Y = (2 + i * 2) % B.Map.H, Sight = 5,
                    };
                    u.Mind = Mind.From(u.W, u.Hp);
                    B.Units.Add(u);
                }
            return B;
        }

        /// 이 편성으로 열리는 길 중 가장 싼 것. 없으면 돌파(조건 없음).
        public static RouteDef BestRoute(FloorDef f, List<CharDef> team)
            => (f.routes ?? new RouteDef[0])
               .Where(r => r.cond == null || r.cond.Length == 0 || r.cond.All(c => Meets(c, team)))
               .OrderBy(r => r.pw).FirstOrDefault();

        /// 이 팀이 져야 할 요구 전투력
        public static int Required(FloorDef f, List<CharDef> team)
            => RoundI((float)f.baseReq / Math.Max(1, f.teams) * (BestRoute(f, team)?.pw ?? 1f));

        public static int TeamPower(List<CharDef> team)
            => team == null ? 0 : team.Where(c => c != null).Sum(c => c.pw);

        public static bool Meets(CondDef c, List<CharDef> team)
        {
            if (team.Count == 0) return false;
            if (c.t == "약체") return team.Average(x => x.r) <= 3;
            int need = Math.Max(1, c.n);
            int have;
            switch (c.t)
            {
                case "역할": have = team.Count(x => x.role == c.v); break;
                case "생업": have = team.Count(x => x.trade == c.v); break;
                case "시대": have = team.Count(x => x.era == c.v); break;
                case "층범위":
                {
                    var ab = c.v.Split('~');
                    have = (ab.Length == 2 && int.TryParse(ab[0], out var a) && int.TryParse(ab[1], out var b))
                         ? team.Count(x => x.floor >= a && x.floor <= b) : 0;
                    break;
                }
                default: have = 0; break;
            }
            return have >= need;
        }
    }
}
