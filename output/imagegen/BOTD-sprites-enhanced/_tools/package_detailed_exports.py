#!/usr/bin/env python3
"""Validate and index original-height exports from the detailed artwork."""
from pathlib import Path
import hashlib
import json

from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / "detailed-artwork"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return Path(path).resolve().relative_to(ROOT.resolve()).as_posix()


def image_record(path, expected_sha=None):
    path = Path(path)
    actual = sha(path)
    assert not expected_sha or actual == expected_sha, path
    with Image.open(path) as image:
        assert image.mode == "RGBA", path
        bbox = image.getchannel("A").getbbox()
        assert bbox, path
        size = list(image.size)
    return dict(path=relative(path), sha256=actual, size=size, alpha_bbox=list(bbox))


def main():
    art = json.loads((ROOT / "manifest.json").read_text())
    assert art["status"] == "complete"
    entries, files = [], {}
    for family in sorted(art["families"]):
        report_path = ROOT / "exports/reports" / (family + ".json")
        report = json.loads(report_path.read_text())
        assert report.get("passed") is True or report.get("status", "").startswith("complete"), (family, report.get("status"))
        states = report["states"]
        assert sorted(x["state_index"] for x in states) == list(range(art["families"][family]["state_count"]))
        files[relative(report_path)] = sha(report_path)
        for state in states:
            plate = Path(state["source_plate"])
            assert sha(plate) == state["source_sha256"], (family, state["state_name"], "changed plate")
            cutout = image_record(state["source_cutout"])
            files[cutout["path"]] = cutout["sha256"]
            item = dict(family=family, state_index=state["state_index"], state_name=state["state_name"],
                        source_plate=relative(plate), crop_box=state["crop_box"], cutout=cutout)
            for variant in ("inventory", "player"):
                source = state[variant]
                output = image_record(source["path"], source["sha256"])
                reference = source["native_reference"]
                bbox = output["alpha_bbox"]
                assert bbox[3] - bbox[1] == reference["visible_height"], (family, state["state_index"], variant, "height")
                assert bbox[3] == reference["bottom_baseline_exclusive"], (family, state["state_index"], variant, "baseline")
                assert output["size"][1] == reference["frame_size"][1]
                output["visible_height"] = bbox[3] - bbox[1]
                item[variant] = output
                files[output["path"]] = output["sha256"]
                sidecar = Path(source["report"])
                files[relative(sidecar)] = sha(sidecar)
            entries.append(item)
    assert len(entries) == 375
    race_report = ROOT / "exports/reports/races.json"
    races = json.loads(race_report.read_text())["records"]
    assert len(races) == 13
    files[relative(race_report)] = sha(race_report)
    for race in races:
        for key, hashkey in (("source_cutout", "source_cutout_sha256"), ("game_height", "game_height_sha256")):
            path = ROOT / race[key]
            record = image_record(path, race[hashkey])
            files[record["path"]] = record["sha256"]
            if key == "game_height":
                assert record["alpha_bbox"][3] - record["alpha_bbox"][1] == race["visible_height"]
                assert record["alpha_bbox"][3] == race["baseline"]
    for name in ("independent-export-review.json", "assigned-ten-family-verification.json", "root-export-check.json"):
        path = ROOT / "exports/reports" / name
        if path.exists():
            files[relative(path)] = sha(path)
    summary = dict(status="complete_checked", equipment_states=375, source_equipment_cutouts=375,
                   source_race_cutouts=13, source_cutouts=388, equipment_height_exports=750,
                   race_height_exports=13, height_exports=763, entries=entries, races=races,
                   files=[dict(path=p, sha256=h) for p, h in sorted(files.items())],
                   source_artwork="Detailed enhanced plates", drop_in_overlay=False,
                   limitations=["One source-facing design per ordered equipment state; full reference views remain in the large plates.",
                                "Native height and baseline are checked; animation and equipment fitting require separate integration."])
    (ROOT / "exports/manifest.json").write_text(json.dumps(summary, indent=2) + "\n")
    data = json.dumps(summary, ensure_ascii=True).replace("<", "\\u003c")
    page = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Detailed artwork cutouts</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#1b212b;color:#f4f0e8}body{max-width:1500px;margin:auto;padding:28px}a{color:#a6ddcb}p,small{color:#bdc8d5}input,select{font:inherit;background:#2a3544;color:inherit;border:1px solid #4b5a6d;border-radius:6px;padding:10px}input{width:min(400px,85%)}.controls{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:14px}article{background:#273140;padding:14px;border-radius:8px}.picture{height:210px;background:#353e4b;display:flex;align-items:center;justify-content:center}.picture img{max-width:100%;max-height:200px;image-rendering:pixelated}h2{font-size:14px;overflow-wrap:anywhere}article a{font-size:13px}.links{display:flex;gap:12px;flex-wrap:wrap}
</style><a href="../index.html">← Large detailed sheets</a><h1>Detailed artwork cutouts</h1><p>Full-resolution individual objects from the detailed plates. Game-height downloads match the original inventory or player sprite height.</p><div class="controls"><input id="search" placeholder="Search a race, material or item…" aria-label="Search cutouts"><select id="kind" aria-label="Asset type"><option value="">All designs</option><option value="race">Races</option><option value="equipment">Equipment</option></select><select id="family" aria-label="Equipment family"><option value="">All materials</option></select></div><p id="count"></p><div id="grid"></div>
<p>These are transparent artwork exports. Height and baseline are checked; game animation and equipment fitting remain separate.</p><script>
const data=EXPORT_DATA;const url=p=>'../'+p.split('/').map(encodeURIComponent).join('/');const safe=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cards=[...data.races.map(x=>({title:x.race,kind:'race',family:'',cutout:x.source_cutout,height:x.game_height})),...data.entries.map(x=>({title:x.state_name,kind:'equipment',family:x.family,cutout:x.cutout.path,inventory:x.inventory.path,player:x.player.path}))];
const search=document.getElementById('search'),kind=document.getElementById('kind'),family=document.getElementById('family');[...new Set(data.entries.map(x=>x.family))].sort().forEach(x=>{const o=document.createElement('option');o.value=x;o.textContent=x;family.appendChild(o)});
function render(){const q=search.value.toLowerCase();const found=cards.filter(x=>(!kind.value||x.kind===kind.value)&&(!family.value||x.family===family.value)&&(!q||(x.title+' '+x.family).toLowerCase().includes(q)));document.getElementById('count').textContent=found.length+' of '+cards.length+' designs';document.getElementById('grid').innerHTML=found.map(x=>`<article><a class="picture" href="${url(x.cutout)}"><img loading="lazy" src="${url(x.cutout)}" alt="${safe(x.title)}"></a><h2>${safe(x.title)}</h2><div class="links"><a href="${url(x.cutout)}" download>Full-size PNG</a>${x.height?`<a href="${url(x.height)}" download>Game height</a>`:`<a href="${url(x.inventory)}" download>Inventory height</a><a href="${url(x.player)}" download>Player height</a>`}</div></article>`).join('')}[search,kind,family].forEach(x=>x.addEventListener('input',render));render();</script></html>"""
    (ROOT / "exports/index.html").write_text(page.replace("EXPORT_DATA", data))
    (ROOT / "exports/README.md").write_text("# Detailed artwork exports\n\nOpen `index.html` to browse 388 full-resolution transparent cutouts: 375 equipment states and 13 races.\n\n`game-height/inventory/` contains 375 variants matching the original 32-frame inventory icons. `game-height/player/` contains 375 variants matching the original 64-frame Human equipment references. `game-height/races/` contains 13 race variants matching each original visible height. Width is proportional and can vary.\n\nThe full-resolution cutouts preserve the detailed artwork colors before mechanical resizing. Height and bottom baseline are checked for every smaller PNG. These are size exports; equipment fitting, animations and runtime installation are separate tasks.\n")
    print(json.dumps(dict(states=375, source_cutouts=388, height_pngs=763)))


if __name__ == "__main__":
    main()
