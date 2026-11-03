#!/usr/bin/env python3
"""Size transparent generated artwork to an original sprite's visible height.

This tool only crops transparent margins, resizes proportionally, and places
RGBA pixels. It never draws, relights, thresholds alpha, or changes source files.
Native frame height and bottom baseline are retained. Width is free to grow.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import PIL
from PIL import Image

from export_sprite64 import load_transparent_sprite, parse_source_crop
from validate_dmi import load_asset


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def native_cell_reference(path: Path, cell_index: int) -> dict:
    """Read an ordered native cell; duplicate state names remain distinct."""
    path = path.expanduser().resolve()
    raw = path.read_bytes()
    asset = load_asset(raw, str(path))
    metadata = asset.metadata
    if not 0 <= cell_index < metadata.used_cells:
        raise ValueError("Native cell index is outside the declared states; padding cells cannot be references")
    width, height = metadata.width, metadata.height
    columns = asset.image.width // width
    left, top = (cell_index % columns) * width, (cell_index // columns) * height
    cell = asset.image.crop((left, top, left + width, top + height))
    bbox = cell.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("Native cell is intentionally transparent; preserve it as empty instead of creating artwork")
    state_index, state = next((i, state) for i, state in enumerate(metadata.states)
                             if state.start_cell <= cell_index < state.start_cell + state.directions * state.frames)
    within_state = cell_index - state.start_cell
    direction_names = ("S", "N", "E", "W", "SE", "SW", "NE", "NW")
    return dict(path=str(path), sha256=sha256(raw), cell_index=cell_index,
                atlas_size=list(asset.image.size), frame_size=[width, height],
                alpha_bbox=list(bbox), visible_height=bbox[3] - bbox[1],
                visible_width=bbox[2] - bbox[0], bottom_baseline_exclusive=bbox[3],
                alpha_sha256=sha256(cell.getchannel("A").tobytes()),
                state_occurrence_index=state_index, state_name=json.loads(state.name),
                state_fields=state.fields, frame_index=within_state // state.directions,
                direction_index=within_state % state.directions,
                direction=direction_names[within_state % state.directions],
                description_sha256=sha256(asset.description.encode("utf-8")))


def prepared_crop(rgba: Image.Image, source_record: dict, source_crop=None) -> Image.Image:
    """Apply only an explicit rectangular crop and exact zero-alpha trim."""
    original_bbox = tuple(source_record["crop_alpha_bbox"])
    rectangle = original_bbox if source_crop is None else parse_source_crop(
        ",".join(str(value) for value in source_crop))
    if rectangle[2] > rgba.width or rectangle[3] > rgba.height:
        raise ValueError("Source crop extends beyond the image")
    cropped = rgba.crop(rectangle)
    local_alpha_bbox = cropped.getchannel("A").getbbox()
    if local_alpha_bbox is None:
        raise ValueError("Source crop contains no artwork")
    # Trimming alpha-zero rows/columns does not alter any visible pixel.
    cropped = cropped.crop(local_alpha_bbox)
    effective = [rectangle[0] + local_alpha_bbox[0], rectangle[1] + local_alpha_bbox[1],
                 rectangle[0] + local_alpha_bbox[2], rectangle[1] + local_alpha_bbox[3]]
    original_hist = rgba.getchannel("A").histogram()
    cropped_hist = cropped.getchannel("A").histogram()
    discarded = [whole - kept for whole, kept in zip(original_hist, cropped_hist)]
    source_record.update(original_alpha_bbox=list(original_bbox),
                         requested_source_crop=list(source_crop) if source_crop is not None else None,
                         effective_source_crop=effective, source_crop_size=list(cropped.size),
                         crop_rgba_sha256=sha256(cropped.tobytes()),
                         crop_rule="Explicit rectangle if supplied, followed by alpha-zero margin trim; no alpha threshold",
                         discarded_pixel_count=sum(discarded),
                         discarded_nonzero_alpha_pixel_count=sum(discarded[1:]),
                         discarded_maximum_alpha=max((i for i, count in enumerate(discarded) if count), default=0),
                         retained_source_rgba_preserved_before_resize=True)
    return cropped


def resize_and_place(crop: Image.Image, target_height: int, method: str,
                     native_reference=None, frame_height=None, baseline=None):
    if not isinstance(target_height, int) or target_height <= 0:
        raise ValueError("Target visible height must be a positive integer")
    width = max(1, int(math.floor(crop.width * target_height / crop.height + 0.5)))
    size = (width, target_height)
    if method == "nearest":
        resized = crop.resize(size, Image.Resampling.NEAREST)
    elif method == "lanczos":
        resized = crop.convert("RGBa").resize(size, Image.Resampling.LANCZOS).convert("RGBA")
    else:
        raise ValueError("Choose nearest or lanczos resampling")
    visible = resized.getchannel("A").getbbox()
    if visible is None:
        raise ValueError("Artwork disappears at the requested height")
    if visible[3] - visible[1] != target_height:
        raise ValueError(f"Resizing lost sparse top/bottom pixels: actual visible height {visible[3] - visible[1]}, "
                         f"required {target_height}. Review the source crop or choose the other resampler.")
    if native_reference is not None:
        native_width, frame_height = native_reference["frame_size"]
        old_left, old_top, old_right, baseline = native_reference["alpha_bbox"]
        old_width = old_right - old_left
        # Preserve both original side margins when the new design is wider.
        # If narrower, center within the original visible region without stretching.
        canvas_width = native_width + max(0, width - old_width)
        left = old_left + max(0, (old_width - width) // 2)
        horizontal_policy = "Keep native side margins when wider; center narrower art in the native visible region"
    else:
        frame_height = target_height if frame_height is None else frame_height
        baseline = frame_height if baseline is None else baseline
        canvas_width, left = width, 0
        horizontal_policy = "Tight proportional width for explicit-height export"
    if not isinstance(frame_height, int) or frame_height <= 0:
        raise ValueError("Frame height must be a positive integer")
    if not isinstance(baseline, int) or not target_height <= baseline <= frame_height:
        raise ValueError("Bottom baseline must fit the complete visible sprite inside the frame")
    top = baseline - target_height
    result = Image.new("RGBA", (canvas_width, frame_height), (0, 0, 0, 0))
    result.paste(resized, (left, top))
    result.putdata([(0, 0, 0, 0) if pixel[3] == 0 else pixel for pixel in result.getdata()])
    actual_bbox = result.getchannel("A").getbbox()
    assert actual_bbox is not None and actual_bbox[3] - actual_bbox[1] == target_height
    assert actual_bbox[3] == baseline
    placement = dict(target_visible_height=target_height, proportional_content_size=list(size),
                     uniform_scale=target_height / crop.height,
                     actual_axis_scales=[width / crop.width, target_height / crop.height],
                     width_rounding="Nearest integer; no independent width fit or distortion",
                     canvas_size=list(result.size), destination_box=[left, top, left + width, top + target_height],
                     actual_alpha_bbox=list(actual_bbox), actual_visible_height=actual_bbox[3] - actual_bbox[1],
                     actual_visible_width=actual_bbox[2] - actual_bbox[0],
                     bottom_baseline_exclusive=baseline, horizontal_policy=horizontal_policy,
                     height_rule="Original native cell alpha > 0 bounds" if native_reference else "Explicit requested visible height")
    return result, placement


def export_height(input_path: Path, output_path: Path, native_source=None, cell_index=0,
                  source_crop=None, method="nearest", target_height=None,
                  frame_height=None, baseline=None) -> Path:
    input_path, output_path = Path(input_path).expanduser().resolve(), Path(output_path).expanduser().resolve()
    if output_path.suffix.lower() != ".png":
        raise ValueError("Output must have a .png suffix")
    report_path = output_path.with_suffix(".export.json")
    if native_source is not None and target_height is not None:
        raise ValueError("Choose a native reference or an explicit target height, not both")
    if native_source is not None and (frame_height is not None or baseline is not None):
        raise ValueError("Native reference supplies frame height and baseline; do not override them")
    for destination in (output_path, report_path):
        if destination.exists() or destination == input_path:
            raise ValueError(f"Refusing to overwrite existing file: {destination}")
    rgba, source_record = load_transparent_sprite(input_path)
    crop = prepared_crop(rgba, source_record, source_crop)
    native = native_cell_reference(Path(native_source), cell_index) if native_source is not None else None
    height = native["visible_height"] if native else target_height
    image, placement = resize_and_place(crop, height, method, native, frame_height, baseline)
    encoded = io.BytesIO()
    image.save(encoded, format="PNG")
    data = encoded.getvalue()
    alpha = image.getchannel("A")
    report = dict(schema_version=1, created_utc=datetime.now(timezone.utc).isoformat(),
                  status="original_height_export_pending_visual_review", source=source_record,
                  native_reference=native, placement=placement,
                  output=dict(path=str(output_path), sha256=sha256(data), size=list(image.size), mode=image.mode,
                              resample=method, alpha_bbox=list(alpha.getbbox()), alpha_sha256=sha256(alpha.tobytes()),
                              visible_height_matches_reference=placement["actual_visible_height"] == height,
                              zero_rgba_outside_alpha=True, semi_transparent_pixels=sum(alpha.histogram()[1:255])),
                  operations=["Explicit crop if requested and alpha-zero margin trim", "Proportional resize to original visible height",
                              "Place at original bottom baseline; allow canvas width to vary", "Clear hidden RGB where alpha equals zero"],
                  artwork_redrawn=False, creative_filters_applied=False, source_overwritten=False,
                  fixed_square_required=False, three_dimensional_conversion=False, runtime_installed=False,
                  complete_source_sheet=False, drop_in_original_registration_claimed=False,
                  script=dict(path=str(Path(__file__).resolve()), sha256=sha256(Path(__file__).read_bytes())),
                  dependencies={name: sha256((Path(__file__).parent / name).read_bytes())
                                for name in ("export_sprite64.py", "validate_dmi.py")},
                  pillow_version=PIL.__version__,
                  limitations=["Visual identity, anatomy and animation consistency require review",
                               "Matching visible height does not establish equipment overlay alignment or complete atlas compatibility",
                               "Generated sparse edge pixels may need a reviewed crop; no automatic alpha threshold is applied"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("xb") as output:
        output.write(data)
    with report_path.open("x") as output:
        output.write(json.dumps(report, indent=2) + "\n")
    assert sha256(input_path.read_bytes()) == source_record["sha256"]
    return report_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--native-source", type=Path, help="Native DMI containing the original cell")
    source.add_argument("--target-height", type=int, help="Explicit visible sprite height when no native reference is supplied")
    parser.add_argument("--cell-index", type=int, default=0, help="Zero-based native atlas cell; duplicates remain ordered")
    parser.add_argument("--source-crop", type=parse_source_crop)
    parser.add_argument("--filter", choices=("nearest", "lanczos"), default="nearest")
    parser.add_argument("--frame-height", type=int, help="Explicit-height mode only; default equals target height")
    parser.add_argument("--baseline", type=int, help="Explicit-height mode only; bottom-exclusive row, default frame bottom")
    args = parser.parse_args()
    try:
        report = export_height(args.input, args.output, args.native_source, args.cell_index,
                               args.source_crop, args.filter, args.target_height, args.frame_height, args.baseline)
    except (OSError, ValueError, TypeError) as error:
        parser.exit(2, f"Export refused: {error}\n")
    print(json.dumps(dict(report=str(report), status="exported_at_original_visible_height_pending_review"), indent=2))


if __name__ == "__main__":
    main()
