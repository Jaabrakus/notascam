#!/usr/bin/env python3
"""Package reviewed existing-art exports and a portable, searchable preview."""
from pathlib import Path
import hashlib
import html
import json
import shutil
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFont

PACK = Path(__file__).resolve().parents[1]
DEST = PACK / "players-gear/final"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_asset(source, relative):
    source = Path(source)
    target = DEST / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    assert digest(source) == digest(target)
    return target


def add_image(entries, source, relative, title, kind, family, mode, height, full_source=None):
    output = copy_asset(source, relative)
    with Image.open(output) as image:
        assert image.mode == "RGBA", output
        bbox = image.getchannel("A").getbbox()
        assert bbox and bbox[3] - bbox[1] == height, (output, bbox, height)
        size = image.size
    item = dict(title=title, kind=kind, family=family, mode=mode,
                path=relative.as_posix(), visible_height=height,
                canvas_size=list(size), sha256=digest(output))
    if full_source:
        full_relative = Path("source-resolution") / relative
        full_output = copy_asset(full_source, full_relative)
        item["source_resolution"] = full_relative.as_posix()
        item["source_resolution_sha256"] = digest(full_output)
    entries.append(item)


def font(size):
    path = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    return ImageFont.truetype(str(path), size) if path.exists() else ImageFont.load_default()


def race_preview(entries):
    races = [x for x in entries if x["kind"] == "race"]
    scale = 3
    width = max(240, max(x["canvas_size"][0] for x in races) * scale + 24)
    height = 248
    image = Image.new("RGB", (width * 4, 64 + height * 4), (39, 44, 53))
    draw = ImageDraw.Draw(image)
    draw.text((18, 14), "Existing race artwork — original sprite heights", font=font(24), fill=(245, 243, 230))
    draw.text((18, 44), "Shown at 3x for inspection. Transparent PNGs are in races/.", font=font(14), fill=(180, 190, 200))
    for index, item in enumerate(races):
        x, y = index % 4 * width, 64 + index // 4 * height
        draw.text((x + 12, y + 8), item["title"], font=font(18), fill=(245, 243, 230))
        draw.text((x + 12, y + 30), f"{item['visible_height']} px tall", font=font(13), fill=(170, 190, 200))
        with Image.open(DEST / item["path"]) as sprite:
            sprite = sprite.resize((sprite.width * scale, sprite.height * scale), Image.Resampling.NEAREST)
            image.paste(sprite, (x + (width - sprite.width) // 2, y + height - 8 - sprite.height), sprite)
    image.save(DEST / "race-preview.png")


def gallery(entries):
    families = sorted({x["family"] for x in entries if x["kind"] != "race"})
    options = "".join(f'<option>{html.escape(x)}</option>' for x in families)
    data = json.dumps(entries, ensure_ascii=True).replace("<", "\\u003c")
    page = """<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Player races, weapons and armor</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#191d24;color:#f4f0e5}
body{max-width:1500px;margin:auto;padding:28px}h1{font-size:30px;margin:0 0 10px}p{color:#b4bfcd;line-height:1.55}
.controls{display:flex;gap:10px;flex-wrap:wrap;position:sticky;top:0;background:#191d24ee;padding:14px 0;z-index:1}
input,select,button{font:inherit;background:#2b3340;color:#f4f0e5;border:1px solid #475467;border-radius:7px;padding:10px}
input{min-width:240px;flex:1}button{cursor:pointer}button:focus-visible,a:focus-visible{outline:3px solid #80c7b6}
#grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px;margin-top:15px}
article{background:#232a35;border:1px solid #3b4555;border-radius:9px;padding:13px;overflow:hidden}
.picture{height:195px;display:flex;align-items:center;justify-content:center;background:var(--back,#303742);border-radius:5px}
.picture img{image-rendering:pixelated;object-fit:contain;max-width:100%;max-height:192px;width:auto;height:192px}
h2{font-size:14px;line-height:1.35;overflow-wrap:anywhere;margin:13px 0 6px}small{color:#b4bfcd}a{color:#a1dbc9}
.links{display:flex;gap:12px;font-size:13px;margin-top:10px}.count{font-size:14px}.note{font-size:13px;max-width:950px}
</style>
<h1>Player races, weapons and armor</h1>
<p>13 race designs · 375 equipment states · 32 additional cutouts from the enhanced sheets.<br>Original sprite heights, with proportional widths. Existing designs are preserved.</p>
<div class="controls"><input id="search" type="search" placeholder="Search races, swords, armor…" aria-label="Search sprites">
<select id="kind" aria-label="Sprite category"><option value="">All sprites</option value="race">Races</option><option value="equipment">Equipment</option></select>
<select id="mode" aria-label="Artwork source"><option value="">All artwork</option><option value="sheet">Existing sheet artwork</option><option value="game">Game equipment sprites</option></select>
<select id="family" aria-label="Equipment family"><option value="">All materials</option>FAMILY_OPTIONS</select>
<button id="background" type="button">Light background</button></div>
<div id="count" class="count" aria-live="polite"></div><div id="grid"></div>
<p class="note">The race and sheet-art cutouts retain their source colors before proportional resizing. Game equipment sprites come from the checked local enhancement pass. Some sheet cutouts retain minor edge residue from the original artwork. Full-resolution cutouts are included for later 3D work. These files have not been installed into the game.</p>
<script>
const data=CATALOG_DATA;
const controls=['search','kind','mode','family'].map(id=>document.getElementById(id));
const safe=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const url=p=>p.split('/').map(encodeURIComponent).join('/');
function render(){const [search,kind,mode,family]=controls.map(x=>x.value.toLowerCase());
const filtered=data.filter(x=>(!kind||x.kind===kind)&&(!mode||x.mode===mode)&&(!family||x.family.toLowerCase()===family)&&(!search||(x.title+' '+x.family).toLowerCase().includes(search)));
document.getElementById('count').textContent=filtered.length+' of '+data.length+' sprites';
document.getElementById('grid').innerHTML=filtered.map(x=>`<article><a class="picture" href="${url(x.path)}"><img loading="lazy" src="${url(x.path)}" alt="${safe(x.title)}"></a><h2>${safe(x.title)}</h2><small>${x.visible_height} px tall · ${x.mode==='sheet'?'Existing sheet art':'Game sprite'}</small><div class="links"><a href="${url(x.path)}" download>PNG</a>${x.source_resolution?`<a href="${url(x.source_resolution)}">Full-size cutout</a>`:''}</div></article>`).join('');}
controls.forEach(x=>x.addEventListener('input',render));let light=false;
document.getElementById('background').onclick=e=>{light=!light;document.documentElement.style.setProperty('--back',light?'#c5c5c5':'#303742');e.target.textContent=light?'Dark background':'Light background';};
render();</script></html>"""
    (DEST / "index.html").write_text(page.replace("FAMILY_OPTIONS", options).replace("CATALOG_DATA", data))


def main():
    assert not DEST.exists(), f"Refusing an existing delivery: {DEST}"
    races = json.loads((PACK / "_meta/faithful-races-batch.json").read_text())
    gear = json.loads((PACK / "_meta/faithful-equipment-batch.json").read_text())
    assert races["status"] == "complete" and gear["passed"]
    entries = []
    order = ["Human", "Dwarves", "Night Elf", "Orc", "Goblins", "Kobold", "LizardMan", "FrogMan", "Vampire", "Demon", "Gargoyle", "Skeleton", "DevourerZombie"]
    for race in sorted(races["files"], key=lambda x: order.index(x["race"])):
        add_image(entries, race["output"], Path("races") / (race["race"] + ".png"),
                  race["race"], "race", "", "sheet", race["native_reference"]["visible_height"], race["source_resolution_cutout"])
    for family, group in gear["approved_sheet_extractions"].items():
        for item in group["objects"]:
            assert item["visual_review"].startswith("independently_accepted")
            add_image(entries, item["output"], Path("equipment") / family / "sheet-art" / Path(item["output"]).name,
                      item["state_name"], "equipment", family, "sheet", item["original_visible_height"], item["cutout"])
    for family, group in gear["families"].items():
        assert group["all_rgba_exact"] and group["state_indices_complete"]
        for item in group["states"]:
            add_image(entries, item["output"], Path("equipment") / family / "catalog" / Path(item["output"]).name,
                      item["state_name"], "equipment", family, "game", item["original_visible_height"])
    assert len(entries) == 420
    queue = json.loads((PACK / "_meta/players-gear-queue.json").read_text())
    native = []
    for item in queue["files"]:
        source = PACK / item["output_relative_path"]
        relative = Path("native-sheets") / source.relative_to(PACK / "players-gear/processed")
        target = copy_asset(source, relative)
        native.append(dict(path=relative.as_posix(), sha256=digest(target)))
    assert len(native) == 279
    catalog = dict(status="complete_checked_existing_art_delivery", race_designs=13,
                   equipment_states=375, additional_sheet_cutouts=32, png_entries=entries,
                   native_sheet_count=279, native_sheets=native, runtime_installed=False,
                   notes=["Source-resolution race/sheet RGB is unchanged before resizing.",
                          "Game sprites are from the checked local enhancement pass.",
                          "Minor source edge residue is recorded in the independent review."])
    (DEST / "catalog.json").write_text(json.dumps(catalog, indent=2) + "\n")
    race_preview(entries)
    gallery(entries)
    (DEST / "README.md").write_text("# Player races, weapons and armor\n\nOpen `index.html` to browse and filter all 420 PNG entries. There are 13 existing-art race designs, 375 ordered equipment states, and 32 additional cutouts from the existing enhanced sheets. All preserve their original native visible heights.\n\n`source-resolution/` contains the larger race/sheet cutouts for later 3D work. `native-sheets/` contains all 279 validated local enhancement DMI sheets, preserving the original metadata, alpha masks and animations.\n\nThe race and enhanced-sheet artwork was extracted without repainting its source RGB. The game equipment catalog uses the earlier local enhancement pass. Minor source edge residue is documented in the independent reports. No files were installed into the running game.\n\nThis folder excludes rejected redesigns and earlier mask candidates. `catalog.json` records every delivered file and hash.\n")
    print(json.dumps(dict(output=str(DEST), races=13, equipment_states=375, sheet_cutouts=32, native_sheets=279)))


if __name__ == "__main__":
    main()
