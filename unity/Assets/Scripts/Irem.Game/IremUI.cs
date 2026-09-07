// 화면에 글자와 그림을 얹는 데 필요한 것들.
//
//   IMGUI 를 쓴다. 렌더 파이프라인이 무엇이든 나오고, 프리팹도 씬 배선도 필요 없다.
//   대신 유니티 기본 폰트에는 한글이 없다. OS 폰트를 런타임에 만들어 끼운다.
using System.Collections.Generic;
using UnityEngine;
using Irem.Data;

namespace Irem.Game
{
    public static class IremUI
    {
        // 리눅스·윈도·맥에서 차례로 찾는다. 하나라도 있으면 한글이 나온다.
        static readonly string[] Faces =
        {
            "Noto Sans CJK KR", "NanumGothic", "나눔고딕", "Noto Sans KR",
            "Malgun Gothic", "맑은 고딕", "AppleSDGothicNeo-Regular", "Apple SD Gothic Neo",
            "Arial Unicode MS", "Arial",
        };

        static readonly Dictionary<int, Font> _fonts = new();
        static bool _warned;
        public static Font Face(int size)
        {
            if (_fonts.TryGetValue(size, out var f) && f != null) return f;
            f = Font.CreateDynamicFontFromOSFont(Faces, size);
            if (f == null && !_warned)
            {
                _warned = true;
                Debug.LogWarning("한글 폰트를 찾지 못했습니다. 글자가 네모로 보이면 " +
                                 "Noto Sans CJK KR 또는 나눔고딕을 설치하거나 " +
                                 "IremUI.Faces 에 쓰시는 폰트 이름을 넣으십시오.");
            }
            _fonts[size] = f;
            return f;
        }

        // ── 색 ──
        public static readonly Color Ink   = new(0.902f, 0.910f, 0.918f);
        public static readonly Color Body  = new(0.760f, 0.784f, 0.804f);
        public static readonly Color Muted = new(0.545f, 0.576f, 0.608f);
        public static readonly Color Faint = new(0.412f, 0.447f, 0.478f);
        public static readonly Color Ember = new(0.788f, 0.584f, 0.310f);
        public static readonly Color Ok    = new(0.471f, 0.698f, 0.580f);
        public static readonly Color Bad   = new(0.788f, 0.478f, 0.478f);
        public static readonly Color Slate = new(0.561f, 0.667f, 0.757f);
        public static readonly Color Panel = new(0.106f, 0.122f, 0.137f, 0.96f);
        public static readonly Color Sunk  = new(0.055f, 0.067f, 0.078f, 0.96f);
        public static readonly Color Line  = new(0.169f, 0.192f, 0.216f);

        static Texture2D _px;
        public static Texture2D Px
        {
            get
            {
                if (_px != null) return _px;
                _px = new Texture2D(1, 1); _px.SetPixel(0, 0, Color.white); _px.Apply();
                return _px;
            }
        }

        public static void Fill(Rect r, Color c)
        {
            var old = GUI.color; GUI.color = c;
            GUI.DrawTexture(r, Px); GUI.color = old;
        }
        public static void Box(Rect r, Color fill, Color border)
        {
            Fill(r, fill);
            Fill(new Rect(r.x, r.y, r.width, 1), border);
            Fill(new Rect(r.x, r.yMax - 1, r.width, 1), border);
            Fill(new Rect(r.x, r.y, 1, r.height), border);
            Fill(new Rect(r.xMax - 1, r.y, 1, r.height), border);
        }
        public static void Bar(Rect r, float pct, Color c)
        {
            Fill(r, Sunk);
            Fill(new Rect(r.x, r.y, r.width * Mathf.Clamp01(pct), r.height), c);
        }

        // ── 글자 ──
        static GUIStyle _s;
        public static GUIStyle S(int size, Color c, TextAnchor a = TextAnchor.UpperLeft,
                                 FontStyle fs = FontStyle.Normal, bool clip = true)
        {
            _s ??= new GUIStyle();
            _s.font = Face(size);
            _s.fontSize = size;
            _s.fontStyle = fs;
            _s.alignment = a;
            _s.clipping = clip ? TextClipping.Clip : TextClipping.Overflow;
            _s.wordWrap = false;
            _s.normal.textColor = c;
            _s.padding = new RectOffset(0, 0, 0, 0);
            return _s;
        }
        public static void Text(Rect r, string t, int size, Color c,
                                TextAnchor a = TextAnchor.MiddleLeft, FontStyle fs = FontStyle.Normal)
            => GUI.Label(r, t, S(size, c, a, fs));

        /// 눌리는 칸. GUI.Button 은 기본 스킨이 붙어 보기 싫으므로 직접 그린다.
        public static bool Hit(Rect r) =>
            Event.current.type == EventType.MouseDown && r.Contains(Event.current.mousePosition)
            && ConsumeClick();
        static bool ConsumeClick() { Event.current.Use(); return true; }

        public static bool Btn(Rect r, string label, bool on = false, bool enabled = true)
        {
            bool hover = r.Contains(Event.current.mousePosition);
            Box(r, on ? new Color(0.16f, 0.19f, 0.22f) : (hover && enabled ? new Color(0.13f, 0.15f, 0.18f) : Sunk),
                   on ? Slate : Line);
            Text(r, label, 13, enabled ? (on ? Ink : Body) : Faint, TextAnchor.MiddleCenter);
            return enabled && Hit(r);
        }

        // ── 잔상 그림 ──
        /// 시트에서 한 프레임만 잘라 그린다. 서 있는 자세(idle 0번)를 쓴다.
        public static void Shade(Rect r, string artId, int nf, int frame = 0)
        {
            var tex = ArtLoad.SheetTex(artId);
            if (tex == null) { Fill(r, new Color(1, 1, 1, 0.05f)); return; }
            float w = 1f / Mathf.Max(1, nf);
            GUI.DrawTextureWithTexCoords(r, tex, new Rect(frame * w, 0, w, 1));
        }

        /// 층 지도를 작게 미리 보여 준다
        public static void MiniMap(Rect r, FloorDef f, int variants = 5)
        {
            if (f?.map == null || f.map.Length == 0) return;
            int h = f.map.Length, w = f.map[0].Length;
            float cw = r.width / w, ch = r.height / h;
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    var cell = new Rect(r.x + x * cw, r.y + y * ch, cw + 0.5f, ch + 0.5f);
                    var g = ArtLoad.TileTex("plain_" + (Mathf.Abs(x * 7 + y * 13) % variants));
                    if (g != null) GUI.DrawTexture(cell, g);
                    char c = x < f.map[y].Length ? f.map[y][x] : '.';
                    if (c == '.') continue;
                    var t = ArtLoad.TileTex(ArtLoad.TileName(c, x, y, variants));
                    if (t != null) GUI.DrawTexture(cell, t);
                }
        }
    }
}
