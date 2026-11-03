"""Prepare the explicitly authorized detailed-artwork page prompts."""
from pathlib import Path
import json
BASE=Path(__file__).resolve().parents[1]
plan=json.loads((BASE/'detailed-artwork/production-plan.json').read_text())
materials={'diamond':'Pale icy cyan-blue diamond crystal: clear faceted planes and white sharp glints, preserve tan/brown grips and any source accent colors. Do not turn it into gray steel or change object silhouettes.',
 'dragonbone':'Warm ivory dragonbone with pale cream planes and golden-brown shadows, dark brown grips, exactly the bone construction visible in the source. Keep the subtle natural bone texture without adding extra horns, spikes, skulls or ornaments.',
 'gold':'Rich warm gold metal with pale yellow glints and amber/brown shadow facets, preserve dark grips and the native accents. Do not turn gold into yellow cloth or add gems, engraving symbols, spikes or filigree absent from source.'}
for family in ['diamond','dragonbone','gold']:
    for page in plan['missing_families'][family]['pages']:
        rows='\n'.join(f"Row {i+1}: label exactly {r['state_name']!r}; visible columns {','.join(('S','N','E','W')[v] for v in r['occupied_direction_indices'])}; other columns must stay empty." for i,r in enumerate(page['rows']))
        prompt=f'''Use case: style-transfer. Detailed fantasy equipment sprite sheet artwork, page {page['page']} of {len(plan['missing_families'][family]['pages'])}.
Input image 1 is the exact source page and authoritative identity/layout reference. Input image 2 is the approved detailed bonehide sheet, STYLE reference only. Input image 3 is the approved detailed magic sheet, STYLE and page layout reference only. Do not transfer bonehide horns, colors or magic effects into the source designs.
Transform the small source sprites into genuinely detailed polished pixel/voxel artwork in the same game style as the two enhanced references: crisp near-black pixel outlines, richly faceted material shading, deliberate stepped highlights, readable small texture details, solid dimensional construction. This must be a meaningful detailed artwork redraw, not a resized copy or an RGB color/lighting filter. Keep the game's actual equipment identity.
MATERIAL: {materials[family]}
Preserve ALL {len(page['rows'])} rows in exact order and all four S N E W columns left to right. Keep the source shapes, proportions, weapon classes, blade curves, axe/hammer head geometry, shafts and grips, armor plate construction and facing direction. Keep disconnected pommels, handles or tiny partial fragments disconnected and in their correct cell; they are intentional equipment overlay art. Never complete a partially hidden W view into a whole object. Do not fill a source blank cell. Do not mirror an E view into a missing W view. No character bodies, heads, faces, mannequins or limbs inside armor. No additional objects, arbitrary spikes, horns, gems, trim or altered design motifs.
ROW AND OCCUPANCY SPECIFICATION:
{rows}
Expected occupied cells total: {page['expected_visible_cells']}; a tiny fragment counts as occupied. Preserve every listed object/view and every intentional blank.
Create a clean full-resolution opaque charcoal blue-gray contact sheet like the style references. Enlarge and space the artwork enough to show the detailed shading clearly. Use readable white labels at the left of each row and white S N E W headers. Title exactly: Gear/{family}.dmi — Page {page['page']} of {len(plan['missing_families'][family]['pages'])}. Keep every row label verbatim as specified, with ample left margin so no label is truncated. No extra words, watermark or decorative panels. No gradient halo or ground shadow touching objects. Keep all artwork completely inside its own cell with clear gutters; no cropping and no row omission. Keep the final sheet at the tool's full output resolution, no native-height reduction in this phase.'''
        path=BASE/'_meta/prompts'/f"detailed-{family}-page-{page['page']:02d}.txt"
        path.write_text(prompt+'\n')
print('Prepared 15 unique prompts')
