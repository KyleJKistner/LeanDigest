"""Resumable compilation in the unchanged original OpenAI Lake project.

Compiled checkpoints accelerate builds; they never establish proof acceptance.
Final library, Comparator and narrative commands still execute independently.
The source/dependency audit is unchanged. Compiler and compiled-cache authenticity
remain trusted; hashes are consistency checks, not signed attestations.
"""
from __future__ import annotations
from dataclasses import asdict
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tarfile
import tempfile
from .original_project import audit_environment, child, digest, file_hash, read, write, validate_plan
from .proof_campaign import check_environment
from .lean import run_bounded

SCHEMA = 'leanglish.build-checkpoint/v1'
STATE = 'leanglish.build-resume-state/v1'
MAX_FILES = 500_000
MAX_BYTES = 40_000_000_000
MAX_MANIFEST = 100_000_000
SHA = re.compile(r'[a-f0-9]{64}')


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


def validate_inventory(value: dict, dependencies: dict) -> dict:
    if not isinstance(value, dict) or len(value) > MAX_FILES:
        raise ValueError('Invalid checkpoint file inventory')
    total = 0
    for name, item in value.items():
        if (not allowed_path(name, dependencies) or not isinstance(item, dict) or
            set(item) != {'sha256', 'size', 'executable'} or
            not isinstance(item['sha256'], str) or not SHA.fullmatch(item['sha256']) or
            type(item['size']) is not int or item['size'] < 0 or
            type(item['executable']) is not bool):
            raise ValueError('Invalid checkpoint file identity')
        total += item['size']
        if total > MAX_BYTES:
            raise ValueError('Build checkpoint inventory limit exceeded')
    return value


def assets(project: Path, dependencies: dict) -> dict:
    """Only regular files below approved build roots; reject linked parents too."""
    relatives = ['.lake/build'] + ['.lake/packages/'+n+'/.lake/build' for n in sorted(dependencies)]
    result = {}; total = 0
    for relative in relatives:
        root = child(project, relative)
        if not root.exists():
            continue
        if not root.is_dir():
            raise ValueError('Build root is not a directory')
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                path = Path(directory)/name
                relative = path.relative_to(project).as_posix()
                if path.is_symlink():
                    raise ValueError('Checkpoint build tree contains a symbolic link')
                if path.is_dir():
                    continue
                if not path.is_file() or not allowed_path(relative, dependencies):
                    raise ValueError('Checkpoint includes a non-build or non-regular file')
                size = path.stat().st_size; total += size
                if len(result) >= MAX_FILES or total > MAX_BYTES:
                    raise ValueError('Build checkpoint inventory limit exceeded')
                result[relative] = {'sha256': file_hash(path), 'size': size,
                                    'executable': bool(path.stat().st_mode & 0o111)}
    return result


def target_allowed(plan: dict, target: str) -> bool:
    return isinstance(target, str) and any(
        target == task.get('library') or target in (task.get('solution_module'), task.get('challenge_module'))
        for task in plan['tasks'])


def initialize(project: Path, plan: dict, environment: dict, state_dir: Path, target: str,
               *, trust_project: bool = False) -> dict:
    if not trust_project:
        raise PermissionError('Build execution requires --trust-project')
    validate_plan(plan); check_environment(plan, environment)
    if not target_allowed(plan, target):
        raise ValueError('Target is not in the complete original project plan')
    if state_dir.exists():
        raise ValueError('Resume state must start in a fresh directory')
    if audit_environment(project, plan) != environment:
        raise ValueError('Original environment differs from the pinned audit')
    baseline = assets(project, plan['dependencies'])
    state = {'schema': STATE, 'target': target, 'plan_sha256': plan['plan_sha256'],
             'environment_sha256': environment['environment_sha256'],
             'baseline': baseline, 'baseline_sha256': digest(baseline),
             'rounds': [], 'build_passed': False, 'proof_verified': False}
    write(state_dir/'state.json', state)
    return state


def validate_state(state: dict, plan: dict, environment: dict) -> dict:
    validate_plan(plan); check_environment(plan, environment)
    if (not isinstance(state, dict) or state.get('schema') != STATE or
        state.get('plan_sha256') != plan['plan_sha256'] or
        state.get('environment_sha256') != environment['environment_sha256'] or
        not target_allowed(plan, state.get('target')) or
        state.get('baseline_sha256') != digest(state.get('baseline')) or
        state.get('proof_verified') is not False or not isinstance(state.get('rounds'), list)):
        raise ValueError('Build resume state identity mismatch')
    validate_inventory(state['baseline'], plan['dependencies'])
    for row in state['rounds']:
        if (not isinstance(row, dict) or set(row) != {'round_sha256','status'} or
            row['status'] not in {'passed','timeout','failed'} or
            not isinstance(row['round_sha256'],str) or not SHA.fullmatch(row['round_sha256'])):
            raise ValueError('Invalid checkpoint round history')
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
    """Save the cumulative build delta relative to the exact restored seed."""
    state = validate_state(read(state_dir/'state.json'), plan, environment)
    if archive.exists():
        raise ValueError('Never overwrite a retained build checkpoint')
    if audit_environment(project, plan) != environment:
        raise ValueError('Do not checkpoint a changed source environment')
    current = assets(project, plan['dependencies']); baseline = state['baseline']
    changed = {name: item for name, item in current.items() if baseline.get(name) != item}
    record = {'schema': SCHEMA, 'plan_sha256': plan['plan_sha256'],
              'environment_sha256': environment['environment_sha256'],
              'target': state['target'], 'baseline_sha256': state['baseline_sha256'],
              'files': changed, 'removed': sorted(set(baseline)-set(current)),
              'rounds': state['rounds'], 'proof_verified': False,
              'cache_authenticity_certified': False}
    record['checkpoint_sha256'] = digest(record)
    payload = json.dumps(record, sort_keys=True).encode()
    if len(payload) > MAX_MANIFEST:
        raise ValueError('Build checkpoint manifest limit exceeded')
    archive.parent.mkdir(parents=True, exist_ok=True)
    pending = archive.with_name(archive.name+'.pending')
    try:
        with tarfile.open(pending, 'w:gz', compresslevel=2) as tar:
            info = tarfile.TarInfo('CHECKPOINT.json'); info.size = len(payload); info.mode = 0o644
            tar.addfile(info, io.BytesIO(payload))
            for name, item in sorted(changed.items()):
                path = child(project, name)
                if file_hash(path) != item['sha256'] or path.stat().st_size != item['size']:
                    raise ValueError('Build file changed while checkpointing')
                info = tarfile.TarInfo(name); info.size = item['size']
                info.mode = 0o755 if item['executable'] else 0o644
                with path.open('rb') as src: tar.addfile(info, src)
        pending.replace(archive)
    finally:
        if pending.exists(): pending.unlink()
    result = {'archive_sha256': file_hash(archive), 'checkpoint_sha256': record['checkpoint_sha256'],
              'changed_files': len(changed), 'removed_files': len(record['removed']),
              'uncompressed_bytes': sum(item['size'] for item in changed.values()),
              'proof_verified': False}
    write(archive.with_suffix(archive.suffix+'.json'), result)
    return result


def restore(project: Path, plan: dict, environment: dict, state_dir: Path, archive: Path,
            expected_sha256: str, *, trust_project: bool = False) -> dict:
    """Validate the complete archive in temporary storage before installing files."""
    if not trust_project:
        raise PermissionError('Restoring executable build artifacts requires --trust-project')
    state = validate_state(read(state_dir/'state.json'), plan, environment)
    if archive.stat().st_size > MAX_BYTES or file_hash(archive) != expected_sha256:
        raise ValueError('Build checkpoint archive digest or size mismatch')
    if audit_environment(project, plan) != environment:
        raise ValueError('Original environment drift before checkpoint restore')
    if assets(project, plan['dependencies']) != state['baseline']:
        raise ValueError('Checkpoint restore requires the exact fresh seed build inventory')
    with tarfile.open(archive, 'r:gz') as tar:
        members = []; size = 0
        for member in tar:
            size += member.size
            if not member.isfile() or len(members) >= MAX_FILES+1 or size > MAX_BYTES+MAX_MANIFEST:
                raise ValueError('Unsafe or oversized checkpoint archive')
            members.append(member)
        if not members or members[0].name != 'CHECKPOINT.json' or members[0].size > MAX_MANIFEST:
            raise ValueError('Missing bounded checkpoint manifest')
        record = json.load(tar.extractfile(members[0]))
        if (not isinstance(record,dict) or record.get('schema') != SCHEMA or
            record.get('plan_sha256') != plan['plan_sha256'] or
            record.get('environment_sha256') != environment['environment_sha256'] or
            record.get('baseline_sha256') != state['baseline_sha256'] or
            record.get('target') != state['target'] or record.get('proof_verified') is not False or
            record.get('checkpoint_sha256') != digest({k:v for k,v in record.items() if k!='checkpoint_sha256'})):
            raise ValueError('Checkpoint source/target identity mismatch')
        names = [member.name for member in members[1:]]
        files = validate_inventory(record.get('files'), plan['dependencies'])
        removed = record.get('removed')
        if (not isinstance(removed,list) or any(not isinstance(n,str) for n in removed) or
            len(set(names)) != len(names) or set(names) != set(files) or
            removed != sorted(set(removed)) or not set(removed) <= set(state['baseline']) or
            set(removed) & set(files) or
            any(not allowed_path(name, plan['dependencies']) for name in removed)):
            raise ValueError('Checkpoint contains duplicate, missing, or non-build paths')
        next_state = dict(state, rounds=record.get('rounds'), build_passed=False,
                          restored_checkpoint_sha256=record['checkpoint_sha256'])
        validate_state(next_state,plan,environment)
        with tempfile.TemporaryDirectory(prefix='leanglish-build-restore-') as tmp:
            staged = Path(tmp)
            for index, member in enumerate(members[1:]):
                item = files[member.name]
                if member.size != item['size']:
                    raise ValueError('Checkpoint file metadata mismatch')
                target = staged/str(index)
                with tar.extractfile(member) as src, target.open('xb') as dst:
                    shutil.copyfileobj(src,dst,1 << 20)
                if file_hash(target) != item['sha256']:
                    raise ValueError('Checkpoint file digest mismatch')
            for name in names+removed: child(project,name)
            for name in removed: child(project,name).unlink()
            for index,name in enumerate(names):
                destination = child(project,name); destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(staged/str(index),destination)
                destination.chmod(0o755 if files[name]['executable'] else 0o644)
    if audit_environment(project,plan) != environment:
        raise ValueError('Original environment drift after checkpoint restore')
    write(state_dir/'state.json',next_state)
    return {'restored_files':len(names),'checkpoint_sha256':record['checkpoint_sha256'],
            'proof_verified':False,'build_passed':False}
