"""Renderer contracts plus existing retained OpenAI observations.

The small records built here are synthetic format fixtures, never claimed as
Lean execution or independently checked proofs. The final tests read unchanged
snapshots already retained in artifacts/pinned-openai-slice.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from proofreader.kernel import InvalidExport
from proofreader.model import walk_steps
from proofreader.narrative import Narrative, check_reading, prose


def given(name, statement):
    return dict(role='given', head='', binder=name, statement=statement)


def application(head, objects, premises, statement):
    return dict(role='application', head=head, objects=objects, arguments=premises,
                statement=statement)


def assume(name, domain, body, *, role='assume'):
    statement = ('∀ (' + name + ' : ' + domain + '), ' + body['statement']
                 if role == 'introduce' else '(' + domain + ') → ' + body['statement'])
    return dict(role=role, head='', binder=name, domain=domain, body=body, statement=statement)


def record(node, hypotheses=()):
    for name, domain in reversed(list(hypotheses)):
        node = assume(name, domain, node)
    for name in ('R', 'Q', 'P'):
        node = assume(name, 'Prop', node, role='introduce')
    frames = []

    def visit(node, path, context):
        i = len(frames)
        frame = dict(id=i, path=path, role=node['role'], head=node['head'],
                     statement=node['statement'], context=deepcopy(context),
                     children=[], premises=[], objects=list(node.get('objects', [])), budget_cut=False)
        frames.append(frame)
        for key in ('binder', 'domain'):
            if key in node:
                frame[key] = node[key]
        if 'body' in node:
            child = visit(node['body'], path+[1], context+[dict(name=node['binder'], type=node['domain'])])
            frame['children'].append(child)
        else:
            arguments = node.get('arguments', [])
            arity = len(frame['objects']) + len(arguments)
            for slot, child_node in arguments:
                child = visit(child_node, path+[0]*(arity-slot-1)+[1], context)
                frame['children'].append(child)
                frame['premises'].append(dict(argument=slot, frame=child, statement=child_node['statement']))
        return i

    visit(node, [], [])
    return dict(schema='proofreader.narrative/v1', theorem='Synthetic.logicalExplanation',
                lean_version='4.34.1', axioms=[], statement=frames[0]['statement'], frames=frames,
                judgements_checked=len(frames), formula_backend='Lean pretty-printer')


CASES = [
    ('Iff.mpr', ['P', 'Q'], [(2, 'P ↔ Q'), (3, 'Q')], 'P', 'equivalence-reverse'),
    ('Iff.intro', ['P', 'Q'], [(2, 'P → Q'), (3, 'Q → P')], 'P ↔ Q', 'equivalence-introduction'),
    ('Or.inl', ['P', 'Q'], [(2, 'P')], 'P ∨ Q', 'disjunction-introduction'),
    ('Or.inr', ['P', 'Q'], [(2, 'Q')], 'P ∨ Q', 'disjunction-introduction'),
    ('False.elim', ['P'], [(1, 'False')], 'P', 'false-elimination'),
    ('Not.intro', ['P'], [(1, 'P → False')], '¬P', 'negation-introduction'),
    ('Decidable.byContradiction', ['P', 'Classical.propDecidable P'], [(2, '¬P → False')], 'P', 'contradiction-proof'),
    ('Classical.byContradiction', ['P'], [(1, '¬P → False')], 'P', 'contradiction-proof'),
    ('Not.elim', ['P'], [(1, '¬P'), (2, 'P')], 'False', 'negation-elimination'),
    ('absurd', ['P', 'Q'], [(2, 'P'), (3, '¬P')], 'Q', 'contradiction-elimination'),
    ('And.left', ['P', 'Q'], [(2, 'P ∧ Q')], 'P', 'conjunction-projection'),
    ('And.right', ['P', 'Q'], [(2, 'P ∧ Q')], 'Q', 'conjunction-projection'),
]


def case_record(case):
    head, objects, premises, statement, _ = case
    hypotheses = [('h'+str(index), typ) for index, (_, typ) in enumerate(premises)]
    arguments = [(slot, given('h'+str(index), typ)) for index, (slot, typ) in enumerate(premises)]
    return record(application(head, objects, arguments, statement), hypotheses)


def target_frame(r, head):
    return next(f for f in r['frames'] if f['head'] == head)


def own_step(narrative, document, frame):
    return next(s for s in walk_steps(document.declarations[0].steps)
                if s.id == narrative.owners[frame['id']])


@pytest.mark.parametrize('case', CASES, ids=[c[0] for c in CASES])
def test_guarded_rules_have_explicit_source_ownership(case):
    r = case_record(case)
    n = Narrative(r)
    d = n.document()
    step = own_step(n, d, target_frame(r, case[0]))
    assert step.rule == case[-1]
    assert not step.fallback
    assert set(n.owners) == set(range(len(r['frames'])))
    assert not any(s.fallback for s in walk_steps(d.declarations[0].steps))
    assert d.provenance['english_formally_verified'] is False
    assert d.provenance['receipt_authenticated'] is False
    check_reading(r, d)
    step.text = 'This altered mathematical explanation was not regenerated.'
    with pytest.raises(InvalidExport):
        check_reading(r, d)


@pytest.mark.parametrize('case', CASES, ids=[c[0] for c in CASES])
@pytest.mark.parametrize('mutation', ['object', 'slot', 'path', 'goal', 'cut'])
def test_rule_rejects_altered_shape_or_type_without_dropping_frames(case, mutation):
    r = case_record(case)
    frame = target_frame(r, case[0])
    if mutation == 'object':
        frame['objects'].append('extra')
    elif mutation == 'slot':
        frame['premises'][-1]['argument'] += 1
    elif mutation == 'path':
        child = r['frames'][frame['children'][0]]
        child['path'] = frame['path']+[2, 1]
    elif mutation == 'goal':
        frame['statement'] = 'R'
    elif mutation == 'cut':
        frame['budget_cut'] = True
    n = Narrative(r)
    d = n.document()
    assert own_step(n, d, frame).fallback
    assert set(n.owners) == set(range(len(r['frames'])))


def test_application_context_is_checked_before_rendering():
    r = case_record(CASES[0])
    frame = target_frame(r, 'Iff.mpr')
    r['frames'][frame['children'][0]]['context'].append(dict(name='escaped', type='False'))
    with pytest.raises(InvalidExport, match='context'):
        Narrative(r)


def test_unknown_and_budget_cut_premises_remain_visible():
    r = case_record(CASES[0])
    frame = target_frame(r, 'Iff.mpr')
    first = r['frames'][frame['children'][0]]
    first.update(role='application', head='Synthetic.unexpanded_equivalence')
    first.pop('binder')
    r['frames'][frame['children'][1]]['budget_cut'] = True
    n = Narrative(r)
    d = n.document()
    assert own_step(n, d, frame).rule == 'equivalence-reverse'
    gaps = [s for s in walk_steps(d.declarations[0].steps) if s.fallback]
    assert len(gaps) == 2
    assert prose(d).count('[Explanation gap]') == 2
    assert 'not formally verified' in prose(d)
    assert 'does not authenticate' in prose(d)


def test_equivalence_directions_do_not_share_assumption_scope():
    left = assume('left_h', 'P', given('left_h', 'P'))
    right = assume('right_h', 'P', given('right_h', 'P'))
    r = record(application('Iff.intro', ['P', 'P'], [(2, left), (3, right)], 'P ↔ P'))
    n = Narrative(r)
    d = n.document()
    step = own_step(n, d, target_frame(r, 'Iff.intro'))
    assert step.rule == 'equivalence-introduction'
    assert len(step.children) == 2
    forward, backward = step.children
    assert forward.text == 'Forward direction: assume P.'
    assert backward.text == 'Reverse direction: assume P.'
    assert len(forward.children) == len(backward.children) == 1
    assert forward.children[0].context[-1]['name'] == 'left_h'
    assert backward.children[0].context[-1]['name'] == 'right_h'
    assert all(c['name'] != 'left_h' for c in backward.children[0].context)
    assert set(n.owners) == set(range(len(r['frames'])))


@pytest.mark.parametrize('fault', ['domain', 'body'])
def test_assumption_and_body_types_are_checked_for_directions(fault):
    left = assume('left_h', 'P', given('left_h', 'P'))
    right = assume('right_h', 'P', given('right_h', 'P'))
    if fault == 'domain':
        left['domain'] = 'Q'
    else:
        left['body']['statement'] = 'Q'
    r = record(application('Iff.intro', ['P', 'P'], [(2, left), (3, right)], 'P ↔ P'))
    n = Narrative(r)
    d = n.document()
    assert own_step(n, d, target_frame(r, 'Iff.intro')).fallback


@pytest.mark.parametrize('antecedent', ['P ∧ Q', 'P ∨ Q', 'P → Q', 'P ↔ Q'])
def test_parentheses_preserve_the_scope_of_negation(antecedent):
    goal = '¬(' + antecedent + ')'
    r = record(application('Not.intro', [antecedent], [(1, given('h', '('+antecedent+') → False'))], goal),
               [('h', '('+antecedent+') → False')])
    n = Narrative(r)
    assert own_step(n, n.document(), target_frame(r, 'Not.intro')).rule == 'negation-introduction'


@pytest.mark.parametrize('goal,antecedent', [
    ('¬P ∧ Q', 'P ∧ Q'), ('¬P ∨ Q', 'P ∨ Q'), ('¬P → Q', 'P → Q'),
    ('¬P ↔ Q', 'P ↔ Q'), ('¬P∧Q', 'P∧Q'), ('¬P ∧Q', 'P ∧Q'), ('¬P→Q', 'P→Q'),
    ('¬∀ n : Nat, n = n', '∀ n : Nat, n = n'),
])
def test_negation_never_steals_a_connective_or_binder_body(goal, antecedent):
    r = record(application('Not.intro', [antecedent], [(1, given('h', '¬('+antecedent+')'))], goal),
               [('h', '¬('+antecedent+')')])
    n = Narrative(r)
    assert own_step(n, n.document(), target_frame(r, 'Not.intro')).fallback


def test_parenthesized_quantifier_can_be_a_conjunction_component():
    prop = '∀ n : Nat, n = n'
    conjunction = '('+prop+') ∧ Q'
    r = record(application('And.left', [prop, 'Q'], [(2, given('h', conjunction))], prop), [('h', conjunction)])
    n = Narrative(r)
    assert own_step(n, n.document(), target_frame(r, 'And.left')).rule == 'conjunction-projection'


@pytest.mark.parametrize('statement', [
    '∀ n : Nat, n = n ∧ Q', 'let x := P; x ∧ Q', 'if P then P ∧ Q else Q',
    'P ∧ Q → R', '¬(P ∧ Q)', 'P ∨ Q', '(P ∧ Q', 'P ∧ Q)',
])
def test_projection_requires_an_outer_conjunction(statement):
    r = record(application('And.left', ['P', 'Q'], [(2, given('h', statement))], 'P'), [('h', statement)])
    n = Narrative(r)
    assert own_step(n, n.document(), target_frame(r, 'And.left')).fallback


def test_long_grouping_and_quoted_formulas_stay_outside_the_display_grammar():
    for prop in ['('*65+'P'+')'*65, '"x  y" = "x y"', '«P Q»']:
        r = record(application('Or.inl', [prop, 'Q'], [(2, given('h', prop))], '('+prop+') ∨ Q'), [('h', prop)])
        n = Narrative(r)
        assert own_step(n, n.document(), target_frame(r, 'Or.inl')).fallback


def retained_snapshots():
    root = Path(__file__).resolve().parents[2]/'artifacts'/'pinned-openai-slice'
    return [json.loads(p.read_text()) for p in sorted(root.rglob('snapshot.json'))]


def test_real_retained_slice_has_new_equivalence_and_negation_explanations():
    snapshots = retained_snapshots()
    assert len(snapshots) == 14, 'The retained real-slice denominator changed; review the evidence.'
    found = {'equivalence-reverse': 0, 'negation-introduction': 0}
    for r in snapshots:
        n = Narrative(r)
        d = n.document()
        for step in walk_steps(d.declarations[0].steps):
            if step.rule in found:
                found[step.rule] += 1
        assert set(n.owners) == set(range(len(r['frames'])))
        assert prose(d).count('[Explanation gap]') == sum(s.fallback for s in walk_steps(d.declarations[0].steps))
    assert found == {'equivalence-reverse': 2, 'negation-introduction': 2}


def test_real_retained_alternating_norm_keeps_automated_proof_gaps():
    r = next(r for r in retained_snapshots()
             if r['theorem'] == 'OAI.CirculantHadamard.AlternatingNorm.norm_eq_one_of_balanced_products')
    n = Narrative(r)
    d = n.document()
    steps = list(walk_steps(d.declarations[0].steps))
    assert sum(s.rule == 'negation-introduction' for s in steps) == 2
    assert any(s.fallback and 'Mathlib.Tactic.Linarith.lt_irrefl' in s.references for s in steps)
    check_reading(r, d)
