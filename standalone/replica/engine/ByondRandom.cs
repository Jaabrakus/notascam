namespace OpenDreamRuntime;

// MT19937 with the output projections measured against BYOND 516.1655.
// rand/prob use the high 24 bits; pick uses the low 16 bits of each draw.
public sealed class ByondRandom : Random {
    private readonly uint[] _state = new uint[624];
    private int _index = 624;

    public ByondRandom() : this(Environment.TickCount) { }
    public ByondRandom(int seed) {
        _state[0] = unchecked((uint)seed);
        for (var i = 1; i < _state.Length; i++)
            _state[i] = unchecked(1812433253u * (_state[i-1] ^ (_state[i-1] >> 30)) + (uint)i);
    }

    private uint Draw() {
        if (_index == 624) {
            for (var i = 0; i < 624; i++) {
                var joined = (_state[i] & 0x80000000u) | (_state[(i+1)%624] & 0x7fffffffu);
                _state[i] = _state[(i+397)%624] ^ (joined >> 1) ^ ((joined & 1) == 0 ? 0u : 0x9908b0dfu);
            }
            _index = 0;
        }
        var value = _state[_index++];
        value ^= value >> 11;
        value ^= (value << 7) & 0x9d2c5680u;
        value ^= (value << 15) & 0xefc60000u;
        return value ^ (value >> 18);
    }

    public override float NextSingle() => (Draw() >> 8) / 16777216f;
    public override double NextDouble() => NextSingle();
    protected override double Sample() => NextDouble();
    public override int Next() => Next(int.MaxValue);
    public override int Next(int maxValue) => Next(0, maxValue);
    public override int Next(int minValue, int maxValue) {
        if (minValue > maxValue) throw new ArgumentOutOfRangeException(nameof(maxValue));
        // DM performs this multiplication at single precision before truncating.
        // A double intermediate differs at rare integer boundaries.
        return minValue + (int)(NextSingle() * ((long)maxValue-minValue));
    }
    public double NextWeight() => (Draw() & 65535u) / 65536.0;
    public int NextPick(int count) => (int)(NextWeight() * count);
}
