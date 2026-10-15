"""Offline tests of acquisition/pinning boundaries; not corpus execution evidence."""
import base64
import json
from pathlib import Path
import tomllib
from unittest.mock import patch
import pytest
from proofreader.openai_acceptance import (PIN,MATHLIB,VERSION,SCOPE,blob,validate_plan,
    header_imports,acquire,dependency_pins,lake_config,github_file,run)

ROOT=Path(__file__).parents[1]

def plan():
    return json.loads((ROOT/'benchmarks/openai-slice.json').read_text())

def small_plan():
    p=plan();p['roots']=[{'module':'OAI.A','blob':blob(b'import OAI.B\ntheorem a : True := True.intro\n')},
                        {'module':'OAI.C','blob':blob(b'import Mathlib\ntheorem c : True := True.intro\n')}];return p

def test_frozen_plan():
    p=validate_plan(plan());assert len(p['roots'])==4
    assert p['roots'][-1]['blob']==blob((ROOT/'proofreader/data/bezout-original.lean').read_bytes())

@pytest.mark.parametrize('field,value',[('commit','main'),('mathlib_revision','latest'),('scope','whole-project'),
                                      ('lean_version','4.34.0'),('repository','attacker/repo')])
def test_wrong_pin_fails(field,value):
    p=plan();p[field]=value
    with pytest.raises(ValueError):validate_plan(p)

@pytest.mark.parametrize('roots',[None,[],[{'module':'OAI.X; import Evil','blob':'0'*40}],
    [{'module':'OAI.X','blob':'0'*40}]*2,[{'module':'OAI.X','blob':'branch'}]])
def test_bad_roots(roots):
    p=plan();p['roots']=roots
    with pytest.raises(ValueError):validate_plan(p)


def test_header_comment_string_and_multiple_imports():
    source='/-- import Fake --/\nmodule\npublic import Mathlib.Data.Nat.Basic OAI.Real\n/- comment\nimport FakeTwo\n-/\nimport Lean\nnamespace N\ndef text := "import OAI.Nope"\n'
    assert header_imports(source)==['Lean','Mathlib.Data.Nat.Basic','OAI.Real']

@pytest.mark.parametrize('source',['import\n  OAI.Hidden\n','import «Unexpected»\n','/- unfinished','import OAI.X; unsafeStuff'])
def test_unsupported_import_syntax_does_not_guess(source):
    with pytest.raises(ValueError):header_imports(source)


def test_acquisition_keeps_failed_root_and_exact_imports(tmp_path):
    project=tmp_path/'project';project.mkdir();out=tmp_path/'out';out.mkdir()
    a=b'import OAI.B\ntheorem a : True := True.intro\n'
    c=b'import Mathlib\ntheorem c : True := True.intro\n'
    sources={'lean/OAI/A.lean':a,'lean/OAI/C.lean':c}
    calls=[]
    def fetch(repo,rev,path):
        assert repo=='openai/math' and rev==PIN
        calls.append(path)
        if path not in sources:raise OSError('unavailable')
        return sources[path],blob(sources[path])
    result=acquire(small_plan(),project,out,fetch)
    assert [r['status'] for r in result['roots']]==['acquisition-failed','acquired']
    assert (project/'OAI/A.lean').read_bytes()==a
    assert (project/'OAI/C.lean').read_bytes()==c
    assert not result['original_imports_rewritten'] and len(calls)==3


def test_wrong_root_hash_retained_as_failure(tmp_path):
    project=tmp_path/'p';project.mkdir();out=tmp_path/'o';out.mkdir()
    result=acquire(small_plan(),project,out,lambda *a:(b'import Lean\n',blob(b'import Lean\n')))
    assert all(r['status']=='acquisition-failed' for r in result['roots'])


def test_import_cycle_is_failure_not_complete(tmp_path):
    project=tmp_path/'p';project.mkdir();out=tmp_path/'o';out.mkdir()
    p=small_plan();p['roots']=p['roots'][:1]
    a=b'import OAI.B\ntheorem a : True := True.intro\n';b=b'import OAI.A\n'
    def fetch(repo,rev,path):
        data=a if path=='lean/OAI/A.lean' else b;return data,blob(data)
    result=acquire(p,project,out,fetch)
    assert result['roots'][0]['status']=='acquisition-failed'
    assert 'Cyclic' in result['roots'][0]['error']


def manifests():
    def dep(n,rev):return {'name':n,'rev':rev,'type':'git','subDir':None,'url':'https://github.com/example/'+n+'.git'}
    return {'packages':[dep('mathlib',MATHLIB),dep('Child','a'*40)]},{'packages':[dep('Child','b'*40)]}


def test_slice_uses_upstream_overrides_not_child_default_revisions():
    up,ml=manifests();pins=dependency_pins(up,ml)
    assert next(p['rev'] for p in pins if p['name']=='Child')=='a'*40
    config=tomllib.loads(lake_config(pins))
    assert config['leanOptions']=={'autoImplicit':False}
    assert config['fixedToolchain'] is True
    assert {p['rev'] for p in config['require']}=={'a'*40,MATHLIB}


def test_missing_shared_pin_cannot_be_silently_resolved():
    up,ml=manifests();up['packages'].pop()
    with pytest.raises(ValueError,match='absent'):dependency_pins(up,ml)


@pytest.mark.parametrize('allow,trust',[(False,False),(True,False),(False,True)])
def test_no_download_or_write_without_both_consents(tmp_path,allow,trust):
    with patch('proofreader.openai_acceptance.urlopen',side_effect=AssertionError('network')):
        with pytest.raises(PermissionError):run(plan(),tmp_path/'p',tmp_path/'o',allow_download=allow,trust_project=trust)
    assert not (tmp_path/'p').exists() and not (tmp_path/'o').exists()


def test_existing_work_is_never_overwritten(tmp_path):
    p=tmp_path/'p';p.mkdir();(p/'sentinel').write_text('keep')
    with pytest.raises(ValueError,match='new empty'):run(plan(),p,tmp_path/'o',allow_download=True,trust_project=True)
    assert (p/'sentinel').read_text()=='keep'


def test_setup_failure_is_a_saved_unknown_denominator(tmp_path):
    with patch('proofreader.openai_acceptance.github_file',side_effect=OSError('not found')):
        r=run(plan(),tmp_path/'p',tmp_path/'o',allow_download=True,trust_project=True)
    assert r['status']=='failed' and r['summary']['total_candidates'] is None
    assert len(r['plan']['roots'])==4
    assert (tmp_path/'o/acceptance.json').exists()


def test_git_content_integrity_and_bounded_size():
    data=b'import Lean\n';obj={'type':'file','encoding':'base64','content':base64.b64encode(data).decode(),
                              'sha':blob(data),'size':len(data)}
    class Response:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,limit):return json.dumps(obj).encode()
    with patch('proofreader.openai_acceptance.urlopen',return_value=Response()):
        assert github_file('openai/math',PIN,'lean/Test.lean')==(data,blob(data))
        obj['sha']='0'*40
        with pytest.raises(ValueError,match='mismatch'):github_file('openai/math',PIN,'lean/Test.lean')
