// 무명 잔상 생성기 — tools/shade_gen4.py 의 C# 포팅.
// 같은 (seed, world) 는 파이썬과 완전히 같은 잔상을 낸다. 난수 호출 순서가 곧 사양이다.
using System;
using System.Collections.Generic;
using System.Linq;
using Irem.Data;

namespace Irem.Sim
{
    public static class ShadeGen
    {
        // 파이썬 sorted(dict.items()) 와 같은 순서를 보장한다
        static IEnumerable<KeyValuePair<int,double>> SortedI(Dictionary<int,double> d)
            => d.OrderBy(kv => kv.Key);
        static IEnumerable<KeyValuePair<string,double>> SortedS(Dictionary<string,double> d)
            => d.OrderBy(kv => kv.Key, StringComparer.Ordinal);

        static int WPick(ref Rng r, Dictionary<int,double> d)
        {
            double x = r.F(), a = 0;
            int last = 0;
            foreach (var kv in SortedI(d)) { a += kv.Value; last = kv.Key; if (x <= a) return kv.Key; }
            return d.Keys.Max();
        }
        static string WPick(ref Rng r, Dictionary<string,double> d)
        {
            double x = r.F(), a = 0;
            string last = null;
            foreach (var kv in SortedS(d)) { a += kv.Value; last = kv.Key; if (x <= a) return kv.Key; }
            return last;
        }
        static T Pick<T>(ref Rng r, IList<T> l) => l[r.I(l.Count)];

        static List<T> Sample<T>(ref Rng r, IList<T> src, int k)
        {
            var l = new List<T>(src); var outp = new List<T>();
            int n = Math.Min(k, l.Count);
            for (int i = 0; i < n; i++) { int j = r.I(l.Count); outp.Add(l[j]); l.RemoveAt(j); }
            return outp;
        }

        /// 한글 조사 — 받침 유무로 고른다
        public static string Josa(string w, string withT, string without)
        {
            char c = w[w.Length - 1];
            if (c < '가' || c > '힣') return without;
            return ((c - '가') % 28) != 0 ? withT : without;
        }

        public static Shade Make(Tables T, long seed, int world = 1, int rarity = 0)
        {
            ulong s;
            unchecked { s = (ulong)seed * 0x9E3779B97F4A7C15UL ^ ((ulong)world * 0xBF58476D1CE4E5B9UL); }
            var r = new Rng(s);

            int rarPre = rarity != 0 ? rarity : WPick(ref r, T.Pull);
            string cls = WPick(ref r, T.ClsByRarity[rarPre]);
            var t = Pick(ref r, T.ByCls[cls]);

            var eras = T.EraOrder.Where(e => t.Eras == null || t.Eras.Contains(e)).ToList();
            string era = Pick(ref r, eras);
            var (lo, hi) = T.Eras[era];
            int floor = lo + r.I(hi - lo + 1);
            string role = Pick(ref r, T.Roles);

            int rar = rarPre;
            int bondi = WPick(ref r, T.Bondi[rar]);

            var dailyPool = t.Daily.Where(d => d.Eras == null || d.Eras.Contains(era))
                                   .Select(d => d.Text).ToList();
            string daily = Pick(ref r, dailyPool);
            var (habit, asName) = Pick(ref r, t.Habit);

            bool named = T.AlwaysNamed.Contains(cls)
                       || (T.RarelyNamed.Contains(cls) ? rar >= 4 : rar >= 3);
            string name = named
                ? Pick(ref r, T.A) + Pick(ref r, T.M) + Pick(ref r, T.B)
                : $"{Pick(ref r, T.Qual)} {asName} {Pick(ref r, T.Call)}";

            string title = named ? $"{era}의 {t.N}" : $"{floor}층 · 이름이 남지 않음";
            string life = $"{Pick(ref r, T.EraOpen[era])}. {daily}. {habit}.";

            string tpl = Pick(ref r, T.End[role]);
            string tgt = tpl.Contains("{place}{을}") ? t.Place : t.Obj;
            string death = tpl.Replace("{place}", t.Place).Replace("{obj}", t.Obj)
                              .Replace("{을}", Josa(tgt, "을", "를"))
                         + ". " + Pick(ref r, T.Tail[role]) + ".";

            double pool = T.Pool[rar] * (0.94 + r.F() * 0.12);
            var bias = T.Bias[role];
            var w = new Dictionary<string, double>();
            foreach (var st in T.StatOrder) w[st] = bias[st] * (0.72 + r.F() * 0.62);
            double tot = w.Values.Sum();
            var stats = new Dictionary<string, int>();
            foreach (var st in T.StatOrder)
                stats[st] = Math.Max(1, (int)Math.Round(pool * w[st] / tot, MidpointRounding.ToEven));
            stats["잔존"] *= 4;
            var growth = new Dictionary<string, double>();
            foreach (var st in T.StatOrder)
                growth[st] = Math.Round(stats[st] * (0.030 + r.F() * 0.048), 2, MidpointRounding.ToEven);

            int npk = 3 + r.I(2);
            var basePool = new List<(string Verb, string Eff)>(T.Skill[role]);
            if (r.F() < 0.45)
            {
                var others = T.Roles.Where(x => x != role).ToList();
                basePool.AddRange(Sample(ref r, T.Skill[Pick(ref r, others)], 2));
            }
            var picks = Sample(ref r, basePool, npk);
            var motifs = Sample(ref r, t.Motif, npk);

            var skills = new List<SkillInst>();
            for (int i = 0; i < picks.Count; i++)
            {
                string bl = Pick(ref r, T.Bloom);
                int v = Pick(ref r, T.VList);
                var conds = new List<string> {
                    $"{era} 층", $"뜰에 {t.G} 배치 중", "아군 3명 이하",
                    $"{Math.Max(1, floor - 5)}~{Math.Min(99, floor + 5)}층", "잔존 절반 이하" };
                string cond = Pick(ref r, conds);
                skills.Add(new SkillInst {
                    Name = motifs[i], Verb = picks[i].Verb,
                    Effect = picks[i].Eff.Replace("{v}", v.ToString()),
                    Bloom = bl,
                    Note = Pick(ref r, T.BloomNote[bl]).Replace("{cond}", cond)
                });
            }

            string sil = Pick(ref r, T.Sil);
            string col = Pick(ref r, T.Col);
            string dtl = Pick(ref r, T.Dtl);

            return new Shade {
                Seed = seed, World = world, Name = name, Title = title, Rarity = rar, Bondi = bondi,
                Role = role, Era = era, Floor = floor, Cls = cls, Trade = t.N, Garden = t.G,
                Life = life, Death = death, Stats = stats, Growth = growth, Skills = skills,
                Silhouette = sil, KeyColor = col, Symbol = t.Obj, Detail = dtl
            };
        }

        /// '같은 사람'인지 판정하는 기준
        public static string Ident(Shade s)
            => string.Join("|", s.Name, s.Trade, s.Floor, s.Role, s.Death,
                           string.Join(",", s.Skills.Select(k => k.Name).OrderBy(x => x, StringComparer.Ordinal)));
    }
}
