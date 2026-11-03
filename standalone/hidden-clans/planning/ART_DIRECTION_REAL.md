# Art direction: the "real" style (October 21)

Supersedes the chunky toon direction in [ART_DIRECTION.md](ART_DIRECTION.md). Status: in progress, being judged by the lead designer from renders and the 3D view.

## The look in one paragraph

Lord of the Rings / Battle for Middle-earth flavour: believable people and creatures in worn, earthy materials (wool, linen, leather, iron), modelled in Blender and rendered to sprites the way pre-rendered isometric games do. Every race, creature and item keeps what made its original 32 px sprite recognisable: its colour, its eye colour and its one defining shape (the orc's green and red eyes, the night elf's navy skin, the kobold's horns, the dragon's orange belly and colour variant). Proportions are realistic but a little heroic (broader, bigger heads, hands and feet) so figures read at sprite size.

These are style references only. Nothing is copied, traced or extracted from other games or videos. All models are built in code (`art/pipeline/`); each one is also saved as a `.blend` file that can be opened and edited by hand.

## Camera and output

| Rule | Value |
| --- | --- |
| View | 37.2 degrees above the horizon, orthographic, the same angle as the 3D view's Iso camera |
| Scale | 1 Blender unit = 1 tile; feet on row 59 of 64 |
| Facings | the model turns 0, 180, +90, -90 degrees for S, N, E, W; camera and lights never move |
| Render | Cycles, 512 px per tile, 64 samples, denoised, AgX colour |
| Sprites | 128 px and 64 px per tile, coverage-weighted colour, binary alpha (50 %), darkened edge ring, soft outline at 38 % of the touching colour |
| In 3D | sprites marked `el` (render angle) are stretched by 1/cos(camera pitch) so they keep their drawn proportions; 128 px sprites are mipmapped |

## Light and materials

- Warm key sun from the screen's top-left and slightly in front, cool sky fill, a warm rim light from behind so silhouettes separate from grass.
- Materials are painted colour plus a little texture: colour variation, a fine bump (weave, leather grain, hair strands, scales) and ambient occlusion in creases. Skin has a touch of subsurface. Eyes that glow in the originals (red, yellow) are emissive.
- Earthy, muted cloth; skins keep the originals' hues.

## Body families

| Family | Builder | Members |
| --- | --- | --- |
| Humanoid | `races_real.build_person` | Human, Dwarf, Night Elf, Orc, Goblin, Kobold, Lizardman, Frogman, Skeleton, Zombie, Vampire, Demon; next: Ratman, Svartalfar, Gargoyle, Half-Demon, Illithid, Werewolf, Gremlin, Angel of Death, Sand King, Fishman, Stone Golem, Ghost |
| Dragon | `creatures_real.build_dragon` | every colour variant of dragons.dmi |
| Spider | `creatures_real.build_spider` | Warrior, Queen, Widow; next: Hunter, Worker, young/old stages, cave spiders, beetles |
| Next | | four-legged animals (wolves, sheep), serpents (Naga), plants, flyers (bats) |

All humanoids share one rig (root, hips, chest, head, shoulder and hip joints, hands, forearms), so the sprite states (missing limbs, sleep, sneak) and gear overlays work the same for every race.

## Gear (next)

Weapons and armour are separate overlay renders on each body, by shape and material tier, using the same classification the 3D models already use (`Remaster3DGear`): weapon kind and tier, shield, helmet, chest, legs, arms. Shapes take an early-medieval / Middle-earth line (nasal helms, mail, round and kite shields, broad dwarf axes, jagged orc blades); colours follow the originals' material code (grey iron, maroon bronze, white bone, black chitin, cyan-white adamantium, gold, red-black hell metal).

## Rebuild

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup --python standalone/remastered/art/pipeline/render_real.py -- [--only Human,Orc]
python3 standalone/remastered/art/pipeline/build_real.py
```
