"""Independent counterexamples for the report's source and denominator claims."""
from hashlib import sha256
import json

import pytest

from proofreader.explanation_gaps import collect


def test_missing_reader_page_cannot_be_a_review_link(synthetic_release):
    next((synthetic_release / "proofs").glob("*/reader.html")).unlink()
    with pytest.raises(ValueError, match="reader page"):
        collect(synthetic_release)


def test_lowered_coverage_cannot_erase_unread_targets(synthetic_release):
    path = synthetic_release / "coverage.json"
    data = json.loads(path.read_bytes())
    data["expected_theorem_targets"] = data["proof_readings"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="configuration inventory"):
        collect(synthetic_release)


def test_canonical_directory_cannot_turn_a_specification_into_a_solution(synthetic_release):
    path = next((synthetic_release / "proofs").glob("*/reading.json"))
    data = json.loads(path.read_bytes())
    declaration = data["declarations"][0]
    declaration["file"] = "lean/ComparatorChallenges/Audit.lean"
    path.write_text(json.dumps(data))
    ident = sha256(("ComparatorChallenges.Audit\0" + declaration["name"]).encode()).hexdigest()[:24]
    path.parent.rename(path.parent.with_name(ident))
    with pytest.raises(ValueError, match="proof identity|module identity"):
        collect(synthetic_release)


def test_source_text_must_match_the_saved_solution(synthetic_release):
    source = synthetic_release / "originals/OAI/Audit/Example.lean"
    source.write_text("-- An unrelated source file.\n")
    with pytest.raises(ValueError, match="source differs"):
        collect(synthetic_release)
