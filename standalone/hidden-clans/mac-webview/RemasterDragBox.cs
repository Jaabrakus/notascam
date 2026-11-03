// Dungeon Master Remastered: draw the selection box while the player drags on
// the map with the left button (the game selects the units on release through
// client/MouseDrop). Visual only; clicks and drags still go to the game as before.
using System.Linq;
using System.Numerics;
using Robust.Client.Graphics;
using Robust.Client.Input;
using Robust.Client.UserInterface;
using Robust.Shared.IoC;
using Robust.Shared.Map;
using Robust.Shared.Maths;
using Key = Robust.Client.Input.Keyboard.Key;

namespace Robust.Client.WebView;

internal sealed class RemasterDragBox : Control {
    private const float StartDistance = 6f; // pixels before a press counts as a drag
    private static RemasterDragBox? _box;
    private static Control? _viewport;
    private static Vector2 _start;
    private static bool _pressed, _onMap;
    private Vector2 _from, _to;

    private RemasterDragBox() { MouseFilter = MouseFilterMode.Ignore; }

    protected internal override void Draw(DrawingHandleScreen handle) {
        var a = _from - GlobalPixelPosition;
        var b = _to - GlobalPixelPosition;
        var box = new UIBox2(Vector2.Min(a, b), Vector2.Max(a, b));
        handle.DrawRect(box, new Color(90, 255, 90, 45));
        handle.DrawRect(box, new Color(110, 255, 110, 235), false);
    }

    private static string _lastDebug = "";
    private static void DebugDragState(IInputManager input) {
        if (string.IsNullOrEmpty(System.Environment.GetEnvironmentVariable("DM_NATIVE_UI_PROBE"))) return;
        var systems = IoCManager.Resolve<Robust.Shared.GameObjects.IEntitySystemManager>();
        object? mouseSystem = null;
        foreach (var type in systems.GetEntitySystemTypes())
            if (type.FullName == "OpenDreamClient.Input.MouseInputSystem") { mouseSystem = systems.GetEntitySystem(type); break; }
        if (mouseSystem == null) return;
        const System.Reflection.BindingFlags all = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Public;
        var selected = mouseSystem.GetType().GetField("_selectedEntity", all)?.GetValue(mouseSystem);
        var isDrag = selected?.GetType().GetField("IsDrag", all)?.GetValue(selected);
        var initial = selected?.GetType().GetField("InitialMousePos", all)?.GetValue(selected);
        var text = selected == null ? "none" : $"selected drag={isDrag} initial={initial} now={input.MouseScreenPosition} left={input.IsKeyDown(Key.MouseLeft)}";
        if (text != _lastDebug) { _lastDebug = text; System.Console.WriteLine("[INFO] remaster.drag: " + text); }
    }

    public static void Update() {
        var input = IoCManager.Resolve<IInputManager>();
        DebugDragState(input);
        var mouse = input.MouseScreenPosition;
        var down = input.IsKeyDown(Key.MouseLeft);
        if (down && !_pressed) {
            _pressed = true;
            _start = mouse.Position;
            _viewport = FindMap(mouse);
            _onMap = _viewport != null;
        } else if (!down) {
            _pressed = false;
            _onMap = false;
            Hide();
            return;
        }
        if (!_onMap || _viewport == null || (mouse.Position - _start).Length() < StartDistance) return;
        var root = _viewport;
        while (root.Parent != null) root = root.Parent;
        if (_box == null) _box = new RemasterDragBox();
        if (_box.Parent != root) { _box.Orphan(); root.AddChild(_box); }
        _box.SetPositionLast();
        // Keep the box inside the map, like the game's selection area.
        var min = _viewport.GlobalPixelPosition;
        var max = min + _viewport.PixelSize;
        _box._from = Vector2.Clamp(_start, min, max);
        _box._to = Vector2.Clamp(mouse.Position, min, max);
        _box.Visible = true;
    }

    private static void Hide() {
        if (_box != null) _box.Visible = false;
    }

    private static Control? FindMap(ScreenCoordinates mouse) {
        var ui = IoCManager.Resolve<IUserInterfaceManager>();
        foreach (var root in ui.AllRoots) {
            if (root.Window == null || root.Window.Id != mouse.Window) continue;
            foreach (var control in Descendants(root)) {
                if (!control.GetType().Name.Contains("Viewport") || !control.VisibleInTree) continue;
                var rect = UIBox2.FromDimensions(control.GlobalPixelPosition, control.PixelSize);
                if (rect.Contains(mouse.Position)) return control;
            }
        }
        return null;
    }

    private static System.Collections.Generic.IEnumerable<Control> Descendants(Control control) {
        yield return control;
        foreach (var child in control.Children.ToArray())
            foreach (var nested in Descendants(child)) yield return nested;
    }
}
