// 3D 바닥. 뜰과 전투 층이 같은 땅 만드는 법을 쓴다.
//
// GardenDirector 에 먼저 적었다가 여기로 옮겼다. Battle3DDirector 가 같은 일을 해야 했고,
// 같은 규칙을 두 군데 적으면 조용히 갈라진다(docs/10-시스템-구조.md). 옮기면서
// 계산은 한 줄도 바꾸지 않았다 — 감는 방향·uv·법선이 그대로다.
//
// 타일 그림은 2D 전투가 쓰는 것을 그대로 쓴다(ArtLoad). 땅을 위해 그림을 새로 굽지 않는다.
// 빛을 받지 않는 재질이다 — 씬에 광원이 없다. Irem/Silhouette 셰이더가 제 빛 방향을
// 갖고 있어서, 광원을 넣으면 실루엣이 깨진다.
using System;
using System.Collections.Generic;
using UnityEngine;

namespace Irem.Game
{
    public static class Ground3D
    {
        /// 칸 하나가 1m. y 가 커지는 쪽이 -z 다 — 지도의 위쪽이 화면의 위쪽이 되게.
        public static Vector3 Cell(int x, int y) => new Vector3(x, 0, -y);

        static readonly Dictionary<string, Material> _mats = new();

        /// 칸마다 오브젝트를 하나씩 세우면 뜰이 504개가 된다. 같은 타일끼리 하나의 메시로 묶는다.
        /// 그리는 순서가 없다 — 수평이라 깊이가 알아서 가려 준다.
        public static Transform Build(Transform parent, int w, int h,
                                      Func<int, int, char> at, int variants = 5,
                                      string name = "땅")
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
                go.AddComponent<MeshFilter>().sharedMesh = Slab(group[n]);
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

        /// 칸 목록을 수평 쿼드 한 장씩으로 펴서 하나의 메시로 만든다.
        /// 감는 방향은 유니티 기본 Quad 와 같은 규칙이다 —
        /// 삼각형 (v0,v1,v2) 에서 cross(v1-v0, v2-v0) 가 앞면의 법선이다.
        public static Mesh Slab(List<Vector2Int> cells)
        {
            int n = cells.Count;
            var v = new Vector3[n * 4];
            var uv = new Vector2[n * 4];
            var nm = new Vector3[n * 4];
            var tri = new int[n * 6];
            for (int i = 0; i < n; i++)
            {
                int x = cells[i].x, y = cells[i].y, b = i * 4, t = i * 6;
                v[b + 0] = new Vector3(x - 0.5f, 0, -y - 0.5f);
                v[b + 1] = new Vector3(x - 0.5f, 0, -y + 0.5f);
                v[b + 2] = new Vector3(x + 0.5f, 0, -y + 0.5f);
                v[b + 3] = new Vector3(x + 0.5f, 0, -y - 0.5f);
                uv[b + 0] = new Vector2(0, 0); uv[b + 1] = new Vector2(0, 1);
                uv[b + 2] = new Vector2(1, 1); uv[b + 3] = new Vector2(1, 0);
                for (int k = 0; k < 4; k++) nm[b + k] = Vector3.up;
                tri[t + 0] = b + 0; tri[t + 1] = b + 1; tri[t + 2] = b + 2;
                tri[t + 3] = b + 0; tri[t + 4] = b + 2; tri[t + 5] = b + 3;
            }
            var m = new Mesh { name = $"땅{n}칸" };
            m.vertices = v; m.uv = uv; m.normals = nm;
            m.triangles = tri;
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
