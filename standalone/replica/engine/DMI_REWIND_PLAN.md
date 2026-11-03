# Rewind animation audit and proposed scope

This is an audit and privately tested candidate, not an installed playback
change. The October 17 idle/walking variant engine remains the baseline.
Original sprite files and normal profiles were not changed.

## Observed behavior

[The isolated audit](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/dmi-edge-audit.json)
inventories 1,712 original states. All use infinite looping (`loop = 0`); none
needs finite-loop-count support. Ten states request rewind. Eight belong to
unreferenced Naga/FemaleNaga resources. The `sand2` dragon state is in a referenced
resource, but included dragon code selects `sand`/`flyingsand` instead.

`Icons/Tapestries.dmi`, state `Retribution`, is reachable: creating a clan with
that name makes its placed tapestry use the matching state. It has 45 frames
with 0.1-second delays and requests rewind. The actual replacement client frame
selector currently plays 0 through 44 and wraps to 0 without reverse traversal.
Its generated `icon()` copies also omit the rewind flag. Original pixels match
the BYOND-generated frame cells; the discrepancy is metadata and playback.

The same audit checks all six groups with duplicate name and movement flag
(20 extra occurrences). BYOND 516.1655 selects the first occurrence for both
direct and copied constructors in every group, matching the replacement. This
includes the reachable Demon `NoLeftArmNoLeftLeg` injury state. No duplicate
selection change is warranted.

## Established reference behavior

[The additional BYOND fixture](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reference/dmi-rewind-audit/metadata-byond/audit.dm)
and [its results](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reference/dmi-rewind-audit/metadata-byond/metadata.json)
show that rewind survives a selected constructor, a full copy, a selected copy,
neutral color multiplication, `Turn(90)`, and insertion under a new name. It
also survives explicit movement extraction and extraction of a single frame.
A single-frame state must remain static despite retaining that metadata.

The official [Insert reference](https://www.byond.com/docs/ref/info.html#/icon/proc/Insert)
describes negative delays enabling rewind and positive delays disabling it.
The [constructor reference](https://www.byond.com/docs/ref/info.html#/icon/New)
describes state/direction/frame/movement extraction. Those references do not
specify whether endpoints are repeated or how reverse traversal associates
unequal frame delays. The [BYOND developer's bouncing-ball example](https://www.patreon.com/BYOND/posts/fighting-with-156456425)
confirms the intended reverse motion but does not settle those timing details.
The missing details were measured with a private BYOND client using the official
[RenderIcon API](https://www.byond.com/docs/ref/info.html#/client/proc/RenderIcon).
[The retained oracle](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reference/dmi-rewind-audit/native-reference-checks.json)
passes 17 checks across 840 rendered captures, with zero observed input/errors.
Fixtures use original sprite cells; no artwork is drawn or changed.

- Infinite rewind visits `0..N-1,N-2..1`, with no repeated endpoint.
- Every visit uses that displayed frame's delay. Three frames with delays
  `[3,5,8]` deciseconds follow `[0,1,2,1]` for `[3,5,8,5]` deciseconds.
- One frame stays static; two frames alternate with their original delays.
- Explicit `flick()` ignores rewind: it plays forward once, then restores the
  underlying appearance after the forward delays.

[The separate phase oracle](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reference/dmi-rewind-audit/native-phase-checks.json)
adds 416 captures. Late shared resources, newly generated resources with a
different state name, and restored appearances join the ongoing cycle rather
than restarting at frame zero. This supports retaining the existing infinite
loop clock (`gameTiming.CurTime`) used by ordinary animations. Newly loaded art
can briefly show its first frame. Sequential RenderIcon requests can straddle
boundaries, so distinct resources are compared within neighboring captures;
no cross-client absolute-clock phase parity is claimed. Server request times
are quantized and can jitter; duration evidence uses repeated-cycle medians.

## Proposed narrow implementation

1. In the retained runtime patch builder, add `Rewind` to `DreamIcon.IconState`,
   copy it in `IconState.Copy`, preserve it from each selected source state in
   `InsertState`, and emit it from `GenerateDMI`. Leave the existing loop-count
   policy and Insert direction/frame/delay support outside this change.
2. Add a separately retained client patch after movement/variant support. Resolve
   the active variant exactly as today, retain stationary movement-only frame 0,
   and apply reverse traversal only to rewind states. Use source frame indices
   and original delays; do not duplicate pixels or rewrite texture caches.
   Keep the ordinary forward-only path unchanged. Only intercept infinite-loop
   rewind states, after the existing stationary and completion checks.
3. Preserve the forward-only Flick scheduler, as the oracle requires. The new
   focused client probe checks its forward indices and completion. The existing
   completed-flick texture fallback edge remains outside this narrow patch.

The proposed ownership is `build_compat_runtime.py`, a new `PatchRewind.cs`,
`PatchClient.cs`/`build_client_compat.py` wiring, and dedicated reference/probe
files. No shared parser rewrite is required: it already reads and exports the
rewind flag. All builds would first go into a new private stage, preserving the
first variant stage and all existing evidence. Root owns installation and app
packaging after review.

The retained runtime has a pre-existing loop-flag polarity issue: GenerateDMI
sets `ParsedDMIState.Loop=false`, while ExportAsText writes that as `loop = 0`.
The client parses `loop = 0` as `Loop=true` (infinite). This candidate leaves
that behavior intact. Its generated tapestry is explicitly observed as
`Loop=true, Rewind=true` by the real selector, so it enters the rewind helper.
The native trace independently confirms reverse traversal and matching phase
for original/generated tapestries. Finite-loop-count fidelity remains outside
scope; no included original state uses it.

## Verification gates

- Establish endpoint sequence and duration with original BYOND rendering,
  including unequal delays and one-/two-/three-frame edge cases.
- Compare original and generated Tapestry metadata and exact frame pixels;
  include copy, selected-frame, movement extraction, Blend, Turn and Insert.
- Exercise actual client selectors over both turnaround points and full cycles,
  including large elapsed-time jumps, stationary/moving transitions, variant
  changes, and single-frame rewind.
- Check ordinary Fire/Water animation is unchanged; run the existing 81 variant,
  36 movement, and 11 generated-icon checks against the new private stage.
- Run a no-input private native trace of the real tapestry plus movement and
  normal-animation controls. Scan world, server and client error logs and
  compare source/runtime hashes before and after.

The candidate passes the [22-check focused suite](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/dmi-rewind-staged-checks.json);
the previous engine fails 15 of those same checks. Existing variant (81),
movement (36), and generated-icon (11) suites pass. The [native integration
probe](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/dmi-rewind-native-checks.json)
passes 51 checks with 254 actual render samples, all 45 tapestry frames, 97
reverse steps for each original/generated tapestry, exact visible pixels,
unchanged movement/equipment controls, and zero input or logged errors.

The final [staging manifest](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/dmi-rewind-staging.json)
records source/artifact paths, hashes, and installation ownership.
