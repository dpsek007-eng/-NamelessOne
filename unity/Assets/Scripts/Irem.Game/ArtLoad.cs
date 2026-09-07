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
