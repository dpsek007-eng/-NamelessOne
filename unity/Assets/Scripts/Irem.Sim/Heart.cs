// 뜰의 마음 — 잔상 하나에 하나씩. Mind.cs 와 같은 것이고, 다른 데 서 있을 뿐이다.
//
//   타고난 것은 Mind 에서 빌린다. 성향을 뽑는 공식을 두 벌 만들면
//   같은 사람이 층에서와 뜰에서 다른 사람이 된다.
//
//   뜰에서 생기는 것은 다르다. 여기엔 피해가 없다. 두려움도 원한도 생기지 않는다.
//   대신 손이 하던 일을 하고 싶고(일함), 오래 서 있으면 쉬고 싶고(쉼),
//   혼자 있으면 사람 쪽으로 가고 싶다(어울림).
//
//   고르는 방식은 Mind 와 같다. 후보마다 점수를 내고, 감정은 그것을 기울이기만 한다.
//   한 번 정한 마음은 몇 걸음 간다 — 그래서 뜰이 덜덜거리지 않는다.
//
//   뜰에서는 시간이 흐르지 않는다(docs/03-뜰.md). 그래서 여기에 밤도 노화도 죽음도 없다.
using System;
using System.Collections.Generic;

namespace Irem.Sim
{
    public enum Doing { Stand, Walk, Work, Rest, Meet, Avoid, Roam }

    public struct Urge
    {
        public Doing D;
        public int X, Y;            // Walk 일 때 가려는 칸
        public int Who;             // Meet/Avoid 일 때 상대 인덱스, 없으면 -1
        public string Why;          // work / goto / rest / meet / miss / avoid / roam / stand
        public int Ttl;             // 이 마음이 몇 걸음 더 가는가
        public double Score;
    }

    public sealed class Heart
    {
        /// 타고난 것. 전투의 마음을 그대로 품는다 — 상속도 복사도 아니다.
        public readonly Mind Mind;

        public double Nerve => Mind.Nerve;
        public double Zeal  => Mind.Zeal;
        public double Care  => Mind.Care;

        // ── 뜰에서 생기는 것 ──
        public double Toil = 0.35;   // 일함   — 손이 하던 일을 하고 싶다
        public double Weary;         // 쉼
        public double Warmth;        // 어울림 — 혼자 있으면 오른다
        public double Drift;         // 서성임 — 갈 곳이 없을 때
        public readonly Dictionary<int, double> Miss = new();   // 그리움 — 인연 상대가 멀리 있다
        public readonly Dictionary<int, double> Shy  = new();   // 거리낌 — 아직 못 보는 얼굴

        public Urge Current;
        public bool HasUrge;
        public bool Stirred;         // 거리낌 상대가 눈에 들었거나, 누가 먼저 말을 걸었다
        public string Thought = "";
        public int Worked, Rested;   // 몇 걸음 일했나 — 방치 산출이 아니라 보여주기용 셈

        static double Clamp(double v, double a, double b) => v < a ? a : v > b ? b : v;

        public Heart(Mind m) { Mind = m; }

        /// 성향의 무게에서 — Mind.From 을 거쳐서만 만든다
        public static Heart From(IReadOnlyDictionary<string, double> w)
            => new Heart(Mind.From(w, 1));

        /// 걸음을 고르기 전에 마음이 먼저 움직인다.
        ///   working  지금 제 일터에서 일하고 있다
        ///   resting  쉬고 있다
        ///   homeless 일터가 없다 (이름 없는 자)
        ///   nearby   눈에 보이는 사람 수
        public void Tick(bool working, bool resting, bool homeless, int nearby)
        {
            Toil = Clamp(working ? Toil - 0.14 : Toil + 0.05 * (0.6 + Zeal * 0.5), 0, 1);
            Weary = Clamp(resting ? Weary - 0.11
                                  : Weary + (working ? 0.035 : 0.012), 0, 1);
            Warmth = Clamp(nearby > 0 ? Warmth - 0.09 * nearby
                                      : Warmth + 0.03 * (0.5 + Care * 0.6), 0, 1);
            Drift = Clamp(homeless ? Drift + 0.06 : Drift * 0.85, 0, 1);

            // 그리움은 멀리 있는 동안 자라고 만나면 사그라든다. Garden 이 거리를 재서 넣는다.
            // 거리낌은 스스로 옅어지지 않는다 — 말을 걸어야 풀린다.
        }

        /// 인연 상대가 멀리 있다 / 가까이 있다
        public void Long(int who, bool far)
        {
            Miss.TryGetValue(who, out var m);
            Miss[who] = Clamp(far ? m + 0.04 * (0.5 + Care * 0.5) : m - 0.15, 0, 1);
        }
        public double MissOn(int i) => Miss.TryGetValue(i, out var m) ? m : 0;

        public void Flinch(int who, double v)
        {
            Shy.TryGetValue(who, out var s);
            Shy[who] = Clamp(Math.Max(s, v), 0, 1);
        }
        public void Forgive(int who) { Shy.Remove(who); }
        public double ShyOn(int i) => Shy.TryGetValue(i, out var s) ? s : 0;

        /// 감정은 판단을 뒤집지 않는다. 기울일 뿐이다. (Mind.Colour 와 같은 규칙)
        public double Colour(string why) => why switch
        {
            "work"  => 1 + Toil * 0.55 + Zeal * 0.18,
            "goto"  => 1 + Toil * 0.35,
            "rest"  => 1 + Weary * 0.60,
            "meet"  => 1 + Warmth * 0.45 + Care * 0.22,
            "miss"  => 1 + Care * 0.20,
            "avoid" => 1 + Nerve * 0.20,
            "roam"  => 1 + Drift * 0.40 - Zeal * 0.12,
            _       => 1,
        };

        // 마음이 굳는 시간 — 일은 길고 마주침은 짧다
        public static int TtlFor(string why) => why switch
        {
            "work" => 6, "rest" => 4, "goto" => 3, "miss" => 3, _ => 2,
        };

        /// 후보 중에서 고른다. 점수가 같으면 먼저 온 것이 이긴다 —
        /// 그래서 후보를 쌓는 순서 자체가 사양이다(docs/10 「순서 자체가 사양이다」).
        public Urge Choose(List<Urge> cand)
        {
            var best = new Urge { D = Doing.Stand, Who = -1, Why = "stand", Score = double.MinValue };
            for (int i = 0; i < cand.Count; i++)
            {
                var c = cand[i];
                c.Score *= Colour(c.Why);
                if (c.Score > best.Score) best = c;
            }
            best.Ttl = TtlFor(best.Why);
            Current = best; HasUrge = true; Stirred = false;
            return best;
        }

        /// 하던 마음을 이어간다 — 눈에 걸린 것이 없고 아직 시간이 남았을 때만
        public bool Keeps(bool sawSomething)
        {
            if (!HasUrge || Current.Ttl <= 0 || Stirred || sawSomething) return false;
            var c = Current; c.Ttl--; Current = c;
            return true;
        }

        // ── 무엇을 말하는가 ──
        // 뱅크 이름만 고른다. 문장은 data/lines.json 에 있고 Garden 이 꺼낸다.
        // 없으면 없는 대로 둔다 — 여기에 문장을 적어 두면 구운 대사와 조용히 갈라진다.
        public string BankFor(in Urge u) => u.D switch
        {
            Doing.Work  => "work",
            Doing.Rest  => "rest",
            Doing.Meet  => "meet",
            Doing.Avoid => "avoid",
            Doing.Walk  => "pass",
            Doing.Roam  => "alone",
            _           => "alone",
        };

        /// 뱅크에서 한 줄 — Mind.Speak 와 같은 방식이다. 난수를 쓰지 않으므로 재현된다.
        public static string Pick(string[] bank, int salt)
            => bank == null || bank.Length == 0 ? "" : bank[Math.Abs(salt) % bank.Length];
    }
}
