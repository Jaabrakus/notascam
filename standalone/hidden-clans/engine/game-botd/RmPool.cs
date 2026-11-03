// An attack box's next foe, ranked (native version 15; the owner, 10-28: "Yes, box re-pick"). Formations.dm
// RemasterPoolNext looked at every foe of the box for every pick (up to 500 in a 500 v 500: about 6 ms a pick, 90 ms a
// game second once foes fall fast). This does the part that needs no game rule beyond plain values, in one pass:
//   - the foes the pick drops from the box: no loc, or no longer one it may fight (Attack.dm RemasterHostile with
//     explicit 1, rule for rule: HP, dying, CantKill, WS, a cart, its own owner's, by the realms' verdicts, on a tile of
//     its level, not a chest);
//   - for each foe left on its level, the lowest score RemasterFoeScore could give it, its room unknown: (far ? the
//     archers and casters on it : the fighters on it) x 1000 + all on it x 100 + get_dist. The real score is that, or
//     100000 more when a fighter finds no free side; a foe it can't get at or can't see is left out by the game.
// The game walks the foes in that order (Formations.dm RmPoolWalk), with its own down, fog, room and score rules, and stops
// when no later foe can score lower: the same foe as the whole loop's (RM_POOL_VERIFY=1 checks every pick).
//   rm_pool_rank(M, pool, load, far_on, far, now, verdicts, monsters, player, chests, siege)
//     list(foes, lowest scores, down (1/0), dropped, unknown owners or null, pool places): foes in order of lowest score,
//     then place in the pool; null when the box holds a siege engine (their own rule: the whole loop runs) or M isn't
//     on a tile. Unknown owners: players not judged this tick (the game judges them and asks again).
using System.Collections.Generic;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmPool {
    private readonly struct Cand(DreamObjectMovable foe, float lb, int place, bool down) {
        public readonly DreamObjectMovable Foe = foe;
        public readonly float Lb = lb;
        public readonly int Place = place;
        public readonly bool Down = down;
    }

    private static readonly List<Cand> Cands = new();

    [DreamProc("rm_pool_rank")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("pool", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("load", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("far_on", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("far", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("now", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("verdicts", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("monsters", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("player", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("chests", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("siege", Type = DreamValueTypeFlag.DreamType)]
    public static DreamValue NativeProc_rm_pool_rank(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m.Deleted) return DreamValue.Null;
        if (m.Loc is not DreamObjectTurf here) return DreamValue.Null;
        if (!bundle.GetArgument(1, "pool").TryGetValueAsDreamList(out var pool)) return DreamValue.Null;
        bundle.GetArgument(2, "load").TryGetValueAsDreamList(out var load);
        bundle.GetArgument(3, "far_on").TryGetValueAsDreamList(out var farOn);
        var far = bundle.GetArgument(4, "far").IsTruthy();
        if (!bundle.GetArgument(5, "now").TryGetValueAsFloat(out var now)) return DreamValue.Null;
        bundle.GetArgument(6, "verdicts").TryGetValueAsDreamList(out var verdicts);
        if (!bundle.GetArgument(7, "monsters").TryGetValueAsType(out var monsters)) return DreamValue.Null;
        if (!bundle.GetArgument(8, "player").TryGetValueAsType(out var player)) return DreamValue.Null;
        bundle.GetArgument(9, "chests").TryGetValueAsType(out var chests);
        bundle.GetArgument(10, "siege").TryGetValueAsType(out var siege);
        if (!m.TryGetVariable("Owner", out var mOwner)) mOwner = DreamValue.Null;
        using (mOwner) {
            var mPlayer = RmMorale.IsPlayer(mOwner, player);
            Cands.Clear();
            DreamList? dropped = null, unknown = null;
            HashSet<DreamObject>? asked = null;
            var place = 0;
            foreach (var v in pool.EnumerateValues()) {   // the list's own values: never disposed (RmNative traps)
                place++;
                if (!v.TryGetValueAsDreamObject<DreamObjectMovable>(out var e) || e == null || e.Deleted || !e.IsSubtypeOf(monsters)) continue;   // the typed loop skips them
                if (siege != null && e.IsSubtypeOf(siege)) {
                    dropped?.DecRef();   // made here and held by nothing: let go
                    unknown?.DecRef();
                    return DreamValue.Null;
                }
                if (e.Loc == null || !Hostile(m, e, mOwner, mPlayer, now, verdicts, player, chests, bundle, ref unknown, ref asked)) {
                    if (e.Loc == null || !UnknownFor(e, mPlayer, player, verdicts)) (dropped ??= bundle.ObjectTree.CreateList()).AddValue(new DreamValue(e));
                    continue;
                }
                if (e.Z != here.Z) continue;
                var all = Count(load, e);
                var farN = Count(farOn, e);
                var dist = e.Loc == here ? -1 : System.Math.Max(System.Math.Abs(e.X - here.X), System.Math.Abs(e.Y - here.Y));
                var lb = (far ? farN : all - farN) * 1000 + all * 100 + dist;
                var down = RmNative.Truthy(e, "Fainted") || RmNative.Truthy(e, "rm_dying_until") || RmMorale.Num(e, "remaster_ko_until") > now;
                Cands.Add(new Cand(e, lb, place, down));
            }
            if (unknown != null) {   // the game judges these players and asks again; nothing else is used
                var only = bundle.ObjectTree.CreateList();
                for (var i = 0; i < 4; i++) only.AddValue(DreamValue.Null);
                using (var v = new DreamValue(unknown)) only.AddValue(v);   // the list holds it; this proc lets go
                only.AddValue(DreamValue.Null);
                dropped?.DecRef();   // made here and held by nothing: let go
                return new DreamValue(only);
            }
            Cands.Sort((a, b) => a.Lb != b.Lb ? a.Lb.CompareTo(b.Lb) : a.Place.CompareTo(b.Place));
            var foes = bundle.ObjectTree.CreateList();
            var lbs = bundle.ObjectTree.CreateList();
            var downs = bundle.ObjectTree.CreateList();
            var places = bundle.ObjectTree.CreateList();
            foreach (var c in Cands) {
                foes.AddValue(new DreamValue(c.Foe));
                lbs.AddValue(new DreamValue(c.Lb));
                downs.AddValue(new DreamValue(c.Down ? 1 : 0));
                places.AddValue(new DreamValue(c.Place));
            }
            Cands.Clear();
            var list = bundle.ObjectTree.CreateList();
            using (var v = new DreamValue(foes)) list.AddValue(v);   // the list holds them; this proc lets go
            using (var v = new DreamValue(lbs)) list.AddValue(v);
            using (var v = new DreamValue(downs)) list.AddValue(v);
            using (var v = dropped != null ? new DreamValue(dropped) : DreamValue.Null) list.AddValue(v);
            list.AddValue(DreamValue.Null);
            using (var v = new DreamValue(places)) list.AddValue(v);
            return new DreamValue(list);
        }
    }

    // A foe failed Hostile only because its owner wasn't judged yet: not dropped (the game asks again).
    private static bool UnknownFor(DreamObject e, bool mPlayer, TreeEntry player, DreamList? verdicts) {
        if (!mPlayer || verdicts == null) return false;
        if (!e.TryGetVariable("Owner", out var o)) return false;
        using (o) {
            if (!RmMorale.IsPlayer(o, player)) return false;
            using var got = verdicts.GetValue(o);
            return !got.TryGetValueAsInteger(out var n) || n == 0;
        }
    }

    private static float Count(DreamList? l, DreamObject e) {
        if (l == null) return 0;
        using var got = l.GetValue(new DreamValue(e));
        return got.TryGetValueAsFloat(out var n) ? n : 0;
    }

    // RemasterHostile(me, E, explicit 1) for a unit that isn't a siege engine.
    private static bool Hostile(DreamObjectMovable m, DreamObjectMovable e, DreamValue mOwner, bool mPlayer, float now, DreamList? verdicts,
                                TreeEntry player, TreeEntry? chests, NativeProc.Bundle bundle, ref DreamList? unknown, ref HashSet<DreamObject>? asked) {
        if (e == m) return false;
        if (RmMorale.Num(e, "HP") <= 0 || RmNative.Truthy(e, "GoingToDie") || RmNative.Truthy(e, "CantKill") || RmNative.Truthy(e, "WS") || RmNative.Truthy(e, "Wagon")) return false;
        if (!e.TryGetVariable("Owner", out var eOwner)) eOwner = DreamValue.Null;
        using (eOwner) {
            if (eOwner.IsTruthy() && DMOpcodeHandlers.IsEqual(eOwner, mOwner)) return false;
            if (mPlayer && RmMorale.IsPlayer(eOwner, player)) {
                if (verdicts == null) {
                    (unknown ??= bundle.ObjectTree.CreateList()).AddValue(eOwner);   // judged in the game
                    return false;
                }
                int v;
                using (var got = verdicts.GetValue(eOwner)) v = got.TryGetValueAsInteger(out var n) ? n : 0;
                if (v == 0) {
                    eOwner.TryGetValueAsDreamObject<DreamObject>(out var oo);
                    if ((asked ??= new HashSet<DreamObject>()).Add(oo!)) (unknown ??= bundle.ObjectTree.CreateList()).AddValue(eOwner);
                    return false;
                }
                if (v == 1) return false;
                if (v == 3 && !RmMorale.AttackedLately(m, e, mOwner, now)) return false;
            }
        }
        if (e.Loc is not DreamObjectTurf || m.Loc is not DreamObjectTurf mt || e.Z != mt.Z) return false;
        if (chests != null && e.IsSubtypeOf(chests)) return false;
        return true;
    }
}
