// The HUD's sends packed for the page (server cost, 2026-10-24; the user: "can we get it to compress 1.4 mb into like
// 10kb?"). A send of a kilobyte or more goes deflated by the engine (rm_pack, engine/native/RmPack.cs) as "~" and
// base64url, and the page unpacks it before anything reads it (Interface/hudpack.js, put in at the page's rm-hudpack
// marker: after every script that wraps updateHUD, before the ready request, after which WebKit stops reading the page).
// Only to a page that says it can ("hudpack" 1, after its first model) and only on an engine with rm_pack; otherwise the
// JSON goes url-encoded as before. Url-encoding alone made a send half as big again ("{", ":", "," and quotes three
// bytes each); base64url needs none.
#define RM_HUD_PACK_FROM 1024
var/rm_native_pack = -1                   // -1 not asked yet; 1 the engine packs, 0 it doesn't
Player/var/tmp/remaster_hud_pack = 0      // the page unpacks (it said "hudpack" 1); 0 again when it (re)loads

// The engine's (RmPack.cs) where it has it; this body runs on an engine without it.
proc/rm_pack(text)
	return null

proc/RmNativePack()
	if(rm_native_pack < 0) rm_native_pack = istext(rm_pack("rm")) ? 1 : 0
	return rm_native_pack

// The page (Audio.dm RemasterHUDPage) with the unpacker at its rm-hudpack marker (hud-craft's, remastered.html): after
// every script that wraps updateHUD, just before the script that says it's ready. No marker: no unpacker (plain sends).
proc/RmHudPackPage(page)
	var/js = file2text('Interface/hudpack.js')
	if(!js || !findtext(page, "<!--rm-hudpack-->")) return page
	return replacetext(page, "<!--rm-hudpack-->", "<script>[js]</script>")

// One model to the page: packed when it can unpack and the engine packs, as it was otherwise.
Player/proc/RemasterHUDSend(encoded)
	if(remaster_hud_pack && length(encoded) >= RM_HUD_PACK_FROM && RmNativePack())
		var/packed = rm_pack(encoded)
		if(istext(packed))
			src << output("~[packed]", "mapwindow.hud:updateHUD")
			return
	src << output(url_encode(encoded), "mapwindow.hud:updateHUD")
