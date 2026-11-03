# The step, in the engine

You asked whether Java or native code would be better for a soldier's step. The game's engine is C#, so native code means C# inside it, and it reaches the units directly.

We timed a 1000 v 1000 proc by proc. A step cost about 55 millionths of a second. The "can a unit stand here?" check around it ran 44,000 times a second and cost more than all the steps. Much of a step was calls that do nothing: on a battlefield full of bodies, blood and dropped gear, the game asked every one of them whether it minded being stepped off.

Now the engine makes a step onto open ground itself, following the same rules. The "can a unit stand here?" check uses the engine's copy, which the route finder already relied on. Doors, wall-walks and other special tiles still go the old way. We checked a million steps and three million checks against the old way, and none differed. In the same 1000 v 1000, walking costs 35% less and the battle runs at 1.07 real seconds per game second instead of 1.29, nearly real time. Build 130.

## Later: fewer fighter ticks, tried and left out

The next idea was to let fighters who are only waiting for room, or already trading blows, think half as often. I built it with a check mode that compares every skipped moment with what the fighter would really have done. Fighters in melee never changed their minds, but the ones waiting at the back would often have stepped into a gap half a second sooner. Timed side by side, the whole battle got no faster: the earlier walking work had already made those moments cheap. So it stays on the shelf, and a 1000 v 1000 now runs at about real time.

## Then: morale and the look for foes, faster

Every second each soldier in a fight counts the friends and foes around it to set its morale. That count read about a dozen facts about every unit within six tiles, one by one, and it was the single biggest cost left in a big battle. Now the engine remembers what it read about each unit and reads again only when something about that unit has really changed, which in a battle is about one time in twenty. A second look, "is any foe standing right beside me?", now gets a quick answer from the engine first, since nearly every time the answer is no. Both were checked against the old way on hundreds of thousands of looks with no difference at all, and a 1000 v 1000 runs about 10% lighter per tick.

## And the step itself, lighter again

Two more pieces of a big battle's walking got lighter. Every step checks whether a soldier may pass through the friends ahead, and each check used to read every body, splash of blood and dropped weapon on a tile one by one. Now the engine remembers those, since they almost never change. Soldiers standing on a friend's tile also used to look all around for a free spot twice a second, which was expensive because of how the engine gathered the tiles; that look now comes straight from the engine. The first try had a bug that deleted a map tile and flooded the test logs (and slowed the Mac), which was caught in testing, fixed, and checked against the old way on millions of steps and checks with no difference.

## Distances, and one that didn't pay

"How far apart are these two?" is asked about nineteen thousand times a second in a big battle. It now has a quick engine answer that gives exactly the same result, checked on every kind of thing it can be asked about. The battle field (the shared map that leads fighters to the front) was measured too. A trick that worked elsewhere, remembering what was already read, saved nothing here: the soldiers it reads are mid-fight and change constantly. So that part was left exactly as it was.

## Watching it: the rubberbanding

Watching a 1000 v 1000, the battle felt smooth, but soldiers walking up to the line kept stepping forward and back. Counting every step showed why: about one step in nine went straight back to the tile it had just left. Fighters looked for the nearest free spot beside an enemy every second, and on a crowded front that spot kept jumping from just ahead to just behind as others filled it. Now a fighter sticks to its way a little longer and never steps straight back; it waits a moment instead. Back-steps fell to about one in twenty-five, and the fighting is as fierce as before.
