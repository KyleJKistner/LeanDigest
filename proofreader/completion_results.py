"""Join original-project recovery results to the independently validated baseline.

Acquisition metadata, archived bytes, source audits, mathematical checks and
reading availability are separate gates. A checkpoint or a green workflow is
never accepted as a substitute for the original verifier's retained result.
"""
from __future__ import annotations
from collections import Counter
from copy import deepcopy
from pathlib import Path
import re
from .original_project import child, digest, file_hash, read
from .original_status import SCHEMA as STATUS_SCHEMA, check_archive

COLLECTION = 'leanglish.completion-collection/v1'
HEAD = re.compile(r'[a-f0-9]{40}')
HASH = re.compile(r'[a-f0-9]{64}')


def check_collection(root: Path, recovery: dict, *, expected_run: int,
                     expected_head: str) -> dict:
    """Return only explicitly inventoried workers from one frozen acquisition."""
    if type(expected_run) is not int or expected_run <= 0 or not HEAD.fullmatch(expected_head):
        raise ValueError('Explicit recovery execution identity is required')
    record = read(root/'collection.json')
    run = read(root/'run.json')
    artifacts = read(root/'frozen-artifacts.json')
    if (record.get('schema') != COLLECTION or record.get('repository') != 'KyleJKistner/LeanDigest' or
        record.get('errors') != [] or record.get('run_id') != expected_run or
        record.get('source_commit') != expected_head or run.get('id') != expected_run or
        run.get('head_sha') != expected_head or run.get('path') != '.github/workflows/completion-recovery.yml' or
        record.get('recovery_plan_sha256') != recovery.get('recovery_plan_sha256')):
        raise ValueError('Recovery collection execution/plan identity mismatch')
    outcomes = record.get('outcomes')
    if (not isinstance(artifacts, list) or not isinstance(outcomes, list) or
        len(artifacts) != len(outcomes) or len({a['id'] for a in artifacts}) != len(artifacts) or
        len({a['name'] for a in artifacts}) != len(artifacts) or
        len({a['id'] for a in outcomes}) != len(outcomes)):
        raise ValueError('Recovery artifact denominator mismatch')
    jobs = {}
    for kind, group in [('module', recovery['module_jobs']), ('library', recovery['library_jobs'])]:
        for job in group:
            ident = job['id'] if kind == 'module' else job['library']
            target = job['module'] if kind == 'module' else job['library']
            name = 'completion-result-' + ident
            if name in jobs:
                raise ValueError('Duplicate planned recovery worker')
            jobs[name] = (kind, ident, target, job)
    by_id = {a['id']: a for a in artifacts}
    proof_roots, build_roots, workers, seed_seen = [], [], [], False
    for outcome in outcomes:
        artifact = by_id.get(outcome['id'])
        if (artifact is None or outcome.get('status') != 'retained' or
            outcome.get('name') != artifact['name'] or outcome.get('run_id') != expected_run or
            outcome.get('source_commit') != expected_head or
            artifact.get('workflow_run', {}).get('id') != expected_run or
            artifact.get('workflow_run', {}).get('head_sha') != expected_head or
            not isinstance(outcome.get('sha256'), str) or not HASH.fullmatch(outcome['sha256']) or
            artifact.get('digest') != 'sha256:' + outcome['sha256'] or
            artifact.get('created_at', '') > record['cutoff']):
            raise ValueError('Recovery artifact is not bound to the selected execution')
        name = outcome['name']
        if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in {'.', '..'}:
            raise ValueError('Unsafe recovery artifact name')
        directory = child(root, name)
        check_archive(child(root, name+'.zip'), directory, outcome['sha256'])
        if name == 'completion-recovery-plan':
            if seed_seen or read(directory/'recovery.json') != recovery:
                raise ValueError('Recovery seed changed')
            seed_seen = True
            continue
        if name not in jobs:
            raise ValueError('Unplanned recovery output cannot enter the catalog')
        kind, ident, target, job = jobs[name]
        identity = read(directory/'identity.json')
        if identity != {'recovery_plan_sha256': recovery['recovery_plan_sha256'],
                        'worker_id': ident, 'kind': kind, 'target': target, 'native_lean_verified': False}:
            raise ValueError('Recovery worker assignment changed')
        proof = directory/'proofs/original-proof-worker.json'
        comparisons = directory/'comparisons/worker.json'
        library = directory/'library/worker.json'
        if proof.exists():
            if kind != 'module' or job['proof_module_id'] is None:
                raise ValueError('Unplanned theorem extraction')
            wrapper = read(proof)
            if (wrapper.get('module_id') != job['proof_module_id'] or
                wrapper.get('module') != target or wrapper.get('expected_targets') != job['theorem_targets']):
                raise ValueError('Recovery theorem targets changed')
            proof_roots.append(proof.parent)
        if comparisons.exists():
            if kind != 'module' or not job['comparators']:
                raise ValueError('Unplanned comparison results')
            wrapper = read(comparisons)
            if (wrapper.get('kind') != 'comparator' or
                [r['id'] for r in wrapper['targets']] != job['comparators']):
                raise ValueError('Recovery comparison targets changed')
            build_roots.append(comparisons.parent)
        if library.exists():
            if kind != 'library':
                raise ValueError('Unplanned library result')
            wrapper = read(library)
            if wrapper.get('kind') != 'library' or [r['id'] for r in wrapper['targets']] != [job['id']]:
                raise ValueError('Recovery library target changed')
            build_roots.append(library.parent)
        workers.append({'id': ident, 'kind': kind, 'target': target,
                        'artifact_sha256': outcome['sha256'],
                        'proof_report_retained': proof.exists(),
                        'comparison_report_retained': comparisons.exists(),
                        'library_report_retained': library.exists()})
    if not seed_seen:
        raise ValueError('The recovery plan artifact is missing')
    return {'proof_roots': proof_roots, 'build_roots': build_roots,
            'workers': workers, 'missing_workers': sorted(set(jobs)-{a['name'] for a in artifacts}),
            'collection': {'run_id': expected_run, 'source_commit': expected_head,
                           'cutoff': record['cutoff'], 'collection_sha256': file_hash(root/'collection.json'),
                           'artifacts': len(artifacts)}}


def join_status(base: dict, attempts: dict, proof_summary: dict,
                selected: dict, collection: dict) -> dict:
    """Internal projection after independent native-report and proof-loader checks.

    `selected` comes from catalog_inputs.load_proofs, not from declared counts.
    This projection does not authenticate any observation or certify English.
    """
    if (base.get('schema') != STATUS_SCHEMA or
        base.get('status_sha256') != digest({k:v for k,v in base.items() if k!='status_sha256'}) or
        attempts.get('summary_sha256') != digest({k:v for k,v in attempts.items() if k!='summary_sha256'}) or
        attempts.get('plan_sha256') != base['original_plan_sha256']):
        raise ValueError('Unbound original-status input')
    theorems = {(r['module'], r['name']): r for r in base['theorems']}
    if len(theorems) != len(base['theorems']) or not set(selected) <= set(theorems):
        raise ValueError('Foreign or duplicate theorem in completion results')
    expected = base['proof_summary']['expected_theorem_targets']
    prior = {k:r for k,r in theorems.items() if r['reading_available']}
    if (len(theorems) != expected or proof_summary.get('expected_theorem_targets') != expected or
        proof_summary.get('baseline_readings') != len(prior) or
        proof_summary.get('total_readings') != len(selected) or not set(prior) <= set(selected) or
        proof_summary.get('original_environment_new_readings') != len(selected)-len(prior)):
        raise ValueError('Completion reading counts do not reconcile')
    for key, row in prior.items():
        if selected[key]['receipt']['snapshot_sha256'] != row['snapshot_sha256']:
            raise ValueError('A baseline reading was replaced or relabeled')
    result = deepcopy(base)
    task_ids = {r['id'] for r in result['tasks']}
    retry_rows = {r['id']:r for r in attempts['tasks']}
    if len(task_ids) != len(result['tasks']) or set(retry_rows) != task_ids or len(retry_rows) != len(attempts['tasks']):
        raise ValueError('Completion build/configuration denominator changed')
    for row in result['tasks']:
        history = retry_rows[row['id']]
        if history['kind'] != row['kind']:
            raise ValueError('Completion task kind changed')
        row['attempts'] = history['attempts']
        row['prior_status'] = row['status']
        if history['status'] == 'passed':
            successes = [a for a in history['attempts'] if a['status']=='passed' and
                         a['worker_report_sha256']==history['selected_success_sha256']]
            if len(successes) != 1:
                raise ValueError('Successful attempt selection is missing or ambiguous')
            chosen = successes[0]
            row.update(status='passed', diagnosis='passed',
                       worker_report_sha256=chosen['worker_report_sha256'],
                       log_sha256=chosen['log_sha256'], exit_code=chosen['exit_code'])
    for kind in ('library', 'comparator'):
        relevant = [r for r in result['tasks'] if r['kind']==kind]
        if (len(relevant) != attempts[kind+'_expected'] or
            sum(r['status']=='passed' for r in relevant) != attempts[kind+'_passed']):
            raise ValueError('Completion task count conflicts with its attempt ledger')
    for row in result['theorems']:
        key = row['module'], row['name']
        if key in selected and not row['reading_available']:
            value = selected[key]
            row.update(reading_available=True, reading_id=value['row']['id'],
                       snapshot_sha256=value['receipt']['snapshot_sha256'],
                       reading_environment='full-original-dependency-audit')
        matches = [t for t in result['tasks'] if t['kind']=='comparator' and
                   t['solution_module']==row['module'] and row['name'] in t['theorem_names']]
        row['configurations_passed'] = [t['configuration'] for t in matches if t['status']=='passed']
        row['configurations_not_passed'] = [t['configuration'] for t in matches if t['status']!='passed']
    p = result['proof_summary']
    new_count = len(selected)-len(prior)
    p.update(schema='leanglish.original-proof-summary/v3', total_readings=len(selected),
             original_environment_new_readings=p['original_environment_new_readings']+new_count,
             theorems_without_reading=expected-len(selected), all_theorems_have_readings=len(selected)==expected,
             completion_campaign=proof_summary)
    # Preserve original outcomes rather than rewriting the preceding campaign.
    p['prior_outcomes_retained'] = True
    result['build_summary'] = attempts
    result['completion'] = {'prior_status_sha256': base['status_sha256'],
                            'new_readings': new_count, 'acquisition': collection}
    result['collection']['completion_cutoff'] = collection['cutoff']
    result['collection']['cutoff'] = max(result['collection']['cutoff'], collection['cutoff'])
    result['diagnoses'] = dict(sorted(Counter(r['diagnosis'] for r in result['tasks']).items()))
    result['baseline_environment_upgraded'] = False
    result['english_formally_verified'] = False
    result['original_obligations_and_readings_complete'] = attempts['complete'] and len(selected)==expected
    result['status_sha256'] = digest({k:v for k,v in result.items() if k!='status_sha256'})
    return result
