// 전투 화면의 글자와 판. 세계(지형·잔상)는 스프라이트로 그리고, 그 위에 이것을 얹는다.
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using Irem.Data;
using Irem.Sim;

namespace Irem.Game
{
    public sealed class BattleHud : MonoBehaviour
    {
        public Camera Cam;
        public Battle B;
        public FloorDef Floor;
        public BattleDirector Dir;

        RectTransform _root, _tags, _float;
        TextMeshProUGUI _title, _goal, _turn, _ticker;
        Image _resultCard; TextMeshProUGUI _resultTop, _resultSub;
        Button _pause, _speed;
        readonly Dictionary<int, (RectTransform rt, TextMeshProUGUI nm, RectTransform bar, Image fill,
                                  RectTransform bub, TextMeshProUGUI bubT)> _tag = new();
        readonly List<string> _lines = new();

        public void Build(Camera cam, Battle b, FloorDef f, BattleDirector dir)
        {
            Cam = cam; B = b; Floor = f; Dir = dir;
            var canvas = UIKit.Root(transform, "전투 UI", 10);
            _root = (RectTransform)canvas.transform;

            // 가장자리를 눌러 준다
            var vig = UIKit.Rect(_root, "vignette"); UIKit.Stretch(vig);
            var vi = vig.gameObject.AddComponent<Image>();
            vi.sprite = Shapes.Vignette(); vi.color = Color.white; vi.raycastTarget = false;

            _tags  = UIKit.Rect(_root, "tags");  UIKit.Stretch(_tags);
            _float = UIKit.Rect(_root, "float"); UIKit.Stretch(_float);

            // 위 띠
            var top = UIKit.Panel(_root, "top", Pal.Ground.A(0.82f), 0);
            top.rectTransform.anchorMin = new Vector2(0, 1);
            top.rectTransform.anchorMax = new Vector2(1, 1);
            top.rectTransform.pivot = new Vector2(0.5f, 1);
            top.rectTransform.offsetMin = new Vector2(0, -52);
            top.rectTransform.offsetMax = Vector2.zero;
            top.sprite = null;
            _title = UIKit.Label(top.transform, $"{f.n}층 · {f.name}", 19, Pal.Ink,
                                 TextAlignmentOptions.MidlineLeft, true);
            UIKit.At(_title.rectTransform, 20, -8, 300, 34);
            _goal = UIKit.Label(top.transform, b.Goal.Name, 14, Pal.Ember, TextAlignmentOptions.Center);
            UIKit.Stretch(_goal.rectTransform, 320, 0, 320, 0);
            _turn = UIKit.Label(top.transform, "", 14, Pal.Muted, TextAlignmentOptions.MidlineRight);
            UIKit.At(_turn.rectTransform, -20, -8, 200, 34, new Vector2(1, 1));

            // 기록
            var log = UIKit.Panel(_root, "log", Pal.Sunk.A(0.72f), 10, Pal.Line.A(0.5f));
            UIKit.At(log.rectTransform, 16, 16, 400, 96, new Vector2(0, 0));
            _ticker = UIKit.Label(log.transform, "", 13, Pal.Body, TextAlignmentOptions.BottomLeft);
            UIKit.Stretch(_ticker.rectTransform, 12, 8, 12, 8);
            _ticker.enableWordWrapping = true;
            _ticker.overflowMode = TextOverflowModes.Truncate;

            // 단추
            var bar = UIKit.Rect(_root, "ctl");
            UIKit.At(bar, -16, 16, 430, 36, new Vector2(1, 0));
            var hl = bar.gameObject.AddComponent<HorizontalLayoutGroup>();
            hl.spacing = 8; hl.childAlignment = TextAnchor.MiddleRight;
            hl.childControlWidth = true; hl.childForceExpandWidth = false;
            _pause = UIKit.Btn(bar, "멈춤", () => { Dir.TogglePause(); RefreshCtl(); });
            UIKit.Fit(_pause, 34); _pause.GetComponent<LayoutElement>().preferredWidth = 78;
            _speed = UIKit.Btn(bar, "속도 ×1", () => { Dir.CycleSpeed(); RefreshCtl(); });
            UIKit.Fit(_speed, 34); _speed.GetComponent<LayoutElement>().preferredWidth = 92;
            var again = UIKit.Btn(bar, "다시", () => IremBoot.Restart());
            UIKit.Fit(again, 34); again.GetComponent<LayoutElement>().preferredWidth = 72;
            var back = UIKit.Btn(bar, "편성 바꾸기", () => IremBoot.ShowRoster(Floor),
                                 Pal.Ember.A(0.85f), Pal.Ground);
            UIKit.Fit(back, 34); back.GetComponent<LayoutElement>().preferredWidth = 118;

            foreach (var u in B.Units) MakeTag(u);
            RefreshCtl();
        }

        void RefreshCtl()
        {
            _pause.GetComponentInChildren<TextMeshProUGUI>().text = Dir.Paused ? "이어서" : "멈춤";
            _speed.GetComponentInChildren<TextMeshProUGUI>().text = "속도 ×" + Dir.SpeedLabel;
        }

        void MakeTag(Unit u)
        {
            var rt = UIKit.Rect(_tags, "tag:" + u.Name);
            rt.sizeDelta = new Vector2(120, 40);
            rt.anchorMin = rt.anchorMax = new Vector2(0, 0);
            rt.pivot = new Vector2(0.5f, 1);

            var barBg = UIKit.Panel(rt, "hp", Pal.Sunk.A(0.9f), 2);
            UIKit.At(barBg.rectTransform, 0, 0, 34, 4, new Vector2(0.5f, 1));
            var fill = UIKit.Panel(barBg.transform, "f", u.Foe ? Pal.Bad : Pal.Slate, 2);
            UIKit.Stretch(fill.rectTransform);

            var nm = UIKit.Label(rt, u.Short ?? u.Name, 11,
                                 u.Foe ? Pal.Bad : Pal.Body, TextAlignmentOptions.Top);
            UIKit.At(nm.rectTransform, 0, -5, 116, 15, new Vector2(0.5f, 1));
            nm.outlineWidth = 0.22f; nm.outlineColor = new Color32(0, 0, 0, 220);

            var bub = UIKit.Panel(rt, "bub", Pal.Sunk.A(0.95f), 6, Pal.Ember.A(0.55f));
            UIKit.At(bub.rectTransform, 0, 84, 132, 20, new Vector2(0.5f, 1));
            var bubT = UIKit.Label(bub.transform, "", 11, Pal.Ink, TextAlignmentOptions.Center, true);
            UIKit.Stretch(bubT.rectTransform, 6, 0, 6, 0);
            bub.gameObject.SetActive(false);

            _tag[u.Idx] = (rt, nm, barBg.rectTransform, fill, bub.rectTransform, bubT);
        }

        public void Say(string s)
        {
            _lines.Add(s);
            while (_lines.Count > 5) _lines.RemoveAt(0);
            _ticker.text = string.Join("\n", _lines);
        }

        public void Bubble(int idx, string text, float seconds = 2.2f)
        {
            if (!_tag.TryGetValue(idx, out var t)) return;
            t.bubT.text = text;
            t.bub.gameObject.SetActive(true);
            StopCoroutine("Hide"); StartCoroutine(Hide(t.bub.gameObject, seconds));
        }
        System.Collections.IEnumerator Hide(GameObject g, float s)
        {
            yield return new WaitForSeconds(s);
            if (g != null) g.SetActive(false);
        }

        /// 맞은 수·회복 수가 떠올랐다 사라진다
        public void Pop(int idx, string text, Color c)
        {
            if (!_tag.TryGetValue(idx, out var t)) return;
            var l = UIKit.Label(_float, text, 17, c, TextAlignmentOptions.Center, true);
            l.rectTransform.sizeDelta = new Vector2(80, 24);
            l.rectTransform.anchorMin = l.rectTransform.anchorMax = new Vector2(0, 0);
            l.outlineWidth = 0.25f; l.outlineColor = new Color32(0, 0, 0, 230);
            StartCoroutine(Rise(l, t.rt));
        }
        System.Collections.IEnumerator Rise(TextMeshProUGUI l, RectTransform anchor)
        {
            float t = 0;
            var from = anchor.anchoredPosition + new Vector2(0, 30);
            while (t < 0.85f && l != null)
            {
                t += Time.deltaTime;
                float k = t / 0.85f;
                l.rectTransform.anchoredPosition = from + new Vector2(0, 34 * k);
                l.color = new Color(l.color.r, l.color.g, l.color.b, 1 - k * k);
                yield return null;
            }
            if (l != null) Destroy(l.gameObject);
        }

        void LateUpdate()
        {
            if (B == null || Cam == null) return;
            _turn.text = B.Done ? (B.Win ? "층을 열었다 — " : "실패 — ") + B.Reason
                                : $"{Dir.ShownTurn}턴";
            foreach (var u in B.Units)
            {
                if (!_tag.TryGetValue(u.Idx, out var t)) continue;
                var v = Dir.ViewOf(u.Idx);
                if (v == null) { t.rt.gameObject.SetActive(false); continue; }
                var sp = Cam.WorldToScreenPoint(v.transform.position);
                bool vis = sp.z > 0;
                t.rt.gameObject.SetActive(vis);
                if (!vis) continue;
                t.rt.position = new Vector3(sp.x, sp.y - 2, 0);
                float pct = Mathf.Clamp01((float)Dir.ShownHp(u.Idx) / Mathf.Max(1, u.Max));
                t.fill.rectTransform.anchorMax = new Vector2(pct, 1);
                bool down = Dir.ShownHp(u.Idx) <= 0;
                t.bar.gameObject.SetActive(!down);
                t.nm.alpha = down ? 0.35f : 1f;
            }
        }

        public void ShowResult()
        {
            if (_resultCard != null) return;
            _resultCard = UIKit.Panel(_root, "result", Pal.Panel.A(0.96f), 14,
                                      B.Win ? Pal.Ok : Pal.Bad);
            UIKit.At(_resultCard.rectTransform, 0, 0, 460, 120, new Vector2(0.5f, 0.5f));
            _resultCard.rectTransform.anchoredPosition = new Vector2(-230, 60);
            _resultTop = UIKit.Label(_resultCard.transform, B.Win ? "층을 열었다" : "실패",
                                     30, B.Win ? Pal.Ok : Pal.Bad, TextAlignmentOptions.Center, true);
            UIKit.At(_resultTop.rectTransform, 0, -14, 440, 40, new Vector2(0.5f, 1));
            _resultSub = UIKit.Label(_resultCard.transform, $"{B.Reason} · {B.Round}턴",
                                     14, Pal.Muted, TextAlignmentOptions.Center);
            UIKit.At(_resultSub.rectTransform, 0, -56, 440, 20, new Vector2(0.5f, 1));
            var b = UIKit.Btn(_resultCard.transform, "편성 바꾸기", () => IremBoot.ShowRoster(Floor),
                              Pal.Ember.A(0.9f), Pal.Ground);
            UIKit.At(((RectTransform)b.transform), 0, -84, 160, 30, new Vector2(0.5f, 1));
        }
    }
}
