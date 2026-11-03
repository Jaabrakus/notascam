// Remastered: browsers play on the server directly (engine/web/, U4 of planning/SERVER_UPGRADES_PLAN_2026-10-30.md).
// RM_WEB_PORT in the server's environment starts the web link (RmWebServer.cs) with the server; without it nothing
// listens and nothing changes. What the browser asks for runs here, on the game thread, at the start of each update:
// before the tick's DM, as Robust reads its players' messages.
using System.Collections.Concurrent;
using System.Threading.Tasks;
using Robust.Shared.Network;

namespace OpenDreamRuntime;

public sealed partial class DreamManager {
    private readonly ConcurrentQueue<Action> _rmWebWork = new();
    private readonly Dictionary<string, NetUserId> _rmWebIds = new();   // a web player's key -> their connection's id, kept for rejoins
    private RmWebServer? _rmWeb;

    private void RmWebStart() {
        if (!int.TryParse(Environment.GetEnvironmentVariable("RM_WEB_PORT"), out var port) || port <= 0)
            return;

        var bind = Environment.GetEnvironmentVariable("RM_WEB_BIND");
        if (string.IsNullOrWhiteSpace(bind))
            bind = "127.0.0.1";

        try {
            _rmWeb = new RmWebServer(this, bind, port);
            _rmWeb.Start();
        } catch (Exception e) {
            _sawmill.Error($"web: cannot listen on {bind}:{port}: {e.Message}");
            _rmWeb = null;
        }
    }

    private void RmWebStop() => _rmWeb?.Stop();

    internal void RmWebRun(Action work) => _rmWebWork.Enqueue(work);

    internal Task<T> RmWebOnMain<T>(Func<T> work) {
        var done = new TaskCompletionSource<T>(TaskCreationOptions.RunContinuationsAsynchronously);
        _rmWebWork.Enqueue(() => {
            try {
                done.SetResult(work());
            } catch (Exception e) {
                done.SetException(e);
            }
        });
        return done.Task;
    }

    private void RmWebPump() {
        if (_rmWeb == null)
            return;

        while (_rmWebWork.TryDequeue(out var work)) {
            try {
                work();
            } catch (Exception e) {
                _sawmill.Error($"web: {e}");
            }
        }

        try {
            _rmWeb.Tick();   // each link's part is caught there too; nothing of the link's reaches the game's update
        } catch (Exception e) {
            _sawmill.Error($"web: {e}");
        }
    }

    /// <summary>A web player's key has (or had) a connection here (game thread).</summary>
    internal bool RmWebKnows(string key) => _rmWebIds.ContainsKey(key);

    internal int RmWebIdCount => _rmWebIds.Count;

    /// <summary>A guest is gone for good (game thread; RmWebServer.EndLink): their connection and id go too, unless the
    /// key is in use again. True when something was let go.</summary>
    internal bool RmWebForget(string key) {
        if (!_rmWebIds.TryGetValue(key, out var userId))
            return false;

        if (_connections.TryGetValue(userId, out var web)) {
            if (web.Session != null || web.RmWeb != null)
                return false;
            _connections.Remove(userId);
        }

        _rmWebIds.Remove(key);
        return true;
    }

    /// <summary>A browser joins as key: a web player's own connection again, or a new one; null when a native player has that key.</summary>
    internal DreamConnection? RmWebConnect(string key, RmWebLink link) {
        foreach (var connection in _connections.Values) {
            if (connection.Key == key && connection.Session != null)
                return null;
        }

        if (!_rmWebIds.TryGetValue(key, out var userId)) {
            userId = new(Guid.NewGuid());
            _rmWebIds.Add(key, userId);
        }

        if (!_connections.TryGetValue(userId, out var web)) {
            web = new DreamConnection(key);
            _connections.Add(userId, web);
        }

        web.HandleWebConnection(link);
        return web;
    }
}
