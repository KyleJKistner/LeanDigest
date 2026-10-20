"""Reader-quality rules added in source-math-en/0.5.0 and 0.6.0.

Fixtures in tests/fixtures/reader_quality.json are subtrees of real retained
snapshots from the pinned 492-snapshot corpus; each records its source
snapshot and original frame ids. Records built by ``synthetic`` below are
hand-made format fixtures, not Lean observations; tests using them say so.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

import proofreader.narrative as narrative
from proofreader.kernel import InvalidExport
from proofreader.model import walk_steps
from proofreader.narrative import Narrative, check_reading, prose
from proofreader.reading_kpis import comparison, measure, measure_corpus

FIXTURES = json.loads((Path(__file__).parent/'fixtures/reader_quality.json').read_text())['fixtures']
DATA = Path(__file__).parents[1]/'proofreader/data'


def rendered(record):
    n = Narrative(record)
    return n, n.document()


def owner(n, d, frame):
    return next(s for s in walk_steps(d.declarations[0].steps) if s.id == n.owners[frame])


def owned(step):
    return [int(x[1:]) for x in step.term_id.split(',')]


def real(name):
    return deepcopy(FIXTURES[name]['record'])


def synthetic(node, theorem='Synthetic.readerQuality'):
    """A hand-made snapshot from a nested node description (format fixture only)."""
    frames = []

    def visit(node, path, context):
        i = len(frames)
        frame = dict(id=i, path=path, role=node['role'], head=node.get('head', ''), statement=node['statement'],
                     context=deepcopy(context), children=[], premises=[], objects=list(node.get('objects', [])),
                     budget_cut=node.get('cut', False))
        frames.append(frame)
        for key in ('binder', 'domain'):
            if key in node:
                frame[key] = node[key]
        if 'body' in node:
            frame['children'].append(visit(node['body'], path+[1], context+[dict(name=node['binder'], type=node['domain'])]))
        else:
            arguments = node.get('arguments', [])
            arity = len(frame['objects']) + len(arguments)
            for slot, child in arguments:
                j = visit(child, path+[0]*(arity-slot-1)+[1], context)
                frame['children'].append(j)
                frame['premises'].append(dict(argument=slot, frame=j, statement=child['statement']))
        return i

    visit(node, [], [])
    return dict(schema='proofreader.narrative/v1', theorem=theorem, lean_version='4.34.1', axioms=[],
                statement=frames[0]['statement'], frames=frames, judgements_checked=len(frames),
                formula_backend='Lean pretty-printer')


def app(head, statement, *arguments, objects=(), role='application', cut=False):
    return dict(role=role, head=head, statement=statement, objects=list(objects), arguments=list(arguments), cut=cut)


def given(binder, statement):
    return dict(role='given', binder=binder, statement=statement)


# Every fixture: ownership, regeneration and determinism.

@pytest.mark.parametrize('name', sorted(FIXTURES))
def test_real_fixture_frames_are_owned_once_and_regenerate(name):
    record = real(name)
    original = deepcopy(record)
    n, d = rendered(record)
    assert set(n.owners) == set(range(len(record['frames'])))
    assert sum(len(owned(s)) for s in walk_steps(d.declarations[0].steps)) == len(record['frames'])
    check_reading(record, d)
    assert Narrative(record).document().to_json() == d.to_json()
    assert record == original
    assert len(FIXTURES[name]['provenance']['recorded_frames']) == len(record['frames'])
    assert prose(d).count('[Explanation gap]') == sum(s.fallback for s in walk_steps(d.declarations[0].steps))


# 1. Typeclass side conditions.

def test_instance_side_conditions_are_one_counted_gap_step():
    record = real('cast_with_instances')
    n, d = rendered(record)
    heads = {'IsOrderedAddMonoid.toAddLeftMono', 'Real.instIsOrderedAddMonoid', 'Real.instZeroLEOneClass',
             'FloorSemiring.instCharZero'}
    ids = [f['id'] for f in record['frames'] if f['head'] in heads]
    step = owner(n, d, ids[0])
    assert step.rule == 'instance-facts' and step.fallback
    assert sorted(owned(step)) == sorted(ids)
    assert step.text == 'Standard instance facts used: AddLeftMono ℝ; ZeroLEOneClass ℝ; CharZero ℝ.'
    citation = owner(n, d, next(f['id'] for f in record['frames'] if f['head'] == 'Nat.cast_lt._simp_1'))
    assert citation.children[-1] is step and citation.rule == 'citation'
    row = measure(record)
    assert row['frames_by_rule']['instance-facts'] == 4 == row['instance_frames']


def test_instance_assumptions_are_grouped_but_remain_hypotheses():
    n, d = rendered(real('instance_assumption'))
    step = next(s for s in walk_steps(d.declarations[0].steps) if s.rule == 'instance-assumptions')
    assert not step.fallback
    # The notation layer omits the opened MeasureTheory namespace in the display.
    assert step.text == 'Instance assumption used: IsProbabilityMeasure ν.'
    assert 'hypothesis inst' in step.detail


def test_instance_family_binder_is_absorbed_with_its_body():
    record = real('pi_instance_family')
    n, d = rendered(record)
    family = next(f['id'] for f in record['frames'] if f['role'] == 'introduce')
    step = owner(n, d, family)
    # The family is built from a local instance hypothesis, so it is not called standard.
    assert step.rule == 'instance-facts' and step.fallback
    assert step.text == ('Instance fact used: Nonempty (ℕ → ι). '
                         'The derivation uses the local instance hypothesis inst_1: Nonempty ι.')
    assert owner(n, d, 0).rule == 'citation'


@pytest.mark.parametrize('name,head,rule', [
    # Real frames: a named hypothesis with a class statement, a structure
    # projection resting on a theorem-level premise, a project lemma whose name
    # starts with "inst", and a constructor of a class.
    ('project_citation', None, 'hypotheses'),
    ('ergodic_projection', 'Ergodic.toMeasurePreserving', 'citation'),
    ('instance_named_project_lemma', 'OAI.UniformSparsestCut.SourceUniform.instance_exists', 'project-citation'),
    ('nonempty_intro', 'Nonempty.intro', 'citation'),
])
def test_mathematical_frames_resembling_instances_stay_visible(name, head, rule):
    record = real(name)
    n, d = rendered(record)
    if head is None:
        frame = next(f['id'] for f in record['frames'] if f.get('binder') == 'hPM')
        assert owner(n, d, frame).text == 'Use the hypotheses heven: Even (Fintype.card V); hPM: Nonempty G.Matching.'
    else:
        frame = next(f['id'] for f in record['frames'] if f['head'] == head)
    assert owner(n, d, frame).rule == rule
    assert not any(s.rule.startswith('instance') and frame in owned(s) for s in walk_steps(d.declarations[0].steps))


@pytest.mark.parametrize('premise,instance', [
    # Synthetic format fixtures for the instance classifier's boundary.
    (app('instCharZeroReal', 'CharZero ℝ', role='named'), True),
    (app('inferInstance', 'Nontrivial ℝ', objects=['Nontrivial ℝ']), True),
    (app('IsStrictOrderedRing.toPosMulStrictMono', 'PosMulStrictMono ℝ',
         (1, app('Real.instIsStrictOrderedRing', 'IsStrictOrderedRing ℝ', role='named')), objects=['ℝ']), True),
    (app('Real.borelSpace', 'BorelSpace ℝ', role='named'), True),
    (given('inst_2', 'CompleteSpace H'), True),
    (given('inst✝¹', 'Nonempty V'), True),
    (app('Foo.instant_bound', '0 < x', role='named'), False),
    (app('Foo.instant_bound', 'Continuous f', role='named'), False),
    (app('instFoo', '0 < 1', role='named'), False),
    (app('Real.instIsOrderedRing', 'IsOrderedRing ℝ', role='named', cut=True), False),
    (app('OAI.Space.instCompleteSpace', 'CompleteSpace X', role='named'), False),
    (app('Nonempty.intro', 'Nonempty X', objects=['X', 'x']), False),
    (app('Ergodic.toMeasurePreserving', 'MeasureTheory.MeasurePreserving f μ μ', (1, given('h', 'Ergodic f μ')), objects=['f']), False),
    (given('inst', '0 < x'), False),
    (given('hinst', 'CharZero R'), False),
    (given('hEinstein', 'IsEinstein g'), False),
    (given('instance', 'CharZero R'), False),
])
def test_instance_classifier_boundary_on_synthetic_frames(premise, instance):
    record = synthetic(app('Foo.lemma', 'P x', (1, premise), objects=['x']))
    n, d = rendered(record)
    assert n.instance(1) is instance
    rules = {s.rule for s in walk_steps(d.declarations[0].steps) if 1 in owned(s)}
    assert bool(rules & {'instance-facts', 'instance-assumptions'}) is instance
    assert set(n.owners) == set(range(len(record['frames'])))
    check_reading(record, d)


def test_instance_resting_on_a_project_lemma_is_not_called_standard():
    record = real('instance_from_project_lemma')
    n, d = rendered(record)
    step = owner(n, d, next(f['id'] for f in record['frames'] if f['head'] == 'inferInstance'))
    assert step.rule == 'instance-facts' and step.fallback
    assert step.text == 'Instance fact used, derived using the premise below: FiniteDimensional ℂ ↥E.'
    assert [c.text for c in step.children] == ['By the project lemma iterateSpace_finiteDimensional:']
    assert not any(s.text.startswith('Standard') for s in walk_steps(d.declarations[0].steps))


def test_project_instance_is_cited_as_a_project_instance():
    # Synthetic: project instances are project content, not standard facts.
    record = synthetic(app('Foo.lemma', 'P x', (1, app('OAI.Space.instCompleteSpaceFree', 'CompleteSpace Free', role='named')), objects=['x']))
    n, d = rendered(record)
    step = owner(n, d, 1)
    assert step.rule == 'project-citation' and step.text == 'By the project instance OAI.Space.instCompleteSpaceFree:'


def test_dictionary_instances_keep_the_certified_bezout_reading():
    record = json.loads((DATA/'bezout-snapshot.json').read_text())
    n, d = rendered(record)
    steps = list(walk_steps(d.declarations[0].steps))
    assert not any(s.fallback for s in steps)
    assert not {s.rule for s in steps} & {'instance-facts', 'instance-assumptions', 'automation', 'citation', 'project-citation',
                                          'hypotheses', 'unchecked-application', 'witness-proof', 'unpack-existential'}
    assert sum(s.rule == 'polynomial-identity' for s in steps) == len(n.certificates) > 0
    assert 'R is an integral domain' in prose(d)
    assert 'x = 0 ∧ z = 0\n' in prose(d)  # the dictionary step keeps its conclusion under hxz


# 2. Decision-procedure certificates.

def test_norm_num_certificate_is_one_gap_step():
    record = real('norm_num')
    n, d = rendered(record)
    [step] = d.declarations[0].steps
    assert step.rule == 'automation' and step.fallback and not step.children
    assert step.text.startswith('Numerical evaluation (norm_num) verifies this') and step.conclusion == '0 < 8'
    assert sorted(owned(step)) == list(range(len(record['frames'])))
    assert measure(record)['automation_frames'] == len(record['frames'])


def test_linarith_contradiction_absorbs_only_its_certificate():
    record = real('linarith')
    n, d = rendered(record)
    root = owner(n, d, 0)
    # A top-level citation proving the theorem itself does not reprint the statement.
    assert root.rule == 'citation' and root.text == 'The statement follows from lt_of_not_ge, applied to the facts below.'
    assert root.conclusion is None
    step = next(s for s in walk_steps(d.declarations[0].steps) if s.rule == 'automation')
    assert step.text == 'Linear arithmetic (linarith) derives a contradiction; the certificate is not expanded.'
    assert step.conclusion is None
    assert {record['frames'][i]['head'] for i in owned(step)} == {'Mathlib.Tactic.Linarith.lt_irrefl', 'Eq.mp'}


def test_positivity_keeps_genuine_premises_visible():
    record = real('positivity_with_premises')
    n, d = rendered(record)
    step = owner(n, d, 0)
    assert step.rule == 'automation' and step.text.startswith('Sign analysis (positivity)')
    for i in owned(step):
        f = record['frames'][i]
        assert (narrative._automation(f['head']) or f['role'] == 'reflexivity' or n.instance(i)
                or f['head'] in narrative._NUMERAL_CASTS), f
    hypotheses = [f['id'] for f in record['frames'] if f['role'] == 'given' and not n.instance(f['id'])]
    assert hypotheses and all(owner(n, d, i).rule == 'given' for i in hypotheses)
    assert {c.rule for c in step.children} >= {'equivalence-reverse', 'citation'}


def test_automation_never_absorbs_a_hypothesis_or_project_lemma():
    # Synthetic: a norm_num root whose premises are a hypothesis and a project lemma.
    record = synthetic(app('Mathlib.Meta.NormNum.isNat_lt_true', '0 < x',
                           (1, given('hx', 'Mathlib.Meta.NormNum.IsNat x 3')),
                           (2, app('OAI.Foo.bound', 'Mathlib.Meta.NormNum.IsNat 0 0', role='named')),
                           (3, app('Eq.refl', 'true = true', objects=['Bool', 'true'], role='reflexivity')),
                           objects=['ℝ']))
    n, d = rendered(record)
    [step] = d.declarations[0].steps
    assert step.rule == 'automation' and sorted(owned(step)) == [0, 3]
    assert [c.rule for c in step.children] == ['given', 'project-citation']


# 3. Rewrite plumbing.

def test_frontier_rewrites_say_what_their_head_does():
    n, d = rendered(real('of_eq_true'))
    [step] = d.declarations[0].steps
    assert step.rule == 'rewrite' and step.fallback
    # of_eq_true (h : p = True) : p. The frontier records no tactic, so the
    # sentence does not claim that simp produced the equation.
    assert step.text == 'This proposition is proved equal to True; that equation is not expanded.'
    record = real('cast_with_instances')
    n, d = rendered(record)
    congruence = owner(n, d, next(f['id'] for f in record['frames'] if f['head'] == "congrFun'"))
    assert congruence.fallback and congruence.text == 'This equation follows by congruence from an equation that is not expanded.'
    record = synthetic(dict(role='rewrite', head='Eq.mpr', statement='P x'))
    [step] = Narrative(record).document().declarations[0].steps
    assert step.fallback and step.text.startswith('Rewrite the goal to an equal proposition') and step.conclusion == 'P x'


def test_cast_along_a_recorded_equation_is_explained():
    record = real('cast_with_instances')
    n, d = rendered(record)
    step = owner(n, d, 0)
    assert step.rule == 'transport' and not step.fallback
    assert step.text == 'From 0 < m, obtain 0 < ↑m by rewriting with the equation of propositions below.'
    assert [c.rule for c in step.children] == ['application', 'given']


@pytest.mark.parametrize('mutation', ['equation', 'objects', 'result'])
def test_cast_with_mismatched_printing_keeps_the_gap(mutation):
    record = real('cast_with_instances')
    root = record['frames'][0]
    equation = root['premises'][0]['frame']
    if mutation == 'equation':
        record['frames'][equation]['statement'] = root['premises'][0]['statement'] = '(0 < m) = (0 < ↑m + 1)'
    elif mutation == 'objects':
        root['objects'] = list(reversed(root['objects']))
    else:
        record['frames'][0]['statement'] = record['statement'] = '0 ≤ ↑m'
    try:
        n, d = rendered(record)
    except InvalidExport:
        return
    step = owner(n, d, 0)
    assert step.fallback and step.rule == 'citation'


# 4. Citations.

def test_citations_read_as_mathematics_and_stay_gaps():
    record = real('project_citation')
    n, d = rendered(record)
    step = owner(n, d, 0)
    assert step.rule == 'project-citation' and step.fallback
    assert step.text == 'The statement follows from the project lemma entropyDefect_attains_max, applied to the facts below.'
    # The cited lemma's full name stays in references; its proved statement is the theorem's, shown above.
    assert step.conclusion is None and step.references == ['OAI.MatchingEntropy.entropyDefect_attains_max']
    assert d.declarations[0].axes['notation']['names'] == {'OAI.MatchingEntropy.entropyDefect_attains_max': 'entropyDefect_attains_max'}
    assert [c.rule for c in step.children] == ['hypotheses']
    record = real('cast_with_instances')
    n, d = rendered(record)
    simp = owner(n, d, next(f['id'] for f in record['frames'] if f['head'] == 'Nat.cast_lt._simp_1'))
    assert simp.text == 'By Nat.cast_lt (in the equational form generated for simp):'
    assert narrative._citation('OAI.T.main._proof_1_2') == (
        'By an auxiliary proof that Lean extracted while elaborating OAI.T.main:', 'project-citation')


def test_citation_count_does_not_depend_on_wording(monkeypatch):
    record = real('project_citation')
    before = measure(record)
    assert before['citation_gap_steps'] == before['project_citation_gap_steps'] == 1
    assert before['opaque_apply_steps'] == 0
    monkeypatch.setattr(narrative, '_citation', lambda head: ('Apply '+head+' to the supplied arguments.',
                                                             'project-citation' if head.startswith('OAI.') else 'citation'))
    after = measure(record)
    assert after['citation_gap_steps'] == before['citation_gap_steps']
    assert after['opaque_apply_steps'] == 1 and after['gap_frames'] == before['gap_frames']


def test_corpus_summary_separates_wording_from_tagged_counts(tmp_path):
    for name in ('project_citation', 'norm_num', 'cast_with_instances'):
        (tmp_path/name).mkdir()
        (tmp_path/name/'snapshot.json').write_text(json.dumps(FIXTURES[name]['record']), encoding='utf-8')
    summary, rows = measure_corpus(tmp_path)
    assert not summary['rendering_failures'] and summary['readings'] == 3
    for key in ('citation_gap_steps', 'project_citation_gap_steps', 'instance_frames', 'automation_frames', 'other_gap_steps'):
        assert summary[key] == sum(r[key] for r in rows)
    assert summary['gap_frames'] == sum(summary['gap_frames_by_rule'].values())
    assert summary['distinct_cited_project_constants'] == 1
    assert summary['measure_notes']['opaque_apply_steps'].startswith('Wording measure')
    table = comparison({'printer_version': 'old', 'corpus_sha256': summary['corpus_sha256']}, summary)
    assert '| opaque_apply_steps (wording) | — |' in table and '| citation_gap_steps | — |' in table


# 5. Other frequent noise.

def test_anonymous_have_is_not_named_this():
    n, d = rendered(real('anonymous_have'))
    text = prose(d)
    assert 'Establish 2 ≤ n + 2.\n' in text and 'call this fact this' not in text
    assert 'Use the fact 2 ≤ n + 2 established above.' in text


def test_this_from_an_assumption_keeps_its_name():
    # Synthetic: `this` introduced by an assumption, not by a `have`.
    record = synthetic(dict(role='assume', binder='this', domain='0 < x', statement='0 < x → 0 < x',
                            body=given('this', '0 < x')))
    assert 'Use the hypothesis this: 0 < x.' in prose(Narrative(record).document())


def test_have_does_not_repeat_its_claim_under_a_sole_citation():
    # Synthetic: have h : P x := Foo.lemma, then a hypothesis closes the goal.
    record = synthetic_have()
    n, d = rendered(record)
    have = d.declarations[0].steps[0]
    [child] = have.children
    assert child.rule == 'citation' and child.text == 'By Foo.lemma.' and child.conclusion is None
    check_reading(record, d)


def synthetic_have():
    frames = [dict(id=0, path=[], role='have', head='', statement='Q', context=[], children=[1, 2], premises=[],
                   objects=[], budget_cut=False, binder='h', domain='P x'),
              dict(id=1, path=[1], role='named', head='Foo.lemma', statement='P x', context=[], children=[],
                   premises=[], objects=[], budget_cut=False),
              dict(id=2, path=[2], role='given', head='', statement='Q', context=[dict(name='h', type='P x')],
                   children=[], premises=[], objects=[], budget_cut=False, binder='hq')]
    return dict(schema='proofreader.narrative/v1', theorem='Synthetic.have', lean_version='4.34.1', axioms=[],
                statement='Q', frames=frames, judgements_checked=3, formula_backend='Lean pretty-printer')


def test_nested_destructuring_of_a_named_hypothesis_is_one_step():
    record = real('rcases_chain')
    n, d = rendered(record)
    step = d.declarations[0].steps[0]
    assert step.rule == 'unpack-conjunction' and not step.fallback and not step.children
    assert step.text == ('From h, obtain hF: F ≠ 0, hhom: MvPolynomial.IsHomogeneous F (MvPolynomial.totalDegree F) '
                         'and hcycle: equationIdealCycle F = D.')
    assert sorted(owned(step)) == list(range(8))


def destructuring(left, right, conjunction, body):
    def assume(name, domain, inner):
        return dict(role='assume', binder=name, domain=domain, statement=domain+' → '+inner['statement'], body=inner)
    return app('And.casesOn', body['statement'], (3, given('h', conjunction)),
               (4, assume('ha', left, assume('hb', right, body))), objects=[left, right, 'fun _ => S'])


@pytest.mark.parametrize('left,right,conjunction,named', [
    # Synthetic format fixtures: precedence decides whether ∧ joins the two parts.
    ('P', 'Q', 'P ∧ Q', True),
    ('∃ x, P x', 'Q', '(∃ x, P x) ∧ Q', True),
    ('P', 'Q → R', 'P ∧ (Q → R)', True),
    ('P', 'Q → R', 'P ∧ Q → R', False),
    ('P ∨ Q', 'R', 'P ∨ Q ∧ R', False),
    ('P ∧ Q', 'R', 'P ∧ Q ∧ R', False),
    ('f fun x => x', 'R', 'f fun x => x ∧ R', False),
])
def test_conjunction_is_named_only_when_printed_with_the_right_precedence(left, right, conjunction, named):
    record = synthetic(destructuring(left, right, conjunction, given('hs', 'S')))
    n, d = rendered(record)
    step = d.declarations[0].steps[0]
    assert step.rule == 'unpack-conjunction' and not step.fallback
    assert step.text.startswith('From h, obtain' if named else 'From the conjunction, obtain')
    assert bool(step.children) is not named
    assert set(n.owners) == set(range(len(record['frames'])))
    check_reading(record, d)


@pytest.mark.parametrize('reused', [False, True])
def test_intermediate_part_is_kept_when_used_again(reused):
    # Synthetic: h : P ∧ Q ∧ R destructured as ⟨ha, hb⟩, then hb : Q ∧ R as ⟨hc, hd⟩.
    tail = app('Foo.use', 'S', (1, given('hb', 'Q ∧ R'))) if reused else given('hs', 'S')
    inner = destructuring('Q', 'R', 'Q ∧ R', tail)
    inner['arguments'][0] = (3, given('hb', 'Q ∧ R'))
    inner['arguments'][1][1]['binder'] = 'hc'; inner['arguments'][1][1]['body']['binder'] = 'hd'
    record = synthetic(destructuring('P', 'Q ∧ R', 'P ∧ Q ∧ R', inner))
    n, d = rendered(record)
    text = prose(d)
    if reused:
        assert 'From h, obtain ha: P and hb: Q ∧ R.' in text and 'From hb, obtain hc: Q and hd: R.' in text
    else:
        assert 'From h, obtain ha: P, hc: Q and hd: R.' in text
    assert set(n.owners) == set(range(len(record['frames'])))
    check_reading(record, d)


def test_projection_from_an_unfolded_premise_is_labelled_unchecked():
    n, d = rendered(real('unfolded_projection'))
    [step] = d.declarations[0].steps
    assert step.rule == 'unchecked-projection' and step.fallback
    assert step.text == ('Take the first conjunct, 0 < s, of the premise below; its second conjunct is s ≤ 1. '
                         'That the premise has this form is not checked here.')
    assert [c.text for c in step.children] == ['Use the hypothesis hs: s ∈ Ioc 0 1.']


def test_nonempty_elimination_chooses_an_element():
    record = real('nonempty_cases')
    n, d = rendered(record)
    step = d.declarations[0].steps[0]
    assert step.rule == 'choose-element' and not step.fallback
    assert step.text.startswith('Since Nonempty (FixedParameters.Parameters δ positive), choose parameters ∈ ')
    assert sorted(owned(step)) == [0, record['frames'][0]['children'][1]]


def test_dependent_nonempty_elimination_keeps_the_gap():
    record = real('nonempty_cases')
    intro = record['frames'][record['frames'][0]['children'][1]]
    body = record['frames'][intro['children'][0]]
    body['statement'] = intro['statement'] = 'Q parameters'
    record['frames'][0]['premises'][1]['statement'] = intro['statement']
    n, d = rendered(record)
    assert owner(n, d, 0).rule == 'citation' and owner(n, d, 0).fallback


def test_substitution_and_restatement_are_named_gaps():
    n, d = rendered(real('substitution'))
    step = d.declarations[0].steps[0]
    assert step.rule == 'substitution' and step.fallback
    assert step.text == ('Rewrite the statement proved below along the equation a_1 i = p; '
                         'which occurrences are rewritten is not displayed.')
    n, d = rendered(real('restatement'))
    step = d.declarations[0].steps[0]
    assert step.rule == 'restatement' and step.fallback


def test_substitution_names_the_objects_it_is_specialized_to():
    # Eq.ndrec … (h : 0 = s) L hL hd: the rewritten statement is a ∀ over L.
    n, d = rendered(real('substitution_specialized'))
    step = d.declarations[0].steps[0]
    assert step.rule == 'substitution' and step.fallback
    assert step.text == ('Rewrite the statement proved below along the equation 0 = s, then specialize the result to L '
                         'and apply it to the further premises below; which occurrences are rewritten is not displayed.')


def test_substitution_prints_the_recorded_equation_not_joined_objects():
    # Synthetic, after a real corpus case: joining a = fun … and b with "="
    # would print fun x => f x = g, which Lean reads as fun x => (f x = g).
    record = synthetic(app('Eq.ndrec', 'P g', (3, given('hp', 'P fun x => f x')), (5, given('h', '(fun x => f x) = g')),
                           objects=['ℕ → ℕ', 'fun x => f x', 'fun g => P g', 'g']))
    n, d = rendered(record)
    step = d.declarations[0].steps[0]
    assert step.rule == 'substitution' and step.fallback
    assert step.text.startswith('Rewrite the statement proved below along the equation (x ↦ f x) = g;')
    check_reading(record, d)


def test_witness_for_a_named_goal_is_a_labelled_gap():
    # Synthetic: Exists.intro proving a definition that Lean unfolds to ∃.
    record = synthetic(app('Exists.intro', 'Main', (3, given('h', '0 < 1 / 2')),
                           objects=['ℝ', 'fun c => 0 < c', '1 / 2'], role='witness'))
    [step] = Narrative(record).document().declarations[0].steps
    assert step.fallback and step.rule == 'witness' and step.text.startswith('Provide the witness 1 / 2;')


# 6. Rules added in source-math-en/0.6.0.

def gaps(record):
    """Gap steps and gap frames of a rendering, the two counts a regrouping must not change."""
    n, d = rendered(record)
    steps = list(walk_steps(d.declarations[0].steps))
    return sum(s.fallback for s in steps), sum(len(owned(s)) for s in steps if s.fallback), len(steps)


def test_adjacent_hypotheses_are_one_step_in_their_original_order():
    record = real('hypotheses_mixed')
    n, d = rendered(record)
    root = owner(n, d, 0)
    assert [c.rule for c in root.children] == ['project-citation', 'hypotheses', 'project-citation', 'given']
    group = root.children[1]
    assert not group.fallback and owned(group) == [2, 3]
    assert group.text == 'Use the hypotheses hv: Geometry.JointSmooth v; hc: Geometry.TimeCollars v.'
    assert 'hv : OAI.BalancedTransport.Geometry.JointSmooth v' in group.detail
    assert root.children[3].text == 'Use the hypothesis hd: ∀ (t : ℝ) (x : Space), div v t x = 0.'


@pytest.mark.parametrize('name', ['hypotheses_mixed', 'project_citation', 'applied_projection', 'unpack_existential',
                                  'unchecked_application'])
def test_grouping_hypotheses_changes_no_gap_count(name, monkeypatch):
    record = real(name)
    gap_steps, gap_frames, shown = gaps(record)
    monkeypatch.setattr(Narrative, 'grouped', lambda self, steps: steps)
    before_steps, before_frames, before_shown = gaps(record)
    assert (gap_steps, gap_frames) == (before_steps, before_frames)
    assert shown < before_shown


def test_hypothesis_groups_keep_other_premises_separate():
    # Synthetic: a hypothesis, a cited lemma, then two hypotheses.
    record = synthetic(app('Foo.lemma', 'P x', (1, given('h1', 'A')), (2, app('Bar.b', 'B', role='named')),
                           (3, given('h2', 'C')), (4, given('h3', 'D')), objects=['x']))
    n, d = rendered(record)
    root = d.declarations[0].steps[0]
    assert [c.text for c in root.children] == ['Use the hypothesis h1: A.', 'By Bar.b:', 'Use the hypotheses h2: C; h3: D.']
    assert owned(root.children[2]) == [3, 4] and root.children[2].rule == 'hypotheses'
    check_reading(record, d)


def test_budget_cut_hypothesis_is_not_merged():
    # Synthetic: the middle hypothesis is a budget cut, so no two mergeable lines are adjacent.
    cut = dict(given('h2', 'B'), cut=True)
    record = synthetic(app('Foo.lemma', 'P x', (1, given('h1', 'A')), (2, cut), (3, given('h3', 'C')), objects=['x']))
    n, d = rendered(record)
    children = d.declarations[0].steps[0].children
    assert [c.rule for c in children] == ['given', 'given', 'given']
    assert [c.fallback for c in children] == [False, True, False]


def test_hypotheses_from_different_scopes_are_not_merged():
    # Synthetic: ⟨fun x => h x, h2⟩; h lives under the binder x, h2 does not.
    record = synthetic(app('And.intro', '(∀ x, P x) ∧ Q',
                           (2, dict(role='introduce', binder='x', domain='T', statement='∀ x, P x', body=given('h', 'P x'))),
                           (3, given('h2', 'Q')), objects=['∀ x, P x', 'Q'], role='combine'))
    n, d = rendered(record)
    [step] = d.declarations[0].steps
    assert [c.text for c in step.children] == ['Let x ∈ T be arbitrary.', 'Use the hypothesis h: P x.', 'Use the hypothesis h2: Q.']
    check_reading(record, d)


def test_fact_from_an_anonymous_have_is_not_merged():
    # Synthetic: have : A := Foo.a; Foo.lemma this h2.
    frames = [dict(id=0, path=[], role='have', head='', statement='P', context=[], children=[1, 2], premises=[],
                   objects=[], budget_cut=False, binder='this', domain='A'),
              dict(id=1, path=[1], role='named', head='Foo.a', statement='A', context=[], children=[], premises=[],
                   objects=[], budget_cut=False),
              dict(id=2, path=[2], role='application', head='Foo.lemma', statement='P', context=[dict(name='this', type='A')],
                   children=[3, 4], premises=[dict(argument=0, frame=3, statement='A'), dict(argument=1, frame=4, statement='B')],
                   objects=[], budget_cut=False),
              dict(id=3, path=[2, 0, 1], role='given', head='', statement='A', context=[dict(name='this', type='A')],
                   children=[], premises=[], objects=[], budget_cut=False, binder='this'),
              dict(id=4, path=[2, 1], role='given', head='', statement='B', context=[dict(name='this', type='A')],
                   children=[], premises=[], objects=[], budget_cut=False, binder='h2')]
    record = dict(schema='proofreader.narrative/v1', theorem='Synthetic.anonymous', lean_version='4.34.1', axioms=[],
                  statement='P', frames=frames, judgements_checked=5, formula_backend='Lean pretty-printer')
    n, d = rendered(record)
    citation = owner(n, d, 2)
    assert [c.text for c in citation.children] == ['Use the fact A established above.', 'Use the hypothesis h2: B.']
    check_reading(record, d)


@pytest.mark.parametrize('node,labels', [
    # Synthetic: both directions of an equivalence, and both branches of an
    # induction, are hypotheses in the same context. Each line keeps its label.
    (app('Iff.intro', 'A ↔ B', (2, given('h1', 'A → B')), (3, given('h2', 'B → A')), objects=['A', 'B']),
     ['Forward direction. Use the hypothesis h1: A → B.', 'Reverse direction. Use the hypothesis h2: B → A.']),
    (app('Nat.rec', 'P n', (1, given('h0', 'P 0')), (2, given('hs', '∀ (n : ℕ), P n → P (n + 1)')),
         objects=['fun n => P n', 'n'], role='induction'),
     ['Base case (zero). Use the hypothesis h0: P 0.', 'Successor step. Use the hypothesis hs: ∀ (n : ℕ), P n → P (n + 1).']),
])
def test_labelled_hypothesis_lines_are_not_merged(node, labels):
    record = synthetic(node)
    n, d = rendered(record)
    [step] = d.declarations[0].steps
    assert [c.text for c in step.children] == labels and [c.rule for c in step.children] == ['given', 'given']
    check_reading(record, d)


def test_hypotheses_printed_over_several_lines_get_one_line_each():
    # Synthetic: a statement that Lean's pretty-printer broke across lines.
    record = synthetic(app('Foo.lemma', 'P x', (1, given('h1', '∀ (k : ℕ),\n  f k ≤ g k')), (2, given('h2', 'A')), objects=['x']))
    [child] = Narrative(record).document().declarations[0].steps[0].children
    assert child.text == 'Use the hypotheses:\nh1: ∀ (k : ℕ),\n  f k ≤ g k;\nh2: A.'


def test_projection_reads_a_premise_with_a_binder_conjunct():
    n, d = rendered(real('binder_conjunct_projection'))
    step = owner(n, d, 0)
    assert step.rule == 'conjunction-projection' and not step.fallback
    assert step.text == 'Take the first conjunct, ↑(n t) / ↑g → ∞ as t → ∞.'
    # A binder as the right conjunct takes the rest of the formula (A ∧ ∀ G, … → …).
    n, d = rendered(real('binder_right_projection'))
    assert owner(n, d, 0).rule == 'conjunction-projection' and not owner(n, d, 0).fallback
    assert owner(n, d, 1).rule == 'unchecked-projection' and owner(n, d, 1).fallback


@pytest.mark.parametrize('premise,left,right,checked', [
    # Synthetic precedence traps: only a premise that Lean parses as left ∧ right is a checked projection.
    ('A ∧ ∃ p, P p', 'A', '∃ p, P p', True),
    ('A ∧ ∀ x, P x → Q x', 'A', '∀ x, P x → Q x', True),
    ('A ∧ ∃ x, P x ∨ Q', 'A', '∃ x, P x ∨ Q', True),
    ('(∃ p, P p) ∧ B', '∃ p, P p', 'B', True),
    ('(∀ x, P x) ∧ ∀ y, Q y', '∀ x, P x', '∀ y, Q y', True),
    ('A ∧ B ∧ C', 'A', 'B ∧ C', True),
    ('¬A ∧ B', '¬A', 'B', True),
    ('A ∧ ∑ i, f i ≤ 1', 'A', '∑ i, f i ≤ 1', True),
    ('∃ p, P p ∧ B', '∃ p, P p', 'B', False),
    ('∀ x, P x ∧ B', '∀ x, P x', 'B', False),
    ('A ∨ B ∧ C', 'A ∨ B', 'C', False),
    ('A ∧ B → C', 'A', 'B → C', False),
    ('A ∧ B ∨ C', 'A', 'B ∨ C', False),
    ('A ∧ B ∧ C', 'A ∧ B', 'C', False),
    ('A ∧ (∃ x, P x) ∨ Q', 'A', '(∃ x, P x) ∨ Q', False),
    ('f fun x => x ∧ R', 'f fun x => x', 'R', False),
    ('A ∧ ∑ i, f i ≤ 1 → B', 'A', '∑ i, f i ≤ 1 → B', False),
])
def test_projection_premise_precedence(premise, left, right, checked):
    record = synthetic(app('And.left', left, (2, given('h', premise)), objects=[left, right]))
    n, d = rendered(record)
    [step] = d.declarations[0].steps
    assert step.rule == ('conjunction-projection' if checked else 'unchecked-projection')
    assert step.fallback is not checked
    check_reading(record, d)


def test_reverse_direction_reads_an_equivalence_with_a_binder_side():
    n, d = rendered(real('equivalence_binder'))
    step = owner(n, d, 0)
    assert step.rule == 'equivalence-reverse' and not step.fallback
    assert step.text.startswith('Use the reverse direction of SetFormula.Realize N.sets')


@pytest.mark.parametrize('iff,left,right,checked', [
    # Synthetic precedence traps for ↔ (precedence 20, non-associative).
    ('A ↔ ∀ x, P x → Q x', 'A', '∀ x, P x → Q x', True),
    ('(∀ x, P x) ↔ Q', '∀ x, P x', 'Q', True),
    ('A → B ↔ C', 'A → B', 'C', True),
    ('A ∧ B ↔ C ∨ D', 'A ∧ B', 'C ∨ D', True),
    ('A ↔ (B ↔ C)', 'A', 'B ↔ C', True),
    ('¬A ↔ B', '¬A', 'B', True),
    ('∀ x, P x ↔ Q', '∀ x, P x', 'Q', False),
    ('∃ x, P x ↔ Q', '∃ x, P x', 'Q', False),
    ('A ↔ B ↔ C', 'A', 'B ↔ C', False),
    ('A ↔ ∀ x, P x ↔ Q x', 'A', '∀ x, P x ↔ Q x', False),
    ('if c then A else B ↔ C', 'if c then A else B', 'C', False),
])
def test_equivalence_premise_precedence(iff, left, right, checked):
    record = synthetic(app('Iff.mpr', left, (2, given('h', iff)), (3, given('hb', right)), objects=[left, right]))
    n, d = rendered(record)
    [step] = d.declarations[0].steps
    assert (step.rule == 'equivalence-reverse') is checked and step.fallback is not checked
    check_reading(record, d)


def test_proof_witness_names_the_proposition_and_the_remaining_claim():
    record = real('witness_proof_named')
    n, d = rendered(record)
    step = owner(n, d, 0)
    assert step.rule == 'witness-proof' and not step.fallback and owned(step) == [0]
    assert step.text == 'Prove hc: LocalLabels G v c, and then the remaining claim, which may depend on the proof hc.'
    assert [c.rule for c in step.children] == ['given', 'project-citation']
    n, d = rendered(real('witness_proof_anonymous'))
    step = owner(n, d, 0)
    assert step.text == 'Prove Group.FG Prescribed.G, and then the remaining claim.' and not step.fallback
    assert [c.rule for c in step.children] == ['instance-facts', 'verify-conclusions']


def proof_witness(statement='∃ (_ : A) (_ : B), C', inner='∃ (_ : B), C'):
    """Synthetic: Exists.intro ⟨a, Exists.intro ⟨b, hc⟩⟩ for ∃ (_ : A) (_ : B), C."""
    second = app('Exists.intro', inner, (2, app('Foo.b', 'B', role='named')), (3, given('hc', 'C')),
                 objects=['B', 'fun x => C'], role='witness')
    return synthetic(app('Exists.intro', statement, (2, app('Foo.a', 'A', role='named')), (3, second),
                         objects=['A', 'fun x => ∃ (_ : B), C'], role='witness'))


def test_chain_of_proof_witnesses_is_one_step():
    # Synthetic format fixture.
    record = proof_witness()
    n, d = rendered(record)
    [step] = d.declarations[0].steps
    assert step.rule == 'witness-proof' and not step.fallback and owned(step) == [0, 2]
    assert step.text == 'Prove A, then B, and then the remaining claim.'
    assert [c.text for c in step.children] == ['By Foo.a:', 'By Foo.b:', 'Use the hypothesis hc: C.']
    check_reading(record, d)


@pytest.mark.parametrize('statement,inner', [
    # Synthetic: the leading binder is printed with another type, or the remaining
    # claim of an anonymous binder is not printed as the rest of the statement.
    ('∃ (_ : A′) (_ : B), C', '∃ (_ : B), C'),
    ('∃ (_ : A) (_ : B), C', '∃ (_ : B), C′'),
    ('Main', '∃ (_ : B), C'),
])
def test_proof_witness_with_mismatched_printing_keeps_the_gap(statement, inner):
    # The synthetic record is valid, so the rule itself must decline it.
    n, d = rendered(proof_witness(statement, inner))
    step = owner(n, d, 0)
    assert step.fallback and step.rule == 'witness'


def test_existential_over_a_proposition_is_unpacked_from_the_hypothesis():
    record = real('unpack_existential')
    n, d = rendered(record)
    step = owner(n, d, 0)
    assert step.rule == 'unpack-existential' and not step.fallback and owned(step) == [0, 1, 2, 3]
    assert step.text.startswith('From h_3, obtain hb: ContMDiff ') and ' and hnear: ∀ (k : ℕ),' in step.text
    assert owner(n, d, 4).rule == 'project-citation'


def proof_cases(body='Q', major=('h', '∃ (_ : A), B')):
    """Synthetic: Exists.casesOn h (fun ha hb => …) with a proposition A as the bound type."""
    inner = dict(role='assume', binder='hb', domain='B', statement='B → '+body, body=app('Foo.q', body, (1, given('hb', 'B'))))
    outer = dict(role='assume', binder='ha', domain='A', statement='∀ (ha : A), B → '+body, body=inner)
    return synthetic(app('Exists.casesOn', 'Q', (3, given(*major)), (4, outer), objects=['A', 'fun x => B', 'fun x => Q'],
                         role='choose'))


def test_unpack_existential_on_synthetic_frames():
    # Synthetic format fixture.
    record = proof_cases()
    n, d = rendered(record)
    step = d.declarations[0].steps[0]
    assert step.rule == 'unpack-existential' and not step.fallback and step.text == 'From h, obtain ha: A and hb: B.'
    check_reading(record, d)


@pytest.mark.parametrize('body,major', [
    # Synthetic: a body that proves another statement (a dependent motive), and a
    # major premise printed as a named definition rather than ∃ over A.
    ('Q′', ('h', '∃ (_ : A), B')),
    ('Q', ('h', 'Main')),
    ('Q', ('h', '∃ (_ : A′), B')),
    # The rest of the major premise is printed differently from the second binder's domain.
    ('Q', ('h', '∃ (_ : A), B′')),
])
def test_unpack_existential_keeps_the_gap_without_exact_printing(body, major):
    # The synthetic record is valid, so the rule itself must decline it.
    n, d = rendered(proof_cases(body, major))
    step = owner(n, d, 0)
    assert step.fallback and step.rule == 'choose'


def test_instance_derived_from_a_local_instance_hypothesis_is_not_called_standard():
    n, d = rendered(real('local_instance'))
    [step] = d.declarations[0].steps
    assert step.rule == 'instance-facts' and step.fallback and owned(step) == [0, 1]
    assert step.text == 'Instance fact used: Countable U. The derivation uses the local instance hypothesis inst_1: Finite U.'


def test_local_instance_hypothesis_next_to_a_visible_premise():
    # Synthetic: inferInstance resting on a project lemma and a local instance hypothesis.
    record = synthetic(app('Foo.lemma', 'P x', (1, app('inferInstance', 'Thing X',
                                                     (1, app('OAI.Foo.bar', 'Lattice X', role='named')),
                                                     (2, given('inst_2', 'Nontrivial X')), objects=['Thing X'])), objects=['x']))
    n, d = rendered(record)
    step = owner(n, d, 1)
    assert step.rule == 'instance-facts' and step.fallback
    assert step.text == ('Instance fact used, derived using the premise below: Thing X. '
                         'The derivation also uses the local instance hypothesis inst_2: Nontrivial X.')


def test_applied_projection_is_explained_only_for_exact_modus_ponens():
    n, d = rendered(real('applied_projection'))
    step = owner(n, d, 0)
    assert step.rule == 'applied-projection' and not step.fallback
    assert step.text.startswith('Take the second conjunct, 1 < stateCount n d → hasSpectralGapAtLeast')
    # Real: the premise is printed in unfolded form, so the application is not checked.
    n, d = rendered(real('unchecked_application'))
    step = owner(n, d, 0)
    assert step.rule == 'unchecked-application' and step.fallback
    assert step.text.endswith('; that this gives the statement shown is not checked here.')


@pytest.mark.parametrize('objects,extra,explained', [
    # Synthetic: modus ponens with exact printing, an instantiation, and a premise printed differently.
    (['P → Q', 'R'], [(3, given('hp', 'P'))], True),
    (['∀ n, f n ≤ 1', 'R', 'm'], [], False),
    (['P → Q', 'R'], [(3, given('hp', 'P′'))], False),
])
def test_applied_projection_on_synthetic_frames(objects, extra, explained):
    statement = 'Q' if objects[0] == 'P → Q' else 'f m ≤ 1'
    record = synthetic(app('And.left', statement, (2, given('h', '(' + objects[0] + ') ∧ R')), *extra, objects=objects))
    n, d = rendered(record)
    [step] = d.declarations[0].steps
    assert step.rule == ('applied-projection' if explained else 'unchecked-application')
    assert step.fallback is not explained
    check_reading(record, d)


def test_exhibited_element_is_described_and_stays_a_gap():
    n, d = rendered(real('nonempty_construction'))
    [step] = d.declarations[0].steps
    assert step.rule == 'citation' and step.fallback
    assert step.text == 'Exhibit the element Machine.MainReduction.reduction m hm of GapReduction m; its construction is not expanded here.'
    # Synthetic: an element that is a variable of the local context is explained.
    record = synthetic(dict(role='introduce', binder='f', domain='T', statement='∀ (f : T), Nonempty T',
                            body=app('Nonempty.intro', 'Nonempty T', objects=['T', 'f'])))
    n, d = rendered(record)
    step = owner(n, d, 1)
    assert step.rule == 'nonempty-intro' and not step.fallback and step.text == 'Since f ∈ T, Nonempty T holds.'
    # Synthetic: the innermost f has another type, so the element is not that variable.
    record = synthetic(dict(role='introduce', binder='f', domain='T', statement='∀ (f : T) (f : S), Nonempty T',
                            body=dict(role='introduce', binder='f', domain='S', statement='∀ (f : S), Nonempty T',
                                      body=app('Nonempty.intro', 'Nonempty T', objects=['T', 'f']))))
    n, d = rendered(record)
    assert owner(n, d, 2).rule == 'citation' and owner(n, d, 2).fallback


# Regeneration across the version label.

def test_check_reading_accepts_only_a_listed_earlier_label_on_identical_output():
    record = json.loads((DATA/'bezout-snapshot.json').read_text())
    d = Narrative(record).document()
    d.declarations[0].axes['printer_version'] = 'source-math-en/0.4.2'
    check_reading(record, d)
    d.declarations[0].axes['printer_version'] = 'source-math-en/0.3.0'
    with pytest.raises(InvalidExport, match='regeneration'):
        check_reading(record, d)
    d.declarations[0].axes['printer_version'] = 'source-math-en/0.4.2'
    d.declarations[0].steps[0].text += ' Changed.'
    with pytest.raises(InvalidExport, match='regeneration'):
        check_reading(record, d)


@pytest.mark.parametrize('label', ['source-math-en/0.4.2', ['source-math-en/0.4.2'], None])
def test_earlier_label_is_refused_for_a_snapshot_without_a_retained_reading(label):
    # The text is exactly the current regeneration; only the label claims 0.4.2.
    # This real subtree has no listed retained 0.4.2 reading, so it is refused.
    record = real('norm_num')
    d = Narrative(record).document()
    check_reading(record, d)
    d.declarations[0].axes['printer_version'] = label
    with pytest.raises(InvalidExport, match='regeneration'):
        check_reading(record, d)
