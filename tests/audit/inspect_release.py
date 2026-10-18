"""Read-only audit of an extracted frozen Leanglish release.

Run from a checkout with:
  python tests/audit/inspect_release.py /path/to/Leanglish

The JSON report contains observations of this Python renderer, not Lean replay,
English certification, or evidence that any upstream theorem is false.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import proofreader.narrative as narrative_module
from proofreader.catalog_inputs import config_inventory, read_json, safe_child
from proofreader.model import canonical_json, walk_steps
from proofreader.narrative import Narrative, prose
from proofreader.render import load_document


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_manifest(root: Path) -> dict:
    """Check the entire saved manifest, without authenticating its publisher."""
    path = safe_child(root, "SHA256SUMS.json")
    entries = read_json(path)
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Empty or invalid SHA256SUMS.json")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*")
              if p.is_file() and p != path}
    if set(entries) != actual:
        raise ValueError("Manifest and release file inventories differ")
    for name, expected in entries.items():
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid manifest SHA-256")
        if file_hash(safe_child(root, name)) != expected:
            raise ValueError("Manifest SHA-256 mismatch: " + name)
    return {"file": "SHA256SUMS.json", "sha256": file_hash(path),
            "files_checked": len(entries), "verified": True,
            "publisher_authenticated": False}


def inspect_release(root: Path, *, verify_sha256sums: bool = False) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("Root must be an extracted release directory")
    coverage_path = safe_child(root, "coverage.json")
    coverage = read_json(coverage_path)
    if not isinstance(coverage, dict) or coverage.get("schema") != "leanglish.finding-catalog/v1":
        raise ValueError("Missing or invalid release coverage schema")
    for field in ("proof_readings", "expected_theorem_targets", "selected_checked_frames",
                  "explicit_explanation_gaps", "configurations"):
        if type(coverage.get(field)) is not int or coverage[field] < 0:
            raise ValueError("Invalid release denominator: " + field)
    if not 0 < coverage["proof_readings"] <= coverage["expected_theorem_targets"]:
        raise ValueError("Empty or inconsistent release reading denominator")
    config_paths = sorted((root / "originals/ComparatorChallenges").glob("*.json"))
    for path in config_paths:
        safe_child(root, path.relative_to(root).as_posix())
    configs = config_inventory(safe_child(root, "originals"))
    targets = {(c["solution_module"], name) for c in configs.values()
               for name in c.get("theorem_names", [])}
    if (len(configs) != coverage["configurations"]
            or len(targets) != coverage["expected_theorem_targets"]):
        raise ValueError("Release denominator differs from comparison configuration inventory")
    paths = sorted((root / "proofs").glob("*/snapshot.json"))
    readings = sorted((root / "proofs").glob("*/reading.json"))
    if len(paths) != coverage["proof_readings"] or len(readings) != len(paths):
        raise ValueError("Snapshot/reading inventory differs from release coverage")
    if ({p.parent for p in paths} != {p.parent for p in readings}
            or set(paths) != set(root.rglob("snapshot.json"))
            or set(readings) != set(root.rglob("reading.json"))):
        raise ValueError("Snapshot/reading inventories differ or contain misplaced inputs")
    manifest = verify_manifest(root) if verify_sha256sums else {
        "file": "SHA256SUMS.json", "verified": False,
        "present": (root / "SHA256SUMS.json").is_file(), "publisher_authenticated": False}
    inventory_files = {"coverage.json": file_hash(coverage_path)}
    for path in config_paths:
        inventory_files[path.relative_to(root).as_posix()] = file_hash(path)
    identities = set()
    saved_printers = Counter()
    saved_gaps = 0
    observations = []
    total_frames = total_gaps = cuts = missing_markers = 0
    reader_path = Path(narrative_module.__file__)
    for path in paths:
        path = safe_child(root, path.relative_to(root).as_posix())
        reading_path = safe_child(root, (path.parent / "reading.json").relative_to(root).as_posix())
        record = read_json(path)
        n = Narrative(record)
        saved_document = load_document(reading_path.read_bytes())
        if len(saved_document.declarations) != 1:
            raise ValueError("A release reading must contain exactly one declaration")
        saved = saved_document.declarations[0]
        if not saved.file.startswith("lean/OAI/") or not saved.file.endswith(".lean"):
            raise ValueError("Reading has no solution module identity")
        key = (saved.file[5:-5].replace("/", "."), record["theorem"])
        ident = hashlib.sha256("\0".join(key).encode()).hexdigest()[:24]
        if (key not in targets or key in identities or path.parent.name != ident
                or saved.name != record["theorem"]
                or saved.axes.get("snapshot_sha256") != n.snapshot.sha256):
            raise ValueError("Mismatched or duplicate reading/snapshot identity")
        identities.add(key)
        saved_steps = {s.id: s for s in walk_steps(saved.steps)}
        owners = saved.axes.get("frame_owners", {})
        prefix = set()
        index = 0
        while record["frames"][index]["role"] in {"introduce", "assume"}:
            prefix.add(str(index))
            index = record["frames"][index]["children"][0]
        if (set(owners) != {str(i) for i in range(len(record["frames"]))}
                or not set(owners.values()) <= set(saved_steps) | {"statement"}
                or {k for k, owner in owners.items() if owner == "statement"} != prefix):
            raise ValueError("Saved reading does not own every source frame")
        printer = saved.axes.get("printer_version")
        if not isinstance(printer, str) or not printer:
            raise ValueError("Saved reading has no printer version")
        saved_printers[printer] += 1
        saved_gaps += sum(s.fallback for s in saved_steps.values())
        for source in (path, reading_path):
            inventory_files[source.relative_to(root).as_posix()] = file_hash(source)
        document = n.document()
        steps = {step.id: step for step in walk_steps(document.declarations[0].steps)}
        if set(n.owners) != set(range(len(record["frames"]))):
            raise AssertionError(f"Unowned source frame in {record['theorem']}")
        count = sum(step.fallback for step in steps.values())
        total_frames += len(record["frames"])
        total_gaps += count
        cuts += sum(frame["budget_cut"] for frame in record["frames"])
        missing_markers += prose(document).count("[Explanation gap]") != count
        for frame in record["frames"]:
            if (frame["head"] not in {"And.left", "And.right"}
                    or len(frame["objects"]) + len(frame["premises"]) <= 3):
                continue
            step = steps[n.owners[frame["id"]]]
            observations.append({
                "theorem": record["theorem"],
                "snapshot": str(path.relative_to(root)),
                "frame_id": frame["id"],
                "source_path": frame["path"],
                "head": frame["head"],
                "total_arguments": len(frame["objects"]) + len(frame["premises"]),
                "premise_slots": [p["argument"] for p in frame["premises"]],
                "fallback": step.fallback,
                "text": step.text,
                "conclusion": frame["statement"],
            })
    if total_frames != coverage["selected_checked_frames"]:
        raise ValueError("Frame count differs from release coverage")
    if saved_gaps != coverage["explicit_explanation_gaps"]:
        raise ValueError("Saved reading gap count differs from release coverage")
    inventory = dict(sorted(inventory_files.items()))
    return {
        "schema": "leanglish.independent-reader-audit/v1",
        "reader_sha256": file_hash(reader_path),
        "printer_version": narrative_module.PRINTER_VERSION,
        "source_inventory": {
            "coverage_schema": coverage["schema"],
            "recorded_upstream_commit": coverage.get("upstream_commit"),
            "coverage_sha256": inventory["coverage.json"],
            "inventory_sha256": hashlib.sha256(canonical_json(inventory).encode()).hexdigest(),
            "inventory_files": inventory,
            "configurations": len(configs), "expected_theorem_targets": len(targets),
            "available_readings": len(paths), "missing_theorem_readings": len(targets) - len(paths),
            "selected_frames": total_frames, "saved_explanation_gaps": saved_gaps,
            "saved_printer_versions": dict(sorted(saved_printers.items())),
            "internally_reconciled": True, "manifest": manifest,
            "saved_english_regenerated": False, "source_replayed": False,
        },
        "snapshots": len(paths),
        "frames": total_frames,
        "explanation_gaps": total_gaps,
        "budget_cut_frames": cuts,
        "plain_text_marker_mismatches": missing_markers,
        "oversaturated_projection_frames": len(observations),
        "oversaturated_projection_readings": len({x["theorem"] for x in observations}),
        "unmarked_oversaturated_projections": sum(not x["fallback"] for x in observations),
        "observations": observations,
        "native_lean_executed": False,
        "english_formally_verified": False,
        "observations_authenticated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--verify-manifest", action="store_true",
                        help="Verify every file against saved SHA256SUMS.json (not authentication)")
    args = parser.parse_args()
    try:
        result = inspect_release(args.root, verify_sha256sums=args.verify_manifest)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
