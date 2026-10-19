"""Native-record reconciliation and tamper tests; no substitute for Lean replay."""
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

from proofreader import equation_text as source
from scripts import check_source_equations as gate

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('equation_companion_builder', ROOT/'docs/companion/build.py')
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


@pytest.fixture
def evidence(tmp_path):
    return Path(shutil.copytree(source.EVIDENCE, tmp_path/'equations'))


def mutate(path, change):
    target = path/'observation.json'
    report = json.loads(target.read_text())
    change(report)
    target.write_text(json.dumps(report))


class Passages(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.texts = []
        self.frames = []
        self.sections = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details' and attrs.get('class') == 'checked-equations':
            self.sections.append(attrs['data-proof-section'])
        if tag == 'div' and attrs.get('class') == 'checked-calculation':
            self.frames.append((attrs['data-kind'], int(attrs['data-source-frame'])))
        if tag == 'p' and attrs.get('class') == 'checked-equation-text':
            self.active = True
            self.texts.append('')

    def handle_data(self, text):
        if self.active:
            self.texts[-1] += text

    def handle_endtag(self, tag):
        if tag == 'p':
            self.active = False


def test_real_records_preserve_paths_contexts_all_links_and_both_actual_tuples():
    result = source.load_equations()
    report = result['observation']
    assert len(report['commands']) == 43
    assert sum(len(r['links']) for r in result['equations']) == 19
    assert report['native_negative_cases'] == 28
    assert report['native_parser_guards'] == 47
    snapshot = json.loads((ROOT/'artifacts/companion/native/current/snapshot.json').read_text())
    for kind, indices in source.FRAMES.items():
        paths = [snapshot['frames'][i]['path'] for i in indices]
        gate.validate_records(kind, result[kind], paths)
        for row in result[kind]:
            assert row['text'].encode('utf-8') == bytes(row['utf8'])
            assert 'hg' in {c['name'] for c in row['context']}
    zero = result['witnesses'][0]
    nonzero = result['witnesses'][1]
    assert '(1, y, 0, 1)' in zero['text']
    assert '(a, d, g, ((r * (z + 1)) + (s * y)))' in nonzero['text']
    assert next(c for c in zero['context'] if c['name'] == 'hg')['type'] == 'g = 0'
    assert next(c for c in nonzero['context'] if c['name'] == 'hg')['type'] == '¬g = 0'


@pytest.mark.parametrize('kind', ['equations', 'witnesses'])
def test_actual_negative_logs_have_required_reasons_and_no_certificate(kind):
    data = source.load_equations()['observation']
    commands = {r['label']: r for r in data['commands']}
    for variant, expected in gate.NEGATIVES[kind].items():
        label = kind+'-'+variant
        assert commands[label]['returncode'] != 0
        assert expected in (source.EVIDENCE/(label+'.log')).read_text()
        assert not (source.EVIDENCE/(label+'.json')).exists()


@pytest.mark.parametrize('module', gate.CONTRACTS)
def test_actual_compiler_axiom_inventory_matches_the_report(module):
    data = source.load_equations()['observation']
    assert gate.checked_axioms(module, (source.EVIDENCE/(module+'.log')).read_text()) == data['contract_axioms'][module]


def test_builder_embeds_exact_twelve_passages_and_keeps_whole_proof_unverified(tmp_path):
    output = tmp_path/'reader.html'
    manifest = BUILDER.build(output)
    data = source.load_equations()
    parser = Passages()
    parser.feed(output.read_text())
    expected = {(kind, frame): row['text'] for kind, frames in source.FRAMES.items()
                for frame, row in zip(frames, data[kind])}
    assert len(parser.frames) == 12
    assert dict(zip(parser.frames, parser.texts)) == expected
    assert parser.sections == ['step-1','step-2','step-3','step-4','step-5','step-6']
    assert manifest['certified_source_sentences'] == 14
    assert manifest['certified_equation_chains'] == 10
    assert manifest['certified_witness_tuples'] == 2
    assert manifest['curated_prose_formally_verified'] is False
    assert '__CALCULATIONS_' not in output.read_text()


def test_panel_escapes_the_literal_text_without_rephrasing():
    # Synthetic escaping fixture, not a native mathematical certificate.
    text = 'We have <x> = "y" & <script>.'
    html = source.calculation_panel([({'text':text}, 68, 'equations')], 'step-4')
    assert '<script>' not in html
    parser = Passages()
    parser.feed(html)
    assert parser.texts == [text]
    assert parser.frames == [('equations',68)]


@pytest.mark.parametrize('key,value', [
    ('schema','other/v1'), ('status','failed'), ('theorem','Wrong.theorem'),
    ('source_sha256','0'*64), ('upstream_commit','0'*40), ('source_frames',{}),
    ('certified_passage_count',14), ('certified_equation_chain_count',9),
    ('certified_witness_tuple_count',True), ('adjacent_source_equalities',18),
    ('native_negative_cases',27), ('native_parser_guards',46),
    ('repeat_byte_identical','true'), ('lean_version','Lean (version 4.34.0, fixture)'),
])
def test_changed_report_inventory_rejects(evidence, key, value):
    mutate(evidence, lambda r: r.update({key:value}))
    with pytest.raises(ValueError):
        source.load_equations(evidence)


@pytest.mark.parametrize('flag', ['complete_english_proof_certified','original_project_replayed',
                                  'html_semantics_proved','receipt_authenticated'])
@pytest.mark.parametrize('value', [True, 'false', None])
def test_component_cannot_be_promoted_to_full_certification(evidence, flag, value):
    mutate(evidence, lambda r: r.update({flag:value}))
    with pytest.raises(ValueError, match='scope'):
        source.load_equations(evidence)


@pytest.mark.parametrize('kind', ['equations','witnesses'])
def test_altered_text_and_all_recomputed_hashes_do_not_replace_reviewed_record(evidence, kind):
    record_path = evidence/(kind+'-positive.json')
    records = json.loads(record_path.read_text())
    records[0]['text'] = 'We have 0 = 1.'
    records[0]['utf8'] = list(records[0]['text'].encode())
    for run in ['positive','repeat']:
        (evidence/(kind+'-'+run+'.json')).write_text(json.dumps(records))
    (evidence/(kind+'-0.txt')).write_bytes(bytes(records[0]['utf8']))
    def rehash(r):
        for name in r['files_sha256']:
            r['files_sha256'][name] = source.digest(evidence/name)
    mutate(evidence, rehash)
    with pytest.raises(ValueError, match='Reviewed equation record'):
        source.load_equations(evidence)


@pytest.mark.parametrize('case', ['missing','extra','extra-directory','symlink','observation-symlink','duplicate-json','missing-inventory'])
def test_file_inventory_and_json_integrity_reject(evidence, case, tmp_path):
    if case == 'missing':
        (evidence/'equations-0.txt').unlink()
    elif case == 'extra':
        (evidence/'unreviewed.txt').write_text('new')
    elif case == 'extra-directory':
        (evidence/'nested').mkdir()
    elif case in ['symlink','observation-symlink']:
        name = 'observation.json' if case == 'observation-symlink' else 'equations-0.txt'
        target = tmp_path/'outside'
        shutil.copyfile(evidence/name, target)
        (evidence/name).unlink()
        (evidence/name).symlink_to(target)
    elif case == 'duplicate-json':
        text = (evidence/'observation.json').read_text()
        (evidence/'observation.json').write_text('{"status":"passed",'+text[1:])
    else:
        mutate(evidence, lambda r: r['files_sha256'].pop('equations-0.txt'))
    with pytest.raises(ValueError):
        source.load_equations(evidence)


@pytest.mark.parametrize('case', ['missing','duplicate','wrong-exit','timeout','no-outcome','wrong-log','string-exit'])
def test_command_receipts_reject(evidence, case):
    def change(r):
        commands = r['commands']
        if case == 'missing': commands.pop()
        elif case == 'duplicate': commands[-1] = commands[0]
        elif case == 'wrong-exit': commands[0]['returncode'] = 1
        elif case == 'timeout': commands[0]['timed_out'] = True
        elif case == 'no-outcome': commands[0]['expected_outcome_observed'] = False
        elif case == 'wrong-log': commands[0]['stdout_sha256'] = '0'*64
        elif case == 'string-exit': commands[0]['returncode'] = '0'
    mutate(evidence, change)
    with pytest.raises(ValueError):
        source.load_equations(evidence)


@pytest.mark.parametrize('case', ['missing-module','wrong-module-hash','wrong-gate-hash','wrong-snapshot','wrong-contract-name','extra-axiom','not-list'])
def test_contract_and_implementation_inventory_rejects(evidence, case):
    def change(r):
        if case == 'missing-module': r['module_sha256'].pop('EquationEnglish.lean')
        elif case == 'wrong-module-hash': r['module_sha256']['EquationEnglish.lean'] = '0'*64
        elif case == 'wrong-gate-hash': r['gate_sha256'] = '0'*64
        elif case == 'wrong-snapshot': r['snapshot_file_sha256'] = '0'*64
        elif case == 'wrong-contract-name':
            r['contract_axioms']['EquationEnglish']['unrelated'] = r['contract_axioms']['EquationEnglish'].pop('certify')
        elif case == 'extra-axiom': r['contract_axioms']['EquationEnglish']['certify'] = ['sorryAx']
        elif case == 'not-list': r['contract_axioms']['EquationEnglish']['certify'] = 'propext'
    mutate(evidence, change)
    with pytest.raises(ValueError):
        source.load_equations(evidence)


def test_missing_equation_evidence_stops_the_builder(tmp_path):
    output = tmp_path/'reader.html'
    with pytest.raises(ValueError):
        BUILDER.build(output, equation_evidence_root=tmp_path/'missing')
    assert not output.exists()


@pytest.mark.parametrize('module,contract', [(m,c) for m,names in gate.CONTRACTS.items() for c in names])
def test_native_gate_requires_each_contract_not_just_a_successful_process(module, contract):
    # Synthetic compiler log mutation to test the gate, not native proof evidence.
    text = (source.EVIDENCE/(module+'.log')).read_text()
    lines = [line for line in text.splitlines() if f".{contract}'" not in line]
    with pytest.raises(ValueError, match='inventory'):
        gate.checked_axioms(module, '\n'.join(lines))


def test_native_gate_refuses_execution_without_consent(tmp_path):
    output = tmp_path/'output'
    result = subprocess.run([sys.executable, str(ROOT/'scripts/check_source_equations.py'),
        '--project',str(tmp_path/'project'),'--output',str(output)],capture_output=True,text=True,timeout=15)
    assert result.returncode == 2 and '--trust-project' in result.stderr
    assert not output.exists()


@pytest.mark.parametrize('case', ['same','inside','parent','nonempty'])
def test_native_gate_preserves_existing_files_and_disallows_project_overlap(tmp_path, case):
    project = tmp_path/'project'
    project.mkdir()
    sentinel = project/'unchanged.txt'
    sentinel.write_text('unchanged')
    output = {'same': project, 'inside': project/'evidence','parent':tmp_path,
              'nonempty':tmp_path/'evidence'}[case]
    if case == 'nonempty':
        output.mkdir()
        (output/'observation.json').write_text('historical failure')
    result = subprocess.run([sys.executable,str(ROOT/'scripts/check_source_equations.py'),
        '--project',str(project),'--output',str(output),'--trust-project'],capture_output=True,text=True,timeout=15)
    assert result.returncode == 2
    assert sentinel.read_text() == 'unchanged'
    if case == 'nonempty':
        assert (output/'observation.json').read_text() == 'historical failure'
