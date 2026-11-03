# HUD and controls (2026-10-26, hud-controls session)

Picked up the HUD and RTS-controls work from the HUD-craft and RTS-feel chats.

## Done
- Read where the HUD and controls stand at build 56 and wrote it up: `reports/hud-controls/README.md` (what's in the
  app, what's rough, the tools).
- No game change yet; waiting for the owner's go.

## Open for the owner
- Menu entries for bug reports, admin chat and developer logs (keys only before, unreachable now)?
- Enter: keep it unbound until kingdom chat and pigeons, or start the chat box now?
- Keep chasing Select all's last slow frame (~1 in 3, ~34 ms), or leave it?
- Build-panel hints as buttons?
- Fix keys lost when the window has no focus (a Mac app change)?

## Afternoon
- **Build panel:** "No stockpile yet" and "Set the Builder job" are now buttons that open those places (staged; checked
  in WebKit at two window sizes, 26/26). ![hints](../../reports/hud-controls/staged/build-hints/check/hints-1440x900.png)
- **"One sprite lags behind" when queueing gathering:**
  - Found: a working unit's animated figure was placed part-way along its last step and stayed there for the whole job.
  - It also stayed at the old tree for a moment when the unit walked on.
  - The fix is staged and checked in WebKit (14/14), waiting on a review by the 3D session.
- **Key check in a real window:** parked while the owner plays.

## Gather bar and Build bar (stills for the owner's pick)
- **Gather on** turns the bottom bar into a Gather bar: Tend on/off (T) where Lethal was, and Gather zone where Plan was.
- **B** (or a new Build button) opens a Build bar: Build list, Set blocks, Workbenches and Construction.
- **Suggestions** sit in a dashed strip above the bar, so the owner can say yes or no to each.
- **The bar now has room** for all of it, clear of the unit card. Before, a ninth button squeezed "Do now".
  ![bars](../../reports/hud-controls/staged/bars/stills/bars-sheet.png)
- **The owner picked:**
  - Gather bar: yes to all three extras (Takes, Auto unload, Stockpile here), now in a row above the bar.
  - Build bar: no extras.
  - Keys: B (Build bar) and T (Tend).
- **Staged:** the page, the keys and the key check's update. Checked in WebKit at two window sizes (42/42) and with the
  key check on a patched copy (17/17). Lands together with the gathering session's server side.
  ![final bars](../../reports/hud-controls/staged/bars/stills-final/bars-final-sheet.png)
- **Landed for build 58:**
  - the Build panel hints;
  - the doll fix: a working unit's sprite stays with it;
  - the Gather bar and Build bar with the B key.
  - The Tend removal follows with the regrowing work.
