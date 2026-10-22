"""Gate/ledger falsifiers, not substitutes for native Lean proof checks.

The executable stubs below intentionally simulate process failures. No stubbed
result is retained or presented as native theorem evidence.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_controlled_text.py'
SPEC = importlib.util.spec_from_file_location('checked_text_gate_for_tests', SCRIPT)
assert SPEC is not None and SPEC.loader is not None
GATE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GATE)
PREFIX = 'ProofReader.ControlledEnglish.Text.'


def axiom_log(axioms: str = 'propext, Classical.choice, Quot.sound') -> str:
    return '\n'.join(f"'{PREFIX}{name}' depends on axioms: [{axioms}]"
                     for name in GATE.REQUIRED_THEOREMS)


def invoke(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          text=True, capture_output=True, timeout=15, check=False)


def fake_lean(path: Path, body: str) -> Path:
    """Clearly fake executable used only to falsify error handling."""
    path.write_text(f'#!{sys.executable}\n' + body)
    path.chmod(0o755)
    return path


def test_complete_axiom_inventory_is_required():
    result = GATE.audit_axioms(axiom_log())
    assert set(result) == set(GATE.REQUIRED_THEOREMS)
    assert all(set(values) == GATE.ALLOWED_AXIOMS for values in result.values())


def test_empty_and_explicit_axiom_free_forms_are_allowed():
    assert all(values == [] for values in GATE.audit_axioms(axiom_log('')).values())
    log = '\n'.join(f"'{PREFIX}{name}' does not depend on any axioms"
                    for name in GATE.REQUIRED_THEOREMS)
    assert all(values == [] for values in GATE.audit_axioms(log).values())


@pytest.mark.parametrize('name', GATE.REQUIRED_THEOREMS)
def test_each_missing_contract_inventory_rejects(name):
    log = '\n'.join(line for line in axiom_log().splitlines() if f".{name}'" not in line)
    with pytest.raises(ValueError, match='Missing theorem inventories'):
        GATE.audit_axioms(log)


@pytest.mark.parametrize('extra', ['sorryAx', 'Lean.sorryAx', 'untrustedAxiom', 'Lean.ofReduceBool'])
def test_unpermitted_axioms_reject(extra):
    with pytest.raises(ValueError, match='admission|Unpermitted'):
        GATE.audit_axioms(axiom_log(extra))


@pytest.mark.parametrize('second', [
    "depends on axioms: [propext]", "does not depend on any axioms",
])
def test_duplicate_inventory_rejects(second):
    with pytest.raises(ValueError, match='Duplicate axiom inventory'):
        GATE.audit_axioms(axiom_log() + f"\n'{PREFIX}lex_render' {second}")


def test_wrong_namespace_is_not_a_contract_inventory():
    with pytest.raises(ValueError, match='Missing theorem inventories'):
        GATE.audit_axioms(axiom_log().replace(PREFIX, 'AnotherModule.'))


def test_failure_to_print_inventories_is_not_an_axiom_free_proof():
    with pytest.raises(ValueError, match='Missing theorem inventories'):
        GATE.audit_axioms('All commands completed successfully.\n')


def test_consent_required_before_output_is_created(tmp_path):
    output = tmp_path / 'evidence'
    result = invoke('--output', output)
    assert result.returncode == 2
    assert '--trust-project is required' in result.stderr
    assert not output.exists()


@pytest.mark.parametrize('kind', ['nonempty-directory', 'file'])
def test_existing_evidence_is_never_overwritten(tmp_path, kind):
    output = tmp_path / 'evidence'
    if kind == 'nonempty-directory':
        output.mkdir()
        sentinel = output / 'observation.json'
    else:
        sentinel = output
    sentinel.write_text('historical-failure')
    result = invoke('--output', output, '--trust-project')
    assert result.returncode == 2
    assert 'stale evidence is not reused' in result.stderr
    assert sentinel.read_text() == 'historical-failure'


def test_missing_lean_is_a_retained_failure_not_a_skip(tmp_path):
    output = tmp_path / 'evidence'
    result = invoke('--lean', tmp_path / 'missing-lean', '--output', output, '--trust-project')
    assert result.returncode == 1
    record = json.loads((output / 'observation.json').read_text())
    assert record['status'] == 'failed'
    assert 'Lean executable unavailable' in record['error']
    assert record['commands'] == []
    assert not record['full_document_english_certified']
    assert not record['original_proof_import_checked']
    assert not record['browser_semantics_checked']
    assert not record['observations_authenticated']


def test_empty_directory_may_be_used_but_never_counts_as_success(tmp_path):
    output = tmp_path / 'evidence'
    output.mkdir()
    result = invoke('--lean', tmp_path / 'missing', '--output', output, '--trust-project')
    assert result.returncode == 1
    assert json.loads((output / 'observation.json').read_text())['status'] == 'failed'


def test_wrong_lean_version_is_retained_and_stops_the_gate(tmp_path):
    compiler = fake_lean(tmp_path / 'fake-lean', 'print("Lean (version 4.33.0, fixture)")\n')
    output = tmp_path / 'evidence'
    result = invoke('--lean', compiler, '--output', output, '--trust-project')
    assert result.returncode == 1
    record = json.loads((output / 'observation.json').read_text())
    assert record['status'] == 'failed'
    assert 'Unexpected compiler version' in record['error']
    assert len(record['commands']) == 1
    assert (output / 'version.log').read_text() == 'Lean (version 4.33.0, fixture)\n'


def test_compiler_failure_does_not_become_a_positive_inventory(tmp_path):
    compiler = fake_lean(tmp_path / 'fake-lean',
        'import sys\n'
        'if "--version" in sys.argv:\n'
        '    print("Lean (version 4.34.1, fixture-not-real)")\n'
        'else:\n'
        '    print("SIMULATED COMPILER FAILURE")\n'
        '    raise SystemExit(9)\n')
    output = tmp_path / 'evidence'
    result = invoke('--lean', compiler, '--output', output, '--trust-project')
    assert result.returncode == 1
    record = json.loads((output / 'observation.json').read_text())
    assert record['status'] == 'failed'
    assert 'Compiler failed: foundation' in record['error']
    assert record['commands'][-1]['returncode'] == 9
    assert 'SIMULATED COMPILER FAILURE' in (output / 'foundation.log').read_text()
    assert 'required_contracts_checked' not in record


def test_inventory_is_sorted_content_based_and_detects_extra_files(tmp_path):
    (tmp_path / 'b').write_bytes(b'one')
    (tmp_path / 'a').mkdir()
    (tmp_path / 'a' / 'leaf').write_bytes(b'two')
    before = GATE.inventory(tmp_path)
    assert list(before) == ['a/leaf', 'b']
    assert before == GATE.inventory(tmp_path)
    (tmp_path / 'b').write_bytes(b'changed')
    assert GATE.inventory(tmp_path)['b'] != before['b']
    (tmp_path / 'unexpected').write_bytes(b'extra')
    assert set(GATE.inventory(tmp_path)) == {'a/leaf', 'b', 'unexpected'}
