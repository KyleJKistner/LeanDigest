"""Small internally consistent catalog; all observations are synthetic."""
from hashlib import sha256
import json

import pytest

from proofreader.narrative_io import write_bundle


@pytest.fixture
def synthetic_release(tmp_path):
    site = tmp_path / "site"
    module = "OAI.Audit.Example"
    source = "-- Synthetic source; no Lean execution.\n"
    for name in ("Audit.first", "Audit.second"):
        ident = sha256((module + "\0" + name).encode()).hexdigest()[:24]
        record = {"schema": "proofreader.narrative/v1", "theorem": name,
                  "lean_version": "4.34.1", "axioms": [], "statement": "True",
                  "judgements_checked": 1, "formula_backend": "Lean pretty-printer",
                  "frames": [{"id": 0, "path": [], "statement": "True", "role": "named",
                              "head": "Unexplained.audit", "context": [], "children": [],
                              "premises": [], "objects": [], "budget_cut": False}]}
        write_bundle(record, site / "proofs" / ident, source=source,
                     file="lean/" + module.replace(".", "/") + ".lean")
    (site / "coverage.json").write_text(json.dumps({
        "schema": "leanglish.finding-catalog/v1", "upstream_commit": "1" * 40,
        "proof_readings": 2, "expected_theorem_targets": 3, "configurations": 1,
        "selected_checked_frames": 2, "explicit_explanation_gaps": 2}))
    config = site / "originals/ComparatorChallenges/Audit.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"challenge_module": "ComparatorChallenges.Audit",
        "solution_module": module,
        "theorem_names": ["Audit.first", "Audit.second", "Audit.unread"],
        "definition_names": []}))
    original = site / "originals" / (module.replace(".", "/") + ".lean")
    original.parent.mkdir(parents=True)
    original.write_text(source)
    return site
