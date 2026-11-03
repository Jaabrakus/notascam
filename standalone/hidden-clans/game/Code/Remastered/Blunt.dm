// Blunt blows end fights (Remastered; the user, 2026-10-25: "bare fist should end why wouldnt they?"; launch audit
// blocker 2). The original's body-part code (Combats.dm Attack) lets a blunt blow (fists, a mace, a staff) take an arm,
// leg, wing or organ down to 10 health ("Mangled") and no further, and never touches HP. So a fist fight ended only by
// a rare head blow or slow blood loss: in the pace arena most were still going after 6 minutes, every part mangled,
// HP full. Now whatever the parts a blunt blow lands on can't take (already crushed, or gone) comes off HP, the same
// armour taken off first; at 0 the unit is beaten to death. Bare fists knock out first: at about a third of its health
// (Subdue.dm RM_KO_MARK) the loser is out cold for 30 s and can be captured, or finished. Measured with
// tests/fists_test.dm (tools/check_arena.py).

var/rm_blunt_mode = 2     // 0: the original's; 1: what the parts can't take comes off HP, death at 0; 2: as 1, bare fists knock out first

mob/var/tmp/rm_blunt_dmg = 0
mob/var/tmp/list/rm_blunt_parts   // the parts a blunt blow lands on, after the defender's deflections (CheckDefence)

// Attack rolls where the blow lands, hands the blow's damage here, then the defender deflects some (CheckDefence).
mob/RmAimFlags(mob/Monsters/M, dmg)
	. = ..()
	rm_blunt_dmg = dmg

mob/CheckDefence()
	. = ..()
	rm_blunt_parts = null
	if(!rm_blunt_mode || DamageType != "Blunt") return
	var/list/L = list()
	if(HitHead) L += "Head"
	if(HitLeftArm) L += "LeftArm"
	if(HitRightArm) L += "RightArm"
	if(HitLeftLeg) L += "LeftLeg"
	if(HitRightLeg) L += "RightLeg"
	if(HitUpperBody) L += "UpperBody"
	if(HitLowerBody) L += "LowerBody"
	if(HitWings) L += "Wings"
	if(length(L)) rm_blunt_parts = L

// mob/RemasterStrike: this file's part is step RmChainStrike_Blunt in Code/Remastered/Chains/Strike.dm
