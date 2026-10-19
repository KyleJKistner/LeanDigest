"""Bounded, resumable compilation in the unchanged original Lake project.

A checkpoint is a build acceleration input, NEVER a proof receipt. Final library,
Comparator and narrative checks must still execute their original commands.
Dependency sources and approved patches are independently audited. Compiled caches
and the compiler remain trusted; hashes are consistency checks, not attestations.
"""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import io
import json
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
from .original_project import audit_environment, child, digest, file_hash, read, write, validate_plan
from .proof_campaign import check_environment
from .lean import run_bounded

SCHEMA = 'leanglish.build-checkpoint/v1'
STATE = 'leanglish.build-resume-state/v1'
MAX_FILES = 300_000
MAX_BYTES = 8_000_000_000
MAX_MANIFEST = 100_000_000


def allowed_path(name: str, dependencies: dict) -> bool:
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        return False
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or name != p.as_posix():
        return False
    parts = p.parts
    return (len(parts) > 2 and parts[:2] == ('.lake', 'build') or
            len(parts) > 5 and parts[:2] == ('.lake', 'packages') and
            parts[2] in dependencies and parts[3:5] == ('.lake', 'build'))


def assets(project: Path, dependencies: dict) -> dict:
    """Inventory only regular files inside approved build directories."""
    roots = [project/'.lake/build'] + [project/'.lake/packages'/n/'.lake/build' for n in sorted(dependencies)]
    result = {}
    total = 0
    for root in roots:
        if not root.exists():
            continue
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                p = Path(directory)/name
                relative = p.relative_to(project).as_posix()
                if p.is_symlink():
                    raise ValueError('Checkpoint build tree contains a symbolic link')
                if p.is_dir():
                    continue
                if not p.is_file() or not allowed_path(relative, dependencies):
                    raise ValueError('Checkpoint includes a non-build or non-regular file')
                total += p.stat().st_size
                if len(result) >= MAX_FILES or total > MAX_BYTES:
                    raise ValueError('Build checkpoint inventory limit exceeded')
                result[relative] = {'sha256': file_hash(p), 'size': p.stat().st_size,
                                    'executable': bool(p.stat().st_mode & 0o111)}
    return result


def target_allowed(plan: dict, target: str) -> bool:
    return isinstance(target, str) and any(
        target == t.get('library') or target in (t.get('solution_module'), t.get('challenge_module'))
        for t in plan['tasks'])


def initialize(project: Path, plan: dict, environment: dict, state_dir: Path, target: str,
               *, trust_project: bool = False) -> dict:
    if not trust_project:
        raise PermissionError('Build execution requires --trust-project')
    validate_plan(plan)
    check_environment(plan, environment)
    if not target_allowed(plan, target):
        raise ValueError('Target is not in the complete original project plan')
    if state_dir.exists():
        raise ValueError('Resume state must start in a fresh directory')
    actual = audit_environment(project, plan)
    if actual != environment:
        raise ValueError('Original environment differs from the pinned audit')
    baseline = assets(project, plan['dependencies'])
    state = {'schema': STATE, 'target': target, 'plan_sha256': plan['plan_sha256'],
             'environment_sha256': environment['environment_sha256'],
             'baseline': baseline, 'baseline_sha256': digest(baseline),
             'rounds': [], 'build_passed': False, 'proof_verified': False}
    write(state_dir/'state.json', state)
    return state


def validate_state(state: dict, plan: dict, environment: dict) -> dict:
    validate_plan(plan)
    check_environment(plan, environment)
    if (state.get('schema') != STATE or state.get('plan_sha256') != plan['plan_sha256'] or
        state.get('environment_sha256') != environment['environment_sha256'] or
        not target_allowed(plan, state.get('target')) or
        state.get('baseline_sha256') != digest(state.get('baseline')) or
        state.get('proof_verified') is not False or not isinstance(state.get('rounds'), list)):
        raise ValueError('Build resume state identity mismatch')
    if any(not allowed_path(n, plan['dependencies']) for n in state['baseline']):
        raise ValueError('Baseline contains a non-build path')
    return state


def run_round(project: Path, plan: dict, environment: dict, state_dir: Path, output: Path,
              *, trust_project: bool = False, seconds: int = 1800) -> dict:
    if not trust_project:
        raise PermissionError('Build execution requires --trust-project')
    if type(seconds) is not int or not 1 <= seconds <= 3600 or output.exists():
        raise ValueError('Use a bounded round and a fresh output directory')
    state = validate_state(read(state_dir/'state.json'), plan, environment)
    before = audit_environment(project, plan)
    if before != environment:
        raise ValueError('Source/dependency drift before build round')
    command = ['lake', 'build', state['target']]
    # Never infer success from old state.json or the existence of .olean files.
    result = run_bounded(command, project, timeout=seconds, max_output=32_000_000)
    write(output/'execution.json', asdict(result))
    after = audit_environment(project, plan)
    stable = after == environment
    record = {'schema': 'leanglish.build-round/v1', 'target': state['target'],
              'plan_sha256': plan['plan_sha256'], 'environment_before': before,
              'environment_after': after, 'seconds': seconds,
              'execution_sha256': file_hash(output/'execution.json'),
              'status': 'passed' if stable and result.status == 'passed' else
                        'timeout' if stable and result.reason == 'timeout' else 'failed',
              'proof_verified': False}
    write(output/'round.json', record)
    if not stable:
        raise ValueError('Source/dependency drift during build round')
    state['rounds'].append({'round_sha256': digest(record), 'status': record['status']})
    state['build_passed'] = record['status'] == 'passed'
    write(state_dir/'state.json', state)
    return record


def pack(project: Path, plan: dict, environment: dict, state_dir: Path, archive: Path) -> dict:
    """Store only changed build artifacts relative to the exact restored seed."""
    state = validate_state(read(state_dir/'state.json'), plan, environment)
    if archive.exists():
        raise ValueError('Never overwrite a retained build checkpoint')
    if audit_environment(project, plan) != environment:
        raise ValueError('Do not checkpoint a changed source environment')
    current = assets(project, plan['dependencies'])
    baseline = state['baseline']
    changed = {n: v for n, v in current.items() if baseline.get(n) != v}
    removed = sorted(set(baseline) - set(current))
    record = {'schema': SCHEMA, 'plan_sha256': plan['plan_sha256'],
              'environment_sha256': environment['environment_sha256'],
              'target': state['target'], 'baseline_sha256': state['baseline_sha256'],
              'files': changed, 'removed': removed, 'rounds': state['rounds'],
              'proof_verified': False, 'cache_authenticity_certified': False}
    record['checkpoint_sha256'] = digest(record)
    payload = json.dumps(record, sort_keys=True).encode()
    if len(payload) > MAX_MANIFEST:
        raise ValueError('Build checkpoint manifest limit exceeded')
    archive.parent.mkdir(parents=True, exist_ok=True)
    pending = archive.with_name(archive.name+'.pending')
    try:
        with tarfile.open(pending, 'w:gz', compresslevel=2) as tar:
            info = tarfile.TarInfo('CHECKPOINT.json');info.size = len(payload);info.mode = 0o644
            tar.addfile(info, io.BytesIO(payload))
            for name, item in sorted(changed.items()):
                path = child(project, name)
                if file_hash(path) != item['sha256'] or path.stat().st_size != item['size']:
                    raise ValueError('Build file changed while checkpointing')
                info = tarfile.TarInfo(name);info.size = item['size']
                info.mode = 0o755 if item['executable'] else 0o644
                with path.open('rb') as src:tar.addfile(info, src)
        pending.replace(archive)
    finally:
        if pending.exists():pending.unlink()
    result = {'archive_sha256': file_hash(archive), 'checkpoint_sha256': record['checkpoint_sha256'],
              'changed_files': len(changed), 'removed_files': len(removed),
              'uncompressed_bytes': sum(v['size'] for v in changed.values()),
              'proof_verified': False}
    write(archive.with_suffix(archive.suffix+'.json'), result)
    return result


def restore(project: Path, plan: dict, environment: dict, state_dir: Path, archive: Path,
            expected_sha256: str, *, trust_project: bool = False) -> dict:
    """Validate the whole delta before installing any compiled files."""
    if not trust_project:
        raise PermissionError('Restoring executable build artifacts requires --trust-project')
    state = validate_state(read(state_dir/'state.json'), plan, environment)
    if file_hash(archive) != expected_sha256:
        raise ValueError('Build checkpoint archive digest mismatch')
    if audit_environment(project, plan) != environment:
        raise ValueError('Original environment drift before checkpoint restore')
    if assets(project, plan['dependencies']) != state['baseline']:
        raise ValueError('Checkpoint restore requires the exact fresh seed build inventory')
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        if (not members or len(members) > MAX_FILES+1 or
            sum(m.size for m in members) > MAX_BYTES+MAX_MANIFEST or
            members[0].name != 'CHECKPOINT.json' or not members[0].isfile() or
            members[0].size > MAX_MANIFEST or any(not m.isfile() for m in members)):
            raise ValueError('Unsafe or oversized checkpoint archive')
        record = json.load(tar.extractfile(members[0]))
        if (record.get('schema') != SCHEMA or record.get('plan_sha256') != plan['plan_sha256'] or
            record.get('environment_sha256') != environment['environment_sha256'] or
            record.get('baseline_sha256') != state['baseline_sha256'] or
            record.get('target') != state['target'] or record.get('proof_verified') is not False or
            record.get('checkpoint_sha256') != digest({k:v for k,v in record.items() if k!='checkpoint_sha256'})):
            raise ValueError('Checkpoint source/target identity mismatch')
        names = [m.name for m in members[1:]]
        files, removed = record['files'], record['removed']
        if (len(set(names)) != len(names) or set(names) != set(files) or
            removed != sorted(set(removed)) or not set(removed) <= set(state['baseline']) or
            set(removed) & set(files) or
            any(not allowed_path(n, plan['dependencies']) for n in names+removed)):
            raise ValueError('Checkpoint contains duplicate, missing, or non-build paths')
        # Stage outside the source tree; no tar.extractall or arbitrary writes.
        with tempfile.TemporaryDirectory(prefix='leanglish-build-restore-') as tmp:
            staged = Path(tmp)
            for index, member in enumerate(members[1:]):
                item = files[member.name]
                if member.size != item['size'] or type(item['executable']) is not bool:
                    raise ValueError('Checkpoint file metadata mismatch')
                target = staged/str(index)
                with tar.extractfile(member) as src, target.open('xb') as dst:
                    for block in iter(lambda:src.read(1 << 20), b''):dst.write(block)
                if file_hash(target) != item['sha256']:
                    raise ValueError('Checkpoint file digest mismatch')
            for name in names+removed:child(project,name)
            for name in removed:child(project,name).unlink()
            for index, name in enumerate(names):
                dst=child(project,name);dst.parent.mkdir(parents=True,exist_ok=True)
                import shutil
                shutil.copyfile(staged/str(index),dst)
                dst.chmod(0o755 if files[name]['executable'] else 0o644)
    if audit_environment(project,plan) != environment:
        raise ValueError('Original environment drift after checkpoint restore')
    state['rounds'] = record['rounds']
    state['build_passed'] = False
    state['restored_checkpoint_sha256'] = record['checkpoint_sha256']
    write(state_dir/'state.json',state)
    return {'restored_files':len(names),'checkpoint_sha256':record['checkpoint_sha256'],
            'proof_verified':False,'build_passed':False}
