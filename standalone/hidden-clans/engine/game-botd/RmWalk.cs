// Walkability for the route search and the game's own checks (rm_walk, RmStep.cs), rule for rule as
// game/Code/Remastered/Orders.dm RemasterWalkableDM (with
// Flying.dm RmFliesOver and WallWalks.dm RemasterWalkRoom). Change those procs and this file together: the shadow mode
// (Native.dm, RM_PATH_VERIFY=1) logs any route that differs. The constants (the stairs icon, the beast-foot and monster
// types, the ground and sky layers) come from the DM caller, so they stay defined in one place.
// A deleted object still listed on a tile is passed over, as DM's own "for(var/atom/movable/A in T)" does (its list
// enumerator reads values through MustGetValueAsDreamObject, which gives null for a deleted object).
// Walkable answers as RemasterWalkable does with a side list: 0 not walkable, 1 open, 2 open but for units of the
// mover's side (its owner's or an ally's), which it goes through (clips) but never stops on.
// Version 23: the movables' density, Flying, Wagon and Owner are read through RmKept.cs (kept while each one's change
// counter stands), and a tile's icon_state once a check.
// Version 25 (swimming, the owner 10-29): deep water (RmSwim.Water) is open to a unit that swims (RmSwim.Swims), unless
// Swim is off (the battle field's rules); the route search and the route map count a water tile as RmSwim.Cost steps.
// Version 8 (jobs' own-door rule, the user: "my own villagers open my own unlocked doors as they pass and close them
// behind"): with the door types given (Native.dm passes them when the game has the rule on), a tile with a door of the
// mover's very owner, placed, unlocked, not a trapdoor, open or shut, is 2 as well (Doors.dm RmOwnDoor).
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;

namespace OpenDreamRuntime.Procs.Native;

internal sealed class RmWalkRules {
    public DreamValue StairsIcon;
    public TreeEntry? FootType;      // /obj/RmBeastFoot: a beast's own feet don't block it
    public TreeEntry? MonsterType;   // /mob/Monsters
    public int GroundZ;
    public int SkyZ;
    public DreamList? Pass;          // rm_path_pass: a group's walking members, gone through
    public DreamList? Side;          // RmSide(M): the owners whose units it goes through, or null
    public TreeEntry? SiegeType;     // /mob/Monsters/RemasterSiege: siege engines are never gone through
    public TreeEntry? DoorType;      // /obj/Items/Furniture/Doors, or null: no own-door rule (an older game)
    public TreeEntry? TrapDoorType;  // /obj/Items/Furniture/Doors/TrapDoor: never one of them
    public bool IgnoreUnits;         // the route map's (RmRoute.cs): units are passed over (they move; the steps' own checks meet them)
    public bool Swim = true;         // version 25 (RmSwim.cs): a swimmer goes into deep water; the battle field's rules don't (RmField.cs)

    private static readonly DreamValue Svartalfar = new("Svartalfar"), Demon = new("Demon");

    // RmFliesOver(A, T): a flying monster goes over anything on the ground and sky layers.
    public bool FliesOver(DreamObject m, DreamObjectTurf t) {
        if (MonsterType == null || !m.IsSubtypeOf(MonsterType) || !RmKept.Flying(m)) return false;
        return t.Z == GroundZ || t.Z == SkyZ;
    }

    // RemasterWalkRoom(T, mover): room on a wall-walk tile, two to a tile.
    private bool WalkRoom(DreamObjectTurf t, DreamObject mover) {
        if (RmNative.Truthy(t, "density")) return false;
        var n = 0;
        foreach (var a in t.Cell.Movables) {   // the tile's things, read from its cell (no contents list made: the memory patch)
            if (a.Deleted || a == mover || !RmKept.Dense(a)) continue;
            if (MonsterType == null || !a.IsSubtypeOf(MonsterType)) return false;
            n++;
        }
        return n < 2;
    }

    // RmSideUnit(A, side): a unit of the mover's side, not a siege engine or a cart (also the plain step's, RmStep.cs).
    internal bool SideUnit(DreamObject a) {
        if (Side == null || MonsterType == null || !a.IsSubtypeOf(MonsterType)) return false;
        if (SiegeType != null && a.IsSubtypeOf(SiegeType)) return false;
        if (RmKept.Wagon(a)) return false;
        if (a is not DreamObjectMovable am) {
            if (!a.TryGetVariable("Owner", out var o2)) return false;
            using (o2) return !o2.IsNull && Side.ContainsValue(o2);
        }
        var owner = RmKept.Owner(am);
        return !owner.IsNull && Side.ContainsValue(owner);
    }

    // RmOwnDoor(A, M) (Doors.dm): a placed, unlocked door, not a trapdoor, with an owner, and a unit (not a siege engine or
    // a cart) of that very owner (not an ally): it goes through, open or shut (the door opens as it steps at it).
    private bool OwnDoor(DreamObject a, DreamObject m) {
        if (DoorType == null || !a.IsSubtypeOf(DoorType) || (TrapDoorType != null && a.IsSubtypeOf(TrapDoorType))) return false;
        if (!RmNative.Truthy(a, "Placed") || RmNative.Truthy(a, "Locked")) return false;
        if (MonsterType == null || !m.IsSubtypeOf(MonsterType)) return false;
        if (!a.TryGetVariable("Owner", out var doorOwner)) return false;
        using (doorOwner) {
            if (!doorOwner.IsTruthy()) return false;
            if (!m.TryGetVariable("Owner", out var owner)) return false;
            using (owner) if (!doorOwner.Equals(owner)) return false;
        }
        if (SiegeType != null && m.IsSubtypeOf(SiegeType)) return false;
        return !RmNative.Truthy(m, "Wagon");
    }

    // RemasterWalkable(T, M, goal, side)
    public int Walkable(DreamObjectTurf t, DreamObject m, DreamObjectTurf? goal) {
        if (FliesOver(m, t)) return 1;
        if (RmNative.Truthy(t, "density") && !(Swim && RmSwim.Water(t) && RmSwim.Swims(m, MonsterType))) return 0;   // deep water: swimmers (version 25)
        if (RmNative.VarEquals(t, "icon", StairsIcon) && t != goal) return 0;
        if (RmNative.Truthy(t, "remaster_wallwalk")) return WalkRoom(t, m) ? 1 : 0;
        var iconState = RmNative.VarString(t, "icon_state");   // once: DM's == against a text
        if (RmKept.Dense(m) && !RmKept.Flying(m) && (iconState == "Chasm" || iconState == "Sky")) return 0;
        if (iconState == "GoodGrass" && (RmNative.Truthy(m, "Infects") || RmNative.Truthy(m, "Undead") || RmNative.Truthy(m, "Unholy") ||
                RmNative.VarEquals(m, "Race", Svartalfar) || RmNative.VarEquals(m, "Race", Demon))) return 0;
        var result = 1;
        foreach (var a in t.Cell.Movables) {   // the tile's things, read from its cell (no contents list made: the memory patch)
            if (a.Deleted || a == m) continue;
            if (IgnoreUnits && MonsterType != null && a.IsSubtypeOf(MonsterType)) continue;
            if (!RmKept.Dense(a)) {
                if (OwnDoor(a, m)) result = 2;   // its owner's door, open: through, never stopped on
                continue;
            }
            if (FootType != null && a.IsSubtypeOf(FootType) && RmNative.VarIsObject(a, "owner", m)) continue;
            if (Pass != null) {
                using var passed = Pass.GetValue(new DreamValue(a));
                if (passed.IsTruthy()) continue;
            }
            if (OwnDoor(a, m)) {   // shut: through (it opens as the unit steps at it), never stopped on
                result = 2;
                continue;
            }
            if (SideUnit(a)) {
                result = 2;
                continue;
            }
            return 0;
        }
        return result;
    }
}
