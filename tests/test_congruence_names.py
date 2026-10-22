"""Fresh display-name regression tests; synthetic snapshots, not Lean evidence."""
from copy import deepcopy

import pytest

from proofreader.model import walk_steps
from proofreader.narrative import Narrative, check_reading
from proofreader.narrative_checks import ReadingChecks


def subscript_name(n):
    return 't' + str(n).translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉'))


def preferred_names(n):
    return ['t', 's', 'u', 'v'] + [subscript_name(k) for k in range(1, n + 1)]


def checks(names, function='LE.le a'):
    value = ReadingChecks()
    value.frames = {0: {'objects': [function],
                        'context': [{'name': name, 'type': 'ℕ'} for name in names]}}
    return value


@pytest.mark.parametrize('names,expected', [
    ([], 't'), (['t'], 's'), (['t', 's', 'v'], 'u'),
    (preferred_names(0), 't₁'), (preferred_names(9), 't₁₀'),
    (preferred_names(150), 't₁₅₁'),
])
def test_congruence_uses_the_first_unoccupied_display_name(names, expected):
    reader = checks(names)
    before = deepcopy(reader.frames)
    assert reader.function_text(0) == f'{expected} ↦ a ≤ {expected}'
    assert reader.function_text(0) == f'{expected} ↦ a ≤ {expected}'
    assert reader.frames == before


def test_names_in_the_function_are_reserved_as_well_as_context_names():
    reader = checks(preferred_names(9), 'LE.le t₁₀')
    assert reader.function_text(0) == 't₁₁ ↦ t₁₀ ≤ t₁₁'


def test_existing_source_fallback_does_not_require_a_fresh_name():
    assert checks(preferred_names(150), 'f').function_text(0) == 'f'


def congruence_snapshot(names):
    """A format fixture for congrArg (LE.le a) h under additional Nat binders."""
    frames = []
    binders = [('a', 'ℕ', 'introduce'), ('b', 'ℕ', 'introduce'),
               ('c', 'ℕ', 'introduce'), ('h', 'b = c', 'assume')]
    binders += [(name, 'ℕ', 'introduce') for name in names]
    conclusion = '(a ≤ b) = (a ≤ c)'

    def statement(k):
        text = conclusion
        for name, kind, role in reversed(binders[k:]):
            text = f'∀ ({name} : {kind}), {text}' if role == 'introduce' else f'{kind} → {text}'
        return text

    context, path = [], []
    for k, (name, kind, role) in enumerate(binders):
        frames.append(dict(id=k, path=path, role=role, head='', statement=statement(k),
                           context=deepcopy(context), children=[k + 1], premises=[], objects=[],
                           binder=name, domain=kind, budget_cut=False))
        context.append(dict(name=name, type=kind))
        path = path + [1]
    i = len(frames)
    frames.append(dict(id=i, path=path, role='congruence', head='congrArg',
                       statement=conclusion, context=deepcopy(context), children=[i + 1],
                       premises=[dict(argument=5, frame=i + 1, statement='b = c')],
                       objects=['ℕ', 'Prop', 'b', 'c', 'LE.le a'], budget_cut=False))
    frames.append(dict(id=i + 1, path=path + [1], role='given', head='',
                       statement='b = c', context=deepcopy(context), children=[], premises=[],
                       objects=[], binder='h', budget_cut=False))
    return dict(schema='proofreader.narrative/v1', theorem='Synthetic.freshCongruence',
                lean_version='4.34.1', axioms=[], statement=frames[0]['statement'],
                frames=frames, judgements_checked=len(frames), formula_backend='Lean pretty-printer')


def test_full_document_renders_when_the_original_thirteen_names_are_occupied():
    record = congruence_snapshot(preferred_names(9))
    before = deepcopy(record)
    reader = Narrative(record)
    document = reader.document()
    steps = list(walk_steps(document.declarations[0].steps))
    assert any(step.text == 'Apply t₁₀ ↦ a ≤ t₁₀ to both sides of the supplied equality.'
               for step in steps)
    assert len(reader.owners) == len(record['frames'])
    check_reading(record, document)
    assert Narrative(record).document().to_json() == document.to_json()
    assert record == before
