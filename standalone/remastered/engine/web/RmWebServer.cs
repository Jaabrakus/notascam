// Remastered: browsers play on the server directly (engine/web/, U4 of planning/SERVER_UPGRADES_PLAN_2026-10-30.md).
// Before this, each web player needed a headless game client on the host (web-relay/, 110-300 MB and about half a core
// each) only to turn the server's messages into page calls. Here the server does it: one HTTP and WebSocket port for
// every player, and no 2D entity sync for a browser.
//
//   GET  /                 the lobby: a name, then /join (any other query, such as the page's own ?overlay, is kept);
//                          with sign-in on, a "Sign in" link to RM_WEB_SIGNIN_URL instead
//   GET  /join?name=X      joins as X (client/New, Login on the game thread) and goes to /c/<token>/
//   GET  /join?token=T     joins as the account a sign-in token names (CheckToken; tools/web_token.py makes them)
//   GET  /c/<token>/       the page the game browse()d (RM_WEB_PAGE, or the first window it browses), with the link's
//                          scripts (dmweb-head.js, dmweb.js); a short "joining" page until there is one
//   GET  /c/<token>/<file> a file the game browse_rsc()d for this player (kept while the server runs)
//   GET  /c/<token>/alive  ok while the player is known; 410 once they were let go (the page asks before reconnecting)
//   WS   /c/<token>/ws?v=1 the game's output() calls in, the page's byond:// links, prompt answers and size out
//
//   RM_WEB_PORT   the port (required); RM_WEB_BIND   127.0.0.1 (default) or * for every interface
//   RM_WEB_PAGE   the window the page is browse()d into; RM_WEB_GRACE  seconds a player may be away (default 90)
//   RM_WEB_STATS  seconds between each player's send counts in the log (default 10; 0: none)
//   RM_WEB_SECRET_FILE  a file holding the sign-in secret: sign-in on, a typed name no longer joins (RM_WEB_OPEN=1: both)
//   RM_GUEST            1: with sign-in on, a typed name joins as a guest ("Guest <name> <n>", Guests.dm), at most
//                       RM_GUEST_PER_ADDRESS (2) from one address; accounts may not start with "guest"
//   RM_WEB_SIGNIN_URL   where the lobby's "Sign in" goes; it gets ?return=<this server's /join>, and sends the player
//                       back there with ?token=
//   RM_GUEST_MAX        guests on the server at once (default 10, as Guests.dm RM_GUEST_MAX)
//   RM_GUEST_IDLE       seconds a guest may send no input before they are let go (default 1200; 0: never)
//   RM_WEB_MACROS       the skin's macro set for keys (default the first; RmWebKeys.cs)
//   RM_WEB_DEFLATE      0: never compress the socket (default: when the page says it can inflate)
//   RM_PUBLIC           1: a public server (tools/public_host.py): counted as reached from other computers even when
//                       bound to 127.0.0.1 behind a proxy, so it needs sign-in to start. With a loopback bind it
//                       listens for every Host (http://*:port/: Tailscale Funnel keeps the visitor's Host, which a
//                       127.0.0.1 prefix never matches), so the socket is open on every interface; every connection
//                       not from this computer is refused (403) before anything else, WebSocket upgrades included:
//                       only the proxy on this Mac talks to it. The sign-in return address is always https.
// A server bound to more than this computer (RM_WEB_BIND) needs sign-in, or RM_WEB_OPEN=1 to say a typed name is enough.
//
// Hardening for a public server (10-31, behind Tailscale Funnel's https proxy, so every connection comes from
// 127.0.0.1): a player's address is the last X-Forwarded-For entry when the connection is from this computer
// (ClientAddress), for the guest limits and client.address; guests are counted per address (IPv6 by its /64), in all
// (RM_GUEST_MAX) and joins per address are paced, all on the game thread; each link takes ~30 messages a second from its
// tabs (a burst of 60; more are dropped, and a tab that keeps on for 10 s is closed); at most 3 tabs a player and 600
// sockets in all; a send that takes over 20 s, or a tab too far behind, aborts that socket; a sign-in token is used
// once by its signature's bytes; a guest's connection and files go when the guest does; idle guests are let go.
//
// The socket compressed (10-31): a page whose browser can inflate says so in its hello ("z": 1, DecompressionStream);
// from then on each message goes as a binary frame, its length (4 bytes, big-endian) and then its bytes through one
// deflate stream kept for the tab and flushed after each message, so a message is read as soon as it comes and the
// next one is compressed against the ones before. Done on the tab's own send task, not the game thread. A slow link's
// sends are skipped by the game (rm_web_behind, native version 29); a backlog over 32 MB still closes the socket.
//
// Not yet (the full path): sounds sent as MsgSound, windows other than the page.
using System.Buffers;
using System.Collections.Concurrent;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.WebSockets;
using System.Security.Cryptography;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.RegularExpressions;
using System.Threading;
using System.Threading.Tasks;
using System.Web;
using OpenDreamShared.Dream;
using OpenDreamShared.Network.Messages;
using Robust.Shared.Network;

namespace OpenDreamRuntime;

internal sealed class RmWebServer {
    public const int Protocol = 1;   // the page's scripts and the server must agree (an old page from a browser's cache is told to reload)

    internal readonly DreamManager Manager;
    internal readonly ISawmill Sawmill = Logger.GetSawmill("opendream.web");
    internal readonly string? PageWindow = Environment.GetEnvironmentVariable("RM_WEB_PAGE") is { Length: > 0 } page ? page : null;
    private readonly HttpListener _listener = new();
    private readonly CancellationTokenSource _stop = new();
    private readonly ConcurrentDictionary<string, RmWebLink> _links = new();   // by token
    // each player's browse_rsc files, kept when they leave: the game sends a file to a player once, as a native client
    // keeps its cache (a returning player's textures). The files are the resources' own bytes, not copies.
    internal readonly ConcurrentDictionary<string, ConcurrentDictionary<string, byte[]>> FilesByKey = new();
    private readonly string _prefix;
    private readonly double _grace = double.TryParse(Environment.GetEnvironmentVariable("RM_WEB_GRACE"), out var g) && g > 0 ? g : 90;
    private readonly double _statsEvery = double.TryParse(Environment.GetEnvironmentVariable("RM_WEB_STATS"), out var s) && s >= 0 ? s : 10;
    private DateTime _nextStats = DateTime.UtcNow;
    private DateTime _nextSweep = DateTime.UtcNow;
    private static readonly Regex NamePattern = new(@"^[A-Za-z0-9][A-Za-z0-9 _-]{0,29}\z", RegexOptions.Compiled);
    private static readonly Regex KeyPattern = new(@"^[A-Za-z0-9][A-Za-z0-9 _.@:-]{0,63}\z", RegexOptions.Compiled);   // an account a token names
    private static readonly Regex TokenPart = new(@"^[A-Za-z0-9_-]+\z", RegexOptions.Compiled);   // base64url, no padding or anything else
    private readonly bool _local;
    private readonly bool _public = Environment.GetEnvironmentVariable("RM_PUBLIC") == "1";
    private readonly bool _loopbackOnly;   // RM_PUBLIC with a loopback bind: any Host, but only connections from this computer
    private readonly byte[]? _secret;
    private readonly bool _open = Environment.GetEnvironmentVariable("RM_WEB_OPEN") == "1";
    // Guests (Guests.dm; planning/GUEST_MODE_PLAN_2026-10-31.md): with sign-in on, a typed name joins as "Guest <name> <n>",
    // which the game keeps nothing of; never an account's key, never another guest's session; a few from one address.
    private readonly bool _guest = Environment.GetEnvironmentVariable("RM_GUEST") == "1";
    private readonly int _guestsPerAddress = int.TryParse(Environment.GetEnvironmentVariable("RM_GUEST_PER_ADDRESS"), out var g) && g > 0 ? g : 2;
    private readonly int _guestMax = int.TryParse(Environment.GetEnvironmentVariable("RM_GUEST_MAX"), out var gm) && gm > 0 ? gm : 10;
    private readonly double _guestIdle = double.TryParse(Environment.GetEnvironmentVariable("RM_GUEST_IDLE"), out var gi) && gi >= 0 ? gi : 1200;
    internal readonly bool Deflate = Environment.GetEnvironmentVariable("RM_WEB_DEFLATE") != "0";
    private readonly string? _signIn = Environment.GetEnvironmentVariable("RM_WEB_SIGNIN_URL") is { Length: > 0 } url ? url : null;
    private readonly ConcurrentDictionary<string, long> _usedTokens = new();   // the signature's bytes (hex) -> expiry: a token joins once
    // guest joins per address (its group: IPv6 by /64), paced: a burst of JoinBurst, then one every JoinEvery seconds (game thread)
    private const double JoinBurst = 2, JoinEvery = 10;
    private readonly Dictionary<string, (double Tokens, long At)> _guestJoins = new();
    private const int MaxSocketsTotal = 600;
    private int _socketsOpen;
    private RmWebKeys? _keys;
    private ServerVerbSystem? _verbs;

    public RmWebServer(DreamManager manager, string bind, int port) {
        Manager = manager;
        // RM_PUBLIC=1 (tools/public_host.py): reached from the internet through a proxy on this computer, so not local
        var loopback = bind is "127.0.0.1" or "localhost" or "::1";
        _local = loopback && !_public;
        _loopbackOnly = loopback && _public;   // the proxy keeps the visitor's Host: match any, refuse other computers (Handle)
        _prefix = $"http://{(bind == "*" || _loopbackOnly ? "*" : bind)}:{port}/";
        _listener.Prefixes.Add(_prefix);
        var secretFile = Environment.GetEnvironmentVariable("RM_WEB_SECRET_FILE");
        if (!string.IsNullOrEmpty(secretFile)) {
            var secret = File.ReadAllText(secretFile).Trim();
            if (secret.Length < 32) throw new InvalidOperationException($"the sign-in secret in {secretFile} is shorter than 32 characters");
            _secret = Encoding.UTF8.GetBytes(secret);
        }
    }

    /// <summary>The skin's key table (game thread; read once, on the first page).</summary>
    internal RmWebKeys Keys {
        get {
            if (_keys == null) {
                _keys = new RmWebKeys(IoCManager.Resolve<OpenDreamRuntime.Resources.DreamResourceManager>(),
                    IoCManager.Resolve<Robust.Shared.Serialization.Manager.ISerializationManager>());
                Sawmill.Info($"web: keys: {_keys.Note}");
            }

            return _keys;
        }
    }

    internal ServerVerbSystem? Verbs => _verbs ??= IoCManager.Resolve<IEntitySystemManager>().TryGetEntitySystem<ServerVerbSystem>(out var verbs) ? verbs : null;

    public void Start() {
        if (!_local && _secret == null && !_open)
            throw new InvalidOperationException("a server reached from other computers needs sign-in (RM_WEB_SECRET_FILE), or RM_WEB_OPEN=1 to let a typed name join");
        _listener.Start();
        _ = Task.Run(AcceptLoop);
        // the game asks how far behind a player's tabs are (rm_web_behind, native version 29) and skips that player's next
        // scene while they catch up (OpenRealm's rate), instead of queueing sends until the 32 MB close
        global::OpenDreamRuntime.Procs.Native.RmNative.WebBehind = who => who is global::OpenDreamRuntime.Objects.Types.DreamObjectMob { Connection.RmWeb: { } link } ? link.Behind : 0;
        Sawmill.Info($"web: browsers join at {(_loopbackOnly ? _prefix.Replace("*", "<any host>") + " from this computer only (RM_PUBLIC)" : _prefix.Replace("*", "<this computer>"))} (protocol {Protocol}, page {PageWindow ?? "the first browse()"}, " +
                     $"{(_secret == null ? "a typed name joins" : _open ? "sign-in or a typed name" : "sign-in only")})");
    }

    public void Stop() {
        _stop.Cancel();
        global::OpenDreamRuntime.Procs.Native.RmNative.WebBehind = null;
        foreach (var link in _links.Values)
            link.CloseSockets("The server stopped.");
        try {
            _listener.Stop();
        } catch (ObjectDisposedException) { }
    }

    /// <summary>Each update, on the game thread: players away longer than the grace leave (idle guests too); the send counts.</summary>
    public void Tick() {
        var now = DateTime.UtcNow;
        var ms = Environment.TickCount64;
        foreach (var link in _links.Values) {
            try {
                TickLink(link, now, ms);
            } catch (Exception e) {   // one player's trouble never reaches the game's update
                Sawmill.Error($"web: {link.Key}: {e}");
            }
        }

        if (now >= _nextSweep) {   // with or without the stats lines (RM_WEB_STATS=0)
            _nextSweep = now.AddSeconds(10);
            var unix = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
            foreach (var used in _usedTokens) {
                if (used.Value < unix) _usedTokens.TryRemove(used.Key, out _);   // expired: it can't join anyway
            }

            List<string>? full = null;
            foreach (var (group, bucket) in _guestJoins) {
                if (bucket.Tokens + (ms - bucket.At) / 1000.0 / JoinEvery >= JoinBurst) (full ??= new()).Add(group);
            }

            if (full != null) foreach (var group in full) _guestJoins.Remove(group);
        }

        if (_statsEvery > 0 && now >= _nextStats) {
            _nextStats = now.AddSeconds(_statsEvery);
            foreach (var link in _links.Values) {
                try {
                    link.LogStats(_statsEvery);
                } catch (Exception e) {
                    Sawmill.Error($"web: {link.Key}'s counts: {e}");
                }
            }
        }
    }

    private void TickLink(RmWebLink link, DateTime now, long ms) {
        if (link.Closed) {   // DM let them go (Kick): once the connection has let go (queued by Kick), the link goes
            if (link.Connection is { RmWeb: { } current } && current == link) return;
            EndLink(link);
            return;
        }

        if (_guest && _guestIdle > 0 && IsGuestKey(link.Key) && (ms - link.LastInput) / 1000.0 >= _guestIdle) {
            Sawmill.Info($"web: {link.Key} left (no input for {_guestIdle:0} s)");
            link.Leave("You were idle too long, so your guest game ended. Join again to play.");
            EndLink(link);
            return;
        }

        if (link.SocketCount > 0) {
            link.RunRepeats();   // keys held down (+REP macros), once a tick
            return;
        }

        var limit = link.EverAttached ? _grace : Math.Max(_grace, 180);
        if ((now - link.LastSeen).TotalSeconds < limit)
            return;

        Sawmill.Info($"web: {link.Key} left ({(link.EverAttached ? "no page open" : "the page never opened")} for {limit:0} s)");
        link.Leave("You were away too long. Join again.");
        EndLink(link);
    }

    /// <summary>A link is over (game thread): it goes, and a guest's connection and files with it (a guest never comes
    /// back by name, so nothing of theirs is needed again; an account keeps them for its rejoins).</summary>
    private void EndLink(RmWebLink link) {
        _links.TryRemove(link.Token, out _);
        if (!IsGuestKey(link.Key) || !_guest || _links.Values.Any(l => l.Key == link.Key)) return;
        FilesByKey.TryRemove(link.Key, out _);
        var forgot = Manager.RmWebForget(link.Key);
        Sawmill.Info($"web: {link.Key} let go ({(forgot ? "connection and files" : "files only")}; web ids {Manager.RmWebIdCount}, file sets {FilesByKey.Count})");
    }

    // ---- HTTP ----------------------------------------------------------------------

    private async Task AcceptLoop() {
        while (!_stop.IsCancellationRequested) {
            HttpListenerContext context;
            try {
                context = await _listener.GetContextAsync();
            } catch (Exception) when (_stop.IsCancellationRequested) {
                return;
            } catch (Exception e) {
                if (!_listener.IsListening) {   // stopped or broken: nothing more will come, so no spinning on it
                    Sawmill.Warning($"web: the listener stopped: {e.Message}");
                    return;
                }

                Sawmill.Warning($"web: accept failed: {e.Message}");
                try {
                    await Task.Delay(100, _stop.Token);
                } catch (OperationCanceledException) {
                    return;
                }

                continue;
            }

            _ = Task.Run(() => Handle(context));
        }
    }

    private async Task Handle(HttpListenerContext context) {
        if (_loopbackOnly && !FromThisComputer(context.Request)) {   // first of all: listening on every interface, only the proxy here may talk
            try {
                context.Response.StatusCode = (int)HttpStatusCode.Forbidden;
                context.Response.Close();
            } catch (Exception) {
                try { context.Response.Abort(); } catch (Exception) { }
            }

            return;
        }

        var path = context.Request.Url?.AbsolutePath ?? "/";
        try {
            if (path == "/" || path == "/index.html") {
                if (context.Request.QueryString["name"] != null || context.Request.QueryString["token"] != null) await Join(context);
                else await Text(context, HttpStatusCode.OK, Lobby(context), "text/html");
                return;
            }

            if (path == "/join") { await Join(context); return; }
            if (path == "/health") { await Text(context, HttpStatusCode.OK, "ok"); return; }
            if (path == "/favicon.ico") { await Bytes(context, HttpStatusCode.NoContent, "image/x-icon", Array.Empty<byte>()); return; }

            if (path.StartsWith("/c/")) {
                var slash = path.IndexOf('/', 3);
                var token = slash < 0 ? path[3..] : path[3..slash];
                if (!_links.TryGetValue(token, out var link) || link.Closed) {
                    await Text(context, HttpStatusCode.Gone, RmWebShim.Ended, "text/html");
                    return;
                }

                if (slash < 0) {   // /c/<token> without its slash: the page's files would resolve one folder up
                    Harden(context.Response);
                    context.Response.Redirect($"/c/{token}/{context.Request.Url?.Query}");
                    context.Response.Close();
                    return;
                }

                var rest = Uri.UnescapeDataString(path[(slash + 1)..]);
                if (rest == "") { await Text(context, HttpStatusCode.OK, link.PageText(), "text/html"); return; }
                if (rest == "ws") { await Socket(context, link); return; }
                if (rest == "alive") { await Text(context, HttpStatusCode.OK, "ok"); return; }   // the page asks before reconnecting
                if (link.TryFile(rest, out var data)) { await ServeFile(context, rest, data); return; }
                await Bytes(context, HttpStatusCode.NotFound, "text/plain", Array.Empty<byte>());
                return;
            }

            await Bytes(context, HttpStatusCode.NotFound, "text/plain", Array.Empty<byte>());
        } catch (Exception e) {
            Sawmill.Warning($"web: {path} failed: {e.Message}");
            try {
                context.Response.Abort();
            } catch (Exception) { }
        }
    }

    /// <summary>The lobby: a name to type, or with sign-in on, a "Sign in" link that comes back to /join with a token.</summary>
    private string Lobby(HttpListenerContext context) {
        if (_secret == null || (_open && !_guest)) return RmWebShim.Lobby;
        var scheme = _public || context.Request.Headers["X-Forwarded-Proto"] == "https" ? "https" : "http";   // a public server is only reached by https
        var back = $"{scheme}://{context.Request.UserHostName}/join" + (PageQuery(context) is { Length: > 0 } q ? "?" + q : "");
        var link = _signIn == null ? "" : _signIn + (_signIn.Contains('?') ? "&" : "?") + "return=" + Uri.EscapeDataString(back);
        var page = RmWebShim.SignIn.Replace("__SIGNIN__", HttpUtility.HtmlAttributeEncode(link));
        return _guest ? page.Replace("<!--guest-->", RmWebShim.GuestForm) : page;
    }

    /// <summary>The page's own options in the address (such as ?overlay): the query without the name and token.</summary>
    private static string PageQuery(HttpListenerContext context)
        => Regex.Replace(context.Request.Url?.Query.TrimStart('?') ?? "", @"(^|&)(name|token)=[^&]*", "").Trim('&');

    private async Task Join(HttpListenerContext context) {
        string key;
        var guest = false;
        var address = ClientAddress(context.Request);
        var token = context.Request.QueryString["token"];
        if (token != null) {
            if (CheckToken(token, out var why) is not { } account) {
                Sawmill.Info($"web: a sign-in from {address} was turned away: {why}");
                await Text(context, HttpStatusCode.Forbidden, RmWebShim.Refused.Replace("__WHY__", HttpUtility.HtmlEncode(why)), "text/html");
                return;
            }

            key = account;
        } else {
            if (_secret != null && !_open && !_guest) {
                await Text(context, HttpStatusCode.Unauthorized, Lobby(context), "text/html");
                return;
            }

            key = (context.Request.QueryString["name"] ?? "").Trim();
            if (!NamePattern.IsMatch(key)) {
                await Text(context, HttpStatusCode.BadRequest, "A name is 1 to 30 letters, digits, spaces, - or _.");
                return;
            }

            guest = _secret != null && _guest;   // the guest limits and the guest's key: on the game thread (JoinOnMain)
        }

        // the game thread may be busy (a long tick, a save): the browser is told, and the join is dropped if it comes late
        var late = new System.Runtime.CompilerServices.StrongBox<bool>();
        Joined joined;
        try {
            joined = await Manager.RmWebOnMain(() => Volatile.Read(ref late.Value) ? new Joined(null, HttpStatusCode.ServiceUnavailable, "")
                : JoinOnMain(key, guest, address)).WaitAsync(TimeSpan.FromSeconds(30));
        } catch (TimeoutException) {
            Volatile.Write(ref late.Value, true);
            Sawmill.Warning($"web: {key}'s join from {address} waited 30 s for the game; turned away");
            await Text(context, HttpStatusCode.ServiceUnavailable, "The game is busy. Try again in a moment.");
            return;
        }

        if (joined.Link is not { } link) {
            await Text(context, joined.Status, joined.Why);
            return;
        }

        // the page's own options go with it
        var query = PageQuery(context);
        Harden(context.Response);
        context.Response.Redirect($"/c/{link.Token}/" + (query.Length > 0 ? "?" + query : ""));
        context.Response.Close();
    }

    private readonly record struct Joined(RmWebLink? Link, HttpStatusCode Status, string Why);

    /// <summary>
    /// The player's address. Behind a proxy on this computer (Tailscale Funnel, RM_WEB_BIND=127.0.0.1) every connection
    /// comes from 127.0.0.1, so there the proxy's X-Forwarded-For says who it is: its last entry, the one the proxy
    /// added (a browser may send its own entries before it, never after). Anything else: the connection's own address.
    /// </summary>
    internal static string ClientAddress(HttpListenerRequest request) {
        var remote = request.RemoteEndPoint?.Address;
        if (remote is { IsIPv4MappedToIPv6: true }) remote = remote.MapToIPv4();
        if (remote != null && IPAddress.IsLoopback(remote) && request.Headers["X-Forwarded-For"] is { Length: > 0 } forwarded) {
            var last = forwarded[(forwarded.LastIndexOf(',') + 1)..].Trim();
            if (last.Length <= 64 && IPEndPoint.TryParse(last, out var end)) return Canonical(end.Address);
        }

        return remote == null ? "" : Canonical(remote);
    }

    private static bool FromThisComputer(HttpListenerRequest request) {
        var remote = request.RemoteEndPoint?.Address;
        if (remote is { IsIPv4MappedToIPv6: true }) remote = remote.MapToIPv4();
        return remote != null && IPAddress.IsLoopback(remote);
    }

    private static string Canonical(IPAddress address) {
        if (address.IsIPv4MappedToIPv6) address = address.MapToIPv4();
        if (address.AddressFamily == System.Net.Sockets.AddressFamily.InterNetworkV6 && address.ScopeId != 0)
            address = new IPAddress(address.GetAddressBytes());   // without its zone (a new one: the shared ones can't change)
        return address.ToString();
    }

    /// <summary>The place an address counts as for the guest limits: an IPv4 address itself; IPv6 by its /64 (one
    /// household or phone is given a whole /64, and can pick any address in it).</summary>
    internal static string AddressGroup(string address) {
        if (!IPAddress.TryParse(address, out var ip) || ip.AddressFamily != System.Net.Sockets.AddressFamily.InterNetworkV6) return address;
        var bytes = ip.GetAddressBytes();
        Array.Clear(bytes, 8, 8);
        return new IPAddress(bytes) + "/64";
    }

    /// <summary>
    /// A sign-in token, made by whatever signs players in (an account service, the Discord link service, or
    /// tools/web_token.py) with the secret this server shares: "1.&lt;payload&gt;.&lt;signature&gt;", the payload base64url
    /// JSON {"key": the account, "exp": unix seconds}, the signature base64url HMAC-SHA256 of "1.&lt;payload&gt;". It joins
    /// once, within an hour at most. Returns the account, or null and why not.
    /// </summary>
    private string? CheckToken(string token, out string why) {
        why = "it is not a sign-in token";
        var parts = token.Split('.');
        if (_secret == null) {
            why = "this server has no sign-in";
            return null;
        }

        // base64url only (no padding, spaces or other letters): one spelling of each part as far as the text goes
        if (parts.Length != 3 || parts[0] != "1" || parts[1].Length > 2048 || parts[2].Length > 64 || !TokenPart.IsMatch(parts[1]) || !TokenPart.IsMatch(parts[2]))
            return null;

        byte[] payload, signature;
        try {
            payload = FromBase64Url(parts[1]);
            signature = FromBase64Url(parts[2]);
        } catch (FormatException) {
            return null;
        }

        var expected = HMACSHA256.HashData(_secret, Encoding.ASCII.GetBytes(parts[0] + "." + parts[1]));
        if (signature.Length != 32 || !CryptographicOperations.FixedTimeEquals(expected, signature)) {
            why = "its signature is wrong";
            return null;
        }

        string? key;
        long expires;
        try {
            using var document = JsonDocument.Parse(payload);
            key = document.RootElement.GetProperty("key").GetString();
            expires = document.RootElement.GetProperty("exp").GetInt64();
        } catch (Exception) {
            why = "its contents are unreadable";
            return null;
        }

        var now = DateTimeOffset.UtcNow.ToUnixTimeSeconds();
        if (expires <= now) {
            why = "it has expired";
            return null;
        }

        if (expires > now + 3600) {
            why = "it is good for more than an hour";
            return null;
        }

        if (key == null || !KeyPattern.IsMatch(key)) {
            why = "its account name is not allowed";
            return null;
        }

        if (_guest && IsGuestKey(key)) {   // on a guest server only: elsewhere the game has no guests (Guests.dm RM_GUEST)
            why = "names starting with Guest are kept for guests";
            return null;
        }

        // by the signature's bytes, not its text: the decoder takes more than one spelling of the same bytes (the last
        // letter's unused bits), and each would have joined once
        if (!_usedTokens.TryAdd(Convert.ToHexString(signature), expires)) {
            why = "it was used already";
            return null;
        }

        return key;
    }

    /// <summary>A guest's key, as the game knows them (Guests.dm RmGuestKey): letters and digits starting with "guest".</summary>
    internal static bool IsGuestKey(string? key) {
        if (key == null) return false;
        var c = new string(key.Where(char.IsLetterOrDigit).ToArray()).ToLowerInvariant();
        return c.Length > 5 && c.StartsWith("guest", StringComparison.Ordinal);
    }

    /// <summary>"Guest &lt;name&gt; &lt;n&gt;": a number no link, connection or kept files have, so a guest never joins
    /// another guest's session by typing the same name (a guest's village can't be taken that way), and a guest can't
    /// come back by name. Game thread (JoinOnMain), so two joins at once can't pick the same one.</summary>
    private string GuestKey(string name) {
        for (var i = 0; ; i++) {
            var key = $"Guest {name} {RandomNumberGenerator.GetInt32(1000, i < 50 ? 10000 : 100000)}";
            if (!_links.Values.Any(l => l.Key == key) && !FilesByKey.ContainsKey(key) && !Manager.RmWebKnows(key)) return key;
        }
    }

    private static byte[] FromBase64Url(string text) {
        var b = text.Replace('-', '+').Replace('_', '/');
        return Convert.FromBase64String(b + new string('=', (4 - b.Length % 4) % 4));
    }

    /// <summary>On the game thread. The same name again (a second tab, the lobby reloaded) is the same player. A guest
    /// (a typed name on a sign-in server) is a new one each time, within the limits: per address (its group), in all,
    /// and joins per address paced. Counted here, not on the HTTP threads, so joins at the same moment can't all pass.</summary>
    private Joined JoinOnMain(string key, bool guest, string address) {
        var group = AddressGroup(address);
        if (guest) {
            int here = 0, all = 0;
            foreach (var open in _links.Values) {
                if (open.Closed || !IsGuestKey(open.Key)) continue;
                all++;
                if (open.Group == group) here++;
            }

            if (here >= _guestsPerAddress)
                return new Joined(null, (HttpStatusCode)429, $"{_guestsPerAddress} guests from one place at a time. Sign in to play more.");
            if (all >= _guestMax)
                return new Joined(null, HttpStatusCode.ServiceUnavailable, "Guest places are full. Sign in to play.");
            if (!SpendGuestJoin(group)) {
                Sawmill.Info($"web: a guest join from {address} was turned away: too many joins from there");
                return new Joined(null, (HttpStatusCode)429, "Too many guests joined from one place just now. Wait a few seconds, or sign in.");
            }

            key = GuestKey(key);
        } else {
            foreach (var open in _links.Values) {
                if (open.Key == key && !open.Closed)
                    return new Joined(open, HttpStatusCode.OK, "");
            }
        }

        var link = new RmWebLink(this, key, address, group);
        _links[link.Token] = link;
        try {
            if (Manager.RmWebConnect(key, link) != null) {
                Sawmill.Info($"web: {key} joined from {address}");
                return new Joined(link, HttpStatusCode.OK, "");
            }
        } catch {
            _links.TryRemove(link.Token, out _);
            if (guest) EndLink(link);
            throw;
        }

        _links.TryRemove(link.Token, out _);
        if (guest) EndLink(link);
        return new Joined(null, HttpStatusCode.Conflict, "That player is playing from the game app.");
    }

    /// <summary>A guest join from this place, if its pace allows (game thread).</summary>
    private bool SpendGuestJoin(string group) {
        var ms = Environment.TickCount64;
        var (tokens, at) = _guestJoins.TryGetValue(group, out var bucket) ? bucket : (JoinBurst, ms);
        tokens = Math.Min(JoinBurst, tokens + (ms - at) / 1000.0 / JoinEvery);
        if (tokens < 1) {
            _guestJoins[group] = (tokens, ms);
            return false;
        }

        _guestJoins[group] = (tokens - 1, ms);
        return true;
    }

    private async Task Socket(HttpListenerContext context, RmWebLink link) {
        if (!context.Request.IsWebSocketRequest) {
            await Text(context, HttpStatusCode.BadRequest, "websocket expected");
            return;
        }

        // at most RmWebLink.MaxSockets tabs a player and MaxSocketsTotal in all, turned away before the upgrade (the page
        // tries again a few seconds later, so a tab that was cut off gets in once the server has let its old socket go)
        if (Interlocked.Increment(ref _socketsOpen) > MaxSocketsTotal) {
            Interlocked.Decrement(ref _socketsOpen);
            await Text(context, HttpStatusCode.ServiceUnavailable, "The server has too many open connections.");
            return;
        }

        var reserved = false;
        try {
            if (!link.ReserveSocket()) {
                await Text(context, (HttpStatusCode)429, $"At most {RmWebLink.MaxSockets} tabs a player.");
                return;
            }

            reserved = true;
            var accepted = await context.AcceptWebSocketAsync(null);
            var socket = new RmWebSocket(link, accepted.WebSocket);
            if (context.Request.QueryString["v"] != Protocol.ToString()) {
                await socket.CloseAsync((WebSocketCloseStatus)4001, "the page is older than the server: reload it");
                return;
            }

            reserved = false;   // Run's Attach takes the place over, and Detach gives it back
            await socket.Run(_stop.Token);
        } finally {
            if (reserved) link.ReleaseSocket();
            Interlocked.Decrement(ref _socketsOpen);
        }
    }

    // A file's tag: a hash of its bytes, worked out once per file (the files are the resources' own arrays, kept for the server's life)
    private static readonly System.Runtime.CompilerServices.ConditionalWeakTable<byte[], string> FileTags = new();

    /// <summary>
    /// A browse_rsc file. The browser keeps it and asks again with its tag ("no-cache" + ETag): a reload or a rejoin gets
    /// "not modified" for what it has, instead of the page's 6 MB of pictures, sounds and models again.
    /// </summary>
    private static async Task ServeFile(HttpListenerContext context, string name, byte[] data) {
        var tag = FileTags.GetValue(data, bytes => "\"" + Convert.ToHexString(SHA256.HashData(bytes), 0, 12).ToLowerInvariant() + "\"");
        var response = context.Response;
        response.Headers["ETag"] = tag;
        if (context.Request.Headers["If-None-Match"] is { } asked && asked.Split(',').Any(t => t.Trim() == tag)) {
            response.StatusCode = (int)HttpStatusCode.NotModified;
            response.Headers["Cache-Control"] = "no-cache";
            Harden(response);
            response.Close();
            return;
        }

        await Bytes(context, HttpStatusCode.OK, MimeFor(Path.GetExtension(name)), data, "no-cache");
    }

    private static Task Text(HttpListenerContext context, HttpStatusCode status, string text, string type = "text/plain")
        => Bytes(context, status, type + "; charset=utf-8", Encoding.UTF8.GetBytes(text));

    private static async Task Bytes(HttpListenerContext context, HttpStatusCode status, string type, byte[] body, string cache = "no-store") {
        var response = context.Response;
        response.StatusCode = (int)status;
        response.ContentType = type;
        response.ContentLength64 = body.Length;
        response.Headers["Cache-Control"] = cache;
        Harden(response);
        await response.OutputStream.WriteAsync(body);
        response.Close();
    }

    /// <summary>Every answer: files are what their type says (no sniffing), the address isn't passed on to other sites,
    /// and only this server's own pages may frame its pages.</summary>
    private static void Harden(HttpListenerResponse response) {
        response.Headers["X-Content-Type-Options"] = "nosniff";
        response.Headers["Referrer-Policy"] = "no-referrer";
        response.Headers["Content-Security-Policy"] = "frame-ancestors 'self'";
    }

    internal static string MimeFor(string extension) => extension.TrimStart('.').ToLowerInvariant() switch {
        "png" => "image/png", "jpg" or "jpeg" => "image/jpeg", "gif" => "image/gif", "webp" => "image/webp", "svg" => "image/svg+xml",
        "ico" => "image/x-icon", "json" => "application/json", "js" => "text/javascript", "css" => "text/css", "html" or "htm" => "text/html",
        "txt" => "text/plain", "ogg" => "audio/ogg", "wav" => "audio/wav", "mp3" => "audio/mpeg", "mp4" => "video/mp4", "webm" => "video/webm",
        "glb" => "model/gltf-binary", "gltf" => "model/gltf+json", "woff" => "font/woff", "woff2" => "font/woff2", "ttf" => "font/ttf",
        "otf" => "font/otf", "wasm" => "application/wasm",
        _ => "application/octet-stream",
    };
}

/// <summary>One web player: their connection, page, files, open prompts and sockets (a socket per open tab).</summary>
internal sealed class RmWebLink {
    private const long BacklogLimit = 32 << 20;   // bytes queued on one socket before it is closed (the page reconnects and asks for everything)
    public const int MaxSockets = 3;              // tabs one player may have open
    // what the page may send: ~Rate messages a second from all of the player's tabs, a burst of Burst; more are dropped,
    // and a tab that keeps on for FloodClose seconds (drops never more than FloodGap apart) is closed
    private const double Rate = 30, Burst = 60, FloodClose = 10, FloodGap = 2;
    private static readonly JsonWriterOptions JsonOptions = new() { Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping };
    // A page sends its byond:// links by setting location.href; on the web, the link's setter (dmweb-head.js) takes them.
    private static readonly Regex NavPattern = new(@"(?<![\w.$])(?:window\.)?location\.href\s*=(?!=)", RegexOptions.Compiled);

    private readonly RmWebServer _server;
    public readonly string Token = Convert.ToHexString(RandomNumberGenerator.GetBytes(16)).ToLowerInvariant();
    public readonly string Key, Address, Group;   // Group: the address for the guest limits (RmWebServer.AddressGroup)
    public DreamConnection? Connection;
    public volatile bool Closed;
    public bool EverAttached;
    public DateTime LastSeen = DateTime.UtcNow;
    public int Width = 1280, Height = 720;   // the page's size, for winget(..., "size")
    private long _lastInput = Environment.TickCount64;   // the last link, answer or key from the page (an idle guest goes)
    public long LastInput => Interlocked.Read(ref _lastInput);

    // the page's message pace (socket threads)
    private readonly object _paceLock = new();
    private double _allowance = Burst;
    private long _paceAt = Environment.TickCount64, _floodSince, _lastDrop;
    private long _received, _dropped;   // since the last stats line

    private readonly List<RmWebSocket> _sockets = new();
    private int _reserved;   // sockets being opened (RmWebServer.Socket), counted with _sockets against MaxSockets
    private readonly ConcurrentDictionary<string, byte[]> _files;
    private readonly Dictionary<int, Prompt> _prompts = new();   // game thread
    private readonly object _pageLock = new();
    private string? _pageWindow;
    private string? _page;                // as browse()d (game thread writes, HTTP threads read)
    private int _pageVersion;
    private string? _pageServed;          // _page with the link's scripts, for _pageServedVersion
    private int _pageServedVersion = -1;

    // send counts since the last stats line: function or kind -> (messages, bytes)
    private readonly Dictionary<string, (int Count, long Bytes)> _sent = new();
    private readonly Dictionary<string, int> _ignored = new();
    private readonly Dictionary<string, int> _keysRun = new();   // command (or why it didn't run) -> times, since the last stats line
    private long _sentTotal, _unsent;
    private long _wire, _wireLogged;   // bytes as they went on the sockets (compressed or not)

    // +REP macros held down: their commands, run when the key goes down (as BYOND does: a tap pans the camera once) and
    // each update after, until the key comes up (the last held key's, as the native client runs its last repeating
    // verb). Game thread.
    private readonly List<Repeat> _repeats = new();
    private sealed class Repeat(string key, List<string> commands) {
        public readonly string Key = key;
        public readonly List<string> Commands = commands;
        public bool Fresh = true;   // ran on its key's press this update already
    }

    private sealed record Prompt(int Id, string Kind, string Title, string Message, string[] Buttons, string[] Items, string Value);

    public RmWebLink(RmWebServer server, string key, string address, string group) {
        _server = server;
        Key = key;
        Address = address;
        Group = group;
        _pageWindow = server.PageWindow;
        _files = server.FilesByKey.GetOrAdd(key, _ => new());
    }

    public int SocketCount {
        get { lock (_sockets) return _sockets.Count; }
    }

    /// <summary>A place for one more tab, if the player has fewer than MaxSockets (open or being opened).</summary>
    public bool ReserveSocket() {
        lock (_sockets) {
            if (_sockets.Count + _reserved >= MaxSockets) return false;
            _reserved++;
            return true;
        }
    }

    public void ReleaseSocket() {
        lock (_sockets) _reserved = Math.Max(0, _reserved - 1);
    }

    /// <summary>A tab's bytes as they went on its socket (RmWebSocket's send task).</summary>
    public void Wire(long bytes) => Interlocked.Add(ref _wire, bytes);

    /// <summary>The most bytes still queued on one of this player's tabs (0 with none open).</summary>
    public long Behind {
        get {
            long most = 0;
            lock (_sockets)
                foreach (var socket in _sockets)
                    most = Math.Max(most, socket.Backlog);
            return most;
        }
    }

    // ---- the server's messages (game thread, from DreamConnection.RmSend) ----------

    public void FromServer(NetMessage message) {
        switch (message) {
            case MsgOutput output:
                Output(output.Value, output.Control);
                break;
            case MsgBrowse browse:
                Browse(browse);
                break;
            case MsgPrompt prompt: {
                var kind = (prompt.Types & DreamValueType.Message) != 0 ? "MessagePrompt"
                    : (prompt.Types & DreamValueType.Num) != 0 ? "NumberPrompt" : "TextPrompt";
                var buttons = (prompt.Types & DreamValueType.Null) != 0 ? new[] { "Ok", "Cancel" } : new[] { "Ok" };
                Ask(new Prompt(prompt.PromptId, kind, prompt.Title, prompt.Message, buttons, Array.Empty<string>(), prompt.DefaultValue));
                break;
            }
            case MsgPromptList list:
                Ask(new Prompt(list.PromptId, "ListPrompt", list.Title, list.Message, list.CanCancel ? new[] { "Ok", "Cancel" } : new[] { "Ok" },
                    list.Values, list.DefaultValue));
                break;
            case MsgAlert alert: {
                var buttons = new[] { alert.Button1, alert.Button2, alert.Button3 }.Where(b => !string.IsNullOrEmpty(b)).ToArray();
                Ask(new Prompt(alert.PromptId, "AlertWindow", alert.Title, alert.Message, buttons.Length > 0 ? buttons : new[] { "Ok" },
                    Array.Empty<string>(), ""));
                break;
            }
            case MsgWinGet winget:
                // answered on the next update, as a reply from a client would come
                Later(() => Connection?.HandleMsgPromptResponse(new MsgPromptResponse
                    { PromptId = winget.PromptId, Type = DreamValueType.Text, Value = WinGet(winget.ControlId, winget.QueryValue) }));
                Ignored("winget " + winget.QueryValue);
                break;
            case MsgWinExists exists:
                Later(() => Connection?.HandleMsgPromptResponse(new MsgPromptResponse
                    { PromptId = exists.PromptId, Type = DreamValueType.Text, Value = "" }));
                Ignored("winexists");
                break;
            case MsgSoundQuery query:
                Later(() => Connection?.HandleMsgSoundQueryResponse(new MsgSoundQueryResponse
                    { PromptId = query.PromptId, Sounds = new() }));
                Ignored("soundquery");
                break;
            default:
                // winset, winclone, client info, stat panels, sounds, links, files to save: nothing the page uses yet
                Ignored(message.GetType().Name);
                break;
        }
    }

    private void Output(string value, string? control) {
        var colon = control?.IndexOf(':') ?? -1;
        if (control == null || colon < 0) {
            Post(writer => {
                writer.WriteString("out", value);
                if (control != null) writer.WriteString("to", control);
            }, "out");
            return;
        }

        var window = control[..colon];
        var function = control[(colon + 1)..];
        if (_pageWindow != null && window != _pageWindow) {
            Ignored("output to " + window);
            return;
        }

        // as the native browser control does (ControlBrowser.Output): split on &, each part url-decoded, one argument each
        var parts = value.Split('&');
        Post(writer => {
            writer.WriteString("f", function);
            writer.WriteStartArray("a");
            foreach (var part in parts)
                writer.WriteStringValue(HttpUtility.UrlDecode(part));
            writer.WriteEndArray();
        }, function);
    }

    private void Browse(MsgBrowse browse) {
        var window = browse.Window ?? "";
        _pageWindow ??= window;
        if (window != _pageWindow || browse.HtmlSource == null) {
            Ignored("browse " + (window.Length > 0 ? window : "(no window)"));
            return;
        }

        var page = SharedPage(browse.HtmlSource);   // the same text for every player: one copy (load-asleep-1030)
        lock (_pageLock) {
            _page = page;
            _pageVersion++;
        }

        Post(writer => writer.WriteNumber("reload", _pageVersion), "page");
    }

    private void Ask(Prompt prompt) {
        _prompts[prompt.Id] = prompt;
        Post(writer => WritePrompt(writer, prompt), "prompt");
    }

    private static void WritePrompt(Utf8JsonWriter writer, Prompt prompt) {
        writer.WriteStartObject("prompt");
        writer.WriteNumber("id", prompt.Id);
        writer.WriteString("kind", prompt.Kind);
        writer.WriteString("title", prompt.Title);
        writer.WriteString("message", prompt.Message);
        writer.WriteStartArray("buttons");
        foreach (var button in prompt.Buttons) writer.WriteStringValue(button);
        writer.WriteEndArray();
        writer.WriteStartArray("items");
        foreach (var item in prompt.Items) writer.WriteStringValue(item);
        writer.WriteEndArray();
        writer.WriteString("value", prompt.Value);
        writer.WriteEndObject();
    }

    private string WinGet(string control, string query) => query.Trim() switch {
        "size" or "view-size" or "inner-size" or "outer-size" => $"{Width}x{Height}",
        "is-visible" => "true",
        "is-maximized" or "is-minimized" => "false",
        _ => "",
    };

    public void File(string name, byte[]? data) {
        if (data != null) _files[name] = data;
    }

    public bool TryFile(string name, out byte[] data) => _files.TryGetValue(name, out data!);

    // ---- the page's messages (socket threads; the game's part runs on the game thread) ----

    /// <summary>A message from one of the player's tabs. False: that tab has sent too fast for too long; close it.</summary>
    public bool FromPage(RmWebSocket socket, string text) {
        if (!Pace(out var keepOpen)) return keepOpen;

        JsonDocument document;
        try {
            document = JsonDocument.Parse(text);
        } catch (JsonException) {
            return true;
        }

        using (document) {
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object) return true;

            if (root.TryGetProperty("nav", out var nav) && nav.ValueKind == JsonValueKind.String) {
                var url = nav.GetString()!;
                Input();
                Later(() => Navigate(url));
            } else if (root.TryGetProperty("prompt", out var answer) && answer.ValueKind == JsonValueKind.Object) {
                var id = answer.TryGetProperty("id", out var idValue) && idValue.TryGetInt32(out var n) ? n : 0;
                var cancel = answer.TryGetProperty("cancel", out var c) && c.ValueKind == JsonValueKind.True;
                var button = answer.TryGetProperty("button", out var b) && b.ValueKind == JsonValueKind.String ? b.GetString() : null;
                var value = answer.TryGetProperty("value", out var v) ? v.Clone() : default;
                Input();
                Later(() => Answer(id, cancel, button, value));
            } else if (root.TryGetProperty("hello", out var hello) && hello.ValueKind == JsonValueKind.Object) {
                ReadSize(hello);
                var served = hello.TryGetProperty("pv", out var pv) && pv.TryGetInt32(out var p) ? p : -1;
                if (_server.Deflate && hello.TryGetProperty("z", out var z) && z.TryGetInt32(out var zv) && zv == 1)
                    socket.DeflateFromNow();   // before Hello's sends: those and all after go compressed
                Later(() => Hello(socket, served));
            } else if (root.TryGetProperty("key", out var key) && key.ValueKind == JsonValueKind.Object) {
                var name = key.TryGetProperty("k", out var k) && k.ValueKind == JsonValueKind.String ? k.GetString() : null;
                var mods = key.TryGetProperty("m", out var m) && m.TryGetInt32(out var held) ? held & 7 : 0;
                var down = key.TryGetProperty("d", out var d) && (d.ValueKind == JsonValueKind.True || (d.ValueKind == JsonValueKind.Number && d.TryGetDouble(out var dv) && dv != 0));
                if (name is { Length: > 0 and <= 12 }) {
                    Input();
                    Later(() => KeyPress(name, mods, down));
                }
            } else if (root.TryGetProperty("size", out var size) && size.ValueKind == JsonValueKind.Object) {
                ReadSize(size);
            }
        }

        return true;
    }

    private void Input() => Interlocked.Exchange(ref _lastInput, Environment.TickCount64);

    /// <summary>The page's pace: true takes this message. False drops it; keepOpen false then says the tab has sent too
    /// fast for FloodClose seconds and is to be closed.</summary>
    private bool Pace(out bool keepOpen) {
        keepOpen = true;
        var ms = Environment.TickCount64;
        bool warn = false, close = false;
        lock (_paceLock) {
            _allowance = Math.Min(Burst, _allowance + (ms - _paceAt) / 1000.0 * Rate);
            _paceAt = ms;
            if (_allowance >= 1) {
                _allowance -= 1;
                _received++;
                return true;
            }

            _dropped++;
            if (_floodSince == 0 || ms - _lastDrop > FloodGap * 1000) {
                _floodSince = ms;
                warn = true;
            }

            _lastDrop = ms;
            if (ms - _floodSince >= FloodClose * 1000) {
                close = true;
                _floodSince = 0;   // the next tab that floods starts its own count
            }
        }

        if (warn) _server.Sawmill.Warning($"web: {Key}'s tabs send more than {Rate:0} messages a second; the rest are dropped");
        if (close) {
            _server.Sawmill.Warning($"web: {Key}'s tab kept sending too fast for {FloodClose:0} s; closing it");
            keepOpen = false;
        }

        return false;
    }

    // the page's size, within what a screen can be (winget answers it to the game)
    private void ReadSize(JsonElement size) {
        if (size.TryGetProperty("w", out var w) && w.TryGetInt32(out var width) && width > 0) Width = Math.Min(width, 16384);
        if (size.TryGetProperty("h", out var h) && h.TryGetInt32(out var height) && height > 0) Height = Math.Min(height, 16384);
    }

    /// <summary>A socket opened: a page made from an older browse() reloads; the page learns the game's keys; open questions are asked again.</summary>
    private void Hello(RmWebSocket socket, int servedVersion) {
        if (servedVersion != _pageVersion) {
            socket.Send(Encode(writer => writer.WriteNumber("reload", _pageVersion)));
            return;
        }

        var keys = _server.Keys.KeyList;
        socket.Send(Encode(writer => {
            writer.WriteStartArray("keys");
            foreach (var key in keys) writer.WriteStringValue(key);
            writer.WriteEndArray();
        }));
        foreach (var prompt in _prompts.Values)
            socket.Send(Encode(writer => WritePrompt(writer, prompt)));
    }

    /// <summary>A byond:// link (or a ?query link) from the page: a Topic, as the native browser control sends it.</summary>
    private void Navigate(string url) {
        if (Connection == null) return;
        var question = url.IndexOf('?');
        var host = url.StartsWith("byond://", StringComparison.OrdinalIgnoreCase) ? url[8..(question < 0 ? url.Length : question)] : "";
        if (host is "winset" or "winget") {   // the page's own winset/winget links: none the game's pages use yet
            Ignored("page " + host);
            return;
        }

        if (question < 0) return;
        Connection.HandleMsgTopic(new MsgTopic { Query = url[question..] });
    }

    /// <summary>A key the page gave the game (one with a skin macro): its macro's command runs, as the native client runs it.</summary>
    private void KeyPress(string key, int mods, bool down) {
        if (Connection == null) return;
        _repeats.RemoveAll(held => held.Key == key);
        var repeating = new List<string>();
        foreach (var macro in _server.Keys.For(key, mods, up: !down)) {
            if (macro.Rep) repeating.Add(macro.Command);
            Run(macro.Command);
        }

        if (down && repeating.Count > 0)
            _repeats.Add(new Repeat(key, repeating));
    }

    /// <summary>Each update (game thread): the last held key's +REP commands.</summary>
    public void RunRepeats() {
        if (_repeats.Count == 0 || Connection == null) return;
        var held = _repeats[^1];
        if (held.Fresh) {
            held.Fresh = false;
            return;
        }

        foreach (var command in held.Commands)
            Run(command);
    }

    private void Run(string command) {
        var verbs = _server.Verbs;
        var why = verbs == null ? "no verb system" : verbs.RmRunCommand(Connection!, command);   // null: it ran
        var label = why == null ? command : $"{command} ({why})";
        _keysRun[label] = _keysRun.TryGetValue(label, out var n) ? n + 1 : 1;
    }

    private const int AnswerTextLimit = 4096;   // characters in a typed answer

    private void Answer(int id, bool cancel, string? button, JsonElement value) {
        if (Connection == null || !_prompts.TryGetValue(id, out var prompt)) return;

        DreamValueType type;
        object? answer;
        if (cancel) {
            if (prompt.Kind != "AlertWindow" && !prompt.Buttons.Contains("Cancel")) return;   // this question can't be cancelled
            type = DreamValueType.Null;
            answer = null;
        } else {
            // an answer the question can't have is not taken (and doesn't throw): the question stays open
            switch (prompt.Kind) {
                case "AlertWindow":
                    if (button != null && !prompt.Buttons.Contains(button)) return;
                    type = DreamValueType.Text;
                    answer = button ?? prompt.Buttons[0];
                    break;
                case "MessagePrompt":
                    if (TextAnswer(value) is not { } message) return;
                    type = DreamValueType.Message;
                    answer = message;
                    break;
                case "NumberPrompt": {
                    double number = 0;
                    if (value.ValueKind == JsonValueKind.Number) {
                        if (!value.TryGetDouble(out number)) return;
                    } else if (value.ValueKind == JsonValueKind.String) {
                        var typed = value.GetString()!;
                        if (typed.Length > 64) return;
                        if (typed.Trim().Length > 0 && !double.TryParse(typed, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out number)) return;
                    }

                    if (!double.IsFinite(number) || !float.IsFinite((float)number)) return;   // no NaN or Infinity, none past a float
                    type = DreamValueType.Num;
                    answer = (float)number;
                    break;
                }
                case "ListPrompt": {
                    int index;
                    if (value.ValueKind == JsonValueKind.Number) {
                        if (!value.TryGetInt32(out index)) return;   // a whole number only
                    } else if (value.ValueKind == JsonValueKind.String) {
                        index = Array.IndexOf(prompt.Items, value.GetString());
                    } else {
                        return;
                    }

                    if (index < 0 || index >= prompt.Items.Length) return;
                    type = DreamValueType.Num;
                    answer = (float)index;
                    break;
                }
                default:
                    if (TextAnswer(value) is not { } text) return;
                    type = DreamValueType.Text;
                    answer = text;
                    break;
            }
        }

        _prompts.Remove(id);
        Post(writer => writer.WriteNumber("promptClose", id), "prompt");
        try {
            Connection.HandleMsgPromptResponse(new MsgPromptResponse { PromptId = id, Type = type, Value = answer });
        } catch (Exception e) {
            _server.Sawmill.Warning($"web: {Key}'s answer to \"{prompt.Title}\" was not taken: {e.Message}");
        }
    }

    /// <summary>A typed answer: text (none is ""), at most AnswerTextLimit characters; null when it can't be one.</summary>
    private static string? TextAnswer(JsonElement value) {
        if (value.ValueKind != JsonValueKind.String) return value.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null ? "" : null;
        var text = value.GetString()!;
        return text.Length <= AnswerTextLimit ? text : null;
    }

    // ---- the page --------------------------------------------------------------------

    /// <summary>The page with the link's scripts in it (made once per browse()), or the joining page until there is one.</summary>
    public string PageText() {
        lock (_pageLock) {
            if (_page == null) return RmWebShim.Joining(RmWebServer.Protocol);
            if (_pageServedVersion == _pageVersion) return _pageServed!;
            if (SharedServed(_page, _pageVersion) is { } shared) {
                _pageServed = shared;
                _pageServedVersion = _pageVersion;
                return shared;
            }

            var html = NavPattern.Replace(_page, "window.__dmGo=");
            var head = "<script>" + RmWebShim.Head(RmWebServer.Protocol, _pageVersion) + "</script>";
            var at = html.IndexOf("<head>", StringComparison.OrdinalIgnoreCase);
            html = at >= 0 ? html.Insert(at + 6, head) : head + html;
            var tail = "<script>" + RmWebShim.Tail + "</script>";
            var end = html.LastIndexOf("</body>", StringComparison.OrdinalIgnoreCase);
            html = end >= 0 ? html.Insert(end, tail) : html + tail;
            if (NavPattern.Matches(_page).Count == 0)
                _server.Sawmill.Warning("web: the page never sets location.href; its byond:// links may not reach the game");
            _pageServed = KeepServed(_page, _pageVersion, html);
            _pageServedVersion = _pageVersion;
            return _pageServed;
        }
    }

    // Remastered (load-asleep-1030, 10-31): every player was browse()d the same page, ~2.4 M characters, and each link kept
    // it twice (as sent and with the link's scripts): 9.7 MB a player, 461 MB of the server's 1,115 MB live heap with 50
    // browser players. Now the links share one copy of each page, and one served copy of each (page, version); the last
    // few pages only, so a page the game no longer sends is let go.
    private static readonly object SharedLock = new();
    private static readonly List<string> SharedPages = new();
    private static readonly List<(string Page, int Version, string Served)> SharedServedPages = new();

    private static string SharedPage(string page) {
        lock (SharedLock) {
            foreach (var kept in SharedPages)
                if (ReferenceEquals(kept, page) || (kept.Length == page.Length && string.Equals(kept, page, StringComparison.Ordinal))) return kept;
            SharedPages.Add(page);
            if (SharedPages.Count > 4) {
                var old = SharedPages[0];
                SharedPages.RemoveAt(0);
                SharedServedPages.RemoveAll(e => ReferenceEquals(e.Page, old));
            }
            return page;
        }
    }

    private static string? SharedServed(string page, int version) {
        lock (SharedLock) {
            foreach (var e in SharedServedPages) if (e.Version == version && ReferenceEquals(e.Page, page)) return e.Served;
            return null;
        }
    }

    private static string KeepServed(string page, int version, string served) {
        lock (SharedLock) {
            foreach (var e in SharedServedPages) if (e.Version == version && ReferenceEquals(e.Page, page)) return e.Served;
            SharedServedPages.Add((page, version, served));
            if (SharedServedPages.Count > 16) SharedServedPages.RemoveAt(0);
            return served;
        }
    }

    // ---- sockets -------------------------------------------------------------------

    public void Attach(RmWebSocket socket) {
        lock (_sockets) {
            _reserved = Math.Max(0, _reserved - 1);   // the place ReserveSocket kept for it
            _sockets.Add(socket);
        }

        EverAttached = true;
        LastSeen = DateTime.UtcNow;
    }

    public void Detach(RmWebSocket socket) {
        lock (_sockets) _sockets.Remove(socket);
        LastSeen = DateTime.UtcNow;
        Later(() => {
            if (SocketCount == 0) _repeats.Clear();   // no tab left to lift the key
        });
    }

    public void CloseSockets(string reason) {
        RmWebSocket[] all;
        lock (_sockets) all = _sockets.ToArray();
        var bye = Encode(writer => writer.WriteString("bye", reason));
        foreach (var socket in all) {
            socket.Send(bye);
            _ = socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "bye");
        }
    }

    /// <summary>DM deleted the client: the tabs are told, and the connection lets go on the next update.</summary>
    public void Kick(string reason) {
        if (Closed) return;
        Closed = true;
        CloseSockets(reason);
        Later(() => Connection?.HandleWebDisconnection());
    }

    /// <summary>Away longer than the grace, or an idle guest (game thread): the player logs out as a native one who quits.</summary>
    public void Leave(string reason) {
        Closed = true;
        CloseSockets(reason);
        Connection?.HandleWebDisconnection();
    }

    private void Later(Action work) => _server.Manager.RmWebRun(work);

    private void Post(Action<Utf8JsonWriter> body, string kind) {
        var data = Encode(body);
        RmWebSocket[] all;
        lock (_sockets) all = _sockets.ToArray();
        if (all.Length == 0) {
            _unsent++;   // no tab open: the page asks for everything when it comes back (the game's "ready")
            return;
        }

        foreach (var socket in all) {
            if (socket.Backlog > BacklogLimit) {   // once: the socket goes at once, with what was queued for it
                socket.Abort($"web: {Key}'s tab fell {socket.Backlog >> 20} MB behind; closing it (it reconnects and asks for everything)");
                continue;
            }

            socket.Send(data);
        }

        _sent[kind] = _sent.TryGetValue(kind, out var c) ? (c.Count + 1, c.Bytes + data.Length) : (1, data.Length);
        _sentTotal += data.Length;
    }

    private static byte[] Encode(Action<Utf8JsonWriter> body) {
        var buffer = new ArrayBufferWriter<byte>(256);
        using (var writer = new Utf8JsonWriter(buffer, JsonOptions)) {
            writer.WriteStartObject();
            body(writer);
            writer.WriteEndObject();
        }

        return buffer.WrittenSpan.ToArray();
    }

    private void Ignored(string what) => _ignored[what] = _ignored.TryGetValue(what, out var n) ? n + 1 : 1;

    public void Warn(string text) => _server.Sawmill.Warning(text);

    public void LogStats(double seconds) {
        long received, dropped;
        lock (_paceLock) {
            received = _received;
            dropped = _dropped;
            _received = _dropped = 0;
        }

        if (_sent.Count == 0 && _ignored.Count == 0 && _unsent == 0 && _keysRun.Count == 0 && dropped == 0) return;
        var sent = string.Join(", ", _sent.OrderByDescending(p => p.Value.Bytes).Select(p => $"{p.Key} {p.Value.Count}/{p.Value.Bytes / 1024.0:0.0} KB"));
        var ignored = _ignored.Count == 0 ? "" : "; not for the page: " + string.Join(", ", _ignored.OrderByDescending(p => p.Value).Select(p => $"{p.Key} {p.Value}"));
        if (_keysRun.Count > 0) ignored += "; keys: " + string.Join(", ", _keysRun.OrderByDescending(p => p.Value).Select(p => $"{p.Key} {p.Value}"));
        if (dropped > 0) ignored += $"; from the page: {received} taken, {dropped} dropped (too fast)";
        var total = _sent.Values.Sum(v => v.Bytes);
        var wire = Interlocked.Read(ref _wire);
        var wireNow = wire - _wireLogged;
        _wireLogged = wire;
        _server.Sawmill.Info($"web: {Key} {seconds:0} s: {_sent.Values.Sum(v => v.Count)} messages, {total / 1024.0:0.0} KB ({total / 1024.0 / seconds:0.0} KB/s; {_sentTotal / 1024.0:0} KB since joining), " +
                             $"{SocketCount} tab(s){(_unsent > 0 ? $", {_unsent} with no tab open" : "")}{(Behind > 0 ? $", {Behind / 1024.0:0.0} KB still queued" : "")}" +
                             $"{(wireNow != total ? $", {wireNow / 1024.0:0.0} KB on the wire ({wireNow / 1024.0 / seconds:0.0} KB/s)" : "")}: {sent}{ignored}");
        _sent.Clear();
        _ignored.Clear();
        _keysRun.Clear();
        _unsent = 0;
    }
}

/// <summary>One open tab's socket: a receive loop, and sends queued in order on their own task.</summary>
internal sealed class RmWebSocket {
    // a page's message: its keys, answers and size are tiny, but a box selection of a big company names every unit
    // (boxrefs/selectmany, ~18 bytes a unit URL-encoded): 256 KB fits ~14,000 units, for the very large companies the
    // game aims at (2,000-unit companies are tested today); more than that closes the tab
    private const int MessageLimit = 256 << 10;
    private static readonly TimeSpan SendTimeout = TimeSpan.FromSeconds(20);   // one message on the wire: longer, and the reader is gone or stalled
    private readonly RmWebLink _link;
    private readonly WebSocket _socket;
    private readonly ConcurrentQueue<byte[]> _out = new();
    private int _sending;
    private long _backlog;
    private int _closing;   // 1 once aborted (too far behind, a send timed out, a flood): nothing more is queued

    public RmWebSocket(RmWebLink link, WebSocket socket) {
        _link = link;
        _socket = socket;
    }

    public long Backlog => Interlocked.Read(ref _backlog);

    // the tab's deflate stream, kept from message to message (only the send task touches it once it exists)
    private volatile bool _deflateOn;
    private System.IO.Compression.DeflateStream? _deflate;
    private MemoryStream? _deflated;

    /// <summary>The page can inflate (its hello said "z": 1): every message from the next one goes compressed.</summary>
    public void DeflateFromNow() => _deflateOn = true;

    // A message as its binary frame: its length, then its bytes through the kept stream, flushed (a sync flush ends
    // on a whole byte, so the page inflates all of it now).
    private byte[] Compress(byte[] data) {
        _deflated ??= new MemoryStream();
        _deflate ??= new System.IO.Compression.DeflateStream(_deflated, System.IO.Compression.CompressionLevel.Optimal, leaveOpen: true);
        _deflated.SetLength(0);
        _deflate.Write(data, 0, data.Length);
        _deflate.Flush();
        var n = (int)_deflated.Length;
        var frame = new byte[4 + n];
        System.Buffers.Binary.BinaryPrimitives.WriteUInt32BigEndian(frame, (uint)data.Length);
        Array.Copy(_deflated.GetBuffer(), 0, frame, 4, n);
        return frame;
    }

    public async Task Run(CancellationToken stop) {
        _link.Attach(this);
        var buffer = new byte[64 * 1024];
        var text = new MemoryStream();
        try {
            while (_socket.State == WebSocketState.Open && !stop.IsCancellationRequested) {
                var result = await _socket.ReceiveAsync(new ArraySegment<byte>(buffer), stop);
                if (result.MessageType == WebSocketMessageType.Close) break;
                if (text.Length + result.Count > MessageLimit) {   // a page never sends this much at once
                    Abort($"web: {_link.Key}'s tab sent a message over {MessageLimit >> 10} KB; closing it");
                    break;
                }

                text.Write(buffer, 0, result.Count);
                if (!result.EndOfMessage) continue;
                if (!_link.FromPage(this, Encoding.UTF8.GetString(text.GetBuffer(), 0, (int)text.Length))) {
                    Abort(null);   // kept sending too fast (FromPage said why)
                    break;
                }

                text.SetLength(0);
            }
        } catch (Exception) {
            // the tab went away
        } finally {
            _link.Detach(this);
            try {
                _socket.Dispose();
            } catch (Exception) { }
        }
        // the deflate stream: let go once the send task is done with it (it may still be sending)
        while (Volatile.Read(ref _sending) != 0) await Task.Delay(20);
        _deflate?.Dispose();
        _deflated?.Dispose();
    }

    public void Send(byte[] data) {
        if (_socket.State != WebSocketState.Open || Volatile.Read(ref _closing) != 0) return;
        Interlocked.Add(ref _backlog, data.Length);
        _out.Enqueue(data);
        if (Interlocked.CompareExchange(ref _sending, 1, 0) == 0)
            _ = Task.Run(Drain);
    }

    /// <summary>The socket goes now, once (later calls do nothing), and what was queued for it is let go; the receive
    /// loop then ends and the tab is detached. why: the log's warning (null: already said).</summary>
    public void Abort(string? why) {
        if (Interlocked.Exchange(ref _closing, 1) != 0) return;
        if (why != null) _link.Warn(why);
        try {
            _socket.Abort();
        } catch (Exception) { }

        while (_out.TryDequeue(out var data))
            Interlocked.Add(ref _backlog, -data.Length);
    }

    private async Task Drain() {
        while (true) {
            while (_out.TryDequeue(out var data)) {
                try {
                    if (_socket.State == WebSocketState.Open && Volatile.Read(ref _closing) == 0) {
                        var binary = _deflateOn;
                        var frame = binary ? Compress(data) : data;
                        using var timeout = new CancellationTokenSource(SendTimeout);
                        try {
                            await _socket.SendAsync(new ArraySegment<byte>(frame), binary ? WebSocketMessageType.Binary : WebSocketMessageType.Text, true, timeout.Token);
                            _link.Wire(frame.Length);
                        } catch (Exception) when (timeout.IsCancellationRequested) {
                            Abort($"web: {_link.Key}'s tab took over {SendTimeout.TotalSeconds:0} s to take a message; closing it");
                        }
                    }
                } catch (Exception) {
                    // closed while sending: the receive loop ends it
                }

                Interlocked.Add(ref _backlog, -data.Length);
            }

            Volatile.Write(ref _sending, 0);
            if (_out.IsEmpty || Interlocked.CompareExchange(ref _sending, 1, 0) != 0)
                return;
        }
    }

    public async Task CloseAsync(WebSocketCloseStatus status, string reason) {
        try {
            // after what is queued (a "bye" goes first)
            for (var i = 0; i < 20 && Backlog > 0 && _socket.State == WebSocketState.Open; i++)
                await Task.Delay(50);
            if (_socket.State == WebSocketState.Open)
                await _socket.CloseOutputAsync(status, reason, CancellationToken.None);
        } catch (Exception) { }
    }
}
