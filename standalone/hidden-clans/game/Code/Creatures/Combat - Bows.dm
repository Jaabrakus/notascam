// Each direct firing command owns its callbacks. A newer command or a
// defensive shot must never inherit a retired command's sleeping timer.
datum/remaster_bow_controller
	parent_type = /datum

mob/var/tmp/datum/remaster_bow_controller/remaster_bow_controller

mob/proc/BowTarget(remaster_defensive_shot = 0, datum/remaster_bow_controller/controller = null)
	if(controller && controller != remaster_bow_controller) return
	if(remaster_defensive_shot) remaster_bow_controller = null
	// A response owns its firing cadence; retire any older repeating bow loop.
	if(!remaster_defensive_shot && istype(src, /mob/Monsters))
		var/mob/Monsters/archer = src
		if(archer.remaster_defense)
			remaster_bow_controller = null
			return
	if(!src.BowOn || !src.Target)
		src.BowOn = 0
		remaster_bow_controller = null
		return
	if(!remaster_defensive_shot && !controller)
		controller = new
		remaster_bow_controller = controller
	if(src.HoldingWeapon == "Bow")
		if(src.Meditating == 0)
			if(src.HasRightArm == 1)
				if(src.Sleeping == 0)
					if(src.Target)
						if(src.Target in oview(RmBowRangeTo(src, src.Target),src)) // Remastered: the bow's own reach, 5-8 tiles (BeastParts.dm), a tile more from higher ground (Surround.dm); the original shot 5
							if(src.HoldingWeapon == "Bow")
								for(var/obj/Items/Equipment/Armour/Quiver/LeatherQuiver/L in src)
									if(L.suffix == "(Equipped)" && L.Content >= 1)
										for(var/obj/Items/Arrows/A in L)
											RemasterNativeSound(src, 'Arrow.wav')   // the HUD plays the bow (Audio.dm)
											A.suffix = null
											A.Owner = src.Owner
											A.Target = src.Target
											src.BowSkill += 0.3
											src.GainEXP(4)
											src.destination = null
											if(src.BowSkill >= 200)
												src.BowSkill = 200
											if(istype(src, /mob/Monsters)) src:RemasterHoldNow()   // Remastered: Bow never above Attack (CombatSkills.dm)
											for(var/mob/Monsters/M in oview(RmBowRangeTo(src, src.Target),src)) // Remastered: the bow's own reach (BeastParts.dm, Surround.dm)
												if(M == src.Target)
													var/Block = 0
													var/Hit = prob(RemasterArrowHitChance(src, M)) // Remastered: Ranged against Defence (CombatSkills.dm)
													var/Deflect = 0
													var/BreakA = prob(25)
													var/LodgeA = prob(3)
													var/Damage = rand(src.WeaponDamageMin,src.WeaponDamageMax)
													Damage += src.BowSkill
													Damage += src.RmAgi() / 10
													Damage += RemasterRangedBonus(src, M) // Remastered: Ranged skill (CombatSkills.dm)
													if(!M.HumanParts) Damage = max(0, Damage * RemasterArmourShare(M)) // Remastered: a creature without body parts: its whole Defence; with them, the armour on the part hit, below (CombatSkills.dm). The original took all of the Defence off, and below 0 an arrow healed
													A.loc = M.loc
													// Notify once a real arrow is fired, including misses and blocks.
													if(HP > 0 && !GoingToDie && M.HP > 0 && !M.GoingToDie) M.RemasterThreatenedBy(src)
													if(M.HumanParts == 0)
														M.HP -= Damage / 2
														if(M.HP <= 0)
															M.GoingToDie = 1
															M.Death()
															if(!M) break
													if(M.WearingShield)
														var/BlockChance = prob(M.ShieldSkill / 2)
														if(BlockChance == 1)
															view(M) << "[M] blocks [src]'s arrow with their shield!"
															Block = 1
													if(M.WearingChest || !M.UsesEquipment && M.WearingLegs || !M.UsesEquipment)
														var/DeflectChance = prob(RemasterArmourTurn(M)) // Remastered: the Defence and Armour skills (CombatSkills.dm)
														if(DeflectChance == 1)
															Deflect = 1
															view(M) << "[M]'s armour deflects the arrow!"
													rm_shot_part = Block ? "block" : Deflect ? "deflect" : null // Remastered: what the 3D view shows the arrow do (Hits.dm)
													if(Hit == 1)
														if(Block == 0 && Deflect == 0)
															if(istype(src, /mob/Monsters)) src:RemasterCombatXP("bow", Damage) // Remastered: Ranged XP
															var/Limb = rand(1,20)
															Limb = RmArrowLimb(M, Limb, Damage)   // Remastered: a great beast's part, its wings in the air (Beasts.dm)
															Damage = max(0, Damage * RemasterPartShare(M, RmArrowRegion(Limb))) // Remastered: the armour covering the part the arrow hits (CombatSkills.dm)
															rm_shot_part = RmArrowRegion(Limb) // Remastered: the part it struck, for the 3D view (Hits.dm)
															view(M) << "[M] is hit by [src]'s arrow!"
															M.BloodContent -= Damage
															M.BloodLoss()
															if(M.ImmunePoison == 0)
																M.BloodContent -= A.PoisonContent / 5
															if(M.ImmunePoison == 1)
																M.BloodContent -= A.PoisonContent / 7
															var/Faint = 0
															if(Limb == 1)
																M.LeftLegHP -= Damage
																if(M.LeftLegHP <= 0)
																	M.HasLeftLeg  = 0
																	M.BloodContent -= 90
																	M.BloodLoss()
																	M.LeftLeg  = "Destroyed"
																	M.LimbLoss()
																	if(!M) break
																	M.LimbFling("Left Leg")
																	Faint = prob(2.5)
																	if(Faint == 1)
																		M.Fainted = 1
																		M.destination = null
																		view(src) << "<b><font color=red>[M] has fainted!"
																	M.CanWalk = 0
															if(Limb == 2)
																M.RightLegHP -= Damage
																if(M.RightLegHP <= 0)
																	M.HasRightLeg  = 0
																	M.BloodContent -= 90
																	M.BloodLoss()
																	M.RightLeg  = "Destroyed"
																	M.LimbLoss()
																	if(!M) break
																	M.LimbFling("Right Leg")
																	Faint = prob(2.5)
																	if(Faint == 1)
																		M.Fainted = 1
																		M.destination = null
																		view(src) << "<b><font color=red>[M] has fainted!"
																	M.CanWalk = 0
															if(Limb == 3)
																M.RightArmHP -= Damage
																if(M.RightArmHP <= 50)
																	M.BloodContent -= 10
																	M.BloodLoss()
																	M.RightArm  = "Slashed"
																	Faint = prob(0.1)
																	if(Faint == 1)
																		M.Fainted = 1
																		M.destination = null
																		view(src) << "<b><font color=red>[M] has fainted!"
																if(M.RightArmHP <= 0)
																	M.HasRightArm  = 0
																	M.BloodContent -= 90
																	M.BloodLoss()
																	M.RightArm  = "Destroyed"
																	M.LimbLoss()
																	if(!M) break
																	M.LimbFling("Right Arm")
																	for(var/obj/Items/Equipment/Weapon/S in M) if(M.UnEquipItem(S)) if(M.DropItem(S)) view() <<"<b><font color=red>[M]'s right arm is broken, they drop their weapon!"
																	Faint = prob(2.5)
																	if(Faint == 1)
																		M.Fainted = 1
																		M.destination = null
																		view(src) << "<b><font color=red>[M] has fainted!"
															if(Limb == 4)
																M.LeftArmHP -= Damage
																if(M.LeftArmHP <= 50)
																	M.BloodContent -= 10
																	M.BloodLoss()
																	M.LeftArm  = "Slashed"
																	Faint = prob(0.1)
																	if(Faint == 1)
																		M.Fainted = 1
																		M.destination = null
																		view(src) << "<b><font color=red>[M] has fainted!"
																if(M.LeftArmHP <= 0)
																	M.HasLeftArm  = 0
																	M.BloodContent -= 90
																	M.BloodLoss()
																	M.LeftArm  = "Destroyed"
																	M.LimbLoss()
																	if(!M) break
																	M.LimbFling("Left Arm")
																	for(var/obj/Items/Equipment/Armour/Shield/S in M) if(M.UnEquipItem(S)) if(M.DropItem(S)) view() <<"<b><font color=red>[M]'s left arm is broken, they drop their shield!"
																	Faint = prob(2.5)
																	if(Faint == 1)
																		M.Fainted = 1
																		M.destination = null
																		view(src) << "<b><font color=red>[M] has fainted!"
															if(Limb == 5 && M.HasRightEye == 1)
																M.RightEyeHP -= Damage
																M.RightEye = "Slashed"
																view(M) << "[M] is hit in the right eye by the arrow!"
																if(M.RightEyeHP <= 0)
																	M.HasRightEye = 0
																	M.RightEye = "Destroyed"
																if(M.HasRightEye == 0 && M.HasLeftEye == 0)
																	M.CanSee = 0
															if(Limb == 6 && M.HasLeftEye == 1)
																M.LeftEyeHP -= Damage
																M.LeftEye = "Slashed"
																view(M) << "[M] is hit in the left eye by the arrow!"
																if(M.LeftEyeHP <= 0)
																	M.HasLeftEye = 0
																	M.LeftEye = "Destroyed"
																if(M.HasRightEye == 0 && M.HasLeftEye == 0)
																	M.CanSee = 0
																	view(M) << "[M] is blinded!"
															if(Limb == 7)
																var/HeartShot = prob(2)
																if(HeartShot == 1 && M.Race != "Gargoyle")
																	view(M) << "[M] is shot through the heart!"   // Remastered: it falls dying, savable (Falls.dm); no longer always killed
																	M.GoingToDie = 1
																	M.Killer = "[src]"
																	if(istype(M, /mob/Monsters)) M:RmFallBy(src)   // Remastered: it falls dying, as from a blow (Falls.dm)
																	M.DeathType = "being shot in the heart with an arrow"
																	M.Death()
																	if(!M) break
															if(Limb == 8)
																var/SpleenShot = prob(40)
																if(SpleenShot == 1 && M.Race != "Gargoyle")
																	view(M) << "[M] is hit in the spleen with an arrow!"
																	M.SpleenHP -= Damage
																	M.Spleen = "Destroyed"
																	M.BloodContent -= rand(1,10)
															if(Limb == 9)
																var/LungShot = prob(25)
																if(LungShot == 1 && M.Race != "Gargoyle")
																	view(M) << "[M] is hit in the left lung with an arrow!"
																	M.LeftLungHP -= Damage
																	M.LeftLung = "Damaged"
																	M.BloodContent -= rand(1,10)
																	if(M.LeftLungHP <= 0)
																		M.LeftLung = "Destroyed"
																		M.HasLeftLung = 0
																	if(M.HasLeftLung == 0 && M.HasRightLung == 0)
																		M.GoingToDie = 1
																		M.Killer = "[src]"
																		if(istype(M, /mob/Monsters)) M:RmFallBy(src)   // Remastered: it falls dying, as from a blow (Falls.dm)
																		M.DeathType = "being shot in the lungs with arrows"
																		M.Death()
																		if(!M) break
															if(Limb == 10)
																var/LungShot = prob(25)
																if(LungShot == 1 && M.Race != "Gargoyle")
																	view(M) << "[M] is hit in the left lung with an arrow!"
																	M.RightLungHP -= Damage
																	M.RightLung = "Damaged"
																	M.BloodContent -= rand(1,10)
																	if(M.RightLungHP <= 0)
																		M.RightLung = "Destroyed"
																		M.HasRightLung = 0
																	if(M.HasLeftLung == 0 && M.HasRightLung == 0)
																		M.GoingToDie = 1
																		M.Killer = "[src]"
																		if(istype(M, /mob/Monsters)) M:RmFallBy(src)   // Remastered: it falls dying, as from a blow (Falls.dm)
																		M.DeathType = "being shot in the lungs with arrows"
																		M.Death()
																		if(!M) break
															if(LodgeA == 1)
																view(M) << "<b><font color=red>[A] lodges itself into [M]<br>"
																A.loc = M
																M.weight += A.weight
																A.suffix = "(Stuck In)"
															if(BreakA == 1 && LodgeA == 0)
																del A
																break
															break
														break

													else
														view(src) << "[src] fires an arrow but misses its target!"
														break
											L.Content -= 1
											break
									break
						else
							src.Target = null
							src.BowOn = 0
			else
				src.BowOn = 0
				return
		else
			src.BowOn = 0
			src.Target = null
			return
	else
		src.BowOn = 0
		return
	if(src.BowOn && !remaster_defensive_shot)
		spawn(50)
			if(src && controller == remaster_bow_controller) BowTarget(0, controller)
	else if(controller == remaster_bow_controller)
		remaster_bow_controller = null
