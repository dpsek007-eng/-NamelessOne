// 편성 화면 — 어느 층에, 누구를 보낼 것인가.
//   판정은 하지 않는다. Irem.Sim/Setup.cs 하나만 쓴다. 화면은 보여 줄 뿐이다.
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using Irem.Data;
using Irem.Sim;

namespace Irem.Game
{
    public sealed class RosterUI : MonoBehaviour
    {
        public BattleTables T;
        public FloorDef Floor;
        public List<List<CharDef>> Teams = new();

        RectTransform _floorList, _midBody, _midBar, _rosterList;
        TextMeshProUGUI _rosterCount;
        (int t, int s) _picking = (-1, -1);
        string _filter = "";
        static readonly string[] Roles = { "", "수호", "저항", "헌신", "탐구", "도피" };
        static readonly Dictionary<string, string> RouteName = new()
        {
            ["force"] = "돌파", ["guard"] = "수호의 길", ["seek"] = "탐구의 길",
            ["devote"] = "헌신의 길", ["resist"] = "저항의 길", ["flee"] = "도피의 길",
            ["trade"] = "생업의 길", ["era"] = "그 자리에 있던 사람", ["weak"] = "이름 없는 길",
            ["wall"] = "담의 약점", ["drain"] = "배수로", ["unseen"] = "묘수",
        };

        public void Begin(BattleTables t, FloorDef f, Camera cam)
        {
            T = t;
            if (cam != null)
            {
                cam.orthographic = true;
                cam.clearFlags = CameraClearFlags.SolidColor;
                cam.backgroundColor = Pal.Ground;
            }
            Build();
            Select(f ?? T.floors[0]);
        }

        void Select(FloorDef f)
        {
            Floor = f;
            Teams = new List<List<CharDef>>();
            for (int i = 0; i < Mathf.Max(1, f.teams); i++) Teams.Add(new List<CharDef>());
            _picking = (-1, -1);
            RefreshFloors(); RefreshMid(); RefreshRoster();
        }

        bool Used(CharDef c) => Teams.Any(t => t.Contains(c));
        List<CharDef> Clean(List<CharDef> t) => t.Where(x => x != null).ToList();

        void Put(CharDef c)
        {
            if (Used(c)) return;
            int ti = _picking.t, si = _picking.s;
            if (ti < 0)
                for (int i = 0; i < Teams.Count && ti < 0; i++)
                    if (Teams[i].Count(x => x != null) < Floor.slot)
                    {
                        ti = i;
                        si = Teams[i].IndexOf(null);
                        if (si < 0) si = Teams[i].Count;
                    }
            if (ti < 0) return;
            while (Teams[ti].Count <= si) Teams[ti].Add(null);
            Teams[ti][si] = c;
            _picking = (-1, -1);
            RefreshMid(); RefreshRoster();
        }

        // ── 뼈대 ────────────────────────────────────────────────────
        void Build()
        {
            var canvas = UIKit.Root(transform, "편성 UI");
            var root = (RectTransform)canvas.transform;

            var bg = UIKit.Panel(root, "bg", Pal.Ground, 0);
            UIKit.Stretch(bg.rectTransform);
            bg.sprite = null;

            // 머리말
            var head = UIKit.Rect(root, "head");
            head.anchorMin = new Vector2(0, 1); head.anchorMax = new Vector2(1, 1);
            head.pivot = new Vector2(0.5f, 1);
            head.offsetMin = new Vector2(0, -76); head.offsetMax = new Vector2(0, 0);
            var t1 = UIKit.Label(head, "이렘의 탑", 30, Pal.Ink, TextAlignmentOptions.BottomLeft, true);
            UIKit.At(t1.rectTransform, 22, -14, 400, 38);
            var t2 = UIKit.Label(head, "잔상 편성 — 전투력이 요구치의 80%를 밑돌면 거의 못 이기고, 넘어서면 대체로 이깁니다",
                                 14, Pal.Muted);
            UIKit.At(t2.rectTransform, 24, -52, 900, 20);

            // 세 칸
            var left = UIKit.Panel(root, "floors", Pal.Panel, 12, Pal.Line);
            UIKit.Col(left.rectTransform, 16, 230, 84, 16);
            var lab = UIKit.Label(left.transform, "층", 12, Pal.Faint);
            UIKit.At(lab.rectTransform, 14, -10, 100, 18);
            var (_, fc) = UIKit.List(left.transform, "list", 4, 8);
            UIKit.Stretch((RectTransform)fc.parent.parent, 6, 34, 6, 8);
            _floorList = fc;

            var mid = UIKit.Panel(root, "mid", Pal.Panel, 12, Pal.Line);
            UIKit.Col(mid.rectTransform, 258, 708, 84, 16);
            var (_, mc) = UIKit.List(mid.transform, "list", 8, 14);
            UIKit.Stretch((RectTransform)mc.parent.parent, 4, 6, 4, 62);   // 아래 62 는 단추 띠
            _midBody = mc;
            _midBar = UIKit.Rect(mid.transform, "bar");
            _midBar.anchorMin = new Vector2(0, 0); _midBar.anchorMax = new Vector2(1, 0);
            _midBar.pivot = new Vector2(0.5f, 0);
            _midBar.offsetMin = new Vector2(12, 10); _midBar.offsetMax = new Vector2(-12, 56);
            var mbl = _midBar.gameObject.AddComponent<HorizontalLayoutGroup>();
            mbl.spacing = 8; mbl.childControlWidth = true; mbl.childForceExpandWidth = false;
            mbl.childAlignment = TextAnchor.MiddleLeft;

            var right = UIKit.Panel(root, "roster", Pal.Panel, 12, Pal.Line);
            UIKit.Col(right.rectTransform, 978, 286, 84, 16);
            _rosterCount = UIKit.Label(right.transform, "", 12, Pal.Faint);
            UIKit.At(_rosterCount.rectTransform, 14, -10, 260, 18);
            var filt = UIKit.Rect(right.transform, "filter");
            UIKit.At(filt, 8, -32, 270, 26);
            var hl = filt.gameObject.AddComponent<HorizontalLayoutGroup>();
            hl.spacing = 3; hl.childControlWidth = true; hl.childForceExpandWidth = true;
            foreach (var r in Roles)
            {
                string role = r;
                var b = UIKit.Btn(filt, role == "" ? "전체" : role, () =>
                        { _filter = role; RefreshRoster(); }, Pal.Sunk, Pal.Body, 12);
                b.name = "f:" + role;
            }
            var (_, rc) = UIKit.List(right.transform, "list", 4, 6);
            UIKit.Stretch((RectTransform)rc.parent.parent, 6, 64, 6, 8);
            _rosterList = rc;
        }

        static void Clear(RectTransform r)
        {
            for (int i = r.childCount - 1; i >= 0; i--) Destroy(r.GetChild(i).gameObject);
        }

        // ── 층 ──────────────────────────────────────────────────────
        void RefreshFloors()
        {
            Clear(_floorList);
            foreach (var f in T.floors)
            {
                bool on = f.n == Floor.n;
                var row = UIKit.Panel(_floorList, "f" + f.n, on ? Pal.Card : Pal.Panel, 8,
                                      on ? Pal.Slate : Pal.Panel);
                UIKit.Fit(row, 30);
                var b = row.gameObject.AddComponent<Button>();
                b.targetGraphic = row;
                var ff = f;
                b.onClick.AddListener(() => Select(ff));
                var n = UIKit.Label(row.transform, f.n.ToString("000"), 12,
                                    on ? Pal.Ember : Pal.Faint);
                UIKit.At(n.rectTransform, 10, -8, 34, 18);
                var nm = UIKit.Label(row.transform, f.name, 14, on ? Pal.Ink : Pal.Body);
                UIKit.At(nm.rectTransform, 48, -8, 120, 18);
                if (f.teams > 1)
                {
                    var tm = UIKit.Label(row.transform, f.teams + "팀", 11, Pal.Faint,
                                         TextAlignmentOptions.MidlineRight);
                    UIKit.At(tm.rectTransform, -12, -8, 40, 18, new Vector2(1, 1));
                }
            }
        }

        // ── 가운데 ───────────────────────────────────────────────────
        void RefreshMid()
        {
            Clear(_midBody);

            var title = UIKit.Rect(_midBody, "title"); UIKit.Fit(title, 34);
            var h = UIKit.Label(title, $"{Floor.n}층 · {Floor.name}", 22, Pal.Ink,
                                TextAlignmentOptions.MidlineLeft, true);
            UIKit.Stretch(h.rectTransform, 4, 0, 200, 0);
            var sub = UIKit.Label(title, $"{Floor.era} · {Floor.teams}팀 {Floor.need}명", 12, Pal.Faint,
                                  TextAlignmentOptions.MidlineRight);
            UIKit.Stretch(sub.rectTransform, 200, 0, 6, 0);

            var goal = UIKit.Panel(_midBody, "goal", Pal.Sunk, 8, Pal.Line);
            UIKit.Fit(goal, 30);
            var gl = UIKit.Label(goal.transform, "목표 · " + Floor.goalName, 14, Pal.Ember);
            UIKit.Stretch(gl.rectTransform, 12, 0, 12, 0);

            if (Floor.env is { Length: > 0 })
            {
                var e = UIKit.Label(_midBody, "환경 · " + string.Join("  ·  ", Floor.env), 12, Pal.Muted);
                UIKit.Fit(e, 18);
            }

            // 지도
            var mapBox = UIKit.Panel(_midBody, "map", Pal.Sunk, 8, Pal.Line);
            UIKit.Fit(mapBox, 120);
            BuildMap(mapBox.rectTransform);
            if (!string.IsNullOrEmpty(Floor.mapNote))
                UIKit.Fit(UIKit.Label(_midBody, Floor.mapNote, 12, Pal.Faint), 18);

            // 팀
            for (int ti = 0; ti < Teams.Count; ti++) BuildTeam(ti);

            // 길
            UIKit.Fit(UIKit.Label(_midBody, "경로 — 조건을 갖추면 요구 전투력이 내려간다", 12, Pal.Faint), 20);
            foreach (var rt in (Floor.routes ?? new RouteDef[0]).OrderBy(z => z.pw))
            {
                bool met = Teams.Any(t =>
                {
                    var c = Clean(t);
                    return c.Count > 0 && (rt.cond == null || rt.cond.Length == 0
                                           || rt.cond.All(cd => Setup.Meets(cd, c)));
                });
                var row = UIKit.Panel(_midBody, "r:" + rt.id,
                                      met ? Pal.Ok.A(0.14f) : Pal.Sunk, 8, met ? Pal.Ok : Pal.Line);
                UIKit.Fit(row, 28);
                var nm = UIKit.Label(row.transform,
                    RouteName.TryGetValue(rt.id, out var n) ? n : rt.id, 14, met ? Pal.Ink : Pal.Muted);
                UIKit.At(nm.rectTransform, 12, -5, 200, 18);
                var cd2 = UIKit.Label(row.transform,
                    rt.cond == null || rt.cond.Length == 0 ? "조건 없음"
                    : string.Join("  ·  ", rt.cond.Select(CondLabel)), 11, Pal.Faint);
                UIKit.At(cd2.rectTransform, 220, -5, 340, 18);
                var pw = UIKit.Label(row.transform, Mathf.RoundToInt(rt.pw * 100) + "%", 13,
                                     met ? Pal.Ok : Pal.Faint, TextAlignmentOptions.MidlineRight);
                UIKit.At(pw.rectTransform, -12, -5, 60, 18, new Vector2(1, 1));
            }

            // 단추 — 스크롤 밖. 언제나 보여야 한다.
            Clear(_midBar);
            var bar = _midBar;
            bool ready = Teams.All(t => Clean(t).Count > 0);
            var go = UIKit.Btn(bar, "등반", () =>
                     IremBoot.StartBattle(Floor, Teams.Select(Clean).ToList()),
                     ready ? Pal.Ember.A(0.9f) : Pal.Sunk, ready ? Pal.Ground : Pal.Faint, 17);
            go.interactable = ready;
            UIKit.Fit(go, 34); go.GetComponent<LayoutElement>().preferredWidth = 120;
            var au = UIKit.Btn(bar, "자동 편성", () => { Teams = Setup.AutoFill(T, Floor);
                     _picking = (-1, -1); RefreshMid(); RefreshRoster(); });
            UIKit.Fit(au, 34); au.GetComponent<LayoutElement>().preferredWidth = 110;
            var cl = UIKit.Btn(bar, "비우기", () => Select(Floor));
            UIKit.Fit(cl, 34); cl.GetComponent<LayoutElement>().preferredWidth = 90;
            if (!ready)
            {
                var w = UIKit.Label(bar, "각 팀에 최소 1명", 13, Pal.Bad);
                UIKit.Fit(w, 34); w.GetComponent<LayoutElement>().preferredWidth = 170;
            }
            else
            {
                int tot = Teams.Sum(t => Setup.TeamPower(Clean(t)));
                int req = Teams.Sum(t => Setup.Required(Floor, Clean(t)));
                var w = UIKit.Label(bar, $"전투력 {tot} / 요구 {req}", 13,
                                    tot >= req ? Pal.Ok : Pal.Bad);
                UIKit.Fit(w, 34); w.GetComponent<LayoutElement>().preferredWidth = 220;
            }
        }

        void BuildTeam(int ti)
        {
            var team = Clean(Teams[ti]);
            int pw = Setup.TeamPower(team), need = Setup.Required(Floor, team);
            bool ok = pw >= need;

            var head = UIKit.Rect(_midBody, "th" + ti); UIKit.Fit(head, 20);
            var l = UIKit.Label(head, (Teams.Count > 1 ? $"{ti + 1}팀" : "편성") + $"  {pw} / {need}",
                                13, Pal.Muted);
            UIKit.Stretch(l.rectTransform, 4, 0, 120, 0);
            var s = UIKit.Label(head, ok ? "충족" : "부족", 13, ok ? Pal.Ok : Pal.Bad,
                                TextAlignmentOptions.MidlineRight);
            UIKit.Stretch(s.rectTransform, 300, 0, 6, 0);

            var barBg = UIKit.Panel(_midBody, "tb" + ti, Pal.Sunk, 3);
            UIKit.Fit(barBg, 5);
            var fill = UIKit.Panel(barBg.transform, "fill", ok ? Pal.Ok : Pal.Bad, 3);
            var fr = fill.rectTransform;
            fr.anchorMin = Vector2.zero; fr.anchorMax = new Vector2(need > 0 ? Mathf.Clamp01((float)pw / need) : 0, 1);
            fr.offsetMin = Vector2.zero; fr.offsetMax = Vector2.zero;

            var slots = UIKit.Rect(_midBody, "ts" + ti); UIKit.Fit(slots, 92);
            var hl = slots.gameObject.AddComponent<HorizontalLayoutGroup>();
            hl.spacing = 8; hl.childControlWidth = true; hl.childForceExpandWidth = false;
            hl.childAlignment = TextAnchor.MiddleLeft; hl.padding = new RectOffset(4, 4, 4, 4);
            for (int si = 0; si < Floor.slot; si++)
            {
                var c = si < Teams[ti].Count ? Teams[ti][si] : null;
                bool sel = _picking.t == ti && _picking.s == si;
                var cell = UIKit.Panel(slots, $"s{ti}_{si}", c != null ? Pal.Card : Pal.Sunk, 8,
                                       sel ? Pal.Ember : Pal.Line);
                var le = cell.gameObject.AddComponent<LayoutElement>();
                le.preferredWidth = 64; le.preferredHeight = 84;
                int tt = ti, ss = si;
                var b = cell.gameObject.AddComponent<Button>();
                b.targetGraphic = cell;
                b.onClick.AddListener(() =>
                {
                    if (Teams[tt].Count > ss && Teams[tt][ss] != null) { Teams[tt][ss] = null; _picking = (-1, -1); }
                    else _picking = (tt, ss);
                    RefreshMid(); RefreshRoster();
                });
                if (c != null)
                {
                    var img = UIKit.Shade(cell.transform, c.id, T.nf);
                    UIKit.Stretch(img.rectTransform, 4, 3, 4, 20);
                    var nm = UIKit.Label(cell.transform, c.name, 11, Pal.Body,
                                         TextAlignmentOptions.Center);
                    UIKit.At(nm.rectTransform, 2, 2, 60, 16, new Vector2(0, 0));
                }
                else
                {
                    var plus = UIKit.Label(cell.transform, sel ? "고르세요" : "+", sel ? 11 : 22,
                                           sel ? Pal.Ember : Pal.Faint, TextAlignmentOptions.Center);
                    UIKit.Stretch(plus.rectTransform);
                }
            }
        }

        void BuildMap(RectTransform box)
        {
            if (Floor.map == null || Floor.map.Length == 0) return;
            int h = Floor.map.Length, w = Floor.map[0].Length;
            var grid = UIKit.Rect(box, "grid");
            UIKit.Stretch(grid, 6, 6, 6, 6);
            var g = grid.gameObject.AddComponent<GridLayoutGroup>();
            g.constraint = GridLayoutGroup.Constraint.FixedColumnCount;
            g.constraintCount = w;
            g.spacing = Vector2.zero;
            g.cellSize = new Vector2(688f / w, 108f / h);
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    char ch = x < Floor.map[y].Length ? Floor.map[y][x] : '.';
                    var cell = UIKit.Rect(grid, "c");
                    var im = cell.gameObject.AddComponent<Image>();
                    im.raycastTarget = false;
                    im.sprite = ArtLoad.Tile(ArtLoad.TileName('.', x, y, 5));
                    if (ch != '.')
                    {
                        var over = UIKit.Rect(cell, "o"); UIKit.Stretch(over);
                        var oi = over.gameObject.AddComponent<Image>();
                        oi.raycastTarget = false;
                        oi.sprite = ArtLoad.Tile(ArtLoad.TileName(ch, x, y, 5));
                    }
                }
        }

        static string CondLabel(CondDef c) =>
            c.t == "약체" ? "평균 선명도 3 이하"
          : c.t == "층범위" ? c.v + "층 출신"
          : c.t + " " + c.v + (c.n > 1 ? " ×" + c.n : "");

        // ── 잔상 ─────────────────────────────────────────────────────
        void RefreshRoster()
        {
            Clear(_rosterList);
            _rosterCount.text = $"보유 잔상 {T.chars.Length}명 · 전승 {T.chars.Count(c => !c.gen)} · 무명 {T.chars.Count(c => c.gen)}";
            foreach (var c in T.chars.Where(x => _filter == "" || x.role == _filter)
                                     .OrderByDescending(x => x.pw))
            {
                bool used = Used(c);
                var row = UIKit.Panel(_rosterList, c.id, used ? Pal.Sunk.A(0.7f) : Pal.Card, 8, Pal.Line);
                UIKit.Fit(row, 52);
                if (!used)
                {
                    var b = row.gameObject.AddComponent<Button>();
                    b.targetGraphic = row;
                    var cc = c;
                    b.onClick.AddListener(() => Put(cc));
                }
                var img = UIKit.Shade(row.transform, c.id, T.nf);
                UIKit.At(img.rectTransform, 6, -3, 34, 46);
                if (used) img.color = new Color(1, 1, 1, 0.35f);
                var col = used ? Pal.Faint : Pal.Ink;
                var nm = UIKit.Label(row.transform, c.name, 13, col);
                UIKit.At(nm.rectTransform, 46, -4, 175, 17);
                var sub = UIKit.Label(row.transform,
                    new string('★', Mathf.Clamp(c.r, 0, 7)) + $"  {c.role} · {c.trade}", 10, Pal.Faint);
                UIKit.At(sub.rectTransform, 46, -20, 175, 14);
                if (!string.IsNullOrEmpty(c.traitName))
                {
                    var tr = UIKit.Label(row.transform, "「" + c.traitName + "」", 10,
                                         used ? Pal.Faint : Pal.Ember, TextAlignmentOptions.MidlineLeft, true);
                    UIKit.At(tr.rectTransform, 46, -33, 175, 14);
                }
                var pw = UIKit.Label(row.transform, c.pw.ToString(), 13,
                                     used ? Pal.Faint : Pal.Slate, TextAlignmentOptions.MidlineRight);
                UIKit.At(pw.rectTransform, -10, -18, 50, 18, new Vector2(1, 1));
            }
        }
    }
}
