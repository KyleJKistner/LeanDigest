"""Source-index and itinerary checks. Synthetic fixtures are not Lean evidence."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from proofreader.argument_index import ArgumentIndex, validate_index, validate_plan
from proofreader.argument_explorer import html, make_item, validate_bundle, SCHEMA
from proofreader.model import canonical_json, digest
from proofreader.narrative import Snapshot


def fixture(*, duplicate_names=False, application=False):
    """Two nested proof assumptions with a local proof reference in the body."""
    names = ['h', 'h' if duplicate_names else 'k']
    context = [{'name': names[0], 'type': 'P'}, {'name': names[1], 'type': 'P'}]
    frames = []
    for i, statement in enumerate(['P → P → P', 'P → P', 'P']):
        frame = dict(id=i, path=[1] * i, role='assume' if i < 2 else 'given',
                     head='', statement=statement, context=context[:i],
                     children=[i + 1] if i < 2 else [], premises=[], objects=[], budget_cut=False,
                     binder=names[i] if i < 2 else names[1])
        if i < 2:
            frame['domain'] = 'P'
        frames.append(frame)
    if application:
        frames[2].update(role='local-application', local_index=1, domain='P')
    return dict(schema='proofreader.narrative/v1', theorem='Synthetic.nested',
                lean_version='4.34.1', axioms=[], statement=frames[0]['statement'],
                frames=frames, judgements_checked=3, formula_backend='Lean pretty-printer')


def fact_fixture():
    """A local proved fact is absent from its own proof and present in its body."""
    base = fixture()
    root = dict(id=0, path=[], role='have', head='', statement='True', context=[],
                children=[1, 2], premises=[], objects=[], budget_cut=False,
                binder='h', domain='True')
    proof = dict(id=1, path=[1], role='named', head='True.intro', statement='True',
                 context=[], children=[], premises=[], objects=[], budget_cut=False)
    body = dict(id=2, path=[2], role='given', head='', statement='True',
                context=[{'name': 'h', 'type': 'True'}], children=[], premises=[],
                objects=[], budget_cut=False, binder='h')
    base.update(theorem='Synthetic.fact', statement='True', frames=[root, proof, body])
    return base


def bundle(record=None):
    return dict(schema=SCHEMA, title='Argument', cohort_sha256=None,
                items=[make_item(record or fixture())])


def test_scopes_use_source_occurrences_not_display_names():
    a = ArgumentIndex(fixture(duplicate_names=True)).to_dict()
    assert [n['scope'] for n in a['nodes']] == [[], [0], [0, 1]]
    assert a['nodes'][2]['reference'] == dict(status='ambiguous', basis='context-name',
                                             binder=None, candidates=[0, 1])
    assert a['summary']['ambiguous_references'] == 1
    assert all(not b['recorded_references'] for b in a['bindings'])
    validate_index(fixture(duplicate_names=True), a)


def test_explicit_local_index_disambiguates_equal_names_and_equal_types():
    record = fixture(duplicate_names=True, application=True)
    a = ArgumentIndex(record).to_dict()
    assert a['nodes'][2]['reference']['binder'] == 1
    assert a['nodes'][2]['reference']['basis'] == 'local-index'
    assert a['bindings'][1]['recorded_references'] == [2]
    assert a['bindings'][0]['recorded_references'] == []
    validate_index(record, a)


def test_missing_reference_remains_unresolved_not_guessed_by_type():
    r = fixture(); r['frames'][2]['binder'] = 'absent'
    a = ArgumentIndex(r).to_dict()
    assert a['nodes'][2]['reference']['status'] == 'unresolved'
    assert a['summary']['unresolved_references'] == 1
    validate_index(r, a)


def test_fact_is_not_available_in_its_own_proof():
    a = ArgumentIndex(fact_fixture()).to_dict()
    assert [n['scope'] for n in a['nodes']] == [[], [], [0]]
    assert a['bindings'] == [{'frame': 0, 'body': 2, 'proof': 1, 'recorded_references': [2]}]
    validate_index(fact_fixture(), a)


def test_build_and_validation_leave_inputs_unchanged():
    r = fixture(); before = deepcopy(r)
    a = ArgumentIndex(r).to_dict(); saved = deepcopy(a)
    validate_index(r, a)
    assert r == before and a == saved
    assert a == ArgumentIndex(r).to_dict()


@pytest.mark.parametrize('mutation', [
    lambda a: a.update(snapshot_sha256='0' * 64),
    lambda a: a.update(theorem='Another.theorem'),
    lambda a: a['nodes'].pop(),
    lambda a: a['nodes'][2].update(frame=True),
    lambda a: a['nodes'][2].update(scope=[1, 0]),
    lambda a: a['nodes'][2].update(scope=[0]),
    lambda a: a['nodes'][1].update(scope=[0, 1]),
    lambda a: a['nodes'][2]['reference'].update(binder=0),
    lambda a: a['nodes'][2]['reference'].update(basis='kernel-checked'),
    lambda a: a['nodes'][2].update(statement='False'),
    lambda a: a['bindings'][1].update(recorded_references=[]),
    lambda a: a['bindings'][0].update(proof=2),
    lambda a: a['summary'].update(resolved_references=0),
    lambda a: a['summary'].update(budget_cuts=False),
    lambda a: a.update(entry=0),
    lambda a: a['claims'].update(complete_hypothesis_usage=True),
    lambda a: a['claims'].update(english_certified=0),
    lambda a: a.update(extra='unchecked'),
])
def test_changed_index_rejected(mutation):
    record = fixture(); a = ArgumentIndex(record).to_dict(); mutation(a)
    with pytest.raises(ValueError):
        validate_index(record, a)


def test_ambiguous_reference_cannot_be_promoted_to_resolved():
    r = fixture(duplicate_names=True); a = ArgumentIndex(r).to_dict()
    a['nodes'][2]['reference'] = dict(status='resolved', basis='unique-context-name', binder=1, candidates=[])
    with pytest.raises(ValueError): validate_index(r, a)


def test_reading_order_can_be_reversed_without_changing_claims_or_scopes():
    r = fixture(); index = ArgumentIndex(r)
    stops = validate_plan(r, index.plan([2, 1, 0]))
    assert [s['frame'] for s in stops] == [2, 1, 0]
    assert [s['scope'] for s in stops] == [[0, 1], [0], []]
    assert [s['context'] for s in stops] == [r['frames'][i]['context'] for i in [2, 1, 0]]
    assert [s['statement'] for s in stops] == [r['frames'][i]['statement'] for i in [2, 1, 0]]


@pytest.mark.parametrize('frames', [[True], [-1], [3], ['2'], [2, 2], [0] * 1001])
def test_invalid_reading_order_rejected(frames):
    with pytest.raises(ValueError): ArgumentIndex(fixture()).plan(frames)


def test_reading_plan_cannot_supply_new_prose_or_scope():
    r = fixture(); plan = ArgumentIndex(r).plan([2]); plan['text'] = 'Therefore False.'
    with pytest.raises(ValueError): validate_plan(r, plan)
    del plan['text']; plan['context'] = []
    with pytest.raises(ValueError): validate_plan(r, plan)


def test_reading_plan_cannot_cross_proofs():
    r = fixture(); plan = ArgumentIndex(r).plan([2]); r['theorem'] = 'Different.proof'
    with pytest.raises(ValueError): validate_plan(r, plan)


def test_html_escapes_payload_and_repeats():
    r = fixture(); r['theorem'] = '</script><script>window.attacked=true</script>\u2028'
    b = bundle(r); page = html(b)
    assert '<script>window.attacked=true</script>' not in page
    assert '\\u003c/script\\u003e' in page and '\\u2028' in page
    assert page == html(b)


def test_bundle_checks_unique_identity_and_source_digest():
    b = bundle(); b['items'].append(deepcopy(b['items'][0]))
    with pytest.raises(ValueError): validate_bundle(b)
    with pytest.raises(ValueError): make_item(fixture(), dict(path='x.lean', sha256='0' * 64, source='False'))


def test_retained_bezout_source_index():
    root = Path(__file__).resolve().parents[1]
    r = Snapshot.read(root / 'artifacts/v0.3/bezout-reader/snapshot.json').record
    a = ArgumentIndex(r).to_dict(); validate_index(r, a)
    assert a['summary']['frames'] == len(r['frames'])
    assert not a['claims']['english_certified']


def test_fixed_cohort_selection_manifest():
    root = Path(__file__).resolve().parents[1]
    p = root / 'benchmarks/argument-explorer/cohort.json'
    assert digest(p.read_bytes()) == 'e73557ed76c64121bbb366d1b2d74bdd8b596b3cff8771362e1dfddb925fc2c3'
    r = json.loads(p.read_text())
    assert r['corpus_count'] == 492 and len(r['selected']) == 20
    assert r['selected'] == sorted(r['selected'], key=lambda x: (x['selection_key'], x['snapshot_sha256']))
    for row in r['selected']:
        assert row['selection_key'] == digest(r['seed'] + '\0' + row['snapshot_sha256'])


def branch_fixture():
    """Same displayed name in two independent lambda subproofs."""
    root = dict(id=0, path=[], role='combine', head='And.intro',
                statement='(P → P) ∧ (P → P)', context=[], children=[1, 3],
                premises=[dict(argument=2, frame=1, statement='P → P'),
                          dict(argument=3, frame=3, statement='P → P')],
                objects=['P → P', 'P → P'], budget_cut=False)
    frames = [root]
    for i, path in [(1, [0, 1]), (3, [1])]:
        frames.append(dict(id=i, path=path, role='assume', head='', statement='P → P',
                           context=[], children=[i+1], premises=[], objects=[],
                           budget_cut=False, binder='h', domain='P'))
        frames.append(dict(id=i+1, path=path+[1], role='given', head='', statement='P',
                           context=[{'name':'h', 'type':'P'}], children=[], premises=[],
                           objects=[], budget_cut=False, binder='h'))
    r = fixture(); r.update(theorem='Synthetic.branches', statement=root['statement'],
                            frames=frames, judgements_checked=5)
    return r


def test_same_named_hypotheses_in_different_branches_are_distinct():
    r = branch_fixture(); idx = ArgumentIndex(r); a = idx.to_dict(); validate_index(r,a)
    assert a['nodes'][2]['reference']['binder'] == 1
    assert a['nodes'][4]['reference']['binder'] == 3
    assert [s['scope'] for s in validate_plan(r,idx.plan([4,2]))] == [[3],[1]]
    a['nodes'][4]['scope'] = [1]
    with pytest.raises(ValueError,match='scope changed or escaped'): validate_index(r,a)


def test_template_markers_in_source_are_literal_data():
    r = fixture(); r['theorem'] = 'Synthetic.«@SCRIPT@ @STYLE@ @DATA@»'
    page = html(bundle(r))
    import re
    match = re.search(r'<script id="argument-data" type="application/json">(.*?)</script>', page, re.S)
    assert json.loads(match[1])['items'][0]['snapshot']['theorem'] == r['theorem']
