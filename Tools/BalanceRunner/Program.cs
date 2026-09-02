using Irem.Data;
using Irem.Sim;

var root = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "../../../../.."));
var T = TableLoader.Load(Path.Combine(root, "unity/Assets/Data/gen_tables.json"));

var mode = args.Length > 0 ? args[0] : "show";
if (mode == "parity")
{
    int n = args.Length > 1 ? int.Parse(args[1]) : 200;
    foreach (var i in Enumerable.Range(0, n))
    {
        var s = ShadeGen.Make(T, i);
        Console.WriteLine($"{i}\t{s.Rarity}\t{s.Bondi}\t{s.Cls}\t{s.Trade}\t{s.Role}\t{s.Era}\t{s.Floor}\t{s.Name}\t{ShadeGen.Ident(s)}");
    }
    return;
}
Console.WriteLine($"생업 {T.Trades.Count}종 · 계층 {T.Strata.Count}종\n");
foreach (var i in new[] { 11, 31, 95, 230, 310 })
{
    var s = ShadeGen.Make(T, i);
    Console.WriteLine($"{new string('★', s.Rarity)}{new string('☆', 5 - s.Rarity)}  {s.Name} — {s.Title}");
    Console.WriteLine($"    {s.Floor}층 {s.Era} · [{s.Cls}] {s.Trade} · {s.Role} · 본디 {s.Bondi} · 시드 {s.Seed}");
    Console.WriteLine($"    생전 | {s.Life}");
    Console.WriteLine($"    최후 | {s.Death}");
    Console.WriteLine($"    스탯 | " + string.Join("  ", s.Stats.Select(kv => $"{kv.Key} {kv.Value}")));
    foreach (var k in s.Skills) Console.WriteLine($"     └ [{k.Bloom}] 「{k.Name}」 — {k.Effect}. {k.Note}");
    Console.WriteLine();
}
