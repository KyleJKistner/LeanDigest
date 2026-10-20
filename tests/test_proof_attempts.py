"""Synthetic consistency fixtures only; no native execution is claimed here."""
from copy import deepcopy
from pathlib import Path
import shutil
import pytest
from test_finding_catalog import sample, synthetic_proof
from proofreader.original_project import make_plan, audit_environment, file_hash, read, write, TOOLCHAIN
from proofreader.proof_campaign import make_campaign, WORKER
from proofreader.proof_attempts import reconcile, MAX_ATTEMPTS_PER_MODULE


@pytest.fixture
def scenario(sample, synthetic_proof, tmp_path):
    _, project, _, proofs, _ = sample
    (project/'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage OAI\nlean_lib OAI\n')
    (project/'lean-toolchain').write_text(TOOLCHAIN+'\n')
    write(project/'lake-manifest.json', {'packages': []})
    inventory = [{'path': 'lean/'+p.relative_to(project).as_posix(), 'sha256': file_hash(p)}
                 for p in sorted(project.rglob('*')) if p.is_file()]
    plan = make_plan(project, inventory)
    environment = audit_environment(project, plan)
    campaign = make_campaign(plan, environment, [])
    task = campaign['module_tasks'][0]
    root = tmp_path/'successful-consistency-fixture'
    shutil.copytree(proofs, root/'reading')
    wrapper = {'schema': WORKER, 'campaign_sha256': campaign['campaign_sha256'],
        'module_id': task['id'], 'module': task['module'], 'expected_targets': task['targets'],
        'status': 'complete', 'environment_before': environment, 'environment_after': environment,
        'proof_report_sha256': file_hash(root/'reading/proofs.json'),
        'validated_readings': 1, 'complete': True,
        'test_fixture_only': 'synthetic consistency data, never a native observation'}
    write(root/'original-proof-worker.json', wrapper)
    return project, plan, environment, campaign, root


def failed(scenario, path, label='synthetic unavailable executable'):
    _, _, _, campaign, _ = scenario
    task = campaign['module_tasks'][0]
    write(path/'original-proof-worker.json', {'schema': WORKER,
        'campaign_sha256': campaign['campaign_sha256'], 'module_id': task['id'],
        'module': task['module'], 'expected_targets': task['targets'],
        'status': 'failed', 'validated_readings': 0, 'complete': False, 'error': label})
    return path


def invoke(scenario, roots, baseline=None, campaign=None):
    project, plan, environment, original, _ = scenario
    return reconcile(project, plan, environment, campaign or original, baseline or [], roots)


def test_success_does_not_remove_the_preceding_failure(scenario, tmp_path):
    good = scenario[-1]; bad = failed(scenario, tmp_path/'failed')
    before = {p.relative_to(good).as_posix(): file_hash(p) for p in good.rglob('*') if p.is_file()}
    report, roots = invoke(scenario, [bad, good])
    assert report['total_readings'] == report['expected_theorem_targets'] == 1
    assert report['module_workers_retained'] == 1 and report['retained_worker_attempts'] == 2
    assert {row['status'] for row in report['targets'][0]['attempts']} == {'worker-failed', 'reading-generated'}
    assert roots == [good/'reading']
    assert report['receipts_rewritten'] is False and report['native_execution_rerun'] is False
    assert before == {p.relative_to(good).as_posix(): file_hash(p) for p in good.rglob('*') if p.is_file()}
    other, other_roots = invoke(scenario, [good, bad])
    assert other == report and other_roots == roots


def test_two_valid_observations_are_one_theorem_not_two(scenario, tmp_path):
    first = scenario[-1]; second = tmp_path/'second-consistency-fixture'
    shutil.copytree(first, second)
    record = read(second/'original-proof-worker.json')
    record['test_fixture_only'] = 'second synthetic observation; not a native run'
    write(second/'original-proof-worker.json', record)
    report, roots = invoke(scenario, [first, second])
    assert len(roots) == 2 and report['total_readings'] == 1
    assert report['retained_worker_attempts'] == 2
    expected = max(file_hash(p/'original-proof-worker.json') for p in [first, second])
    assert report['targets'][0]['selected_worker_report_sha256'] == expected
    assert invoke(scenario, [second, first])[0] == report


def test_no_attempts_and_failed_attempts_preserve_the_full_denominator(scenario, tmp_path):
    empty, roots = invoke(scenario, [])
    assert empty['theorems_without_reading'] == 1 and not roots
    bad = failed(scenario, tmp_path/'bad')
    another = failed(scenario, tmp_path/'other-bad', 'synthetic timeout')
    report, roots = invoke(scenario, [bad, another])
    assert report['theorems_without_reading'] == 1 and report['total_readings'] == 0
    assert report['retained_worker_attempts'] == 2 and not roots
    assert report['statuses'] == {'attempts-unsuccessful': 1}


def test_changed_earlier_success_is_not_hidden_by_a_later_valid_one(scenario, tmp_path):
    first = scenario[-1]; second = tmp_path/'second'
    shutil.copytree(first, second)
    wrapper = read(second/'original-proof-worker.json'); wrapper['test_fixture_only'] = 'second'
    write(second/'original-proof-worker.json', wrapper)
    run_file = next((first/'reading/targets').glob('*/run.json'))
    run = read(run_file); run['exit_code'] = 1; write(run_file, run)
    with pytest.raises(ValueError):
        invoke(scenario, [first, second])


def test_identical_worker_copy_is_not_an_additional_attempt(scenario, tmp_path):
    first = scenario[-1]; second = tmp_path/'duplicate'
    shutil.copytree(first, second)
    with pytest.raises(ValueError, match='Duplicate'):
        invoke(scenario, [first, second])


def test_baseline_reading_keeps_its_original_snapshot_and_scope(scenario):
    project, plan, environment, _, good = scenario
    target = read(good/'reading/proofs.json')['targets'][0]
    campaign = make_campaign(plan, environment, [{'module': target['module'], 'name': target['name'],
                                                'snapshot_sha256': target['snapshot_sha256']}])
    report, roots = invoke(scenario, [], baseline=[good/'reading'], campaign=campaign)
    assert report['baseline_readings'] == report['total_readings'] == 1
    assert report['original_environment_new_readings'] == 0
    assert report['baseline_environment_upgraded'] is False
    assert report['retained_worker_attempts'] == 0 and not roots


def test_attempt_bound_is_checked_before_large_reconciliation(scenario, tmp_path):
    roots = [failed(scenario, tmp_path/str(i), 'synthetic failure '+str(i))
             for i in range(MAX_ATTEMPTS_PER_MODULE+1)]
    with pytest.raises(ValueError, match='bound'):
        invoke(scenario, roots)


def test_unknown_module_and_changed_campaign_are_rejected(scenario, tmp_path):
    bad = failed(scenario, tmp_path/'bad')
    marker = bad/'original-proof-worker.json'; record = read(marker)
    record['module_id'] = 'not-in-plan'; write(marker, record)
    with pytest.raises(ValueError, match='Unknown'):
        invoke(scenario, [bad])
    record['module_id'] = scenario[3]['module_tasks'][0]['id']
    record['campaign_sha256'] = '0'*64; write(marker, record)
    with pytest.raises(ValueError):
        invoke(scenario, [bad])
