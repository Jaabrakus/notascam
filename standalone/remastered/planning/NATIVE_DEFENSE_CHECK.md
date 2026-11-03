# Native original-unit defense and work resume

Verified privately on 2026-10-17, 06:28:15–06:28:58 UTC. This is a staged,
mapless encounter using original Human/Orc constructors and their original stats,
movement timers, inventory procedures and actual client-driven RemasterLoop.
It is not a natural encounter in the four-map world.

## Actual input and effects

- A real client renderer hit-test/network click selects the Human worker and
  orders a natural, original 250-HP Tree1 to be chopped.
- The loaded native WebKit page's actual Add tasks button enables queue mode;
  a second map hit-test/network click appends a Move. These are internal targeted
  callbacks, with no OS mouse injection or physical touchscreen claim.
- The fixture gives the worker a real Quality MetalAxe through CraftItem,
  PickUpItem and EquipItem; the enemy receives a real bow, quiver and one arrow.
  Human capacity110, starting weight25, WoodCuttingSkill20 and Delay4 are unchanged.
- After genuine tree damage and the pending Move exist, the fixture calls the
  Orc's original BowTarget once. The consumed arrow triggers the real attack hook,
  including the original hit/miss randomness. No damage/invulnerability override.
- A worker eight tiles diagonally away and an idle helper eight cardinal tiles
  away respond. Cardinal/diagonal radius9 and other-level controls do not.
- The loaded WebKit Deselect button clears selection while response and exact
  active/pending task objects remain. Once the worker has moved at least two
  tiles, the fixture relocates the still-live attacker to another level to end
  this bounded encounter. This retreat is scripted scenario control.
- The worker returns, resumes the identical Chop task, collects four logs,
  leaves both seeds on the ground, and completes the identical pending Move.
  It finishes at105/110 weight. Both responding helpers return to their original
  positions; the three bounds controls remain idle. All six Humans retain350HP.

The fixture changes private startup/positions/equipment and suppresses original
long world season/spawn/save scheduling. It does not pump the order loop manually,
override combat/movement methods, alter game source, or touch normal saves.

## Defect found by the native test

`defense-native-initial-checks.json` failed to reach the live HUD response:
range(8) admitted the diagonal worker, then the next defense tick rejected it.
The installed compiler standard's get_dist used Euclidean distance, reporting11
for an8-by8 offset. Both the defense leash and bounded path search consequently
excluded the corner of their own hearing square. Existing103 tests checked the
initial diagonal alarm only, then reset before a controller tick.

A BYOND516.1655 oracle confirms tile/Chebyshev distance. The private shared
compiler-standard candidate fixes get_dist, preserving same-reference=-1,
ignoring z and returning positive infinity for distinct invalid/unlocated or
area endpoints. No Defense.dm or Orders.dm workaround was made.

## Evidence

| Evidence | Result |
| --- | --- |
| `tests/defense-native-initial-checks.json` | Before: real diagonal helper abandons response; retained failure |
| `tests/defense-bounds-before-verified-checks.json` | Before:9 of34 boundary assertions fail |
| `tests/defense-native-distance-checks.json` |22/22 native staged encounter checks pass;64 observations |
| `tests/defense-bounds-distance-final-checks.json` |34/34 boundary checks with final candidate |
| `tests/defense-distance-checks.json` |103/103 existing defense regressions |
| `tests/easy-orders-distance-checks.json` |72/72 existing orders regressions |

All successful runs have no runtime errors. Native source and private runtime
hashes were stable, no unexpected native input was logged, and private processes
were stopped. The oracle reports102 matching comparable endpoint cases, versus
35 failures before. It separately preserves two unrelated area-constructor
placement mismatches: BYOND new/obj(area) selects a turf, while the replacement
engine leaves loc=/area and exposes different coordinates. Full104-case parity
is explicitly false; this distance change does not claim to fix area placement.

Candidate stage: `/tmp/dm-runtime-audit/get-dist-stage/`.
Final standard SHA256:
`56851ae14a16ccb715a723b595a894985f1e6c4cae3bdd3b176a297e8eb1093b`.
Runtime:
`f81a365897c80b9cbb748ba821d6c6a4e3f77760465fee17c18c62fba87d060d`.
Client:
`5481500f48d338c1525c1bca98d821d5f7d42178544385f4fd6c7189c06d160a`.

## Repeat without replacing evidence

`check_defense_native.py` supports unique `--label`, `--port`, `--compiler-dir`,
`--server-dir`, `--client-zip`, `--client-assemblies-dir`, and `--webview-dir`.
It refuses to overwrite an existing evidence label. The accepted private module
is `/tmp/dm-runtime-audit/full-world-orders-stage/engine/webview-webkit`; it adds
read-only observations and opt-in internal map/WebKit callbacks. Canonical
NativeUiProbe and the installed WebView module were unchanged by this check.
