# Original starting army: full-world two-tree queue

This private check starts the unchanged four-map Remastered world, completes the
original Human race prompt, and uses its three original Human units. It adds one
observer include to a private DME wrapper; the observer records objects and
chooses nearby reachable natural tree candidates. It does not create units,
resources, tools or terrain, change stats, override movement/collision, or disable
world AI/defense. Source and runtime hashes belong to the copied snapshot.

## Original gameplay constraints

[Restart.dm](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Restart.dm:129)
gives each starting Human a Quality MetalAxe and equips original gear through
`EquipItem`. [Human defaults](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Mobs.dm:330)
include capacity 110 and WoodCuttingSkill 20. The first Human also carries a stone;
the observer picks the Human with most free capacity without changing inventory.

A natural [Tree1](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Building/TurfTypes.dm:231)
has 250 HP. The original [tree collision](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Creatures/Bump.dm:94)
reduces it using the worker's skill and creates four wood plus two seeds for a
Human. Each [wood weighs 20](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Turfs.dm:5359),
so eight logs cannot fit alongside starting gear. The test uses the existing
stockpile and automatic-unload controls and checks conservation across carried
and deposited logs. Capacity and original equipment remain in effect.

## Exact input and observation boundary

- Race startup uses the existing opt-in client smoke driver: original Restart
  command and original prompt callbacks.
- Selecting the real starting worker and ordering the two natural trees use
  `ControlMap`/`MouseInputSystem`, the rendered hit map, and network click events.
  Every hit must match the intended unit or turf before the command is sent.
- Stockpile, wood filter, automatic unloading, Add tasks and Deselect use actual
  loaded native WebKit DOM buttons. Their existing handlers navigate through
  `send()` → `byond://` → network `client.Topic` → server HUD validation. These
  commands do not use an HTTP game endpoint.
- Camera positioning alone calls the existing browser `send('camera', value)`
  route so the two targets fit inside the current viewport; it moves no unit.
- An additive read-only observer records tree HP/density, original unit
  positions/inventory/capacity, exact task identities, harvest object references,
  delivered objects, seeds, and defense/alert changes. It inspects original
  `harvest_items` rather than substituting resource production or collection.
- There are no OS pointer/focus/key events, normal-app input, user-save access,
  physical touch claims, or native gesture claims.

The scenario rejects missing suitable natural targets, unexpected unit input,
blocked work, lost objects, changed task identities, and real-world attacks.
Defense and other world activity remain enabled. A bounded queue check does not
establish that a longer full-world soak is clean.

## Reproduction

[Harness](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tools/check_full_world_orders.py)
and [observer](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/full_world_orders_observer.dm).
Use a fresh label; prior evidence is preserved. Port 12198 is the assigned private
port. The private module adds only targeted diagnostic WebKit dispatch to the
existing opt-in probe:
`/tmp/dm-runtime-audit/full-world-orders-stage/engine/webview-webkit`.

```sh
python3 standalone/remastered/tools/check_full_world_orders.py --label full-world-orders-initial
```

## Verified result

[Full-world report](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/full-world-orders-initial-checks.json): **22/22 pass**, recorded 2026-10-17 06:12:58–06:15:45 UTC.
The 254 state observations show both natural trees harvested in FIFO order while
the worker remains deselected. All eight logs are conserved: seven deposited at
`627,651,1`, one carried. Four seeds remain on the ground. Starting gear stays
carried/equipped, final weight is 105/110, and both other Humans remain idle at
their original positions. Original first-harvest collection finishes before the
second tree takes damage. No attacks, unexpected input, capacity excess,
unrelated collection, client/server/world errors, or private artifact drift were
observed. Both private processes exited.

Natural tree targets were `620,656,1` and `627,665,1`; the camera was positioned
at `624,660,1`. Runtime SHA starts `783f6ad2`, client `9a0a190a`, shared
`9d35743a`, ZIP `7e53b1fe`. The complete digests and original source manifest are
in the report (SHA256
`667b070f04eca01abe9aa4f02b48375f3e1458275994dabd0eb957201494f620`).

The canonical `Turfs.dm` changed during this run when a separately reproduced
Desert/Snow lifetime guard was added. This copied world deliberately retains its
recorded prior `Turfs.dm` hash `a85b5479e7165eda8edd72e504a121b64f3990eb024875cadc05ce11bb48e045`;
the report does not claim to test the new guards or a long-world soak.

After the native run, the analyzer received a small failure-reporting guard:
DM encodes an empty associative list as `[]`, so an interrupted scenario before
the first harvest must treat that as an empty output map rather than throw while
writing its failure report. The accepted native report retains its original
harness digest. A separate retained-evidence analysis check verifies unchanged
22-case results and that empty-output failures are still recorded as failures.

