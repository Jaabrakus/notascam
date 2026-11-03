#!/usr/bin/env python3
"""Validate the atlas consumer and its failure cases without changing game art."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('border_icons', Path(__file__).with_name('export_border_icons.py'))
consumer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(consumer)
ATLAS_SPEC = importlib.util.spec_from_file_location('sprite_atlas', Path(__file__).with_name('export_sprite_assets.py'))
atlas = importlib.util.module_from_spec(ATLAS_SPEC)
ATLAS_SPEC.loader.exec_module(atlas)
BASE = consumer.BASE


class BorderIconsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='dm-border-icons-test-')
        self.root = Path(self.tmp.name)
        self.config = self.root / 'controls.json'
        self.config.write_text(json.dumps([dict(id='stop', source='Icons/HUD.dmi', icon_state='Stop')]))
        self.manifest = BASE / 'assets/sprites/manifest.json'
        self.source = BASE / 'game'
        self.output = self.root / 'output'
        self.report = self.root / 'report.json'

    def tearDown(self):
        self.tmp.cleanup()

    def export(self):
        return consumer.export(self.config, self.manifest, self.source, self.output, self.report)

    def test_original_pixels_and_variants_repeat_exactly(self):
        report = self.export()
        self.assertEqual(report['images'], 3)
        self.assertEqual({r['id'] for r in report['outputs']}, {'stop', 'daynight-sun', 'daynight-moon'})
        self.assertTrue(all(r['native_size'] == [32, 32] and r['matches_original'] for r in report['outputs']))
        first = {p.name: consumer.sha(p.read_bytes()) for p in self.output.iterdir()}
        report_before = self.report.read_bytes()
        self.export()
        self.assertEqual(first, {p.name: consumer.sha(p.read_bytes()) for p in self.output.iterdir()})
        self.assertEqual(report_before, self.report.read_bytes())

    def test_ambiguous_and_missing_states_are_rejected(self):
        manifest = consumer.read_json(self.manifest)
        row = dict(id='stop', source='Icons/HUD.dmi', icon_state='Stop')
        asset = next(a for a in manifest['assets'] if a['source'] == 'Icons/HUD.dmi')
        state = copy.deepcopy(next(s for s in asset['states'] if s['name'] == 'Stop'))
        state['occurrence'] = 1
        asset['states'].append(state)
        with self.assertRaisesRegex(ValueError, 'ambiguous state'):
            consumer.resolve(manifest, row)
        with self.assertRaisesRegex(ValueError, 'ambiguous state'):
            consumer.resolve(manifest, {**row, 'icon_state': 'does-not-exist'})

    def test_safe_unique_ids_and_original_source_hash(self):
        for rows in ([dict(id='../escape', source='Icons/HUD.dmi', icon_state='Stop')],
                     [dict(id='same', source='Icons/HUD.dmi', icon_state='Stop')] * 2):
            self.config.write_text(json.dumps(rows))
            with self.assertRaises(ValueError): self.export()
        manifest = consumer.read_json(self.manifest)
        next(a for a in manifest['assets'] if a['source'] == 'Icons/HUD.dmi')['source_sha256'] = '0' * 64
        self.config.write_text(json.dumps([dict(id='stop', source='Icons/HUD.dmi', icon_state='Stop')]))
        # Keep atlas-relative paths valid while replacing only parsed metadata.
        old_reader = consumer.read_json
        consumer.read_json = lambda p: manifest if p == self.manifest else old_reader(p)
        try:
            with self.assertRaisesRegex(ValueError, 'Atlas is stale'): self.export()
        finally:
            consumer.read_json = old_reader

    def test_wrong_atlas_crop_is_caught_by_independent_original_comparison(self):
        manifest = consumer.read_json(self.manifest)
        asset = next(a for a in manifest['assets'] if a['source'] == 'Icons/HUD.dmi')
        stop = next(s for s in asset['states'] if s['name'] == 'Stop')
        moon = next(s for s in asset['states'] if s['name'] == 'Moon')
        stop['cells'] = copy.deepcopy(moon['cells'])
        old_reader = consumer.read_json
        consumer.read_json = lambda p: manifest if p == self.manifest else old_reader(p)
        try:
            with self.assertRaisesRegex(ValueError, 'differs from original DMI'): self.export()
        finally:
            consumer.read_json = old_reader

    def test_generated_pngs_never_reenter_original_atlas(self):
        source = self.root / 'discovery-source'
        (source / 'Interface/border-icons').mkdir(parents=True)
        (source / 'entry.dme').write_text('// fixture\n')
        # The contents need not be a valid PNG: discovery must exclude it first.
        (source / 'Interface/border-icons/stop.png').write_bytes(b'generated')
        paths, _, _ = atlas.discover(source, source / 'entry.dme', [])
        self.assertEqual(paths, [])


if __name__ == '__main__':
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(BorderIconsTests))
    target = BASE / 'tests/border-icons-checks.json'
    target.write_text(json.dumps(dict(passed=result.wasSuccessful(), focused_tests=result.testsRun,
                                     exporter_sha256=consumer.sha(Path(consumer.__file__).read_bytes()),
                                     test_sha256=consumer.sha(Path(__file__).read_bytes())), indent=2) + '\n')
    raise SystemExit(0 if result.wasSuccessful() else 1)
