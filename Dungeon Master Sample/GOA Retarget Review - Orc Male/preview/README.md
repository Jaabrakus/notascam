# GOA Orc male — retarget review candidate

Generated from the approved Elf renderer. This is not a claim of perfect art or completed validation.
Read `fit-report.json` first. Open `preview/index.html` to review.

Rebuild: `python3 rebuild.py`. Optional server: `python3 -m http.server 8881 --bind 127.0.0.1`, then open `/preview/`.

Edit `profiles/character.json` joints/grips and `poseTargets.bow` to refine the fit. Bow targets are mapped relative to this body's neck and shoulder span; East mirrors West. Set `keepGrips: true` when reusing an explicitly calibrated profile through the retarget tool.

Review idle, walk, slash, thrust, bow and throw in all four directions. Bow: 0.32, 0.72, 0.90, 1.15, 1.40, 1.75 seconds. Throw: 0.26, 0.38, 0.52, 0.75 seconds. Check seams, hand contact, reach, foot contact and recovery at native scale. Fixed Elf throw offsets and other special cases still require character-specific review.

No Elf baked sheets or pass reports are included. Use viewer export buttons after visual review. Other races and hybrids use the same input schema; wings/tails and non-humanoid anatomy require additional layers. Never hide those limitations behind a passing build.

Warnings:
- Zone cutter creates provisional flat fillers and synthetic far arms; hidden anatomy needs art review.
