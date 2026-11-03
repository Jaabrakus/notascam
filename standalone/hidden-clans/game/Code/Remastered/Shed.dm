// How far behind the server is: rm_shed_level (declared in Spread.dm), for cosmetic work that may step back while the
// server catches up (the coordinator's option 1, the user's go, 2026-10-24: "cosmetic work steps back when behind,
// health/combat/selection never delayed"). Each tick it looks at the last RM_SHED_WINDOW ticks: the game time made
// against the real time passed (at the game's speed; 1 is keeping up) and the ticks' cpu (world.cpu, the DM share of a
// tick). The level rises as soon as it's needed and comes down one step per RM_SHED_DOWN ticks of being better, so it
// doesn't flap. A change of speed (pause, x2, x4: Speed.dm) starts the window again: nothing runs while paused, and the
// real time that passed then isn't the server falling behind. Each change goes to the world log as SHED|..., and a
// return to 0 says how long it shed. What reads it: the HUD's tiers (HudView.dm, hud-craft) and the 3D view's
// (world-look). It changes nothing else.
#define RM_SHED_WINDOW 30   // ticks looked at
#define RM_SHED_DOWN 50     // ticks better before a level comes down one step

var/list/rm_shed_real = list()   // world.timeofday of each of the last ticks
var/list/rm_shed_game = list()   // their world.time
var/list/rm_shed_cpu = list()    // their world.cpu
var/rm_shed_better = 0           // ticks in a row a lower level would have done
var/rm_shed_from = 0             // world.time the level last left 0
var/rm_shed_ratio = 1            // game time made / real time, over the window
var/rm_shed_load = 0             // the window's mean cpu
var/rm_shed_speed = -1           // the game speed the window was measured at
var/rm_shed_mine = 0             // the level this code last set: a test that sets rm_shed_level itself is left alone

// world/New: this file's part is step RmChainWorldNew_Shed in Code/Remastered/Chains/WorldNew.dm

proc/RmShedLoop()
	while(1)
		sleep(1)
		RmShedTick()

// The game's speed (Speed.dm rm_speed: 0 paused, 1-3), or the speed a harness set straight into world.game_state (the
// checks run at 4): world.game_state reads 0 until someone sets it, which isn't a pause. The engine caps it at 4.
proc/RmShedSpeed()
	var/speed = rm_speed
	if(isnum(world.game_state) && world.game_state > 0 && world.game_state != rm_speed) speed = world.game_state
	return min(4, speed)

proc/RmShedTick()
	if(rm_shed_level != rm_shed_mine) return   // set by someone else (a check forcing a tier): theirs until they put it back
	var/speed = RmShedSpeed()
	if(speed != rm_shed_speed)   // paused, resumed or sped up: measure afresh
		rm_shed_speed = speed
		rm_shed_real = list()
		rm_shed_game = list()
		rm_shed_cpu = list()
	if(speed <= 0)
		RmShedSet(0)
		return
	rm_shed_real += world.timeofday
	rm_shed_game += world.time
	rm_shed_cpu += world.cpu
	if(length(rm_shed_real) > RM_SHED_WINDOW)
		rm_shed_real.Cut(1, 2)
		rm_shed_game.Cut(1, 2)
		rm_shed_cpu.Cut(1, 2)
	var/n = length(rm_shed_real)
	if(n < 10) return
	var/real = rm_shed_real[n] - rm_shed_real[1]
	if(real < 0) real += 864000   // midnight
	var/game = rm_shed_game[n] - rm_shed_game[1]
	rm_shed_ratio = real > 0 ? game / (real * speed) : 1
	var/cpu = 0
	for(var/c in rm_shed_cpu) cpu += c
	rm_shed_load = cpu / n
	var/want = 0
	if(rm_shed_ratio < 0.6) want = 3
	else if(rm_shed_ratio < 0.8 || rm_shed_load >= 110) want = 2
	else if(rm_shed_ratio < 0.95 || rm_shed_load >= 90) want = 1
	if(want > rm_shed_level)
		rm_shed_better = 0
		RmShedSet(want)
	else if(want < rm_shed_level)
		if(++rm_shed_better >= RM_SHED_DOWN)
			rm_shed_better = 0
			RmShedSet(rm_shed_level - 1)
	else rm_shed_better = 0

proc/RmShedSet(level)
	if(level == rm_shed_level) return
	var/was = rm_shed_level
	rm_shed_level = level
	rm_shed_mine = level
	if(was == 0) rm_shed_from = world.time
	if(level == 0) world.log << "SHED|0|back to keeping up after [round((world.time - rm_shed_from) / 10, 0.1)] game s|ratio=[round(rm_shed_ratio, 0.01)]|cpu=[round(rm_shed_load)]|t=[world.time]"
	else world.log << "SHED|[level]|from [was]|ratio=[round(rm_shed_ratio, 0.01)]|cpu=[round(rm_shed_load)]|t=[world.time]"
