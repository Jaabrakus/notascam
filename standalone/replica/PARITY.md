# Measured compatibility

The replacement runs the supplied Dungeon Master code without BYOND to play.
It is **not yet a verified exact replica**. The tracked acceptance criteria are
in [COMPLETION_CHECKLIST.md](COMPLETION_CHECKLIST.md); the source-to-scenario
inventory is in [COVERAGE.md](COVERAGE.md).

## Corrections retained in this build

- Constructor `usr` context, FIFO equal-tick scheduling, collision callback
  targets, movement return values and coordinate restoration from nullspace.
- Structural expansion of ambiguous compact conditionals in the staged source;
  the frozen source remains unchanged. Minimal branch comparisons and original
  gameplay comparisons exercise the resulting binding.
- Native object-graph saves, shared references, temporary-field exclusions,
  restored icon resources and fresh-process unit restoration.
- Original MT19937 `rand`, `prob`, ordinary `pick` and weighted `pick` sequences,
  including single-precision range boundaries and negative one-argument ranges.
  Wandering now uses an independent stream. Open-terrain direction distributions
  pass eight 10,000-draw comparisons; exact sequences and edge-following remain open.
- Empty self-calls forward current arguments, including modified arguments, as
  used by the original injury/combat branches.
- Ordered container contents, including reassignment to the same container;
  contained objects are deleted with their container and deleted objects no longer
  pass typed-object checks; text-recipient output is
  a no-op as measured in the reference.
- Icon rotation accepts atom icon resources, preserves its input, and indexes
  each atlas frame locally. The square quarter-turn fixture compares pixels.
- Legacy DMI state escaping and hotspots. All 163 original DMI assets compare
  successfully against the original engine's exported pixels and metadata.
- Original map-object repopulation, static/map tag indexing, text-file append
  and CRLF behavior, and uncached reads of updated text files.
- Explicit world reboot through the local supervisor, native-client reconnect,
  replacement of verb snapshots, cleanup of old window IDs and resource caches.
- Original browser routing and skin fill/layout behavior, native WebKit panels,
  legacy key names, and independent local client connections.
- Random-step obstacle rejection prevents the recursion observed in enclosed NPC
  neighborhoods. Independent movement randomness and open-terrain forward bias are corrected.
  The original 5x5 edge-following rule remains unmatched.

## Evidence and limits

Reports retain ordered expected/actual observations, fixture and runtime hashes,
and original engine version. `reports/fidelity-checks.json` is the aggregate
result and reports failure immediately if a component fails. A passing result
covers its listed checks only.

| Reports | Verified scope / important limits |
| --- | --- |
| `foundation-checks.json` | 309 source hashes, constructor/scheduler fixture and full-world startup; startup alone does not certify continued simulation |
| `map-geometry-checks.json`, `map_layout-parity.json` | Four maps, 4,000,000 cells, 1,396 object placements and overrides; separate runtime layout fixture; no full post-constructor population equivalence |
| `icon-assets-checks.json` | 163 DMI assets, including 53 legacy conversions; does not certify client rendering, fonts or animation timing |
| `persistence-parity.json`, `coordinates-parity.json` | Object graphs, cycles, nested inventory, exclusions and coordinate restoration |
| `movement-parity.json`, `bump_reentry-parity.json` | Callback targets/order, blocked/clear/diagonal/distant moves and nested callbacks |
| `gameplay-parity.json`, `gameplay_reload-parity.json` | Ordinary race setups, selection, ownership, wall blocking, arrival, damage, attacks, items and original game saves |
| `systems-parity.json` | Nine control groups, ownership, limb masks, weapon damage types, cooldowns, flight and all 15 race branches with save/load in a bounded arena |
| `branching-parity.json`, `compiler_edges-parity.json` | Compact conditional forms, 24 admin-editor conditional cases, switch defaults, membership precedence, parent no-ops and `src` parameter shadowing |
| `randomness-parity.json` | Five seeds; random, probability and pick variants; 30,000 long-run draws and boundary cases; excludes random walking stream |
| `self_call-parity.json` | Implicit self-call forwarding, modified arguments, explicit null and empty argument lists |
| `contents_order-parity.json`, `deleted_refs-parity.json`, `output_targets-parity.json` | Ordered inventory mutations, deleted aliases and offline/text output recipients |
| `icon_turn-parity.json` | Square icon pixel results for five quarter-turn angles and atom-icon resources; arbitrary-angle/non-square behavior remains open |
| `crafting-inventory.json`, `crafting-parity.json` | 14 workshop types, 239 inventoried choices, 698 missing-material/high-skill/zero-skill scenarios; race-specific unavailable choices, altar spells and an original smelter error are explicitly excluded |
| `repopulation-parity.json`, `reboot-parity.json`, `text_io-parity.json` | Deleted map-object restoration, moved-object preservation, reboot persistence and text append/newline behavior |
| `lifecycle-checks.json` | Two real native clients, independent armies/health, original SaveUnits, world reboot, reconnect and LoadUnits; no reference graphical multiplayer/latency comparison |
| `client-gameplay-checks.json` | Real race prompt, save/restart/reload and observed unit/equipment/location state |
| `browser-checks.json` | Complete-skin harness, native browser images/links, named panels and tested layouts |
| `random_step_blocked-parity.json` | Enclosed dense turf/object neighborhoods reject random movement without collision callbacks |
| `world-long-checks.json`, `world-reference-checks.json`, `world-long-comparison.json` | Both engines reached Winter over 11,000+ ticks. Both report deleted-target overlays/LimbFling/SunLight errors. Population parity and error-free stability are not established. |
| `world-soak-checks.json` | Current candidate completed a fresh 1,200-tick run with four deleted-target LimbFling errors; this is a failed clean-soak check. |
| `wander_invariants-parity.json`, `wandering-checks.json` | Wandering does not advance combat RNG, change facing/position or invoke collision callbacks; repeated queries preserve map tiles. Eight open-terrain distributions pass declared tolerances; edge-following and sequence identity remain open. |
| `mac-app-checks.json`, `mac-app-package.json` | Relocated native Mac package and personal save import; inspect current status and listed save/reload exclusions. |

All report paths above are under `reports/`. `random_step-reference-run.log`
retains the initial discrepancy. `wander-probe-first.log` and
`wander-probe-second.log` record the still-unmatched obstacle distributions.

The gameplay/system/crafting comparisons use original procedures in small arenas
with geographic spawn searches bounded and world event loops disabled. Headless
choice functions supply test input; they do not certify physical keyboard/mouse
behavior. Fixture substitutions and exclusions are retained beside the reports.
The full-world soak uses the original maps and event loops. The original reference
itself produced null-target errors in `Attack()`; preserving its source does not
mean those errors can be counted as a clean stability pass in the replacement.

## Repeat the checks

From this directory:

```sh
python3 tools/check_fidelity.py --full
python3 tools/check_world_soak.py --ticks 11000
```

Add `--reference` to the fidelity command to refresh the isolated BYOND oracle.
That development-only comparison requires Docker and its prepared reference image.
Normal play and checks against retained reference logs use the retained runtime.

```sh
python3 tools/local_runtime.py compile
python3 tools/play.py
```

The runtime builder, client IL patcher, native WebKit builder and standard-library
patcher are in `tools/`. Retained compatibility source and generated patches are
in `engine/`. Original project files and `source/` remain unchanged.

## Outstanding acceptance

Exact fonts, overlays, physical input and timing require equivalent original-client
captures and input traces. Complete combat/status/building coverage, AI direction
edge-following and exact wandering sequences, full population/event equivalence, multiplayer
interactions under latency, and BYOND binary-save migration remain open. Native
JSON saves work within the tested scope; old binary saves are unsupported.

## Standalone application

`Dungeon Master.app` bundles the runtime, server, client and game assets. Playing
does not invoke Python, BYOND, Docker or a development SDK. The native launcher
copies writable client data and game state to Application Support, preserves
existing standalone saves on first launch, and requests the original `SaveUnits()`
procedure before shutting down its local server. This explicit local-host save
is an added hosting behavior; the original game relies on a persistent server.
The compiled game source remains unchanged.

The application uses macOS system frameworks and Rosetta 2 for the bundled x64
engine on Apple Silicon. The package has only been tested on this Mac.
