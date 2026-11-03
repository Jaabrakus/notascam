# Every item in the game

Made by `python3 art/items/list_items.py` from the compiled game (2026-10-28 16:03). Run it again after a build.

**792 kinds:** 375 from the gear catalogue (art/enhance/catalogue.json), 386 from the item catalogue (art/items/catalogue.json), 29 written in the 2006 files and 2 hand-written for Remastered. 0 could be adopted into the item catalogue as they are.

- **From:** where its values are written. A catalogue row, or the 2006 or Remastered code (file and line).
- **Own code:** what it does that others of its group don't (its own procs). Adopting never moves code.
- **Made by:** the code that creates it (a workshop's menu, mining, a spell...).
- **Adopt:** yes, if its values are a plain block that can move into a catalogue row, keeping its type name.
  Otherwise, why not.

| Group | Kinds | Gear rows | Item rows | 2006 | Remastered | Can adopt |
|---|---|---|---|---|---|---|
| [Equipment](#equipment) | 585 | 375 | 203 | 7 | 0 | 0 |
| [Furniture](#furniture) | 51 | 0 | 45 | 6 | 0 | 0 |
| [Shafts](#shafts) | 17 | 0 | 16 | 1 | 0 | 0 |
| [Traps](#traps) | 15 | 0 | 13 | 2 | 0 | 0 |
| [Bones](#bones) | 14 | 0 | 13 | 1 | 0 | 0 |
| [gems](#gems) | 11 | 0 | 10 | 1 | 0 | 0 |
| [Potions](#potions) | 8 | 0 | 7 | 1 | 0 | 0 |
| [Plants](#plants) | 8 | 0 | 8 | 0 | 0 | 0 |
| [Seeds](#seeds) | 8 | 0 | 7 | 1 | 0 | 0 |
| [ores](#ores) | 7 | 0 | 6 | 1 | 0 | 0 |
| [Food](#food) | 7 | 0 | 6 | 1 | 0 | 0 |
| [RemasterTools](#remastertools) | 7 | 0 | 7 | 0 | 0 | 0 |
| [Ingots](#ingots) | 5 | 0 | 4 | 1 | 0 | 0 |
| [Arrows](#arrows) | 5 | 0 | 4 | 1 | 0 | 0 |
| [Glands](#glands) | 5 | 0 | 4 | 1 | 0 | 0 |
| [Poisons](#poisons) | 4 | 0 | 3 | 1 | 0 | 0 |
| [RemasterHerb](#remasterherb) | 4 | 0 | 4 | 0 | 0 | 0 |
| [RemasterRemedy](#remasterremedy) | 4 | 0 | 4 | 0 | 0 | 0 |
| [RemasterRope](#remasterrope) | 4 | 0 | 4 | 0 | 0 | 0 |
| [Graves](#graves) | 3 | 0 | 2 | 1 | 0 | 0 |
| [woods](#woods) | 3 | 0 | 2 | 1 | 0 | 0 |
| [Thrown](#thrown) | 3 | 0 | 2 | 0 | 1 | 0 |
| [RemasterBandage](#remasterbandage) | 3 | 0 | 3 | 0 | 0 | 0 |
| [Skin](#skin) | 2 | 0 | 2 | 0 | 0 | 0 |
| [Silks](#silks) | 2 | 0 | 1 | 1 | 0 | 0 |
| [RemasterSalt](#remastersalt) | 1 | 0 | 1 | 0 | 0 | 0 |
| [RemasterLimb](#remasterlimb) | 1 | 0 | 1 | 0 | 0 | 0 |
| [RemasterSoulStone](#remastersoulstone) | 1 | 0 | 1 | 0 | 0 | 0 |
| [RmBeastEgg](#rmbeastegg) | 1 | 0 | 1 | 0 | 0 | 0 |
| [RemasterStake](#remasterstake) | 1 | 0 | 1 | 0 | 0 | 0 |
| [RmRuneStone](#rmrunestone) | 1 | 0 | 1 | 0 | 0 | 0 |
| [RemasterTorch](#remastertorch) | 1 | 0 | 0 | 0 | 1 | 0 |

## Equipment

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Equipment *(group of 2)* | Equipment |  | 0 |  | 2006 (:None) | DblClick, RemasterUseCarried | Chieftain › New, Chieftain › New, Commander › New +31 | no values of its own |
| Armour *(group of 10)* | Equipment/Armour |  | 0 |  | 2006 (Items/Equipment Lists.dm:155) |  |  | no values of its own |
| Capes *(group of 6)* | Equipment/Armour/Capes |  | 10 |  | item row |  |  | already a row |
| AstralCape | Equipment/Armour/Capes/AstralCape | Robe.dmi: AstralCape | 10 |  | item row |  |  | already a row |
| BlackCape | Equipment/Armour/Capes/BlackCape | Robe.dmi: BlackCape | 10 |  | item row |  | LeatherWorks › DblClick | already a row |
| ChaosCape | Equipment/Armour/Capes/ChaosCape | Robe.dmi: ChaosCape | 10 |  | item row |  |  | already a row |
| NecroCape | Equipment/Armour/Capes/NecroCape | Robe.dmi: NecroCape | 10 |  | item row |  |  | already a row |
| RedCape | Equipment/Armour/Capes/RedCape | Robe.dmi: RedCape | 10 |  | item row |  | LeatherWorks › DblClick | already a row |
| WhiteCape | Equipment/Armour/Capes/WhiteCape | Robe.dmi: WhiteCape | 10 |  | item row |  | LeatherWorks › DblClick | already a row |
| Chestplate *(group of 100)* | Equipment/Armour/Chestplate |  | 0 |  | item row |  |  | already a row |
| AdamantiumChestPlate | Equipment/Armour/Chestplate/AdamantiumChestPlate | MetalObjects.dmi: Adamantium ChestPlate | 0 |  | item row |  | Forge › DblClick | already a row |
| Astral Robe | Equipment/Armour/Chestplate/AstralRobe | Robe.dmi: AstralRobe | 5 |  | item row |  |  | already a row |
| Black Trenchcoat | Equipment/Armour/Chestplate/BlackCoat | MetalObjects.dmi: BlackCoat | 5 |  | item row |  |  | already a row |
| Magician's Robe | Equipment/Armour/Chestplate/BlackRobe | Robe.dmi: BlackRobe | 5 |  | item row |  | LeatherWorks › DblClick | already a row |
| BoneChestPlate | Equipment/Armour/Chestplate/BoneChestPlate | BoneItems.dmi: Bone ChestPlate | 10 |  | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick, MiscCreate › FullBoneLegendary | already a row |
| Chaos Robe | Equipment/Armour/Chestplate/ChaosRobe | Robe.dmi: ChaosRobe | 5 |  | item row |  |  | already a row |
| ChitinChestPlate | Equipment/Armour/Chestplate/ChitinChestPlate | BoneItems.dmi: ChitinChestPlate | 10 |  | item row |  | BoneCraft › DblClick | already a row |
| Demon Leather Top | Equipment/Armour/Chestplate/DemonLeatherChestPlate | LeatherItems.dmi: Demon Leather ChestPlate | 5 |  | item row |  | LeatherWorks › DblClick | already a row |
| DiamondGoldChestPlate | Equipment/Armour/Chestplate/DiamondGoldChestPlate | GemItems.dmi: GoldChestDiamond | 30 |  | item row |  | Forge › DblClick | already a row |
| DiamondMetalChestPlate | Equipment/Armour/Chestplate/DiamondMetalChestPlate | GemItems.dmi: MetalChestDiamond | 30 |  | item row |  | Forge › DblClick | already a row |
| DiamondSilverChestPlate | Equipment/Armour/Chestplate/DiamondSilverChestPlate | GemItems.dmi: SilverChestDiamond | 30 |  | item row |  | Forge › DblClick | already a row |
| Dragoon Chest Plate | Equipment/Armour/Chestplate/DragoonChestPlate | TrimmedMetal.dmi: Gold Trimmed Chestplate | 30 |  | item row |  |  | already a row |
| EmeraldGoldChestPlate | Equipment/Armour/Chestplate/EmeraldGoldChestPlate | GemItems.dmi: GoldChestEmerald | 30 |  | item row |  | Forge › DblClick | already a row |
| EmeraldMetalChestPlate | Equipment/Armour/Chestplate/EmeraldMetalChestPlate | GemItems.dmi: MetalChestEmerald | 30 |  | item row |  | Forge › DblClick | already a row |
| EmeraldSilverChestPlate | Equipment/Armour/Chestplate/EmeraldSilverChestPlate | GemItems.dmi: SilverChestEmerald | 30 |  | item row |  | Forge › DblClick | already a row |
| GladiatorMetalChestPlate | Equipment/Armour/Chestplate/GladiatorMetalChestPlate | MetalObjects.dmi: Bronze ChestPlate | 30 |  | item row |  |  | already a row |
| GoldChestPlate | Equipment/Armour/Chestplate/GoldChestPlate | GoldItems.dmi: Gold ChestPlate | 30 |  | item row |  | Forge › DblClick | already a row |
| Leather Top | Equipment/Armour/Chestplate/LeatherChestPlate | LeatherItems.dmi: Leather ChestPlate | 5 |  | item row |  | LeatherWorks › DblClick | already a row |
| MetalChestPlate | Equipment/Armour/Chestplate/MetalChestPlate | MetalObjects.dmi: Metal ChestPlate | 30 |  | item row |  | Forge › DblClick, MiscCreate › FullMetalLegendary | already a row |
| Necromancer's Robe | Equipment/Armour/Chestplate/NecroRobe | Robe.dmi: NecroRobe | 5 |  | item row |  |  | already a row |
| Magician's Robe | Equipment/Armour/Chestplate/RedRobe | Robe.dmi: RedRobe | 5 |  | item row |  | LeatherWorks › DblClick | already a row |
| RubyGoldChestPlate | Equipment/Armour/Chestplate/RubyGoldChestPlate | GemItems.dmi: GoldChestRuby | 35 |  | item row |  | Forge › DblClick | already a row |
| RubyMetalChestPlate | Equipment/Armour/Chestplate/RubyMetalChestPlate | GemItems.dmi: MetalChestRuby | 35 |  | item row |  | Forge › DblClick | already a row |
| RubySilverChestPlate | Equipment/Armour/Chestplate/RubySilverChestPlate | GemItems.dmi: SilverChestRuby | 35 |  | item row |  | Forge › DblClick | already a row |
| SilverChestPlate | Equipment/Armour/Chestplate/SilverChestPlate | SilverItems.dmi: Silver ChestPlate | 30 |  | item row |  | Forge › DblClick | already a row |
| Skorn ChestPlate | Equipment/Armour/Chestplate/SkornChestPlate | SkornArmour.dmi: SChest | 10 |  | item row |  |  | already a row |
| SupernaturalBoneChestPlate | Equipment/Armour/Chestplate/SupernaturalBoneChestPlate | Superbone.dmi: chest | 10 |  | item row |  | BoneCraft › DblClick | already a row |
| Priest's Robe | Equipment/Armour/Chestplate/WhiteRobe | Robe.dmi: WhiteRobe | 5 |  | item row |  | LeatherWorks › DblClick | already a row |
| WoodenChestplate | Equipment/Armour/Chestplate/WoodenChestplate | WoodItems.dmi: Wooden ChestPlate | 5 |  | item row |  | Carpentry › DblClick | already a row |
| Adamantium Banded Mail | Equipment/Armour/Chestplate/rm_chest_banded_adamantium | adamantium.dmi: chest.banded.adamantium | 32 | armour | gear row |  |  | already a row |
| Diamond Banded Mail | Equipment/Armour/Chestplate/rm_chest_banded_diamond | diamond.dmi: chest.banded.diamond | 40 | armour | gear row |  |  | already a row |
| Gold Banded Mail | Equipment/Armour/Chestplate/rm_chest_banded_gold | gold.dmi: chest.banded.gold | 52 | armour | gear row |  |  | already a row |
| Hellforged Banded Mail | Equipment/Armour/Chestplate/rm_chest_banded_hell | hell.dmi: chest.banded.hell | 44 | armour | gear row |  |  | already a row |
| Iron Banded Mail | Equipment/Armour/Chestplate/rm_chest_banded_iron | iron.dmi: chest.banded.iron | 40 | armour | gear row |  |  | already a row |
| Silver Banded Mail | Equipment/Armour/Chestplate/rm_chest_banded_silver | silver.dmi: chest.banded.silver | 40 | armour | gear row |  |  | already a row |
| Adamantium Brigandine | Equipment/Armour/Chestplate/rm_chest_brigandine_adamantium | adamantium.dmi: chest.brigandine.adamantium | 18 | armour | gear row |  |  | already a row |
| Diamond Brigandine | Equipment/Armour/Chestplate/rm_chest_brigandine_diamond | diamond.dmi: chest.brigandine.diamond | 22 | armour | gear row |  |  | already a row |
| Gold Brigandine | Equipment/Armour/Chestplate/rm_chest_brigandine_gold | gold.dmi: chest.brigandine.gold | 29 | armour | gear row |  |  | already a row |
| Hellforged Brigandine | Equipment/Armour/Chestplate/rm_chest_brigandine_hell | hell.dmi: chest.brigandine.hell | 24 | armour | gear row |  |  | already a row |
| Iron Brigandine | Equipment/Armour/Chestplate/rm_chest_brigandine_iron | iron.dmi: chest.brigandine.iron | 22 | armour | gear row |  |  | already a row |
| Silver Brigandine | Equipment/Armour/Chestplate/rm_chest_brigandine_silver | silver.dmi: chest.brigandine.silver | 22 | armour | gear row |  |  | already a row |
| Adamantium Lamellar Coat | Equipment/Armour/Chestplate/rm_chest_lamellar_adamantium | adamantium.dmi: chest.lamellar.adamantium | 22 | armour | gear row |  |  | already a row |
| Bone Lamellar Coat | Equipment/Armour/Chestplate/rm_chest_lamellar_bone | bone.dmi: chest.lamellar.bone | 22 | armour | gear row |  |  | already a row |
| Chitin Lamellar Coat | Equipment/Armour/Chestplate/rm_chest_lamellar_chitin | chitin.dmi: chest.lamellar.chitin | 20 | armour | gear row |  |  | already a row |
| Diamond Lamellar Coat | Equipment/Armour/Chestplate/rm_chest_lamellar_diamond | diamond.dmi: chest.lamellar.diamond | 28 | armour | gear row |  |  | already a row |
| Dragonscale Coat | Equipment/Armour/Chestplate/rm_chest_lamellar_dragon | dragon.dmi: chest.lamellar.dragon | 20 | armour | gear row |  |  | already a row |
| Dragonbone Lamellar | Equipment/Armour/Chestplate/rm_chest_lamellar_dragonbone | dragonbone.dmi: chest.lamellar.dragonbone | 24 | armour | gear row |  |  | already a row |
| Gold Lamellar Coat | Equipment/Armour/Chestplate/rm_chest_lamellar_gold | gold.dmi: chest.lamellar.gold | 36 | armour | gear row |  |  | already a row |
| Hellforged Lamellar Coat | Equipment/Armour/Chestplate/rm_chest_lamellar_hell | hell.dmi: chest.lamellar.hell | 31 | armour | gear row |  |  | already a row |
| Iron Lamellar Coat | Equipment/Armour/Chestplate/rm_chest_lamellar_iron | iron.dmi: chest.lamellar.iron | 28 | armour | gear row |  |  | already a row |
| Silver Lamellar Coat | Equipment/Armour/Chestplate/rm_chest_lamellar_silver | silver.dmi: chest.lamellar.silver | 28 | armour | gear row |  |  | already a row |
| Bonehide Jerkin | Equipment/Armour/Chestplate/rm_chest_leather_bonehide | bonehide.dmi: chest.leather.bonehide | 4 | armour | gear row |  |  | already a row |
| Dragonhide Jerkin | Equipment/Armour/Chestplate/rm_chest_leather_dragonhide | dragonhide.dmi: chest.leather.dragonhide | 4 | armour | gear row |  |  | already a row |
| Studded Leather Jerkin | Equipment/Armour/Chestplate/rm_chest_leather_leather | leather.dmi: chest.leather.leather | 4 | armour | gear row |  |  | already a row |
| Spidersilk Jerkin | Equipment/Armour/Chestplate/rm_chest_leather_spidersilk | spidersilk.dmi: chest.leather.spidersilk | 4 | armour | gear row |  |  | already a row |
| Adamantium Chainmail | Equipment/Armour/Chestplate/rm_chest_mail_adamantium | adamantium.dmi: chest.mail.adamantium | 20 | armour | gear row |  |  | already a row |
| Diamond Chainmail | Equipment/Armour/Chestplate/rm_chest_mail_diamond | diamond.dmi: chest.mail.diamond | 25 | armour | gear row |  |  | already a row |
| Gold Chainmail | Equipment/Armour/Chestplate/rm_chest_mail_gold | gold.dmi: chest.mail.gold | 32 | armour | gear row |  |  | already a row |
| Hellforged Chainmail | Equipment/Armour/Chestplate/rm_chest_mail_hell | hell.dmi: chest.mail.hell | 28 | armour | gear row |  |  | already a row |
| Iron Chainmail | Equipment/Armour/Chestplate/rm_chest_mail_iron | iron.dmi: chest.mail.iron | 25 | armour | gear row |  |  | already a row |
| Silver Chainmail | Equipment/Armour/Chestplate/rm_chest_mail_silver | silver.dmi: chest.mail.silver | 25 | armour | gear row |  |  | already a row |
| Adamantium Breastplate | Equipment/Armour/Chestplate/rm_chest_plate_adamantium | adamantium.dmi: chest.plate.adamantium | 28 | armour | gear row |  |  | already a row |
| Bone Breastplate | Equipment/Armour/Chestplate/rm_chest_plate_bone | bone.dmi: chest.plate.bone | 28 | armour | gear row |  |  | already a row |
| Chitin Breastplate | Equipment/Armour/Chestplate/rm_chest_plate_chitin | chitin.dmi: chest.plate.chitin | 24 | armour | gear row |  |  | already a row |
| Diamond Breastplate | Equipment/Armour/Chestplate/rm_chest_plate_diamond | diamond.dmi: chest.plate.diamond | 35 | armour | gear row |  |  | already a row |
| Dragonscale Breastplate | Equipment/Armour/Chestplate/rm_chest_plate_dragon | dragon.dmi: chest.plate.dragon | 24 | armour | gear row |  |  | already a row |
| Dragonbone Cuirass | Equipment/Armour/Chestplate/rm_chest_plate_dragonbone | dragonbone.dmi: chest.plate.dragonbone | 30 | armour | gear row |  |  | already a row |
| Gold Breastplate | Equipment/Armour/Chestplate/rm_chest_plate_gold | gold.dmi: chest.plate.gold | 46 | armour | gear row |  |  | already a row |
| Hellforged Breastplate | Equipment/Armour/Chestplate/rm_chest_plate_hell | hell.dmi: chest.plate.hell | 38 | armour | gear row |  |  | already a row |
| Iron Breastplate | Equipment/Armour/Chestplate/rm_chest_plate_iron | iron.dmi: chest.plate.iron | 35 | armour | gear row |  |  | already a row |
| Silver Breastplate | Equipment/Armour/Chestplate/rm_chest_plate_silver | silver.dmi: chest.plate.silver | 35 | armour | gear row |  |  | already a row |
| Wooden Chestplate | Equipment/Armour/Chestplate/rm_chest_plate_wood | wood.dmi: chest.plate.wood | 18 | armour | gear row |  |  | already a row |
| Black Robe | Equipment/Armour/Chestplate/rm_chest_robe_black | cloth.dmi: chest.robe.black | 5 | armour | gear row |  |  | already a row |
| Astral Robe | Equipment/Armour/Chestplate/rm_chest_robe_blue | cloth.dmi: chest.robe.blue | 5 | armour | gear row |  |  | already a row |
| Dragonbone Robe | Equipment/Armour/Chestplate/rm_chest_robe_bonerobe | cloth.dmi: chest.robe.bonerobe | 5 | armour | gear row |  |  | already a row |
| Plain Robe | Equipment/Armour/Chestplate/rm_chest_robe_brown | cloth.dmi: chest.robe.brown | 5 | armour | gear row |  |  | already a row |
| Robe of Flames | Equipment/Armour/Chestplate/rm_chest_robe_crimson | cloth.dmi: chest.robe.crimson | 5 | armour | gear row |  |  | already a row |
| Dragonscale Robe | Equipment/Armour/Chestplate/rm_chest_robe_dragonrobe | cloth.dmi: chest.robe.dragonrobe | 5 | armour | gear row |  |  | already a row |
| Priest's Robe | Equipment/Armour/Chestplate/rm_chest_robe_gold | gold.dmi: chest.robe.gold | 5 | armour | gear row |  |  | already a row |
| Druid's Robe | Equipment/Armour/Chestplate/rm_chest_robe_green | cloth.dmi: chest.robe.green | 5 | armour | gear row |  |  | already a row |
| Necromancer's Robe | Equipment/Armour/Chestplate/rm_chest_robe_grey | cloth.dmi: chest.robe.grey | 5 | armour | gear row |  |  | already a row |
| Chaos Robe | Equipment/Armour/Chestplate/rm_chest_robe_purple | cloth.dmi: chest.robe.purple | 5 | armour | gear row |  |  | already a row |
| Red Robe | Equipment/Armour/Chestplate/rm_chest_robe_red | cloth.dmi: chest.robe.red | 5 | armour | gear row |  |  | already a row |
| Spider Silk Robe | Equipment/Armour/Chestplate/rm_chest_robe_spiderrobe | cloth.dmi: chest.robe.spiderrobe | 5 | armour | gear row |  |  | already a row |
| White Robe | Equipment/Armour/Chestplate/rm_chest_robe_white | cloth.dmi: chest.robe.white | 5 | armour | gear row |  |  | already a row |
| Adamantium Scale Hauberk | Equipment/Armour/Chestplate/rm_chest_scale_adamantium | adamantium.dmi: chest.scale.adamantium | 24 | armour | gear row |  |  | already a row |
| Bone Scale Hauberk | Equipment/Armour/Chestplate/rm_chest_scale_bone | bone.dmi: chest.scale.bone | 24 | armour | gear row |  |  | already a row |
| Chitin Scale Hauberk | Equipment/Armour/Chestplate/rm_chest_scale_chitin | chitin.dmi: chest.scale.chitin | 21 | armour | gear row |  |  | already a row |
| Diamond Scale Hauberk | Equipment/Armour/Chestplate/rm_chest_scale_diamond | diamond.dmi: chest.scale.diamond | 30 | armour | gear row |  |  | already a row |
| Dragonscale Hauberk | Equipment/Armour/Chestplate/rm_chest_scale_dragon | dragon.dmi: chest.scale.dragon | 21 | armour | gear row |  |  | already a row |
| Gold Scale Hauberk | Equipment/Armour/Chestplate/rm_chest_scale_gold | gold.dmi: chest.scale.gold | 39 | armour | gear row |  |  | already a row |
| Hellforged Scale Hauberk | Equipment/Armour/Chestplate/rm_chest_scale_hell | hell.dmi: chest.scale.hell | 33 | armour | gear row |  |  | already a row |
| Iron Scale Hauberk | Equipment/Armour/Chestplate/rm_chest_scale_iron | iron.dmi: chest.scale.iron | 30 | armour | gear row |  |  | already a row |
| Silver Scale Hauberk | Equipment/Armour/Chestplate/rm_chest_scale_silver | silver.dmi: chest.scale.silver | 30 | armour | gear row |  |  | already a row |
| Adamantium Mail and Tabard | Equipment/Armour/Chestplate/rm_chest_tabard_adamantium | adamantium.dmi: chest.tabard.adamantium | 21 | armour | gear row |  |  | already a row |
| Diamond Mail and Tabard | Equipment/Armour/Chestplate/rm_chest_tabard_diamond | diamond.dmi: chest.tabard.diamond | 26 | armour | gear row |  |  | already a row |
| Gold Mail and Tabard | Equipment/Armour/Chestplate/rm_chest_tabard_gold | gold.dmi: chest.tabard.gold | 34 | armour | gear row |  |  | already a row |
| Hellforged Mail and Tabard | Equipment/Armour/Chestplate/rm_chest_tabard_hell | hell.dmi: chest.tabard.hell | 29 | armour | gear row |  |  | already a row |
| Iron Mail and Tabard | Equipment/Armour/Chestplate/rm_chest_tabard_iron | iron.dmi: chest.tabard.iron | 26 | armour | gear row |  |  | already a row |
| Silver Mail and Tabard | Equipment/Armour/Chestplate/rm_chest_tabard_silver | silver.dmi: chest.tabard.silver | 26 | armour | gear row |  |  | already a row |
| Crown *(group of 9)* | Equipment/Armour/Crown |  | 0 |  | item row | Del, DeleteItem, New |  | already a row |
| Bone Crown | Equipment/Armour/Crown/Bone | RoyalItems.dmi: BoneCrown | 5 |  | 2006 (Items/Crowning.dm:3) |  | BoneCraft › DblClick | values in Code/Items/Crowning.dm, Code/Remastered/Rulership.dm |
| Gold Crown | Equipment/Armour/Crown/Gold | GoldItems.dmi: Crown | 10 |  | 2006 (Items/Crowning.dm:11) |  | Forge › DblClick | values in Code/Items/Crowning.dm, Code/Remastered/Rulership.dm |
| Chain of Office | Equipment/Armour/Crown/RmChain | Regalia.dmi: chain | 6 |  | item row |  |  | already a row |
| Heir's Band | Equipment/Armour/Crown/RmHeirBand | Regalia.dmi: heirband | 2 |  | item row |  |  | already a row |
| Heir's Circlet | Equipment/Armour/Crown/RmHeirCirclet | Regalia.dmi: heircirclet | 2 |  | item row |  |  | already a row |
| Silver Circlet | Equipment/Armour/Crown/RmSilverCirclet | Regalia.dmi: silvercirclet | 4 |  | item row |  |  | already a row |
| Elder's Staff | Equipment/Armour/Crown/RmStaff | Regalia.dmi: staff | 5 |  | item row |  |  | already a row |
| Chief's Totem | Equipment/Armour/Crown/RmTotem | Regalia.dmi: totem | 4 |  | item row |  |  | already a row |
| Helmet *(group of 81)* | Equipment/Armour/Helmet |  | 0 |  | item row |  |  | already a row |
| AdamantiumHelmet | Equipment/Armour/Helmet/AdamantiumHelmet | MetalObjects.dmi: Adamantium Helmet | 0 |  | item row |  | Forge › DblClick | already a row |
| AstralHat | Equipment/Armour/Helmet/AstralHat | Robe.dmi: AstralHat | 10 |  | item row |  |  | already a row |
| BlackHood | Equipment/Armour/Helmet/BlackHood | Robe.dmi: BlackHood | 10 |  | item row |  | LeatherWorks › DblClick | already a row |
| BoneHelmet | Equipment/Armour/Helmet/BoneHelmet | Cave.dmi: Bone Helmet | 10 |  | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick, MiscCreate › FullBoneLegendary | already a row |
| ChaosHood | Equipment/Armour/Helmet/ChaosHood | Robe.dmi: ChaosHood | 10 |  | item row |  |  | already a row |
| ChitinHelmet | Equipment/Armour/Helmet/ChitinHelmet | BoneItems.dmi: ChitinHelmet | 10 |  | item row |  | BoneCraft › DblClick | already a row |
| DemonLeatherHelmet | Equipment/Armour/Helmet/DemonLeatherHelmet | LeatherItems.dmi: Demon Leather Helmet | 10 |  | item row |  | LeatherWorks › DblClick | already a row |
| DiamondGoldHelmet | Equipment/Armour/Helmet/DiamondGoldHelmet | GemItems.dmi: Diamond Gold Helmet | 35 |  | item row |  | Forge › DblClick | already a row |
| DiamondMetalHelmet | Equipment/Armour/Helmet/DiamondMetalHelmet | GemItems.dmi: Diamond Metal Helmet | 35 |  | item row |  | Forge › DblClick | already a row |
| DiamondSilverHelmet | Equipment/Armour/Helmet/DiamondSilverHelmet | GemItems.dmi: Diamond Silver Helmet | 35 |  | item row |  | Forge › DblClick | already a row |
| Dragoon Helmet | Equipment/Armour/Helmet/DragoonHelmet | TrimmedMetal.dmi: Gold Trimmed Helmet | 30 |  | item row |  |  | already a row |
| EmeraldGoldHelmet | Equipment/Armour/Helmet/EmeraldGoldHelmet | GemItems.dmi: Emerald Gold Helmet | 35 |  | item row |  | Forge › DblClick | already a row |
| EmeraldMetalHelmet | Equipment/Armour/Helmet/EmeraldMetalHelmet | GemItems.dmi: Emerald Metal Helmet | 35 |  | item row |  | Forge › DblClick | already a row |
| EmeraldSilverHelmet | Equipment/Armour/Helmet/EmeraldSilverHelmet | GemItems.dmi: Emerald Silver Helmet | 35 |  | item row |  | Forge › DblClick | already a row |
| GoldHelmet | Equipment/Armour/Helmet/GoldHelmet | GoldItems.dmi: Gold Helmet | 30 |  | item row |  | Forge › DblClick | already a row |
| LeatherHelmet | Equipment/Armour/Helmet/LeatherHelmet | LeatherItems.dmi: Leather Helmet | 10 |  | item row |  | LeatherWorks › DblClick | already a row |
| MetalHelmet | Equipment/Armour/Helmet/MetalHelmet | MetalObjects.dmi: Metal Helmet | 30 |  | item row |  | Forge › DblClick, MiscCreate › FullMetalLegendary | already a row |
| RedHat | Equipment/Armour/Helmet/RedHat | Robe.dmi: RedHat | 10 |  | item row |  | LeatherWorks › DblClick | already a row |
| RubyGoldHelmet | Equipment/Armour/Helmet/RubyGoldHelmet | GemItems.dmi: Ruby Gold Helmet | 35 |  | item row |  | Forge › DblClick | already a row |
| RubyMetalHelmet | Equipment/Armour/Helmet/RubyMetalHelmet | GemItems.dmi: Ruby Metal Helmet | 35 |  | item row |  | Forge › DblClick | already a row |
| RubySilverHelmet | Equipment/Armour/Helmet/RubySilverHelmet | GemItems.dmi: Ruby Silver Helmet | 35 |  | item row |  | Forge › DblClick | already a row |
| SilverHelmet | Equipment/Armour/Helmet/SilverHelmet | SilverItems.dmi: Silver Helmet | 20 |  | item row |  | Forge › DblClick | already a row |
| Skorn Plate Helmet | Equipment/Armour/Helmet/SkornPlateHelmet | SkornArmour.dmi: SHelmet | 10 |  | item row |  |  | already a row |
| SupernaturalBoneHelmet | Equipment/Armour/Helmet/SupernaturalBoneHelmet | Superbone.dmi: helmet | 10 |  | item row |  | BoneCraft › DblClick | already a row |
| WhiteHood | Equipment/Armour/Helmet/WhiteHood | Robe.dmi: WhiteHood | 10 |  | item row |  | LeatherWorks › DblClick | already a row |
| WoodenHelmet | Equipment/Armour/Helmet/WoodenHelmet | WoodItems.dmi: Wooden Helmet | 10 |  | item row |  | Carpentry › DblClick | already a row |
| Adamantium Crested Helm | Equipment/Armour/Helmet/rm_helmet_crested_adamantium | adamantium.dmi: helmet.crested.adamantium | 8 | armour | gear row |  |  | already a row |
| Bone Crested Helm | Equipment/Armour/Helmet/rm_helmet_crested_bone | bone.dmi: helmet.crested.bone | 8 | armour | gear row |  |  | already a row |
| Chitin Crested Helm | Equipment/Armour/Helmet/rm_helmet_crested_chitin | chitin.dmi: helmet.crested.chitin | 7 | armour | gear row |  |  | already a row |
| Diamond Crested Helm | Equipment/Armour/Helmet/rm_helmet_crested_diamond | diamond.dmi: helmet.crested.diamond | 10 | armour | gear row |  |  | already a row |
| Crested Dragon Helm | Equipment/Armour/Helmet/rm_helmet_crested_dragon | dragon.dmi: helmet.crested.dragon | 7 | armour | gear row |  |  | already a row |
| Gold Crested Helm | Equipment/Armour/Helmet/rm_helmet_crested_gold | gold.dmi: helmet.crested.gold | 13 | armour | gear row |  |  | already a row |
| Hellforged Crested Helm | Equipment/Armour/Helmet/rm_helmet_crested_hell | hell.dmi: helmet.crested.hell | 11 | armour | gear row |  |  | already a row |
| Iron Crested Helm | Equipment/Armour/Helmet/rm_helmet_crested_iron | iron.dmi: helmet.crested.iron | 10 | armour | gear row |  |  | already a row |
| Silver Crested Helm | Equipment/Armour/Helmet/rm_helmet_crested_silver | silver.dmi: helmet.crested.silver | 10 | armour | gear row |  |  | already a row |
| Adamantium Great Helm | Equipment/Armour/Helmet/rm_helmet_great_helm_adamantium | adamantium.dmi: helmet.great helm.adamantium | 10 | armour | gear row |  |  | already a row |
| Chitin Great Helm | Equipment/Armour/Helmet/rm_helmet_great_helm_chitin | chitin.dmi: helmet.great helm.chitin | 8 | armour | gear row |  |  | already a row |
| Diamond Great Helm | Equipment/Armour/Helmet/rm_helmet_great_helm_diamond | diamond.dmi: helmet.great helm.diamond | 12 | armour | gear row |  |  | already a row |
| Dragon Great Helm | Equipment/Armour/Helmet/rm_helmet_great_helm_dragon | dragon.dmi: helmet.great helm.dragon | 8 | armour | gear row |  |  | already a row |
| Dragon Skull Helm | Equipment/Armour/Helmet/rm_helmet_great_helm_dragonbone | dragonbone.dmi: helmet.great helm.dragonbone | 10 | armour | gear row |  |  | already a row |
| Gold Great Helm | Equipment/Armour/Helmet/rm_helmet_great_helm_gold | gold.dmi: helmet.great helm.gold | 16 | armour | gear row |  |  | already a row |
| Hellforged Great Helm | Equipment/Armour/Helmet/rm_helmet_great_helm_hell | hell.dmi: helmet.great helm.hell | 13 | armour | gear row |  |  | already a row |
| Iron Great Helm | Equipment/Armour/Helmet/rm_helmet_great_helm_iron | iron.dmi: helmet.great helm.iron | 12 | armour | gear row |  |  | already a row |
| Silver Great Helm | Equipment/Armour/Helmet/rm_helmet_great_helm_silver | silver.dmi: helmet.great helm.silver | 12 | armour | gear row |  |  | already a row |
| Adamantium Horned Helm | Equipment/Armour/Helmet/rm_helmet_horned_adamantium | adamantium.dmi: helmet.horned.adamantium | 8 | armour | gear row |  |  | already a row |
| Bone Horned Helm | Equipment/Armour/Helmet/rm_helmet_horned_bone | bone.dmi: helmet.horned.bone | 8 | armour | gear row |  |  | already a row |
| Chitin Horned Helm | Equipment/Armour/Helmet/rm_helmet_horned_chitin | chitin.dmi: helmet.horned.chitin | 7 | armour | gear row |  |  | already a row |
| Diamond Horned Helm | Equipment/Armour/Helmet/rm_helmet_horned_diamond | diamond.dmi: helmet.horned.diamond | 10 | armour | gear row |  |  | already a row |
| Horned Dragon Helm | Equipment/Armour/Helmet/rm_helmet_horned_dragon | dragon.dmi: helmet.horned.dragon | 7 | armour | gear row |  |  | already a row |
| Horned Dragonbone Helm | Equipment/Armour/Helmet/rm_helmet_horned_dragonbone | dragonbone.dmi: helmet.horned.dragonbone | 8 | armour | gear row |  |  | already a row |
| Gold Horned Helm | Equipment/Armour/Helmet/rm_helmet_horned_gold | gold.dmi: helmet.horned.gold | 13 | armour | gear row |  |  | already a row |
| Hellforged Horned Helm | Equipment/Armour/Helmet/rm_helmet_horned_hell | hell.dmi: helmet.horned.hell | 11 | armour | gear row |  |  | already a row |
| Iron Horned Helm | Equipment/Armour/Helmet/rm_helmet_horned_iron | iron.dmi: helmet.horned.iron | 10 | armour | gear row |  |  | already a row |
| Silver Horned Helm | Equipment/Armour/Helmet/rm_helmet_horned_silver | silver.dmi: helmet.horned.silver | 10 | armour | gear row |  |  | already a row |
| Adamantium Kettle Helm | Equipment/Armour/Helmet/rm_helmet_kettle_adamantium | adamantium.dmi: helmet.kettle.adamantium | 6 | armour | gear row |  |  | already a row |
| Skull Helm | Equipment/Armour/Helmet/rm_helmet_kettle_bone | bone.dmi: helmet.kettle.bone | 6 | armour | gear row |  |  | already a row |
| Bonehide Cap | Equipment/Armour/Helmet/rm_helmet_kettle_bonehide | bonehide.dmi: helmet.kettle.bonehide | 4 | armour | gear row |  |  | already a row |
| Chitin Kettle Helm | Equipment/Armour/Helmet/rm_helmet_kettle_chitin | chitin.dmi: helmet.kettle.chitin | 6 | armour | gear row |  |  | already a row |
| Diamond Kettle Helm | Equipment/Armour/Helmet/rm_helmet_kettle_diamond | diamond.dmi: helmet.kettle.diamond | 8 | armour | gear row |  |  | already a row |
| Dragonscale Helm | Equipment/Armour/Helmet/rm_helmet_kettle_dragon | dragon.dmi: helmet.kettle.dragon | 6 | armour | gear row |  |  | already a row |
| Dragonbone Helm | Equipment/Armour/Helmet/rm_helmet_kettle_dragonbone | dragonbone.dmi: helmet.kettle.dragonbone | 7 | armour | gear row |  |  | already a row |
| Dragonhide Cap | Equipment/Armour/Helmet/rm_helmet_kettle_dragonhide | dragonhide.dmi: helmet.kettle.dragonhide | 3 | armour | gear row |  |  | already a row |
| Gold Kettle Helm | Equipment/Armour/Helmet/rm_helmet_kettle_gold | gold.dmi: helmet.kettle.gold | 10 | armour | gear row |  |  | already a row |
| Hellforged Kettle Helm | Equipment/Armour/Helmet/rm_helmet_kettle_hell | hell.dmi: helmet.kettle.hell | 9 | armour | gear row |  |  | already a row |
| Iron Kettle Helm | Equipment/Armour/Helmet/rm_helmet_kettle_iron | iron.dmi: helmet.kettle.iron | 8 | armour | gear row |  |  | already a row |
| Leather Cap | Equipment/Armour/Helmet/rm_helmet_kettle_leather | leather.dmi: helmet.kettle.leather | 3 | armour | gear row |  |  | already a row |
| Silver Kettle Helm | Equipment/Armour/Helmet/rm_helmet_kettle_silver | silver.dmi: helmet.kettle.silver | 8 | armour | gear row |  |  | already a row |
| Spidersilk Cap | Equipment/Armour/Helmet/rm_helmet_kettle_spidersilk | spidersilk.dmi: helmet.kettle.spidersilk | 3 | armour | gear row |  |  | already a row |
| Wooden Helmet | Equipment/Armour/Helmet/rm_helmet_kettle_wood | wood.dmi: helmet.kettle.wood | 4 | armour | gear row |  |  | already a row |
| Adamantium Nasal Helm | Equipment/Armour/Helmet/rm_helmet_nasal_adamantium | adamantium.dmi: helmet.nasal.adamantium | 6 | armour | gear row |  |  | already a row |
| Diamond Nasal Helm | Equipment/Armour/Helmet/rm_helmet_nasal_diamond | diamond.dmi: helmet.nasal.diamond | 8 | armour | gear row |  |  | already a row |
| Gold Nasal Helm | Equipment/Armour/Helmet/rm_helmet_nasal_gold | gold.dmi: helmet.nasal.gold | 10 | armour | gear row |  |  | already a row |
| Hellforged Nasal Helm | Equipment/Armour/Helmet/rm_helmet_nasal_hell | hell.dmi: helmet.nasal.hell | 9 | armour | gear row |  |  | already a row |
| Iron Nasal Helm | Equipment/Armour/Helmet/rm_helmet_nasal_iron | iron.dmi: helmet.nasal.iron | 8 | armour | gear row |  |  | already a row |
| Silver Nasal Helm | Equipment/Armour/Helmet/rm_helmet_nasal_silver | silver.dmi: helmet.nasal.silver | 8 | armour | gear row |  |  | already a row |
| Adamantium Winged Helm | Equipment/Armour/Helmet/rm_helmet_winged_adamantium | adamantium.dmi: helmet.winged.adamantium | 7 | armour | gear row |  |  | already a row |
| Diamond Winged Helm | Equipment/Armour/Helmet/rm_helmet_winged_diamond | diamond.dmi: helmet.winged.diamond | 9 | armour | gear row |  |  | already a row |
| Gold Winged Helm | Equipment/Armour/Helmet/rm_helmet_winged_gold | gold.dmi: helmet.winged.gold | 12 | armour | gear row |  |  | already a row |
| Hellforged Winged Helm | Equipment/Armour/Helmet/rm_helmet_winged_hell | hell.dmi: helmet.winged.hell | 10 | armour | gear row |  |  | already a row |
| Iron Winged Helm | Equipment/Armour/Helmet/rm_helmet_winged_iron | iron.dmi: helmet.winged.iron | 9 | armour | gear row |  |  | already a row |
| Silver Winged Helm | Equipment/Armour/Helmet/rm_helmet_winged_silver | silver.dmi: helmet.winged.silver | 9 | armour | gear row |  |  | already a row |
| LeftArm *(group of 33)* | Equipment/Armour/LeftArm |  | 5 |  | item row |  |  | already a row |
| AdamantiumLeftGauntlet | Equipment/Armour/LeftArm/AdamantiumLeftGauntlet | MetalObjects.dmi: AdamantiumLeftArm | 5 |  | item row |  | Forge › DblClick | already a row |
| BoneLeftGauntlet | Equipment/Armour/LeftArm/BoneLeftGauntlet | BoneItems.dmi: BLeftArm | 5 |  | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick, MiscCreate › FullBoneLegendary | already a row |
| ChitinLeftGauntlet | Equipment/Armour/LeftArm/ChitinLeftGauntlet | BoneItems.dmi: CLeftArm | 5 |  | item row |  | BoneCraft › DblClick | already a row |
| DemonLeatherLeftGauntlet | Equipment/Armour/LeftArm/DemonLeatherLeftGauntlet | LeatherItems.dmi: DemonLeatherLeft | 2 |  | item row |  | LeatherWorks › DblClick | already a row |
| Dragoon Left Gauntlet | Equipment/Armour/LeftArm/DragoonLeftGauntlet | TrimmedMetal.dmi: Gold Trimmed Left Gauntlet | 5 |  | item row |  |  | already a row |
| GoldLeftGauntlet | Equipment/Armour/LeftArm/GoldLeftGauntlet | GoldItems.dmi: GLeftArm | 5 |  | item row |  | Forge › DblClick | already a row |
| LeatherLeftGauntlet | Equipment/Armour/LeftArm/LeatherLeftGauntlet | LeatherItems.dmi: LeatherLeft | 2 |  | item row |  | LeatherWorks › DblClick | already a row |
| MetalLeftGauntlet | Equipment/Armour/LeftArm/MetalLeftGauntlet | MetalObjects.dmi: MLeftArm | 5 |  | item row |  | Forge › DblClick, MiscCreate › FullMetalLegendary | already a row |
| SilverLeftGauntlet | Equipment/Armour/LeftArm/SilverLeftGauntlet | SilverItems.dmi: SilverLeft | 5 |  | item row |  | Forge › DblClick | already a row |
| Skorn Gauntlet | Equipment/Armour/LeftArm/SkornLeftGauntlet | SkornArmour.dmi: SLeftArm | 5 |  | item row |  |  | already a row |
| SupernaturalBoneLeftGauntlet | Equipment/Armour/LeftArm/SupernaturalBoneLeftGauntlet | Superbone.dmi: leftarm | 5 |  | item row |  | BoneCraft › DblClick | already a row |
| WoodenLeftGauntlet | Equipment/Armour/LeftArm/WoodenLeftGauntlet | WoodItems.dmi: Wooden LeftArm | 5 |  | item row |  | Carpentry › DblClick | already a row |
| Bonehide Left Bracer | Equipment/Armour/LeftArm/rm_arms_leather_bonehide_left | bonehide.dmi: arms.leather.bonehide.L | 1 | armour | gear row |  |  | already a row |
| Dragonhide Left Bracer | Equipment/Armour/LeftArm/rm_arms_leather_dragonhide_left | dragonhide.dmi: arms.leather.dragonhide.L | 1 | armour | gear row |  |  | already a row |
| Leather Left Bracer | Equipment/Armour/LeftArm/rm_arms_leather_leather_left | leather.dmi: arms.leather.leather.L | 1 | armour | gear row |  |  | already a row |
| Spidersilk Left Bracer | Equipment/Armour/LeftArm/rm_arms_leather_spidersilk_left | spidersilk.dmi: arms.leather.spidersilk.L | 1 | armour | gear row |  |  | already a row |
| Adamantium Mail Left Sleeve | Equipment/Armour/LeftArm/rm_arms_mail_adamantium_left | adamantium.dmi: arms.mail.adamantium.L | 3 | armour | gear row |  |  | already a row |
| Diamond Mail Left Sleeve | Equipment/Armour/LeftArm/rm_arms_mail_diamond_left | diamond.dmi: arms.mail.diamond.L | 4 | armour | gear row |  |  | already a row |
| Gold Mail Left Sleeve | Equipment/Armour/LeftArm/rm_arms_mail_gold_left | gold.dmi: arms.mail.gold.L | 5 | armour | gear row |  |  | already a row |
| Hellforged Mail Left Sleeve | Equipment/Armour/LeftArm/rm_arms_mail_hell_left | hell.dmi: arms.mail.hell.L | 4 | armour | gear row |  |  | already a row |
| Iron Mail Left Sleeve | Equipment/Armour/LeftArm/rm_arms_mail_iron_left | iron.dmi: arms.mail.iron.L | 4 | armour | gear row |  |  | already a row |
| Silver Mail Left Sleeve | Equipment/Armour/LeftArm/rm_arms_mail_silver_left | silver.dmi: arms.mail.silver.L | 4 | armour | gear row |  |  | already a row |
| Adamantium Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_adamantium_left | adamantium.dmi: arms.plate.adamantium.L | 5 | armour | gear row |  |  | already a row |
| Bone Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_bone_left | bone.dmi: arms.plate.bone.L | 5 | armour | gear row |  |  | already a row |
| Chitin Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_chitin_left | chitin.dmi: arms.plate.chitin.L | 4 | armour | gear row |  |  | already a row |
| Diamond Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_diamond_left | diamond.dmi: arms.plate.diamond.L | 6 | armour | gear row |  |  | already a row |
| Dragonscale Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_dragon_left | dragon.dmi: arms.plate.dragon.L | 4 | armour | gear row |  |  | already a row |
| Dragonbone Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_dragonbone_left | dragonbone.dmi: arms.plate.dragonbone.L | 5 | armour | gear row |  |  | already a row |
| Gold Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_gold_left | gold.dmi: arms.plate.gold.L | 8 | armour | gear row |  |  | already a row |
| Hellforged Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_hell_left | hell.dmi: arms.plate.hell.L | 7 | armour | gear row |  |  | already a row |
| Iron Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_iron_left | iron.dmi: arms.plate.iron.L | 6 | armour | gear row |  |  | already a row |
| Silver Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_silver_left | silver.dmi: arms.plate.silver.L | 6 | armour | gear row |  |  | already a row |
| Wooden Left Vambrace | Equipment/Armour/LeftArm/rm_arms_plate_wood_left | wood.dmi: arms.plate.wood.L | 3 | armour | gear row |  |  | already a row |
| Leggings *(group of 53)* | Equipment/Armour/Leggings |  | 30 |  | item row |  |  | already a row |
| AdamantiumLeggings | Equipment/Armour/Leggings/AdamantiumLeggings | MetalObjects.dmi: Adamantium Leggings | 0 |  | item row |  | Forge › DblClick | already a row |
| BoneLeggings | Equipment/Armour/Leggings/BoneLeggings | BoneItems.dmi: BoneLeggings | 10 |  | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick, MiscCreate › FullBoneLegendary | already a row |
| ChitinLeggings | Equipment/Armour/Leggings/ChitinLeggings | BoneItems.dmi: ChitinLeggings | 10 |  | item row |  | BoneCraft › DblClick | already a row |
| DemonLeatherLeggings | Equipment/Armour/Leggings/DemonLeatherLeggings | LeatherItems.dmi: DemonLeatherLeggings | 5 |  | item row |  | LeatherWorks › DblClick | already a row |
| DiamondGoldLeggings | Equipment/Armour/Leggings/DiamondGoldLeggings | GemItems.dmi: GoldDiamondLeggings | 30 |  | item row |  | Forge › DblClick | already a row |
| DiamondMetalLeggings | Equipment/Armour/Leggings/DiamondMetalLeggings | GemItems.dmi: MetalDiamondLeggings | 30 |  | item row |  | Forge › DblClick | already a row |
| DiamondSilverLeggings | Equipment/Armour/Leggings/DiamondSilverLeggings | GemItems.dmi: SilverDiamondLeggings | 30 |  | item row |  | Forge › DblClick | already a row |
| Dragoon Leggings | Equipment/Armour/Leggings/DragoonLeggings | TrimmedMetal.dmi: Gold Trimmed Leggings | 30 |  | item row |  |  | already a row |
| EmeraldGoldLeggings | Equipment/Armour/Leggings/EmeraldGoldLeggings | GemItems.dmi: GoldEmeraldLeggings | 30 |  | item row |  | Forge › DblClick | already a row |
| EmeraldMetalLeggings | Equipment/Armour/Leggings/EmeraldMetalLeggings | GemItems.dmi: MetalEmeraldLeggings | 30 |  | item row |  | Forge › DblClick | already a row |
| EmeraldSilverLeggings | Equipment/Armour/Leggings/EmeraldSilverLeggings | GemItems.dmi: SilverEmeraldLeggings | 30 |  | item row |  | Forge › DblClick | already a row |
| GoldLeggings | Equipment/Armour/Leggings/GoldLeggings | GoldItems.dmi: Gold Leggings | 30 |  | item row |  | Forge › DblClick | already a row |
| LeatherLeggings | Equipment/Armour/Leggings/LeatherLeggings | LeatherItems.dmi: LeatherLeggings | 5 |  | item row |  | LeatherWorks › DblClick | already a row |
| MetalLeggings | Equipment/Armour/Leggings/MetalLeggings | MetalObjects.dmi: Metal Leggings | 30 |  | item row |  | Forge › DblClick, MiscCreate › FullMetalLegendary | already a row |
| RubyGoldLeggings | Equipment/Armour/Leggings/RubyGoldLeggings | GemItems.dmi: GoldRubyLeggings | 30 |  | item row |  | Forge › DblClick | already a row |
| RubyMetalLeggings | Equipment/Armour/Leggings/RubyMetalLeggings | GemItems.dmi: MetalRubyLeggings | 30 |  | item row |  | Forge › DblClick | already a row |
| RubySilverLeggings | Equipment/Armour/Leggings/RubySilverLeggings | GemItems.dmi: SilverRubyLeggings | 30 |  | item row |  | Forge › DblClick | already a row |
| SilverLeggings | Equipment/Armour/Leggings/SilverLeggings | SilverItems.dmi: Silver Leggings | 30 |  | item row |  | Forge › DblClick | already a row |
| Skorn Leggings | Equipment/Armour/Leggings/SkornLeggings | SkornArmour.dmi: SLegs | 10 |  | item row |  |  | already a row |
| SupernaturalBoneLeggings | Equipment/Armour/Leggings/SupernaturalBoneLeggings | Superbone.dmi: leggings | 10 |  | item row |  | BoneCraft › DblClick | already a row |
| WoodenLeggings | Equipment/Armour/Leggings/WoodenLeggings | WoodItems.dmi: Wooden Leggings | 5 |  | item row |  | Carpentry › DblClick | already a row |
| Boots | Equipment/Armour/Leggings/rm_legs_boots | cloth.dmi: legs.boots | 3 | armour | gear row |  |  | already a row |
| Padded Trousers | Equipment/Armour/Leggings/rm_legs_cloth | cloth.dmi: legs.cloth | 6 | armour | gear row |  |  | already a row |
| Bonehide Breeches | Equipment/Armour/Leggings/rm_legs_leather_bonehide | bonehide.dmi: legs.leather.bonehide | 3 | armour | gear row |  |  | already a row |
| Dragonhide Breeches | Equipment/Armour/Leggings/rm_legs_leather_dragonhide | dragonhide.dmi: legs.leather.dragonhide | 2 | armour | gear row |  |  | already a row |
| Leather Breeches | Equipment/Armour/Leggings/rm_legs_leather_leather | leather.dmi: legs.leather.leather | 2 | armour | gear row |  |  | already a row |
| Spidersilk Breeches | Equipment/Armour/Leggings/rm_legs_leather_spidersilk | spidersilk.dmi: legs.leather.spidersilk | 2 | armour | gear row |  |  | already a row |
| Adamantium Chausses | Equipment/Armour/Leggings/rm_legs_mail_adamantium | adamantium.dmi: legs.mail.adamantium | 14 | armour | gear row |  |  | already a row |
| Diamond Chausses | Equipment/Armour/Leggings/rm_legs_mail_diamond | diamond.dmi: legs.mail.diamond | 18 | armour | gear row |  |  | already a row |
| Gold Chausses | Equipment/Armour/Leggings/rm_legs_mail_gold | gold.dmi: legs.mail.gold | 23 | armour | gear row |  |  | already a row |
| Hellforged Chausses | Equipment/Armour/Leggings/rm_legs_mail_hell | hell.dmi: legs.mail.hell | 20 | armour | gear row |  |  | already a row |
| Iron Chausses | Equipment/Armour/Leggings/rm_legs_mail_iron | iron.dmi: legs.mail.iron | 18 | armour | gear row |  |  | already a row |
| Silver Chausses | Equipment/Armour/Leggings/rm_legs_mail_silver | silver.dmi: legs.mail.silver | 18 | armour | gear row |  |  | already a row |
| Adamantium Greaves | Equipment/Armour/Leggings/rm_legs_plate_adamantium | adamantium.dmi: legs.plate.adamantium | 20 | armour | gear row |  |  | already a row |
| Bone Greaves | Equipment/Armour/Leggings/rm_legs_plate_bone | bone.dmi: legs.plate.bone | 20 | armour | gear row |  |  | already a row |
| Chitin Greaves | Equipment/Armour/Leggings/rm_legs_plate_chitin | chitin.dmi: legs.plate.chitin | 18 | armour | gear row |  |  | already a row |
| Diamond Greaves | Equipment/Armour/Leggings/rm_legs_plate_diamond | diamond.dmi: legs.plate.diamond | 25 | armour | gear row |  |  | already a row |
| Dragonscale Greaves | Equipment/Armour/Leggings/rm_legs_plate_dragon | dragon.dmi: legs.plate.dragon | 18 | armour | gear row |  |  | already a row |
| Dragonbone Greaves | Equipment/Armour/Leggings/rm_legs_plate_dragonbone | dragonbone.dmi: legs.plate.dragonbone | 21 | armour | gear row |  |  | already a row |
| Gold Greaves | Equipment/Armour/Leggings/rm_legs_plate_gold | gold.dmi: legs.plate.gold | 32 | armour | gear row |  |  | already a row |
| Hellforged Greaves | Equipment/Armour/Leggings/rm_legs_plate_hell | hell.dmi: legs.plate.hell | 28 | armour | gear row |  |  | already a row |
| Iron Greaves | Equipment/Armour/Leggings/rm_legs_plate_iron | iron.dmi: legs.plate.iron | 25 | armour | gear row |  |  | already a row |
| Silver Greaves | Equipment/Armour/Leggings/rm_legs_plate_silver | silver.dmi: legs.plate.silver | 25 | armour | gear row |  |  | already a row |
| Wooden Greaves | Equipment/Armour/Leggings/rm_legs_plate_wood | wood.dmi: legs.plate.wood | 12 | armour | gear row |  |  | already a row |
| Adamantium Scale Tassets | Equipment/Armour/Leggings/rm_legs_scale_adamantium | adamantium.dmi: legs.scale.adamantium | 16 | armour | gear row |  |  | already a row |
| Bone Scale Tassets | Equipment/Armour/Leggings/rm_legs_scale_bone | bone.dmi: legs.scale.bone | 16 | armour | gear row |  |  | already a row |
| Chitin Scale Tassets | Equipment/Armour/Leggings/rm_legs_scale_chitin | chitin.dmi: legs.scale.chitin | 14 | armour | gear row |  |  | already a row |
| Diamond Scale Tassets | Equipment/Armour/Leggings/rm_legs_scale_diamond | diamond.dmi: legs.scale.diamond | 20 | armour | gear row |  |  | already a row |
| Dragonscale Tassets | Equipment/Armour/Leggings/rm_legs_scale_dragon | dragon.dmi: legs.scale.dragon | 14 | armour | gear row |  |  | already a row |
| Gold Scale Tassets | Equipment/Armour/Leggings/rm_legs_scale_gold | gold.dmi: legs.scale.gold | 26 | armour | gear row |  |  | already a row |
| Hellforged Scale Tassets | Equipment/Armour/Leggings/rm_legs_scale_hell | hell.dmi: legs.scale.hell | 22 | armour | gear row |  |  | already a row |
| Iron Scale Tassets | Equipment/Armour/Leggings/rm_legs_scale_iron | iron.dmi: legs.scale.iron | 20 | armour | gear row |  |  | already a row |
| Silver Scale Tassets | Equipment/Armour/Leggings/rm_legs_scale_silver | silver.dmi: legs.scale.silver | 20 | armour | gear row |  |  | already a row |
| NeckGuards *(group of 3)* | Equipment/Armour/NeckGuards |  | 10 |  | item row |  |  | already a row |
| GoldNeckGuard | Equipment/Armour/NeckGuards/GoldNeckGuard | GoldItems.dmi: Guard | 10 |  | item row |  | Forge › DblClick | already a row |
| MetalNeckGuard | Equipment/Armour/NeckGuards/MetalNeckGuard | MetalObjects.dmi: Guard | 10 |  | item row |  | Forge › DblClick | already a row |
| SilverNeckGuard | Equipment/Armour/NeckGuards/SilverNeckGuard | SilverItems.dmi: Guard | 10 |  | item row |  | Forge › DblClick | already a row |
| Quiver *(group of 2)* | Equipment/Armour/Quiver |  | 0 |  | item row |  |  | already a row |
| Leather Quiver | Equipment/Armour/Quiver/LeatherQuiver | Quiver.dmi:  | 5 | quiver | item row |  | LeatherWorks › DblClick | already a row |
| Resource Sack | Equipment/Armour/Quiver/RemasterSack | Sack.dmi:  | 3 |  | item row |  | Monsters › RemasterCraftSack | already a row |
| RightArm *(group of 33)* | Equipment/Armour/RightArm |  | 0 |  | item row |  |  | already a row |
| AdamantiumRightGauntlet | Equipment/Armour/RightArm/AdamantiumRightGauntlet | MetalObjects.dmi: AdamantiumRightArm | 0 |  | item row |  | Forge › DblClick | already a row |
| BoneRightGauntlet | Equipment/Armour/RightArm/BoneRightGauntlet | BoneItems.dmi: BRightArm | 5 |  | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick, MiscCreate › FullBoneLegendary | already a row |
| ChitinRightGauntlet | Equipment/Armour/RightArm/ChitinRightGauntlet | BoneItems.dmi: CRightArm | 5 |  | item row |  | BoneCraft › DblClick | already a row |
| DemonLeatherRightGauntlet | Equipment/Armour/RightArm/DemonLeatherRightGauntlet | LeatherItems.dmi: DemonLeatherRight | 2 |  | item row |  | LeatherWorks › DblClick | already a row |
| Dragoon Right Gauntlet | Equipment/Armour/RightArm/DragoonRightGauntlet | TrimmedMetal.dmi: Gold Trimmed Right Gauntlet | 7 |  | item row |  |  | already a row |
| GoldRightGauntlet | Equipment/Armour/RightArm/GoldRightGauntlet | GoldItems.dmi: GRightArm | 7 |  | item row |  | Forge › DblClick | already a row |
| LeatherRightGauntlet | Equipment/Armour/RightArm/LeatherRightGauntlet | LeatherItems.dmi: LeatherRight | 2 |  | item row |  | LeatherWorks › DblClick | already a row |
| MetalRightGauntlet | Equipment/Armour/RightArm/MetalRightGauntlet | MetalObjects.dmi: MRightArm | 5 |  | item row |  | Forge › DblClick, MiscCreate › FullMetalLegendary | already a row |
| SilverRightGauntlet | Equipment/Armour/RightArm/SilverRightGauntlet | SilverItems.dmi: SilverRight | 5 |  | item row |  | Forge › DblClick | already a row |
| Skorn Gauntlet | Equipment/Armour/RightArm/SkornRightGauntlet | SkornArmour.dmi: SRightArm | 5 |  | item row |  |  | already a row |
| SupernaturalBoneRightGauntlet | Equipment/Armour/RightArm/SupernaturalBoneRightGauntlet | Superbone.dmi: rightarm | 5 |  | item row |  | BoneCraft › DblClick | already a row |
| WoodenRightGauntlet | Equipment/Armour/RightArm/WoodenRightGauntlet | WoodItems.dmi: Wooden RightArm | 5 |  | item row |  | Carpentry › DblClick | already a row |
| Bonehide Right Bracer | Equipment/Armour/RightArm/rm_arms_leather_bonehide_right | bonehide.dmi: arms.leather.bonehide.R | 1 | armour | gear row |  |  | already a row |
| Dragonhide Right Bracer | Equipment/Armour/RightArm/rm_arms_leather_dragonhide_right | dragonhide.dmi: arms.leather.dragonhide.R | 1 | armour | gear row |  |  | already a row |
| Leather Right Bracer | Equipment/Armour/RightArm/rm_arms_leather_leather_right | leather.dmi: arms.leather.leather.R | 1 | armour | gear row |  |  | already a row |
| Spidersilk Right Bracer | Equipment/Armour/RightArm/rm_arms_leather_spidersilk_right | spidersilk.dmi: arms.leather.spidersilk.R | 1 | armour | gear row |  |  | already a row |
| Adamantium Mail Right Sleeve | Equipment/Armour/RightArm/rm_arms_mail_adamantium_right | adamantium.dmi: arms.mail.adamantium.R | 3 | armour | gear row |  |  | already a row |
| Diamond Mail Right Sleeve | Equipment/Armour/RightArm/rm_arms_mail_diamond_right | diamond.dmi: arms.mail.diamond.R | 4 | armour | gear row |  |  | already a row |
| Gold Mail Right Sleeve | Equipment/Armour/RightArm/rm_arms_mail_gold_right | gold.dmi: arms.mail.gold.R | 5 | armour | gear row |  |  | already a row |
| Hellforged Mail Right Sleeve | Equipment/Armour/RightArm/rm_arms_mail_hell_right | hell.dmi: arms.mail.hell.R | 4 | armour | gear row |  |  | already a row |
| Iron Mail Right Sleeve | Equipment/Armour/RightArm/rm_arms_mail_iron_right | iron.dmi: arms.mail.iron.R | 4 | armour | gear row |  |  | already a row |
| Silver Mail Right Sleeve | Equipment/Armour/RightArm/rm_arms_mail_silver_right | silver.dmi: arms.mail.silver.R | 4 | armour | gear row |  |  | already a row |
| Adamantium Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_adamantium_right | adamantium.dmi: arms.plate.adamantium.R | 5 | armour | gear row |  |  | already a row |
| Bone Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_bone_right | bone.dmi: arms.plate.bone.R | 5 | armour | gear row |  |  | already a row |
| Chitin Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_chitin_right | chitin.dmi: arms.plate.chitin.R | 4 | armour | gear row |  |  | already a row |
| Diamond Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_diamond_right | diamond.dmi: arms.plate.diamond.R | 6 | armour | gear row |  |  | already a row |
| Dragonscale Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_dragon_right | dragon.dmi: arms.plate.dragon.R | 4 | armour | gear row |  |  | already a row |
| Dragonbone Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_dragonbone_right | dragonbone.dmi: arms.plate.dragonbone.R | 5 | armour | gear row |  |  | already a row |
| Gold Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_gold_right | gold.dmi: arms.plate.gold.R | 8 | armour | gear row |  |  | already a row |
| Hellforged Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_hell_right | hell.dmi: arms.plate.hell.R | 7 | armour | gear row |  |  | already a row |
| Iron Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_iron_right | iron.dmi: arms.plate.iron.R | 6 | armour | gear row |  |  | already a row |
| Silver Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_silver_right | silver.dmi: arms.plate.silver.R | 6 | armour | gear row |  |  | already a row |
| Wooden Right Vambrace | Equipment/Armour/RightArm/rm_arms_plate_wood_right | wood.dmi: arms.plate.wood.R | 3 | armour | gear row |  |  | already a row |
| Shield *(group of 58)* | Equipment/Armour/Shield |  | 30 |  | item row |  |  | already a row |
| AdamantiumBuckler | Equipment/Armour/Shield/AdamantiumBuckler | MetalObjects.dmi: AdamantiumBuckler | 30 |  | item row |  | Forge › DblClick | already a row |
| BoneBuckler | Equipment/Armour/Shield/BoneBuckler | BoneItems.dmi: Bone Buckler | 10 |  | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick | already a row |
| ChitinBuckler | Equipment/Armour/Shield/ChitinBuckler | BoneItems.dmi: Chitin Buckler | 10 |  | item row |  | BoneCraft › DblClick | already a row |
| DemonLeatherShield | Equipment/Armour/Shield/DemonLeatherShield | LeatherItems.dmi: DemonLeatherShield | 30 |  | item row |  | LeatherWorks › DblClick | already a row |
| GoldBuckler | Equipment/Armour/Shield/GoldBuckler | GoldItems.dmi: Gold Buckler | 30 |  | item row |  | Forge › DblClick | already a row |
| LizardShield | Equipment/Armour/Shield/LizardShield | MetalObjects.dmi: LizShield | 20 |  | item row |  | Carpentry › DblClick | already a row |
| MetalBuckler | Equipment/Armour/Shield/MetalBuckler | MetalObjects.dmi: Metal Buckler | 30 |  | item row |  | Forge › DblClick | already a row |
| SilverBuckler | Equipment/Armour/Shield/SilverBuckler | SilverItems.dmi: Silver Buckler | 30 |  | item row |  | Forge › DblClick | already a row |
| WoodenBuckler | Equipment/Armour/Shield/WoodenBuckler | GoblinBuckler.dmi: poor | 10 |  | item row |  | Carpentry › DblClick | already a row |
| Adamantium Buckler | Equipment/Armour/Shield/rm_shield_buckler_adamantium | adamantium.dmi: shield.buckler.adamantium | 8 | armour | gear row |  |  | already a row |
| Bone Buckler | Equipment/Armour/Shield/rm_shield_buckler_bone | bone.dmi: shield.buckler.bone | 8 | armour | gear row |  |  | already a row |
| Chitin Buckler | Equipment/Armour/Shield/rm_shield_buckler_chitin | chitin.dmi: shield.buckler.chitin | 7 | armour | gear row |  |  | already a row |
| Diamond Buckler | Equipment/Armour/Shield/rm_shield_buckler_diamond | diamond.dmi: shield.buckler.diamond | 10 | armour | gear row |  |  | already a row |
| Gold Buckler | Equipment/Armour/Shield/rm_shield_buckler_gold | gold.dmi: shield.buckler.gold | 13 | armour | gear row |  |  | already a row |
| Hellforged Buckler | Equipment/Armour/Shield/rm_shield_buckler_hell | hell.dmi: shield.buckler.hell | 11 | armour | gear row |  |  | already a row |
| Iron Buckler | Equipment/Armour/Shield/rm_shield_buckler_iron | iron.dmi: shield.buckler.iron | 10 | armour | gear row |  |  | already a row |
| Leather Buckler | Equipment/Armour/Shield/rm_shield_buckler_leather | leather.dmi: shield.buckler.leather | 4 | armour | gear row |  |  | already a row |
| Silver Buckler | Equipment/Armour/Shield/rm_shield_buckler_silver | silver.dmi: shield.buckler.silver | 10 | armour | gear row |  |  | already a row |
| Wooden Buckler | Equipment/Armour/Shield/rm_shield_buckler_wood | wood.dmi: shield.buckler.wood | 5 | armour | gear row |  |  | already a row |
| Adamantium Heater Shield | Equipment/Armour/Shield/rm_shield_heater_adamantium | adamantium.dmi: shield.heater.adamantium | 18 | armour | gear row |  |  | already a row |
| Chitin Heater Shield | Equipment/Armour/Shield/rm_shield_heater_chitin | chitin.dmi: shield.heater.chitin | 15 | armour | gear row |  |  | already a row |
| Diamond Heater Shield | Equipment/Armour/Shield/rm_shield_heater_diamond | diamond.dmi: shield.heater.diamond | 22 | armour | gear row |  |  | already a row |
| Dragonscale Heater Shield | Equipment/Armour/Shield/rm_shield_heater_dragon | dragon.dmi: shield.heater.dragon | 15 | armour | gear row |  |  | already a row |
| Gold Heater Shield | Equipment/Armour/Shield/rm_shield_heater_gold | gold.dmi: shield.heater.gold | 29 | armour | gear row |  |  | already a row |
| Hellforged Heater Shield | Equipment/Armour/Shield/rm_shield_heater_hell | hell.dmi: shield.heater.hell | 24 | armour | gear row |  |  | already a row |
| Iron Heater Shield | Equipment/Armour/Shield/rm_shield_heater_iron | iron.dmi: shield.heater.iron | 22 | armour | gear row |  |  | already a row |
| Silver Heater Shield | Equipment/Armour/Shield/rm_shield_heater_silver | silver.dmi: shield.heater.silver | 22 | armour | gear row |  |  | already a row |
| Wooden Heater Shield | Equipment/Armour/Shield/rm_shield_heater_wood | wood.dmi: shield.heater.wood | 11 | armour | gear row |  |  | already a row |
| Adamantium Kite Shield | Equipment/Armour/Shield/rm_shield_kite_adamantium | adamantium.dmi: shield.kite.adamantium | 22 | armour | gear row |  |  | already a row |
| Bone Kite Shield | Equipment/Armour/Shield/rm_shield_kite_bone | bone.dmi: shield.kite.bone | 22 | armour | gear row |  |  | already a row |
| Chitin Kite Shield | Equipment/Armour/Shield/rm_shield_kite_chitin | chitin.dmi: shield.kite.chitin | 20 | armour | gear row |  |  | already a row |
| Diamond Kite Shield | Equipment/Armour/Shield/rm_shield_kite_diamond | diamond.dmi: shield.kite.diamond | 28 | armour | gear row |  |  | already a row |
| Dragonscale Kite Shield | Equipment/Armour/Shield/rm_shield_kite_dragon | dragon.dmi: shield.kite.dragon | 20 | armour | gear row |  |  | already a row |
| Dragon Skull Shield | Equipment/Armour/Shield/rm_shield_kite_dragonbone | dragonbone.dmi: shield.kite.dragonbone | 24 | armour | gear row |  |  | already a row |
| Gold Kite Shield | Equipment/Armour/Shield/rm_shield_kite_gold | gold.dmi: shield.kite.gold | 36 | armour | gear row |  |  | already a row |
| Hellforged Kite Shield | Equipment/Armour/Shield/rm_shield_kite_hell | hell.dmi: shield.kite.hell | 31 | armour | gear row |  |  | already a row |
| Iron Kite Shield | Equipment/Armour/Shield/rm_shield_kite_iron | iron.dmi: shield.kite.iron | 28 | armour | gear row |  |  | already a row |
| Silver Kite Shield | Equipment/Armour/Shield/rm_shield_kite_silver | silver.dmi: shield.kite.silver | 28 | armour | gear row |  |  | already a row |
| Wooden Kite Shield | Equipment/Armour/Shield/rm_shield_kite_wood | wood.dmi: shield.kite.wood | 14 | armour | gear row |  |  | already a row |
| Adamantium Round Shield | Equipment/Armour/Shield/rm_shield_round_adamantium | adamantium.dmi: shield.round.adamantium | 14 | armour | gear row |  |  | already a row |
| Bone Round Shield | Equipment/Armour/Shield/rm_shield_round_bone | bone.dmi: shield.round.bone | 14 | armour | gear row |  |  | already a row |
| Chitin Round Shield | Equipment/Armour/Shield/rm_shield_round_chitin | chitin.dmi: shield.round.chitin | 13 | armour | gear row |  |  | already a row |
| Diamond Round Shield | Equipment/Armour/Shield/rm_shield_round_diamond | diamond.dmi: shield.round.diamond | 18 | armour | gear row |  |  | already a row |
| Dragonscale Round Shield | Equipment/Armour/Shield/rm_shield_round_dragon | dragon.dmi: shield.round.dragon | 13 | armour | gear row |  |  | already a row |
| Dragonbone Round Shield | Equipment/Armour/Shield/rm_shield_round_dragonbone | dragonbone.dmi: shield.round.dragonbone | 15 | armour | gear row |  |  | already a row |
| Gold Round Shield | Equipment/Armour/Shield/rm_shield_round_gold | gold.dmi: shield.round.gold | 23 | armour | gear row |  |  | already a row |
| Hellforged Round Shield | Equipment/Armour/Shield/rm_shield_round_hell | hell.dmi: shield.round.hell | 20 | armour | gear row |  |  | already a row |
| Iron Round Shield | Equipment/Armour/Shield/rm_shield_round_iron | iron.dmi: shield.round.iron | 18 | armour | gear row |  |  | already a row |
| Leather Round Shield | Equipment/Armour/Shield/rm_shield_round_leather | leather.dmi: shield.round.leather | 7 | armour | gear row |  |  | already a row |
| Silver Round Shield | Equipment/Armour/Shield/rm_shield_round_silver | silver.dmi: shield.round.silver | 18 | armour | gear row |  |  | already a row |
| Wooden Round Shield | Equipment/Armour/Shield/rm_shield_round_wood | wood.dmi: shield.round.wood | 9 | armour | gear row |  |  | already a row |
| Adamantium Tower Shield | Equipment/Armour/Shield/rm_shield_tower_adamantium | adamantium.dmi: shield.tower.adamantium | 32 | armour | gear row |  |  | already a row |
| Diamond Tower Shield | Equipment/Armour/Shield/rm_shield_tower_diamond | diamond.dmi: shield.tower.diamond | 40 | armour | gear row |  |  | already a row |
| Gold Tower Shield | Equipment/Armour/Shield/rm_shield_tower_gold | gold.dmi: shield.tower.gold | 52 | armour | gear row |  |  | already a row |
| Hellforged Tower Shield | Equipment/Armour/Shield/rm_shield_tower_hell | hell.dmi: shield.tower.hell | 44 | armour | gear row |  |  | already a row |
| Iron Tower Shield | Equipment/Armour/Shield/rm_shield_tower_iron | iron.dmi: shield.tower.iron | 40 | armour | gear row |  |  | already a row |
| Silver Tower Shield | Equipment/Armour/Shield/rm_shield_tower_silver | silver.dmi: shield.tower.silver | 40 | armour | gear row |  |  | already a row |
| Wooden Tower Shield | Equipment/Armour/Shield/rm_shield_tower_wood | wood.dmi: shield.tower.wood | 20 | armour | gear row |  |  | already a row |
| Weapon *(group of 8)* | Equipment/Weapon |  | 0 | weapon | 2006 (Items/Equipment Lists.dm:1) |  |  | no values of its own |
| Axes *(group of 28)* | Equipment/Weapon/Axes |  | 0 | weapon | item row |  |  | already a row |
| AdamantiumAxe | Equipment/Weapon/Axes/AdamantiumAxe | MetalObjects.dmi: Adamantium Axe | 25 | weapon | item row |  | Forge › DblClick | already a row |
| BoneAxe | Equipment/Weapon/Axes/BoneAxe | WoodItems.dmi: Wooden Axe | 20 | weapon | 2006 (Items/Equipment Lists.dm:104) |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick | values mixed with code (Code/Items/Equipment Lists.dm:108) |
| ChitinAxe | Equipment/Weapon/Axes/ChitinAxe | BoneItems.dmi: ChitinAxe | 20 | weapon | item row |  | BoneCraft › DblClick | already a row |
| GoldAxe | Equipment/Weapon/Axes/GoldAxe | GoldItems.dmi: Gold Axe | 30 | weapon | item row |  | Forge › DblClick | already a row |
| MetalAxe | Equipment/Weapon/Axes/MetalAxe | Cave.dmi: Axe | 25 | weapon | item row |  | Forge › DblClick | already a row |
| MetalOrcAxe | Equipment/Weapon/Axes/MetalOrcAxe | MetalObjects.dmi: MetalOrcAxe | 25 | weapon | item row |  | Forge › DblClick, MiscCreate › LegendaryMetalAxe | already a row |
| SilverAxe | Equipment/Weapon/Axes/SilverAxe | SilverItems.dmi: Silver Axe | 25 | weapon | item row |  | Forge › DblClick | already a row |
| WoodenAxe | Equipment/Weapon/Axes/WoodenAxe | WoodItems.dmi: Wooden Axe | 20 | weapon | item row |  | Carpentry › DblClick | already a row |
| Frostbite Axe | Equipment/Weapon/Axes/rm_magic_frost_axe | magic.dmi: magic.frost axe | 40 | weapon | gear row |  |  | already a row |
| Adamantium Battle Axe | Equipment/Weapon/Axes/rm_weapon_battle_axe_adamantium | adamantium.dmi: weapon.battle axe.adamantium | 32 | weapon | gear row |  |  | already a row |
| Chitin Battle Axe | Equipment/Weapon/Axes/rm_weapon_battle_axe_chitin | chitin.dmi: weapon.battle axe.chitin | 28 | weapon | gear row |  |  | already a row |
| Diamond Battle Axe | Equipment/Weapon/Axes/rm_weapon_battle_axe_diamond | diamond.dmi: weapon.battle axe.diamond | 40 | weapon | gear row |  |  | already a row |
| Dragonbone Battle Axe | Equipment/Weapon/Axes/rm_weapon_battle_axe_dragonbone | dragonbone.dmi: weapon.battle axe.dragonbone | 34 | weapon | gear row |  |  | already a row |
| Dragonfang Battle Axe | Equipment/Weapon/Axes/rm_weapon_battle_axe_dragonfang | dragonfang.dmi: weapon.battle axe.dragonfang | 24 | weapon | gear row |  |  | already a row |
| Gold Battle Axe | Equipment/Weapon/Axes/rm_weapon_battle_axe_gold | gold.dmi: weapon.battle axe.gold | 52 | weapon | gear row |  |  | already a row |
| Hellforged Battle Axe | Equipment/Weapon/Axes/rm_weapon_battle_axe_hell | hell.dmi: weapon.battle axe.hell | 44 | weapon | gear row |  |  | already a row |
| Iron Battle Axe | Equipment/Weapon/Axes/rm_weapon_battle_axe_iron | iron.dmi: weapon.battle axe.iron | 40 | weapon | gear row |  |  | already a row |
| Silver Battle Axe | Equipment/Weapon/Axes/rm_weapon_battle_axe_silver | silver.dmi: weapon.battle axe.silver | 40 | weapon | gear row |  |  | already a row |
| Adamantium Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_adamantium | adamantium.dmi: weapon.hand axe.adamantium | 16 | weapon | gear row |  |  | already a row |
| Bone Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_bone | bone.dmi: weapon.hand axe.bone | 16 | weapon | gear row |  |  | already a row |
| Chitin Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_chitin | chitin.dmi: weapon.hand axe.chitin | 14 | weapon | gear row |  |  | already a row |
| Diamond Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_diamond | diamond.dmi: weapon.hand axe.diamond | 20 | weapon | gear row |  |  | already a row |
| Dragonfang Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_dragonfang | dragonfang.dmi: weapon.hand axe.dragonfang | 12 | weapon | gear row |  |  | already a row |
| Gold Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_gold | gold.dmi: weapon.hand axe.gold | 26 | weapon | gear row |  |  | already a row |
| Hellforged Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_hell | hell.dmi: weapon.hand axe.hell | 22 | weapon | gear row |  |  | already a row |
| Iron Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_iron | iron.dmi: weapon.hand axe.iron | 20 | weapon | gear row |  |  | already a row |
| Silver Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_silver | silver.dmi: weapon.hand axe.silver | 20 | weapon | gear row |  |  | already a row |
| Wooden Hand Axe | Equipment/Weapon/Axes/rm_weapon_hand_axe_wood | wood.dmi: weapon.hand axe.wood | 10 | weapon | gear row |  |  | already a row |
| Bows *(group of 11)* | Equipment/Weapon/Bows |  | 0 | weapon | item row |  |  | already a row |
| BoneBow | Equipment/Weapon/Bows/BoneBow | BoneItems.dmi: BoneBow | 0 | weapon | item row |  | BoneCraft › DblClick | already a row |
| ElfBow | Equipment/Weapon/Bows/ElfBow | WoodItems.dmi: Elf Bow | 20 | weapon | item row |  | Carpentry › DblClick | already a row |
| MetalBow | Equipment/Weapon/Bows/MetalBow | MetalObjects.dmi: MetalBow | 25 | weapon | item row |  | Forge › DblClick | already a row |
| WoodenBow | Equipment/Weapon/Bows/WoodenBow | WoodItems.dmi: WoodBow | 20 | weapon | item row |  | Carpentry › DblClick | already a row |
| Adamantium Bow | Equipment/Weapon/Bows/rm_weapon_bow_adamantium | adamantium.dmi: weapon.bow.adamantium | 12 | weapon | gear row |  |  | already a row |
| Diamond Bow | Equipment/Weapon/Bows/rm_weapon_bow_diamond | diamond.dmi: weapon.bow.diamond | 15 | weapon | gear row |  |  | already a row |
| Dragonbone Bow | Equipment/Weapon/Bows/rm_weapon_bow_dragonbone | dragonbone.dmi: weapon.bow.dragonbone | 13 | weapon | gear row |  |  | already a row |
| Gold Bow | Equipment/Weapon/Bows/rm_weapon_bow_gold | gold.dmi: weapon.bow.gold | 20 | weapon | gear row |  |  | already a row |
| Hellforged Bow | Equipment/Weapon/Bows/rm_weapon_bow_hell | hell.dmi: weapon.bow.hell | 16 | weapon | gear row |  |  | already a row |
| Iron Bow | Equipment/Weapon/Bows/rm_weapon_bow_iron | iron.dmi: weapon.bow.iron | 15 | weapon | gear row |  |  | already a row |
| Silver Bow | Equipment/Weapon/Bows/rm_weapon_bow_silver | silver.dmi: weapon.bow.silver | 15 | weapon | gear row |  |  | already a row |
| Daggers *(group of 16)* | Equipment/Weapon/Daggers |  | 0 | weapon | item row |  |  | already a row |
| AdamantiumDagger | Equipment/Weapon/Daggers/AdamantiumDagger | MetalObjects.dmi: AdamantiumDagger | 0 | weapon | item row |  | Forge › DblClick | already a row |
| BoneDagger | Equipment/Weapon/Daggers/BoneDagger | BoneItems.dmi: BoneDagger | 10 | weapon | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick | already a row |
| ChitinDagger | Equipment/Weapon/Daggers/ChitinDagger | BoneItems.dmi: ChitinDagger | 10 | weapon | item row |  | BoneCraft › DblClick | already a row |
| GoldDagger | Equipment/Weapon/Daggers/GoldDagger | GoldItems.dmi: Gold Dagger | 15 | weapon | item row |  | Forge › DblClick | already a row |
| MetalDagger | Equipment/Weapon/Daggers/MetalDagger | Cave.dmi: Metal Dagger | 10 | weapon | item row |  | Forge › DblClick | already a row |
| SilverDagger | Equipment/Weapon/Daggers/SilverDagger | Cave.dmi: Silver Dagger | 10 | weapon | item row |  | Forge › DblClick | already a row |
| Adamantium Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_adamantium | adamantium.dmi: weapon.dagger.adamantium | 8 | weapon | gear row |  |  | already a row |
| Bone Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_bone | bone.dmi: weapon.dagger.bone | 8 | weapon | gear row |  |  | already a row |
| Chitin Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_chitin | chitin.dmi: weapon.dagger.chitin | 7 | weapon | gear row |  |  | already a row |
| Diamond Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_diamond | diamond.dmi: weapon.dagger.diamond | 10 | weapon | gear row |  |  | already a row |
| Dragonfang Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_dragonfang | dragonfang.dmi: weapon.dagger.dragonfang | 6 | weapon | gear row |  |  | already a row |
| Gold Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_gold | gold.dmi: weapon.dagger.gold | 13 | weapon | gear row |  |  | already a row |
| Hellforged Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_hell | hell.dmi: weapon.dagger.hell | 11 | weapon | gear row |  |  | already a row |
| Iron Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_iron | iron.dmi: weapon.dagger.iron | 10 | weapon | gear row |  |  | already a row |
| Silver Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_silver | silver.dmi: weapon.dagger.silver | 10 | weapon | gear row |  |  | already a row |
| Spiderfang Dagger | Equipment/Weapon/Daggers/rm_weapon_dagger_spiderfang | spiderfang.dmi: weapon.dagger.spiderfang | 5 | weapon | gear row |  |  | already a row |
| DemonicWeapons *(group of 9)* | Equipment/Weapon/DemonicWeapons | DemonicItems.dmi:  | 25 | weapon | item row |  |  | already a row |
| Hell Forged Axe - Supernatural Quality | Equipment/Weapon/DemonicWeapons/Axe | DemonicItems.dmi: Axe | 25 | weapon | item row |  |  | already a row |
| Hell Forged Bow - Supernatural Quality | Equipment/Weapon/DemonicWeapons/Bow | DemonicItems.dmi: Bow | 25 | weapon | item row |  |  | already a row |
| Giant Butcher Knife | Equipment/Weapon/DemonicWeapons/Butcher_Knife | MetalObjects.dmi: Butcher Knife | 125 | weapon | item row |  | Warlord › New | already a row |
| Hell Forged Dagger - Supernatural Quality | Equipment/Weapon/DemonicWeapons/Dagger | DemonicItems.dmi: Dagger | 15 | weapon | item row |  | Chieftain › New | already a row |
| Sword of Destruction - Ungodly Quality | Equipment/Weapon/DemonicWeapons/DestructionSword | DemonicItems.dmi: FireSword | 25 | weapon | item row |  | Lord › New | already a row |
| Hell Forged Mace - Supernatural Quality | Equipment/Weapon/DemonicWeapons/Mace | DemonicItems.dmi: Mace | 25 | weapon | item row |  |  | already a row |
| Soul Eater | Equipment/Weapon/DemonicWeapons/SoulBlade | DemonicItems.dmi: SoulBlade | 25 | weapon | item row |  | Forge › DblClick | already a row |
| Hell Forged Spear - Supernatural Quality | Equipment/Weapon/DemonicWeapons/Spear | DemonicItems.dmi: Spear | 25 | weapon | item row |  |  | already a row |
| Hell Forged Sword - Supernatural Quality | Equipment/Weapon/DemonicWeapons/Sword | DemonicItems.dmi: Sword | 25 | weapon | item row |  |  | already a row |
| Maces *(group of 40)* | Equipment/Weapon/Maces |  | 0 | weapon | item row |  |  | already a row |
| AdamantiumMace | Equipment/Weapon/Maces/AdamantiumMace | MetalObjects.dmi: Adamantium Mace | 25 | weapon | item row |  | Forge › DblClick | already a row |
| AstralStaff | Equipment/Weapon/Maces/AstralStaff | MetalObjects.dmi: AstralStaff | 20 | weapon | item row |  | Lich › New | already a row |
| ChitinMace | Equipment/Weapon/Maces/ChitinMace | BoneItems.dmi: ChitinMace | 20 | weapon | item row |  | BoneCraft › DblClick | already a row |
| GoldMace | Equipment/Weapon/Maces/GoldMace | GoldItems.dmi: GoldMace | 30 | weapon | item row |  | Forge › DblClick | already a row |
| MetalMace | Equipment/Weapon/Maces/MetalMace | MetalObjects.dmi: Mace | 25 | weapon | item row |  | Forge › DblClick, MiscCreate › LegendaryMetalMace | already a row |
| NecroStaff | Equipment/Weapon/Maces/NecroStaff | MetalObjects.dmi: NecroStaff | 20 | weapon | item row |  | Carpentry › DblClick | already a row |
| SilverMace | Equipment/Weapon/Maces/SilverMace | SilverItems.dmi: Silver Mace | 25 | weapon | item row |  | Forge › DblClick | already a row |
| SkullMace | Equipment/Weapon/Maces/SkullMace | BoneItems.dmi: Bone Mace | 20 | weapon | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick | already a row |
| Staff | Equipment/Weapon/Maces/Staff | MetalObjects.dmi: MageStaff | 20 | weapon | item row |  | Carpentry › DblClick | already a row |
| WoodenMace | Equipment/Weapon/Maces/WoodenMace | WoodItems.dmi: Wooden Mace | 10 | weapon | item row |  | Carpentry › DblClick | already a row |
| Crystal Staff | Equipment/Weapon/Maces/rm_magic_crystal_staff | magic.dmi: magic.crystal staff | 20 | weapon | gear row |  |  | already a row |
| Dragon Skull Staff | Equipment/Weapon/Maces/rm_magic_dragon_staff | magic.dmi: magic.dragon staff | 20 | weapon | gear row |  |  | already a row |
| Flame Staff | Equipment/Weapon/Maces/rm_magic_flame_staff | magic.dmi: magic.flame staff | 20 | weapon | gear row |  |  | already a row |
| Dawnbringer | Equipment/Weapon/Maces/rm_magic_holy_mace | magic.dmi: magic.holy mace | 32 | weapon | gear row |  |  | already a row |
| Nature Staff | Equipment/Weapon/Maces/rm_magic_nature_staff | magic.dmi: magic.nature staff | 20 | weapon | gear row |  |  | already a row |
| Orb Staff | Equipment/Weapon/Maces/rm_magic_orb_staff | magic.dmi: magic.orb staff | 20 | weapon | gear row |  |  | already a row |
| Skull Staff | Equipment/Weapon/Maces/rm_magic_skull_staff | magic.dmi: magic.skull staff | 20 | weapon | gear row |  |  | already a row |
| Spider Staff | Equipment/Weapon/Maces/rm_magic_spider_staff | magic.dmi: magic.spider staff | 20 | weapon | gear row |  |  | already a row |
| Adamantium Mace | Equipment/Weapon/Maces/rm_weapon_mace_adamantium | adamantium.dmi: weapon.mace.adamantium | 20 | weapon | gear row |  |  | already a row |
| Skull Mace | Equipment/Weapon/Maces/rm_weapon_mace_bone | bone.dmi: weapon.mace.bone | 20 | weapon | gear row |  |  | already a row |
| Chitin Mace | Equipment/Weapon/Maces/rm_weapon_mace_chitin | chitin.dmi: weapon.mace.chitin | 18 | weapon | gear row |  |  | already a row |
| Diamond Mace | Equipment/Weapon/Maces/rm_weapon_mace_diamond | diamond.dmi: weapon.mace.diamond | 25 | weapon | gear row |  |  | already a row |
| Gold Mace | Equipment/Weapon/Maces/rm_weapon_mace_gold | gold.dmi: weapon.mace.gold | 32 | weapon | gear row |  |  | already a row |
| Hellforged Mace | Equipment/Weapon/Maces/rm_weapon_mace_hell | hell.dmi: weapon.mace.hell | 28 | weapon | gear row |  |  | already a row |
| Iron Mace | Equipment/Weapon/Maces/rm_weapon_mace_iron | iron.dmi: weapon.mace.iron | 25 | weapon | gear row |  |  | already a row |
| Silver Mace | Equipment/Weapon/Maces/rm_weapon_mace_silver | silver.dmi: weapon.mace.silver | 25 | weapon | gear row |  |  | already a row |
| Wooden Club | Equipment/Weapon/Maces/rm_weapon_mace_wood | wood.dmi: weapon.mace.wood | 12 | weapon | gear row |  |  | already a row |
| Adamantium Morning Star | Equipment/Weapon/Maces/rm_weapon_morning_star_adamantium | adamantium.dmi: weapon.morning star.adamantium | 22 | weapon | gear row |  |  | already a row |
| Diamond Morning Star | Equipment/Weapon/Maces/rm_weapon_morning_star_diamond | diamond.dmi: weapon.morning star.diamond | 28 | weapon | gear row |  |  | already a row |
| Gold Morning Star | Equipment/Weapon/Maces/rm_weapon_morning_star_gold | gold.dmi: weapon.morning star.gold | 36 | weapon | gear row |  |  | already a row |
| Hellforged Morning Star | Equipment/Weapon/Maces/rm_weapon_morning_star_hell | hell.dmi: weapon.morning star.hell | 31 | weapon | gear row |  |  | already a row |
| Iron Morning Star | Equipment/Weapon/Maces/rm_weapon_morning_star_iron | iron.dmi: weapon.morning star.iron | 28 | weapon | gear row |  |  | already a row |
| Silver Morning Star | Equipment/Weapon/Maces/rm_weapon_morning_star_silver | silver.dmi: weapon.morning star.silver | 28 | weapon | gear row |  |  | already a row |
| Adamantium Warhammer | Equipment/Weapon/Maces/rm_weapon_warhammer_adamantium | adamantium.dmi: weapon.warhammer.adamantium | 28 | weapon | gear row |  |  | already a row |
| Diamond Warhammer | Equipment/Weapon/Maces/rm_weapon_warhammer_diamond | diamond.dmi: weapon.warhammer.diamond | 35 | weapon | gear row |  |  | already a row |
| Dragonbone Warhammer | Equipment/Weapon/Maces/rm_weapon_warhammer_dragonbone | dragonbone.dmi: weapon.warhammer.dragonbone | 30 | weapon | gear row |  |  | already a row |
| Gold Warhammer | Equipment/Weapon/Maces/rm_weapon_warhammer_gold | gold.dmi: weapon.warhammer.gold | 46 | weapon | gear row |  |  | already a row |
| Hellforged Warhammer | Equipment/Weapon/Maces/rm_weapon_warhammer_hell | hell.dmi: weapon.warhammer.hell | 38 | weapon | gear row |  |  | already a row |
| Iron Warhammer | Equipment/Weapon/Maces/rm_weapon_warhammer_iron | iron.dmi: weapon.warhammer.iron | 35 | weapon | gear row |  |  | already a row |
| Silver Warhammer | Equipment/Weapon/Maces/rm_weapon_warhammer_silver | silver.dmi: weapon.warhammer.silver | 35 | weapon | gear row |  |  | already a row |
| Picks *(group of 8)* | Equipment/Weapon/Picks |  | 0 | weapon | item row |  |  | already a row |
| GoldPickAxe | Equipment/Weapon/Picks/GoldPickAxe | GoldItems.dmi: Gold Pick | 30 | weapon | item row |  | Forge › DblClick | already a row |
| PickAxe | Equipment/Weapon/Picks/PickAxe | Cave.dmi: Metal Pick | 25 | weapon | item row |  | Forge › DblClick | already a row |
| WoodenPickAxe | Equipment/Weapon/Picks/WoodenPickAxe | WoodItems.dmi: Wooden Pick | 10 | weapon | item row |  | Carpentry › DblClick | already a row |
| Adamantium Pickaxe | Equipment/Weapon/Picks/rm_weapon_pickaxe_adamantium | adamantium.dmi: weapon.pickaxe.adamantium | 24 | weapon | gear row |  |  | already a row |
| Gold Pickaxe | Equipment/Weapon/Picks/rm_weapon_pickaxe_gold | gold.dmi: weapon.pickaxe.gold | 39 | weapon | gear row |  |  | already a row |
| Hellforged Pickaxe | Equipment/Weapon/Picks/rm_weapon_pickaxe_hell | hell.dmi: weapon.pickaxe.hell | 33 | weapon | gear row |  |  | already a row |
| Iron Pickaxe | Equipment/Weapon/Picks/rm_weapon_pickaxe_iron | iron.dmi: weapon.pickaxe.iron | 30 | weapon | gear row |  |  | already a row |
| Silver Pickaxe | Equipment/Weapon/Picks/rm_weapon_pickaxe_silver | silver.dmi: weapon.pickaxe.silver | 30 | weapon | gear row |  |  | already a row |
| Spears *(group of 32)* | Equipment/Weapon/Spears |  | 0 | weapon | item row |  |  | already a row |
| AdamantiumSpear | Equipment/Weapon/Spears/AdamantiumSpear | MetalObjects.dmi: Adamantium Spear | 25 | weapon | item row |  | Forge › DblClick | already a row |
| Bloodwhisker | Equipment/Weapon/Spears/Bloodwhisker | Marine.dmi: Marine Spear | 25 | weapon | item row |  | King › New | already a row |
| BoneSpear | Equipment/Weapon/Spears/BoneSpear | BoneSpear.dmi: Poor | 15 | weapon | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick | already a row |
| ChitinSpear | Equipment/Weapon/Spears/ChitinSpear | BoneItems.dmi: Chitin Spear | 10 | weapon | item row |  | BoneCraft › DblClick | already a row |
| ElfSpear | Equipment/Weapon/Spears/ElfSpear | WoodItems.dmi: Elf Spear | 10 | weapon | item row |  | Carpentry › DblClick | already a row |
| GoldSpear | Equipment/Weapon/Spears/GoldSpear | GoldItems.dmi: Gold Spear | 30 | weapon | item row |  | Forge › DblClick | already a row |
| MetalSpear | Equipment/Weapon/Spears/MetalSpear | MetalObjects.dmi: Metal Spear | 25 | weapon | item row |  | Forge › DblClick, MiscCreate › LegendaryMetalSpear | already a row |
| SilverSpear | Equipment/Weapon/Spears/SilverSpear | SilverItems.dmi: Silver Spear | 25 | weapon | item row |  | Forge › DblClick | already a row |
| Spear | Equipment/Weapon/Spears/Spear | Spear.dmi: Poor | 20 | weapon | item row |  | mob › Death | already a row |
| WoodenSpear | Equipment/Weapon/Spears/WoodenSpear | WoodItems.dmi: Wood Spear | 15 | weapon | item row |  | Carpentry › DblClick | already a row |
| Stormcaller Spear | Equipment/Weapon/Spears/rm_magic_storm_spear | magic.dmi: magic.storm spear | 20 | weapon | gear row |  |  | already a row |
| Adamantium Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_adamantium | adamantium.dmi: weapon.halberd.adamantium | 32 | weapon | gear row |  |  | already a row |
| Bone Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_bone | bone.dmi: weapon.halberd.bone | 32 | weapon | gear row |  |  | already a row |
| Chitin Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_chitin | chitin.dmi: weapon.halberd.chitin | 28 | weapon | gear row |  |  | already a row |
| Diamond Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_diamond | diamond.dmi: weapon.halberd.diamond | 40 | weapon | gear row |  |  | already a row |
| Dragonbone Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_dragonbone | dragonbone.dmi: weapon.halberd.dragonbone | 34 | weapon | gear row |  |  | already a row |
| Dragonfang Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_dragonfang | dragonfang.dmi: weapon.halberd.dragonfang | 24 | weapon | gear row |  |  | already a row |
| Gold Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_gold | gold.dmi: weapon.halberd.gold | 52 | weapon | gear row |  |  | already a row |
| Hellforged Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_hell | hell.dmi: weapon.halberd.hell | 44 | weapon | gear row |  |  | already a row |
| Iron Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_iron | iron.dmi: weapon.halberd.iron | 40 | weapon | gear row |  |  | already a row |
| Silver Halberd | Equipment/Weapon/Spears/rm_weapon_halberd_silver | silver.dmi: weapon.halberd.silver | 40 | weapon | gear row |  |  | already a row |
| Adamantium Spear | Equipment/Weapon/Spears/rm_weapon_spear_adamantium | adamantium.dmi: weapon.spear.adamantium | 16 | weapon | gear row |  |  | already a row |
| Bone Spear | Equipment/Weapon/Spears/rm_weapon_spear_bone | bone.dmi: weapon.spear.bone | 16 | weapon | gear row |  |  | already a row |
| Chitin Spear | Equipment/Weapon/Spears/rm_weapon_spear_chitin | chitin.dmi: weapon.spear.chitin | 14 | weapon | gear row |  |  | already a row |
| Diamond Spear | Equipment/Weapon/Spears/rm_weapon_spear_diamond | diamond.dmi: weapon.spear.diamond | 20 | weapon | gear row |  |  | already a row |
| Dragonfang Spear | Equipment/Weapon/Spears/rm_weapon_spear_dragonfang | dragonfang.dmi: weapon.spear.dragonfang | 12 | weapon | gear row |  |  | already a row |
| Gold Spear | Equipment/Weapon/Spears/rm_weapon_spear_gold | gold.dmi: weapon.spear.gold | 26 | weapon | gear row |  |  | already a row |
| Hellforged Spear | Equipment/Weapon/Spears/rm_weapon_spear_hell | hell.dmi: weapon.spear.hell | 22 | weapon | gear row |  |  | already a row |
| Iron Spear | Equipment/Weapon/Spears/rm_weapon_spear_iron | iron.dmi: weapon.spear.iron | 20 | weapon | gear row |  |  | already a row |
| Silver Spear | Equipment/Weapon/Spears/rm_weapon_spear_silver | silver.dmi: weapon.spear.silver | 20 | weapon | gear row |  |  | already a row |
| Spiderfang Spear | Equipment/Weapon/Spears/rm_weapon_spear_spiderfang | spiderfang.dmi: weapon.spear.spiderfang | 10 | weapon | gear row |  |  | already a row |
| Wooden Spear | Equipment/Weapon/Spears/rm_weapon_spear_wood | wood.dmi: weapon.spear.wood | 10 | weapon | gear row |  |  | already a row |
| Swords *(group of 43)* | Equipment/Weapon/Swords |  | 0 | weapon | item row |  |  | already a row |
| AdamantiumSword | Equipment/Weapon/Swords/AdamantiumSword | MetalObjects.dmi: Adamantium Sword | 20 | weapon | item row |  | Forge › DblClick | already a row |
| BoneSword | Equipment/Weapon/Swords/BoneSword | BoneItems.dmi: BoneSword | 20 | weapon | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick | already a row |
| ChitinSword | Equipment/Weapon/Swords/ChitinSword | BoneItems.dmi: ChitinSword | 20 | weapon | item row |  | BoneCraft › DblClick | already a row |
| Gladius | Equipment/Weapon/Swords/Gladius | MetalObjects.dmi: Gladius | 20 | weapon | item row |  | Forge › DblClick | already a row |
| GoblinSword | Equipment/Weapon/Swords/GoblinSword | GoblinSword.dmi: Swords | 25 | weapon | item row |  | Forge › DblClick | already a row |
| GoldGladius | Equipment/Weapon/Swords/GoldGladius | GoldItems.dmi: Gold Gladius | 30 | weapon | item row |  | Forge › DblClick | already a row |
| GoldStraightSword | Equipment/Weapon/Swords/GoldStraightSword | WoodItems.dmi: Wooden Sword | 10 | weapon | 2006 (Items/Equipment Lists.dm:30) |  | Forge › DblClick | values mixed with code (Code/Items/Equipment Lists.dm:34) |
| Lichbane | Equipment/Weapon/Swords/Lichbane | HolyItems.dmi: HolySword | 25 | weapon | item row |  | Commander › New | already a row |
| SilverSword | Equipment/Weapon/Swords/SilverSword | SilverItems.dmi: Silver Sword | 25 | weapon | item row |  | Forge › DblClick | already a row |
| StraightSword | Equipment/Weapon/Swords/StraightSword | MetalObjects.dmi: Sword | 25 | weapon | item row |  | Forge › DblClick, MiscCreate › LegendaryMetalSword | already a row |
| WoodenSword | Equipment/Weapon/Swords/WoodenSword | WoodItems.dmi: Wooden Sword | 12 | weapon | item row |  | Carpentry › DblClick | already a row |
| Flametongue | Equipment/Weapon/Swords/rm_magic_flame_sword | magic.dmi: magic.flame sword | 25 | weapon | gear row |  |  | already a row |
| Runeblade | Equipment/Weapon/Swords/rm_magic_rune_sword | magic.dmi: magic.rune sword | 30 | weapon | gear row |  |  | already a row |
| Voidedge | Equipment/Weapon/Swords/rm_magic_void_blade | magic.dmi: magic.void blade | 20 | weapon | gear row |  |  | already a row |
| Adamantium Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_adamantium | adamantium.dmi: weapon.arming sword.adamantium | 20 | weapon | gear row |  |  | already a row |
| Bone Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_bone | bone.dmi: weapon.arming sword.bone | 20 | weapon | gear row |  |  | already a row |
| Chitin Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_chitin | chitin.dmi: weapon.arming sword.chitin | 18 | weapon | gear row |  |  | already a row |
| Diamond Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_diamond | diamond.dmi: weapon.arming sword.diamond | 25 | weapon | gear row |  |  | already a row |
| Dragonfang Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_dragonfang | dragonfang.dmi: weapon.arming sword.dragonfang | 15 | weapon | gear row |  |  | already a row |
| Gold Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_gold | gold.dmi: weapon.arming sword.gold | 32 | weapon | gear row |  |  | already a row |
| Hellforged Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_hell | hell.dmi: weapon.arming sword.hell | 28 | weapon | gear row |  |  | already a row |
| Iron Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_iron | iron.dmi: weapon.arming sword.iron | 25 | weapon | gear row |  |  | already a row |
| Silver Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_silver | silver.dmi: weapon.arming sword.silver | 25 | weapon | gear row |  |  | already a row |
| Spiderfang Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_spiderfang | spiderfang.dmi: weapon.arming sword.spiderfang | 12 | weapon | gear row |  |  | already a row |
| Wooden Sword | Equipment/Weapon/Swords/rm_weapon_arming_sword_wood | wood.dmi: weapon.arming sword.wood | 12 | weapon | gear row |  |  | already a row |
| Adamantium Longsword | Equipment/Weapon/Swords/rm_weapon_longsword_adamantium | adamantium.dmi: weapon.longsword.adamantium | 24 | weapon | gear row |  |  | already a row |
| Diamond Longsword | Equipment/Weapon/Swords/rm_weapon_longsword_diamond | diamond.dmi: weapon.longsword.diamond | 30 | weapon | gear row |  |  | already a row |
| Dragonbone Longsword | Equipment/Weapon/Swords/rm_weapon_longsword_dragonbone | dragonbone.dmi: weapon.longsword.dragonbone | 26 | weapon | gear row |  |  | already a row |
| Dragonfang Longsword | Equipment/Weapon/Swords/rm_weapon_longsword_dragonfang | dragonfang.dmi: weapon.longsword.dragonfang | 18 | weapon | gear row |  |  | already a row |
| Gold Longsword | Equipment/Weapon/Swords/rm_weapon_longsword_gold | gold.dmi: weapon.longsword.gold | 39 | weapon | gear row |  |  | already a row |
| Hellforged Longsword | Equipment/Weapon/Swords/rm_weapon_longsword_hell | hell.dmi: weapon.longsword.hell | 33 | weapon | gear row |  |  | already a row |
| Iron Longsword | Equipment/Weapon/Swords/rm_weapon_longsword_iron | iron.dmi: weapon.longsword.iron | 30 | weapon | gear row |  |  | already a row |
| Silver Longsword | Equipment/Weapon/Swords/rm_weapon_longsword_silver | silver.dmi: weapon.longsword.silver | 30 | weapon | gear row |  |  | already a row |
| Adamantium Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_adamantium | adamantium.dmi: weapon.scimitar.adamantium | 20 | weapon | gear row |  |  | already a row |
| Bone Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_bone | bone.dmi: weapon.scimitar.bone | 20 | weapon | gear row |  |  | already a row |
| Chitin Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_chitin | chitin.dmi: weapon.scimitar.chitin | 18 | weapon | gear row |  |  | already a row |
| Diamond Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_diamond | diamond.dmi: weapon.scimitar.diamond | 25 | weapon | gear row |  |  | already a row |
| Dragonfang Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_dragonfang | dragonfang.dmi: weapon.scimitar.dragonfang | 15 | weapon | gear row |  |  | already a row |
| Gold Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_gold | gold.dmi: weapon.scimitar.gold | 32 | weapon | gear row |  |  | already a row |
| Hellforged Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_hell | hell.dmi: weapon.scimitar.hell | 28 | weapon | gear row |  |  | already a row |
| Iron Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_iron | iron.dmi: weapon.scimitar.iron | 25 | weapon | gear row |  |  | already a row |
| Silver Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_silver | silver.dmi: weapon.scimitar.silver | 25 | weapon | gear row |  |  | already a row |
| Spiderfang Scimitar | Equipment/Weapon/Swords/rm_weapon_scimitar_spiderfang | spiderfang.dmi: weapon.scimitar.spiderfang | 12 | weapon | gear row |  |  | already a row |

## Furniture

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Furniture *(group of 13)* | Furniture |  | 0 |  | 2006 (Turfs.dm:3120) |  |  | no values of its own |
| Beds *(group of 5)* | Furniture/Beds |  | 0 |  | item row |  |  | already a row |
| GoldBed | Furniture/Beds/GoldBed | GoldItems.dmi: Bed | 50 |  | item row | DblClick | Forge › DblClick | already a row |
| LeatherBed | Furniture/Beds/LeatherBed | Cave.dmi: LeatherBed | 25 |  | item row | DblClick | LeatherWorks › DblClick | already a row |
| MetalBed | Furniture/Beds/MetalBed | MetalObjects.dmi: Bed | 50 |  | item row | DblClick | Forge › DblClick | already a row |
| SleepingBag | Furniture/Beds/SleepingBag | Cave.dmi: SleepingBag | 5 |  | item row | DblClick, New | LeatherWorks › DblClick | already a row |
| WoodenBed | Furniture/Beds/WoodenBed | Cave.dmi: Bed | 50 |  | item row | DblClick | Carpentry › DblClick | already a row |
| Chairs *(group of 3)* | Furniture/Chairs |  | 0 |  | 2006 (Turfs.dm:4752) |  |  | no values of its own |
| BoneThrone | Furniture/Chairs/BoneThrone | BoneItems.dmi: Throne | 50 |  | item row | DblClick | BoneCraft › DblClick, BuiltInBonecraft › DblClick | already a row |
| GoldenThrone | Furniture/Chairs/GoldenThrone | RoyalItems.dmi: Throne | 50 |  | item row | DblClick | Forge › DblClick | already a row |
| WoodenChair | Furniture/Chairs/WoodenChair | Cave.dmi: Chair | 15 |  | item row | DblClick | Carpentry › DblClick | already a row |
| Doors *(group of 6)* | Furniture/Doors |  | 0 |  | item row | Death, Del, New |  | already a row |
| BoneDoor | Furniture/Doors/BoneDoor | Cave.dmi: BoneDoor | 100 |  | item row | DblClick | BoneCraft › DblClick, BuiltInBonecraft › DblClick, MiscCreate › BoneDoor | already a row |
| GoldDoor | Furniture/Doors/GoldDoor | GoldItems.dmi: GoldDoor | 100 |  | item row | DblClick | Forge › DblClick | already a row |
| MetalDoor | Furniture/Doors/MetalDoor | MetalObjects.dmi: MetalDoor | 100 |  | item row | DblClick | Forge › DblClick, MiscCreate › MetalDoor | already a row |
| StoneDoor | Furniture/Doors/StoneDoor | StoneItems.dmi: StoneDoor | 100 |  | item row | DblClick, Del, New | Masonary › DblClick | already a row |
| TrapDoor | Furniture/Doors/TrapDoor | Cave.dmi: ClosedTrapDoor | 100 |  | item row | DblClick |  | already a row |
| WoodenDoor | Furniture/Doors/WoodenDoor | Cave.dmi: WoodenDoor | 100 |  | item row | DblClick | Carpentry › DblClick, MiscCreate › WoodenDoor | already a row |
| Fences *(group of 3)* | Furniture/Fences |  | 0 |  | 2006 (Turfs.dm:3121) |  |  | no values of its own |
| MetalFence | Furniture/Fences/MetalFence | Fences.dmi: Metal Fence | 25 |  | item row | DblClick | Forge › DblClick | already a row |
| StoneFence | Furniture/Fences/StoneFence | Fences.dmi: Stone Fence | 25 |  | item row | DblClick | Masonary › DblClick | already a row |
| WoodenFence | Furniture/Fences/WoodenFence | Fences.dmi: Wooden Fence | 25 |  | item row | DblClick | Carpentry › DblClick | already a row |
| Pillars *(group of 7)* | Furniture/Pillars |  | 0 |  | 2006 (Turfs.dm:4520) |  | Player › RemasterBuildPiece | no values of its own |
| Pillar | Furniture/Pillars/DwarfPillar | StoneItems.dmi: Pillar | 50 |  | item row | DblClick | Masonary › DblClick, Player › RemasterBuildPiece | already a row |
| Pillar | Furniture/Pillars/GoblinPillar | StoneItems.dmi: Pillar | 50 |  | item row | DblClick | Player › RemasterBuildPiece | already a row |
| Golden Pillar | Furniture/Pillars/GoldPillar | GoldItems.dmi: Pillar | 50 |  | item row | DblClick | Forge › DblClick | already a row |
| Anti-Astral Stone | Furniture/Pillars/PortalStone | Book.dmi: PortalStone | 50 |  | item row | DblClick | Masonary › DblClick | already a row |
| wall support | Furniture/Pillars/RemasterWallHold |  | 999 |  | item row |  |  | already a row |
| Statue | Furniture/Pillars/Statue | Statue.dmi:  | 50 |  | item row | DblClick | Masonary › DblClick | already a row |
| Support beam | Furniture/Pillars/WoodenBeam | Cave.dmi: Wood Post | 20 |  | item row |  | Player › RemasterBuildBeam | already a row |
| Posts *(group of 6)* | Furniture/Posts |  | 0 |  | 2006 (Turfs.dm:4685) | DblClick |  | no values of its own |
| BoneTrainingPost | Furniture/Posts/BoneTrainingPost | Cave.dmi: BonePost | 50 |  | item row |  | BoneCraft › DblClick, BuiltInBonecraft › DblClick | already a row |
| GoldTrainingPost | Furniture/Posts/GoldTrainingPost | GoldItems.dmi: Gold Training Post | 50 |  | item row |  | Forge › DblClick | already a row |
| MetalTrainingPost | Furniture/Posts/MetalTrainingPost | MetalObjects.dmi: Metal Training Post | 50 |  | item row |  | Forge › DblClick | already a row |
| SilkTrainingPost | Furniture/Posts/SilkTrainingPost | Cave.dmi: SilkPost | 50 |  | item row |  | Post › DblClick | already a row |
| SilverTrainingPost | Furniture/Posts/SilverTrainingPost | SilverItems.dmi: Silver Training Post | 50 |  | item row |  | Forge › DblClick | already a row |
| WoodTrainingPost | Furniture/Posts/WoodTrainingPost | Cave.dmi: Wood Post | 50 |  | item row |  | Carpentry › DblClick | already a row |
| Mine cart | Furniture/RemasterCart | Cave.dmi: Wagon | 999 |  | item row | New, RemasterCartBusiest, RemasterCartGo, RemasterCartNearestLoad, RemasterCartRun | Player › RemasterBuildPiece | already a row |
| Cart stop | Furniture/RemasterCartStop | Cave.dmi: sign | 999 |  | item row | Del, New | Player › RemasterBuildPiece | already a row |
| Cobweb | Furniture/RemasterCobweb | Decoration1.dmi:  | 999 |  | item row |  | Player › RemasterBuildPiece | already a row |
| Dragon hoard | Furniture/RemasterHoard | GoldItems.dmi: Coin | 999 |  | item row | RemasterTreasure | Player › RemasterBuildPiece | already a row |
| Lift head | Furniture/RemasterLiftHead | Cave.dmi: Shaft | 999 |  | item row |  | Player › RemasterBuildLift | already a row |
| drive piece *(group of 6)* | Furniture/RemasterPower | Cave.dmi: Shaft | 999 |  | item row | Del, New, PowerDemand, PowerSupply | Player › RemasterBuildPower | already a row |
| Axle | Furniture/RemasterPower/Axle | Cave.dmi: Shaft | 999 |  | item row |  |  | already a row |
| Bellows | Furniture/RemasterPower/Bellows | Cave.dmi: Shaft | 999 |  | item row | PowerDemand |  | already a row |
| Rune dynamo | Furniture/RemasterPower/Dynamo | Cave.dmi: Shaft | 999 |  | item row | PowerDemand |  | already a row |
| Water wheel | Furniture/RemasterPower/Wheel | Cave.dmi: Shaft | 999 |  | item row | PowerSupply |  | already a row |
| Lift winch | Furniture/RemasterPower/Winch | Cave.dmi: Shaft | 999 |  | item row | Del, PowerDemand | Player › RemasterBuildLift | already a row |
| Windmill | Furniture/RemasterPower/Windmill | Cave.dmi: Shaft | 999 |  | item row | PowerSupply |  | already a row |
| Tables *(group of 1)* | Furniture/Tables |  | 0 |  | 2006 (Turfs.dm:4720) |  |  | no values of its own |
| Table | Furniture/Tables/Table | Cave.dmi: Table | 30 |  | item row | DblClick | Admin › MakeChess, Carpentry › DblClick | already a row |

## Shafts

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Shafts *(group of 16)* | Shafts |  | 0 |  | 2006 (Turfs.dm:747) |  |  | no values of its own |
| AstralBook | Shafts/AstralBook | Book.dmi: AstralBook | 5 |  | item row | DblClick |  | already a row |
| DoorKey | Shafts/DoorKey | MetalObjects.dmi: Key | 5 |  | item row | DblClick | BoneDoor › DblClick, TrapDoor › DblClick | already a row |
| EngineeredOrgan | Shafts/EngineeredOrgan | Devourer.dmi: Organ | 0 |  | item row | DblClick | CreateOrgan › DblClick | already a row |
| Flag | Shafts/Flag | Flags.dmi: Good Flag | 7 |  | item row | DblClick |  | already a row |
| LeatherFlask | Shafts/LeatherFlask | LeatherItems.dmi: Flask | 5 |  | item row | DblClick | LeatherWorks › DblClick | already a row |
| LockPick | Shafts/LockPick | Cave.dmi: LockPick | 5 |  | item row | DblClick | BoneCraft › DblClick, BuiltInBonecraft › DblClick | already a row |
| MagicScroll | Shafts/MagicScroll | Book.dmi: Scroll | 2 |  | item row | DblClick | Carpentry › DblClick | already a row |
| MetalFlask | Shafts/MetalFlask | LeatherItems.dmi: Flask | 5 |  | item row | DblClick | Forge › DblClick | already a row |
| MobileSandKing | Shafts/MobileSandKing | Book.dmi: MobileSand | 5 |  | item row |  |  | already a row |
| Dormant Cocoon | Shafts/PortableDevourerCacoon | Eggs.dmi: Devourer | 0 |  | item row | DblClick | CreateZombieCacoon › DblClick | already a row |
| Sign | Shafts/Sign | Cave.dmi: sign | 5 |  | item row | DblClick | Carpentry › DblClick | already a row |
| Spade | Shafts/Spade | MetalObjects.dmi: Spade | 7 |  | item row | DblClick | Forge › DblClick | already a row |
| SpearHead | Shafts/SpearHead | Cave.dmi: SpearHead | 5 |  | item row | DblClick |  | already a row |
| SpearShaft | Shafts/SpearShaft | Cave.dmi: Shaft | 5 |  | item row | DblClick |  | already a row |
| WoodenBucket | Shafts/WoodenBucket | WoodItems.dmi: Bucket | 7 |  | item row | DblClick | Carpentry › DblClick | already a row |
| WoodenSpade | Shafts/WoodenSpade | Cave.dmi: Spade | 5 |  | item row | DblClick | Carpentry › DblClick | already a row |

## Traps

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Traps *(group of 8)* | Traps |  | 0 |  | item row |  |  | already a row |
| BST | Traps/BST | Cave.dmi: BST | 0 |  | item row | New | mob › CreateBST, turf › MouseDrag | already a row |
| CacoonTrap | Traps/CacoonTrap | Devourer.dmi: TinyCacoon | 0 |  | item row | New | Player › RemasterBuildPiece, mob › CreateCacoonTrap | already a row |
| Cages *(group of 5)* | Traps/Cages |  | 0 |  | 2006 (Turfs.dm:560) | DblClick |  | values mixed with code (Code/Turfs.dm:561) |
| BoneCage | Traps/Cages/BoneCage | BoneItems.dmi: Cage | 40 |  | item row |  | BoneCraft › DblClick | already a row |
| Cacoon | Traps/Cages/Cacoon | Spiders.dmi: Cage | 25 |  | item row |  | Cacoon › DblClick, Player › RemasterBuildPiece | already a row |
| GoldCage | Traps/Cages/GoldCage | GoldItems.dmi: Cage | 50 |  | item row |  | Forge › DblClick | already a row |
| MetalCage | Traps/Cages/MetalCage | MetalObjects.dmi: Cage | 50 |  | item row |  | Forge › DblClick | already a row |
| WoodenCage | Traps/Cages/WoodenCage | Cave.dmi: Cage | 40 |  | item row |  | Carpentry › DblClick | already a row |
| PitTrap | Traps/PitTrap | Cave.dmi: Hole | 0 |  | item row | New | Player › RemasterBuildPiece, mob › CreatePit | already a row |
| Sticky web | Traps/RemasterWeb | Decoration1.dmi:  | 0 |  | item row | New, RemasterWebCatch, RemasterWebWatch | Player › RemasterBuildPiece | already a row |
| RibTrap | Traps/RibTrap | Cave.dmi: RibTrap | 0 |  | item row | New | mob › CreateRib, turf › MouseDrag | already a row |
| Spikes *(group of 1)* | Traps/Spikes |  | 0 |  | 2006 (Turfs.dm:721) |  |  | no values of its own |
| WoodenSpike | Traps/Spikes/WoodenSpike | Cave.dmi: Spike | 5 |  | item row | DblClick | Carpentry › DblClick | already a row |
| StoneTrap | Traps/StoneTrap | Cave.dmi: FallTrap | 0 |  | item row | New | mob › CreateStone, turf › MouseDrag | already a row |

## Bones

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Bones *(group of 9)* | Bones |  | 0 | bone | 2006 (Creatures/Death.dm:286) | DblClick, New |  | no values of its own |
| BeastFang *(group of 2)* | Bones/BeastFang | beastparts.dmi:  | 3 | bone | item row |  |  | already a row |
| Dragon Tooth *(group of 1)* | Bones/BeastFang/DragonTooth | beastparts.dmi: tooth | 3 | bone | item row |  | RmButcherBeast | already a row |
| Dragon Claw | Bones/BeastFang/DragonTooth/DragonClaw | beastparts.dmi: claw | 4 | bone | item row |  | RmButcherBeast | already a row |
| Spider Fang | Bones/BeastFang/SpiderFang | beastparts.dmi: fang | 2 | bone | item row |  | RmButcherBeast | already a row |
| BloodyLimb | Bones/BloodyLimb | Blood.dmi: Arm | 5 | bone | item row |  | Monsters › LimbFling, RemasterTakeLimb, mob › LimbFling | already a row |
| Bones *(group of 1)* | Bones/Bones | Cave.dmi: Bone | 10 | bone | item row |  | MiscCreate › Bones, Monsters › RmChainBump_Bump, mob › MakeBody | already a row |
| Dragon Bones | Bones/Bones/DragonBones | beastparts.dmi: dragonbones | 12 | bone | item row |  | RmButcherBeast | already a row |
| Dragon Heart | Bones/DragonHeart | beastparts.dmi: heart | 15 | bone | item row |  | RmButcherBeast | already a row |
| Dragon Scales | Bones/DragonScales | beastparts.dmi: scales-red | 6 | bone | item row |  | RmButcherBeast | already a row |
| Head | Bones/Head | Heads.dmi: FrogManHead | 10 | bone | item row |  |  | already a row |
| Shell | Bones/Shell | Cave.dmi: Shell | 10 | bone | item row |  | RmButcherBeast | already a row |
| Skull | Bones/Skull | Cave.dmi: Skull | 10 | bone | item row |  | Bones › DblClick, mob › MakeBody | already a row |
| SkullPile | Bones/SkullPile | Cave.dmi: SkullPile | 10 | bone | item row |  |  | already a row |

## gems

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| gems *(group of 10)* | gems |  | 0 | gem | 2006 (Turfs.dm:5106) | New |  | no values of its own |
| Diamond | gems/Diamond | Cave.dmi: Diamond | 10 | gem | item row | DblClick | GemCutter › DblClick | already a row |
| DiamondRing | gems/DiamondRing | Jewelry.dmi: Diamond Ring | 5 | gem | item row | DblClick | GemCutter › DblClick | already a row |
| Emerald | gems/Emerald | Cave.dmi: Emerald | 10 | gem | item row | DblClick | GemCutter › DblClick | already a row |
| EmeraldRing | gems/EmeraldRing | Jewelry.dmi: Emerald Ring | 5 | gem | item row | DblClick | GemCutter › DblClick | already a row |
| PlantFibreRing | gems/PlantFibreRing | Jewelry.dmi: Lycan Ring | 5 | gem | item row | DblClick | GemCutter › DblClick | already a row |
| Ruby | gems/Ruby | Cave.dmi: Ruby | 10 | gem | item row | DblClick | GemCutter › DblClick | already a row |
| RubyRing | gems/RubyRing | Jewelry.dmi: Ruby Ring | 5 | gem | item row | DblClick | GemCutter › DblClick | already a row |
| UnCutDiamond | gems/UnCutDiamond | Cave.dmi: Un-CutDiamond | 10 | gem | item row | DblClick | Monsters › RmChainBump_Bump, client › Click | already a row |
| UnCutEmerald | gems/UnCutEmerald | Cave.dmi: Un-CutEmerald | 10 | gem | item row | DblClick | Monsters › RmChainBump_Bump, client › Click | already a row |
| UnCutRuby | gems/UnCutRuby | Cave.dmi: Un-CutRuby | 10 | gem | item row | DblClick | Monsters › RmChainBump_Bump, client › Click | already a row |

## Potions

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Potions *(group of 7)* | Potions |  | 0 |  | 2006 (Turfs.dm:2304) |  |  | no values of its own |
| Immunity To Devourer Potion | Potions/DevourerPotion | Farm Items.dmi: PurplePotion | 10 |  | item row | DblClick | MiscCreate › ImmuneToDevPotion | already a row |
| Empty Bottle | Potions/EmptyBottle | Farm Items.dmi: Empty | 10 |  | item row | DblClick | MiscCreate › EmptyBottle | already a row |
| Potion of Eternal Life | Potions/EternalLifePotion | Farm Items.dmi: SparklePotion | 10 |  | item row | DblClick |  | already a row |
| Potion of Restoration | Potions/HealPotion | Farm Items.dmi: BluePotion | 10 |  | item row | DblClick |  | already a row |
| Potion of LongLife | Potions/LifePotion | Farm Items.dmi: RedPotion | 10 |  | item row | DblClick | MiscCreate › LonglifePotion | already a row |
| Brew | Potions/RemasterBrew | Farm Items.dmi: Empty | 10 |  | item row |  | Player › RemasterCauldronCommand | already a row |
| Vampirism Cure | Potions/VampirismCure | Farm Items.dmi: BluePotion | 10 |  | item row | DblClick | MiscCreate › VampCurePotion | already a row |

## Plants

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Plants *(group of 4)* | Plants |  | 0 |  | item row | New, PlantRegen | RemasterWildPlant | already a row |
| GarlicPlant | Plants/GarlicPlant | Cave.dmi: Garlic Plant | 10 |  | item row | DblClick | MiscCreate › Garlic, obj › GarlicGrow | already a row |
| GrapeVine | Plants/GrapeVine | Cave.dmi: PPlant1 | 10 |  | item row | DblClick, New | MiscCreate › Grapes, Monsters › RemasterHarvest, RemasterAwayGrow +1 | already a row |
| RemasterHerbPlant *(group of 3)* | Plants/RemasterHerbPlant | Cave.dmi: Garlic Plant | 0 |  | item row | DblClick, New, Pick, RemasterHerbRegrow |  | already a row |
| Athelas | Plants/RemasterHerbPlant/Athelas | Cave.dmi: Garlic Plant | 0 |  | item row |  |  | already a row |
| Feverfew | Plants/RemasterHerbPlant/Feverfew | Cave.dmi: Garlic Plant | 0 |  | item row |  |  | already a row |
| Milk thistle | Plants/RemasterHerbPlant/MilkThistle | Cave.dmi: Garlic Plant | 0 |  | item row |  |  | already a row |
| TomatoPlant | Plants/TomatoPlant | Cave.dmi: Plant1 | 10 |  | item row | DblClick, New | MiscCreate › Tomatos, RemasterAwayGrow, obj › TomatoGrow | already a row |

## Seeds

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Seeds *(group of 7)* | Seeds |  | 0 | seed | 2006 (Turfs.dm:2677) | New |  | no values of its own |
| CarnivorousPlantSeed | Seeds/CarnivorousPlantSeed | Cave.dmi: TowerCapSeed | 2 | seed | item row | DblClick |  | already a row |
| Garlic | Seeds/Garlic | Farm Items.dmi: Garlic | 2 | seed | item row | DblClick | GarlicPlant › DblClick | already a row |
| GrapeSeed | Seeds/GrapeSeed | Cave.dmi: TowerCapSeed | 2 | seed | item row | DblClick |  | already a row |
| PoisonSporeSeed | Seeds/PoisonSporeSeed | Cave.dmi: TowerCapSeed | 2 | seed | item row | DblClick |  | already a row |
| TomatoSeed | Seeds/TomatoSeed | Cave.dmi: TowerCapSeed | 2 | seed | item row | DblClick |  | already a row |
| TowerCapSeed | Seeds/TowerCapSeed | Cave.dmi: TowerCapSeed | 2 | seed | item row | DblClick |  | already a row |
| TreeSeed | Seeds/TreeSeed | Cave.dmi: TowerCapSeed | 2 | seed | item row | DblClick | Monsters › RmChainBump_Bump, turf › ForestGrowth | already a row |

## ores

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| ores *(group of 6)* | ores |  | 0 | ore | 2006 (Turfs.dm:5601) | New |  | no values of its own |
| Adamantium | ores/Adamantium | Cave.dmi: Adamantium | 20 | ore | item row | DblClick | Monsters › RmChainBump_Bump, RemasterBiomeMined, RemasterBiomeResource | already a row |
| Gold | ores/Gold | Cave.dmi: Gold | 30 | ore | item row | DblClick | Monsters › RmChainBump_Bump, client › Click | already a row |
| Iron | ores/Iron | Cave.dmi: Iron | 20 | ore | item row | DblClick | Monsters › RmChainBump_Bump, RemasterBiomeMined, RemasterBiomeResource +1 | already a row |
| Sand | ores/Sand | Farm Items.dmi: Sand | 30 | ore | item row | DblClick | Flag › DblClick, Spade › DblClick, WoodenSpade › DblClick | already a row |
| Silver | ores/Silver | Cave.dmi: Silver | 20 | ore | item row | DblClick | Monsters › RmChainBump_Bump, client › Click | already a row |
| Stone | ores/stone | Cave.dmi: Stone | 20 | stone | item row | DblClick | MiscCreate › Stone, Monsters › RemasterRampTick, Monsters › RmChainBump_Bump +7 | already a row |

## Food

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Food *(group of 5)* | Food | Food.dmi:  | 10 | food | 2006 (Items/Food.dm:4) | DblClick, New, RemasterUseCarried | Monsters › RemasterAwayFarm, RemasterFood › Take | values mixed with code (Code/Items/Food.dm:7) |
| Cheese | Food/Cheese | Food.dmi: Cheese | 10 | food | item row |  | Kitchen › DblClick | already a row |
| Fungus | Food/Fungus | Food.dmi: Fungus | 10 | food | item row |  | RemasterBiomeResource | already a row |
| Grape | Food/Grape | Food.dmi: Grape | 10 | food | item row |  | GrapeVine › DblClick | already a row |
| Meat *(group of 1)* | Food/Meat | Food.dmi: RawMeat | 10 | food | item row |  |  | already a row |
| Cooked_Meat | Food/Meat/Cooked_Meat | Food.dmi: CookedMeat | 10 | food | item row |  | MiscCreate › Food | already a row |
| Tomato | Food/Tomato | Food.dmi: Tomato | 10 | food | item row |  | TomatoPlant › DblClick | already a row |

## RemasterTools

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| RemasterTools *(group of 6)* | RemasterTools |  | 4 |  | item row |  |  | already a row |
| Climbing Gear | RemasterTools/ClimbingGear | Cave.dmi: Metal Spike | 5 |  | item row |  |  | already a row |
| Fishing Net | RemasterTools/FishingNet | Cave.dmi: SilkPost | 4 |  | item row |  |  | already a row |
| Fishing Rod | RemasterTools/FishingRod | WoodItems.dmi: Wood Spear | 4 |  | item row |  |  | already a row |
| Harpoon | RemasterTools/Harpoon | Cave.dmi: Metal Spike | 6 |  | item row |  |  | already a row |
| Iron Chains | RemasterTools/IronChains | beastparts.dmi: chains | 15 |  | item row |  | Monsters › RmCapBreakFree, Monsters › RmCapRopeItem, Player › RmCapRevoltTick +1 | already a row |
| Lobster Cage | RemasterTools/LobsterCage | Cave.dmi: Cage | 8 |  | item row |  |  | already a row |

## Ingots

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Ingots *(group of 4)* | Ingots |  | 0 | ingot | 2006 (Turfs.dm:2027) | New |  | no values of its own |
| AdamantiumIngot | Ingots/AdamantiumIngot | Cave.dmi: AdamantiumIngot | 0 | ingot | item row | DblClick |  | already a row |
| GoldIngot | Ingots/GoldIngot | Cave.dmi: GoldIngot | 20 | ingot | item row | DblClick | IronIngot › DblClick, MiscCreate › GoldIngot, SilverIngot › DblClick | already a row |
| IronIngot | Ingots/IronIngot | Cave.dmi: IronIngot | 20 | ingot | item row | DblClick | GoldIngot › DblClick, MiscCreate › IronIngot, SilverIngot › DblClick | already a row |
| SilverIngot | Ingots/SilverIngot | Cave.dmi: SilverIngot | 20 | ingot | item row | DblClick | GoldIngot › DblClick, IronIngot › DblClick, MiscCreate › SilverIngot | already a row |

## Arrows

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Arrows *(group of 4)* | Arrows |  | 0 | arrows | 2006 (Turfs.dm:2467) |  |  | no values of its own |
| BoneArrow | Arrows/BoneArrow | BoneItems.dmi: Arrow | 3 | arrows | item row | DblClick | BoneCraft › DblClick | already a row |
| MetalArrow | Arrows/MetalArrow | MetalObjects.dmi: Arrow | 3 | arrows | item row | DblClick | Forge › DblClick | already a row |
| SilverArrow | Arrows/SilverArrow | SilverItems.dmi: Arrow | 3 | arrows | item row | DblClick | Forge › DblClick | already a row |
| WoodenArrow | Arrows/WoodenArrow | WoodItems.dmi: Arrow | 3 | arrows | item row | DblClick | Carpentry › DblClick | already a row |

## Glands

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Glands *(group of 3)* | Glands |  | 0 |  | 2006 (Creatures/Death.dm:341) | DblClick, New |  | no values of its own |
| PoisonGland *(group of 1)* | Glands/PoisonGland | Cave.dmi: Gland | 10 |  | item row |  |  | already a row |
| Venom Sac | Glands/PoisonGland/VenomSac | beastparts.dmi: venomsac | 6 |  | item row |  | RmButcherBeast | already a row |
| PoisonRoots | Glands/PoisonRoots | Animal.dmi: Gland | 10 |  | item row |  |  | already a row |
| ToxicGland | Glands/ToxicGland | Cave.dmi: Gland | 10 |  | item row |  |  | already a row |

## Poisons

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Poisons *(group of 3)* | Poisons |  | 0 | poison | 2006 (Turfs.dm:2271) | DblClick |  | no values of its own |
| Poison | Poisons/Poison | Cave.dmi: Poison | 10 | poison | item row |  | PoisonStation › DblClick | already a row |
| StrongPoison | Poisons/StrongPoison | Cave.dmi: StrongPoison | 10 | poison | item row |  |  | already a row |
| Toxic | Poisons/Toxic | Cave.dmi: Toxic | 10 | poison | item row |  | PoisonStation › DblClick | already a row |

## RemasterHerb

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| RemasterHerb *(group of 3)* | RemasterHerb | Farm Items.dmi: Garlic | 2 | herb | item row | New | RemasterHerbPlant › Pick | already a row |
| Athelas | RemasterHerb/Athelas | Farm Items.dmi: Garlic | 2 | herb | item row |  |  | already a row |
| Feverfew | RemasterHerb/Feverfew | Farm Items.dmi: Garlic | 2 | herb | item row |  |  | already a row |
| Milk thistle | RemasterHerb/MilkThistle | Farm Items.dmi: Garlic | 2 | herb | item row |  |  | already a row |

## RemasterRemedy

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| RemasterRemedy *(group of 3)* | RemasterRemedy | Farm Items.dmi: GreenPotion | 3 |  | item row |  | RemasterClinic › TakeOut | already a row |
| Athelas poultice | RemasterRemedy/Poultice | Farm Items.dmi: GreenPotion | 3 |  | item row |  |  | already a row |
| Thistle purge | RemasterRemedy/Purge | Farm Items.dmi: PurplePotion | 3 |  | item row |  |  | already a row |
| Feverfew tonic | RemasterRemedy/Tonic | Farm Items.dmi: BluePotion | 3 |  | item row |  |  | already a row |

## RemasterRope

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Rope *(group of 3)* | RemasterRope | rope.dmi: rope-leather | 3 |  | item row | RmSetQuality | Monsters › RemasterCraftRope, Monsters › RmCapRopeItem | already a row |
| Leather Rope | RemasterRope/LeatherRope | rope.dmi: rope-leather | 3 |  | item row |  |  | already a row |
| Plant Rope | RemasterRope/PlantRope | rope.dmi: rope-plant | 2 |  | item row |  |  | already a row |
| Silk Rope | RemasterRope/SilkRope | rope.dmi: rope-silk | 1 |  | item row |  |  | already a row |

## Graves

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Graves *(group of 2)* | Graves |  | 0 |  | 2006 (Turfs.dm:3093) |  |  | no values of its own |
| Grave | Graves/Grave | Cave.dmi: Vrage | 10 |  | item row |  | Body › DblClick, Monsters › RemasterBury | already a row |
| TombStone | Graves/TombStone | StoneItems.dmi: TombStone1 | 30 |  | item row | DblClick | Masonary › DblClick | already a row |

## woods

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| woods *(group of 1)* | woods |  | 0 | wood | 2006 (Turfs.dm:5056) | New |  | no values of its own |
| wood *(group of 1)* | woods/wood | Cave.dmi: Wood | 20 | wood | item row | DblClick | MiscCreate › Wood, Monsters › RmChainBump_Bump, Player › RemasterStartLogs +4 | already a row |
| Bamboo | woods/wood/Bamboo | Cave.dmi: Wood | 20 | wood | item row |  | RemasterBambooWood | already a row |

## Thrown

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Thrown *(group of 2)* | Thrown |  | 0 |  | Remastered (Remastered/Throwing.dm:11) |  |  | no values of its own |
| Javelin | Thrown/Javelin | WoodItems.dmi: Wood Spear | 6 |  | item row |  |  | already a row |
| Throwing Axe | Thrown/ThrowingAxe | Cave.dmi: Axe | 5 |  | item row |  |  | already a row |

## RemasterBandage

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Bandage *(group of 2)* | RemasterBandage | stumpcare.dmi: bandage-leather | 1 |  | item row | RmSetQuality |  | already a row |
| Leather Bandage | RemasterBandage/Leather | stumpcare.dmi: bandage-leather | 1 |  | item row |  |  | already a row |
| Silk Bandage | RemasterBandage/Silk | stumpcare.dmi: bandage-silk | 1 |  | item row |  |  | already a row |

## Skin

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Skin *(group of 1)* | Skin | Skin.dmi: FrogSkin | 10 | skin | item row | DblClick |  | already a row |
| Dragon Wing Hide | Skin/WingHide | beastparts.dmi: winghide | 8 | skin | item row |  | RmButcherBeast | already a row |

## Silks

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Silks *(group of 1)* | Silks |  | 0 |  | 2006 (Turfs.dm:518) |  |  | no values of its own |
| SpiderSilk | Silks/SpiderSilk | Spiders.dmi: Silk | 10 |  | item row | DblClick | mob › BleedingTick | already a row |

## RemasterSalt

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Rock salt | RemasterSalt | Farm Items.dmi: Sand | 3 |  | item row | New | RemasterBiomeMined | already a row |

## RemasterLimb

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| RemasterLimb | RemasterLimb | Blood.dmi: Arm | 8 |  | item row | New, RemasterLimbLook | Monsters › RemasterMakeProsthesis | already a row |

## RemasterSoulStone

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Soul stone | RemasterSoulStone | Cave.dmi: Diamond | 5 |  | item row | RemasterSoulLook | RemasterBiomeMined | already a row |

## RmBeastEgg

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Dragon Egg | RmBeastEgg | beastparts.dmi: egg-red | 20 | egg | item row | Del, DeleteItem, New, RmEggTick, RmHatch | RmMakeEgg | already a row |

## RemasterStake

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Stake | RemasterStake | rope.dmi: stake | 2 |  | item row |  |  | already a row |

## RmRuneStone

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Rune Stone | RmRuneStone | Runes.dmi: crystal | 2 |  | item row |  |  | already a row |

## RemasterTorch

| Name | Code name | Picture | Weight | Categories | From | Own code | Made by | Adopt |
|---|---|---|---|---|---|---|---|---|
| Torch | RemasterTorch | stumpcare.dmi: torch | 2 |  | Remastered (Remastered/Stumps.dm:62) |  |  | values mixed with code (Code/Remastered/Stumps.dm:67) |
