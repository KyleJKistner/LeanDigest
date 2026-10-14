#!/usr/bin/env python3
"""Prepare bounded context packs; explicitly opt into external-agent execution.
No provider is assumed. No automatic merge/push. This is not a sandbox.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import argparse
import fnmatch
import json
import re
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from proofreader.lean import run_bounded


def git(root: Path, *args: str) -> str:
    return subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True, text=True, timeout=30).stdout.strip()


def load_tasks(root: Path) -> list[dict[str, Any]]:
    data = json.loads((root / 'agents/tasks.json').read_text())
    if data.get('schema') != 'proofreader.agent-tasks/v1': raise ValueError('Unsupported task schema')
    tasks = data['tasks']
    ids = [t['id'] for t in tasks]
    if not tasks or len(ids) != len(set(ids)) or not all(re.fullmatch(r'[a-z][a-z0-9-]*', i) for i in ids):
        raise ValueError('Task identifiers must be unique safe names')
    return tasks


def context_packet(root: Path, task: dict) -> str:
    parts = [f"# ProofReader workstream: {task['id']}\n\n{task['goal']}\n",
             '# Required return\nWrite SUMMARY.md with changed files, exact checks and exit codes, unrun checks, blockers, counterexamples and next task. Do not claim checks you did not execute.\n',
             '# Ownership\n' + '\n'.join(task['allowed_paths']) + '\n',
             '# Acceptance\n' + '\n'.join(task['acceptance']) + '\n',
             '# Known blocker\n' + task['blocker'] + '\n']
    for relative in task['context']:
        path = (root / relative).resolve()
        path.relative_to(root.resolve())
        text = path.read_text(encoding='utf-8')
        if len(text) > 70_000: raise ValueError(f'Context file exceeds budget: {relative}')
        parts.append(f'\n# File: {relative}\n\n{text}\n')
    result = '\n'.join(parts)
    if len(result) > 220_000: raise ValueError('Task context exceeds budget; split the workstream')
    return result


def expand_command(template: list[str], prompt: Path, worktree: Path) -> list[str]:
    if not template or any(not isinstance(x, str) or '\x00' in x for x in template): raise ValueError('Command must be a nonempty JSON array of strings')
    if not any('{prompt}' in x for x in template): raise ValueError('Command must receive the context packet using {prompt}')
    return [x.replace('{prompt}', str(prompt)).replace('{worktree}', str(worktree)) for x in template]


def owned(path: str, patterns: list[str]) -> bool:
    return path == 'SUMMARY.md' or any(path.startswith(p) if p.endswith('/') else fnmatch.fnmatchcase(path, p) for p in patterns)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT / '.agent-runs' / 'handoff')
    p.add_argument('--execute', action='store_true', help='Execute configured external agents; arbitrary code, not sandboxed')
    p.add_argument('--command-json', help='Actual external-agent argv JSON containing {prompt}; no shell')
    p.add_argument('--workers', type=int, default=4)
    p.add_argument('--timeout', type=float, default=3600)
    a = p.parse_args(argv)
    try:
        if not 1 <= a.workers <= 4 or a.timeout <= 0: raise ValueError('Use 1–4 workers and a positive timeout')
        tasks = load_tasks(ROOT)
        output = a.output.resolve()
        output.mkdir(parents=True, exist_ok=True)
        if (output / 'team-results.json').exists(): raise ValueError('Use a fresh output directory to preserve previous run evidence')
        prompts = {}
        for task in tasks:
            prompt = output / f"{task['id']}.md"
            prompt.write_text(context_packet(ROOT, task), encoding='utf-8')
            prompts[task['id']] = prompt
        result = {'schema': 'proofreader.team-run/v1', 'mode': 'prepare', 'independent_agents_started': 0,
                  'tasks': [{'id': t['id'], 'prompt': str(prompts[t['id']])} for t in tasks]}
        if a.execute:
            if not a.command_json: raise ValueError('--execute requires an explicit --command-json')
            template = json.loads(a.command_json)
            if not isinstance(template, list): raise ValueError('Command must be a JSON array')
            expand_command(template, output, ROOT)
            if git(ROOT, 'status', '--porcelain'): raise ValueError('Commit/stash current changes before dispatch; the source checkout must be clean')
            baseline = git(ROOT, 'rev-parse', 'HEAD')
            worktrees = output / 'worktrees'
            worktrees.mkdir()
            plan = []
            suffix = baseline[:12] + '-' + output.name
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', suffix): raise ValueError('Output directory basename must be a safe branch component')
            for task in tasks:
                worktree = worktrees / task['id']
                branch = f"proofreader/{suffix}/{task['id']}"
                git(ROOT, 'worktree', 'add', '-b', branch, str(worktree), baseline)
                plan.append((task, worktree, branch))
            def run(item):
                task, worktree, branch = item
                command = expand_command(template, prompts[task['id']], worktree)
                execution = run_bounded(command, worktree, timeout=a.timeout, max_output=16_000_000)
                (output / f"{task['id']}.stdout.log").write_text(execution.stdout)
                (output / f"{task['id']}.stderr.log").write_text(execution.stderr)
                try:
                    changed = sorted(set(git(worktree, 'diff', '--name-only', baseline).splitlines() + git(worktree, 'ls-files', '--others', '--exclude-standard').splitlines()))
                except subprocess.SubprocessError:
                    changed = ['<unable-to-read-worktree>']
                return {'id': task['id'], 'branch': branch, 'worktree': str(worktree), 'status': execution.status,
                        'exit_code': execution.exit_code, 'reason': execution.reason, 'changed_files': changed,
                        'ownership_violations': [f for f in changed if not owned(f, task['allowed_paths'])],
                        'summary_present': (worktree / 'SUMMARY.md').is_file()}
            with ThreadPoolExecutor(max_workers=a.workers) as pool:
                rows = list(pool.map(run, plan))
            result.update(mode='execute', baseline=baseline, independent_agents_started=sum(r['status'] != 'unavailable' for r in rows),
                          tasks=rows, automatic_merge=False, automatic_push=False)
        (output / 'team-results.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
        return 0 if result['mode'] == 'prepare' or all(r['status'] == 'passed' and not r['ownership_violations'] and r['summary_present'] for r in result['tasks']) else 2
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(f'team: {exc}', file=sys.stderr)
        return 2

if __name__ == '__main__': raise SystemExit(main())
