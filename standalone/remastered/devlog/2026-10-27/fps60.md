# 60 fps in the 3D view (fps60, 2026-10-27)

You asked for "everything to be able to run at 60fps". I measured first, in the real game window. When I suggested
cheaper shading for far-off scenery you said **"i want it look clean and detailed from zoom out to zoom in we can fix
perfamance in a different way"**, so nothing about the look was touched. Then you asked to **remove the 2D tiles in
the background** you saw while resizing. That is what landed.

## What the numbers said

All in the real client on this Mac (M4 mini, 1920x1200 screen), calm village of 40, normal look.

| | 1280x720 window | full-screen window |
|---|---|---|
| Late frames (over 20 ms) | 3% | 1-27%, following how busy the Mac was |
| The 3D view's script per frame | about 1 ms | about 1-2 ms |
| The 3D view's GPU work per frame | about 4 ms | about 4 ms (zoomed right out: about 8 ms) |

- **The scenery is not the bottleneck.** The 3D view uses about a third of a frame at most.
- **Late frames came with no game work in them.** They tracked the Mac's load from other programs (27% late at
  load 14, 4% at 10.6, 1% at 8.5). A player's own game server shares the Mac in the same way.
- **The hidden 2D map was pure waste.** The client kept drawing the old 2D map under the 3D view every frame.

The HUD against the 2D map, full screen (the test you asked for):

| Phase | Late frames | Mac GPU busy |
|---|---|---|
| As is | 4.2% | 38.5% |
| HUD hidden | 3.2% | 35.1% |
| 2D map off | 4.4% | 28.0% |
| Both off | 0.6% | 27.4% |

## Landed: the 2D map goes once the 3D view runs

- **What changed.** As soon as the page's 3D view is running, the game hides the old 2D map control
  (`HUD.dm`, `RemasterHide2DMap`). The client stops drawing it.
- **What you get.** About 10 points of the Mac's GPU back (38.8% shown against 28.8% hidden, same run), roughly 1.7 ms
  every frame. A resize can't show tiles any more: there are none drawn to show.
- **What it doesn't touch.** The world the AI and units use lives on the server, and the 3D view is built from it.
  Clicks in 3D already go through the 3D view, and keys through the client's own key system.
- **Checked in the real window.**
  - The map really is hidden after the 3D view comes up.
  - A click in 3D reached the game.
  - Keys worked with the map hidden. G toggled Gather on and off, and the Up arrow stepped the camera, through both
    key routes. The keys you typed into the test window ran their commands too.
  - One round sent 3 s after the window opened got through to the client but ran nothing. I put that down to the
    window being too new. The confirming rerun was cancelled when you said to land it.
- **For the test tools.** About 30 real-client tools found the game window through the 2D map. They now fall back to
  the biggest window. Six that click the 2D map directly set `RM_KEEP_2D=1`, which keeps it shown for them.

## Not done

- The 200v200 battle and the 2,000-villager town were never measured: the runs broke before reaching them.
- Same-pixel shader savings are written but parked (`reports/polish-night-1026/fps60/work/new/`). They skip work whose
  result is thrown away, so every pixel stays the same, but they are not measured yet and wait for your OK.

## Needs you

- Nothing for this landing.

Tools: `reports/polish-night-1026/fps60/fps_native.py` (real-client frame probe: scenes, phases, GPU sync, key and
click checks) and `gpuab.py` (windowless page A/B). Results under `reports/polish-night-1026/fps60/runs*`.
