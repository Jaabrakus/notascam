# qa-stability, 2026-10-25

- 15:22 One test suite for every landing: `tools/check_suite.py` (QUICK: 13 arena and headless checks; FULL adds the real app check and the launch check). Baseline on today's game: all 15 pass, the 6 known chop cases in obey listed in one file with their reason.
- 16:17 The test suite now runs three checks at a time, each on its own port and files; the quick tier is about 12-13 minutes of running. All 13 pass on today's game, including the two afternoon landings.
- 19:57 The combat test runs again and is part of the suite (it had stopped starting); two tests that had drifted from the game (bodies' rot smell, swords now drawn in 3D) check the right thing again.
