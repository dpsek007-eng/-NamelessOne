// 전투 — 판정은 여기서 다 끝난다. 화면은 나중에 사건 목록을 시간에 맞춰 재생할 뿐이다.
// 계산과 보여주기를 나눠 두면 같은 전투를 빨리 감거나 되감을 수 있다.
using System;
using System.Collections.Generic;
using System.Linq;

namespace Irem.Sim
{
    public enum Ev { Turn, Act, Hit, Heal, Move, Fall, Spot, Think, Ring, Escape, Env }

    public struct Event
    {
        public Ev K;
        public int A, T;            // 행한 자 / 당한 자 (인덱스, 없으면 -1)
        public int X, Y, D, Hp, N;
        public string S;            // 대사 · 스킬 이름 · 이유
    }

    public sealed class Unit
    {
        public string Name, Short, Role, TraitName, TraitLine;
        public string Art;                              // 어느 시트를 쓰는가
        public Dictionary<string, double> W = new();     // 성향의 무게
        public int Hp, Max, Atk, Def, Spd;
        public int X, Y, PostX, PostY;
        public bool Foe, Refugee;
        public int Range = 1, Move = 3;
        public double Mult = 1.0;
        public int Sight = 7;
        public string Skill = "공격";
        public Mind Mind;
        public double Dbuf;
        public int Dealt, Taken, Healed, FellAt;
        public readonly Dictionary<int, int> Known = new();   // 상대 인덱스 → 마지막으로 본 턴
        public bool Alert;
        public int Idx;
        public bool Alive => Hp > 0;
    }

    public sealed class Goal
    {
        public string Kind = "전멸";      // 전멸 / 생존 / 대피 / 도달 / 타종
        public string Name = "";
        public int N;
    }

    public sealed class Battle
    {
        public readonly List<Unit> Units = new();
        public readonly List<Event> Events = new();
        public readonly List<string> Log = new();
        public Grid Map;
        public Goal Goal = new();
        public HashSet<string> Env = new();
        public int Round, Rings, Escaped;
        public bool Done, Win;
        public string Reason = "";
        Rng _r;
        public Action<Unit, Intent> OnDecide;      // 검증용 갈고리

        public Battle(ulong seed) { _r = new Rng(seed); }

        IEnumerable<Unit> Side(bool foe) => Units.Where(u => u.Foe == foe && !u.Refugee && u.Alive);
        IEnumerable<Unit> Refugees()     => Units.Where(u => u.Refugee && u.Alive);

        static int Dist(Unit a, Unit b) => Math.Abs(a.X - b.X) + Math.Abs(a.Y - b.Y);

        bool On(string e) => Env.Contains(e);
        bool High(Unit u) => Map.At(u.X, u.Y) == '^';
        int SightOf(Unit u) => Math.Max(2, u.Sight - (On("어둠") ? 3 : 0) + (High(u) ? 3 : 0));
        int RangeOf(Unit u) => Math.Max(1, u.Range - (On("어둠") ? 1 : 0) + (High(u) ? 1 : 0));
        int MoveOf(Unit u)  => Math.Max(1, u.Move - (On("재") ? 1 : 0));
        bool InRange(Unit a, Unit b) => Dist(a, b) <= RangeOf(a);

        bool CanSee(Unit a, Unit b)
        {
            if (Dist(a, b) > SightOf(a)) return false;
            if (High(a)) return true;                       // 높은 곳에서는 담 너머가 보인다
            return Map.Line(a.X, a.Y, b.X, b.Y);
        }

        /// 아는 적 — 지금 보이는 것과, 놓친 지 세 턴이 안 된 것
        List<Unit> KnownFoes(Unit u)
        {
            var outl = new List<Unit>();
            foreach (var t in Side(!u.Foe))
            {
                if (CanSee(u, t)) { u.Known[t.Idx] = Round; outl.Add(t); continue; }
                if (u.Known.TryGetValue(t.Idx, out var last) && Round - last <= 3) outl.Add(t);
            }
            return outl;
        }

        /// 쏘면 위치가 드러난다
        void Reveal(Unit u)
        {
            foreach (var o in Side(!u.Foe)) o.Known[u.Idx] = Round;
        }

        /// 좁은 통로에서는 가장 앞선 둘만 붙을 수 있다
        List<Unit> Engageable(Unit u, List<Unit> seen)
        {
            if (!On("좁음")) return seen;
            return (u.Foe ? seen.OrderByDescending(f => f.X) : seen.OrderBy(f => f.X))
                   .Take(2).ToList();
        }

        void Push(Ev k, int a = -1, int t = -1, int x = 0, int y = 0,
                  int d = 0, int hp = 0, int n = 0, string s = null)
            => Events.Add(new Event { K = k, A = a, T = t, X = x, Y = y, D = d, Hp = hp, N = n, S = s });

        // ── 결정 ─────────────────────────────────────────────────────
        public Intent Decide(Unit u)
        {
            var seen = KnownFoes(u);
            bool was = u.Alert;
            u.Alert = seen.Count > 0;
            if (u.Alert && !was) Push(Ev.Spot, a: u.Idx);

            var m = u.Mind;

            // 아직 아무것도 못 봤을 때만 마음이 굳는다.
            // 걸어갈 때는 마음을 정하고 가지만, 붙고 나면 매 순간 다시 본다.
            if (m != null && m.HasIntent && m.Current.Ttl > 0
                && !m.Shocked(u.Max) && seen.Count == 0
                && (m.Current.A == Act.Move || m.Current.A == Act.Wait))
            {
                var it = m.Current; it.Ttl--; m.Current = it;
                return it;
            }

            // 수호자는 자기 자리를 지킨다. 누가 보여야 움직인다.
            if (u.Foe)
            {
                if (seen.Count == 0)
                {
                    if (u.X != u.PostX || u.Y != u.PostY)
                        return new Intent { A = Act.Move, X = u.PostX, Y = u.PostY, Why = "post", Ttl = 1, Target = -1 };
                    return new Intent { A = Act.Wait, Why = "hold", Ttl = 1, Target = -1 };
                }
                if (m != null && m.Fear > 1.0 && u.Hp < u.Max * 0.4)
                    return new Intent { A = Act.Move, X = u.PostX, Y = u.PostY, Why = "post", Ttl = 1, Target = -1 };

                var pool0 = Engageable(u, seen);
                if (Goal.Kind == "대피" && !pool0.Any(x => InRange(u, x)))
                {
                    var r0 = Refugees().Where(x => InRange(u, x) && CanSee(u, x)).ToList();
                    if (r0.Count > 0) pool0 = r0;
                }
                var tg = pool0.Where(f => InRange(u, f)).OrderBy(f => f.Hp).FirstOrDefault();
                if (tg != null) return new Intent { A = Act.Hit, Target = tg.Idx, Why = "attack", Ttl = 1 };
                var nn = pool0.OrderBy(f => Dist(u, f)).FirstOrDefault();
                return nn != null
                    ? new Intent { A = Act.Move, X = nn.X, Y = nn.Y, Why = "close", Ttl = 1, Target = -1 }
                    : new Intent { A = Act.Wait, Why = "hold", Ttl = 1, Target = -1 };
            }

            double W(string k) => u.W.TryGetValue(k, out var v) ? v : 0;
            double w(string k) => 1 + W(k) * 0.55;

            var mates = Side(u.Foe).ToList();
            var opts = new List<Intent>();
            var pool = Engageable(u, seen);
            var inR = pool.Where(f => InRange(u, f)).ToList();
            double ratio = (double)u.Hp / u.Max;

            // 어느 줄로 갈 것인가 — 지형과 적 분포를 보고 고른다
            int PickLane()
            {
                int best = u.Y; double bs = double.NegativeInfinity;
                for (int y = 0; y < Map.H; y++)
                {
                    if (!Map.Passable(u.X, y) && y != u.Y) continue;
                    double cost = 0, hazard = 0; int enemies = 0;
                    for (int x = u.X; x < Map.W; x++)
                    {
                        if (!Map.Passable(x, y)) { cost += 6; continue; }
                        cost += Map.Cost(x, y) - 1;
                        hazard += Map.T(x, y).Dmg * 14;
                    }
                    foreach (var f in seen) if (f.Y == y) enemies++;
                    double s = -cost - hazard + enemies * W("attack") * 1.4 - enemies * W("retreat") * 1.2;
                    if (s > bs) { bs = s; best = y; }
                }
                return best;
            }
            int lane = PickLane();

            double Gr(Unit f) => m?.GrudgeOn(f.Idx) ?? 0;

            // 친다 — 약한 것부터. 단, 나를 친 것을 기억하고 있으면 그쪽이 먼저다.
            if (inR.Count > 0)
            {
                var t = inR.OrderByDescending(f => (1 - (double)f.Hp / f.Max) + Gr(f) * 0.9).First();
                opts.Add(new Intent { A = Act.Hit, Target = t.Idx, Why = "attack",
                    Score = (1.0 + (1 - (double)t.Hp / t.Max) * 0.7 + Gr(t) * 0.6) * w("attack") });
                var t2 = inR.OrderByDescending(f => f.Hp).First();
                opts.Add(new Intent { A = Act.Mark, Target = t2.Idx, Why = "mark", Score = 0.85 * w("mark") });
            }
            // 살린다
            var hurt = mates.Where(x => x.Hp < x.Max * 0.95)
                            .OrderBy(x => (double)x.Hp / x.Max).FirstOrDefault();
            if (hurt != null)
            {
                double need = 1 - (double)hurt.Hp / hurt.Max;
                if (Dist(u, hurt) <= RangeOf(u))
                    opts.Add(new Intent { A = Act.Heal, Target = hurt.Idx, Why = "heal",
                        Score = (0.5 + need * 1.8) * w("heal") });
                else
                    opts.Add(new Intent { A = Act.Move, X = hurt.X, Y = hurt.Y, Target = -1, Why = "heal",
                        Score = (0.3 + need * 0.9) * w("heal") });
            }
            // 앞을 막는다
            if (seen.Count > 0 && mates.Count > 0)
            {
                var fm = mates.OrderByDescending(x => x.X).First();
                if (u.X < fm.X)
                    opts.Add(new Intent { A = Act.Move, X = Math.Min(Map.W - 1, fm.X + 1), Y = fm.Y,
                        Target = -1, Why = "guard", Score = 0.75 * w("guard") });
                else
                    opts.Add(new Intent { A = Act.Move, X = Math.Min(Map.W - 1, u.X + 1), Y = lane,
                        Target = -1, Why = "guard", Score = 0.55 * w("guard") });
            }
            // 나아간다
            if (Goal.Kind is "도달" or "타종" or "대피")
                opts.Add(new Intent { A = Act.Move, X = Map.W - 1, Y = lane, Target = -1,
                    Why = "advance", Score = 1.25 * w("advance") });
            // 종을 친다
            if (Goal.Kind == "타종" && u.X >= Map.W - 2)
                opts.Add(new Intent { A = Act.Ring, Target = -1, Why = "ring", Score = 3.2 * w("ring") });
            // 물러선다
            if (ratio < 0.6)
                opts.Add(new Intent { A = Act.Move, X = Math.Max(0, u.X - MoveOf(u)), Y = lane, Target = -1,
                    Why = "retreat", Score = (1 - ratio) * 1.7 * w("retreat") });
            // 거리를 둔다
            if (RangeOf(u) >= 3 && seen.Any(f => Dist(u, f) <= 1))
                opts.Add(new Intent { A = Act.Move, X = Math.Max(0, u.X - MoveOf(u)), Y = lane, Target = -1,
                    Why = "keepdist", Score = 0.95 * w("keepdist") });
            // 다가간다
            if (inR.Count == 0 && pool.Count > 0)
            {
                var n = pool.OrderBy(f => Dist(u, f)).First();
                opts.Add(new Intent { A = Act.Move, X = n.X, Y = n.Y, Target = -1, Why = "close", Score = 0.8 });
            }

            if (seen.Count == 0)
            {
                var obj = opts.FirstOrDefault(o => o.A == Act.Ring || o.A == Act.Heal);
                if (obj.A != Act.Wait && (obj.A == Act.Ring || obj.A == Act.Heal))
                { obj.Ttl = 1; return obj; }
                return new Intent { A = Act.Move, X = Map.W - 1, Y = lane, Target = -1, Why = "advance", Ttl = 2 };
            }

            if (m != null)
                for (int i = 0; i < opts.Count; i++)
                {
                    var o = opts[i]; o.Score *= Math.Max(0.05, m.Colour(o.Why)); opts[i] = o;
                }

            if (opts.Count == 0) return new Intent { A = Act.Wait, Why = "hold", Ttl = 1, Target = -1 };
            var best = opts.OrderByDescending(o => o.Score).First();
            best.Ttl = Mind.TtlFor(best.Why);
            return best;
        }

        // ── 실행 ─────────────────────────────────────────────────────
        int Damage(Unit a, Unit t, double mult)
        {
            double v = 0.85 + _r.F() * 0.30;
            double crit = _r.F() < 0.12 ? 1.6 : 1.0;
            double cover = Map.T(t.X, t.Y).Def;
            int d = Math.Max(1, (int)Math.Round(
                ((a.Atk * mult * v * crit) - t.Def * (1 - t.Dbuf) * 0.6) * (1 - cover)));
            t.Hp = Math.Max(0, t.Hp - d);
            a.Dealt += d; t.Taken += d;
            t.Mind?.Remember(a.Idx, d, t.Max);
            Push(Ev.Hit, a: a.Idx, t: t.Idx, d: d, hp: t.Hp);
            return d;
        }

        void Witness(Unit fallen)
        {
            foreach (var o in Units)
            {
                if (!o.Alive || o == fallen || o.Mind == null) continue;
                if (o.Foe != fallen.Foe) continue;              // 제 편이 흐려질 때만 흔들린다
                if (CanSee(o, fallen)) o.Mind.SawFall++;
            }
        }

        void MoveTo(Unit u, int tx, int ty)
        {
            var (nx, ny) = Map.Step(u.X, u.Y, Math.Clamp(tx, 0, Map.W - 1),
                                    Math.Clamp(ty, 0, Map.H - 1), MoveOf(u));
            u.X = nx; u.Y = ny;
        }

        /// 층의 환경이 매 턴 한 번씩 손을 댄다
        void EnvTick()
        {
            var live = Units.Where(x => x.Alive && !x.Refugee).ToList();

            if (On("붕괴") && live.Count > 0)                 // 벽이 무너진다
            {
                var v = live[(int)(_r.Next() % (ulong)live.Count)];
                int d = (int)Math.Round(v.Max * 0.045);
                v.Hp = Math.Max(0, v.Hp - d);
                Push(Ev.Env, t: v.Idx, d: d, hp: v.Hp, s: "낙석");
                if (v.Hp == 0) { v.FellAt = Round; Push(Ev.Fall, t: v.Idx); Witness(v); }
            }

            foreach (var v in live)                            // 균열·불 위에 서 있으면 깎인다
            {
                if (!v.Alive) continue;
                double h = Map.T(v.X, v.Y).Dmg;
                if (h <= 0) continue;
                int d = (int)Math.Round(v.Max * h);
                v.Hp = Math.Max(0, v.Hp - d);
                Push(Ev.Env, t: v.Idx, d: d, hp: v.Hp, s: Map.T(v.X, v.Y).Name);
                if (v.Hp == 0) { v.FellAt = Round; Push(Ev.Fall, t: v.Idx); Witness(v); }
            }

            if (On("종") && Round % 3 == 0)                    // 위층에서 종이 울린다
                foreach (var v in Side(false))
                {
                    int h = (int)Math.Round(v.Max * 0.06), b = v.Hp;
                    v.Hp = Math.Min(v.Max, v.Hp + h);
                    if (v.Hp > b) { v.Healed += v.Hp - b; Push(Ev.Heal, a: v.Idx, t: v.Idx, d: v.Hp - b, hp: v.Hp); }
                }
        }

        void CheckGoal()
        {
            if (!Side(false).Any()) { Done = true; Win = false; Reason = "아군이 전부 흐려졌다"; return; }
            switch (Goal.Kind)
            {
                case "전멸" when !Side(true).Any():
                    Done = true; Win = true; Reason = "수호자를 전부 흐리게 했다"; break;
                case "생존" when Round >= Goal.N:
                    Done = true; Win = true; Reason = $"{Goal.N}턴을 버텼다"; break;
                case "대피" when Escaped >= Goal.N:
                    Done = true; Win = true; Reason = $"{Goal.N}명을 내보냈다"; break;
                case "도달" when Side(false).Any(u => u.X >= Map.W - 1):
                    Done = true; Win = true; Reason = "반대편에 닿았다"; break;
                case "타종" when Rings >= Goal.N:
                    Done = true; Win = true; Reason = $"종을 {Goal.N}번 쳤다"; break;
            }
            if (Goal.Kind == "대피" && !Refugees().Any() && Escaped < Goal.N)
            { Done = true; Win = false; Reason = "피난민이 남지 않았다"; }
        }

        public void Run(int maxRounds = 40)
        {
            for (int i = 0; i < Units.Count; i++) Units[i].Idx = i;

            for (Round = 1; Round <= maxRounds && !Done; Round++)
            {
                Push(Ev.Turn, n: Round);
                EnvTick();

                if (Goal.Kind == "대피")
                    foreach (var r in Refugees().ToList())
                    {
                        MoveTo(r, Map.W - 1, r.Y);
                        Push(Ev.Move, t: r.Idx, x: r.X, y: r.Y);
                        if (r.X >= Map.W - 1) { r.Hp = 0; Escaped++; Push(Ev.Escape, t: r.Idx, n: Escaped); }
                    }

                foreach (var u in Units.Where(x => x.Alive && !x.Refugee)
                                       .OrderByDescending(x => x.Spd).ToList())
                {
                    if (!u.Alive || Done) continue;
                    u.Mind?.Tick(u.Hp, u.Max);
                    var d = Decide(u);
                    OnDecide?.Invoke(u, d);
                    if (u.Mind != null)
                    {
                        u.Mind.Current = d; u.Mind.HasIntent = true;
                        var tgt = d.Target >= 0 ? Units[d.Target] : null;
                        bool grudged = tgt != null && u.Mind.GrudgeOn(tgt.Idx) > 0.12;
                        string th = u.Mind.ThoughtFor(d, u.TraitLine, grudged,
                                                      u.Known.Count > 0, u.Idx * 7 + Round * 3);
                        if (!string.IsNullOrEmpty(th) && th != u.Mind.Thought)
                        {
                            u.Mind.Thought = th;
                            Push(Ev.Think, a: u.Idx, s: th);
                        }
                        u.Mind.SawFall = 0;
                    }

                    switch (d.A)
                    {
                        case Act.Move:
                        {
                            int fx = u.X, fy = u.Y;
                            MoveTo(u, d.X, d.Y);
                            if (u.X != fx || u.Y != fy)
                                Push(Ev.Move, t: u.Idx, x: u.X, y: u.Y, s: d.Why);
                            break;
                        }
                        case Act.Ring:
                            Rings++; Push(Ev.Ring, a: u.Idx, n: Rings);
                            break;
                        case Act.Heal:
                        {
                            var t = Units[d.Target];
                            int h = (int)Math.Round(u.Atk * 1.7), before = t.Hp;
                            t.Hp = Math.Min(t.Max, t.Hp + h); u.Healed += t.Hp - before;
                            if (t != u) t.Mind?.Owe(u.Idx);
                            Push(Ev.Act, a: u.Idx, s: u.Skill);
                            Push(Ev.Heal, a: u.Idx, t: t.Idx, d: t.Hp - before, hp: t.Hp);
                            break;
                        }
                        case Act.Hit:
                        case Act.Mark:
                        {
                            var t = Units[d.Target];
                            Push(Ev.Act, a: u.Idx, s: u.Skill);
                            if (d.A == Act.Mark) t.Dbuf = 0.35;
                            Damage(u, t, u.Mult);
                            if (Dist(u, t) > 1) Reveal(u);
                            if (t.Hp == 0)
                            {
                                t.FellAt = Round; Push(Ev.Fall, t: t.Idx); Witness(t);
                            }
                            break;
                        }
                    }
                    CheckGoal();
                }
                if (!Done) CheckGoal();
            }
            if (!Done) { Done = true; Win = false; Reason = "40턴을 넘겼다"; }
        }
    }
}
