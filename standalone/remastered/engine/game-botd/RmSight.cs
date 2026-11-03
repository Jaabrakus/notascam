// rm_foe_near(M, dist, monsters): whether a unit an attack-move's look could pick stands within dist tiles of M: any
// /mob/Monsters but M within the square oview(dist, M) looks over (on M's z, M's own tile too) that isn't of M's own
// owner (game/Code/Remastered/Attack.dm RemasterHostile never picks one of its own owner's). False means the look
// (oview, its line of sight and every hostility rule) would find nobody, so the game skips it; true, it runs as before.
// No line of sight and no lists: the cells' movables are read in place (the memory patch). M off the map or inside
// something, or an owner deleted on either side: true (the look runs, as before), so a false is always the look's answer.
// An owner is a player (an object, the same one) or a name, as the wild creatures' "{NPC Goblins}" (the same text: Monster
// AI.dm LocateTarget skips a unit whose Owner == its own; rts-feel, 2026-10-25). M with no owner: any unit may be one it
// fights (true).
// The DM fallback (Remastered/Native.dm) answers true: on an engine without this, the look always runs.
// v12: with the unit grid on (RmGrid.cs), the units come from their cells instead of every tile; RM_GRID_VERIFY=1 does
// both and counts any difference.
// rm_foe_beside(M, foe, monsters) (v22; the owner, 10-29: "Morale + foe look"): whether Attack.dm RmFoeBeside(foe) can
// find anyone: a unit of type monsters but M on the nine tiles round M (the grid's, as RmUnitsNear(1, M) reads them) whose
// Owner isn't M's and is foe (DM's != and ==). 0: nobody, and RmFoeBeside answers null at once (2,900 looks a second in a
// 1000 v 1000, nearly all of them finding nobody: ~12 us each in DM); 1: someone, and its DM look picks one by every rule
// as before; null: the grid can't answer (off, or M not on a tile), and the DM look runs.
using System.Collections.Generic;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using OpenDreamShared.Dream;
using Robust.Shared.Maths;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmSight {
    private static readonly List<DreamObjectMovable> Beside = new();

    [DreamProc("rm_foe_beside")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("foe")]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_foe_beside(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m.Deleted) return DreamValue.Null;
        if (m.Loc is not DreamObjectTurf here) return DreamValue.Null;
        if (!bundle.GetArgument(2, "monsters").TryGetValueAsType(out var monsters)) return DreamValue.Null;
        if (!RmGrid.UnitsIn(here.X - 1, here.Y - 1, here.X + 1, here.Y + 1, here.Z, Beside)) return DreamValue.Null;
        var foe = bundle.GetArgument(1, "foe");
        if (!m.TryGetVariable("Owner", out var mOwner)) mOwner = DreamValue.Null;
        using (mOwner) {
            foreach (var o in Beside) {
                if (o == m || o.Deleted || !o.IsSubtypeOf(monsters)) continue;
                if (!o.TryGetVariable("Owner", out var oOwner)) oOwner = DreamValue.Null;
                using (oOwner) if (!DMOpcodeHandlers.IsEqual(oOwner, mOwner) && DMOpcodeHandlers.IsEqual(oOwner, foe)) return new DreamValue(1);
            }
        }
        return new DreamValue(0);
    }

    [DreamProc("rm_foe_near")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("dist", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_foe_near(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m.Deleted) return new DreamValue(1);
        if (m.Loc is not DreamObjectTurf here) return new DreamValue(1);
        if (!bundle.GetArgument(1, "dist").TryGetValueAsInteger(out var dist) || dist < 0) return new DreamValue(1);
        if (!bundle.GetArgument(2, "monsters").TryGetValueAsType(out var monsters)) return new DreamValue(1);
        DreamObject? own = null;
        string? ownName = null;
        if (m.TryGetVariable("Owner", out var mo)) {
            using (mo) {
                if (mo.TryGetValueAsDreamObject<DreamObject>(out var o)) {
                    if (o.Deleted) return new DreamValue(1);
                    own = o;
                } else if (mo.TryGetValueAsString(out var n)) {
                    ownName = n;
                }
            }
        }
        var map = bundle.MapManager;
        if (RmGrid.On) {   // the unit grid (RmGrid.cs, v12): the same units, read from their cells
            var g = RmGrid.FoeNear(m, here, dist, monsters, own, ownName);
            if (g != null) {
                if (!RmGrid.Verify) return new DreamValue(g.Value ? 1 : 0);
                var s = Scan(map, m, here, dist, monsters, own, ownName);
                RmGrid.Compared(g.Value == s, here, dist, g.Value, s);
                return new DreamValue(s ? 1 : 0);
            }
        }
        return new DreamValue(Scan(map, m, here, dist, monsters, own, ownName) ? 1 : 0);
    }

    // The tile scan: every tile of the square, the movables on it.
    private static bool Scan(Map.IDreamMapManager map, DreamObjectMovable m, DreamObjectTurf here, int dist, TreeEntry monsters, DreamObject? own, string? ownName) {
        for (var dy = -dist; dy <= dist; dy++) {
            for (var dx = -dist; dx <= dist; dx++) {
                if (!map.TryGetTurfAt(new Vector2i(here.X + dx, here.Y + dy), here.Z, out var t)) continue;
                foreach (var a in t.Cell.Movables) {
                    if (a == m || a.Deleted || !a.IsSubtypeOf(monsters)) continue;
                    if (own == null && ownName == null) return true;   // M has no owner: any unit may be one it fights
                    if (!a.TryGetVariable("Owner", out var ao)) return true;
                    using (ao) {
                        if (own != null) {
                            if (!ao.TryGetValueAsDreamObject<DreamObject>(out var o) || o.Deleted || o != own) return true;
                        } else if (!ao.TryGetValueAsString(out var an) || !string.Equals(an, ownName, System.StringComparison.Ordinal)) {
                            return true;
                        }
                    }
                }
            }
        }
        return false;
    }
}
