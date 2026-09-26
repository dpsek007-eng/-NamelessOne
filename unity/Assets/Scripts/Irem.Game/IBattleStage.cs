// 전투를 보여 주는 연출자를 부르는 낯.
//
// BattleHud 가 글자를 얹을 때 알아야 하는 것만 모았다: 지금 몇 턴인가, 멈췄는가,
// 어느 잔상이 어디 서 있는가, 남은 체력이 몇인가.
//
// 이 낯을 낸 이유는 하나다. 2D 와 3D 가 같은 판(BattleHud)을 쓰게 하려고.
// 3D 용으로 HUD 를 한 벌 더 베끼면 버튼 두 개와 이름표 규칙이 두 군데 있게 되고,
// 한쪽만 고치는 날이 온다(docs/10-시스템-구조.md).
//
// BattleDirector 의 ViewOf 는 ShadeView 를 그대로 돌려주던 것이라 그 서명을 남겨 두고,
// 이 낯의 ViewOf 만 따로 잇는다 — 2D 쪽 코드는 한 줄도 바뀌지 않는다.
namespace Irem.Game
{
    public interface IBattleStage
    {
        bool Paused { get; }
        int ShownTurn { get; }
        string SpeedLabel { get; }
        void TogglePause();
        void CycleSpeed();

        /// 이름표를 몸 위로 얼마나 올려 놓는가(m). 2D 는 0 — 지금 화면이 그렇다.
        /// 3D 는 발밑이 몸의 자리라서 올려야 머리 위에 온다.
        float TagLift { get; }

        /// 그 잔상의 몸. 아직 세우지 않았으면 null 이다.
        IShadeView ViewOf(int idx);

        /// 재생이 지금까지 보여 준 체력. 계산이 끝난 값이 아니라 「화면이 아는 값」이다.
        int ShownHp(int idx);
    }
}
