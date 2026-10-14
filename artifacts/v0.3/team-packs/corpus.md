# ProofReader workstream: corpus

Acquire and run the complete pinned OpenAI corpus through the kernel engine in bounded shards. Reconcile expected files and actual theorem inventories, preserving every failure and unknown denominator. Extend resumability and scale without weakening gates.

# Required return
Write SUMMARY.md with changed files, exact checks and exit codes, unrun checks, blockers, counterexamples and next task. Do not claim checks you did not execute.

# Ownership
proofreader/corpus.py
tests/test_corpus.py
benchmarks/
docs/OPENAI_BENCHMARK.md

# Acceptance
python -m pytest tests/test_corpus.py -q
Publish exact inventory/shard reconciliation including every missing or failed module
Do not count file inventory or import-adapted experiments as full theorem checking

# Known blocker
Complete metadata counts 122458 Lean files (1.57 GB); their contents and dependencies have not all been acquired or compiled. The theorem denominator remains unknown while modules are unenumerated.


# File: docs/OPENAI_BENCHMARK.md

# OpenAI acceptance target

Repository `openai/math`, commit
`1581d4cbdd69a0faf34b2089614fe2a814316a6a`; `lean-toolchain` specifies 4.34.1.
The mathematics manuscripts, formalization catalog and actual Lean theorem
inventory are different sets. Do not report file counts as proof counts or say
that unformalized manuscripts have been translated.

## Observed metadata

`artifacts/v0.2/openai-inventory-observation.json` records a GitHub metadata
traversal across all 23 `lean/OAI` domain subtrees: 122,458 `.lean` files totaling
1,571,301,358 source bytes. Root and subtrees were untruncated. No whole-corpus
content acquisition, build, export, replay, English check or human study occurred.
The metadata service response supplies expected file counts, not proof truth.

The repository includes six original source files whose Git hashes are tested.
They contain nine source declaration candidates. A separate adapted-harness
Bézout experiment is recorded, but is not a pinned-project pass.

## Reproducible runner

```sh
proofreader fetch-openai work/openai-math
proofreader benchmark work/openai-math -o output/inventory
proofreader gate output/inventory/coverage.json --level inventory

# Execute each index from 0 through 15 on a trusted configured runner.
proofreader extract-corpus work/openai-math -o output/shard-0 \
  --engine kernel --trust-project --shard-count 16 --shard-index 0

proofreader aggregate work/openai-math output/shard-*/extraction.json \
  -o output/aggregate
proofreader gate output/aggregate/coverage.json --level replay
# English fidelity gate intentionally fails in 0.2.
proofreader gate output/aggregate/coverage.json --level english
```

Acquisition falls back from truncated recursive trees to independently complete
subtrees. Existing files that differ from pinned hashes are not overwritten.
Missing artifacts stay in the manifest. For corpora above 500 source files,
benchmarking emits a memory-bounded ledger rather than holding all proof documents.
Typed module extraction separately writes per-module/per-theorem readers.

Each v2 module report reconciles an environment-derived theorem inventory with
one result per expected theorem. The aggregator rejects missing/duplicate modules,
different corpus commits, missing theorem outcomes, duplicate declaration ownership,
failed replay and disallowed axioms. It reports an additional
`all_path_bound_theorem_judgements_checked` flag only for complete v2 runs; legacy
root-term-only replay cannot set it. These reports are unsigned run ledgers.

## Limits

The v2 denominator is theorem declarations in `lean/OAI` modules. Proof-valued
`def`s and all dependency definitions need explicit future coverage. Per-module
proof checking can be expensive and should be cached/batched on the runner;
performance at full target scale is not measured. Unexpected timeouts, expression
budgets, export caps or unsupported structures must remain visible. Do not tune
coverage by deleting hard files, assuming imported lemma names explain their
proofs, or relabelling an adapted Lean version as the pinned one.



# File: docs/TRUST.md

# Trust boundary — 0.2

## Three inputs, different authority

A `.lean` **source outline** is a lexical/layout reading aid. Recognizing `simp`
does not reveal a mathematical derivation. None of the nine OpenAI source-mode
demo declarations is relabelled as kernel checked.

A `proofreader.kernel-export/v2` **typed argument** is a constructor DAG plus a
set of typed proof-subterm judgements. Python validates a strict schema, universe
and binder scope, immutable original-root paths, exact child/argument inventories,
and resource budgets. It does not serve as a Lean type checker.

A **checking observation/receipt** records a run. An imported JSON file is not a
signature, an attestation, or proof of its own origin. The browser never claims to
authenticate it. The release's remote observations include request identifiers,
exact request-source hashes, positive markers and negative outcomes.

## What the generated Lean program checks

1. Exact Lean version and universe-parameter inventory.
2. Transitive axiom inventory matching the argument export.
3. Original declaration statement and proof AST identity, after erasing metadata.
   Proof irrelevance/definitional equality is not substituted for this exactness.
4. The original reconstructed proof submitted as a new kernel-checked theorem.
5. Every recorded proof path followed independently in Lean through that original
   proof; its real enclosing binders are used to close the subterm.
6. Each resulting term/type judgement submitted through `addDecl`: theorem
   declarations for proofs and safe definitions for data arguments.
7. Proposition/data and assumption/object classification checked in Lean.

`debug.skipKernelTC` is forced false around the new declarations. A failure after
root replay but before the final marker is an overall failure. The exact final
marker includes the argument hash and judgement count. The verifier also checks
process/API success, errors, failed declarations, returned source and version.

This still assumes a trusted Lean implementation, checking program, runtime,
project metaprograms, imported dependencies and service execution. It does not
cryptographically authenticate compiled dependencies, hardware, or the service.
An adversarial project with arbitrary metaprogram execution is not made logically
or operationally trustworthy merely by passing a command-line flag.

## What is not certified

The English printer is deterministic and regression-tested, not formally proved.
`check-reading` checks regeneration, not a formal interpretation of English.
Beta/zeta display simplification is bounded and capture-avoiding in the tested
implementation; original expression nodes remain authoritative. Unknown symbols,
recursors, large expressions and named lemmas can remain explicitly unexpanded.
Standard mathematical notation still needs its displayed types and instances.

No human comprehension study, full-corpus prose-completeness result, paper-to-Lean
correspondence proof, or correctness claim for OpenAI's manuscripts is implied.
The v2 enumerator covers theorem declarations, not all proof-valued definitions.
The legacy exporter retains a wider declaration inventory but does not provide
v2 intermediate-judgement verification.

## Axioms and admissions

Default permitted axioms: `propext`, `Classical.choice`, `Quot.sound`. These are
visible, not silently described as axiom-free. Additional axioms require explicit
`--permit-axiom` and remain visible. `sorryAx` / `Lean.sorryAx` cannot be permitted
through that option. An empty transitive axiom inventory is reported separately.

## Execution and transport

Offline reading makes no model, telemetry, CDN or service requests. The local
single-user server accepts source text, not arbitrary filesystem paths. It binds
to loopback and checks Host/Origin; it has no Lean build or shell endpoint.

Native compilation requires `--trust-project`; this does not sandbox anything.
Remote operations require `--allow-remote` and send complete code to AXLE. Remote
requests require UTF-8 JSON, fixed official host, bounded responses and no redirect
following. API keys are read from the environment and excluded from artifacts.

Source snapshots and module/source hashes do not authenticate every dependency
binary. Corpus reports are unsigned reproducible ledgers, not self-authenticating
mathematical certificates. Security tests are not an independent security audit.

## Source-bound route added in 0.3

`source-bound-snapshot` is not `typed-export`. Its formula strings use Lean's pretty-printer. Read docs/NARRATIVE.md for the full trust boundary, re-extraction checks and integer-polynomial certificates. No snapshot or imported receipt self-authenticates. Exact source paths and selected judgements ran on 4.34.1 for the retained example; the full pinned project did not.



# File: proofreader/corpus.py

"""Pinned OpenAI corpus acquisition and non-vacuous coverage accounting."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path, PurePosixPath
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable
from .model import Document, digest, report
from .source import merge_documents, parse_source

OPENAI_COMMIT = "1581d4cbdd69a0faf34b2089614fe2a814316a6a"
REPOSITORY = "openai/math"
MANIFEST = "proofreader-corpus.json"


class AcquisitionError(RuntimeError):
    pass


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def safe_destination(root: Path, relative: str) -> Path:
    # POSIX paths are used in Git, regardless of the host operating system.
    p = PurePosixPath(relative)
    if p.is_absolute() or ".." in p.parts or "\\" in relative or "\x00" in relative or not p.parts:
        raise ValueError(f"Unsafe corpus path: {relative!r}")
    root = root.resolve()
    dst = root.joinpath(*p.parts)
    try: dst.resolve().relative_to(root)
    except ValueError as exc: raise ValueError("Corpus path escapes its destination") from exc
    # Reject symlinks even if they currently resolve inside the workspace.
    for ancestor in [dst, *dst.parents]:
        if ancestor == root: break
        if ancestor.is_symlink(): raise ValueError("Symlink destinations are not permitted")
    return dst


def role(path: str) -> str:
    if path.startswith("lean/ComparatorChallenges/"): return "comparator"
    if path.startswith("lean/OAI/") and path.endswith(".lean"): return "proof-library"
    if path == "lean/OAI.lean": return "library-index"
    if path.endswith(".lean"): return "other-lean"
    if path.startswith("preprints/"): return "manuscript"
    return "metadata"


def wanted(path: str) -> bool:
    return path.endswith(".lean") or path in {"README.md", "CONTENTS.md", "LICENSE", "lean/LICENSE", "lean/formalization.yaml", "lean/lean-toolchain", "lean/lake-manifest.json", "lean/lakefile.toml", "lean/lakefile.lean"} or (path.startswith("lean/") and path.endswith((".json", ".md")))


class GitHubClient:
    """No model calls. Tokens are optional, read from the environment, never saved."""
    def __init__(self, token: str | None = None, timeout: float = 60):
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.timeout = timeout

    def request(self, url: str) -> bytes:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {"api.github.com", "raw.githubusercontent.com"}:
            raise AcquisitionError("Only official GitHub API and raw-source hosts are accepted")
        headers = {"User-Agent": "lean-proofreader/0.2.0", "Accept": "application/vnd.github+json"}
        if self.token and parsed.hostname == "api.github.com": headers["Authorization"] = "Bearer " + self.token
        for attempt in range(4):
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=self.timeout) as response:
                    length = response.headers.get("Content-Length")
                    if length and int(length) > 256_000_000: raise AcquisitionError("Remote artifact exceeds the size budget")
                    data = response.read(256_000_001)
                    if len(data) > 256_000_000: raise AcquisitionError("Remote artifact exceeds the size budget")
                    return data
            except urllib.error.HTTPError as exc:
                if exc.code in {429, 500, 502, 503, 504} and attempt < 3:
                    time.sleep(min(2 ** attempt, 4))
                    continue
                raise AcquisitionError(f"GitHub returned HTTP {exc.code}; acquisition is incomplete") from exc
            except urllib.error.URLError as exc:
                if attempt < 2:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                raise AcquisitionError("GitHub is unreachable; acquisition is incomplete") from exc
        raise AcquisitionError("Request retry budget exhausted")

    def json(self, endpoint: str) -> dict:
        return json.loads(self.request("https://api.github.com" + endpoint))

    def tree(self, commit: str) -> list[dict]:
        if not re.fullmatch(r"[0-9a-f]{40}", commit): raise ValueError("A full immutable commit SHA is required")
        first = self.json(f"/repos/{REPOSITORY}/git/trees/{commit}?recursive=1")
        if not first.get("truncated", False):
            return first["tree"]
        # GitHub recursive trees may be truncated. Walk every subtree instead
        # of treating the incomplete response as the corpus denominator.
        queue = [("", commit)]
        entries: list[dict] = []
        while queue:
            prefix, sha = queue.pop(0)
            # A complete recursive child saves thousands of directory requests.
            if prefix:
                recursive = self.json(f"/repos/{REPOSITORY}/git/trees/{sha}?recursive=1")
                if not recursive.get("truncated", False):
                    entries.extend({**e, "path": prefix + e["path"]} for e in recursive["tree"])
                    continue
            tree = self.json(f"/repos/{REPOSITORY}/git/trees/{sha}")
            if tree.get("truncated", False): raise AcquisitionError("Nonrecursive tree is truncated; cannot establish corpus completeness")
            for original in tree["tree"]:
                item = {**original, "path": prefix + original["path"]}
                entries.append(item)
                if item["type"] == "tree": queue.append((item["path"] + "/", item["sha"]))
        return entries

    def raw(self, path: str, commit: str) -> bytes:
        return self.request(f"https://raw.githubusercontent.com/{REPOSITORY}/{commit}/" + urllib.parse.quote(path, safe="/"))


def fetch_snapshot(destination: Path, commit: str = OPENAI_COMMIT, workers: int = 4,
                   client: Any = None, progress: Callable[[str], None] | None = None) -> dict:
    if not 1 <= workers <= 16: raise ValueError("workers must be between 1 and 16")
    client = client or GitHubClient()
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True)
    tree = client.tree(commit)
    all_blobs = sorted([entry for entry in tree if entry.get("type") == "blob"], key=lambda x: x["path"])
    paths = [entry["path"] for entry in all_blobs]
    if len(paths) != len(set(paths)): raise AcquisitionError("Duplicate paths in Git tree")
    targets = [entry for entry in all_blobs if wanted(entry["path"])]
    if not targets: raise AcquisitionError("No requested artifacts in snapshot; refusing vacuous coverage")
    manifest = {
        "schema": "proofreader.corpus/v1", "repository": REPOSITORY, "commit": commit,
        "tree_complete": True, "scope": "all-available-lean-and-metadata", "state": "fetching",
        "manuscript_files": [entry["path"] for entry in all_blobs if entry["path"].startswith("preprints/") and entry["path"].endswith(".pdf")],
        "files": [{"path": e["path"], "git_blob_sha": e["sha"], "size": e.get("size"), "role": role(e["path"]), "status": "pending"} for e in targets],
    }
    write_manifest(destination, manifest)

    def download(index: int, entry: dict) -> tuple[int, dict]:
        metadata = manifest["files"][index].copy()
        try:
            if entry.get("mode") == "120000": raise AcquisitionError("Symlink artifact is not a source file")
            target = safe_destination(destination, entry["path"])
            if target.exists():
                data = target.read_bytes()
                if git_blob_sha(data) != entry["sha"]:
                    raise AcquisitionError("Existing file differs from the pinned snapshot; not overwritten")
            else:
                data = client.raw(entry["path"], commit)
                if git_blob_sha(data) != entry["sha"]: raise AcquisitionError("Downloaded Git blob hash mismatch")
                target.parent.mkdir(parents=True, exist_ok=True)
                # Exclusive creation avoids overwriting edits during a concurrent run.
                with target.open("xb") as out: out.write(data)
            metadata.update(status="downloaded", sha256=digest(data))
        except (AcquisitionError, OSError, ValueError) as exc:
            metadata.update(status="failed", reason=str(exc))
        return index, metadata

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(download, i, entry) for i, entry in enumerate(targets)]
        for future in as_completed(futures):
            i, metadata = future.result()
            manifest["files"][i] = metadata
            if progress: progress(f"{metadata['status']}: {metadata['path']}")
    manifest["state"] = "complete" if all(f["status"] == "downloaded" for f in manifest["files"]) else "incomplete"
    write_manifest(destination, manifest)
    return manifest


def write_manifest(root: Path, manifest: dict) -> None:
    path = root / MANIFEST
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def local_manifest(root: Path) -> dict:
    manifest_path = root / MANIFEST
    if manifest_path.exists():
        value = json.loads(manifest_path.read_text())
        if value.get("schema") != "proofreader.corpus/v1": raise ValueError("Unsupported corpus manifest")
        if not isinstance(value.get("files"), list): raise ValueError("Missing corpus file inventory")
        listed = [f["path"] for f in value["files"]]
        if len(listed) != len(set(listed)): raise ValueError("Duplicate corpus paths")
        return value
    # A full Git checkout provides a trustworthy *expected* file list even
    # when the working tree has deletions. Do not rglob away missing files.
    try:
        top = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if Path(top).resolve() != root.resolve(): raise ValueError("Requested directory is not the Git checkout root")
        result = subprocess.run(["git", "-C", str(root), "ls-tree", "-r", "-z", "--full-tree", "HEAD"], capture_output=True, check=True, timeout=30)
        head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        entries = []
        for item in result.stdout.split(b"\0"):
            if not item: continue
            header, name = item.split(b"\t", 1)
            mode, kind, sha = header.decode().split()
            name = name.decode("utf-8")
            if kind == "blob" and wanted(name): entries.append({"path": name, "git_blob_sha": sha, "role": role(name), "status": "expected"})
        return {"schema": "proofreader.corpus/v1", "scope": "git-checkout", "tree_complete": True, "commit": head, "files": entries}
    except (OSError, subprocess.SubprocessError, ValueError):
        entries = [{"path": p.relative_to(root).as_posix(), "role": role(p.relative_to(root).as_posix()), "sha256": digest(p.read_bytes()), "status": "present"}
                   for p in sorted(root.rglob("*.lean")) if not p.is_symlink() and not {".lake", ".git", "_proofreader_cache"}.intersection(p.parts)]
        return {"schema": "proofreader.corpus/v1", "scope": "selected-source-files", "tree_complete": False, "commit": None, "files": entries}


def benchmark_sources(root: Path, output: Path) -> dict:
    root = root.resolve()
    manifest = local_manifest(root)
    lean_entries = [f for f in manifest["files"] if f["path"].endswith(".lean")]
    documents, rows = [], []
    ledger_only = len(lean_entries) > 500
    totals = {k:0 for k in ("declaration_candidates","source_steps","source_steps_classified","source_steps_unclassified",
                             "source_only_declarations","typed_export_declarations","path_bound_kernel_declarations","unique_display_step_ids")}
    rules=set()
    for entry in lean_entries:
        row = {"file": entry["path"], "role": entry.get("role", role(entry["path"])), "status": "not-run"}
        try:
            path = safe_destination(root, entry["path"])
            data = path.read_bytes()
            if entry.get("git_blob_sha") and git_blob_sha(data) != entry["git_blob_sha"]:
                raise ValueError("Source differs from pinned Git blob")
            if entry.get("sha256") and digest(data) != entry["sha256"]:
                raise ValueError("Source differs from recorded SHA-256")
            document = parse_source(data.decode("utf-8"), entry["path"])
            if not ledger_only: documents.append(document)
            metrics = report(document)
            for k in totals: totals[k] += metrics[k]
            rules.update(metrics["unclassified_rules"])
            row.update(status="source-indexed", **{k: metrics[k] for k in ["declaration_candidates", "source_steps", "source_steps_classified", "source_steps_unclassified"]}, diagnostics=document.warnings)
        except (OSError, ValueError, UnicodeError) as exc:
            row.update(status="failed", error=str(exc))
        rows.append(row)
    merged = merge_documents(documents, "OpenAI math · source reading benchmark")
    merged.provenance.update(repository=manifest.get("repository", REPOSITORY), commit=manifest.get("commit"),
                             scope=manifest.get("scope"), inventory_complete=bool(manifest.get("tree_complete")),
                             expected_lean_files=len(lean_entries), lean_build_performed=False)
    summary = report(merged)
    if ledger_only:
        summary.update(totals)
        summary["files_indexed"]=sum(r["status"]=="source-indexed" for r in rows)
        summary["unclassified_rules"]=sorted(rules)
        merged.warnings.append("Large-corpus run emits a bounded-memory coverage ledger, not a monolithic proof book. Read individual source files on demand.")
        merged.provenance.update(ledger_only=True, source_documents_retained=False)
    summary.update({
        "reading_documents_emitted": not ledger_only,"memory_mode":"ledger-only" if ledger_only else "embedded-readers",
        "commit": manifest.get("commit"), "scope": manifest["scope"], "inventory_complete": bool(manifest.get("tree_complete")),
        "expected_lean_files": len(lean_entries), "source_files_indexed": sum(r["status"] == "source-indexed" for r in rows),
        "failed_or_missing_files": sum(r["status"] != "source-indexed" for r in rows),
        "proof_library_files_expected": sum(r["role"] == "proof-library" for r in rows),
        "whole_corpus_english_coverage": False, "all_formal_proofs_replayed": False,
        "environment_discovered_theorems": None, "rows": rows,
    })
    output.mkdir(parents=True, exist_ok=True)
    (output / "coverage.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    (output / "document.json").write_text(merged.to_json())
    from .render import write_html
    write_html(merged, output / "index.html", coverage=summary)
    return summary


def coverage_gate(report_data: dict, level: str = "inventory") -> tuple[bool, str]:
    expected = report_data.get("expected_lean_files", 0)
    if not isinstance(expected, int) or expected <= 0:
        return False, "No nonempty expected corpus inventory"
    if not report_data.get("inventory_complete"):
        return False, "Selected samples are not a complete corpus inventory"
    if report_data.get("failed_or_missing_files", expected) != 0:
        return False, "Some expected source files are missing or failed"
    if report_data.get("source_files_indexed", 0) != expected:
        return False, "Indexed-file count does not reconcile with inventory"
    if level == "inventory":
        return True, "Every expected source file was indexed; this is not proof explanation coverage"
    if level == "replay":
        count = report_data.get("environment_discovered_theorems")
        passed = (report_data.get("schema") == "proofreader.aggregate-coverage/v1"
                  and type(count) is int and count > 0
                  and report_data.get("replayed_theorems") == count
                  and report_data.get("failed_or_missing_modules") == 0
                  and not report_data.get("unexpected_or_duplicate_modules")
                  and report_data.get("axiom_policy_passed") is True
                  and report_data.get("all_formal_proofs_replayed") is True)
        return passed, "Complete, reconciled theorem replay evidence with the declared axiom policy is required"
    if level == "english":
        return False, "Version 0.2 does not certify English fidelity; this gate cannot pass"
    raise ValueError("Unknown coverage gate")


def extract_corpus(root: Path, output: Path, *, trust_project: bool = False, timeout: float = 600,
                   replay: bool = True, shard_index: int = 0, shard_count: int = 1, engine: str = "kernel") -> dict:
    from .lean import extract_module
    if engine not in {"legacy", "kernel"}: raise ValueError("Unknown corpus extraction engine")
    if not trust_project: raise PermissionError("Extraction requires explicit --trust-project")
    if shard_count <= 0 or not 0 <= shard_index < shard_count: raise ValueError("Invalid shard configuration")
    manifest = local_manifest(root)
    # Hash partitioning is stable when the corpus changes; it does not silently
    # exclude modules as --limit sampling would.
    entries = [f for f in manifest["files"] if f["path"].startswith("lean/OAI/") and f["path"].endswith(".lean")]
    selected = [f for f in entries if int(digest(f["path"])[:16], 16) % shard_count == shard_index]
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for entry in selected:
        path = safe_destination(root, entry["path"])
        module = entry["path"][len("lean/"):-len(".lean")].replace("/", ".")
        try:
            data = path.read_bytes()
            if entry.get("git_blob_sha") and git_blob_sha(data) != entry["git_blob_sha"]: raise ValueError("Pinned source hash mismatch")
            if engine == "legacy":
                result = extract_module(root / "lean", module, output / digest(module)[:20], trust_project=True, timeout=timeout, replay=replay)
            else:
                from .kernel_pipeline import extract_kernel
                from .kernel import display_name
                from .kernel_io import axiom_status
                dest = output / digest(module)[:20]
                run = extract_kernel(dest,module=module,project=root/"lean",trust_project=True,timeout=timeout,verify=replay)
                records=[]
                for item in run["rows"]:
                    path = dest / item["directory"] / "argument.json"
                    if not path.exists(): continue
                    record=json.loads(path.read_text())
                    records.append({"name":item["name"],"kind":"theorem","axioms":record["axioms"]})
                result={"module":module,"status":"exported" if run["status"]=="complete" else run["status"],
                        "engine":"kernel","checking_scope":"source-paths-and-all-typed-judgements",
                        "inventory":{"declarations":[display_name(n) for n in run.get("inventory",{}).get("names",[])]},
                        "declarations":records,"failures":run["failures"],"error":run.get("error"),
                        "replays":[{"name":r["name"],"passed":r["checked"]} for r in run["rows"]],
                        "replay_requested":replay,"checked_english_proofs":0}
        except (OSError, ValueError) as exc:
            result = {"module": module, "status": "failed", "reason": str(exc)}
        rows.append(result)
        # Persist after every module. A killed run remains visibly incomplete.
        progress = {"schema": "proofreader.extraction-benchmark/v1", "commit": manifest.get("commit"), "expected_modules": len(entries), "shard_index": shard_index, "shard_count": shard_count, "shard_expected": len(selected), "shard_attempted": len(rows), "rows": rows, "checked_english_proofs": 0, "whole_corpus_english_coverage": False, "engine":engine}
        (output / "extraction.json").write_text(json.dumps(progress, indent=2, ensure_ascii=False) + "\n")
    result = {"schema": "proofreader.extraction-benchmark/v1", "commit": manifest.get("commit"), "expected_modules": len(entries), "shard_index": shard_index, "shard_count": shard_count, "shard_expected": len(selected), "shard_attempted": len(rows), "rows": rows, "checked_english_proofs": 0, "whole_corpus_english_coverage": False, "engine":engine}
    (output / "extraction.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return result


def aggregate_extractions(root: Path, reports: list[Path], output: Path) -> dict:
    """Reconcile actual module inventories and replay rows across every shard.

    Like build logs, these records are not signed attestations. Reproduce the
    runs on trusted infrastructure; do not treat arbitrary imported JSON as proof.
    """
    manifest = local_manifest(root)
    expected = {f["path"][len("lean/"):-len(".lean")].replace("/", ".")
                for f in manifest["files"] if f["path"].startswith("lean/OAI/") and f["path"].endswith(".lean")}
    rows: dict[str, dict] = {}
    unexpected: list[str] = []
    errors: list[str] = []
    for path in reports:
        data = json.loads(path.read_text())
        if data.get("schema") != "proofreader.extraction-benchmark/v1": raise ValueError("Unsupported extraction report")
        if data.get("commit") != manifest.get("commit"): raise ValueError("Extraction report belongs to a different corpus commit")
        if data.get("shard_attempted") != len(data.get("rows", [])): raise ValueError("Shard row count does not reconcile")
        for row in data.get("rows", []):
            name = row.get("module", "")
            if name not in expected or name in rows:
                unexpected.append(name)
            else: rows[name] = row
    declarations: set[str] = set()
    theorems: set[str] = set()
    replayed: set[str] = set()
    bad_modules = []
    axiom_ok = True
    from .core import ALLOWED_AXIOMS
    for module in sorted(expected):
        row = rows.get(module)
        if not row or row.get("status") != "exported":
            bad_modules.append(module)
            continue
        records = row.get("declarations", [])
        inventory = row.get("inventory", {}).get("declarations", [])
        names = [d.get("name") for d in records]
        if len(names) != len(set(names)) or set(names) != set(inventory):
            bad_modules.append(module);errors.append(f"Declaration inventory mismatch: {module}");continue
        if declarations.intersection(names):
            bad_modules.append(module);errors.append(f"Duplicate declaration ownership: {module}");continue
        declarations.update(names)
        module_theorems = {d["name"] for d in records if d.get("kind") == "theorem"}
        theorems.update(module_theorems)
        for d in records:
            if d.get("kind") == "theorem" and not set(d.get("axioms", [])).issubset(ALLOWED_AXIOMS): axiom_ok = False
        replay_rows = row.get("replays", [])
        replay_names = [r.get("name") for r in replay_rows]
        if len(replay_names) != len(set(replay_names)) or set(replay_names) - module_theorems:
            bad_modules.append(module);errors.append(f"Invalid replay inventory: {module}");continue
        replayed.update(r["name"] for r in replay_rows if r.get("passed") is True)
    source = benchmark_sources(root, output / "source")
    complete = bool(manifest.get("tree_complete")) and bool(expected) and not bad_modules and not unexpected and source["failed_or_missing_files"] == 0
    claims_checked = bool(complete and theorems and replayed == theorems and axiom_ok and
                          all(row.get("engine")=="kernel" and row.get("checking_scope")=="source-paths-and-all-typed-judgements" for row in rows.values()))
    result = {**source, "all_path_bound_theorem_judgements_checked": claims_checked, "schema": "proofreader.aggregate-coverage/v1", "scope": "all-theorems-defined-in-lean/OAI-modules",
              "expected_modules": len(expected), "attempted_modules": len(rows), "failed_or_missing_modules": len(set(bad_modules)),
              "missing_or_failed_module_names": sorted(set(bad_modules)), "unexpected_or_duplicate_modules": sorted(unexpected),
              "exported_declarations": len(declarations), "environment_discovered_theorems": len(theorems) if complete else None,
              "observed_theorems": len(theorems), "replayed_theorems": len(replayed), "axiom_policy_passed": axiom_ok,
              "all_formal_proofs_replayed": bool(complete and theorems and replayed == theorems and axiom_ok),
              "checked_english_proofs": 0, "whole_corpus_english_coverage": False, "errors": errors}
    output.mkdir(parents=True, exist_ok=True)
    (output / "coverage.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return result



# File: tests/test_corpus.py

from pathlib import Path
import json
import pytest
from proofreader.corpus import *


def manifest(root,files,complete=False):
    (root/MANIFEST).write_text(json.dumps({'schema':'proofreader.corpus/v1','scope':'test-fixture','tree_complete':complete,'commit':OPENAI_COMMIT,'files':files}))


def test_pinned_real_samples_match_blob_hashes():
    root=Path(__file__).resolve().parents[1]/'examples/openai'
    m=local_manifest(root)
    assert len(m['files'])==6
    for e in m['files']:
        assert git_blob_sha((root/e['path']).read_bytes())==e['git_blob_sha']


def test_real_sample_benchmark_not_full_corpus(tmp_path):
    root=Path(__file__).resolve().parents[1]/'examples/openai'
    result=benchmark_sources(root,tmp_path/'out')
    assert result['source_files_indexed']==6
    assert result['declaration_candidates']==9
    assert result['checked_english_proofs']==0
    assert not coverage_gate(result,'english')[0]
    assert not coverage_gate(result,'inventory')[0]
    assert (tmp_path/'out/index.html').is_file()


def test_missing_expected_file_not_dropped(tmp_path):
    manifest(tmp_path,[{'path':'lean/OAI/Missing.lean','git_blob_sha':'0'*40}],True)
    r=benchmark_sources(tmp_path,tmp_path/'out')
    assert r['expected_lean_files']==1 and r['failed_or_missing_files']==1
    assert not coverage_gate(r)[0]


def test_changed_source_fails_pinned_integrity(tmp_path):
    (tmp_path/'Test.lean').write_text('theorem t : True := by trivial')
    manifest(tmp_path,[{'path':'Test.lean','git_blob_sha':'0'*40}],True)
    r=benchmark_sources(tmp_path,tmp_path/'out')
    assert r['rows'][0]['status']=='failed'


def test_empty_dataset_cannot_pass_gate():
    assert not coverage_gate({'expected_lean_files':0,'inventory_complete':True,'failed_or_missing_files':0,'source_files_indexed':0})[0]


def test_full_source_inventory_not_english_coverage():
    r={'expected_lean_files':1,'inventory_complete':True,'failed_or_missing_files':0,'source_files_indexed':1}
    assert coverage_gate(r,'inventory')[0]
    assert not coverage_gate(r,'replay')[0]
    assert not coverage_gate(r,'english')[0]


@pytest.mark.parametrize('path',['../evil','/evil','a/../../evil','a\\evil','a\0b'])
def test_unsafe_corpus_paths_rejected(tmp_path,path):
    with pytest.raises(ValueError):safe_destination(tmp_path,path)


def test_symlink_not_followed(tmp_path):
    (tmp_path/'real').mkdir();(tmp_path/'alias').symlink_to(tmp_path/'real',target_is_directory=True)
    with pytest.raises(ValueError):safe_destination(tmp_path,'alias/x.lean')


def test_truncated_remote_tree_walks_subtrees():
    class Mock(GitHubClient):
        def __init__(self):self.calls=[]
        def json(self,endpoint):
            self.calls.append(endpoint)
            if '?recursive' in endpoint:return {'truncated':True,'tree':[]}
            if endpoint.endswith('/'+OPENAI_COMMIT):return {'truncated':False,'tree':[{'path':'lean','type':'tree','sha':'1'*40}]}
            return {'truncated':False,'tree':[{'path':'X.lean','type':'blob','sha':'2'*40}]}
    c=Mock();rows=c.tree(OPENAI_COMMIT)
    assert any(r['path']=='lean/X.lean' for r in rows)
    assert len(c.calls)==4


def test_truncated_nonrecursive_tree_fails():
    class Mock(GitHubClient):
        def json(self,endpoint):return {'truncated':True,'tree':[]}
    with pytest.raises(AcquisitionError):Mock().tree(OPENAI_COMMIT)


def test_requires_pinned_commit():
    with pytest.raises(ValueError):GitHubClient().tree('main')


def test_duplicate_manifest_paths_fail(tmp_path):
    manifest(tmp_path,[{'path':'A.lean'},{'path':'A.lean'}])
    with pytest.raises(ValueError):local_manifest(tmp_path)


def test_corpus_extract_requires_consent(tmp_path):
    with pytest.raises(PermissionError):extract_corpus(tmp_path,tmp_path/'out')


def test_cannot_assert_english_success_by_setting_a_boolean():
    r={'expected_lean_files':1,'inventory_complete':True,'failed_or_missing_files':0,'source_files_indexed':1,'whole_corpus_english_coverage':True}
    assert not coverage_gate(r,'english')[0]


def test_missing_shard_prevents_full_replay(tmp_path):
    source=b'theorem t : True := by trivial\n'
    f=tmp_path/'lean/OAI/A.lean';f.parent.mkdir(parents=True);f.write_bytes(source)
    manifest(tmp_path,[{'path':'lean/OAI/A.lean','git_blob_sha':git_blob_sha(source)}],True)
    report=tmp_path/'empty-shard.json'
    report.write_text(json.dumps({'schema':'proofreader.extraction-benchmark/v1','commit':OPENAI_COMMIT,'shard_attempted':0,'rows':[]}))
    r=aggregate_extractions(tmp_path,[report],tmp_path/'out')
    assert r['failed_or_missing_modules']==1
    assert r['environment_discovered_theorems'] is None
    assert not coverage_gate(r,'replay')[0]


def test_synthetic_complete_replay_accounting(tmp_path):
    # Unit-test ledger accounting only: this fabricated log is not real proof evidence.
    source=b'theorem t : True := by trivial\n'
    f=tmp_path/'lean/OAI/A.lean';f.parent.mkdir(parents=True);f.write_bytes(source)
    manifest(tmp_path,[{'path':'lean/OAI/A.lean','git_blob_sha':git_blob_sha(source)}],True)
    report=tmp_path/'shard.json'
    row={'module':'OAI.A','status':'exported','inventory':{'declarations':['OAI.t']},'declarations':[{'name':'OAI.t','kind':'theorem','axioms':[]}],'replays':[{'name':'OAI.t','passed':True}]}
    report.write_text(json.dumps({'schema':'proofreader.extraction-benchmark/v1','commit':OPENAI_COMMIT,'shard_attempted':1,'rows':[row]}))
    r=aggregate_extractions(tmp_path,[report],tmp_path/'out')
    assert coverage_gate(r,'replay')[0]
    assert not coverage_gate(r,'english')[0]
    r=aggregate_extractions(tmp_path,[report,report],tmp_path/'duplicate-out')
    assert not coverage_gate(r,'replay')[0]


def test_complete_child_subtree_avoids_per_directory_fetch():
    class Mock(GitHubClient):
        def __init__(self):self.calls=[]
        def json(self,endpoint):
            self.calls.append(endpoint)
            if endpoint.endswith(OPENAI_COMMIT+'?recursive=1'):return {'truncated':True,'tree':[]}
            if endpoint.endswith(OPENAI_COMMIT):return {'truncated':False,'tree':[{'path':'lean','type':'tree','sha':'1'*40}]}
            assert endpoint.endswith('?recursive=1')
            return {'truncated':False,'tree':[{'path':'A/B.lean','type':'blob','sha':'2'*40}]}
    c=Mock();r=c.tree(OPENAI_COMMIT)
    assert any(x['path']=='lean/A/B.lean' for x in r) and len(c.calls)==3

def test_large_corpus_ledger_does_not_retain_proof_book(tmp_path):
    files=[]
    for i in range(501):
        name=f'File{i}.lean';data=f'theorem t{i} : True := by trivial\n'.encode()
        (tmp_path/name).write_bytes(data)
        files.append({'path':name,'git_blob_sha':git_blob_sha(data)})
    manifest(tmp_path,files,True)
    r=benchmark_sources(tmp_path,tmp_path/'out')
    assert r['memory_mode']=='ledger-only' and r['source_files_indexed']==501
    assert r['declaration_candidates']==501
    assert not r['reading_documents_emitted']
    assert not json.loads((tmp_path/'out/document.json').read_text())['declarations']
    assert coverage_gate(r,'inventory')[0] and not coverage_gate(r,'english')[0]



# File: artifacts/v0.2/openai-inventory-observation.json

{
  "repository": "openai/math",
  "commit": "1581d4cbdd69a0faf34b2089614fe2a814316a6a",
  "scope": "lean/OAI/**/*.lean",
  "root_tree": "351061cd373017200b8e08122a9ecdf78ffd2f0c",
  "root_not_truncated": true,
  "all_subtrees_complete": true,
  "lean_files": 122458,
  "lean_bytes": 1571301358,
  "domains": [
    {
      "domain": "Algebra",
      "tree_sha": "70b23ffb2bbb977e5c6d623962fe436e372ce7cd",
      "complete": true,
      "lean_files": 2081,
      "lean_bytes": 13054952
    },
    {
      "domain": "AlgebraicGeometry",
      "tree_sha": "dd4e73fa4306db6958399d324116427b787be67e",
      "complete": true,
      "lean_files": 975,
      "lean_bytes": 10651191
    },
    {
      "domain": "AlgebraicTopology",
      "tree_sha": "ed01aec0436d54f6cf71d76ab1931a2c60748138",
      "complete": true,
      "lean_files": 45,
      "lean_bytes": 964454
    },
    {
      "domain": "Analysis",
      "tree_sha": "31ee05829b116f3a2ae102665b7a0bfcdeb7c5b7",
      "complete": true,
      "lean_files": 26567,
      "lean_bytes": 501776247
    },
    {
      "domain": "CategoryTheory",
      "tree_sha": "588645c2b2d905fe783949b22460caa6e27280f4",
      "complete": true,
      "lean_files": 312,
      "lean_bytes": 7693823
    },
    {
      "domain": "Combinatorics",
      "tree_sha": "1c13837c1d7c42a9828e5d805cfbb87bb0c5da37",
      "complete": true,
      "lean_files": 16614,
      "lean_bytes": 374073302
    },
    {
      "domain": "Computability",
      "tree_sha": "9fe1124f7e8e1629dfb56f964087caad51922e17",
      "complete": true,
      "lean_files": 5213,
      "lean_bytes": 70108018
    },
    {
      "domain": "Dynamics",
      "tree_sha": "3ac4ebd40bdd3f03b13f47975716f8edcacda2e9",
      "complete": true,
      "lean_files": 664,
      "lean_bytes": 9347514
    },
    {
      "domain": "GameTheory",
      "tree_sha": "91d6c9b2d4633e91eb0927eb1e9381ad37b8b3b1",
      "complete": true,
      "lean_files": 303,
      "lean_bytes": 12521635
    },
    {
      "domain": "Geometry",
      "tree_sha": "802c5efb3142a299fb780105e14b7a9f268c4d32",
      "complete": true,
      "lean_files": 14057,
      "lean_bytes": 106103682
    },
    {
      "domain": "GroupTheory",
      "tree_sha": "10488f44fe2e06c2e62dd2fc259f3da04174e992",
      "complete": true,
      "lean_files": 4192,
      "lean_bytes": 24569152
    },
    {
      "domain": "InformationTheory",
      "tree_sha": "8fbc55211aefc4ed5922845768e78a2f4a93e6d6",
      "complete": true,
      "lean_files": 339,
      "lean_bytes": 3410782
    },
    {
      "domain": "LinearAlgebra",
      "tree_sha": "7b267fd75dd170c2d21469a0907a061afd056735",
      "complete": true,
      "lean_files": 954,
      "lean_bytes": 17235358
    },
    {
      "domain": "MathematicalPhysics",
      "tree_sha": "8ff63ddc3f0ba9604f2a3c039cd6e00a34e49b64",
      "complete": true,
      "lean_files": 6736,
      "lean_bytes": 120045134
    },
    {
      "domain": "MeasureTheory",
      "tree_sha": "14769f9bf222b1e1dd36b247016aa8c94d6d8a6f",
      "complete": true,
      "lean_files": 2950,
      "lean_bytes": 13375859
    },
    {
      "domain": "ModelTheory",
      "tree_sha": "a672e3a86cc962bd36fe0d4f4a50b616e3722612",
      "complete": true,
      "lean_files": 42,
      "lean_bytes": 1013533
    },
    {
      "domain": "NumberTheory",
      "tree_sha": "bd483de1f2aabba45a8fed73ad80fc7edcec6515",
      "complete": true,
      "lean_files": 23530,
      "lean_bytes": 132538691
    },
    {
      "domain": "Optimization",
      "tree_sha": "fbdbfdcaff7b3b71bad12420c86502badf215c49",
      "complete": true,
      "lean_files": 2,
      "lean_bytes": 11050
    },
    {
      "domain": "Probability",
      "tree_sha": "fb517d878a6acc1e4ea2ecc2af331dbd4e70a958",
      "complete": true,
      "lean_files": 12971,
      "lean_bytes": 107062936
    },
    {
      "domain": "RepresentationTheory",
      "tree_sha": "82b2c23c0149bf9106392d87a5d8a8b92bec9bd6",
      "complete": true,
      "lean_files": 1108,
      "lean_bytes": 19543700
    },
    {
      "domain": "RingTheory",
      "tree_sha": "c73c85500fa22b4c68dec7248b3b2ce96344b238",
      "complete": true,
      "lean_files": 536,
      "lean_bytes": 5379726
    },
    {
      "domain": "SetTheory",
      "tree_sha": "12bb2c3c9ef59f4a7e7bef47ddd344235a768b3e",
      "complete": true,
      "lean_files": 1018,
      "lean_bytes": 14344369
    },
    {
      "domain": "Topology",
      "tree_sha": "700ea8e85ef83671b303ac99eaaa5ffeaf2e2a4a",
      "complete": true,
      "lean_files": 1249,
      "lean_bytes": 6476250
    }
  ],
  "file_contents_downloaded": false,
  "proofs_compiled": 0,
  "english_coverage_measured": false
}

