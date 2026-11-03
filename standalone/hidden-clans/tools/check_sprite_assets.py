#!/usr/bin/env python3
"""Exercise sprite metadata, exact pixels, paging, quarantine and determinism."""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image, PngImagePlugin

SPEC = importlib.util.spec_from_file_location("sprite_export", Path(__file__).with_name("export_sprite_assets.py"))
pipeline = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pipeline)


def dmi(path, cell=(7, 5), count=8, metadata=None, columns=3):
    image = Image.new("RGBA", (cell[0] * columns, cell[1] * ((count + columns - 1) // columns)))
    for i in range(count):
        for y in range(cell[1]):
            for x in range(cell[0]):
                image.putpixel((i % columns * cell[0] + x, i // columns * cell[1] + y),
                               ((i * 41 + x) % 256, y * 7, 29, (0, 73, 255)[(x + y) % 3]))
    description = '# BEGIN DMI\nversion = 4.0\nwidth = %s\nheight = %s\n' % cell
    description += metadata or 'state = ""\ndirs = 1\nframes = %s\n' % count
    description += '# END DMI\n'
    info = PngImagePlugin.PngInfo()
    info.add_text("Description", description, zip=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", pnginfo=info)
    return image


def hashes(root):
    return {p.relative_to(root).as_posix(): pipeline.digest(p.read_bytes())
            for p in root.rglob("*") if p.is_file()}


class SpriteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "game"
        self.root.mkdir()
        self.output = self.base / "sprites"
        self.dme = self.root / "test.dme"
        self.dme.write_text('#include "main.dm"\n')
        (self.root / "main.dm").write_text("// no static resources\n")

    def tearDown(self):
        self.tmp.cleanup()

    def export(self, page_size=32, gutter=1):
        return pipeline.export(self.root, self.output, self.dme, page_size, gutter)

    def test_animation_directions_hotspots_alpha_and_native_size(self):
        metadata = 'state = "walk"\ndirs = 8\nframes = 3\ndelay = 0.5,2,3\nmovement = 1\nrewind = 1\nloop = 2\nhotspot = 2,3,24\n'
        original = dmi(self.root / "Icons" / "Odd.dmi", count=24, metadata=metadata)
        m, v = self.export()
        a, = m["assets"]
        s, = a["states"]
        self.assertEqual(a["native_size"], [7, 5])
        self.assertEqual(s["delay_deciseconds"], [0.5, 2, 3])
        self.assertEqual((s["rewind"], s["loop"], s["movement"]), (1, 2, 1))
        self.assertEqual(s["hotspots"], [{"x": 2, "y": 3, "cell_1based": 24}])
        self.assertEqual([c["direction"] for c in s["cells"][:8]], pipeline.DIRECTIONS)
        self.assertEqual([c["frame"] for c in s["cells"]], [0] * 8 + [1] * 8 + [2] * 8)
        self.assertEqual(a["sheet_rgba_sha256"], pipeline.digest(original.tobytes()))
        self.assertTrue(v["passed"])
        self.assertEqual(v["cells_compared"], 24)
        self.assertGreater(v["pages_checked"], 1)

    def test_page_exact_fill_and_one_extra_frame(self):
        dmi(self.root / "Fill.dmi", cell=(4, 4), count=4, columns=4)
        m, _ = self.export(page_size=8, gutter=0)
        self.assertEqual(len(m["pages"]), 1)
        dmi(self.root / "Fill.dmi", cell=(4, 4), count=5, columns=5)
        m, _ = self.export(page_size=8, gutter=0)
        self.assertEqual(len(m["pages"]), 2)
        self.assertEqual(m["assets"][0]["states"][0]["cells"][-1]["rect"], [0, 0, 4, 4])

    def test_duplicate_states_movement_variants_extra_delays_and_unassigned_art(self):
        metadata = ('state = "same"\ndirs = 1\nframes = 1\ndelay = 2,3\n'
                    'state = "same"\nmovement = 1\n'
                    'state = "same"\n')
        dmi(self.root / "Dup.dmi", count=4, columns=4, metadata=metadata)
        m, v = self.export()
        a, = m["assets"]
        self.assertEqual(len(a["states"]), 3)
        self.assertEqual(len({s["id"] for s in a["states"]}), 3)
        self.assertEqual([s["occurrence"] for s in a["states"]], [0, 0, 1])
        self.assertEqual(a["states"][0]["delay_deciseconds"], [2, 3])
        self.assertEqual(a["states"][0]["playback_delay_deciseconds"], [2])
        self.assertEqual(len(a["extra_cells"]), 1)
        self.assertTrue(a["extra_cells"][0]["visible"])
        self.assertEqual({i["code"] for i in m["issues"]}, {"duplicate_state", "extra_delays", "unassigned_visible_cells"})
        self.assertEqual(v["cells_compared"], 4)

    def test_references_nested_assets_case_dynamic_names_and_excluded_copies(self):
        (self.root / "test.dme").write_text('#define FILE_DIR "Nested/Icons"\n#include "Code/logic.dm"\n')
        (self.root / "Code").mkdir()
        (self.root / "Code/logic.dm").write_text("// 'not-real.dmi'\nvar/icon = 'odd.dmi'\nvar/x = \"unit-[id].png\"\n")
        dmi(self.root / "Nested/Icons/Odd.dmi")
        dmi(self.root / "backup/Copy.dmi")
        m, _ = self.export()
        self.assertEqual(len(m["assets"]), 1)
        self.assertEqual(m["assets"][0]["references"][0]["line"], 2)
        self.assertEqual(m["assets"][0]["source"], "Nested/Icons/Odd.dmi")
        self.assertEqual(m["summary"]["errors"], 0)
        self.assertEqual({i["code"] for i in m["issues"]}, {"resource_case_mismatch", "dynamic_image_name"})

    def test_quarantines_empty_and_invalid_referenced_assets_without_hiding_them(self):
        (self.root / "Empty.dmi").write_bytes(b"")
        dmi(self.root / "Bad.dmi", metadata='state = "bad"\nframes = 8\ndelay = 2\n')
        (self.root / "main.dm").write_text("var/icon = 'Bad.dmi'\n")
        m, v = self.export()
        self.assertEqual(m["summary"]["quarantined_files"], 2)
        self.assertEqual(m["summary"]["errors"], 1)
        self.assertEqual(m["summary"]["warnings"], 1)
        self.assertEqual(len(m["assets"]), 2)
        self.assertEqual(v["cells_compared"], 0)

    def test_missing_includes_and_resources_are_errors(self):
        (self.root / "main.dm").write_text('#include "Missing.dm"\nvar/i = \'Missing.dmi\'\n')
        m, _ = self.export()
        self.assertEqual(m["summary"]["errors"], 2)

    def test_plain_png_and_animated_gif_compositing(self):
        Image.new("RGBA", (9, 13), (47, 98, 114, 0)).save(self.root / "Single.png")
        first, second = Image.new("RGBA", (5, 6), "red"), Image.new("RGBA", (5, 6), "blue")
        first.save(self.root / "Disguised.dmi", format="GIF", save_all=True, append_images=[second],
                   duration=[100, 250], loop=2)
        m, v = self.export()
        a = next(a for a in m["assets"] if a["encoding"] == "gif")
        self.assertEqual(a["states"][0]["delay_deciseconds"], [1, 2.5])
        self.assertEqual(a["gif"]["loop"], 2)
        self.assertEqual(v["gif_frames_compared"], 2)
        self.assertEqual(v["sheets_reconstructed"], 1)

    def test_repeat_is_byte_identical_and_source_untouched(self):
        dmi(self.root / "Repeat.dmi")
        (self.root / "LICENSE").write_bytes(b"Example provenance\xff\n")
        before = hashes(self.root)
        self.export()
        first = hashes(self.output)
        self.export()
        self.assertEqual(first, hashes(self.output))
        self.assertEqual(before, hashes(self.root))
        self.assertEqual((self.output / "notices/LICENSE").read_bytes(), b"Example provenance\xff\n")

    def test_unknown_metadata_retained_but_invalid_directions_rejected(self):
        dmi(self.root / "Unknown.dmi", metadata='state = "odd"\nframes = 8\ncustom_future = 9\n')
        dmi(self.root / "Invalid.dmi", metadata='state = "invalid"\ndirs = 3\nframes = 1\n')
        m, _ = self.export()
        self.assertEqual(m["summary"]["exported_files"], 1)
        a = next(a for a in m["assets"] if a["status"] == "exported")
        self.assertIn({"key": "custom_future", "value": "9"}, a["states"][0]["metadata"])
        self.assertIn("unsupported_metadata", {i["code"] for i in m["issues"]})

    def test_refuses_unsafe_output_and_detects_atlas_corruption(self):
        dmi(self.root / "Safe.dmi")
        with self.assertRaises(ValueError):
            pipeline.export(self.root, self.root / "new", self.dme)
        self.output.mkdir()
        (self.output / "user-file.txt").write_text("keep")
        with self.assertRaises(ValueError):
            self.export()
        self.assertEqual((self.output / "user-file.txt").read_text(), "keep")
        (self.output / "user-file.txt").unlink()
        m, _ = self.export()
        page = self.output / m["pages"][0]["file"]
        page.write_bytes(b"corrupt")
        with self.assertRaises(ValueError):
            pipeline.verify(self.root, self.output, m)


def full_check():
    root = pipeline.BASE / "game"
    dme_path = root / "Cave Crawlers.dme"
    before = {p.relative_to(root).as_posix(): pipeline.digest(p.read_bytes()) for p in root.rglob("*")
              if p.is_file() and p.suffix.lower() in (".dmi", ".png")}
    with tempfile.TemporaryDirectory(prefix="sprite-full-check-") as temp:
        output = Path(temp) / "sprites"
        m, v = pipeline.export(root, output, dme_path)
        first = hashes(output)
        pipeline.export(root, output, dme_path)
        if hashes(output) != first:
            raise AssertionError("Full export is not byte deterministic")
    after = {p.relative_to(root).as_posix(): pipeline.digest(p.read_bytes()) for p in root.rglob("*")
             if p.is_file() and p.suffix.lower() in (".dmi", ".png")}
    if before != after:
        raise AssertionError("Original sprite files changed")
    if m["summary"]["errors"]:
        raise AssertionError("Full export has blocking issues; inspect manifest")
    report = dict(passed=True, deterministic_repeat=True, original_sprites_unchanged=True,
                  summary=m["summary"], roundtrip=v)
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true", help="Also export actual game assets twice and compare every output byte")
    parser.add_argument("--report", type=Path, help="Save test evidence as JSON")
    args = parser.parse_args()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SpriteTests))
    if not result.wasSuccessful():
        raise SystemExit(1)
    report = {"passed": True, "focused_tests": result.testsRun,
              "test_script_sha256": pipeline.digest(Path(__file__).read_bytes()),
              "exporter_sha256": pipeline.digest(Path(pipeline.__file__).read_bytes())}
    if args.full:
        report["full_export"] = full_check()
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        pipeline.write_json(args.report, report)
