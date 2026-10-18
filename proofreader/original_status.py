"""Join original-project checks to a reading catalog without upgrading old receipts.

Reconcile raw worker evidence first. The status ledger records all build/config
obligations, separate proof-reading availability, and definition-hole limitations.
It is a consistency check over unsigned observations, not an attestation service.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import html
from pathlib import Path
import re
import zipfile

from .original_project import read, write, file_hash, digest, child, reconcile
from .proof_campaign import reconcile as reconcile_proofs, check_environment, universe
from .catalog_inputs import config_inventory, load_proofs

SCHEMA = 'leanglish.original-status/v1'


def check_archive(archive: Path, directory: Path, expected_digest: str) -> None:
    """Bind the extracted observations to their retained, digest-checked ZIP bytes."""
    if file_hash(archive) != expected_digest:
        raise ValueError('Original artifact archive digest changed')
    with zipfile.ZipFile(archive) as z:
        expected = set()
        for member in z.infolist():
            if member.is_dir():
                continue
            path = child(directory, member.filename)
            if member.filename in expected:
                raise ValueError('Duplicate archived evidence path')
            expected.add(member.filename)
            if not path.is_file() or path.stat().st_size != member.file_size:
                raise ValueError('Retained evidence file is missing or has changed size')
            with z.open(member) as stream:
                from hashlib import file_digest
                value = file_digest(stream, 'sha256').hexdigest()
            if file_hash(path) != value:
                raise ValueError('Retained evidence differs from its original archive')
        actual = {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}
        if actual != expected:
            raise ValueError('Extra or missing extracted evidence files')


def check_collection(root: Path) -> dict:
    """No glob-only denominator: use the frozen acquisition inventory explicitly."""
    collection = read(root/'collection.json')
    if (collection.get('schema') != 'leanglish.original-evidence-collection/v1' or
        collection.get('repository') != 'KyleJKistner/LeanDigest' or collection.get('errors') != [] or
        set(collection.get('runs', {})) != {'original-build', 'original-proofs'}):
        raise ValueError('Missing or unsuccessful original evidence collection')
    counts = {}
    for group, bound in collection['runs'].items():
        folder = child(root, group)
        frozen = read(folder/'frozen-artifacts.json')
        run = read(folder/'run.json')
        if bound.get('run_id') != run.get('id') or bound.get('source_commit') != run.get('head_sha'):
            raise ValueError('Collection execution identity mismatch')
        observations = bound.get('outcomes', [])
        if len(observations) != len(frozen) or len({x['id'] for x in observations}) != len(frozen):
            raise ValueError('Artifact denominator mismatch')
        by_id = {x['id']:x for x in frozen}
        for row in observations:
            artifact = by_id.get(row['id'])
            if (artifact is None or row.get('status') != 'retained' or
                row.get('name') != artifact['name'] or
                row.get('run_id') != bound['run_id'] or row.get('source_commit') != bound['source_commit'] or
                artifact.get('workflow_run', {}).get('id') != bound['run_id'] or
                artifact.get('workflow_run', {}).get('head_sha') != bound['source_commit'] or
                artifact.get('digest') != 'sha256:'+row['sha256']):
                raise ValueError('Artifact identity or source binding changed')
            name = row['name']
            if not re.fullmatch(r'[A-Za-z0-9_.-]+', name) or name in {'.', '..'}:
                raise ValueError('Unsafe artifact name')
            check_archive(child(folder, name+'.zip'), child(folder, name), row['sha256'])
        counts[group] = len(observations)
    return {'collection_sha256': file_hash(root/'collection.json'),
            'cutoff': collection['cutoff'], 'artifact_counts': counts}


def diagnosis(row: dict | None, log: dict | None) -> str:
    """Conservative operational labels; failed execution is not a mathematical refutation."""
    if row is None:
        return 'no-retained-outcome'
    if row['status'] == 'passed':
        return 'passed'
    if log is None:
        return 'unfinished-or-unretained-execution'
    if row['status'] == 'timeout' or log.get('reason') == 'timeout':
        return 'time-budget-exhausted'
    messages = log.get('stderr', '')+'\n'+log.get('stdout', '')
    if 'nanoda_bin' in messages and 'executable file not found' in messages:
        return 'required-external-kernel-unavailable'
    if log.get('exit_code') in (143, -15):
        return 'process-terminated'
    return 'unsuccessful-execution-needs-review'


def task_rows(plan: dict, roots: list[Path]) -> tuple[dict, list[dict]]:
    """Reuse the independent original-build gate before publishing any successful row."""
    summary = reconcile(plan, roots)
    observations = {}
    for root in roots:
        report_path = root/'worker.json'
        report = read(report_path)
        for row in report['targets']:
            log = None
            if row.get('log'):
                p = child(root, row['log'])
                if file_hash(p) != row.get('log_sha256'):
                    raise ValueError('Even unsuccessful outcomes require their unchanged execution log')
                log = read(p)
            observations[row['id']] = (row, log, file_hash(report_path))
    rows = []
    for task in plan['tasks']:
        row, log, report_hash = observations.get(task['id'], (None, None, None))
        result = {'id': task['id'], 'kind': task['kind'],
                  'status': row['status'] if row else 'not-retained',
                  'diagnosis': diagnosis(row, log), 'worker_report_sha256': report_hash,
                  'log_sha256': row.get('log_sha256') if row else None,
                  'exit_code': log.get('exit_code') if log else None}
        if task['kind'] == 'comparator':
            result.update(configuration=task['config'].removeprefix('ComparatorChallenges/').removesuffix('.json'),
                          configuration_sha256=task['sha256'], solution_module=task['solution_module'],
                          theorem_names=task['theorem_names'], definition_names=task['definition_names'],
                          definition_intent_review_required=bool(task['definition_names']),
                          external_kernel_required=task['enable_nanoda'])
        else:
            result['library'] = task['library']
        rows.append(result)
    assert len(rows) == summary['expected_tasks']
    return summary, rows


def build_status(project: Path, root: Path, *, recovery_output: Path | None = None) -> tuple[dict, list[Path]]:
    """Return a freshly reconciled status record and only validated reading roots."""
    collection = check_collection(root)
    seed = root/'original-proofs/original-proof-campaign-plan'
    plan, env, campaign = [read(seed/(name+'.json')) for name in ('plan', 'environment', 'campaign')]
    check_environment(plan, env)
    builds, tasks = task_rows(plan, [p.parent for p in sorted((root/'original-build').rglob('worker.json'))])
    baseline = [root/'baseline'/str(i) for i in range(4)]
    proof_summary, new_roots = reconcile_proofs(project, plan, env, campaign, baseline,
        [p.parent for p in sorted((root/'original-proofs').rglob('original-proof-worker.json'))])
    recoveries = []
    if recovery_output is not None:
        from .retained_output import recover
        before_recovery = digest(proof_summary)
        for worker in sorted((root/'original-proofs').rglob('original-proof-worker.json')):
            if not (worker.parent/'reading/proofs.json').is_file():
                continue
            for row in read(worker.parent/'reading/proofs.json')['targets']:
                if row.get('status')=='extraction-failed' and row.get('errors')==['Exporter output budget']:
                    destination = recovery_output/row['id']
                    recovered = recover(project,plan,env,worker.parent,row,destination)
                    recoveries.append(recovered);new_roots.append(destination)
        if recoveries:
            recovered_keys = {(r['module'],r['name']) for r in recoveries}
            if len(recovered_keys)!=len(recoveries):raise ValueError('Repeated retained-output recovery')
            proof_summary['schema']='leanglish.original-proof-summary/v2'
            proof_summary['prior_reconciliation_sha256']=before_recovery
            proof_summary['direct_original_environment_readings']=proof_summary['original_environment_new_readings']
            proof_summary['retained_output_recovered_readings']=len(recoveries)
            proof_summary['original_environment_new_readings']+=len(recoveries)
            proof_summary['total_readings']+=len(recoveries)
            proof_summary['theorems_without_reading']-=len(recoveries)
            for row in proof_summary['targets']:
                if (row['module'],row['name']) in recovered_keys:
                    row['prior_status']=row['status'];row['prior_errors']=row.get('errors',[])
                    row['status']='reading-reprocessed-from-successful-native-output';row['errors']=[]
            proof_summary['statuses']=dict(Counter(r['status'] for r in proof_summary['targets']))
            proof_summary['all_theorems_have_readings']=proof_summary['theorems_without_reading']==0
    chosen, _ = load_proofs(baseline+new_roots, config_inventory(project), project)
    if len(chosen)!=proof_summary['total_readings']:
        raise ValueError('Recovery results do not match normal proof-loader validation')
    baseline_keys = {(r['module'], r['name']) for r in campaign['baseline']}
    proofs = []
    for module, name in sorted(universe(plan)):
        selected = chosen.get((module, name))
        matches = [r for r in tasks if r['kind']=='comparator' and
                   r['solution_module']==module and name in r['theorem_names']]
        proofs.append({'module': module, 'name': name, 'reading_available': selected is not None,
            'reading_id': selected['row']['id'] if selected else None,
            'snapshot_sha256': selected['receipt']['snapshot_sha256'] if selected else None,
            'reading_environment': ('not-available' if selected is None else
                'baseline-recorded-environment' if (module,name) in baseline_keys else 'full-original-dependency-audit'),
            'configurations_passed': [r['configuration'] for r in matches if r['status']=='passed'],
            'configurations_not_passed': [r['configuration'] for r in matches if r['status']!='passed'],
            'definition_intent_review_required': any(r['definition_intent_review_required'] for r in matches)})
    result = {'schema': SCHEMA, 'upstream_commit': plan['upstream_commit'],
        'collection': collection, 'original_plan_sha256': plan['plan_sha256'],
        'original_environment_sha256': env['environment_sha256'],
        'build_summary': builds, 'proof_summary': proof_summary,
        'tasks': tasks, 'theorems': proofs, 'retained_output_recoveries':recoveries,
        'diagnoses': dict(sorted(Counter(r['diagnosis'] for r in tasks).items())),
        'toolchain': plan['toolchain'], 'dependency_count': len(env['dependencies']),
        'approved_dependency_patch_count': sum(r['patch_sha256'] is not None for r in env['dependencies'].values()),
        'baseline_environment_upgraded': False, 'english_formally_verified': False,
        'adversarial_sandbox_security_certified': False, 'observations_authenticated': False,
        'limitations': ['Specification identity and permitted axioms are checked only for the passed configurations.',
                       'Definition holes still need independent mathematical-intent review.',
                       'A timeout or missing job artifact is not evidence against the theorem.',
                       'Imported libraries and external checker implementations remain trusted.',
                       'The old baseline is not relabeled as a full-original-environment run.',
                       'Complete exposition and formally verified English remain separate requirements.']}
    result['status_sha256'] = digest(result)
    return result, baseline+new_roots


def attach_status(site: Path, record: dict) -> None:
    """Add status pages, preserving every formal source, receipt and reading byte."""
    from .finding_catalog import shell
    coverage = read(site/'coverage.json')
    if (record['schema'] != SCHEMA or
        record.get('status_sha256') != digest({k:v for k,v in record.items() if k!='status_sha256'}) or
        record['proof_summary']['total_readings'] != coverage['proof_readings'] or
        record['proof_summary']['expected_theorem_targets'] != coverage['expected_theorem_targets']):
        raise ValueError('Original-project ledger does not match the rendered catalog')
    write(site/'original-verification.json', record)
    b, p = record['build_summary'], record['proof_summary']
    body = ('<h1>Original-project verification</h1><p>Frozen retained observations as of '+html.escape(record['collection']['cutoff'])+'. '
            'Missing and active workers remain outstanding; this is not a completion claim.</p>'
            '<div class="stats"><div><strong>'+str(p['total_readings'])+' / '+str(p['expected_theorem_targets'])+'</strong><span>proof readings available</span></div>'
            '<div><strong>'+str(b['comparator_passed'])+' / '+str(b['comparator_expected'])+'</strong><span>original comparison configurations passed</span></div>'
            '<div><strong>'+str(b['library_passed'])+' / '+str(b['library_expected'])+'</strong><span>original library targets built</span></div></div>'
            '<p>'+str(p['original_environment_new_readings'])+' new readings have the full '+str(record['dependency_count'])+'-dependency audit. '
            'The '+str(p['baseline_readings'])+' earlier readings retain their own execution scope.</p>'
            '<p><strong>Readings are not formally verified English.</strong> Definition-hole acceptance does not certify the intended mathematical meaning. '
            'Timeouts and infrastructure failures are not mathematical refutations.</p>'
            '<p><a href="original-verification.json">Complete machine-readable ledger and source bindings</a> · '
            '<a href="coverage.html">Reading coverage and limitations</a></p>'
            '<h2>Every original build and configuration</h2><table style="table-layout:fixed;width:100%;overflow-wrap:anywhere"><thead><tr><th>Obligation</th><th>Retained outcome</th><th>Interpretation</th></tr></thead><tbody>')
    for row in record['tasks']:
        label = row.get('configuration', row.get('library'))
        anchor = sha256(row['id'].encode()).hexdigest()[:24]
        link = ('<a href="originals/ComparatorChallenges/'+html.escape(label,quote=True)+'.json">'+html.escape(label)+'</a>'
                if row['kind']=='comparator' else html.escape(label))
        detail = row['diagnosis'].replace('-', ' ')
        if row.get('definition_intent_review_required'):
            detail += '; definition-intent review required'
        if row.get('external_kernel_required'):
            detail += '; external kernel required by original configuration'
        body += '<tr id="'+anchor+'"><td>'+link+'</td><td>'+html.escape(row['status'])+'</td><td>'+html.escape(detail)+'</td></tr>'
    body += '</tbody></table>'
    (site/'original-verification.html').write_text(shell('Original-project verification',body),encoding='utf-8')
    notice = '<p class="notice"><a href="original-verification.html">Inspect original-project builds, statement comparisons, and the full theorem-reading ledger.</a></p>'
    for filename in ('index.html','coverage.html'):
        path = site/filename
        text = path.read_text()
        if '<main id="content">' not in text:
            raise ValueError('Catalog attachment location is missing')
        path.write_text(text.replace('<main id="content">','<main id="content">'+notice,1),encoding='utf-8')
    # Existing readers stay unchanged. Navigation on each finding exposes exact configuration outcomes.
    ledger = read(site/'catalog.json')
    for finding in ledger:
        configs = set(finding['configurations'])
        checks = [r for r in record['tasks'] if r.get('configuration') in configs]
        if not checks:
            continue
        passed = sum(r['status']=='passed' for r in checks)
        text = ('<p class="notice">Original configuration checks: '+str(passed)+' of '+str(len(checks))+' passed. '
                '<a href="../original-verification.html">Inspect the exact recorded scope and remaining work.</a></p>')
        path = site/'findings'/(finding['id']+'.html')
        path.write_text(path.read_text().replace('<main id="content">','<main id="content">'+text,1),encoding='utf-8')
