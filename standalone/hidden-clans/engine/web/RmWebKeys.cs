// Remastered: a web player's keys (engine/web/, U4). The skin's macros (the interface file's first macro set, or
// RM_WEB_MACROS), read on the server with the parser the client uses, become a key table: the page sends a key that has
// a macro ("G", "CTRL+1", "NORTH"), and the server runs its command (ServerVerbSystem.RmRunCommand).
//   down: the macros for that key whose modifiers are all held, the ones with the most modifiers (Shift+A with no
//         SHIFT+A macro runs A's, as the native input does); a +REP one runs then and every tick until the key comes up
//   up:   the +UP macros chosen the same way
// Client-side commands (.winset, .options, .screenshot...) and ANY macros have nothing to do on the web yet: skipped.
using System.Linq;
using OpenDreamRuntime.Resources;
using OpenDreamShared.Interface.DMF;
using Robust.Shared.Serialization.Manager;

namespace OpenDreamRuntime;

internal sealed class RmWebKeys {
    public const int Shift = 1, Ctrl = 2, Alt = 4;

    public sealed record Macro(string Key, int Mods, bool Up, bool Rep, string Command);

    public readonly List<Macro> Macros = new();
    public readonly string[] KeyList;   // for the page: "MODS|KEY" of every down macro, so it knows which keys are the game's
    public readonly string Note;

    // the key names a macro may use (OpenDream's ParsedKeybind), which are the names the page sends
    private static readonly HashSet<string> Names = new(
        Enumerable.Range('A', 26).Select(c => ((char)c).ToString())
        .Concat(Enumerable.Range(0, 10).Select(n => n.ToString()))
        .Concat(Enumerable.Range(1, 15).Select(n => "F" + n))
        .Concat(Enumerable.Range(0, 10).Select(n => "NUMPAD" + n))
        .Concat(new[] { "NORTH", "SOUTH", "EAST", "WEST", "NORTHWEST", "SOUTHWEST", "NORTHEAST", "SOUTHEAST", "RETURN", "ESCAPE",
            "TAB", "SPACE", "BACK", "INSERT", "DELETE", "PAUSE", "MULTIPLY", "ADD", "SUBTRACT", "DIVIDE", ";", ",", ".", "`",
            "SHIFT", "CTRL", "ALT" }));

    public RmWebKeys(DreamResourceManager resources, ISerializationManager serialization) {
        var source = resources.InterfaceFile?.ReadAsString();
        if (source == null) {
            KeyList = Array.Empty<string>();
            Note = "no interface file: no keys";
            return;
        }

        var parser = new DMFParser(new DMFLexer(source), serialization);
        var descriptor = parser.Interface();
        var wanted = Environment.GetEnvironmentVariable("RM_WEB_MACROS");
        var set = descriptor.MacroSetDescriptors.FirstOrDefault(s => wanted == null || s.Id.AsRaw() == wanted);
        var skipped = 0;
        if (set != null) {
            foreach (var macro in set.Macros) {
                if (Parse(macro.Name.AsRaw(), macro.Command) is { } parsed) Macros.Add(parsed);
                else skipped++;
            }
        }

        KeyList = Macros.Where(m => !m.Up).Select(m => $"{m.Mods}|{m.Key}").Distinct().ToArray();
        Note = set == null ? "no macro set: no keys" : $"{Macros.Count} macros from \"{set.Id.AsRaw()}\" ({skipped} not for the web)";
    }

    private static Macro? Parse(string name, string? command) {
        if (string.IsNullOrWhiteSpace(command) || command.TrimStart().StartsWith('.'))
            return null;   // nothing to run, or a client-side command
        var parts = name.ToUpperInvariant().Split('+');
        string? key = null;
        int mods = 0;
        bool up = false, rep = false;
        foreach (var part in parts) {
            switch (part) {
                case "UP": up = true; break;
                case "REP": rep = true; break;
                case "SHIFT": mods |= Shift; break;
                case "CTRL": mods |= Ctrl; break;
                case "ALT": mods |= Alt; break;
                default:
                    if (key != null || !Names.Contains(part)) return null;   // ANY, or a name the page never sends
                    key = part;
                    break;
            }
        }

        if (key == null) {   // a lone modifier is the key itself ("SHIFT")
            if (parts.Length != 1 || !Names.Contains(parts[0])) return null;
            key = parts[0];
            mods = 0;
        }

        return up && rep ? null : new Macro(key, mods, up, rep, command.Trim());
    }

    /// <summary>The macros a key press (or release) runs: of those for this key whose modifiers are all held, the most specific.</summary>
    public List<Macro> For(string key, int held, bool up) {
        var fits = Macros.Where(m => m.Key == key && m.Up == up && (m.Mods & ~held) == 0).ToList();
        if (fits.Count == 0) return fits;
        var most = fits.Max(m => System.Numerics.BitOperations.PopCount((uint)m.Mods));
        return fits.Where(m => System.Numerics.BitOperations.PopCount((uint)m.Mods) == most).ToList();
    }
}
