// 마음 — 잔상 하나에 하나씩. 이것이 "에이전트"다.
//
//   타고난 것(성향)은 소환될 때 정해지고 변하지 않는다.
//   두려움·결의·피로·원한·빚은 이 전투에서 생긴다.
//   그래서 같은 성향 둘이 같은 층에서 다르게 움직인다.
//
//   행동은 매 턴 새로 고르지 않는다. 한 번 정한 마음은 몇 턴 간다.
//   크게 맞거나 제 편이 흐려지면 그때 다시 생각한다.
using System;
using System.Collections.Generic;

namespace Irem.Sim
{
    public enum Act { Wait, Move, Hit, Heal, Ring, Mark }

    public struct Intent
    {
        public Act A;
        public int X, Y;            // Move 일 때
        public int Target;          // Hit/Heal 일 때 상대 인덱스, 없으면 -1
        public string Why;          // advance / retreat / guard / heal / attack / ...
        public int Ttl;             // 이 마음이 몇 턴 더 가는가
        public double Score;
    }

    public sealed class Mind
    {
        // ── 타고난 것 ──
        public double Nerve;        // 겁의 크기. 「물러서지 않는다」는 낮다
        public double Zeal;         // 앞으로 나서는 성질
        public double Care;         // 남을 챙기는 성질

        // ── 이 전투에서 생긴 것 ──
        public double Fear, Resolve = 0.45, Fatigue, Shake;
        public readonly Dictionary<int, double> Grudge = new();   // 나를 친 것
        public readonly Dictionary<int, int> Debt = new();        // 나를 살린 것
        public Intent Current;
        public bool HasIntent;
        public int LastHp, Took, SawFall;
        public string Thought = "";

        static double Clamp(double v, double a, double b) => v < a ? a : v > b ? b : v;

        /// 성향의 무게에서 타고난 성질을 뽑는다
        public static Mind From(IReadOnlyDictionary<string, double> w, int hp)
        {
            double W(string k) => w != null && w.TryGetValue(k, out var v) ? v : 0;
            return new Mind
            {
                Nerve   = Clamp(0.45 + W("retreat") * 0.22, 0.08, 1.3),
                Zeal    = Clamp(0.50 + (W("attack") + W("advance") + W("ring")) * 0.09, 0.15, 1.6),
                Care    = Clamp(0.45 + (W("heal") + W("guard")) * 0.11, 0.10, 1.6),
                LastHp  = hp,
            };
        }

        /// 행동을 고르기 전에 마음이 먼저 움직인다
        public void Tick(int hp, int maxHp)
        {
            int lost = Math.Max(0, LastHp - hp);
            LastHp = hp; Took = lost;

            Fear = Clamp(
                  Fear * 0.78
                + (double)lost / maxHp * 1.5 * Nerve
                + SawFall * 0.28 * Nerve
                + ((double)hp / maxHp < 0.35 ? 0.08 * Nerve : 0), 0, 1.0);

            Resolve = Clamp(
                  Resolve * 0.93 + 0.07 * Zeal
                + (Debt.Count > 0 ? 0.06 : 0)
                - Fear * 0.08, 0, 1.5);

            Fatigue = Math.Min(1, Fatigue + 0.022);
            Shake   = Math.Max(0, Fear - Resolve * 0.55);
        }

        /// 크게 맞았거나 제 편이 흐려지는 것을 봤다 — 하던 생각을 접는다
        public bool Shocked(int maxHp) => Took > maxHp * 0.11 || SawFall > 0;

        public void Remember(int by, int dmg, int maxHp)
        {
            Grudge.TryGetValue(by, out var g);
            Grudge[by] = Math.Min(1.2, g + (double)dmg / maxHp * 2.2);
        }
        public void Owe(int to)
        {
            Debt.TryGetValue(to, out var n);
            Debt[to] = n + 1;
        }
        public double GrudgeOn(int i) => Grudge.TryGetValue(i, out var g) ? g : 0;

        /// 감정은 판단을 뒤집지 않는다. 기울일 뿐이다.
        public double Colour(string why) => why switch
        {
            "attack"   => 1 - Shake * 0.30,
            "mark"     => 1 + Resolve * 0.12,
            "close"    => 1 - Shake * 0.35,
            "guard"    => 1 + Shake * 0.35 + Care * 0.15,
            "heal"     => 1 + Care * 0.25 + (Debt.Count > 0 ? 0.20 : 0),
            "advance"  => 1 - Shake * 0.25 - Fatigue * 0.15,
            "ring"     => 1 + Resolve * 0.35,
            "retreat"  => 1 + Shake * 0.55,
            "keepdist" => 1 + Shake * 0.45,
            _          => 1,
        };

        // 마음이 굳는 시간 — 물러섬은 짧고, 나아감과 지킴은 길다
        public static int TtlFor(string why) => why switch
        {
            "guard" => 2, "advance" => 2, _ => 1,
        };

        // ── 무엇을 생각하는가 ──
        static readonly Dictionary<string, string[]> Say = new()
        {
            ["afraid"] = new[] { "여기서는 안 됩니다", "손이 떨립니다", "더는 못 버팁니다" },
            ["grudge"] = new[] { "저건 제가 봅니다", "저놈은 기억합니다", "아까 그것입니다" },
            ["repay"]  = new[] { "이번엔 제가 갑니다", "그때 붙잡아 주셨죠", "받은 것이 있습니다" },
            ["cover"]  = new[] { "뒤는 보지 마십시오", "제 뒤로 오십시오", "여기는 제가 섭니다" },
            ["seek"]   = new[] { "뭔가 있습니다", "저쪽이 이상합니다", "조금만 더 보겠습니다" },
            ["hold"]   = new[] { "아직 아무것도 없습니다", "기다립니다", "조용합니다" },
            ["spent"]  = new[] { "숨이 찹니다", "다리가 무겁습니다" },
        };

        public string Speak(string bank, int salt)
        {
            if (!Say.TryGetValue(bank, out var l)) return "";
            return l[Math.Abs(salt) % l.Length];
        }

        /// 성향의 한 줄에 지금의 상태가 얹힌다
        public string ThoughtFor(in Intent d, string traitLine, bool grudged, bool sawAnything, int salt)
        {
            if (Shake > 0.45)                       return Speak("afraid", salt);
            if (d.Why == "heal" && Debt.Count > 0)  return Speak("repay", salt);
            if (d.Why == "attack" && grudged)       return Speak("grudge", salt);
            if (d.Why == "guard")                   return Speak("cover", salt);
            if (d.A == Act.Wait)                    return Speak("hold", salt);
            if (Fatigue > 0.6 && d.Why == "advance" && Resolve < 0.5) return Speak("spent", salt);
            if (d.Why == "advance" && !sawAnything) return Speak("seek", salt);
            return traitLine ?? "";
        }
    }
}
