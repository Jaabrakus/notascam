# Guard prompt and patrol cleanup validation

The scoped candidate changes only Guard in `Code/Creatures/Monster AI.dm` and
adds an optional selection-policy parameter to the shared captured-action
validator in `Code/Remastered/SelectedActions.dm`.

Guard deliberately acts on the units that opened its menu even if selection
changes while the menu is open. This matches the established manual interaction
and workshop policy: a new selection must not receive the old unit's chosen
command. The candidate keeps that behavior. It checks every original actor's
lifetime token, ownership/roster membership, living/profile state, the initiating
controller and the original Guard grant after the main choice and again after
Friendly text input. Deleting another actor in the captured group cancels the
stale command rather than silently shrinking the group.

The shared validator still requires the exact current selection by default;
Rename, speech, emote and royalty behavior retain that stricter policy. Guard
alone requests captured actors without current-selection membership. Token count
and every lifetime check remain mandatory. Native `DE && FreeSelect` selection
continues to be accepted by the capture, then Guard's existing ownership filter
still skips foreign units. Modern Guard entry remains owned-unit only.

Original Guard On handoff pauses automatic work while retaining the active and
pending orders; Guard Off does not resume that queue. Viewing rules, cancelling,
and the original rule/friend edits preserve their established work behavior.
No new guarding, movement, combat, recipe or placement mechanics are introduced.

Clear Rules now remembers both old patrol endpoints before clearing them.
An old HomeLoc is cleared only when it matches a non-null old endpoint.
A matching destination is cleared only when it is still controlled by Guard:
running automatic orders/delivery, a defense response, and an unpaused worker's
recorded production/role destination keep their movement. A paused stored FIFO
is not an active movement controller, so an actual Guard loop still clears its
patrol destination. Unrelated destinations and home locations are retained.

The retained `tests/guard-context-before-checks.json` records 27 passes and 14
failures: dead/transformed/misted or missing captured actors, withdrawn grants,
and old patrol destinations remaining after Clear Rules. Original valid effects,
selection-change completion and native FreeSelect pruning already passed before
the candidate. Real Human and Orc constructors are used; only modal reply
delivery is scripted in an isolated world. Controller-deletion cases also remain
safe; they did not reproduce an additional failure in this Guard path.

The initial candidate passed 41 focused cases, 139 curated-action regressions
and 35 manual-handoff regressions. Review then found the equal-coordinate
execution-ownership edge. `guard-owner-before-checks.json` preserves its ten
failures (Move, delivery, role, production and defense for both Human and Orc)
and two passing actual-Guard cases with retained paused work. The extended final
Guard suite passes **53/53**, including those twelve ownership cases, with zero
errors and stable source/fixture/runtime hashes; see
`guard-final-context-checks.json`. Existing endpoint cases now explicitly start
Guard with a paused FIFO instead of treating an unpaused queue as Guard-owned.
The shared validator is unchanged from the **139/139** curated-action report
`guard-curated-regression-checks.json`. The final manual-handoff rerun passes **35/35** in
`guard-final-manual-checks.json`, also with zero errors and stable hashes. All reports are under `tests/`.
The copied runtime is
`f81a365897c80b9cbb748ba821d6c6a4e3f77760465fee17c18c62fba87d060d`.
Canonical promotion is pending root integration review.
Normal app, profiles, saves and OS input remain untouched.
