"""Native gate bookkeeping tests. Synthetic records are not proof evidence."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/check_source_cancellation.py'
SPEC = importlib.util.spec_from_file_location('source_cancellation_gate', SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)


def invoke(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True, timeout=15, check=False)


def inventory():
    return '\n'.join(f"'ProofReader.ArithmeticEnglish.{name}' depends on axioms: [propext, Classical.choice, Quot.sound]"
                     for name in GATE.CONTRACTS)


def test_native_contract_inventory_matches_the_retained_compiler_output():
    output = (ROOT / 'artifacts/source-cancellation/ArithmeticEnglish.log').read_text()
    assert set(GATE.checked_axioms(output)) == set(GATE.CONTRACTS)
    assert len(GATE.CONTRACTS) == 9


@pytest.mark.parametrize('name', GATE.CONTRACTS)
def test_each_missing_contract_is_a_failure(name):
    log = '\n'.join(line for line in inventory().splitlines() if f'.{name}\'' not in line)
    with pytest.raises(ValueError, match='inventory'):
        GATE.checked_axioms(log)


@pytest.mark.parametrize('mutation', ['duplicate', 'unexpected', 'sorry', 'unapproved', 'wrong-namespace'])
def test_no_invented_or_unapproved_contracts(mutation):
    log = inventory()
    if mutation == 'duplicate':
        log += '\n' + log.splitlines()[0]
    elif mutation == 'unexpected':
        log += "\n'ProofReader.ArithmeticEnglish.unrelated' depends on axioms: []"
    elif mutation == 'sorry':
        log = log.replace('propext', 'sorryAx')
    elif mutation == 'unapproved':
        log = log.replace('propext', 'unapprovedAxiom')
    else:
        log = log.replace('ArithmeticEnglish', 'Unrelated')
    with pytest.raises(ValueError):
        GATE.checked_axioms(log)


def test_execution_consent_is_required_before_creating_evidence(tmp_path):
    output = tmp_path / 'evidence'
    result = invoke('--project', tmp_path / 'project', '--output', output)
    assert result.returncode == 2
    assert '--trust-project' in result.stderr
    assert not output.exists()


@pytest.mark.parametrize('which', ['same', 'output-in-project', 'project-in-output'])
def test_evidence_and_project_cannot_overlap(tmp_path, which):
    project, output = tmp_path / 'project', tmp_path / 'evidence'
    if which == 'same':
        output = project
    elif which == 'output-in-project':
        output = project / 'evidence'
    else:
        project = output / 'project'
    result = invoke('--project', project, '--output', output, '--trust-project')
    assert result.returncode == 2
    assert 'must be separate' in result.stderr


def test_old_failure_record_is_not_overwritten(tmp_path):
    output = tmp_path / 'evidence'
    output.mkdir()
    sentinel = output / 'observation.json'
    sentinel.write_text('historical failure')
    result = invoke('--project', tmp_path / 'project', '--output', output, '--trust-project')
    assert result.returncode == 2
    assert sentinel.read_text() == 'historical failure'


def test_missing_environment_fails_instead_of_skipping(tmp_path):
    output = tmp_path / 'evidence'
    result = invoke('--project', tmp_path / 'missing', '--output', output, '--trust-project')
    assert result.returncode == 1
    report = json.loads((output / 'observation.json').read_text())
    assert report['status'] == 'failed' and report['certified_sentence_count'] == 0
    assert report['commands'] == []
    assert not report['complete_english_proof_certified']
    assert not report['original_project_replayed']


def test_retained_archive_cannot_be_replaced_by_a_commit_label(tmp_path):
    archive = tmp_path / 'not-an-environment.zip'
    archive.write_text(GATE.MATHLIB)
    with pytest.raises(ValueError, match='archive identity'):
        GATE.check_archive(tmp_path / 'project', archive)


def test_all_native_mutations_failed_for_the_intended_reason_without_a_record():
    directory = ROOT / 'artifacts/source-cancellation'
    report = json.loads((directory / 'observation.json').read_text())
    commands = {c['label']: c for c in report['commands']}
    assert len(GATE.NEGATIVES) == 12
    for mode, reason in GATE.NEGATIVES.items():
        assert commands[mode]['returncode'] != 0
        assert reason in (directory / (mode + '.log')).read_text()
        assert not (directory / (mode + '.json')).exists()


def test_source_paths_and_native_values_are_reconciled():
    records = json.loads((ROOT / 'artifacts/source-cancellation/positive.json').read_text())
    source_paths = json.loads((ROOT / 'docs/companion/cancellation-paths.json').read_text())
    GATE.validate_records(records, source_paths)
    with pytest.raises(ValueError, match='occurrence mismatch'):
        GATE.validate_records(records, list(reversed(source_paths)))
    with pytest.raises(ValueError, match='precisely two'):
        GATE.validate_records(records[:1], source_paths)
