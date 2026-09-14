// 초상 셰이더 — 초점을 그림으로 옮긴다. 값 하나(_Focus)로 민다.
// `docs/22-아트.md` 「초점」이 정한 세 층을 이 순서로 쌓는다.
// 순서가 바뀌면 결과가 바뀐다.
//
//   1 이목구비   눈~입 자리만 (1-feature) 만큼 뭉갠다. 바깥은 안 건드린다
//   2 흐림       전체에 가우시안 blur
//   3 이중상     어긋난 사본 둘을 ghost 만큼 섞는다
//
// 값은 tools/focus_curve.py 가 정한 것을 그대로 옮긴 것이다. 같은 수가 세
// 군데에 적혀 있다 (여기 · focus_stack.py · viewer/index.html) — 한쪽을
// 고치면 다른 쪽도 고쳐야 한다. _Focus 밖의 파라미터는 게임 파라미터가
// 아니라 텍스처 속성이다:
//
//   _FaceRect  이목구비 자리 (UV x,y,w,h) — 조림 전에 tools/portrait_assemble.py
//              --sheet 가 parts.face_boxes.json 로 남긴다. 두상(base) 얼굴
//              상자 그대로다 (이목구비를 그 상자에 맞춰 끼우므로).
//   _Borrowed  빌린 특성 — ★6 에서도 이중상 0.15 가 끝까지 남는다 (docs/22).
//
// 실시간 셰이더는 진짜 컨벌루션 블러를 싸게 못 돌린다. 그래서 흐림을 9탭
// 근삿값으로 대신한다 — 도구(PNG 구움)와 뷰어(브라우저)는 진짜 블러고,
// 유니티는 반지름만 같은 근삿값이다. "초점이 안 맞은 정도"의 지표이지
// 포토샵 블러가 아니다.
Shader "Irem/Portrait"
{
    Properties
    {
        _MainTex  ("초상", 2D) = "white" {}
        _Focus    ("초점 (0 = 안 맞음, 1 = 완전히)", Range(0, 1)) = 0
        _FaceRect ("이목구비 자리 (UV x, y, w, h)", Vector) = (0.29, 0.16, 0.42, 0.42)
        _Borrowed ("빌린 특성 (0 = 고유, 1 = 빌린)", Float) = 0
    }

    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent"
               "IgnoreProjector" = "True" }

        Pass
        {
            Cull Off
            ZWrite Off
            Blend SrcAlpha OneMinusSrcAlpha

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"

            sampler2D _MainTex;
            float  _Focus, _Borrowed;
            float4 _FaceRect;

            // --- 정한 수 (아트 파라미터, 계산이 아니다) — tools/focus_curve.py ---
            const float BLUR_MAX      = 6.0;    // ★1 흐림 반경 (px, 512 기준)
            const float FEATURE_FLOOR = 0.25;   // ★1 에도 이목구비는 이만큼 보인다
            const float GHOST_MAX     = 0.40;   // ★1 이중상(잔상)의 진하기
            const float GHOST_OFF     = 3.0;    // ★1 이중상의 어긋난 거리 (px)
            const float GHOST_RESID   = 0.15;   // 빌린 특성의 ★6 잔류 이중상
            const float BORROW_OFF    = 1.0;    // 빌린 특성의 잔류 어긋남 (px, focus_stack)
            const float REF           = 512.0;  // 문서 px 값의 기준 크기. UV 로는 나눠라
            const float SMEAR         = 0.045;  // 이목구비 뭉갬 반지름 (초상 크기 대비)
                                                 //   focus_stack: max(1, size*0.045)
                                                 //   viewer: OFFN*0.045

            struct appdata
            {
                float4 vertex : POSITION;
                float2 uv     : TEXCOORD0;
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float2 uv  : TEXCOORD0;
            };

            v2f vert(appdata v)
            {
                v2f o;
                o.pos = UnityObjectToClipPos(v.vertex);
                o.uv  = v.uv;
                return o;
            }

            // 이목구비 자리 — viewer/index.html 의 fbox 와 같은 수:
            //   중심   cx = rect.x + w/2 ,  cy = rect.y + h*0.61
            //   반지름 rx = w*0.46       ,  ry = h*0.33
            //   가장자리는 0.72 배에서 1.0 배까지 부드럽게 사라진다 (radial gradient)
            float featureMask(float2 uv)
            {
                float2 c = float2(_FaceRect.x + _FaceRect.z * 0.5,
                                  _FaceRect.y + _FaceRect.w * 0.61);
                float2 r = float2(_FaceRect.z * 0.46, _FaceRect.w * 0.33);
                float2 p = (uv - c) / max(r, 1e-4);
                return 1.0 - smoothstep(0.72, 1.0, length(p));
            }

            // 흐림 한 번 — 중심 + 축 4탭 + 대각 4탭 = 9탭.
            // 가중치가 0.40 + 4×0.09 + 4×0.06 = 1.0 이라 r=0 이면 원본 그대로다
            // (★5 전승·★6 고유는 그림이 갈라지지 않아야 한다).
            float3 blur9(float2 uv, float r)
            {
                const float wc = 0.40, wa = 0.09, wd = 0.06;
                float3 o = tex2D(_MainTex, uv).rgb * wc;
                o += tex2D(_MainTex, uv + float2( r,  0)).rgb * wa;
                o += tex2D(_MainTex, uv + float2(-r,  0)).rgb * wa;
                o += tex2D(_MainTex, uv + float2( 0,  r)).rgb * wa;
                o += tex2D(_MainTex, uv + float2( 0, -r)).rgb * wa;
                o += tex2D(_MainTex, uv + float2( r,  r)).rgb * wd;
                o += tex2D(_MainTex, uv + float2(-r,  r)).rgb * wd;
                o += tex2D(_MainTex, uv + float2( r, -r)).rgb * wd;
                o += tex2D(_MainTex, uv + float2(-r, -r)).rgb * wd;
                return o;
            }

            half4 frag(v2f i) : SV_Target
            {
                float f  = saturate(_Focus);
                float bk = _Borrowed > 0.5 ? 1.0 : 0.0;

                // --- focus_curve.py 와 같은 숫자들 ---
                float blurPx   = BLUR_MAX  * (1.0 - f);            // px, 512 기준
                float feature  = FEATURE_FLOOR
                               + (1.0 - FEATURE_FLOOR) * sqrt(f);
                float ghost    = GHOST_MAX * (1.0 - f);
                float goffPx   = GHOST_OFF * (1.0 - f);
                if (bk > 0.0) {                                    // 빌린 특성
                    ghost  = max(ghost,  GHOST_RESID);
                    goffPx = max(goffPx, BORROW_OFF);
                }
                float blurUv  = blurPx  / REF;
                float goffUv  = goffPx  / REF;

                // 층 1·2 — 이목구비를 (1-feature) 만큼 뭉개고, 전체를 흐리운다.
                //   바깥은 blur 뿐, 얼굴 자리는 뭉갬+흐림이 겹친 만큼(제곱합) 뭉갠다.
                //   이 우물 정은 보는 사람 눈에는 순서 1→2 로 쌓인 것과 같다
                //   (블러는 선형이고 이목구비 자리는 블러 폭보다 훨씬 크다).
                float  k  = featureMask(i.uv) * (1.0 - feature);
                float  rc = sqrt(SMEAR * SMEAR + blurUv * blurUv);
                float3 bs = blur9(i.uv, blurUv);
                float3 bm = blur9(i.uv, rc);
                float3 base = lerp(bs, bm, k);

                // 층 3 — 어긋난 사본 둘을 ghost 만큼 섞는다.
                //   focus_stack/viewer 는 사본마다 ghost/2 를 쓴다 (밑에 깔면
                //   불투명한 초상에서는 본판이 덮어 아무것도 안 보인다).
                float3 rgb = base;
                if (ghost > 0.001)
                {
                    float2 o1 = float2(-2.0, -1.0) * goffUv;
                    float2 o2 = float2( 2.0,  0.6) * goffUv;
                    // 사본 자리는 흐림+뭉갬이 끝난 것을 통째로 옮긴 것이어야
                    // 하는데, 오프셋(≤ 6px)은 블러 폭 안이라 중심 값을 쓰면
                    // 된다. 얼굴 부분의 bm 은 뭉개져 있어 옮겨도 같다.
                    float3 c1 = lerp(blur9(i.uv + o1, blurUv), bm, k);
                    float3 c2 = lerp(blur9(i.uv + o2, blurUv), bm, k);
                    rgb = base * (1.0 - ghost) + (c1 + c2) * (ghost * 0.5);
                }

                float a = tex2D(_MainTex, i.uv).a;
                return half4(rgb, a);
            }
            ENDCG
        }
    }
}