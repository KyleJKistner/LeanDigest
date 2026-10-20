"""Document evidence and display tests; native proofs run in a separate gate."""
from __future__ import annotations

import copy
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from proofreader import document_text as loader
from scripts import check_source_document as gate

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('checked_proof_builder', ROOT / 'docs/companion/build_checked_proof.py')
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


@pytest.fixture
def evidence(tmp_path):
    return Path(shutil.copytree(loader.EVIDENCE, tmp_path / 'document'))


def mutate(path, change):
    report = json.loads((path / 'observation.json').read_text())
    change(report)
    (path / 'observation.json').write_text(json.dumps(report))


class ProofText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.parts = []
        self.passages = []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get('id') == 'proof-text': self.active = True
        if self.active and values.get('class') == 'source-passage':
            self.passages.append((values['data-kind'], int(values['data-index'])))
    def handle_endtag(self, tag):
        if tag == 'pre': self.active = False
    def handle_data(self, data):
        if self.active: self.parts.append(data)


def test_complete_native_run_and_both_restored_scopes():
    result = loader.load_document()
    report, record = result['observation'], result['record']
    gate.validate_record(record, gate.configuration())
    assert len(report['commands']) == 31
    assert report['parser_guards'] == 30
    assert report['source_negative_cases'] == 16
    assert len(record['equations']) == 10
    assert sum(r['link_count'] for r in record['equations']) == 19
    assert len(record['witnesses']) == len(record['cancellations']) == 2
    assert record['document']['closed_outer_binders'] == 2
    assert [r['name'] for r in record['nonzero_context'] if r['definition_restored']] == [
        'g', 'ha', 'hd', 'r', 's', 'hbez', 'hrel']
    assert record['zero_context'][-1]['name'] == 'hxz'
    assert record['zero_context'][-1]['definition_restored'] is True
    assert result['text'].startswith('Statement\nLet R be a Euclidean domain.')
    assert result['text'].endswith('so the statement follows.\n\n')


def test_gate_and_reader_contract_inventories_agree():
    assert loader.MODULES == gate.MODULES
    assert loader.CONTRACTS == gate.CONTRACTS
    assert loader.NEGATIVES == gate.NEGATIVES
    assert loader.ALLOWED_AXIOMS == gate.base.ALLOWED_AXIOMS
    assert gate.contract_axioms((loader.EVIDENCE / 'ProofDocument.log').read_text()) == \
        loader.load_document()['observation']['contract_axioms']


@pytest.mark.parametrize('label', gate.NEGATIVES)
def test_actual_negative_controls_reject_before_a_document_is_emitted(label):
    report = loader.load_document()['observation']
    row = next(r for r in report['commands'] if r['label'] == label)
    assert row['returncode'] != 0
    text = (loader.EVIDENCE / (label + '.log')).read_text()
    assert gate.NEGATIVES[label] in text
    assert 'SOURCE_DOCUMENT_CHECKED:1' not in text
    assert not (loader.EVIDENCE / (label + '.json')).exists()


@pytest.mark.parametrize('key,value', [
    ('schema', 'other'), ('status', 'failed'), ('theorem', 'Wrong'),
    ('source_sha256', '0' * 64), ('upstream_commit', '0' * 40),
    ('certified_surface', 'all-english'), ('canonical_document_count', True),
    ('source_passage_count', 13), ('equation_link_count', 18),
    ('source_negative_cases', 15), ('parser_guards', 29),
    ('repeat_byte_identical', 'true'), ('complete_canonical_document_certified', False),
])
def test_missing_or_changed_document_acceptance_is_rejected(evidence, key, value):
    mutate(evidence, lambda r: r.update({key: value}))
    with pytest.raises(ValueError): loader.load_document(evidence)


@pytest.mark.parametrize('key', loader.FLAGS_FALSE)
@pytest.mark.parametrize('value', [True, None, 'false'])
def test_document_certificate_does_not_promote_unchecked_surfaces(evidence, key, value):
    mutate(evidence, lambda r: r.update({key: value}))
    with pytest.raises(ValueError, match='scope'): loader.load_document(evidence)


@pytest.mark.parametrize('case', ['missing-file', 'extra-file', 'nested', 'symlink',
                                 'observation-link', 'duplicate-key', 'missing-inventory'])
def test_file_inventory_and_duplicate_keys_fail_closed(evidence, tmp_path, case):
    if case == 'missing-file': (evidence / 'proof.txt').unlink()
    elif case == 'extra-file': (evidence / 'unexpected.txt').write_text('new')
    elif case == 'nested': (evidence / 'nested').mkdir()
    elif case in ('symlink', 'observation-link'):
        name = 'observation.json' if case == 'observation-link' else 'proof.txt'
        target = tmp_path / 'original'
        shutil.copyfile(evidence / name, target)
        (evidence / name).unlink(); (evidence / name).symlink_to(target)
    elif case == 'duplicate-key':
        p = evidence / 'observation.json'
        p.write_text('{"status":"passed",' + p.read_text()[1:])
    else: mutate(evidence, lambda r: r['files_sha256'].pop('proof.txt'))
    with pytest.raises(ValueError): loader.load_document(evidence)


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'reorder', 'wrong-exit', 'truthy-exit',
                                 'timeout', 'no-outcome', 'wrong-log'])
def test_incomplete_command_ledger_is_not_a_success(evidence, case):
    def change(r):
        rows = r['commands']
        if case == 'missing': rows.pop()
        elif case == 'duplicate': rows[-1] = rows[0]
        elif case == 'reorder': rows[1], rows[2] = rows[2], rows[1]
        elif case == 'wrong-exit': rows[0]['returncode'] = 1
        elif case == 'truthy-exit': rows[0]['returncode'] = False
        elif case == 'timeout': rows[0]['timed_out'] = True
        elif case == 'no-outcome': rows[0]['expected_outcome_observed'] = False
        elif case == 'wrong-log': rows[0]['stdout_sha256'] = '0' * 64
    mutate(evidence, change)
    with pytest.raises(ValueError): loader.load_document(evidence)


@pytest.mark.parametrize('case', ['missing-module', 'module-bytes', 'gate', 'helper', 'mathlib',
                                 'version', 'adaptation', 'config', 'contract-name', 'axiom'])
def test_code_source_environment_and_contracts_remain_bound(evidence, case):
    def change(r):
        if case == 'missing-module': r['module_sha256'].pop('SourceProofDocument.lean')
        elif case == 'module-bytes': r['module_sha256']['ProofDocument.lean'] = '0' * 64
        elif case == 'gate': r['gate_sha256'] = '0' * 64
        elif case == 'helper': r['helper_sha256']['check_source_equations.py'] = '0' * 64
        elif case == 'mathlib': r['environment']['mathlib_commit'] = '0' * 40
        elif case == 'version': r['lean_version'] = 'Lean (version 4.33.0, fixture)'
        elif case == 'adaptation': r['import_adaptation']['theorem_body_unchanged'] = False
        elif case == 'config': r['configuration']['equations'].reverse()
        elif case == 'contract-name': r['contract_axioms']['unrelated'] = r['contract_axioms'].pop('certify')
        elif case == 'axiom': r['contract_axioms']['certify'] = ['sorryAx']
    mutate(evidence, change)
    with pytest.raises(ValueError): loader.load_document(evidence)


@pytest.mark.parametrize('case', ['text', 'zero-proof-let', 'nonzero-proof-let', 'alias', 'outer-assumptions'])
def test_rehashed_altered_record_cannot_replace_reviewed_document(evidence, case):
    r = json.loads((evidence / 'positive.json').read_text())
    if case == 'text':
        r['document']['text'] += 'Therefore 0 = 1.\n'
        r['document']['utf8'] = list(r['document']['text'].encode())
        (evidence / 'proof.txt').write_bytes(bytes(r['document']['utf8']))
    elif case == 'zero-proof-let': r['zero_context'][8]['definition_restored'] = False
    elif case == 'nonzero-proof-let': r['nonzero_context'][16]['definition_restored'] = False
    elif case == 'alias': r['nonzero_context'][12]['definition_restored'] = False
    else: r['document']['closed_outer_binders'] = 3
    for name in ('positive.json', 'repeat.json'):
        (evidence / name).write_bytes(gate.encoded(r))
    mutate(evidence, lambda obs: obs.update(files_sha256={n: loader.digest(evidence / n)
                                                        for n in obs['files_sha256']}))
    with pytest.raises(ValueError, match='Reviewed document record'): loader.load_document(evidence)


@pytest.mark.parametrize('contract', gate.CONTRACTS)
def test_gate_requires_each_universal_contract(contract):
    text = (loader.EVIDENCE / 'ProofDocument.log').read_text()
    text = '\n'.join(line for line in text.splitlines() if f'.{contract}\'' not in line)
    with pytest.raises(ValueError, match='inventory'): gate.contract_axioms(text)


@pytest.mark.parametrize('case', ['extra-axiom', 'duplicate', 'wrong-namespace'])
def test_gate_rejects_spoofed_contract_logs(case):
    text = (loader.EVIDENCE / 'ProofDocument.log').read_text()
    if case == 'extra-axiom': text = text.replace('propext', 'untrusted')
    elif case == 'duplicate': text += text
    else: text = text.replace('ProofReader.BezoutDocument', 'Wrong')
    with pytest.raises(ValueError): gate.contract_axioms(text)


@pytest.mark.parametrize('kind,index', [('zero_context', 8), ('nonzero_context', 12), ('nonzero_context', 16)])
def test_gate_record_validation_rejects_assumed_local_definitions(kind, index):
    record = copy.deepcopy(loader.load_document()['record'])
    record[kind][index]['definition_restored'] = False
    with pytest.raises(ValueError, match='definition'): gate.validate_record(record, gate.configuration())


def test_gate_consent_precedes_execution_or_evidence_creation(tmp_path):
    output = tmp_path / 'out'
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/check_source_document.py'),
                           '--project', str(tmp_path / 'project'), '--output', str(output)],
                          capture_output=True, text=True, timeout=15)
    assert proc.returncode == 2 and '--trust-project' in proc.stderr
    assert not output.exists()


def test_existing_native_evidence_is_not_overwritten(tmp_path):
    output = tmp_path / 'out'; output.mkdir()
    sentinel = output / 'observation.json'; sentinel.write_text('historical failure')
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/check_source_document.py'),
        '--project', str(tmp_path / 'project'), '--output', str(output), '--trust-project'],
        capture_output=True, text=True, timeout=15)
    assert proc.returncode == 2
    assert sentinel.read_text() == 'historical failure'


def test_invalid_environment_produces_retained_failure(tmp_path):
    output = tmp_path / 'out'; project = tmp_path / 'project'; project.mkdir()
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/check_source_document.py'),
        '--project', str(project), '--output', str(output), '--trust-project'],
        capture_output=True, text=True, timeout=15)
    assert proc.returncode == 1
    obs = json.loads((output / 'observation.json').read_text())
    assert obs['status'] == 'failed' and obs['commands'] == []
    assert obs['complete_canonical_document_certified'] is False


def test_builder_preserves_every_character_and_the_checked_passage_order(tmp_path):
    path = tmp_path / 'checked.html'
    manifest = BUILDER.build(path)
    parser = ProofText(); parser.feed(path.read_text())
    data = loader.load_document()
    assert ''.join(parser.parts) == data['text']
    assert parser.passages == BUILDER.ORDER
    assert manifest['canonical_document_certified'] is True
    assert manifest['authored_companion_certified'] is False
    assert manifest['html_semantics_proved'] is False
    assert manifest['lean_executed_by_build'] is False
    assert path.read_bytes() == (ROOT / 'docs/companion/checked-proof.html').read_bytes()
    assert BUILDER.build(tmp_path / 'repeat.html') == manifest
    assert (tmp_path / 'repeat.html').read_bytes() == path.read_bytes()


def test_missing_evidence_does_not_produce_a_certified_page(tmp_path):
    output = tmp_path / 'checked.html'
    with pytest.raises(ValueError): BUILDER.build(output, evidence_root=tmp_path / 'missing')
    assert not output.exists()


def test_escaping_changes_markup_not_underlying_text():
    # Synthetic display fixture, not an instance of the certified grammar.
    parser = ProofText()
    parser.feed('<pre id="proof-text">' + BUILDER.structural_markup('<script>&"\nStatement\nx<y') + '</pre>')
    assert ''.join(parser.parts) == '<script>&"\nStatement\nx<y'
    assert '<script>' not in BUILDER.structural_markup('<script>')
