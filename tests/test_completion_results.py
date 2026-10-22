"""A successful archive download, build, and proof explanation are distinct."""
from copy import deepcopy
from pathlib import Path
import zipfile
import pytest
from proofreader.completion_results import check_collection, join_status, COLLECTION
from proofreader.original_project import digest, read, write, file_hash
from proofreader.original_status import SCHEMA, task_rows
from proofreader.original_attempts import reconcile_attempts
from test_original_project import successful_library_report

RUN = 123
HEAD = 'a' * 40


def archive(root, name, files):
    folder=root/name;folder.mkdir()
    for relative,value in files.items():write(folder/relative,value)
    path=root/(name+'.zip')
    with zipfile.ZipFile(path,'w') as z:
        for p in sorted(folder.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(folder).as_posix())
    return file_hash(path)


def collection_fixture(tmp_path, worker=False):
    root=tmp_path/'collection';root.mkdir()
    recovery={'recovery_plan_sha256':'b'*64, 'module_jobs':[],
              'library_jobs':[{'id':'library:OAI','library':'OAI','kind':'library'}]}
    artifacts=[];outcomes=[]
    def add(name, files):
        h=archive(root,name,files);ident=len(artifacts)+1
        artifacts.append({'id':ident,'name':name,'created_at':'2026-10-19T01:00:00Z',
            'digest':'sha256:'+h,'workflow_run':{'id':RUN,'head_sha':HEAD}})
        outcomes.append({'id':ident,'name':name,'sha256':h,'status':'retained',
            'run_id':RUN,'source_commit':HEAD})
    add('completion-recovery-plan',{'recovery.json':recovery})
    if worker:
        add('completion-result-OAI',{'identity.json':{
            'recovery_plan_sha256':'b'*64,'worker_id':'OAI','kind':'library',
            'target':'OAI','native_lean_verified':False},
            'final-status.json':{'status':'prebuild-incomplete'}})
    write(root/'run.json',{'id':RUN,'head_sha':HEAD,'path':'.github/workflows/completion-recovery.yml'})
    write(root/'frozen-artifacts.json',artifacts)
    write(root/'collection.json',{'schema':COLLECTION,'repository':'KyleJKistner/LeanDigest',
        'errors':[],'run_id':RUN,'source_commit':HEAD,'recovery_plan_sha256':'b'*64,
        'cutoff':'2026-10-19T02:00:00Z','outcomes':outcomes})
    return root,recovery


def test_seed_only_collection_keeps_all_workers_outstanding(tmp_path):
    root,recovery=collection_fixture(tmp_path)
    result=check_collection(root,recovery,expected_run=RUN,expected_head=HEAD)
    assert result['proof_roots']==[] and result['build_roots']==[]
    assert result['missing_workers']==['completion-result-OAI']


def test_retained_partial_build_does_not_become_a_library_receipt(tmp_path):
    root,recovery=collection_fixture(tmp_path,True)
    result=check_collection(root,recovery,expected_run=RUN,expected_head=HEAD)
    assert result['missing_workers']==[]
    assert result['build_roots']==[] and result['proof_roots']==[]
    assert result['workers'][0]['library_report_retained'] is False


@pytest.mark.parametrize('change',['run','head','plan','digest','missing-outcome','missing-seed'])
def test_recovery_acquisition_identity_is_required(tmp_path,change):
    root,recovery=collection_fixture(tmp_path)
    record=read(root/'collection.json')
    if change=='run':record['run_id']=RUN+1
    elif change=='head':record['source_commit']='c'*40
    elif change=='plan':record['recovery_plan_sha256']='c'*64
    elif change=='digest':record['outcomes'][0]['sha256']='c'*64
    elif change=='missing-outcome':record['outcomes']=[]
    else:
        record['outcomes']=[];write(root/'frozen-artifacts.json',[])
    write(root/'collection.json',record)
    with pytest.raises(ValueError):check_collection(root,recovery,expected_run=RUN,expected_head=HEAD)


def test_changed_extracted_bytes_cannot_keep_old_archive_binding(tmp_path):
    root,recovery=collection_fixture(tmp_path,True)
    write(root/'completion-result-OAI/final-status.json',{'status':'passed'})
    with pytest.raises(ValueError):check_collection(root,recovery,expected_run=RUN,expected_head=HEAD)


def join_fixture(tmp_path, baseline=False):
    _,plan,worker,report=successful_library_report(tmp_path)
    attempts=reconcile_attempts(plan,[worker],environment=report['environment_before'])
    _,tasks=task_rows(plan,[worker])
    base={'schema':SCHEMA,'original_plan_sha256':plan['plan_sha256'],
          'tasks':tasks,'theorems':[{'module':'Solution','name':'target','reading_available':baseline,
          'reading_id':'old' if baseline else None,'snapshot_sha256':'d'*64 if baseline else None,
          'reading_environment':'baseline-recorded-environment' if baseline else 'not-available',
          'configurations_passed':[],'configurations_not_passed':['A']}],
          'proof_summary':{'expected_theorem_targets':1,'baseline_readings':int(baseline),
          'original_environment_new_readings':0,'total_readings':int(baseline)},
          'collection':{'cutoff':'2026-10-18T00:00:00Z'},'build_summary':{}}
    base['status_sha256']=digest(base)
    summary={'expected_theorem_targets':1,'baseline_readings':int(baseline),
             'total_readings':1,'original_environment_new_readings':0 if baseline else 1}
    selected={('Solution','target'):{'receipt':{'snapshot_sha256':'d'*64},'row':{'id':'old' if baseline else 'new'}}}
    return base,attempts,summary,selected,{'cutoff':'2026-10-19T00:00:00Z'}


def test_available_reading_does_not_imply_comparison_or_complete_project(tmp_path):
    args=join_fixture(tmp_path)
    result=join_status(*args)
    assert result['proof_summary']['total_readings']==1
    assert result['build_summary']['comparator_passed']==0
    assert result['original_obligations_and_readings_complete'] is False
    assert result['theorems'][0]['reading_environment']=='full-original-dependency-audit'
    assert result['english_formally_verified'] is False
    assert result['status_sha256']==digest({k:v for k,v in result.items() if k!='status_sha256'})
    assert args[0]['theorems'][0]['reading_available'] is False


def test_baseline_scope_and_snapshot_remain_unchanged(tmp_path):
    result=join_status(*join_fixture(tmp_path,True))
    assert result['theorems'][0]['reading_environment']=='baseline-recorded-environment'
    assert result['completion']['new_readings']==0
    assert result['proof_summary']['baseline_readings']==1
    assert result['baseline_environment_upgraded'] is False


@pytest.mark.parametrize('change',['snapshot','missing-baseline','extra-theorem','false-count','changed-task-kind'])
def test_join_cannot_inflate_counts_or_rewrite_previous_evidence(tmp_path,change):
    base,attempts,summary,selected,collection=join_fixture(tmp_path,True)
    if change=='snapshot':selected[('Solution','target')]['receipt']['snapshot_sha256']='e'*64
    elif change=='missing-baseline':selected={};summary['total_readings']=0
    elif change=='extra-theorem':selected[('Other','fake')]={}
    elif change=='false-count':summary['total_readings']=2
    else:
        attempts['tasks'][0]['kind']='comparator'
        attempts['summary_sha256']=digest({k:v for k,v in attempts.items() if k!='summary_sha256'})
    with pytest.raises(ValueError):join_status(base,attempts,summary,selected,collection)
