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
