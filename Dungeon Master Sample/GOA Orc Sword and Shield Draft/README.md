# GOA Orc sword and shield hold

Uses the supplied goa-zones-bundle tuned Orc body, fine zones and per-frame skeleton. No source bundle files or live-game assets are changed.

Idle hold and guarded walk: four facings, eight frames, native 64px transparent exports (256x512 sheets) plus padded 128px exports. All equipment fits inside the native cell; build checks prevent accidental cropping. Columns South/North/East/West, rows animation frames, 150ms per frame. Sword stays in anatomical right hand, shield in left. Side-view idle far arms are extracted from authored walk frames where visible. Held arms follow the source neck movement while the drawn walking legs stay intact. Small seam caps use existing Orc skin colors. Torso backing uses visible torso pixels from neighboring source frames; this is a limited hold, not an unrestricted pose generator.

Separate render layers, exact source hashes, grips and joint positions are in rig.json and assets/. The viewer can hide either item and show grips. Existing approved arming-sword and round-shield designs are reused, with shield front/back art selected by facing.

Build: `python3 standalone/goa-races/bundle-equipment-rig-v1/build.py`

Scope: Orc hold and guarded walk only. No attacks, universal race conversion, fitted armor set or live-game integration is claimed.
