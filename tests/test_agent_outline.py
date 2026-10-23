"""Outline protocol tests. Fixture observations are not fresh Lean checks."""
from copy import deepcopy
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from proofreader import outline as o
from proofreader.model import canonical_json, digest
from proofreader.proof_decomposition import frontier
from proofreader.source_expressions import Expressions

FIXTURES = Path(__file__).parent / 'fixtures/source-expressions/records.zip'


def record(name='dependent', snapshot=False):
    with ZipFile(FIXTURES) as archive:
        return json.loads(json.loads(archive.read('records.json'))[name + ('.snapshot.json' if snapshot else '.json')])


def block(i, key=None, children=None):
    return {'id': key or 'step-' + str(i), 'frame': i, 'title': 'Claim',
            'text': 'Commentary.', 'children': children or []}


def proposal(r=None):
    r = r or record()
    return {'schema': o.SCHEMA, 'source_sha256': Expressions(r).sha256, 'parent': None,
            'title': 'Proof', 'introduction': '', 'blocks': [block(len(r['frames']) - 1)]}


def nested():
    r = record()
    pairs = [(i, j) for i, f in enumerate(r['frames']) for j, g in enumerate(r['frames'])
             if f['path'] and len(g['path']) > len(f['path']) and g['path'][:len(f['path'])] == f['path']]
    i, j = pairs[0]
    p = proposal(r); p['blocks'] = [block(i, 'outer')]
    return r, p, block(j, 'inner')


def test_nested_outline_extracts_inner_first_and_preserves_input():
    r, p, child = nested(); old = deepcopy(p)
    expanded = o.expand(r, p, 'outer', [child])
    assert p == old
    assert o.validate_proposal(r, expanded) == [child['frame'], p['blocks'][0]['frame']]
    assert o.delta(p, expanded) == {'added': ['inner'], 'removed': [], 'changed': [],
                                    'expanded': ['outer'], 'unchanged': []}


def test_expansion_cannot_drop_or_change_existing_parent():
    r, p, child = nested()
    expanded = o.expand(r, p, 'outer', [child])
    assert {k: v for k, v in expanded['blocks'][0].items() if k != 'children'} == {
        k: v for k, v in p['blocks'][0].items() if k != 'children'}
    with pytest.raises(ValueError, match='already expanded'): o.expand(r, expanded, 'outer', [])
    with pytest.raises(ValueError, match='Unknown'): o.expand(r, p, 'other', [])


@pytest.mark.parametrize('mutation', [
    lambda p: p.update(source_sha256='0' * 64),
    lambda p: p.update(parent='not-a-revision'),
    lambda p: p.update(title=''),
    lambda p: p.update(title='a\nb'),
    lambda p: p.update(title='a' * 201),
    lambda p: p.update(introduction=4),
    lambda p: p.update(introduction='a' * 20001),
    lambda p: p.update(blocks={}),
    lambda p: p['blocks'][0].update(frame=True),
    lambda p: p['blocks'][0].update(frame=0),
    lambda p: p['blocks'][0].update(frame=-1),
    lambda p: p['blocks'][0].update(frame=100000),
    lambda p: p['blocks'][0].update(id='../escape'),
    lambda p: p['blocks'][0].update(title='a\nb'),
    lambda p: p['blocks'][0].update(text='x' * 20001),
    lambda p: p['blocks'][0].update(children={}),
    lambda p: p['blocks'].append(deepcopy(p['blocks'][0])),
])
def test_invalid_proposal_is_rejected(mutation):
    p = proposal(); mutation(p)
    with pytest.raises(ValueError): o.validate_proposal(record(), p)


@pytest.mark.parametrize('field', ['claim', 'scope', 'proof', 'axioms', 'hypotheses', 'result'])
def test_proposals_cannot_override_mathematics(field):
    p = proposal(); p['blocks'][0][field] = 'False'
    with pytest.raises(ValueError): o.validate_proposal(record(), p)


def test_scope_containment_not_display_name():
    r = record('branches'); p = proposal(r)
    paths = [f['path'] for f in r['frames']]
    a, b = next((i, j) for i in range(1, len(paths)) for j in range(i+1, len(paths))
                if paths[i][:len(paths[j])] != paths[j] and paths[j][:len(paths[i])] != paths[i])
    p['blocks'] = [block(a, children=[block(b)])]
    with pytest.raises(ValueError, match='escapes'): o.validate_proposal(r, p)
    p['blocks'] = [block(b), block(a)]
    assert o.validate_proposal(r, p) == [b, a]


def test_source_containment_cannot_be_flattened_into_siblings():
    r, p, child = nested(); p['blocks'].append(child)
    with pytest.raises(ValueError, match='must be nested'): o.validate_proposal(r, p)


def test_commentary_is_not_mistaken_for_a_formal_claim():
    p = proposal(); p['blocks'][0]['text'] = 'This is unchecked commentary, even if mathematically wrong.'
    assert o.validate_proposal(record(), p)


def test_empty_outline_is_an_explicit_empty_selection():
    p = proposal(); p['blocks'] = []
    assert o.validate_proposal(record(), p) == []


@pytest.mark.parametrize('name', ['A; quit', '../A', 'A\nimport Evil', '', '2bad', 'A..B'])
def test_names_cannot_inject_lean(name):
    with pytest.raises(ValueError): o.named(name)


def test_names_use_the_existing_wire_format():
    assert o.named('A.b') == {'tag': 'str', 'prefix': {'tag': 'str', 'prefix': {'tag': 'anonymous'}, 'value': 'A'}, 'value': 'b'}


def test_lock_rejects_concurrent_updates_and_cleans_up(tmp_path):
    with o.lock(tmp_path):
        with pytest.raises(ValueError, match='holds'):
            with o.lock(tmp_path): pass
    assert not (tmp_path / '.lock').exists()
    with pytest.raises(RuntimeError):
        with o.lock(tmp_path): raise RuntimeError()
    assert not (tmp_path / '.lock').exists()


def test_consent_precedes_compiler_and_session_creation(tmp_path):
    target = tmp_path / 'no-session'
    with pytest.raises(ValueError, match='trust-project'):
        o.start(target, 'missing-lean', 'Init', 'And.comm', [], False)
    assert not target.exists()


def test_atomic_state_write_preserves_content(tmp_path):
    path = tmp_path / 'state.json'; o.atomic(path, {'head': 'x'})
    assert o.read(path) == {'head': 'x'}
    assert list(tmp_path.iterdir()) == [path]


def test_duplicate_json_keys_rejected(tmp_path):
    p = tmp_path / 'input.json'; p.write_text('{"frames":[],"frames":[1]}')
    with pytest.raises(ValueError): o.read(p)


def test_compiled_environment_changes_and_missing_modules_detected(tmp_path):
    p = tmp_path / 'Example.olean'; p.write_bytes(b'fixture-not-a-real-olean')
    initial = o.environment_files([str(p)])
    p.with_suffix('.olean.private').write_bytes(b'changed')
    assert o.environment_files([str(p)]) != initial
    p.unlink()
    with pytest.raises(ValueError): o.environment_files([str(p)])


def test_rejection_cli_emits_json_not_traceback(capsys, tmp_path):
    assert o.main(['open', '--lean', 'missing', '--module', 'Init', '--declaration', 'And.comm',
                   '--session', str(tmp_path/'new')]) == 1
    result = json.loads(capsys.readouterr().err)
    assert result['status'] == 'rejected' and '--trust-project' in result['error']


def fake_session(path):
    """Saved structure fixture only; it does not claim a compiler has run."""
    r = record(); s = record(snapshot=True)
    o.write(path/'source.json', r); o.write(path/'snapshot.json', s)
    state = {'schema': o.SCHEMA, 'source_sha256': Expressions(r).sha256,
             'snapshot_sha256': o.sha(path/'snapshot.json'), 'target': r['name'], 'head': None}
    o.write(path/'state.json', state)
    return r, state


def test_stale_parent_rejected_before_native_run(tmp_path):
    r, state = fake_session(tmp_path)
    p = proposal(r); p['parent'] = '1' * 64
    with pytest.raises(ValueError, match='Stale'): o.check(tmp_path, p, True)
    assert o.read(tmp_path/'state.json') == state


def test_session_mutation_fails_loading(tmp_path):
    r, _ = fake_session(tmp_path)
    r['frames'][-1]['display']['claim'] = 'False'; o.write(tmp_path/'source.json', r)
    with pytest.raises(ValueError, match='source changed'): o.load(tmp_path)


def test_revision_hash_detects_edited_commentary(tmp_path):
    (tmp_path/'revisions').mkdir()
    item = {'proposal': proposal(), 'result': {}}
    key = digest(canonical_json(item)); item['proposal']['introduction'] = 'changed'
    o.write(tmp_path/'revisions'/(key+'.json'), item)
    with pytest.raises(ValueError, match='content changed'): o.revision(tmp_path, key)
