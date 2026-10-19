"""Build the offline, curated Bézout companion. No Lean or network execution."""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from proofreader.source_text import EVIDENCE as TEXT_EVIDENCE, load_cancellations, cancellation_panel
from proofreader.model import canonical_json
from proofreader.narrative import Snapshot, check_reading
from proofreader.narrative_io import verify_certificates
from proofreader.render import embedded_json, html_document, load_document

THEOREM = "OAI.ComplexCancellation.BezoutFrame.exists_frame"
SOURCE = ROOT / "examples/openai/lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean"
EVIDENCE = ROOT / "artifacts/companion/native"
SOURCE_SHA256 = "d108afa98f200bfce183b8afc0af586b70734f7ad2cce1bc5e49853a2f555c6f"
SNAPSHOT_SHA256 = "e93e0455259fc3283983f3a47f956cdac4b1a28869bc5027bcc694b4a124d8d0"
LEAN_VERSION = "4.34.1"
MATHLIB_COMMIT = "d13f23b723b8a846827a245b89c10fc7d3f11612"


# Presentation headings are editorial data, not mathematical assertions. Shared
# labels keep the page, contents, and evidence dialog consistent.
HEADING_KEYS = frozenset({
    "page", "statement", "definitions", "proof", "example", "why", "evidence",
    *(f"step-{i}" for i in range(1, 7)),
})


def load_headings(path: Path = HERE / "headings.json") -> dict[str, str]:
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"Duplicate companion heading: {key}")
            result[key] = value
        return result

    headings = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
    if not isinstance(headings, dict) or headings.keys() != HEADING_KEYS:
        raise ValueError("Companion headings must include exactly the named page sections")
    if any(not isinstance(value, str) or not value or value != value.strip()
           or not value.isprintable() for value in headings.values()):
        raise ValueError("Companion headings must be nonempty, single-line text")
    return headings


HEADINGS = load_headings()

# Editorial correspondence, not a formal semantics for the curated English.
# The groups include the structural introduction/And/Exists frames as well as
# the displayed claims. Every retained frame belongs to exactly one group.
SECTIONS = [
    {"id": "statement", "title": HEADINGS["statement"], "lines": [11, 13], "frames": list(range(6)), "focus": 0},
    {"id": "step-1", "title": HEADINGS["step-1"], "lines": [15, 18], "frames": list(range(6, 24)), "focus": 17},
    {"id": "step-2", "title": HEADINGS["step-2"], "lines": [19, 29], "frames": list(range(24, 52)) + [84, 85], "focus": 40},
    {"id": "step-3", "title": HEADINGS["step-3"], "lines": [30, 34], "frames": list(range(52, 63)), "focus": 53},
    {"id": "step-4", "title": HEADINGS["step-4"], "lines": [35, 36], "frames": list(range(63, 70)), "focus": 67},
    {"id": "step-5", "title": HEADINGS["step-5"], "lines": [37, 41], "frames": list(range(70, 79)), "focus": 70},
    {"id": "step-6", "title": HEADINGS["step-6"], "lines": [42, 44], "frames": list(range(79, 84)), "focus": 79},
]


def build(output: Path = HERE / "index.html", evidence_root: Path = EVIDENCE,
          text_evidence_root: Path = TEXT_EVIDENCE) -> dict:
    source_text = load_cancellations(text_evidence_root)
    headings = load_headings()
    sections = [{**section, "title": headings[section["id"]]} for section in SECTIONS]
    source_bytes = SOURCE.read_bytes()
    if sha256(source_bytes).hexdigest() != SOURCE_SHA256:
        raise ValueError("Original source changed: review the prose and source-line correspondence before rebuilding")
    source = source_bytes.decode("utf-8")
    retained = evidence_root / "current"
    transport = (retained / "Extract.lean").read_text(encoding="utf-8")
    context = (retained / "Context.lean").read_text(encoding="utf-8")
    snapshot = Snapshot.read(retained / "snapshot.json")
    receipt = json.loads((retained / "receipt.json").read_text())
    reading = load_document((retained / "reading.json").read_bytes())
    certificates = json.loads((retained / "polynomial-certificates.json").read_text())
    native = json.loads((evidence_root / "observation.json").read_text())
    if snapshot.record["theorem"] != THEOREM or reading.declarations[0].name != THEOREM:
        raise ValueError("The retained record belongs to a different theorem")
    if receipt["snapshot_sha256"] != snapshot.sha256 or native["snapshot_sha256"] != snapshot.sha256:
        raise ValueError("Retained receipt and snapshot differ")
    if snapshot.sha256 != SNAPSHOT_SHA256:
        raise ValueError("Snapshot changed: review the editorial correspondence before rebuilding")
    if receipt["source_sha256"] != sha256(transport.encode()).hexdigest():
        raise ValueError("Retained transport does not match the receipt")
    if receipt["context_sha256"] != sha256(context.encode()).hexdigest():
        raise ValueError("Adapted context does not match the receipt")
    if native["original_source_sha256"] != SOURCE_SHA256:
        raise ValueError("Observation and original source differ")
    if source.split("namespace OAI", 1)[1] != context.split("namespace OAI", 1)[1]:
        raise ValueError("Original theorem body and adapted context differ")
    for record in (receipt, native):
        if record["status"] != "passed" or record["exact_openai_project_replayed"] is not False or record["english_formally_verified"] is not False:
            raise ValueError("Review the evidence language before changing the recorded checking scope")
    if receipt["all_selected_judgements_kernel_checked"] is not True or receipt["path_linkage_checked_in_lean"] is not True:
        raise ValueError("Recorded selected-claim checks are incomplete")
    if any(record["lean_version"] != LEAN_VERSION for record in (snapshot.record, receipt, native)) or native["mathlib_commit"] != MATHLIB_COMMIT:
        raise ValueError("Evidence differs from the reviewed Lean version or Mathlib revision")
    if native["scope"] != "fresh-pinned-adapted-context":
        raise ValueError("Unexpected checking scope")
    required_checks = ("current_export", "repeat_snapshot_exact", "wrong_path_rejected", "wrong_claim_rejected")
    if any(native["checks"].get(check) != "passed" for check in required_checks):
        raise ValueError("Native observation does not report every required check passing")
    for name in ("Context.lean", "Extract.lean", "snapshot.json", "receipt.json", "reading.json", "polynomial-certificates.json"):
        actual = sha256((retained / name).read_bytes()).hexdigest()
        if native["files"].get(f"current/{name}") != actual:
            raise ValueError(f"Native observation file identity differs: {name}")
    check_reading(snapshot.record, reading)
    verify_certificates(snapshot.record, certificates)
    grouped = [frame for section in sections for frame in section["frames"]]
    if sorted(grouped) != list(range(len(snapshot.frames))):
        raise ValueError("Editorial correspondence must account for each retained frame once")
    for section in sections:
        if section["focus"] not in section["frames"]:
            raise ValueError("Initial inspected claim is outside its section")
    data = {
        "theorem": THEOREM,
        "original_source": source,
        "original_source_sha256": SOURCE_SHA256,
        "original_source_path": str(SOURCE.relative_to(ROOT)),
        "transport_source": transport,
        "transport_source_sha256": receipt["source_sha256"],
        "context_source": context,
        "context_sha256": receipt["context_sha256"],
        "snapshot": snapshot.record,
        "snapshot_sha256": snapshot.sha256,
        "receipt": receipt,
        "certificates": certificates,
        "reading": reading.to_dict(),
        "sections": sections,
        "native_record": native,
        "curated_prose_formally_verified": False,
        "source_line_mapping": "editorially reviewed",
        "source_text": source_text,
    }
    reader_html = html_document(reading)
    data["deterministic_reader_html"] = reader_html
    replacements = {
        "__STYLE__": (HERE / "style.css").read_text(),
        "__APP__": (HERE / "app.js").read_text(),
        "__KATEX__": (HERE / "assets/katex.min.js").read_text(),
        "__DATA__": embedded_json(data),
        "__CANCELLATION_0__": cancellation_panel(source_text["sentences"][0], 40),
        "__CANCELLATION_1__": cancellation_panel(source_text["sentences"][1], 53),
    }
    replacements.update({
        "__HEADING_" + key.upper().replace("-", "_") + "__": escape(value)
        for key, value in headings.items()
    })
    template = (HERE / "template.html").read_text()
    rendered = re.sub("|".join(re.escape(key) for key in replacements),
                      lambda match: replacements[match[0]], template)
    if any(token in rendered for token in replacements) or re.search(r"__HEADING_[A-Z0-9_]+__", rendered):
        raise ValueError("Unreplaced companion template token")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    manifest = {
        "schema": "leanglish.curated-companion-build/v1",
        "theorem": THEOREM,
        "source_sha256": SOURCE_SHA256,
        "transport_sha256": receipt["source_sha256"],
        "snapshot_sha256": snapshot.sha256,
        "recorded_frames": len(snapshot.frames),
        "editorial_sections": len(sections),
        "curated_prose_formally_verified": False,
        "lean_executed_by_build": False,
        "network_requests_by_build": False,
        "native_record_embedded": True,
        "native_observation_sha256": sha256((evidence_root / "observation.json").read_bytes()).hexdigest(),
        "context_sha256": receipt["context_sha256"],
        "mathlib_commit": native["mathlib_commit"],
        "index_sha256": sha256(rendered.encode()).hexdigest(),
        "certified_source_sentences": 2,
        "source_text_record_sha256": source_text["record_sha256"],
        "source_text_observation_sha256": source_text["observation_sha256"],
    }
    output.with_name("build-manifest.json").write_text(canonical_json(manifest) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "index.html")
    parser.add_argument("--evidence-root", type=Path, default=EVIDENCE,
                        help="Native observation directory containing observation.json and current/ artifacts")
    parser.add_argument("--text-evidence-root", type=Path, default=TEXT_EVIDENCE)
    args = parser.parse_args()
    print(json.dumps(build(args.output, args.evidence_root, args.text_evidence_root), indent=2))
