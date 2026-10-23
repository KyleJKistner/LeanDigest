"""Plans for source-bound lemma extraction and whole-proof reconstruction.

Plans contain source references, not replacement assertions. Python validates
scope/graph consistency; only the separate native run checks mathematical types.
"""
from __future__ import annotations

from copy import deepcopy

from .kernel import require, name_key
from .model import canonical_json
from .source_expressions import Expressions, fields

PLAN_SCHEMA = 'leanglish.proof-decomposition-plan/v1'
RESULT_SCHEMA = 'leanglish.proof-decomposition-result/v1'


def _prefix(a: tuple[int, ...], b: tuple[int, ...]) -> bool:
    return b[:len(a)] == a


def make_plan(record: dict, selected: list[int]) -> dict:
    view = Expressions(record)
    plan = {'schema': PLAN_SCHEMA, 'expressions_sha256': view.sha256, 'frames': deepcopy(selected)}
    validate_plan(record, plan)
    return plan


def validate_plan(record: dict, plan: dict) -> dict:
    """Check source identity, distinct non-root selections, and dependency order.

    An inner selected occurrence precedes a containing selected occurrence.
    This is an extraction schedule, not permission to move an open assumption.
    """
    view = Expressions(record)
    fields(plan, {'schema', 'expressions_sha256', 'frames'})
    require(plan['schema'] == PLAN_SCHEMA and plan['expressions_sha256'] == view.sha256,
            'Decomposition plan belongs to a different expression bundle')
    ids = plan['frames']
    require(isinstance(ids, list) and len(ids) <= 1000
            and all(type(i) is int and 0 <= i < len(view.frames) for i in ids),
            'Invalid decomposition frame inventory')
    require(len(set(ids)) == len(ids), 'Duplicate decomposition frame')
    require(all(view.frames[i]['path'] for i in ids), 'Root is not an intermediate lemma')
    paths = [tuple(f['path']) for f in view.frames]
    for k, i in enumerate(ids):
        require(not any(_prefix(paths[j], paths[i]) for j in ids[:k]),
                'Selected inner lemma must precede containing lemma')
    return {'plans_checked': 1, 'selected_lemmas': len(ids),
            'native_check_performed_here': False, 'english_certified': False}


def frontier(record: dict, selected: list[int], owner: int | None) -> list[int]:
    """Nearest selected descendants; not all dependencies of the original proof."""
    paths = [tuple(f['path']) for f in record['frames']]
    here = () if owner is None else paths[owner]
    below = [i for i in selected if paths[i] != here and _prefix(here, paths[i])]
    return sorted([i for i in below if not any(
        j != i and _prefix(paths[j], paths[i]) for j in below)], key=lambda i: paths[i])


def exhaustive_plan(record: dict, *, reverse_siblings: bool = False) -> dict:
    """Stress-test schedule. Extracting every source step is not useful exposition."""
    require(type(reverse_siblings) is bool, 'Invalid sibling-order flag')
    view = Expressions(record)
    ids = [i for i, f in enumerate(view.frames) if f['path']]
    # Reversing same-depth order tests independent reordering; depth stays descending.
    ids.sort(key=lambda i: tuple(view.frames[i]['path']), reverse=reverse_siblings)
    ids.sort(key=lambda i: -len(view.frames[i]['path']))
    return make_plan(record, ids)


def suggest_plan(record: dict, snapshot: dict, *, limit: int = 8) -> dict:
    """Select local facts and calculations by source structure, not theorem names.

    This is a deterministic starting point for review, not a measured claim of
    explanatory importance. No candidate means an explicit empty selection.
    """
    require(type(limit) is int and 0 <= limit <= 100, 'Invalid lemma-selection limit')
    view = Expressions(record)
    view.bind_snapshot(snapshot)
    candidates = set()
    for i, f in enumerate(snapshot['frames']):
        if f['role'] == 'have' and f['children']:
            candidates.add(f['children'][0])
        elif f['role'] in {'cancel', 'chain'}:
            candidates.add(i)
    ids = sorted(i for i in candidates if view.frames[i]['path'])[:limit]
    ids.sort(key=lambda i: (-len(view.frames[i]['path']), tuple(view.frames[i]['path'])))
    return make_plan(record, ids)


def _child_name(namespace: dict, suffix: str) -> dict:
    return {'tag': 'str', 'prefix': deepcopy(namespace), 'value': suffix}


def validate_result(record: dict, plan: dict, result: dict, namespace: dict) -> dict:
    """Reconcile a native observation, without treating loading as kernel checking."""
    validate_plan(record, plan)
    require(bool(name_key(namespace)), 'Missing decomposition namespace')
    view = Expressions(record)
    fields(result, {'schema', 'source', 'selection', 'lemmas', 'root_uses', 'result',
                    'statement', 'source_kernel_judgements', 'composition_kernel_judgements',
                    'source_axioms', 'result_axioms', 'english_certified'})
    require(result['schema'] == RESULT_SCHEMA and result['source'] == record['name'],
            'Decomposition result belongs to another source')
    require(canonical_json(result['selection']) == canonical_json(plan['frames']),
            'Decomposition selection changed')
    require(result['result'] == _child_name(namespace, 'result'), 'Result declaration changed')
    require(() in view.by_path, 'The original declared statement must be included')
    require(result['statement'] == view.frames[view.by_path[()]]['display']['claim'],
            'Original theorem statement changed')
    expected_count = 1 + sum(2 + (len(f['application']['arguments']) + 1
                                  if f['application'] else 0) for f in view.frames)
    require(type(result['source_kernel_judgements']) is int
            and result['source_kernel_judgements'] == expected_count,
            'Source replay inventory mismatch')
    require(type(result['composition_kernel_judgements']) is int
            and result['composition_kernel_judgements'] == 2 * len(plan['frames']) + 1,
            'Composition checking inventory mismatch')
    require(result['english_certified'] is False, 'Decomposition does not certify prose')
    require(result['source_axioms'] == record['axioms'], 'Source axiom inventory changed')
    axioms = result['result_axioms']
    require(isinstance(axioms, list) and all(isinstance(a, str) for a in axioms)
            and len(set(axioms)) == len(axioms) and set(axioms) <= set(record['axioms']),
            'New or invalid result axiom')
    ids = plan['frames']
    require(isinstance(result['lemmas'], list) and len(result['lemmas']) == len(ids),
            'Extracted lemma inventory mismatch')
    for row, i in zip(result['lemmas'], ids):
        f = view.frames[i]
        expected = {'frame': i, 'path': f['path'], 'name': _child_name(namespace, 'lemma_' + str(i)),
                    'uses': frontier(record, ids, i), 'required_context': f['required_context'],
                    'signature': f['display']['lifted']}
        require(canonical_json(row) == canonical_json(expected), 'Extracted lemma record changed')
    require(canonical_json(result['root_uses']) == canonical_json(frontier(record, ids, None)),
            'Root replacement frontier changed')
    return {'lemmas_reconciled': len(ids), 'native_check_performed_here': False,
            'english_certified': False}
