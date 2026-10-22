"""Original-environment completion of the explicit documented proof inventory.

A campaign preserves the validated old readings but never upgrades their
execution environment. New workers build one unchanged solution module each;
all 536 theorem targets remain in the global denominator. Missing worker output,
failed compilation, and explanation gaps are different outcomes.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path
import hashlib
import json
import subprocess

from .catalog_inputs import config_inventory, load_proofs
from .original_project import (PIN, audit_environment, validate_plan, digest,
                               file_hash, read, write, child)

SCHEMA = 'leanglish.original-proof-campaign/v1'
WORKER = 'leanglish.original-proof-worker/v1'
PRIORITY = {'OAI.MathematicalPhysics.NavierStokes.BalancedTransport.MainResult': 0,
            'OAI.Analysis.SymmetricDomains.Main': 1}


def key(row: dict) -> tuple[str, str]:
    return row['module'], row['name']


def universe(plan: dict) -> set[tuple[str, str]]:
    validate_plan(plan)
    return {(t['solution_module'], n) for t in plan['tasks']
            if t['kind'] == 'comparator' for n in t['theorem_names']}


def check_environment(plan: dict, env: dict) -> None:
    if (not isinstance(env, dict) or env.get('schema') != 'leanglish.original-environment/v1' or
        env.get('plan_sha256') != plan['plan_sha256'] or
        env.get('source_check') != {'checked_source_files': len(plan['source_files'])-1,
                                    'manifest_resolution_permitted': True}):
        raise ValueError('Missing full original-source audit')
    deps = env.get('dependencies', {})
    if not isinstance(deps, dict) or set(deps) != set(plan['dependencies']):
        raise ValueError('Incomplete original dependency audit')
    for name, expected in plan['dependencies'].items():
        got = deps[name]
        patch = plan['source_files'].get('lean/patches/'+name+'-lean4341.patch')
        if (any(got.get(k) != v for k, v in expected.items()) or got.get('patch_sha256') != patch or
            not isinstance(got.get('tree'), str) or len(got['tree']) != 40):
            raise ValueError('Wrong original dependency/patch identity')
    if env.get('environment_sha256') != digest(deps):
        raise ValueError('Dependency-tree binding mismatch')


def make_campaign(plan: dict, env: dict, baseline: list[dict]) -> dict:
    """The caller derives baseline records with catalog_inputs.load_proofs."""
    all_targets = universe(plan)
    check_environment(plan, env)
    baseline = sorted(baseline, key=key)
    keys = [key(x) for x in baseline]
    if len(set(keys)) != len(keys) or not set(keys) <= all_targets:
        raise ValueError('Duplicate or foreign baseline theorem')
    for row in baseline:
        if set(row) != {'module', 'name', 'snapshot_sha256'} or not isinstance(row['snapshot_sha256'], str) or len(row['snapshot_sha256']) != 64:
            raise ValueError('Baseline needs its exact selected snapshot binding')
    pending = sorted(all_targets-set(keys))
    modules = sorted({m for m, _ in pending}, key=lambda m:(PRIORITY.get(m, 2), m))
    tasks = [{'id': hashlib.sha256(m.encode()).hexdigest()[:24], 'module': m,
              'targets': [{'module': a, 'name': b} for a, b in pending if a == m]}
             for m in modules]
    if len({t['id'] for t in tasks}) != len(tasks):
        raise ValueError('Module identifier collision')
    result = {'schema': SCHEMA, 'upstream_commit': PIN,
              'original_plan_sha256': plan['plan_sha256'],
              'original_environment_sha256': env['environment_sha256'],
              'expected_theorem_targets': len(all_targets),
              'baseline': baseline, 'baseline_readings': len(baseline),
              'selected_theorems': len(pending), 'module_tasks': tasks,
              'baseline_environment_upgraded': False,
              'english_formally_certified': False, 'observations_authenticated': False}
    result['campaign_sha256'] = digest(result)
    return result


def validate_campaign(plan: dict, env: dict, campaign: dict) -> dict:
    if not isinstance(campaign, dict) or campaign != make_campaign(plan, env, campaign.get('baseline', [])):
        raise ValueError('Campaign is not the exact complement of the bound baseline')
    return campaign


def from_artifacts(project: Path, plan: dict, env: dict, proof_roots: list[Path]) -> dict:
    chosen, _ = load_proofs(proof_roots, config_inventory(project), project)
    baseline = [{'module': m, 'name': n, 'snapshot_sha256': v['receipt']['snapshot_sha256']}
                for (m, n), v in chosen.items()]
    return make_campaign(plan, env, baseline)


def run_module(project: Path, plan: dict, env: dict, campaign: dict, module_id: str,
               output: Path, *, trust_project: bool = False, build_timeout: int = 3600,
               extract_timeout: int = 900, max_heartbeats: int = 2_000_000,
               wall_seconds: int = 12_000) -> dict:
    if not trust_project:
        raise PermissionError('Original source execution requires --trust-project')
    validate_campaign(plan, env, campaign)
    selected = [t for t in campaign['module_tasks'] if t['id'] == module_id]
    if len(selected) != 1:
        raise ValueError('Unknown campaign module')
    task = selected[0]
    if output.exists():
        raise ValueError('Use a fresh original-proof worker output directory')
    output.mkdir(parents=True)
    report = {'schema': WORKER, 'campaign_sha256': campaign['campaign_sha256'],
              'module_id': module_id, 'module': task['module'],
              'expected_targets': task['targets'], 'status': 'preflight',
              'environment_before': None, 'environment_after': None,
              'proof_report_sha256': None, 'validated_readings': 0,
              'complete': False, 'observations_authenticated': False}
    save = lambda:write(output/'original-proof-worker.json', report)
    save()
    proof_file = output/'reading/proofs.json'
    try:
        report['environment_before'] = audit_environment(project, plan)
        if report['environment_before'] != env:
            raise ValueError('Worker differs from the independently audited original environment')
        report['status'] = 'running';save()
        # Import only after consent. This runner never writes a reduced Lake file.
        from scripts.retry_finding_proofs import run
        original = run(project, output/'reading', task['targets'], 0, 1,
                       trust_project=True, wall_seconds=wall_seconds,
                       build_timeout=build_timeout, extract_timeout=extract_timeout,
                       max_heartbeats=max_heartbeats)
        report['environment_after'] = audit_environment(project, plan)
        if report['environment_after'] != env:
            raise ValueError('Original source or dependency environment changed during extraction')
        if [key(x) for x in original['targets']] != [key(x) for x in task['targets']]:
            raise ValueError('Worker theorem inventory mismatch')
        chosen, _ = load_proofs([output/'reading'], config_inventory(project), project)
        report['validated_readings'] = len(chosen)
        report['proof_report_sha256'] = file_hash(proof_file)
        report['complete'] = len(chosen) == len(task['targets'])
        report['status'] = 'complete' if report['complete'] else 'partial'
    except (ValueError, OSError, RuntimeError, RecursionError, subprocess.SubprocessError) as exc:
        report.update(status='failed', error=str(exc), complete=False, validated_readings=0)
        # Preserve raw evidence, but do not leave canonical successful rows that a
        # reading-only loader could mistake for a validated original-source run.
        if proof_file.is_file():
            original = read(proof_file)
            write(output/'unvalidated-proof-outcomes.json', original)
            for row in original.get('targets', []):
                if row.get('status') == 'reading-generated':
                    row.update(status='original-environment-invalidated', kernel_checked=False)
            for k in ['kernel_checked', 'readers_written']:
                original[k] = 0
            write(proof_file, original)
            report['proof_report_sha256'] = file_hash(proof_file)
    save()
    return report


def reconcile(project: Path, plan: dict, env: dict, campaign: dict,
              baseline_roots: list[Path], worker_roots: list[Path]) -> tuple[dict, list[Path]]:
    """Return strict accounting plus only validated original-environment reading roots."""
    validate_campaign(plan, env, campaign)
    configs = config_inventory(project)
    baseline, old_attempts = load_proofs(baseline_roots, configs, project)
    expected_baseline = {(r['module'], r['name']): r['snapshot_sha256'] for r in campaign['baseline']}
    if {k:v['receipt']['snapshot_sha256'] for k,v in baseline.items()} != expected_baseline:
        raise ValueError('Baseline artifacts changed since campaign planning')
    tasks = {t['id']:t for t in campaign['module_tasks']}
    seen = set(); fresh = {}; rows = {}; accepted_roots = []
    for root in worker_roots:
        report = read(root/'original-proof-worker.json')
        ident = report.get('module_id')
        if report.get('schema') != WORKER or report.get('campaign_sha256') != campaign['campaign_sha256']:
            raise ValueError('Original-proof worker belongs to another campaign')
        if ident not in tasks or ident in seen:
            raise ValueError('Duplicate or unknown original-proof worker')
        seen.add(ident); task = tasks[ident]
        if report.get('module') != task['module'] or report.get('expected_targets') != task['targets']:
            raise ValueError('Original-proof worker denominator changed')
        status = report.get('status')
        if status not in {'preflight','running','complete','partial','failed'}:
            raise ValueError('Unknown worker state')
        if status not in {'complete','partial'}:
            if report.get('validated_readings', 0) or report.get('complete'):
                raise ValueError('Unfinished worker cannot claim validated readings')
            for target in task['targets']:
                rows[key(target)] = {'module':key(target)[0], 'name':key(target)[1],
                                     'status': 'worker-'+status, 'error': report.get('error')}
            continue
        if report.get('environment_before') != env or report.get('environment_after') != env:
            raise ValueError('Reading success lacks the full original environment audit')
        proof_file = child(root, 'reading/proofs.json')
        if file_hash(proof_file) != report.get('proof_report_sha256'):
            raise ValueError('Original proof outcome ledger changed')
        raw = read(proof_file)
        if [key(r) for r in raw['targets']] != [key(t) for t in task['targets']]:
            raise ValueError('Original proof results omit a selected theorem')
        proofs, _ = load_proofs([root/'reading'], configs, project)
        if len(proofs) != report.get('validated_readings') or report.get('complete') != (len(proofs)==len(task['targets'])):
            raise ValueError('Worker success counts disagree with retained evidence')
        if bool(report['complete']) != (status == 'complete'):
            raise ValueError('Worker completion status mismatch')
        fresh.update(proofs);accepted_roots.append(root/'reading')
        for row in raw['targets']:
            rows[key(row)] = {'module':row['module'], 'name':row['name'], 'status':row['status'],
                              'reason':row.get('reason'), 'errors':row.get('errors',[])}
    for ident, task in tasks.items():
        if ident not in seen:
            for t in task['targets']:
                rows[key(t)] = {'module':t['module'], 'name':t['name'], 'status':'worker-artifact-missing'}
    if set(rows) != universe(plan)-set(baseline):
        raise ValueError('Reconciled campaign does not cover every missing theorem')
    report = {'schema':'leanglish.original-proof-summary/v1','campaign_sha256':campaign['campaign_sha256'],
              'expected_theorem_targets':campaign['expected_theorem_targets'],
              'baseline_readings':len(baseline),'original_environment_new_readings':len(fresh),
              'total_readings':len(baseline)+len(fresh),'theorems_without_reading':len(rows)-len(fresh),
              'module_workers_expected':len(tasks),'module_workers_retained':len(seen),
              'missing_workers':sorted(set(tasks)-seen), 'statuses':dict(Counter(x['status'] for x in rows.values())),
              'targets':[rows[k] for k in sorted(rows)],
              'all_theorems_have_readings':len(baseline)+len(fresh)==campaign['expected_theorem_targets'],
              'baseline_environment_upgraded':False,'full_project_build':False,
              'all_comparators_passed':False,'english_formally_certified':False,
              'observations_authenticated':False,'baseline_attempts_retained':len(old_attempts)}
    return report, accepted_roots
