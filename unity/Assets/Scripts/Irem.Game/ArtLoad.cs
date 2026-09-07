// 그림을 읽어 온다. 시트 한 장을 프레임으로 잘라 캐시한다.
using System.Collections.Generic;
using UnityEngine;

namespace Irem.Game
{
    public static class ArtLoad
    {
        public const int FW = 48, FH = 64, PPU = 16;      // 프레임 크기와 픽셀 대 유닛
        static readonly Dictionary<string, Sprite[]> _sheets = new();
        static readonly Dictionary<string, Sprite> _tiles = new();

        static readonly Dictionary<string, Texture2D> _tex = new();

        /// 시트 원본. 편성 화면은 프레임 하나만 잘라 쓰므로 텍스처가 그대로 필요하다.
        public static Texture2D SheetTex(string id)
        {
            if (_tex.TryGetValue(id, out var t)) return t;
            t = Resources.Load<Texture2D>("Irem/Shades/" + id);
            if (t != null) t.filterMode = FilterMode.Point;
            _tex[id] = t;
            return t;
        }
        public static Texture2D TileTex(string name)
        {
            var k = "#t/" + name;
            if (_tex.TryGetValue(k, out var t)) return t;
            t = Resources.Load<Texture2D>("Irem/Tiles/" + name);
            if (t != null) t.filterMode = FilterMode.Point;
            _tex[k] = t;
            return t;
        }

        public static Sprite[] Sheet(string id, int frames)
        {
            if (_sheets.TryGetValue(id, out var s)) return s;
            var tex = Resources.Load<Texture2D>("Irem/Shades/" + id);
            if (tex == null) { _sheets[id] = null; return null; }
            tex.filterMode = FilterMode.Point;
            var outp = new Sprite[frames];
            for (int i = 0; i < frames; i++)
                outp[i] = Sprite.Create(tex, new Rect(i * FW, 0, FW, FH),
                                        new Vector2(0.5f, 0.06f), PPU, 0,
                                        SpriteMeshType.FullRect);
            _sheets[id] = outp;
            return outp;
        }

        /// 시트에서 한 프레임만. UI 는 서 있는 자세 하나면 된다.
        public static Sprite Frame(string id, int nf, int frame = 0)
        {
            var f = Sheet(id, nf);
            return f == null || f.Length == 0 ? null : f[Mathf.Clamp(frame, 0, f.Length - 1)];
        }

        public static Sprite Tile(string name)
        {
            if (_tiles.TryGetValue(name, out var s)) return s;
            var tex = Resources.Load<Texture2D>("Irem/Tiles/" + name);
            if (tex == null) { _tiles[name] = null; return null; }
            tex.filterMode = FilterMode.Point;
            var sp = Sprite.Create(tex, new Rect(0, 0, tex.width, tex.height),
                                   new Vector2(0.5f, 0.5f), tex.width / 2f, 0,
                                   SpriteMeshType.FullRect);
            _tiles[name] = sp;
            return sp;
        }

        public static string TileName(char ch, int x, int y, int variants)
        {
            string k = ch switch
            {
                '#' => "block", ':' => "rubble", '~' => "crack", '_' => "drain",
                '^' => "high", 'o' => "cover", 'w' => "water", 'x' => "fire", _ => "plain",
            };
            int v = Mathf.Abs(x * 7 + y * 13 + ch) % Mathf.Max(1, variants);
            return k + "_" + v;
        }
    }
}
