proc/LocateValidLocation(X=220,XX=999,Y=210,YY=800,Z=1,ZZ=Z)
	var/TRIES=0
	START
	TRIES+=1
	var/turf/T = locate(rand(X,XX),rand(Y,YY),rand(Z,ZZ))
	if(T)
		if(TRIES<50)
			if(T.z != 2) for(var/atom/TT in range(1,T)) if(TT.density) goto START
			for(var/mob/Monsters/M in view(15,T)) if(M.HumanParts) goto START
		for(var/turf/TT in range(1,T)) if(TT.density||TT.opacity)
			TT.icon_state = "CaveFloor"
			TT.CanDigAt = 0
			TT.opacity = 0
			TT.density = 0
			TT.name = "cavefloor"
			TT.icon = 'Cave.dmi'
			TT.Sky = 1
			TT.Content3 = "CanClimb"
			TT.OIcon = "CaveFloor"
	return(T)
mob/verb/Restart()
	if(Up)
		Close()
		Up = 0
	if(Restart) return
	Restart = 1
	var/ASK
	for(var/mob/Monsters/M in UnitList)
		ASK=1
		break
	if(ASK) if(RemasterChoose(usr, "Start again with a new people? Your current company will be left behind.", "Start over", list("Keep playing", "Start again"))=="Start again") ASK=null
	if(!ASK)
		Function = null
		if(client)
			var/list/menu = new()
			if(!RmPublicWorld() && key == world.host) verbs+=typesof(/Admin/verb/)
//			if("SandKing" in Rares) menu += "Sand King - Rare"
			// Remastered: rare races appear only when drawn (Rarity.dm)
			var/list/remaster_rares = istype(src, /Player) ? src:RemasterRareDraw() : list()
			for(var/r in remaster_rares) menu += "[r] - Rare"
			menu += "Human"
			menu += "Dwarf"
			menu += "Elf"
			menu += "Orc"
			menu += "Goblin"
			menu += "Lizardman"
			menu += "Frogman"
			menu += "Kobold"
			menu += "Ratman"
			menu += "Cancel"
			if(RmIsGuest(src)) menu = RmGuestRaceMenu(menu)   // Remastered: guests choose from four while locked, else any (Guests.dm)
			Race=RemasterChooseRace(src, menu)   // Remastered: a HUD card (Onboarding.dm)
			if(!Race || Race=="Cancel")
				Restart=0
				return
			// Remastered (polish-start 10-26): the old company is left behind only once a people is chosen, so Not now on
			// the race card (or Esc) after "Start again" keeps it; it used to be gone already.
			for(var/mob/Monsters/M in Selected) M.Deselect(src)
			for(var/mob/Monsters/M in world) if(!M.Wagon) if(M.Owner == usr)
				for(var/obj/DigAt/DD in world) if(DD.Owner == M.Owner) for(var/turf/T in DD.loc)
					if(T.density) if(!T.IsWall) T.icon_state = "CaveWall"
					del(DD)
				for(var/obj/Items/I in M) if(I.Content3 == "Cage") M.ForceDropItem(I)
				if(M.Race != "Devouerer" && M.Race != "Illithid" && M.Caged && M.Race != "SandKing" && M.SubRace != "Werewolf" && M.Race != "Svartalfar" && !M.Infects && M.SubRace != "Queen" && !M.IsRoyal)
					M.CanBeSlaved = 1
					M.ChangeOwnership(FORCE=1)
				else del(M)
			UnitList = list()
			CoolDowns= list()
			if(istype(src, /Player)) src:RmStartOverWork()   // Remastered: the old company's zones, rows, plans and stores go with it
			Restart = 1
			loc = locate(rand(350,700),rand(400,750),1)
			density = 0
			if(findtext(Race, " - Rare") && Race != "Illithid - Rare") Race = copytext(Race, 1, findtext(Race, " - Rare"))
			if(istype(src, /Player)) src:remaster_rare_back = src:remaster_rare_drawn   // kept for Back on the company card (Company.dm)
			if(istype(src, /Player)) src:remaster_rare_drawn = null     // the draw is used up
			var/TYPE = text2path("/mob/Monsters/[Race]")
			var/LOC
			var/NUMBER = 3
			switch(Race)
				if("Spider")
					TYPE=/mob/Monsters/Spider/Queen
					NUMBER=1
					LOC=LocateValidLocation(X=240,XX=850,Y=210,YY=800)
				if("Sand King - Rare")
					TYPE=/mob/Monsters/SandKing
					NUMBER=1
					LOC=LocateValidLocation(Z=2)
				if("Illithid - Rare")
					TYPE=/mob/Monsters/Illithid
					NUMBER=1
				if("Dragon","Devourer")
					NUMBER=1
					LOC=LocateValidLocation(X=240,XX=850,Y=210,YY=800)
				if("Svartalfar")
					NUMBER=1
					LOC=LocateValidLocation(Z=2)
				if("Ratman","Kobold")
					NUMBER=5
					LOC=LocateValidLocation(X=289,XX=851,Y=211,YY=360)
				if("Dwarf")
					LOC=LocateValidLocation(X=240,XX=350,Y=263,YY=666)
				if("Goblin","Human")
					LOC=LocateValidLocation(X=240,XX=850,Y=210,YY=800)
				if("Elf")
					LOC=LocateValidLocation(X=600,XX=850,Y=200,YY=800)
				if("Lizardman","Frogman") LOC=LocateValidLocation(X=175,XX=365,Y=675,YY=785)
			if(!LOC) LOC = LocateValidLocation()
			// Remastered: join an open realm as migrants instead (Realms.dm)
			if(istype(src, /Player))
				var/turf/J = src:RemasterMigrantChoice()
				if(J)
					LOC = J
					src:rm_fh_skip = 1   // migrants join a realm with buildings: no first house (FirstHouse.dm)
			var/CURNUM=0
			if(TYPE) for(var/mob/Monsters/M in MakeMany(TYPE,NUMBER,LOC,1))
				CURNUM+=1
				if(!(M.Race in rm_rare_races)) M.RemasterStartSkills()   // Remastered: a fair start (Rarity.dm)
				if(!(M.Race in rm_rare_races)) M.RmStartRolls()   // Remastered: a new company starts weaker (Company.dm)
				if(NUMBER>1)
					switch(CURNUM)
						if(1)
							M.x-=1
							switch(M.Race)
								if("Frogman","Lizardman") M.ForcePickUpItem(new/obj/Items/woods/wood(loc))
								else M.ForcePickUpItem(new/obj/Items/ores/stone(loc))
						if(2) loc=M.loc
						if(3) M.x+=1
						if(4) M.y+=1
						if(5) M.y-=1
				else loc=M.loc
				switch(M.Race)
					if("Human","Dwarf","Goblin","Orc","Lizardman","Frogman","Kobold","Ratman") M.ForcePickUpItem(new/obj/Items/Furniture/Beds/SleepingBag)
				if(M.Carn) M.ForcePickUpItem(new/obj/Items/Food/Meat(loc))
				else
					M.ForcePickUpItem(new/obj/Items/Food/Meat/Cooked_Meat)
					M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Armour/Chestplate/LeatherChestPlate,"Quality"))
					M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Armour/Leggings/LeatherLeggings,"Quality"))
					M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Weapon/Daggers/MetalDagger,"Quality"))
				if(M.UsesPicks) M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Weapon/Picks/PickAxe,"Quality"))
				switch(M.Race)
					if("Dragon")
						M.Age=50
						M.EggContent=0.9
						M.Gender="Female"
					if("Human","Dwarf")
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Weapon/Axes/MetalAxe,"Quality"))
					if("Elf")
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Weapon/Axes/WoodenAxe,"Quality"))
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Armour/Chestplate/WoodenChestplate,"Quality"))
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Armour/Leggings/WoodenLeggings,"Quality"))
					if("Orc")
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Weapon/Axes/MetalOrcAxe,"Quality"))
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Armour/Shield/WoodenBuckler,"Quality"))
					if("Goblin")
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Weapon/Swords/GoblinSword,"Quality"))
					if("Lizardman","Frogman","Kobold","Ratman")
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Weapon/Spears/Spear,"Quality"))
					if("Svartalfar")
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Armour/Helmet/RedHat,"Quality"))
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Armour/Chestplate/RedRobe,"Quality"))
						M.ForcePickUpItem(CraftItem(new/obj/Items/Equipment/Weapon/Maces/NecroStaff,"Quality"))
				for(var/obj/Items/Equipment/E in M) M.EquipItem(E)
				if(M.weight>M.weightmax) M.weightmax=M.weight+30
				M.ChangeOwnership(src)
				M.name="{[name]} [M.name]"
				M.CantBeGiven=1
				M.PillarPowerup()
			if(NUMBER > 1 && istype(src, /Player) && src:RemasterCompanyCard() == "Back")   // Remastered: the first-company card (Company.dm); Back picks the people again
				src:RmCompanyBack()
				Restart = 0
				spawn(1) Restart()
				return
			switch(Race)
				if("Sand King - Rare") RemasterStory(src,"You hatch in an odd place, at first completely unaware of your surroundings. Slowly you realise you are one of the Sand Kings, in larva form. You must create tool bodies for yourself and grow to maturity if you wish to survive... and you will need a castle to protect your fragile form.","The Sand King")
				if("Illithid - Rare")
					src << "<font color=red>Illithid guide: F6 (or the Mental abilities button) opens your mind powers. For mind control, first pick the target with Choose magic target, then use it from the powers menu. It only works on creatures under level 10, and may take several tries against player-owned units."
					RemasterStory(src,"You are an illithid, an ancient creature of great power. You have come to this land to dominate the minds of its inhabitants and amass an army to destroy any and all who challenge your awesome power.","The Illithid")
				if("Dragon") RemasterStory(src,"A legendary dragon. That's you. Soon, however, you will be more than that: you'll be a mother. Before that time comes you'll need to find a suitable place to make your home.","The Dragon")
				if("Human") RemasterStory(src,"As part of the Human empire you were ordered to scout out new lands suitable for settlements. It now looks as though your search has come to an end! It might be best to set up camp for the winter ahead.","The Humans")
				if("Dwarf") RemasterStory(src,"You and your companions have arrived in new, unexplored lands. Many adventures and dangers await you here. Think about making a secure place to live deep in the mountains, so that you may begin to build a vast dwarven city.","The Dwarves")
				if("Elf") RemasterStory(src,"As elves of the woods, it is your ancient duty to protect the forests from the fools who would desecrate them. The forests themselves called you here. Now you must perform your duty.","The Elves")
				if("Orc") RemasterStory(src,"Forever have the orcs roamed the lands of this world in nomadic tribes, searching for the perfect place to settle. Upon reaching [WorldName] the orcs decided they liked it, and soon discovered that others did too. As the leader of your tribe you must decide which races, if any, are worthy of staying in your land and which must be driven out, for if you are to create the perfect tribe there can be no room for weakness!","The Orcs")
				if("Goblin") RemasterStory(src,"Lured to this land in the hope of starting a dark dungeon, you and your companions finally arrive. A simple cave would be a good place to start.","The Goblins")
				if("Lizardman") RemasterStory(src,"Native to this land, the lizardmen live a harsh life in a horrific environment. Disturbed by the other races, your lizardmen decide to hunt down and kill the intruders, so that this land may be yours once more.","The Lizardmen")
				if("Frogman") RemasterStory(src,"For as long as anyone can remember, the frogmen and the lizardmen have been at war for control of the swamps. Every day there is bloodshed. It's up to you whether to take part, or to flee and find somewhere a little safer to live. Whatever you choose, watch out for swamp dragons.","The Frogmen")
				if("Kobold") RemasterStory(src,"Tempted by the undiscovered treasures of this new land, you finally arrive. A secure cave would be a good start, so that one day you may raise a vast kobold army to raid this land.","The Kobolds")
				if("Ratman") RemasterStory(src,"Driven from your home by hordes of dangerous predators, you have arrived in this new land to propagate your kind... and eat cheese.","The Ratmen")
				if("Svartalfar") RemasterStory(src,"A dark god of another land destroyed your family and cursed you with long life and power, only to warp your appearance and set you apart from the rest of mankind.","The Svartalfar")
				if("Spider") RemasterStory(src,"After many weeks of travel from your old nests you arrive in new lands, ready to begin a new swarm. First, find a suitable place for your hatchlings.","The Spider Queen")
				if("Dragon") RemasterStory(src,"Travelling far from your hatching ground, you have arrived in this new land to make your home.","The Dragon")
				if("Devourer")
					RemasterStory(src,"Awoken after two thousand years of slumber, you have finally regenerated your body from the wounds dealt all those years ago by the gods that imprisoned you. Strong once more, you are ready to bring about the second coming of the dreaded Plague of Black Blight!","The Devourer")
					src<<"Carry dead bodies and use Tear meat from carried corpses: your Devourer takes them into its body total."
					src<<"When putting organs into a zombie, up to 5 of the same organ count; more add nothing."
	if(istype(src, /Player)) spawn(5) src:RmFirstHousePlan()   // building rework L8: the first house or lodge, as blocks (FirstHouse.dm)
	Restart = 0

// Remastered (polish-zones, 10-27): starting over leaves the old company behind, and its work goes with it: the job
// board's rows and zones (plans too), the stockpile zones, the construction plans and sites, the board's orders and the
// stockpile's place. The new people start as a new player does (the owner: "we loaded a new game the saved kept the
// work zones instead of cleaning it"). HUD settings, formations, the profile, progress and the soul stone carry-over
// are not touched. The tmp lists below are what was worked out from those while the world ran.
Player/proc/RmStartOverWork()
	rm_jz = null                    // RmJzFixedRows makes Builders and Haulers again
	remaster_zones = null
	remaster_blueprints = null
	remaster_sites = null
	remaster_board_orders = null
	remaster_board_standing = null
	remaster_stock_x = 0
	remaster_stock_y = 0
	remaster_stock_z = 0
	remaster_stock_filter = "mixed"
	rm_jz_members = null
	rm_jz_nfree = 0
	rm_jz_cells = null
	rm_jz_vi = null
	rm_jz_zfree = null
	rm_jz_targets = null
	rm_jz_built = null
	rm_jz_ti = null
	rm_jz_doing = null
	rm_jz_stock = null
	rm_jz_out = null
	rm_jz_out_t = null
	rm_jz_hist = null
	rm_jz_prob = null
	rm_jz_lognote = null
	rm_jz_resting = null
	rm_jz_res = null
	rm_jz_far = null
	rm_jz_loose = null
	rm_jz_loose_at = null
	rm_jz_waiting = null
	rm_jz_seeds_c = null
	rm_jz_regrow = null
	rm_jz_hshort = null
	rm_jz_bwork = null
	rm_jz_bidle = 0
	rm_jz_bseen = 0
	rm_jz_blook = null
	rm_jz_yards_c = null
	rm_gz_pending = null
	rm_ch_bclaims = null
	rm_ch_prog = null
	rm_ch_needs = null
	rm_ch_lying = null
	rm_ch_aside_units = null
	rm_cell_aim = null
	rm_zone_cells = null
	rm_plan_res = null
	remaster_sites_had = 0
	remaster_unreachable = null
	remaster_patrol_draft = null
	rm_store_tick = -1
	rm_store_sig = null
	rm_jz_ready = 0                 // the next board pass counts the new company from scratch
	rm_jz_next = 0
	rm_jz_recount_at = 0
