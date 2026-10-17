"""Mandatory native CI integration; local absence is an explicit skip."""
from pathlib import Path
import os,shutil
import pytest
from proofreader.narrative_io import extract_narrative
from proofreader.narrative import Snapshot,Narrative,check_reading
from proofreader.render import load_document
REQUIRED=os.environ.get('PROOFREADER_REQUIRE_LEAN')=='1'
@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED,reason='Native narrative integration requires Lean/Lake; separate live AXLE observations are retained')
def test_native_narrative_pipeline_and_mutation(tmp_path):
    if not shutil.which('lake'):pytest.fail('Required Lean gate cannot skip')
    project=Path(__file__).parents[1]/'lean'
    context='import Lean\nnamespace NativeNarrative\ntheorem swap (P Q : Prop) : P ∧ Q → Q ∧ P := fun h => ⟨h.2,h.1⟩\nend NativeNarrative\n'
    result=extract_narrative('NativeNarrative.swap',tmp_path/'one',project=project,context=context,trust_project=True)
    assert result['status']=='passed',result
    r=Snapshot.read(tmp_path/'one/snapshot.json').record
    check_reading(r,load_document((tmp_path/'one/reading.json').read_bytes()))
    good=extract_narrative('NativeNarrative.swap',tmp_path/'two',project=project,context=context,trust_project=True,expected=r)
    assert good['status']=='passed',good
    # An invented theorem name cannot be 'verified' from a successful old receipt.
    r['frames'][0]['statement']='False';r['statement']='False'
    bad=extract_narrative('NativeNarrative.swap',tmp_path/'three',project=project,context=context,trust_project=True,expected=r)
    assert bad['status']=='failed'


@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED, reason='Native narrative name/type regressions require Lean/Lake')
@pytest.mark.parametrize('name', ['wrapped', 'shadowed', 'shadowedLet'])
def test_native_declared_type_and_stable_binder_names(tmp_path, name):
    """Regression for real corpus failures; do not relax snapshot validation."""
    if not shutil.which('lake'):
        pytest.fail('Required Lean gate cannot skip')
    context = """import Lean
namespace NarrativeBindingRegression
def Wrapped (P : Prop) : Prop := P → P
theorem wrapped (P : Prop) : Wrapped P := fun h => h
theorem shadowed (n : Nat) (h : n = n) : ∀ n : Nat, n = n :=
  fun n => Eq.refl n
theorem shadowedLet (n : Nat) (h : n = n) : n = n := by
  let n := n + 1
  have h : n = n := Eq.refl n
  exact Eq.refl _
end NarrativeBindingRegression
"""
    theorem = 'NarrativeBindingRegression.' + name
    output = tmp_path/name
    result = extract_narrative(theorem, output, project=Path(__file__).parents[1]/'lean',
                               context=context, trust_project=True)
    assert result['status'] == 'passed', result
    record = Snapshot.read(output/'snapshot.json').record
    assert record['statement'] == record['frames'][0]['statement']
    for frame in record['frames']:
        names = [x['name'] for x in frame['context']]
        assert len(names) == len(set(names)), frame
    if name == 'wrapped':
        assert 'Wrapped P' in record['statement']
    if name == 'shadowed':
        assert any(f.get('binder') == 'n_1' for f in record['frames'])
        assert all('✝' not in x['type'] for f in record['frames'] for x in f['context'])
    check_reading(record, load_document((output/'reading.json').read_bytes()))
    repeated = extract_narrative(theorem, tmp_path/(name+'-repeat'),
        project=Path(__file__).parents[1]/'lean', context=context,
        trust_project=True, expected=record)
    assert repeated['status'] == 'passed', repeated
