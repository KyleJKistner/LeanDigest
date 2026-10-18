"""Independent regressions from unchanged published source-bound observations.

These tests replay the Python reader, not Lean. The files are byte-for-byte
copies from the v0.4.1 offline release; provenance.json binds their identity.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from proofreader.model import report, walk_steps
from proofreader.narrative import Narrative, check_reading, prose


FIXTURES = Path(__file__).parent / "fixtures"


def retained(name: str) -> dict:
    return json.loads((FIXTURES / name).read_bytes())


def owner(document, frame_id: int):
    declaration = document.declarations[0]
    identity = declaration.axes["frame_owners"][str(frame_id)]
    return next(s for s in walk_steps(declaration.steps) if s.id == identity)


def test_retained_observations_have_the_published_fixture_hashes():
    manifest = json.loads((FIXTURES / "provenance.json").read_text())
    for entry in manifest["fixtures"]:
        raw = (FIXTURES / entry["file"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["sha256"]
        record = json.loads(raw)
        assert record["theorem"] == entry["theorem"]
        assert len(record["frames"]) == entry["frames"]


@pytest.mark.parametrize(
    "filename,frame_id",
    [("diamond_distortion.snapshot.json", 7),
     ("diamond_distortion.snapshot.json", 20),
     ("infinite_matroid.snapshot.json", 41)],
)
def test_projection_followed_by_application_is_not_just_a_conjunct(filename, frame_id):
    record = retained(filename)
    original = deepcopy(record)
    frame = record["frames"][frame_id]
    assert frame["head"] in {"And.left", "And.right"}
    assert len(frame["objects"]) + len(frame["premises"]) > 3
    # DiamondDistortion instantiates four objects, then applies a premise.
    # InfiniteMatroid projects a negation and applies it to derive False.
    n = Narrative(record)
    d = n.document()
    step = owner(d, frame_id)
    assert step.fallback, (
        "An oversaturated projection still has an unexplained application; "
        f"{record['theorem']} f{frame_id}: {step.text!r} -> {step.conclusion!r}"
    )
    assert record == original
    assert set(n.owners) == set(range(len(record["frames"])))
    check_reading(record, d)


def test_negated_conjunct_is_not_described_as_itself_being_false():
    record = retained("infinite_matroid.snapshot.json")
    frame = record["frames"][41]
    assert frame["statement"] == "False"
    assert "∉" in frame["objects"][0]
    assert [p["argument"] for p in frame["premises"]] == [2, 3]
    step = owner(Narrative(record).document(), 41)
    assert step.fallback
    assert step.text != "Take the first conjunct."


@pytest.mark.parametrize("filename", ["diamond_distortion.snapshot.json", "infinite_matroid.snapshot.json"])
def test_plain_text_keeps_every_unexpanded_step_visible(filename):
    d = Narrative(retained(filename)).document()
    gaps = sum(s.fallback for s in walk_steps(d.declarations[0].steps))
    assert gaps > 0
    assert prose(d).count("[Explanation gap]") == gaps


def test_standalone_plain_text_keeps_its_evidence_boundary():
    d = Narrative(retained("diamond_distortion.snapshot.json")).document()
    text = prose(d).lower()
    assert "not formally verified" in text or "not certified" in text
    assert "does not authenticate" in text or "not authenticated" in text
    assert report(d)["checked_english_proofs"] == 0
    assert d.provenance["source_replayed_by_rendering"] is False


def test_branch_local_context_cannot_be_promoted_to_global_assumptions():
    record = retained("infinite_matroid.snapshot.json")
    # f39 introduces the negative alternative of the disjunction at f34.
    # Its child f40, and the negation application at f41, live only there.
    parent = record["frames"][34]
    assert parent["head"] == "Or.casesOn"
    assert record["frames"][39]["role"] == "assume"
    branch_domain = record["frames"][39]["domain"]
    d = Narrative(record).document()
    case_step = owner(d, 39)
    assert case_step.rule == "case"
    assert owner(d, 41).id in {s.id for s in walk_steps(case_step.children)}
    assert all(p["type"] != branch_domain for p in d.declarations[0].parameters)

