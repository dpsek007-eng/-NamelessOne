// 뜰을 유니티 없이 돌린다. 도커의 dotnet SDK 로 실행한다 — 이 서버에 dotnet 을 설치하지 않았다.
//
//   docker run --rm -v "$PWD":/w -w /w mcr.microsoft.com/dotnet/sdk:8.0 \
//     dotnet run --project Tools/GardenRunner -- garden 200 42
//
// 같은 시드를 두 번 돌려 diff 가 0 이어야 한다. 0 이 아니면 뜰이 재현되지 않는 것이고,
// 그러면 방치 계산도 전승도 성립하지 않는다(docs/10).
using System.Text.Json;
using Irem.Data;
using Irem.Sim;

static GardenTables Load(string root)
{
    var path = Path.Combine(root, "unity/Assets/Resources/Irem/garden.json");
    var o = new JsonSerializerOptions { IncludeFields = true };
    return JsonSerializer.Deserialize<GardenTables>(File.ReadAllText(path), o);
}

var root = Directory.GetCurrentDirectory();
while (!Directory.Exists(Path.Combine(root, "unity")) && Directory.GetParent(root) != null)
    root = Directory.GetParent(root).FullName;

var mode = args.Length > 0 ? args[0] : "garden";
var T = Load(root);

if (mode == "bonds")
{
    // 파이썬과 맞춰 보기 위한 출력. 한 줄에 하나, 탭으로 나눈다.
    var zone = T.agents.ToList();
    var found = Bonds.Find(zone, T.bonds);
    Bonds.Split(found, T.activeSlots);
    Console.WriteLine($"# 인원 {zone.Count} · 규칙 {T.bonds.Length} · 칸 {T.activeSlots}");
    foreach (var b in found)
        Console.WriteLine($"{b.R.kind}\t{b.R.id}\t{(b.Active ? "발동" : "대기")}\t{b.Need}\t{b.Arg}");
    return;
}

if (mode == "map")
{
    var g0 = GardenSetup.BuildGrid(T);
    int walk = 0;
    for (int y = 0; y < g0.H; y++) for (int x = 0; x < g0.W; x++) if (g0.Passable(x, y)) walk++;
    Console.WriteLine($"뜰 {g0.W}×{g0.H} = {g0.W * g0.H}칸 · 딛을 수 있는 칸 {walk} · 일터 {T.stations.Length}곳");
    foreach (var s in T.stations)
    {
        var gate = T.Station("성문");
        bool ok = g0.Connected(gate.x, gate.y, s.x, s.y);
        Console.WriteLine($"  {s.name}\t({s.x},{s.y})\t{(ok ? "이어짐" : "막힘")}\t{s.prop}");
    }
    return;
}

int ticks = args.Length > 1 ? int.Parse(args[1]) : 200;
ulong seed = args.Length > 2 ? ulong.Parse(args[2]) : 42UL;

var G = GardenSetup.Build(T, seed);

Console.WriteLine($"# 시드 {seed} · 잔상 {G.Cast.Count} · 걸음 {ticks}");
foreach (var s in G.Cast)
    Console.WriteLine($"세움\t{s.Idx}\t{s.Id}\t{s.Name}\t{s.Def.role}\t{s.Def.trade}\t" +
                      $"{(s.Homeless ? "없음" : s.Place)}\t일터({s.Wx},{s.Wy})\t선자리({s.X},{s.Y})\t" +
                      $"{s.Def.body}+{s.Def.garment}\t걸음{s.Mv}\t시야{s.Sight}");
foreach (var b in G.Found)
    Console.WriteLine($"인연\t{b.R.kind}\t{b.R.id}\t{(b.Active ? "발동" : "대기")}\t{b.Title}");
foreach (var t in G.Ties)
    Console.WriteLine($"가닥\t{t.R.id}\t{G.Cast[t.A].Name} → {G.Cast[t.B].Name}\t거리낌 {(t.R.shy ? "있음" : "없음")}");

int at = 0;
for (int i = 0; i < ticks; i++)
{
    G.Tick();
    while (at < G.Log.Count)
    {
        var e = G.Log[at++];
        var who = e.A >= 0 ? G.Cast[e.A].Name : "";
        var to = e.T >= 0 ? G.Cast[e.T].Name : "";
        Console.WriteLine($"{G.Turn}\t{e.K}\t{who}\t{to}\t({e.X},{e.Y})\t{e.N}\t{e.S}");
    }
}

// ── 돌린 뒤에 잰다 ──
int arrived = 0, stuck = 0, worked = 0;
foreach (var s in G.Cast)
{
    if (s.Homeless) continue;
    if (s.X == s.Wx && s.Y == s.Wy) arrived++;
    if (s.Heart.Worked == 0) stuck++;
    worked += s.Heart.Worked;
}
int spoke = 0; foreach (var t in G.Ties) if (t.Spoken) spoke++;
Console.WriteLine($"# 걸음 {G.Turn} 뒤 — 일터에 선 잔상 {arrived}/{G.Cast.Count - 1} · " +
                  $"한 번도 일하지 못한 잔상 {stuck} · 일한 걸음 합 {worked} · " +
                  $"말을 건 인연 {spoke}/{G.Ties.Count} · 사건 {G.Log.Count}건");
