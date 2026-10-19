"""Execute one preselected original-project recovery worker in bounded phases."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader import build_resume
from proofreader.original_project import read,write,digest,run_worker,validate_plan
from proofreader.proof_campaign import check_environment,validate_campaign,run_module


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=['initialize','round','pack','verify'])
    p.add_argument('--kind',choices=['module','library'],required=True)
    p.add_argument('--id',required=True)
    for key in ('seed','project','state','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--round',type=int,default=1)
    p.add_argument('--seconds',type=int,default=1800)
    p.add_argument('--tools',type=Path)
    p.add_argument('--trust-project',action='store_true')
    a=p.parse_args()
    if not a.trust_project:p.error('Original project execution requires --trust-project')
    plan,env,recovery=[read(a.seed/(n+'.json')) for n in ('plan','environment','recovery')]
    validate_plan(plan);check_environment(plan,env)
    if (recovery.get('recovery_plan_sha256')!=digest({k:v for k,v in recovery.items() if k!='recovery_plan_sha256'}) or
        recovery.get('original_plan_sha256')!=plan['plan_sha256'] or
        recovery.get('environment_sha256')!=env['environment_sha256']):
        raise ValueError('Recovery worker plan identity mismatch')
    validate_campaign(plan,env,recovery['campaign'])
    jobs=recovery['module_jobs'] if a.kind=='module' else recovery['library_jobs']
    matches=[j for j in jobs if j['id']==a.id]
    if len(matches)!=1:raise ValueError('Worker is not in the preselected recovery inventory')
    job=matches[0];target=job['module'] if a.kind=='module' else job['library']
    a.project=a.project.resolve();a.state=a.state.resolve();a.output=a.output.resolve()
    if a.phase=='initialize':
        state=build_resume.initialize(a.project,plan,env,a.state,target,trust_project=True)
        result={k:v for k,v in state.items() if k!='baseline'}
        result['baseline_files']=len(state['baseline'])
        result['baseline_bytes']=sum(v['size'] for v in state['baseline'].values())
        write(a.output/'identity.json',{'recovery_plan_sha256':recovery['recovery_plan_sha256'],
            'worker_id':a.id,'kind':a.kind,'target':target,'native_lean_verified':False})
    elif a.phase=='round':
        if not 1<=a.round<=12:raise ValueError('Invalid bounded build round')
        state=build_resume.validate_state(read(a.state/'state.json'),plan,env)
        if state['target']!=target:raise ValueError('Worker target changed')
        if state['build_passed']:
            result={'status':'already-built','final_verification_still_required':True}
        else:
            result=build_resume.run_round(a.project,plan,env,a.state,a.output/f'round-{a.round}',
                                          trust_project=True,seconds=a.seconds)
            result={k:v for k,v in result.items() if k not in ('environment_before','environment_after')}
        github_output=os.environ.get('GITHUB_OUTPUT')
        if github_output:
            with open(github_output,'a') as stream:stream.write('status='+result['status']+'\n')
    elif a.phase=='pack':
        directory=a.output/f'checkpoint-{a.round}'
        result=build_resume.pack(a.project,plan,env,a.state,directory/'build.tar.gz')
        write(directory/'identity.json',{'recovery_plan_sha256':recovery['recovery_plan_sha256'],
             'worker_id':a.id,'target':target,'checkpoint':result,'proof_verified':False})
    else:
        state=build_resume.validate_state(read(a.state/'state.json'),plan,env)
        if state['target']!=target:raise ValueError('Final verification target changed')
        result={'worker_id':a.id,'kind':a.kind,'target':target,
                'recovery_plan_sha256':recovery['recovery_plan_sha256'],
                'status':'prebuild-incomplete','proofs':None,'comparisons':None,'library':None}
        if state['build_passed']:
            if a.kind=='library':
                r=run_worker(a.project,plan,a.output/'library',kind='library',shard=0,shards=1,
                             only=[a.id],trust_project=True,timeout=1800,wall_seconds=2100)
                result['library']=r['status']
            else:
                if job['proof_module_id'] is not None:
                    r=run_module(a.project,plan,env,recovery['campaign'],job['proof_module_id'],
                                 a.output/'proofs',trust_project=True,build_timeout=3600,
                                 extract_timeout=900,max_heartbeats=2_000_000,wall_seconds=7200)
                    result['proofs']={'status':r['status'],'validated_readings':r['validated_readings']}
                if job['comparators']:
                    if a.tools is None:raise ValueError('Missing independently controlled Comparator toolchain')
                    r=run_worker(a.project,plan,a.output/'comparisons',kind='comparator',shard=0,shards=1,
                                 only=job['comparators'],trust_project=True,timeout=2400,wall_seconds=7200,
                                 comparator=a.tools/'bin/comparator',tool_receipt=a.tools/'controls/toolchain.json')
                    result['comparisons']=r['status']
            result['status']='verified-attempts-retained'
        write(a.output/'final-status.json',result)
    print('COMPLETION_WORKER',json.dumps(result,sort_keys=True),flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
