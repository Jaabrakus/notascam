# Gear authoring standard

Use Dungeon Master's modular equipment structure for new Banners of the Deep / GOA gear.
This records the agreed authoring rules; it does not claim all listed animations exist.

## Artwork and coordinates

- Work in the approved chunky GOA pixel style. Character fitting space is 64 × 64,
  normally with feet near (32,61).
- Keep equipment separate from the body. No skin, eyes, hair or character pixels in
  final equipment layers. A visible-pixel cutout is a starting draft; hidden surfaces
  need artwork before the piece can support different poses.
- Supply South, North, East and West views. Keep the same canvas, origin and body
  registration for every layer. Tight crops must retain their original offset.
- Separate left/right limb pieces wherever those pieces exist. A design can have
  one shoulder guard, no shoulder guards, wraps, a mantle, a harness, a long coat,
  or another distinctive silhouette; never force every set into a twelve-part kit.
  A missing limb must not hide the other side or leave armor floating in place.
- Keep shape and material/palette separate where practical. Do not mix body skin
  recoloring into a material change.

## Shared pieces and fitted bodies

Racial armor is a distinct crafting tradition, not just one human kit resized.
Human Leather, Orc Leather, Dwarf Leather, Elf Leather and other racial sets have
their own fantasy designs and crafting-race tags. Only the named crafting race can
craft its racial set. Record crafting access separately from body fits and existing
wearer rules; do not infer who can equip an item from who can craft it. These tags
are authoring data until they are integrated into the game's crafting system.

Draw inspiration from fantasy while keeping the approved pixel style. Allow exotic
and asymmetric pieces. Fit the actual race's torso, limbs, ears, horns, hair and
wings where present. Native generated sheets are drafts until their pixels are
registered, composed on actual bodies and reviewed through the required motion.

One item definition identifies the design, material, slot, source frames and fitting
profile. Each body family supplies its size, attachment points and animation mapping.
Reuse a body's fit for compatible hybrids; supply an override for a genuinely different
shape, horns, ears, tail, or wing arrangement. Reuse is verified visually, not assumed.

Armor can use race-fitted transparent overlay sheets, as Dungeon Master's Gear64 does.
Weapons, shields and helmets can use registered attachment sprites or the existing
mesh-derived 16-angle art. Four body facings do not imply sixteen body sprites.

## Motion and attachments

- Match the body's actual direction, state and animation frame.
- Standing views are not completed walk, armed-walk or attack art.
- Attach weapon grips to the right hand, shields to the left forearm/hand, and helmets
  to the head. Apply the same frame's attachment positions as the body moves.
- Keep the holding arm consistent in an armed walk; do not let the weapon's grip
  detach while the legs move. Author the required body/armor poses.
- Respect near/far depth. A weapon may be partly hidden by the body from behind.
- Preserve ears/horns where the helmet design permits them. A generic oversized
  helmet is not a substitute for a compatible fit.
- Visible ears and hair may protrude outside fitted equipment, including on small
  races. Do not erase those features to force a flush helmet outline. Review armor
  placement, face visibility, coverage and hand grips separately.
- Hide or unequip pieces whose required limb is absent. Two-handed equipment needs
  both appropriate hands; shield compatibility follows the game's item rules.

## Export and review

Keep editable/source layers and fitting metadata. Export complete equipped sheets
from those layers when useful; they are derived outputs, not a second independent
art source. Pad equipped frames for weapons extending beyond the body cell, recording
the body origin and frame rectangles. Do not silently crop them to 64 pixels.

Check all four directions, each authored animation frame, the loop transition, hand
grips, near/far masking, and missing-limb visibility. File validity, a successful
composition or a zero-difference reassembly does not prove correct anatomy or motion.

## Existing assets

- `armory/catalog.json`: 63 source-backed designs, including 33 weapon entries;
  32 weapon designs use 16-angle art, with their available poses, plus the GOA sword.
- `armory/Universal Gear and Weapons.csv`: supported design/material combinations.
- `armor-designs/deepguard-iron/pixel-fit-v2/pieces/`: twelve Deepguard equipment cuts,
  four standing views, full-resolution sources and shared-origin 64px versions.
  These still need clean hidden surfaces, pose authoring and race-fit review.
- `wardrobe/inventory.json`: original GOA wearable inventory, including color variants.

## Source framework

- `standalone/remastered/game/Code/Creatures/OverlayBuilds.dm`: original overlay stack.
- `standalone/remastered/game/Code/Remastered/Gear.dm`: item slots and race-fitted sheets.
- `standalone/remastered/game/Code/Remastered/Gear3D.dm`: armed states and held gear.
- `standalone/remastered/art/gear3d/gear3d.js`: attachment anchors, depth and gear poses.

The existing armory renderer and catalog implement a fitting/export workshop around
these sources. New artwork is not automatically integrated into the live game.
