// Opt-in native-window integration probe. Normal launches never enable it.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.Json;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using Robust.Client.Graphics;
using Robust.Client.UserInterface;
using Robust.Client.UserInterface.Controls;
using Robust.Shared.IoC;
using Robust.Shared.Maths;
using SDL3;

namespace Robust.Client.WebView;

internal static class NativeUiProbe {
    private static readonly string? DirectoryPath = Environment.GetEnvironmentVariable("DM_NATIVE_UI_PROBE");
    private static DateTime _next;
    private static readonly HashSet<string> Captured = new();
    private static readonly Dictionary<uint, DateTime> FirstSeen = new();
    private static readonly Queue<SDL.SDL_Event> PendingEvents = new();
    [DllImport("dmwebkit")] private static extern void dm_ui_test_resize(uint window, double width, double height);
    [DllImport("dmwebkit")] private static extern void dm_ui_test_focus(uint window, double x, double y);
    [DllImport("dmwebkit")] private static extern void dm_ui_test_native_key(uint window, ushort keyCode, string text, nuint flags);
    [DllImport("dmwebkit")] private static extern void dm_ui_test_native_click(uint window, double x, double y);
    [DllImport("dmwebkit")] private static extern void dm_ui_test_first_responder(uint window, byte[] output, int size);
    private static string Responder(uint window) {
        var buffer = new byte[1024];
        dm_ui_test_first_responder(window, buffer, buffer.Length);
        return System.Text.Encoding.UTF8.GetString(buffer).TrimEnd('\0');
    }
    private static object? Member(object value, string name) {
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
        return value.GetType().GetProperty(name, flags)?.GetValue(value) ?? value.GetType().GetField(name, flags)?.GetValue(value);
    }
    private static uint Id(IClydeWindow window) => Member(window, "Reg") is object reg && Member(reg, "WindowId") is uint id ? id : 0;
    private static IEnumerable<Control> Tree(Control control) {
        yield return control;
        foreach (var child in control.Children)
            foreach (var node in Tree(child)) yield return node;
    }
    private static object Rect(Control c) => new { x=c.GlobalPixelPosition.X, y=c.GlobalPixelPosition.Y, width=c.PixelSize.X, height=c.PixelSize.Y };
    private static bool _keyLog;
    public static void Update() {
        if (string.IsNullOrEmpty(DirectoryPath)) return;
        if (!_keyLog) {
            _keyLog = true;
            var keys = IoCManager.Resolve<Robust.Client.Input.IInputManager>();
            keys.FirstChanceOnKeyEvent += (args, type) => System.Console.WriteLine(
                $"[INFO] native.ui.probe: engine key {args.Key} {type} focus={IoCManager.Resolve<IUserInterfaceManager>().KeyboardFocused?.GetType().Name ?? "none"} context={Member(keys.Contexts.ActiveContext, "Name")}");
        }
        if (DateTime.UtcNow < _next) return;
        _next = DateTime.UtcNow.AddMilliseconds(100);
        try {
            Directory.CreateDirectory(DirectoryPath);
            DispatchEvent();
            var roots = IoCManager.Resolve<IUserInterfaceManager>().AllRoots.ToArray();
            var windows = roots.Where(r => r.Window != null && !r.Window.IsDisposed).Select(root => {
                var w = root.Window!;
                var controls = Tree(root).ToArray();
                var prompt = controls.OfType<OSWindow>().FirstOrDefault(p => p.GetType().Namespace?.EndsWith(".Prompts") == true);
                if (!FirstSeen.ContainsKey(Id(w))) FirstSeen[Id(w)] = DateTime.UtcNow;
                if (prompt != null && prompt.Width > 0 && DateTime.UtcNow-FirstSeen[Id(w)] > TimeSpan.FromMilliseconds(300) && Captured.Add(prompt.Title)) {
                    var path = Path.Combine(DirectoryPath, "prompt-"+Id(w)+".png");
                    var clyde = IoCManager.Resolve<IClyde>();
                    var target = clyde.CreateRenderTarget(w.Size, new RenderTargetFormatParameters());
                    clyde.GetType().GetMethod("RenderNow")!.Invoke(clyde, new object[] { target,
                        (Action<IRenderHandle>)(handle => {
                            handle.DrawingHandleScreen.DrawRect(new UIBox2(0,0,w.Size.X,w.Size.Y), root.ActualBgColor);
                            IoCManager.Resolve<IUserInterfaceManager>().RenderControl(handle, root, Vector2i.Zero);
                        }) });
                    target.CopyPixelsToMemory<Rgba32>(image => { using(image) image.SaveAsPng(path); target.Dispose(); });
                }
                return new {
                    id=Id(w), responder=Responder(Id(w)), title=prompt?.Title ?? w.Title, width=w.Size.X, height=w.Size.Y, scale=root.UIScale,
                    prompt=prompt?.GetType().Name,
                    buttons=controls.OfType<Button>().Where(c => c.VisibleInTree).Select(c => new {
                        text=string.Join("", Tree(c).OfType<Label>().Select(l => l.Text)), rect=Rect(c)
                    }).ToArray(),
                    messages=controls.OfType<RichTextLabel>().Select(c => new { text=c.GetFormattedMessage()?.ToString(), rect=Rect(c), desiredHeight=c.DesiredSize.Y }).ToArray(),
                    // Row regions are list-relative pixels from the last draw; null until drawn.
                    lists=controls.OfType<ItemList>().Select(c => new { rect=Rect(c), scroll=(Member(c,"_scrollBar") is ScrollBar bar ? bar.Value : -1f), items=c.Select(i => new { text=i.Text, selected=i.Selected,
                        rect=i.Region is UIBox2 r ? (object)new { x=c.GlobalPixelPosition.X+r.Left, y=c.GlobalPixelPosition.Y+r.Top, width=r.Width, height=r.Height } : null }).ToArray() }).ToArray(),
                    lineEdits=controls.OfType<LineEdit>().Select(c => new { text=c.Text, cursor=c.CursorPosition, selection=c.SelectionStart, focused=c.HasKeyboardFocus() }).ToArray(),
                    viewports=controls.Where(c => c.GetType().Name.Contains("Viewport") && c.VisibleInTree).Select(c => new { type=c.GetType().Name, rect=Rect(c) }).ToArray(),
                    scrolls=controls.OfType<ScrollContainer>().Select(c => new { rect=Rect(c), horizontal=c.HScrollEnabled, vertical=c.VScrollEnabled }).ToArray()
                };
            }).ToArray();
            var state = Path.Combine(DirectoryPath, "state.json");
            var input = IoCManager.Resolve<Robust.Client.Input.IInputManager>();
            var mouse = input.MouseScreenPosition;
            File.WriteAllText(state+".pending", JsonSerializer.Serialize(new { windows, pendingEvents=PendingEvents.Count,
                mouse=new { window=mouse.Window.ToString(), x=mouse.Position.X, y=mouse.Position.Y },
                keyboardFocus=IoCManager.Resolve<IUserInterfaceManager>().KeyboardFocused?.GetType().Name,
                context=Member(input.Contexts.ActiveContext,"Name")?.ToString() }));
            File.Move(state+".pending", state, true);
            var action = Path.Combine(DirectoryPath, "action.json");
            if (!File.Exists(action) || PendingEvents.Count > 0) return;
            using var doc = JsonDocument.Parse(File.ReadAllText(action));
            File.Delete(action);
            var a=doc.RootElement;
            var id=a.GetProperty("window").GetUInt32(); var kind=a.GetProperty("kind").GetInt32();
            var window=roots.First(r => r.Window != null && Id(r.Window)==id).Window!;
            if (kind==2) dm_ui_test_resize(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
            else if (kind==4) {
                // Real AppKit key press: macOS key code, its characters and modifier flags.
                dm_ui_test_focus(id,-1,-1);
                dm_ui_test_native_key(id,(ushort)a.GetProperty("code").GetInt32(),a.GetProperty("text").GetString() ?? "",(nuint)a.GetProperty("modifiers").GetInt64());
            } else if (kind==5) {
                dm_ui_test_focus(id,-1,-1);
                dm_ui_test_native_click(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
            }
            else InjectInput(id,kind,window,a);
        } catch (Exception error) {
            System.Console.WriteLine("[ERRO] native.ui.probe: "+error);
        }
    }
    [DllImport("libSDL3.0.dylib", EntryPoint="SDL_PushEvent")] private static extern unsafe byte PushEvent(SDL.SDL_Event* ev);
    private static unsafe void DispatchEvent() {
        if (PendingEvents.Count==0) return;
        var ev=PendingEvents.Dequeue();
        if ((uint)ev.type==0) return; // An intentional held-key interval.
        System.Console.WriteLine($"[INFO] native.ui.probe: event {ev.type} window={ev.key.windowID} scan={ev.key.scancode}");
        if(PushEvent(&ev)==0) throw new InvalidOperationException("SDL rejected a test input event");
    }
    private static unsafe void InjectInput(uint id, int kind, IClydeWindow window, JsonElement action) {
        var ev = new SDL.SDL_Event();
        // Real pointer/focus events must agree with the injected click position;
        // macOS may otherwise deliver a live mouse move between our down/up.
        dm_ui_test_focus(id,kind==0?action.GetProperty("x").GetDouble():-1,
            kind==0?action.GetProperty("y").GetDouble():-1);
        PendingEvents.Enqueue(new SDL.SDL_Event());
        PendingEvents.Enqueue(new SDL.SDL_Event());
        ev=new SDL.SDL_Event();
        if (kind==3) {
            // `code` clicks with `modifiers` idle 100 ms frames between them; an
            // optional x2/y2 moves the pointer before the second click.
            var reg=Member(window,"Reg")!;
            var size=(Vector2i)Member(reg,"WindowSize")!;
            for (var click=0; click<action.GetProperty("code").GetInt32(); click++) {
                var second=click>0 && action.TryGetProperty("x2", out var x2);
                ev=new SDL.SDL_Event();
                ev.motion.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_MOTION; ev.motion.windowID=id;
                ev.motion.x=(float)(second ? action.GetProperty("x2") : action.GetProperty("x")).GetDouble()*size.X;
                ev.motion.y=(float)(second ? action.GetProperty("y2") : action.GetProperty("y")).GetDouble()*size.Y;
                if (click==0 || second) PendingEvents.Enqueue(ev);
                ev=new SDL.SDL_Event();
                ev.button.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_BUTTON_DOWN; ev.button.windowID=id; ev.button.button=1; ev.button.down=true;
                ev.button.clicks=(byte)(click+1);
                PendingEvents.Enqueue(ev);
                ev.button.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_BUTTON_UP; ev.button.down=false;
                PendingEvents.Enqueue(ev);
                if (click+1<action.GetProperty("code").GetInt32())
                    for (var pause=0; pause<action.GetProperty("modifiers").GetInt32(); pause++) PendingEvents.Enqueue(new SDL.SDL_Event());
            }
        } else if (kind==0) {
            var reg=Member(window,"Reg")!;
            var size=(Vector2i)Member(reg,"WindowSize")!;
            ev.motion.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_MOTION;
            ev.motion.windowID=id;
            ev.motion.x=(float)action.GetProperty("x").GetDouble()*size.X;
            ev.motion.y=(float)action.GetProperty("y").GetDouble()*size.Y;
            PendingEvents.Enqueue(ev);
            ev=new SDL.SDL_Event();
            ev.button.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_BUTTON_DOWN; ev.button.windowID=id; ev.button.button=1; ev.button.down=true;
            PendingEvents.Enqueue(ev);
            ev.button.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_BUTTON_UP; ev.button.down=false;
            PendingEvents.Enqueue(ev);
        } else {
            var modifiers=action.GetProperty("modifiers").GetInt32();
            var modifierKeys=new List<int>();
            if ((modifiers&1)!=0) modifierKeys.Add(225);
            if ((modifiers&0x40)!=0) modifierKeys.Add(224);
            if ((modifiers&0x100)!=0) modifierKeys.Add(226);
            foreach(var scan in modifierKeys) {
                var modifier=new SDL.SDL_Event(); modifier.key.type=SDL.SDL_EventType.SDL_EVENT_KEY_DOWN;
                modifier.key.windowID=id; modifier.key.scancode=(SDL.SDL_Scancode)scan; modifier.key.down=true;
                modifier.key.mod=(SDL.SDL_Keymod)modifiers; PendingEvents.Enqueue(modifier);
            }
            ev.key.type=SDL.SDL_EventType.SDL_EVENT_KEY_DOWN; ev.key.windowID=id;
            ev.key.scancode=(SDL.SDL_Scancode)action.GetProperty("code").GetInt32();
            ev.key.mod=(SDL.SDL_Keymod)action.GetProperty("modifiers").GetInt32();
            ev.key.down=true; PendingEvents.Enqueue(ev);
            PendingEvents.Enqueue(new SDL.SDL_Event());
            PendingEvents.Enqueue(new SDL.SDL_Event());
            ev.key.type=SDL.SDL_EventType.SDL_EVENT_KEY_UP; ev.key.down=false; PendingEvents.Enqueue(ev);
            modifierKeys.Reverse();
            foreach(var scan in modifierKeys) {
                var modifier=new SDL.SDL_Event(); modifier.key.type=SDL.SDL_EventType.SDL_EVENT_KEY_UP;
                modifier.key.windowID=id; modifier.key.scancode=(SDL.SDL_Scancode)scan; modifier.key.down=false;
                PendingEvents.Enqueue(modifier);
            }
        }
    }
}
