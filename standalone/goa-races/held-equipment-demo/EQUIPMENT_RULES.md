# Equipment and animation rules

These rules apply when designing, fitting, equipping or enabling weapons on these bodies.

1. The body carries the equipment. Animate the torso, shoulder, elbow, wrist and closed fist together. Equip switches must not introduce a gap or change hands.
2. This sample uses the anatomical right hand for one-handed melee weapons. The left arm remains free or supports a shield. Author west-facing anatomy independently; changing facing must not swap hands.
3. Measure the actual handle/shaft grip per item. Place it inside the fist, restore foreground finger pixels over it, and keep the wrist aligned. Fit pole thickness separately from length. An item with a different handle must get its own fitting offset.
4. A forward-facing spear is foreshortened: show the projected tip and short shaft, not its full sideways length. Keep the physical shaft thickness at the grip. North-facing body/arms naturally occlude equipment held in front of the character. Side views show more length.
5. Short spear jabs use a low point, compact wrist travel and no large lunge. Blades, axes and hammers can share a body sweep as a prototype; bow and casting actions have separate body poses.
6. Anticipation moves the whole assembled character. A small hop back, hop forward, attack and settle apply one root transform to body, hands and gear. Never move the weapon independently of the fist. Root animation is included in exported timing metadata; it is not extra hand-drawn frames.
7. Review every direction and every phase with the equipment enabled, including optional shield. Check grip contact, face clearance, near/far occlusion, projection, padding and settled feet. Automated layout checks cannot approve the artwork.

Implementation: `actions.js` renders held equipment; `demo.js` owns shared root motion and timing. Per-body sockets and spear projection are in `combat/*/rig.json`. The local viewer and PNG/JSON exports are a human prototype; fitting other bodies and integrating with the live game are separate work.
