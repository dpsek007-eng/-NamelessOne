// 재생을 누르기 전에는 화면이 비어 있다. 모든 것이 재생할 때 만들어지기 때문이다.
// 그래서 빈 화면 대신 무엇을 눌러야 하는지 적어 둔다.
using UnityEngine;

namespace Irem.Game
{
    [ExecuteAlways]
    [AddComponentMenu("이렘/안내")]
    public sealed class IremHint : MonoBehaviour
    {
        void OnGUI()
        {
            if (Application.isPlaying) return;      // 재생 중에는 진짜 화면이 그린다
            float w = Screen.width, h = Screen.height;
            IremUI.Fill(new Rect(0, 0, w, h), new Color(0.071f, 0.082f, 0.094f));
            var r = new Rect(0, h * 0.36f, w, 30);
            IremUI.Text(r, "이렘의 탑", 26, IremUI.Ink, TextAnchor.MiddleCenter, FontStyle.Bold);
            IremUI.Text(new Rect(0, h * 0.36f + 34, w, 24),
                        "▶ 재생을 누르면 편성 화면이 뜹니다", 15, IremUI.Ember, TextAnchor.MiddleCenter);
            IremUI.Text(new Rect(0, h * 0.36f + 62, w, 22),
                        "층을 고르고 · 슬롯을 누르고 · 잔상을 고른 뒤 · 등반",
                        12, IremUI.Muted, TextAnchor.MiddleCenter);
            IremUI.Text(new Rect(0, h - 34, w, 20),
                        "메뉴 [이렘 → 자체 점검] 으로 그림·폰트·판정을 한 번에 확인할 수 있습니다",
                        11, IremUI.Faint, TextAnchor.MiddleCenter);
        }
    }
}
