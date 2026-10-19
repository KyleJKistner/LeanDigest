"""Collect source-bound recovery reports at a fixed cutoff without executing Lean."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.collect_original_evidence import api, stable_artifacts, retain
from proofreader.original_project import read, write, digest
from proofreader.completion_results import COLLECTION, check_collection, ORIGINAL_WORKFLOW, RESUME_WORKFLOW

REPOSITORY='KyleJKistner/LeanDigest'


def collect(run_id: int, expected_head: str, recovery: dict, output: Path,
            *, allow_download: bool=False, workflow_path: str=ORIGINAL_WORKFLOW) -> dict:
    if not allow_download:
        raise PermissionError('Recovery acquisition requires --allow-download')
    if (type(run_id) is not int or run_id <= 0 or not isinstance(expected_head,str) or
        not re.fullmatch(r'[a-f0-9]{40}',expected_head) or
        workflow_path not in {ORIGINAL_WORKFLOW,RESUME_WORKFLOW}):
        raise ValueError('Explicit supported workflow execution identity is required')
    if recovery.get('recovery_plan_sha256') != digest({k:v for k,v in recovery.items() if k!='recovery_plan_sha256'}):
        raise ValueError('Recovery plan digest mismatch')
    if output.exists():
        raise ValueError('Never overwrite a frozen recovery collection')
    output.mkdir(parents=True)
    cutoff=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    result={'schema':COLLECTION,'repository':REPOSITORY,'run_id':run_id,
            'source_commit':expected_head,'workflow_path':workflow_path,
            'recovery_plan_sha256':recovery['recovery_plan_sha256'],
            'cutoff':cutoff,'outcomes':[],'errors':[],
            'native_execution_performed':False,'all_expected_work_complete':False,
            'observations_authenticated':False}
    try:
        run=api(REPOSITORY,f'actions/runs/{run_id}')
        if run.get('head_sha')!=expected_head or run.get('path')!=workflow_path:
            raise ValueError('Wrong recovery workflow or application revision')
        write(output/'run.json',run)
        prefixes=('completion-recovery-plan','completion-result-')
        artifacts=stable_artifacts(REPOSITORY,run_id,prefixes,cutoff)
        if len(artifacts)>1+len(recovery['module_jobs'])+len(recovery['library_jobs']):
            raise ValueError('Too many recovery outputs for the declared work')
        write(output/'frozen-artifacts.json',artifacts)
        jobs=api(REPOSITORY,f'actions/runs/{run_id}/jobs?per_page=100',paged=True)
        write(output/'jobs-pages.json',jobs)
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures=[(artifact,pool.submit(retain,REPOSITORY,run,artifact,output)) for artifact in artifacts]
            for artifact,future in futures:
                try:
                    result['outcomes'].append(future.result())
                except Exception as exc:
                    result['errors'].append({'artifact_id':artifact['id'],'name':artifact['name'],
                                             'error':str(exc)})
    except Exception as exc:
        result['errors'].append({'error':str(exc)})
    finally:
        write(output/'collection.json',result)
    if result['errors']:
        raise ValueError('Recovery collection failed; no reports are accepted: '+str(result['errors']))
    validated=check_collection(output,recovery,expected_run=run_id,expected_head=expected_head,
                               expected_workflow=workflow_path)
    summary={'run_id':run_id,'workflow_path':workflow_path,'cutoff':cutoff,
             'retained_artifacts':len(result['outcomes']),
             'expected_workers':len(recovery['module_jobs'])+len(recovery['library_jobs']),
             'retained_workers':len(validated['workers']),
             'missing_workers':len(validated['missing_workers']),
             'native_proof_reports':len(validated['proof_roots']),
             'original_verification_reports':len(validated['build_roots']),
             'proof_acceptance_inferred_from_job_status':False}
    write(output/'summary.json',summary)
    print('RECOVERY_COLLECTION',summary,flush=True)
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id',type=int,required=True)
    parser.add_argument('--expected-head',required=True)
    parser.add_argument('--workflow-path',choices=[ORIGINAL_WORKFLOW,RESUME_WORKFLOW],default=ORIGINAL_WORKFLOW)
    parser.add_argument('--recovery',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--allow-download',action='store_true')
    a=parser.parse_args()
    collect(a.run_id,a.expected_head,read(a.recovery),a.output,
            allow_download=a.allow_download,workflow_path=a.workflow_path)
    return 0

if __name__=='__main__':raise SystemExit(main())
