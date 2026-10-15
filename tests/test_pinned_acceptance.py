"""Offline safety/accounting tests, not evidence of a native corpus build."""
import copy
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import pytest
from proofreader.core import replay_source

PATH = Path(__file__).parents[1] / 'scripts/check_pinned_openai.py'
spec = importlib.util.spec_from_file_location('pinned_acceptance', PATH)
pinned = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pinned)


def manifests():
    entries = [dict(name=n, type='git', rev=rev, inputRev='main',
                    url='https://github.com/example/'+n, subDir=None)
               for n, rev in [('mathlib', pinned.MATHLIB), ('batteries', 'a'*40)]]
    return {'version':'1.2.0','packages':entries}, {'packages':[{'name':'batteries'}]}


def test_exact_revisions_override_moving_input_branches():
    u,m=manifests();before=copy.deepcopy(u)
    result=pinned.dependency_manifest(u,m)
    assert u==before
    assert all(p['rev']==p['inputRev'] for p in result['packages'])
    assert [p['inherited'] for p in result['packages']]==[False,True]
    assert result['fixedToolchain']


@pytest.mark.parametrize('failure',['duplicate','missing','mutable','origin','subdir','name'])
def test_dependency_errors_do_not_resolve_or_silently_skip(failure):
    u,m=manifests()
    if failure=='duplicate':u['packages'].append(u['packages'][0])
    if failure=='missing':u['packages'].pop()
    if failure=='mutable':u['packages'][1]['rev']='main'
    if failure=='origin':u['packages'][1]['url']='https://other.example/data'
    if failure=='subdir':u['packages'][1]['subDir']='src'
    if failure=='name':m['packages'][0]['name']='../escape'
    with pytest.raises(ValueError):pinned.dependency_manifest(u,m)


def test_existing_source_is_not_overwritten(tmp_path):
    project=tmp_path/'project';project.mkdir();(project/'work').write_text('keep')
    with pytest.raises(ValueError):pinned.prepare(project,tmp_path/'out')
    assert (project/'work').read_text()=='keep'


def test_nested_output_is_rejected_before_network(tmp_path):
    with pytest.raises(ValueError,match='disjoint'):
        pinned.prepare(tmp_path,tmp_path/'output')


def test_git_blob_check_matches_known_empty_object():
    assert pinned.blob(b'')=='e69de29bb2d1d6434b8b29ae775ad8c2e48c5391'


@dataclass
class Run:
    status:str='passed'
    stderr:str=''
    stdout:str=''


def test_failed_targets_remain_in_denominator(monkeypatch,tmp_path):
    monkeypatch.setattr(pinned,'run_bounded',lambda *a,**k:Run())
    monkeypatch.setattr(pinned,'verify_checkout',lambda *a:[])
    monkeypatch.setattr(pinned,'extract_narrative',lambda *a,**k:{'status':'failed','errors':['unexpanded']})
    result=pinned.execute(tmp_path,tmp_path,{})
    assert result['status']=='partial'
    assert len(result['rows'])==result['expected_targets']==7
    assert result['targets_passed']==0
    assert all(r['status']=='failed' for r in result['rows'])
    assert not result['full_openai_project_built']
    assert not result['english_formally_verified']


def test_cache_failure_still_preserves_unrun_targets(monkeypatch,tmp_path):
    monkeypatch.setattr(pinned,'run_bounded',lambda *a,**k:Run('failed','cache missing'))
    result=pinned.execute(tmp_path,tmp_path,{})
    assert result['status']=='failed'
    assert result['expected_targets']==7 and result['targets_passed']==0
    assert all(r['status']=='not-run' for r in result['rows'])


def test_replay_marker_uses_generic_lift_not_command_only_lift(identity_export):
    source=replay_source(identity_export,'Example')
    assert 'liftM <| IO.println "PROOFREADER_REPLAY_OK"' in source
    assert 'liftIO' not in source
