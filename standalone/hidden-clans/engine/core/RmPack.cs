// The HUD's sends packed (server cost, 2026-10-24; game/Code/Remastered/HudPack.dm): rm_pack(text) returns the text as
// UTF-8, raw deflate (RFC 1951), base64url without padding, which the page unpacks (game/Interface/hudpack.js). A full
// model of 200 selected units is ~400 KB of JSON, the same field names over and over; packed it is a few KB. Bound only
// where the game declares rm_pack; its DM body returns null, and the game then sends the plain text.
using System.IO;
using System.IO.Compression;
using System.Text;
using OpenDreamRuntime.Objects;
using DreamValueTypeFlag = OpenDreamRuntime.DreamValue.DreamValueTypeFlag;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmPack {
    [DreamProc("rm_pack")]
    [DreamProcParameter("text", Type = DreamValueTypeFlag.String)]
    public static DreamValue NativeProc_rm_pack(NativeProc.Bundle bundle, DreamObject? src, DreamObject? usr) {
        if (!bundle.GetArgument(0, "text").TryGetValueAsString(out var text)) return DreamValue.Null;
        var bytes = Encoding.UTF8.GetBytes(text);
        using var packed = new MemoryStream(bytes.Length / 6 + 64);
        using (var deflate = new DeflateStream(packed, CompressionLevel.Optimal, leaveOpen: true)) deflate.Write(bytes, 0, bytes.Length);
        var b64 = Convert.ToBase64String(packed.GetBuffer(), 0, (int)packed.Length);
        var sb = new StringBuilder(b64.Length);
        foreach (var c in b64) {
            if (c == '=') break;
            sb.Append(c == '+' ? '-' : c == '/' ? '_' : c);
        }
        return new DreamValue(sb.ToString());
    }
}
