// 유니티 없이 할 수 있는 만큼만 본다 — 문법만 본다.
//
// 이 서버에 유니티가 없다. 그래서 Irem.Game·Irem.Editor 의 C# 은 컴파일할 수가 없다
// (UnityEngine.dll 이 없으니 형을 하나도 못 찾는다). 그러나 괄호가 맞는지,
// switch 식이 닫혔는지, 한글 식별자가 파서를 넘는지는 형 없이도 잴 수 있다.
//
// 즉 이것이 통과한 것은 「문법이 맞다」는 뜻뿐이다. 「유니티에서 돈다」는 뜻이 아니다.
// 그쪽은 IremSelfTest 가 유니티 안에서 재는 자리다.
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.Text;

var roots = args.Length > 0 ? args : new[] { "unity/Assets/Scripts" };
var files = new List<string>();
foreach (var r in roots)
{
    if (File.Exists(r)) files.Add(r);
    else if (Directory.Exists(r)) files.AddRange(Directory.GetFiles(r, "*.cs", SearchOption.AllDirectories));
    else { Console.Error.WriteLine("없는 길: " + r); return 2; }
}
files.Sort(StringComparer.Ordinal);

// 유니티가 실제로 쓰는 것과 같게 둔다. 갈리면 여기서 통과한 것이 저기서 걸린다.
var opts = new CSharpParseOptions(LanguageVersion.CSharp9);

int bad = 0;
foreach (var f in files)
{
    var text = File.ReadAllText(f);
    var tree = CSharpSyntaxTree.ParseText(SourceText.From(text), opts, f);
    foreach (var d in tree.GetDiagnostics())
    {
        if (d.Severity != DiagnosticSeverity.Error) continue;
        var p = d.Location.GetLineSpan().StartLinePosition;
        Console.WriteLine($"✕ {f}:{p.Line + 1}:{p.Character + 1} {d.Id} {d.GetMessage()}");
        bad++;
    }
}
Console.WriteLine($"── 문법 검사: 파일 {files.Count}개, 오류 {bad}건 ──");
Console.WriteLine(bad == 0
    ? "문법은 맞다. 형·유니티 API 는 이 서버에서 잴 수 없다 (유니티가 없다)."
    : "위를 고쳐야 한다.");
return bad == 0 ? 0 : 1;
