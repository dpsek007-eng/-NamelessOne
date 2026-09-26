// 잔상의 몸을 부르는 낯 하나.
//
// 2D 스프라이트(ShadeView)와 3D 몸(ShadeView3D)이 같은 말을 알아듣는다.
// 그래서 연출자는 무엇으로 보여 주는지 모른 채 「걸어라」 「쳐라」만 말한다 —
// BattleDirector 가 2D 로, Battle3DDirector·GardenDirector 가 3D 로 같은 사건 목록을 재생한다.
//
// 동작 이름은 한 벌뿐이다: idle · walk · attack · hurt · fall · look.
// tables.json 의 clips, chars/src/make_clips.py 의 CLIPS, 이 셋이 같은 낱말을 쓴다.
// 이름이 갈리면 Play() 가 조용히 아무것도 안 한다.
using UnityEngine;

namespace Irem.Game
{
    public interface IShadeView
    {
        /// 지금 하고 있는 동작의 이름
        string Clip { get; }

        /// 2D 에서는 좌우, 3D 에서는 몸이 오른쪽을 보는가
        bool Facing { get; }

        /// 몸이 실제로 서 있는 자리. 2D 는 리그, 3D 는 몸의 루트다.
        Vector3 Pos { get; }

        /// force = 이 동작이 끝날 때까지 다른 것으로 안 바뀐다
        void Play(string name, bool force = false);

        /// 칸에서 칸으로 미끄러져 간다. 순간이동하면 살아 있는 것으로 보이지 않는다.
        void MoveRig(Vector3 p, float seconds = 0.30f);

        /// 사건 없이 자리만 옮긴다 (세울 때)
        void Warp(Vector3 p);

        void Face(bool right);

        /// 맞은 순간 하얗게 튄다
        void Flash(Color c);

        /// 2D 의 그리는 순서. 3D 는 깊이로 가리므로 할 일이 없다.
        void SetOrder(int o);
    }
}
