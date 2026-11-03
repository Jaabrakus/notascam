// Sound (Interface/audio.js). The HUD page's sound engine is its own file; it goes into the page where
// remastered.html has the <!--rm-audio--> marker, when the page is sent. Its effects are synthesized in the page; the
// war drums and the forest ambience are recordings in Interface/sounds/ (tools/build_audio_assets.py): a player gets
// them once per connection, sent ahead of the page, and the page is told their names.
// The player's volume settings are kept in their profile (units/remaster_profile_<ckey>.sav, Rarity.dm),
// because the app's web view forgets its own storage when the game quits.

var/list/remaster_sound_files
proc/RemasterSoundFiles()
	if(!remaster_sound_files)
		remaster_sound_files = list()
		for(var/f in flist("Interface/sounds/"))
			if(length(f) > 4 && copytext(f, length(f) - 3) == ".m4a") remaster_sound_files += f
	return remaster_sound_files

Player/var/tmp/client/remaster_sounds_sent   // the connection that has them
Player/var/tmp/client/remaster_fonts_sent    // the connection that has the HUD's lettering (Interface/fonts)

proc/RemasterHUDPage(Player/P)
	var/page = file2text('Interface/remastered.html')
	var/sfx = file2text('Interface/audio.js')
	if(sfx)
		var/list/files = RemasterSoundFiles()
		if(P && P.client && P.remaster_sounds_sent != P.client)
			P.remaster_sounds_sent = P.client
			for(var/f in files) P << browse_rsc(file("Interface/sounds/[f]"), f)
		page = replacetext(page, "<!--rm-audio-->", "<script>window.rmSoundFiles=[json_encode(files)];[sfx]</script>")
	if(P && P.client && P.remaster_fonts_sent != P.client)   // the HUD's lettering, ahead of the page (041 "HUD lettering", hud-rework 10-27)
		P.remaster_fonts_sent = P.client
		for(var/f in list("hud-text.ttf", "hud-text-italic.ttf", "hud-figures.ttf", "hud-head.ttf", "hud-caps.ttf", "hud-textcaps.ttf"))
			if(fexists("Interface/fonts/[f]")) P << browse_rsc(file("Interface/fonts/[f]"), f)
	if(P) P.RmG3Send()   // the 3D gear's files, ahead of the page (Gear3D.dm)
	return RmG3Page(page)

Player/var/tmp/remaster_audio_prefs

// The saved settings as the page sent them (a short JSON object), "" when none.
Player/proc/RemasterAudioPrefs()
	if(isnull(remaster_audio_prefs))
		remaster_audio_prefs = ""
		if(ckey && fexists(RemasterProfilePath(ckey)))
			var/savefile/S = new(RemasterProfilePath(ckey))
			var/t
			S["audio"] >> t
			if(istext(t)) remaster_audio_prefs = t
	return remaster_audio_prefs

// rm=audioprefs from the Sound settings: {"master":70,"fx":80,...}. Only lowercase letters, digits and
// JSON punctuation are accepted; it only ever goes back to this player's own page.
Player/proc/RemasterAudioSave(value)
	if(!ckey || !istext(value) || !length(value) || length(value) > 300) return
	for(var/i = 1, i <= length(value), i++)
		var/c = text2ascii(value, i)
		if(!((c >= 48 && c <= 57) || (c >= 97 && c <= 122) || c == 123 || c == 125 || c == 34 || c == 58 || c == 44)) return
	if(value == remaster_audio_prefs) return
	remaster_audio_prefs = value
	var/savefile/S = new(RemasterProfilePath(ckey))
	S["audio"] << value

// The HUD's other settings (HUD size, colour-blind colours, 3D look, edge scroll, right-click, folds) live in the page's
// storage too, which the app forgets on quit: the page mirrors them here (rm=hudprefs, a JSON object of strings) and gets
// them back in the HUD model ("hudPrefs") to restore on the next start (audio.js).
Player/var/tmp/remaster_hud_prefs
Player/proc/RemasterHUDPrefs()
	if(isnull(remaster_hud_prefs))
		remaster_hud_prefs = ""
		if(ckey && fexists(RemasterProfilePath(ckey)))
			var/savefile/S = new(RemasterProfilePath(ckey))
			var/t
			S["hud"] >> t
			if(istext(t)) remaster_hud_prefs = t
	return remaster_hud_prefs

Player/proc/RemasterHUDPrefsSave(value)
	if(!ckey || !istext(value) || !length(value) || length(value) > 4000) return
	for(var/i = 1, i <= length(value), i++)
		var/c = text2ascii(value, i)
		if(c < 32 || c > 126) return
	if(value == remaster_hud_prefs) return
	remaster_hud_prefs = value
	var/savefile/S = new(RemasterProfilePath(ckey))
	S["hud"] << value

// The original's own WAVs (weapon clashes, punches, the bow) play under no volume setting and double the HUD's
// combat sounds, which come from the hits feed (Hits.dm). They stay in the game, silent unless this is set to 1.
var/remaster_native_sounds = 0
proc/RemasterNativeSound(atom/A, snd)
	if(remaster_native_sounds && A) view(A) << snd
mob/FightSound()
	if(remaster_native_sounds) ..()
mob/FightSound2()
	if(remaster_native_sounds) ..()
