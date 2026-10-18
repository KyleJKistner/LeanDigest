"""Synthetic selector/receipt controls. These are not live nanoda observations."""
from copy import deepcopy
from pathlib import Path
import pytest
from proofreader.original_project import make_plan,read,write,file_hash,selection,audit_environment,reconcile,RUN_SCHEMA
from test_original_project import fixture_project


def nano_report(tmp_path):
    project,inventory,_=fixture_project(tmp_path)
    path=project/'ComparatorChallenges/A.json';cfg=read(path);cfg['enable_nanoda']=True;write(path,cfg)
    for row in inventory:
        if row['path']=='lean/ComparatorChallenges/A.json':row['sha256']=file_hash(path)
    plan=make_plan(project,inventory);env=audit_environment(project,plan);out=tmp_path/'observed';out.mkdir()
    task=selection(plan,'comparator',0,1)[0]
    log={'command':['lake','env','/tmp/verified/comparator',task['config']],
         'status':'passed','exit_code':0,'reason':'',
         'stdout':'nanoda kernel accepts the solution\nLean default kernel accepts the solution\nYour solution is okay!\n'}
    write(out/'log.json',log)
    report={'schema':RUN_SCHEMA,'plan_sha256':plan['plan_sha256'],'kind':'comparator','shard':0,'shards':1,
            'only':[task['id']],'expected_tasks':1,'status':'passed','complete':True,
            'environment_before':env,'environment_after':env,
            'toolchain':{'passed':True,'nanoda_commit':'a'*40,'binaries':{'nanoda_bin':'b'*64},
                'tests':{'nanoda-positive':{'passed':True},'nanoda-disallowed-axiom':{'passed':True}}},
            'targets':[{'id':task['id'],'status':'passed','log':'log.json','log_sha256':file_hash(out/'log.json')}]}
    write(out/'worker.json',report)
    return plan,out,report,log


def test_explicit_subset_does_not_shrink_original_plan(tmp_path):
    plan,root,_,_=nano_report(tmp_path)
    summary=reconcile(plan,[root])
    assert summary['expected_tasks']==2 and summary['comparator_passed']==1
    assert not summary['complete'] and not summary['full_project_build']


@pytest.mark.parametrize('field',['positive','negative','binary','commit','marker'])
def test_required_external_kernel_cannot_be_omitted(tmp_path,field):
    plan,root,r,log=nano_report(tmp_path)
    if field=='positive':r['toolchain']['tests']['nanoda-positive']['passed']=False
    elif field=='negative':r['toolchain']['tests']['nanoda-disallowed-axiom']['passed']=False
    elif field=='binary':r['toolchain']['binaries']['nanoda_bin']='invalid'
    elif field=='commit':r['toolchain']['nanoda_commit']=None
    else:
        log['stdout']=log['stdout'].replace('nanoda kernel accepts the solution','Running nanoda')
        write(root/'log.json',log);r['targets'][0]['log_sha256']=file_hash(root/'log.json')
    write(root/'worker.json',r)
    with pytest.raises(ValueError,match='external-kernel'):reconcile(plan,[root])


@pytest.mark.parametrize('only',[[],['made-up'],['compare:ComparatorChallenges/A.json']*2,'compare:ComparatorChallenges/A.json'])
def test_retry_selector_is_not_a_freeform_denominator(tmp_path,only):
    plan,_,_,_=nano_report(tmp_path)
    with pytest.raises(ValueError,match='retry targets'):selection(plan,'comparator',0,1,only)


def test_subset_must_belong_to_selected_shard(tmp_path):
    plan,_,_,_=nano_report(tmp_path)
    with pytest.raises(ValueError):selection(plan,'comparator',1,2,['compare:ComparatorChallenges/A.json'])
