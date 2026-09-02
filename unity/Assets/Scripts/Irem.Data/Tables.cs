// 순수 데이터. 유니티도 JSON 라이브러리도 참조하지 않는다.
using System.Collections.Generic;

namespace Irem.Data
{
    public sealed class Trade
    {
        public string N, Obj, Place, G, Cls;
        public List<string> Eras;                       // null 이면 전 시대
        public List<(string Text, List<string> Eras)> Daily = new();
        public List<(string Text, string AsName)> Habit = new();
        public List<string> Motif = new();
    }

    public sealed class Tables
    {
        public List<string> Strata = new();
        public List<Trade> Trades = new();
        public Dictionary<string,(int Lo,int Hi)> Eras = new();
        public Dictionary<string,List<string>> EraOpen = new();
        public List<string> Roles = new();
        public Dictionary<string,List<string>> End = new(), Tail = new();
        public List<string> Qual = new(), Call = new(), A = new(), M = new(), B = new();
        public Dictionary<string,List<(string Verb,string Eff)>> Skill = new();
        public List<string> Bloom = new();
        public Dictionary<string,List<string>> BloomNote = new();
        public List<string> Sil = new(), Dtl = new(), Col = new();
        public Dictionary<int,double> Pull = new();
        public Dictionary<int,Dictionary<int,double>> Bondi = new();
        public Dictionary<int,int> Pool = new();
        public Dictionary<string,Dictionary<string,double>> Bias = new();
        public Dictionary<int,Dictionary<string,double>> ClsByRarity = new();
        public HashSet<string> AlwaysNamed = new(), RarelyNamed = new();
        public List<string> EraOrder = new();    // 시대 나열 순서 (난수 소비 순서에 영향)
        public List<string> StatOrder = new();   // 잔존·의지·자취·공명
        public List<int> VList = new();

        public Dictionary<string,List<Trade>> ByCls = new();
        public void Index()
        {
            ByCls.Clear();
            foreach (var t in Trades)
            {
                if (!ByCls.TryGetValue(t.Cls, out var l)) ByCls[t.Cls] = l = new List<Trade>();
                l.Add(t);
            }
        }
    }

    /// 생성된 잔상. 저장에는 Seed/World/Rarity/Bondi 만 남긴다 (10-시스템-구조.md)
    public sealed class Shade
    {
        public long Seed; public int World;
        public string Name, Title, Role, Era, Cls, Trade, Garden, Life, Death;
        public int Rarity, Bondi, Floor;
        public Dictionary<string,int> Stats = new();
        public Dictionary<string,double> Growth = new();
        public List<SkillInst> Skills = new();
        public string Silhouette, KeyColor, Symbol, Detail;
    }
    public sealed class SkillInst { public string Name, Verb, Effect, Bloom, Note; }
}
