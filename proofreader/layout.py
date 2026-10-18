"""Independent binder-scope checks for the exact-DAG reading layout.

This checker imports neither the English printer nor its templates. It verifies
where a selected proof step may be placed, not the meaning of its English text.
Bindings are identified by occurrence paths in the original term, NOT by printed
names or shared DAG node numbers. Reusing a name/node in another branch must not
make that branch's hypothesis available here.
"""
from __future__ import annotations

from .kernel import Argument, EDGES, require
from .model import Document, Step


def check_layout(record: dict, document: Document) -> dict:
    """Reject escaped assumptions, dropped steps and invalid support links.

    Allowed compression: a prefix of root lambda binders becomes statement
    parameters or leading introductions; direct proof arguments can appear as
    earlier inferences with explicit support links. All other local binders
    remain nested. This is intentionally narrower than all valid mathematical
    exposition strategies. It is not a Lean type checker or an English theorem.
    """
    a = Argument(record)
    require(len(document.declarations) == 1, "Layout needs exactly one declaration")
    d = document.declarations[0]
    require(d.id == a.sha256[:20] and d.name == a.name, "Layout declaration identity mismatch")
    ids = {f"{d.id}:s{i}": i for i in range(len(a.steps))}
    paths = [tuple(s['path']) for s in a.steps]
    needs = []
    for path in paths:
        node = a.root
        bindings = set()
        for depth, edge in enumerate(path):
            expr = a.dag.nodes[node]
            tag = expr['tag']
            if (tag in {'lam', 'forall'} and edge == 1) or (tag == 'let' and edge == 2):
                bindings.add(path[:depth])
            node = expr[EDGES[tag][edge]]
        needs.append(frozenset(bindings))
    seen = set()
    completed = set()

    def index(identity: str) -> int:
        require(isinstance(identity, str) and identity in ids, "Unknown layout source-step identity")
        return ids[identity]

    def claim(i: int, available: frozenset) -> None:
        require(i not in seen, "Duplicated layout source step")
        require(needs[i] <= available, f"Escaped original binder scope at step {i}")
        seen.add(i)

    available = frozenset()
    cursor = 0
    for parameter in d.parameters:
        require(isinstance(parameter, dict), "Malformed statement parameter")
        i = index(parameter.get('source_step_id'))
        require(i == cursor, "Statement parameters are not a leading proof prefix")
        s = a.steps[i]
        n = a.dag.nodes[s['term']]
        require(n['tag'] == 'lam' and not s['truncated'] and len(s['children']) == 1,
                "A non-lambda step cannot become a statement parameter")
        claim(i, available)
        available = available | {paths[i]}
        completed.add(i)
        cursor = s['children'][0]

    def visit(step: Step, scope: frozenset, depth: int = 0,
              leading_intro: bool = False) -> None:
        require(depth <= 512, "Layout nesting budget exceeded")
        i = index(step.id)
        claim(i, scope)
        s = a.steps[i]
        node = a.dag.nodes[s['term']]
        require(isinstance(step.children, list) and isinstance(step.supports, list), "Malformed layout edges")
        child_ids = [index(child.id) for child in step.children]
        support_ids = [index(support) for support in step.supports]
        represented = child_ids + support_ids
        require(len(set(represented)) == len(represented), "Duplicated layout dependency")
        if leading_intro:
            require(node['tag'] == 'lam' and not s['truncated'] and not represented,
                    "Only a leading lambda may open a sequential proof scope")
        else:
            require(set(represented) == set(s['children']), "Layout omits or substitutes a supporting proof step")
        for support in support_ids:
            require(support in completed, "Layout support is not an earlier established subargument")
            require(needs[support] <= scope, "Support link imports a branch-local assumption")
        for child, child_id in zip(step.children, child_ids):
            child_scope = scope
            if node['tag'] == 'lam':
                require(paths[child_id] == paths[i] + (1,), "Invalid lambda-body layout")
                child_scope = scope | {paths[i]}
            elif node['tag'] == 'let' and paths[child_id] == paths[i] + (2,):
                child_scope = scope | {paths[i]}
            visit(child, child_scope, depth + 1)
        completed.add(i)

    for step in d.steps:
        i = index(step.id)
        s = a.steps[i]
        n = a.dag.nodes[s['term']]
        leading = i == cursor and n['tag'] == 'lam' and not s['truncated'] and not step.children
        visit(step, available, leading_intro=leading)
        if leading:
            available = available | {paths[i]}
            cursor = s['children'][0]
        else:
            cursor = None
    require(seen == set(range(len(a.steps))), "Layout did not account for every selected proof step")
    return {'schema': 'proofreader.layout-check/v1', 'selected_steps_accounted': len(seen),
            'binder_scopes_checked': True, 'earlier_support_links_checked': True,
            'typing_checked_here': False, 'english_formally_verified': False}
