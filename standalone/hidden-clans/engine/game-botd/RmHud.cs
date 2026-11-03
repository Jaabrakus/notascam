// Remastered: the HUD's units delta (native version 30; U5's rest, reports/u5-hud-1031, 10-31; the owner: "lets do it").
//   rm_hud_units(units, old, parts, hot, full)
//     units  the HUD model's unit entries (HUD.dm RemasterHUDData), each an associative list with its "ref"
//     old    the last send's codes (ref -> the entry's parts as JSON, HUD.dm RemasterHUDUnitsDelta), or null
//     parts  rm_hud_unit_parts (each part that goes on its own when it changes); hot  rm_hud_hot (the fast fields)
//     full   1: a full model (nothing is compared)
//   What HUD.dm RmHudUnitsPass does in DM, to the byte. For each entry: its hot row as text (the fields Stringify'd and
//   joined by ",", as DM's "[...]" makes them); a kept entry ("#r", taken off) reuses the last send's codes list with its
//   hot row rewritten; any other is encoded (each part it holds that isn't null, by the engine's own json_encode, a null
//   one taken out of the entry; "hot"; "", the rest without the parts and the hot fields; "#", its keys joined by "|";
//   "#n", the parts' size). Then, unless full, each entry not kept against its last codes: a new one whole, a changed one
//   as its changed parts ("_p", and "_gone" for keys it no longer has). Returns list(codes with "#order", the refs in
//   order, the places of the units whose hot row isn't as last sent, the codes' size for the full model, the changed
//   entries or null, their size); null for anything it doesn't expect, and the DM does it as before. 200 units: ~2.7 ms
//   of DM a send, ~40 entries encoded again each time (a changed key, or the 3 s refresh) at ~50-100 us each.
// Kept codes (10-31, the owner: "Yes, do it", the HUD unit list keeping unchanged parts' encoded text): at 100 players
// 88% of the parts encoded again came out as before (an entry is made again whenever its status line moves), and the rest
// part, 70% of the bytes, changed only in a few small fields. So each unit (by its ref) keeps, for each part and each of
// the rest's fields, a snapshot of what was encoded and its code: a value the same as its snapshot (numbers to the bit,
// text, type paths, plain lists of those in the same order and shape) takes the kept code, and the rest is put together
// from its fields' codes as the encoder writes an object. Anything else (an object, whose text is its name; a special
// list; a list nested past 16) is encoded as before. RM_HUD_KEEP=0: off; RM_HUD_KEEP_VERIFY=1: every kept code and every
// rest put together is checked against the encoder's own, counted in the server log every 10 s.
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmHud {
    // the engine's own encoder (DreamProcNativeRoot.JsonEncode, private), so every part is what json_encode makes of it
    private static readonly System.Action<Utf8JsonWriter, DreamValue>? Encode = MakeEncode();
    private static readonly JsonWriterOptions Options = new() {
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,   // as json_encode: "\"" not """
        Indented = false
    };
    private static readonly DreamValue KRef = new("ref"), KKept = new("#r"), KHot = new("hot"), KSize = new("#n"),
        KRest = new(""), KKeys = new("#"), KOrder = new("#order"), KPart = new("_p"), KGone = new("_gone");

    private static System.Action<Utf8JsonWriter, DreamValue>? MakeEncode() {
        var m = typeof(DreamProcNativeRoot).GetMethod("JsonEncode", BindingFlags.NonPublic | BindingFlags.Static,
            null, new[] { typeof(Utf8JsonWriter), typeof(DreamValue) }, null);
        return m == null ? null : (System.Action<Utf8JsonWriter, DreamValue>)m.CreateDelegate(typeof(System.Action<Utf8JsonWriter, DreamValue>));
    }

    private sealed class Json {
        private readonly MemoryStream _stream = new();
        private readonly Utf8JsonWriter _writer;
        public Json() { _writer = new Utf8JsonWriter(_stream, Options); }

        public string Of(DreamValue value) {
            _stream.SetLength(0);
            _writer.Reset(_stream);
            Encode!(_writer, value);
            _writer.Flush();
            return Encoding.UTF8.GetString(_stream.GetBuffer(), 0, (int)_stream.Length);
        }

        // a key as the encoder writes it before its value (WritePropertyName: escaped as a text value, no formatting taken out)
        public string Name(string key) {
            _stream.SetLength(0);
            _writer.Reset(_stream);
            _writer.WriteStringValue(key);
            _writer.Flush();
            return Encoding.UTF8.GetString(_stream.GetBuffer(), 0, (int)_stream.Length) + ":";
        }
    }

    // --- kept codes -------------------------------------------------------------------------------------------------------
    private static readonly bool KeepOn = Environment.GetEnvironmentVariable("RM_HUD_KEEP") != "0";
    private static readonly bool KeepVerify = Environment.GetEnvironmentVariable("RM_HUD_KEEP_VERIFY") == "1";
    private static long _verN, _verBad;
    private static DateTime _verAt = DateTime.UtcNow;
    private const int KeptMax = 50000;   // units kept for; past it all are let go (deleted units' refs, many players)

    private sealed class Kept {
        public readonly object Snap;
        public readonly string Code;
        public Kept(object snap, string code) { Snap = snap; Code = code; }
    }
    private sealed class ListSnap {
        public bool Assoc;
        public object[] Keys = [];
        public object?[]? Vals;   // an associative list's values by place; null: that key has none (the encoder writes null)
    }
    private static readonly object NullSnap = new();
    private static readonly Dictionary<string, Dictionary<string, Kept>> _kept = new();
    private static readonly Dictionary<string, string> _names = new();

    private static Dictionary<string, Kept> KeptFor(string unit) {
        if (_kept.TryGetValue(unit, out var k)) return k;
        if (_kept.Count >= KeptMax) _kept.Clear();
        return _kept[unit] = new Dictionary<string, Kept>();
    }

    // what the encoder reads of a value, or null when it reads more (an object's name, a special list's own rules)
    private static object? Snap(DreamValue v, int depth) {
        if (depth > 16) return null;
        if (v.IsNull) return NullSnap;
        if (v.TryGetValueAsFloat(out var f)) return f;
        if (v.TryGetValueAsString(out var s)) return s;
        if (v.TryGetValueAsType(out var t)) return t;
        if (!v.TryGetValueAsDreamList(out var L) || L == null || L.GetType() != typeof(DreamList)) return null;
        var assoc = L.IsAssociative;
        var keys = new List<object>();
        var vals = assoc ? new List<object?>() : null;
        foreach (var e in L.EnumerateValues()) {
            var ks = Snap(e, depth + 1);
            if (ks == null) return null;
            if (assoc) {
                if (ks is not (string or float)) return null;   // the encoder Stringifies a key: only these to the letter
                if (L.ContainsKey(e)) {
                    using var sv = L.GetValue(e);
                    var vs = Snap(sv, depth + 1);
                    if (vs == null) return null;
                    vals!.Add(vs);
                } else vals!.Add(null);
            }
            keys.Add(ks);
        }
        return new ListSnap { Assoc = assoc, Keys = keys.ToArray(), Vals = vals?.ToArray() };
    }

    private static bool Same(DreamValue v, object snap) {
        switch (snap) {
            case float f:
                return v.TryGetValueAsFloat(out var g) && BitConverter.SingleToInt32Bits(f) == BitConverter.SingleToInt32Bits(g);
            case string s:
                return v.TryGetValueAsString(out var t) && string.Equals(s, t, StringComparison.Ordinal);
            case ListSnap ls: {
                if (!v.TryGetValueAsDreamList(out var L) || L == null || L.GetType() != typeof(DreamList) ||
                    L.IsAssociative != ls.Assoc || L.GetLength() != ls.Keys.Length) return false;
                var i = 0;
                foreach (var e in L.EnumerateValues()) {
                    if (i >= ls.Keys.Length || !Same(e, ls.Keys[i])) return false;
                    if (ls.Assoc) {
                        var want = ls.Vals![i];
                        if (L.ContainsKey(e)) {
                            if (want == null) return false;
                            using var sv = L.GetValue(e);
                            if (!Same(sv, want)) return false;
                        } else if (want != null) return false;
                    }
                    i++;
                }
                return i == ls.Keys.Length;
            }
            default:
                if (ReferenceEquals(snap, NullSnap)) return v.IsNull;
                return v.TryGetValueAsType(out var ty) && ReferenceEquals(ty, snap);
        }
    }

    // a part's code: the kept one while its value is as encoded, else encoded (and kept when it can be)
    private static string KeptCode(Dictionary<string, Kept> kept, string key, DreamValue v, Json json) {
        if (kept.TryGetValue(key, out var k) && Same(v, k.Snap)) {
            if (KeepVerify) Check(k.Code, json.Of(v), key);
            return k.Code;
        }
        var code = json.Of(v);
        var snap = Snap(v, 0);
        if (snap != null) kept[key] = new Kept(snap, code);
        else kept.Remove(key);
        return code;
    }

    // the rest part put together from its fields' codes as the encoder writes an object ({"k":v,...}), or null: encode it
    // whole (a key with no value, a special list, a list it can't keep)
    private static string? RestCode(Dictionary<string, Kept> kept, List<DreamValue> keys, Dictionary<DreamValue, DreamValue>? assoc,
        Json json, StringBuilder sb) {
        if (assoc == null || assoc.Count != keys.Count || keys.Count == 0) return null;
        sb.Clear();
        sb.Append('{');
        for (var i = 0; i < keys.Count; i++) {
            var ks = keys[i].MustGetValueAsString();
            var code = FieldCode(kept, ks, assoc[keys[i]], json);
            if (code == null) return null;
            if (!_names.TryGetValue(ks, out var name)) _names[ks] = name = json.Name(ks);
            if (i > 0) sb.Append(',');
            sb.Append(name).Append(code);
        }
        sb.Append('}');
        return sb.ToString();
    }

    // one of the rest's fields: as KeptCode, a level down (it sits inside the rest object), or null for a list it can't
    // keep (a special list skips or reads its own way; one nested deep meets the encoder's depth limit a level sooner)
    private static string? FieldCode(Dictionary<string, Kept> kept, string key, DreamValue v, Json json) {
        if (kept.TryGetValue(key, out var k) && Same(v, k.Snap)) {
            if (KeepVerify) Check(k.Code, json.Of(v), key);
            return k.Code;
        }
        var isList = v.TryGetValueAsDreamList(out var L) && L != null;
        if (isList && L!.GetType() != typeof(DreamList)) return null;
        var snap = Snap(v, 1);
        if (snap == null && isList) return null;
        var code = json.Of(v);
        if (snap != null) kept[key] = new Kept(snap, code);
        else kept.Remove(key);
        return code;
    }

    private static void Check(string kept, string fresh, string what) {
        _verN++;
        if (kept != fresh) {
            _verBad++;
            if (_verBad <= 20) Logger.GetSawmill("opendream.rmhud").Info($"rmhud: kept code differs: {what}: kept {kept} fresh {fresh}");
        }
        var now = DateTime.UtcNow;
        if ((now - _verAt).TotalSeconds < 10) return;
        _verAt = now;
        Logger.GetSawmill("opendream.rmhud").Info($"rmhud: kept codes checked {_verN}, different {_verBad}");
    }

    // jointext(L, glue): each element Stringify'd (DreamProcNativeList Join)
    private static string Join(DreamList list, string glue) {
        var sb = new StringBuilder();
        var first = true;
        foreach (var v in list.EnumerateValues()) {
            if (!first) sb.Append(glue);
            sb.Append(v.Stringify());
            first = false;
        }
        return sb.ToString();
    }

    private static string? Text(DreamList list, DreamValue key) {
        using var v = list.GetValue(key);
        return v.TryGetValueAsString(out var s) ? s : null;
    }

    [DreamProc("rm_hud_units")]
    [DreamProcParameter("units")]
    [DreamProcParameter("old")]
    [DreamProcParameter("parts")]
    [DreamProcParameter("hot")]
    [DreamProcParameter("full")]
    public static DreamValue NativeProc_rm_hud_units(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (Encode == null ||
            !bundle.GetArgument(0, "units").TryGetValueAsDreamList(out var units) || units == null ||
            !bundle.GetArgument(2, "parts").TryGetValueAsDreamList(out var parts) || parts == null ||
            !bundle.GetArgument(3, "hot").TryGetValueAsDreamList(out var hotKeys) || hotKeys == null)
            return DreamValue.Null;
        var full = bundle.GetArgument(4, "full").IsTruthy();
        var oldArg = bundle.GetArgument(1, "old");
        DreamList? old = null;
        if (!oldArg.IsNull && (!oldArg.TryGetValueAsDreamList(out old) || old == null)) return DreamValue.Null;
        if (units.GetType() != typeof(DreamList) || parts.GetType() != typeof(DreamList) || hotKeys.GetType() != typeof(DreamList) ||
            (old != null && old.GetType() != typeof(DreamList)))
            return DreamValue.Null;   // a special list (vars, contents...): the DM does it
        if (!full && old == null) return DreamValue.Null;   // the DM would read an old list it hasn't got

        // the parts and the hot fields: names, each part's value true (rm_hud_unit_parts[f], as the DM reads it)
        var partKeys = new List<DreamValue>();
        var partSet = new HashSet<string>();
        foreach (var k in parts.EnumerateValues()) {
            if (!k.TryGetValueAsString(out var s)) return DreamValue.Null;
            using (var pv = parts.GetValue(k)) if (!pv.IsTruthy()) return DreamValue.Null;
            partKeys.Add(k);
            partSet.Add(s);
        }
        var hotList = new List<DreamValue>();
        var hotSet = new HashSet<string>();
        foreach (var k in hotKeys.EnumerateValues()) {
            if (!k.TryGetValueAsString(out var s)) return DreamValue.Null;
            hotList.Add(k);
            hotSet.Add(s);
        }
        // the entries: plain lists with a text ref; a kept one (its "#r" and last codes with a size) has only those read, any
        // other each key a text and there once, its last codes plain lists of texts with a number size and their keys as text
        var entries = new List<DreamList>();
        var seen = new HashSet<string>();
        foreach (var v in units.EnumerateValues()) {
            if (!v.TryGetValueAsDreamList(out var U) || U == null) continue;   // for(var/list/U in units)
            if (U.GetType() != typeof(DreamList)) return DreamValue.Null;
            using var r = U.GetValue(KRef);
            if (!r.TryGetValueAsString(out _)) return DreamValue.Null;
            bool reused;
            using (var rv = U.GetValue(KKept)) reused = rv.IsTruthy();
            using var was = old != null ? old.GetValue(r) : DreamValue.Null;
            DreamList? wl = null;
            if (!was.IsNull && (!was.TryGetValueAsDreamList(out wl) || wl == null || wl.GetType() != typeof(DreamList))) return DreamValue.Null;
            if (wl != null) {
                using var wn = wl.GetValue(KSize);
                if (!wn.IsNull && !wn.TryGetValueAsFloat(out _)) return DreamValue.Null;   // a size that isn't a number
                if (reused && wn.IsTruthy()) {
                    entries.Add(U);   // kept: its codes as they are
                    continue;
                }
                foreach (var k in wl.EnumerateValues())
                    if (!k.TryGetValueAsString(out _)) return DreamValue.Null;
                if (Text(wl, KKeys) == null) return DreamValue.Null;
            }
            seen.Clear();
            foreach (var k in U.EnumerateValues())
                if (!k.TryGetValueAsString(out var s) || !seen.Add(s)) return DreamValue.Null;
            entries.Add(U);
        }

        var tree = bundle.ObjectTree;
        var codes = tree.CreateList();
        var order = tree.CreateList();
        var moved = tree.CreateList();
        float fullBytes = 0;   // DM's numbers: adds as the DM did, in its order
        var json = new Json();
        var sb = new StringBuilder();
        var partVals = new Dictionary<string, DreamValue>();
        var nullParts = new List<DreamValue>();
        var i = 0;
        foreach (var U in entries) {
            i++;
            using var r = U.GetValue(KRef);
            order.AddValue(r);
            sb.Clear();
            for (var h = 0; h < hotList.Count; h++) {
                if (h > 0) sb.Append(',');
                using var hv = U.GetValue(hotList[h]);
                sb.Append(hv.Stringify());
            }
            var hot = sb.ToString();
            bool reused;
            using (var rv = U.GetValue(KKept)) reused = rv.IsTruthy();
            if (reused) U.RemoveValue(KKept);
            using var wasV = old != null ? old.GetValue(r) : DreamValue.Null;
            wasV.TryGetValueAsDreamList(out var was);
            var same = false;
            if (was != null) {
                same = Text(was, KHot) == hot;
                if (!same) moved.AddValue(new DreamValue(i));
            }
            if (reused && was != null) {
                using var wn = was.GetValue(KSize);
                if (wn.IsTruthy()) {
                    // the last send's codes list itself, its hot row rewritten
                    if (!same) was.SetValue(KHot, new DreamValue(hot));
                    codes.SetValue(r, wasV);
                    wn.TryGetValueAsFloat(out var n);
                    fullBytes += n;
                    continue;
                }
            }
            // one look at its keys: its parts (a null one comes out of the entry), the hot fields, the rest in order
            partVals.Clear();
            nullParts.Clear();
            var restKeys = new List<DreamValue>();
            Dictionary<DreamValue, DreamValue>? restAssoc = null;
            foreach (var k in U.EnumerateValues()) {
                var s = k.MustGetValueAsString();
                if (partSet.Contains(s)) {
                    var pv = U.GetValue(k);   // held until it is encoded below
                    if (pv.IsNull) nullParts.Add(k);
                    else partVals[s] = pv;
                    continue;
                }
                if (hotSet.Contains(s)) continue;
                restKeys.Add(k);
                if (U.ContainsKey(k)) {
                    using var rv = U.GetValue(k);
                    (restAssoc ??= new Dictionary<DreamValue, DreamValue>())[k] = rv;   // the list below counts its own
                }
            }
            var C = tree.CreateList();
            float nb = 0;
            var kept = KeepOn ? KeptFor(r.MustGetValueAsString()) : null;
            foreach (var k in partKeys) {   // in rm_hud_unit_parts' order
                var ks = k.MustGetValueAsString();
                if (!partVals.TryGetValue(ks, out var pv)) continue;
                var code = kept != null ? KeptCode(kept, ks, pv, json) : json.Of(pv);
                pv.Dispose();
                C.SetValue(k, new DreamValue(code));
                fullBytes += code.Length;
                nb += code.Length;
            }
            foreach (var k in nullParts) U.RemoveValue(k);
            C.SetValue(KHot, new DreamValue(hot));
            // the rest put together from its fields' kept codes; the list itself made and encoded only when it can't be (or
            // to check it)
            var restCode = kept != null ? RestCode(kept, restKeys, restAssoc, json, sb) : null;
            if (restCode == null || KeepVerify) {
                var rest = new DreamList(U.ObjectDefinition, restKeys, restAssoc);   // as U.Copy() less those keys
                using var restV = new DreamValue(rest);
                var whole = json.Of(restV);
                if (restCode == null) restCode = whole;
                else Check(restCode, whole, "(rest)");
            }
            C.SetValue(KRest, new DreamValue(restCode));
            C.SetValue(KKeys, new DreamValue(Join(U, "|")));
            fullBytes += restCode.Length;
            nb += restCode.Length;
            C.SetValue(KSize, new DreamValue(System.Math.Max(1f, nb)));
            using (var cv = new DreamValue(C)) codes.SetValue(r, cv);   // the codes hold it; this proc lets go
        }
        codes.SetValue(KOrder, new DreamValue(Join(order, "|")));

        // against the last send (RemasterHUDUnitsDelta's comparison)
        DreamList? changed = null;
        float bytes = 0;
        if (!full) {
            changed = tree.CreateList();
            foreach (var U in entries) {
                using var r = U.GetValue(KRef);
                using var cV = codes.GetValue(r);
                using var oV = old!.GetValue(r);
                cV.TryGetValueAsDreamList(out var C);
                oV.TryGetValueAsDreamList(out var O);
                if (O != null && ReferenceEquals(C, O)) continue;   // a kept entry: the last send's own codes
                if (O == null) {
                    changed.AddValue(new DreamValue(U));
                    foreach (var k in C!.EnumerateValues()) {
                        if (k.MustGetValueAsString() == "#n") continue;
                        bytes += Text(C, k)?.Length ?? 0;
                    }
                    continue;
                }
                DreamList? P = null;
                foreach (var k in C!.EnumerateValues()) {
                    var s = k.MustGetValueAsString();
                    if (s == "#" || s == "hot" || s == "#n") continue;
                    var code = Text(C, k);
                    if (code == Text(O, k)) continue;
                    P ??= Partial(tree, r);
                    bytes += code?.Length ?? 0;
                    if (s == "") {
                        foreach (var f in U.EnumerateValues()) {
                            var fs = f.MustGetValueAsString();
                            if (partSet.Contains(fs) || hotSet.Contains(fs)) continue;
                            using var fv = U.GetValue(f);
                            P.SetValue(f, fv);
                        }
                    } else {
                        using var kv = U.GetValue(k);
                        P.SetValue(k, kv);
                    }
                }
                var newKeys = Text(C, KKeys)!;
                var oldKeys = Text(O, KKeys)!;
                if (newKeys != oldKeys) {
                    // splittext(old, "|") - splittext(new, "|"): each of the new keys takes one of the old off (the last)
                    var gone = new List<string>(oldKeys.Split('|'));
                    foreach (var k in newKeys.Split('|')) {
                        var at = gone.LastIndexOf(k);
                        if (at >= 0) gone.RemoveAt(at);
                    }
                    if (gone.Count > 0) {
                        P ??= Partial(tree, r);
                        var G = tree.CreateList();
                        foreach (var g in gone) G.AddValue(new DreamValue(g));
                        using (var gv = new DreamValue(G)) P.SetValue(KGone, gv);
                    }
                }
                if (P != null)
                    using (var pv = new DreamValue(P)) changed.AddValue(pv);
            }
        }

        var result = tree.CreateList();
        using (var v = new DreamValue(codes)) result.AddValue(v);   // the result holds them; this proc lets go
        using (var v = new DreamValue(order)) result.AddValue(v);
        using (var v = new DreamValue(moved)) result.AddValue(v);
        result.AddValue(new DreamValue(fullBytes));
        if (changed != null)
            using (var v = new DreamValue(changed)) result.AddValue(v);
        else result.AddValue(DreamValue.Null);
        result.AddValue(new DreamValue(bytes));
        return new DreamValue(result);   // the caller takes this proc's reference (as RmRange's list)
    }

    // list("ref"=r, "_p"=1): a changed entry's start
    private static DreamList Partial(DreamObjectTree tree, DreamValue r) {
        var P = tree.CreateList();
        P.SetValue(KRef, r);
        P.SetValue(KPart, new DreamValue(1));
        return P;
    }
}
