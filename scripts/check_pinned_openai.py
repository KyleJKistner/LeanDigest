#!/usr/bin/env python3
"""Bounded native acceptance run against an unchanged OpenAI import closure.

This does not build the full OpenAI project. It uses a reduced Lake configuration
with the upstream compiler flags and exact Mathlib dependency revisions. Source,
manifest, execution, extraction, and reading results remain distinct in the ledger.
Network access and Lean metaprogram execution each require explicit consent.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from proofreader.lean import run_bounded
from proofreader.narrative_io import extract_narrative

COMMIT = '1581d4cbdd69a0faf34b2089614fe2a814316a6a'
MATHLIB = 'd13f23b723b8a846827a245b89c10fc7d3f11612'
MODULE = 'OAI.Algebra.AffineCancellation.BezoutFrame'
TARGETS = [
    (MODULE + '.exists_frame', 'OpenAI source target'),
    ('Nat.add_comm', 'standard-library control'),
    ('List.reverse_reverse', 'standard-library control'),
    ('Set.union_assoc', 'Mathlib control'),
    ('Function.Injective.comp', 'Mathlib control'),
    ('Finset.card_union_add_card_inter', 'Mathlib control'),
    ('Nat.gcd_comm', 'standard-library control'),
]
SOURCES = {
    'OAI/Algebra/AffineCancellation/Model.lean': '2c633efa58fa934eeca8097d12f57b6f9c9fee11',
    'OAI/Algebra/AffineCancellation/BezoutFrame.lean': '3e50ca65f9638fd532b6fff5054726b29bd17974',
}
UPSTREAM_MANIFEST = '67d01d2717d0aaff59fb8814bb53581b961f42b4'
MATHLIB_MANIFEST = 'de612f43de68d2b64dc65f74fc9b37d1f9d20898'


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)


def download(url: str, expected: str) -> bytes:
    if not url.startswith('https://raw.githubusercontent.com/'):
        raise ValueError('Only fixed public GitHub source URLs are supported')
    req = urllib.request.Request(url, headers={'User-Agent': 'LeanDigest-pinned-acceptance'})
    with urllib.request.urlopen(req, timeout=60) as response:
        data = response.read(4_000_001)
    if len(data) > 4_000_000 or blob(data) != expected:
        raise ValueError('Pinned Git-blob verification failed: ' + url)
    data.decode('utf-8')
    return data


def dependency_manifest(upstream: dict, mathlib: dict) -> dict:
    """Use upstream revisions, never resolve mutable upstream inputRev branches."""
    entries = upstream['packages']
    by_name = {p['name']: p for p in entries}
    if len(by_name) != len(entries):
        raise ValueError('Duplicate upstream dependency name')
    required = ['mathlib'] + [p['name'] for p in mathlib['packages']]
    if len(set(required)) != len(required):
        raise ValueError('Duplicate required dependency')
    selected = []
    for name in required:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', name):
            raise ValueError('Unsafe dependency name')
        if name not in by_name:
            raise ValueError('Missing pinned dependency: ' + name)
        p = dict(by_name[name])
        if p['type'] != 'git' or not re.fullmatch(r'[0-9a-f]{40}', p['rev']):
            raise ValueError('Unpinned dependency: ' + name)
        if not p['url'].startswith('https://github.com/') or p.get('subDir') is not None:
            raise ValueError('Unexpected dependency origin/layout: ' + name)
        p['inputRev'] = p['rev']
        p['inherited'] = name != 'mathlib'
        selected.append(p)
    if selected[0]['rev'] != MATHLIB:
        raise ValueError('Unexpected Mathlib revision')
    return {'version': upstream['version'], 'packagesDir': '.lake/packages',
            'packages': selected, 'name': 'OAI', 'lakeDir': '.lake', 'fixedToolchain': True}


def prepare(project: Path, output: Path) -> dict:
    project, output = project.resolve(), output.resolve()
    if project == output or project in output.parents or output in project.parents:
        raise ValueError('Project and output directories must be disjoint')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty output directory')
    project.mkdir(parents=True, exist_ok=True)
    if any(project.iterdir()):
        raise ValueError('Use a new empty project directory; existing work is not overwritten')
    upstream_bytes = download(f'https://raw.githubusercontent.com/openai/math/{COMMIT}/lean/lake-manifest.json', UPSTREAM_MANIFEST)
    mathlib_bytes = download(f'https://raw.githubusercontent.com/leanprover-community/mathlib4/{MATHLIB}/lake-manifest.json', MATHLIB_MANIFEST)
    manifest = dependency_manifest(json.loads(upstream_bytes), json.loads(mathlib_bytes))
    output.mkdir(parents=True, exist_ok=True)
    (output/'upstream-lake-manifest.json').write_bytes(upstream_bytes)
    (output/'mathlib-lake-manifest.json').write_bytes(mathlib_bytes)
    for path, sha in SOURCES.items():
        data = download(f'https://raw.githubusercontent.com/openai/math/{COMMIT}/lean/{path}', sha)
        target = project/path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (project/'lean-toolchain').write_text('leanprover/lean4:v4.34.1\n')
    (project/'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage OAI where\n  fixedToolchain := true\n  leanOptions := #[\u27e8`autoImplicit, false\u27e9]\nrequire mathlib from git\n  "https://github.com/leanprover-community/mathlib4.git" @ "'+MATHLIB+'"\nlean_lib OAI\n', encoding='utf-8')
    write_json(project/'lake-manifest.json', manifest)
    info = {'source_commit': COMMIT, 'mathlib_commit': MATHLIB,
            'sources': SOURCES, 'original_imports_preserved': True,
            'configuration': 'reduced dependency-closure fixture; not the complete upstream Lake project',
            'autoImplicit': False, 'lean_version': '4.34.1',
            'dependencies': manifest['packages'], 'full_openai_project_built': False}
    write_json(output/'preparation.json', info)
    return info


def verify_checkout(project: Path, info: dict) -> list[dict]:
    for path, expected in info['sources'].items():
        if blob((project/path).read_bytes()) != expected:
            raise ValueError('Source changed: ' + path)
    installed = json.loads((project/'lake-manifest.json').read_text())
    actual = {p['name']: p for p in installed['packages']}
    expected = {p['name']: p for p in info['dependencies']}
    if set(actual) != set(expected):
        raise ValueError('Dependency inventory changed')
    checked = []
    for name, p in expected.items():
        for field in ('rev', 'url', 'type', 'subDir'):
            if actual[name].get(field) != p.get(field):
                raise ValueError('Dependency manifest drift: ' + name)
        path = project/'.lake/packages'/name
        head = run_bounded(['git', 'rev-parse', 'HEAD'], path, timeout=15)
        diff = run_bounded(['git', 'diff', '--exit-code', 'HEAD', '--'], path, timeout=15)
        if head.status != 'passed' or head.stdout.strip() != p['rev'] or diff.status != 'passed':
            raise ValueError('Dependency checkout drift: ' + name)
        checked.append({'name': name, 'revision': p['rev'], 'tracked_sources_unchanged': True})
    return checked


def execute(project: Path, output: Path, info: dict) -> dict:
    ledger = {'schema': 'leandigest.pinned-acceptance/v1', 'status': 'running',
              'source_commit': COMMIT, 'expected_targets': len(TARGETS),
              'full_openai_project_built': False, 'english_formally_verified': False,
              'rows': [{'theorem': n, 'kind': k, 'status': 'not-run'} for n, k in TARGETS]}
    def save():
        write_json(output/'result.json', ledger)
    save()
    try:
        for label, command, seconds in [
            ('cache', ['lake', 'exe', 'cache', 'get', 'Mathlib'], 1200),
            ('build', ['lake', 'build', MODULE], 1200),
        ]:
            run = run_bounded(command, project, timeout=seconds, max_output=8_000_000)
            write_json(output/(label+'.json'), asdict(run))
            print(label, run.status, flush=True)
            if run.status != 'passed':
                raise RuntimeError(label + ' failed: ' + (run.stderr + run.stdout)[-5000:])
        ledger['dependencies_checked'] = verify_checkout(project, info)
        ledger['original_source_hashes_matched'] = True
        for i, row in enumerate(ledger['rows']):
            dest = output/f'target-{i:02}'
            receipt = extract_narrative(row['theorem'], dest, module=MODULE, version='4.34.1',
                                        project=project, trust_project=True, timeout=240)
            row.update(status=receipt['status'], errors=receipt['errors'], directory=dest.name)
            if receipt['status'] == 'passed':
                coverage = json.loads((dest/'coverage.json').read_text())
                row.update(coverage=coverage, snapshot_sha256=receipt['snapshot_sha256'])
                again = extract_narrative(row['theorem'], output/f'repeat-{i:02}', module=MODULE,
                    version='4.34.1', project=project, trust_project=True, timeout=240,
                    expected=json.loads((dest/'snapshot.json').read_text()))
                row['reextraction_matched'] = again['status'] == 'passed'
                if again['status'] != 'passed':
                    row.update(status='failed', errors=again['errors'])
            print(json.dumps(row, ensure_ascii=False, sort_keys=True), flush=True)
            save()
        verify_checkout(project, info)
        ledger['status'] = 'passed' if all(x['status']=='passed' for x in ledger['rows']) else 'partial'
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        ledger.update(status='failed', error=str(exc))
    ledger['targets_passed'] = sum(x['status']=='passed' for x in ledger['rows'])
    save()
    print('PINNED_ACCEPTANCE ' + json.dumps(ledger, ensure_ascii=False, sort_keys=True), flush=True)
    return ledger


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--allow-network', action='store_true')
    p.add_argument('--trust-project', action='store_true')
    args = p.parse_args()
    if not args.allow_network or not args.trust_project:
        p.error('Both --allow-network and --trust-project are required: dependencies and Lean metaprograms execute code')
    project, output = args.project.resolve(), args.output.resolve()
    try:
        info = prepare(project, output)
        return 0 if execute(project, output, info)['status'] == 'passed' else 1
    except (OSError, ValueError, KeyError) as exc:
        write_json(output/'result.json', {'status':'preparation-failed', 'error':str(exc),
            'expected_targets':len(TARGETS), 'targets_passed':0, 'full_openai_project_built':False})
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
