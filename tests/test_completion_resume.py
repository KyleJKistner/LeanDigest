"""A restored compilation cache never supplies mathematical acceptance."""
from copy import deepcopy
import pytest
from proofreader.original_project import read,write
from proofreader.completion_results import check_collection,check_resume_parent,RESUME_WORKFLOW
from test_completion_results import collection_fixture,RUN,HEAD


def parent_fixture(tmp_path):
    directory=tmp_path/'worker';directory.mkdir()
    recovery={'original_plan_sha256':'p'*64,'environment_sha256':'e'*64}
    target='OAI.Analysis.NuclearUltrapower.Main';ident='142c3d0f555a25666bb36dd1'
    record={'proof_acceptance_from_checkpoint':False,
        'previous_worker':{'id':118274980446,'run_id':39315174445,
                           'status':'completed','conclusion':'failure'},
        'parent_checkpoint':{'schema':'leanglish.original-checkpoint-cold-restore/v1',
            'status':'passed','target':target,'plan_sha256':recovery['original_plan_sha256'],
            'environment_sha256':recovery['environment_sha256'],'proof_verified':False,
            'original_source_audit_passed':True,'exact_resulting_build_inventory_verified':True,
            'checkpoint_sha256':'87f52a446dfcdf14117bc864299782ccda1d81945483b5b6c3037cb8b76d8eb9',
            'checkpoint_acquisition':{'artifact_id':12217614568,'run_id':39315174445,
                'source_commit':'4f9c1e823dd65023cfa7d8b9afe5e08390b8d2ad',
                'archive_sha256':'f0cb3658f6edbffc2e62cd8f538ea9a7529a0e4cbe4e27286241030441003523'}}}
    write(directory/'resume.json',record)
    return directory,recovery,target,ident,record


def test_known_stopped_worker_can_resume_but_checkpoint_is_not_a_proof(tmp_path):
    directory,recovery,target,ident,record=parent_fixture(tmp_path)
    result=check_resume_parent(directory,recovery,target,ident)
    assert result==record['parent_checkpoint']['checkpoint_sha256']
    assert record['parent_checkpoint']['proof_verified'] is False


@pytest.mark.parametrize('change',['running','already-successful','wrong-run','wrong-checkpoint',
                                  'source-drift','environment-drift','cache-is-proof','wrong-worker'])
def test_changed_parent_is_not_a_valid_continuation(tmp_path,change):
    directory,recovery,target,ident,record=parent_fixture(tmp_path)
    if change=='running':record['previous_worker']['status']='in_progress'
    elif change=='already-successful':record['previous_worker']['conclusion']='success'
    elif change=='wrong-run':record['previous_worker']['run_id']=1
    elif change=='wrong-checkpoint':record['parent_checkpoint']['checkpoint_sha256']='0'*64
    elif change=='source-drift':record['parent_checkpoint']['plan_sha256']='0'*64
    elif change=='environment-drift':record['parent_checkpoint']['environment_sha256']='0'*64
    elif change=='cache-is-proof':record['parent_checkpoint']['proof_verified']=True
    else:ident='unplanned'
    write(directory/'resume.json',record)
    with pytest.raises(ValueError):check_resume_parent(directory,recovery,target,ident)


def test_resumed_workflow_must_be_explicit_not_relabelled_as_original_run(tmp_path):
    root,recovery=collection_fixture(tmp_path)
    run=read(root/'run.json');run['path']=RESUME_WORKFLOW;write(root/'run.json',run)
    with pytest.raises(ValueError):check_collection(root,recovery,expected_run=RUN,expected_head=HEAD)
    result=check_collection(root,recovery,expected_run=RUN,expected_head=HEAD,expected_workflow=RESUME_WORKFLOW)
    assert result['proof_roots']==[] and result['build_roots']==[]
    assert result['collection']['workflow_path']==RESUME_WORKFLOW


def test_arbitrary_workflow_is_not_a_supported_verifier(tmp_path):
    root,recovery=collection_fixture(tmp_path)
    with pytest.raises(ValueError):
        check_collection(root,recovery,expected_run=RUN,expected_head=HEAD,
                         expected_workflow='.github/workflows/unrelated.yml')
