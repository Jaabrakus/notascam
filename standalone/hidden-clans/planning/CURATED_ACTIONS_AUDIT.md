# Curated action and prompt audit

2026-10-17. The reviewed actor/grant fix is integrated into Remastered.
Reproductions and native acceptance use private worlds; no normal profile, save
or OS input was touched.

## Demonstrated prompt races

`tests/curated-actions-before-checks.json` records ten normal-effect/work checks
passing and ten stale-action checks failing. Source, fixture and installed
runtime hashes stayed stable and no errors occurred. Runtime SHA-256:
`569d6ae37dd4e29219f37d90a8025be9bf6fffdcc34dc4bfdca9b1d3fdaef42c`.

| Command | Actual stale effect |
| --- | --- |
| Rename | The captured unit is renamed after the player selects another unit or the captured unit transfers to another owner. |
| Unit speech | The text prompt returns, then the original UnitSay verb reads the new selection and speaks through the replacement unit. |
| Unit emote | The text prompt returns, then the original Emote verb reads the new selection and emotes through the replacement unit. |
| Declare leader | Confirmation can promote the old or transferred unit, changing royalty and Strength after the context changed. |
| Remove leader | Confirmation can demote the old or transferred unit, changing royalty and Strength after the context changed. |

The test creates real Human units and invokes the actual HUD action dispatcher.
Only text input and leader confirmation calls are replaced in its private copy.
The replacements yield, change real selection/ownership, then return text/Yes.
Original names, logs, royalty/stat effects and command bodies execute unchanged.
This is not a native prompt pointer-input test.

## Delivered validation

The implementation captures immutable unit-token strings and the exact actor set before a prompt.
After every yield, reject changed selection, actor lifetime, ownership, unit-list
membership, living/profile state or required verb availability. Deleted atoms
must not be skipped through typed list iteration. Cancel/stale paths must not
pause work or change other unit fields.

For UnitSay and Emote, validate the captured context before calling the original
text verbs. Keep their existing escaping, logs and mute behavior. Rename and
leader prompts need shared validation at their actual commit points so native
routes receive the same protection. Preserve name limits/prefixes, original
royalty stat changes, existing king/queen checks and cooldowns.

AddLeader is also reached by manually equipping a crown in Item Procs.dm. That
route must validate the same crown lifetime, direct carrier and applicable item
state after confirmation before royalty/equipment commits; a renamed-only HUD
wrapper would leave this original route exposed. Do not broaden or remove the
existing developer FreeSelect privilege while securing ordinary commands.

Guard already captures its actor list and rechecks ownership after its choice
prompt. It was not changed or included in these five demonstrated effect cases.

## Discoverability

The pre-change “All controls” drawer searched only `border.controls`: 44 runnable original
border commands and one day/night indicator. Seventeen existing ordinary Actions
entries were absent from that search: Guard, Rename, UnitSay, Emote, leader,
mental abilities, magic target, Deselect, attack-alert jump, world/clan chat,
Add/Remove/List allies, Legends, Music off and Help. They remain available in
other HUD sections or All commands, but the earlier drawer's claim of all commands was
incomplete. The curated merge described below is now installed and packaged. Numbered groups have their own local drawer.

The minimal UI adaptation is a curated merge of these existing Actions entries
into the same purpose categories, with original labels/descriptions, shortcuts
and current disabled reasons. Keep the existing action IDs and `action` request
route for these entries; do not send them as borderaction or synthesize icons.
The groups row can open its existing local drawer. Preserve stable row identity,
search/focus state and the original 44 border routes.

Availability must be checked server-side again at execution. Relevant inherited
verbs include Guard, Rename, UnitSay, Emote, DeclareLeader, MindFlayer and the
listed social utilities; the original LockDown path can remove verbs. Magic
Target already checks the Targeting verb. Help/Deselect remain local conveniences.
No GM, developer, file-transfer or other privileged command should be promoted
by enumerating all runtime verbs indiscriminately.

## Availability and grant enforcement

The pure availability function reports the same reason in exported
command data and at dispatch. Rename, speech, emote, leader and Guard require an
owned, living, fully valid selection. Mental abilities and Magic Target retain
their additional original eligibility rules. All fifteen curated routes backed
by verbs verify those original grants, including social commands and the attack
alert jump. No privileged verb is added or enumerated into the HUD. Clan chat
also reports its original no-clan condition before opening a prompt. Deselect
and Help remain available conveniences.

The native Rename and DeclareLeader wrappers retain the original explicit
`DE && FreeSelect` privilege. Modern touch actions remain owned-unit only.
Captured actions check every actor token and profile again after each prompt;
valid multi-unit rename updates its own snapshot between original rename
commits. Manual crown equipment also checks the same crown inventory, carrier,
item lifetime, wearing state and equipment state after confirmation. An already
royal unit still equips a crown without requiring a selection or another prompt;
the original NPC royal constructor is unchanged. The crown wrappers also remember
whether a Player initiated the confirmation; deleting that controller cancels
the commit. The retained `curated-controller-before-checks.json` reproduced a
stale demotion plus deleted-controller runtime errors before this final guard.

Candidate validation uses real Human constructors and original effect bodies.
It substitutes only text/confirmation replies, allowing controlled changes
during their actual yields. Work-state assertions observe the immediate return
from the real action, before ordinary movement advances on later world ticks.
This covers active/pending identities, destination, queue pause, role and role
pause. The private candidate passes **139/139 checks**, with no errors and stable
source, fixture and runtime hashes (`tests/curated-actions-final-checks.json`).
Root integrated the six reviewed source files with a hash-checked backup.

A separate diagnostic exposed an engine/compiler compatibility gap:
`typesof(/Targeting/verb/)` returned an empty list under installed runtime
`783f6ad20cb1f578d57429d2c015587187f6ac59e88e6c8bce609858fff5b6f4`.
The availability fixture explicitly grants the original SetTarget verb before
testing its withdrawal, matching the existing Magic Target fixture. This is a
headless fixture prerequisite, not proof of a normal player's Login grant. The
retained `curated-actions-availability-explicit-grant-checks.json` records that
separate observation; the engine/login path requires independent verification.

## Native Controls acceptance

`tests/curated-controls-native-compact-receipt-checks.json` passes **44/44**
checks with zero server/client/world errors. The actual native WebKit DOM has
all 44 classic commands, its status indicator and 17 curated commands, without
duplicate rows. Curated availability matches the live server model for owned,
empty and withdrawn-grant states.

Existing DOM buttons sent exactly one real Topic per action. Genuine native
Rename, speech, emote and leader prompts were cancelled or accepted through the
isolated client's internal UI callbacks. Only the original selected Human was
renamed/spoke/emoted/promoted; another real Human remained unchanged. Every
outcome retained exact active and pending tasks, paused state and role settings.
The fixture uses isolated Login setup; normal Login and the Magic grant are
separate acceptance cases. Text was assigned through the native LineEdit setter;
these checks do not claim physical typing or mobile application support.

The diagnostic-only HTML bridge is inserted before the existing ready send and
reports compact DOM observations to stay within the Topic text limit. It leaves
the production model, event handler and `send()` unchanged. Installed client
`5481500f48d338c1525c1bca98d821d5f7d42178544385f4fd6c7189c06d160a`
and private probe module
`26883e4fe652fa6119a5039bc6d390f73f001e6b5396df090521e05873521fb8`
were used; all recorded source/runtime/module hashes remained stable. Both
private processes stopped and no save or OS input event was created.


## Current packaged status

The fourth verified app includes the curated Controls merge and actor validation. Original Login dynamic verb groups were subsequently corrected in the shared runtime, with52 focused enumeration checks and15 native Login checks proving the actual ordinary player's SetTarget grant without an explicit-grant workaround. Global/proc enumeration remains a separate engine limit. The historical explicit-grant fixtures above remain labeled as such.
