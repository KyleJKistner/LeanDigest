"""Native regression for bound names inside older hypothesis types."""
from pathlib import Path
import os,shutil
import pytest
from proofreader.narrative_io import extract_narrative
from proofreader.narrative import Snapshot,check_reading
from proofreader.render import load_document
REQUIRED=os.environ.get('PROOFREADER_REQUIRE_LEAN')=='1'


@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED, reason='Frozen contextual pretty-printing requires Lean/Lake')
@pytest.mark.parametrize('name', ['boundNames', 'boundLocalApplication'])
def test_native_bound_names_inside_earlier_hypotheses_remain_stable(tmp_path, name):
    if not shutil.which('lake'): pytest.fail('Required Lean gate cannot skip')
    context = """import Lean
namespace FrozenContextRegression
theorem boundNames (F : (Nat → Nat → Nat) → Prop)
    (h : F (fun x x_1 => x)) : ∀ (x_1 : Nat), F (fun x x_1 => x) :=
  fun x_1 => h
theorem boundLocalApplication (F : (Nat → Nat → Nat) → Prop)
    (h : ∀ (k : Nat), F (fun x x_1 => x)) : ∀ (x_1 : Nat), F (fun x x_1 => x) :=
  fun x_1 => h x_1
end FrozenContextRegression
"""
    project=Path(__file__).parents[1]/'lean'
    theorem='FrozenContextRegression.'+name
    out=tmp_path/name
    result=extract_narrative(theorem,out,project=project,context=context,trust_project=True)
    assert result['status']=='passed',result
    snapshot=Snapshot.read(out/'snapshot.json')
    hypotheses=[next(c['type'] for c in f['context'] if c['name']=='h')
                for f in snapshot.frames if any(c['name']=='h' for c in f['context'])]
    assert hypotheses and len(set(hypotheses))==1
    assert any(f.get('binder')=='x_1' for f in snapshot.frames)
    if name=='boundLocalApplication':
        frames=[f for f in snapshot.frames if f['role']=='local-application']
        assert frames and all(f['domain']==hypotheses[0] for f in frames)
    check_reading(snapshot.record,load_document((out/'reading.json').read_bytes()))
    again=extract_narrative(theorem,tmp_path/(name+'-again'),project=project,context=context,
                           trust_project=True,expected=snapshot.record)
    assert again['status']=='passed',again
