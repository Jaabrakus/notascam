# dying-save-wait (10-27)

A save no longer catches a unit that is down. The autosave waits while one of your units is dying or knocked out, and Save Now refuses. This is the plan's interim fix (fixes plan, section 6, "Now"). It is staged and not landed.

## Done
- The autosave looks again every 10 s while someone is down. It saves once everyone is up or dead, and after about 3 minutes it saves anyway.
- Save Now says "Can't save while X is down." and doesn't save.
- The save format is unchanged. The autosave still comes every ~16 min from when it was due.
- Files: game/Code/Saves.dm (CallSave), game/Code/Remastered/Comfort.dm.

## Numbers (arena `dying_save_wait_check.dm`, the real autosave at game speed 16)
| Case | Before | After |
|---|---|---|
| Autosave due, unit dying, friend saves it at +25 s | saved at once, unit dying | saved 3 s after the rescue, all standing |
| Autosave due, unit dying alone | saved at once, unit dying | saved 50 s later, after it bled out |
| Unit kept knocked out for 4 min | saved at once | saved at the 180 s cap |
| Save Now with a unit down | saved | refused, with the line |
| Checks passing | 3 / 9 | 9 / 9 |

Existing checks, base and fix alike: save round trip, unit save, bleed-out, falls, subdue (knock-out), village (rescue), far records, obey, combat 32/32, stumps, compile (294 warnings both). treat_check doesn't compile on either copy (Treat.dm isn't in the game).

Speed: the check runs once per autosave (every ~16 min), and then every 10 s only while someone is down. Save Now does one pass over your units per click. No per-tick cost.

## Needs the user
- The autosave saves every player at once, so it waits while any player has a unit down. Save Now checks only your own units.
