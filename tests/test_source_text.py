"""Static evidence and presentation tests, not replacements for Lean replay."""
from __future__ import annotations

import copy
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from proofreader import source_text as source

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('source_text_builder', ROOT / 'docs/companion/build.py')
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


@pytest.fixture
def evidence(tmp_path):
    return Path(shutil.copytree(source.EVIDENCE, tmp_path / 'text-evidence'))


def mutate(path, change):
    report_path = path / 'observation.json'
    data = json.loads(report_path.read_text())
    change(data)
    report_path.write_text(json.dumps(data))


class Sentences(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.sentences = []
        self.frames = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'details' and attrs.get('class') == 'checked-cancellation':
            self.frames.append(int(attrs['data-source-frame']))
        if tag == 'p' and attrs.get('class') == 'checked-sentence':
            self.active = True
            self.sentences.append('')

    def handle_data(self, data):
        if self.active:
            self.sentences[-1] += data

    def handle_endtag(self, tag):
        if tag == 'p':
            self.active = False


def test_loaded_source_sentences_match_native_bytes_and_original_occurrences():
    result = source.load_cancellations()
    report, records = result['observation'], result['sentences']
    assert len(records) == 2
    assert report['source_frames'] == [40, 53]
    assert report['certified_sentence_count'] == 2
    assert len(report['contract_axioms']) == 9
    assert all(set(a) <= {'propext', 'Classical.choice', 'Quot.sound'}
               for a in report['contract_axioms'].values())
    paths = json.loads((ROOT / 'docs/companion/cancellation-paths.json').read_text())
    snapshot = json.loads((ROOT / 'artifacts/companion/native/current/snapshot.json').read_text())
    for i, frame in enumerate([40, 53]):
        assert records[i]['path'] == paths[i] == snapshot['frames'][frame]['path']
        assert records[i]['source_ast_identity_checked'] is True
        assert records[i]['literal_string_kernel_checked'] is True
        assert bytes(records[i]['utf8']) == records[i]['text'].encode('utf-8')
        assert bytes(records[i]['utf8']) == (source.EVIDENCE / f'cancellation-{i}.txt').read_bytes()
        assert 'hg' in {c['name'] for c in records[i]['context']}


def test_page_embeds_only_the_two_checked_sentences_and_preserves_scope(tmp_path):
    path = tmp_path / 'index.html'
    manifest = BUILDER.build(path)
    parser = Sentences()
    parser.feed(path.read_text())
    records = source.load_cancellations()['sentences']
    assert parser.frames == [40, 53]
    assert parser.sentences == [r['text'] for r in records]
    assert manifest['certified_source_sentences'] == 14
    assert manifest['certified_cancellation_sentences'] == 2
    assert manifest['curated_prose_formally_verified'] is False
    assert manifest['source_text_record_sha256'] == source.RECORD_HASH
    assert '__CANCELLATION_' not in path.read_text()


def test_panel_escapes_text_without_rewriting_it():
    # Synthetic escaping example, not a native certificate.
    text = 'Since <x> & "y" are labels, do not interpret <script> as HTML.'
    panel = source.cancellation_panel({'text': text}, 40)
    assert '<script>' not in panel and '&lt;script&gt;' in panel
    parser = Sentences()
    parser.feed(panel)
    assert parser.sentences == [text]


@pytest.mark.parametrize('key,value', [
    ('status', 'failed'), ('schema', 'other/v1'), ('theorem', 'Unrelated.theorem'),
    ('source_sha256', '0' * 64), ('certified_sentence_count', 86),
    ('certified_sentence_count', 2.0), ('native_negative_cases', 11),
    ('native_parser_guards', 31), ('repeat_byte_identical', 'true'),
])
def test_incomplete_observation_rejects(evidence, key, value):
    mutate(evidence, lambda data: data.update({key: value}))
    with pytest.raises(ValueError):
        source.load_cancellations(evidence)


@pytest.mark.parametrize('flag', ['complete_english_proof_certified', 'original_project_replayed',
                                  'receipt_authenticated', 'html_semantics_proved'])
@pytest.mark.parametrize('value', [True, 'false', None])
def test_component_result_cannot_promote_the_whole_reader(evidence, flag, value):
    mutate(evidence, lambda data: data.update({flag: value}))
    with pytest.raises(ValueError, match='scope'):
        source.load_cancellations(evidence)


@pytest.mark.parametrize('content', ['[]', 'null', '"passed"', '{', '{"status":"passed","status":"failed"}'])
def test_malformed_observation_rejects(evidence, content):
    (evidence / 'observation.json').write_text(content)
    with pytest.raises(ValueError):
        source.load_cancellations(evidence)


@pytest.mark.parametrize('name', ['positive.json', 'cancellation-0.txt', 'repeat.log'])
def test_missing_or_changed_files_reject(evidence, name):
    path = evidence / name
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(ValueError, match='Changed source-text evidence'):
        source.load_cancellations(evidence)
    path.unlink()
    with pytest.raises(ValueError):
        source.load_cancellations(evidence)


def test_rehashing_an_altered_native_record_does_not_authorize_it(evidence):
    records = json.loads((evidence / 'positive.json').read_text())
    records[0]['text'] = 'Since g is zero, cancel g to obtain 0 = 1.'
    records[0]['utf8'] = list(records[0]['text'].encode('utf-8'))
    for name in ['positive.json', 'repeat.json']:
        (evidence / name).write_text(json.dumps(records))
    (evidence / 'cancellation-0.txt').write_text(records[0]['text'])
    mutate(evidence, lambda data: data['files_sha256'].update(
        {name: source.digest(evidence / name) for name in ['positive.json', 'repeat.json', 'cancellation-0.txt']}))
    with pytest.raises(ValueError, match='Reviewed source-text record changed'):
        source.load_cancellations(evidence)


def test_rehashing_an_altered_text_file_does_not_authorize_it(evidence):
    name = 'cancellation-1.txt'
    (evidence / name).write_text('Different text')
    mutate(evidence, lambda data: data['files_sha256'].update({name: source.digest(evidence / name)}))
    with pytest.raises(ValueError, match='certified bytes'):
        source.load_cancellations(evidence)


@pytest.mark.parametrize('bad_path', ['../escape', '/absolute', 'folder/file', '.', '..', 'folder\\file'])
def test_unsafe_evidence_path_rejects(evidence, bad_path):
    mutate(evidence, lambda data: data['files_sha256'].update({bad_path: '0' * 64}))
    with pytest.raises(ValueError, match='evidence path'):
        source.load_cancellations(evidence)


@pytest.mark.parametrize('name', ['observation.json', 'positive.json'])
def test_symlinks_are_not_accepted_as_retained_files(evidence, tmp_path, name):
    member = evidence / name
    destination = tmp_path / ('actual-' + name)
    member.rename(destination)
    member.symlink_to(destination)
    with pytest.raises(ValueError):
        source.load_cancellations(evidence)


@pytest.mark.parametrize('which', ['module', 'gate', 'missing-module', 'mathlib'])
def test_stale_code_or_environment_identity_rejects(evidence, which):
    def change(data):
        if which == 'module':
            data['module_sha256']['ArithmeticEnglish.lean'] = '0' * 64
        elif which == 'gate':
            data['gate_sha256'] = '0' * 64
        elif which == 'missing-module':
            data['module_sha256'].pop('SourceCancellation.lean')
        else:
            data['environment']['mathlib_commit'] = '0' * 40
    mutate(evidence, change)
    with pytest.raises(ValueError):
        source.load_cancellations(evidence)


@pytest.mark.parametrize('which', ['missing', 'duplicate', 'timeout', 'positive-fails', 'negative-passes', 'truthy', 'log'])
def test_failed_native_controls_cannot_keep_the_page_label(evidence, which):
    def change(data):
        commands = data['commands']
        if which == 'missing':
            commands.pop()
        elif which == 'duplicate':
            commands[-1] = copy.deepcopy(commands[0])
        elif which == 'timeout':
            commands[-1]['timed_out'] = True
        elif which == 'positive-fails':
            commands[0]['returncode'] = 1
        elif which == 'negative-passes':
            commands[-1]['returncode'] = 0
        elif which == 'truthy':
            commands[0]['expected_outcome_observed'] = 'true'
        elif which == 'log':
            commands[0]['stdout_sha256'] = '0' * 64
    mutate(evidence, change)
    with pytest.raises(ValueError):
        source.load_cancellations(evidence)


def test_builder_refuses_missing_text_evidence_without_writing_page(tmp_path):
    output = tmp_path / 'index.html'
    with pytest.raises(ValueError):
        BUILDER.build(output, text_evidence_root=tmp_path / 'missing')
    assert not output.exists()
