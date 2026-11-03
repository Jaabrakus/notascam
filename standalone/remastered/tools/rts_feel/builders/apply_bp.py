#!/usr/bin/env python3
"""Builders waiting for material (rts-feel, 2026-10-25; world-look's find, the user's "yellow things"): the same answers,
worked out once instead of again for every site.
  1. RemasterSiteReady asks only whether the task still uses the material (RmSiteNeedsAny: stops at the first piece
     that does) instead of counting every piece (RemasterSiteNeedCount walked every blueprint for every builder and site).
  2. RemasterSiteSource keeps a "none" for the rest of one builder's step (RmBlueprintUnit): the answer depends only on
     the task's layer and the material, so the other sites on that layer, the next-tile look and the fetch get the same
     "none" without walking every store and range(12) again. Cleared when the builder joins another task.
Exact-match edits, idempotent, Latin-1 safe.
    python3 tools/rts_feel/builders/apply_bp.py <game folder>"""
import os, sys, tempfile
from pathlib import Path

EDITS = [
    ("""		if(!path || !RemasterSiteNeedCount(S, path) || M.RemasterCarriedCount(path) || RemasterSiteSource(S, path, M)) return 1
	return 0
""", """		if(!path || !RmSiteNeedsAny(S, path) || M.RemasterCarriedCount(path) || RemasterSiteSource(S, path, M)) return 1
	return 0

// RemasterSiteNeedCount(S, path) > 0, stopping at the first piece that uses the material (every piece's need is 0 or more).
Player/proc/RmSiteNeedsAny(list/S, path)
	if(remaster_blueprints) for(var/list/B in remaster_blueprints) if(B["site"] == S["id"])
		for(var/mode in B["then"] ? list(B["mode"], B["then"]) : list(B["mode"]))
			if(path && RemasterBuildMaterial(mode) != path) continue
			if(RemasterBlueprintNeed(mode, locate(B["x"], B["y"], B["z"]))) return 1
	return 0
"""),
    ("""Player/proc/RemasterSiteSource(list/S, path, mob/Monsters/M)
	var/obj/Items/best
	var/best_d = 1#INF
""", """Player/var/tmp/mob/Monsters/rm_bp_unit   // the builder whose step (RmBlueprintUnit) this is: its "none"s hold all step
Player/var/tmp/list/rm_bp_none           // "layer|material" -> 1: nothing of it for rm_bp_unit this step

Player/proc/RemasterSiteSource(list/S, path, mob/Monsters/M)
	var/memo = M == rm_bp_unit ? "[S["z"]]|[path]" : null   // the answer depends on the layer and material only
	if(memo && rm_bp_none && rm_bp_none[memo]) return null
	var/obj/Items/best
	var/best_d = 1#INF
"""),
    ("""		var/d = get_dist(M, I)
		if(d < best_d)
			best = I
			best_d = d
	return best

// How many pieces this worker fetches""", """		var/d = get_dist(M, I)
		if(d < best_d)
			best = I
			best_d = d
	if(!best && memo)
		if(!rm_bp_none) rm_bp_none = list()
		rm_bp_none[memo] = 1
	return best

// How many pieces this worker fetches"""),
    ("""	if(!duty) return
	var/list/S = open ? RemasterSiteFor(M, claims) : null
	if(!S)
		if(M.remaster_builder) M.RemasterSiteEndDuty(src)""", """	if(!duty) return
	rm_bp_unit = M   // RemasterSiteSource's "none"s hold for the rest of this step
	rm_bp_none = null
	var/list/S = open ? RemasterSiteFor(M, claims) : null
	if(!S)
		rm_bp_unit = null
		if(M.remaster_builder) M.RemasterSiteEndDuty(src)"""),
    ("""	if(M.remaster_site != S["id"])
		if(M.remaster_site) claims[M.remaster_site] = max(0, (claims[M.remaster_site] || 1) - 1)
		M.RemasterSiteJoin(src, S)
		claims[S["id"]] = (claims[S["id"]] || 0) + 1
	M.RemasterSiteWork(src, S)
""", """	if(M.remaster_site != S["id"])
		rm_bp_unit = null   // joining lets go of its orders and pieces: look afresh
		if(M.remaster_site) claims[M.remaster_site] = max(0, (claims[M.remaster_site] || 1) - 1)
		M.RemasterSiteJoin(src, S)
		claims[S["id"]] = (claims[S["id"]] || 0) + 1
	M.RemasterSiteWork(src, S)
	rm_bp_unit = null
"""),
]


def main(game):
    p = Path(game)/'Code/Remastered/Blueprints.dm'
    t = p.read_bytes().decode('latin-1')
    done = 0
    for old, new in EDITS:
        if new in t: continue
        if t.count(old) != 1: sys.exit(f'{p}: no unique match for:\n{old[:200]}')
        t = t.replace(old, new); done += 1
    b = t.encode('latin-1')
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='.bp-'); os.write(fd, b); os.close(fd)
    os.chmod(tmp, p.stat().st_mode); os.replace(tmp, p)
    print(f'{p}: {done} edit(s) applied' if done else f'{p}: already applied')


if __name__ == '__main__':
    main(sys.argv[1])
