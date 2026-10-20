"""Independent logical-rule falsifiers, using explicitly synthetic snapshots.

The expected mathematical relationships below are hand-checked propositional
ones. They do not import the renderer's formula matcher or assert a Lean run.
Every proof leaf is represented as an explicitly bound hypothesis, so a false
specialization cannot be excused by silently inventing an additional premise.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from proofreader.kernel import InvalidExport
from proofreader.model import walk_steps
from proofreader.narrative import Narrative, check_reading


def application_snapshot(head, objects, premises, goal):
    """A closed fixture with arbitrary propositions and explicit proof premises.

    premises is an ordered list of (application-slot, proposition) pairs.
    The returned index identifies the application beneath the root binders.
    """
    binders = [("P", "Prop", "introduce"), ("Q", "Prop", "introduce"),
               ("R", "Prop", "introduce")]
    binders += [(f"h{i}", statement, "assume")
                for i, (_, statement) in enumerate(premises)]
    app_id = len(binders)
    context = []
    frames = []

    def frame(i, path, role, statement, children=(), **extra):
        return dict(id=i, path=path, role=role, head="", statement=statement,
                    context=deepcopy(context), objects=[], premises=[],
                    children=list(children), budget_cut=False, **extra)

    statements = [goal]
    for name, domain, role in reversed(binders):
        if role == "introduce":
            statements.append(f"∀ ({name} : {domain}), {statements[-1]}")
        else:
            statements.append(f"({domain}) → {statements[-1]}")
    statements.reverse()
    for i, (name, domain, role) in enumerate(binders):
        frames.append(frame(i, [1] * i, role, statements[i], [i + 1],
                            binder=name, domain=domain))
        context.append(dict(name=name, type=domain))
    app_path = [1] * app_id
    node = frame(app_id, app_path, "application", goal)
    node["head"] = head
    node["objects"] = list(objects)
    arity = len(objects) + len(premises)
    for i, (slot, statement) in enumerate(premises):
        child_id = app_id + i + 1
        node["children"].append(child_id)
        node["premises"].append(dict(argument=slot, statement=statement, frame=child_id))
    frames.append(node)
    for i, (slot, statement) in enumerate(premises):
        assert 0 <= slot < arity
        child_id = app_id + i + 1
        path = app_path + [0] * (arity - slot - 1) + [1]
        frames.append(frame(child_id, path, "given", statement, binder=f"h{i}"))
    return dict(schema="proofreader.narrative/v1", theorem="Audit.synthetic_rule",
                lean_version="4.34.1", axioms=[], statement=statements[0],
                frames=frames, judgements_checked=len(frames),
                formula_backend="Lean pretty-printer"), app_id


def rendered_application(record, index):
    n = Narrative(record)
    d = n.document()
    identity = d.declarations[0].axes["frame_owners"][str(index)]
    step = next(s for s in walk_steps(d.declarations[0].steps) if s.id == identity)
    return n, d, step


# Each case conflicts with the advertised rule's exact premise/result contract.
# Some resulting implications happen to be provable by additional reasoning;
# that does not license silently substituting a different source inference.
INVALID_LOGIC = [
    ("Iff.mpr", ["P", "Q"], [(2, "P ↔ Q"), (3, "P")], "P"),
    ("Iff.mpr", ["P", "Q"], [(2, "P ↔ R"), (3, "Q")], "P"),
    ("Iff.mpr", ["P", "Q"], [(2, "P ↔ Q"), (3, "Q")], "R"),
    ("Iff.mpr", ["P → Q", "R"], [(2, "P → (Q ↔ R)"), (3, "R")], "P → Q"),
    ("Iff.mpr", ["P", "Q"], [(2, "P ↔ Q → R"), (3, "Q")], "P"),
    ("Iff.intro", ["P", "Q"], [(2, "P → Q"), (3, "P → Q")], "P ↔ Q"),
    ("Iff.intro", ["P", "Q"], [(2, "P → Q"), (3, "Q → R")], "P ↔ Q"),
    ("Iff.intro", ["P → Q", "R"], [(2, "P → Q → R"), (3, "R → P → Q")], "(P → Q) ↔ R"),
    ("Or.inl", ["P", "Q"], [(2, "Q")], "P ∨ Q"),
    ("Or.inr", ["P", "Q"], [(2, "P")], "P ∨ Q"),
    ("Or.inl", ["P", "Q"], [(2, "P")], "P ∧ Q"),
    ("Or.inr", ["P", "Q"], [(2, "Q")], "P ∧ Q"),
    ("Or.inl", ["P → Q", "R"], [(2, "P → Q")], "P → Q ∨ R"),
    ("False.elim", ["P"], [(1, "True")], "P"),
    ("False.elim", ["P"], [(1, "False")], "Q"),
    ("Not.intro", ["P ∧ Q"], [(1, "P ∧ Q → False")], "¬P ∧ Q"),
    ("Not.intro", ["P → Q"], [(1, "P → Q → False")], "¬(P → Q)"),
    ("Not.intro", ["P"], [(1, "P → Q")], "¬P"),
    ("Decidable.byContradiction", ["P", "inst"], [(2, "P → False")], "P"),
    ("Classical.byContradiction", ["P ∧ Q"], [(1, "¬P ∧ Q → False")], "P ∧ Q"),
    ("Classical.byContradiction", ["P"], [(1, "¬P → Q")], "P"),
    ("And.left", ["P", "Q"], [(2, "P ∨ Q")], "P"),
    ("And.right", ["P", "Q"], [(2, "P ∧ Q")], "P"),
    ("And.left", ["P ∨ Q", "R"], [(2, "P ∨ Q ∧ R")], "P ∨ Q"),
    ("And.left", ["P → Q", "R"], [(2, "P → Q ∧ R")], "P → Q"),
    ("And.right", ["P", "Q → R"], [(2, "P ∧ Q → R")], "Q → R"),
]


@pytest.mark.parametrize("head,objects,premises,goal", INVALID_LOGIC)
def test_wrong_direction_or_precedence_keeps_an_explanation_gap(head, objects, premises, goal):
    record, index = application_snapshot(head, objects, premises, goal)
    try:
        _, _, step = rendered_application(record, index)
    except InvalidExport:
        return
    assert step.fallback, f"Invalid {head} interpretation became an explained step: {step.text}"


VALID_LOGIC = [
    ("Iff.mpr", ["P", "Q"], [(2, "P ↔ Q"), (3, "Q")], "P"),
    ("Iff.intro", ["P", "Q"], [(2, "P → Q"), (3, "Q → P")], "P ↔ Q"),
    ("Or.inl", ["P", "Q"], [(2, "P")], "P ∨ Q"),
    ("Or.inr", ["P", "Q"], [(2, "Q")], "P ∨ Q"),
    ("False.elim", ["P"], [(1, "False")], "P"),
    ("Not.intro", ["P"], [(1, "P → False")], "¬P"),
    ("Decidable.byContradiction", ["P", "inst"], [(2, "¬P → False")], "P"),
    ("Classical.byContradiction", ["P"], [(1, "¬P → False")], "P"),
    ("And.left", ["P", "Q"], [(2, "P ∧ Q")], "P"),
    ("And.right", ["P", "Q"], [(2, "P ∧ Q")], "Q"),
]


@pytest.mark.parametrize("head,objects,premises,goal", VALID_LOGIC)
def test_simple_logical_controls_preserve_every_source_frame(head, objects, premises, goal):
    record, index = application_snapshot(head, objects, premises, goal)
    original = deepcopy(record)
    n, d, step = rendered_application(record, index)
    assert not step.fallback
    assert record == original
    assert set(n.owners) == set(range(len(record["frames"])))
    assert d.provenance["english_formally_verified"] is False
    assert d.provenance["receipt_authenticated"] is False
    check_reading(record, d)


@pytest.mark.parametrize("head,objects,premises,goal", VALID_LOGIC)
@pytest.mark.parametrize("mutation", ["extra_object", "wrong_path", "cut", "wrong_slot"])
def test_unproved_argument_inventory_is_not_hidden_by_a_logical_name(head, objects, premises, goal, mutation):
    record, index = application_snapshot(head, objects, premises, goal)
    frame = record["frames"][index]
    if mutation == "extra_object":
        frame["objects"].append("extra")
    elif mutation == "wrong_path":
        child = record["frames"][frame["children"][0]]
        # Keep a legal descendant of the application, but not its proof slot.
        child["path"] += [2]
    elif mutation == "cut":
        frame["budget_cut"] = True
    else:
        for premise in frame["premises"]:
            premise["argument"] += 1
    try:
        _, _, step = rendered_application(record, index)
    except InvalidExport:
        return
    assert step.fallback, f"{head} specialized a {mutation} frame"


@pytest.mark.parametrize("head,objects,premises,goal", VALID_LOGIC[:2])
def test_proof_children_cannot_swap_their_argument_roles(head, objects, premises, goal):
    record, index = application_snapshot(head, objects, premises, goal)
    frame = record["frames"][index]
    frame["children"].reverse()
    # The original premise inventory and source paths are preserved. Merely
    # reordering the display children must not reinterpret a directional proof.
    try:
        _, _, step = rendered_application(record, index)
    except InvalidExport:
        return
    assert step.fallback


@pytest.mark.parametrize("operand", ["P∧Q", "P ∧Q", "P∧ Q", "P→Q", "P∨Q", "P↔Q"])
def test_compact_connectives_do_not_extend_the_scope_of_negation(operand):
    # This falsifier caught a false specialization in the first implementation.
    # Lean's connective binding is not changed by omitting spaces: ¬P∧Q means
    # (¬P)∧Q. A tiny parser may refuse that notation; it may not pretend the
    # whole compact suffix is a single atomic proposition after the negation.
    record, index = application_snapshot("Not.intro", [operand], [(1, f"¬({operand})")], f"¬{operand}")
    try:
        _, _, step = rendered_application(record, index)
    except InvalidExport:
        return
    assert step.fallback, f"Negation silently changed scope: {step.text}"


@pytest.mark.parametrize("operand", ["P∧Q", "P ∧Q", "P→Q"])
def test_compact_negation_in_a_contradiction_premise_keeps_its_scope(operand):
    record, index = application_snapshot("Classical.byContradiction", [operand],
                                        [(1, f"¬{operand} → False")], operand)
    try:
        _, _, step = rendered_application(record, index)
    except InvalidExport:
        return
    assert step.fallback, f"Wrong contradiction assumption became a proof: {step.text}"

