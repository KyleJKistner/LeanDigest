"""Goal and local-fact navigation over an unchanged narrative snapshot.

This index does not infer mathematical dependencies from formula text. It records
source-tree inputs, lexical scopes, and explicit local-proof references. A missing
reference is never evidence that an assumption is unnecessary. Legacy `given`
frames have no binder index; ambiguous names remain unresolved.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from typing import Any

from .kernel import require
from .model import canonical_json
from .narrative import Snapshot

SCHEMA = 'leanglish.argument-index/v1'
PLAN_SCHEMA = 'leanglish.reading-plan/v1'
BINDERS = frozenset({'introduce', 'assume', 'have', 'define'})
REFERENCE_ROLES = frozenset({'given', 'local-application'})
MAX_PLAN_NODES = 1000


def _number(value: Any, size: int) -> bool:
    return type(value) is int and 0 <= value < size


def _scopes(snapshot: Snapshot) -> list[list[int]]:
    """The frame introducing each context slot, identified by its source occurrence."""
    scopes: list[list[int]] = [[] for _ in snapshot.frames]
    for frame in snapshot.frames:
        i = frame['id']
        if i:
            parent = snapshot.frames[snapshot.parents[i]]
            opens = parent['role'] in BINDERS and i == parent['children'][-1]
            scopes[i] = scopes[parent['id']] + ([parent['id']] if opens else [])
        actual = [{'name': snapshot.frames[j]['binder'], 'type': snapshot.frames[j]['domain']}
                  for j in scopes[i]]
        require(actual == frame['context'], 'Argument context differs from source binders')
    return scopes


def _reference(frame: dict, scope: list[int]) -> dict | None:
    if frame['role'] not in REFERENCE_ROLES:
        return None
    if frame['role'] == 'local-application':
        # Snapshot validates this positional index against the frozen context.
        return {'status': 'resolved', 'basis': 'local-index',
                'binder': scope[frame['local_index']], 'candidates': []}
    slots = [k for k, entry in enumerate(frame['context']) if entry['name'] == frame['binder']]
    if len(slots) == 1:
        return {'status': 'resolved', 'basis': 'unique-context-name',
                'binder': scope[slots[0]], 'candidates': []}
    return {'status': 'ambiguous' if slots else 'unresolved', 'basis': 'context-name',
            'binder': None, 'candidates': [scope[k] for k in slots]}


class ArgumentIndex:
    """A source index, not a second representation of the mathematical claims."""

    def __init__(self, record: dict):
        self.snapshot = Snapshot(record)
        self.scopes = _scopes(self.snapshot)
        self.references = [_reference(f, self.scopes[f['id']]) for f in self.snapshot.frames]

    def to_dict(self) -> dict:
        frames = self.snapshot.frames
        uses: dict[int, list[int]] = {f['id']: [] for f in frames if f['role'] in BINDERS}
        for i, ref in enumerate(self.references):
            if ref and ref['status'] == 'resolved':
                uses[ref['binder']].append(i)
        entry = 0
        while frames[entry]['role'] in {'introduce', 'assume'}:
            entry = frames[entry]['children'][0]
        bindings = []
        for frame in frames:
            if frame['role'] not in BINDERS:
                continue
            i = frame['id']
            bindings.append({'frame': i, 'body': frame['children'][-1],
                             'proof': frame['children'][0] if frame['role'] == 'have' else None,
                             'recorded_references': uses[i]})
        counts = Counter(ref['status'] for ref in self.references if ref)
        return {'schema': SCHEMA, 'snapshot_sha256': self.snapshot.sha256,
                'theorem': self.snapshot.record['theorem'], 'entry': entry,
                'nodes': [{'frame': f['id'], 'scope': list(self.scopes[f['id']]),
                           'reference': deepcopy(self.references[f['id']])} for f in frames],
                'bindings': bindings,
                'summary': {'frames': len(frames), 'binders': len(bindings),
                            'resolved_references': counts['resolved'],
                            'ambiguous_references': counts['ambiguous'],
                            'unresolved_references': counts['unresolved'],
                            'budget_cuts': sum(f['budget_cut'] for f in frames)},
                'claims': {'complete_hypothesis_usage': False,
                           'minimal_dependencies': False, 'english_certified': False,
                           'source_rechecked_here': False}}

    def plan(self, frames: list[int]) -> dict:
        plan = {'schema': PLAN_SCHEMA, 'snapshot_sha256': self.snapshot.sha256,
                'frames': list(frames)}
        validate_plan(self.snapshot.record, plan)
        return plan


def validate_index(record: dict, index: dict) -> dict:
    """Validate navigation against source contexts; no inference uses the index as evidence.

    Claims and source-child edges remain in `record`, not editable index fields.
    The direct-reference convention is checked separately from context structure.
    This is a Python consistency check, not a Lean certificate or authentication.
    """
    snapshot = Snapshot(record)
    frames = snapshot.frames
    require(isinstance(index, dict) and set(index) == {
        'schema', 'snapshot_sha256', 'theorem', 'entry', 'nodes', 'bindings', 'summary', 'claims'},
        'Unknown or missing argument-index fields')
    require(index['schema'] == SCHEMA and index['snapshot_sha256'] == snapshot.sha256
            and index['theorem'] == snapshot.record['theorem'], 'Argument source identity mismatch')
    nodes = index['nodes']
    require(isinstance(nodes, list) and len(nodes) == len(frames), 'Argument node inventory mismatch')
    for i, node in enumerate(nodes):
        require(isinstance(node, dict) and set(node) == {'frame', 'scope', 'reference'}
                and type(node['frame']) is int and node['frame'] == i, 'Invalid argument node')
        scope = node['scope']
        require(isinstance(scope, list) and all(_number(j, len(frames)) for j in scope),
                'Invalid argument scope')
        # Reconstruct the scope from ancestor BODY edges, not display names.
        chain, cursor = [], i
        while cursor in snapshot.parents:
            parent = frames[snapshot.parents[cursor]]
            if parent['role'] in BINDERS and cursor == parent['children'][-1]:
                chain.append(parent['id'])
            cursor = parent['id']
        chain.reverse()
        require(scope == chain, 'Argument scope changed or escaped')
        expected = _reference(frames[i], chain)
        require(canonical_json(node['reference']) == canonical_json(expected),
                'Local reference is not supported by the snapshot')
    bindings = index['bindings']
    expected_binders = [f['id'] for f in frames if f['role'] in BINDERS]
    require(isinstance(bindings, list) and len(bindings) == len(expected_binders),
            'Binding inventory mismatch')
    for binding, i in zip(bindings, expected_binders):
        f = frames[i]
        expected = {'frame': i, 'body': f['children'][-1],
                    'proof': f['children'][0] if f['role'] == 'have' else None,
                    'recorded_references': [j for j, node in enumerate(nodes)
                        if node['reference'] and node['reference']['status'] == 'resolved'
                        and node['reference']['binder'] == i]}
        require(canonical_json(binding) == canonical_json(expected), 'Binding record changed')
    entry = index['entry']
    require(_number(entry, len(frames)), 'Invalid argument entry')
    cursor = 0
    while frames[cursor]['role'] in {'introduce', 'assume'}:
        cursor = frames[cursor]['children'][0]
    require(entry == cursor, 'Argument entry omits proof structure')
    statuses = Counter(n['reference']['status'] for n in nodes if n['reference'])
    expected_summary = {'frames': len(frames), 'binders': len(bindings),
                        'resolved_references': statuses['resolved'],
                        'ambiguous_references': statuses['ambiguous'],
                        'unresolved_references': statuses['unresolved'],
                        'budget_cuts': sum(f['budget_cut'] for f in frames)}
    require(canonical_json(index['summary']) == canonical_json(expected_summary),
            'Argument summary mismatch')
    require(index['claims'] == {'complete_hypothesis_usage': False,
                               'minimal_dependencies': False, 'english_certified': False,
                               'source_rechecked_here': False}
            and all(type(v) is bool for v in index['claims'].values()),
            'Navigation must not claim mathematical certification or complete usage')
    return {'status': 'passed', 'frames': len(frames), 'source_rechecked_here': False,
            'english_certified': False}


def validate_plan(record: dict, plan: dict) -> list[dict]:
    """Resolve a reading itinerary. It is not a reordered proof or a proof of completeness.

    Every stop keeps the original local context, whatever order was requested.
    An AI planner can select stops but cannot supply replacement mathematical text.
    """
    snapshot = Snapshot(record)
    require(isinstance(plan, dict) and set(plan) == {'schema', 'snapshot_sha256', 'frames'},
            'A reading plan contains only source references')
    require(plan['schema'] == PLAN_SCHEMA and plan['snapshot_sha256'] == snapshot.sha256,
            'Reading plan belongs to a different snapshot')
    ids = plan['frames']
    require(isinstance(ids, list) and len(ids) <= MAX_PLAN_NODES
            and all(_number(i, len(snapshot.frames)) for i in ids), 'Invalid reading-plan frames')
    require(len(set(ids)) == len(ids), 'Reading plan repeats a frame')
    scopes = _scopes(snapshot)
    return [{'frame': i, 'path': list(snapshot.frames[i]['path']), 'scope': scopes[i],
             'statement': snapshot.frames[i]['statement'],
             'context': deepcopy(snapshot.frames[i]['context'])} for i in ids]
