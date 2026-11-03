# Hidden Clans as a battler (owner, 2026-11-01)

The owner, after playing the first slice: "now this is a completely new game lets remove the rts controls and focus on
this new battler game", "make all goa races the main", "use goa animation", a GOA-style ninja game. Names stay our own
(the game is hosted publicly): Naruto's villages, techniques, clans and characters are never used.

## Done on 11-01

| Piece | Where | State |
|---|---|---|
| Chakra (80 + 4 per Intelligence, 1.5% back a second, worked out when read) | `Code/Remastered/Ninja.dm` | played: drops and refills |
| Techniques as moves every ninja has: Substitution, Flash step, Fireball (seals, real fire), Kunai (10, refill 1 / 20 s) | `Ninja.dm`, hooks in WeaponSkills, Strike, Attack, Defense | played: used by both sides in fights, by hand and on their own |
| Techniques section + chakra/kunai bar on the card's Spells tab; hit words; kunai drawn in 3D | `art/hud/src` 012, 022 | seen |
| GOA bodies, limb states, ropes, grips, ragdoll maps, generated armour (all races, male hybrids) | `game/Icons/Remastered`, `Interface/gear3d` (from the GOA test pipeline) | seen |
| Female GOA bodies (80, hybrids included); a woman's own top and hair, not laid over again | `game/Icons/Remastered/Races64/* Female.dmi`, `FemaleBodies.dm` | seen (Elf woman) |
| WASD walks your ninja (camera-relative, 8 ways), camera follows; click a foe to attack it; R is attack-move (A moves) | `Drive.dm`, `View3D.dm`, `HUD.dm`, page 009/027, `skin.dmf` | played |
| WASD strictly on the tiles (one key a grid line, two a tile diagonal, turned by the camera a quarter at a time, steady at 45°); first step at once (12-20 ms to the 3D view), then its own walking pace (~0.4 s a tile); through its own people | `Drive.dm`, page 027 | measured |
| A new way steps at once (~60 ms), never waiting out the tile it was on; one step early at most, so tapping W/D for 3 s made 9 steps, its walking pace | `Drive.dm` RmDriveNow(turn) | measured |
| GOA's kick (KickA: knee up in a guard, leg out high, body leaning back) as a clip; a `kick` key lifts the front foot; bare hands throw it 35% of blows (50% on a kill) beside the punch | `art/gear3d/skills.js`, `game.js` → `game/Interface/gear3d.js` (scripts only: install.py would put Banners' grips back over GOA's) | played by the raiders in a fight |

## Next, in order (owner to confirm the order)

1. **Responsive.** Measure key to screen. Then: the server at 20 ticks a second if the cost allows (every Banners
   system runs per tick: measure CPU first); your own ninja moved on the page at once (prediction) and corrected by the
   server's step; attacks and techniques on exact tick timing (no 0.1 s slop between a press and its blow).
2. **Battler controls, Diablo's way, no RTS** (the owner, 11-01: "click on target to do the click animation ... like diablo
   how they do their skills and clicks"). Left-click a foe: your ninja goes at it and swings (in). Techniques on the number
   keys fire at once at what is under the mouse, a tile or a foe, no second click; the shape shows on the tiles while
   hovering (the specials' 3D aim preview, Specials.dm). Off: box select, right-click orders, the village/work/build bars,
   group keys.
3. **Animation: keep what there is** (the owner, 11-01: "i like the animations what every we did its good keep it"):
   the game's own clips on the GOA bodies stay. Keep the techniques and the GOA punch and kick: unarmed fighting is
   GOA's punch (the game's punch clip already plays on the GOA bodies) and a kick still to add (the GOA pack's kick
   frames, or the Ki Combat side project's rising kick, as a clip). The 15-part rig replaces nothing unless asked.
4. **GOA races the main ones.** Bodies are in. Left: male elves (Banners draws them on the Human body), tuning the 79
   first-pass female bodies, the race list and names.

## Open questions for the owner
- (Decided 11-01: WASD strictly follows the tiles, at walking pace, first step at once.)
- The village: gone entirely (one ninja per player, as GOA), or kept running on its own with no RTS controls.
