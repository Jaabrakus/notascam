// NPC and starting kits make their armour by its material, as a player's own is made (Remastered; the user, 2026-10-26:
// "Do it now"). The original's CraftItem ("1 - Item Making.dm", for NPCs only) ran every armour piece through
// MetalArmourCraft, so a raider's or a new army's leather, bone, wood, gold or silver had metal's Defence (Quality 12,
// Legendary 17), where the same piece made by a player gets the bone rule (Quality 7, Legendary 12) and a bonus: wood +4,
// gold and silver +1 (Code/Items/CraftingStations.dm, which this list is read from). Metal, adamantium and the pieces
// players can't make (Dragoon, Skorn, robes...) keep what they had.

var/rm_kit_material = 1   // 0: the original's, metal Defence for every NPC piece

var/list/rm_kit_bone_armour = list(
	/obj/Items/Equipment/Armour/Capes/BlackCape = 0,
	/obj/Items/Equipment/Armour/Capes/RedCape = 0,
	/obj/Items/Equipment/Armour/Capes/WhiteCape = 0,
	/obj/Items/Equipment/Armour/Chestplate/BoneChestPlate = 0,
	/obj/Items/Equipment/Armour/Chestplate/EmeraldGoldChestPlate = 1,
	/obj/Items/Equipment/Armour/Chestplate/EmeraldSilverChestPlate = 1,
	/obj/Items/Equipment/Armour/Chestplate/GoldChestPlate = 1,
	/obj/Items/Equipment/Armour/Chestplate/LeatherChestPlate = 0,
	/obj/Items/Equipment/Armour/Chestplate/RubyGoldChestPlate = 1,
	/obj/Items/Equipment/Armour/Chestplate/RubySilverChestPlate = 1,
	/obj/Items/Equipment/Armour/Chestplate/SilverChestPlate = 1,
	/obj/Items/Equipment/Armour/Chestplate/WoodenChestplate = 4,
	/obj/Items/Equipment/Armour/Helmet/BlackHood = 0,
	/obj/Items/Equipment/Armour/Helmet/BoneHelmet = 0,
	/obj/Items/Equipment/Armour/Helmet/DiamondGoldHelmet = 1,
	/obj/Items/Equipment/Armour/Helmet/EmeraldGoldHelmet = 1,
	/obj/Items/Equipment/Armour/Helmet/GoldHelmet = 1,
	/obj/Items/Equipment/Armour/Helmet/LeatherHelmet = 0,
	/obj/Items/Equipment/Armour/Helmet/RedHat = 0,
	/obj/Items/Equipment/Armour/Helmet/RubyGoldHelmet = 1,
	/obj/Items/Equipment/Armour/Helmet/SilverHelmet = 1,
	/obj/Items/Equipment/Armour/Helmet/WhiteHood = 0,
	/obj/Items/Equipment/Armour/Helmet/WoodenHelmet = 4,
	/obj/Items/Equipment/Armour/LeftArm/BoneLeftGauntlet = 0,
	/obj/Items/Equipment/Armour/LeftArm/GoldLeftGauntlet = 1,
	/obj/Items/Equipment/Armour/LeftArm/LeatherLeftGauntlet = 0,
	/obj/Items/Equipment/Armour/LeftArm/SilverLeftGauntlet = 1,
	/obj/Items/Equipment/Armour/LeftArm/WoodenLeftGauntlet = 4,
	/obj/Items/Equipment/Armour/Leggings/BoneLeggings = 0,
	/obj/Items/Equipment/Armour/Leggings/EmeraldGoldLeggings = 1,
	/obj/Items/Equipment/Armour/Leggings/EmeraldSilverLeggings = 1,
	/obj/Items/Equipment/Armour/Leggings/GoldLeggings = 1,
	/obj/Items/Equipment/Armour/Leggings/LeatherLeggings = 0,
	/obj/Items/Equipment/Armour/Leggings/RubyGoldLeggings = 1,
	/obj/Items/Equipment/Armour/Leggings/RubySilverLeggings = 1,
	/obj/Items/Equipment/Armour/Leggings/SilverLeggings = 1,
	/obj/Items/Equipment/Armour/Leggings/WoodenLeggings = 4,
	/obj/Items/Equipment/Armour/RightArm/BoneRightGauntlet = 0,
	/obj/Items/Equipment/Armour/RightArm/GoldRightGauntlet = 1,
	/obj/Items/Equipment/Armour/RightArm/LeatherRightGauntlet = 0,
	/obj/Items/Equipment/Armour/RightArm/SilverRightGauntlet = 1,
	/obj/Items/Equipment/Armour/RightArm/WoodenRightGauntlet = 4,
	/obj/Items/Equipment/Armour/Shield/BoneBuckler = 0,
	/obj/Items/Equipment/Armour/Shield/GoldBuckler = 1,
	/obj/Items/Equipment/Armour/Shield/SilverBuckler = 1,
	/obj/Items/Equipment/Armour/Shield/WoodenBuckler = 4)

mob/CraftItem(obj/Items/A1, RANK)
	var/n = A1 ? A1.name : null
	. = ..()
	if(!rm_kit_material || !istype(A1, /obj/Items/Equipment/Armour) || !(A1.type in rm_kit_bone_armour)) return
	A1.name = n   // BoneArmourCraft names it again
	A1.BoneArmourCraft()
	A1.Defence += rm_kit_bone_armour[A1.type]
