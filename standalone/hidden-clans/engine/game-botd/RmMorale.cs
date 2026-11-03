// Morale's look round (native version 14; the owner, 10-28: "Yes, morale next"): Morale.dm RmMoraleTick's count of the
// units within r tiles of a unit in combat, read from the unit grid (RmGrid.cs) with no list made, rule for rule as its DM
// loop and Attack.dm RemasterHostile with explicit 0 (both stay as the fallback and the reference; Native.dm RmMoraleLook,
// RM_MORALE_VERIFY=1 runs both and logs any difference).
// A unit counts when it isn't M and has HP above 0, isn't dying, a critter, fainted, asleep or knocked out
// (remaster_ko_until past now). Of M's very owner (DM ==, text owners too): an ally. Otherwise a foe when RemasterHostile
// would say so: not CantKill, WS or a cart, not a chest, not a caravan, and by its owner:
//   - M's owner not a /Player, or the unit's owner not one: a foe (RemasterWarAllows says yes);
//   - both players: the game's verdict for that owner, from verdicts (an assoc list owner -> 1 allied, 2 at war, 3 at
//     peace) made once a tick by the game (RemasterAllied, RemasterAtWar). At peace a foe only when one attacked the other
//     within 30 s (RemasterWarAllows: M's remaster_attacker is it, or its remaster_attacker is of M's owner).
// An owner missing from verdicts goes in the answer's unknown list (the game judges it and asks again). Siege engines go
// in its sieges list: their own rule (RemasterHostile's first lines) runs in the game.
//   rm_morale_look(M, r, royal_r, now, chests, siege, player, verdicts)
//     list(foes, beside (a foe within a tile), allies (not counting M), royal (with royal_r: 1 when a unit of M's owner with
//     IsRoyal and HP above 0 stands within royal_r, else 0; null without), unknown owners or null, siege engines or null);
//     null when the grid is off or M isn't standing on a tile (the DM loop runs).
// v22 (the owner, 10-29: "Morale + foe look"): a look was ~90 us in a 1000 v 1000, nearly all of it reading a dozen vars
// of each of the ~100 units round M by name. What a look reads of a unit is now kept with the unit's change counter
// (DreamObjectMovable.RmChanges, RmVer.cs: it moves on every DM var write to the unit or anything in it, every move and
// every look change), and read again only when that counter has moved: the same answers, as the vars are only ever
// written through SetVariable (or animate, also counted). Owners are kept as read and compared as before; the verdicts
// and the attacked-lately rule are read fresh every look. Deleted units' entries go once a game minute.
//   rm_morale_stats()   tests: "looks N kept N read N"
using System.Collections.Generic;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmMorale {
    private static readonly List<DreamObjectMovable> Near = new();
    private static long _looks, _kept, _read;

    // What a look reads of a unit, as of its change counter Changes.
    private sealed class Seen {
        public int Changes;
        public float Hp, KoUntil;
        public bool Out;        // GoingToDie, Critter, Fainted or Sleeping
        public bool NotFoe;     // CantKill, WS, Wagon or remaster_caravan (chests and siege engines: by type, each look)
        public bool IsRoyal;
        public DreamValue Owner;   // as read; the unit's var holds the reference, read again when Changes moves
    }
    private static readonly Dictionary<DreamObjectMovable, Seen> Kept = new();
    private static float _sweepAt;

    private static Seen SeenOf(DreamObjectMovable o) {
        if (Kept.TryGetValue(o, out var s)) {
            if (s.Changes == o.RmChanges) {
                _kept++;
                return s;
            }
        } else {
            s = new Seen();
            Kept[o] = s;
        }
        _read++;
        s.Changes = o.RmChanges;
        s.Hp = Num(o, "HP");
        s.KoUntil = Num(o, "remaster_ko_until");
        s.Out = RmNative.Truthy(o, "GoingToDie") || RmNative.Truthy(o, "Critter") || RmNative.Truthy(o, "Fainted") || RmNative.Truthy(o, "Sleeping");
        s.NotFoe = RmNative.Truthy(o, "CantKill") || RmNative.Truthy(o, "WS") || RmNative.Truthy(o, "Wagon") || RmNative.Truthy(o, "remaster_caravan");
        s.IsRoyal = RmNative.Truthy(o, "IsRoyal");
        if (!o.TryGetVariable("Owner", out var owner)) owner = DreamValue.Null;
        s.Owner = owner;
        owner.Dispose();
        return s;
    }

    // Deleted units' entries, once a game minute
    private static void Sweep(float now) {
        if (now < _sweepAt && now >= _sweepAt - 1200) return;
        _sweepAt = now + 600;
        List<DreamObjectMovable>? gone = null;
        foreach (var o in Kept.Keys) if (o.Deleted) (gone ??= new()).Add(o);
        if (gone != null) foreach (var o in gone) Kept.Remove(o);
    }

    [DreamProc("rm_morale_stats")]
    public static DreamValue NativeProc_rm_morale_stats(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        return new DreamValue($"looks {_looks} kept {_kept} read {_read}");
    }

    [DreamProc("rm_morale_look")]
    [DreamProcParameter("M", Type = DreamValueTypeFlag.DreamObject)]
    [DreamProcParameter("r", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("royal_r", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("now", Type = DreamValueTypeFlag.Float)]
    [DreamProcParameter("chests", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("siege", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("player", Type = DreamValueTypeFlag.DreamType)]
    [DreamProcParameter("verdicts", Type = DreamValueTypeFlag.DreamObject)]
    public static DreamValue NativeProc_rm_morale_look(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "M").TryGetValueAsDreamObject<DreamObjectMovable>(out var m) || m.Deleted) return DreamValue.Null;
        if (m.Loc is not DreamObjectTurf here) return DreamValue.Null;
        if (!bundle.GetArgument(1, "r").TryGetValueAsInteger(out var r)) return DreamValue.Null;
        bundle.GetArgument(2, "royal_r").TryGetValueAsInteger(out var royalR);
        if (!bundle.GetArgument(3, "now").TryGetValueAsFloat(out var now)) return DreamValue.Null;
        bundle.GetArgument(4, "chests").TryGetValueAsType(out var chests);
        bundle.GetArgument(5, "siege").TryGetValueAsType(out var siege);
        if (!bundle.GetArgument(6, "player").TryGetValueAsType(out var player)) return DreamValue.Null;
        bundle.GetArgument(7, "verdicts").TryGetValueAsDreamList(out var verdicts);
        var box = System.Math.Max(r, royalR);   // one read of the grid for both looks
        if (!RmGrid.UnitsIn(here.X - box, here.Y - box, here.X + box, here.Y + box, here.Z, Near)) return DreamValue.Null;
        _looks++;
        Sweep(now);
        if (!m.TryGetVariable("Owner", out var mOwner)) mOwner = DreamValue.Null;
        using (mOwner) {
            var mPlayer = IsPlayer(mOwner, player);
            int foes = 0, beside = 0, allies = 0;
            DreamList? unknown = null, sieges = null;
            HashSet<DreamObject>? asked = null;
            var found = 0;
            foreach (var o in Near) {
                if (o == m || o.Deleted) continue;
                var d = System.Math.Max(System.Math.Abs(o.X - here.X), System.Math.Abs(o.Y - here.Y));
                var royalLook = royalR > 0 && found == 0 && d <= royalR;
                if (d > r && !royalLook) continue;
                var s = SeenOf(o);
                if (royalLook && s.IsRoyal && s.Hp > 0 && DMOpcodeHandlers.IsEqual(s.Owner, mOwner)) found = 1;   // RmMoraleRoyalNear's test
                if (d > r) continue;
                if (s.Hp <= 0 || s.Out || s.KoUntil > now) continue;
                var oOwner = s.Owner;
                {
                    if (DMOpcodeHandlers.IsEqual(oOwner, mOwner)) {
                        allies++;
                        continue;
                    }
                    if (siege != null && o.IsSubtypeOf(siege)) {
                        (sieges ??= bundle.ObjectTree.CreateList()).AddValue(new DreamValue(o));
                        continue;
                    }
                    if (s.NotFoe || (chests != null && o.IsSubtypeOf(chests))) continue;
                    if (mPlayer && IsPlayer(oOwner, player)) {
                        if (verdicts == null) {
                            unknown?.DecRef();   // made here and held by nothing: let go
                            sieges?.DecRef();
                            return DreamValue.Null;
                        }
                        int v;
                        using (var got = verdicts.GetValue(oOwner)) v = got.TryGetValueAsInteger(out var n) ? n : 0;
                        if (v == 0) {   // not judged yet this tick: the game judges it and asks again
                            oOwner.TryGetValueAsDreamObject<DreamObject>(out var oo);
                            if ((asked ??= new HashSet<DreamObject>()).Add(oo!)) (unknown ??= bundle.ObjectTree.CreateList()).AddValue(oOwner);
                            continue;
                        }
                        if (v == 1) continue;
                        if (v == 3 && !AttackedLately(m, o, mOwner, now)) continue;
                    }
                    foes++;
                    if (d <= 1) beside++;
                }
            }
            var royal = royalR > 0 ? new DreamValue(found) : DreamValue.Null;
            var list = bundle.ObjectTree.CreateList();
            list.AddValue(new DreamValue(foes));
            list.AddValue(new DreamValue(beside));
            list.AddValue(new DreamValue(allies));
            list.AddValue(royal);
            using (var v = unknown != null ? new DreamValue(unknown) : DreamValue.Null) list.AddValue(v);   // the list holds them; this proc lets go
            using (var v = sieges != null ? new DreamValue(sieges) : DreamValue.Null) list.AddValue(v);
            return new DreamValue(list);
        }
    }

    // istype(owner, /Player): a live object of that type (DM reads a deleted one as null)
    internal static bool IsPlayer(DreamValue owner, TreeEntry player) =>
        owner.TryGetValueAsDreamObject<DreamObject>(out var o) && o != null && !o.Deleted && o.IsSubtypeOf(player);

    // RemasterWarAllows' last lines: M's attacker within 30 s is o, or o's attacker within 30 s is of M's owner.
    internal static bool AttackedLately(DreamObject m, DreamObject o, DreamValue mOwner, float now) {
        if (RmNative.VarIsObject(m, "remaster_attacker", o) && now - Num(m, "remaster_attacked_at") < 300) return true;
        if (!o.TryGetVariable("remaster_attacker", out var a)) return false;
        using (a) {
            if (!a.TryGetValueAsDreamObject<DreamObject>(out var ao) || ao == null || ao.Deleted) return false;
            if (!ao.TryGetVariable("Owner", out var aOwner)) aOwner = DreamValue.Null;
            using (aOwner) if (!DMOpcodeHandlers.IsEqual(aOwner, mOwner)) return false;
        }
        return now - Num(o, "remaster_attacked_at") < 300;
    }

    internal static float Num(DreamObject o, string name) {
        if (!o.TryGetVariable(name, out var v)) return 0;
        using (v) return v.TryGetValueAsFloat(out var n) ? n : 0;
    }
}
