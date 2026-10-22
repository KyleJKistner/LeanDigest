"""Validate every native proof attempt, then select one reading per target.

The original single-attempt checker is unchanged. Independent layers contain at
most one attempt per module, so each can pass that checker without relaxing its
source, scope, receipt or denominator rules. All accepted reading directories
remain the original directories; no receipt or compiler output is rewritten.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from pathlib import Path
from .original_project import read, file_hash, digest
from .catalog_inputs import config_inventory, load_proofs
from .proof_campaign import validate_campaign, universe, reconcile as check_layer

MAX_ATTEMPTS_PER_MODULE = 8


def reconcile(project: Path, plan: dict, environment: dict, campaign: dict,
              baseline_roots: list[Path], worker_roots: list[Path]) -> tuple[dict, list[Path]]:
    validate_campaign(plan, environment, campaign)
    tasks = {task['id']: task for task in campaign['module_tasks']}
    if len(worker_roots) > MAX_ATTEMPTS_PER_MODULE * len(tasks):
        raise ValueError('Native proof attempt inventory exceeds the configured bound')
    groups = defaultdict(list)
    seen = set()
    for root in worker_roots:
        marker = root/'original-proof-worker.json'
        record = read(marker)
        ident = record.get('module_id')
        checksum = file_hash(marker)
        if ident not in tasks:
            raise ValueError('Unknown native proof-attempt module')
        if checksum in seen:
            raise ValueError('Duplicate retained native proof attempt')
        seen.add(checksum)
        groups[ident].append((checksum, root))
        if len(groups[ident]) > MAX_ATTEMPTS_PER_MODULE:
            raise ValueError('Too many attempts for one original proof module')
    for attempts in groups.values():
        attempts.sort(key=lambda item: item[0])
    histories = {(target['module'], target['name']): []
                 for task in tasks.values() for target in task['targets']}
    accepted = []
    layer_records = []
    # Even an empty attempt set must validate the bound baseline independently.
    layer_count = max((len(attempts) for attempts in groups.values()), default=1)
    for index in range(layer_count):
        layer = [groups[ident][index] for ident in sorted(groups) if index < len(groups[ident])]
        summary, roots = check_layer(project, plan, environment, campaign,
                                     baseline_roots, [root for _, root in layer])
        layer_records.append({'summary_sha256': digest(summary),
                              'worker_report_sha256': [checksum for checksum, _ in layer]})
        by_key = {(row['module'], row['name']): row for row in summary['targets']}
        accepted_paths = {root.resolve() for root in roots}
        for checksum, root in layer:
            wrapper = read(root/'original-proof-worker.json')
            task = tasks[wrapper['module_id']]
            for target in task['targets']:
                key = target['module'], target['name']
                row = by_key[key]
                histories[key].append({'worker_report_sha256': checksum,
                    'status': row['status'], 'reason': row.get('reason'),
                    'error': row.get('error'), 'errors': row.get('errors', [])})
            reading = root/'reading'
            if reading.resolve() in accepted_paths:
                accepted.append((checksum, reading))
    # load_proofs already supports multiple successful observations of a target.
    # A fixed hash order is reproducible and does not pretend to establish time.
    accepted.sort(key=lambda item: item[0])
    reading_roots = [root for _, root in accepted]
    chosen, _ = load_proofs(baseline_roots + reading_roots, config_inventory(project), project)
    baseline = {(row['module'], row['name']): row['snapshot_sha256'] for row in campaign['baseline']}
    expected = universe(plan)
    if not set(chosen) <= expected or not set(baseline) <= set(chosen):
        raise ValueError('Proof attempts changed the original theorem inventory')
    for key, checksum in baseline.items():
        if chosen[key]['receipt']['snapshot_sha256'] != checksum:
            raise ValueError('A native retry replaced or relabeled a baseline reading')
    if set(histories) != expected - set(baseline):
        raise ValueError('Proof attempts do not preserve the complete outstanding denominator')
    successful_selection = {}
    for checksum, root in accepted:
        proofs, _ = load_proofs([root], config_inventory(project), project)
        for key in proofs:
            successful_selection[key] = checksum
    rows = []
    for key in sorted(histories):
        attempts = sorted(histories[key], key=lambda row: row['worker_report_sha256'])
        selected = chosen.get(key)
        rows.append({'module': key[0], 'name': key[1],
            'status': 'reading-generated' if selected else
                      'attempts-unsuccessful' if attempts else 'worker-artifact-missing',
            'attempts': attempts,
            'selected_worker_report_sha256': successful_selection.get(key),
            'snapshot_sha256': selected['receipt']['snapshot_sha256'] if selected else None})
    fresh = len(chosen) - len(baseline)
    result = {'schema': 'leanglish.original-proof-attempt-summary/v1',
        'campaign_sha256': campaign['campaign_sha256'],
        'expected_theorem_targets': len(expected), 'baseline_readings': len(baseline),
        'original_environment_new_readings': fresh, 'total_readings': len(chosen),
        'theorems_without_reading': len(expected) - len(chosen),
        'module_workers_expected': len(tasks), 'module_workers_retained': len(groups),
        'retained_worker_attempts': len(seen),
        'missing_workers': sorted(set(tasks) - set(groups)),
        'statuses': dict(Counter(row['status'] for row in rows)), 'targets': rows,
        'validated_layers': layer_records,
        'selection_rule': 'last successful observation in ascending worker-report SHA-256 order; not chronological',
        'all_theorems_have_readings': len(chosen) == len(expected),
        'baseline_environment_upgraded': False, 'receipts_rewritten': False,
        'native_execution_rerun': False, 'full_project_build': False,
        'all_comparators_passed': False, 'english_formally_certified': False,
        'observations_authenticated': False}
    result['summary_sha256'] = digest(result)
    return result, reading_roots
