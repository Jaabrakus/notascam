// The sea, its shallows, rivers and their fords (hud-rework 10-27, the owner: "first we need land tiles such as rivers and
// oceans and beaches", then naval ships). Laid into the maps by reports/polish-night-1026/hud-rework/water/bake.py: the
// ocean along the south and east with sandy beaches (desert ground) and a few islands, rivers from the snowfields and
// from lakes in the mountains down to the sea, widening on the way, with fords. They are the water family, so they draw
// as water in 3D (View3D.dm Remaster3DKind: Content3 "Liquid"), can be fished and block building like any water. Deep
// water (the sea, a river) cannot be walked; shallows by a shore and a river's fords can be waded.
// Up in the mountains (the owner, 10-27: "raise the mountain lakes and make the rivers drop down the rock face as
// waterfalls"): a mountain lake and the river out of it lie remaster_waterlift blocks up, in rock kept at least a block
// higher round them (remaster_mapblocks, Breaking.dm RemasterBlocksAt); the 3D view draws the water at that height and
// a waterfall where it drops to the water below. Both are set by the bake.
turf/var/remaster_waterlift = 0
turf/var/remaster_mapblocks = 0

turf/grounds/waters
	sea
		name = "Sea"
		icon = 'water.dmi'
		icon_state = "water"
		density = 1
		CanFish = 1
		Detailed = 1
		Content = "Water"
		OIcon = "water"
		text = "<font color=#000088>W"
	shallows
		name = "Shallows"
		icon = 'water.dmi'
		icon_state = "water"
		density = 0
		CanFish = 1
		Detailed = 1
		Content = "Water"
		OIcon = "water"
		text = "<font color=#3366CC>w"
	river
		name = "River"
		icon = 'water.dmi'
		icon_state = "water"
		density = 1
		CanFish = 1
		Detailed = 1
		Content = "Water"
		OIcon = "water"
		text = "<font color=#0000CC>W"
	ford
		name = "Ford"
		icon = 'water.dmi'
		icon_state = "water"
		density = 0
		CanFish = 1
		Detailed = 1
		Content = "Water"
		OIcon = "water"
		text = "<font color=#3366CC>w"
