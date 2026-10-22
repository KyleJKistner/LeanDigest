"""Structural checks for source expressions; frozen native outputs are fixtures.

These tests do not rerun Lean. The native gate regenerates the fixtures and checks
source identity and typing in fresh compiler processes.
"""
from copy import deepcopy
import json
from zipfile import ZipFile
from pathlib import Path

import pytest

from proofreader.source_expressions import Binder, Expressions, path
from proofreader.kernel import display_name
from scripts.check_source_expressions import FIXTURES, mutations, named

HERE = Path(__file__).parent / 'fixtures/source-expressions'


def record(name='dependent'):
    with ZipFile(HERE/'records.zip') as z:
        return json.loads(json.loads(z.read('records.json'))[name+'.json'])


def snapshot(name='dependent'):
    with ZipFile(HERE/'records.zip') as z:
        return json.loads(json.loads(z.read('records.json'))[name+'.snapshot.json'])


@pytest.mark.parametrize('name', FIXTURES)
def test_native_fixture_can_be_indexed_and_bound_without_mutation(name):
    r = record(name); before = deepcopy(r); e = Expressions(r)
    binding = e.bind_snapshot(snapshot(name))
    assert binding['frames'] == len(r['frames'])
    assert not binding['native_replay_performed_here'] and not binding['english_certified']
    assert e.summary() == Expressions(r).summary()
    assert r == before
    for f in e.frames:
        assert e.dag.equal(e.close_claim(f), f['lifted_type'])


def test_dependency_closure_preserves_dependent_types_but_removes_unused_parameter():
    e = Expressions(record())
    f = e.frames[-1]
    assert f['proof_support'] == [1, 3]  # xs and i
    assert f['claim_support'] == [1, 3]
    assert f['required_context'] == [0, 1, 3]  # Fin n still needs n
    assert [display_name(f['context'][i]['name']) for i in f['required_context']] == ['n', 'xs', 'i']
    assert f['display']['lifted'] == '∀ (n : Nat) (xs : Fin n → Nat) (i : Fin n), xs i = xs i'


def test_proof_local_fact_is_not_promoted_to_an_extra_assumption():
    e = Expressions(record('hiddenDependency')); f = e.frames[-1]
    assert f['proof_support'] == [4] and f['claim_support'] == [1]
    assert f['required_context'] == [0, 1, 2, 3, 4]
    assert f['context'][-1]['kind'] == 'let' and f['context'][-1]['nondep'] is True
    root = f['lifted_type']
    for _ in range(4):
        assert e.dag.nodes[root]['tag'] == 'forall'
        root = e.dag.nodes[root]['body']
    assert e.dag.nodes[root]['tag'] == 'let'
    assert e.dag.nodes[root]['value'] is not None


def test_typeclass_dictionary_is_retained_when_the_term_uses_it():
    e = Expressions(record('implicitInstance')); f = e.frames[-1]
    assert f['required_context'] == [0, 1]
    assert f['context'][1]['binder'] == 'instance'
    assert 'Inhabited' in f['display']['lifted']


def test_unreferenced_local_definitions_are_not_mandatory_parameters():
    f = Expressions(record('localDefinitions')).frames[-1]
    assert f['required_context'] == []
    assert f['display']['lifted'] == 'True'


def test_same_proposition_does_not_make_two_source_hypotheses_identical():
    e = Expressions(record('twoProofs')); f = e.frames[-1]
    assert f['reference'] == 2
    assert e.context_uses(f['context'][1]['type'],1) == [0]
    assert e.context_uses(f['context'][2]['type'],2) == [0]
    assert f['context'][1]['path'] != f['context'][2]['path']
    assert f['required_context'] == [0, 2]


def test_same_dag_row_under_two_quantifiers_does_not_make_same_binder():
    e = Expressions(record('sharedBinderNodes')); root = e.frames[0]['type']
    _, args = e.dag.app(root)
    assert args[0] == args[1]  # Identical quantified propositions are interned.
    left = e.resolve_variable(0, root, [0, 1, 1, 1])
    right = e.resolve_variable(0, root, [1, 1, 1])
    assert left != right
    assert left.owner == right.owner
    assert left.path == (0, 1) and right.path == (1,)


def test_source_variable_inside_a_dependent_context_type_resolves_to_origin():
    e = Expressions(record()); f = e.frames[-1]
    # i : Fin n. The argument n is a loose de Bruijn variable in a prefix of
    # the source context, not a variable named by a string substitution.
    typ = f['context'][3]['type']
    identity = e.resolve_variable(len(e.frames)-1, typ, [1], owner='context:3:type', context_size=3)
    assert identity == Binder(e.sha256, 'source', tuple(f['context'][0]['path']))


def test_binding_identity_is_scoped_to_its_bundle():
    a = Expressions(record('sharedBinderNodes'))
    changed = record('sharedBinderNodes'); changed['lean_version'] = 'fixture-only-other-environment'
    b = Expressions(changed)
    assert a.resolve_variable(0,a.frames[0]['type'],[1,1,1]) != b.resolve_variable(0,b.frames[0]['type'],[1,1,1])


def test_occurrence_must_end_at_an_in_scope_variable():
    e = Expressions(record())
    with pytest.raises(ValueError): e.resolve_variable(0,e.statement,[])
    with pytest.raises(ValueError): e.resolve_variable(0,e.statement,[2])
    with pytest.raises(ValueError): e.resolve_variable(True,e.statement,[])


def test_generic_claim_shapes_are_constructor_based():
    assert Expressions(record('sharedBinderNodes')).claim_shape(0)['kind'] == 'and'
    e = Expressions(record('witness'))
    assert any(e.claim_shape(i)['kind']=='exists' for i in range(len(e.frames)))
    assert Expressions(record()).claim_shape(len(record()['frames'])-1)['kind'] == 'eq'
    # A similarly named arbitrary predicate is not the built-in conjunction.
    changed=record('sharedBinderNodes')
    for node in changed['exprs']:
        if node['tag']=='const' and node['name']==named('And'):
            node['name']=named('Other.And')
    assert Expressions(changed).claim_shape(0)['kind']=='atom'


def test_application_keeps_proof_arguments_and_data_arguments_separate():
    e=Expressions(record('witness'))
    i=next(i for i,f in enumerate(e.frames) if f['application'])
    view=e.inference(i)
    assert view['kind']=='application'
    assert view['head']['constant']==named('Exists.intro')
    assert len(view['objects'])==3 and len(view['premises'])==1
    before=deepcopy(e.record)
    view['premises'][0]['path'].append(2)
    view['head']['constant']['value']='wrong'
    assert e.record==before


def test_reference_and_nonapplication_inferences_are_not_invented_applications():
    e=Expressions(record('twoProofs'))
    assert e.inference(0)['kind']=='source'
    assert e.inference(len(e.frames)-1)['kind']=='reference'


def test_sibling_binders_keep_their_strict_names():
    e=Expressions(record('siblingNames'))
    # Default Lean Expr equality ignores binder labels. The new native encoder
    # must not replace an h binder with an alpha-equivalent anonymous binder.
    for f in e.frames:
        assert e.dag.equal(e.close_claim(f),f['lifted_type'])
    bound=[c for f in e.frames for c in f['context']]
    assert any(display_name(c['name'])=='h' for c in bound)


@pytest.mark.parametrize('bad', [[True],[-1],[3],['1'],[0]*513])
def test_bad_paths_rejected(bad):
    with pytest.raises(ValueError): path(bad)


@pytest.mark.parametrize('mutation', [
    lambda r:r.update(extra='unchecked'),
    lambda r:r.update(schema='unknown'),
    lambda r:r.update(axioms=['sorryAx']),
    lambda r:r.update(axioms=['propext','propext']),
    lambda r:r.update(frames=[]),
    lambda r:r['frames'].append(deepcopy(r['frames'][0])),
    lambda r:r['frames'][-1].update(reference=True),
    lambda r:r['frames'][-1].update(required_context=[]),
    lambda r:r['frames'][-1].update(proof_support=[True]),
    lambda r:r['frames'][-1].update(claim_support=[]),
    lambda r:r['frames'][-1]['context'][-1].update(path=[]),
    lambda r:r['frames'][-1]['context'][-1].update(type=r['statement']),
    lambda r:r['frames'][-1]['context'][-1].update(value=0),
    lambda r:r['frames'][-1].update(lifted_type=r['statement']),
    lambda r:r['exprs'][0].update(extra='unchecked'),
    lambda r:r['exprs'].append({'tag':'app','fn':999999,'arg':0}),
])
def test_structurally_invalid_record_rejected(mutation):
    r=record('twoProofs');mutation(r)
    with pytest.raises(ValueError):Expressions(r)


def test_python_does_not_claim_to_check_truth_or_source_typing():
    r=record('twoProofs')
    # Unsupported display text is caught by native replay, not by a text parser.
    r['frames'][-1]['display']['claim']='False'
    e=Expressions(r)
    assert e.summary()['english_certified'] is False
    assert e.summary()['native_replay_performed_here'] is False


def test_snapshot_source_paths_and_scope_ids_must_match():
    e=Expressions(record())
    s=snapshot();s['theorem']='Other.theorem'
    with pytest.raises(ValueError,match='declaration mismatch'):e.bind_snapshot(s)
    s=snapshot();s['lean_version']='4.33.0'
    with pytest.raises(ValueError,match='version mismatch'):e.bind_snapshot(s)


def test_snapshot_display_is_not_used_as_variable_identity():
    e=Expressions(record())
    s=snapshot();s['frames'][-1]['statement']='different display'
    # Snapshot's own consistency may constrain some statements. This leaf has
    # a source-bound type; this bridge alone must not promote text to semantics.
    try:
        result=e.bind_snapshot(s)
    except ValueError:
        return
    assert len(e.frames)-1 in result['display_differences']
    assert result['native_replay_performed_here'] is False


@pytest.mark.parametrize('old,kept,depth', [(-1,(),0),(3,(-1,),0),(3,(True,),0),(3,(3,),0),
                                         (3,(1,0),0),(3,(1,1),0),(3,(),513)])
def test_invalid_restriction_rejected(old,kept,depth):
    e=Expressions(record())
    with pytest.raises(ValueError):e.reindex(e.statement,old,kept,depth)


def test_removing_a_used_context_variable_rejected():
    e=Expressions(record()); f=e.frames[-1]
    with pytest.raises(ValueError,match='removed context variable'):
        e.reindex(f['type'],len(f['context']),())


def test_declared_root_type_has_not_been_replaced_by_inference():
    # A real library example is checked in the native gate: Nat.mul_zero's
    # proof body infers n*0=n*0, while its declaration is n*0=0.
    for name in FIXTURES:
        e=Expressions(record(name))
        assert e.frames[0]['path']==[]
        assert e.dag.equal(e.statement,e.frames[0]['type'])


def test_native_mutation_inventory_is_unique_and_does_not_mutate_inputs():
    records={'SourceExpressionsFixtures.'+n:record(n) for n in FIXTURES}
    saved=deepcopy(records);tests=mutations(records)
    assert len(tests)==35 and len({t[0] for t in tests})==35
    assert records==saved
    for label,target,changed,error in tests:
        assert changed!=records[target] and error


def test_shadowed_name_still_selects_the_original_outer_proof():
    e=Expressions(record('shadow'));f=e.frames[-1]
    assert display_name(f['context'][2]['name'])==display_name(f['context'][3]['name'])=='h'
    assert f['reference']==2 and f['required_context']==[0,2]
    assert f['context'][2]['path']!=f['context'][3]['path']
