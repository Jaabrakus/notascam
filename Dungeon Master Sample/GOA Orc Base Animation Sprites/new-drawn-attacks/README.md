# Newly drawn Orc attack drafts

Generated with the built-in image tool. These are drawing reviews, not registered native game atlases. Original in-game Orc remains the chosen master; the generated artwork still requires native-pixel cleanup and continuity checks.

Each sheet has columns South, North, East, West; rows guard, windup/chamber, impact, recovery. Left/right always means the character's anatomical side.

- `punch-left-draft-v2.png`: left punch draft; the North impact still incorrectly uses the right shoulder and must be corrected.
- `punch-right-draft-v2.png`: right punch counterpart.
- `kick-left-draft-v1.png`: left kick draft; South impact still extends sideways and needs the approved front-kick foreshortening.
- `kick-right-draft-v2.png`: right kick counterpart, with the right leg raised on screen left in South and screen right in North.

The user's approved front kick is saved at `references/user-approved-front-kick.png`. Preserve the guard → raised knee → forward-facing sole → recovery motion. Short legs, body-only artwork, separate equipment/shields/effects remain required.

Prompts are preserved alongside the PNGs. `right_punch-v2-prompt.txt` and `right_kick-v2-prompt.txt` specify the new right-side drawings and the near/far limb overlap. Generated requests to preserve pixels are not proof of identical pixels; none of these sheets is certified pixel-locked.

Open `index.html` for a static review that works without a server. It does not change or filter the PNG files.
