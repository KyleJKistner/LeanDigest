"""Reconcile separately validated attempts against the same original obligations.

The strict single-run checker is unchanged. A later successful retry can satisfy
an obligation, but all preceding attempts remain visible. This module never
converts a checkpoint, a missing artifact, or a job color into proof acceptance.
"""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from .original_project import read, digest, file_hash, reconcile, validate_plan
from .proof_campaign import check_environment


def reconcile_attempts(plan: dict, roots: list[Path], *, environment: dict | None = None) -> dict:
    validate_plan(plan)
    if environment is not None:
        check_environment(plan, environment)
    histories = {task['id']: [] for task in plan['tasks']}
    seen = set()
    for root in roots:
        root = Path(root)
        report = read(root/'worker.json')
        report_hash = file_hash(root/'worker.json')
        if report_hash in seen:
            raise ValueError('Duplicate retained worker attempt')
        seen.add(report_hash)
        # Import here to avoid a module cycle when status pages use this ledger.
        from .original_status import task_rows
        _, validated_rows = task_rows(plan, [root])
        rows = {row['id']: row for row in validated_rows if row['status']!='not-retained'}
        if any(row['status']=='passed' for row in report['targets']):
            check_environment(plan, report['environment_before'])
            if environment is not None and report['environment_before'] != environment:
                raise ValueError('Successful retry belongs to a different original environment')
        for row in report['targets']:
            detail = rows[row['id']]
            histories[row['id']].append({
                'status': row['status'], 'diagnosis': detail['diagnosis'],
                'worker_report_sha256': report_hash, 'log_sha256': detail['log_sha256'],
                'exit_code': detail['exit_code'],
                'environment_sha256': (report.get('environment_before') or {}).get('environment_sha256'),
            })
    result_rows = []
    for task in plan['tasks']:
        attempts = sorted(histories[task['id']], key=lambda r:r['worker_report_sha256'])
        passed = [r for r in attempts if r['status']=='passed']
        result_rows.append({'id':task['id'], 'kind':task['kind'],
            'status':'passed' if passed else 'not-retained' if not attempts else 'outstanding',
            'attempts':attempts,
            'selected_success_sha256':passed[0]['worker_report_sha256'] if passed else None})
    missing = [row['id'] for row in result_rows if not row['attempts']]
    outstanding = [row['id'] for row in result_rows if row['status']!='passed']
    summary = {'schema':'leanglish.original-attempt-summary/v1',
        'plan_sha256':plan['plan_sha256'], 'expected_tasks':len(result_rows),
        'recorded_tasks':len(result_rows)-len(missing), 'retained_workers':len(seen),
        'retained_attempts':sum(len(r['attempts']) for r in result_rows),
        'missing_tasks':missing, 'outstanding_tasks':outstanding,
        'statuses':dict(Counter(r['status'] for r in result_rows)),
        'all_comparators_passed':False, 'full_project_build':False,
        'english_fidelity_certified':False, 'observations_authenticated':False,
        'selection_rule':'any independently validated success; every earlier failure retained',
        'tasks':result_rows}
    for kind,field in [('library','full_project_build'),('comparator','all_comparators_passed')]:
        selected=[r for r in result_rows if r['kind']==kind]
        summary[kind+'_expected']=len(selected)
        summary[kind+'_passed']=sum(r['status']=='passed' for r in selected)
        summary[field]=bool(selected) and all(r['status']=='passed' for r in selected)
    summary['complete']=summary['full_project_build'] and summary['all_comparators_passed']
    summary['summary_sha256']=digest(summary)
    return summary
