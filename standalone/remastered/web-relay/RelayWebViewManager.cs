// Dungeon Master Remastered: the engine's WebView module for playing in a web browser.
//
// The Mac client hosts remastered.html in a native WebKit panel (mac-webview/). This
// module takes the same place in a headless client (Robust.Client.dll --headless) and
// instead serves that page to a real browser over HTTP, with a WebSocket carrying the
// game's output() calls in and the page's byond:// commands out. One headless client
// runs per web player, next to the server (planning/WEB_CLIENT.md).
//
//   DM_WEB_RELAY_PORT   port to listen on (required; without it the module stays idle)
//   DM_WEB_RELAY_BIND   "127.0.0.1" (default) or "*" for every interface
//   DM_JOIN_PASSWORD    answers the world's "Join password" prompt, as the Mac client does
//   DM_WEB_RELAY_IDLE   seconds without a browser before the client quits (default 90)
using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics.CodeAnalysis;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.WebSockets;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using Robust.Client;
using Robust.Client.Graphics;
using Robust.Client.Input;
using Robust.Client.UserInterface;
using Robust.Client.UserInterface.Controls;
using Robust.Client.WebViewHook;
using Robust.Shared.Configuration;
using Robust.Shared.IoC;
using Robust.Shared.Reflection;

[assembly: WebViewManagerImpl(typeof(Robust.Client.WebView.RelayWebViewManager))]

namespace Robust.Client.WebView;

internal sealed class RelayWebViewManager : IWebViewManagerInternal, IWebViewManagerHook {
    internal readonly List<RelayBrowser> Browsers = new();
    private readonly Dictionary<string, string> _mime = new();
    private readonly ConcurrentQueue<Action> _mainThread = new();
    private readonly List<RelaySocket> _sockets = new();
    private readonly object _socketLock = new();
    private RelayServer? _server;
    private RelayPrompts? _prompts;
    private DateTime _started, _lastSocket;
    private bool _everConnected, _quitting;
    private int _idleSeconds = 90;

    public void PreInitialize(IDependencyCollection dependencies, GameController.DisplayMode mode) {
        dependencies.Resolve<IConfigurationManagerInternal>().LoadCVarsFromAssembly(typeof(RelayWebViewManager).Assembly);
        dependencies.Resolve<IReflectionManager>().LoadAssemblies(typeof(RelayWebViewManager).Assembly);
        dependencies.RegisterInstance<IWebViewManager>(this);
        dependencies.RegisterInstance<IWebViewManagerInternal>(this);
        if (mode == GameController.DisplayMode.Headless) HeadlessGL.Install();
    }

    public void Initialize() {
        _started = _lastSocket = DateTime.UtcNow;
        if (int.TryParse(Environment.GetEnvironmentVariable("DM_WEB_RELAY_IDLE"), out var idle) && idle > 0) _idleSeconds = idle;
        var port = Environment.GetEnvironmentVariable("DM_WEB_RELAY_PORT");
        if (!int.TryParse(port, out var number) || number <= 0) {
            Log("DM_WEB_RELAY_PORT is not set; the web relay stays idle");
            return;
        }
        var bind = Environment.GetEnvironmentVariable("DM_WEB_RELAY_BIND");
        if (string.IsNullOrWhiteSpace(bind)) bind = "127.0.0.1";
        _prompts = new RelayPrompts(this);
        _server = new RelayServer(this, bind, number);
        _server.Start();
        Log($"listening on http://{bind}:{number}/");
    }

    public void Update() {
        while (_mainThread.TryDequeue(out var work)) {
            try { work(); }
            catch (Exception error) { Log($"error: {error}"); }
        }
        _prompts?.Update();
        if (_server != null) RelayView.Refresh();
        QuitWhenAbandoned();
    }

    public void Shutdown() => _server?.Stop();

    public IWebViewControlImpl MakeControlImpl(WebViewControl owner) => new RelayControl(this, owner);
    public IWebViewWindow CreateBrowserWindow(BrowserWindowCreateParameters parameters) {
        var window = new RelayWindow(this) { Url = parameters.Url };
        return window;
    }
    public void SetResourceMimeType(string extension, string mimeType) => _mime[extension] = mimeType;
    public bool TryGetResourceMimeType(string extension, [NotNullWhen(true)] out string? mimeType) => _mime.TryGetValue(extension, out mimeType);

    // ---- page <-> game -------------------------------------------------------------

    internal static void Log(string text) => System.Console.WriteLine($"[INFO] web.relay: {text}");
    internal void RunOnMainThread(Action work) => _mainThread.Enqueue(work);
    internal Task<T> OnMainThread<T>(Func<T> work) {
        var done = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
        _mainThread.Enqueue(() => {
            try { done.SetResult(work()); }
            catch (Exception error) { done.SetException(error); }
        });
        return done.Task;
    }

    /// <summary>The browser control that shows the HUD page (mapwindow.hud): the first one given a page URL.</summary>
    internal RelayBrowser? Page => Browsers.FirstOrDefault(b => b.IsPage && !b.Closed);

    internal void Script(RelayBrowser browser, string code) {
        if (browser != Page) return;    // the Announcement/ChatLog/EmoteLog windows are not shown in the browser yet
        Broadcast(code, cache: true);
    }

    internal void Broadcast(string code, bool cache) => BroadcastRaw(JsonSerializer.Serialize(new { js = code }));

    /// <summary>One message to every open tab of this player.</summary>
    internal void BroadcastRaw(string json) {
        RelaySocket[] targets;
        lock (_socketLock) targets = _sockets.ToArray();
        foreach (var socket in targets) socket.Send(json);
    }

    internal void SendTo(RelaySocket socket, object message) => socket.Send(JsonSerializer.Serialize(message));

    internal void SocketOpened(RelaySocket socket) {
        lock (_socketLock) _sockets.Add(socket);
        _everConnected = true;
        _lastSocket = DateTime.UtcNow;
        Log("browser connected");
    }

    internal void SocketReady(RelaySocket socket) {
        // The page's own "ready" command makes the server send the HUD and the whole
        // 3D scene again (HUD.dm), so only open questions need repeating here.
        RunOnMainThread(() => _prompts?.Resend(socket));
    }

    internal void SocketClosed(RelaySocket socket) {
        lock (_socketLock) _sockets.Remove(socket);
        _lastSocket = DateTime.UtcNow;
        Log("browser disconnected");
    }

    internal void Receive(RelaySocket socket, string text) {
        JsonDocument document;
        try { document = JsonDocument.Parse(text); }
        catch (JsonException) { return; }
        using (document) {
            var root = document.RootElement;
            if (root.TryGetProperty("ready", out _)) { SocketReady(socket); return; }
            if (root.TryGetProperty("nav", out var nav) && nav.ValueKind == JsonValueKind.String) {
                var url = nav.GetString()!;
                RunOnMainThread(() => Page?.Navigate(url));
                return;
            }
            if (root.TryGetProperty("prompt", out var prompt) && prompt.ValueKind == JsonValueKind.Object) {
                var id = prompt.TryGetProperty("id", out var idValue) ? idValue.GetInt32() : 0;
                var cancel = prompt.TryGetProperty("cancel", out var c) && c.ValueKind == JsonValueKind.True;
                var button = prompt.TryGetProperty("button", out var b) && b.ValueKind == JsonValueKind.String ? b.GetString() : null;
                var value = prompt.TryGetProperty("value", out var v) ? v.Clone() : default;
                RunOnMainThread(() => _prompts?.Answer(id, cancel, button, value));
                return;
            }
            if (root.TryGetProperty("cmd", out var cmd) && cmd.ValueKind == JsonValueKind.String) {
                var command = cmd.GetString()!;
                RunOnMainThread(() => RunSkinCommand(command));
                return;
            }
            if (root.TryGetProperty("key", out var key) && key.ValueKind == JsonValueKind.Object) {
                var code = key.TryGetProperty("code", out var codeValue) ? codeValue.GetString() ?? "" : "";
                var down = key.TryGetProperty("down", out var downValue) && downValue.ValueKind == JsonValueKind.True;
                var alt = key.TryGetProperty("alt", out var a) && a.ValueKind == JsonValueKind.True;
                var ctrl = key.TryGetProperty("ctrl", out var ct) && ct.ValueKind == JsonValueKind.True;
                var shift = key.TryGetProperty("shift", out var s) && s.ValueKind == JsonValueKind.True;
                RunOnMainThread(() => RelayKeys.Inject(code, down, alt, ctrl, shift));
            }
        }
    }

    /// <summary>Run a skin command (a verb name, ".winset ...") the way a macro does: through OpenDream's interface manager.</summary>
    internal static void RunSkinCommand(string command) {
        var type = IoCManager.Resolve<IReflectionManager>().GetType("OpenDreamClient.Interface.IDreamInterfaceManager");
        if (type == null) { Log("IDreamInterfaceManager not found"); return; }
        var manager = IoCManager.ResolveType(type);
        var run = type.GetMethod("RunCommand");
        if (run == null) { Log("RunCommand not found"); return; }
        run.Invoke(manager, new object[] { command, false });
        if (Environment.GetEnvironmentVariable("DM_WEB_RELAY_TRACE") != null) Log($"ran command {command}");
    }

    /// <summary>Resolve a page resource (the HUD page itself, portraits, textures, model json) through the control's handlers.</summary>
    internal Task<RelayResponse> Resource(string path) => OnMainThread(() => {
        var page = Page;
        if (page == null) return new RelayResponse(HttpStatusCode.ServiceUnavailable, "text/plain", Array.Empty<byte>());
        var url = "http://127.0.0.1/" + path.TrimStart('/');
        var context = new RequestContext(url);
        foreach (var handler in page.Requests.ToArray()) {
            handler(context);
            if (context.IsHandled || context.IsCancelled) break;
        }
        if (!context.IsHandled) return new RelayResponse(HttpStatusCode.NotFound, "text/plain", Array.Empty<byte>());
        using var content = context.Content;
        using var memory = new MemoryStream();
        content?.CopyTo(memory);
        var type = context.ContentType ?? "application/octet-stream";
        if (type == "application/octet-stream" || type == "text/plain") {
            var extension = Path.GetExtension(path).TrimStart('.');
            if (extension.Length > 0 && _mime.TryGetValue(extension, out var known)) type = known;
            else type = RelayServer.MimeFor(extension, type);
        }
        return new RelayResponse(context.Status, type, memory.ToArray());
    });

    private void QuitWhenAbandoned() {
        if (_quitting || _server == null) return;
        int open;
        lock (_socketLock) open = _sockets.Count;
        if (open > 0) { _lastSocket = DateTime.UtcNow; return; }
        var since = (DateTime.UtcNow - (_everConnected ? _lastSocket : _started)).TotalSeconds;
        var limit = _everConnected ? _idleSeconds : Math.Max(_idleSeconds, 180);
        if (since < limit) return;
        _quitting = true;
        Log(_everConnected ? "the browser left; quitting" : "no browser came; quitting");
        IoCManager.Resolve<IGameController>().Shutdown("web player left");
    }

    // ---- browsers ------------------------------------------------------------------

    internal abstract class RelayBrowser : IWebViewControl {
        protected readonly RelayWebViewManager Manager;
        private string _url = "about:blank";
        internal readonly List<Action<IRequestHandlerContext>> Requests = new();
        internal readonly List<Action<IBeforeBrowseContext>> Navigation = new();
        public bool IsLoading => false;
        public bool Closed { get; protected set; }
        /// <summary>Set once the game pointed this browser at a cached page (http://127.0.0.1/...).</summary>
        public bool IsPage { get; private set; }
        public string PagePath { get; private set; } = "";
        public string Url {
            get => _url;
            set {
                _url = value;
                if (Uri.TryCreate(value, UriKind.Absolute, out var uri) && uri.Scheme == "http" && uri.Host == "127.0.0.1") {
                    IsPage = true;
                    PagePath = uri.AbsolutePath.TrimStart('/');
                    Log($"page {PagePath}");
                }
            }
        }
        protected RelayBrowser(RelayWebViewManager manager) {
            Manager = manager;
            manager.Browsers.Add(this);
        }
        /// <summary>A byond:// link clicked in the browser: the same handlers the WebKit view ran (Topic, winset, winget).</summary>
        internal void Navigate(string url) {
            var context = new NavigationContext(url);
            foreach (var handler in Navigation.ToArray()) {
                handler(context);
                if (context.IsCancelled) break;
            }
            if (!context.IsCancelled) Url = url;
        }
        public void StopLoad() { }
        public void Reload() { }
        public bool GoBack() => false;
        public bool GoForward() => false;
        public void ExecuteJavaScript(string code) => Manager.Script(this, code);
        public void AddResourceRequestHandler(Action<IRequestHandlerContext> handler) => Requests.Add(handler);
        public void RemoveResourceRequestHandler(Action<IRequestHandlerContext> handler) => Requests.Remove(handler);
    }

    internal sealed class RelayControl : RelayBrowser, IWebViewControlImpl {
        private readonly WebViewControl _owner;
        public RelayControl(RelayWebViewManager manager, WebViewControl owner) : base(manager) { _owner = owner; }
        public bool IsOpen { get; private set; }
        public void StartBrowser() { IsOpen = true; }
        public void CloseBrowser() { IsOpen = false; Closed = true; Manager.Browsers.Remove(this); }
        public void MouseMove(GUIMouseMoveEventArgs args) { }
        public void MouseExited() { }
        public void MouseWheel(GUIMouseWheelEventArgs args) { }
        public bool RawKeyEvent(in GuiRawKeyEvent args) => false;
        public void TextEntered(GUITextEnteredEventArgs args) { }
        public void Resized() { }
        public void Draw(DrawingHandleScreen handle) { }
        public void AddBeforeBrowseHandler(Action<IBeforeBrowseContext> handler) => Navigation.Add(handler);
        public void RemoveBeforeBrowseHandler(Action<IBeforeBrowseContext> handler) => Navigation.Remove(handler);
        public void FocusEntered() { }
        public void FocusExited() { }
    }

    internal sealed class RelayWindow : RelayBrowser, IWebViewWindow {
        public RelayWindow(RelayWebViewManager manager) : base(manager) { }
        public void Dispose() { Closed = true; Manager.Browsers.Remove(this); }
    }

    internal sealed class RequestContext : IRequestHandlerContext {
        private readonly string _url;
        public RequestContext(string url) { _url = url; }
        public bool IsNavigation => false;
        public bool IsDownload => false;
        public string RequestInitiator => "";
        public string Url => _url;
        public string Method => "GET";
        public bool IsHandled { get; private set; }
        public bool IsCancelled { get; private set; }
        public Stream? Content { get; private set; }
        public string? ContentType { get; private set; }
        public HttpStatusCode Status { get; private set; } = HttpStatusCode.OK;
        public void DoCancel() { IsCancelled = true; }
        public void DoRespondStream(Stream stream, string contentType, HttpStatusCode code = HttpStatusCode.OK) {
            IsHandled = true; Content = stream; ContentType = contentType; Status = code;
        }
    }

    internal sealed class NavigationContext : IBeforeBrowseContext {
        public NavigationContext(string url) { Url = url; }
        public string Url { get; }
        public string Method => "GET";
        public bool IsRedirect => false;
        public bool UserGesture => true;
        public bool IsCancelled { get; private set; }
        public void DoCancel() { IsCancelled = true; }
    }
}

internal readonly record struct RelayResponse(HttpStatusCode Status, string ContentType, byte[] Body);

/// <summary>The HTTP and WebSocket side: serves the page and its files, keeps one socket per open tab.</summary>
internal sealed class RelayServer {
    private readonly RelayWebViewManager _manager;
    private readonly HttpListener _listener = new();
    private readonly CancellationTokenSource _stop = new();
    private static readonly Regex SendPattern = new(@"function send\(action,value\)\{window\.location\.href=(.*?)\}", RegexOptions.Compiled);

    public RelayServer(RelayWebViewManager manager, string bind, int port) {
        _manager = manager;
        _listener.Prefixes.Add($"http://{bind}:{port}/");
    }

    public void Start() {
        _listener.Start();
        _ = Task.Run(AcceptLoop);
    }

    public void Stop() {
        _stop.Cancel();
        try { _listener.Stop(); } catch (ObjectDisposedException) { }
    }

    private async Task AcceptLoop() {
        while (!_stop.IsCancellationRequested) {
            HttpListenerContext context;
            try { context = await _listener.GetContextAsync(); }
            catch (Exception) when (_stop.IsCancellationRequested) { return; }
            catch (Exception error) { RelayWebViewManager.Log($"accept failed: {error.Message}"); continue; }
            _ = Task.Run(() => Handle(context));
        }
    }

    private async Task Handle(HttpListenerContext context) {
        var path = context.Request.Url?.AbsolutePath ?? "/";
        try {
            if (path == "/ws") {
                if (!context.Request.IsWebSocketRequest) { await Text(context, HttpStatusCode.BadRequest, "websocket expected"); return; }
                var upgrade = await context.AcceptWebSocketAsync(null);
                var socket = new RelaySocket(_manager, upgrade.WebSocket);
                await socket.Run(_stop.Token);
                return;
            }
            if (path == "/" || path == "/index.html") { await ServePage(context); return; }
            if (path == "/health") { await Text(context, HttpStatusCode.OK, _manager.Page != null ? "ready" : "starting"); return; }
            if (path == "/favicon.ico") { await Bytes(context, HttpStatusCode.NoContent, "image/x-icon", Array.Empty<byte>()); return; }
            var resource = await _manager.Resource(Uri.UnescapeDataString(path));
            await Bytes(context, resource.Status, resource.ContentType, resource.Body);
        } catch (Exception error) {
            RelayWebViewManager.Log($"request {path} failed: {error.Message}");
            try { context.Response.Abort(); } catch (Exception) { }
        }
    }

    private async Task ServePage(HttpListenerContext context) {
        var page = _manager.Page;
        if (page == null) {
            await Text(context, HttpStatusCode.OK, RelayShim.Waiting, "text/html");
            return;
        }
        var resource = await _manager.Resource(page.PagePath);
        if (resource.Status != HttpStatusCode.OK) {
            await Text(context, HttpStatusCode.OK, RelayShim.Waiting, "text/html");
            return;
        }
        var html = Encoding.UTF8.GetString(resource.Body);
        // byond:// links become socket messages; the chat mirror no longer needs the native overlay host.
        var patched = SendPattern.Replace(html, "function send(action,value){__relayNav($1)}", 1);
        if (patched == html) RelayWebViewManager.Log("warning: send() was not found in the page; falling back to the shim's copy");
        patched = patched.Replace("window.remasterChat=function(lines){if(!overlayHost)return;", "window.remasterChat=function(lines){");
        // The layered HUD (the .ovonly panels) is only built for the overlay host; a browser tab is one too.
        var host = Regex.Replace(patched, @"const overlayHost=!!\(window\.webkit[^;]*;", "const overlayHost=true;", RegexOptions.None, TimeSpan.FromSeconds(2));
        if (host == patched) RelayWebViewManager.Log("warning: overlayHost was not found in the page; the classic layout will show");
        patched = host;
        var early = "<script>" + RelayShim.Early + "</script>";
        var head = patched.IndexOf("<head>", StringComparison.OrdinalIgnoreCase);
        patched = head >= 0 ? patched.Insert(head + "<head>".Length, early) : early + patched;
        var shim = "<script>" + RelayShim.Script + "</script>";
        var end = patched.LastIndexOf("</body>", StringComparison.OrdinalIgnoreCase);
        patched = end >= 0 ? patched.Insert(end, shim) : patched + shim;
        await Text(context, HttpStatusCode.OK, patched, "text/html");
    }

    private static Task Text(HttpListenerContext context, HttpStatusCode status, string text, string type = "text/plain")
        => Bytes(context, status, type + "; charset=utf-8", Encoding.UTF8.GetBytes(text));

    private static async Task Bytes(HttpListenerContext context, HttpStatusCode status, string type, byte[] body) {
        var response = context.Response;
        response.StatusCode = (int)status;
        response.ContentType = type;
        response.ContentLength64 = body.Length;
        response.Headers["Cache-Control"] = "no-store";
        await response.OutputStream.WriteAsync(body, 0, body.Length);
        response.Close();
    }

    internal static string MimeFor(string extension, string fallback) => extension.ToLowerInvariant() switch {
        "png" => "image/png", "jpg" or "jpeg" => "image/jpeg", "gif" => "image/gif", "webp" => "image/webp", "svg" => "image/svg+xml",
        "json" => "application/json", "js" => "text/javascript", "css" => "text/css", "html" or "htm" => "text/html",
        "ogg" => "audio/ogg", "wav" => "audio/wav", "mp3" => "audio/mpeg", "glb" => "model/gltf-binary", "gltf" => "model/gltf+json",
        _ => fallback,
    };
}

internal sealed class RelaySocket {
    private readonly RelayWebViewManager _manager;
    private readonly WebSocket _socket;
    private readonly SemaphoreSlim _sending = new(1, 1);
    public RelaySocket(RelayWebViewManager manager, WebSocket socket) { _manager = manager; _socket = socket; }

    public async Task Run(CancellationToken stop) {
        _manager.SocketOpened(this);
        var buffer = new byte[64 * 1024];
        var text = new MemoryStream();
        try {
            while (_socket.State == WebSocketState.Open && !stop.IsCancellationRequested) {
                var result = await _socket.ReceiveAsync(new ArraySegment<byte>(buffer), stop);
                if (result.MessageType == WebSocketMessageType.Close) break;
                text.Write(buffer, 0, result.Count);
                if (!result.EndOfMessage) continue;
                _manager.Receive(this, Encoding.UTF8.GetString(text.GetBuffer(), 0, (int)text.Length));
                text.SetLength(0);
            }
        } catch (Exception) { /* the tab went away */ }
        finally {
            _manager.SocketClosed(this);
            try { _socket.Dispose(); } catch (Exception) { }
        }
    }

    public void Send(string message) {
        if (_socket.State != WebSocketState.Open) return;
        var bytes = Encoding.UTF8.GetBytes(message);
        _ = Task.Run(async () => {
            await _sending.WaitAsync();
            try { if (_socket.State == WebSocketState.Open) await _socket.SendAsync(new ArraySegment<byte>(bytes), WebSocketMessageType.Text, true, CancellationToken.None); }
            catch (Exception) { }
            finally { _sending.Release(); }
        });
    }
}

/// <summary>
/// The game's native prompts (input()/alert(): OpenDream's PromptWindow subclasses) shown in the
/// browser instead, and answered through the same FinishPrompt the native buttons call.
/// </summary>
internal sealed class RelayPrompts {
    private readonly RelayWebViewManager _manager;
    private readonly Dictionary<Control, PromptInfo> _open = new();
    private int _nextId;
    private sealed record PromptInfo(int Id, string Kind, string Title, string Message, string[] Buttons, string[] Items, string Value);

    public RelayPrompts(RelayWebViewManager manager) { _manager = manager; }

    public void Update() {
        // Snapshot first: answering a prompt closes its window, which edits the tree being walked.
        var found = new List<Control>();
        foreach (var root in IoCManager.Resolve<IUserInterfaceManager>().AllRoots.ToArray())
            foreach (var control in Descendants(root))
                if (IsPrompt(control)) found.Add(control);
        var alive = new HashSet<Control>(found);
        foreach (var control in found) {
                if (_open.ContainsKey(control)) continue;
                // A prompt's buttons are added after the window is created: describe it once they exist.
                if (!Descendants(control).OfType<Button>().Any()) continue;
                var info = Describe(control, ++_nextId);
                _open[control] = info;
                var password = Environment.GetEnvironmentVariable("DM_JOIN_PASSWORD");
                if (info.Kind == "TextPrompt" && info.Title == "Join password" && !string.IsNullOrEmpty(password)) {
                    Finish(control, "Text", password);
                    RelayWebViewManager.Log("answered the join password prompt");
                    continue;
                }
                Announce(info, null);
            }
        foreach (var gone in _open.Keys.Where(c => !alive.Contains(c) || c.Disposed).ToArray()) {
            Broadcast(new { promptClose = _open[gone].Id });
            _open.Remove(gone);
        }
    }

    public void Resend(RelaySocket socket) {
        foreach (var info in _open.Values) Announce(info, socket);
    }

    private void Announce(PromptInfo info, RelaySocket? only) {
        var message = new { prompt = new { id = info.Id, kind = info.Kind, title = info.Title, message = info.Message, buttons = info.Buttons, items = info.Items, value = info.Value } };
        if (only != null) _manager.SendTo(only, message); else Broadcast(message);
    }

    private void Broadcast(object message) {
        // Every open tab of this player sees the same question.
        _manager.BroadcastRaw(JsonSerializer.Serialize(message));
    }

    public void Answer(int id, bool cancel, string? button, JsonElement value) {
        var entry = _open.FirstOrDefault(pair => pair.Value.Id == id);
        if (entry.Key == null) return;
        var control = entry.Key;
        var info = entry.Value;
        if (cancel) { Finish(control, "Null", null); return; }
        switch (info.Kind) {
            case "AlertWindow": Finish(control, "Text", button ?? info.Buttons.FirstOrDefault() ?? "Ok"); break;
            case "TextPrompt": Finish(control, "Text", value.ValueKind == JsonValueKind.String ? value.GetString() : ""); break;
            case "MessagePrompt": Finish(control, "Message", value.ValueKind == JsonValueKind.String ? value.GetString() : ""); break;
            case "NumberPrompt": {
                float number = 0;
                if (value.ValueKind == JsonValueKind.Number) number = value.GetSingle();
                else if (value.ValueKind == JsonValueKind.String) float.TryParse(value.GetString(), out number);
                Finish(control, "Num", number);
                break;
            }
            case "ListPrompt": {
                var index = value.ValueKind == JsonValueKind.Number ? value.GetInt32() : Array.IndexOf(info.Items, value.ValueKind == JsonValueKind.String ? value.GetString() : null);
                if (index < 0) Finish(control, "Null", null); else Finish(control, "Num", (float)index);
                break;
            }
            default: Finish(control, "Null", null); break;
        }
    }

    private static void Finish(Control control, string type, object? value) {
        var method = BaseNamed(control.GetType(), "PromptWindow")?.GetMethod("FinishPrompt", BindingFlags.Instance | BindingFlags.NonPublic);
        if (method == null) { RelayWebViewManager.Log("FinishPrompt not found"); return; }
        var enumType = method.GetParameters()[0].ParameterType;
        method.Invoke(control, new[] { Enum.Parse(enumType, type), value });
        if (control is OSWindow window) window.Close();
    }

    private static PromptInfo Describe(Control control, int id) {
        var kind = control.GetType().Name;
        var title = control is OSWindow window ? window.Title : "";
        var all = Descendants(control).ToArray();
        // OpenDream's prompt buttons carry their text in a child Label, not in Button.Text.
        var buttons = all.OfType<Button>().Select(b => (b.Text ?? "").Length > 0 ? b.Text! : Descendants(b).OfType<Label>().Select(l => l.Text ?? "").FirstOrDefault(t => t.Length > 0) ?? "")
            .Where(t => t.Length > 0).ToArray();
        var message = all.Where(c => c is Label && !InButton(c)).Cast<Label>().Select(l => l.Text ?? "").FirstOrDefault(t => t.Length > 0)
                      ?? all.OfType<RichTextLabel>().Select(l => l.GetFormattedMessage()?.ToString() ?? "").FirstOrDefault(t => t.Length > 0) ?? "";
        var items = all.OfType<ItemList>().SelectMany(list => list.Select(item => item.Text ?? "")).ToArray();
        var value = all.OfType<LineEdit>().Select(e => e.Text).FirstOrDefault() ?? "";
        return new PromptInfo(id, kind, title, message, buttons, items, value);
    }

    private static bool InButton(Control c) {
        for (var p = c.Parent; p != null; p = p.Parent) if (p is Button) return true;
        return false;
    }
    private static bool IsPrompt(Control control) => BaseNamed(control.GetType(), "PromptWindow") != null;
    private static Type? BaseNamed(Type? type, string name) {
        for (; type != null; type = type.BaseType) if (type.Name == name) return type;
        return null;
    }
    private static IEnumerable<Control> Descendants(Control control) {
        foreach (var child in control.Children) {
            yield return child;
            foreach (var node in Descendants(child)) yield return node;
        }
    }
}

/// <summary>Keys the page does not use itself, replayed into the engine so the skin's macros (Alt+1.. groups, Space, F-keys) still work.</summary>
internal static class RelayKeys {
    public static void Inject(string code, bool down, bool alt, bool ctrl, bool shift) {
        var key = Map(code);
        if (key == Keyboard.Key.Unknown) { if (down) RelayWebViewManager.Log($"key {code} has no engine key"); return; }
        var input = IoCManager.Resolve<IInputManager>();
        // The skin's command input holds the keyboard by default and the engine then keeps every key
        // binding from the game (the Mac client's DreamSeekerKeys works around the same thing).
        // Nothing is typed into native controls here, so no control needs the focus.
        var ui = IoCManager.Resolve<IUserInterfaceManager>();
        var focused = ui.KeyboardFocused?.GetType().Name;
        if (ui.KeyboardFocused != null) ui.ReleaseKeyboardFocus();
        var args = new KeyEventArgs(key, false, alt, ctrl, shift, false, 0);
        if (down) input.KeyDown(args); else input.KeyUp(args);
        if (down && Environment.GetEnvironmentVariable("DM_WEB_RELAY_TRACE") != null)
            RelayWebViewManager.Log($"key {key} down enabled={input.Enabled} context={input.Contexts.ActiveContext.Name} handled={args.Handled} focused={focused ?? "none"}");
    }

    private static Keyboard.Key Map(string code) {
        if (code.StartsWith("Key") && code.Length == 4) return Enum.TryParse<Keyboard.Key>(code.Substring(3), out var letter) ? letter : Keyboard.Key.Unknown;
        if (code.StartsWith("Digit") && code.Length == 6) return Enum.TryParse<Keyboard.Key>("Num" + code[5], out var digit) ? digit : Keyboard.Key.Unknown;
        if (code.StartsWith("Numpad") && code.Length == 7 && char.IsDigit(code[6])) return Enum.TryParse<Keyboard.Key>("NumpadNum" + code[6], out var pad) ? pad : Keyboard.Key.Unknown;
        switch (code) {
            case "ArrowUp": return Keyboard.Key.Up;
            case "ArrowDown": return Keyboard.Key.Down;
            case "ArrowLeft": return Keyboard.Key.Left;
            case "ArrowRight": return Keyboard.Key.Right;
            case "Enter": return Keyboard.Key.Return;
            case "NumpadEnter": return Keyboard.Key.NumpadEnter;
            case "Backspace": return Keyboard.Key.BackSpace;
            case "ShiftLeft": case "ShiftRight": return Keyboard.Key.Shift;
            case "ControlLeft": case "ControlRight": return Keyboard.Key.Control;
            case "AltLeft": case "AltRight": return Keyboard.Key.Alt;
            case "MetaLeft": return Keyboard.Key.LSystem;
            case "MetaRight": return Keyboard.Key.RSystem;
            case "BracketLeft": return Keyboard.Key.LBracket;
            case "BracketRight": return Keyboard.Key.RBracket;
            case "Semicolon": return Keyboard.Key.SemiColon;
            case "Quote": return Keyboard.Key.Apostrophe;
            case "Backslash": return Keyboard.Key.BackSlash;
            case "Backquote": return Keyboard.Key.Tilde;
            case "NumpadAdd": return Keyboard.Key.NumpadAdd;
            case "NumpadSubtract": return Keyboard.Key.NumpadSubtract;
            case "NumpadMultiply": return Keyboard.Key.NumpadMultiply;
            case "NumpadDivide": return Keyboard.Key.NumpadDivide;
            case "NumpadDecimal": return Keyboard.Key.NumpadDecimal;
        }
        // Escape, Space, Tab, Home, End, PageUp, PageDown, Insert, Delete, Minus, Equal, Comma, Period, Slash, F1..F24, CapsLock, Pause
        return Enum.TryParse<Keyboard.Key>(code, out var same) ? same : Keyboard.Key.Unknown;
    }
}
