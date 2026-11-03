// Remastered: a web player's keys (engine/web/, U4 of planning/SERVER_UPGRADES_PLAN_2026-10-30.md). A native client
// turns a key into its skin macro's command and asks the server to run that verb (DreamInterfaceManager.RunCommand). A
// browser has no skin, so the server runs the command itself, with the same steps: the verb found by its command name
// among the player's client and mob verbs, the arguments parsed as the client parses them, and CanExecute.
using System.Globalization;
using System.Text;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Procs;
using OpenDreamShared.Dream;

namespace OpenDreamRuntime;

public sealed partial class ServerVerbSystem {
    /// <summary>Runs a command line ("Quick 1 \"Select\"") for a connection. Null when it ran, else why it didn't.</summary>
    internal string? RmRunCommand(DreamConnection connection, string command) {
        if (connection.Client == null || connection.Mob == null)
            return "no mob";

        var split = command.Split(' ', 2, StringSplitOptions.TrimEntries);
        var name = split[0].ToLowerInvariant();   // case-insensitive, as the client
        DreamProc? verb = null;
        DreamObject? src = null;

        foreach (var clientVerb in connection.Client.ClientVerbs.Verbs) {
            if (clientVerb.VerbId == null)
                RegisterVerb(clientVerb);
            if (_verbs[clientVerb.VerbId!.Value].GetCommandName() == name) {
                verb = clientVerb;
                src = connection.Client;
                break;
            }
        }

        if (verb == null) {
            foreach (var verbId in _atomManager.MustGetAppearance(connection.Mob).Verbs) {
                if (verbId < _verbs.Count && _verbs[verbId].GetCommandName() == name) {
                    verb = _verbIdToProc[verbId];
                    src = connection.Mob;
                    break;
                }
            }
        }

        if (verb == null || src == null)
            return "no such verb";
        if (!CanExecute(connection, src, verb))
            return "not allowed";

        var args = RmSplitArguments(split.Length > 1 ? split[1] : "");
        var count = verb.ArgumentTypes?.Count ?? 0;
        if (args.Count != count)   // the client would prompt for missing ones; macros give them all
            return $"{args.Count} argument(s) for {count}";

        var values = new DreamValue[count];
        for (var i = 0; i < count; i++) {
            var type = verb.ArgumentTypes![i];
            object? raw = args[i];
            if ((type & DreamValueType.Num) != 0 && (type & (DreamValueType.Text | DreamValueType.Message | DreamValueType.CommandText)) == 0)
                raw = float.TryParse(args[i], NumberStyles.Float, CultureInfo.InvariantCulture, out var number) ? number : null;
            if (raw == null || !connection.TryConvertPromptResponse(type, raw, out values[i]))
                return $"argument {i + 1} \"{args[i]}\" is not a {type}";
        }

        RunVerb(verb, $"command {name}", src, connection, values);
        return null;
    }

    /// <summary>Arguments as the client splits them: by spaces, a "quoted" one kept whole.</summary>
    private static List<string> RmSplitArguments(string text) {
        var args = new List<string>();
        var current = new StringBuilder();
        var quoted = false;
        foreach (var c in text) {
            if (c == '"') {
                if (quoted) {
                    args.Add(current.ToString());
                    current.Clear();
                }

                quoted = !quoted;
                continue;
            }

            if (c == ' ' && !quoted) {
                if (current.Length > 0) args.Add(current.ToString());
                current.Clear();
                continue;
            }

            current.Append(c);
        }

        if (current.Length > 0)
            args.Add(current.ToString());
        return args;
    }
}
