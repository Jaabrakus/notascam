# Redraw and fitting status

The user subsequently rejected the automatic worn fitting result. The active
preview now uses `../worn-masters-v1/index.html`: complete worn character redraws
matched to the approved Deepguard Iron style. Keep this compositor as an experiment.
Equal-width column cuts were also found to clip some source objects; `build.py`
now finds per-row transparent gutters and hashes the cuts to reject stale previews.

The built-in imagegen tool produced the PNG design sheets in this folder. Exact
prompts are in `PROMPTS.md`. Source cells and override artwork are cataloged by
`build.py`; the source images are preserved.

The 63 modern drawable design classes have draft representations. This is not a
claim that every material/race combination, animation or original item is complete.
The original 182-item equipment list also contains named Dragoon/gold-trimmed,
gem-encrusted, Skorn and Supernatural Bone equipment. Their 42 special definitions
are recorded in `legacy-special-items.json`; generic ornament studies must not be
silently substituted for those actual item definitions.

`worn.html` defaults to the approved Deepguard Iron. It uses the previously approved
registered 64px piece layers in their original common coordinates. On Human, every
part's rectangle remains exactly (0,0,64,64), verified during export. Other bodies
use a shared body-family width/height transform. Their fit still needs visual review.
This preview does not redraw or independently resize each approved armor component.

The other native kits use preliminary individual-part registrations. The first pass
covered some eyes and altered proportions; head alignment was adjusted, and the
approved Deepguard master was restored as the reference. These experimental fits
are explicitly drafts, not production game assets. Ears and hair may remain visible.

Crafting-race tags are authoring data, not implemented game crafting restrictions.
Crafting origin, body fit and the existing wearer rules remain separate.

Remaining work includes individual race-fit review, checking the original special
items against their exact source sprites, pose authoring, near/far masks, missing-
limb behavior and game integration. Bloodwhisker's original identity is a dark green
spear (see `oldlooks64.py`); its new thin-green-weapon draft needs that source check.
