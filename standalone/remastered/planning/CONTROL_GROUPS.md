# Numbered unit groups

Updated 2026-10-17 for the active Remastered game. Groups use the original
numbers 1–9. They last for the current session and are not restored from saves.

## Behavior

The HUD offers a row per numbered group, showing its current owned living
members and separate Recall, Set and Add controls.

- **Set** replaces that group with the captured current selection.
- **Add** keeps its existing valid members and adds the captured selection
  without duplicates.
- **Recall** replaces the selection with that group's current valid members.
  It uses the original Select/Deselect methods, including their selection
  markers and restrictions on sleeping, contained and other unavailable units.
- Assigned work, pending tasks, destinations and pause state are unchanged by
  these operations. Recall resets Add tasks, as other selection changes do.

Keyboard controls still use the original Quick verb: number to recall,
Ctrl+number to set, Shift+number to add. Their Alt-prefixed variants also remain.
Recalling the same group again within the original `spawn(3)` repeat window
centers the camera on the first recalled selected unit. This only applies if
that selection still matches the preceding recall. Changing selection between
recalls now causes a fresh recall instead of jumping to an unrelated unit.
The repeat jump does not extend its original window.

For the original keyboard route, recalling an empty group still deselects, and
setting a group with no selected units still clears it. The touch controls may
disable these empty choices and explain why. No new persistence was added.

## Validation and selection cleanup

Both keyboard and touch routes validate an integer group number 1–9 and exactly
Set, Add or Select. Deleted, dead, transferred or no-longer-listed members are
removed before recall or export, so old groups cannot select a former unit or
leak its current name in the HUD.

Touch Set and Add carry an opaque immutable selection token. Every captured
actor token must still resolve to an owned, living, listed and selected unit.
Changed selection, transfer, deletion, membership or death rejects the stale
request. Recall uses the numbered group's current membership, independently of
the old selection token. Requests never contain an arbitrary proc/type name.

Deleted atoms can remain null entries in `Selected`. Selection/HUD boundaries
now remove those entries and invalid members while retaining valid units and
using the original marker-removal method. Explicit Deselect clears all remaining
slots after removing each live unit's marker. The original developer
`DE && FreeSelect` exception remains intact; neither flag alone preserves a
foreign selection, and owned-only group Set/Add still reject it. This fixes a badge reporting two
selected units when only one survives; it does not stop that survivor's work.

## Wire contract

`controlGroups` contains `selection`, `selectedCount`, `setReason`, `addReason`,
and nine `groups` rows with `number`, `count`, `names` and `reason`. Names are
plain data. The browser sends:

```
rm=controlgroup&value=NUMBER|ACTION|SELECTION_TOKEN
```

The group drawer itself is local browser UI. It does not introduce a server
placement mode or replace any original world action.

## Evidence

The original implementation's private before report,
`tests/control-groups-before-checks.json`, reproduced seven failed safety checks:
foreign members being recalled, stale membership retained, three malformed Set
numbers altering repeat state, and a repeat jump using unrelated selection.
Eleven existing-behavior checks passed. Its whole-source stability flag is false
because an unrelated Palette.dm change occurred during the run; original Quick,
ownership, selection and runtime hashes remained stable.

`tests/control-groups-audit-checks.json` verifies the repaired legacy path and
actual HUD requests with real Human constructors. All **42/42** assertions pass
with stable source/runtime/fixture hashes and no errors. It covers all nine groups,
Set/Add/Recall, duplicate prevention, immutable selection tokens, ownership and
deletion races, privacy, exact task preservation, ghost selection counts,
empty legacy behavior, repeat timing and temporary save boundaries.
`tests/qol-checks.json` also passes the existing 20 expected selection, task,
health-bar and alert observations (including its completion marker). Browser
and native integration results are recorded separately with their own hashes. The headless fixture verifies original Star images exist and uses the
original selection methods; it does not claim native highlight rendering or
phone input testing. No normal save/profile or foreground input is used.

The final installed-runtime groups report is
`tests/installed-groups-20261017-checks.json`: **48/48** assertions pass, with
stable source/fixture/runtime hashes and no errors, on runtime
`569d6ae37dd4e29219f37d90a8025be9bf6fffdcc34dc4bfdca9b1d3fdaef42c`.
The six added checks use the original Admin FreeSelect verb and real unit
DblClick to preserve privileged legacy selection without granting foreign
group membership. Its preceding private report
`tests/control-groups-admin-before-checks.json` reproduced the cleanup issue
with stable hashes and no runtime errors. The earlier 42-check report remains
a separate snapshot before this narrowly scoped compatibility exception.
