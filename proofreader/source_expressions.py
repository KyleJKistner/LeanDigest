"""Binder-aware views of source expressions; Lean, not Python, checks their types.

This module consumes the existing constructor DAG. It never parses printed
mathematics. Context binders are source occurrences, not expression-table rows or
names. The native replay is required before treating a derived lemma as checked.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from .kernel import Dag, EDGES, BINDERS, display_name, name_key, nat, plain_name, require
from .kernel_io import STANDARD_AXIOMS
from .model import canonical_json, digest

SCHEMA = 'leanglish.source-expressions/v1'
FRAME_FIELDS = {'path', 'context', 'type', 'term_kind', 'reference', 'proof_support',
                'claim_support', 'required_context', 'lifted_type', 'application', 'display'}
LOCAL_FIELDS = {'path', 'kind', 'name', 'binder', 'type', 'value', 'nondep'}
MAX_CONTEXT = 512
MAX_WALK = 1_000_000


def fields(value: Any, expected: set[str]) -> None:
    require(isinstance(value, dict) and set(value) == expected, 'Unexpected or missing expression fields')


def path(value: Any) -> tuple[int, ...]:
    require(isinstance(value, list) and len(value) <= 512, 'Invalid expression source path')
    require(all(type(i) is int and 0 <= i <= 2 for i in value), 'Invalid expression source edge')
    return tuple(value)


def slots(value: Any, size: int) -> list[int]:
    require(isinstance(value, list) and all(type(i) is int and 0 <= i < size for i in value),
            'Invalid context slot inventory')
    require(value == sorted(set(value)), 'Context slots must be distinct and ordered')
    return value


@dataclass(frozen=True)
class Binder:
    """An identity is valid only within the digest-bound expression bundle."""
    bundle: str
    owner: str
    path: tuple[int, ...]


class Expressions:
    def __init__(self, record: dict):
        fields(record, {'schema', 'name', 'lean_version', 'levels', 'axioms', 'statement', 'exprs', 'frames'})
        require(record['schema'] == SCHEMA, 'Unsupported source-expression schema')
        self.record = deepcopy(record)
        record = self.record
        name_key(record['name'])
        require(isinstance(record['lean_version'], str) and len(record['lean_version']) < 100,
                'Missing Lean version')
        require(isinstance(record['axioms'], list) and all(isinstance(a, str) for a in record['axioms']),
                'Invalid axiom inventory')
        require(len(set(record['axioms'])) == len(record['axioms']) and
                set(record['axioms']) <= STANDARD_AXIOMS, 'Disallowed or duplicate axiom')
        self.dag = Dag(record['exprs'], record['levels'])
        self._source_nodes = len(self.dag.nodes)
        self._free: dict[int, frozenset[int]] = {}
        self._remapped: dict[tuple[int, int, tuple[int, ...], int], int] = {}
        self.statement = self.dag.ref(record['statement'])
        require(self.dag.demand[self.statement] == 0, 'Source statement is not closed')
        self.frames = record['frames']
        require(isinstance(self.frames, list) and 0 < len(self.frames) <= 1000,
                'Invalid expression frame inventory')
        self.by_path: dict[tuple[int, ...], int] = {}
        self._binders: dict[tuple[int, ...], dict] = {}
        for i, frame in enumerate(self.frames):
            self._frame(i, frame)
        self.sha256 = digest(canonical_json(record))

    def free_indices(self, root: int) -> frozenset[int]:
        """Loose de Bruijn indices, computed on the DAG without expanding sharing."""
        self.dag.ref(root)
        todo = [(root, False)]
        count = 0
        while todo:
            count += 1
            require(count <= MAX_WALK, 'Expression support budget exceeded')
            i, ready = todo.pop()
            if i in self._free:
                continue
            node = self.dag.nodes[i]
            tag = node['tag']
            if not ready:
                todo.append((i, True))
                todo.extend((node[k], False) for k in EDGES.get(tag, ()))
                continue
            used = set()
            if tag == 'bvar':
                used.add(node['index'])
            for key in EDGES.get(tag, ()):
                values = self._free[node[key]]
                if key == 'body' and tag in {'lam', 'forall', 'let'}:
                    used.update(k - 1 for k in values if k > 0)
                else:
                    used.update(values)
            require(len(used) <= MAX_CONTEXT, 'Expression has too many context references')
            self._free[i] = frozenset(used)
        return self._free[root]

    def context_uses(self, root: int, size: int) -> list[int]:
        require(self.dag.demand[self.dag.ref(root)] <= size, 'Expression escapes its context')
        return sorted(size - 1 - k for k in self.free_indices(root))

    def _scoped_ref(self, value: Any, size: int) -> int:
        i = self.dag.ref(value)
        require(i < self._source_nodes, 'Reference points outside supplied expression inventory')
        self.context_uses(i, size)
        return i

    def _frame(self, i: int, f: dict) -> None:
        fields(f, FRAME_FIELDS)
        p = path(f['path'])
        require(p not in self.by_path, 'Duplicate source occurrence')
        self.by_path[p] = i
        ctx = f['context']
        require(isinstance(ctx, list) and len(ctx) <= MAX_CONTEXT, 'Invalid source context')
        preceding: tuple[int, ...] | None = None
        for k, c in enumerate(ctx):
            fields(c, LOCAL_FIELDS)
            cp = path(c['path'])
            require(c['kind'] in {'lambda', 'forall', 'let'}, 'Unknown source binder kind')
            body = cp + ((2,) if c['kind'] == 'let' else (1,))
            require(p[:len(body)] == body, 'Binder is not an ancestor body of the claim')
            require(preceding is None or cp[:len(preceding)] == preceding,
                    'Source context is not in ancestor order')
            preceding = body
            name_key(c['name'])
            require(c['binder'] in BINDERS, 'Unknown binder annotation')
            self._scoped_ref(c['type'], k)
            if c['kind'] == 'let':
                require(type(c['nondep']) is bool, 'Missing let dependency flag')
                self._scoped_ref(c['value'], k)
            else:
                require(c['value'] is None and c['nondep'] is None, 'Unexpected local definition')
            if cp in self._binders:
                require(self._same_binder(self._binders[cp], c), 'Source binder differs between frames')
            else:
                self._binders[cp] = c
        size = len(ctx)
        self._scoped_ref(f['type'], size)
        if not p:
            require(self.dag.equal(f['type'], self.statement), 'Root claim differs from declared statement')
        require(f['term_kind'] in {'app', 'lam', 'letE', 'fvar', 'const', 'proj'},
                'Unsupported proof-term kind')
        require(f['claim_support'] == self.context_uses(f['type'], size), 'Claim dependency inventory mismatch')
        direct = slots(f['proof_support'], size)
        slots(f['claim_support'], size)
        slots(f['required_context'], size)
        needed = set(direct) | set(f['claim_support'])
        pending = list(needed)
        while pending:
            slot = pending.pop()
            c = ctx[slot]
            for root in [c['type']] + ([c['value']] if c['value'] is not None else []):
                for dependency in self.context_uses(root, slot):
                    if dependency not in needed:
                        needed.add(dependency)
                        pending.append(dependency)
        require(f['required_context'] == sorted(needed), 'Dependency closure mismatch')
        if f['term_kind'] == 'fvar':
            require(type(f['reference']) is int and direct == [f['reference']], 'Local reference mismatch')
        else:
            require(f['reference'] is None, 'Unexpected local reference')
        self._scoped_ref(f['lifted_type'], 0)
        computed = self.close_claim(f)
        require(self.dag.equal(computed, f['lifted_type']), 'Lifted claim does not match its source context')
        fields(f['display'], {'claim', 'lifted'})
        require(all(isinstance(t, str) and len(t) < 1_000_000 for t in f['display'].values()),
                'Invalid display text')
        app = f['application']
        if f['term_kind'] != 'app':
            require(app is None, 'Non-application has inference arguments')
            return
        fields(app, {'head_path', 'head_type', 'constant', 'local', 'arguments'})
        args = app['arguments']
        require(isinstance(args, list) and 0 < len(args) <= 512, 'Invalid application argument inventory')
        require(path(app['head_path']) == p + (0,) * len(args), 'Application head path mismatch')
        self._scoped_ref(app['head_type'], size)
        if app['constant'] is not None:
            name_key(app['constant'])
            require(app['local'] is None, 'Application has two different heads')
        if app['local'] is not None:
            require(type(app['local']) is int and 0 <= app['local'] < size, 'Invalid local application head')
        for k, a in enumerate(args):
            fields(a, {'index', 'path', 'is_proof', 'type', 'value'})
            require(type(a['index']) is int and a['index'] == k, 'Application argument order mismatch')
            require(path(a['path']) == p + (0,) * (len(args) - k - 1) + (1,),
                    'Application argument path mismatch')
            require(type(a['is_proof']) is bool, 'Invalid argument classification')
            self._scoped_ref(a['type'], size)
            if a['is_proof']:
                require(a['value'] is None, 'Proof body must remain source-bound')
            else:
                self._scoped_ref(a['value'], size)

    def _same_binder(self, a: dict, b: dict) -> bool:
        for k in LOCAL_FIELDS - {'type', 'value'}:
            if a[k] != b[k]:
                return False
        if not self.dag.equal(a['type'], b['type']):
            return False
        return (a['value'] is None and b['value'] is None) or (
            a['value'] is not None and b['value'] is not None and self.dag.equal(a['value'], b['value']))

    def reindex(self, root: int, old_size: int, kept: tuple[int, ...], depth: int = 0) -> int:
        """Capture-avoiding context restriction; local bound variables are untouched."""
        require(type(old_size) is int and 0 <= old_size <= MAX_CONTEXT
                and type(depth) is int and 0 <= depth <= 512
                and all(type(k) is int and 0 <= k < old_size for k in kept)
                and list(kept) == sorted(set(kept)),
                'Invalid context restriction')
        self.dag.ref(root)
        if kept == tuple(range(old_size)):
            return root
        wanted = root, old_size, kept, depth
        todo = [(root, depth, False)]
        count = 0
        while todo:
            count += 1
            require(count <= MAX_WALK, 'Expression remapping budget exceeded')
            i, d, ready = todo.pop()
            require(d <= 512, 'Expression binder-depth budget exceeded')
            key = i, old_size, kept, d
            if key in self._remapped:
                continue
            node = self.dag.nodes[i]
            tag = node['tag']
            children = [(child, d + int(child == 'body' and tag in {'lam', 'forall', 'let'}))
                        for child in EDGES.get(tag, ())]
            if not ready:
                todo.append((i, d, True))
                todo.extend((node[child], child_depth, False) for child, child_depth in children)
                continue
            require(len(self._remapped) < MAX_WALK, 'Expression remapping budget exceeded')
            result = dict(node)
            if tag == 'bvar' and node['index'] >= d:
                slot = old_size - 1 - (node['index'] - d)
                require(slot in kept, 'Claim uses a removed context variable')
                result['index'] = d + len(kept) - 1 - kept.index(slot)
            for child, child_depth in children:
                result[child] = self._remapped[node[child], old_size, kept, child_depth]
            self._remapped[key] = self.dag.add(result)
        return self._remapped[wanted]

    def close_claim(self, f: dict) -> int:
        """Reconstruct the lifted type independently of Lean's closing procedure."""
        kept = tuple(f['required_context'])
        body = self.reindex(f['type'], len(f['context']), kept)
        for k in reversed(kept):
            c = f['context'][k]
            before = tuple(j for j in kept if j < k)
            typ = self.reindex(c['type'], k, before)
            if c['kind'] == 'let':
                value = self.reindex(c['value'], k, before)
                body = self.dag.add(dict(tag='let', name=c['name'], type=typ, value=value,
                                         body=body, nondep=c['nondep']))
            else:
                body = self.dag.add(dict(tag='forall', name=c['name'], domain=typ,
                                         body=body, binder=c['binder']))
        return body

    def resolve_variable(self, frame: int, root: int, occurrence: list[int], *,
                         owner: str = 'claim', context_size: int | None = None) -> Binder:
        """Resolve one bvar occurrence, including binders nested inside its type.

        The same DAG node can occur under different binders. Its row number is
        therefore never a binder identity. `owner` must distinguish expression roots.
        """
        require(type(frame) is int and 0 <= frame < len(self.frames), 'Invalid source frame')
        f = self.frames[frame]
        size = len(f['context']) if context_size is None else nat(context_size, len(f['context']))
        i = self._scoped_ref(root, size)
        require(isinstance(owner, str) and 0 < len(owner) < 200, 'Invalid expression owner')
        ids = [Binder(self.sha256, 'source', path(c['path'])) for c in f['context'][:size]]
        walked: tuple[int, ...] = ()
        for edge in path(occurrence):
            node = self.dag.nodes[i]
            children = EDGES.get(node['tag'], ())
            require(edge < len(children), 'Invalid expression occurrence')
            child = children[edge]
            if child == 'body' and node['tag'] in {'lam', 'forall', 'let'}:
                ids.append(Binder(self.sha256, f'{frame}:{owner}:{root}', walked))
            i = node[child]
            walked += (edge,)
        node = self.dag.nodes[i]
        require(node['tag'] == 'bvar' and node['index'] < len(ids), 'Occurrence is not a scoped variable')
        return ids[-1 - node['index']]

    def claim_shape(self, frame: int) -> dict:
        """Structural constructors only; unrecognized predicates stay as source atoms."""
        f = self.frames[nat(frame, len(self.frames) - 1)]
        root = f['type']
        node = self.dag.nodes[root]
        if node['tag'] == 'forall':
            return {'kind': 'forall', 'root': root, 'domain': node['domain'], 'body': node['body']}
        head, args = self.dag.app(root)
        h = self.dag.nodes[head]
        name = plain_name(h['name']) if h['tag'] == 'const' else None
        recognized = {'And': ('and', 2), 'Or': ('or', 2), 'Iff': ('iff', 2),
                      'Not': ('not', 1), 'Eq': ('eq', 3), 'HEq': ('heq', 4),
                      'Exists': ('exists', 2), 'True': ('true', 0), 'False': ('false', 0)}
        kind, arity = recognized.get(name, ('atom', -1))
        return {'kind': kind if len(args) == arity else 'atom', 'root': root,
                'head': head, 'arguments': args}

    def inference(self, frame: int) -> dict:
        f = self.frames[nat(frame, len(self.frames) - 1)]
        app = f['application']
        if app is None:
            return {'kind': 'reference' if f['reference'] is not None else 'source',
                    'path': list(f['path']), 'claim': f['type'], 'reference': f['reference']}
        return {'kind': 'application', 'path': list(f['path']), 'claim': f['type'],
                'head': {'path': list(app['head_path']), 'type': app['head_type'],
                         'constant': deepcopy(app['constant']), 'local': app['local']},
                'premises': [deepcopy(a) for a in app['arguments'] if a['is_proof']],
                'objects': [deepcopy(a) for a in app['arguments'] if not a['is_proof']]}

    def bind_snapshot(self, snapshot: dict) -> dict:
        from .narrative import Snapshot
        s = Snapshot(snapshot)
        # Snapshot names are Lean's original spelling, not the injective UI spelling.
        from .kernel import name_key
        components = name_key(self.record['name'])
        require(all(tag == 'str' and '.' not in value for tag, value in components),
                'Snapshot name spelling cannot express this structured declaration name')
        require('.'.join(value for _, value in components) == s.record['theorem'],
                'Snapshot declaration mismatch')
        require(self.record['lean_version'] == s.record['lean_version'], 'Snapshot version mismatch')
        require([f['path'] for f in self.frames] == [f['path'] for f in s.frames],
                'Snapshot frame inventory mismatch')
        from .argument_index import ArgumentIndex
        navigation = ArgumentIndex(s.record).to_dict()
        for i, f in enumerate(self.frames):
            require([c['path'] for c in f['context']] ==
                    [s.frames[j]['path'] for j in navigation['nodes'][i]['scope']],
                    'Snapshot binder identity mismatch')
        # Narrative alpha-renames local variables for display. Its inferred
        # child types may print differently even at the same source occurrence.
        # Native replay must regenerate the snapshot; Python does not certify
        # correspondence of these strings by guessing a substitution.
        return {'snapshot_sha256': s.sha256, 'expressions_sha256': self.sha256,
                'frames': len(self.frames), 'native_replay_performed_here': False,
                'display_differences': [i for i, f in enumerate(self.frames)
                                        if f['display']['claim'] != s.frames[i]['statement']],
                'english_certified': False}

    def summary(self) -> dict:
        return {'schema': 'leanglish.source-expressions-summary/v1', 'name': display_name(self.record['name']),
                'expressions_sha256': self.sha256, 'frames': len(self.frames),
                'expression_nodes': self._source_nodes,
                'applications': sum(f['application'] is not None for f in self.frames),
                'context_slots_removed': sum(len(f['context']) - len(f['required_context']) for f in self.frames),
                'native_replay_performed_here': False, 'english_certified': False}
