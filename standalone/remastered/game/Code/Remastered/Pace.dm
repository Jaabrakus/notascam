// Combat pace (Remastered; the user, 2026-10-23: "a slow game", "a brutal grindy game", like vanilla WoW or
// RuneScape, not the original's). Measured with tools/check_pace.py (duels through the game's own attack orders).
//  - Melee needs a bump: a unit fights by stepping at its foe (WalkTo) and being stopped by it (Bump.dm). The ground's
//    Enter() (Building/TurfTypes.dm) stops a unit only when usr is that unit, and Orders.dm sets usr for move orders
//    and guard duty, not for attack orders or a monster's chase. So a fighter could step onto its foe's tile: then
//    neither could strike again, and the fight stood still until healing outlasted it (duels "still going after
//    3 minutes"). A unit walking at another owner's unit is now stopped like any unit, so it bumps and strikes.
//  - Slower blows: weapons swing at twice the old swing table's times (Hits.dm rm_swing_pace) and weapon moves'
//    cooldowns are as much longer (WeaponSkills.dm), while each blow lands as hard as before. Measured (8 duels of
//    humans each, 2026-10-23): iron swords 47 s -> 95 s median, swords in full metal armour 47 s -> 100 s; most
//    deaths are bleeding to death. Natural healing is gone (Healing.dm), and blunt blows that the parts they land on
//    can't take come off HP (Blunt.dm), so fist and mace fights end too.

// mob/Monsters/Move: this file's part is step RmChainMove_Pace in Code/Remastered/Chains/Move.dm
