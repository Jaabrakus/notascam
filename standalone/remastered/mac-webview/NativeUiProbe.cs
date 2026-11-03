// Opt-in native-window integration probe. Normal launches never enable it.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.Json;
using System.Numerics;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.PixelFormats;
using Robust.Client.Graphics;
using Robust.Client.UserInterface;
using Robust.Client.UserInterface.Controls;
using Robust.Shared.IoC;
using Robust.Shared.Maths;
using Robust.Shared.Reflection;
using Robust.Shared.GameObjects;
using Robust.Shared.Input;
using Robust.Shared.Map;
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
    [DllImport("dmwebkit")] private static extern void dm_ui_test_native_right_click(uint window, double x, double y);
    [DllImport("dmwebkit")] private static extern void dm_ui_test_native_double_click(uint window, double x, double y);
    [DllImport("dmwebkit")] private static extern void dm_ui_test_native_scroll(uint window, double x, double y, double dy);
    [DllImport("dmwebkit")] private static extern void dm_ui_test_native_drag(uint window, double x, double y, double x2, double y2, nuint flags);
    [DllImport("dmwebkit")] private static extern void dm_ui_test_native_button_drag(uint window, double x, double y, double x2, double y2, int button);
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
    // Opt-in diagnostic only: target this client's actual viewport callback,
    // including its renderer hit map and network click path. Never moves the
    // system pointer, changes focus, or calls a server/game procedure directly.
    private static void InternalMapClick(IClydeWindow window, JsonElement action) {
        var reflection = IoCManager.Resolve<IReflectionManager>();
        var type = reflection.GetType("OpenDreamClient.Interface.IDreamInterfaceManager")!;
        var manager = IoCManager.ResolveType(type);
        var map = Member(manager, "DefaultMap") ?? throw new InvalidOperationException("No default map");
        var viewport = (Control)Member(map, "Viewport")!;
        if (!viewport.VisibleInTree || viewport.Root?.Window?.Id != window.Id)
            throw new InvalidOperationException("Requested window does not own the visible map");
        var drawBox = (UIBox2i)viewport.GetType().GetMethod("GetDrawBox")!.Invoke(viewport, null)!;
        var fraction = new Vector2((float)action.GetProperty("x").GetDouble(), (float)action.GetProperty("y").GetDouble());
        if (fraction.X <= 0 || fraction.X >= 1 || fraction.Y <= 0 || fraction.Y >= 1)
            throw new InvalidOperationException("Map click is outside the draw box");
        var relative = (Vector2)drawBox.TopLeft + fraction * drawBox.Size;
        var global = relative + viewport.GlobalPixelPosition;
        var pointer = new ScreenCoordinates(global, window.Id);
        var systems = IoCManager.Resolve<IEntitySystemManager>();
        var mouseType = reflection.GetType("OpenDreamClient.Input.MouseInputSystem")!;
        var mouse = systems.GetEntitySystem(mouseType);
        var hit = mouseType.GetMethod("GetAtomUnderMouse")!.Invoke(mouse, new object[] { viewport, relative, pointer });
        var atom = hit == null ? null : Member(hit, "Item1");
        var hitText = atom?.ToString();
        var expected = action.TryGetProperty("expected", out var expectedValue) ? expectedValue.GetString() : null;
        var nonce = action.GetProperty("nonce").GetString();
        var accepted = hit != null && (expected == null || expected == hitText);
        if (accepted) {
            var handler = map.GetType().GetMethod("OnViewportKeyBindEvent", BindingFlags.Instance | BindingFlags.NonPublic)!;
            // Down/up in the same update prevents a real pointer move between
            // them from turning this diagnostic click into a drag.
            foreach (var state in new[] { BoundKeyState.Down, BoundKeyState.Up })
                handler.Invoke(map, new object[] { new GUIBoundKeyEventArgs(EngineKeyFunctions.Use, state,
                    pointer, false, relative / viewport.UIScale, relative) });
        }
        var receipt = new { nonce, accepted, expected, hit=hitText, utc=DateTime.UtcNow,
            dispatch="ControlMap.OnViewportKeyBindEvent -> MouseInputSystem renderer hit-test -> network AtomClickedEvent",
            x=global.X, y=global.Y, width=drawBox.Width, height=drawBox.Height,
            viewportSize=Member(viewport,"ViewportSize")?.ToString() };
        File.WriteAllText(Path.Combine(DirectoryPath!, "map-click-result.pending"), JsonSerializer.Serialize(receipt));
        File.Move(Path.Combine(DirectoryPath!, "map-click-result.pending"), Path.Combine(DirectoryPath!, "map-click-result.json"), true);
        File.AppendAllText(Path.Combine(DirectoryPath!, "map-clicks.jsonl"), JsonSerializer.Serialize(receipt)+"\n");
    }
    private static object? InterfaceState() {
        var type = IoCManager.Resolve<IReflectionManager>().GetType("OpenDreamClient.Interface.IDreamInterfaceManager");
        if (type == null) return null;
        var manager = IoCManager.ResolveType(type);
        var maps = new List<object>();
        if (Member(manager, "Windows") is IDictionary windows)
            foreach (DictionaryEntry entry in windows)
                if (Member(entry.Value!, "ChildControls") is IEnumerable controls)
                    foreach (var control in controls)
                        if (control.GetType().Name == "ControlMap") {
                            var descriptor = Member(control, "ElementDescriptor") ?? Member(control, "ControlDescriptor");
                            var rightClick = descriptor == null ? null : Member(descriptor, "RightClick");
                            maps.Add(new { rightClick=rightClick == null ? null : Member(rightClick, "Value"),
                                descriptorType=descriptor?.GetType().FullName });
                        }
        return new { showPopupMenus=Member(manager, "ShowPopupMenus"), maps };
    }
    private static bool _keyLog;
    // Opt-in, read-only lifecycle trace. Values come from the real client
    // entity/render objects; this never toggles movement or advances frames.
    private static void TraceAnimation() {
        var prefix = Environment.GetEnvironmentVariable("DM_ANIMATION_PROBE");
        if (string.IsNullOrEmpty(prefix)) return;
        var reflection = IoCManager.Resolve<IReflectionManager>();
        var spriteType = reflection.GetType("OpenDreamClient.Rendering.DMISpriteComponent");
        var glideType = reflection.GetType("OpenDreamClient.Rendering.AtomGlideSystem");
        if (spriteType == null || glideType == null) return;
        var manager = IoCManager.Resolve<IEntityManager>();
        var systems = IoCManager.Resolve<IEntitySystemManager>();
        if (!systems.TryGetEntitySystem(glideType, out var glideSystem)) return;
        var glides = (Member(glideSystem!, "_currentGlides") as IEnumerable)?.Cast<object>().ToArray() ?? Array.Empty<object>();
        object IconState(object icon, int depth=0) {
            var children = new List<object>();
            if (depth < 3)
                foreach (var edge in new[] { "Overlays", "Underlays" })
                    if (Member(icon, edge) is IEnumerable list)
                        foreach (var child in list) children.Add(new { edge, icon=IconState(child, depth+1) });
            var dmi = Member(icon, "DMI");
            var description = dmi == null ? null : Member(dmi, "Description");
            var states = description == null ? null : Member(description, "States") as IDictionary;
            var state = Member(icon, "_iconState")?.ToString() ?? "";
            var selectedState = states == null ? null : states.Contains(state) ? states[state] : states.Contains("") ? states[""] : null;
            var moving = Member(icon, "_movementActive") is true;
            var resolve = description?.GetType().GetMethod("GetStateForMovement");
            if (resolve != null) selectedState = resolve.Invoke(description, new object[] { state, moving });
            object? textureRect = null;
            string? resourceSha = null;
            var pixelProbe = Environment.GetEnvironmentVariable("DM_ANIMATION_PIXEL_PROBE") == "1";
            if (pixelProbe && dmi != null && Member(dmi, "Data") is byte[] data) {
                resourceSha = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(data)).ToLowerInvariant();
                var path = Path.Combine(DirectoryPath!, "animation-resource-"+resourceSha+".dmi");
                if (!File.Exists(path)) File.WriteAllBytes(path, data);
                var getState = dmi.GetType().GetMethod("GetStateForMovement");
                var rendered = getState == null ? dmi.GetType().GetMethod("GetState")?.Invoke(dmi, new object[] { state })
                    : getState.Invoke(dmi, new object[] { state, moving });
                if (rendered != null && Member(icon, "_direction") is object direction && Member(icon, "_animationFrame") is int frame) {
                    var frames = rendered.GetType().GetMethod("GetFrames")?.Invoke(rendered, new[] { direction }) as Array;
                    if (frames != null && frame >= 0 && frame < frames.Length && frames.GetValue(frame) is object atlas && Member(atlas, "SubRegion") is object rect)
                        textureRect = new { x=Member(rect,"Left"), y=Member(rect,"Top"), width=Member(rect,"Width"), height=Member(rect,"Height") };
                }
            }
            return new { id=System.Runtime.CompilerServices.RuntimeHelpers.GetHashCode(icon),
                active=Member(icon, "_movementActive"), frame=Member(icon, "_animationFrame"),
                direction=Member(icon, "_direction")?.ToString(), state,
                movement=selectedState == null ? null : Member(selectedState, "Movement"),
                resource=dmi == null ? null : Member(dmi, "Id"), resourceSha, textureRect,
                frameCount=selectedState == null ? null : Member(selectedState,"FrameCount"), loaded=dmi != null, children };
        }
        var sprites = manager.GetAllComponents(spriteType, true).ToDictionary(pair => pair.Item1, pair => pair.Item2);
        var imageType = reflection.GetType("OpenDreamClient.Rendering.ClientImagesSystem");
        var attached = imageType == null ? null : Member(systems.GetEntitySystem(imageType), "_amClientImages") as IDictionary;
        var rows = new List<object>();
        foreach (var (uid, component) in sprites) {
            var icon = Member(component, "Icon");
            var appearance = icon == null ? null : Member(icon, "_appearance");
            var name = appearance == null ? null : Member(appearance, "Name")?.ToString();
            if (icon == null || name == null || !name.StartsWith(prefix, StringComparison.Ordinal)) continue;
            var transform = manager.GetComponent<TransformComponent>(uid);
            var clientImages = new List<object>();
            if (attached != null && attached.Contains(uid) && attached[uid] is IEnumerable images)
                foreach (var image in images) {
                    var imageUid = manager.GetEntity((NetEntity)image);
                    if (sprites.TryGetValue(imageUid, out var imageSprite) && Member(imageSprite, "Icon") is object imageIcon)
                        clientImages.Add(new { uid=imageUid.ToString(), icon=IconState(imageIcon) });
                }
            rows.Add(new { uid=uid.ToString(), netEntity=manager.GetNetEntity(uid).ToString(), name, x=transform.LocalPosition.X, y=transform.LocalPosition.Y,
                parent=transform.ParentUid.ToString(), gliding=glides.Any(g => Equals(Member(g, "Uid"), uid)), icon=IconState(icon), clientImages });
        }
        if (rows.Count > 0) File.AppendAllText(Path.Combine(DirectoryPath!, "animation.jsonl"),
            JsonSerializer.Serialize(new { utc=DateTime.UtcNow, rows })+"\n");
    }
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
                var testTitle = Environment.GetEnvironmentVariable("DM_NATIVE_UI_TEST_TITLE");
                if (!string.IsNullOrEmpty(testTitle) && w.Title != testTitle) w.Title = testTitle;
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
                    contextItems=controls.Where(c => c.GetType().Name == "ContextMenuItem" && c.VisibleInTree).Select(c => new {
                        text=string.Join("", Tree(c).OfType<Label>().Select(l => l.Text)), rect=Rect(c)
                    }).ToArray(),
                    messages=controls.OfType<RichTextLabel>().Select(c => new { text=c.GetFormattedMessage()?.ToString(), rect=Rect(c), desiredHeight=c.DesiredSize.Y }).ToArray(),
                    // Row regions are list-relative pixels from the last draw; null until drawn.
                    lists=controls.OfType<ItemList>().Select(c => new { rect=Rect(c), scroll=(Member(c,"_scrollBar") is ScrollBar bar ? bar.Value : -1f), items=c.Select(i => new { text=i.Text, selected=i.Selected,
                        rect=i.Region is UIBox2 r ? (object)new { x=c.GlobalPixelPosition.X+r.Left, y=c.GlobalPixelPosition.Y+r.Top, width=r.Width, height=r.Height } : null }).ToArray() }).ToArray(),
                    lineEdits=controls.OfType<LineEdit>().Select(c => new { text=c.Text, cursor=c.CursorPosition, selection=c.SelectionStart, focused=c.HasKeyboardFocus() }).ToArray(),
                    viewports=controls.Where(c => c.GetType().Name.Contains("Viewport") && c.VisibleInTree).Select(c => new { type=c.GetType().Name, rect=Rect(c),
                        viewportSize=Member(c,"ViewportSize") is Vector2i size ? new { width=size.X, height=size.Y } : null }).ToArray(),
                    scrolls=controls.OfType<ScrollContainer>().Select(c => new { rect=Rect(c), horizontal=c.HScrollEnabled, vertical=c.VScrollEnabled }).ToArray()
                };
            }).ToArray();
            var state = Path.Combine(DirectoryPath, "state.json");
            var input = IoCManager.Resolve<Robust.Client.Input.IInputManager>();
            var mouse = input.MouseScreenPosition;
            File.WriteAllText(state+".pending", JsonSerializer.Serialize(new { windows, interfaceState=InterfaceState(), pendingEvents=PendingEvents.Count,
                mouse=new { window=mouse.Window.ToString(), x=mouse.Position.X, y=mouse.Position.Y },
                keyboardFocus=IoCManager.Resolve<IUserInterfaceManager>().KeyboardFocused?.GetType().Name,
                context=Member(input.Contexts.ActiveContext,"Name")?.ToString() }));
            File.Move(state+".pending", state, true);
            TraceAnimation();
            // Test-only framebuffer request, independent of game input. It
            // captures real selection images on the normal map renderer.
            var capture = Path.Combine(DirectoryPath, "capture.txt");
            if (File.Exists(capture)) {
                var filename = File.ReadAllText(capture).Trim();
                File.Delete(capture);
                if (filename.EndsWith(".png") && Path.GetFileName(filename) == filename) {
                    var output = Path.Combine(DirectoryPath, filename);
                    IoCManager.Resolve<IClyde>().Screenshot(ScreenshotType.Final, image => {
                        using (image) image.SaveAsPng(output);
                    });
                }
            }
            var action = Path.Combine(DirectoryPath, "action.json");
            if (!File.Exists(action) || PendingEvents.Count > 0) return;
            using var doc = JsonDocument.Parse(File.ReadAllText(action));
            File.Delete(action);
            var a=doc.RootElement;
            var id=a.GetProperty("window").GetUInt32(); var kind=a.GetProperty("kind").GetInt32();
            var window=roots.First(r => r.Window != null && Id(r.Window)==id).Window!;
            if (kind==9) InternalMapClick(window, a);
            else if (kind==2) dm_ui_test_resize(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
            else if (kind==4) {
                // Real AppKit key press: macOS key code, its characters and modifier flags.
                dm_ui_test_focus(id,-1,-1);
                dm_ui_test_native_key(id,(ushort)a.GetProperty("code").GetInt32(),a.GetProperty("text").GetString() ?? "",(nuint)a.GetProperty("modifiers").GetInt64());
            } else if (kind==5) {
                dm_ui_test_focus(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
                dm_ui_test_native_click(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
            } else if (kind==6) {
                dm_ui_test_focus(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
                dm_ui_test_native_right_click(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
            } else if (kind==11) {
                dm_ui_test_focus(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
                dm_ui_test_native_scroll(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble(),a.GetProperty("dy").GetDouble());
            } else if (kind==10) {
                dm_ui_test_focus(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
                dm_ui_test_native_double_click(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble());
            } else if (kind==12) {
                // right (button 1) or middle (button 2) drag
                dm_ui_test_focus(id,-1,-1);
                dm_ui_test_native_button_drag(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble(),
                    a.GetProperty("x2").GetDouble(),a.GetProperty("y2").GetDouble(),a.GetProperty("button").GetInt32());
            } else if (kind==7) {
                dm_ui_test_focus(id,-1,-1);
                dm_ui_test_native_drag(id,a.GetProperty("x").GetDouble(),a.GetProperty("y").GetDouble(),
                    a.GetProperty("x2").GetDouble(),a.GetProperty("y2").GetDouble(),(nuint)a.GetProperty("modifiers").GetInt64());
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
        if (kind==8) {
            // SDL-level left drag from (x,y) to (x2,y2): one event per frame, so the
            // client sees the button held while the pointer moves.
            var reg=Member(window,"Reg")!;
            var size=(Vector2i)Member(reg,"WindowSize")!;
            float X(double f)=>(float)(f*size.X); float Y(double f)=>(float)(f*size.Y);
            double x0=action.GetProperty("x").GetDouble(), y0=action.GetProperty("y").GetDouble();
            double x1=action.GetProperty("x2").GetDouble(), y1=action.GetProperty("y2").GetDouble();
            ev=new SDL.SDL_Event(); ev.motion.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_MOTION; ev.motion.windowID=id; ev.motion.x=X(x0); ev.motion.y=Y(y0);
            PendingEvents.Enqueue(ev);
            ev=new SDL.SDL_Event(); ev.button.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_BUTTON_DOWN; ev.button.windowID=id; ev.button.button=1; ev.button.down=true; ev.button.clicks=1;
            ev.button.x=X(x0); ev.button.y=Y(y0); PendingEvents.Enqueue(ev);
            for (var step=1; step<=6; step++) {
                var t=step/6.0;
                ev=new SDL.SDL_Event(); ev.motion.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_MOTION; ev.motion.windowID=id;
                ev.motion.x=X(x0+(x1-x0)*t); ev.motion.y=Y(y0+(y1-y0)*t); ev.motion.state=SDL.SDL_MouseButtonFlags.SDL_BUTTON_LMASK;
                PendingEvents.Enqueue(ev);
            }
            ev=new SDL.SDL_Event(); ev.button.type=SDL.SDL_EventType.SDL_EVENT_MOUSE_BUTTON_UP; ev.button.windowID=id; ev.button.button=1; ev.button.down=false; ev.button.clicks=1;
            ev.button.x=X(x1); ev.button.y=Y(y1); PendingEvents.Enqueue(ev);
        } else if (kind==3) {
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
