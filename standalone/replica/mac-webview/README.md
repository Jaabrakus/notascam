# Mac browser panels

This module implements the existing Robust browser interfaces with native macOS
`WKWebView` controls. It uses the original DM-generated HTML, CSS, JavaScript and
game resource requests. Game links still pass through OpenDream's original
`BeforeBrowseHandler` and `MsgTopic` handling; game procedures are unchanged.

The Swift bridge embeds each view inside the exact SDL-backed NSWindow for its
owner, using the SDL window ID rather than window titles. Browser rectangles
follow the engine's pixel layout and the native window's point dimensions, so
resizing and Retina scaling do not require fixed offsets. AppKit operations and
SDL window lookups run on the main thread. Native navigation/resource events are
queued back to the engine thread before calling game handlers.

Local `http://127.0.0.1/` resources use a private WebKit URL scheme; the adapter
maps them back to the original URLs before invoking the existing cache loader.
No extra HTTP server is opened. The adapter also corrects the client’s embedded pane sizing: pane roots stretch to their splitter allocation, and a zero-size child control fills the remaining canvas area. These corrections keep the original DMF descriptors intact. The launcher extracts original zero-size flags from the supplied skin because the published client normalizes those values too early. The retained hints restore fill behavior after runtime pane changes. Native keyboard focus is reflected into the
engine control to avoid executing game macros while typing in a web panel.

The runtime also fixes unnamed `browse()` output: the DMF resource records the
first default browser control and the connection routes output to that control.
The supplied skin already marks `browserwindow.browser` as its default. The
connection also invokes that browser's original `on-show` command when opening
HTML, so the supplied skin can expose and select its browser pane. This is tested
with an initially hidden control. The original skin and DM game source are unchanged.

Run `python3 tools/check_browser.py` from the replica directory for the real
client/server integration check. It verifies default and named panels, an image
sent by `browse_rsc()`, a relative game link, a `byond://` game link, a DM `Topic()`
response, closing a named panel, panel bounds, and a rendered WebKit snapshot.
Add `--legacy` to run the same round trip and bounds checks with the complete original game skin. Results are in `reports/browser-checks.json` and `reports/browser-test.png`.
The test opens its own client on localhost port 12123 and stops both test
processes after completion. The regular game uses port 12121.

Rebuild with `tools/build_mac_webview.py --help`. Inputs are the pinned
RobustToolbox source, .NET 10 SDK and JetBrains annotations assembly. Public
browser interface files are copied from that source into an isolated build
directory; the browser implementation and native bridge are in this directory.
The normal `Play.command` selects the retained module in
`runtime/macos-x64/webview-webkit/` with `web.headless=false`.

HTML behavior follows WebKit. Exact equivalence with historical IE-specific
rendering is not established by these functional checks.

The module also registers the original `CENTER`, `-`, `=`, and `/` key names
against the client's existing keyboard enum before the skin is loaded. An
opt-in `DM_TEST_RACE` environment variable drives the existing race prompt for
`tools/check_client_gameplay.py`; normal play does not enable it. Snapshots from
the engine framebuffer omit the native WebKit overlay, which is checked with
its own WebKit snapshot.

References: [Apple WKURLSchemeHandler](https://developer.apple.com/documentation/webkit/wkurlschemehandler),
[SDL native window properties](https://wiki.libsdl.org/SDL3/SDL_GetWindowProperties),
[BYOND default browser behavior](https://www.byond.com/docs/ref/skinparams.html).
