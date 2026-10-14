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
