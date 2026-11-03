# polish-words (polish night, 10-26)

Every word a player reads, swept for typos, wrong names, old names, dev-speak and broken plurals. The game now says
"1 unit", not "1 units"; unit cards speak plainly ("Asleep; carries on after waking", not "Sleeping; tasks retained");
the capture tip no longer promises a captive "joins your house after a minute"; about 150 of the 2006 game's typos
("posion", "it can ued to", "I Cant Carry Too Much!") are spelled right; and four blow-by-blow / waking chat lines the
owner's rule drops are gone. Speed: no measurable change (measured, see Numbers).

## Done

Status: all landed (game/Code 21:54, in build 64; HUD page 23:58; docs 00:00). See Landed.

- **Plurals and wrong names (words-remastered-a, 28 edits).** "Group 3: 1 units", "Tilled 1 tiles", "Took 1
  arrows", "Pressed 1 cups of wine", "1 more minutes", "1 tiles to dig" now read right; "Group 2 ungrouped: its 4 back"
  gained its missing word. A failed Vampirism Cure said "<your account name> didn't work!", and a fatal Potion of
  Vampirism said "<your account name> has died!!": they now name the cure and the unit. "no affect" -> "no effect".
  "Realm page" / "Village page" -> "Realm tab" / "Village tab" (what the HUD calls them). Build-tab tips no longer say
  "the original pit/cocoon/queen's lair" (the 2006 code talking). Auto Dig's "On!" / "off!" made one style.
- **Unit-card and order lines in plain words (words-status-voice, 28 edits).** "tasks retained", "current task
  retained", "Carry capacity reached", "Item cannot be picked up here", "Cannot free enough space with the stockpile's
  accepted cargo", "No eligible cargo or selected worker", "inside another object", "Unable to consume the carried
  wood", "Crafting failed; 1 wood consumed" -> the game's own voice, same meaning.
- **The 2006 game's typos (words-original-typos 56 edits, -2 7 edits + 85 repeated lines, -3 7 edits).** posion ->
  poison (item descriptions, "was poisoned!", workshop help), "it can ued to store items" (all chests), peice,
  supprisingly, furtniture, absorbtion, cacoon/caccoon, existance, dissappearing, commited, outstreched, "gruesomly bloody mess!! !!!", layed, expells, "tryed to eat fungas", targetting, dispicable,
  craftmanship (five demon armours), "Sacrifical Blade", "Frogman Cheiftain", "I Cant Carry Too Much!" (79 places: every
  full bag), "Cant plant too many seeds" (6), "a Adamantium ingot", "a Emerald Ring", it's -> its (5), "This is limb",
  "failed working working". The wording, Title Case and lore stay; spelling only.
- **Cocoon names (words-cocoon-names).** A Devourer's placed trap was called "Cacoon Trap" (the Build tab says Cocoon
  trap); the sand king's item "Dormant Cacoon".
- **Chat rule (words-chat-blows).** "X is hit by Y's arrow!", "X is hit by Y's javelin!" and "X's armour deflects the
  arrow!" were still sent on every shot, though the owner's rule drops blow-by-blow (the misses and part hits of the
  same shots were already dropped), and "X comes to." when a knocked-out unit woke (waking lines are dropped). Three
  patterns added to the chat filter; eye/heart/lung hits, limbs lost and deaths stay.
- **The worst bleeding (words-bleed-word).** The unit sheet said "Bleeding: Extremly" and the Doctor "(bleeding
  extremly)", the 2006 value's misspelling; now "Extremely" (the Health tab already did this).
- **From other agents' notes (words-remastered-d).** "No ramp or stairs nearby lead up there" said to a unit sent down;
  "Traitor! goblin tracks"; the Log's "Sold Log for 2" (now "for 2 coins", like the market); "Raid! 1 Kobolds are
  coming" (now "A lone Kobold is coming").
- **Chat filter list repaired (words-chat-sites-refresh).** make_chat's check had been failing since 10-25 (send-site
  line numbers moved), so nobody could gate chat text on it. Re-derived at land time; nothing a player sees changes.
- **HUD words (words-hud-a, 10 edits; words-hud-b, 11 edits).** The Capture tip now says rope, then win over or enslave; "(Formations.dm)" removed
  from a tooltip; "Interact -> Breed With" -> "Have a child"; "the original Interact menu/command/choices",
  "inventories", "Recipes consume materials" reworded; a "Realm page" button -> "Realm tab"; "unit frame"/"hero frame"
  -> "unit card"; menu paths "A -> B" -> "A › B" like the rest of the HUD.
- **Player docs (words-docs).** JOIN_IN_BROWSER.md was titled "Kin & Stone", told friends to press R for a race and
  said right-drag turns the camera (it moves it; middle-drag turns). README.md's title said Dungeon Master Remastered and
  it still said a captive joins after a minute. Host on the Web.command's window said Kin & Stone.

Most visible lines, before -> after:

| Where | Before | After |
|---|---|---|
| Capture tip (right-click) | ...then take them: led on a rope, they join your house after a minute. | ...then tie them with a rope: they never join on their own, so win them over or enslave them. |
| Control groups | Group 3: 1 units. Groups last for this session. | Group 3: 1 unit. Groups last for this session. |
| Truce | You swore a truce with X: 1 more minutes. | ...: 1 more minute. |
| Unit card | Sleeping; tasks retained | Asleep; carries on after waking |
| Unit card | Carry capacity reached | Bag too full to carry it |
| Delivery | No eligible cargo or selected worker on this level. | None of the selected on this level carries anything the stockpile takes. |
| Potion of Vampirism | (your account name) has died!! | Aldric has died!! |
| Full bag (79 places) | Aldric : I Cant Carry Too Much! | Aldric : I Can't Carry Too Much! |
| Item | This is a posion root, it can be used to add posion to weapons... | This is a poison root, it can be used to add poison to weapons... |
| Chest | This is a gold chest, it can ued to store items in. | ...it can be used to store items in. |
| Build tip | Spiders; the original pit, covered with web... | Spiders; a pit covered with web... |
| Chat in a bow fight | Goblin is hit by Aldric's arrow! (every hit) | (dropped, like the misses) |
| Browser guide | First time in, press R and pick a race. | First time in, a card asks which people you will lead: pick one. |

## Numbers

| Check (clone of game/, then the land gate on game/) | Result |
|---|---|
| Compile, all words fixes on a fresh clone | 294 warnings, same as today's game/ |
| make_chat check on game/ before tonight | FAIL (21 patterns drifted) |
| make_chat check on the clone after | PASS |
| Chat filter test (tests/chat_filter_check.dm, arena), 1,963 send texts | 213 -> 217 dropped, 0 differ between DM and the generator |
| Arena probe (words_probe.dm): bleed word, pickup reason, plurals, chat drops/keeps, raid of one | today's game/: 7 of 15 fail; with the fixes: 15/15 (the two raid rows test the new wording itself) |
| HUD page scripts (check_scripts) / headless Chrome console | 10/10 ok / 0 script errors |
| Chat filter cost per line, 34 -> 37 patterns (arena, A/B alternated in one run, 2 runs) | 19.35 -> 21.37 us and 20.65 -> 20.24 us: within noise; the dropped lines aren't sent at all |
| HUD update time, today's page vs the words page (headless Chrome, 240 updates each, alternated) | median 0.20 -> 0.20 ms, mean 0.25 -> 0.25 ms: no change |
| Everything else (string literals in unchanged code paths) | no new work per tick: no measurable change |

## Landed

- **21:54 words-batch-dm**: every game/Code word fix (gate: compile, jscheck 10/10, hudjoin, make_chat, combat 32/32;
  restore point restore-points/before-polish-words-batch-dm-20261026-215235). In build 64.
- **23:58 words-batch-hud**: the HUD page words, re-proven on today's art/hud/src after hud-rework landed (gate: compile,
  jscheck 10/10, hudjoin, combat 32/32; restore point before-polish-words-batch-hud-20261026-235714). Not built yet.
- **00:00 words-batch-docs**: README.md, JOIN_IN_BROWSER.md, Host on the Web.command (gate hudjoin, make_chat; restore
  point before-polish-words-batch-docs-20261026-235823). Not in the game.
- Each batch's README lists its parts; each part's folder (reports/polish-night-1026/words/<part>/) has what the player
  saw, what changed and its proof.

## Needs the owner

- **Old name on the browser lobby.** Friends joining in a browser still see "Kin & Stone" / "The Deepholds" on the
  lobby page and "Kin & Stone" on the "Joining the world" page. That text is in tools/web_host.py and the web relay,
  which polish may not touch. Exact fix staged: reports/polish-night-1026/words/staged-web-name/ (the relay part needs
  a relay rebuild). The launcher's fallback title also says "KIN & STONE", but only if its art file is missing.
- **Item descriptions with dev words.** 18 silver weapons say "(the game's Silver flag)" and 8 helmets "The original
  Metal Helmet's shape." These come from the gear catalogue (art/enhance/catalogue.json, exported into GearData.dm,
  "do not edit"), so they need the catalogue changed and re-exported by whoever owns the gear export.
- **Two names for one board.** Lines say "bulletin board", "the Board", "Board worker" and "job board" for what the
  supply chain now shows as Work › Supply chain (Make rows are the Bulletin board's orders). Which name should players
  read? Then one pass makes them match.
- **House names have two rules.** Renaming in Village › Lineage takes 1 to 32 characters; naming in the Realm tab takes
  2 to 24 letters (Lineage.dm vs Realms.dm). A number, so not changed.
- **Workshop names in sentences** are capitalised both ways ("a carpentry" / "a Carpentry", "the Forge" / "a forge")
  across dozens of lines. A house style (capitalised, as the Place-a-workshop list shows them?) would let one pass fix
  them all.
- **Tend words** ("Tend living: off in Work fells them", the Work tab's Tend switch, unit-card tend lines) are left for
  the session removing Tend (hud-controls' staged living-off).
- **Blocked path to stockpile; retrying shortly** and **Worker cannot walk** kept as they are: tests/settlement_test.dm
  matches them.
- **Two settings called "Stance".** The Orders page's Hold / Guard / Aggressive and the unit card / band card / roster's
  Help nearby / Defend self / No response (which the Work panel calls "Automatic defense"). One name for the second
  (start's suggestion: "Automatic defense") would end the clash; a naming call, so not changed.
- **Fever chat.** "X coughs." goes to everyone in view several times a minute per sick unit (beside a *cough* bubble).
  It reads like the dropped hungry/tired chatter but isn't on the owner's list, so it stays until you say.
- **Gear names spelt "Armor"** in some 2006 workshop menus ("Full Metal Armor") while the game says armour; the menu
  label is also the code's key (StationCosts, CraftingStations), so it needs a matched rename.
