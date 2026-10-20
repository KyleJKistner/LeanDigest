"""Committed artifacts/ budget, plus synthetic-repository regressions for the checker.

The first test measures this repository's tracked files. The others build small
synthetic Git repositories; they test the checker, not any recorded run output.
"""
from __future__ import annotations
import os
from pathlib import Path
import shutil
import subprocess

import pytest

from scripts import check_artifact_budget as budget

ROOT = Path(__file__).resolve().parents[1]


def _git_checkout(root: Path) -> bool:
    if not shutil.which('git'):
        return False
    r = subprocess.run(['git', '-C', str(root), 'rev-parse', '--is-inside-work-tree'], capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == 'true'


def test_committed_artifacts_fit_the_recorded_budget():
    if not _git_checkout(ROOT):
        if os.environ.get('GITHUB_ACTIONS'):
            pytest.fail('CI must run from a Git checkout so the artifact budget is enforced')
        pytest.skip('Not a Git checkout; tracked artifact sizes are unavailable')
    report = budget.check(budget.tracked_sizes(ROOT))
    assert report['tracked_files'] > 0
    assert report['problems'] == [], '\n'.join(report['problems'])
    # The budget is a ratchet, not a ceiling to grow into: keep the headroom modest.
    assert budget.BUDGET_BYTES <= 1.25*report['total_bytes'], 'Lower BUDGET_BYTES to the current size plus modest headroom'


def repo(tmp_path: Path, files: dict[str, int], untracked: dict[str, int] | None = None) -> Path:
    """Synthetic repository: files are staged (tracked); untracked files are only written."""
    if not shutil.which('git'):
        pytest.skip('git is required for the synthetic-repository checks')
    root = tmp_path/'repo'
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    for name, size in {**files, **(untracked or {})}.items():
        p = root/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'x'*size)
    if files:
        subprocess.run(['git', '-C', str(root), 'add', '--', *files], check=True)
    return root


def test_only_tracked_files_under_artifacts_are_measured(tmp_path):
    root = repo(tmp_path, {'artifacts/a.json': 10, 'artifacts/run/b.txt': 25, 'docs/big.md': 5000},
                untracked={'artifacts/local-run/out.xml': 9000})
    assert budget.tracked_sizes(root) == {'artifacts/a.json': 10, 'artifacts/run/b.txt': 25}


def test_index_size_is_measured_not_an_unstaged_edit(tmp_path):
    root = repo(tmp_path, {'artifacts/a.json': 10})
    (root/'artifacts/a.json').write_bytes(b'x'*4000)
    assert budget.tracked_sizes(root) == {'artifacts/a.json': 10}


def test_a_subdirectory_is_not_measured_as_the_repository(tmp_path):
    root = repo(tmp_path, {'artifacts/a.json': 10, 'docs/x.md': 5})
    with pytest.raises(RuntimeError, match='not the top level'):
        budget.tracked_sizes(root/'docs')


def test_empty_inventory_is_not_a_pass(tmp_path):
    root = repo(tmp_path, {'docs/x.md': 5})
    assert budget.tracked_sizes(root) == {}
    assert budget.check({}, budget=10, max_file=10, allowed={})['problems'] == \
        ['no tracked files under artifacts/; nothing was measured']


def test_total_over_budget_fails():
    sizes = {'artifacts/a': 600, 'artifacts/b': 500}
    assert budget.check(sizes, budget=1100, max_file=1000, allowed={})['problems'] == []
    problems = budget.check(sizes, budget=1099, max_file=1000, allowed={})['problems']
    assert len(problems) == 1 and 'over the recorded budget' in problems[0]


def test_large_file_needs_an_allowlist_reason():
    sizes = {'artifacts/small': 10, 'artifacts/large': 1001}
    problems = budget.check(sizes, budget=10**6, max_file=1000, allowed={})['problems']
    assert problems == ['artifacts/large: 1,001 bytes exceeds the 1,000-byte file limit and is not allowlisted']
    assert budget.check(sizes, budget=10**6, max_file=1000, allowed={'artifacts/large': 'bound by a run digest'})['problems'] == []
    blank = budget.check(sizes, budget=10**6, max_file=1000, allowed={'artifacts/large': '  '})['problems']
    assert blank == ['artifacts/large: allowlist entry has no reason']


def test_stale_allowlist_entries_fail():
    sizes = {'artifacts/shrunk': 999}
    problems = budget.check(sizes, budget=10**6, max_file=1000,
                            allowed={'artifacts/shrunk': 'was large', 'artifacts/deleted': 'was large'})['problems']
    assert problems == ['artifacts/deleted: allowlisted but not tracked; remove the entry',
                        'artifacts/shrunk: allowlisted but within the file limit; remove the entry']


def test_command_exit_codes(tmp_path, monkeypatch, capsys):
    root = repo(tmp_path, {'artifacts/a.json': 300, 'artifacts/b.json': 300})
    monkeypatch.setattr(budget, 'ALLOWED_LARGE', {})
    monkeypatch.setattr(budget, 'MAX_FILE_BYTES', 1000)
    monkeypatch.setattr(budget, 'BUDGET_BYTES', 600)
    assert budget.main(['--root', str(root)]) == 0
    monkeypatch.setattr(budget, 'BUDGET_BYTES', 599)
    assert budget.main(['--root', str(root)]) == 1
    assert 'FAIL: tracked artifacts/ holds 600 bytes' in capsys.readouterr().out
    outside = tmp_path/'not-a-repo'
    outside.mkdir()
    assert budget.main(['--root', str(outside)]) == 2
