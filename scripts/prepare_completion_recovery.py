"""Prepare only outstanding original tasks from a frozen, checked collection."""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.original_project import read,write,digest,file_hash,validate_plan
from proofreader.original_status import build_status,check_archive
from proofreader.original_attempts import reconcile_attempts
from proofreader.proof_campaign import make_campaign,universe,check_environment


def checked_retry_roots(evidence: Path) -> list[Path]:
    root=evidence/'retries';collection=read(root/'collection.json')
    if (collection.get('schema')!='leanglish.original-retry-collection/v1' or
        collection.get('repository')!='KyleJKistner/LeanDigest'):
        raise ValueError('Retry collection identity mismatch')
    run=collection['run'];artifacts=collection['artifacts'];outcomes=collection['outcomes']
    if len(artifacts)!=len(outcomes) or len({x['id'] for x in artifacts})!=len(artifacts):
        raise ValueError('Retry archive denominator mismatch')
    by_id={x['id']:x for x in artifacts};roots=[]
    for outcome in outcomes:
        item=by_id.get(outcome['id'])
        if (item is None or outcome.get('status')!='retained' or outcome.get('name')!=item['name'] or
            outcome.get('run_id')!=run['id'] or outcome.get('source_commit')!=run['head_sha'] or
            item.get('workflow_run',{}).get('id')!=run['id'] or
            item.get('workflow_run',{}).get('head_sha')!=run['head_sha'] or
            item.get('digest')!='sha256:'+outcome['sha256']):
            raise ValueError('Retry artifact is not bound to the retained execution')
        from proofreader.original_project import child
        directory=child(root,outcome['name']);archive=child(root,outcome['name']+'.zip')
        check_archive(archive,directory,outcome['sha256'])
        roots.append(directory)
    return roots


def recovery_plan(plan: dict,environment: dict,status: dict,attempts: dict) -> dict:
    validate_plan(plan);check_environment(plan,environment)
    if (status.get('status_sha256')!=digest({k:v for k,v in status.items() if k!='status_sha256'}) or
        status.get('original_plan_sha256')!=plan['plan_sha256'] or
        status.get('original_environment_sha256')!=environment['environment_sha256'] or
        attempts.get('summary_sha256')!=digest({k:v for k,v in attempts.items() if k!='summary_sha256'}) or
        attempts.get('plan_sha256')!=plan['plan_sha256']):
        raise ValueError('Recovery source ledger binding mismatch')
    theorems=status['theorems'];keys=[(r['module'],r['name']) for r in theorems]
    if len(keys)!=len(set(keys)) or set(keys)!=universe(plan):
        raise ValueError('Recovery theorem denominator mismatch')
    if any(type(r.get('reading_available')) is not bool for r in theorems):
        raise ValueError('Unknown reading availability must not become a success')
    baseline=[{'module':r['module'],'name':r['name'],'snapshot_sha256':r['snapshot_sha256']}
              for r in theorems if r['reading_available']]
    campaign=make_campaign(plan,environment,baseline)
    task_by_id={t['id']:t for t in plan['tasks']}
    rows=attempts['tasks']
    if len(rows)!=len(task_by_id) or {r['id'] for r in rows}!=set(task_by_id):
        raise ValueError('Recovery comparison/build denominator mismatch')
    pending=[task_by_id[r['id']] for r in rows if r['status']!='passed']
    proofs={t['module']:t for t in campaign['module_tasks']}
    comparisons={}
    for task in pending:
        if task['kind']=='comparator':comparisons.setdefault(task['solution_module'],[]).append(task['id'])
    jobs=[]
    for module in sorted(set(proofs)|set(comparisons),key=lambda m:(m not in proofs,m)):
        proof=proofs.get(module)
        jobs.append({'id':sha256(module.encode()).hexdigest()[:24], 'module':module,
                     'proof_module_id':proof['id'] if proof else None,
                     'theorem_targets':proof['targets'] if proof else [],
                     'comparators':sorted(comparisons.get(module,[]))})
    result={'schema':'leanglish.original-recovery-plan/v1','original_plan_sha256':plan['plan_sha256'],
            'environment_sha256':environment['environment_sha256'],
            'prior_status_sha256':status['status_sha256'],'attempt_summary_sha256':attempts['summary_sha256'],
            'campaign':campaign,'module_jobs':jobs,
            'library_jobs':[t for t in pending if t['kind']=='library'],
            'expected_theorem_targets':len(keys),'prior_readings':len(baseline),
            'remaining_theorem_targets':campaign['selected_theorems'],
            'expected_comparators':attempts['comparator_expected'],
            'prior_comparators_passed':attempts['comparator_passed'],
            'remaining_comparators':sum(len(j['comparators']) for j in jobs),
            'prior_libraries_passed':attempts['library_passed'],
            'all_original_work_complete':attempts['complete'] and not campaign['selected_theorems'],
            'compiled_cache_is_proof_evidence':False,'english_formally_verified':False}
    if result['remaining_comparators']+result['prior_comparators_passed']!=result['expected_comparators']:
        raise ValueError('Recovery comparison complement is inconsistent')
    result['recovery_plan_sha256']=digest(result)
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence','project','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a fresh recovery plan directory')
    args.output.mkdir(parents=True)
    evidence=args.evidence;seed=evidence/'original-proofs/original-proof-campaign-plan'
    plan=read(seed/'plan.json');environment=read(seed/'environment.json')
    status,_=build_status(args.project,evidence,recovery_output=args.output/'recovered')
    roots=[p.parent for p in sorted((evidence/'original-build').rglob('worker.json'))]
    attempts=reconcile_attempts(plan,roots+checked_retry_roots(evidence),environment=environment)
    result=recovery_plan(plan,environment,status,attempts)
    for name,value in [('plan',plan),('environment',environment),('prior-status',status),
                       ('attempts',attempts),('recovery',result),('campaign',result['campaign'])]:
        write(args.output/(name+'.json'),value)
    summary={k:result[k] for k in ('expected_theorem_targets','prior_readings','remaining_theorem_targets',
        'expected_comparators','prior_comparators_passed','remaining_comparators','prior_libraries_passed')}
    summary.update(module_workers=len(result['module_jobs']),library_workers=len(result['library_jobs']),
        recovery_plan_sha256=result['recovery_plan_sha256'])
    write(args.output/'summary.json',summary)
    print('RECOVERY_PLAN',json.dumps(summary,sort_keys=True),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
