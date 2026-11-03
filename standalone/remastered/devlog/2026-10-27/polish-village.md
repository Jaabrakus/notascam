# Polish pass 2: village life and rule (polish-village, 10-27)

The village now says when a raid is over and when a siege on your banner is lifted, and a footprint clue reads
"goblin footprints at 12, 30" instead of "tracks by footprints". I replayed the village on build 68 (houses and rooms,
laws and rulership, the log, the morning and away cards, raids and siege lines); last night's strings and fixes held up,
and these were what still read unfinished.

Status: done. village-polish2 landed 08:43 (restore point restore-points/before-polish-village-polish2-20261027-081549); village 20/20, war 10/10, siege 11/11 on the live game.

## Done

- **closing-lines**: a raid wrote "Raid! ... coming" and then nothing; a siege that faded never said it was lifted.
  Now "The raid is over: no raiders are left marching on you." and "The siege of your banner at 40,40 is lifted."
  Arena probe (closing_probe): lines before 0 / 0, after 1 / 1. War 10/10, siege 11/11, raids 8/8, realms 8/8, board 10/10.
- **clue-footprints**: "Clue: goblin tracks by footprints at 12, 30" is now "Clue: goblin footprints at 12, 30".
  Village check 20/20 (its forensics row included).
- Speed: both write one line or build one string per event: no measurable change.

## Looked at, nothing to fix

- The away card, morning card, room text (no mood promises), law and succession banner, truce and peace messages (the
  plural slips I noted last night were already fixed by the words batch), the tavern box (buttons already disabled with
  a reason).

## Needs the owner

- Nothing new. Last night's list in `devlog/2026-10-26/polish-village.md` still stands.
