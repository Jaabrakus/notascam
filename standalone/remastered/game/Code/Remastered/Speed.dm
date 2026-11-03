// Pause and game speed. Remastered's engine (engine/clock) reads world.game_state, a
// hub-only setting it otherwise never uses: 0 paused (orders can still be given),
// 1 normal, 2 fast, 3 faster.
// Space pauses and resumes. In a shared world only the host changes it.

var/rm_speed = 1
var/rm_speed_before_pause = 1

Player/proc/RemasterMayChangeSpeed()
	if(RmPublicWorld()) return 0   // a public server keeps one speed for everyone
	var/n = 0
	for(var/Player/P in world) if(P.client) n++
	if(n <= 1) return 1
	var/host = fexists("host-name") ? trimtext(file2text("host-name")) : null
	return host && RemasterIsHost()   // (not a browser player typing the host's name)

Player/proc/RemasterSetSpeed(v)
	v = clamp(round(text2num("[v]")), 0, 3)
	if(!RemasterMayChangeSpeed())
		RemasterNotice(RmPublicWorld() ? "This world's speed is the same for everyone." : "Only the host can pause or change the speed.")
		return 0
	if(v == 0 && rm_speed) rm_speed_before_pause = rm_speed
	rm_speed = v
	world.game_state = v
	var/text = v == 0 ? "Paused. Give orders, then press Space to carry on." : "Speed: [list("normal", "fast", "faster")[v]]."
	for(var/Player/P in world) if(P.client)
		P.RemasterNotice(text)
		P.RemasterHUDTick()
	return 1

Player/verb/RemasterPauseVerb()
	set name = "Remaster-Pause"
	set hidden = 1
	RemasterSetSpeed(rm_speed ? 0 : max(1, rm_speed_before_pause))
