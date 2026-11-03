# World look test: Albion-style (2026-10-27)

Status: **rejected by the owner on 2026-10-27 ("the lotr look is better")**. The world stays on the LOTR / Battle for Middle-earth look. Kept for reference only.

Originally a look test for the owner to judge. Nothing is in `game/`; the app was not rebuilt. Only the world was restyled (ground, trees, rock, water, light). Units are the original sprites, untouched.

Picture: [albion-vs-today.jpg](../reports/albion-look/staged/shots/albion-vs-today.jpg). It shows five recorded scenes (forest, mountain face, pond shore, village, biome edges), each three ways: today, the Albion look at today's camera, and the Albion look at a fixed, steep Albion-style camera.

## How it was made

`reports/albion-look/staged/arena.py` copies the real 3D page (`game/Interface/remastered.html`, read only) twice and feeds both the recorded scenes from `tools/worldlook_replay.py`. No game server, client or input is involved. `albion.html` gets 10 small text patches; `today.html` gets none.

```bash
python3 standalone/remastered/reports/albion-look/staged/arena.py shots
```

```bash
python3 standalone/remastered/reports/albion-look/staged/arena.py serve --port 8765
```

`shots` rebuilds both pages and remakes every still and the sheet in about 90 seconds. `serve` lets you look around (wheel, right-drag, Q/E): open `http://127.0.0.1:8765/albion.html?clean=1&scene=5&cx=14&cy=47&dist=13&pitch=0.62&yaw=0.35&dayp=0.45`. Use the same address with `today.html` to compare.

A patch that no longer matches the page stops the build with a message, so the test can't silently drift from the game.

## The style, as patched

| Part | Today | Albion test |
| --- | --- | --- |
| Meadow | Olive `0.36 0.45 0.25`, fine photo-like grain | Fresh green `0.37 0.52 0.23`, broad soft painted blotches and short brush strokes (new 512 px textures, still averaging neutral) |
| Leaves | Muted greens | Clearer greens, bright canopy tops, darker undersides |
| Pines | Dark green | Deep teal-green |
| Rock | Brown-grey, bare | Neutral cool grey with **moss on every upward face** (noise-broken). This is the strongest Albion cue, and the faceted rock is kept. |
| Water | Navy `0.15 0.24 0.36` | Teal `0.10 0.38 0.46` |
| Sand | `0.82 0.72 0.48` | Warmer `0.86 0.74 0.48` |
| Light | Smooth falloff | Soft painted two-step from shade to sun; shade slightly cool, light slightly warm; saturation +12 % on world faces only |
| Sun | 14° to 58° high | 28° to 62° high: shorter shadows, brighter mid-day |
| Haze | Grey-blue | Faintly turquoise |

## What the pictures say

1. **The world restyle works with the engine as it is.** All of it is colour, light and texture on the current meshes. There are no new models, no server change, and no change to chunks, mining blocks or the fade rules.
2. **Moss-topped rock and fresh meadows carry most of the Albion read.** The tree and water changes help; the sun change is subtle.
3. **Keep today's camera.** At Albion's steep, fixed camera the original unit sprites shrink and flatten, and near cacti stretch. Albion's camera suits its 3D characters, not 2D sprites, so the look should be judged at today's camera (middle column).
4. It conflicts with the earlier LOTR / Battle for Middle-earth direction for the world, which is darker and earthier. The owner decides between them, or a blend: these patches can be dialled between both with one strength value per row above.

## Cost and risk of rolling it out

- **Cost: small.** About 10 text-level changes in `remastered.html` plus 3 ground textures, and a per-biome pass for jungle, mesa, tundra, ashlands and mushroom (not covered here). Roughly a day of work, including a seasons and night check.
- **Risk: low to medium.** The shader change touches every lit face, so night, seasons, fog of war and the rock and tree fades must be re-checked. The test covers only day, summer and the surface level. Rock fade and tree thinning still work, since they use the same alpha tags the moss patch reads.
- **Frame cost:** a few extra shader instructions per pixel; not measured yet. Run `worldlook_replay.py perf` before landing.
