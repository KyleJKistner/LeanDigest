from copy import deepcopy
import pytest
from proofreader.stopped_recovery import select
from proofreader.original_project import digest
from test_completion_recovery_plan import inputs
from scripts.prepare_completion_recovery import recovery_plan


def case(tmp_path):
    plan,env,status,attempts=inputs(tmp_path)
    recovery=recovery_plan(plan,env,status,attempts)
    ident=recovery['module_jobs'][0]['id']
    jobs=[{'id':99,'run_id':10,'name':'modules ('+ident+') / recover',
           'status':'completed','conclusion':'failure'}]
    return plan,env,recovery,jobs,[ident],set()


def run(args):
    return select(*args,run_id=10,source_commit='a'*40)


def test_stopped_job_is_retried_with_exact_original_targets(tmp_path):
    args=case(tmp_path);result=run(args)
    assert len(result['selected'])==1
    assert result['selected'][0]['theorem_targets']==args[2]['module_jobs'][0]['theorem_targets']
    assert result['selected'][0]['comparators']==['compare:ComparatorChallenges/A.json']
    assert result['proof_acceptance_established'] is False
    assert result['source_or_dependency_changes_permitted'] is False
    assert result['selection_sha256']==digest({k:v for k,v in result.items() if k!='selection_sha256'})


@pytest.mark.parametrize('field,value',[('status','in_progress'),('conclusion','success'),('run_id',11)])
def test_active_or_other_execution_is_not_duplicated(tmp_path,field,value):
    args=case(tmp_path);args[3][0][field]=value
    with pytest.raises(ValueError):run(args)


def test_existing_proof_wrapper_is_not_silently_replaced(tmp_path):
    args=list(case(tmp_path));args[-1]={args[4][0]}
    result=run(args)
    assert result['selected']==[]
    assert result['excluded'][0]['reason']=='retained-proof-worker-must-be-reconciled'


def test_unplanned_or_duplicate_modules_are_rejected(tmp_path):
    args=list(case(tmp_path));requested=list(args[4])
    args[4]=['not-in-plan']
    with pytest.raises(ValueError):run(args)
    args[4]=requested*2
    with pytest.raises(ValueError):run(args)


def test_ambiguous_prior_job_is_rejected(tmp_path):
    args=list(case(tmp_path));args[3].append(deepcopy(args[3][0]))
    with pytest.raises(ValueError):run(args)
