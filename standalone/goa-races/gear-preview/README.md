# GOA bodies with the existing 16-angle gear

Open `index.html` in a browser. It is self-contained: images and metadata are embedded, so no server, JavaScript packages, network access, or game process are required.

Open `goa-held-sword.html` to start directly with GOA's original character and held sword. The main preview also offers **GOA · original held sword** in its weapon selector. This uses `sword1/swordover.dmi` for the held/walking overlay and `sword1/sword1.dmi` through `sword4.dmi` with the original pixel offsets for attack pieces. Enable Walk or Attack poses to cycle the corresponding original GOA body, armor and weapon frames. This native mode has four weapon directions; Dungeon Master's gear remains available with sixteen angle frames. The new race drafts still have no body attack animations.

This uses the current game's `gear3d-pix.json` and 136 original material-indexed PNG strips: 43 weapon, shield, and helmet designs, sixteen angles, plus the available weapon attack poses. Those strips were originally rendered from 3D gear models. The viewer decodes their material palettes in the browser using the same calculation as `art/gear3d/gear3d.js`. It does not use the older `gear3d-body.png` preview that was initially shown in chat.

## Controls

- Choose any of the six race drafts, or an original GOA character base.
- Choose a weapon, shield, helmet, and material.
- Select an armor layer. GOA chest/shoulders and dark red variants retain the original source-state alignment for native GOA bodies. Dungeon Master plate/mail/lamellar layers are available as fitting studies.
- Move the angle slider or enable Rotate to inspect the sixteen gear views.
- Enable Attack poses to inspect existing weapon pose frames. This is pose cycling, not a complete body attack animation.
- Enable attachment points, select a slot, and click the large preview to adjust it for the current character and cardinal body direction.
- Save anchors downloads the current fitting coordinates as JSON. Coordinates use a 64-pixel fitting space.

The body retains four cardinal sprite views while the gear has sixteen angles. The viewer is an isolated 2D fitting tool for that asset pipeline; it does not replace the live game's 3D renderer, depth buffers, camera transform, weapon motion, or arm/head masking. The race draft sheet is cropped at display time; it has not been converted into finished DMI animation sheets. Per-race animated body armor, hidden-hand/head masking, and production rig calibration remain unfinished.

All source game files and images are read-only inputs. No new AI-generated armor or gear image was created for this preview. `sources.json` records provenance. The earlier race body draft was generated with imagegen; its prompt is in the parent directory.

## Rebuild and verify

```sh
python3 standalone/goa-races/gear-preview/build_preview.py
python3 standalone/goa-races/gear-preview/verify_preview.py
```

The builder currently locates the user's GOA source at `/Users/kiwimango/Downloads/GOA Source`. The browser check uses a temporary headless Chrome profile with external requests blocked, visits the local file, checks sixteen angle selections, all 43 gear designs, nine body options, four attack poses, and JavaScript errors. It writes `verification.json` and preview screenshots.
