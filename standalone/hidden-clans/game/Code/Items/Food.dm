obj/Items/var
	FoodPower=100

obj/Items/Food
	icon='Food.dmi'
	ItemType="Food"
	New() ItemDecay()
	weight = 10
	Cheese
		// its values: art/items/catalogue.json row food.cheese (export_items.py writes ItemData.dm)
	Grape
		// its values: art/items/catalogue.json row food.grape (export_items.py writes ItemData.dm)
	Tomato
		// its values: art/items/catalogue.json row food.tomato (export_items.py writes ItemData.dm)
	Fungus
		// its values: art/items/catalogue.json row food.fungus (export_items.py writes ItemData.dm)
	Meat
		// its values: art/items/catalogue.json row food.meat (export_items.py writes ItemData.dm)
		Cooked_Meat //Just for quick create.
			// its values: art/items/catalogue.json row food.meat.cooked_meat (export_items.py writes ItemData.dm)
obj/Items/Food/DblClick()
	if(ismob(loc)) return RemasterUseCarried(loc,usr)
	else if(!suffix) for(var/mob/Monsters/M in usr.Selected) if(M.PickUpItem(src,1)) return(1)

obj/Items/Food/RemasterUseCarried(mob/M,mob/controller,require_selected=0)
	var/datum/remaster_carried_context/context=RemasterCarriedCapture(src,M,controller,require_selected)
	if(!context) return 0
	usr=controller
	var/list/menu=new()
	if(M.Race != "Vampire" && M.Race != "Gargoyle") menu+="Eat"
	menu+="Inspect"
	menu+="Drop"
	RmMenuExtras(M,controller,menu)   // Remastered: Use on..., Drop all (InventoryActions.dm)
	menu+="Cancel"
	var/Result=RemasterCarriedChoice(controller,menu)
	if(!RemasterCarriedCurrent(context) || !(Result in menu)) return 0
	if(RmMenuExtraDo(M,controller,Result)) return 1
	switch(Result)
		if("Eat") M.EatItem(src)
		if("Inspect")
			usr<<"\icon[src] <b>[name]</b>"
			if(FoodPower) usr<<"Satisfies [FoodPower] points of hunger when eaten."
			if(weight) usr<<"Weighs [weight] units."
			if(desc)usr<<desc
			usr<<"" //just the same as including a "<br>" at the end, stops people from getting as confused when looking at lots of items.
		if("Drop")M.DropItem(src)
	return 1
mob/proc/EatItem(obj/Items/ITEM) if(ITEM.loc==src) if(ITEM.suffix=="(Carrying)")
	if(istype(src, /mob/Monsters) && src:RemasterBeforeEat(ITEM)) return(0) // Remastered: rot smelt, poison tasted (Ailments.dm, FoodSupply.dm)
	var/Healthy=1
	switch(ITEM.icon_state)
		if("RawMeat") if(!Carn) Healthy=0
		if("Fungus") if(!Carn&&Race!="Dwarf") Healthy=0
		if("Adamantium")
			Hunger+=100
			MaxHunger+=100
	view(src) << "[src] eats the [ITEM]."
	if(istype(src, /mob/Monsters)) src:RemasterAteThought(ITEM, Healthy) // Remastered: moods (Moods.dm)
	if(istype(src, /mob/Monsters)) src:RemasterAfterEat(ITEM) // Remastered: poison, rot, a fever's germs (Ailments.dm)
	if(!Healthy)
		Hunger+=ITEM.FoodPower/2
		Tiredness-=ITEM.FoodPower
	else Hunger+=ITEM.FoodPower
	if(Hunger>MaxHunger) Hunger=MaxHunger
	switch(Race)
		if("Spider")
			WebContent += ITEM.FoodPower
			if(WebContent > MaxWebContent) WebContent=MaxWebContent
		if("Dragon") switch(ITEM.Race)
			if("Demon") MagmaPoints += 100
			if("Dragon") ZombiePoints += 250
			if("Gremlin") SandPoints += 50
			if("Lizardman") PoisonPoints += 50
			if("Orc") IcePoints += 50
	switch(ITEM.icon_state)
		if("Grape") MakeMany(/obj/Items/Seeds/GrapeSeed,2,loc)
		if("Tomato") MakeMany(/obj/Items/Seeds/TomatoSeed,2,loc)
	if(DropItem(ITEM)) del(ITEM)
	return(1)