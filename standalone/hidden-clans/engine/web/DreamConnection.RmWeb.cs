// Remastered: a player in a web browser, connected to the server directly (engine/web/, U4 of
// planning/SERVER_UPGRADES_PLAN_2026-10-30.md). The web patch (web_patch.py) sends every message this connection sends
// through RmSend: a native player's goes to its Robust session as before, a browser's to its web link (RmWebServer.cs),
// which turns it into what the page needs. DM sees the same /client either way.
using OpenDreamRuntime.Objects.Types;
using OpenDreamShared.Network.Messages;
using Robust.Shared.Network;

namespace OpenDreamRuntime;

public sealed partial class DreamConnection {
    internal RmWebLink? RmWeb { get; private set; }
    private string? _rmWebAddress;   // kept after the browser goes: Logout and client/Del may still read client.address

    /// <summary>client.address for a browser player (null for a native one).</summary>
    internal string? RmWebAddress => Session == null ? _rmWebAddress : null;

    private void RmSend(NetMessage msg) {
        if (Session != null) {
            Session.Channel.SendMessage(msg);
            return;
        }

        if (RmWeb == null)
            return;

        // browse_rsc: the browser fetches the file over HTTP when the page asks for it, so the link keeps it
        if (msg is MsgBrowseResource resource && _permittedBrowseRscFiles.Remove(resource.Filename, out var file)) {
            RmWeb.File(resource.Filename, file.ResourceData);
            return;
        }

        RmWeb.FromServer(msg);
    }

    /// <summary>A browser joined (RmWebServer): the same steps as <see cref="HandleConnection"/>, with no Robust session.</summary>
    internal void HandleWebConnection(RmWebLink link) {
        RmWeb = link;
        link.Connection = this;
        _rmWebAddress = link.Address;

        Client = new DreamObjectClient(_objectTree.Client.ObjectDefinition, this, _screenOverlaySystem, _clientImagesSystem);
        Client.InitSpawn(new());

        _verbSystem?.UpdateClientVerbs(Client);
        SendClientInfoUpdate();
    }

    /// <summary>The browser left for good (or DM deleted the client): <see cref="HandleDisconnection"/>'s steps.</summary>
    internal void HandleWebDisconnection() {
        if (RmWeb == null)
            return;

        RmWeb = null;
        _verbSystem?.RemoveConnectionFromRepeatingVerbs(this);

        if (Client != null) {
            // The client still has a reference to the mob when deleted, so we do this first
            Client.DecRef();
            Client.Delete();
            Client = null;
        }

        if (Mob is not null) {
            var oldMob = Mob;
            SetClientMob(null, true);
            oldMob.SpawnProc("Logout").Dispose();
        }
    }

    /// <summary>DM deleted the client (DreamObjectClient.HandleDeletion): the browser is told and let go.</summary>
    internal void RmWebKicked(string reason) => RmWeb?.Kick(reason);
}
