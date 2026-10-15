"""Bounded, exhaustive target queue for the documented OpenAI findings.

All targets are recorded before any build. A deadline or failure never removes a
target. Definition references are not counted as theorem proofs. A successful
source-bound reading is not a formal verification of the English renderer.
"""
from __future__ import annotations
from dataclasses import asdict
from hashlib import sha256
import argparse
import json
import os
from pathlib import Path
import re
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.lean import run_bounded
from proofreader.narrative_io import extract_narrative

PIN='1581d4cbdd69a0faf34b2089614fe2a814316a6a'
VALID=re.compile(r'[A-Za-z_][A-Za-z0-9_.]*')


def inventory(project: Path, shard: int, shards: int) -> list[dict]:
    if not 0<=shard<shards<=64:raise ValueError('Invalid shard')
    targets={}
    for path in sorted((project/'ComparatorChallenges').glob('*.json')):
        cfg=json.loads(path.read_text());module=cfg['solution_module']
        if not VALID.fullmatch(module) or not module.startswith('OAI.'):
            raise ValueError('Unsafe solution module')
        family_prefix='.'.join(module.split('.')[:3])
        if int(sha256(family_prefix.encode()).hexdigest(),16)%shards!=shard:continue
        for field,kind in [('theorem_names','theorem'),('definition_names','definition')]:
            for name in cfg.get(field,[]):
                if not VALID.fullmatch(name):raise ValueError('Unsafe target name')
                tid=sha256((module+'\0'+name).encode()).hexdigest()[:24]
                if tid not in targets:
                    targets[tid]={'id':tid,'module':module,'name':name,'kind':kind,'configurations':[],
                                  'status':'pending','kernel_checked':False,'english_formally_certified':False}
                if targets[tid]['kind']!=kind:raise ValueError('Conflicting target roles')
                targets[tid]['configurations'].append(path.stem)
    return sorted(targets.values(),key=lambda r:(r['module'],r['name']))


def write(path: Path,value: dict):
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    tmp.replace(path)


def run(project: Path,output: Path,shard: int,shards: int,*,trust_project=False,wall_seconds=2400):
    if not trust_project:raise PermissionError('--trust-project is required; source elaboration executes code')
    if output.exists():raise ValueError('Use a new output directory')
    if not 1<=wall_seconds<=14400:raise ValueError('Invalid wall-clock budget')
    output.mkdir(parents=True)
    rows=inventory(project,shard,shards)
    started=time.monotonic()
    report={'schema':'leanglish.finding-proof-shard/v1','upstream_commit':PIN,'shard':shard,'shards':shards,
            'scope':'unaltered-OAI-modules-with-upstream-shared-dependency-pins',
            'whole_upstream_project_build':False,'targets':rows,'expected_targets':len(rows),
            'expected_theorems':sum(r['kind']=='theorem' for r in rows),'all_targets_accounted':True,
            'english_formally_certified':False}
    def checkpoint():
        report['elapsed_seconds']=round(time.monotonic()-started,2)
        report['kernel_checked']=sum(r['kernel_checked'] for r in rows)
        report['readers_written']=sum(r['status']=='reading-generated' for r in rows)
        report['pending']=sum(r['status'] in {'pending','building','extracting'} for r in rows)
        write(output/'proofs.json',report)
    checkpoint()
    version=run_bounded(['lake','env','lean','--version'],project,timeout=60)
    if version.status!='passed' or not re.search(r'\b4\.34\.1\b',version.stdout):
        raise ValueError('Expected Lean 4.34.1')
    builds={}
    for row in rows:
        if row['kind']=='definition':
            row['status']='definition-reference-not-a-proof-obligation';checkpoint();continue
        remaining=wall_seconds-(time.monotonic()-started)
        if remaining<10:
            row['status']='deadline-not-attempted';checkpoint();continue
        module=row['module'];out=output/'targets'/row['id'];out.mkdir(parents=True)
        source=project/(module.replace('.','/')+'.lean')
        if not source.is_file():
            row['status']='source-missing';checkpoint();continue
        row['source_sha256']=sha256(source.read_bytes()).hexdigest()
        if module not in builds:
            row['status']='building';checkpoint()
            built=run_bounded(['lake','build',module],project,timeout=min(600,remaining),max_output=4_000_000)
            build_id=sha256(module.encode()).hexdigest()[:24]
            dest=output/'builds';dest.mkdir(exist_ok=True)
            write(dest/(build_id+'.json'),asdict(built))
            builds[module]=built
        built=builds[module]
        if built.status!='passed':
            row['status']='build-'+built.status;row['reason']=(built.reason or built.stderr[-2000:])[:2000]
            checkpoint();continue
        remaining=wall_seconds-(time.monotonic()-started)
        if remaining<10:row['status']='deadline-not-extracted';checkpoint();continue
        row['status']='extracting';checkpoint()
        try:
            receipt=extract_narrative(row['name'],out,module=module,project=project,version='4.34.1',
                                      trust_project=True,timeout=min(120,remaining))
            if receipt['status']=='passed' and sha256(source.read_bytes()).hexdigest()==row['source_sha256']:
                row['status']='reading-generated';row['kernel_checked']=True
                row['directory']='targets/'+row['id']
                coverage=json.loads((out/'coverage.json').read_text())
                row['coverage']=coverage
                row['selected_judgements']=receipt.get('selected_judgements')
                row['snapshot_sha256']=receipt.get('snapshot_sha256')
            else:
                row['status']='extraction-failed';row['errors']=receipt.get('errors',[])
        except (ValueError,OSError,RuntimeError,RecursionError) as exc:
            row['status']='extraction-failed';row['errors']=[str(exc)[:2000]]
        print(row['name'],row['status'],flush=True)
        checkpoint()
    checkpoint()
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--shard',required=True,type=int);p.add_argument('--shards',default=16,type=int)
    p.add_argument('--wall-seconds',default=2400,type=int);p.add_argument('--trust-project',action='store_true')
    a=p.parse_args();r=run(a.project.resolve(),a.output.resolve(),a.shard,a.shards,trust_project=a.trust_project,wall_seconds=a.wall_seconds)
    print(json.dumps({k:v for k,v in r.items() if k!='targets'},indent=2))
    return 0 if r['kernel_checked']==r['expected_theorems'] else 2
if __name__=='__main__':raise SystemExit(main())
