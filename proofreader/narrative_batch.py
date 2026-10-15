"""Bounded module batches with independently reconciled proof inventories.

Execution is native and explicit opt-in. A checked snapshot is not certified
English. Missing output, failed imports and unsupported proofs remain in the
ledger, and unknown declaration denominators remain null rather than zero.
"""
from __future__ import annotations

from dataclasses import asdict
from html import escape
from pathlib import Path
import json
import math
import re
import uuid
from typing import Any

from .core import lean_string
from .kernel import require
from .kernel_io import strict_json
from .lean import MODULE_RE, driver_file, run_bounded, source_fingerprint
from .model import canonical_json, digest, walk_steps
from .narrative import Snapshot, Narrative
from .narrative_io import exporter_source, write_bundle

PREFIX = 'PR_NARRATIVE_BATCH:'
INVENTORY = 'leanglish.narrative-inventory/v1'
OUTCOME = 'leanglish.narrative-outcome/v1'
COMPLETION = 'leanglish.narrative-completion/v1'
REPORT = 'leanglish.narrative-batch/v1'
KINDS = {'theorem', 'proof-definition', 'opaque-proof'}
MAX_OUTPUT = 32_000_000
MAX_CANDIDATES = 100_000


def _name(value: Any) -> None:
    require(isinstance(value, str) and 0 < len(value) <= 2000 and '\x00' not in value,
            'Invalid declaration name')


def _inventory(obj: dict, scope: str, version: str) -> dict:
    require(isinstance(obj, dict) and set(obj) ==
            {'schema', 'scope', 'lean_version', 'candidates', 'excluded'}, 'Invalid inventory fields')
    require(obj['schema'] == INVENTORY and obj['scope'] == scope, 'Inventory scope mismatch')
    require(obj['lean_version'] == version, 'Inventory toolchain mismatch')
    require(isinstance(obj['candidates'], list) and len(obj['candidates']) <= MAX_CANDIDATES,
            'Missing or over-budget candidate inventory')
    seen: set[str] = set()
    for row in obj['candidates']:
        require(isinstance(row, dict) and set(row) == {'name', 'kind'}, 'Invalid candidate')
        _name(row['name'])
        require(isinstance(row['kind'], str) and row['kind'] in KINDS, 'Invalid declaration kind')
        require(row['name'] not in seen, 'Duplicate candidate')
        seen.add(row['name'])
    require(isinstance(obj['excluded'], list) and len(obj['excluded']) <= MAX_CANDIDATES,
            'Invalid exclusions')
    for row in obj['excluded']:
        require(isinstance(row, dict) and set(row) == {'name', 'reason'}, 'Invalid exclusion')
        _name(row['name'])
        require(row['name'] not in seen and row['reason'] == 'proposition-without-supported-proof-body',
                'Conflicting or unexplained exclusion')
        seen.add(row['name'])
    return obj


def parse_stream(stdout: str, *, module: str, version: str) -> dict:
    """Retain an interrupted inventory, but never call an incomplete stream valid.

    Errors after a valid header keep the denominator. Invalid or duplicated
    records make the whole stream ineligible for checked-evidence labels.
    """
    require(isinstance(stdout, str) and len(stdout.encode('utf-8')) <= MAX_OUTPUT,
            'Batch output budget exceeded')
    inventory = None
    outcomes: dict[str, dict] = {}
    issues: list[str] = []
    footer = None
    for line in stdout.splitlines():
        if not line.startswith(PREFIX):
            continue
        try:
            obj = strict_json(line[len(PREFIX):])
            require(isinstance(obj, dict), 'Event is not an object')
            schema = obj.get('schema')
            require(footer is None, 'Event after completion')
            if schema == INVENTORY:
                require(inventory is None and not outcomes, 'Duplicate or late inventory')
                inventory = _inventory(obj, 'module:' + module, version)
            else:
                require(inventory is not None, 'Event before inventory')
                expected = {r['name']: r['kind'] for r in inventory['candidates']}
                if schema == OUTCOME:
                    status = obj.get('status')
                    fields = {'schema', 'name', 'kind', 'status',
                              'snapshot' if status == 'exported' else 'error'}
                    require(set(obj) == fields and status in {'exported', 'failed'}, 'Invalid outcome fields')
                    _name(obj['name'])
                    require(obj['name'] in expected and obj['kind'] == expected[obj['name']],
                            'Outcome outside the candidate inventory')
                    require(obj['name'] not in outcomes, 'Duplicate outcome')
                    if status == 'exported':
                        snapshot = Snapshot(obj['snapshot'])
                        require(snapshot.record['theorem'] == obj['name'], 'Snapshot identity mismatch')
                        require(snapshot.record['lean_version'] == version, 'Snapshot toolchain mismatch')
                    else:
                        require(isinstance(obj['error'], str) and len(obj['error']) <= 10000,
                                'Invalid failure description')
                    outcomes[obj['name']] = obj
                elif schema == COMPLETION:
                    require(set(obj) == {'schema', 'scope', 'lean_version', 'expected', 'attempted'},
                            'Invalid completion fields')
                    require(obj['scope'] == 'module:' + module and obj['lean_version'] == version,
                            'Completion scope/toolchain mismatch')
                    require(type(obj['expected']) is int and obj['expected'] == len(expected),
                            'Completion inventory mismatch')
                    require(type(obj['attempted']) is int and obj['attempted'] == len(outcomes),
                            'Completion outcome count mismatch')
                    footer = obj
                else:
                    raise ValueError('Unknown batch event schema')
        except (ValueError, TypeError, KeyError, RecursionError) as exc:
            issues.append(str(exc)[:1000])
    if inventory is None:
        issues.append('Missing complete candidate inventory; denominator unknown')
    if footer is None:
        issues.append('Missing completion event')
    expected_rows = inventory['candidates'] if inventory is not None else []
    rows = []
    for candidate in expected_rows:
        outcome = outcomes.get(candidate['name'])
        rows.append(outcome or {**candidate, 'schema': OUTCOME, 'status': 'missing',
                                'error': 'No outcome emitted; candidate remains in the denominator'})
    return {'inventory': inventory, 'rows': rows, 'issues': issues,
            'protocol_ok': not issues, 'missing': sum(r['status'] == 'missing' for r in rows)}


def batch_source(module: str, version: str, max_declarations: int) -> str:
    require(isinstance(module, str) and MODULE_RE.fullmatch(module) is not None, 'Unsafe module name')
    require(isinstance(version, str) and re.fullmatch(r'4\.\d+\.\d+', version) is not None,
            'An exact Lean version is required')
    require(type(max_declarations) is int and 1 <= max_declarations <= 10000, 'Invalid declaration budget')
    marker = 'open Lean Meta Elab Command'
    exporter = exporter_source()
    batch = (Path(__file__).parent / 'data/NarrativeBatch.lean').read_text(encoding='utf-8')
    require(marker in exporter and marker in batch, 'Missing exporter boundary')
    source = exporter.replace(marker, f'import {module}\n{marker}', 1)
    source += '\n' + batch[batch.index(marker):]
    source += '\nset_option maxRecDepth 10000\nset_option maxHeartbeats 4000000\n'
    source += '\nrun_elab do\n  unless Lean.versionString == ' + lean_string(version)
    source += ' do\n    throwError "Leanglish batch exact Lean version mismatch"\n'
    source += '\n#narrative_batch ' + lean_string(module) + f' limit {max_declarations}\n'
    return source


def _write(path: Path, obj: dict | list) -> None:
    """Publish each progress update atomically, not half a JSON document."""
    path.parent.mkdir(parents=True, exist_ok=True)
    require(not path.is_symlink(), 'Refusing a symlink output')
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        tmp.write_text(canonical_json(obj) + '\n', encoding='utf-8')
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink()


def summarize(modules: list[dict]) -> dict:
    unknown = [m['module'] for m in modules if m.get('expected') is None]
    rows = [r for m in modules for r in m.get('rows', [])]
    known = sum(m['expected'] for m in modules if m.get('expected') is not None)
    return {'modules_expected': len(modules),
            'modules_complete': sum(m.get('status') == 'complete' for m in modules),
            'unknown_denominator_modules': unknown,
            'known_candidate_count': known,
            'total_candidates': None if unknown else known,
            'exported': sum(r.get('exported') is True for r in rows),
            'kernel_checked': sum(r.get('kernel_checked') is True for r in rows),
            'rendered': sum(r.get('rendered') is True for r in rows),
            'declarations_with_gaps': sum((r.get('unexpanded_steps') or 0) > 0 for r in rows),
            'unexpanded_steps': sum(r.get('unexpanded_steps') or 0 for r in rows),
            'not_rendered': sum(r.get('rendered') is not True for r in rows),
            'pipeline_complete': bool(modules) and not unknown and all(m.get('status') == 'complete' for m in modules),
            'certified_english_proofs': 0, 'human_readability_evaluated': False,
            'whole_openai_corpus_coverage': False}


def _index(report: dict, output: Path) -> None:
    summary = report['summary']
    chunks = ['<!doctype html><html lang="en"><meta charset="utf-8">',
              '<meta name="viewport" content="width=device-width, initial-scale=1">',
              '<title>Leanglish — batch results</title>',
              '<style>body{font:16px/1.5 system-ui;max-width:1050px;margin:2rem auto;padding:0 1rem}'
              'td,th{text-align:left;padding:.5rem;border-bottom:1px solid #bbb}'
              'table{width:100%;border-collapse:collapse}code{overflow-wrap:anywhere}'
              'details{margin:1rem 0}a{overflow-wrap:anywhere}</style>',
              '<h1>Leanglish · batch results</h1>',
              '<p>Every requested module and every enumerated proof candidate remains visible. '
              'A rendered or kernel-checked proof is not certified English.</p>',
              '<p><strong>' + escape(str(summary['rendered'])) + ' rendered; ' +
              escape(str(summary['kernel_checked'])) + ' kernel-checked; ' +
              escape(str(summary['declarations_with_gaps'])) + ' have explanation gaps.</strong></p>',
              '<p>Total candidate denominator: ' +
              ('unknown (one or more inventories are missing)' if summary['total_candidates'] is None else str(summary['total_candidates'])) +
              '. Run status: ' + escape(report['status']) + '.</p>']
    for module in report['modules']:
        chunks.append('<section><h2>' + escape(module['module']) + '</h2><p>' +
                      escape(module['status']) + ' · expected candidates: ' + escape(str(module['expected'])) + '</p>')
        for error in module.get('errors', []):
            chunks.append('<p><strong>' + escape(error) + '</strong></p>')
        chunks.append('<table><thead><tr><th>Declaration</th><th>Kind</th><th>Result</th><th>Gaps</th></tr></thead><tbody>')
        for row in module.get('rows', []):
            name = escape(row['name'])
            if row.get('rendered'):
                name = '<a href="' + escape(row['reader'], quote=True) + '">' + name + '</a>'
            chunks.append('<tr><td>' + name + '</td><td>' + escape(row['kind']) + '</td><td>' +
                          escape(row['status']) + '</td><td>' + escape(str(row.get('unexpanded_steps', '—'))) + '</td></tr>')
            if row.get('error'):
                chunks.append('<tr><td colspan="4"><code>' + escape(row['error']) + '</code></td></tr>')
        chunks.append('</tbody></table>')
        excluded = module.get('excluded', [])
        if excluded:
            chunks.append('<details><summary>Propositions without proof bodies (' + str(len(excluded)) + ')</summary>')
            chunks.extend('<p>' + escape(r['name'] + ': ' + r['reason']) + '</p>' for r in excluded)
            chunks.append('</details>')
        chunks.append('</section>')
    chunks.append('<p>Evidence is unsigned. Project source fingerprints exclude compiled dependency artifacts. '
                  'No human readability study or formal English-equivalence proof is asserted.</p></html>')
    page = output / 'index.html'
    require(not page.is_symlink(), 'Refusing a symlink index')
    page.write_text('\n'.join(chunks), encoding='utf-8')


def run_batch(modules: list[str], project: Path, output: Path, *, version: str = '4.34.1',
              trust_project: bool = False, timeout: float = 180,
              max_declarations: int = 1000, shard_index: int = 0, shard_count: int = 1) -> dict:
    if not trust_project:
        raise PermissionError('Lean elaboration runs code. Pass --trust-project for a trusted or independently isolated project.')
    require(isinstance(modules, list) and 0 < len(modules) <= MAX_CANDIDATES, 'Supply a nonempty module plan')
    require(all(isinstance(m, str) and MODULE_RE.fullmatch(m) for m in modules), 'Invalid module plan')
    require(len(modules) == len(set(modules)), 'Duplicate module in plan')
    require(type(shard_count) is int and 1 <= shard_count <= 10000 and type(shard_index) is int
            and 0 <= shard_index < shard_count, 'Invalid shard configuration')
    require(isinstance(timeout, (int, float)) and not isinstance(timeout, bool) and math.isfinite(timeout)
            and 0 < timeout <= 900, 'Invalid timeout')
    # Validate all source parameters before creating any output or executing code.
    batch_source(modules[0], version, max_declarations)
    project = Path(project).resolve()
    require(project.is_dir(), 'Native batch needs an existing project')
    output = Path(output)
    require(not output.is_symlink(), 'Refusing a symlink output directory')
    output.mkdir(parents=True, exist_ok=True)
    output = output.resolve()
    require(output != project and project not in output.parents, 'Place batch output outside the Lean project')
    before = source_fingerprint(project)
    selected = [m for m in sorted(modules) if int(digest(m)[:16], 16) % shard_count == shard_index]
    attempt = 'attempts/' + uuid.uuid4().hex
    require(not (output / 'attempts').is_symlink(), 'Refusing a symlink attempts directory')
    (output / attempt).mkdir(parents=True)
    plan = {'modules': sorted(modules), 'version': version, 'max_declarations': max_declarations,
            'exporter_sha256': digest(exporter_source()),
            'batch_exporter_sha256': digest((Path(__file__).parent / 'data/NarrativeBatch.lean').read_bytes())}
    report = {'schema': REPORT, 'status': 'running', 'plan': plan, 'plan_sha256': digest(canonical_json(plan)),
              'project_source_fingerprint': before, 'dependency_artifacts_authenticated': False,
              'receipt_authenticated': False, 'shard_count': shard_count, 'shard_index': shard_index,
              'attempt_directory': attempt,
              'modules': [{'module': m, 'status': 'pending', 'expected': None, 'rows': [], 'errors': []}
                          for m in selected]}

    def save() -> None:
        report['summary'] = summarize(report['modules'])
        _write(output / 'batch.json', report)
        _index(report, output)

    save()  # An interrupted run must not leave the previous successful report.
    for row in report['modules']:
        module = row['module']
        dest = output / attempt / digest(module)
        dest.mkdir()
        row.update(status='running', directory=str(dest.relative_to(output)))
        save()
        try:
            source = batch_source(module, version, max_declarations)
            (dest / 'Extract.lean').write_text(source, encoding='utf-8')
            build = run_bounded(['lake', 'build', module], project, timeout=timeout, max_output=MAX_OUTPUT)
            _write(dest / 'build.json', asdict(build))
            require(build.status == 'passed' and build.exit_code == 0,
                    'Module build failed: ' + (build.reason or build.stderr[-2000:]))
            with driver_file(project, source) as path:
                run = run_bounded(['lake', 'env', 'lean', str(path)], project,
                                  timeout=timeout, max_output=MAX_OUTPUT)
            _write(dest / 'run.json', asdict(run))
            stream = parse_stream(run.stdout, module=module, version=version)
            inv = stream['inventory']
            if inv is not None:
                row['expected'] = len(inv['candidates'])
                row['excluded'] = inv['excluded']
                row['candidate_inventory'] = inv['candidates']
                _write(dest / 'inventory.json', inv)
            row['errors'].extend(stream['issues'])
            execution_ok = run.status == 'passed' and run.exit_code == 0
            if not execution_ok:
                row['errors'].append('Exporter process did not finish successfully: ' + (run.reason or run.stderr[-2000:]))
            eligible = execution_ok and stream['protocol_ok']
            for outcome in stream['rows']:
                result = {k: outcome[k] for k in ('name', 'kind', 'status')}
                result.update(exported=False, kernel_checked=False, path_checked=False, rendered=False)
                row['rows'].append(result)
                if outcome['status'] != 'exported':
                    result['error'] = outcome['error']
                    continue
                snapshot = Snapshot(outcome['snapshot'])
                result['exported'] = True
                result['snapshot_sha256'] = snapshot.sha256
                proof_dir = dest / 'proofs' / digest(outcome['name'])
                _write(proof_dir / 'snapshot.json', snapshot.record)
                if not eligible:
                    result.update(status='unverified-export', error='Incomplete or invalid execution stream; no checking claim attached')
                    continue
                receipt = {'schema': 'proofreader.narrative-receipt/v1', 'status': 'passed',
                           'theorem': outcome['name'], 'lean_version': version, 'backend': 'native',
                           'snapshot_sha256': snapshot.sha256, 'source_sha256': digest(source),
                           'selected_judgements': snapshot.record['judgements_checked'],
                           'all_selected_judgements_kernel_checked': True, 'path_linkage_checked_in_lean': True,
                           'receipt_authenticated': False, 'english_formally_verified': False,
                           'exact_openai_project_replayed': False, 'module': module}
                result.update(kernel_checked=True, path_checked=True)
                try:
                    coverage = write_bundle(snapshot.record, proof_dir, source='import ' + module + '\n',
                                            file=module, receipt=receipt, title='Leanglish · ' + outcome['name'],
                                            provenance_note='Native module batch; declaration kind: ' + outcome['kind'])
                    document = Narrative(snapshot.record).document()
                    gaps = sum(step.fallback for step in walk_steps(document.declarations[0].steps))
                    result.update(rendered=True, status='rendered-with-gaps' if gaps else 'rendered',
                                  reader=str((proof_dir / 'reader.html').relative_to(output)), unexpanded_steps=gaps,
                                  frames=coverage['frames'], budget_cuts=coverage['budget_cuts'],
                                  polynomial_certificates=coverage['polynomial_certificates_replayed'])
                except (OSError, ValueError, RuntimeError, RecursionError) as exc:
                    result.update(status='render-failed', error=str(exc)[:4000])
            row['status'] = ('complete' if eligible and stream['missing'] == 0 and
                             all(r['rendered'] for r in row['rows']) else 'partial')
        except (OSError, ValueError, RuntimeError, RecursionError) as exc:
            row['status'] = 'failed'
            row['errors'].append(str(exc)[:4000])
        save()
    try:
        after = source_fingerprint(project)
    except OSError:
        after = None
    report['project_source_unchanged'] = before == after
    if before != after:
        for module in report['modules']:
            module['status'] = 'source-changed'
            module['errors'].append('Project sources changed during the batch; checking observations invalidated')
            for row in module['rows']:
                row.update(kernel_checked=False, path_checked=False, rendered=False, status='source-changed')
                reader = row.pop('reader', None)
                if reader is not None:
                    proof_dir = (output / reader).parent
                    for filename in ('reading.json', 'reader.html', 'coverage.json', 'proof.txt', 'polynomial-certificates.json'):
                        path = proof_dir / filename
                        if path.is_file():
                            path.unlink()
                    _write(proof_dir / 'receipt.json', {'status': 'source-changed',
                           'snapshot_sha256': row.get('snapshot_sha256'),
                           'all_selected_judgements_kernel_checked': False,
                           'path_linkage_checked_in_lean': False, 'receipt_authenticated': False})
        report['status'] = 'source-changed'
    else:
        report['status'] = 'complete' if all(r['status'] == 'complete' for r in report['modules']) else 'partial'
    save()
    return report


def _validate_report(report: dict) -> None:
    require(isinstance(report, dict) and report.get('schema') == REPORT, 'Unsupported batch report')
    plan = report.get('plan')
    require(isinstance(plan, dict) and isinstance(plan.get('modules'), list), 'Missing plan')
    require(report.get('plan_sha256') == digest(canonical_json(plan)), 'Plan digest mismatch')
    require(all(isinstance(m, str) and MODULE_RE.fullmatch(m) for m in plan['modules']) and
            len(plan['modules']) == len(set(plan['modules'])), 'Invalid plan modules')
    require(isinstance(plan.get('version'), str) and re.fullmatch(r'4\.\d+\.\d+', plan['version']), 'Invalid plan toolchain')
    require(isinstance(report.get('modules'), list), 'Missing module outcomes')
    require(isinstance(report.get('project_source_fingerprint'), str), 'Missing project fingerprint')
    count, index = report.get('shard_count'), report.get('shard_index')
    require(type(count) is int and count > 0 and type(index) is int and 0 <= index < count, 'Invalid shard metadata')
    selected = {m for m in plan['modules'] if int(digest(m)[:16], 16) % count == index}
    seen = set()
    for module in report['modules']:
        require(isinstance(module, dict), 'Invalid module outcome')
        name = module.get('module')
        _name(name)
        require(name in selected and name not in seen, 'Duplicate/unexpected module outcome')
        seen.add(name)
        expected = module.get('expected')
        rows = module.get('rows')
        require(isinstance(rows, list), 'Missing declaration outcomes')
        if expected is None:
            require(not rows and module.get('status') != 'complete', 'Unknown inventory cannot claim completed declarations')
            continue
        require(type(expected) is int and expected >= 0, 'Invalid denominator')
        inv = _inventory({'schema': INVENTORY, 'scope': 'module:' + name, 'lean_version': plan['version'],
                          'candidates': module.get('candidate_inventory'), 'excluded': module.get('excluded', [])},
                         'module:' + name, plan['version'])
        require(expected == len(inv['candidates']) == len(rows), 'Declaration denominator mismatch')
        names = {r['name']: r['kind'] for r in inv['candidates']}
        observed = set()
        for row in rows:
            require(isinstance(row, dict), 'Invalid declaration outcome')
            _name(row.get('name'))
            require(row.get('name') in names and row.get('name') not in observed, 'Duplicate/unexpected declaration')
            observed.add(row['name'])
            require(row.get('kind') == names[row['name']], 'Declaration kind mismatch')
            for flag in ('exported', 'kernel_checked', 'path_checked', 'rendered'):
                require(type(row.get(flag)) is bool, 'Missing or invalid status flag')
            require(not row['kernel_checked'] or (row['exported'] and row['path_checked']), 'Invalid checking claim')
            require(not row['rendered'] or row['kernel_checked'], 'Unchecked batch rendering claim')
            if row['rendered']:
                require(type(row.get('unexpanded_steps')) is int and row['unexpanded_steps'] >= 0, 'Missing gap count')
        require(module.get('status') != 'complete' or all(r['rendered'] for r in rows), 'Incomplete module marked complete')
    require(seen == selected, 'Shard module set mismatch')
    require(report.get('summary') == summarize(report['modules']), 'Summary differs from ledger')


def aggregate(paths: list[Path], output: Path) -> dict:
    """Reconcile unsigned local run records. This never executes or authenticates Lean."""
    require(bool(paths), 'No shard reports supplied')
    require(len(paths) <= 10000, 'Too many shard reports')
    runs=[]
    for p in paths:
        with Path(p).open('rb') as f:
            raw=f.read(MAX_OUTPUT+1)
        require(len(raw) <= MAX_OUTPUT, 'Shard report exceeds the input budget')
        runs.append(strict_json(raw))
    for run in runs:
        _validate_report(run)
    first = runs[0]
    modules: dict[str, dict] = {}
    owners: set[str] = set()
    for run in runs:
        require(run['plan'] == first['plan'], 'Reports belong to different module plans/toolchains/exporters')
        require(run['project_source_fingerprint'] == first['project_source_fingerprint'], 'Reports belong to different project sources')
        for module in run['modules']:
            require(module['module'] not in modules, 'Overlapping shard module')
            for row in module['rows']:
                require(row['name'] not in owners, 'Duplicate declaration ownership across modules')
                owners.add(row['name'])
            modules[module['module']] = module
    combined = [modules.get(name) or {'module': name, 'status': 'missing-shard',
                'expected': None, 'rows': [], 'errors': ['No report supplied for this requested module']}
                for name in first['plan']['modules']]
    result = {'schema': 'leanglish.narrative-aggregate/v1', 'plan': first['plan'],
              'plan_sha256': first['plan_sha256'], 'project_source_fingerprint': first['project_source_fingerprint'],
              'receipt_authenticated': False, 'modules': combined, 'summary': summarize(combined)}
    _write(Path(output), result)
    return result
