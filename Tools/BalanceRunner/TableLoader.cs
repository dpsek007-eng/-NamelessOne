// JSON → POCO. Irem.Data / Irem.Sim 은 JSON 을 모른다 (10-시스템-구조.md 계층 분리).
using System.Text.Json;
using Irem.Data;

static class TableLoader
{
    static List<string> Strs(JsonElement e) => e.EnumerateArray().Select(x => x.GetString()).ToList();

    public static Tables Load(string path)
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        var j = doc.RootElement;
        var T = new Tables();

        T.Strata = Strs(j.GetProperty("strata"));
        foreach (var e in j.GetProperty("trades").EnumerateArray())
        {
            var t = new Trade {
                N = e.GetProperty("n").GetString(), Obj = e.GetProperty("obj").GetString(),
                Place = e.GetProperty("place").GetString(), G = e.GetProperty("g").GetString(),
                Cls = e.GetProperty("cls").GetString(),
                Eras = e.GetProperty("eras").ValueKind == JsonValueKind.Null ? null : Strs(e.GetProperty("eras"))
            };
            foreach (var d in e.GetProperty("daily").EnumerateArray())
            {
                var a = d.EnumerateArray().ToArray();
                t.Daily.Add((a[0].GetString(), a[1].ValueKind == JsonValueKind.Null ? null : Strs(a[1])));
            }
            foreach (var h in e.GetProperty("habit").EnumerateArray())
            {
                var a = h.EnumerateArray().ToArray();
                t.Habit.Add((a[0].GetString(), a[1].GetString()));
            }
            t.Motif = Strs(e.GetProperty("motif"));
            T.Trades.Add(t);
        }
        foreach (var p in j.GetProperty("eras").EnumerateObject())
        {
            var a = p.Value.EnumerateArray().Select(x => x.GetInt32()).ToArray();
            T.Eras[p.Name] = (a[0], a[1]);
        }
        foreach (var p in j.GetProperty("eraOpen").EnumerateObject()) T.EraOpen[p.Name] = Strs(p.Value);
        T.Roles = Strs(j.GetProperty("roles"));
        foreach (var p in j.GetProperty("end").EnumerateObject())  T.End[p.Name]  = Strs(p.Value);
        foreach (var p in j.GetProperty("tail").EnumerateObject()) T.Tail[p.Name] = Strs(p.Value);
        T.Qual = Strs(j.GetProperty("qual")); T.Call = Strs(j.GetProperty("call"));
        T.A = Strs(j.GetProperty("A")); T.M = Strs(j.GetProperty("M")); T.B = Strs(j.GetProperty("B"));
        foreach (var p in j.GetProperty("skill").EnumerateObject())
            T.Skill[p.Name] = p.Value.EnumerateArray()
                .Select(x => { var a = x.EnumerateArray().ToArray(); return (a[0].GetString(), a[1].GetString()); })
                .ToList();
        T.Bloom = Strs(j.GetProperty("bloom"));
        foreach (var p in j.GetProperty("bloomNote").EnumerateObject()) T.BloomNote[p.Name] = Strs(p.Value);
        T.Sil = Strs(j.GetProperty("sil")); T.Dtl = Strs(j.GetProperty("dtl")); T.Col = Strs(j.GetProperty("col"));
        foreach (var p in j.GetProperty("pull").EnumerateObject()) T.Pull[int.Parse(p.Name)] = p.Value.GetDouble();
        foreach (var p in j.GetProperty("bondi").EnumerateObject())
        {
            var m = new Dictionary<int,double>();
            foreach (var q in p.Value.EnumerateObject()) m[int.Parse(q.Name)] = q.Value.GetDouble();
            T.Bondi[int.Parse(p.Name)] = m;
        }
        foreach (var p in j.GetProperty("pool").EnumerateObject()) T.Pool[int.Parse(p.Name)] = p.Value.GetInt32();
        foreach (var p in j.GetProperty("bias").EnumerateObject())
        {
            var m = new Dictionary<string,double>();
            foreach (var q in p.Value.EnumerateObject()) m[q.Name] = q.Value.GetDouble();
            T.Bias[p.Name] = m;
        }
        foreach (var p in j.GetProperty("clsByRarity").EnumerateObject())
        {
            var m = new Dictionary<string,double>();
            foreach (var q in p.Value.EnumerateObject()) m[q.Name] = q.Value.GetDouble();
            T.ClsByRarity[int.Parse(p.Name)] = m;
        }
        T.AlwaysNamed = new HashSet<string>(Strs(j.GetProperty("alwaysNamed")));
        T.RarelyNamed = new HashSet<string>(Strs(j.GetProperty("rarelyNamed")));
        T.EraOrder = Strs(j.GetProperty("eraOrder"));
        T.StatOrder = Strs(j.GetProperty("statOrder"));
        T.VList = j.GetProperty("vList").EnumerateArray().Select(x => x.GetInt32()).ToList();
        T.Index();
        return T;
    }
}
