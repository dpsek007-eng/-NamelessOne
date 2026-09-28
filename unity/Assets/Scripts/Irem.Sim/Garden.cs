// 뜰 — 0층. 계산은 전부 여기서 끝난다. 보여주기는 GardenDirector 가 한다.
// Battle.cs 와 같은 골격이다: 한 틱을 돌리면 사건이 목록에 쌓이고, 연출자는 그것만 재생한다.
//
//   뜰에서는 시간이 흐르지 않는다(docs/03-뜰.md).
//   밤도 노화도 흐려짐도 죽음도 없다. 한 틱은 「한 걸음」일 뿐 하루가 아니다.
//   플레이어가 접속해 있는 동안만 조금 흐른다 — 그래서 틱을 세는 것으로 충분하다.
//
//   길찾기는 Grid.Step 을 그대로 쓴다. 거기 적힌 이유가 여기서도 그대로다 —
//   「우선순위 큐를 쓰면 값이 같은 길에서 다른 쪽을 고른다. 알고리즘까지 같아야 한다.」
using System;
using System.Collections.Generic;
using Irem.Data;

namespace Irem.Sim
{
    public enum Gv { Turn, Walk, Work, Rest, Meet, Avoid, Say, Think, Bond, Stand }

    public struct GardenEvent
    {
        public Gv K;
        public int A, T;            // 누가 / 누구에게
        public int X, Y;            // 어느 칸에서
        public int N;               // 셈 (몇 걸음째 일함, 성립한 인연 수 …)
        public string S;            // 한 줄
    }

    /// 뜰에 선 잔상 하나. ShadeGen 의 Shade(무명 잔상 레코드)와 다른 것이라 이름을 달리 둔다.
    public sealed class GardenShade
    {
        public int Idx;
        public AgentDef Def;
        public Heart Heart;
        public int X, Y;            // 지금 선 칸
        public int Wx, Wy;          // 제 일터 자리 (없으면 서있는자리)
        public string Place = "";   // 일터 이름, 없으면 ""
        public int Mv = 2, Sight = 6;
        public int Salt;            // 대사를 고르는 소금. 시드에서 나오므로 재현된다
        public int SaidAt = -9999;  // 마지막으로 입을 연 걸음
        public Doing Said = Doing.Stand;   // 그때 하던 것 — 바뀌는 자리가 말이 나올 자리다
        public int MetWho = -1, MetAt = -9999;     // 지금 이어지는 만남
        public int AwayFrom = -1, AwayAt = -9999;  // 지금 이어지는 피함

        public bool Homeless => string.IsNullOrEmpty(Place);
        public bool AtWork => X == Wx && Y == Wy && !Homeless;
        public string Id => Def?.id ?? "";
        public string Name => Def?.name ?? "";
    }

    /// 관계 인연 한 가닥. 처음엔 피하고, 여러 걸음 뒤에 상대가 먼저 말을 건다.
    /// 이 움직임이 뜰 인연의 전부다(docs/03-뜰.md 카브릴 × 북문의 수문장).
    public sealed class Tie
    {
        public BondRule R;
        public int A, B;            // A 가 피하는 쪽, B 가 먼저 말을 거는 쪽
        public bool Spoken;
        public int Since;           // 같은 뜰에 있은 걸음 수
    }

    public sealed class Garden
    {
        public readonly GardenTables T;
        public readonly Grid G;
        public readonly List<GardenShade> Cast = new();
        public readonly List<GardenEvent> Log = new();
        public readonly List<Bond> Found = new();
        public readonly List<Tie> Ties = new();
        public int Turn;

        Rng _r;
        public readonly ulong Seed;

        /// 며칠(실시간)이 지나면 수문장이 먼저 말을 건다 — 그 「며칠」을 걸음으로 옮긴 값.
        /// 잰 값이 아니라 정한 값이다. 바꾸면 인연이 열리는 때가 바뀐다.
        public const int ThawSteps = 40;

        // ── 말은 사건이라야 한다 ──
        //
        // 처음에는 일·쉼·서성임이 있을 때마다 그대로 말하게 두었다. 되풀이되는 일이
        // 걸음마다 한 번씩 오므로, 스물셋이 걸음마다 입을 열었다(실측: 600걸음에
        // 13,108줄 — 한 사람이 같은 문장을 128번 되풀이했다). 그건 뜰이 아니라 전광판이다.
        //
        // 그래서 입을 열 자리를 둘로 줄인다:
        //   · 하던 것이 바뀐 걸음 — 일터에 막 닿았다, 손을 놓고 쉰다, 걷기 시작했다
        //   · 같은 것을 오래 하다가 문득 — 사람마다 어긋난 주기로 흩어 놓는다
        // 만남·피함·인연은 그 자체가 사건이므로 그대로 말한다. 다만 누구든
        // 연달아 떠들지는 않는다.
        public const int MuteSteps  = 12;   // 한 사람이 두 번 말하는 사이 최소 걸음
        public const int MusePeriod = 47;   // 이어가는 중에 문득 혼잣말하는 주기.
                                            // 소수로 둔다 — 23명이 같은 걸음에 몰리지 않는다

        public Garden(GardenTables t, Grid g, ulong seed)
        {
            T = t; G = g; Seed = seed; _r = new Rng(seed);
        }

        void Push(Gv k, int a = -1, int t = -1, int x = 0, int y = 0, int n = 0, string s = null)
            => Log.Add(new GardenEvent { K = k, A = a, T = t, X = x, Y = y, N = n, S = s });

        // ── 인연 ──
        /// 구역에 성립한 인연을 다시 잰다. 배치가 바뀌면 성립 목록 자체가 달라진다.
        public void Reckon()
        {
            var zone = new List<AgentDef>();
            foreach (var s in Cast) zone.Add(s.Def);
            Found.Clear();
            Found.AddRange(Bonds.Find(zone, T.bonds));
            Bonds.Split(Found, T.activeSlots <= 0 ? 4 : T.activeSlots);

            Ties.Clear();
            foreach (var b in Found)
            {
                if (b.R.kind != "관계" || !b.Active) continue;
                var ms = b.R.members; if (ms == null || ms.Length < 2) continue;
                int a = Index(ms[0]); if (a < 0) continue;
                for (int i = 1; i < ms.Length; i++)
                {
                    int c = Index(ms[i]); if (c < 0) continue;
                    Ties.Add(new Tie { R = b.R, A = a, B = c });
                    // 아직 못 보는 얼굴. 데이터가 그렇다고 적어 둔 인연에만 건다 —
                    // 만들어 낸 거리낌을 모든 인연에 붙이지 않는다.
                    if (b.R.shy) Cast[a].Heart.Flinch(c, 0.6);
                }
            }
            int on = 0; foreach (var b in Found) if (b.Active) on++;
            Push(Gv.Bond, n: Found.Count, s: $"성립 {Found.Count}종 · 발동 {on}종 · 대기 {Found.Count - on}종");
        }

        public int Index(string id)
        {
            for (int i = 0; i < Cast.Count; i++) if (Cast[i].Id == id) return i;
            return -1;
        }

        static int Dist(GardenShade a, GardenShade b) => Math.Abs(a.X - b.X) + Math.Abs(a.Y - b.Y);

        bool Sees(GardenShade a, GardenShade b)
            => Dist(a, b) <= a.Sight && G.Line(a.X, a.Y, b.X, b.Y);

        // ── 한 걸음 ──
        public void Tick()
        {
            Turn++;
            Push(Gv.Turn, n: Turn);

            foreach (var t in Ties) if (!t.Spoken) t.Since++;

            // 잔상 순서는 Cast 순서다. 순서를 바꾸면 같은 시드가 다르게 흐른다.
            for (int i = 0; i < Cast.Count; i++) Move(Cast[i]);
        }

        void Move(GardenShade s)
        {
            var h = s.Heart;

            // ── 본다 ──
            int near = 0, sawShy = -1, seeker = -1;
            for (int j = 0; j < Cast.Count; j++)
            {
                if (j == s.Idx) continue;
                if (!Sees(s, Cast[j])) continue;
                near++;
                if (sawShy < 0 && h.ShyOn(j) > 0) sawShy = j;
            }
            if (sawShy >= 0) h.Stirred = true;

            // ── 마음이 먼저 움직인다 ──
            bool working = h.HasUrge && h.Current.D == Doing.Work;
            bool resting = h.HasUrge && h.Current.D == Doing.Rest;
            h.Tick(working, resting, s.Homeless, near);

            foreach (var t in Ties)
            {
                int other = t.A == s.Idx ? t.B : t.B == s.Idx ? t.A : -1;
                if (other < 0) continue;
                bool far = !Sees(s, Cast[other]);
                if (h.ShyOn(other) > 0) continue;        // 피하는 상대를 그리워하지는 않는다
                h.Long(other, far);
                // 여러 걸음이 지나면 이쪽이 먼저 말을 건다
                if (!t.Spoken && t.B == s.Idx && t.Since >= ThawSteps) seeker = t.A;
            }

            // ── 하던 마음을 이어갈 수 있으면 이어간다 ──
            if (seeker < 0 && h.Keeps(sawShy >= 0))
            {
                Act(s, h.Current);
                return;
            }

            // ── 후보를 쌓는다. 이 순서가 사양이다 ──
            var cand = new List<Urge>();
            if (!s.Homeless)
            {
                if (s.AtWork) cand.Add(new Urge { D = Doing.Work, Who = -1, Why = "work", Score = 1.00, X = s.X, Y = s.Y });
                else          cand.Add(new Urge { D = Doing.Walk, Who = -1, Why = "goto", Score = 0.90, X = s.Wx, Y = s.Wy });
            }
            cand.Add(new Urge { D = Doing.Rest, Who = -1, Why = "rest", Score = 0.50, X = s.X, Y = s.Y });
            if (sawShy >= 0)
                cand.Add(new Urge { D = Doing.Avoid, Who = sawShy, Why = "avoid", Score = 0.80 + h.ShyOn(sawShy) });
            if (seeker >= 0)
                cand.Add(new Urge { D = Doing.Meet, Who = seeker, Why = "meet", Score = 2.00 });
            else
            {
                int mate = -1; double most = 0;
                foreach (var t in Ties)
                {
                    int other = t.A == s.Idx ? t.B : t.B == s.Idx ? t.A : -1;
                    if (other < 0 || h.ShyOn(other) > 0) continue;
                    double m = h.MissOn(other);
                    if (m > most) { most = m; mate = other; }
                }
                if (mate >= 0 && most > 0.35)
                    cand.Add(new Urge { D = Doing.Meet, Who = mate, Why = "miss", Score = 0.60 + most });
                else if (near > 0)
                {
                    int who = -1;
                    for (int j = 0; j < Cast.Count; j++)
                        if (j != s.Idx && h.ShyOn(j) == 0 && Sees(s, Cast[j])) { who = j; break; }
                    if (who >= 0) cand.Add(new Urge { D = Doing.Meet, Who = who, Why = "meet", Score = 0.45 });
                }
            }
            if (s.Homeless) cand.Add(new Urge { D = Doing.Roam, Who = -1, Why = "roam", Score = 0.45 });

            Act(s, h.Choose(cand));
        }

        // ── 고른 것을 한다 ──
        void Act(GardenShade s, in Urge u)
        {
            var h = s.Heart;
            switch (u.D)
            {
                case Doing.Work:
                    h.Worked++;
                    Push(Gv.Work, s.Idx, x: s.X, y: s.Y, n: h.Worked, s: s.Place);
                    Mutter(s, "work", Doing.Work);
                    break;

                case Doing.Rest:
                    h.Rested++;
                    Push(Gv.Rest, s.Idx, x: s.X, y: s.Y, n: h.Rested);
                    Mutter(s, "rest", Doing.Rest);
                    break;

                case Doing.Walk:
                    Walk(s, u.X, u.Y);
                    s.Said = Doing.Walk;
                    if (s.AtWork) Push(Gv.Work, s.Idx, x: s.X, y: s.Y, n: h.Worked, s: s.Place);
                    break;

                case Doing.Meet:
                    Greet(s, u.Who, u.Why);
                    break;

                case Doing.Avoid:
                    Away(s, u.Who);
                    // 피하는 동안은 걸음마다 발이 움직이지만, 사건은 「피하기 시작한 걸음」
                    // 하나다. 이어지는 것을 걸음마다 적으면 한 번 돌아선 일이 마흔다섯 번이 된다.
                    if (s.AwayFrom != u.Who || Turn - s.AwayAt > 1)
                    {
                        Push(Gv.Avoid, s.Idx, u.Who, s.X, s.Y);
                        SayNow(s, "avoid");
                    }
                    s.AwayFrom = u.Who; s.AwayAt = Turn;
                    break;

                case Doing.Roam:
                    Roam(s);
                    break;

                default:
                    Push(Gv.Stand, s.Idx, x: s.X, y: s.Y);
                    break;
            }
        }

        /// 사건이라 말한다 — 만났다, 피했다. 최소 간격만 지킨다.
        void SayNow(GardenShade s, string bank)
        {
            if (Turn - s.SaidAt < MuteSteps) return;
            Emit(s, bank);
        }

        /// 되풀이되는 일 중의 혼잣말. 하던 것이 바뀐 걸음이거나, 오래 하다 문득일 때만.
        void Mutter(GardenShade s, string bank, Doing now)
        {
            bool changed = s.Said != now;
            bool muse = (Turn + s.Salt) % MusePeriod == 0;
            s.Said = now;
            if (!changed && !muse) return;
            if (Turn - s.SaidAt < MuteSteps) return;
            Emit(s, bank);
        }

        void Emit(GardenShade s, string bank)
        {
            var line = Heart.Pick(T.Bank(s.Id, bank), s.Salt + Turn);
            if (line.Length == 0) return;          // 구운 대사가 없으면 없는 대로 둔다
            s.SaidAt = Turn;
            Push(Gv.Say, s.Idx, x: s.X, y: s.Y, s: line);
        }

        bool Taken(int x, int y, int self) => At(x, y, self) != null;

        GardenShade At(int x, int y, int self)
        {
            for (int i = 0; i < Cast.Count; i++)
                if (i != self && Cast[i].X == x && Cast[i].Y == y) return Cast[i];
            return null;
        }

        /// 한 걸음. 길은 Grid.Step 이 알고, 여기서는 그 길에 사람이 서 있는 것만 다룬다.
        ///
        /// 실측(걸음 200, 시드 42): 걸음 수만큼 간 자리에 사람이 서 있으면 그 자리에 굳어
        /// 두 잔상이 200걸음 동안 한 번도 일터에 닿지 못했다. 종탑에 선 세렌과
        /// 기록관 앞에 선 이름을 적던 병사가 각각 길을 막고 있었다.
        /// 뜰에는 사람이 늘 서 있으므로, 문간에 선 사람 하나가 줄을 세우면 안 된다.
        void Walk(GardenShade s, int tx, int ty)
        {
            // 덜 가는 것부터 다시 잰다. 두 칸이 막혔으면 한 칸이라도 간다.
            for (int b = s.Mv; b >= 1; b--)
            {
                var (nx, ny) = G.Step(s.X, s.Y, tx, ty, b);
                if ((nx == s.X && ny == s.Y) || Taken(nx, ny, s.Idx)) continue;
                s.X = nx; s.Y = ny;
                Push(Gv.Walk, s.Idx, x: nx, y: ny);
                return;
            }
            // 서로가 서로의 일터에 서 있으면 아무리 기다려도 풀리지 않는다.
            // 실측(걸음 200, 시드 42): 이델이 장부를 맞추던 사람의 자리에,
            // 그 사람이 이델의 자리에 서서 둘 다 200걸음을 굳었다. 그럴 땐 자리를 바꾼다.
            for (int k = 0; k < 4; k++)
            {
                var o = At(s.X + DX[k], s.Y + DY[k], s.Idx);
                if (o == null || o.AtWork) continue;
                if (o.Wx != s.X || o.Wy != s.Y) continue;
                int ox = o.X, oy = o.Y;
                o.X = s.X; o.Y = s.Y; s.X = ox; s.Y = oy;
                Push(Gv.Walk, s.Idx, x: s.X, y: s.Y);
                Push(Gv.Walk, o.Idx, x: o.X, y: o.Y);
                return;
            }
            // 길이 통째로 막혔다. 목표에 가까워지는 옆칸으로 비켜 간다.
            int now = Math.Abs(s.X - tx) + Math.Abs(s.Y - ty);
            for (int k = 0; k < 4; k++)
            {
                int x = s.X + DX[k], y = s.Y + DY[k];
                if (!G.Passable(x, y) || Taken(x, y, s.Idx)) continue;
                if (G.Cost(x, y) > s.Mv) continue;
                if (Math.Abs(x - tx) + Math.Abs(y - ty) >= now) continue;
                s.X = x; s.Y = y;
                Push(Gv.Walk, s.Idx, x: x, y: y);
                return;
            }
            Push(Gv.Stand, s.Idx, x: s.X, y: s.Y);
        }

        void Greet(GardenShade s, int who, string why)
        {
            var o = Cast[who];
            if (Dist(s, o) > 1)
            {
                // 상대 옆까지 간다. 상대 칸은 이미 사람이 서 있으므로 그 옆을 목표로 잡는다.
                var (tx, ty) = Beside(o, s);
                Walk(s, tx, ty);
                Mutter(s, "pass", Doing.Walk);
                return;
            }
            // 만남도 마찬가지다 — 나란히 선 걸음마다가 아니라 다가선 그 걸음이 사건이다.
            if (s.MetWho != who || Turn - s.MetAt > 1)
            {
                Push(Gv.Meet, s.Idx, who, s.X, s.Y, s: why);
                SayNow(s, "meet");
            }
            s.MetWho = who; s.MetAt = Turn;
            s.Heart.Long(who, false);
            o.Heart.Long(s.Idx, false);

            foreach (var t in Ties)
            {
                bool pair = (t.A == s.Idx && t.B == who) || (t.B == s.Idx && t.A == who);
                if (!pair || t.Spoken) continue;
                if (t.Since < ThawSteps) continue;      // 아직 때가 아니다
                t.Spoken = true;
                Cast[t.A].Heart.Forgive(t.B);
                Cast[t.B].Heart.Forgive(t.A);
                Push(Gv.Bond, s.Idx, who, s.X, s.Y, n: t.Since,
                     s: $"{t.R.title} · {t.R.reward}");
            }
        }

        static readonly int[] DX = { 1, -1, 0, 0 };
        static readonly int[] DY = { 0, 0, 1, -1 };

        (int x, int y) Beside(GardenShade o, GardenShade me)
        {
            for (int k = 0; k < 4; k++)
            {
                int x = o.X + DX[k], y = o.Y + DY[k];
                if (G.Passable(x, y) && !Taken(x, y, me.Idx)) return (x, y);
            }
            return (o.X, o.Y);
        }

        void Away(GardenShade s, int who)
        {
            var o = Cast[who];
            int bx = s.X, by = s.Y, best = Dist(s, o);
            for (int k = 0; k < 4; k++)
            {
                int x = s.X + DX[k], y = s.Y + DY[k];
                if (!G.Passable(x, y) || Taken(x, y, s.Idx)) continue;
                int d = Math.Abs(x - o.X) + Math.Abs(y - o.Y);
                if (d > best) { best = d; bx = x; by = y; }
            }
            s.X = bx; s.Y = by;
        }

        void Roam(GardenShade s)
        {
            // 갈 곳이 없는 잔상. 대기 자리 주변을 돈다 — 난수를 쓰지만 시드에서 나온다.
            //
            // 실측(걸음 200, 시드 42): 성문에서 시작한 「이름 없는 자」는 대기 자리에서
            // 열네 칸 떨어져 있어 아래 세 칸 조건이 모든 방향을 막았고, 200걸음을 성문에 굳었다.
            // 멀면 우선 그 자리로 간다. 일터가 아니니 일하지는 않는다 — 생업이 없다.
            if (Math.Abs(s.X - s.Wx) + Math.Abs(s.Y - s.Wy) > 3) { Walk(s, s.Wx, s.Wy); Mutter(s, "alone", Doing.Walk); return; }
            int k = _r.I(4);
            int x = s.X + DX[k], y = s.Y + DY[k];
            if (G.Passable(x, y) && !Taken(x, y, s.Idx)
                && Math.Abs(x - s.Wx) + Math.Abs(y - s.Wy) <= 3) { s.X = x; s.Y = y; }
            Push(Gv.Walk, s.Idx, x: s.X, y: s.Y);
            Mutter(s, "alone", Doing.Roam);
        }
    }
}
