"""Prevent a truncated frozen corpus from being measured as the complete one."""
from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil

import pytest

import proofreader.narrative as narrative_module


inspect_release = runpy.run_path(str(Path(__file__).with_name("inspect_release.py")))["inspect_release"]


def change(path, field, value):
    record = json.loads(path.read_bytes())
    record[field] = value
    path.write_text(json.dumps(record))


def manifest(site):
    entries = {p.relative_to(site).as_posix(): sha256(p.read_bytes()).hexdigest()
               for p in site.rglob("*") if p.is_file() and p.name != "SHA256SUMS.json"}
    (site / "SHA256SUMS.json").write_text(json.dumps(entries))


def test_audit_preserves_inventory_identity_and_printer(synthetic_release):
    report = inspect_release(synthetic_release)
    source = report["source_inventory"]
    assert report["snapshots"] == source["available_readings"] == 2
    assert source["expected_theorem_targets"] == 3
    assert source["missing_theorem_readings"] == 1
    assert report["frames"] == source["selected_frames"] == 2
    assert source["saved_explanation_gaps"] == 2
    assert source["saved_printer_versions"] == {narrative_module.PRINTER_VERSION: 2}
    assert report["printer_version"] == narrative_module.PRINTER_VERSION
    assert len(source["inventory_sha256"]) == 64
    assert source["internally_reconciled"]
    assert not source["saved_english_regenerated"]
    assert not source["source_replayed"]
    assert inspect_release(synthetic_release) == report


@pytest.mark.parametrize("missing", ["snapshot.json", "reading.json", "whole-bundle"])
def test_missing_input_cannot_shrink_the_audited_corpus(synthetic_release, missing):
    bundle = next((synthetic_release / "proofs").iterdir())
    if missing == "whole-bundle":
        shutil.rmtree(bundle)
    else:
        (bundle / missing).unlink()
    with pytest.raises(ValueError, match="inventory"):
        inspect_release(synthetic_release)


@pytest.mark.parametrize("field,value", [("proof_readings", 1), ("proof_readings", 0),
    ("expected_theorem_targets", 2), ("selected_checked_frames", 1),
    ("explicit_explanation_gaps", 0), ("configurations", 0), ("proof_readings", True)])
def test_inconsistent_saved_denominator_is_rejected(synthetic_release, field, value):
    change(synthetic_release / "coverage.json", field, value)
    with pytest.raises(ValueError):
        inspect_release(synthetic_release)


def test_empty_or_missing_release_is_rejected(tmp_path):
    with pytest.raises((ValueError, OSError)):
        inspect_release(tmp_path / "absent")
    with pytest.raises((ValueError, OSError)):
        inspect_release(tmp_path)


def test_snapshot_outside_canonical_inventory_is_rejected(synthetic_release):
    original = next((synthetic_release / "proofs").glob("*/snapshot.json"))
    shutil.copyfile(original, synthetic_release / "snapshot.json")
    with pytest.raises(ValueError, match="misplaced"):
        inspect_release(synthetic_release)


def test_saved_reading_must_belong_to_its_snapshot(synthetic_release):
    path = next((synthetic_release / "proofs").glob("*/reading.json"))
    record = json.loads(path.read_bytes())
    record["declarations"][0]["axes"]["snapshot_sha256"] = "0" * 64
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="identity"):
        inspect_release(synthetic_release)


def test_duplicate_snapshot_cannot_fill_a_missing_bundle(synthetic_release):
    first, second = list((synthetic_release / "proofs").iterdir())
    for name in ("snapshot.json", "reading.json"):
        shutil.copyfile(first / name, second / name)
    with pytest.raises(ValueError, match="identity"):
        inspect_release(synthetic_release)


def test_saved_gap_baseline_is_separate_from_current_renderer(synthetic_release, monkeypatch):
    original = narrative_module.Narrative.document

    def changed_reader(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        result.declarations[0].steps[0].fallback = False
        return result

    monkeypatch.setattr(narrative_module.Narrative, "document", changed_reader)
    report = inspect_release(synthetic_release)
    assert report["explanation_gaps"] == 0
    assert report["source_inventory"]["saved_explanation_gaps"] == 2


def test_manifest_verification_is_explicit_and_not_authentication(synthetic_release):
    manifest(synthetic_release)
    report = inspect_release(synthetic_release, verify_sha256sums=True)
    check = report["source_inventory"]["manifest"]
    assert check["verified"] and check["files_checked"] > 4
    assert not check["publisher_authenticated"]
    assert not inspect_release(synthetic_release)["source_inventory"]["manifest"]["verified"]


@pytest.mark.parametrize("mutation", ["hash", "omission", "extra-file"])
def test_manifest_requires_exact_file_inventory_and_bytes(synthetic_release, mutation):
    manifest(synthetic_release)
    path = synthetic_release / "SHA256SUMS.json"
    data = json.loads(path.read_bytes())
    if mutation == "hash":
        data["coverage.json"] = "0" * 64
    elif mutation == "omission":
        data.pop("coverage.json")
    else:
        (synthetic_release / "extra.txt").write_text("unlisted")
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Manifest"):
        inspect_release(synthetic_release, verify_sha256sums=True)
