# Generated matching equipment pack

All 354 generated gameplay equipment definitions map to source-backed shared assets. The pack exports every supported drawable design/material combination once, plus fitted item-layer and equipped previews for seven main GOA body templates and socket metadata for all registered bodies. Material-set previews combine compatible source recipes without replacing missing slots with unrelated art.

This is a deterministic source-art export, not an AI redesign of the whole catalog or proof that every fit is production-ready. Standing-only variants remain standing. Full hybrid movement, limb-loss states and clean hidden Deepguard surfaces are still pending. Original source/game files are unchanged. All canonical gear poses available in the source are exported; fitted previews show the real body movement with the neutral hold, not newly created attack animations.

Run generate.py --resume to regenerate skipped/missing artifacts. Use --all-bodies to bake every reference-material design onto all registered bodies; fit metadata already covers them without those duplicate PNGs.
