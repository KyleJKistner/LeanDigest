"""Synthetic adversarial accounting tests; not native OpenAI build observations."""
from copy import deepcopy
from pathlib import Path
import json
import os
import subprocess
import pytest
from proofreader.original_project import (TOOLCHAIN,make_plan,validate_plan,verify_sources,pins,
    audit_environment,file_hash,write,read,selection,reconcile,run_worker,digest,RUN_SCHEMA)


def fixture_project(tmp_path):
    p=tmp_path/'source';p.mkdir()
    (p/'lean-toolchain').write_text(TOOLCHAIN+'\n')
    (p/'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage Example\n@[default_target] lean_lib OAI\n')
    d=p/'.lake/packages/example';d.mkdir(parents=True)
    def git(*args):return subprocess.check_output(['git','-C',str(d),*args],text=True).strip()
    git('init','-q');git('config','user.name','Test');git('config','user.email','test@example.invalid')
    (d/'A.lean').write_text('def n := 0\n');(d/'B.lean').write_text('def b := 1\n')
    git('add','.');git('commit','-qm','Fixture')
    remote='https://github.com/example/example.git';git('remote','add','origin',remote)
    manifest={'packages':[{'name':'example','type':'git','rev':git('rev-parse','HEAD'),'url':remote}]}
    write(p/'lake-manifest.json',manifest)
    config={'challenge_module':'Challenge','solution_module':'Solution','theorem_names':['target'],
            'definition_names':[],'permitted_axioms':['propext']}
    write(p/'ComparatorChallenges/A.json',config)
    (p/'Challenge.lean').write_text('theorem target : True := by sorry\n')
    (p/'Solution.lean').write_text('theorem target : True := True.intro\n')
    inv=[{'path':'lean/'+f.relative_to(p).as_posix(),'sha256':file_hash(f)} for f in p.rglob('*') if f.is_file() and '.lake' not in f.parts]
    return p,inv,git


def test_plan_denominator_and_determinism(tmp_path):
    p,inv,_=fixture_project(tmp_path);a=make_plan(p,inv);b=make_plan(p,list(reversed(inv)))
    assert a==b and len(a['tasks'])==2 and len(a['dependencies'])==1
    assert selection(a,'comparator',0,1)[0]['config']=='ComparatorChallenges/A.json'
    assert sorted(x['id'] for i in range(4) for x in selection(a,'comparator',i,4))==['compare:ComparatorChallenges/A.json']


@pytest.mark.parametrize('mutation',['revision','lakefile','toolchain','config','extra','missing'])
def test_original_source_drift_rejected(tmp_path,mutation):
    p,inv,_=fixture_project(tmp_path);plan=make_plan(p,inv)
    if mutation=='revision':
        m=read(p/'lake-manifest.json');m['packages'][0]['rev']='0'*40;write(p/'lake-manifest.json',m)
    elif mutation=='lakefile':(p/'lakefile.lean').write_text('reduced project')
    elif mutation=='toolchain':(p/'lean-toolchain').write_text('leanprover/lean4:v4.35.0')
    elif mutation=='config':write(p/'ComparatorChallenges/A.json',{})
    elif mutation=='extra':(p/'New.lean').write_text('new source')
    else:(p/'Solution.lean').unlink()
    with pytest.raises(ValueError):audit_environment(p,plan)


def test_dependency_patch_is_exact_not_just_reversible(tmp_path):
    p,inv,git=fixture_project(tmp_path);d=p/'.lake/packages/example'
    (d/'A.lean').write_text('def n := 1\n')
    patch=git('diff')+'\n';(p/'patches').mkdir();(p/'patches/example-lean4341.patch').write_text(patch)
    inv.append({'path':'lean/patches/example-lean4341.patch','sha256':file_hash(p/'patches/example-lean4341.patch')})
    plan=make_plan(p,inv);r=audit_environment(p,plan)
    assert r['dependencies']['example']['patch_sha256']==file_hash(p/'patches/example-lean4341.patch')
    (d/'B.lean').write_text('def b := 2\n')
    git('apply','--check','--reverse',str(p/'patches/example-lean4341.patch'))
    with pytest.raises(ValueError,match='Unapproved'):audit_environment(p,plan)


def test_untracked_dependency_source_rejected(tmp_path):
    p,inv,_=fixture_project(tmp_path);plan=make_plan(p,inv)
    (p/'.lake/packages/example/Injected.lean').write_text('axiom false : False\n')
    with pytest.raises(ValueError,match='Unapproved'):audit_environment(p,plan)


def test_worker_requires_optin_and_fresh_output(tmp_path):
    p,inv,_=fixture_project(tmp_path);plan=make_plan(p,inv)
    with pytest.raises(PermissionError):run_worker(p,plan,tmp_path/'out',kind='library',shard=0,shards=1)
    out=tmp_path/'out';out.mkdir()
    with pytest.raises(ValueError):run_worker(p,plan,out,kind='library',shard=0,shards=1,trust_project=True)


def test_missing_targets_never_become_complete(tmp_path):
    p,inv,_=fixture_project(tmp_path);plan=make_plan(p,inv)
    r=reconcile(plan,[])
    assert r['expected_tasks']==2 and r['recorded_tasks']==0 and not r['complete']
    assert len(r['missing_tasks'])==2 and r['comparator_expected']==1


def successful_library_report(tmp_path):
    p,inv,_=fixture_project(tmp_path);plan=make_plan(p,inv);env=audit_environment(p,plan)
    out=tmp_path/'run';out.mkdir()
    log=out/'logs/a.json';write(log,{'command':['lake','build','OAI'],'status':'passed','exit_code':0,'reason':'','stdout':'Build completed successfully'})
    report={'schema':RUN_SCHEMA,'plan_sha256':plan['plan_sha256'],'kind':'library','shard':0,'shards':1,
            'expected_tasks':1,'status':'passed','complete':True,'environment_before':env,'environment_after':env,
            'targets':[{'id':'build:OAI','status':'passed','log':'logs/a.json','log_sha256':file_hash(log)}]}
    write(out/'worker.json',report);return p,plan,out,report


def test_build_and_comparator_gates_stay_separate(tmp_path):
    p,plan,out,r=successful_library_report(tmp_path);s=reconcile(plan,[out])
    assert s['full_project_build'] and not s['all_comparators_passed'] and not s['complete']


@pytest.mark.parametrize('mutation',['log','target','count','plan','audit','exit','marker'])
def test_forged_pass_rejected(tmp_path,mutation):
    p,plan,out,r=successful_library_report(tmp_path)
    if mutation=='log':(out/'logs/a.json').write_text('tampered')
    elif mutation=='target':r['targets'][0]['id']='build:Wrong'
    elif mutation=='count':r['expected_tasks']=0
    elif mutation=='plan':r['plan_sha256']='0'*64
    elif mutation=='audit':r['environment_after']=None
    else:
        log=read(out/'logs/a.json')
        if mutation=='exit':log['exit_code']=1
        else:log['command']=['echo','Build completed successfully']
        write(out/'logs/a.json',log);r['targets'][0]['log_sha256']=file_hash(out/'logs/a.json')
    write(out/'worker.json',r)
    with pytest.raises(ValueError):reconcile(plan,[out])


def test_duplicate_worker_rejected(tmp_path):
    p,plan,out,r=successful_library_report(tmp_path)
    with pytest.raises(ValueError,match='Duplicate'):reconcile(plan,[out,out])


@pytest.mark.parametrize('names',['duplicate','unsafe','unfixed'])
def test_invalid_dependencies_rejected(tmp_path,names):
    p,inv,_=fixture_project(tmp_path);m=read(p/'lake-manifest.json')
    if names=='duplicate':m['packages'].append(m['packages'][0])
    elif names=='unsafe':m['packages'][0]['name']='../outside'
    else:m['packages'][0]['rev']='main'
    with pytest.raises(ValueError):pins(m)


def test_dependency_patch_may_add_files(tmp_path):
    p,inv,git=fixture_project(tmp_path);d=p/'.lake/packages/example'
    (d/'Added.lean').write_text('def added := 2\n')
    git('add','-N','Added.lean');patch=git('diff')+'\n';git('reset','--','Added.lean')
    (p/'patches').mkdir();(p/'patches/example-lean4341.patch').write_text(patch)
    inv.append({'path':'lean/patches/example-lean4341.patch','sha256':file_hash(p/'patches/example-lean4341.patch')})
    plan=make_plan(p,inv);assert audit_environment(p,plan)['source_check']
