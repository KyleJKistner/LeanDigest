"""Elaborate comparison statements, never certify their solution proofs.

The comparison files deliberately contain admitted specifications. Successful
runs here establish what was stated, not whether OpenAI's solution proves it.
Every requested target remains in the output, including timed-out modules.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from proofreader.lean import run_bounded

PIN = '1581d4cbdd69a0faf34b2089614fe2a814316a6a'
NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.]*')
MARKER = 'LEANGLISH_STATEMENT:'


def run(project: Path, output: Path, shard: int, shards: int, *, trust_project=False):
    if not trust_project:
        raise PermissionError('Statement elaboration executes upstream Lean; --trust-project is required')
    if not 0 <= shard < shards <= 64:
        raise ValueError('Invalid shard')
    if output.exists():
        raise ValueError('Output must be a new directory')
    output.mkdir(parents=True)
    configs = []
    for path in sorted((project/'ComparatorChallenges').glob('*.json')):
        key = path.stem
        if int(sha256(key.encode()).hexdigest(),16) % shards != shard:
            continue
        config = json.loads(path.read_text())
        if config.get('challenge_module') != 'ComparatorChallenges.'+key or not NAME.fullmatch(key):
            raise ValueError('Unsafe or mismatched comparison module')
        targets = config.get('theorem_names',[])+config.get('definition_names',[])
        if not targets or len(set(targets))!=len(targets) or any(not NAME.fullmatch(n) for n in targets):
            raise ValueError('Invalid comparison targets')
        configs.append((key,config,targets))
    identity = {'schema':'leanglish.statement-shard/v1','upstream_commit':PIN,
                'shard':shard,'shards':shards,'expected_configurations':len(configs),
                'expected_occurrences':sum(len(t) for _,_,t in configs),
                'solution_proofs_checked':0,'english_formally_certified':0}
    (output/'identity.json').write_text(json.dumps(identity,indent=2))
    version=run_bounded(['lake','env','lean','--version'],project,timeout=60)
    if version.status!='passed' or not re.search(r'\b4\.34\.1\b',version.stdout):
        raise ValueError('Expected Lean 4.34.1')
    exporter=run_bounded(['lake','build','FindingStatements'],project,timeout=120)
    (output/'exporter-build.json').write_text(json.dumps(asdict(exporter),indent=2))
    if exporter.status!='passed':
        raise ValueError('Statement exporter did not compile')
    def one(item):
        key,cfg,targets=item
        out=output/key;out.mkdir()
        record={'configuration':key,'solution_module':cfg['solution_module'],
                'challenge_module':cfg['challenge_module'],'upstream_commit':PIN,
                'status':'not-run','targets':[], 'solution_proof_checked':False}
        challenge=project/'ComparatorChallenges'/(key+'.lean')
        source_digest=sha256(challenge.read_bytes()).hexdigest()
        record['challenge_sha256']=source_digest
        built=run_bounded(['lake','build',cfg['challenge_module']],project,timeout=180,max_output=4_000_000)
        (out/'build.json').write_text(json.dumps(asdict(built),ensure_ascii=False))
        record['status']='build-'+built.status
        rows={}
        if built.status=='passed':
            driver='import '+cfg['challenge_module']+'\nimport FindingStatements\nset_option maxRecDepth 10000\nset_option maxHeartbeats 2000000\nset_option pp.maxDepth 1000\nset_option pp.maxSteps 1000000\n'
            driver+=''.join('#leanglish_statement '+json.dumps(n)+'\n' for n in targets)
            path=out/'Statements.lean';path.write_text(driver)
            executed=run_bounded(['lake','env','lean',str(path.resolve())],project,timeout=120,max_output=8_000_000)
            (out/'execution.json').write_text(json.dumps(asdict(executed),ensure_ascii=False))
            record['driver_sha256']=sha256(driver.encode()).hexdigest()
            record['status']='extraction-'+executed.status
            for line in executed.stdout.splitlines():
                if MARKER not in line:continue
                raw=line.split(MARKER,1)[1]
                try:r=json.loads(raw)
                except ValueError:continue
                n=r.get('name')
                if n not in targets or n in rows:raise ValueError('Unexpected or duplicate statement')
                if r.get('origin')!='comparison-specification' or r.get('solution_proof_checked') is not False:
                    raise ValueError('Unacceptable statement provenance')
                if r.get('lean_version')!='4.34.1':raise ValueError('Statement toolchain mismatch')
                rows[n]=r
            # Partial output from an unsuccessful process is retained but not
            # promoted to a successful elaboration observation.
            if executed.status!='passed':rows={}
        if sha256(challenge.read_bytes()).hexdigest()!=source_digest:
            raise ValueError('Comparison source changed during execution')
        for n in targets:
            row={'name':n,'status':'elaborated-specification' if n in rows else 'unavailable',
                 'solution_proof_checked':False,'statement':rows.get(n)}
            record['targets'].append(row)
        if len(rows)==len(targets):record['status']='complete-statements-only'
        (out/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
        return record
    records=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures={pool.submit(one,item):item for item in configs}
        for future in as_completed(futures):
            key,cfg,targets=futures[future]
            try:record=future.result()
            except Exception as exc:
                record={'configuration':key,'solution_module':cfg['solution_module'],
                        'upstream_commit':PIN,'status':'failed','error':str(exc),
                        'targets':[{'name':n,'status':'unavailable','statement':None,'solution_proof_checked':False} for n in targets]}
            records.append(record)
            print(key,record['status'],flush=True)
            report={**identity,'configurations':sorted(records,key=lambda r:r['configuration'])}
            (output/'statements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    report['elaborated_occurrences']=sum(t['status']=='elaborated-specification' for r in records for t in r['targets'])
    report['all_configurations_accounted']=len(records)==len(configs)
    (output/'statements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--shard',type=int,required=True)
    p.add_argument('--shards',type=int,default=4)
    p.add_argument('--trust-project',action='store_true')
    a=p.parse_args()
    r=run(a.project.resolve(),a.output.resolve(),a.shard,a.shards,trust_project=a.trust_project)
    print(json.dumps({k:v for k,v in r.items() if k!='configurations'},indent=2))
    return 0 if r['elaborated_occurrences']==r['expected_occurrences'] else 2

if __name__=='__main__':raise SystemExit(main())
