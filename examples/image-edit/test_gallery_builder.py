#!/usr/bin/env python3
"""Offline regression tests: no CLI, browser, or model credentials required."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent

class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.destination = Path(self.temp.name)/'gallery'

    def run_builder(self, *args):
        return subprocess.run([sys.executable,str(ROOT/'build_gallery.py'),*map(str,args)],capture_output=True,text=True)

    def test_input_requires_destination(self):
        result=self.run_builder('--input',ROOT/'source.jpg')
        self.assertEqual(result.returncode,2)
        self.assertIn('--input requires --output-dir',result.stderr)

    def test_nonempty_destination_is_protected_even_with_overwrite(self):
        self.destination.mkdir()
        marker=self.destination/'keep.txt';marker.write_text('keep')
        result=self.run_builder('--input',ROOT/'source.jpg','--output-dir',self.destination,'--overwrite')
        self.assertEqual(result.returncode,2)
        self.assertEqual(marker.read_text(),'keep')

    def test_invalid_width_does_not_create_output(self):
        result=self.run_builder('--input',ROOT/'source.jpg','--output-dir',self.destination,'--width','9999')
        self.assertEqual(result.returncode,2)
        self.assertFalse(self.destination.exists())

    def test_unknown_case_does_not_create_output(self):
        result=self.run_builder('--input',ROOT/'source.jpg','--output-dir',self.destination,'--only','missing-case')
        self.assertEqual(result.returncode,2)
        self.assertFalse(self.destination.exists())

    def prepare(self):
        self.destination.mkdir()
        for name in ['source.jpg','cases.json','capabilities.json']:
            shutil.copy2(ROOT/name,self.destination/name)
        shutil.copytree(ROOT/'recipes',self.destination/'recipes')
        (self.destination/'custom-source.json').write_text('{}')

    def test_changed_source_rejects_old_results(self):
        self.prepare()
        (self.destination/'results.json').write_text(json.dumps({'source_sha256':'wrong','cases':{}}))
        result=self.run_builder('--output-dir',self.destination)
        self.assertEqual(result.returncode,2)
        self.assertIn('Source changed',result.stderr)
        self.assertFalse((self.destination/'index.html').exists())

    def test_unrendered_custom_gallery_has_valid_hero_and_labels(self):
        self.prepare()
        result=self.run_builder('--output-dir',self.destination)
        self.assertEqual(result.returncode,0,result.stderr)
        page=(self.destination/'index.html').read_text()
        self.assertNotIn('src="images/stage-balance.jpg"',page)
        self.assertNotIn('href="../../',page)
        self.assertIn('Your photograph. Your experiments.',page)
        self.assertIn('Not rendered',page)
        self.assertIn('They do not identify subjects',page)
        markdown=(self.destination/'GALLERY.md').read_text()
        self.assertIn('Not rendered',markdown)
        self.assertNotIn('![Edited:',markdown)
        self.assertEqual(markdown.count('[Recipe]('),113)


if __name__=='__main__': unittest.main()
