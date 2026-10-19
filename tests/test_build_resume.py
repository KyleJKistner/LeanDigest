"""Build-cache tests: checkpoint availability is deliberately not proof success."""
from copy import deepcopy
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import shutil
import tarfile
from unittest.mock import patch
import pytest
from proofreader import build_resume as br
from proofreader.lean import RunResult
from proofreader.original_project import make_plan, audit_environment, read, write, file_hash, digest, TOOLCHAIN
from test_original_project import fixture_project


def setup(tmp_path):
    project, inventory, _ = fixture_project(tmp_path)
    plan = make_plan(project, inventory)
    env = audit_environment(project, plan)
    state = tmp_path/'state'
    br.initialize(project,plan,env,state,'OAI',trust_project=True)
    return project,plan,env,state


def added(project):
    for relative, body in [('.lake/build/lib/lean/OAI.olean',b'compiled-example'),
                            ('.lake/packages/example/.lake/build/lib/lean/A.olean',b'compiled-dependency')]:
        p=project/relative;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body)


@pytest.mark.parametrize('name',['../source.lean','.lake/build/../../Solution.lean',
    '.lake/packages/foreign/.lake/build/a','.lake/packages/example/A.lean',
    '/tmp/escape','.lake/build/x/../y','.lake/build//x','.lake/build\\x',
    '.lake/build/.git:config','lakefile.lean','.lake/build'])
def test_non_build_paths_rejected(name):
    assert not br.allowed_path(name,{'example':{}})


def test_checkpoint_optin_and_plan_scope(tmp_path):
    project,inventory,_=fixture_project(tmp_path);plan=make_plan(project,inventory);env=audit_environment(project,plan)
    with pytest.raises(PermissionError):br.initialize(project,plan,env,tmp_path/'state','OAI')
    with pytest.raises(ValueError,match='complete original project plan'):
        br.initialize(project,plan,env,tmp_path/'state','Foreign',trust_project=True)
    assert not (tmp_path/'state').exists()


def test_delta_roundtrip_does_not_create_proof_success(tmp_path):
    p,plan,env,state=setup(tmp_path)
    added(p);archive=tmp_path/'checkpoint.tar.gz'
    result=br.pack(p,plan,env,state,archive)
    assert result['changed_files']==2 and result['proof_verified'] is False
    for name in br.assets(p,plan['dependencies']):br.child(p,name).unlink()
    restored=br.restore(p,plan,env,state,archive,result['archive_sha256'],trust_project=True)
    assert restored['restored_files']==2
    assert restored['build_passed'] is False and restored['proof_verified'] is False
    assert (p/'.lake/build/lib/lean/OAI.olean').read_bytes()==b'compiled-example'
    assert audit_environment(p,plan)==env
    assert read(state/'state.json')['build_passed'] is False


def test_successful_round_always_runs_original_command(tmp_path):
    p,plan,env,state=setup(tmp_path)
    s=read(state/'state.json');s['build_passed']=True;write(state/'state.json',s)
    def run(command,cwd,**kwargs):
        assert command==['lake','build','OAI'] and cwd==p
        added(p)
        return RunResult('passed',command,0,'Build completed','',1.0)
    with patch.object(br,'run_bounded',side_effect=run) as call:
        r=br.run_round(p,plan,env,state,tmp_path/'round',trust_project=True,seconds=2)
    assert call.call_count==1 and r['status']=='passed' and r['proof_verified'] is False


def test_timeout_keeps_build_delta_but_not_success(tmp_path):
    p,plan,env,state=setup(tmp_path)
    def run(command,cwd,**kwargs):
        added(p)
        return RunResult('failed',command,-9,'partial','',2.0,'timeout')
    with patch.object(br,'run_bounded',side_effect=run):
        r=br.run_round(p,plan,env,state,tmp_path/'round',trust_project=True,seconds=2)
    assert r['status']=='timeout' and read(state/'state.json')['build_passed'] is False
    assert br.pack(p,plan,env,state,tmp_path/'partial.tar.gz')['changed_files']==2


@pytest.mark.parametrize('what',['plan','environment','baseline','target','source'])
def test_identity_or_source_drift_cannot_be_checkpointed(tmp_path,what):
    p,plan,env,state=setup(tmp_path);added(p)
    if what=='source':(p/'Solution.lean').write_text('changed source')
    else:
        s=read(state/'state.json')
        if what=='plan':s['plan_sha256']='0'*64
        elif what=='environment':s['environment_sha256']='0'*64
        elif what=='baseline':s['baseline']['.lake/build/new']={}
        else:s['target']='Unplanned'
        write(state/'state.json',s)
    with pytest.raises(ValueError):br.pack(p,plan,env,state,tmp_path/'bad.tar.gz')
    assert not (tmp_path/'bad.tar.gz').exists()


def mutate_archive(source,destination,change):
    with tarfile.open(source,'r:gz') as a:
        rows=[(m.name,a.extractfile(m).read()) for m in a.getmembers()]
    record=json.loads(rows[0][1]);change(record,rows)
    record['checkpoint_sha256']=digest({k:v for k,v in record.items() if k!='checkpoint_sha256'})
    rows[0]=('CHECKPOINT.json',json.dumps(record).encode())
    with tarfile.open(destination,'w:gz') as a:
        for name,body in rows:
            m=tarfile.TarInfo(name);m.size=len(body);a.addfile(m,io.BytesIO(body))


@pytest.mark.parametrize('mutation',['bytes','path','duplicate','missing','target'])
def test_rehashed_malicious_checkpoint_rejected_before_install(tmp_path,mutation):
    p,plan,env,state=setup(tmp_path);added(p);archive=tmp_path/'checkpoint.tar.gz'
    br.pack(p,plan,env,state,archive)
    for name in br.assets(p,plan['dependencies']):br.child(p,name).unlink()
    def change(record,rows):
        if mutation=='bytes':rows[1]=(rows[1][0],b'changed-olean')
        elif mutation=='path':
            old=rows[1][0];new='../Solution.lean';record['files'][new]=record['files'].pop(old);rows[1]=(new,rows[1][1])
        elif mutation=='duplicate':rows.append(rows[1])
        elif mutation=='missing':rows.pop()
        else:record['target']='Solution'
    changed=tmp_path/'tampered.tar.gz';mutate_archive(archive,changed,change)
    before=(p/'Solution.lean').read_bytes()
    with pytest.raises(ValueError):br.restore(p,plan,env,state,changed,file_hash(changed),trust_project=True)
    assert (p/'Solution.lean').read_bytes()==before and not br.assets(p,plan['dependencies'])


def test_wrong_archive_digest_and_restore_optin(tmp_path):
    p,plan,env,state=setup(tmp_path);a=tmp_path/'a.tar.gz';br.pack(p,plan,env,state,a)
    with pytest.raises(PermissionError):br.restore(p,plan,env,state,a,file_hash(a))
    with pytest.raises(ValueError,match='digest'):br.restore(p,plan,env,state,a,'0'*64,trust_project=True)


def test_symbolic_link_in_build_tree_rejected(tmp_path):
    p,plan,env,state=setup(tmp_path)
    b=p/'.lake/build';b.mkdir();(b/'escape').symlink_to(p/'Solution.lean')
    with pytest.raises(ValueError,match='symbolic link'):br.pack(p,plan,env,state,tmp_path/'a.tar.gz')


REQUIRED=os.environ.get('PROOFREADER_REQUIRE_LEAN')=='1'
@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED,reason='Native checkpoint integration requires Lean/Lake')
def test_native_checkpoint_roundtrip(tmp_path):
    if not shutil.which('lake'):pytest.fail('Required native checkpoint gate cannot skip')
    p=tmp_path/'native';p.mkdir()
    (p/'lean-toolchain').write_text(TOOLCHAIN+'\n')
    (p/'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage OAI\n@[default_target] lean_lib OAI\n')
    write(p/'lake-manifest.json',{'version':'1.2.0','packagesDir':'.lake/packages','packages':[],'name':'OAI','lakeDir':'.lake'})
    (p/'OAI.lean').write_text('theorem checked : True := True.intro\n')
    write(p/'ComparatorChallenges/A.json',{'challenge_module':'OAI','solution_module':'OAI','theorem_names':['checked']})
    inventory=[{'path':'lean/'+f.relative_to(p).as_posix(),'sha256':file_hash(f)} for f in p.rglob('*') if f.is_file()]
    plan=make_plan(p,inventory);env=audit_environment(p,plan);state=tmp_path/'state'
    br.initialize(p,plan,env,state,'OAI',trust_project=True)
    first=br.run_round(p,plan,env,state,tmp_path/'first',trust_project=True,seconds=90)
    assert first['status']=='passed'
    a=tmp_path/'native.tar.gz';info=br.pack(p,plan,env,state,a)
    assert info['changed_files']>0
    shutil.rmtree(p/'.lake/build')
    br.restore(p,plan,env,state,a,info['archive_sha256'],trust_project=True)
    assert read(state/'state.json')['build_passed'] is False
    second=br.run_round(p,plan,env,state,tmp_path/'second',trust_project=True,seconds=90)
    assert second['status']=='passed' and audit_environment(p,plan)==env
