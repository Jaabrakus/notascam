using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;

namespace OpenDreamRuntime.Map;

// Keep original map placements independently of later movement and variable
// changes. Tracking does not add a DM reference or prevent normal deletion.
public sealed partial class DreamMapManager {
    private sealed class MapSeed(DreamObjectDefinition definition, int x, int y, int z) {
        public readonly DreamObjectDefinition Definition = definition;
        public readonly int X = x, Y = y, Z = z;
        public DreamObject? Instance;
    }

    private readonly List<MapSeed> _mapSeeds = new();
    private bool _repopulating;

    private void CreateSeedInstance(MapSeed seed, DreamObjectTurf turf) {
        var definition = seed.Definition;
        DreamObject obj;
        if (definition.IsSubtypeOf(_objectTree.Mob))
            obj = new DreamObjectMob(definition);
        else if (definition.IsSubtypeOf(_objectTree.Movable))
            obj = new DreamObjectMovable(definition);
        else if (definition.IsSubtypeOf(_objectTree.Atom))
            obj = new DreamObjectAtom(definition);
        else
            obj = new DreamObject(definition);
        // Publish before New(): constructors can themselves call Repop().
        seed.Instance = obj;
        obj.InitSpawn(new(new DreamValue(turf)));
        obj.DecRef();
    }

    public void Repopulate() {
        if (_repopulating) return;
        _repopulating = true;
        try {
            foreach (var seed in _mapSeeds) {
                if (seed.Instance is { Deleted: false }) continue;
                if (TryGetTurfAt((seed.X, seed.Y), seed.Z, out var turf))
                    CreateSeedInstance(seed, turf);
            }
        } finally {
            _repopulating = false;
        }
    }
}
