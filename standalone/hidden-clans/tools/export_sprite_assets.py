#!/usr/bin/env python3
"""Export original game sprites to deterministic RGBA atlas pages and a manifest.

Requires Pillow. No original files are modified. See planning/SPRITE_PIPELINE.md.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile

from PIL import Image, __version__ as PILLOW_VERSION

BASE = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".godot", "backup", "backups", "dist", "generated", "tests", "test", "assets", "border-icons", "gear3d"}
DIRECTIONS = ["south", "north", "east", "west", "southeast", "southwest", "northeast", "northwest"]
DIRECTION_VALUES = [2, 1, 4, 8, 6, 10, 5, 9]
PIPELINE_ID = "dungeon-master-sprite-atlas-v1"
SOURCE_REFERENCE = "https://github.com/OpenDreamProject/OpenDream/blob/master/OpenDreamShared/Resources/DMIParser.cs"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(kind: str, *parts) -> str:
    return kind + "_" + digest(json.dumps(parts, ensure_ascii=True, separators=(",", ":")).encode())[:24]


def issue(issues: list, code: str, path: str, detail: str, severity="warning", **extra):
    issues.append(dict(severity=severity, code=code, path=path, detail=detail, **extra))


def strip_comments(text: str) -> str:
    """Remove DM comments, retaining line numbers and quoted resource literals."""
    return re.sub(r'''("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')|//[^\n]*|/\*[\s\S]*?\*/''',
                  lambda m: m[1] if m[1] is not None else "\n" * m[0].count("\n"), text)


def inside(root: Path, path: Path) -> bool:
    return path.resolve().is_relative_to(root.resolve())


def discover(root: Path, dme: Path, issues: list):
    """Inventory this source tree only, and resolve literals from DME-included files.

    Preprocessor conditions/macros are not evaluated: references are a conservative
    source inventory, not proof of runtime use.
    """
    files = sorted((p for p in root.rglob("*") if p.is_file() and
                    not any(part.lower() in EXCLUDED or part.lower().endswith(".app")
                            for part in p.relative_to(root).parts)),
                   key=lambda p: p.relative_to(root).as_posix())
    assets = [p for p in files if p.suffix.lower() in (".dmi", ".png")]
    # the page's own files (Interface/, e.g. gear3d/: sent to the page with browse_rsc, not DM icons): names of them in
    # the code are noted, not missing resources (coordinator 2026-10-25, Gear3DData.dm's rm_g3_files)
    page_names = {q.name.lower() for q in (root / "Interface").rglob("*") if q.is_file()} if (root / "Interface").is_dir() else set()
    by_lower = defaultdict(list)
    for p in files:
        by_lower[p.relative_to(root).as_posix().lower()].append(p)
    search = [root]
    included, seen = [], set()

    def visit(path):
        path = path.resolve()
        if path in seen:
            return
        seen.add(path)
        if not inside(root, path) or not path.is_file():
            issue(issues, "missing_include", path.name, "DME include missing or outside source root", "error")
            return
        included.append(path)
        text = strip_comments(path.read_text(encoding="latin-1"))
        for value in re.findall(r'^\s*#define\s+FILE_DIR\s+("[^"]+"|[^\s]+)', text, re.M):
            candidate = root / value.strip('"').replace("\\", "/")
            if inside(root, candidate) and candidate not in search:
                search.append(candidate)
        for value in re.findall(r'^\s*#include\s+"([^"]+)"', text, re.M):
            visit(path.parent / value.replace("\\", "/"))

    visit(dme)
    references = defaultdict(list)
    for p in sorted(included):
        text = strip_comments(p.read_text(encoding="latin-1"))
        for match in re.finditer(r'''["']([^"'\r\n]+\.(?:dmi|png))["']''', text, re.I):
            name = match[1].replace("\\", "/")
            record = {"source": p.relative_to(root).as_posix(),
                      "line": text.count("\n", 0, match.start()) + 1, "literal": match[1]}
            if "[" in name or "]" in name:
                issue(issues, "dynamic_image_name", record["source"],
                      "Runtime-generated image name is not a static source asset: " + name, "info",
                      line=record["line"])
                continue
            found = None
            for base in [root, p.parent, *search]:
                candidate = (base / name).resolve()
                if not inside(root, candidate):
                    continue
                candidates = by_lower.get(candidate.relative_to(root).as_posix().lower(), [])
                exact = next((p for p in candidates if p == candidate), None)
                if exact is not None:
                    found = exact
                    break
                if len(candidates) == 1:
                    found = candidates[0]
                    issue(issues, "resource_case_mismatch", record["source"], name,
                          resolved=found.relative_to(root).as_posix())
                    break
                if len(candidates) > 1:
                    issue(issues, "ambiguous_resource", record["source"], name, "error")
            if found is None and Path(name).name.lower() in page_names:
                issue(issues, "page_file", record["source"], name + ": the page's own file under Interface/", "info",
                      line=record["line"])
                continue
            if found is None:
                issue(issues, "missing_resource", record["source"], name, "error", line=record["line"])
            else:
                rel = found.relative_to(root).as_posix()
                references[rel].append(record)
                if found not in assets:
                    issue(issues, "excluded_resource", rel, "Included code references an excluded path", "error")
    return assets, references, included


def parse_description(description: str, size: tuple[int, int], path: str, issues: list):
    header, raw_states, current = {}, [], None
    for number, line in enumerate(description.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([a-zA-Z_]\w*)\s*=\s*(.*)", line)
        if not match:
            raise ValueError(f"Malformed DMI metadata at line {number}: {line!r}")
        key, value = match.groups()
        if key == "state":
            try:
                name = json.loads(value)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid quoted state name at line {number}") from exc
            if not isinstance(name, str):
                raise ValueError(f"Non-string state at line {number}")
            current = {"name": name, "metadata": [], "fields": {}}
            raw_states.append(current)
        elif current is None:
            if key in header:
                raise ValueError(f"Duplicate DMI header {key}")
            header[key] = value
        else:
            current["metadata"].append({"key": key, "value": value})
            if key in current["fields"] and key != "hotspot":
                raise ValueError(f"Duplicate {key} field in state {current['name']!r}")
            current["fields"][key] = value
    if header.get("version") not in ("3.0", "4.0"):
        raise ValueError(f"Unsupported DMI metadata version {header.get('version')!r}")
    for key in header.keys() - {"width", "height", "version"}:
        issue(issues, "unsupported_metadata", path, f"Header {key!r} retained without interpretation")
    w, h = int(header.get("width", 32)), int(header.get("height", 32))
    if w <= 0 or h <= 0 or size[0] % w or size[1] % h:
        raise ValueError(f"Sheet {size} is not a positive whole-cell grid of {(w, h)}")
    if not raw_states:
        raise ValueError("DMI metadata contains no states")
    states, seen, offset = [], Counter(), 0
    for index, raw in enumerate(raw_states):
        fields = raw["fields"]
        dirs, frames = int(fields.get("dirs", 1)), int(fields.get("frames", 1))
        movement, rewind, loop = (int(fields.get(k, 0)) for k in ("movement", "rewind", "loop"))
        if dirs not in (1, 4, 8) or frames < 1:
            raise ValueError(f"Invalid dirs/frames for state {raw['name']!r}: {dirs}/{frames}")
        if movement not in (0, 1) or rewind not in (0, 1) or loop < 0:
            raise ValueError(f"Invalid movement/rewind/loop for state {raw['name']!r}")
        delays = [float(v.strip()) for v in fields["delay"].split(",")] if "delay" in fields else [1.0] * frames
        if len(delays) < frames or any(not math.isfinite(v) or v <= 0 for v in delays):
            raise ValueError(f"Delay count/values do not match frames in state {raw['name']!r}")
        if len(delays) > frames:
            issue(issues, "extra_delays", path,
                  f"State {raw['name']!r} has {len(delays)} delays for {frames} frames; all retained, playback uses first {frames}",
                  state_index=index)
        pair = (raw["name"], movement)
        occurrence = seen[pair]
        seen[pair] += 1
        if occurrence:
            issue(issues, "duplicate_state", path,
                  f"State {raw['name']!r}, movement={movement}, occurrence {occurrence + 1}; preserved separately",
                  state_index=index)
        extra_keys = fields.keys() - {"dirs", "frames", "delay", "movement", "rewind", "loop", "hotspot"}
        for key in extra_keys:
            issue(issues, "unsupported_metadata", path, f"State field {key!r} retained without interpretation",
                  state_index=index)
        hotspots = []
        for entry in raw["metadata"]:
            if entry["key"] == "hotspot":
                values = [int(v.strip()) for v in entry["value"].split(",")]
                if len(values) != 3 or not 1 <= values[2] <= frames * dirs:
                    raise ValueError(f"Invalid hotspot in state {raw['name']!r}")
                hotspots.append({"x": values[0], "y": values[1], "cell_1based": values[2]})
        states.append(dict(id=stable_id("state", path, *pair, occurrence), name=raw["name"],
                           source_index=index, occurrence=occurrence, dirs=dirs, frames=frames,
                           delay_deciseconds=delays, playback_delay_deciseconds=delays[:frames],
                           delay_was_explicit="delay" in fields,
                           loop=loop, loop_was_explicit="loop" in fields, rewind=rewind,
                           movement=movement, hotspots=hotspots, metadata=raw["metadata"],
                           cell_offset=offset, cells=[]))
        offset += frames * dirs
    if offset > size[0] // w * (size[1] // h):
        raise ValueError(f"DMI requires {offset} cells but sheet has too few pixels")
    return (w, h), header, states


def decode_asset(path: Path, relative: str, issues: list):
    data = path.read_bytes()
    if data.startswith(b"\x04DMI"):
        raise ValueError("Legacy binary DMI is unsupported here; use standalone/tools/legacy_dmi.py first")
    if not data:
        raise ValueError("Empty source file")
    # verify() checks PNG chunk CRCs before any pixels are accepted.
    with Image.open(io.BytesIO(data)) as probe:
        probe.verify()
    with Image.open(io.BytesIO(data)) as im:
        fmt, size = im.format, im.size
        if fmt not in ("PNG", "GIF"):
            raise ValueError(f"Unsupported source format {fmt}")
        description = im.info.get("Description", "")
        if fmt == "PNG" and getattr(im, "n_frames", 1) != 1:
            raise ValueError("Animated PNG requires an explicit animation importer")
        if description:
            cell_size, header, states = parse_description(description, size, relative, issues)
            image = im.convert("RGBA")
            w, h = cell_size
            columns = image.width // w
            pixels = [image.crop(((i % columns) * w, (i // columns) * h,
                                  (i % columns + 1) * w, (i // columns + 1) * h))
                      for i in range(columns * (image.height // h))]
            sheet_hash = digest(image.tobytes())
            encoding = "dmi-png"
        else:
            header, pixels, delays = {}, [], []
            for i in range(getattr(im, "n_frames", 1)):
                im.seek(i)
                pixels.append(im.convert("RGBA").copy())
                delays.append(im.info.get("duration", 100) / 100)
            cell_size = size
            states = [dict(id=stable_id("state", relative, "", 0, 0), name="", source_index=0,
                           occurrence=0, dirs=1, frames=len(pixels), delay_deciseconds=delays,
                           playback_delay_deciseconds=delays,
                           delay_was_explicit=fmt == "GIF", loop=im.info.get("loop", 0),
                           loop_was_explicit="loop" in im.info, rewind=0, movement=0,
                           hotspots=[], metadata=[], cell_offset=0, cells=[])]
            sheet_hash = digest(pixels[0].tobytes()) if len(pixels) == 1 else None
            encoding = "gif" if fmt == "GIF" else "plain-png"
            if fmt == "GIF":
                issue(issues, "gif_with_dmi_extension", relative,
                      "GIF decoded as composited RGBA frames; GIF timing/loop metadata retained separately")
            elif path.suffix.lower() == ".dmi":
                issue(issues, "no_dmi_metadata", relative, "PNG without DMI metadata imported as one whole-image frame")
        asset = dict(id=stable_id("asset", relative), source=relative, source_sha256=digest(data),
                     bytes=len(data), status="exported", encoding=encoding, native_size=list(cell_size),
                     sheet_size=list(size), sheet_rgba_sha256=sheet_hash, description=description,
                     header=header, states=states, extra_cells=[])
        if fmt == "GIF":
            asset["gif"] = dict(loop=im.info.get("loop"),
                                duration_ms=[round(x * 100, 6) for x in delays],
                                loop_semantics="GIF repeat count; 0=infinite, null=one playback")
        return asset, pixels


class AtlasWriter:
    """Stable shelf packer; each frame retains its original RGBA bytes."""
    def __init__(self, output: Path, size: int, gutter: int):
        self.output, self.size, self.gutter = output, size, gutter
        self.pages = []
        self.image = None
        self.x = self.y = self.row_height = self.used_height = 0

    def flush(self):
        if self.image is None:
            return
        filename = f"atlas-{len(self.pages):03d}.png"
        target = self.output / filename
        self.image.save(target, format="PNG", optimize=False, compress_level=9)
        self.pages.append(dict(id=len(self.pages), file=filename, width=self.size, height=self.size,
                               used_height=self.used_height, sha256=digest(target.read_bytes()),
                               rgba_sha256=digest(self.image.tobytes())))
        self.image = None

    def add(self, pixels: Image.Image):
        w, h = pixels.size
        padded_w, padded_h = w + self.gutter * 2, h + self.gutter * 2
        if padded_w > self.size or padded_h > self.size:
            raise ValueError(f"Frame {pixels.size} plus gutter exceeds page size {self.size}")
        if self.image is None:
            self.image = Image.new("RGBA", (self.size, self.size), (0, 0, 0, 0))
            self.x = self.y = self.row_height = self.used_height = 0
        if self.x + padded_w > self.size:
            self.y += self.row_height
            self.x, self.row_height = 0, 0
        if self.y + padded_h > self.size:
            self.flush()
            return self.add(pixels)
        x, y = self.x + self.gutter, self.y + self.gutter
        # No alpha mask: a masked paste would blend/alter semitransparent pixels.
        self.image.paste(pixels, (x, y))
        entry = dict(page=len(self.pages), rect=[x, y, w, h], rgba_sha256=digest(pixels.tobytes()))
        self.x += padded_w
        self.row_height = max(self.row_height, padded_h)
        self.used_height = max(self.used_height, self.y + padded_h)
        return entry


def write_json(path: Path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def build(root: Path, output: Path, dme: Path, page_size=2048, gutter=1):
    issues = []
    paths, references, included = discover(root, dme, issues)
    writer = AtlasWriter(output, page_size, gutter)
    assets = []
    notices = []
    for name in ("LICENSE", "README", "README.md", "COPYING", "COPYING.txt"):
        source = root / name
        if source.is_file():
            target = output / "notices" / name
            target.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, target)
            notices.append(dict(source=name, file="notices/" + name, sha256=digest(source.read_bytes())))
    for path in paths:
        rel = path.relative_to(root).as_posix()
        try:
            asset, pixels = decode_asset(path, rel, issues)
            if any(max(p.size) + gutter * 2 > page_size for p in pixels):
                raise ValueError("Native frame plus gutter exceeds configured page size")
            used = 0
            w, h = asset["native_size"]
            columns = asset["sheet_size"][0] // w
            for state in asset["states"]:
                for frame in range(state["frames"]):
                    for direction in range(state["dirs"]):
                        cell = writer.add(pixels[used])
                        cell.update(frame=frame, direction=DIRECTIONS[direction],
                                    direction_value=DIRECTION_VALUES[direction], source_cell=used,
                                    source_rect=[used % columns * w, used // columns * h, w, h]
                                    if asset["encoding"] == "dmi-png" else [0, 0, w, h])
                        state["cells"].append(cell)
                        used += 1
            for index in range(used, len(pixels)):
                cell = writer.add(pixels[index])
                cell.update(source_cell=index, source_rect=[index % columns * w, index // columns * h, w, h],
                            visible=pixels[index].getchannel("A").getbbox() is not None)
                asset["extra_cells"].append(cell)
            visible = sum(c["visible"] for c in asset["extra_cells"])
            if visible:
                issue(issues, "unassigned_visible_cells", rel,
                      f"{visible} visible cells beyond declared states preserved in extra_cells")
        except (ValueError, OSError, SyntaxError) as exc:
            asset = dict(id=stable_id("asset", rel), source=rel, source_sha256=digest(path.read_bytes()),
                         bytes=path.stat().st_size, status="quarantined", reason=str(exc), states=[], extra_cells=[])
            issue(issues, "invalid_asset", rel, str(exc), "error" if rel in references else "warning")
        asset["references"] = references.get(rel, [])
        asset["notice_files"] = [n["file"] for n in notices]
        assets.append(asset)
    writer.flush()
    manifest = dict(schema_version=1, pipeline=PIPELINE_ID,
                    generator=dict(file="tools/export_sprite_assets.py", sha256=digest(Path(__file__).read_bytes()),
                                   pillow_version=PILLOW_VERSION),
                    source=dict(root_label=root.name, entrypoint=dme.relative_to(root).as_posix(),
                                included_files=[dict(path=p.relative_to(root).as_posix(), sha256=digest(p.read_bytes()))
                                                for p in sorted(included)],
                                references_are="Literal references in included files; macros and conditionals not evaluated"),
                    conventions=dict(rect="x,y,width,height; top-left origin; integer pixels", frame_index_base=0,
                                     cell_order="animation frame, then direction; source cells row-major",
                                     directions=[dict(name=n, value=v) for n, v in zip(DIRECTIONS, DIRECTION_VALUES)],
                                     delay_unit="deciseconds (multiply by 100 for milliseconds)",
                                     dmi_loop="Raw DMI loop value, default 0; retained for the target renderer",
                                     alpha="Unpremultiplied RGBA, including RGB underneath transparent pixels",
                                     sampling="Nearest neighbor, no mipmaps; transparent gutter is outside rect",
                                     duplicate_lookup="Resolve source + name + movement; multiple matching occurrences require explicit choice",
                                     pixel_offsets="Atom pixel_x/pixel_y, overlays and transforms live in gameplay source, not these sheets"),
                    configuration=dict(page_size=page_size, gutter=gutter),
                    notices=notices, format_reference=SOURCE_REFERENCE, pages=writer.pages, assets=assets, issues=issues)
    manifest["summary"] = dict(source_files=len(assets), exported_files=sum(a["status"] == "exported" for a in assets),
                               quarantined_files=sum(a["status"] == "quarantined" for a in assets),
                               states=sum(len(a["states"]) for a in assets),
                               animation_cells=sum(len(s["cells"]) for a in assets for s in a["states"]),
                               extra_cells=sum(len(a["extra_cells"]) for a in assets), pages=len(writer.pages),
                               errors=sum(i["severity"] == "error" for i in issues), warnings=sum(i["severity"] == "warning" for i in issues))
    write_json(output / "manifest.json", manifest)
    return manifest


def verify(root: Path, output: Path, manifest: dict) -> dict:
    """Independently reconstruct original sheets from saved atlas PNGs."""
    pages = []
    for p in manifest["pages"]:
        path = output / p["file"]
        if digest(path.read_bytes()) != p["sha256"]:
            raise ValueError(f"Atlas hash mismatch: {p['file']}")
        im = Image.open(path).convert("RGBA")
        if digest(im.tobytes()) != p["rgba_sha256"]:
            raise ValueError(f"Atlas pixel hash mismatch: {p['file']}")
        pages.append(im)
    cells, sheets, gif_frames = 0, 0, 0
    for asset in manifest["assets"]:
        source = root / asset["source"]
        if digest(source.read_bytes()) != asset["source_sha256"]:
            raise ValueError(f"Source changed during export: {asset['source']}")
        if asset["status"] != "exported":
            continue
        with Image.open(source) as original:
            reconstructed = Image.new("RGBA", tuple(asset["sheet_size"]))
            records = [cell for state in asset["states"] for cell in state["cells"]] + asset["extra_cells"]
            for cell in records:
                x, y, w, h = cell["rect"]
                page = pages[cell["page"]]
                if x < 0 or y < 0 or x + w > page.width or y + h > page.height:
                    raise ValueError(f"Atlas rect outside page: {asset['source']}")
                pixels = page.crop((x, y, x + w, y + h))
                if digest(pixels.tobytes()) != cell["rgba_sha256"]:
                    raise ValueError(f"Frame pixel mismatch: {asset['source']}")
                if asset["encoding"] == "gif":
                    original.seek(cell["frame"])
                    if pixels.tobytes() != original.convert("RGBA").tobytes():
                        raise ValueError(f"GIF frame mismatch: {asset['source']}")
                    gif_frames += 1
                else:
                    sx, sy, _, _ = cell["source_rect"]
                    reconstructed.paste(pixels, (sx, sy))
                cells += 1
            if asset["encoding"] != "gif":
                if reconstructed.tobytes() != original.convert("RGBA").tobytes():
                    raise ValueError(f"Full sheet pixel mismatch: {asset['source']}")
                sheets += 1
    return dict(passed=True, sheets_reconstructed=sheets, gif_frames_compared=gif_frames,
                cells_compared=cells, pages_checked=len(pages), original_files_unchanged=True)


def export(root: Path, output: Path, dme: Path, page_size=2048, gutter=1):
    root, output, dme = root.resolve(), output.resolve(), dme.resolve()
    if page_size < 4 or gutter < 0 or gutter * 2 >= page_size:
        raise ValueError("Invalid page size or gutter")
    if inside(root, output) or inside(output, root) or output == root:
        raise ValueError("Output and original source tree must be separate")
    if output.exists() and any(output.iterdir()):
        marker = output / "manifest.json"
        if not marker.is_file() or json.loads(marker.read_text()).get("pipeline") != PIPELINE_ID:
            raise ValueError("Refusing to replace a non-pipeline output directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".sprite-export-", dir=output.parent) as temporary:
        stage = Path(temporary) / "export"
        stage.mkdir()
        manifest = build(root, stage, dme, page_size, gutter)
        validation = verify(root, stage, manifest)
        write_json(stage / "validation.json", validation)
        if output.exists():
            shutil.rmtree(output)
        shutil.move(str(stage), output)
    return manifest, validation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=BASE / "game")
    parser.add_argument("--output", type=Path, default=BASE / "assets" / "sprites")
    parser.add_argument("--dme", type=Path, help="Relative to --source, defaults to Cave Crawlers.dme")
    parser.add_argument("--page-size", type=int, default=2048)
    parser.add_argument("--gutter", type=int, default=1)
    args = parser.parse_args()
    try:
        manifest, validation = export(args.source, args.output,
                                      args.source / (args.dme or "Cave Crawlers.dme"), args.page_size, args.gutter)
    except (ValueError, OSError) as exc:
        parser.exit(1, f"Sprite export failed: {exc}\n")
    print(json.dumps(dict(output=str(args.output.resolve()), **manifest["summary"], validation=validation), indent=2))
    return 1 if manifest["summary"]["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
