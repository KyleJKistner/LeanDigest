"""Real native acceptance over several proof shapes, not mocked service output."""
from pathlib import Path
import os
import shutil
import json
import pytest
from proofreader.narrative_batch import run_batch, aggregate
from proofreader.narrative import Snapshot, Narrative, check_reading
from proofreader.narrative_io import verify_certificates
from proofreader.render import load_document

REQUIRED = os.environ.get('PROOFREADER_REQUIRE_LEAN') == '1'
ROOT = Path(__file__).parents[1]
MODULES = ['ProofReader.Acceptance.' + m for m in ('Logic', 'Induction', 'Lists', 'Rejected')]


@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED, reason='Native batch integration requires Lean/Lake')
def test_native_batch_breadth_and_failure_accounting(tmp_path):
    if not shutil.which('lake'):
        pytest.fail('Required native batch integration must not skip')
    output = Path(os.environ.get('LEANGLISH_BATCH_ARTIFACTS', str(tmp_path/'batch'))).resolve()
    result = run_batch(MODULES, ROOT/'lean', output, trust_project=True, timeout=300)
    (output/'test-observation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    assert result['summary']['unknown_denominator_modules'] == [], result
    assert result['status']=='partial', result  # deliberately disallowed-axiom theorem
    by_name = {r['name']:r for m in result['modules'] for r in m['rows']}
    expected = {
        'BatchAcceptance.Logic.implication', 'BatchAcceptance.Logic.cases', 'BatchAcceptance.Logic.choose',
        'BatchAcceptance.Logic.proof_definition', 'BatchAcceptance.Logic.opaque_proof',
        'BatchAcceptance.Induction.addition_associates', 'BatchAcceptance.Induction.zero_adds',
        'BatchAcceptance.Induction.rec_overapplied',
        'BatchAcceptance.Lists.append_empty', 'BatchAcceptance.Lists.map_append',
        'BatchAcceptance.Rejected.must_fail', 'BatchAcceptance.Rejected.still_runs',
    }
    assert expected <= set(by_name), result
    # Generated auxiliary proof definitions, if any, must be reported too, not dropped.
    assert result['summary']['total_candidates'] == len(by_name)
    assert by_name['BatchAcceptance.Rejected.must_fail']['status']=='failed', result
    assert 'Disallowed axiom' in by_name['BatchAcceptance.Rejected.must_fail']['error']
    assert not by_name['BatchAcceptance.Rejected.must_fail']['kernel_checked']
    for name in expected-{'BatchAcceptance.Rejected.must_fail'}:
        row=by_name[name]
        assert row['kernel_checked'] and row['rendered'], (name,row)
        directory=(output/row['reader']).parent
        record=Snapshot.read(directory/'snapshot.json').record
        document=load_document((directory/'reading.json').read_bytes())
        check_reading(record,document)
        verify_certificates(record,json.loads((directory/'polynomial-certificates.json').read_text()))
    assert by_name['BatchAcceptance.Logic.proof_definition']['kind']=='proof-definition'
    assert by_name['BatchAcceptance.Logic.opaque_proof']['kind']=='opaque-proof'
    for name in ('BatchAcceptance.Induction.zero_adds','BatchAcceptance.Lists.map_append'):
        directory=(output/by_name[name]['reader']).parent
        prose=(directory/'proof.txt').read_text()
        assert 'induction' in prose, prose
        assert 'both sides' in prose, prose
    result2=aggregate([output/'batch.json'],output/'aggregate.json')
    assert result2['summary']['total_candidates']==len(by_name)
    assert result2['summary']['certified_english_proofs']==0

    path = output/by_name['BatchAcceptance.Induction.zero_adds']['reader']
    assert 'Apply Nat.succ to both sides' in (path.parent/'proof.txt').read_text()

    for name in ('BatchAcceptance.Logic.implication','BatchAcceptance.Logic.choose',
                 'BatchAcceptance.Logic.proof_definition','BatchAcceptance.Logic.opaque_proof'):
        assert by_name[name]['unexpanded_steps']==0, by_name[name]
    assert 'Apply the hypothesis' in ((output/by_name['BatchAcceptance.Logic.implication']['reader']).parent/'proof.txt').read_text()

    row=by_name['BatchAcceptance.Induction.rec_overapplied']
    assert row['unexpanded_steps'] == 0
    prose=((output/row['reader']).parent/'proof.txt').read_text()
    assert 'Proceed by induction on m' not in prose

    assert by_name['BatchAcceptance.Logic.cases']['unexpanded_steps']==0
    assert 'Specialize its object arguments to m' in prose
    assert 'Proceed by induction on n' in prose
