// 뜰 화면의 글자와 판. 세계(땅·소품·몸)는 GardenDirector 가 3D 로 그리고, 그 위에 이것을 얹는다.
// BattleHud 와 같은 방식이다 — uGUI 를 코드로 짓고, 이름표는 매 프레임 월드 자리를 화면으로 옮긴다.
//
// 전투 HUD 와 다른 것은 셋이다.
//   · 체력 막대가 없다. 뜰에서는 아무도 다치지 않는다(docs/03-뜰.md).
//   · 대신 인연 목록이 있다. 성립한 것과 켜진 것을 구분해 보여 준다 — 그것이 뜰의 재미다.
//   · 이름표를 누르면 그 사람을 따라간다. 스물셋이 동시에 움직이므로 하나를 골라 볼 수 있어야 한다.
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using Irem.Data;
using Irem.Sim;

namespace Irem.Game
{
    public sealed class GardenHud : MonoBehaviour
    {
        public Camera Cam;
        public GardenTables T;
        public Garden G;
        public GardenDirector Dir;

        RectTransform _root, _tags;
        TextMeshProUGUI _title, _note, _count, _ticker;
        Button _pause, _speed, _bondBtn, _release;
        RectTransform _bondPanel, _bondList;
        bool _bondOpen;

        readonly Dictionary<int, Tag> _tag = new();
        readonly List<(Vector3 at, RectTransform rt)> _marks = new();
        readonly List<string> _lines = new();

        sealed class Tag
        {
            public RectTransform rt;
            public TextMeshProUGUI nm;
            public RectTransform bub;
            public TextMeshProUGUI bubT;
            public float until;
        }

        public void Build(Camera cam, GardenTables t, Garden g, GardenDirector dir)
        {
            Cam = cam; T = t; G = g; Dir = dir;
            var canvas = UIKit.Root(transform, "뜰 UI", 10);
            _root = (RectTransform)canvas.transform;

            var vig = UIKit.Rect(_root, "vignette"); UIKit.Stretch(vig);
            var vi = vig.gameObject.AddComponent<Image>();
            vi.sprite = Shapes.Vignette(); vi.color = Color.white; vi.raycastTarget = false;

            _tags = UIKit.Rect(_root, "tags"); UIKit.Stretch(_tags);

            // ── 위 띠 ──
            var top = UIKit.Panel(_root, "top", Pal.Ground.A(0.82f), 0);
            top.rectTransform.anchorMin = new Vector2(0, 1);
            top.rectTransform.anchorMax = new Vector2(1, 1);
            top.rectTransform.pivot = new Vector2(0.5f, 1);
            top.rectTransform.offsetMin = new Vector2(0, -52);
            top.rectTransform.offsetMax = Vector2.zero;
            top.sprite = null;
            _title = UIKit.Label(top.transform, "0층 · 뜰", 19, Pal.Ink,
                                 TextAlignmentOptions.MidlineLeft, true);
            UIKit.At(_title.rectTransform, 20, -8, 240, 34);
            _note = UIKit.Label(top.transform, "여기서는 시간이 흐르지 않는다", 14, Pal.Ember,
                                TextAlignmentOptions.Center);
            UIKit.Stretch(_note.rectTransform, 300, 0, 300, 0);
            _count = UIKit.Label(top.transform, "", 13, Pal.Muted, TextAlignmentOptions.MidlineRight);
            UIKit.At(_count.rectTransform, -20, -8, 320, 34, new Vector2(1, 1));

            // ── 기록 ──
            var log = UIKit.Panel(_root, "log", Pal.Sunk.A(0.72f), 10, Pal.Line.A(0.5f));
            UIKit.At(log.rectTransform, 16, 16, 430, 96, new Vector2(0, 0));
            _ticker = UIKit.Label(log.transform, "", 13, Pal.Body, TextAlignmentOptions.BottomLeft);
            UIKit.Stretch(_ticker.rectTransform, 12, 8, 12, 8);
            _ticker.enableWordWrapping = true;
            _ticker.overflowMode = TextOverflowModes.Truncate;

            // ── 단추 ──
            var bar = UIKit.Rect(_root, "ctl");
            UIKit.At(bar, -16, 16, 430, 36, new Vector2(1, 0));
            var hl = bar.gameObject.AddComponent<HorizontalLayoutGroup>();
            hl.spacing = 8; hl.childAlignment = TextAnchor.MiddleRight;
            hl.childControlWidth = true; hl.childForceExpandWidth = false;
            _pause = UIKit.Btn(bar, "멈춤", () => { Dir.TogglePause(); RefreshCtl(); });
            UIKit.Fit(_pause, 34); _pause.GetComponent<LayoutElement>().preferredWidth = 78;
            _speed = UIKit.Btn(bar, "속도 ×1", () => { Dir.CycleSpeed(); RefreshCtl(); });
            UIKit.Fit(_speed, 34); _speed.GetComponent<LayoutElement>().preferredWidth = 92;
            _release = UIKit.Btn(bar, "놓기", () => { if (Dir.Following >= 0) Dir.Follow(Dir.Following); });
            UIKit.Fit(_release, 34); _release.GetComponent<LayoutElement>().preferredWidth = 70;
            _bondBtn = UIKit.Btn(bar, "인연", () => { _bondOpen = !_bondOpen; ShowBonds(); },
                                 Pal.Ember.A(0.85f), Pal.Ground);
            UIKit.Fit(_bondBtn, 34); _bondBtn.GetComponent<LayoutElement>().preferredWidth = 78;

            BuildBondPanel();
            foreach (var s in T.stations ?? new StationDef[0]) MakeMark(s);
            foreach (var s in G.Cast) MakeTag(s);
            RefreshCtl();
        }

        void RefreshCtl()
        {
            _pause.GetComponentInChildren<TextMeshProUGUI>().text = Dir.Paused ? "이어서" : "멈춤";
            _speed.GetComponentInChildren<TextMeshProUGUI>().text = "속도 ×" + Dir.SpeedLabel;
        }

        // ── 일터 이름표 ──
        void MakeMark(StationDef s)
        {
            var rt = UIKit.Rect(_tags, "일터:" + s.name);
            rt.sizeDelta = new Vector2(150, 30);
            rt.anchorMin = rt.anchorMax = Vector2.zero;
            rt.pivot = new Vector2(0.5f, 0);
            var nm = UIKit.Label(rt, s.name, 12, Pal.Faint, TextAlignmentOptions.Center, true);
            UIKit.Stretch(nm.rectTransform);
            nm.outlineWidth = 0.2f; nm.outlineColor = new Color32(0, 0, 0, 220);
            // 이름표는 그 채의 꼭대기 위에 뜬다. 칸 한가운데에 두면 8m 짜리 종탑이
            // 제 이름표를 가린다.
            _marks.Add((Dir.MarkAt(s), rt));
        }

        // ── 잔상 이름표 ──
        void MakeTag(GardenShade s)
        {
            int idx = s.Idx;
            var rt = UIKit.Rect(_tags, "tag:" + s.Name);
            rt.sizeDelta = new Vector2(140, 40);
            rt.anchorMin = rt.anchorMax = Vector2.zero;
            rt.pivot = new Vector2(0.5f, 0);

            // 이름 자체가 단추다. 누르면 따라간다.
            var hit = UIKit.Panel(rt, "hit", new Color(0, 0, 0, 0.001f), 4);
            UIKit.At(hit.rectTransform, 0, 0, 132, 18, new Vector2(0.5f, 0));
            var b = hit.gameObject.AddComponent<Button>();
            b.targetGraphic = hit;
            b.onClick.AddListener(() => Dir.Follow(idx));

            var nm = UIKit.Label(hit.transform, s.Name, 11, Pal.Body, TextAlignmentOptions.Center);
            UIKit.Stretch(nm.rectTransform);
            nm.outlineWidth = 0.22f; nm.outlineColor = new Color32(0, 0, 0, 220);

            var bub = UIKit.Panel(rt, "bub", Pal.Sunk.A(0.95f), 6, Pal.Ember.A(0.55f));
            UIKit.At(bub.rectTransform, 0, 22, 176, 20, new Vector2(0.5f, 0));
            var bubT = UIKit.Label(bub.transform, "", 11, Pal.Ink, TextAlignmentOptions.Center, true);
            UIKit.Stretch(bubT.rectTransform, 6, 0, 6, 0);
            bub.gameObject.SetActive(false);

            _tag[idx] = new Tag { rt = rt, nm = nm, bub = bub.rectTransform, bubT = bubT };
        }

        public void Say(string s)
        {
            if (string.IsNullOrEmpty(s)) return;
            _lines.Add(s);
            while (_lines.Count > 5) _lines.RemoveAt(0);
            _ticker.text = string.Join("\n", _lines);
        }

        /// 말풍선. 한 걸음에 스물셋이 동시에 말할 수 있으므로 코루틴을 쓰지 않는다 —
        /// 언제까지 띄울지만 적어 두고 LateUpdate 가 지운다.
        public void Bubble(int idx, string text, float seconds = 2.2f)
        {
            if (string.IsNullOrEmpty(text)) return;
            if (!_tag.TryGetValue(idx, out var t)) return;
            t.bubT.text = text;
            t.bub.gameObject.SetActive(true);
            t.until = Time.time + seconds;
        }

        // ── 인연 판 ──
        void BuildBondPanel()
        {
            var p = UIKit.Panel(_root, "bonds", Pal.Panel.A(0.94f), 12, Pal.Line);
            UIKit.At(p.rectTransform, -16, -62, 330, 330, new Vector2(1, 1));
            _bondPanel = p.rectTransform;
            var head = UIKit.Label(p.transform, "인연", 16, Pal.Ink, TextAlignmentOptions.MidlineLeft, true);
            UIKit.At(head.rectTransform, 14, -10, 200, 24);
            var (sr, content) = UIKit.List(p.transform, "list", 3, 6);
            UIKit.Stretch(sr.GetComponent<RectTransform>(), 8, 38, 8, 8);
            _bondList = content;
            _bondPanel.gameObject.SetActive(false);
        }

        /// 성립 목록을 다시 적는다. 배치가 바뀌면 목록 자체가 달라지므로
        /// 구역을 다시 잴 때마다(Gv.Bond 요약) 여기가 다시 그려진다.
        public void ShowBonds()
        {
            if (_bondPanel == null) return;
            _bondPanel.gameObject.SetActive(_bondOpen);
            if (!_bondOpen) return;

            for (int i = _bondList.childCount - 1; i >= 0; i--)
                Destroy(_bondList.GetChild(i).gameObject);

            if (G.Found.Count == 0)
            {
                var none = UIKit.Label(_bondList, "성립한 인연이 없다", 12, Pal.Muted);
                UIKit.Fit(none, 20);
                return;
            }
            foreach (var b in G.Found)
            {
                var row = UIKit.Panel(_bondList, "b:" + b.Title,
                                      b.Active ? Pal.Card : Pal.Sunk.A(0.8f), 6,
                                      b.Active ? Pal.Ember.A(0.6f) : Pal.Line.A(0.5f));
                UIKit.Fit(row, 40);
                var nm = UIKit.Label(row.transform, b.Title, 13,
                                     b.Active ? Pal.Ink : Pal.Muted, TextAlignmentOptions.MidlineLeft, true);
                UIKit.At(nm.rectTransform, 10, -4, 210, 20);
                var kind = UIKit.Label(row.transform, $"{b.R.kind} · {(b.Active ? "발동" : "대기")}", 11,
                                       b.Active ? Pal.Ember : Pal.Faint, TextAlignmentOptions.MidlineRight);
                UIKit.At(kind.rectTransform, -10, -4, 90, 20, new Vector2(1, 1));
                var sub = UIKit.Label(row.transform, b.R.reward ?? "", 11, Pal.Faint,
                                      TextAlignmentOptions.MidlineLeft);
                UIKit.At(sub.rectTransform, 10, -22, 300, 16);
            }
        }

        // ── 매 프레임 ──
        void LateUpdate()
        {
            if (G == null || Cam == null || Dir == null) return;

            _count.text = $"걸음 {Dir.ShownTurn} · 일한 걸음 {Dir.WorkSteps} · 말을 건 인연 {Dir.Spoken}";
            _release.interactable = Dir.Following >= 0;

            foreach (var (at, rt) in _marks) Place(rt, at + Vector3.up * 0.08f, -6);

            float now = Time.time;
            foreach (var s in G.Cast)
            {
                if (!_tag.TryGetValue(s.Idx, out var t)) continue;
                var v = Dir.ViewOf(s.Idx);
                if (v == null) { t.rt.gameObject.SetActive(false); continue; }
                bool vis = Place(t.rt, v.Pos + Vector3.up * 1.78f, 0);
                if (!vis) continue;
                if (t.until > 0 && now > t.until)
                {
                    t.until = 0;
                    t.bub.gameObject.SetActive(false);
                }
                bool on = Dir.Following == s.Idx;
                t.nm.color = on ? Pal.Ember : Pal.Body;
                t.nm.alpha = 1f;
            }
        }

        /// 월드 자리를 화면으로 옮긴다. 카메라 뒤로 가면 감춘다 —
        /// 원근 카메라라 z 를 안 보면 뒤에 있는 것이 화면 위에 거꾸로 나타난다.
        bool Place(RectTransform rt, Vector3 world, float dy)
        {
            var sp = Cam.WorldToScreenPoint(world);
            bool vis = sp.z > 0.2f;
            if (rt.gameObject.activeSelf != vis) rt.gameObject.SetActive(vis);
            if (vis) rt.position = new Vector3(sp.x, sp.y + dy, 0);
            return vis;
        }
    }
}
