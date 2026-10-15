"""This must actually run in Lean CI. Python/source tests cannot substitute for it."""
from pathlib import Path
import json
import os
import shutil
import pytest
from proofreader.lean import extract_module,run_bounded,driver_file
from proofreader.core import replay_source,make_name

REQUIRED=os.environ.get('PROOFREADER_REQUIRE_LEAN')=='1'

@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED,reason='Lean/Lake is not installed; real compile/export/replay integration remains unvalidated')
def test_real_lean_compile_export_replay_and_tamper_rejection(tmp_path):
    if not shutil.which('lake'):pytest.fail('Lean CI requires a working Lake executable; skipping is forbidden')
    project=Path(__file__).resolve().parents[1]/'lean'
    result=extract_module(project,'ProofReader.Smoke',tmp_path/'export',trust_project=True,timeout=300,replay=True)
    if result['status'] != 'exported':
        logs = '\n'.join(p.name + '\n' + p.read_text()[-12000:] for p in sorted((tmp_path/'export').glob('*.log')))
        pytest.fail(json.dumps(result, indent=2) + '\n' + logs)
    expected={'ProofReaderSmoke.implication_transitivity','ProofReaderSmoke.and_commute','ProofReaderSmoke.composition_injective'}
    assert {r['name'] for r in result['replays']}==expected
    assert all(r['passed'] for r in result['replays'])
    assert result['axiom_policy_passed']
    files=sorted((tmp_path/'export').glob('*.export.json'))
    record=json.loads(files[0].read_text())
    record['raw_term']={'tag':'const','name':make_name('True.intro'),'levels':[]}
    source=replay_source(record,'ProofReader.Smoke')
    with driver_file(project,source) as driver:
        outcome=run_bounded(['lake','env','lean',str(driver)],project,timeout=60)
    assert outcome.status!='passed' and 'PROOFREADER_REPLAY_OK' not in outcome.stdout.splitlines()
