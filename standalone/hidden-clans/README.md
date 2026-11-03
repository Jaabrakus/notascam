# Hidden Clans

A ninja game grown from a copy of Banners of the Deep (`standalone/remastered`), taken on 2026-11-01. It keeps
Banners' engine, 3D world, HUD, body-part combat (limbs, wounds, severing), villages and work, and adds the
mechanics of Naruto GOA (`~/Downloads/GOA Source`): chakra, jutsu, clans, ranks, missions. GOA's names and lore
are not used; everything gets its own names.

Play: you play your own ninja directly, and your village's ninjas work and fight RTS-style (Banners'
towns-and-heroes plan).

## Separate from Banners

| | Banners of the Deep | Hidden Clans |
|---|---|---|
| Folder | `standalone/remastered` | `standalone/hidden-clans` |
| App | `Banners of the Deep.app` | `Hidden Clans.app` |
| Saves | `~/Library/Application Support/Dungeon Master Remastered` | `~/Library/Application Support/Hidden Clans` |
| Ports (game, topic, web) | 12151, 25651, 8080 | 12171, 25671, 8090 |
| Bundle id | `local.dungeonmaster.remastered` | `local.hiddenclans` |

Banners' own README (how its tools, checks and engine fit together) is `standalone/remastered/README.md`; most of
it applies here too. The engine (`engine/server/OpenDreamRuntime.dll`) and the shared runtime under `standalone/replica` are the
same as Banners' at the copy. Engine improvements made for either game can be carried to the other.

## Build

```sh
python3 tools/build_app.py
```

Builds `Hidden Clans.app` here. The title, window name and icon come from `tools/make_client_brand.py`
(run it, then `python3 art/hud/hud.py adopt`, after changing the name).

## Its own so far (2026-11-01)

- `Code/Remastered/Ninja.dm`: chakra and the techniques (Substitution, Flash step, Fireball, Kunai).
- `Code/Remastered/Drive.dm`: WASD for your ninja, a click on a foe attacks; R is attack-move (A moves).
- `Code/Remastered/FemaleBodies.dm`: women on their own GOA bodies.
- `game/Icons/Remastered` and `Interface/gear3d`: the GOA bodies, limbs, ropes, grips, ragdoll maps and generated
  armour from `standalone/remastered/reports/goa-sprite-test/staged` (land/out, armour/out, overlay female sheets).
  Banners' own pictures are still in `standalone/remastered/game` to go back to.
- Where it is going: `planning/BATTLER_PLAN.md` (a GOA-style battler: no RTS controls, techniques aimed at tiles, the
  GOA animation rig). `planning/GOA_MECHANICS_PLAN.md` maps GOA's mechanics.

## Not yet changed from Banners

- Discord sign-in still uses Banners' Discord application (`mac-app/Launcher.m`).
- In-game text, HUD wording, the RTS controls and the world are still Banners'.
- The test tools in `tools/` came along, but `tests/` and `reports/` did not; checks that need them are copied
  in as they're needed.
