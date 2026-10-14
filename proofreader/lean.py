"""Explicitly opt-in local Lean execution and evidence receipts.

Never called by the browser upload API. Lean elaboration can execute arbitrary
IO; --trust-project is informed consent, not a sandbox. Isolate untrusted
projects in a disposable container without credentials or network access.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
from contextlib import contextmanager
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from typing import Any
from .core import export_document, replay_source, validate_export
from .model import Document, digest

PREFIX = "PROOFREADER_JSON:"
MODULE_RE = re.compile(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*")
EXCLUDES = {".git", ".lake", "_proofreader_cache", ".venv", "node_modules", "__pycache__"}


@dataclass
class RunResult:
    status: str
    command: list[str]
    exit_code: int | None
    stdout: str
    stderr: str
    elapsed_seconds: float
    reason: str = ""


def run_bounded(command: list[str], cwd: Path, timeout: float = 120, max_output: int = 128_000_000) -> RunResult:
    """Drain to bounded files, kill the process group on timeout/output overflow."""
    if timeout <= 0 or max_output <= 0:
        raise ValueError("Timeout and output budget must be positive")
    begin = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="proofreader-process-") as directory:
        out_path, err_path = Path(directory) / "stdout", Path(directory) / "stderr"
        with out_path.open("wb") as out, err_path.open("wb") as err:
            try:
                proc = subprocess.Popen(command, cwd=cwd, stdout=out, stderr=err, stdin=subprocess.DEVNULL,
                                        start_new_session=(os.name == "posix"))
            except (OSError, ValueError) as exc:
                return RunResult("unavailable", command, None, "", str(exc), round(time.monotonic() - begin, 3), "Executable could not be started")
            reason = ""
            while proc.poll() is None:
                if time.monotonic() - begin > timeout:
                    reason = "timeout"
                elif out_path.stat().st_size + err_path.stat().st_size > max_output:
                    reason = "output budget exceeded"
                if reason:
                    if os.name == "posix":
                        try: os.killpg(proc.pid, signal.SIGKILL)
                        except ProcessLookupError: pass
                    else:
                        proc.kill()
                    proc.wait()
                    break
                time.sleep(0.025)
            exit_code = proc.wait()
        if not reason and out_path.stat().st_size + err_path.stat().st_size > max_output:
            reason = "output budget exceeded"
        stdout = out_path.read_bytes()[:max_output].decode("utf-8", "replace")
        stderr = err_path.read_bytes()[:max_output].decode("utf-8", "replace")
    status = "passed" if exit_code == 0 and not reason else "failed"
    return RunResult(status, command, exit_code, stdout, stderr, round(time.monotonic() - begin, 3), reason)


def doctor(project: Path | None = None) -> dict[str, Any]:
    project = (project or Path.cwd()).resolve()
    lake = shutil.which("lake")
    lean = shutil.which("lean")
    info = {"project": str(project), "lake_available": bool(lake), "lean_available": bool(lean),
            "toolchain": (project / "lean-toolchain").read_text().strip() if (project / "lean-toolchain").exists() else None,
            "lean_version": None, "can_extract": False}
    if lake:
        run = run_bounded([lake, "env", "lean", "--version"], project, timeout=30, max_output=100_000)
        info["lean_version"] = run.stdout.strip() or None
        info["can_extract"] = run.status == "passed"
        if not info["can_extract"]: info["error"] = run.stderr or run.reason
    return info


def source_fingerprint(project: Path) -> str:
    """Hash all project source/config files; external .lake dependencies are excluded.

The lake manifest is included. This is a source snapshot, not an attestation
of dependency artifact integrity; that limitation is included in receipts.
"""
    h = hashlib.sha256()
    candidates: list[Path] = []
    for root, dirs, names in os.walk(project):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDES and not (Path(root) / d).is_symlink())
        for name in sorted(names):
            path = Path(root) / name
            if path.is_symlink(): continue
            if name.endswith(".lean") or name in {"lean-toolchain", "lake-manifest.json", "lakefile.toml"}:
                candidates.append(path)
    for path in sorted(candidates):
        h.update(path.relative_to(project).as_posix().encode() + b"\0")
        h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


@contextmanager
def driver_file(project: Path, content: str):
    cache = project / "_proofreader_cache"
    cache.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="run_", dir=cache) as directory:
        path = Path(directory) / "Driver.lean"
        path.write_text(content, encoding="utf-8")
        yield path


def exporter_path() -> Path:
    # Source distribution layout; installed wheels include a packaged copy.
    candidates = [Path(__file__).resolve().parent / "data" / "ProofReader.lean", Path(__file__).resolve().parent.parent / "lean" / "ProofReader.lean"]
    for path in candidates:
        if path.is_file(): return path
    raise FileNotFoundError("The Lean exporter was not packaged. Use the source distribution or reinstall.")


def export_driver(module: str) -> str:
    if not MODULE_RE.fullmatch(module):
        raise ValueError("Unsafe or unsupported module name")
    source = exporter_path().read_text(encoding="utf-8")
    marker = "open Lean Meta Elab Command"
    if marker not in source:
        raise ValueError("Exporter import boundary not found")
    # This avoids requiring a separately installed ProofReader.olean. The
    # imported target is built in its own existing, pinned Lake environment.
    return source.replace(marker, f"import {module}\n\n{marker}", 1) + f'\n#proofreader_export_module "{module}"\n'


def parse_export_stream(stdout: str) -> dict[str, Any]:
    records, failures, inventories = [], [], []
    for line_number, line in enumerate(stdout.splitlines(), 1):
        if not line.startswith(PREFIX): continue
        try:
            record = json.loads(line[len(PREFIX):])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Malformed exporter JSON at output line {line_number}") from exc
        schema = record.get("schema")
        if schema == "proofreader.lean-export/v1":
            validate_export(record)
            records.append(record)
        elif schema == "proofreader.export-failure/v1":
            failures.append(record)
        elif schema == "proofreader.module-inventory/v1":
            inventories.append(record)
        else:
            raise ValueError(f"Unsupported exporter record schema: {schema}")
    if len(inventories) != 1:
        raise ValueError("Missing or duplicated module inventory: export is incomplete")
    expected = inventories[0].get("declarations")
    if not isinstance(expected, list) or any(not isinstance(n, str) for n in expected):
        raise ValueError("Malformed module inventory")
    observed = [r["name"] for r in records + failures]
    if len(set(observed)) != len(observed) or len(set(expected)) != len(expected) or set(observed) != set(expected):
        raise ValueError("Exported declarations do not reconcile with the module inventory")
    return {"records": records, "failures": failures, "inventory": inventories[0], "complete": not failures}


def extract_module(project: Path, module: str, output: Path, *, trust_project: bool = False,
                   timeout: float = 600, replay: bool = False) -> dict[str, Any]:
    if not trust_project:
        raise PermissionError("Lean elaboration can execute arbitrary code. Extraction requires --trust-project; isolate untrusted projects first.")
    if not MODULE_RE.fullmatch(module): raise ValueError("Unsafe or unsupported module name")
    project = project.resolve()
    if not project.is_dir(): raise ValueError("Project directory does not exist")
    output.mkdir(parents=True, exist_ok=True)
    environment = doctor(project)
    if not environment["can_extract"]:
        result = {"module": module, "status": "unavailable", "environment": environment, "reason": "Working Lean/Lake toolchain is unavailable"}
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    before = source_fingerprint(project)
    build = run_bounded(["lake", "build", module], project, timeout=timeout)
    (output / "build.stdout.log").write_text(build.stdout)
    (output / "build.stderr.log").write_text(build.stderr)
    if build.status != "passed":
        result = {"module": module, "status": "build-failed", "reason": build.reason or "Lake returned a nonzero exit status", "exit_code": build.exit_code}
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    driver = export_driver(module)
    with driver_file(project, driver) as path:
        run = run_bounded(["lake", "env", "lean", str(path)], project, timeout=timeout)
    (output / "export.stdout.log").write_text(run.stdout)
    (output / "export.stderr.log").write_text(run.stderr)
    if run.status != "passed":
        result = {"module": module, "status": "export-failed", "reason": run.reason or "Exporter returned a nonzero exit status", "exit_code": run.exit_code}
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    try:
        stream = parse_export_stream(run.stdout)
    except ValueError as exc:
        result = {"module": module, "status": "incomplete-export", "reason": str(exc)}
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    after = source_fingerprint(project)
    if before != after:
        result = {"module": module, "status": "source-changed", "reason": "Project sources changed during extraction"}
        (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    document_list = []
    replay_results = []
    from .core import ALLOWED_AXIOMS
    for record in stream["records"]:
        key = digest(record["name"])[:20]
        (output / f"{key}.export.json").write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        receipt = {
            "schema": "proofreader.lean-receipt/v1", "status": "passed", "scope": "module-build-and-extraction",
            "declaration": record["name"], "module": module, "source_fingerprint": before,
            "exporter_sha256": digest(exporter_path().read_bytes()), "export_sha256": digest(json.dumps(record, ensure_ascii=False, sort_keys=True)),
            "toolchain": environment["toolchain"], "lean_version": environment["lean_version"],
            "axioms": record["axioms"], "axiom_policy_passed": set(record["axioms"]).issubset(ALLOWED_AXIOMS),
            "raw_term_replayed": False, "english_fidelity_certified": False,
            "dependency_artifacts_fully_hashed": False,
        }
        if replay and record.get("kind") == "theorem" and "raw_term" in record:
            generated = replay_source(record, module)
            (output / f"{key}.replay.lean").write_text(generated)
            with driver_file(project, generated) as path:
                replay_run = run_bounded(["lake", "env", "lean", str(path)], project, timeout=timeout)
            passed = replay_run.status == "passed" and "PROOFREADER_REPLAY_OK" in replay_run.stdout.splitlines()
            receipt["raw_term_replayed"] = passed
            replay_results.append({"name": record["name"], "passed": passed})
            (output / f"{key}.replay.log").write_text(replay_run.stdout + "\n" + replay_run.stderr)
        (output / f"{key}.receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        document_list.append(export_document(record, module, receipt))
    combined = Document(module, [], [d for doc in document_list for d in doc.declarations], provenance={"mode": "typed-export", "module": module, "pipeline_model_calls": 0})
    (output / "document.json").write_text(combined.to_json())
    from .render import write_html
    write_html(combined, output / "index.html")
    replay_failed = any(not r["passed"] for r in replay_results)
    source_changed = source_fingerprint(project) != before
    status = "source-changed" if source_changed else "partial-export" if not stream["complete"] else "replay-failed" if replay_failed else "exported"
    result = {"module": module, "status": status, "inventory": stream["inventory"], "failures": stream["failures"],
              "replays": replay_results, "replay_requested": replay, "exported_records": len(stream["records"]),
              "declarations": [{"name": r["name"], "kind": r.get("kind"), "axioms": r["axioms"]} for r in stream["records"]],
              "axiom_policy_passed": all(set(r["axioms"]).issubset(ALLOWED_AXIOMS) for r in stream["records"]),
              "checked_english_proofs": 0}
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
