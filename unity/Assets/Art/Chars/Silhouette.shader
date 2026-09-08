// 잔상은 짙은 실루엣 하나와 강조색 하나로 읽힌다. 그리고 발끝이 흐려진다.
// `docs/22-아트.md` — "아래에서 위로 사라지는 존재다".
//
// 그래서 이 셰이더가 하는 일은 셋뿐이다.
//   · 단색으로 칠한다 (질감·그림자·반사 없음. 있으면 실루엣이 깨진다)
//   · 한 방향 빛으로 아주 조금만 밝기를 준다 — 팔과 몸통이 겹쳐도 갈리게
//   · 발밑에서부터 알파를 깎는다. 오브젝트 원점이 발이므로(블렌더에서 z0=0)
//     원점 기준 높이를 쓴다. 월드 Y 를 그냥 쓰면 계단 위에 선 잔상이나
//     확인 신처럼 공중에 늘어놓은 잔상에서 발끝이 아니라 엉뚱한 데가 사라진다
//
// 색은 머티리얼이 아니라 MaterialPropertyBlock 으로 넣는다.
// 강조색은 계층이 아니라 개체별로 다르기 때문이다(20종 이상).
// 55벌마다 머티리얼을 만들면 드로우콜만 늘고 얻는 것이 없다.
Shader "Irem/Silhouette"
{
    Properties
    {
        _Colour  ("색",            Color)        = (0.13, 0.11, 0.10, 1)
        _Light   ("빛 방향",       Vector)       = (0.3, 0.9, 0.4, 0)
        _Wrap    ("밝기 폭",       Range(0, 0.6)) = 0.20
        _FadeTop ("흐려짐 높이(m)", Float)        = 0.22
        _FadeOn  ("흐려짐 켬",     Float)        = 1
    }

    SubShader
    {
        Tags { "Queue" = "Transparent" "RenderType" = "Transparent"
               "IgnoreProjector" = "True" }

        Pass
        {
            // 옷은 얇은 껍질이라 안쪽 면이 보인다. Cull Off 가 아니면 구멍이 뚫린다.
            Cull Off
            // 단색이므로 앞뒤 순서가 틀려도 그림이 같다. 깊이는 쓴다 —
            // 그래야 뒤에 선 잔상이 앞의 잔상을 뚫고 나오지 않는다.
            ZWrite On
            Blend SrcAlpha OneMinusSrcAlpha

            CGPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #include "UnityCG.cginc"

            struct appdata
            {
                float4 vertex : POSITION;
                float3 normal : NORMAL;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct v2f
            {
                float4 pos : SV_POSITION;
                float3 n   : TEXCOORD0;
                float  y   : TEXCOORD1;   // 제 발밑에서 잰 높이. 흐려짐은 이것만 본다
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            float4 _Light;   // xyz 만 쓴다. 셰이더랩 Vector 는 4성분이다
            float  _Wrap, _FadeTop, _FadeOn;

            UNITY_INSTANCING_BUFFER_START(Props)
                UNITY_DEFINE_INSTANCED_PROP(float4, _Colour)
            UNITY_INSTANCING_BUFFER_END(Props)

            v2f vert(appdata v)
            {
                v2f o;
                UNITY_SETUP_INSTANCE_ID(v);
                UNITY_TRANSFER_INSTANCE_ID(v, o);
                o.pos = UnityObjectToClipPos(v.vertex);
                o.n   = UnityObjectToWorldNormal(v.normal);
                o.y   = mul(unity_ObjectToWorld, v.vertex).y - unity_ObjectToWorld._m13;
                return o;
            }

            fixed4 frag(v2f i) : SV_Target
            {
                UNITY_SETUP_INSTANCE_ID(i);
                float4 c = UNITY_ACCESS_INSTANCED_PROP(Props, _Colour);

                float l = (1.0 - _Wrap)
                        + _Wrap * saturate(dot(normalize(i.n), normalize(_Light.xyz)));

                float a = lerp(1.0, smoothstep(0.0, max(1e-4, _FadeTop), i.y), _FadeOn);
                clip(a - 0.01);          // 완전히 사라진 곳은 깊이도 쓰지 않는다

                return float4(c.rgb * l, a * c.a);
            }
            ENDCG
        }
    }
}
