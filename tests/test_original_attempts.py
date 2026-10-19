from copy import deepcopy
import shutil
import pytest
from proofreader.original_project import read, write, file_hash
from proofreader.original_attempts import reconcile_attempts
from test_original_project import successful_library_report


def make_timeout(root):
    report=read(root/'worker.json')
    log_path=root/report['targets'][0]['log']
    log=read(log_path)
    log.update(status='failed',exit_code=-9,reason='timeout',stdout='partial build')
    write(log_path,log)
    report['targets'][0].update(status='timeout',log_sha256=file_hash(log_path))
    report.update(status='partial',complete=False)
    write(root/'worker.json',report)


def test_successful_retry_preserves_prior_failure(tmp_path):
    _,plan,success,report=successful_library_report(tmp_path)
    prior=tmp_path/'prior';shutil.copytree(success,prior);make_timeout(prior)
    result=reconcile_attempts(plan,[prior,success],environment=report['environment_before'])
    assert result['expected_tasks']==2 and result['recorded_tasks']==1
    assert result['retained_attempts']==2 and result['library_passed']==1
    assert result['comparator_passed']==0 and result['complete'] is False
    histories=result['tasks'][0]['attempts']
    assert {r['status'] for r in histories}=={'passed','timeout'}
    assert result==reconcile_attempts(plan,[success,prior],environment=report['environment_before'])


def test_timeout_never_satisfies_missing_task(tmp_path):
    _,plan,root,_=successful_library_report(tmp_path);make_timeout(root)
    result=reconcile_attempts(plan,[root])
    assert result['library_passed']==0 and len(result['outstanding_tasks'])==2
    assert len(result['missing_tasks'])==1


def test_duplicate_copy_not_a_second_attempt(tmp_path):
    _,plan,root,_=successful_library_report(tmp_path)
    copied=tmp_path/'copy';shutil.copytree(root,copied)
    with pytest.raises(ValueError,match='Duplicate'):
        reconcile_attempts(plan,[root,copied])


def test_earlier_failed_log_stays_bound(tmp_path):
    _,plan,success,_=successful_library_report(tmp_path)
    prior=tmp_path/'prior';shutil.copytree(success,prior);make_timeout(prior)
    (prior/'logs/a.json').write_text('modified evidence')
    with pytest.raises(ValueError):reconcile_attempts(plan,[success,prior])


def test_foreign_retry_plan_is_rejected(tmp_path):
    _,plan,root,report=successful_library_report(tmp_path)
    report['plan_sha256']='0'*64;write(root/'worker.json',report)
    with pytest.raises(ValueError):reconcile_attempts(plan,[root])


def test_missing_workers_do_not_shrink_inventory(tmp_path):
    _,plan,_,_=successful_library_report(tmp_path)
    result=reconcile_attempts(plan,[])
    assert result['expected_tasks']==2 and len(result['missing_tasks'])==2
    assert result['complete'] is False and result['retained_attempts']==0
