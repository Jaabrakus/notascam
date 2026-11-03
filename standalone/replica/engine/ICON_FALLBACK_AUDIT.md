# Missing-state constructor and corpse composite audit

The missing-state constructor difference is reproduced, but the audited live
equipment/hair paths do not justify a broad fallback change. A separate
uninitialized-pixel defect was observed in generated corpse directions and is
the better narrow follow-up. The initial audit changed no production files.
The buffer fix described below was subsequently installed; see the
[buffer installation manifest](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-buffer-install.json)
for its exact promotion time, backup, and hashes. The missing-state and other
composite limitations remain separate.

The [retained runner](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/audit_icon_fallback.py)
runs copied, real Remastered constructors and `MakeBody` in BYOND 516.1655 and
the reviewed rewind runtime `569d6ae37dd4e29219f37d90a8025be9bf6fffdcc34dc4bfdca9b1d3fdaef42c`.
The two private worlds replace startup, remove map includes, and rename the
unused old `StopAll` definition identically because BYOND rejects the duplicate
verb accepted by the replacement compiler. No icon/compositing routine is
changed. Inputs normalize genuine constructor skin/hair branches to keep the
two engines' random choices comparable. There is no client, input, normal save,
new artwork, or installed-engine mutation.

## Reachable selectors and reference results

- The 183 instantiated equipment types produce the same inventory in both
  engines. All concrete text selectors exist. `LeatherQuiver` intentionally
  has a null selector, meaning a whole-resource constructor. The abstract
  `DemonicWeapons` parent also has a null selector; it is not a missing text
  selector. Hair/beard choices in included `Mobs.dm` name existing states.
- Human, Elf and Dwarf bodies retain `icon_state="Normal"`, absent from
  `Human.dmi`/`HumanBlack.dmi`. Their renderer correctly falls back to the empty
  state. The distinct constructor call in
  [MakeBody](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Creatures/Death.dm:89)
  returns all 17 states in BYOND, but one empty-state selection in the
  replacement. BYOND also retains all 17 states when direction/frame/movement
  selectors are supplied with that missing name. The replacement applies
  those filters to its empty-state fallback instead.
- Female corpse construction requests `"Hair"` or `"BlackHair"` from
  [Female.dmi](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/game/Code/Creatures/Icons/Female.dmi),
  which contains only Shirt/Unders. BYOND returns both states; the replacement
  produces no states. These calls belong to corpse construction; live hair uses
  the valid states in the separate `Hair.dmi` resource.
- Seven actual corpse variants were exported: Human male/female, Black Human
  female, Elf female, Dwarf male, Orc male/female. Every default SOUTH frame-0
  cell matches BYOND exactly. All bodies are created SOUTH. Included corpse
  pickup/drop code changes location, not facing; no normal route to their
  other directions was established. Therefore this audit does **not** claim
  that the missing-state difference currently changes their default display.

The [first run](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-fallback-real-game.json)
and [identical repeat](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-fallback-real-game-repeat.json)
preserve source hashes, unchanged original artwork hashes, fixtures, generated
resources and both engine logs. Both completed without runtime errors.
The earlier `initial/` directory retains the failed compile attempt; its missing
JSON resource and duplicate verb were corrected only in the private fixture.

## Separate composite defects

The [repeat comparison](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-fallback-repeat-comparison.json)
separates three issues from missing-state selection:

1. Human male corpse NORTH/EAST/WEST contain 80/90/97 extra visible pixels on
   the first replacement run. Every intended opaque pixel is otherwise correct.
   Those extra pixels change on the identical repeat; BYOND is stable. The
   runtime's `GenerateDMI` rents `ArrayPool<Rgba32>` storage without clearing it,
   then leaves newly added blank directions unwritten before alpha blending.
   Clearing the used buffer span immediately after renting is the proposed
   narrow fix. It requires no parser/client change or original art rewrite.
2. BYOND expands the original one-frame blank destination to three frames when
   blending an animated body; the replacement preserves only one. The runtime
   already marks frame expansion TODO. This is separate from the constructor
   fallback and should not be silently bundled with the buffer fix.
3. Female NORTH/EAST/WEST have stable differences in intended body pixels,
   consistent with the source's single-SOUTH underwear blend not extending to
   other destination directions. Their SOUTH frame is exact. Direction fallback
   during Blend needs its own reference test before any implementation change.

The proposed buffer verification is to rerun this unchanged real-game fixture
against a private candidate and require stable, exact Human male frame-0 cells
in all four directions. Also verify empty generated icons remain transparent,
existing generated equipment/direction tests still pass, and original sprites
remain unchanged. Continue to report frame expansion and other Blend behavior
as known limits rather than declaring full icon parity.

## Private buffer candidate

The one-statement buffer initialization was subsequently approved for private
staging. Comparing the entire generated runtime source tree against the reviewed
rewind build confirms that `Array.Clear(pixels, 0, span * frameHeight)` is its
only source change. This describes the historical private staging step;
the lead subsequently promoted the reviewed builder and runtime, recorded in
the [installation manifest](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-buffer-install.json).

[The focused retained check](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/check_icon_buffer.py)
passes **120/120** on the candidate; the previous runtime fails nine checks for
the three affected Human male directions. Two separate real-game runs now have
stable pixels, preserve every intended opaque pixel, and contain no unexpected
visible pixels. All four Human male directions match BYOND exactly. Sixteen
new empty-icon exports are transparent. The existing generated-icon **11**,
idle/walking-variant **81**, and rewind **22** checks also pass. Original art is
unchanged; no client or normal profile was opened.

The [staging manifest](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/icon-buffer-staging.json)
contains the precise builder diff, runtime/source paths, SHA-256 values and
verification reports for lead review. Candidate runtime SHA-256 is
`783f6ad20cb1f578d57429d2c015587187f6ac59e88e6c8bce609858fff5b6f4`.
This does not change the three deferred icon semantics above or assert complete
sprite parity.
