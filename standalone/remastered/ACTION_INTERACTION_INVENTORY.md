# Actions and interactions — planning inventory

Audit date: October 16, 2026. This document preserves the earlier packaged-game inventory. Implementation has since resumed in **Dungeon Master Remastered**; current progress and checks are tracked in [EASY_ORDERS_PLAN.md](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/EASY_ORDERS_PLAN.md>).

## Baseline and how to use this document

The baseline is the distributed Remastered source in [dist/Dungeon Master Remastered/Source/game](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game>). At the time of this audit, the editable game directory contained unfinished combat, Orders, Settlement and HUD drafts. The rows below retain that baseline; use the Easy Orders plan and its current reports for subsequent implementation evidence. Classic remains the fidelity reference.

The packaged compiled game has SHA-256 c44dd047be99b7a95b6479d429c7cd66e19039ae93bc6f86e9a824623c2b35b4. The source distribution is useful for this inventory, but a reproducible source-to-app match has not been certified for every procedure. In particular, combat source/trace provenance needs reconciling before a new release. No app was rebuilt or launched for this documentation pass.

Use these three levels together:

1. **This document:** action families, behavior that matters to the HUD, decisions and acceptance checklist.
2. [Detailed action catalog](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/ACTION_CATALOG.md>): all 55 Actions-panel rows, keyboard/menu bindings, verb and event declarations, literal menu options, placement modes and prompt sites, with source links.
3. [Building, crafting and item audit](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/BUILDING_CRAFTING_AUDIT.md>): workshop families, recipe gates, cost semantics, item use and destructive side effects.

The [machine-readable catalog](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/action-catalog.json>) records hashes and can be regenerated with [catalog_actions.py](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/catalog_actions.py>). It scans the 49 included DM files, rather than treating every old file on disk as active.

| Indexed evidence | Count | Meaning |
| --- | ---: | --- |
| Included DM source files | 49 | Active include graph; 38,516 source lines |
| Actions-panel commands | 55 | Only the top-level convenience panel |
| Verb declarations | 180 | Includes player, hidden, host and admin verbs |
| Mouse/collision/browser handlers | 229 | Includes inherited/specialized routes; not all are distinct actions |
| Literal menu-option occurrences | 988 | Includes recipes, repeated names, submenus and Cancel |
| Input/alert sites | 280 | Includes generated choices needing manual interpretation |
| Placement-mode assignments | 37 | 31 distinct nonempty mode names |
| Keyboard macros / native menu commands | 104 / 8 | Declared bindings; engine command support still needs checking |

These are **coverage counts, not a completion percentage**. The scanner is an index, not a compiler: dynamic lists, inheritance, runtime permissions and every recipe branch still need interpretation. Do not mark a mechanic working merely because it appears in a menu.

Evidence labels used below:

- **Observed:** a previous native-window test recorded the stated effect.
- **Logic checked:** a focused server/arena check recorded the stated behavior.
- **Source mapped:** the route exists in included source; end-to-end behavior remains open.
- **Known issue:** a recorded error or a specific source discrepancy is identified.
- **Proposed:** a future touch/UI choice, not current behavior.

Unless explicitly stated otherwise, the inventory rows below are **Source mapped**. Earlier evidence and its limits are in [REVIEW.md](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/REVIEW.md>).

## 1. Input routes we must preserve

| Route | What currently goes through it | Planning consequence |
| --- | --- | --- |
| Remastered client Click wrapper | Own-unit selection; one-click HUD buttons; right-click delegation | Selection and commands compete for the same target. |
| Original client Click | Movement/attack targets; containers, wagon, door placement, potion/poison and other special cases | A generic object DblClick adapter would omit existing actions. |
| Object/unit DblClick | Unit race selection; workshop, equipment, food and many item menus | Each class has its own carrying, ownership and range rules. |
| MouseDrag / MouseDrop | Selection rectangle or active terrain placement | Drag cannot mean both camera pan and construction without explicit state. |
| Bump / terrain Enter | Melee, resource work, fishing, terrain/trap effects | Some effects happen on arrival/collision rather than at command time. |
| Verbs / HUD commands | Guard, build, group control, bulk inventory, chat and abilities | Menu loops may act on one unit or all selected units differently. |
| Browser Topic links | Clickable information and administrative editor actions | Link identity and permissions must survive any panel replacement. |
| Timed unit/world procedures | Eating, sleep, movement, guard, aging, weather, decay, autosave | The HUD needs to show automatic state as well as explicit orders. |

Primary references: [Remastered input][qol], [original click routing][click], [placement][building], [collision][bump], [browser handlers][plugin].

## 2. Selection, camera and information

| ID | Action / current route | Behavior and constraints to retain |
| --- | --- | --- |
| SEL-01 | Left-click owned unit | Replaces selection. **Observed** for U1 then U3 in the prior mouse report. |
| SEL-02 | Shift-click owned unit | Adds/removes that unit. **Logic checked**; physical modifier path still needs coverage. |
| SEL-03 | Double-click owned unit | Selects owned units of the same race in view. **Logic checked**. |
| SEL-04 | Drag selection; Shift adds | Owned units inside the rectangle; blocked by active placement mode. Selection result **Observed**; visible rectangle not established by that report. |
| SEL-05 | A / nearby, E / all, Space / clear | Nearby versus world-wide ownership scopes differ; all excludes wagons. Area/all/clear have prior recorded effects. |
| SEL-06 | Groups 1–9; Ctrl set; Shift add | Original Alt variants also exist. Repeated group selection can jump the view. Do not require a keyboard for grouping on mobile. |
| CAM-01 | Arrow/numpad camera movement; Z / Goto | Camera is separate from units. Goto loops selection and finishes at the last unit. |
| CAM-02 | C coordinates; G go to coordinates | Reads/moves the player view, not a normal unit walking order. |
| CAM-03 | Q waypoints | Three stored camera positions with set/goto prompts. |
| CAM-04 | Comma/period or level icons | Changes view between surface, underground, sky and Hell. Camera change alone does not move units. |
| CAM-05 | Backspace / attack jump | Jumps to last attacked owned unit. Alert/jump logic checked; target removal needs coverage. |
| INFO-01 | Units, Unit Stats, Inventory, Unit Information | Health/bleeding/body parts, food, fatigue, cold, weight, skills, equipment, age, race-specific resources and magic attributes. |
| INFO-02 | Player information, Actions, Verbs and log | Preserve ownership, army and social information; distinguish informational entries from commands. |
| INFO-03 | Health bars / attack alerts | Owned-unit bars and throttled nearby-enemy alerts have focused logic checks. |
| INFO-04 | F3 help, updates T, legends K, music O | Help/onboarding, history and music stopping; the old popup guide conflicts with new input instructions. |

References: [input][qol], [groups][quick], [camera/verbs][verbs], [unit panels][stats], [layer controls][login].

## 3. Movement, combat, gathering and guard

| ID | Action / target | Requirements, effects and unresolved behavior |
| --- | --- | --- |
| ORD-01 | Order movement onto terrain | Original Click assigns destinations; Remastered right-click delegates there. **Physical right-click is unverified:** previous report has no destination observations. |
| ORD-02 | Melee attack / hostile collision | Target, ownership, reach, weapon/body state and collision matter. Combat applies injuries, blood loss, death and loot. Packaged deletion/lifetime exceptions are a **Known issue**. |
| ORD-03 | Bow attack | Target, bow, arrows/quiver and cooldown differ from melee and magical targeting. Test moving targets and interrupted firing. |
| ORD-04 | P / Stop | Clears destinations and combat targets; do not assume it deletes guard rules or every active placement mode. |
| ORD-05 | J / Guard On or Off | Starts/stops home-based guard behavior; excludes wagons in relevant branches. |
| ORD-06 | Guard rules | Check, add aggressive rule, clear rules, set friendly owner, clear friendlies. Guard friendlies and player allies are different lists. |
| ORD-07 | Patrol | Sets a placement mode; next location establishes a route with the unit's current position. Turning guard off, clearing rules and Stop need separate checks. |
| RES-01 | Chop tree / wood obstacle | Collision work; axe or race exemptions; damages target, changes terrain and produces resources/skill gains. |
| RES-02 | Mine wall / ore-bearing terrain | Pickaxe or race exemptions; mining skill, drops and terrain changes. An unreachable target needs visible feedback. |
| RES-03 | Fish at suitable water | Collision path has different water/creature/tool cases and probabilistic fish output. |
| RES-04 | Autodig | Unit digging toggle and place/remove dig-marker modes are distinct operations. F5 and old dig macros need route checks. |
| RES-05 | Training posts / structures | Interactions and collision can train or damage things; do not classify every dense object as an enemy. |
| ORD-08 | Run, rest, flight and immobilization | Speed/state and ability-dependent actions; sleep, fainting, stun, holes, missing limbs, mist and flight affect whether orders execute. |

References: [Click][click], [Bump][bump], [melee][combat], [bows][bows], [guard/AI][ai], [digging controls][selection], [self interaction][interact]. A visible order queue and worker priority system are **draft extensions**, not established baseline mechanics.

## 4. Inventory, living targets and world objects

| ID | Interaction family | Existing choices and gates |
| --- | --- | --- |
| ITEM-01 | Bulk pickup | Wood, stone, ores, gems, ingots, food, bones, skin, seeds, armour, arrows. Selection, nearby range, weight and item restrictions; arrows need a quiver. |
| ITEM-02 | Bulk drop | Wood, stone, ores, gems, ingots, food, bones, armour. Drop/equip tests recorded some effects but did not assert every conservation outcome. |
| ITEM-03 | Individual item / equipment | Pick up, inspect, drop, equip/unequip; holder ownership, equipment slots and limbs. Old handlers and generic pickup do not all use the same capacity calculation. |
| ITEM-04 | Quiver / necromancer staff | Drop arrows; Raise Skeleton uses a nearby skull, mana and hunger. |
| ITEM-05 | Food | Eat/inspect/drop; race diet, toxicity/progression and seed byproducts vary. Automatic eating is a separate path. |
| ITEM-06 | Corpses | Carry, inspect, drop, bury with spade, tear meat/skin with appropriate anatomy/tool, Devourer Incorporate Mass. |
| ITEM-07 | Heads, bones, glands | Carry/use/inspect; skull and spike processing, Illithid brain consumption and crafting materials. |
| ITEM-08 | Chests | Carry/drop, inspect and take contents; container/contents capacity and actor choice need explicit handling. |
| ITEM-09 | Drills | Carry/drop, inspect, take contents and drill; resource production changes terrain. |
| ITEM-10 | Wagons | Pull, stop pulling, drop contents; movement links and capacity differ from ordinary inventory. |
| ITEM-11 | Doors/fences/locks | Carry/place, destroy, lock/unlock, keys, lockpick, telekinetic and attack branches. Ownership and lock ID matter. |
| ITEM-12 | Cages and captives | Capture, inspect contents, take captive items, release, tame, enslave; target/race/state and escape conditions. |
| ITEM-13 | Flasks/buckets and creatures | Fill, empty/drink, milking and content-specific use; water, blood, poison and potions are distinct contents. |
| ITEM-14 | Poison and potions | Drink, combine, apply to weapons/traps/arrows, poison sleeping target, transformation and other effects. Some choices consume or kill. |
| ITEM-15 | Seeds/plants | Carry, plant, harvest/interact; farmland, occupancy and growth state gates. |
| ITEM-16 | Scrolls / astral book | Write magic, cast, travel/return, terrain or mind effects; create/destroy portals. Reading failure can destroy a scroll. |
| ITEM-17 | Devourer cocoon / organs | Inspect, initiate incubation, add/remove organ and engineering. |
| ITEM-18 | Ingot / wood / stone transmutation | Convert carried resources with magical gates; replacement and weight changes. |
| ITEM-19 | Rings / gems / ores | Enchant, wear/remove, consume for certain races, healing/progression tradeoffs. A gem is not always just a crafting material. |
| ITEM-20 | Furniture, signs, graves | Place, change facing, write/inscribe, destroy, rob grave; beds and training posts also participate in unit routines. |
| ITEM-21 | Portals / faction pillars | World-context actions with their own conditions and effects. |

The [building/crafting/item audit](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/BUILDING_CRAFTING_AUDIT.md>) gives source references and detailed conditions for each of these object families. Bulk commands do not substitute for their individual menus.

## 5. Building and crafting

| ID | Family | Existing scope and important distinctions |
| --- | --- | --- |
| BUILD-01 | Open/close building | B / Build; selection, race, resources and mist state influence menus. The label “needs stone or wood” does not describe every racial build path. |
| BUILD-02 | Walls | Stone, wood, bone, tribal, elven, secret, silk, devourer; material, race, skill and terrain-specific branches. |
| BUILD-03 | Floors | Stone, wood, bone, tribal, devourer. Inspected branches require material possession or stored bodies without deducting them. |
| BUILD-04 | Bridges | Stone, wood, bone, tribal, silk; water/chasm/lava eligibility differs. |
| BUILD-05 | Stairs / floor removal | Paired layer changes; stairs can move the builder immediately. Removing floor/stairs can remove connected support. |
| BUILD-06 | Workshops / campfire | Create/info/cancel; material, race and existing nearby workshop checks. Many stations consist of two objects. |
| BUILD-07 | Farming | Spade prepares nearby grass as farmland; planting is a separate inventory interaction. |
| BUILD-08 | Digging / traps / channels | Dig marks, pit/sticky traps, bone spikes, ribcage, stone fall, channels and trap upgrades. |
| BUILD-09 | Racial structures/powers | Spider silk/lair/cocoon; Devourer engineering/incubation; Illithid forcefield, pyrokinesis, telekinesis. |
| BUILD-10 | Decorations / arrow slits / tapestry | Placement modes and target upgrades; keep cancellation separate from selecting a unit. |
| CRAFT-01 | Forge | Metal weapons, armour and tools; material and skill/quality branches. |
| CRAFT-02 | Potion station | Potion recipes and transformations; ingredients, race and skill gates. Build label “Meth Lab” refers to this station. |
| CRAFT-03 | Poison station | Poison recipes; ingredients and skill gates; application happens through separate item interactions. |
| CRAFT-04 | Gem cutter | Gem processing and special outputs; race, resource and skill requirements. |
| CRAFT-05 | Smelter | Ore processing, success/failure and batch effects. Consumption differs from a guaranteed conversion. |
| CRAFT-06 | Kitchen / campfire | Food preparation and different actor/range/ingredient paths. |
| CRAFT-07 | Melter | Deletes carried materials/items for experience. It is destructive disposal, not resource recycling. |
| CRAFT-08 | Masonry | Stone furnishings, structures and special recipes; requirements include more than raw stone in some branches. |
| CRAFT-09 | Bonecraft | Bone/chitin equipment, furniture, doors, cages, crowns, posts, arrows and lockpick; race/poison-use gates. |
| CRAFT-10 | Carpentry | Wood gear, tools, furniture, wagon/chest, bucket/spade, arrows, paper and staffs; paper needs water, arrows use quantity/quiver logic. |
| CRAFT-11 | Leatherworks | Corpse skinning, clothing, quiver/flask, sleeping gear and armour, including material-derived properties. |
| CRAFT-12 | Good / evil altars | Pray, Holy Shield, blessed water; sacrifice, Unholy Vigor, blessed blood. Points and unit/stat costs, not ordinary recipes. |
| CRAFT-13 | Destroy workshop | Helpers can remove every same-family station in view(3) of the unit, without an owner filter. Actual affected scope must be shown. |

There are 11 main workshop families, plus campfire and two altars. Each recipe variant remains individually discoverable in the [catalog](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/ACTION_CATALOG.md>); all variants are **not** yet certified. Preserve required possession versus consumption, tools, skill/quality, chance, stat cost, byproducts, output location and batch semantics.

## 6. Unit, race, magic and progression interactions

The I / Interact root loops selected units and offers This Creature, Closest Creature and, where eligible, Magical Skills. This can mean several prompts for a group, and “closest” is not an explicitly tapped target. [Interaction source][interact].

| ID | Family | Existing options / gates |
| --- | --- | --- |
| UNIT-01 | Self management | Run, Dig On/Off, conditional Rest, Pull Out Arrow, Give Creature To and Suicide. Arrow removal can cause blood loss. |
| UNIT-02 | Transfer unit | Recipient acceptance and race/state restrictions; wagons, royalty, infection and other flags can prevent transfer. |
| UNIT-03 | Suicide | Confirmation and ownership-history constraints; keep a deliberate destructive action. |
| UNIT-04 | Nearby creature | Rescue, Breed With, vampire Feed From, werewolf Bite, depending on actor/target. |
| UNIT-05 | Breeding | Nearby compatible male/female pair, age/race restrictions, ownership/other-player acceptance and existing pregnancy. Eggs, cooldowns, offspring and race timing differ. |
| UNIT-06 | Leadership | Declare king/queen, demote/replace and crown interactions; cooldown and role rules. Action label says “needs a crown,” but DeclareLeader can call AddLeader without one. |
| RACE-01 | Orc | Level-gated Berserk and Defensive Fighting. |
| RACE-02 | Gargoyle | Ruby/emerald progression unlocks fire/poison/tree/life abilities; later choices replace earlier ones. Mineral diet is separate. |
| RACE-03 | Vampire | Feed, morph, mist, daywalker progression; level/state restrictions, travel/diet and infection distinctions. |
| RACE-04 | Werewolf | Bite/infection plus automatic transformation/progression; not every race change is a manual button. |
| RACE-05 | Winged units | Fly/retract wings depending on anatomy/race/state; affects movement and item use. |
| RACE-06 | Spider | Queen egg selection, workers/hunters/warriors, silk/web budget and lair progression. |
| RACE-07 | Dragon | Breath by element, dietary progression, flight and female age-gated egg laying. |
| RACE-08 | Devourer | Corpse mass, engineering, organs and incubation across several UI routes. |
| RACE-09 | Illithid | F6 MindFlayer powers, targeting, terrain mental powers and brain consumption. |
| RACE-10 | Sand King | Cocoon and generation choices appear in source; three Generate Sand branches have empty bodies. Offered menu choices must not be called complete abilities. |
| MAGIC-01 | Select magic target | SetTarget assigns MagicTarget to selected units. It is separate from movement destination and bow Target. |
| MAGIC-02 | Meditate / stop | Magical aptitude, state changes and resource progression; communicate why a unit stops moving. |
| MAGIC-03 | Nether travel / return | Concentration gate and travel restrictions; some portal stones interfere with travel. |
| MAGIC-04 | Alteration / willful / destructive magic | Attribute gates, terrain transformations and resource effects; target and area vary by spell. |
| MAGIC-05 | Insanity / damage mind / steal thoughts | Magical Mind/Will/Anger/Concentration gates differ; requires appropriate targeting and per-spell checks. |
| MAGIC-06 | Teleport | Moves toward the player's camera location; the inspected dense-destination branch can kill the unit. This must be explicit in any preview. |

References: [interaction menus][interact], [breeding][breeding], [crowning][crowning], [target assignment][targeting]. Rare/admin-obtainable units are included in the inventory without assuming they are normal starting choices.

## 7. Social, session, host and automatic systems

| ID | Family | Existing scope / HUD implication |
| --- | --- | --- |
| SOCIAL-01 | Rename N, UnitSay U, Emote X | Selection and unit-specific text; multi-selection behavior differs. |
| SOCIAL-02 | WorldSay S, WorldChat L, Who H | Send message, toggle channel, inspect online players. |
| SOCIAL-03 | Private message W / Ignore F | Recipient/message inputs, ignore list, cancellation. Packaged MSG route has a recorded null IgnoreList exception. |
| SOCIAL-04 | Ally add/remove/list | Player diplomacy; distinguish from per-unit guard friendlies and clan membership. |
| SOCIAL-05 | Clans | Create, invite, accept/decline, boot, members, shrines, clan chat and tapestry; leader permissions. |
| SOCIAL-06 | GM/admin help, bug report/view, send file | Support/client flows and permissions; native engine support must be checked before presenting them as mobile features. |
| SESSION-01 | R / race choice and restart | Current restart confirms when units exist, then releases/deletes eligible old units before the race prompt. Cancelling that later prompt is not a rollback. |
| SESSION-02 | Save, load, quit | Periodic unit saving and load reconstruction; explicit save verb is an admin route. Prior smoke test retained three units, not equality of all state. |
| SESSION-03 | Native menu | Options, screenshots, quit, icon stretch/size and text mode are declared; standalone support needs separate validation. |
| HOST-01 | Admin / developer / event controls | Spawn/create/edit/delete, moderation, server restart, events, world settings and save. Catalogued separately from ordinary unit actions. File name alone does not establish permission. |
| AUTO-01 | Hunger / food / fatigue / cold | Automatic consumption, sleep/bed behavior, weather and survival conditions can interrupt work. Surface the real blocking condition. |
| AUTO-02 | Health / injury / death | Regeneration, bleeding, poison, limb loss, fainting, corpse creation and decay. |
| AUTO-03 | Growth / skills / ownership | Experience, maturation, reproduction, transformations, leadership and transferred/captured units. |
| AUTO-04 | AI / guard / world | Wandering, hostile acquisition, patrol, spawns, seasons/day-night and events. |
| AUTO-05 | Persistence side effects | Loading resets several temporary states including selection, sleep, stun, fainting, home location and combat target. Full world construction persistence is not established by the unit-count test. |

References: [verbs][verbs], [clan/target/admin declarations][targeting], [restart][restart], [save/load][saves], [world][world], [health][health], [AI][ai].

## 8. Findings that affect the plan

1. **There is no single existing “interact” contract.** Click, DblClick, Bump, drag modes and modal prompts all implement meaningful behavior. Route by actor + target + state, preserving the actual handler semantics.
2. **A group is not consistently a batch.** Some handlers stop at the first success, first invalid unit or cancellation; others prompt each unit. Record actor selection policy before making one-tap group promises.
3. **Costs and danger are easy to mislabel.** Floors may only require materials; Melter deletes; crafting may spend stats or sacrifice units; workshop destruction has area effects; restart clears units before the race-menu Cancel.
4. **Selection, camera and target are separate concepts.** Movement destination, bow target and magic target must not be conflated. A camera layer change is not a unit travel command.
5. **Partial tests cannot certify a route.** Existing click/drag evidence is useful; right-click has no recorded order result. Actions tests log calls without asserting every effect. Combat and MSG errors remain packaged-baseline issues even if draft fixes exist.
6. **Old labels and unfinished branches need explicit decisions.** Crown/build labels overstate requirements; Sand King generation branches are empty; legacy guide controls conflict with Remastered. Decide preservation versus correction per case.
7. **Recipe and item state must be captured before UI abstraction.** Same-tile versus adjacent pickup, old capacity rules, stale targets during prompts and mixed selection need tests. A new button must not silently choose a different resource or owner.

## 9. Proposed touch behavior — decisions to make next

These are design proposals, **not implemented or verified mobile controls**.

The next focused proposal is [Easy clicks and independent unit work](</Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/planning/EASY_ORDERS_PLAN.md>): select → chop/dig/collect → append targets and resource drop-offs → deselect while the unit keeps working. It includes optional unload-and-resume behavior, categorized stockpiles and Woodcutter/Miner/Hauler roles. It distinguishes existing independent movement/autodig and draft hauling from the unfinished general queue and proposed automation.

| Context | Proposed primary tap | Secondary / ambiguous behavior |
| --- | --- | --- |
| Owned unit | Select it and show condition/current order | Explicit multi-select/group mode and details; do not require double-tap. |
| Clear ground with units selected | Move eligible units and show destination | Camera pan gesture must be resolved independently; active placement/target modes take precedence. |
| Tree / mineable rock / fishing spot | Start the matching work if the selected actor can do it | Show missing tool, race restriction or unreachable reason. |
| Enemy | Attack only in a clear command context with eligible combatants | Keep magic, capture, feed and other interactions available as alternatives. |
| Loose ordinary resource | Pick up using an explicit eligible actor policy | Show quantity, capacity and blocked units; special items open context choices. |
| Door / chest / wagon / cage | Show the most relevant available interaction | Keep lock, contents, captive, pull and destructive alternatives accessible. |
| Workshop | Open recipes for the selected eligible crafter | Costs, required tools, quality, quantity and missing ingredients; destruction separately. |
| Inventory item | Open its real use options | Equipment, food, poison, scroll and racial consumption remain distinct. |
| Building mode | Preview then place; show footprint and resource semantics | Visible cancel; separate painting from camera pan and selection. |
| Ability | Show eligible actor and targeting mode | Range/target preview, cost and explicit dangerous effects. |
| HUD / status | Compact selected-unit strip and contextual actions | Expand skills, injuries, log, diplomacy and rare abilities when needed. |

Recommended first scope: selection → movement → resource work → pickup → build/craft → inspect result, using the existing rules. Queueing, stockpiles, worker priorities and production automation should be separately scoped extensions after this loop is reliable. Mobile platform/export feasibility is a separate task: a touch-friendly Mac HUD alone does not establish iOS or Android support.

## 10. Checklist to follow

### Inventory work

- [x] Establish a distributed-source baseline and distinguish unfinished working changes.
- [x] Index all included files, Actions rows, verb declarations, event handlers, literal choices and input sites.
- [x] Map main player action families, object interactions, races, magic, workshops and automatic systems.
- [x] Record important requirement/cost differences and dangerous or incomplete source paths.
- [x] Separate source findings, prior test evidence and touch proposals.
- [ ] Manually resolve every generated menu and inherited handler in the detailed catalog; mark unreachable/host-only entries with evidence.
- [ ] Record exact ingredients, tool/stat requirements, quantities, skill/quality effects and output for each recipe variant before replacing its menu.

### Baseline playthrough — no category is complete from menu presence alone

- [ ] SEL / CAM / INFO: mouse selection variants, groups, camera/layers, waypoints, unit detail and attack jump.
- [ ] ORD: physical move, melee, ranged attack, stop, guard/friendlies and patrol with observable outcomes.
- [ ] RES: chop, mine, fish and autodig with/without tools, nearby/blocked targets and multiple units.
- [ ] ITEM: every object family above, including same-tile pickup, full inventory, containers and all offered secondary actions.
- [ ] BUILD: each material/race family, each layer, legal/illegal placement, cancellation and removal of linked structures.
- [ ] CRAFT: every station plus campfire/altars; verify output, costs, quality, failures, batching and destruction scope.
- [ ] UNIT / RACE / MAGIC: allowed/blocked states, explicit target selection, costs, cooldowns, progression and interrupted actions.
- [ ] SOCIAL / HOST: permissions, recipient acceptance/decline, cancellation, disconnected players and separate admin access.
- [ ] SESSION / AUTO: restart cancellation, save/load field comparisons, construction persistence, survival routines and a sustained play session without runtime exceptions.

### Mobile plan, after behavior is understood

- [ ] Define each action record: ID, actor policy, target type, entry route, range/layer, ownership, gates, required/consumed resources, effects, failure reason and cancel behavior.
- [ ] Decide tap, pan, multi-select, placement and targeting precedence; keep every existing action reachable without a keyboard/right-click/double-click.
- [ ] Define one primary action per unambiguous context and a readable alternative-actions sheet for the rest.
- [ ] Decide how far-away work is approached and resumed; distinguish this new automation from current behavior.
- [ ] Resolve which source quirks to preserve and which to intentionally fix; record each rule change separately from presentation changes.
- [ ] Design selected-unit status, action availability, target/placement previews and concise result feedback using actual state.
- [ ] Validate small landscape/portrait layouts, text/input size, occlusion, scrolling and camera behavior on the intended device.
- [ ] Confirm the standalone runtime/export route for the intended mobile platforms.

### Acceptance rule for checking off an action

For each action ID, record: **build hash → actor and target → physical input → expected effect → observed effect → evidence path → pass/fail**. Include success, missing requirement, cancellation, out-of-range/blocked target, mixed selection and ownership changes where applicable. Check conservation and side effects for consumptive actions; check save/load for persistent effects. If the actor or target dies while a prompt is open, the interaction must end predictably without an exception.

A checked source-inventory item means it was mapped. A checked gameplay item means its outcome was actually verified. This distinction is the basis for honest progress tracking from here.

[qol]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Remastered/QoL.dm:1>
[click]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Click.dm:1>
[building]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Building/Building.dm:160>
[bump]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Creatures/Bump.dm:1>
[plugin]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/plugin.dm:1>
[quick]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/1 - QuickProcs.dm:38>
[verbs]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Verbs.dm:253>
[stats]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/1 - Stat Proc.dm:1>
[login]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Login.dm:283>
[combat]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Creatures/Combats.dm:1>
[bows]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Creatures/Combat - Bows.dm:1>
[ai]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Creatures/Monster AI.dm:20>
[selection]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Selection.dm:36>
[interact]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Creatures/Interact.dm:1>
[breeding]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Creatures/Breeding.dm:17>
[crowning]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Items/Crowning.dm:24>
[targeting]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Admin.dm:1161>
[restart]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Restart.dm:21>
[saves]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Saves.dm:1>
[world]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/World.dm:1>
[health]: </Users/kiwimango/Downloads/Dungeon-Master-master/standalone/remastered/dist/Dungeon Master Remastered/Source/game/Code/Creatures/Health.dm:1>
