"""Versioned, evidence-labelled reading IR. Strings never constitute proof evidence."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any

SCHEMA = "proofreader.document/v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(data: str | bytes) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    line: int
    end_line: int
    column: int = 0


@dataclass
class Step:
    id: str
    rule: str
    text: str
    source: str = ""
    span: Span | None = None
    evidence: str = "source"
    references: list[str] = field(default_factory=list)
    supports: list[str] = field(default_factory=list)
    children: list[Step] = field(default_factory=list)
    conclusion: str | None = None
    context: list[dict[str, str]] = field(default_factory=list)
    term_id: str | None = None
    fallback: bool = False
    detail: str = ""


@dataclass
class Declaration:
    id: str
    name: str
    kind: str
    file: str
    statement: str
    source: str
    span: Span
    context: list[str] = field(default_factory=list)
    parameters: list[dict[str, str]] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: str = "source"
    dependencies: list[str] = field(default_factory=list)
    docstring: str = ""
    receipt: dict[str, Any] | None = None
    axes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    title: str
    files: list[dict[str, Any]]
    declarations: list[Declaration]
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    schema: str = SCHEMA
    generator: str = "lean-proofreader/0.3.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return canonical_json(self.to_dict()) + "\n"


def walk_steps(steps: list[Step]):
    for step in steps:
        yield step
        yield from walk_steps(step.children)


def report(document: Document) -> dict[str, Any]:
    """Keep syntactic rendering, Lean validation and semantic fidelity distinct."""
    declarations = document.declarations
    steps = [s for d in declarations for s in walk_steps(d.steps)]
    source_steps = [s for d in declarations if d.evidence == "source" for s in walk_steps(d.steps)]
    typed_steps = [s for d in declarations if d.evidence == "typed-export" for s in walk_steps(d.steps)]
    classified = sum(not s.fallback for s in source_steps)
    unique_steps = {s.id: s for s in steps}
    kernel_declarations = [d for d in declarations if d.axes.get("proof") == "path-bound-typed-judgements"]
    source_only = sum(d.evidence == "source" for d in declarations)
    return {
        "schema": "proofreader.coverage/v1",
        "files_indexed": len(document.files),
        "declaration_candidates": len(declarations),
        "declaration_discovery": ("mixed-source-and-exported" if 0 < source_only < len(declarations)
                                  else "source-heuristic" if source_only else "exported-or-empty"),
        "display_steps": len(steps),
        "typed_display_steps": len(typed_steps),
        "typed_display_steps_unexpanded": sum(s.fallback for s in typed_steps),
        "source_steps": len(source_steps),
        "source_steps_classified": classified,
        "source_steps_unclassified": len(source_steps) - classified,
        "source_character_classification": None,
        "source_character_classification_note": "Not measured: nested source spans overlap.",
        "source_only_declarations": source_only,
        "typed_export_declarations": sum(d.evidence == "typed-export" for d in declarations),
        "source_bound_snapshot_declarations": sum(d.evidence == "source-bound-snapshot" for d in declarations),
        "source_bound_snapshot_frames": sum(len(d.axes.get("frame_owners",{})) for d in declarations if d.evidence == "source-bound-snapshot"),
        "source_bound_polynomial_certificates": sum(d.axes.get("polynomial_certificates",0) for d in declarations if d.evidence == "source-bound-snapshot"),
        "source_bound_unexpanded_steps": sum(s.fallback for d in declarations if d.evidence == "source-bound-snapshot" for s in walk_steps(d.steps)),
        "successful_local_lean_receipts": 0,
        "receipt_trust_note": "Imported receipts are not authenticated. Attached observations are reported separately.",
        "attached_passed_receipt_records": sum(bool(d.receipt and d.receipt.get("status") == "passed") for d in declarations),
        "unique_display_step_ids": len(unique_steps),
        "path_bound_kernel_declarations": len(kernel_declarations),
        "checked_english_proofs": 0,
        "readability_human_evaluated": False,
        "unclassified_rules": sorted({s.rule for s in steps if s.fallback}),
        "limitations": [
            "Source classification is not semantic explanation coverage.",
            "A build receipt does not establish fidelity of English or paper-to-Lean correspondence.",
            "Source discovery is heuristic; custom command-generated declarations need the Lean exporter.",
        ],
    }
