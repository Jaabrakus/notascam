// The browser requests its first model only after every script of the page has run (the main one, the sound engine
// inserted at the rm-audio marker, rts-feel's): asking navigates (byond://), and WebKit stops reading the page there,
// so a script placed after the request never ran in the game (found 2026-10-22, rts-feel).
send('ready','');
