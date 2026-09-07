// 편성 화면 — 어느 층에, 누구를 보낼 것인가.
//
//   층을 고르고, 슬롯을 누르고, 잔상을 고른다.
//   조건을 갖추면 길이 열리고 요구 전투력이 내려간다.
//   시험판(HTML)과 같은 규칙이다. 판정은 Irem.Sim/Setup.cs 하나만 쓴다.
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using Irem.Data;
using Irem.Sim;

namespace Irem.Game
{
    public sealed class RosterScreen : MonoBehaviour
    {
        public BattleTables T;
        public FloorDef Floor;
        public List<List<CharDef>> Teams = new();

        Vector2 _flScroll, _roScroll;
        (int t, int s) _picking = (-1, -1);
        string _filter = "";          // 역할로 거른다
        Camera _cam;

        static readonly Dictionary<string, string> RouteName = new()
        {
            ["force"] = "돌파", ["guard"] = "수호의 길", ["seek"] = "탐구의 길",
            ["devote"] = "헌신의 길", ["resist"] = "저항의 길", ["flee"] = "도피의 길",
            ["trade"] = "생업의 길", ["era"] = "그 자리에 있던 사람", ["weak"] = "이름 없는 길",
            ["wall"] = "담의 약점", ["drain"] = "배수로", ["unseen"] = "묘수",
        };
        static readonly string[] Roles = { "", "수호", "저항", "헌신", "탐구", "도피" };

        public void Begin(BattleTables t, FloorDef f, Camera cam)
        {
            T = t; _cam = cam;
            if (_cam != null)
            {
                _cam.orthographic = true;
                _cam.clearFlags = CameraClearFlags.SolidColor;
                _cam.backgroundColor = new Color32(0x12, 0x15, 0x18, 255);
            }
            Pick(f ?? T.floors[0]);
        }

        void Pick(FloorDef f)
        {
            Floor = f;
            Teams = new List<List<CharDef>>();
            for (int i = 0; i < Mathf.Max(1, f.teams); i++) Teams.Add(new List<CharDef>());
            _picking = (-1, -1);
        }

        bool Used(CharDef c) => Teams.Any(t => t.Contains(c));

        void Put(CharDef c)
        {
            if (Used(c)) return;
            int ti = _picking.t, si = _picking.s;
            if (ti < 0)
            {
                for (int i = 0; i < Teams.Count && ti < 0; i++)
                    if (Teams[i].Count < Floor.slot) { ti = i; si = Teams[i].Count; }
            }
            if (ti < 0) return;
            while (Teams[ti].Count <= si) Teams[ti].Add(null);
            Teams[ti][si] = c;
            _picking = (-1, -1);
        }

        List<CharDef> Clean(List<CharDef> t) => t.Where(x => x != null).ToList();

        // ── 그리기 ────────────────────────────────────────────────────
        void OnGUI()
        {
            if (T == null) return;
            float W = Screen.width, H = Screen.height;
            IremUI.Fill(new Rect(0, 0, W, H), new Color(0.071f, 0.082f, 0.094f));

            // 머리말
            IremUI.Text(new Rect(20, 14, W - 40, 22), "이렘의 탑 · 잔상 편성", 18, IremUI.Ink,
                        TextAnchor.MiddleLeft, FontStyle.Bold);
            IremUI.Text(new Rect(20, 36, W - 40, 18),
                "전투력이 요구치의 80%를 밑돌면 거의 못 이기고, 넘어서면 대체로 이깁니다. 그 사이가 승부입니다.",
                12, IremUI.Muted);

            float top = 62, pad = 12;
            float colFl = Mathf.Min(190, W * 0.20f);
            float colRo = Mathf.Min(330, W * 0.30f);
            float colMi = W - colFl - colRo - pad * 4;

            Floors(new Rect(pad, top, colFl, H - top - pad));
            Middle(new Rect(pad * 2 + colFl, top, colMi, H - top - pad));
            Roster(new Rect(pad * 3 + colFl + colMi, top, colRo, H - top - pad));
        }

        void Floors(Rect r)
        {
            IremUI.Box(r, IremUI.Panel, IremUI.Line);
            IremUI.Text(new Rect(r.x + 10, r.y + 6, r.width - 20, 16), "층", 11, IremUI.Faint);
            var view = new Rect(r.x + 6, r.y + 26, r.width - 12, r.height - 32);
            float rowH = 30, inner = T.floors.Length * rowH;
            _flScroll = GUI.BeginScrollView(view, _flScroll, new Rect(0, 0, view.width - 16, inner));
            for (int i = 0; i < T.floors.Length; i++)
            {
                var f = T.floors[i];
                var row = new Rect(0, i * rowH, view.width - 16, rowH - 3);
                bool on = f.n == Floor.n;
                if (on) IremUI.Box(row, new Color(0.13f, 0.16f, 0.19f), IremUI.Slate);
                IremUI.Text(new Rect(row.x + 8, row.y, 34, row.height),
                            f.n.ToString("000"), 11, on ? IremUI.Ember : IremUI.Faint);
                IremUI.Text(new Rect(row.x + 44, row.y, row.width - 80, row.height),
                            f.name, 13, on ? IremUI.Ink : IremUI.Body);
                if (f.teams > 1)
                    IremUI.Text(new Rect(row.xMax - 40, row.y, 34, row.height),
                                f.teams + "팀", 10, IremUI.Faint, TextAnchor.MiddleRight);
                if (IremUI.Hit(row)) Pick(f);
            }
            GUI.EndScrollView();
        }

        void Middle(Rect r)
        {
            IremUI.Box(r, IremUI.Panel, IremUI.Line);
            float x = r.x + 14, w = r.width - 28, y = r.y + 12;

            IremUI.Text(new Rect(x, y, w, 22), $"{Floor.n}층 · {Floor.name}", 17, IremUI.Ink,
                        TextAnchor.MiddleLeft, FontStyle.Bold);
            IremUI.Text(new Rect(x, y, w, 22), $"{Floor.era} · {Floor.teams}팀 {Floor.need}명",
                        11, IremUI.Faint, TextAnchor.MiddleRight);
            y += 26;

            IremUI.Box(new Rect(x, y, w, 22), IremUI.Sunk, IremUI.Line);
            IremUI.Text(new Rect(x + 8, y, w - 16, 22), Floor.goalName, 12, IremUI.Ember);
            y += 28;

            if (Floor.env != null && Floor.env.Length > 0)
            {
                IremUI.Text(new Rect(x, y, w, 16), "환경 · " + string.Join(" · ", Floor.env),
                            11, IremUI.Muted);
                y += 20;
            }

            // 지도
            float mh = Mathf.Min(96, r.height * 0.18f);
            var mr = new Rect(x, y, w, mh);
            IremUI.Box(mr, IremUI.Sunk, IremUI.Line);
            IremUI.MiniMap(new Rect(mr.x + 1, mr.y + 1, mr.width - 2, mr.height - 2), Floor);
            y += mh + 6;
            IremUI.Text(new Rect(x, y, w, 16), Floor.mapNote ?? "", 11, IremUI.Faint);
            y += 22;

            // 팀
            for (int ti = 0; ti < Teams.Count; ti++)
            {
                var team = Clean(Teams[ti]);
                int pw = Setup.TeamPower(team), need = Setup.Required(Floor, team);
                bool ok = pw >= need;
                IremUI.Text(new Rect(x, y, w * 0.5f, 16),
                            (Teams.Count > 1 ? $"{ti + 1}팀" : "편성") + $" · {pw} / {need}",
                            11, IremUI.Muted);
                IremUI.Text(new Rect(x + w * 0.5f, y, w * 0.5f, 16), ok ? "충족" : "부족",
                            11, ok ? IremUI.Ok : IremUI.Bad, TextAnchor.MiddleRight);
                y += 18;
                IremUI.Bar(new Rect(x, y, w, 3), need > 0 ? (float)pw / need : 0,
                           ok ? IremUI.Ok : IremUI.Bad);
                y += 8;

                float sw = 52, sh = 68;
                for (int si = 0; si < Floor.slot; si++)
                {
                    var sr = new Rect(x + si * (sw + 6), y, sw, sh);
                    var c = si < Teams[ti].Count ? Teams[ti][si] : null;
                    bool sel = _picking.t == ti && _picking.s == si;
                    IremUI.Box(sr, c != null ? new Color(0.11f, 0.13f, 0.15f) : IremUI.Sunk,
                               sel ? IremUI.Ember : IremUI.Line);
                    if (c != null)
                    {
                        IremUI.Shade(new Rect(sr.x + 4, sr.y + 2, sr.width - 8, sr.height - 18), c.id, T.nf);
                        IremUI.Text(new Rect(sr.x + 2, sr.yMax - 16, sr.width - 4, 14),
                                    c.name, 10, IremUI.Body, TextAnchor.MiddleCenter);
                    }
                    if (IremUI.Hit(sr))
                    {
                        if (c != null) { Teams[ti][si] = null; _picking = (-1, -1); }
                        else _picking = (ti, si);
                    }
                }
                y += sh + 12;
            }

            // 길
            IremUI.Text(new Rect(x, y, w, 16), "경로 — 조건을 갖추면 요구 전투력이 내려간다",
                        11, IremUI.Faint);
            y += 20;
            foreach (var rt in (Floor.routes ?? new RouteDef[0]).OrderBy(z => z.pw))
            {
                bool met = Teams.Any(t => { var c = Clean(t);
                    return c.Count > 0 && (rt.cond == null || rt.cond.Length == 0
                                           || rt.cond.All(cd => Setup.Meets(cd, c))); });
                var rr = new Rect(x, y, w, 22);
                IremUI.Box(rr, met ? new Color(0.09f, 0.15f, 0.12f) : IremUI.Sunk,
                           met ? IremUI.Ok : IremUI.Line);
                string nm = RouteName.TryGetValue(rt.id, out var n) ? n : rt.id;
                string cd2 = rt.cond == null || rt.cond.Length == 0 ? "조건 없음"
                    : string.Join(" · ", rt.cond.Select(CondLabel));
                IremUI.Text(new Rect(rr.x + 8, rr.y, rr.width * 0.4f, 22), nm, 12,
                            met ? IremUI.Ink : IremUI.Muted);
                IremUI.Text(new Rect(rr.x + rr.width * 0.4f, rr.y, rr.width * 0.4f, 22), cd2, 10, IremUI.Faint);
                IremUI.Text(new Rect(rr.xMax - 56, rr.y, 48, 22),
                            Mathf.RoundToInt(rt.pw * 100) + "%", 11,
                            met ? IremUI.Ok : IremUI.Faint, TextAnchor.MiddleRight);
                y += 25;
            }

            // 단추
            y = r.yMax - 44;
            bool ready = Teams.All(t => Clean(t).Count > 0);
            if (IremUI.Btn(new Rect(x, y, 90, 30), "등반", true, ready) && ready)
                IremBoot.StartBattle(Floor, Teams.Select(Clean).ToList());
            if (IremUI.Btn(new Rect(x + 98, y, 90, 30), "자동 편성"))
            {
                var a = Setup.AutoFill(T, Floor);
                Teams = a; _picking = (-1, -1);
            }
            if (IremUI.Btn(new Rect(x + 196, y, 70, 30), "비우기")) Pick(Floor);
            if (!ready)
                IremUI.Text(new Rect(x + 276, y, 200, 30), "각 팀에 최소 1명", 11, IremUI.Bad);
        }

        static string CondLabel(CondDef c)
        {
            if (c.t == "약체") return "평균 선명도 3 이하";
            if (c.t == "층범위") return c.v + "층 출신";
            return c.t + " " + c.v + (c.n > 1 ? " ×" + c.n : "");
        }

        void Roster(Rect r)
        {
            IremUI.Box(r, IremUI.Panel, IremUI.Line);
            var pool = T.chars.Where(c => _filter == "" || c.role == _filter)
                              .OrderByDescending(c => c.pw).ToList();
            IremUI.Text(new Rect(r.x + 10, r.y + 6, r.width - 20, 16),
                        $"보유 잔상 {T.chars.Length}명 · 전승 {T.chars.Count(c => !c.gen)} · 무명 {T.chars.Count(c => c.gen)}",
                        11, IremUI.Faint);

            float fy = r.y + 26;
            for (int i = 0; i < Roles.Length; i++)
            {
                var br = new Rect(r.x + 8 + i * ((r.width - 16) / Roles.Length),
                                  fy, (r.width - 16) / Roles.Length - 3, 22);
                if (IremUI.Btn(br, Roles[i] == "" ? "전체" : Roles[i], _filter == Roles[i]))
                    _filter = Roles[i];
            }

            var view = new Rect(r.x + 6, fy + 28, r.width - 12, r.height - (fy + 28 - r.y) - 8);
            float rowH = 46, inner = pool.Count * rowH;
            _roScroll = GUI.BeginScrollView(view, _roScroll, new Rect(0, 0, view.width - 16, inner));
            for (int i = 0; i < pool.Count; i++)
            {
                var c = pool[i];
                var row = new Rect(0, i * rowH, view.width - 16, rowH - 3);
                if (row.yMax < _roScroll.y - 40 || row.y > _roScroll.y + view.height + 40) continue;
                bool used = Used(c);
                IremUI.Box(row, used ? new Color(0.08f, 0.09f, 0.10f, 0.6f) : new Color(0.10f, 0.12f, 0.14f),
                           IremUI.Line);
                IremUI.Shade(new Rect(row.x + 4, row.y + 1, 30, 41), c.id, T.nf);
                var col = used ? IremUI.Faint : IremUI.Ink;
                IremUI.Text(new Rect(row.x + 38, row.y + 3, row.width - 90, 16), c.name, 12, col,
                            TextAnchor.MiddleLeft, c.gen ? FontStyle.Normal : FontStyle.Bold);
                IremUI.Text(new Rect(row.x + 38, row.y + 18, row.width - 90, 14),
                            new string('★', c.r) + $"  {c.role} · {c.trade}", 10, IremUI.Faint);
                IremUI.Text(new Rect(row.x + 38, row.y + 30, row.width - 90, 14),
                            string.IsNullOrEmpty(c.traitName) ? "" : "「" + c.traitName + "」",
                            10, used ? IremUI.Faint : IremUI.Ember);
                IremUI.Text(new Rect(row.xMax - 48, row.y, 42, row.height),
                            c.pw.ToString(), 12, used ? IremUI.Faint : IremUI.Slate, TextAnchor.MiddleRight);
                if (!used && IremUI.Hit(row)) Put(c);
            }
            GUI.EndScrollView();
        }
    }
}
