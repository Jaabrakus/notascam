# Movement-only sprite playback

The shared engine previously discarded DMI `movement = 1`. Its client then
advanced Human, Orc, hair, and equipment walking frames using elapsed time even
when an actor had not moved. This is separate from the earlier generated-DMI
direction/frame layout correction.

The retained patch preserves this metadata while parsing, exporting, copying,
and generating icons. A stationary movement-only state displays frame zero;
actual client transform glides enable its existing animation clock. Glide
completion, long-distance teleport, and parent/container changes clear that
state. Overlays and underlays inherit it immediately, including when equipment
is rebuilt mid-glide. Ordinary water/fire animations and explicit `flick()`
playback retain their existing paths. Original artwork is unchanged.

Implementation:

- [PatchMovement.cs](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/engine/PatchMovement.cs): shared parser/export metadata and client playback/glide hooks.
- [PatchDmiVariants.cs](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/engine/PatchDmiVariants.cs): preserves ordered same-name idle/walking entries, separates their rendered texture caches, and selects the variant from actual movement. Public state names stay unique. Normal states are preferred while idle; movement-only assets retain the first-frame fallback.
- [PatchClient.cs](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/engine/PatchClient.cs): applies movement support alongside all existing prompt, verb, layout, and sound fixes.
- [build_client_compat.py](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/build_client_compat.py): `--stage-only` builds without replacing installed DLLs; normal install replaces both client/shared package assemblies and server shared assembly.
- [build_compat_runtime.py](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/build_compat_runtime.py): `--shared-assembly` accepts the staged compatible shared DLL when building generated-icon metadata support. `--output` keeps an isolated build outside the retained engine directory; `--install` writes only to the explicitly selected `--server`. Install matching shared/client and runtime artifacts together.

Verification:

- [check_movement_animation.py](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/check_movement_animation.py) executes the actual client frame selector with a controlled clock. It checks idle → moving → idle, all cardinal/diagonal facings, generated icons, child layers, completed-animation reset, default-state fallback, and ordinary animated scenery. It uses the packaged x64 runtime because the published Robust client assembly is x64.
- [check_generated_icons.py](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/check_generated_icons.py) compiles and runs real headless DM `icon()`/`fcopy()` fixtures, then compares frame/direction pixels and movement flags independently.
- [save audit](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/movement-animation-save-audit.json): read-only check found fifteen saved file resources matching original bytes and no generated `IconData`; no save migration was needed. Original `LoadUnits` rebuilds equipment overlays after restart.

Same-name variants are covered by the staged October 17 patch. The original
Deer (`Icons/Animal.dmi`) and Hell Forged Sword
(`Code/Items/Icons/DemonicItems.dmi`, `Sword`) both declare walking artwork before
separate idle artwork. The parser retains both in source order and the renderer
switches between them. The sword's normal state is itself animated: idle stops
walking artwork, while its ordinary idle animation continues.

[check_dmi_variants.py](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/tools/check_dmi_variants.py)
checks the real parser, rendered texture cache, frame selector, original atlas
pixels, generated icon metadata, and all cardinal/diagonal facings. Its isolated
BYOND 516.1655 reference fixture independently establishes constructor and
Insert behavior. `icon(source,state,moving=null)` keeps both variants;
`moving=0/1` selects idle/walking pixels and produces an ordinary output state.
`Insert(source,state,moving=...)` selects the first source entry and assigns the
destination name and movement flag. Copies and neutral color multiplies retain
both variants. References: [icon constructor](https://www.byond.com/docs/ref/info.html#/icon/New),
[Insert](https://www.byond.com/docs/ref/info.html#/icon/proc/Insert),
[icon_states](https://www.byond.com/docs/ref/info.html#/proc/icon_states).

[The native variant probe](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tools/check_dmi_variants_native.py)
constructs original Deer and Human units, equips a real Hell Forged Sword on a
qualified Human, then scripts east and northwest movement without client input.
It observes actual glide membership, body and overlay frames, facing, cached
texture rectangles, and exported resource bytes. Those visible pixels and
alpha are compared with original sprite cells; a real mid-glide unequip/equip
checks a newly created overlay. The generated sword's ordinary idle animation
and Fire control keep animating. [Final native evidence](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/tests/dmi-variants-native-checks.json)
passes 40 checks with no input, private saves, or world/server/client errors.

[The staged manifest](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/dmi-variants-staging.json)
records matching runtime/shared/client/package/module hashes and the restore
point. The full 81-check isolated variant suite has 44 failures on the previous
engine and none on the staged engine. Existing movement-selector checks (36)
and generated-icon layout checks (11) also pass. All 164 original sprite source
hashes remain unchanged.

The [follow-up audit](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/reports/dmi-edge-audit.json)
confirms same-name/same-movement first-wins lookup matches BYOND across all six
original duplicate groups (20 extra occurrences); raw metadata still preserves
all occurrences. The [rewind proposal](/Users/kiwimango/Downloads/Dungeon-Master-master/standalone/replica/engine/DMI_REWIND_PLAN.md)
records the remaining real tapestry animation gap and its reference gates.

Known limits: full loop
counts, rewind timing, Insert direction/frame/delay options, and GetPixel's
movement argument are not expanded by this patch. The existing constructor fallback
for a missing state also differs from BYOND (which returns the full resource);
HUD consumers should resolve an absent state to the empty state explicitly.
Movement-only extraction with moving=0 is blank in BYOND and in the staged runtime. No complete DMI parity is
claimed. Staged artifacts passed the native probe and read-only review; the lead
owns their coordinated installation. A successful private build does not mean
the packaged app has changed.

Two upstream renderer paths remain outside these checks: a completed `flick()`
can pair effect artwork with the actor's current frame index, and `vis_contents`
with inherited icon flags uses the ordinary state cache even when its frame
selector uses a walking variant. The included game does not use the latter;
its paired Deer/Sword variants do not invoke flick effects. These paths need
targeted tests before claiming broader engine compatibility.
