// RmChat (v11 candidate = v10 + this, server cost, 2026-10-25; the hidden-2D audit's (a2), reports/server-cost/hidden-2d-audit.md):
// a text line for a client goes to the HUD's chat by the page's own channel, not into the hidden output control that the
// chat relay copied it out of. DreamConnection.OutputDreamValue asks Route first (the CHAT patch in build_chat.py): every
// `<<` of text to a player ends there (a mob, a client, world, lists and view()); output(x, "control") doesn't.
//   RM_CHAT_ROUTE unset: the route (1) when the game declares RemasterChatKeep (Remastered/Chat.dm), else as before (0).
//   0: as before (the output control, the relay): the off switch.
//   1: the route only. The line is made plain exactly as the client's output control makes it (OpenDreamClient's
//      HtmlParser into a FormattedMessage, its ToString(), then trimmed and blank ones skipped, as the relay did), asked
//      of DM's RemasterChatKeep (Remastered/Chat.dm; 0 drops it), and sent as output(line, "mapwindow.hud:remasterChatLine").
//   2: shadow. Both go: the old path as before, and the route to "mapwindow.hud:remasterChatShadow" (the page records it
//      and shows nothing). Each line is logged, RMCHAT|key|seq|keep|line, to compare with what the relay copied.
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using OpenDreamRuntime.Objects;
using OpenDreamRuntime.Objects.Types;

namespace OpenDreamRuntime.Procs.Native;

internal static class RmChat {
    private static readonly string? Env = System.Environment.GetEnvironmentVariable("RM_CHAT_ROUTE");
    private static string? _mode;   // settled on the first line, when the game's procs are known
    private static DreamProc? _keep;
    private static string Mode => _mode ?? "0";
    private static long _seq;
    private static readonly Regex Attr = new(@"[^ =]+(?:=(?:\w+|""[^""]*""|'[^']*'))?");   // the client parser's
    private static readonly string[] Void = { "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr" };

    // true: the line has been dealt with here and the old path is skipped.
    public static bool Route(DreamConnection connection, string message, DreamObjectTree tree, DreamObject world) {
        if (_mode == null) {
            tree.TryGetGlobalProc("RemasterChatKeep", out _keep);
            _mode = Env is "0" or "1" or "2" ? Env : _keep != null ? "1" : "0";
            System.Console.WriteLine($"RmChat: {(_mode == "0" ? "old path (output control)" : _mode == "1" ? "route on" : "shadow")}, RM_CHAT_ROUTE {Env ?? "unset"}, RemasterChatKeep {(_keep != null ? "declared" : "not declared")}");
        }
        if (Mode != "1" && Mode != "2") return false;
        var line = Plain(message);
        if (string.IsNullOrWhiteSpace(line)) return Mode == "1";
        line = line.Trim();
        var keep = true;
        if (_keep != null) {
            using var r = DreamThread.Run(_keep, world, null, new DreamValue(line));
            keep = r.IsTruthy();
        }
        if (Mode == "2") System.Console.WriteLine($"RMCHAT|{connection.Key}|{++_seq}|{(keep ? 1 : 0)}|{line.Replace('\n', '\u2028')}");
        if (keep) connection.OutputControl(System.Uri.EscapeDataString(line), Mode == "2" ? "mapwindow.hud:remasterChatShadow" : "mapwindow.hud:remasterChatLine");
        return Mode == "1";
    }

    // The text a line shows as in the client's output control: OpenDreamClient/Interface/Html/HtmlParser.Parse, step for
    // step, keeping only what FormattedMessage.ToString() keeps (text, and "\n" for <br> and newlines). Where the client's
    // parser stops at a bad tag, this stops too.
    public static string Plain(string text) {
        text = text.Replace("\t", "    ");   // ControlOutput.Output
        var sb = new StringBuilder();
        var tags = new System.Collections.Generic.Stack<string>();
        for (var i = 0; i < text.Length; i++) {
            var c = text[i];
            switch (c) {
                case '<': {
                    i++;
                    while (i < text.Length && char.IsWhiteSpace(text[i])) i++;
                    if (i >= text.Length) return sb.ToString();
                    var closing = text[i] == '/';
                    if (closing) i++;
                    var inside = new StringBuilder();
                    var d = '\0';
                    while (i < text.Length) {
                        d = text[i];
                        if (d == '>') break;
                        inside.Append(d);
                        i++;
                    }
                    if (d != '>') return sb.ToString();
                    var attributes = Attr.Matches(inside.ToString()).Where(x => x.Length > 0).Select(x => x.Value).ToArray();
                    if (attributes.Length == 0) return sb.ToString();
                    var tagType = attributes[0].ToLowerInvariant();
                    var self = tagType.EndsWith("/") || attributes[^1].EndsWith("/") || Void.Contains(tagType);
                    tagType = tagType.TrimEnd('/');
                    if (closing) {
                        if (self || tags.Count == 0 || tags.Peek() != tagType) return sb.ToString();
                        tags.Pop();
                    } else {
                        if (tagType == "!--") {
                            while (i < text.Length && (i - 2 < 0 || text[i - 2] != '-' || text[i - 1] != '-' || text[i] != '>') && text.Length > 2) i++;
                            continue;
                        }
                        if (!self) tags.Push(tagType);
                        if (tagType == "br") sb.Append('\n');
                    }
                    break;
                }
                case '&': {
                    var end = text.IndexOf(';', i);
                    if (end == -1) break;   // the client's parser drops a lone '&'
                    var ent = text.Substring(i + 1, end - (i + 1));
                    i = end;
                    if (ent.StartsWith('#')) {
                        if (int.TryParse(ent.Substring(1), out var n)) sb.Append((char)n);
                    } else sb.Append(ent switch {
                        "nbsp" => "\u00A0", "lt" => "<", "gt" => ">", "amp" => "&", "quot" => "\"", "apos" => "'",
                        "cent" => "\u00A2", "pound" => "\u00A3", "yen" => "\u00A5", "euro" => "\u20AC", "copyright" => "\u00A9", "trademark" => "\u00AE",
                        _ => "&" + ent + ";"
                    });
                    break;
                }
                case '\n':
                    sb.Append('\n');
                    break;
                default:
                    if (c == OpenDreamShared.Dream.StringFormatting.Icon) { i += 2; break; }   // an icon: no text
                    sb.Append(c);
                    break;
            }
        }
        return sb.ToString();
    }
}
