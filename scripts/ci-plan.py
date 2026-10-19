# SPDX-License-Identifier: Apache-2.0
"""Select affected samples. Shared/root changes conservatively test everything."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def catalog():
    entries = json.loads((ROOT / "samples/catalog.json").read_text())
    ids = set()
    paths = set()
    for sample in entries:
        expected = f"samples/{sample['area']}/{sample['task']}/{sample['language']}"
        assert sample['path'] == expected, "Catalog must match area/task/language layout"
        assert sample['id'] not in ids and expected not in paths, "Duplicate sample"
        ids.add(sample['id'])
        paths.add(expected)
        assert sample['kind'] in ('request', 'application')
        assert sample['test'] and all(isinstance(arg, str) for arg in sample['test'])
        for required in ('README.md', '.env.example', 'src', 'tests'):
            assert (ROOT / expected / required).exists(), f"Missing {expected}/{required}"
    actual = {str(p.parent.relative_to(ROOT)) for p in (ROOT / 'samples').glob('*/*/*/README.md')}
    assert paths == actual, "Every runnable sample must be cataloged"
    return entries


def select(entries, files):
    if files is None:
        return entries
    selected = set()
    for filename in files:
        matches = [s for s in entries if filename.startswith(s['path'] + '/')]
        if not matches:
            return entries  # Includes fixtures, workflow, catalog and removed samples.
        selected.update(s['id'] for s in matches)
    return [s for s in entries if s['id'] in selected]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    entries = catalog()
    try:
        files = subprocess.check_output(['git', 'diff', '--no-renames', '--name-only', args.base, args.head], cwd=ROOT, text=True).splitlines()
    except subprocess.CalledProcessError:
        files = None  # Missing comparison history must never silently skip tests.
    chosen = select(entries, files)
    languages = {s['language'] for s in chosen}
    with open(args.output, 'a', encoding='utf-8') as output:
        output.write('selected=' + json.dumps([s['id'] for s in chosen]) + '\n')
        for language in ('nodejs', 'python', 'java', 'curl'):
            output.write(language + '=' + str(language in languages).lower() + '\n')
    print('Selected:', [s['id'] for s in chosen])
