# Moved (2026-10-30)

The native procs that were here are now in two folders (U3 of `planning/SERVER_UPGRADES_PLAN_2026-10-30.md`):

- `engine/core/`: what any DM game could use. Nothing in it names Banners of the Deep's types, vars, races or rules;
  `tools/engine_boundary_audit.py` checks that.
  - RmNative (registration and helpers), RmAlloc, RmMemory, RmPack, RmVer, RmWatch, RmDist, RmTiles.
- `engine/game-botd/`: what knows the game.
  - RmGrid, RmKept, RmPath, RmPlan, RmChat, RmSight, RmWalk, RmStep, RmReach, RmRoute, RmField, RmMorale, RmPool,
    RmSlots, RmStore, RmDecay, RmWorked, RmSwim.

`tools/build_runtime.py` merges the two as it took this folder; `--native-dir` still takes one folder holding all of
them (a staged copy). A `.cs` file left here stops the build, so a change can't be left out without anyone seeing.
