# Universal equipment art catalog

This catalog groups real drawable designs by shape and supported material. It does not replace gameplay item definitions or invent combat statistics.

**63 designs**, **454 supported shape/material variants**. The 43 existing 3D-derived gear designs use 136 original strips at sixteen orientations.

| Slot | Drawable designs |
|---|---:|
| Weapon | 33 |
| Shield | 5 |
| Head | 6 |
| Chest | 10 |
| Arms | 3 |
| Legs | 5 |
| Feet | 1 |
| Hands | 0 |
| Back | 0 |

## Designs

| ID | Slot | Materials | Renderer |
|---|---|---:|---|
| `weapon.dagger` | weapon | 12 | `gear16` |
| `weapon.arming sword` | weapon | 12 | `gear16` |
| `weapon.longsword` | weapon | 12 | `gear16` |
| `weapon.scimitar` | weapon | 12 | `gear16` |
| `weapon.hand axe` | weapon | 11 | `gear16` |
| `weapon.battle axe` | weapon | 12 | `gear16` |
| `weapon.warhammer` | weapon | 11 | `gear16` |
| `weapon.mace` | weapon | 10 | `gear16` |
| `weapon.morning star` | weapon | 10 | `gear16` |
| `weapon.spear` | weapon | 12 | `gear16` |
| `weapon.halberd` | weapon | 12 | `gear16` |
| `weapon.pickaxe` | weapon | 10 | `gear16` |
| `weapon.bow` | weapon | 11 | `gear16` |
| `weapon.hammer` | weapon | 10 | `gear16` |
| `weapon.fishing rod` | weapon | 10 | `gear16` |
| `weapon.harpoon` | weapon | 10 | `gear16` |
| `weapon.spade` | weapon | 10 | `gear16` |
| `weapon.crystal staff` | weapon | 1 | `gear16` |
| `weapon.orb staff` | weapon | 1 | `gear16` |
| `weapon.skull staff` | weapon | 1 | `gear16` |
| `weapon.flame staff` | weapon | 1 | `gear16` |
| `weapon.nature staff` | weapon | 1 | `gear16` |
| `weapon.dragon staff` | weapon | 1 | `gear16` |
| `weapon.spider staff` | weapon | 1 | `gear16` |
| `weapon.rune sword` | weapon | 1 | `gear16` |
| `weapon.flame sword` | weapon | 1 | `gear16` |
| `weapon.frost axe` | weapon | 1 | `gear16` |
| `weapon.storm spear` | weapon | 1 | `gear16` |
| `weapon.void blade` | weapon | 1 | `gear16` |
| `weapon.holy mace` | weapon | 1 | `gear16` |
| `weapon.soul eater` | weapon | 1 | `gear16` |
| `weapon.bloodwhisker` | weapon | 1 | `gear16` |
| `shield.buckler` | shield | 10 | `gear16` |
| `shield.round` | shield | 12 | `gear16` |
| `shield.heater` | shield | 11 | `gear16` |
| `shield.kite` | shield | 12 | `gear16` |
| `shield.tower` | shield | 10 | `gear16` |
| `helmet.kettle` | head | 15 | `gear16` |
| `helmet.nasal` | head | 10 | `gear16` |
| `helmet.horned` | head | 12 | `gear16` |
| `helmet.winged` | head | 10 | `gear16` |
| `helmet.great helm` | head | 12 | `gear16` |
| `helmet.crested` | head | 11 | `gear16` |
| `chest.plate` | chest | 11 | `dmi` |
| `chest.banded` | chest | 6 | `dmi` |
| `chest.mail` | chest | 6 | `dmi` |
| `chest.scale` | chest | 9 | `dmi` |
| `chest.lamellar` | chest | 10 | `dmi` |
| `chest.brigandine` | chest | 6 | `dmi` |
| `chest.tabard` | chest | 6 | `dmi` |
| `legs.plate` | legs | 11 | `dmi` |
| `legs.mail` | legs | 6 | `dmi` |
| `legs.scale` | legs | 9 | `dmi` |
| `arms.plate` | arms | 11 | `dmi` |
| `arms.mail` | arms | 6 | `dmi` |
| `chest.leather` | chest | 4 | `dmi` |
| `legs.leather` | legs | 4 | `dmi` |
| `arms.leather` | arms | 4 | `dmi` |
| `chest.robe` | chest | 13 | `dmi` |
| `legs.cloth` | legs | 1 | `dmi` |
| `feet.boots` | feet | 1 | `dmi` |
| `goa.sword` | weapon | 1 | `goaHeld` |
| `goa.chest` | chest | 2 | `dmi` |

## Rendering contract

`catalog.py` exposes `build_catalog()` with no image embedding or writes. `catalog.json` is its generated snapshot.

- `gear16`: `pieceKey`, `strips` and per-pose `w/h/ax/ay` come from the existing metadata. Only `materials` listed for that shape are declared supported. Decode the original material-index pixels using `gear3d-pix.json.index`, then select one of sixteen horizontal strip cells.
- `dmi`: each supported material has `materialRecipes[material].layers`. Every layer supplies its actual `source`, frame width/height, source columns, and selected `states` with offsets, direction/frame counts, movement and delays. A layer with `state` selects that exact state; GOA dynamic layers omit it and list all source states.
- DM armor overlays are 64px full-body layers. Arms use paired L/R layers. `armedLayers` contains the alternate right-arm pose and replaces the normal right-arm layer when used; it must not be added on top of the normal right-arm layer.
- `feet.boots` is a real source state named `legs.boots` in `cloth.dmi`. There are no dedicated modern hand/glove or back/cloak assets in the catalog.
- `goaHeld`: the held/walk overlay lives in `layers`; `attackLayers` are separate w-attack pieces. Their offsets are already converted from BYOND +y-up 32px offsets into +y-down 64px fitting coordinates. GOA source frames should be displayed at 2x their 32px size.
- `sourceRaces` provides original race-specific armor filenames as alternatives; inspect their own metadata when switching sources. Canonical recipes and source metadata in this catalog are Human-based.

Armory renderers still need body-fit anchors, scale, depth ordering, and limb availability rules. These recipes do not create missing body animations. Full source transparency and source images remain unchanged.

Source paths inside the project are project-relative; GOA paths are absolute because that input lives outside this workspace. No network lookup or image generation is performed.
