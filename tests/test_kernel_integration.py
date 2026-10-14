"""Mandatory live tests in native CI; no mock can satisfy this job."""
from pathlib import Path
import json,os,shutil,re
import pytest
from proofreader.kernel_pipeline import extract_kernel
from proofreader.kernel import read_record, replay_source, Argument
from proofreader.lean import driver_file, run_bounded

REQUIRED=os.environ.get('PROOFREADER_REQUIRE_LEAN')=='1'
@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED,reason='Native v2 pipeline requires Lean/Lake; remote observations are recorded separately')
def test_native_v2_full_module_and_independent_claim_checks(tmp_path):
    if not shutil.which('lake'):pytest.fail('Required native Lean job cannot skip')
    project=Path(__file__).parents[1]/'lean'
    result=extract_kernel(tmp_path,module='ProofReader.Smoke',project=project,trust_project=True,verify=True,timeout=300)
    assert result['status']=='complete',result
    assert result['theorems_expected']==3 and result['theorems_checked']==3
    row=next(x for x in result['rows'] if x['name'].endswith('.and_commute'))
    record=read_record(tmp_path/row['directory']/'argument.json')
    source=replay_source(record,imports=['ProofReader.Smoke'])
    # A forced wrong root proof cannot pass the independent AST check.
    source=re.sub(r'(proofreaderEraseMetadata originalValue == )e\d+',r'\1(Lean.mkConst `True.intro)',source)
    with driver_file(project,source) as f:
        run=run_bounded(['lake','env','lean',str(f)],project,timeout=120)
    assert run.status!='passed'
    assert 'PROOFREADER_JUDGEMENTS_OK' not in run.stdout
