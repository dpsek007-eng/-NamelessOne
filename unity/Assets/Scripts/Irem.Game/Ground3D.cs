// 3D 바닥. 뜰과 전투 층이 같은 땅 만드는 법을 쓴다.
//
// GardenDirector 에 먼저 적었다가 여기로 옮겼다. Battle3DDirector 가 같은 일을 해야 했고,
// 같은 규칙을 두 군데 적으면 조용히 갈라진다(docs/10-시스템-구조.md). 옮기면서
// 계산은 한 줄도 바꾸지 않았다 — 감는 방향·uv·법선이 그대로다.
//
// 타일 그림은 2D 전투가 쓰는 것을 그대로 쓴다(ArtLoad). 땅을 위해 그림을 새로 굽지 않는다.
// 빛을 받지 않는 재질이다 — 씬에 광원이 없다. Irem/Silhouette 셰이더가 제 빛 방향을
// 갖고 있어서, 광원을 넣으면 실루엣이 깨진다.
//
// 땅에 높이가 있다. 전에는 모든 꼭짓점을 y=0 으로 찍었고(예전 Slab), 그래서 담도
// 언덕도 우물물도 바닥에 그린 무늬였다 — 사람이 벽을 밟고 지나가는 것처럼 보였다.
// 높이는 지형 표(TerrDef.h)에서 온다. 여기서 정하지 않는다.
// 옆면은 「나보다 낮은 이웃 쪽」에만 붙인다. 같은 높이끼리는 안 보이는 면이므로
// 붙이면 삼각형만 두 배가 된다.
using System;
using System.Collections.Generic;
using UnityEngine;

namespace Irem.Game
{
    public static class Ground3D
    {
        /// 칸 하나가 1m. y 가 커지는 쪽이 -z 다 — 지도의 위쪽이 화면의 위쪽이 되게.
        public static Vector3 Cell(int x, int y) => new Vector3(x, 0, -y);

        /// 높이가 있는 땅의 그 칸. 뜰이 쓴다.
        public static Vector3 Cell(int x, int y, float h) => new Vector3(x, h, -y);

        static readonly Dictionary<string, Material> _mats = new();

        /// 칸마다 오브젝트를 하나씩 세우면 뜰이 504개가 된다. 같은 타일끼리 하나의 메시로 묶는다.
        /// 그리는 순서가 없다 — 수평이라 깊이가 알아서 가려 준다.
        /// hAt 이 null 이면 예전처럼 평평하다 — 전투 층이 그쪽이다.
        public static Transform Build(Transform parent, int w, int h,
                                      Func<int, int, char> at, int variants = 5,
                                      string name = "땅", Func<int, int, float> hAt = null)
        {
            var root = new GameObject(name).transform;
            root.SetParent(parent, false);

            var group = new Dictionary<string, List<Vector2Int>>();
            var order = new List<string>();
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    string n = ArtLoad.TileName(at(x, y), x, y, variants);
                    if (ArtLoad.TileTex(n) == null)          // 없는 타일은 평지로 깐다
                        n = ArtLoad.TileName('.', x, y, variants);
                    if (!group.TryGetValue(n, out var l))
                    {
                        group[n] = l = new List<Vector2Int>();
                        order.Add(n);
                    }
                    l.Add(new Vector2Int(x, y));
                }

            foreach (var n in order)
            {
                var mat = Mat(n);
                if (mat == null) continue;
                var go = new GameObject(name + ":" + n);
                go.transform.SetParent(root, false);
                go.AddComponent<MeshFilter>().sharedMesh = Slab(group[n], hAt, w, h);
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = mat;
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                mr.receiveShadows = false;
            }
            return root;
        }

        public static Material Mat(string name)
        {
            if (_mats.TryGetValue(name, out var m)) return m;
            var tex = ArtLoad.TileTex(name);
            if (tex == null) { _mats[name] = null; return null; }
            var sh = Shader.Find("Unlit/Texture");
            if (sh == null) sh = Shader.Find("Sprites/Default");
            if (sh == null)
            {
                Debug.LogError("[이렘] 땅에 쓸 셰이더(Unlit/Texture)를 못 찾았다.");
                _mats[name] = null; return null;
            }
            tex.wrapMode = TextureWrapMode.Clamp;
            m = new Material(sh) { mainTexture = tex };
            _mats[name] = m;
            return m;
        }

        /// 칸 목록을 윗면 한 장 + 낮은 이웃 쪽 옆면으로 펴서 하나의 메시로 만든다.
        /// 감는 방향은 유니티 기본 Quad 와 같은 규칙이다 —
        /// 삼각형 (v0,v1,v2) 에서 cross(v1-v0, v2-v0) 가 앞면의 법선이다.
        /// (Slab 의 첫 칸으로 손으로 확인했다: (0,0,1)×(1,0,1) = (0,1,0) = 위.)
        public static Mesh Slab(List<Vector2Int> cells,
                                Func<int, int, float> hAt = null, int w = 0, int h = 0)
        {
            var v = new List<Vector3>(cells.Count * 4);
            var uv = new List<Vector2>(cells.Count * 4);
            var nm = new List<Vector3>(cells.Count * 4);
            var tri = new List<int>(cells.Count * 6);

            // 뜰 밖은 「가장 낮은 곳」으로 친다. 그래야 가장자리 담에도 옆면이 붙는다.
            float H(int x, int y)
            {
                if (hAt == null) return 0f;
                if (w > 0 && h > 0 && (x < 0 || y < 0 || x >= w || y >= h)) return -0.5f;
                return hAt(x, y);
            }
            void Quad(Vector3 a, Vector3 b, Vector3 c, Vector3 d)
            {
                int i = v.Count;
                var n = Vector3.Cross(b - a, c - a).normalized;
                v.Add(a); v.Add(b); v.Add(c); v.Add(d);
                uv.Add(new Vector2(0, 0)); uv.Add(new Vector2(0, 1));
                uv.Add(new Vector2(1, 1)); uv.Add(new Vector2(1, 0));
                for (int k = 0; k < 4; k++) nm.Add(n);
                tri.Add(i + 0); tri.Add(i + 1); tri.Add(i + 2);
                tri.Add(i + 0); tri.Add(i + 2); tri.Add(i + 3);
            }

            foreach (var c in cells)
            {
                int x = c.x, y = c.y;
                float t = H(x, y);
                // 윗면. 예전 Slab 과 꼭짓점 차례가 같다 — 법선이 위로 나온다.
                Quad(new Vector3(x - 0.5f, t, -y - 0.5f), new Vector3(x - 0.5f, t, -y + 0.5f),
                     new Vector3(x + 0.5f, t, -y + 0.5f), new Vector3(x + 0.5f, t, -y - 0.5f));

                // 옆면. 지도의 y 가 커지는 쪽이 -z 다(Cell).
                //   (dx,dy) = 이웃 쪽 · (ax,az)-(bx,bz) = 그 쪽 모서리 두 끝
                for (int k = 0; k < 4; k++)
                {
                    int dx = k == 0 ? 1 : k == 1 ? -1 : 0;
                    int dy = k == 2 ? 1 : k == 3 ? -1 : 0;
                    float nh = H(x + dx, y + dy);
                    if (t - nh < 1e-4f) continue;           // 이웃이 더 높거나 같으면 안 보인다

                    float ex = x + dx * 0.5f, ez = -(y + dy * 0.5f);
                    // 모서리와 나란한 방향
                    float px = dx != 0 ? 0f : 0.5f, pz = dx != 0 ? 0.5f : 0f;
                    var a = new Vector3(ex - px, t,  ez - pz);
                    var b = new Vector3(ex + px, t,  ez + pz);
                    var lo = nh;
                    var qa = new Vector3(a.x, lo, a.z);
                    var qb = new Vector3(b.x, lo, b.z);
                    // 바깥(이웃 쪽)을 보게 감는다. 둘 중 맞는 차례를 법선으로 고른다 —
                    // 손으로 여덟 경우를 맞히는 것보다 여기서 한 번 재는 것이 틀리지 않는다.
                    var outward = new Vector3(dx, 0, -dy);
                    if (Vector3.Dot(Vector3.Cross(qa - a, qb - a), outward) > 0) Quad(a, qa, qb, b);
                    else Quad(a, b, qb, qa);
                }
            }

            var m = new Mesh { name = $"땅{cells.Count}칸" };
            if (v.Count > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
            m.SetVertices(v); m.SetUVs(0, uv); m.SetNormals(nm);
            m.SetTriangles(tri, 0);
            m.RecalculateBounds();
            return m;
        }

        /// 발밑 그림자. 이것 하나로 땅에 서 있는 것처럼 보인다 —
        /// 2D 가 스프라이트로 깔던 것을 수평으로 눕혔을 뿐이다(BattleDirector.SpawnUnits).
        public static GameObject Decal(Transform parent, string name, Sprite sp, Color col,
                                       float size, float y)
        {
            var go = new GameObject(name);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = new Vector3(0, y, 0);
            go.transform.localRotation = Quaternion.Euler(90, 0, 0);
            go.transform.localScale = new Vector3(size, size, 1);
            var sr = go.AddComponent<SpriteRenderer>();
            sr.sprite = sp; sr.color = col;
            sr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            sr.receiveShadows = false;
            return go;
        }
    }
}
