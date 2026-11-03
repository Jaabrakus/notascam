#!/usr/bin/env python3
"""Mechanically package one transparent AI-created sprite as native 64x64 PNGs.

Only transparent-margin cropping, proportional resizing, and placement occur.
There is no drawing, color adjustment, sharpening, 3D rendering, or generation.
Input artwork and existing output files are never overwritten.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
import PIL

FRAME = (64, 64)
STAGING = Path(__file__).resolve().parents[1]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_box(value: str) -> tuple[int, int, int, int]:
    try:
        box = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use x0,y0,x1,y1 integer coordinates") from exc
    if len(box) != 4 or not (0 <= box[0] < box[2] <= 64 and 0 <= box[1] < box[3] <= 64):
        raise argparse.ArgumentTypeError("Content box must lie within the 64x64 frame")
    return box


def parse_source_crop(value: str) -> tuple[int, int, int, int]:
    try:
        box = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Use x0,y0,x1,y1 integer coordinates") from exc
    if len(box) != 4 or not (0 <= box[0] < box[2] and 0 <= box[1] < box[3]):
        raise argparse.ArgumentTypeError("Source crop must be a positive rectangle inside the input image")
    return box


def default_native_source() -> Path:
    override = os.environ.get("BOTD_PROJECT_ROOT")
    if override:
        project = Path(override).expanduser()
    else:
        manifest = STAGING / "_meta/manifest.json"
        try:
            project = Path(json.loads(manifest.read_text())["native_source_repository_root"])
        except (OSError, ValueError, KeyError) as exc:
            raise ValueError("Cannot find native Goblin reference. Pass --native-source, "
                             "set BOTD_PROJECT_ROOT, or provide --content-box.") from exc
    return (project / "standalone/remastered/game/Icons/Remastered/Races64/Goblins.dmi").resolve()


def native_goblin_box(path: Path) -> tuple[tuple[int, int, int, int], dict]:
    raw = path.read_bytes()
    with Image.open(io.BytesIO(raw)) as atlas:
        description = atlas.info.get("Description", "")
        width = re.search(r"(?m)^\s*width\s*=\s*(\d+)", description)
        height = re.search(r"(?m)^\s*height\s*=\s*(\d+)", description)
        first_state = re.search(r'(?m)^state\s*=\s*"([^"]*)"', description)
        if not width or not height or (int(width[1]), int(height[1])) != FRAME:
            raise ValueError("Native Goblin DMI must declare 64x64 cells")
        if not first_state or first_state[1] != "":
            raise ValueError("Expected first native Goblin state to be the default standing/walk state")
        cell = atlas.convert("RGBA").crop((0, 0, 64, 64))
        bbox = cell.getchannel("A").getbbox()
        if bbox is None:
            raise ValueError("Native Goblin standing south frame is empty")
        return bbox, dict(path=str(path), sha256=sha256(raw), atlas_size=list(atlas.size),
                          state="", frame_index=0, direction="S", cell_index=0,
                          cell_size=list(FRAME), alpha_bbox=list(bbox))


def load_transparent_sprite(path: Path) -> tuple[Image.Image, dict]:
    raw = path.read_bytes()
    with Image.open(io.BytesIO(raw)) as source:
        if source.format != "PNG" or getattr(source, "n_frames", 1) != 1:
            raise ValueError("Input must be one static PNG containing a single sprite")
        if "A" not in source.getbands() and "transparency" not in source.info:
            raise ValueError("Input has no alpha/transparency channel; opaque sheets are refused")
        rgba = source.convert("RGBA")
        mode = source.mode
    alpha = rgba.getchannel("A")
    histogram = alpha.histogram()
    total = rgba.width * rgba.height
    transparent = histogram[0]
    if transparent == 0:
        raise ValueError("Input has no fully transparent background pixels; opaque sheets are refused")
    if transparent == total:
        raise ValueError("Input is entirely transparent")
    if transparent < max(16, math.ceil(total * 0.01)):
        raise ValueError("Input lacks a meaningful transparent background; inspect or regenerate the single sprite")
    pixels = alpha.load()
    perimeter = ([pixels[x, 0] for x in range(rgba.width)]
                 + [pixels[x, rgba.height - 1] for x in range(rgba.width)]
                 + [pixels[0, y] for y in range(1, rgba.height - 1)]
                 + [pixels[rgba.width - 1, y] for y in range(1, rgba.height - 1)])
    clear_fraction = sum(value == 0 for value in perimeter) / len(perimeter)
    if clear_fraction < 0.90:
        raise ValueError("Background remains around the image perimeter; supply a padded transparent single sprite")
    bbox = alpha.getbbox()
    return rgba, dict(path=str(path), sha256=sha256(raw), size=list(rgba.size),
                      original_mode=mode, working_mode="RGBA", crop_alpha_bbox=list(bbox),
                      crop_rule="Smallest rectangle containing alpha > 0; no alpha threshold or background removal",
                      fully_transparent_pixels=transparent,
                      transparent_perimeter_fraction=clear_fraction,
                      semi_transparent_pixels=sum(histogram[1:255]),
                      input_is_single_sprite="Required from caller; visual identity and sheet content must be reviewed",
                      background_validation="Transparent pixels and perimeter verified; opaque/background-filled sheets refused")


def fit_placement(crop_size, content_box, anchor_x=None, feet_anchor=None) -> dict:
    x0, y0, x1, y1 = content_box
    center = (x0 + x1) / 2 if anchor_x is None else anchor_x
    feet = y1 if feet_anchor is None else feet_anchor
    if not math.isfinite(center) or not x0 < center < x1 or not y0 < feet <= y1:
        raise ValueError("Anchor x and feet anchor must lie inside the content box (feet may equal its bottom)")
    available_width = 2 * min(center - x0, x1 - center)
    available_height = feet - y0
    factor = min(available_width / crop_size[0], available_height / crop_size[1])
    width = max(1, min(int(math.floor(available_width)), int(math.floor(crop_size[0] * factor + 0.5))))
    height = max(1, min(available_height, int(math.floor(crop_size[1] * factor + 0.5))))
    left = int(math.floor(center - width / 2 + 0.5))
    top = feet - height
    if left < x0 or left + width > x1 or top < y0 or top + height > y1:
        raise ValueError("Chosen anchors and rounded size cannot fit within the content box")
    return dict(content_box=list(content_box), anchor_x=center,
                feet_anchor_bottom_exclusive=feet,
                source_crop_size=list(crop_size), resized_size=[width, height],
                uniform_fit_scale=factor,
                actual_axis_scales=[width / crop_size[0], height / crop_size[1]],
                rounding="Nearest integer dimensions; aspect ratio differs only by unavoidable pixel rounding",
                destination_box=[left, top, left + width, top + height])


def package_sprite(cropped: Image.Image, placement: dict, method: str) -> Image.Image:
    size = tuple(placement["resized_size"])
    if method == "nearest":
        resized = cropped.resize(size, Image.Resampling.NEAREST)
    elif method == "lanczos":
        # Premultiplied-alpha interpolation avoids introducing hidden RGB halos.
        resized = cropped.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    else:
        raise ValueError(f"Unsupported resampling method: {method}")
    result = Image.new("RGBA", FRAME, (0, 0, 0, 0))
    left, top = placement["destination_box"][:2]
    result.paste(resized, (left, top))  # Copy RGBA; a mask would multiply alpha twice.
    result.putdata([(0, 0, 0, 0) if pixel[3] == 0 else pixel for pixel in result.getdata()])
    return result


def export_sprite(input_path: Path, output_dir: Path, name: str, methods=("nearest", "lanczos"),
                  content_box=None, anchor_x=None, feet_anchor=None, native_source=None,
                  source_crop=None) -> Path:
    input_path = input_path.expanduser().resolve()
    output_dir = output_dir.expanduser().resolve()
    if not name or Path(name).name != name or name in (".", ".."):
        raise ValueError("Output name must be a filename stem without directories")
    if not methods or any(method not in ("nearest", "lanczos") for method in methods) or len(set(methods)) != len(methods):
        raise ValueError("Choose unique nearest and/or lanczos methods")
    rgba, source_record = load_transparent_sprite(input_path)
    native_record = None
    if content_box is None:
        path = Path(native_source).expanduser().resolve() if native_source else default_native_source()
        content_box, native_record = native_goblin_box(path)
    content_box = parse_box(",".join(str(value) for value in content_box))
    original_alpha_bbox = tuple(source_record["crop_alpha_bbox"])
    crop = original_alpha_bbox if source_crop is None else parse_source_crop(",".join(str(v) for v in source_crop))
    if crop[2] > rgba.width or crop[3] > rgba.height:
        raise ValueError("Requested source crop extends beyond the original image")
    cropped = rgba.crop(crop)
    if cropped.getchannel("A").getbbox() is None:
        raise ValueError("Requested source crop contains no visible artwork")
    original_histogram = rgba.getchannel("A").histogram()
    kept_histogram = cropped.getchannel("A").histogram()
    discarded_histogram = [whole - kept for whole, kept in zip(original_histogram, kept_histogram)]
    source_record.update(original_alpha_bbox=list(original_alpha_bbox),
                         requested_source_crop=list(source_crop) if source_crop is not None else None,
                         effective_source_crop=list(crop),
                         crop_rgba_sha256=sha256(cropped.tobytes()),
                         discarded_pixel_count=sum(discarded_histogram),
                         discarded_nonzero_alpha_pixel_count=sum(discarded_histogram[1:]),
                         discarded_maximum_alpha=max((i for i, count in enumerate(discarded_histogram) if count), default=0),
                         inside_crop_rgba_preserved_exactly=True)
    if source_crop is not None:
        source_record["crop_rule"] = "Explicit requested source rectangle; all RGBA pixels inside preserved, no threshold filtering"
    placement = fit_placement(cropped.size, content_box, anchor_x, feet_anchor)
    output_paths = {method: output_dir / f"{name}.{method}.64.png" for method in methods}
    report_path = output_dir / f"{name}.export.json"
    for path in [*output_paths.values(), report_path]:
        if path == input_path or path.exists():
            raise ValueError(f"Refusing to overwrite existing or source file: {path}")
    rendered, records = {}, []
    for method, path in output_paths.items():
        image = package_sprite(cropped, placement, method)
        assert image.size == FRAME and image.mode == "RGBA"
        assert all(pixel == (0, 0, 0, 0) for pixel in image.getdata() if pixel[3] == 0)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        rendered[path] = buffer.getvalue()
        alpha = image.getchannel("A")
        bbox = alpha.getbbox()
        if bbox is None:
            raise ValueError(f"Sprite disappears at this scale with {method}; choose a larger content box or different resampler")
        records.append(dict(path=str(path), sha256=sha256(rendered[path]), size=list(image.size),
                            mode=image.mode, resample=method,
                            alpha_bbox=list(bbox),
                            alpha_sha256=sha256(alpha.tobytes()),
                            zero_rgba_outside_alpha=True,
                            semi_transparent_pixels=sum(alpha.histogram()[1:255])))
    record = dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
                  status="mechanical_64x64_export_pending_visual_review",
                  source=source_record, native_reference=native_record, placement=placement,
                  outputs=records, frame_size=list(FRAME),
                  operations=["Explicit requested source rectangle crop" if source_crop is not None else "Crop alpha-zero margins",
                              "Resize proportionally using requested resampler",
                              "Place on transparent 64x64 frame at recorded anchor", "Clear hidden RGB where alpha is zero"],
                  artwork_redrawn=False, creative_filters_applied=False, source_overwritten=False,
                  three_dimensional_conversion=False, runtime_installed=False,
                  drop_in_original_registration_claimed=False,
                  delivery_scope="Single-sprite 64x64 design review variants; not completed game assets",
                  script=dict(path=str(Path(__file__).resolve()), sha256=sha256(Path(__file__).read_bytes())),
                  pillow_version=PIL.__version__,
                  limitations=["Single-sprite identity requires visual review", "Native sizing alone does not verify a complete animation atlas"])
    output_dir.mkdir(parents=True, exist_ok=True)
    for path, data in rendered.items():
        with path.open("xb") as destination:
            destination.write(data)
    with report_path.open("x") as destination:
        destination.write(json.dumps(record, indent=2) + "\n")
    assert sha256(input_path.read_bytes()) == source_record["sha256"]
    return report_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Already generated, transparent, single-sprite PNG")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--name", help="Output filename stem (defaults to input stem)")
    parser.add_argument("--filter", choices=("nearest", "lanczos", "both"), default="both")
    parser.add_argument("--source-crop", type=parse_source_crop,
                        help="Explicit source x0,y0,x1,y1; preserves all pixels inside without alpha thresholding")
    parser.add_argument("--content-box", type=parse_box, help="x0,y0,x1,y1; defaults to native Goblin standing alpha bounds")
    parser.add_argument("--anchor-x", type=float, help="Horizontal center; defaults to content-box center")
    parser.add_argument("--feet-anchor", type=int, help="Bottom-exclusive pixel row; defaults to content-box bottom")
    parser.add_argument("--native-source", type=Path, help="Optional native Goblins.dmi used for default bounds")
    args = parser.parse_args()
    methods = ("nearest", "lanczos") if args.filter == "both" else (args.filter,)
    try:
        report = export_sprite(args.input, args.output_dir, args.name or args.input.stem,
                               methods, args.content_box, args.anchor_x, args.feet_anchor, args.native_source,
                               args.source_crop)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Export refused: {exc}\n")
    print(json.dumps(dict(report=str(report), status="exported_64x64_pending_visual_review"), indent=2))


if __name__ == "__main__":
    main()
