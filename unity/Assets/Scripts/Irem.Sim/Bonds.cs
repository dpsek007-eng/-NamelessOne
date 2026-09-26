// 인연 — 뜰 한 구역에 함께 있는 잔상 사이에서 성립하는 관계.
//
//   규칙을 여기에 적지 않는다. 규칙은 tools/bonds.py 에 있고
//   tools/export_unity.py 가 garden.json 으로 내보낸다. 여기엔 맞춰보는 논리만 있다.
//   규칙을 두 언어로 각각 적으면 조용히 갈라진다 — 생성기에서 이미 겪은 일이다(docs/10).
//
//   성립과 발동은 다르다. 성립한 것이 열둘이어도 켜지는 것은 넷뿐이고(ACTIVE_SLOTS),
//   나머지는 「대기」다. 전부 인연이면 아무것도 특별하지 않다(docs/03-뜰.md).
using System;
using System.Collections.Generic;
using System.Linq;
using Irem.Data;

namespace Irem.Sim
{
    public struct Bond
    {
        public BondRule R;
        public string Arg;          // 시대 인연일 때 그 시대 이름
        public bool Active;         // 켜졌나, 대기인가
        public int Need;            // 최후 인연일 때 실제로 요구된 인원
        public string Title => R?.title ?? "";
        public string Story => Arg == null ? (R?.story ?? "") : (R?.story ?? "").Replace("{era}", Arg);
    }

    public static class Bonds
    {
        /// 구체적인 것이 우선이다. tools/bonds.py PRIORITY 와 같아야 한다.
        public static int Priority(string kind) => kind switch
        {
            "관계" => 0, "생업" => 1, "계층" => 2, "최후" => 3, "시대" => 4, _ => 9,
        };

        static int Count(IReadOnlyList<AgentDef> z, Func<AgentDef, string> f, string v)
        {
            int n = 0;
            for (int i = 0; i < z.Count; i++) if (f(z[i]) == v) n++;
            return n;
        }

        /// 구역에서 성립하는 인연 — tools/bonds.py:find_bonds() 와 글자까지 같은 목록을 낸다.
        ///
        /// 쌓는 순서(관계 → 계층 → 생업 → 시대 → 최후)와 그 뒤의 정렬까지 파이썬과 같게 둔다.
        /// 값이 같을 때 어느 것이 앞에 오는지가 달라지면 같은 규칙인데 다른 목록이 된다.
        /// C# List.Sort 는 안정 정렬이 아니므로 OrderBy 를 쓴다 — 파이썬 sort 는 안정이다.
        public static List<Bond> Find(IReadOnlyList<AgentDef> zone, IReadOnlyList<BondRule> rules)
        {
            var found = new List<Bond>();
            if (zone == null || rules == null) return found;

            var have = new HashSet<string>(zone.Select(a => a.id));

            // 관계 — 지정된 잔상이 전부 있어야 성립한다. 둘일 때도 있고 셋일 때도 있다.
            foreach (var r in rules)
            {
                if (r.kind != "관계") continue;
                var ms = r.members ?? new string[0];
                if (ms.Length > 0 && ms.All(have.Contains))
                    found.Add(new Bond { R = r, Active = false });
            }
            // 계층 — a 가 na 명, b 가 nb 명. 같은 계층이면 합쳐서 na+nb 명
            foreach (var r in rules)
            {
                if (r.kind != "계층") continue;
                bool ok = r.a == r.b
                    ? Count(zone, x => x.cls, r.a) >= r.na + r.nb
                    : Count(zone, x => x.cls, r.a) >= r.na && Count(zone, x => x.cls, r.b) >= r.nb;
                if (ok) found.Add(new Bond { R = r, Active = false });
            }
            // 생업 — 두 생업이 다 있으면
            foreach (var r in rules)
            {
                if (r.kind != "생업") continue;
                if (Count(zone, x => x.trade, r.a) > 0 && Count(zone, x => x.trade, r.b) > 0)
                    found.Add(new Bond { R = r, Active = false });
            }
            // 시대 — 구역 최다 시대 하나만. 같은 문구가 세 번 뜨던 것을 고친 규칙이다.
            foreach (var r in rules)
            {
                if (r.kind != "시대") continue;
                var top = TopEra(zone, out int n);
                if (top != null && n >= r.n)
                    found.Add(new Bond { R = r, Arg = top, Active = false });
            }
            // 최후 — 구역 인원에 비례한다. 고정 3명은 열여덟 명 구역에서 너무 쉽다.
            foreach (var r in rules)
            {
                if (r.kind != "최후") continue;
                int need = Need(zone.Count, r.ratio);
                if (Count(zone, x => x.role, r.role) >= need)
                    found.Add(new Bond { R = r, Need = need, Active = false });
            }

            return found.OrderBy(b => Priority(b.R.kind)).ToList();
        }

        /// max(3, round(인원 × ratio)). 파이썬 round() 는 은행가 반올림이다(docs/10).
        public static int Need(int people, float ratio)
        {
            double r = ratio <= 0 ? 0.30 : ratio;
            return Math.Max(3, (int)Math.Round(people * r, MidpointRounding.ToEven));
        }

        /// 구역에서 가장 많은 시대. 수가 같으면 이름이 앞선 쪽 —
        /// 파이썬 쪽도 sorted() 로 같게 맞춰 두었다. 안 맞추면 동수일 때 둘이 갈라진다.
        public static string TopEra(IReadOnlyList<AgentDef> zone, out int n)
        {
            var cnt = new Dictionary<string, int>();
            foreach (var a in zone)
            {
                if (string.IsNullOrEmpty(a.era)) continue;
                cnt.TryGetValue(a.era, out var c); cnt[a.era] = c + 1;
            }
            string top = null; n = 0;
            foreach (var k in cnt.Keys.OrderBy(k => k, StringComparer.Ordinal))
                if (cnt[k] > n) { top = k; n = cnt[k]; }
            return top;
        }

        /// 앞의 slots 개만 발동. 나머지는 대기 — 실제 게임에서는 플레이어가 고른다.
        public static void Split(List<Bond> found, int slots)
        {
            for (int i = 0; i < found.Count; i++)
            {
                var b = found[i]; b.Active = i < slots; found[i] = b;
            }
        }
    }
}
