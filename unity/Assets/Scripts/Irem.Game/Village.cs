// 마을. 일터 열네 곳에 실제로 서 있는 구조물을 세운다.
//
// 모양은 여기서 정하지 않는다. tools/places.py 가 한 번 적고, make_garden →
// export_unity → garden.json 으로 실려 와서, 브라우저(viewer/garden.html)와 여기가
// 똑같이 세운다. 두 군데에 모양을 적으면 두 화면이 조용히 갈라진다(docs/10-시스템-구조.md).
//
// 덩이는 넷뿐이다 — box · cyl · roof(박공) · pyr(사각뿔). 이 넷으로 열네 채가 다 선다.
// 표에 적힌 자리는 「칸 좌표」다: x 동쪽 · y 남쪽 · z 위. 유니티 땅은 y 가 커지는 쪽이
// -z 이므로(Ground3D.Cell) 여기서 (x, z, -y) 로 옮긴다. 옮기는 자리는 Local() 하나다.
//
// 감는 방향을 손으로 맞히지 않는다. 넷 다 볼록한 덩이라 속의 한 점을 잡아 두고,
// 면의 법선이 그 점을 등지지 않으면 뒤집는다. 브라우저 쪽에서 이걸 손으로 맞히다가
// 지붕 여섯 장이 검게 뚫렸었다 — 같은 실수를 두 번 하지 않는다.
using System.Collections.Generic;
using UnityEngine;
using Irem.Data;

namespace Irem.Game
{
    public static class Village
    {
        /// 0 돌 · 1 나무 · 2 쇠붙이·불빛. viewer/garden.html 의 PARTCOL 과 같은 값이다.
        static readonly Color32[] PartCol =
        {
            new Color32(0x7a, 0x71, 0x65, 255),
            new Color32(0x6d, 0x54, 0x3c, 255),
            new Color32(0xc8, 0x90, 0x3f, 255),
        };

        static readonly int ColourId = Shader.PropertyToID("_Colour");
        static readonly int FadeOnId = Shader.PropertyToID("_FadeOn");

        /// 칸 좌표 → 유니티 자리. 옮기는 곳은 여기 하나다.
        static Vector3 Local(float x, float y, float z) => new Vector3(x, z, -y);

        /// 한 채를 세운다. 돌아오는 값은 그 채의 꼭대기 높이(세계 좌표 y) —
        /// 이름표를 그 위에 띄우는 데 쓴다. 덩이가 없으면 z0 을 그대로 돌려준다.
        public static float Build(Transform parent, StationDef s, Material sil)
        {
            float z0 = s.z0;
            if (s.parts == null || s.parts.Length == 0) return z0;

            var root = new GameObject(s.name).transform;
            root.SetParent(parent, false);
            root.position = new Vector3(s.x, z0, -s.y);

            var slot = new Dictionary<int, Mesh3>();
            float top = 0f;
            foreach (var q in s.parts)
            {
                if (q == null || q.p == null || q.s == null || q.p.Length < 3) continue;
                int k = Mathf.Clamp(q.k, 0, PartCol.Length - 1);
                if (!slot.TryGetValue(k, out var m)) slot[k] = m = new Mesh3();
                if (!Add(m, q)) continue;
                float hi = q.p[2] + (q.t == "cyl" ? q.s[1] : q.s[2]);
                if (hi > top) top = hi;
            }

            foreach (var kv in slot)
            {
                if (kv.Value.V.Count == 0) continue;
                var go = new GameObject(s.name + ":" + kv.Key);
                go.transform.SetParent(root, false);
                go.AddComponent<MeshFilter>().sharedMesh = kv.Value.Bake(s.name + kv.Key);
                var mr = go.AddComponent<MeshRenderer>();
                mr.sharedMaterial = sil;
                mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
                mr.receiveShadows = false;
                // 색은 머티리얼이 아니라 블록으로 넣는다 — CastLoad 가 잔상에 하는 것과 같다.
                var mpb = new MaterialPropertyBlock();
                mpb.SetColor(ColourId, PartCol[kv.Key]);
                mpb.SetFloat(FadeOnId, 0f);      // 흐려지는 것은 사람이고, 건물은 거기 그냥 있다
                mr.SetPropertyBlock(mpb);
            }
            return z0 + top;
        }

        /// 연장이 놓이는 자리(세계 좌표). 휘두르는 손이 여기를 지난다.
        public static Vector3 WorkAt(StationDef s)
        {
            var w = s.work != null && s.work.Length >= 3 ? s.work : new[] { 0f, 0f, 1f };
            return new Vector3(s.x + w[0], s.z0 + w[2], -s.y - w[1]);
        }

        /// 연장이 일하는 사람을 향하게 돌린다. face 는 사람이 보는 쪽이므로 그 반대다.
        public static Quaternion FaceBack(StationDef s)
        {
            var f = s.face != null && s.face.Length >= 2 ? s.face : new[] { 0f, -1f };
            var d = Local(-f[0], -f[1], 0);
            return d.sqrMagnitude > 1e-6f ? Quaternion.LookRotation(d) : Quaternion.identity;
        }

        // ── 덩이 ─────────────────────────────────────────────────────
        sealed class Mesh3
        {
            public readonly List<Vector3> V = new();
            public readonly List<Vector3> N = new();
            public readonly List<int> T = new();

            /// 볼록한 덩이의 속 한 점을 등지도록 감는다. 면마다 제 법선을 갖는다(평면 음영).
            public void Face(Vector3 inside, params Vector3[] p)
            {
                if (p.Length < 3) return;
                var n = Vector3.Cross(p[1] - p[0], p[2] - p[0]);
                if (n.sqrMagnitude < 1e-12f) return;
                bool flip = Vector3.Dot(n, p[0] - inside) < 0f;
                n = (flip ? -n : n).normalized;
                int b = V.Count;
                for (int i = 0; i < p.Length; i++) { V.Add(p[i]); N.Add(n); }
                for (int i = 1; i < p.Length - 1; i++)
                {
                    if (flip) { T.Add(b); T.Add(b + i + 1); T.Add(b + i); }
                    else      { T.Add(b); T.Add(b + i); T.Add(b + i + 1); }
                }
            }

            public Mesh Bake(string name)
            {
                var m = new Mesh { name = name };
                if (V.Count > 65000) m.indexFormat = UnityEngine.Rendering.IndexFormat.UInt32;
                m.SetVertices(V); m.SetNormals(N); m.SetTriangles(T, 0);
                m.RecalculateBounds();
                return m;
            }
        }

        static bool Add(Mesh3 m, PartDef q)
        {
            float px = q.p[0], py = q.p[1], pz = q.p[2];
            Vector3 P(float x, float y, float z) => Local(px + x, py + y, pz + z);

            switch (q.t)
            {
                case "box":
                {
                    float w = q.s[0] / 2, d = q.s[1] / 2, h = q.s[2];
                    var c = P(0, 0, h / 2);
                    Vector3 A(int sx, int sy, int sz) => P(sx * w, sy * d, sz * h);
                    m.Face(c, A(-1,-1,0), A( 1,-1,0), A( 1, 1,0), A(-1, 1,0));   // 밑
                    m.Face(c, A(-1,-1,1), A( 1,-1,1), A( 1, 1,1), A(-1, 1,1));   // 위
                    m.Face(c, A(-1,-1,0), A( 1,-1,0), A( 1,-1,1), A(-1,-1,1));
                    m.Face(c, A(-1, 1,0), A( 1, 1,0), A( 1, 1,1), A(-1, 1,1));
                    m.Face(c, A(-1,-1,0), A(-1, 1,0), A(-1, 1,1), A(-1,-1,1));
                    m.Face(c, A( 1,-1,0), A( 1, 1,0), A( 1, 1,1), A( 1,-1,1));
                    return true;
                }
                case "cyl":
                {
                    float r = q.s[0], h = q.s[1];
                    int n = Mathf.Max(3, q.n);
                    var c = P(0, 0, h / 2);
                    var lo = new Vector3[n]; var hi = new Vector3[n];
                    for (int i = 0; i < n; i++)
                    {
                        float a = i * Mathf.PI * 2f / n;
                        float cx = Mathf.Cos(a) * r, cy = Mathf.Sin(a) * r;
                        lo[i] = P(cx, cy, 0); hi[i] = P(cx, cy, h);
                    }
                    for (int i = 0; i < n; i++)
                    {
                        int j = (i + 1) % n;
                        m.Face(c, lo[i], lo[j], hi[j], hi[i]);
                    }
                    m.Face(c, lo); m.Face(c, hi);
                    return true;
                }
                case "roof":
                {
                    // 박공지붕. a=="x" 면 용마루가 동서로 눕는다.
                    float w = q.s[0] / 2, d = q.s[1] / 2, h = q.s[2];
                    var c = P(0, 0, h / 3);
                    var b0 = P(-w, -d, 0); var b1 = P(w, -d, 0);
                    var b2 = P(w, d, 0);   var b3 = P(-w, d, 0);
                    Vector3 r0, r1;
                    if (q.a == "x") { r0 = P(-w, 0, h); r1 = P(w, 0, h); }
                    else            { r0 = P(0, -d, h); r1 = P(0, d, h); }
                    m.Face(c, b0, b1, b2, b3);                       // 밑
                    if (q.a == "x")
                    {
                        m.Face(c, b3, b2, r1, r0);                   // 남쪽 비탈
                        m.Face(c, b0, b1, r1, r0);                   // 북쪽 비탈
                        m.Face(c, b0, b3, r0);                       // 서쪽 박공
                        m.Face(c, b1, b2, r1);                       // 동쪽 박공
                    }
                    else
                    {
                        m.Face(c, b1, b2, r1, r0);                   // 동쪽 비탈
                        m.Face(c, b0, b3, r1, r0);                   // 서쪽 비탈
                        m.Face(c, b0, b1, r0);                       // 북쪽 박공
                        m.Face(c, b3, b2, r1);                       // 남쪽 박공
                    }
                    return true;
                }
                case "pyr":
                {
                    float w = q.s[0] / 2, d = q.s[1] / 2, h = q.s[2];
                    var c = P(0, 0, h / 4);
                    var b0 = P(-w, -d, 0); var b1 = P(w, -d, 0);
                    var b2 = P(w, d, 0);   var b3 = P(-w, d, 0);
                    var ap = P(0, 0, h);
                    m.Face(c, b0, b1, b2, b3);
                    m.Face(c, b0, b1, ap); m.Face(c, b1, b2, ap);
                    m.Face(c, b2, b3, ap); m.Face(c, b3, b0, ap);
                    return true;
                }
            }
            return false;
        }
    }
}
