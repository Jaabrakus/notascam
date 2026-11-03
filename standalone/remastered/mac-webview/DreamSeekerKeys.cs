// Dream Seeker keyboard routing for the skin's command input. While that input
// has focus, text keys type into it but other keys (arrows, numpad, function
// keys, Ctrl/Alt chords) still reach the macro set, so arrow keys keep moving
// the player. Robust otherwise withholds every key binding from a focused
// LineEdit. Prompt windows (input()/alert()) keep the keyboard to themselves.
using System;
using Robust.Client.Input;
using Robust.Client.UserInterface;
using Robust.Client.UserInterface.Controls;
using Robust.Shared.IoC;
using Key = Robust.Client.Input.Keyboard.Key;

namespace Robust.Client.WebView;

internal static class DreamSeekerKeys {
    private static bool _installed;
    private static LineEdit? _restore;
    private static Key _releasedFor;
    private static bool _restorePending;

    public static void Update() {
        if (!_installed) {
            _installed = true;
            IoCManager.Resolve<IInputManager>().FirstChanceOnKeyEvent += OnKey;
        }
        if (!_restorePending || _restore == null) return;
        var ui = IoCManager.Resolve<IUserInterfaceManager>();
        // Return focus once the key's own handlers ran, unless the player moved it.
        if (ui.KeyboardFocused == null && !_restore.Disposed && _restore.VisibleInTree) _restore.GrabKeyboardFocus();
        _restore = null;
        _restorePending = false;
    }

    private static void OnKey(KeyEventArgs args, KeyEventType type) {
        if (type == KeyEventType.Up && _restore != null && args.Key == _releasedFor) {
            _restorePending = true;
            return;
        }
        if (type != KeyEventType.Down) return;
        var ui = IoCManager.Resolve<IUserInterfaceManager>();
        if (ui.KeyboardFocused is not LineEdit edit || !IsSkinInput(edit) || IsTypingKey(args)) return;
        _restore = edit;
        _releasedFor = args.Key;
        _restorePending = false;
        ui.ReleaseKeyboardFocus();
    }

    private static bool IsSkinInput(Control control) {
        for (var node = control.Parent; node != null; node = node.Parent)
            if (node.GetType().Namespace?.EndsWith(".Prompts") == true) return false;
        return control.GetType() == typeof(LineEdit);
    }

    private static bool IsTypingKey(KeyEventArgs args) {
        if (args.Control || args.Alt || args.System) return false;
        var key = args.Key;
        return key is >= Key.A and <= Key.Z or >= Key.Num0 and <= Key.Num9 or Key.Space or Key.Minus or Key.Equal
            or Key.LBracket or Key.RBracket or Key.SemiColon or Key.Apostrophe or Key.Comma or Key.Period or Key.Slash
            or Key.BackSlash or Key.Tilde or Key.BackSpace or Key.Delete or Key.Return or Key.NumpadEnter or Key.Tab
            or Key.Shift or Key.Escape;
    }
}
