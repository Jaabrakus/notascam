# Playing in a web browser

Started and first played 2026-10-22. Status: **works**, both on a private test world and
against the app's own *Host for friends* world (run from a copy of the real save folder):
a browser tab joined with the password, chose a race with the R macro, got three Dwarves,
selected one from the company list, gave it an order by clicking, and came back to the
same state after a page reload; the host's native client and server logged no errors.
Friends' instructions: [JOIN_IN_BROWSER.md](../JOIN_IN_BROWSER.md). Not yet tried from a
second computer.

## What the game already is

- The whole player-facing UI is one HTML page, `game/Interface/remastered.html`:
  the HUD, the cards, and the 3D world (WebGL). It renders everything itself.
- The server pushes state into that page with four JavaScript calls
  (`updateHUD`, `update3D`, `move3D`, `key3d`), each sent as
  `src << output(..., "mapwindow.hud:<fn>")` ([HUD.dm](../game/Code/Remastered/HUD.dm),
  [View3D.dm](../game/Code/Remastered/View3D.dm)).
- The page talks back with one mechanism: `send()` navigates to
  `byond://?rm=<action>&value=...`, which the client turns into a Topic call.
- Images (portraits, sprite sheets, 3D textures, `model-*.json`) are fetched by
  plain relative URLs, served from the client's resource cache (`browse_rsc`).
- The native client's job is therefore: hold the engine connection, host the
  page in a WebKit view (`mac-webview/`), route those calls in and the
  `byond://` links out, and show the few native prompts the game still uses
  (`input()`/`alert()`: the join password, the race list, the welcome text).

So a browser version needs no new renderer or protocol: the page is served to a
real browser and the WebKit plumbing is replaced by a WebSocket.

## How it works: one headless relay client per browser player

```
browser  <--http/ws-->  Robust.Client --headless (+ engine/webview-relay)  <--udp-->  Robust.Server (OpenDream)
                        one process per web player, on the hosting Mac
```

- **`web-relay/` → `engine/webview-relay/Robust.Client.WebView.dll`** (built by
  `tools/build_web_relay.py`): a second implementation of the engine's WebView
  module, same assembly name and interfaces as `mac-webview/`, picked with
  `ROBUST_MODULE_ROBUST_CLIENT_WEBVIEW`. Instead of a WebKit panel it runs an HTTP
  + WebSocket server on `DM_WEB_RELAY_PORT`:
  - `GET /` serves the HUD page through the control's own resource handlers, with
    a shim script added (`RelayShim.cs`), `send()` rerouted to the socket, and
    `overlayHost` forced on so the layered HUD is built. `GET /<file>` serves
    resources the same way. `/health` says `ready` once the page exists.
  - `ExecuteJavaScript` → socket `{js}`. Page → `{nav: "byond://..."}` → the
    BeforeBrowse handlers → Topic. `{cmd}` runs a skin command like a macro would.
  - Native prompts (`PromptWindow` subclasses) are described to the page
    (`{prompt}`), drawn as a card, and answered through `FinishPrompt` by
    reflection. The join password is answered from `DM_JOIN_PASSWORD`.
  - Keys go to the engine (`IInputManager.KeyDown/KeyUp`) so the skin's macros
    work; the page's own key handlers are skipped, as in the native app where the
    game window has the keyboard. Typing in fields, prompt cards and Escape stay
    with the page.
  - The combat-log mirror (`RemasterChatRelay`) is reused as is.
  - The client quits by itself once no browser has been connected for
    `DM_WEB_RELAY_IDLE` seconds (90).
- **`tools/web_host.py`** runs on the hosting Mac: a lobby page (name + password)
  that, per player, copies the client runtime to a temp folder, starts
  `Robust.Client.dll --headless` with the relay module on a free port
  (12200-12299), waits until it answers, and sends the browser there.
  `--private-world` starts a throw-away world for testing.

## Three things headless needed (all in the module)

1. `ResourceCache.PreloadRsis` calls `GL.GetInteger` unconditionally in release
   builds; without a window that throws. `HeadlessGL.cs` installs stub OpenGL
   bindings (glGetIntegerv answers 4096, all else no-ops), and texture preloading
   is off (`res.texturepreloadingenabled=false`).
2. The client only knows the mob's verbs for entities the renderer saw last frame
   (`DreamViewOverlay.EntitiesInView`); nothing renders headless, so macros found
   no verb. `RelayView.cs` fills that set around the player twice a second.
3. The skin's command input keeps keyboard focus, and the engine then withholds
   every key binding (what `DreamSeekerKeys` works around natively); the relay
   releases focus before injecting a key.

Two game-side changes: `ready` from the page now also resets the 3D send state so
a reloaded page gets the whole scene again (HUD.dm), and `Player/Login()` resends
the HUD page when a player's new client attaches to their existing mob (Joining.dm).

## Cost

Measured 2026-10-22 on this Mac (x64 build under Rosetta, no ReadyToRun): a relay
client with three Dwarves uses 110–300 MB and 45–70 % of one core (the higher CPU on the
real, larger world). Ten web players
would need a few GB and most of the cores, on top of the server (1.5–2.7 GB). An
arm64 build of the client, or ReadyToRun, would likely cut the CPU a lot.

## Not done yet

- Not tested against the app's "Host for friends" world or from a second
  computer; only `--private-world` on this Mac.
- Sounds; the Announcement / ChatLog / EmoteLog browser windows; a single-port
  reverse proxy (players get their own port now); HTTPS; a "Host on the web"
  button in the launcher.
- Player identity is the name typed in the lobby; the host's own saves are keyed
  by Mac login name as before.
