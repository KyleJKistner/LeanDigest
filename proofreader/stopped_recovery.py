"""Bound a small fresh retry to stopped native jobs, not to guessed coverage.

Selection does not grant mathematical acceptance. Existing proof-worker outcomes
are excluded so the strict campaign reconciler never has to discard duplicates.
"""
from __future__ import annotations
import re
from .original_project import digest, validate_plan
from .proof_campaign import validate_campaign, check_environment


def select(plan: dict, environment: dict, recovery: dict, jobs: list[dict],
           requested: list[str], proof_reports: set[str], *, run_id: int,
           source_commit: str) -> dict:
    validate_plan(plan); check_environment(plan, environment)
    if (recovery.get('recovery_plan_sha256') != digest({k:v for k,v in recovery.items() if k!='recovery_plan_sha256'}) or
        recovery.get('original_plan_sha256') != plan['plan_sha256'] or
        recovery.get('environment_sha256') != environment['environment_sha256']):
        raise ValueError('Retry selection has a different original project')
    validate_campaign(plan, environment, recovery['campaign'])
    if (type(run_id) is not int or run_id <= 0 or not isinstance(source_commit, str) or
        re.fullmatch(r'[a-f0-9]{40}', source_commit) is None or
        not isinstance(requested, list) or not 1 <= len(requested) <= 12 or
        len(requested) != len(set(requested))):
        raise ValueError('A bounded explicit retry selection is required')
    tasks = {task['id']: task for task in recovery['module_jobs']}
    if not set(requested) <= set(tasks) or not proof_reports <= set(tasks):
        raise ValueError('Retry selection is outside the original recovery inventory')
    selected, excluded = [], []
    for ident in requested:
        matches = [job for job in jobs if job.get('name') == 'modules ('+ident+') / recover']
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous original worker identity')
        job = matches[0]
        if (job.get('run_id') != run_id or job.get('status') != 'completed' or
            job.get('conclusion') not in {'failure', 'cancelled', 'timed_out'}):
            raise ValueError('Do not overlap an active or successfully completed worker')
        task = tasks[ident]
        if ident in proof_reports:
            excluded.append({'id': ident, 'reason': 'retained-proof-worker-must-be-reconciled'})
            continue
        selected.append({'id': ident, 'module': task['module'],
                         'previous_job_id': job['id'], 'previous_conclusion': job['conclusion'],
                         'theorem_targets': task['theorem_targets'],
                         'comparators': task['comparators']})
    result = {'schema': 'leanglish.stopped-worker-selection/v1',
              'recovery_plan_sha256': recovery['recovery_plan_sha256'],
              'previous_run_id': run_id, 'previous_source_commit': source_commit,
              'requested_modules': requested, 'selected': selected, 'excluded': excluded,
              'proof_acceptance_established': False,
              'source_or_dependency_changes_permitted': False,
              'method': 'fresh original-environment execution; no reused theorem acceptance'}
    result['selection_sha256'] = digest(result)
    return result
