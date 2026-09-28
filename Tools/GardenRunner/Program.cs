// 뜰을 유니티 없이 돌린다. 도커의 dotnet SDK 로 실행한다 — 이 서버에 dotnet 을 설치하지 않았다.
//
//   docker run --rm -v "$PWD":/w -w /w mcr.microsoft.com/dotnet/sdk:8.0 \
//     dotnet run --project Tools/GardenRunner -- garden 200 42
//
// 같은 시드를 두 번 돌려 diff 가 0 이어야 한다. 0 이 아니면 뜰이 재현되지 않는 것이고,
// 그러면 방치 계산도 전승도 성립하지 않는다(docs/10).
using System.Globalization;
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

if (mode == "web")
{
    // 웹 뷰어가 재생할 사건 목록을 내보낸다.
    //
    // 유니티가 이 서버에 없어 3D 를 눈으로 볼 수가 없다. 그런데 계산은 순수 C# 이고
    // 3D 몸은 이미 GLB 로 있다(chars/out/cast, 동작 네 벌). 그래서 **유니티의
    // GardenDirector 가 재생하는 것과 같은 목록**을 브라우저가 재생하게 한다.
    //
    // 여기서 다시 계산하지 않는다 — 위 garden 모드와 같은 Garden 을 굴려 그 Log 를 적는다.
    // 계산을 두 벌 적으면 웹에서 본 것과 유니티에서 도는 것이 조용히 갈라진다(docs/10).
    int wt = args.Length > 1 ? int.Parse(args[1]) : 600;
    ulong ws = args.Length > 2 ? ulong.Parse(args[2]) : 42UL;
    var W = GardenSetup.Build(T, ws);
    // 세운 자리를 먼저 적어 둔다. 재생은 여기서 시작해야 한다 —
    // 다 굴린 뒤의 자리를 적으면 브라우저는 결말부터 보게 된다.
    int[] ix = new int[W.Cast.Count], iy = new int[W.Cast.Count];
    foreach (var c in W.Cast) { ix[c.Idx] = c.X; iy[c.Idx] = c.Y; }
    // 사건에는 몇 걸음째인지가 없다. 굴리면서 같이 적어 둔다.
    var turns = new List<int>();
    for (int i = 0; i < wt; i++)
    {
        W.Tick();
        while (turns.Count < W.Log.Count) turns.Add(W.Turn);
    }

    var sb = new System.Text.StringBuilder();
    string Q(string x) => JsonSerializer.Serialize(x ?? "");
    // 소수점은 로캘을 타지 않게 적는다. 쉼표가 찍히면 JSON 이 깨진다.
    string N(float v) => v.ToString("0.###", CultureInfo.InvariantCulture);
    sb.Append("{\n");
    sb.Append($"\"note\":\"Tools/GardenRunner -- web {wt} {ws} 가 쓴다. 손으로 고치지 마라.\",\n");
    sb.Append($"\"seed\":{ws},\"ticks\":{wt},\"w\":{T.w},\"h\":{T.h},\n");
    sb.Append("\"map\":[");
    for (int y = 0; y < T.map.Length; y++) sb.Append((y > 0 ? "," : "") + Q(T.map[y]));
    sb.Append("],\n\"stations\":[");
    for (int i = 0; i < T.stations.Length; i++)
    {
        var st = T.stations[i];
        sb.Append((i > 0 ? "," : "") + $"{{\"name\":{Q(st.name)},\"prop\":{Q(st.prop)},"
                + $"\"desc\":{Q(st.desc)},\"x\":{st.x},\"y\":{st.y}}}");
    }
    sb.Append("],\n\"cast\":[");
    for (int i = 0; i < W.Cast.Count; i++)
    {
        var c = W.Cast[i];
        sb.Append((i > 0 ? "," : "") + $"{{\"idx\":{c.Idx},\"id\":{Q(c.Id)},\"name\":{Q(c.Name)},"
                + $"\"role\":{Q(c.Def.role)},\"cls\":{Q(c.Def.cls)},\"trade\":{Q(c.Def.trade)},"
                + $"\"slug\":{Q(c.Def.garment)},\"col\":{Q(c.Def.col)},\"place\":{Q(c.Place)},"
                + $"\"wx\":{c.Wx},\"wy\":{c.Wy},\"x\":{ix[c.Idx]},\"y\":{iy[c.Idx]},"
                // 몸의 박자. 계산하는 쪽(GardenSetup)이 낸 값을 그대로 내보낸다.
                + $"\"phase\":{N(c.Phase)},\"tempo\":{N(c.Tempo)},\"breath\":{N(c.Breath)}}}");
    }
    sb.Append("],\n\"bonds\":[");
    for (int i = 0; i < W.Ties.Count; i++)
    {
        var t = W.Ties[i];
        sb.Append((i > 0 ? "," : "") + $"{{\"a\":{t.A},\"b\":{t.B},\"shy\":{(t.R.shy ? "true" : "false")},"
                + $"\"title\":{Q(t.R.title)}}}");
    }
    // 사건은 배열의 배열로 적는다. 열 이름을 매 줄 되풀이하면 파일이 몇 배로 커진다.
    sb.Append("],\n\"cols\":[\"turn\",\"k\",\"a\",\"t\",\"x\",\"y\",\"n\",\"s\"],\n\"log\":[");
    for (int i = 0; i < W.Log.Count; i++)
    {
        var e = W.Log[i];
        sb.Append((i > 0 ? "," : "") + $"\n[{turns[i]},{(int)e.K},{e.A},{e.T},{e.X},{e.Y},{e.N},{Q(e.S)}]");
    }
    sb.Append("\n],\n\"kinds\":[");
    var kn = Enum.GetNames(typeof(Gv));
    for (int i = 0; i < kn.Length; i++) sb.Append((i > 0 ? "," : "") + Q(kn[i]));
    sb.Append("]\n}\n");

    var outp = Path.Combine(root, "viewer/garden.json");
    File.WriteAllText(outp, sb.ToString());
    Console.WriteLine($"viewer/garden.json — 시드 {ws} · 걸음 {wt} · 잔상 {W.Cast.Count} · "
                    + $"일터 {T.stations.Length} · 사건 {W.Log.Count}건 · "
                    + $"{new FileInfo(outp).Length:N0} bytes");
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
