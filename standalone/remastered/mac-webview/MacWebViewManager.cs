using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using System.Linq;
using System.Net;
using System.Runtime.InteropServices;
using System.Reflection;
using System.Collections;
using System.Text.Json;
using SixLabors.ImageSharp;
using Robust.Client;
using Robust.Client.Graphics;
using Robust.Client.UserInterface;
using Robust.Client.UserInterface.Controls;
using Robust.Client.WebViewHook;
using Robust.Shared.Configuration;
using Robust.Shared.IoC;
using Robust.Shared.Reflection;
using Robust.Shared.GameObjects;

[assembly: WebViewManagerImpl(typeof(Robust.Client.WebView.MacWebViewManager))]

namespace Robust.Client.WebView;

internal sealed class MacWebViewManager : IWebViewManagerInternal, IWebViewManagerHook {
    private static readonly ConcurrentQueue<(long Panel, int Kind, long Request, string Text)> Events = new();
    private static readonly Native.EventCallback Callback = (panel, kind, request, text) =>
        Events.Enqueue((panel, kind, request, Marshal.PtrToStringUTF8(text) ?? ""));
    internal readonly Dictionary<long, MacBrowser> Browsers = new();
    private readonly Dictionary<string, string> _mime = new();
    private Type? _interfaceType;
    private int _loadedFrames;
    private bool _captured;
    private bool _layoutReported;
    private bool _macroKeysInstalled;
    private bool _raceRequested;
    private bool _raceChosen;
    private string? _serverGeneration;
    private DateTime _nextReconnectCheck;
    private readonly HashSet<string> _panesChecked = new();
    private readonly Dictionary<string, (bool X, bool Y)> _autoFill = new();

    public void PreInitialize(IDependencyCollection dependencies, GameController.DisplayMode mode) {
        dependencies.Resolve<IConfigurationManagerInternal>().LoadCVarsFromAssembly(typeof(MacWebViewManager).Assembly);
        dependencies.Resolve<IReflectionManager>().LoadAssemblies(typeof(MacWebViewManager).Assembly);
        dependencies.RegisterInstance<IWebViewManager>(this);
        dependencies.RegisterInstance<IWebViewManagerInternal>(this);
    }
    public void Initialize() {
        var hints = Environment.GetEnvironmentVariable("DM_SKIN_LAYOUT_HINTS");
        if (!string.IsNullOrEmpty(hints)) {
            using var document = JsonDocument.Parse(File.ReadAllText(hints));
            foreach (var property in document.RootElement.GetProperty("controls").EnumerateObject())
                _autoFill[property.Name] = (property.Value.GetProperty("x").GetBoolean(), property.Value.GetProperty("y").GetBoolean());
        }
        Native.dm_web_initialize(Callback, Path.Combine(AppContext.BaseDirectory, "libSDL3.0.dylib"));
        System.Console.WriteLine("[INFO] mac.webview: Native WebKit renderer initialized");
    }
    public void Update() {
        ReconnectLocalWorld();
        InstallLegacyKeys();
        FitEmbeddedPanes();
        while (Events.TryDequeue(out var item)) {
            if (!Browsers.TryGetValue(item.Panel, out var browser)) continue;
            try { browser.Receive(item.Kind, item.Request, item.Text); }
            catch (Exception error) { System.Console.WriteLine($"[ERRO] mac.webview: {error}"); }
        }
        foreach (var browser in Browsers.Values.ToArray()) browser.Layout();
        DreamSeekerKeys.Update();
        RemasterDragBox.Update();
        RunRaceSmokeTest();
        AnswerJoinPassword();
        NativeUiProbe.Update();
        CaptureProbeBrowsers();
        var snapshot = Environment.GetEnvironmentVariable("DM_GAME_SNAPSHOT");
        if (!_captured && !string.IsNullOrEmpty(snapshot) && Browsers.Values.Any(b => b.HasLoaded) && ++_loadedFrames > (Environment.GetEnvironmentVariable("DM_TEST_RACE") == null ? 240 : 900)) {
            _captured = true;
            IoCManager.Resolve<IClyde>().Screenshot(ScreenshotType.Final, image => {
                using (image) image.SaveAsPng(snapshot);
                System.Console.WriteLine($"[INFO] mac.webview: game framebuffer captured to {snapshot}");
            });
        }
    }
    private void CaptureProbeBrowsers() {
        // Read-only, private-client diagnostic. Native WebKit panels are not
        // part of the engine framebuffer; snapshot each loaded panel directly.
        // No screen-recording permission, focus change or OS input is involved.
        var directory = Environment.GetEnvironmentVariable("DM_NATIVE_UI_PROBE");
        if (string.IsNullOrEmpty(directory)) return;
        var request = Path.Combine(directory, "capture-web.txt");
        if (!File.Exists(request)) return;
        var prefix = File.ReadAllText(request).Trim();
        File.Delete(request);
        if (prefix.Length == 0 || prefix.Length > 80 || prefix.Any(c => !char.IsAsciiLetterOrDigit(c) && c != '-' && c != '_')) return;
        var entries = Browsers.Where(pair => pair.Value.HasLoaded && !pair.Value.Closed)
            .Select(pair => new { panel = pair.Key, url = pair.Value.Url, file = prefix + "-panel-" + pair.Key + ".png" }).ToArray();
        foreach (var entry in entries) Native.dm_web_snapshot(entry.panel, Path.Combine(directory, entry.file));
        var manifest = Path.Combine(directory, prefix + "-panels.json");
        File.WriteAllText(manifest + ".pending", JsonSerializer.Serialize(entries));
        File.Move(manifest + ".pending", manifest, true);
    }
    private void ReconnectLocalWorld() {
        var ready = Environment.GetEnvironmentVariable("DM_LOCAL_SERVER_READY_FILE");
        if (string.IsNullOrEmpty(ready) || DateTime.UtcNow < _nextReconnectCheck) return;
        _nextReconnectCheck = DateTime.UtcNow.AddMilliseconds(500);
        if (!File.Exists(ready)) return;
        string generation;
        try { generation = File.ReadAllText(ready); }
        catch (IOException) { return; }
        if (string.IsNullOrWhiteSpace(generation)) return;
        if (_serverGeneration == null) { _serverGeneration = generation; return; }
        if (_serverGeneration == generation) return;
        var client = IoCManager.Resolve<IBaseClient>();
        if (client.RunLevel != ClientRunLevel.Initialize && client.RunLevel != ClientRunLevel.Error) return;
        // Upstream Reset() clears skin controls but retains native window IDs.
        // A second interface load otherwise fails on the existing main-window ID.
        if (_interfaceType != null) {
            var manager = IoCManager.ResolveType(_interfaceType);
            var oldControls = new List<Control>();
            if (Member(manager, "Windows") is IDictionary windows)
                foreach (DictionaryEntry entry in windows)
                    if (Member(entry.Value!, "UIElement") is Control root)
                        oldControls.AddRange(Descendants(root));
            manager.GetType().GetMethod("Reset", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(manager, null);
            foreach (var control in oldControls.Distinct().Reverse()) control.Dispose();
            if (Member(manager, "ClydeWindowIdToControl") is IDictionary windowIds) windowIds.Clear();
        }
        var reflection = IoCManager.Resolve<IReflectionManager>();
        var systems = _interfaceType != null && Member(IoCManager.ResolveType(_interfaceType), "_entitySystemManager") is IEntitySystemManager contentSystems
            ? contentSystems : IoCManager.Resolve<IEntitySystemManager>();
        foreach (var name in new[] {"OpenDreamClient.ClientVerbSystem", "OpenDreamClient.Rendering.ClientAppearanceSystem",
                     "OpenDreamClient.Rendering.ClientImagesSystem", "OpenDreamClient.Rendering.ClientScreenOverlaySystem"}) {
            var type = systems.GetEntitySystemTypes().FirstOrDefault(t => t.FullName == name);
            // These overrides only clear per-world caches; subscriptions remain
            // active for the next world. The engine retains the systems on disconnect.
            if (type != null && systems.TryGetEntitySystem(type, out var system)) {
                type.GetMethod("Shutdown")!.Invoke(system, null);
                System.Console.WriteLine($"[INFO] mac.webview: reset {name} for reconnect");
            }
        }
        var resourceType = reflection.GetType("OpenDreamClient.Resources.IDreamResourceManager")!;
        var resources = IoCManager.ResolveType(resourceType);
        foreach (var name in new[] {"_resourceCache", "_loadingResources", "_pendingResourceLookups", "_resourcePathToIdCache"})
            if (Member(resources, name) is IDictionary cache) cache.Clear();
        _panesChecked.Clear();
        _layoutReported = false;
        var port = ushort.TryParse(Environment.GetEnvironmentVariable("DM_LOCAL_SERVER_PORT"), out var parsed) ? parsed : (ushort)12121;
        client.ConnectToServer("127.0.0.1", port);
        _serverGeneration = generation;
        System.Console.WriteLine("[INFO] mac.webview: reconnecting to the rebooted local world");
    }
    private void InstallLegacyKeys() {
        if (_macroKeysInstalled) return;
        var type = IoCManager.Resolve<IReflectionManager>().GetType("OpenDreamClient.Interface.ParsedKeybind");
        if (type?.GetField("keyNameToKey", BindingFlags.Static | BindingFlags.NonPublic)?.GetValue(null) is not IDictionary keys) return;
        keys["-"] = Robust.Client.Input.Keyboard.Key.Minus;
        keys["="] = Robust.Client.Input.Keyboard.Key.Equal;
        keys["/"] = Robust.Client.Input.Keyboard.Key.Slash;
        keys["CENTER"] = Robust.Client.Input.Keyboard.Key.NumpadNum5;
        type.GetField("keyToKeyName", BindingFlags.Static | BindingFlags.NonPublic)?.SetValue(null, null);
        _macroKeysInstalled = true;
        System.Console.WriteLine("[INFO] mac.webview: registered legacy keys CENTER, -, =, /");
    }
    // Opt-in smoke test uses the game's existing command and prompt handlers.
    // It is never enabled by Play.command or a normal game launch.
    private bool _joinAnswered;
    private bool _passwordAnswered;
    // Remastered: joining a friend's world, the launcher passes the password the
    // player typed (DM_JOIN_PASSWORD); the world's "Join password" prompt gets it.
    private void AnswerJoinPassword() {
        var password = Environment.GetEnvironmentVariable("DM_JOIN_PASSWORD");
        if (_passwordAnswered || string.IsNullOrEmpty(password)) return;
        foreach (var root in IoCManager.Resolve<IUserInterfaceManager>().AllRoots.ToArray())
            foreach (var control in Descendants(root).ToArray()) {
                if (control.GetType().Name != "TextPrompt" || control is not OSWindow window || window.Title != "Join password") continue;
                if (Member(control, "_textEdit") is not LineEdit edit) continue;
                edit.Text = password;
                control.GetType().GetMethod("OkButtonClicked", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(control, null);
                _passwordAnswered = true;
                System.Console.WriteLine("[INFO] mac.webview: answered the join password prompt");
                return;
            }
    }
    private void RunRaceSmokeTest() {
        var race = Environment.GetEnvironmentVariable("DM_TEST_RACE");
        if (string.IsNullOrEmpty(race) || _interfaceType == null) return;
        if (!_raceRequested && _loadedFrames > 300) {
            _raceRequested = true;
            _interfaceType.GetMethod("RunCommand")!.Invoke(IoCManager.ResolveType(_interfaceType), new object[] {"Restart", false});
            System.Console.WriteLine("[INFO] mac.webview: smoke test requested race selection");
        }
        if (!_raceRequested) return;
        foreach (var root in IoCManager.Resolve<IUserInterfaceManager>().AllRoots.ToArray()) {
            foreach (var control in Descendants(root).ToArray()) {
                // Remastered: the "found or join a realm" prompt after the race (DM_TEST_JOIN=1 joins the first realm offered)
                if (_raceChosen && !_joinAnswered && control.GetType().Name == "ListPrompt" && Member(control, "_itemList") is ItemList joins && joins.Any(item => item.Text == "Found my own land")) {
                    var pick = Environment.GetEnvironmentVariable("DM_TEST_JOIN") == "1" ? joins.FirstOrDefault(item => item.Text.StartsWith("Join ")) : null;
                    foreach (var item in joins) item.Selected = pick != null ? item == pick : item.Text == "Found my own land";
                    control.GetType().GetMethod("OkButtonClicked", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(control, null);
                    control.GetType().GetMethod("Close")!.Invoke(control, null);
                    _joinAnswered = true;
                    System.Console.WriteLine($"[INFO] mac.webview: smoke test answered the realm prompt: {(pick != null ? pick.Text : "Found my own land")}");
                    return;
                }
                if (_raceChosen && control.GetType().Name == "AlertWindow") {
                    control.GetType().GetMethod("ButtonClicked", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(control, new object[] {"Ok"});
                    return;
                }
                if (_raceChosen) continue;
                if (control.GetType().Name != "ListPrompt" || Member(control, "_itemList") is not ItemList items) continue;
                if (!items.Any(item => item.Text == race)) continue;
                foreach (var item in items) item.Selected = item.Text == race;
                control.GetType().GetMethod("OkButtonClicked", BindingFlags.Instance | BindingFlags.NonPublic)!.Invoke(control, null);
                control.GetType().GetMethod("Close")!.Invoke(control, null);
                _raceChosen = true;
                System.Console.WriteLine($"[INFO] mac.webview: smoke test chose {race} through the race prompt");
                return;
            }
        }
    }
    private static IEnumerable<Control> Descendants(Control root) {
        yield return root;
        foreach (var child in root.Children)
            foreach (var nested in Descendants(child)) yield return nested;
    }
    private void FitEmbeddedPanes() {
        _interfaceType ??= IoCManager.Resolve<IReflectionManager>()
            .GetType("OpenDreamClient.Interface.IDreamInterfaceManager");
        if (_interfaceType == null) return;
        var manager = IoCManager.ResolveType(_interfaceType);
        if (Member(manager, "Windows") is not IDictionary windows) return;
        if (!_layoutReported && windows.Count > 0) {
            _layoutReported = true;
            System.Console.WriteLine($"[INFO] mac.webview: checking {windows.Count} interface windows for embedded layout");
        }
        foreach (DictionaryEntry entry in windows) {
            var window = entry.Value!;
            var descriptor = Member(window, "WindowDescriptor");
            var pane = descriptor == null ? null : Member(descriptor, "IsPane");
            if (pane != null && Member(pane, "Value") is true &&
                Member(window, "UIElement") is Control control) {
            if (_panesChecked.Add(entry.Key.ToString()!))
                System.Console.WriteLine($"[INFO] mac.webview: fitting embedded pane {entry.Key}");
            // A pane's DMF size is its anchor design size, not a fixed size in
            // its splitter. Keep descriptors intact and let the parent arrange it.
            if (!float.IsNaN(control.SetWidth) || !float.IsNaN(control.SetHeight)) {
                control.SetWidth = float.NaN;
                control.SetHeight = float.NaN;
            }
            }
            if (Member(window, "ChildControls") is not IEnumerable children) continue;
            foreach (var child in children) {
                if (Member(child!, "Size") is not object size ||
                    Member(child!, "UIElement") is not Control element ||
                    element.Parent is not LayoutContainer canvas) continue;
                var x = (int)Member(size, "X")!;
                var y = (int)Member(size, "Y")!;
                var auto = _autoFill.GetValueOrDefault(entry.Key+"."+element.Name, (x == 0, y == 0));
                if (auto.Item1) element.SetWidth = Math.Max(0, canvas.Width - element.GetValue<float>(LayoutContainer.MarginLeftProperty));
                if (auto.Item2) element.SetHeight = Math.Max(0, canvas.Height - element.GetValue<float>(LayoutContainer.MarginTopProperty));
            }
        }
    }
    private static object? Member(object value, string name) {
        const BindingFlags flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
        var type = value.GetType();
        return type.GetProperty(name, flags)?.GetValue(value)
            ?? type.GetField(name, flags)?.GetValue(value)
            ?? type.GetMethod("get_"+name, flags)?.Invoke(value, null);
    }
    public void Shutdown() {
        foreach (var browser in Browsers.Values.ToArray()) browser.Dispose();
    }
    public IWebViewControlImpl MakeControlImpl(WebViewControl owner) => new MacControl(this, owner);
    public IWebViewWindow CreateBrowserWindow(BrowserWindowCreateParameters parameters) {
        var browser = new MacWindow(this, parameters.Width, parameters.Height);
        browser.Url = parameters.Url;
        return browser;
    }
    public void SetResourceMimeType(string extension, string mimeType) => _mime[extension] = mimeType;
    public bool TryGetResourceMimeType(string extension, [NotNullWhen(true)] out string? mimeType) => _mime.TryGetValue(extension, out mimeType);

    internal abstract class MacBrowser : IWebViewControl, IDisposable {
        protected readonly MacWebViewManager Manager;
        protected long Id;
        private string _url = "about:blank";
        protected readonly List<Action<IRequestHandlerContext>> Requests = new();
        protected readonly List<Action<IBeforeBrowseContext>> Navigation = new();
        public bool IsLoading { get; private set; }
        public bool HasLoaded { get; private set; }
        public bool Closed { get; private set; }
        public string Url {
            get => _url;
            set {
                _url = value;
                IsLoading = true;
                Native.dm_web_load(Id, value);
            }
        }
        protected MacBrowser(MacWebViewManager manager, int width = 0, int height = 0) {
            Manager = manager;
            Id = Native.dm_web_create(width, height);
            manager.Browsers.Add(Id, this);
        }
        public virtual void Receive(int kind, long request, string text) {
            switch (kind) {
                case 1: {
                    var context = new RequestContext(text);
                    foreach (var handler in Requests.ToArray()) {
                        handler(context);
                        if (context.IsHandled || context.IsCancelled) break;
                    }
                    using var content = context.Content;
                    using var memory = new MemoryStream();
                    content?.CopyTo(memory);
                    var bytes = memory.ToArray();
                    Native.dm_web_respond(Id, request, bytes, bytes.Length,
                        context.ContentType ?? "text/plain", context.IsHandled ? (int)context.Status : 404);
                    System.Console.WriteLine($"[INFO] mac.webview: resource {text} status={(context.IsHandled ? (int)context.Status : 404)} bytes={bytes.Length}");
                    break;
                }
                case 2: {
                    var context = new NavigationContext(text);
                    foreach (var handler in Navigation.ToArray()) {
                        handler(context);
                        if (context.IsCancelled) break;
                    }
                    System.Console.WriteLine($"[INFO] mac.webview: navigation {text} handled={context.IsCancelled}");
                    if (!context.IsCancelled) Url = text;
                    break;
                }
                case 3:
                    IsLoading = false;
                    HasLoaded = true;
                    System.Console.WriteLine($"[INFO] mac.webview: loaded panel={Id} url={Url}" +
                        (Environment.GetEnvironmentVariable("DM_WEBVIEW_TEST") == "1" ? $" DOM={text}" : ""));
                    if (Environment.GetEnvironmentVariable("DM_WEBVIEW_TEST") == "1") {
                        if (text.Contains("FOUNDATION BROWSER TEST"))
                            ExecuteJavaScript("document.getElementById('topic-test').click()");
                        if (text.Contains("FOUNDATION BROWSER RESPONSE")) {
                            Native.dm_web_snapshot(Id, Environment.GetEnvironmentVariable("DM_WEBVIEW_SNAPSHOT") ?? "/private/tmp/dm-webkit-test.png");
                        }
                        if (text.Contains("FOUNDATION NAMED PANEL"))
                            ExecuteJavaScript("document.getElementById('close-test').click()");
                    }
                    break;
                case 4:
                    IsLoading = false;
                    System.Console.WriteLine($"[ERRO] mac.webview: {text}");
                    break;
                case 5:
                    System.Console.WriteLine($"[INFO] mac.webview: panel={Id} {text}");
                    break;
            }
        }
        public virtual void Layout() { }
        public void StopLoad() => Native.dm_web_history(Id, 0);
        public void Reload() => Native.dm_web_history(Id, 2);
        public bool GoBack() { Native.dm_web_history(Id, -1); return true; }
        public bool GoForward() { Native.dm_web_history(Id, 1); return true; }
        public void ExecuteJavaScript(string code) {
            // Read-only test telemetry: retain the exact existing server HUD
            // output. No commands are injected and normal launches do no I/O.
            var probe = Environment.GetEnvironmentVariable("DM_NATIVE_UI_PROBE");
            if (!string.IsNullOrEmpty(probe) && (code.Contains("updateHUD(") || code.Contains("update3D("))) {
                Directory.CreateDirectory(probe);
                var path = Path.Combine(probe, code.Contains("update3D(") ? (code.Contains("terrain") ? "hud-3d-terrain.js" : "hud-3d.js") : "hud-update.js");
                File.WriteAllText(path + ".pending", code);
                File.Move(path + ".pending", path, true);
            }
            Native.dm_web_script(Id, code);
        }
        public void AddResourceRequestHandler(Action<IRequestHandlerContext> handler) => Requests.Add(handler);
        public void RemoveResourceRequestHandler(Action<IRequestHandlerContext> handler) => Requests.Remove(handler);
        public void Dispose() {
            if (Closed) return;
            Closed = true;
            Manager.Browsers.Remove(Id);
            Native.dm_web_destroy(Id);
        }
    }

    private sealed class MacControl : MacBrowser, IWebViewControlImpl {
        private readonly WebViewControl _owner;
        private bool _nativeFocus;
        public bool IsOpen { get; private set; }
        public MacControl(MacWebViewManager manager, WebViewControl owner) : base(manager) { _owner = owner; }
        public override void Layout() {
            var pos = _owner.GlobalPixelPosition;
            var size = _owner.PixelSize;
            var window = _owner.Window;
            uint sdlId = 0;
            if (window != null && !window.IsDisposed) {
                // WindowHandle and its SDL register are private engine types.
                // Resolve the real NSWindow, never a possibly empty/repeated title.
                var reg = window.GetType().GetField("Reg", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)?.GetValue(window);
                var number = reg?.GetType().GetField("WindowId", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)?.GetValue(reg);
                if (number is uint value) sdlId = value;
            }
            Native.dm_web_layout(Id, sdlId, window?.Size.X ?? 0, window?.Size.Y ?? 0, pos.X, pos.Y, size.X, size.Y,
                IsOpen && _owner.VisibleInTree ? 1 : 0);
        }
        public override void Receive(int kind, long request, string text) {
            if (kind == 7) {
                // Transparent HUD over the game: clicks the page does not claim
                // must reach the map control underneath, not this placeholder.
                _owner.MouseFilter = Control.MouseFilterMode.Ignore;
                // OpenDream's browser control always paints a white panel behind
                // the page; an overlay must show the map through it instead.
                if (_owner.Parent is PanelContainer panel) {
                    panel.PanelOverride = new StyleBoxFlat(Robust.Shared.Maths.Color.Transparent);
                    panel.MouseFilter = Control.MouseFilterMode.Ignore;
                }
                System.Console.WriteLine($"[INFO] mac.webview: overlay panel={Id}");
                return;
            }
            if (kind != 6) { base.Receive(kind, request, text); return; }
            _nativeFocus = text == "1";
            if (_nativeFocus) _owner.GrabKeyboardFocus();
            else if (_owner.HasKeyboardFocus()) _owner.ReleaseKeyboardFocus();
        }
        public void StartBrowser() { IsOpen = true; }
        public void CloseBrowser() {
            IsOpen = false;
            Native.dm_web_layout(Id, 0, 0, 0, 0, 0, 0, 0, 0);
        }
        // AppKit delivers pointer, keyboard, scrolling, selection and IME events
        // directly to the embedded native view. Do not send duplicate SDL events.
        public void MouseMove(GUIMouseMoveEventArgs args) { }
        public void MouseExited() { }
        public void MouseWheel(GUIMouseWheelEventArgs args) { }
        public bool RawKeyEvent(in GuiRawKeyEvent args) => _nativeFocus;
        public void TextEntered(GUITextEnteredEventArgs args) { }
        public void Resized() => Layout();
        public void Draw(DrawingHandleScreen handle) { }
        public void AddBeforeBrowseHandler(Action<IBeforeBrowseContext> handler) => Navigation.Add(handler);
        public void RemoveBeforeBrowseHandler(Action<IBeforeBrowseContext> handler) => Navigation.Remove(handler);
        public void FocusEntered() { }
        public void FocusExited() { }
    }
    private sealed class MacWindow : MacBrowser, IWebViewWindow {
        public MacWindow(MacWebViewManager manager, int width, int height) : base(manager, width, height) { }
    }
    private sealed class RequestContext(string url) : IRequestHandlerContext {
        public bool IsNavigation => true;
        public bool IsDownload => false;
        public string RequestInitiator => "http://127.0.0.1";
        public string Url => url;
        public string Method => "GET";
        public bool IsHandled { get; private set; }
        public bool IsCancelled { get; private set; }
        public Stream? Content;
        public string? ContentType;
        public HttpStatusCode Status;
        public void DoCancel() { IsCancelled = true; }
        public void DoRespondStream(Stream stream, string contentType, HttpStatusCode code = HttpStatusCode.OK) {
            Content = stream; ContentType = contentType; Status = code; IsHandled = true;
        }
    }
    private sealed class NavigationContext(string url) : IBeforeBrowseContext {
        public string Url => url;
        public string Method => "GET";
        public bool IsRedirect => false;
        public bool UserGesture => true;
        public bool IsCancelled { get; private set; }
        public void DoCancel() { IsCancelled = true; }
    }
    private static class Native {
        private const string Library = "dmwebkit";
        [UnmanagedFunctionPointer(CallingConvention.Cdecl)]
        public delegate void EventCallback(long panel, int kind, long request, IntPtr text);
        [DllImport(Library)] public static extern void dm_web_initialize(EventCallback callback, [MarshalAs(UnmanagedType.LPUTF8Str)] string sdlLibrary);
        [DllImport(Library)] public static extern long dm_web_create(int width, int height);
        [DllImport(Library)] public static extern void dm_web_load(long panel, [MarshalAs(UnmanagedType.LPUTF8Str)] string url);
        [DllImport(Library)] public static extern void dm_web_layout(long panel, uint window, double pixelWidth, double pixelHeight, double x, double y, double width, double height, int visible);
        [DllImport(Library)] public static extern void dm_web_respond(long panel, long request, byte[] bytes, int length, [MarshalAs(UnmanagedType.LPUTF8Str)] string mime, int status);
        [DllImport(Library)] public static extern void dm_web_script(long panel, [MarshalAs(UnmanagedType.LPUTF8Str)] string code);
        [DllImport(Library)] public static extern void dm_web_history(long panel, int action);
        [DllImport(Library)] public static extern void dm_web_destroy(long panel);
        [DllImport(Library)] public static extern void dm_web_snapshot(long panel, [MarshalAs(UnmanagedType.LPUTF8Str)] string path);
    }
}
