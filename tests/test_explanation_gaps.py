"""Catalog accounting tests use synthetic snapshots, not Lean observations."""
from hashlib import sha256
import json
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from proofreader.explanation_gaps import collect, page_body, write_report
from proofreader.narrative_io import write_bundle


@pytest.fixture
def gap_catalog(tmp_path):
    site = tmp_path / 'site'
    module = 'OAI.Algebra.Example.Main'
    for name, head in [('Example.first', 'Unknown.first'), ('Example.second', 'Unknown.second')]:
        ident = sha256((module + '\0' + name).encode()).hexdigest()[:24]
        record = {'schema': 'proofreader.narrative/v1', 'theorem': name,
                  'lean_version': '4.34.1', 'axioms': [], 'statement': 'True',
                  'judgements_checked': 1, 'formula_backend': 'Lean pretty-printer',
                  'frames': [{'id': 0, 'path': [], 'statement': 'True', 'role': 'named',
                              'head': head, 'context': [], 'children': [], 'premises': [],
                              'objects': [], 'budget_cut': False}]}
        write_bundle(record, site / 'proofs' / ident, source='-- synthetic input; not compiled\n',
                     file='lean/' + module.replace('.', '/') + '.lean')
    coverage = {'proof_readings': 2, 'expected_theorem_targets': 5,
                'selected_checked_frames': 2, 'explicit_explanation_gaps': 2,
                'configurations': 1}
    (site / 'coverage.json').write_text(json.dumps(coverage))
    config = site / 'originals/ComparatorChallenges/Example.json'
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({'challenge_module': 'ComparatorChallenges.Example',
        'solution_module': module, 'theorem_names': ['Example.first', 'Example.second',
            'Example.missing1', 'Example.missing2', 'Example.missing3'], 'definition_names': []}))
    source = site / 'originals' / (module.replace('.', '/') + '.lean')
    source.parent.mkdir(parents=True)
    source.write_text('-- synthetic input; not compiled\n')
    return site


def test_gap_inventory_keeps_missing_theorems_separate(gap_catalog):
    report = collect(gap_catalog)
    assert report['proof_readings'] == report['readings_with_gaps'] == 2
    assert report['expected_theorem_targets'] == 5
    assert report['missing_theorem_readings'] == 3
    assert len(report['passages']) == sum(report['by_head'].values()) == 2
    assert sum(report['by_rule'].values()) == 2
    assert not report['english_formally_verified']
    assert not report['source_replayed_here']
    assert not report['receipts_authenticated']
    assert not report['zero_reported_gaps_implies_complete_explanation']


def test_every_gap_links_to_its_exact_step_and_source_frames(gap_catalog):
    for passage in collect(gap_catalog)['passages']:
        link = urlsplit(passage['reader_link'])
        assert not link.scheme and not link.netloc and not link.fragment
        assert (gap_catalog / link.path).is_file()
        assert parse_qs(link.query) == {'declaration': [passage['declaration_id']],
                                       'step': [passage['step_id']]}
        assert passage['source_frames'][0]['id'] == 0
        assert passage['source_frames'][0]['path'] == []
        assert passage['source_frames'][0]['head'] == passage['head']


def test_stale_reader_page_cannot_serve_a_validated_gap(gap_catalog):
    path = next((gap_catalog / 'proofs').glob('*/reader.html'))
    path.write_text(path.read_text().replace('Unknown.first', 'Invented.explanation').replace(
        'Unknown.second', 'Invented.explanation'))
    with pytest.raises(ValueError, match='reader page differs'):
        collect(gap_catalog)


@pytest.mark.parametrize('filename', ['snapshot.json', 'reading.json'])
def test_missing_bundle_file_cannot_reduce_denominator(gap_catalog, filename):
    next((gap_catalog / 'proofs').glob('*/' + filename)).unlink()
    with pytest.raises(ValueError, match='inventor|missing'):
        collect(gap_catalog)


@pytest.mark.parametrize('field,value', [('proof_readings', 1), ('selected_checked_frames', 1),
    ('explicit_explanation_gaps', 0), ('expected_theorem_targets', 1),
    ('expected_theorem_targets', True), ('explicit_explanation_gaps', -1)])
def test_inconsistent_denominators_are_rejected(gap_catalog, field, value):
    path = gap_catalog / 'coverage.json'
    record = json.loads(path.read_text()); record[field] = value
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        collect(gap_catalog)


@pytest.mark.parametrize('mutation', ['text', 'fallback', 'ownership'])
def test_modified_reading_cannot_supply_gap_inventory(gap_catalog, mutation):
    path = next((gap_catalog / 'proofs').glob('*/reading.json'))
    record = json.loads(path.read_text()); declaration = record['declarations'][0]
    if mutation == 'text':
        declaration['steps'][0]['text'] = 'An unsupported invented explanation.'
    elif mutation == 'fallback':
        declaration['steps'][0]['fallback'] = False
    else:
        declaration['axes']['frame_owners'] = {'0': 'statement'}
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='regeneration'):
        collect(gap_catalog)


def test_external_bundle_symlink_is_rejected(gap_catalog, tmp_path):
    path = next((gap_catalog / 'proofs').glob('*/reading.json'))
    outside = tmp_path / 'external.json'; outside.write_bytes(path.read_bytes())
    path.unlink(); path.symlink_to(outside)
    with pytest.raises(ValueError):
        collect(gap_catalog)


def test_wrong_module_or_directory_identity_is_rejected(gap_catalog):
    path = next((gap_catalog / 'proofs').glob('*/reading.json'))
    record = json.loads(path.read_text())
    record['declarations'][0]['file'] = 'lean/OAI/Other.lean'
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match='proof identity'):
        collect(gap_catalog)


def test_gap_page_escapes_formula_and_reference_text(gap_catalog):
    report = collect(gap_catalog)
    attack = '</td><script>alert(1)</script>'
    report['readings'][0]['theorem'] = attack
    report['readings'][0]['groups'][attack] = {'count': 1, 'reader_link': 'safe.html'}
    report['by_head'][attack] = 1
    rendered = page_body(report)
    assert '<script>' not in rendered
    assert '&lt;script&gt;' in rendered
    assert 'role="status"' in rendered


def test_report_is_deterministic(gap_catalog):
    first = write_report(gap_catalog)
    data = (gap_catalog / 'explanation-gaps.json').read_bytes()
    page = (gap_catalog / 'explanations.html').read_bytes()
    assert write_report(gap_catalog) == first
    assert (gap_catalog / 'explanation-gaps.json').read_bytes() == data
    assert (gap_catalog / 'explanations.html').read_bytes() == page
