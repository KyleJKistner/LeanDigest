"""No invented proof passes: campaign fixtures contain only missing/failed work."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from proofreader.original_project import digest,write
from proofreader.proof_campaign import (make_campaign,validate_campaign,from_artifacts,
                                       run_module,reconcile,check_environment,WORKER)
from test_original_project import fixture_project
from proofreader.original_project import make_plan,audit_environment


def fixture_campaign(tmp_path):
    project,inventory,_=fixture_project(tmp_path)
    plan=make_plan(project,inventory)
    env=audit_environment(project,plan)
    campaign=make_campaign(plan,env,[])
    return project,plan,env,campaign


def test_complete_denominator_before_any_worker(tmp_path):
    project,plan,env,campaign=fixture_campaign(tmp_path)
    assert campaign['expected_theorem_targets']==1
    assert campaign['baseline_readings']==0 and campaign['selected_theorems']==1
    assert campaign['module_tasks'][0]['targets']==[{'module':'Solution','name':'target'}]
    assert not campaign['baseline_environment_upgraded']


@pytest.mark.parametrize('edit',[
    lambda x:x.update(selected_theorems=0),
    lambda x:x.update(expected_theorem_targets=0),
    lambda x:x.update(original_plan_sha256='0'*64),
    lambda x:x.update(original_environment_sha256='0'*64),
    lambda x:x.update(module_tasks=[]),
    lambda x:x.update(baseline_environment_upgraded=True),
    lambda x:x['module_tasks'][0].update(targets=[]),
    lambda x:x.update(campaign_sha256='0'*64),
])
def test_campaign_tampering_rejected(tmp_path,edit):
    project,plan,env,campaign=fixture_campaign(tmp_path)
    edit(campaign)
    with pytest.raises(ValueError):validate_campaign(plan,env,campaign)


@pytest.mark.parametrize('baseline',[
    [{'module':'Wrong','name':'target','snapshot_sha256':'a'*64}],
    [{'module':'Solution','name':'target','snapshot_sha256':'a'*64}]*2,
    [{'module':'Solution','name':'target'}],
    [{'module':'Solution','name':'target','snapshot_sha256':'a'*64,'complete':True}],
])
def test_foreign_or_ambiguous_baseline_rejected(tmp_path,baseline):
    project,plan,env,campaign=fixture_campaign(tmp_path)
    with pytest.raises(ValueError):make_campaign(plan,env,baseline)


def test_failed_worker_requires_no_lean_installation(tmp_path):
    project,plan,env,campaign=fixture_campaign(tmp_path)
    with pytest.raises(PermissionError):
        run_module(project,plan,env,campaign,campaign['module_tasks'][0]['id'],tmp_path/'out')
    with pytest.raises(ValueError,match='Unknown'):
        run_module(project,plan,env,campaign,'foreign',tmp_path/'out',trust_project=True)
    (tmp_path/'out').mkdir()
    with pytest.raises(ValueError,match='fresh'):
        run_module(project,plan,env,campaign,campaign['module_tasks'][0]['id'],tmp_path/'out',trust_project=True)


@pytest.mark.parametrize('edit',[
    lambda e:e.update(source_check=None),
    lambda e:e['source_check'].update(checked_source_files=0),
    lambda e:e['dependencies']['example'].update(rev='0'*40),
    lambda e:e['dependencies']['example'].update(patch_sha256='a'*64),
    lambda e:e.update(dependencies={}),
    lambda e:e.update(environment_sha256='0'*64),
])
def test_incomplete_original_environment_rejected(tmp_path,edit):
    project,plan,env,campaign=fixture_campaign(tmp_path)
    edit(env)
    with pytest.raises(ValueError):check_environment(plan,env)


def test_planning_from_records_rejects_unrecognized_comparison_name(tmp_path):
    project,plan,env,campaign=fixture_campaign(tmp_path)
    # Existing catalog validator has its own original naming constraint.
    with pytest.raises(ValueError,match='Configuration path/name mismatch'):
        from_artifacts(project,plan,env,[])


def test_missing_worker_not_a_reading(tmp_path,monkeypatch):
    project,plan,env,campaign=fixture_campaign(tmp_path)
    monkeypatch.setattr('proofreader.proof_campaign.config_inventory',lambda _: {})
    report,roots=reconcile(project,plan,env,campaign,[],[])
    assert not roots and report['total_readings']==0
    assert report['theorems_without_reading']==1 and not report['all_theorems_have_readings']
    assert report['statuses']=={'worker-artifact-missing':1}
    assert not report['full_project_build'] and not report['all_comparators_passed']


def test_failed_worker_is_retained_not_omitted(tmp_path,monkeypatch):
    project,plan,env,campaign=fixture_campaign(tmp_path)
    monkeypatch.setattr('proofreader.proof_campaign.config_inventory',lambda _: {})
    task=campaign['module_tasks'][0];root=tmp_path/'worker'
    write(root/'original-proof-worker.json',{'schema':WORKER,'campaign_sha256':campaign['campaign_sha256'],
        'module_id':task['id'],'module':task['module'],'expected_targets':task['targets'],
        'status':'failed','validated_readings':0,'complete':False,'error':'Synthetic unavailable executable'})
    report,roots=reconcile(project,plan,env,campaign,[],[root])
    assert report['module_workers_retained']==1 and not report['missing_workers']
    assert report['statuses']=={'worker-failed':1} and not roots
    with pytest.raises(ValueError,match='Duplicate'):
        reconcile(project,plan,env,campaign,[],[root,root])


def test_failed_worker_cannot_claim_a_pass(tmp_path,monkeypatch):
    project,plan,env,campaign=fixture_campaign(tmp_path)
    monkeypatch.setattr('proofreader.proof_campaign.config_inventory',lambda _: {})
    task=campaign['module_tasks'][0];root=tmp_path/'worker'
    write(root/'original-proof-worker.json',{'schema':WORKER,'campaign_sha256':campaign['campaign_sha256'],
        'module_id':task['id'],'module':task['module'],'expected_targets':task['targets'],
        'status':'running','validated_readings':1,'complete':False})
    with pytest.raises(ValueError,match='Unfinished'):
        reconcile(project,plan,env,campaign,[],[root])
