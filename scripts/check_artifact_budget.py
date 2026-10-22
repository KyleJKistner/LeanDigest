"""Keep committed run outputs under artifacts/ within a recorded size budget.

Bulky run outputs belong in GitHub Actions artifacts or release assets, cited by
run ID and SHA-256 (see artifacts/README.md). This check reads the Git index, so
it measures exactly the tracked blobs and ignores untracked local run outputs. It
fails when the tracked total exceeds BUDGET_BYTES, when a tracked file exceeds
MAX_FILE_BYTES without an allowlist reason, when an allowlist entry is stale, or
when nothing was measured (an empty inventory is not a pass). Raising the budget
or adding an allowlist entry is a reviewed change to this file.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TREE = 'artifacts'
# Tracked artifacts/ held 19,659,106 bytes in 1,022 files at 04df977; ~7% headroom.
BUDGET_BYTES = 21_000_000
MAX_FILE_BYTES = 1_000_000
ALLOWED_LARGE = {
    'artifacts/pinned-openai-slice/38767243074/batch/attempts/7476d316d1944b5c8c39db3f30d20e71/'
    'ee407ca41101a581e515fe2f2de9b4bebc58a577501060dec4f8d211780565a9/run.json':
        'Process record of the native batch extraction in pinned-slice run 38767243074, including '
        'the Lean driver\'s complete stdout. run-provenance.json in the same run directory records '
        'its byte count and SHA-256, so trimming it would break that record. '
        'tests/reader/test_logical_explanations.py reads snapshots from the same retained slice.',
}


def tracked_sizes(root: Path = ROOT, tree: str = TREE) -> dict[str, int]:
    """Map every tracked path under tree to the size of its blob in the Git index."""
    git = ['git', '-C', str(root)]
    top = subprocess.run(git+['rev-parse', '--show-toplevel'], capture_output=True, check=True, text=True).stdout.strip()
    if Path(top).resolve() != Path(root).resolve():  # a subdirectory would silently measure the wrong tree
        raise RuntimeError(f'{root} is not the top level of its Git work tree ({top})')
    listing = subprocess.run(git+['ls-files', '-z', '-s', '--', tree], capture_output=True, check=True).stdout
    entries = []
    for record in filter(None, listing.split(b'\0')):
        meta, path = record.split(b'\t', 1)
        mode, blob, _stage = meta.split()
        if mode != b'160000':  # a submodule entry names a commit, not a blob
            entries.append((path.decode('utf-8', 'surrogateescape'), blob.decode()))
    if not entries:
        return {}
    query = ''.join(blob+'\n' for _, blob in entries).encode()
    sizes = subprocess.run(git+['cat-file', '--batch-check=%(objectsize)'], input=query,
                           capture_output=True, check=True).stdout.split()
    if len(sizes) != len(entries) or not all(s.isdigit() for s in sizes):
        raise RuntimeError('git cat-file did not report a size for every tracked blob')
    return {path: int(size) for (path, _), size in zip(entries, sizes)}


def check(sizes: dict[str, int], budget: int = BUDGET_BYTES, max_file: int = MAX_FILE_BYTES,
          allowed: dict[str, str] = ALLOWED_LARGE) -> dict:
    total = sum(sizes.values())
    problems = [] if sizes else [f'no tracked files under {TREE}/; nothing was measured']
    if total > budget:
        problems.append(f'tracked {TREE}/ holds {total:,} bytes, over the recorded budget of {budget:,} bytes')
    for path, size in sorted(sizes.items()):
        if size > max_file and path not in allowed:
            problems.append(f'{path}: {size:,} bytes exceeds the {max_file:,}-byte file limit and is not allowlisted')
    for path, reason in sorted(allowed.items()):
        if not reason.strip():
            problems.append(f'{path}: allowlist entry has no reason')
        if path not in sizes:
            problems.append(f'{path}: allowlisted but not tracked; remove the entry')
        elif sizes[path] <= max_file:
            problems.append(f'{path}: allowlisted but within the file limit; remove the entry')
    largest = sorted(sizes.items(), key=lambda item: (-item[1], item[0]))[:10]
    return {'tree': TREE, 'tracked_files': len(sizes), 'total_bytes': total, 'budget_bytes': budget,
            'max_file_bytes': max_file, 'allowlisted': sorted(allowed),
            'largest': [{'path': p, 'bytes': n} for p, n in largest], 'problems': problems}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=ROOT, help='Git work tree to measure')
    parser.add_argument('--json', action='store_true', help='print the full report as JSON')
    args = parser.parse_args(argv)
    try:
        report = check(tracked_sizes(args.root), BUDGET_BYTES, MAX_FILE_BYTES, ALLOWED_LARGE)
    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f'Cannot read tracked files under {args.root}: {exc}', file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"{report['tracked_files']:,} tracked files under {TREE}/: {report['total_bytes']:,} of "
              f"{report['budget_bytes']:,} budgeted bytes; file limit {report['max_file_bytes']:,} bytes.")
        for problem in report['problems']:
            print('FAIL: '+problem)
    return 1 if report['problems'] else 0


if __name__ == '__main__':
    sys.exit(main())
