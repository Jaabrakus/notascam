# Guards that hold while you're away (quest maker Q4), 10-31

Your guards now keep guarding after you log off, for every player. When someone's units or camera are near, they
fight off whatever comes at them and then go back to their posts. Patrols keep walking. Each guard's post is saved
with the unit, so it's still there after a restart. Where nobody is near, nothing fights.

## Done

- **Guards stay on post when you log off.** Set units to Guard or Aggressive and log off: each keeps guarding the
  tile it was put on. Before, the guard itself went on, but anything that hit it started a "defence" that only the
  online part of the game moved forward. So the first blow froze the guard for good and it never fought back.
- **A fight that starts while you're away now ends.** A world loop moves those defences forward (and attacks and
  patrols) for away players, every half second, only in land near other players. When the attacker is down, the
  defence ends and the guards walk back.
- **Patrols go on** while you're away, in land near other players. Far from everyone they wait where they are.
- **No fights where nobody watches.** Far from every player an away player's guard starts no fight, and a defence
  that starts there ends at once.
- **Posts are saved.** A unit remembers its post ("Guarding" or "Aggressive guard") in the save. When you log in after
  a restart, it takes that post again and walks back to it. Hold, or any other order, ends the guard and its post.
- Landed 11:51 as "q4-offline-guards" (gate: compile, combat 32/32, obey 32/32; restore point
  `restore-points/before-polish-q4-offline-guards-20261031-114957`). Not in an app build yet; the train builds after
  landings.
- Arena test `tests/offline_guard.dm`: 23 of 23 checks pass on the live game after the landing. Hand-over for Q5:
  side-session notes `q4-offline-guards.md`.

## Numbers

Arena test, speed 32 (ticks are game tenths of a second, counted from when the goblins appear):

| Case | Before Q4 (world loop off) | Now |
|---|---|---|
| A goblin strikes a posted guard of an away player | defence starts, never ends; guards stuck off post | guards fight it until it's knocked out (tick 144); all 3 back on post at tick 164 |
| Aggressive guard, awake land | fights, back on post | the same (foe out at tick 250, back at 268) |
| Aggressive guard, nobody near | not measured (nothing checked for land nobody's near) | starts no fight |
| Defence begun where nobody is near | never ends | ends after 2 ticks |
| Patrol, away owner, awake land | stands still | walks its route |
| Post after save and load | gone (HomeLoc isn't saved) | kept; loaded units walk back in 12 ticks |

6 of the checks fail with the world loop switched off (`tests/og-noloop-checks.json`), all pass with it on
(`tests/og-final-checks.json`).

Server cost of the new world loop (tick profiler label "offline guards"), speed 1, an away player's guards posted in
land near another player. 30 s with nothing happening, then 30 s with goblins walking in (one per 10 guards, three
waves). Tests `og-prof0/20/200-checks-tick-profile.log`:

| Guards | Nothing happening | Goblins walking in | Units on the loop at the end |
|---|---|---|---|
| 0 | 0 ms/s | 0 ms/s | 0 |
| 20 | 0 ms/s | ~1.0 ms/s | 0 (6 goblins, fights over) |
| 200 | 0 ms/s | ~2.6 ms/s | 18 (16 still fighting 60 goblins) |

Guards on post cost the loop nothing: only units with a fight, an attack or a patrol are on it. That works out at
about 0.07 ms per fighting unit per pass, spent in the same fight steps the online part of the game runs. The
guards' own looks round for a foe are an older cost: 0.3 ms/s for 20, 0.9 ms/s for 200. The profiler's clock counts
whole milliseconds and the Mac was busy with a 100-player swarm test at the same time, so read these as rough.

## Not done

- **The Garrison order** (units pick their own posts: doors first, then walls for bowmen) is left for Q5. It needs a
  button in the HUD and a command in the HUD's command list, both being edited by the quest-maker session today. It
  also needs to know which side of a door is the fort's inside, which is Q5's Site area.
- **After a server restart, an away player's units aren't in the world** until their owner logs in (that's how saves
  work today). So their guards only guard once the owner has logged in at least once since the restart. Q9 (far
  records, regions) has to bring garrisons back without their owner.
- The log-in step (taking posts again after a load) can't run in the arena (it needs a real client). The arena checks
  the same step called directly. Not play-tested in the browser yet.

## Correction: guards don't linger

Earlier I said guards stand over a knocked-out foe for 15-30 s before going back. That was wrong. The test counted a
*stunned* goblin as down. A stun ends the defence (the game treats a stunned foe as out of that fight), but the
guards' own AI keeps fighting it, which is right. Measured from the real knock-out, guards are back on post in about
2 s, online and away. You said "go straight back": they already do, so nothing changed. I tried a change that made
guards drop a downed foe sooner, and in its test run one guard didn't get back to its post, so I didn't land it. The
test now checks "back on post within 10 s of the knock-out" for both guard cases.
