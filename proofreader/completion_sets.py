"""Gather independently validated workflow snapshots without inventing successes."""
from __future__ import annotations
from pathlib import Path
from .completion_results import check_collection, ORIGINAL_WORKFLOW, RESUME_WORKFLOW


def gather(recovery: dict, requests: list[dict]) -> dict:
    """Use one frozen acquisition per run; mathematical validation follows separately.

    Missing worker results are intersected across attempts. Partial worker output
    remains partial: this function never turns retained files into accepted proofs.
    Duplicate theorem-worker outcomes are subsequently rejected by the existing
    native campaign reconciler rather than silently selecting or rewriting them.
    """
    if not isinstance(requests,list) or not 1<=len(requests)<=8:
        raise ValueError('One to eight explicit recovery acquisitions are required')
    keys={'root','run_id','source_commit','workflow_path'}
    seen_runs=set();seen_roots=set();validated=[]
    for request in requests:
        if (not isinstance(request,dict) or set(request)!=keys or
            type(request['run_id']) is not int or request['run_id']<=0 or
            not isinstance(request['root'],str) or
            request['workflow_path'] not in {ORIGINAL_WORKFLOW,RESUME_WORKFLOW}):
            raise ValueError('Invalid explicit recovery acquisition')
        root=Path(request['root']).resolve()
        if request['run_id'] in seen_runs or root in seen_roots:
            raise ValueError('Do not count two snapshots of the same execution')
        seen_runs.add(request['run_id']);seen_roots.add(root)
        validated.append(check_collection(root,recovery,
            expected_run=request['run_id'],expected_head=request['source_commit'],
            expected_workflow=request['workflow_path']))
    missing=set(validated[0]['missing_workers'])
    workers=[];proof_roots=[];build_roots=[]
    for value in validated:
        missing.intersection_update(value['missing_workers'])
        proof_roots.extend(value['proof_roots']);build_roots.extend(value['build_roots'])
        for worker in value['workers']:
            workers.append(dict(worker,run_id=value['collection']['run_id'],
                                source_commit=value['collection']['source_commit'],
                                workflow_path=value['collection']['workflow_path']))
    executions=sorted((v['collection'] for v in validated),key=lambda e:e['run_id'])
    return {'proof_roots':proof_roots,'build_roots':build_roots,
            'workers':sorted(workers,key=lambda w:(w['id'],w['run_id'])),
            'missing_workers':sorted(missing),
            'collection':{'cutoff':max(e['cutoff'] for e in executions),
                          'executions':executions,
                          'proof_acceptance_from_collection':False}}
