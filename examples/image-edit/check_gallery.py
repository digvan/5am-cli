#!/usr/bin/env python3
"""Offline integrity check for the published gallery and its rendered artifacts."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit
import zipfile

ROOT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--allow-partial', action='store_true', help='Permit cases not yet rendered/validated')
args = parser.parse_args()
cases = json.loads((ROOT / 'cases.json').read_text())
report = json.loads((ROOT / 'results.json').read_text())
assert report['source_sha256'] == hashlib.sha256((ROOT / 'source.jpg').read_bytes()).hexdigest()
assert len({c['id'] for c in cases}) == len(cases)
assert set(report['cases']) <= {c['id'] for c in cases}
if not args.allow_partial: assert set(report['cases']) == {c['id'] for c in cases}
commands = set()
for case in cases:
    recipe = (ROOT / 'recipes' / (case['id'] + '.iedl')).read_text()
    commands.update(line.split()[0] for line in recipe.splitlines() if line.strip() and not line.startswith('#'))
    if args.allow_partial and case['id'] not in report['cases']: continue
    result = report['cases'][case['id']]
    if case['remote']:
        assert result['status'] == 'Recipe only' and result['validated']
        assert not result.get('image'), case['id']
        continue
    assert result['status'] == 'Rendered', case['id']
    assert result['width'] > 0 and result['height'] > 0
    data = (ROOT / result['image']).read_bytes()
    assert data.startswith((b'\xff\xd8', b'\x89PNG', b'RIFF')), case['id']
    resolved = json.loads((ROOT / 'resolved' / (case['id'] + '.json')).read_text())
    assert resolved['source']['sha256'] == report['source_sha256'], case['id']
    if case['mask']:
        assert (ROOT / result['mask']).read_bytes().startswith(b'\x89PNG'), case['id']
    if result.get('bundle'):
        with zipfile.ZipFile(ROOT / result['bundle']) as bundle:
            assert bundle.testzip() is None
registry = json.loads((ROOT / 'capabilities.json').read_text())
assert not set(registry['registry']) - commands

class Links(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key not in ('src', 'href') or not value: continue
            url = urlsplit(value)
            if url.scheme or url.netloc or not url.path: continue
            assert (ROOT / unquote(url.path)).is_file(), value

Links().feed((ROOT / 'index.html').read_text())
print(f'PASS: {len(cases)} cases, source hashes, artifacts, command coverage, and HTML links')
