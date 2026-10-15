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


@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED,reason='Imported declaration regression requires native Lean')
def test_native_imported_narrative_preserves_declared_type_and_fresh_names(tmp_path):
    if not shutil.which('lake'):pytest.fail('Required Lean gate cannot skip')
    project=Path(__file__).parents[1]/'lean'
    result=extract_narrative('Nat.add_comm',tmp_path/'first',project=project,
                             module='ProofReader.Smoke',trust_project=True)
    assert result['status']=='passed',result
    snapshot=Snapshot.read(tmp_path/'first/snapshot.json')
    assert snapshot.frames[0]['statement']==snapshot.record['statement']
    for frame in snapshot.frames:
        names=[entry['name'] for entry in frame['context']]
        assert len(names)==len(set(names))
        assert all('_@' not in name for name in names)
    doc=load_document((tmp_path/'first/reading.json').read_bytes())
    assert doc.declarations[0].source=='import ProofReader.Smoke\n'
    check_reading(snapshot.record,doc)
    repeated=extract_narrative('Nat.add_comm',tmp_path/'repeat',project=project,
                              module='ProofReader.Smoke',trust_project=True,expected=snapshot.record)
    assert repeated['status']=='passed',repeated
