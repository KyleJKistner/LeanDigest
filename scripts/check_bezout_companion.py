#!/usr/bin/env python3
"""Reproduce the companion's narrow, pinned native evidence in an isolated Mathlib checkout.

This executes trusted Lean metaprograms. It does not build the original OAI
project, certify English, download dependencies, or publish anything.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from proofreader.lean import driver_file, run_bounded
from proofreader.narrative import Snapshot
from proofreader.narrative_io import extract_narrative

MATHLIB = 'd13f23b723b8a846827a245b89c10fc7d3f11612'
UPSTREAM = '1581d4cbdd69a0faf34b2089614fe2a814316a6a'
THEOREM = 'OAI.ComplexCancellation.BezoutFrame.exists_frame'
ORIGINAL = ROOT / 'examples/openai/lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean'
RETAINED = ROOT / 'artifacts/v0.3'
ORIGINAL_SHA256 = 'd108afa98f200bfce183b8afc0af586b70734f7ad2cce1bc5e49853a2f555c6f'


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--trust-project', action='store_true')
    args = parser.parse_args()
    if not args.trust_project:
        parser.error('Lean elaboration executes code; --trust-project is required')
    project = args.project.resolve()
    output = args.output.resolve()
    if output == project or project.is_relative_to(output) or output.is_relative_to(project):
        parser.error('Evidence output and native project must be separate')
    output.mkdir(parents=True, exist_ok=True)
    # Preflight can fail too. Invalidate the prior result before opening any
    # source, snapshot, project, or dependency that might be missing or changed.
    write_json(output / 'observation.json', {
        'schema': 'leanglish.bezout-native-observation/v1', 'status': 'failed',
        'scope': 'fresh-pinned-adapted-context', 'checks': {},
        'errors': ['Verification has not completed; inspect the failed command.']})
    if sha256(ORIGINAL.read_bytes()).hexdigest() != ORIGINAL_SHA256:
        parser.error('Original source differs from the pinned upstream module')
    expected = Snapshot.read(ROOT / 'artifacts/companion/native/current/snapshot.json')
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=project, text=True).strip() != MATHLIB:
        parser.error('Project is not the exact pinned Mathlib checkout')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'],
                               cwd=project, text=True).strip():
        parser.error('Pinned Mathlib tracked source has local modifications')
    if (project / 'lean-toolchain').read_text().strip() != 'leanprover/lean4:v4.34.1':
        parser.error('Pinned toolchain differs')
    manifest = json.loads((project / 'lake-manifest.json').read_text())
    dependencies = []
    for dependency in manifest['packages']:
        path = project / manifest['packagesDir'] / dependency['name']
        actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=path, text=True).strip()
        dirty = subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'],
                                        cwd=path, text=True).strip()
        if actual != dependency['rev'] or dirty:
            parser.error('Missing, changed or mismatched dependency: ' + dependency['name'])
        dependencies.append({'name': dependency['name'], 'url': dependency['url'], 'commit': actual})
    summary = {'schema': 'leanglish.bezout-native-observation/v1', 'status': 'failed',
               'scope': 'fresh-pinned-adapted-context',
               'theorem': THEOREM, 'upstream_commit': UPSTREAM,
               'mathlib_commit': MATHLIB, 'lean_version': '4.34.1',
               'dependencies': dependencies, 'original_source_sha256': sha256(ORIGINAL.read_bytes()).hexdigest(),
               'checker_script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
               'exporter_sha256': sha256((ROOT / 'proofreader/data/Narrative.lean').read_bytes()).hexdigest(),
               'exact_openai_project_replayed': False, 'english_formally_verified': False,
               'receipt_authenticated': False, 'checks': {}}
    write_json(output / 'observation.json', summary)
    source = ORIGINAL.read_text()
    header = 'import OAI.Algebra.AffineCancellation.Model\n'
    if not source.startswith(header):
        raise ValueError('Unexpected original import boundary')
    context = ('import Mathlib.Algebra.EuclideanDomain.Basic\nimport Mathlib.Tactic.Ring\n'
               + source[len(header):])
    assert context[context.index('namespace OAI'):] == source[source.index('namespace OAI'):]
    summary['import_adaptation'] = {'removed': ['OAI.Algebra.AffineCancellation.Model'],
        'added': ['Mathlib.Algebra.EuclideanDomain.Basic', 'Mathlib.Tactic.Ring'],
        'theorem_body_bytes_unchanged': True,
        'context_sha256': sha256(context.encode()).hexdigest(),
        'scope': 'Unchanged theorem body under explicitly substituted, pinned Mathlib imports.'}
    current = extract_narrative(THEOREM, output / 'current', context=context,
        project=project, trust_project=True, timeout=180, max_heartbeats=2_000_000,
        expected=expected.record)
    summary['checks']['current_export'] = current['status']
    write_json(output / 'observation.json', summary)
    if current['status'] != 'passed':
        print(json.dumps(summary), flush=True)
        return 1
    snapshot = Snapshot.read(output / 'current/snapshot.json')
    repeated = extract_narrative(THEOREM, output / 'repeat', context=context,
        project=project, trust_project=True, timeout=180, expected=snapshot.record,
        max_heartbeats=2_000_000)
    summary['checks']['repeat_snapshot_exact'] = repeated['status']
    old = extract_narrative(THEOREM, output / 'retained-driver',
        driver=(RETAINED / 'bezout-4.34.1-valid.lean').read_text(),
        expected=Snapshot.read(RETAINED / 'bezout.narrative.json').record,
        project=project, trust_project=True, timeout=180)
    # Historical byte identity is an explicit comparison, not the contract for
    # the fresh reading. The old exporter includes module-scoped generated names.
    historical_stdout = (output / 'retained-driver/stdout.txt').read_text()
    historical_run = json.loads((output / 'retained-driver/run.json').read_text())
    summary['historical_comparison'] = {
        'snapshot_exact': old['status'], 'errors': old.get('errors', []),
        'expected_snapshot_sha256': old['expected_snapshot_sha256'],
        'native_exit_code': historical_run['exit_code'],
        'internal_repeat_and_mutation_markers': all(marker in historical_stdout for marker in
            ('PR_NARRATIVE_REPEAT_OK', 'PR_NARRATIVE_MUTATION_REJECTED')),
        'note': 'The older exporter retains macro-scoped instance names that depend on its module path. '
                'A failed historical byte comparison remains a failure; the fresh reading uses its own exact repeat.'}
    summary['selected_judgements'] = len(snapshot.frames)
    summary['axioms'] = snapshot.record['axioms']
    summary['snapshot_sha256'] = snapshot.sha256
    current_driver = (output / 'current/Extract.lean').read_text()
    mutations = {
        'wrong_path': ('let actual ← match atPath original path with',
                       'let actual ← match atPath original (if i == 40 then [] else path) with'),
        'wrong_claim': ('let ct ← liftM <| mkForallFVars xs typ (usedLetOnly := false)',
                        'let ct ← liftM <| mkForallFVars xs (if i == 40 then mkConst ``False else typ) (usedLetOnly := false)')}
    for name, expected_error in (
            ('wrong_path', 'Original source linkage mismatch'),
            ('wrong_claim', 'type mismatch')):
        before, after = mutations[name]
        if current_driver.count(before) != 1:
            raise ValueError('Current exporter mutation target is not unique: ' + name)
        driver = current_driver.replace(before, after)
        directory = output / name
        directory.mkdir(exist_ok=True)
        (directory / 'Probe.lean').write_text(driver)
        with driver_file(project, driver) as path:
            result = run_bounded(['lake', 'env', 'lean', str(path)], project, timeout=180)
        write_json(directory / 'run.json', asdict(result))
        (directory / 'stdout.txt').write_text(result.stdout)
        (directory / 'stderr.txt').write_text(result.stderr)
        text = (result.stdout + result.stderr).lower()
        summary['checks'][name + '_rejected'] = ('passed'
            if result.exit_code not in (None, 0) and expected_error.lower() in text else 'failed')
        write_json(output / 'observation.json', summary)
    summary['status'] = 'passed' if all(v == 'passed' for v in summary['checks'].values()) else 'failed'
    summary['files'] = {path.relative_to(output).as_posix(): sha256(path.read_bytes()).hexdigest()
                        for path in sorted(output.rglob('*'))
                        if path.is_file() and path.name != 'observation.json'}
    write_json(output / 'observation.json', summary)
    print(json.dumps({key: summary[key] for key in ('status', 'checks', 'selected_judgements',
                                                   'snapshot_sha256', 'axioms')}), flush=True)
    return 0 if summary['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
