"""Retry an explicit, reconciled subset of documented finding proof targets.

This never changes an upstream file or removes failed selections. Old reports
select the queue; they are not treated as fresh proof-checking observations.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.extract_finding_proofs import PIN, inventory, write
from proofreader.lean import run_bounded
from proofreader.narrative_io import extract_narrative


def selected_targets(project: Path, selections: list[dict], shard: int, shards: int) -> list[dict]:
    if not 0 <= shard < shards <= 64:
        raise ValueError('Invalid shard')
    universe = {(r['module'], r['name']): r for r in inventory(project, 0, 1)}
    keys = []
    for row in selections:
        if not isinstance(row, dict) or set(row) != {'module', 'name'}:
            raise ValueError('Selection requires exactly module and name')
        key = (row['module'], row['name'])
        if key not in universe or universe[key]['kind'] != 'theorem' or key in keys:
            raise ValueError('Unknown, duplicate, or non-theorem selection')
        keys.append(key)
    # Assign whole modules, not unrelated mathematical families. Each selected
    # module is built once in this run, regardless of its theorem count.
    return [dict(universe[k]) for k in sorted(keys)
            if int(sha256(k[0].encode()).hexdigest(), 16) % shards == shard]


def run(project: Path, output: Path, selections: list[dict], shard: int, shards: int,
        *, trust_project: bool = False, wall_seconds: int = 2400,
        build_timeout: int = 900, extract_timeout: int = 180) -> dict:
    if not trust_project:
        raise PermissionError('--trust-project is required; Lean elaboration executes code')
    if output.exists():
        raise ValueError('Use a new output directory')
    if not 1 <= wall_seconds <= 14400 or not 1 <= build_timeout <= 3600 or not 1 <= extract_timeout <= 1200:
        raise ValueError('Invalid execution budget')
    rows = selected_targets(project, selections, shard, shards)
    output.mkdir(parents=True)
    started = time.monotonic()
    report = {'schema': 'leanglish.finding-proof-shard/v1', 'upstream_commit': PIN,
        'shard': shard, 'shards': shards, 'selection_count': len(selections),
        'selection_sha256': sha256(json.dumps(selections, sort_keys=True).encode()).hexdigest(),
        'scope': 'explicit-retry-subset-unaltered-modules-upstream-shared-dependency-pins',
        'whole_upstream_project_build': False, 'targets': rows, 'expected_targets': len(rows),
        'expected_theorems': len(rows), 'all_targets_accounted': True,
        'english_formally_certified': False}
    def checkpoint():
        report.update(elapsed_seconds=round(time.monotonic()-started, 2),
            kernel_checked=sum(r['kernel_checked'] for r in rows),
            readers_written=sum(r['status']=='reading-generated' for r in rows),
            pending=sum(r['status'] in {'pending','building','extracting'} for r in rows))
        write(output/'proofs.json', report)
    checkpoint()
    version = run_bounded(['lake','env','lean','--version'], project, timeout=60)
    if version.status != 'passed' or '4.34.1' not in version.stdout:
        for row in rows: row['status'] = 'toolchain-unavailable'
        checkpoint()
        return report
    builds = {}
    for row in rows:
        remaining = wall_seconds-(time.monotonic()-started)
        if remaining < 10:
            row['status']='deadline-not-attempted'; checkpoint(); continue
        module = row['module']; source=project/(module.replace('.','/')+'.lean')
        if not source.is_file():
            row['status']='source-missing'; checkpoint(); continue
        row['source_sha256']=sha256(source.read_bytes()).hexdigest()
        if module not in builds:
            row['status']='building'; checkpoint()
            built=run_bounded(['lake','build',module],project,
                timeout=min(build_timeout,remaining),max_output=4000000)
            directory=output/'builds'; directory.mkdir(exist_ok=True)
            write(directory/(sha256(module.encode()).hexdigest()[:24]+'.json'),asdict(built))
            builds[module]=built
        built=builds[module]
        if built.status!='passed':
            row['status']='build-'+built.status
            row['reason']=(built.reason or built.stderr[-2000:])[:2000]
            checkpoint(); continue
        remaining=wall_seconds-(time.monotonic()-started)
        if remaining<10:
            row['status']='deadline-not-extracted'; checkpoint(); continue
        row['status']='extracting'; checkpoint()
        out=output/'targets'/row['id']; out.mkdir(parents=True)
        try:
            receipt=extract_narrative(row['name'],out,module=module,project=project,
                version='4.34.1',trust_project=True,timeout=min(extract_timeout,remaining))
            stable=sha256(source.read_bytes()).hexdigest()==row['source_sha256']
            if receipt['status']=='passed' and stable:
                row.update(status='reading-generated',kernel_checked=True,
                    directory='targets/'+row['id'],coverage=json.loads((out/'coverage.json').read_text()),
                    selected_judgements=receipt.get('selected_judgements'),
                    snapshot_sha256=receipt.get('snapshot_sha256'))
            else:
                row.update(status='extraction-failed',errors=receipt.get('errors',[]))
                if not stable: row['errors'].append('Original source changed during extraction')
        except (ValueError,OSError,RuntimeError,RecursionError) as exc:
            row.update(status='extraction-failed',errors=[str(exc)[:2000]])
        print(row['name'],row['status'],flush=True)
        checkpoint()
    checkpoint()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--selection',required=True,type=Path)
    p.add_argument('--shard',required=True,type=int)
    p.add_argument('--shards',default=16,type=int)
    p.add_argument('--wall-seconds',default=2400,type=int)
    p.add_argument('--build-timeout',default=900,type=int)
    p.add_argument('--extract-timeout',default=180,type=int)
    p.add_argument('--trust-project',action='store_true')
    a=p.parse_args()
    report=run(a.project.resolve(),a.output.resolve(),json.loads(a.selection.read_text()),
        a.shard,a.shards,trust_project=a.trust_project,wall_seconds=a.wall_seconds,
        build_timeout=a.build_timeout,extract_timeout=a.extract_timeout)
    print(json.dumps({k:v for k,v in report.items() if k!='targets'},indent=2))
    return 0 if report['kernel_checked']==report['expected_theorems'] else 2
if __name__=='__main__': raise SystemExit(main())
