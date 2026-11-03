"""Preservation checks using tiny in-memory PNG/DMI fixtures, not game artwork."""

import io
import unittest
from unittest.mock import patch

from PIL import Image, PngImagePlugin

from validate_dmi import compare_assets, load_asset, parse_description, validate_paths


HEADER = "# BEGIN DMI\nversion = 4.0\n\twidth = 2\n\theight = 2\n"
FIRST = 'state = "walk"\n\tdirs = 1\n\tframes = 1\n'
SECOND = 'state = "walk"\n\tdirs = 1\n\tframes = 1\n\tmovement = 1\n'
TAIL = "# END DMI\n"
DESCRIPTION = HEADER + FIRST + SECOND + TAIL


def fixture_bytes(description=DESCRIPTION, changes=None, size=(4, 2)):
    image = Image.new("RGBA", size, (0, 0, 0, 0))
    image.putpixel((0, 0), (20, 40, 60, 255))
    image.putpixel((2, 0), (40, 60, 80, 128))
    for coordinate, value in (changes or {}).items():
        image.putpixel(coordinate, value)
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Description", description, zip=True)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", pnginfo=metadata)
    return buffer.getvalue()


def fixture(description=DESCRIPTION, changes=None, size=(4, 2)):
    return load_asset(fixture_bytes(description, changes, size))


class DmiValidationTests(unittest.TestCase):
    def setUp(self):
        self.source = fixture()

    def test_duplicate_names_are_ordered_occurrences(self):
        parsed = parse_description(DESCRIPTION)
        self.assertEqual(len(parsed.states), 2)
        self.assertEqual([state.name for state in parsed.states], ['"walk"', '"walk"'])
        self.assertEqual([state.start_cell for state in parsed.states], [0, 1])
        report = compare_assets(self.source, fixture())
        self.assertTrue(report["passed"])
        self.assertEqual(report["source"]["metadata"]["duplicate_state_names"], {'"walk"': 2})
        self.assertEqual(len(report["frames"]), 2)

    def test_dropped_duplicate_state_fails(self):
        report = compare_assets(self.source, fixture(HEADER + FIRST + TAIL))
        self.assertFalse(report["passed"])
        self.assertIn("Ordered states or their metadata differ", report["failures"])

    def test_reordered_duplicate_states_fail(self):
        report = compare_assets(self.source, fixture(HEADER + SECOND + FIRST + TAIL))
        self.assertFalse(report["passed"])
        self.assertIn("Ordered states or their metadata differ", report["failures"])

    def test_alpha_drift_with_same_occupancy_fails(self):
        report = compare_assets(self.source, fixture(changes={(2, 0): (40, 60, 80, 127)}))
        self.assertFalse(report["passed"])
        self.assertEqual(report["pixels"]["alpha_changed"], 1)
        self.assertEqual(report["frames"][1]["alpha_changed"], 1)

    def test_shifted_occupied_coordinate_fails(self):
        report = compare_assets(self.source, fixture(changes={
            (0, 0): (0, 0, 0, 0), (1, 0): (20, 40, 60, 255)}))
        self.assertFalse(report["passed"])
        self.assertEqual(report["pixels"]["alpha_changed"], 2)

    def test_unchanged_source_rejected_when_enhancement_required(self):
        report = compare_assets(self.source, fixture(), require_enhanced=True)
        self.assertFalse(report["passed"])
        self.assertIn("No visible RGB changes; candidate is not an enhanced asset", report["failures"])

    def test_visible_rgb_change_passes_without_claiming_quality(self):
        report = compare_assets(self.source, fixture(changes={(0, 0): (21, 42, 63, 255)}),
                                require_enhanced=True)
        self.assertTrue(report["passed"])
        self.assertEqual(report["pixels"]["visible_rgb_changed"], 1)
        self.assertEqual(report["pixels"]["alpha_changed"], 0)
        self.assertEqual(report["frames"][0]["visible_rgb_changed"], 1)
        self.assertIn("artistic improvement", report["limitations"][0])

    def test_transparent_rgb_changes_are_strict_by_default(self):
        candidate = fixture(changes={(1, 1): (80, 0, 0, 0)})
        strict = compare_assets(self.source, candidate)
        permissive = compare_assets(self.source, candidate, allow_transparent_rgb_changes=True)
        still_unchanged = compare_assets(self.source, candidate,
                                        allow_transparent_rgb_changes=True, require_enhanced=True)
        self.assertFalse(strict["passed"])
        self.assertTrue(permissive["passed"])
        self.assertFalse(still_unchanged["passed"])
        self.assertEqual(strict["pixels"]["transparent_rgb_changed"], 1)

    def test_all_metadata_fields_and_unknown_fields_are_preserved(self):
        for field in ("delay = 2", "movement = 1", "loop = 0", "rewind = 1",
                      "hotspot = 1,1,1", "future_field = anything"):
            with self.subTest(field=field):
                candidate = fixture(HEADER + FIRST + "\t" + field + "\n" + SECOND + TAIL)
                report = compare_assets(self.source, candidate)
                self.assertFalse(report["passed"])
                self.assertIn("Description metadata text differs", report["failures"])

    def test_dimensions_and_frames_cannot_silently_change(self):
        report = compare_assets(self.source, fixture(size=(6, 2)))
        self.assertFalse(report["passed"])
        self.assertIn("Image dimensions differ", report["failures"])
        with self.assertRaisesRegex(ValueError, "more frames"):
            fixture(DESCRIPTION.replace("frames = 1", "frames = 4"))

    def test_exact_description_includes_whitespace(self):
        report = compare_assets(self.source, fixture(DESCRIPTION.replace("\twidth", "  width")))
        self.assertFalse(report["passed"])
        self.assertNotIn("Ordered states or their metadata differ", report["failures"])
        self.assertIn("Description metadata text differs", report["failures"])

    def test_missing_invalid_or_duplicate_versions_fail(self):
        for version_line in ("", "version = bananas\n", "version = 5.0\n",
                             "version = 4.0\nversion = 4.0\n"):
            with self.subTest(version=version_line):
                with self.assertRaises(ValueError):
                    fixture(DESCRIPTION.replace("version = 4.0\n", version_line))
        self.assertEqual(parse_description(DESCRIPTION.replace("version = 4.0", "version = 3.0")).width, 2)

    def test_invalid_directions_fail_before_self_comparison(self):
        for directions in ("0", "3", "-1", "1.5", "bananas"):
            with self.subTest(directions=directions):
                with self.assertRaises(ValueError):
                    fixture(DESCRIPTION.replace("dirs = 1", "dirs = " + directions))

    def test_malformed_or_nonstring_state_names_fail(self):
        for name in ('"walk""', '"bad\\q"', '"unclosed', "42", "null", '["walk"]'):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    fixture(DESCRIPTION.replace('state = "walk"', "state = " + name, 1))

    def test_duplicate_header_and_nonhotspot_state_fields_fail(self):
        for description in (
            DESCRIPTION.replace("\twidth = 2", "\twidth = 2\n\twidth = 2"),
            DESCRIPTION.replace("\tdirs = 1", "\tdirs = 1\n\tdirs = 1", 1),
            HEADER + FIRST + "\tloop = 0\n\tloop = 0\n" + SECOND + TAIL,
        ):
            with self.subTest(description=description):
                with self.assertRaises(ValueError):
                    fixture(description)

    def test_invalid_delay_counts_and_values_fail(self):
        for delay in ("0", "-1", "NaN", "inf", "1,", "", "bananas"):
            with self.subTest(delay=delay):
                with self.assertRaises(ValueError):
                    fixture(HEADER + FIRST + "\tdelay = " + delay + "\n" + SECOND + TAIL)
        with self.assertRaisesRegex(ValueError, "delay count"):
            fixture(HEADER + FIRST.replace("frames = 1", "frames = 2") + "\tdelay = 1\n" + TAIL)

    def test_invalid_movement_rewind_loop_fail(self):
        for field in ("movement = 2", "movement = -1", "rewind = 2", "rewind = 0.5",
                      "loop = -1", "loop = bananas"):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    fixture(HEADER + FIRST + "\t" + field + "\n" + SECOND + TAIL)

    def test_invalid_hotspots_fail(self):
        for hotspot in ("1,1", "1,1,1,1", "1,1,0", "1,1,2", "1.5,1,1", "a,1,1"):
            with self.subTest(hotspot=hotspot):
                with self.assertRaises(ValueError):
                    fixture(HEADER + FIRST + "\thotspot = " + hotspot + "\n" + SECOND + TAIL)

    def test_extra_delays_and_repeated_hotspots_are_preserved(self):
        description = (HEADER + FIRST + "\tdelay = 1,2,3\n"
                       + "\thotspot = 1,1,1\n\thotspot = -2,20,1\n" + SECOND + TAIL)
        asset = fixture(description)
        report = compare_assets(asset, fixture(description))
        self.assertTrue(report["passed"])
        self.assertTrue(any("3 delays for 1 frames" in message for message in report["warnings"]))
        self.assertEqual([pair for pair in asset.metadata.states[0].fields if pair[0] == "hotspot"],
                         [("hotspot", "1,1,1"), ("hotspot", "-2,20,1")])

    def test_same_alpha_rgb_swap_is_an_explicit_limit(self):
        source = fixture(changes={(2, 0): (40, 60, 80, 255)})
        swapped = fixture(changes={(0, 0): (40, 60, 80, 255), (2, 0): (20, 40, 60, 255)})
        report = compare_assets(source, swapped, require_enhanced=True)
        self.assertTrue(report["passed"])
        self.assertEqual(report["pixels"]["alpha_changed"], 0)
        self.assertEqual(report["pixels"]["visible_rgb_changed"], 2)
        self.assertTrue(any("sprite identity is not verified" in message for message in report["limitations"]))

    def test_corrupt_idat_crc_is_rejected_and_reported(self):
        data = bytearray(fixture_bytes())
        position = 8  # PNG signature precedes the chunk sequence.
        while position < len(data):
            length = int.from_bytes(data[position:position + 4], "big")
            if data[position + 4:position + 8] == b"IDAT":
                data[position + 8 + length] ^= 1
                break
            position += 12 + length
        else:
            self.fail("Fixture did not contain IDAT")
        with self.assertRaises(SyntaxError):
            load_asset(bytes(data))
        with patch("pathlib.Path.read_bytes", return_value=bytes(data)):
            report = validate_paths("source.dmi", "candidate.dmi")
        self.assertFalse(report["passed"])
        self.assertIn("bad header checksum", report["failures"][0])

    def test_animated_png_is_rejected(self):
        buffer = io.BytesIO()
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("Description", DESCRIPTION)
        first = Image.new("RGBA", (4, 2), (20, 40, 60, 255))
        second = Image.new("RGBA", (4, 2), (80, 100, 120, 255))
        first.save(buffer, format="PNG", pnginfo=metadata, save_all=True, append_images=[second])
        with self.assertRaisesRegex(ValueError, "Animated PNG"):
            load_asset(buffer.getvalue())

    def test_multidirection_multiframe_cells_wrap_rows_and_keep_state_occurrences(self):
        first = FIRST.replace("dirs = 1", "dirs = 4").replace("frames = 1", "frames = 2")
        description = HEADER + first + "\tdelay = 1,2\n" + SECOND + TAIL
        source = fixture(description, changes={(0, 2): (30, 40, 50, 255),
                                               (4, 4): (60, 70, 80, 255)}, size=(6, 6))
        candidate = fixture(description, changes={(0, 2): (31, 40, 50, 255),
                                                  (4, 4): (61, 70, 80, 255)}, size=(6, 6))
        report = compare_assets(source, candidate, require_enhanced=True)
        self.assertTrue(report["passed"])
        self.assertEqual(len(report["frames"]), 9)
        self.assertEqual([frame["box"] for frame in report["frames"]],
                         [[x, y, x + 2, y + 2] for y in (0, 2, 4) for x in (0, 2, 4)])
        self.assertEqual([frame["state_index"] for frame in report["frames"]], [0] * 8 + [1])
        self.assertEqual([frame["state_cell_offset"] for frame in report["frames"]], list(range(8)) + [0])
        self.assertEqual([frame["sheet_cell_index"] for frame in report["frames"]], list(range(9)))
        self.assertEqual([frame["visible_rgb_changed"] for frame in report["frames"]],
                         [0, 0, 0, 1, 0, 0, 0, 0, 1])


if __name__ == "__main__":
    unittest.main()
