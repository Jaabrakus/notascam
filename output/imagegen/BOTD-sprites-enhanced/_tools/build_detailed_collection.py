#!/usr/bin/env python3
"""Index full-resolution detailed artwork, excluding held candidates."""
from pathlib import Path
import hashlib
import json
import re
import shutil
from PIL import Image

PACK = Path(__file__).resolve().parents[1]
ROOT = PACK / "detailed-artwork"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def accepted(page):
    status = page.get("status", "").lower()
    if any(x in status for x in ("pending", "repair", "failed", "held", "candidate")):
        return False
    return any(x in status for x in ("checked", "complete", "review_pass"))


def main():
    plan = json.loads((ROOT / "production-plan.json").read_text())
    original = json.loads((PACK / "_meta/manifest.json").read_text())
    originals = {Path(x["source_path"]).stem: x for x in original["files"] if x["source_path"].startswith("Gear/")}
    families, pages = {}, []
    for family, group in plan["existing_families"].items():
        native = Path(original["native_source_repository_root"]) / originals[family]["native_source_relative_path"]
        with Image.open(native) as atlas:
            names = [json.loads(x) for x in re.findall(r'^state\s*=\s*(".*")\s*$', atlas.info["Description"], re.M)]
        entries = []
        for number, record in enumerate(group["pages"], 1):
            path = Path(record["path"])
            assert path.exists() and sha(path) == record["sha256"]
            reference = originals[family]["reference_outputs"][number - 1]
            page_names = reference.get("states", names)
            entry = dict(family=family, page=number, path=path.relative_to(ROOT).as_posix(),
                         sha256=sha(path), status="existing_checked_artwork", states=page_names,
                         state_indices=[names.index(x) for x in page_names])
            entries.append(entry)
        families[family] = dict(status="complete", ready_pages=len(entries), expected_pages=len(entries), state_count=len(names))
        pages.extend(entries)
    for family, group in plan["missing_families"].items():
        report_path = ROOT / "reports" / (family + ".json")
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        checked = {x["page"]: x for x in report.get("pages", []) if accepted(x)}
        ready = []
        for record in group["pages"]:
            number = record["page"]
            if number not in checked:
                continue
            audit = checked[number]
            path = Path(record["target"])
            assert path.exists(), (family, number, "accepted page missing")
            expected_sha = audit.get("output_sha256", audit.get("sha256"))
            assert not expected_sha or sha(path) == expected_sha, (family, number, "report hash mismatch")
            count = audit.get("observed_visible_cells")
            assert count == record["expected_visible_cells"], (family, number, count)
            entry = dict(family=family, page=number, path=path.relative_to(ROOT).as_posix(),
                         sha256=sha(path), status="new_detailed_artwork_checked",
                         states=[x["state_name"] for x in record["rows"]],
                         state_indices=[x["state_index"] for x in record["rows"]],
                         source_state_range=record["source_state_range"],
                         visible_cells=count)
            prompt = Path(audit["prompt"]) if audit.get("prompt") else None
            if prompt and prompt.exists():
                destination = ROOT / "prompts" / family / f"page-{number:02d}.txt"
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(prompt, destination)
                entry["prompt"] = destination.relative_to(ROOT).as_posix()
                entry["prompt_sha256"] = sha(destination)
                related = []
                for extra in sorted(prompt.parent.glob(f"detailed-{family}-page-{number:02d}*.txt")):
                    related_path = destination.parent / extra.name
                    shutil.copy2(extra, related_path)
                    related.append(dict(path=related_path.relative_to(ROOT).as_posix(), sha256=sha(related_path)))
                entry["related_prompts"] = related
            ready.append(entry)
        families[family] = dict(status="complete" if len(ready) == len(group["pages"]) else "in_progress",
                                ready_pages=len(ready), expected_pages=len(group["pages"]),
                                state_count=group["state_count"])
        pages.extend(ready)
    pages.sort(key=lambda x: (x["family"], x["page"]))
    races = [dict(title="13 races — eight body views", path="Races/races-8-angles.png"),
             dict(title="13 races — eight head views", path="Races/races-8-angles-heads.png"),
             dict(title="Kobold — original detailed sheet", path="Races/Kobold-detailed-sheet.png"),
             dict(title="Goblin — original detailed sheet", path="Races/Goblins-detailed-sheet.png"),
             dict(title="Kobold — detailed four-view sheet", path="Races/Kobold-four-views.png"),
             dict(title="Goblin — detailed four-view sheet", path="Races/Goblins-four-views.png")]
    for race in races:
        race["sha256"] = sha(ROOT / race["path"])
    complete = sum(x["status"] == "complete" for x in families.values())
    total = sum(x["expected_pages"] for x in families.values())
    if complete == 19:
        for family, group in families.items():
            covered = sorted(i for page in pages if page["family"] == family for i in page["state_indices"])
            assert covered == list(range(group["state_count"])), (family, "ordered state coverage mismatch")
    manifest = dict(classification="detailed_enhanced_sheet_artwork", status="complete" if complete == 19 else "in_progress",
                    race_bases=13, completed_equipment_families=complete, equipment_family_target=19,
                    ready_gear_pages=len(pages), expected_gear_pages=total, families=families,
                    equipment_state_target=sum(x["state_count"] for x in families.values()),
                    covered_equipment_states=sum(len(x["state_indices"]) for x in pages),
                    gear_pages=pages, race_plates=races, runtime_atlas_exports=False,
                    original_tool_resolution_retained=True,
                    limitations=["Detailed artwork plates, not runtime sprite atlases.",
                                 "Some embedded labels are abbreviated; the page metadata retains full names."])
    manifest["existing_detailed_gear_pages"] = sum(x["status"] == "existing_checked_artwork" for x in pages)
    manifest["new_detailed_gear_pages"] = sum(x["status"] == "new_detailed_artwork_checked" for x in pages)
    reviews = ["reports/independent-art-review.json", "reports/root-independent-art-review.json"]
    if all((ROOT / path).exists() for path in reviews):
        checked_pages = []
        for relative in reviews:
            review = json.loads((ROOT / relative).read_text())
            for group in review["families"].values():
                for page in group["pages"]:
                    assert page["status"].startswith("pass") and sha(Path(page["path"])) == page["sha256"], (relative, page["page"], "stale review")
                    checked_pages.append(page)
        assert len(checked_pages) == 50
        manifest["independent_art_reviews"] = reviews
        manifest["independently_reviewed_new_pages"] = len(checked_pages)
    export_manifest = ROOT / "exports/manifest.json"
    if export_manifest.exists():
        exports = json.loads(export_manifest.read_text())
        manifest["original_height_exports"] = {key: exports[key] for key in (
            "status", "equipment_states", "source_cutouts", "height_exports", "equipment_height_exports", "race_height_exports")}
        manifest["export_gallery"] = "exports/index.html"
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    data = json.dumps(manifest, ensure_ascii=True).replace("<", "\\u003c")
    template = """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Detailed enhanced artwork</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#181d26;color:#f4f0e8}body{max-width:1500px;margin:0 auto;padding:28px}h1{font-size:32px;margin:0 0 8px}p{color:#bcc6d4;line-height:1.55}a{color:#a5e0cf}
.bar{display:flex;gap:10px;flex-wrap:wrap;padding:14px 0;position:sticky;top:0;background:#181d26ed;z-index:1}input,select{font:inherit;padding:10px;border:1px solid #485467;border-radius:7px;color:inherit;background:#273140}input{flex:1;min-width:230px}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:18px}article{background:#252d3a;border:1px solid #3e4a5d;border-radius:10px;overflow:hidden}article img{width:100%;height:400px;object-fit:contain;background:#303640}article div{padding:15px}h2{font-size:18px;margin:0 0 8px}small{color:#b6c3d3}details{font-size:13px;line-height:1.5;margin-top:12px}li{overflow-wrap:anywhere}.links{padding:0;margin-top:12px;font-size:14px}#progress{padding-bottom:15px}
</style><h1>Detailed enhanced artwork</h1><p>Full-resolution race, weapon and armor sheets for the later 3D work. Open any plate to see the large artwork.</p><div id="progress"></div>
<div class="bar"><select id="section" aria-label="Artwork category"><option value="all">All artwork</option><option value="races">Races</option><option value="gear">Weapons and armor</option></select><select id="family" aria-label="Material family"><option value="">All families</option></select><input id="search" type="search" placeholder="Search material or item name…" aria-label="Search artwork"></div><div id="grid"></div>
<p>The full generated resolution is retained. Detailed plates are artwork references; original-height game exports are separate. Rejected candidates and native reshading previews are excluded from this gallery.</p><script>
const data=MANIFEST_DATA;
const safe=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const url=p=>p.split('/').map(encodeURIComponent).join('/');
const section=document.getElementById('section'),family=document.getElementById('family'),search=document.getElementById('search');
Object.keys(data.families).sort().forEach(x=>{const option=document.createElement('option');option.value=x;option.textContent=x;family.appendChild(option)});
document.getElementById('progress').textContent=data.completed_equipment_families+' / 19 equipment families ready · '+data.ready_gear_pages+' / '+data.expected_gear_pages+' equipment pages · 13 race bases';
function render(){const q=search.value.toLowerCase();let items=[];if(section.value!=='gear'&&!family.value)items.push(...data.race_plates.map(x=>({...x,kind:'races'})));if(section.value!=='races')items.push(...data.gear_pages.map(x=>({...x,title:x.family+' — page '+x.page,kind:'gear'})));items=items.filter(x=>(!family.value||x.family===family.value)&&(!q||(x.title+' '+(x.states||[]).join(' ')).toLowerCase().includes(q)));document.getElementById('grid').innerHTML=items.map(x=>`<article><a href="${url(x.path)}"><img loading="lazy" src="${url(x.path)}" alt="${safe(x.title)}"></a><div><h2>${safe(x.title)}</h2><small>Full-resolution detailed artwork</small><p class="links"><a href="${url(x.path)}">Open large image</a> · <a href="${url(x.path)}" download>PNG</a>${x.prompt?` · <a href="${url(x.prompt)}">Prompt</a>`:''}</p>${x.states&&x.states.length?`<details><summary>${x.states.length} source items</summary><ol>${x.states.map(s=>`<li>${safe(s)}</li>`).join('')}</ol></details>`:''}</div></article>`).join('');} [section,family,search].forEach(x=>x.addEventListener('input',render));render();
</script></html>"""
    (ROOT / "index.html").write_text(template.replace("MANIFEST_DATA", data))
    if export_manifest.exists():
        gallery = ROOT / "index.html"
        gallery.write_text(gallery.read_text().replace('<div id="progress"></div>',
            '<p><a href="exports/index.html">Browse individual full-size cutouts and original-height exports</a></p><div id="progress"></div>'))
    (ROOT / "README.md").write_text(f"# Detailed enhanced sheet artwork\n\nOpen `index.html` to browse the large plates. Currently {complete}/19 weapon and armor families are ready, with {len(pages)}/{total} equipment pages. The existing race plates cover all 13 base races.\n\nThis collection uses the detailed AI-enhanced sheet style selected by the user. Images retain their full generated resolution for later 3D work. Native/local reshading previews and rejected candidates are not listed. Original-height game exports remain separate.\n\n`manifest.json` records accepted pages and hashes. `prompts/` retains the prompts for new built-in image-tool artwork. Page metadata carries complete state names when embedded labels are abbreviated.\n")
    if export_manifest.exists():
        with (ROOT / "README.md").open("a") as description:
            description.write("\n## Individual artwork and original-height exports\n\nOpen `exports/index.html` for 388 transparent full-resolution cutouts:375 equipment states and 13 races. It also links763 original-height PNGs (375 inventory variants,375 player-equipment variants and 13 race variants). These come from the detailed artwork in this collection.\n\nEach smaller PNG matches the original visible height and bottom anchor; width follows the artwork proportions. The equipment exports use one source-facing view per state. Animation, equipment fitting and runtime installation remain separate.\n\nThe 50 new equipment pages were created with the built-in image tool, coordinated by Sol agents. The 10 existing detailed equipment pages and the original detailed race references were retained. Minor embedded-label, tiny-fragment and internal-gap variations are documented in the review reports.\n")
    release = ROOT / "release"
    release.mkdir(exist_ok=True)
    required = {"index.html", "manifest.json", "README.md"}
    required.update(x["path"] for x in pages + races)
    required.update(x["prompt"] for x in pages if x.get("prompt"))
    required.update(y["path"] for x in pages for y in x.get("related_prompts", []))
    required.update(path for path in reviews if (ROOT / path).exists())
    if export_manifest.exists():
        for record in exports["files"]:
            assert sha(ROOT / record["path"]) == record["sha256"], record["path"]
            required.add(record["path"])
        required.update(["exports/manifest.json", "exports/index.html", "exports/README.md"])
    for family, group in families.items():
        source_report = ROOT / "reports" / (family + ".json")
        if group["status"] == "complete" and source_report.exists():
            required.add("reports/" + family + ".json")
    owned = release / "published-files.json"
    previous = set(json.loads(owned.read_text())) if owned.exists() else set()
    for relative in previous - required:
        stale = release / relative
        assert stale.is_relative_to(release) and ".." not in Path(relative).parts
        if stale.is_file():
            stale.unlink()
    for relative in sorted(required):
        target = release / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    owned.write_text(json.dumps(sorted(required), indent=2) + "\n")
    print(json.dumps(dict(ready_families=complete, ready_pages=len(pages), total_pages=total,
                         clean_release=str(release))))


if __name__ == "__main__":
    main()
