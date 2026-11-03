#!/usr/bin/env python3
"""Native-size standing Human pilot using the existing editable voxel model.

Art changes happen in 3D material illumination before the existing render3
rasterizer runs. No generated art, 2D relighting, resizing of exports, or runtime
asset replacement occurs. The comparison image alone is enlarged for inspection.
"""
from __future__ import annotations

import copy
import argparse
import hashlib
import json
import math
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

STAGING = Path(__file__).resolve().parents[1]


def resolve_project() -> Path:
    """Find the editable project independently of this delivered script's path."""
    override = os.environ.get("BOTD_PROJECT_ROOT")
    manifest = STAGING / "_meta/manifest.json"
    if override:
        candidate = Path(override).expanduser().resolve()
        origin = "BOTD_PROJECT_ROOT"
    else:
        try:
            data = json.loads(manifest.read_text())
            value = data["native_source_repository_root"]
        except (OSError, ValueError, KeyError) as exc:
            raise SystemExit(f"Cannot locate editable BOTD project: {manifest} must contain "
                             "native_source_repository_root, or set BOTD_PROJECT_ROOT "
                             f"to the project directory. Detail: {exc}") from exc
        candidate = Path(value).expanduser().resolve()
        origin = str(manifest)
    required = ("standalone/remastered/art/voxel/inflate2.py",
                "standalone/remastered/art/voxel/render3.py",
                "standalone/remastered/game/Icons/Remastered/Races64/Human.dmi")
    missing = [str(candidate / name) for name in required if not (candidate / name).is_file()]
    if missing:
        raise SystemExit(f"Editable BOTD project from {origin} is incomplete: "
                         + ", ".join(missing)
                         + ". Set BOTD_PROJECT_ROOT to the existing source repository.")
    return candidate


PROJECT = resolve_project()
VOXEL = PROJECT / "standalone/remastered/art/voxel"
OUT = STAGING / "native-3d/pilot"
sys.path.insert(0, str(VOXEL))
import inflate2  # noqa: E402
import render3  # noqa: E402
import landmarks  # noqa: E402

# The legacy module has an absolute workstation path. Override its in-memory
# source location only; the source file and all original artwork stay untouched.
landmarks.R = str(PROJECT / "standalone/remastered/game/Icons/Remastered/Races64") + "/"

YAW = (0, 45, 90, 180)
CAMERA = dict(pitch=37, scale=0.94, size=64, stretch=1.2,
              foot=57 / 64, inner=True, bands=True, shadow=False)
LIGHT = dict(direction=[-0.50, 0.80, -0.40], ambient=0.64,
             diffuse=0.48, offset=0.45, spread=1.30, exponent=0.88)
AO = dict(rad=3, out=4.0, strength=0.65, base=0.12, floor=0.86)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def array_digest(a: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def cache_recipe() -> dict:
    """Content-only inputs: relocating the delivered folder keeps the same key."""
    import PIL
    # build3d9.measure optionally uses the fitted iron helmet to measure the skull.
    helmet = PROJECT / "standalone/remastered/game/Icons/Remastered/Gear64/Human/iron.dmi"
    return dict(
        schema=1, subject="Human", pose="default standing",
        model_call="inflate2.inflate('Human') with repository defaults",
        camera={**CAMERA, "yaw_degrees": list(YAW)}, enhanced_light=LIGHT,
        enhanced_ao=AO, native_frame=[64, 64],
        script_sha256=digest(Path(__file__)),
        voxel_python_sources={str(p.relative_to(VOXEL)): digest(p)
                              for p in sorted(VOXEL.glob("*.py"))},
        human_dmi_sha256=digest(PROJECT / "standalone/remastered/game/Icons/Remastered/Races64/Human.dmi"),
        optional_measurement_helmet_sha256=digest(helmet) if helmet.is_file() else None,
        dependencies={"numpy": np.__version__, "Pillow": PIL.__version__},
        presentation_font_sha256=next((digest(Path(p)) for p in (
            "/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Helvetica.ttc")
            if Path(p).exists()), "Pillow-default"),
    )


def recipe_key(recipe: dict) -> str:
    return hashlib.sha256(json.dumps(recipe, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def cache_is_valid(report: dict, key: str) -> bool:
    """A recipe match is insufficient: verify every expected output's bytes."""
    if report.get("cache", {}).get("recipe_key") != key:
        return False
    expected = {f"native-3d/pilot/Human-yaw-{yaw:03d}-{version}-64.png"
                for yaw in YAW for version in ("baseline", "enhanced")}
    expected.add("native-3d/pilot/Human-comparison-6x-nearest.png")
    try:
        outputs = [frame[version] for frame in report["frames"]
                   for version in ("baseline", "enhanced")] + [report["preview"]]
        if {item["path"] for item in outputs} != expected or len(outputs) != 9:
            return False
        return all((STAGING / item["path"]).is_file()
                   and digest(STAGING / item["path"]) == item["sha256"] for item in outputs)
    except (KeyError, TypeError, OSError):
        return False


def normalized(v: list[float]) -> np.ndarray:
    a = np.array(v, dtype=np.float64)
    return a / np.linalg.norm(a)


def enhanced_materials(model):
    """Replace the shader's diffuse ramp in the 3D material buffer.

    render3's baseline lighting direction/ramp are fixed in its source. Dividing
    the desired scalar irradiance by that ramp lets its unchanged rasterizer
    apply our light instead. The float material buffer is not clipped before
    rendering, avoiding highlight loss from an intermediate 8-bit conversion.
    Face orientation's .96 factor, palette features, outlines, depth ordering,
    geometry, normals, and camera remain identical to the baseline.
    """
    result = copy.copy(model)
    result.col = model.col.astype(np.float64).copy()
    solid = model.solid()
    normals = model.sn[solid].astype(np.float64)
    baseline_dot = np.einsum("ij,j->i", normals,
                             normalized([-0.50, 0.75, -0.45]))
    baseline = 0.70 + 0.36 * np.clip((baseline_dot + 0.45) / 1.30, 0, 1) ** 0.90
    enhanced_dot = np.einsum("ij,j->i", normals, normalized(LIGHT["direction"]))
    enhanced = LIGHT["ambient"] + LIGHT["diffuse"] * np.clip(
        (enhanced_dot + LIGHT["offset"]) / LIGHT["spread"], 0, 1
    ) ** LIGHT["exponent"]
    features = model.lit[solid]
    ratio = np.where(features, 1.0, enhanced / baseline)
    colors = result.col[solid]
    colors[:, :3] *= ratio[:, None]
    result.col[solid] = colors
    result.ao = inflate2.occlusion(solid, model.sn, **AO)
    result.ao[model.lit] = 1.0
    return result, {
        "material_irradiance_ratio_range_nonfeature": [
            float(ratio[~features].min()), float(ratio[~features].max())],
        "ao_range_occupied": [float(result.ao[solid].min()), float(result.ao[solid].max())],
        "ao_affected_voxels": int(np.count_nonzero(result.ao[solid] < 0.999)),
        "feature_materials_exactly_preserved": bool(np.array_equal(
            result.col[model.lit], model.col[model.lit])),
        "feature_ao_exactly_one": bool(np.all(result.ao[model.lit] == 1)),
    }


def frame_info(path: Path) -> dict:
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im)
    return dict(path=str(path.relative_to(STAGING)), sha256=digest(path),
                size=list(im.size), mode=im.mode, alpha_bbox=list(im.getbbox()),
                alpha_sha256=array_digest(a[:, :, 3]),
                opaque_pixels=int(np.count_nonzero(a[:, :, 3])),
                alpha_values=[int(x) for x in np.unique(a[:, :, 3])],
                touches_frame_edge=bool(np.any(a[0, :, 3]) or np.any(a[-1, :, 3])
                                        or np.any(a[:, 0, 3]) or np.any(a[:, -1, 3])))


def validate_projection_math(model) -> dict:
    """Check render3's actual per-face matmul inputs against scalar-axis sums.

    This host's NumPy/BLAS can emit floating-point flags for finite small matrix
    products. Do not assume they are harmless: verify every projected coordinate,
    normal-light product, and depth product for this pilot against einsum.
    """
    solid = model.solid()
    rr, xx, zz = np.nonzero(solid)
    pad = np.pad(solid, 1)
    center = np.array([model.center[0], 0, model.center[1]])
    light = normalized([-0.5, 0.75, -0.45])
    checks, maximum_error, messages = 0, 0.0, set()
    assert np.isfinite(model.sn).all() and np.isfinite(model.col).all()
    for yaw in YAW:
        t, p = math.radians(yaw), math.radians(CAMERA["pitch"])
        right = np.array([math.cos(t), 0, -math.sin(t)])
        facing = np.array([math.sin(t) * math.cos(p), -math.sin(p), math.cos(t) * math.cos(p)])
        up = np.array([math.sin(t) * math.sin(p), math.cos(p), math.cos(t) * math.sin(p)])
        for normal in render3.NORMALS:
            if np.array(normal) @ facing >= 0:
                continue
            dx, dy, dz = normal
            visible = ~pad[rr + 1 - dy, xx + 1 + dx, zz + 1 + dz]
            r, x, z = rr[visible], xx[visible], zz[visible]
            base = np.stack([x, model.n - 1 - r, z], -1).astype(float)
            corners = base[:, None, :] + np.array(render3.CORNERS[normal], float)[None]
            world = (corners - center) / model.sub
            world[..., 1] *= CAMERA["stretch"]
            for values, vector in ((world, right), (world, up), (world.mean(1), facing),
                                   (model.sn[r, x, z], light), (model.sn[r, x, z], facing)):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always", RuntimeWarning)
                    actual = values @ vector
                messages.update(str(w.message) for w in caught)
                expected = np.einsum("...j,j->...", values, vector)
                assert np.isfinite(actual).all() and np.isfinite(expected).all()
                assert np.allclose(actual, expected, atol=1e-10, rtol=1e-12)
                maximum_error = max(maximum_error, float(np.abs(actual - expected).max()))
                checks += 1
    return dict(all_products_finite=True, scalar_axis_reference_agrees=True,
                matrix_products_checked=checks, maximum_absolute_difference=maximum_error,
                inherited_host_matmul_warning_messages=sorted(messages))


def font(size: int):
    for candidate in ("/System/Library/Fonts/Supplemental/Arial.ttf",
                      "/System/Library/Fonts/Helvetica.ttc"):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def comparison(frames: dict) -> Path:
    """Presentation-only nearest-neighbor enlargement of exact native exports."""
    zoom, tile, left, top, rowgap = 6, 384, 24, 112, 65
    canvas = Image.new("RGB", (1584, 1010), (37, 41, 49))
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 17), "HUMAN • native voxel standing-pose pilot", font=font(28), fill=(244, 245, 249))
    draw.text((24, 57), "Exports: 64 × 64 RGBA | Preview: 6× NEAREST-NEIGHBOR | Same geometry, camera and alpha", font=font(20), fill=(199, 206, 218))
    for row, version in enumerate(("baseline", "enhanced")):
        y = top + row * (tile + rowgap)
        label = "BASELINE • existing voxel render" if row == 0 else "ENHANCED • broader key light + restrained crease AO"
        draw.text((24, y - 29), label, font=font(20), fill=(244, 245, 249))
        for col, yaw in enumerate(YAW):
            x = left + col * (tile + 8)
            for cy in range(0, tile, 24):
                for cx in range(0, tile, 24):
                    color = (48, 53, 62) if (cy // 24 + cx // 24) % 2 else (43, 48, 56)
                    draw.rectangle((x + cx, y + cy, x + cx + 23, y + cy + 23), fill=color)
            native = Image.open(frames[version][yaw]).convert("RGBA")
            enlarged = native.resize((64 * zoom, 64 * zoom), Image.Resampling.NEAREST)
            canvas.paste(enlarged, (x, y), enlarged)
            draw.text((x, y + tile + 6), f"yaw {yaw}° · pitch 37°", font=font(18), fill=(199, 206, 218))
    draw.text((24, 981), "Reference pilot only: one standing pose, four angles. No game atlas or runtime files replaced.", font=font(17), fill=(199, 206, 218))
    path = OUT / "Human-comparison-6x-nearest.png"
    canvas.save(path)
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-key-only", action="store_true",
                        help="Print the current content key without writing or rendering")
    args = parser.parse_args()
    recipe = cache_recipe()
    key = recipe_key(recipe)
    if args.cache_key_only:
        print(json.dumps(dict(recipe_key=key, project=str(PROJECT)), indent=2))
        return
    report_path = OUT / "pilot-report.json"
    try:
        previous = json.loads(report_path.read_text())
    except (OSError, ValueError):
        previous = {}
    if cache_is_valid(previous, key):
        print(json.dumps(dict(status="cache_hit", recipe_key=key, native_frames=8,
                              reason="Complete recipe/source hashes and all nine generated output hashes match",
                              report=str(report_path), renders_performed=0), indent=2))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    baseline, _ = inflate2.inflate("Human")
    enhanced, material_stats = enhanced_materials(baseline)
    # Shader-only pilot: every geometric/feature input must remain byte-identical.
    for attr in ("owner", "part", "sn", "lit"):
        assert np.array_equal(getattr(baseline, attr), getattr(enhanced, attr)), attr
    assert baseline.center == enhanced.center
    assert baseline.n == enhanced.n and baseline.sub == enhanced.sub
    numeric_validation = validate_projection_math(baseline)
    assert np.isfinite(enhanced.col).all() and np.isfinite(enhanced.ao).all()
    frames = {"baseline": {}, "enhanced": {}}
    results = []
    render_warnings = set()
    for yaw in YAW:
        pair = {}
        for version, model in (("baseline", baseline), ("enhanced", enhanced)):
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", RuntimeWarning)
                rendered = render3.render(model, yaw=yaw, **CAMERA)
            render_warnings.update(str(w.message) for w in caught)
            assert rendered.size == (64, 64) and rendered.mode == "RGBA"
            path = OUT / f"Human-yaw-{yaw:03d}-{version}-64.png"
            rendered.save(path)
            frames[version][yaw] = path
            pair[version] = frame_info(path)
        a = np.asarray(Image.open(frames["baseline"][yaw]))
        b = np.asarray(Image.open(frames["enhanced"][yaw]))
        assert np.array_equal(a[:, :, 3], b[:, :, 3]), f"alpha mismatch at yaw {yaw}"
        assert not pair["baseline"]["touches_frame_edge"], f"clipping risk at yaw {yaw}"
        visible = a[:, :, 3] > 0
        delta = b[:, :, :3].astype(int) - a[:, :, :3].astype(int)
        pair.update(yaw=yaw, alpha_exact_match=True,
                    changed_visible_rgb_pixels=int(np.count_nonzero(np.any(delta != 0, axis=2) & visible)),
                    mean_absolute_rgb_delta_visible=float(np.abs(delta[visible]).mean()),
                    mean_rgb_delta_visible=float(delta[visible].mean()))
        results.append(pair)
    preview = comparison(frames)
    sources = [VOXEL / name for name in (
        "inflate2.py", "render3.py", "anglesheet.py", "refsheet.py", "build3d9.py", "landmarks.py")]
    sources.extend([
        PROJECT / "standalone/remastered/game/Icons/Remastered/Races64/Human.dmi",
        PROJECT / "standalone/remastered/art/ref/Human-34.png",
    ])
    report = dict(
        status="native_size_standing_pose_pilot_pending_visual_review",
        created_utc=datetime.now(timezone.utc).isoformat(),
        scope="Human standing pose only at four yaw angles; not a complete game atlas",
        runtime_ready=False, installed_in_game=False, source_assets_modified=False,
        method="Existing inflate2 3D voxel geometry; per-voxel normal illumination and geometry-derived ambient occlusion before unchanged render3 rasterization",
        prohibited_shortcuts_used={"ai_reference_downscale": False, "2d_relighting": False,
                                  "pasted_bitmap_replacement": False, "paid_api": False},
        native_exports=dict(frame_size=[64, 64], mode="RGBA", direct_native_rasterization=True,
                            supersampling=False, palette_lock=False),
        camera={**CAMERA, "yaw_degrees": list(YAW), "fixed_horizontal_center_px": 32,
                "fixed_ground_anchor_px": 57, "model_rotation_center_voxels": list(baseline.center),
                "framing_note": "One shared projection for every frame. Alpha bounding boxes can differ by yaw because the same 3D volume rotates. No per-frame crop, translation, fit, or resize."},
        baseline=dict(model="inflate2.inflate('Human') defaults, sub=2, style=grey, bright=1.06, normal_sigma=2.8",
                      lighting=dict(direction=[-0.5, 0.75, -0.45], ambient=0.70,
                                    diffuse=0.36, offset=0.45, spread=1.3, exponent=0.90),
                      ao=None),
        enhanced=dict(lighting=LIGHT, ambient_occlusion=AO,
                      feature_rule="Model lit mask retains original eye/mouth/painted-feature colors and AO=1",
                      material_implementation="Float RGB voxel material multiplied by desired/baseline irradiance before render3. No clipping until render3 final face shading.",
                      **material_stats),
        geometry=dict(grid_shape=list(baseline.owner.shape), sub=baseline.sub,
                      occupied_voxels=int(baseline.solid().sum()),
                      owner_sha256=array_digest(baseline.owner), normals_sha256=array_digest(baseline.sn),
                      feature_mask_sha256=array_digest(baseline.lit),
                      owner_part_normals_features_center_identical=True),
        validation=dict(all_native_frames_64x64_rgba=True,
                        all_baseline_enhanced_alpha_masks_exactly_equal=True,
                        no_frame_edge_contact=True, geometry_preserved=True,
                        visual_review="pending; inspect exact native files and nearest-neighbor preview",
                        flat_2d_dmi_alpha_or_registration_match_claimed=False,
                        full_animation_or_equipment_alignment_claimed=False),
        numerical_validation={**numeric_validation,
                              "render_warning_messages": sorted(render_warnings),
                              "handling": "Warnings recorded; corresponding existing-renderer products independently checked for finite values and agreement with einsum. No source renderer changes."},
        frames=results,
        preview=dict(path=str(preview.relative_to(STAGING)), sha256=digest(preview),
                     size=list(Image.open(preview).size), interpolation="nearest", enlargement=6,
                     presentation_only=True),
        script=dict(path=str(Path(__file__).relative_to(STAGING)), sha256=digest(Path(__file__))),
        cache=dict(recipe_key=key, recipe=recipe,
                   policy="Skip rendering only when recipe and all eight native frame plus preview hashes match",
                   cache_state_at_creation="rebuilt"),
        source_project_resolution=dict(project_root=str(PROJECT),
                                       manifest=str(STAGING / "_meta/manifest.json"),
                                       environment_override=bool(os.environ.get("BOTD_PROJECT_ROOT"))),
        source_provenance=[dict(path=str(p), sha256=digest(p)) for p in sources],
        remaining_work=["Independent visual review of native-size result", "Calibrate additional race/material families before bulk processing",
                        "Full native animation/state/direction and equipment alignment work"],
        user_feedback="Optional; broader work already authorized. No additional approval gate is imposed.",
    )
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(report=str(report_path), preview=str(preview),
                          geometry=report["geometry"], material_stats=material_stats,
                          frames=[dict(yaw=f["yaw"], bbox=f["baseline"]["alpha_bbox"],
                                       changed_pixels=f["changed_visible_rgb_pixels"]) for f in results]), indent=2))


if __name__ == "__main__":
    main()
