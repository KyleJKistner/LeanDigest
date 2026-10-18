"""Freeze and download completed original-project evidence, without rerunning jobs.

Only artifact contents present in a stable, time-bounded GitHub inventory are
selected. The archive digest is checked before safe extraction. Job colors are
metadata, not proof results. GH_TOKEN is consumed by gh, never recorded here.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import zipfile

RUNS = {
    'original-build': (39141760623, ('original-project-seed', 'validated-comparator-toolchain',
                                   'original-library-', 'original-comparison-')),
    'original-proofs': (39144564607, ('original-proof-',)),
}


def api(repository: str, path: str, *, paged: bool = False):
    command = ['gh', 'api', f'repos/{repository}/{path}']
    if paged:
        command += ['--paginate', '--slurp']
    run = subprocess.run(command, capture_output=True, text=True, timeout=180, check=True)
    return json.loads(run.stdout)


def stable_artifacts(repository: str, run_id: int, prefixes: tuple[str, ...], cutoff: str) -> list[dict]:
    """Two identical filtered enumerations defeat pagination shifts from new uploads."""
    def once():
        pages = api(repository, f'actions/runs/{run_id}/artifacts?per_page=100', paged=True)
        found = {}
        for page in pages:
            for item in page['artifacts']:
                if item['created_at'] > cutoff or not item['name'].startswith(prefixes):
                    continue
                if item['id'] in found and found[item['id']] != item:
                    raise ValueError('Inconsistent artifact identity during pagination')
                found[item['id']] = item
        return sorted(found.values(), key=lambda x: x['id'])
    previous = once()
    for _ in range(3):
        current = once()
        if current == previous:
            names = [x['name'] for x in current]
            if len(names) != len(set(names)):
                raise ValueError('Multiple retained versions of an artifact name')
            return current
        previous = current
    raise ValueError('Artifact inventory did not stabilize; retry collection later')


def unpack(archive: Path, output: Path) -> int:
    """Reject traversal, links, duplicate paths, and unexpectedly large archives."""
    if output.exists():
        raise ValueError('Evidence directories must be fresh')
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        if len(infos) > 25000 or sum(x.file_size for x in infos) > 3_000_000_000:
            raise ValueError('Artifact expansion limit exceeded')
        seen = set()
        for item in infos:
            raw = item.filename.rstrip('/')
            p = PurePosixPath(raw)
            if (not raw or p.is_absolute() or '..' in p.parts or '\\' in raw or ':' in raw
                    or raw != p.as_posix() or raw in seen):
                raise ValueError('Unsafe or repeated artifact path')
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode) or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError('Non-regular artifact entry')
            seen.add(raw)
        output.mkdir(parents=True)
        for item in infos:
            target = output.joinpath(*PurePosixPath(item.filename).parts)
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(item) as src, target.open('xb') as dst:
                    shutil.copyfileobj(src, dst, 1 << 20)
    return len(infos)


def retain(repository: str, run: dict, artifact: dict, destination: Path) -> dict:
    name = artifact['name']
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in ('.', '..'):
        raise ValueError('Invalid artifact name')
    identity = artifact.get('workflow_run', {})
    if identity.get('id') != run['id'] or identity.get('head_sha') != run['head_sha']:
        raise ValueError('Artifact belongs to another run or source commit')
    expected = artifact.get('digest', '')
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', expected) or artifact['expired']:
        raise ValueError('No current digest-bound artifact available')
    if not 0 < artifact['size_in_bytes'] <= 1_000_000_000:
        raise ValueError('Archive size outside the allowed bound')
    archive = destination / (name + '.zip')
    if archive.exists():
        raise ValueError('Never overwrite retained evidence')
    with archive.open('xb') as out:
        subprocess.run(['gh', 'api', f'repos/{repository}/actions/artifacts/{artifact["id"]}/zip'],
                       stdout=out, stderr=subprocess.PIPE, timeout=300, check=True)
    with archive.open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    if archive.stat().st_size != artifact['size_in_bytes'] or 'sha256:' + actual != expected:
        raise ValueError('Downloaded artifact archive differs from frozen identity')
    entries = unpack(archive, destination / name)
    return {'id': artifact['id'], 'name': name, 'sha256': actual, 'entries': entries,
            'run_id': run['id'], 'source_commit': run['head_sha'], 'status': 'retained'}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', default='KyleJKistner/LeanDigest')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--allow-download', action='store_true')
    args = parser.parse_args()
    if not args.allow_download:
        parser.error('Artifact acquisition requires --allow-download')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repository):
        parser.error('Invalid repository')
    if args.output.exists():
        parser.error('Use a fresh collection output')
    args.output.mkdir(parents=True)
    cutoff = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    result = {'schema': 'leanglish.original-evidence-collection/v1', 'cutoff': cutoff,
              'repository': args.repository, 'runs': {}, 'errors': [],
              'all_expected_work_complete': False, 'observations_authenticated': False}
    try:
        for group, (run_id, prefixes) in RUNS.items():
            dest = args.output / group
            dest.mkdir()
            run = api(args.repository, f'actions/runs/{run_id}')
            artifacts = stable_artifacts(args.repository, run_id, prefixes, cutoff)
            (dest/'run.json').write_text(json.dumps(run, indent=2)+'\n')
            (dest/'frozen-artifacts.json').write_text(json.dumps(artifacts, indent=2)+'\n')
            jobs = api(args.repository, f'actions/runs/{run_id}/jobs?per_page=100', paged=True)
            (dest/'jobs-pages.json').write_text(json.dumps(jobs, indent=2)+'\n')
            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = [(a, pool.submit(retain, args.repository, run, a, dest)) for a in artifacts]
                outcomes = []
                for artifact, future in futures:
                    try:
                        outcomes.append(future.result())
                    except Exception as exc:
                        error = {'run_id': run_id, 'artifact_id': artifact['id'], 'name': artifact['name'],
                                 'error': str(exc), 'status': 'collection-failed'}
                        result['errors'].append(error)
                        outcomes.append(error)
            result['runs'][group] = {'run_id': run_id, 'source_commit': run['head_sha'],
                                     'cutoff': cutoff, 'outcomes': outcomes}
    finally:
        (args.output/'collection.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'cutoff': cutoff, 'retained': {k:len(v['outcomes']) for k,v in result['runs'].items()},
                      'collection_errors': len(result['errors'])}, indent=2))
    return 2 if result['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
