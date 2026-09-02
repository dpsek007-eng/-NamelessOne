namespace Irem.Sim
{
    /// xorshift64. 언어·런타임이 달라도 같은 시드는 같은 수열을 낸다.
    /// System.Random 을 쓰면 .NET 버전에 따라 결과가 달라져 시드 저장이 깨진다.
    public struct Rng
    {
        ulong _s;
        public Rng(ulong seed) { _s = seed | 1UL; }

        public ulong Next()
        {
            unchecked
            {
                ulong x = _s;
                x ^= x << 13;
                x ^= x >> 7;
                x ^= x << 17;
                _s = x;
                return x;
            }
        }
        /// [0,1) — 파이썬 (next()>>11)/2^53 과 동일
        public double F() => (Next() >> 11) / 9007199254740992.0;
        public int I(int k) => (int)(Next() % (ulong)k);
    }
}
