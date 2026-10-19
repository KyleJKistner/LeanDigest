from copy import deepcopy
import pytest
from proofreader.original_project import digest
from proofreader.original_attempts import reconcile_attempts
from scripts.prepare_completion_recovery import recovery_plan
from test_original_project import successful_library_report


def inputs(tmp_path, available=False):
    _,plan,root,report=successful_library_report(tmp_path)
    env=report['environment_before']
    status={'original_plan_sha256':plan['plan_sha256'],
            'original_environment_sha256':env['environment_sha256'],
            'theorems':[{'module':'Solution','name':'target','reading_available':available,
                         'snapshot_sha256':'a'*64 if available else None}]}
    status['status_sha256']=digest(status)
    attempts=reconcile_attempts(plan,[root],environment=env)
    return plan,env,status,attempts


def test_pending_proof_and_comparison_share_one_module_build(tmp_path):
    result=recovery_plan(*inputs(tmp_path))
    assert result['expected_theorem_targets']==1
    assert result['remaining_theorem_targets']==1 and result['remaining_comparators']==1
    assert len(result['module_jobs'])==1 and result['library_jobs']==[]
    job=result['module_jobs'][0]
    assert job['module']=='Solution' and len(job['theorem_targets'])==1
    assert job['comparators']==['compare:ComparatorChallenges/A.json']
    assert result['compiled_cache_is_proof_evidence'] is False


def test_existing_reading_does_not_imply_original_comparator_acceptance(tmp_path):
    result=recovery_plan(*inputs(tmp_path,True))
    assert result['remaining_theorem_targets']==0 and result['prior_readings']==1
    assert result['remaining_comparators']==1
    assert result['module_jobs'][0]['proof_module_id'] is None
    assert result['all_original_work_complete'] is False


def test_missing_theorem_rejected_even_with_recomputed_digest(tmp_path):
    plan,env,status,attempts=inputs(tmp_path)
    status['theorems']=[]
    status['status_sha256']=digest({k:v for k,v in status.items() if k!='status_sha256'})
    with pytest.raises(ValueError,match='denominator'):recovery_plan(plan,env,status,attempts)


def test_unknown_reading_state_is_not_success(tmp_path):
    plan,env,status,attempts=inputs(tmp_path)
    status['theorems'][0]['reading_available']='passed'
    status['status_sha256']=digest({k:v for k,v in status.items() if k!='status_sha256'})
    with pytest.raises(ValueError,match='availability'):recovery_plan(plan,env,status,attempts)


def test_modified_attempt_summary_is_rejected(tmp_path):
    plan,env,status,attempts=inputs(tmp_path)
    attempts['comparator_passed']=1
    with pytest.raises(ValueError,match='binding'):recovery_plan(plan,env,status,attempts)
