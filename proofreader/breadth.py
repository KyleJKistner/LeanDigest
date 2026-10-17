"""Reconcile native breadth shards against the full documented theorem universe.

Missing or interrupted job artifacts are not successes, failures of mathematics,
zero-theorem modules, or proof observations. Successful observations still pass
catalog_inputs.load_proofs, including source, driver, snapshot and output checks.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from .catalog_inputs import PIN, config_inventory, load_proofs, read_json, write_json


def key(row: dict) -> tuple[str, str]:
    return row['module'], row['name']


def partition(module: str, shards: int) -> int:
    return int(sha256(module.encode()).hexdigest(), 16) % shards


def validate_selection(selection: list, universe: set, baseline: set) -> list[tuple[str, str]]:
    if not isinstance(selection, list):
        raise ValueError('Selection must be a list')
    if any(not isinstance(r, dict) or set(r) != {'module', 'name'} or
           any(not isinstance(r[x], str) for x in ('module', 'name')) for r in selection):
        raise ValueError('Selection requires exactly module and name strings')
    keys = [key(r) for r in selection]
    if keys != sorted(set(keys)):
        raise ValueError('Selection must be unique and sorted')
    if not baseline <= universe or set(keys) != universe - baseline:
        raise ValueError('Selection is not the full complement of the baseline readings')
    return keys


def validate_shards(selection: list, universe: set, baseline: set,
                    reports: list[dict], shards: int = 64) -> dict:
    """Pure inventory checks; this function alone does not validate proof receipts."""
    if type(shards) is not int or not 1 <= shards <= 64:
        raise ValueError('Invalid shard count')
    keys = validate_selection(selection, universe, baseline)
    selection_hash = sha256(json.dumps(selection, sort_keys=True).encode()).hexdigest()
    by = {}; recorded = {}
    statuses = {'pending', 'building', 'extracting', 'reading-generated', 'source-missing',
                'toolchain-unavailable', 'build-failed', 'build-unavailable',
                'deadline-not-attempted', 'deadline-not-extracted', 'extraction-failed'}
    for r in reports:
        if not isinstance(r, dict) or r.get('schema') != 'leanglish.finding-proof-shard/v1' or r.get('upstream_commit') != PIN:
            raise ValueError('Wrong breadth report format or source revision')
        shard = r.get('shard')
        if type(shard) is not int or not 0 <= shard < shards or shard in by or r.get('shards') != shards:
            raise ValueError('Duplicate, foreign or invalid shard')
        expected = [k for k in keys if partition(k[0], shards) == shard]
        if (r.get('selection_count') != len(keys) or r.get('selection_sha256') != selection_hash or
                type(r.get('expected_targets')) is not int or r['expected_targets'] != len(expected) or
                type(r.get('expected_theorems')) is not int or r['expected_theorems'] != len(expected)):
            raise ValueError('Shard selection identity or denominator mismatch')
        rows = r.get('targets')
        if not isinstance(rows, list) or len(rows) != len(expected):
            raise ValueError('Missing or extra shard targets')
        for row, k in zip(rows, expected):
            if not isinstance(row, dict) or (row.get('module'), row.get('name')) != k or row.get('kind') != 'theorem':
                raise ValueError('Wrong target order, identity or kind')
            ident = sha256((k[0]+'\0'+k[1]).encode()).hexdigest()[:24]
            if row.get('id') != ident or row.get('status') not in statuses:
                raise ValueError('Invalid target identifier or status')
            if type(row.get('kernel_checked')) is not bool or row['kernel_checked'] != (row['status'] == 'reading-generated'):
                raise ValueError('Target status/checking claim disagreement')
            recorded[k] = row
        checks = sum(x['kernel_checked'] for x in rows)
        pending = sum(x['status'] in {'pending', 'building', 'extracting'} for x in rows)
        for name, value in [('kernel_checked', checks), ('readers_written', checks), ('pending', pending)]:
            if type(r.get(name)) is not int or r[name] != value:
                raise ValueError('Shard summary does not reconcile with its targets')
        by[shard] = r
    missing = sorted(set(range(shards))-set(by))
    outcomes = []
    for k in keys:
        row = recorded.get(k)
        outcomes.append({'module': k[0], 'name': k[1], 'shard': partition(k[0], shards),
                         'status': row['status'] if row else 'artifact-not-retained',
                         'observation_retained': row is not None,
                         'kernel_checked': bool(row and row['kernel_checked'])})
    return {'schema': 'leanglish.breadth-ledger/v1', 'upstream_commit': PIN,
            'expected_theorem_targets': len(universe), 'baseline_readings': len(baseline),
            'selected_targets': len(keys), 'selection_sha256': selection_hash,
            'expected_shards': shards, 'retained_report_shards': sorted(by),
            'missing_report_shards': missing, 'all_shard_reports_retained': not missing,
            'recorded_targets': len(recorded), 'targets_without_report': len(keys)-len(recorded),
            'recorded_new_readings': sum(r['kernel_checked'] for r in outcomes),
            'statuses': dict(sorted(Counter(r['status'] for r in outcomes).items())),
            'targets': outcomes, 'receipts_consistency_checked': False,
            'receipts_authenticated': False, 'formally_certified_english_proofs': 0}


def reconcile(lean: Path, baseline_roots: list[Path], breadth: Path, shards: int = 64) -> dict:
    configs = config_inventory(lean)
    universe = {(c['solution_module'], n) for c in configs.values() for n in c.get('theorem_names', [])}
    baseline, _ = load_proofs(baseline_roots, configs, lean)
    paths = sorted(breadth.rglob('proofs.json'))
    if not paths:
        raise ValueError('No breadth shard reports retained')
    selections = [read_json(p.parent/'selection.json') for p in paths]
    if any(s != selections[0] for s in selections):
        raise ValueError('Shard selections disagree')
    result = validate_shards(selections[0], universe, set(baseline), [read_json(p) for p in paths], shards)
    new, _ = load_proofs([breadth], configs, lean)
    if len(new) != result['recorded_new_readings'] or set(new) & set(baseline):
        raise ValueError('Receipt-validated readings do not match breadth outcomes')
    result['receipts_consistency_checked'] = True
    result['total_retained_readings'] = len(baseline) + len(new)
    result['theorem_targets_without_reading'] = len(universe) - len(baseline) - len(new)
    result['reports'] = [{'path': p.relative_to(breadth).as_posix(), 'sha256': sha256(p.read_bytes()).hexdigest()}
                         for p in paths]
    result['limitations'] = [
        'A missing artifact is not evidence that its job succeeded or failed.',
        'Unfinished and failed targets remain in the complete documented denominator.',
        'Source-bound readings may contain explicit explanation gaps.',
        'Unsigned execution observations establish consistency, not authenticity.']
    return result


def attach(site: Path, ledger: dict) -> None:
    """Attach a human-readable progress page without upgrading catalog coverage."""
    import html
    from .finding_catalog import shell
    coverage=read_json(site/'coverage.json')
    if (ledger.get('receipts_consistency_checked') is not True or
        ledger.get('expected_theorem_targets') != coverage['expected_theorem_targets'] or
        ledger.get('total_retained_readings') != coverage['proof_readings']):
        raise ValueError('Breadth ledger disagrees with the rendered catalog')
    write_json(site/'breadth.json', ledger)
    statuses = ''.join('<tr><td>'+html.escape(s)+'</td><td>'+str(n)+'</td></tr>' for s, n in ledger['statuses'].items())
    body = ('<h1>Proof-reading coverage</h1><p>Every documented theorem target remains in the denominator. '
            'Job scheduling, source compilation, checked readings and English explanation are separate stages.</p>'
            '<p><strong>'+str(ledger['total_retained_readings'])+' of '+str(ledger['expected_theorem_targets'])+
            '</strong> theorem targets have retained source-bound readings. '
            +str(ledger['theorem_targets_without_reading'])+' still lack a reading.</p>'
            '<h2>Additional breadth run</h2><p>'+str(ledger['recorded_targets'])+' of '+str(ledger['selected_targets'])+
            ' selected targets have retained job reports. Missing reports do not change the target count.</p>'
            '<table><thead><tr><th>Recorded state</th><th>Targets</th></tr></thead><tbody>'+statuses+'</tbody></table>'
            '<p>Missing report shards: '+html.escape(', '.join(map(str, ledger['missing_report_shards'])) or 'none')+'.</p>'
            '<p>These are resource and tool-pipeline states, not verdicts on mathematical correctness. '
            'Readings can contain unexpanded arguments and are not formally certified English proofs.</p>'
            '<p><a href="breadth.json">Complete target-by-target ledger</a> · '
            '<a href="coverage.html">Coverage and verification boundaries</a></p>')
    (site/'progress.html').write_text(shell('Proof-reading progress', body), encoding='utf-8')
    for name in ('index.html', 'coverage.html'):
        p = site/name
        s = p.read_text()
        link = '<p class="notice"><a href="progress.html">Track every remaining theorem target and retained job outcome.</a></p>'
        s = s.replace('<main id="content">', '<main id="content">'+link, 1)
        p.write_text(s, encoding='utf-8')
