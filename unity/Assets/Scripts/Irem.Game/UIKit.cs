// 화면을 코드로 짓는다. 프리팹을 쓰지 않는 이유는, 프리팹은 눈으로만 고칠 수 있어서
// 무엇이 왜 그렇게 생겼는지 코드에 남지 않기 때문이다.
//
// 스프라이트(둥근 모서리, 그림자, 고리)는 그때그때 만든다. 파일로 두면 또 관리해야 한다.
using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;

namespace Irem.Game
{
    public static class Pal
    {
        public static readonly Color Ground = Hex("#12161A");
        public static readonly Color Panel  = Hex("#1A2026");
        public static readonly Color Card   = Hex("#212931");
        public static readonly Color Sunk   = Hex("#0D1114");
        public static readonly Color Line   = Hex("#2C353D");
        public static readonly Color Ink    = Hex("#E6EAEE");
        public static readonly Color Body   = Hex("#B9C2CA");
        public static readonly Color Muted  = Hex("#7C8894");
        public static readonly Color Faint  = Hex("#55606B");
        public static readonly Color Ember  = Hex("#C9954F");
        public static readonly Color Ok     = Hex("#6FB18C");
        public static readonly Color Bad    = Hex("#C97A7A");
        public static readonly Color Slate  = Hex("#8FAAC1");

        public static Color Hex(string h)
        {
            ColorUtility.TryParseHtmlString(h, out var c); return c;
        }
        public static Color A(this Color c, float a) { c.a = a; return c; }
    }

    /// 스프라이트를 코드로 굽는다
    public static class Shapes
    {
        static readonly Dictionary<string, Sprite> _cache = new();

        /// 둥근 사각형 — 9슬라이스로 늘려 쓴다
        public static Sprite Round(int radius = 10, int thickness = 0)
        {
            string k = $"r{radius}_{thickness}";
            if (_cache.TryGetValue(k, out var s)) return s;
            int n = radius * 2 + 4;
            var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear };
            for (int y = 0; y < n; y++)
                for (int x = 0; x < n; x++)
                {
                    float dx = Mathf.Max(radius - x, x - (n - 1 - radius), 0);
                    float dy = Mathf.Max(radius - y, y - (n - 1 - radius), 0);
                    float d  = Mathf.Sqrt(dx * dx + dy * dy);
                    float a  = Mathf.Clamp01(radius - d + 0.5f);            // 바깥 경계 안티에일리어싱
                    if (thickness > 0)
                    {
                        float inner = Mathf.Clamp01(d - (radius - thickness) + 0.5f);
                        a = Mathf.Min(a, inner);
                    }
                    t.SetPixel(x, y, new Color(1, 1, 1, a));
                }
            t.Apply();
            s = Sprite.Create(t, new Rect(0, 0, n, n), new Vector2(0.5f, 0.5f), 100, 0,
                              SpriteMeshType.FullRect,
                              new Vector4(radius + 1, radius + 1, radius + 1, radius + 1));
            _cache[k] = s;
            return s;
        }

        /// 부드러운 원 — 그림자·발밑 고리·빛무리에 쓴다
        public static Sprite Blob(int size = 64, float soft = 0.55f)
        {
            string k = $"b{size}_{soft:0.00}";
            if (_cache.TryGetValue(k, out var s)) return s;
            var t = new Texture2D(size, size, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear };
            float r = size / 2f;
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float d = Vector2.Distance(new Vector2(x + .5f, y + .5f), new Vector2(r, r)) / r;
                    float a = Mathf.Clamp01(1 - Mathf.SmoothStep(1 - soft, 1f, d));
                    t.SetPixel(x, y, new Color(1, 1, 1, a));
                }
            t.Apply();
            s = Sprite.Create(t, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100);
            _cache[k] = s;
            return s;
        }

        /// 위아래로 어두워지는 판 — 화면 가장자리를 눌러 준다
        public static Sprite Vignette(int size = 256)
        {
            const string k = "vig";
            if (_cache.TryGetValue(k, out var s)) return s;
            var t = new Texture2D(size, size, TextureFormat.RGBA32, false) { filterMode = FilterMode.Bilinear };
            for (int y = 0; y < size; y++)
                for (int x = 0; x < size; x++)
                {
                    float dx = (x / (float)size - .5f) * 2, dy = (y / (float)size - .5f) * 2;
                    float d = Mathf.Sqrt(dx * dx * 0.85f + dy * dy);
                    t.SetPixel(x, y, new Color(0, 0, 0, Mathf.Clamp01((d - 0.55f) / 0.75f) * 0.72f));
                }
            t.Apply();
            s = Sprite.Create(t, new Rect(0, 0, size, size), new Vector2(0.5f, 0.5f), 100);
            _cache[k] = s;
            return s;
        }
    }

    public static class UIKit
    {
        public static TMP_FontAsset Sans, Serif;

        public static void LoadFonts()
        {
            Sans  ??= Resources.Load<TMP_FontAsset>("Irem/Fonts/NanumGothic SDF");
            Serif ??= Resources.Load<TMP_FontAsset>("Irem/Fonts/NanumMyeongjo SDF");
            if (Sans == null)
                Debug.LogWarning("한글 TMP 폰트가 없습니다. [이렘 → 폰트 만들기] 를 한 번 돌리십시오.");
        }

        // ── 뼈대 ──
        public static Canvas Root(Transform parent, string name = "UI", int order = 0)
        {
            LoadFonts();
            var go = new GameObject(name, typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            go.transform.SetParent(parent, false);
            var c = go.GetComponent<Canvas>();
            c.renderMode = RenderMode.ScreenSpaceOverlay;
            c.sortingOrder = order;
            var s = go.GetComponent<CanvasScaler>();
            s.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            s.referenceResolution = new Vector2(1280, 720);
            s.screenMatchMode = CanvasScaler.ScreenMatchMode.MatchWidthOrHeight;
            s.matchWidthOrHeight = 0.5f;
            if (EventSystem.current == null)
            {
                var es = new GameObject("EventSystem", typeof(EventSystem),
                                        typeof(StandaloneInputModule));
                es.transform.SetParent(parent, false);
            }
            return c;
        }

        public static RectTransform Rect(Transform parent, string name)
        {
            var go = new GameObject(name, typeof(RectTransform));
            go.transform.SetParent(parent, false);
            return (RectTransform)go.transform;
        }

        public static Image Panel(Transform parent, string name, Color fill,
                                  int radius = 10, Color? border = null)
        {
            var rt = Rect(parent, name);
            var img = rt.gameObject.AddComponent<Image>();
            img.sprite = Shapes.Round(radius);
            img.type = Image.Type.Sliced;
            img.color = fill;
            if (border.HasValue)
            {
                var b = Rect(rt, "border");
                Stretch(b);
                var bi = b.gameObject.AddComponent<Image>();
                bi.sprite = Shapes.Round(radius, 2);
                bi.type = Image.Type.Sliced;
                bi.color = border.Value;
                bi.raycastTarget = false;
            }
            return img;
        }

        public static TextMeshProUGUI Label(Transform parent, string text, float size, Color color,
                                            TextAlignmentOptions align = TextAlignmentOptions.MidlineLeft,
                                            bool serif = false)
        {
            var rt = Rect(parent, "t:" + (text ?? ""));
            var t = rt.gameObject.AddComponent<TextMeshProUGUI>();
            t.font = serif ? (Serif ?? Sans) : Sans;
            t.text = text ?? "";
            t.fontSize = size;
            t.color = color;
            t.alignment = align;
            t.enableWordWrapping = false;
            t.overflowMode = TextOverflowModes.Ellipsis;
            t.raycastTarget = false;
            return t;
        }

        /// 눌리는 판. 색이 바뀌고, 눌리면 살짝 들어간다.
        public static Button Btn(Transform parent, string label, Action onClick,
                                 Color? fill = null, Color? text = null, float size = 15)
        {
            var img = Panel(parent, "btn:" + label, fill ?? Pal.Card, 8, Pal.Line);
            var b = img.gameObject.AddComponent<Button>();
            b.targetGraphic = img;
            var cb = b.colors;
            cb.normalColor = Color.white;
            cb.highlightedColor = new Color(1.18f, 1.18f, 1.18f);
            cb.pressedColor = new Color(0.82f, 0.82f, 0.82f);
            cb.disabledColor = new Color(1, 1, 1, 0.35f);
            cb.fadeDuration = 0.08f;
            b.colors = cb;
            if (onClick != null) b.onClick.AddListener(() => onClick());
            var t = Label(img.transform, label, size, text ?? Pal.Ink, TextAlignmentOptions.Center);
            Stretch(t.rectTransform);
            return b;
        }

        /// 세로로 흐르는 목록. 스크롤은 손가락으로도 된다.
        public static (ScrollRect sr, RectTransform content) List(Transform parent, string name,
                                                                  float spacing = 4, int pad = 6)
        {
            var rt = Rect(parent, name);
            var sr = rt.gameObject.AddComponent<ScrollRect>();
            sr.horizontal = false;
            sr.movementType = ScrollRect.MovementType.Elastic;
            sr.scrollSensitivity = 28;

            var vp = Rect(rt, "viewport");
            Stretch(vp);
            var vi = vp.gameObject.AddComponent<Image>();
            vi.color = new Color(0, 0, 0, 0.001f);            // 레이캐스트용
            vp.gameObject.AddComponent<RectMask2D>();
            sr.viewport = vp;

            var content = Rect(vp, "content");
            content.anchorMin = new Vector2(0, 1); content.anchorMax = new Vector2(1, 1);
            content.pivot = new Vector2(0.5f, 1); content.offsetMin = new Vector2(0, 0);
            content.offsetMax = new Vector2(0, 0);
            var vl = content.gameObject.AddComponent<VerticalLayoutGroup>();
            vl.spacing = spacing;
            vl.padding = new RectOffset(pad, pad, pad, pad);
            // childControlHeight 를 끄면 LayoutElement 의 높이를 무시하고
            // 각 칸이 기본 100px 을 그대로 쓴다. 그러면 목록이 세로로 늘어진다.
            vl.childControlWidth = true; vl.childControlHeight = true;
            vl.childForceExpandWidth = true; vl.childForceExpandHeight = false;
            var fit = content.gameObject.AddComponent<ContentSizeFitter>();
            fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
            sr.content = content;
            return (sr, content);
        }

        // ── 자리잡기 ──
        public static RectTransform Stretch(RectTransform rt, float l = 0, float t = 0,
                                            float r = 0, float b = 0)
        {
            rt.anchorMin = Vector2.zero; rt.anchorMax = Vector2.one;
            rt.offsetMin = new Vector2(l, b); rt.offsetMax = new Vector2(-r, -t);
            return rt;
        }
        public static RectTransform At(RectTransform rt, float x, float y, float w, float h,
                                       Vector2? anchor = null)
        {
            var a = anchor ?? new Vector2(0, 1);
            rt.anchorMin = rt.anchorMax = a;
            rt.pivot = a;
            rt.anchoredPosition = new Vector2(x, y);
            rt.sizeDelta = new Vector2(w, h);
            return rt;
        }
        public static RectTransform Col(RectTransform rt, float x, float w, float top = 0, float bottom = 0)
        {
            rt.anchorMin = new Vector2(0, 0); rt.anchorMax = new Vector2(0, 1);
            rt.pivot = new Vector2(0, 0.5f);
            rt.offsetMin = new Vector2(x, bottom);
            rt.offsetMax = new Vector2(x + w, -top);
            rt.sizeDelta = new Vector2(w, rt.sizeDelta.y);
            return rt;
        }
        public static T Fit<T>(T g, float h) where T : Component
        {
            var le = g.gameObject.GetComponent<LayoutElement>() ?? g.gameObject.AddComponent<LayoutElement>();
            le.minHeight = le.preferredHeight = h;
            return g;
        }

        /// 시트에서 한 프레임만 잘라 쓰는 그림칸
        public static Image Shade(Transform parent, string artId, int nf, int frame = 0)
        {
            var rt = Rect(parent, "shade:" + artId);
            var img = rt.gameObject.AddComponent<Image>();
            img.raycastTarget = false;
            img.preserveAspect = true;
            var sp = ArtLoad.Frame(artId, nf, frame);
            if (sp != null) img.sprite = sp; else img.color = new Color(1, 1, 1, 0.06f);
            return img;
        }
    }
}
