#!/usr/bin/env python3
"""Read-only structural checks for a native DMI candidate against its source.

Pillow decodes the PNG container. Description is compared verbatim, including
unknown metadata, and is also parsed as an ordered list (never a name-keyed map).
No image is saved or changed. A passing report establishes these preservation
checks only; it cannot establish art quality, gameplay behavior, or integration.
"""

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import re
from typing import List, Tuple

from PIL import Image, ImageChops


ASSIGNMENT = re.compile(r"^\s*([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.*?)\s*$")
LIMITATIONS = [
    "Passing checks do not establish artistic improvement or runtime integration.",
    "Alpha equality preserves occupied coordinates, not the meaning of RGB details.",
    "RGB changes can include recoloring, accidental corruption, or changed features.",
    "Swapping RGB between states with identical alpha can pass; sprite identity is not verified.",
    "Runtime equipment alignment, animation playback, and visual review remain required.",
    "Decoded Description text is exact; PNG compression and chunk ordering may differ.",
]


@dataclass
class State:
    # Raw quoted names preserve escapes and distinguish every ordered occurrence.
    name: str
    fields: List[Tuple[str, str]]
    start_cell: int = 0
    directions: int = 1
    frames: int = 1


@dataclass
class Metadata:
    header: List[Tuple[str, str]]
    states: List[State]
    width: int
    height: int
    used_cells: int
    warnings: List[str]


@dataclass
class Asset:
    label: str
    file_sha256: str
    image: Image.Image
    original_mode: str
    container_format: str
    description: str
    metadata: Metadata


def integer_field(fields, key, default):
    values = [value for name, value in fields if name == key]
    if len(values) > 1:
        raise ValueError("Repeated metadata key {!r}".format(key))
    value = int(values[0]) if values else default
    if value <= 0:
        raise ValueError("{} must be positive".format(key))
    return value


def parse_description(description):
    """Validate like the native exporter, retaining ordered fields and states.

    Requirements mirror standalone/remastered/tools/export_sprite_assets.py.
    Extra positive delays and repeated hotspots are intentional supported cases.
    Unknown fields remain uninterpreted, but their exact values are retained.
    """
    if not isinstance(description, str):
        raise ValueError("PNG has no text Description metadata")
    lines = description.splitlines()
    if "# BEGIN DMI" not in [line.strip() for line in lines]:
        raise ValueError("Description lacks # BEGIN DMI")
    if "# END DMI" not in [line.strip() for line in lines]:
        raise ValueError("Description lacks # END DMI")
    header = []
    states = []
    current = None
    inside = False
    ended = False
    for line in lines:
        stripped = line.strip()
        if stripped == "# BEGIN DMI":
            if inside or ended:
                raise ValueError("Repeated or misplaced # BEGIN DMI")
            inside = True
            continue
        if stripped == "# END DMI":
            if not inside:
                raise ValueError("Misplaced # END DMI")
            inside, ended = False, True
            continue
        if not stripped or stripped.startswith("#"):
            continue
        if not inside:
            raise ValueError("Noncomment metadata outside DMI markers")
        match = ASSIGNMENT.match(line)
        if not match:
            raise ValueError("Unrecognized metadata line: {!r}".format(line))
        key, value = match.groups()
        if key == "state":
            try:
                name = json.loads(value)
            except (ValueError, TypeError) as error:
                raise ValueError("Invalid quoted state name") from error
            if not isinstance(name, str):
                raise ValueError("State name must be a quoted string")
            current = State(name=value, fields=[])
            states.append(current)
        elif current is None:
            if key in dict(header):
                raise ValueError("Duplicate DMI header {!r}".format(key))
            header.append((key, value))
        else:
            if key != "hotspot" and key in dict(current.fields):
                raise ValueError("Duplicate state field {!r}".format(key))
            current.fields.append((key, value))
    header_values = dict(header)
    if header_values.get("version") not in ("3.0", "4.0"):
        raise ValueError("Unsupported DMI metadata version {!r}".format(header_values.get("version")))
    if not states:
        raise ValueError("Description contains no states")
    width = integer_field(header, "width", 32)
    height = integer_field(header, "height", 32)
    used_cells = 0
    warnings = []
    for key in header_values.keys() - {"version", "width", "height"}:
        warnings.append("Unknown header {!r} retained without interpretation".format(key))
    for index, state in enumerate(states):
        state.directions = integer_field(state.fields, "dirs", 1)
        state.frames = integer_field(state.fields, "frames", 1)
        if state.directions not in (1, 4, 8):
            raise ValueError("State {} has invalid dirs {}; expected 1, 4, or 8".format(
                index, state.directions))
        fields = dict(state.fields)
        movement, rewind, loop = (int(fields.get(key, "0")) for key in ("movement", "rewind", "loop"))
        if movement not in (0, 1) or rewind not in (0, 1) or loop < 0:
            raise ValueError("Invalid movement/rewind/loop in state {}".format(index))
        delays = ([float(value.strip()) for value in fields["delay"].split(",")]
                  if "delay" in fields else [1.0] * state.frames)
        if len(delays) < state.frames or any(not math.isfinite(value) or value <= 0 for value in delays):
            raise ValueError("Invalid delay count/values in state {}".format(index))
        if len(delays) > state.frames:
            warnings.append("State {} has {} delays for {} frames; all retained".format(
                index, len(delays), state.frames))
        for key, value in state.fields:
            if key == "hotspot":
                values = [int(part.strip()) for part in value.split(",")]
                if len(values) != 3 or not 1 <= values[2] <= state.frames * state.directions:
                    raise ValueError("Invalid hotspot in state {}".format(index))
            elif key not in {"dirs", "frames", "delay", "movement", "rewind", "loop"}:
                warnings.append("State {} field {!r} retained without interpretation".format(index, key))
        state.start_cell = used_cells
        used_cells += state.directions * state.frames
    return Metadata(header, states, width, height, used_cells, warnings)


def load_asset(data, label="memory.dmi"):
    """Accept bytes so tests do not need to create or alter raster files."""
    # Match the exporter: check container integrity before accepting pixels.
    with Image.open(io.BytesIO(data)) as probe:
        probe.verify()
    with Image.open(io.BytesIO(data)) as decoded:
        if decoded.format != "PNG":
            raise ValueError("DMI candidate is not a PNG container")
        if getattr(decoded, "n_frames", 1) != 1:
            raise ValueError("Animated PNG is not a native DMI sprite sheet")
        description = decoded.info.get("Description")
        metadata = parse_description(description)
        image = decoded.convert("RGBA")
        mode = decoded.mode
        container_format = decoded.format
    if image.width % metadata.width or image.height % metadata.height:
        raise ValueError("Image dimensions are not divisible by DMI frame dimensions")
    capacity = (image.width // metadata.width) * (image.height // metadata.height)
    if metadata.used_cells > capacity:
        raise ValueError("DMI metadata describes more frames than fit in the image")
    return Asset(label, hashlib.sha256(data).hexdigest(), image, mode,
                 container_format, description, metadata)


def count_nonzero(channel):
    histogram = channel.histogram()
    return sum(histogram[1:])


def nonzero_mask(channel):
    return channel.point([0] + [255] * 255)


def rgb_difference_mask(left, right):
    red, green, blue = ImageChops.difference(left.convert("RGB"),
                                           right.convert("RGB")).split()
    return nonzero_mask(ImageChops.lighter(ImageChops.lighter(red, green), blue))


def metadata_summary(metadata):
    names = Counter(state.name for state in metadata.states)
    return {
        "header_fields": metadata.header,
        "frame_size": [metadata.width, metadata.height],
        "used_cells": metadata.used_cells,
        "parser_warnings": metadata.warnings,
        "duplicate_state_names": {key: value for key, value in names.items() if value > 1},
        "ordered_states": [
            {"index": index, "name_raw": state.name, "fields": state.fields,
             "start_cell": state.start_cell, "directions": state.directions,
             "frames": state.frames}
            for index, state in enumerate(metadata.states)
        ],
    }


def describe_asset(asset):
    return {
        "path": asset.label,
        "file_sha256": asset.file_sha256,
        "rgba_sha256": hashlib.sha256(asset.image.tobytes()).hexdigest(),
        "size": list(asset.image.size),
        "original_mode": asset.original_mode,
        "description_sha256": hashlib.sha256(asset.description.encode("utf-8")).hexdigest(),
        "metadata": metadata_summary(asset.metadata),
    }


def compare_assets(source, candidate, require_enhanced=False,
                   allow_transparent_rgb_changes=False):
    failures = []
    warnings = (["Source metadata: " + message for message in source.metadata.warnings]
                + ["Candidate metadata: " + message for message in candidate.metadata.warnings])
    report = {
        "schema_version": 1,
        "source": describe_asset(source),
        "candidate": describe_asset(candidate),
        "policy": {"require_enhanced": require_enhanced,
                   "allow_transparent_rgb_changes": allow_transparent_rgb_changes},
        "failures": failures, "warnings": warnings, "limitations": LIMITATIONS,
        "frames": [],
    }
    if source.description != candidate.description:
        failures.append("Description metadata text differs")
    source_summary = metadata_summary(source.metadata)
    candidate_summary = metadata_summary(candidate.metadata)
    if source_summary["ordered_states"] != candidate_summary["ordered_states"]:
        failures.append("Ordered states or their metadata differ")
    if source.image.size != candidate.image.size:
        failures.append("Image dimensions differ")
    if (source.metadata.width, source.metadata.height) != (
            candidate.metadata.width, candidate.metadata.height):
        failures.append("DMI frame dimensions differ")
    if source.original_mode != candidate.original_mode:
        warnings.append("PNG color mode differs; comparison uses decoded RGBA")
    if source.image.size == candidate.image.size:
        source_alpha = source.image.getchannel("A")
        candidate_alpha = candidate.image.getchannel("A")
        alpha_delta = ImageChops.difference(source_alpha, candidate_alpha)
        rgb_delta = rgb_difference_mask(source.image, candidate.image)
        visible_mask = nonzero_mask(source_alpha)
        visible_rgb_delta = ImageChops.multiply(rgb_delta, visible_mask)
        transparent_rgb_delta = ImageChops.multiply(rgb_delta, ImageChops.invert(visible_mask))
        alpha_changed = count_nonzero(alpha_delta)
        visible_changed = count_nonzero(visible_rgb_delta)
        transparent_changed = count_nonzero(transparent_rgb_delta)
        visible_count = count_nonzero(source_alpha)
        report["pixels"] = {
            "alpha_changed": alpha_changed,
            "visible_rgb_changed": visible_changed,
            "source_visible_pixels": visible_count,
            "visible_rgb_changed_fraction": visible_changed / visible_count if visible_count else 0,
            "transparent_rgb_changed": transparent_changed,
            "rgba_identical": source.image.tobytes() == candidate.image.tobytes(),
        }
        if alpha_changed:
            failures.append("Alpha values differ at {} coordinates".format(alpha_changed))
        if transparent_changed:
            message = "RGB differs at {} source-transparent coordinates".format(transparent_changed)
            (warnings if allow_transparent_rgb_changes else failures).append(message)
        if require_enhanced and not visible_changed:
            failures.append("No visible RGB changes; candidate is not an enhanced asset")
        elif not visible_changed:
            warnings.append("No visible RGB changes; valid only as a preservation baseline")
        width, height = source.metadata.width, source.metadata.height
        columns = source.image.width // width
        for state_index, state in enumerate(source.metadata.states):
            for slot in range(state.directions * state.frames):
                cell = state.start_cell + slot
                x, y = (cell % columns) * width, (cell // columns) * height
                box = (x, y, x + width, y + height)
                old_alpha = source_alpha.crop(box)
                new_alpha = candidate_alpha.crop(box)
                report["frames"].append({
                    "state_index": state_index, "state_name_raw": state.name,
                    "state_cell_offset": slot, "sheet_cell_index": cell,
                    "box": list(box), "source_alpha_bbox": old_alpha.getbbox(),
                    "candidate_alpha_bbox": new_alpha.getbbox(),
                    "alpha_changed": count_nonzero(alpha_delta.crop(box)),
                    "visible_rgb_changed": count_nonzero(visible_rgb_delta.crop(box)),
                    "transparent_rgb_changed": count_nonzero(transparent_rgb_delta.crop(box)),
                })
        capacity = columns * (source.image.height // height)
        report["padding"] = {"unused_cells": capacity - source.metadata.used_cells}
        padding_changed = 0
        for cell in range(source.metadata.used_cells, capacity):
            x, y = (cell % columns) * width, (cell // columns) * height
            box = (x, y, x + width, y + height)
            padding_changed += count_nonzero(rgb_delta.crop(box))
        report["padding"]["rgb_changed"] = padding_changed
        if padding_changed:
            failures.append("RGB changed in unused trailing DMI cells")
    report["passed"] = not failures
    return report


def validate_paths(source_path, candidate_path, **policy):
    try:
        source = load_asset(Path(source_path).read_bytes(), str(Path(source_path).resolve()))
        candidate = load_asset(Path(candidate_path).read_bytes(), str(Path(candidate_path).resolve()))
        return compare_assets(source, candidate, **policy)
    except (OSError, ValueError, TypeError, SyntaxError) as error:
        return {"schema_version": 1, "passed": False,
                "source": {"path": str(source_path)},
                "candidate": {"path": str(candidate_path)},
                "failures": ["Could not validate: {}".format(error)],
                "warnings": [], "limitations": LIMITATIONS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Original native .dmi")
    parser.add_argument("candidate", type=Path, help="Candidate native .dmi")
    parser.add_argument("--report", type=Path, required=True,
                        help="JSON report; never use an image path")
    parser.add_argument("--require-enhanced", action="store_true",
                        help="Require at least one changed visible RGB pixel")
    parser.add_argument("--allow-transparent-rgb-changes", action="store_true",
                        help="Warn instead of rejecting invisible RGB changes")
    args = parser.parse_args()
    if args.report.suffix.lower() != ".json":
        parser.error("--report must have a .json extension")
    if args.report.resolve() in (args.source.resolve(), args.candidate.resolve()):
        parser.error("Report path cannot overwrite either input")
    report = validate_paths(args.source, args.candidate,
                            require_enhanced=args.require_enhanced,
                            allow_transparent_rgb_changes=args.allow_transparent_rgb_changes)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("{}: {} ({} failures, {} warnings)".format(
        "PASS" if report["passed"] else "FAIL", args.candidate,
        len(report["failures"]), len(report["warnings"])))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
