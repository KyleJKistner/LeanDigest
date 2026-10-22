"""Failure accounting for the source-expression gate, not native proof evidence."""
import json
from zipfile import ZipFile
import hashlib
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import check_source_expressions as gate

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/check_source_expressions.py'


def invoke(*args):
    return subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True,
                          timeout=20,check=False)


def fake_lean(path,body):
    path.write_text(f'#!{sys.executable}\n'+body);path.chmod(0o755)
    return path


def test_execution_consent_required(tmp_path):
    p=tmp_path/'out';r=invoke('--output',p)
    assert r.returncode==2 and '--trust-project' in r.stderr
    assert not p.exists()


@pytest.mark.parametrize('file',[False,True])
def test_stale_evidence_cannot_be_replaced(tmp_path,file):
    p=tmp_path/'out'
    if file:p.write_text('old')
    else:p.mkdir();(p/'observation.json').write_text('old')
    r=invoke('--output',p,'--trust-project')
    assert r.returncode==2 and 'new or empty' in r.stderr
    assert (p if file else p/'observation.json').read_text()=='old'


def test_missing_compiler_records_failure(tmp_path):
    p=tmp_path/'out';r=invoke('--output',p,'--lean',tmp_path/'missing','--trust-project')
    assert r.returncode==1
    record=json.loads((p/'observation.json').read_text())
    assert record['status']=='failed' and 'unavailable' in record['error']
    assert record['commands']==[] and not record['english_certified']
    assert not record['fixed_openai_cohort_checked']


def test_wrong_compiler_version_records_failure(tmp_path):
    binary=fake_lean(tmp_path/'fake','print("Lean (version 4.33.0, test fixture)")\n')
    p=tmp_path/'out';r=invoke('--output',p,'--lean',binary,'--trust-project')
    assert r.returncode==1
    record=json.loads((p/'observation.json').read_text())
    assert 'Unexpected compiler version' in record['error']
    assert len(record['commands'])==1
    assert (p/'version.log').is_file()


def test_compilation_failure_is_not_counted_as_replay(tmp_path):
    binary=fake_lean(tmp_path/'fake','''import sys
if '--version' in sys.argv: print('Lean (version 4.34.1, fixture only)')
else:
    print('SIMULATED COMPILATION FAILURE')
    raise SystemExit(7)
''')
    p=tmp_path/'out';r=invoke('--output',p,'--lean',binary,'--trust-project')
    assert r.returncode==1
    record=json.loads((p/'observation.json').read_text())
    assert record['commands'][-1]['returncode']==7
    assert 'declarations' not in record
    assert 'SIMULATED' in (p/'compile-KernelExport.log').read_text()


def test_zero_exit_without_export_is_not_a_success(tmp_path):
    binary=fake_lean(tmp_path/'fake','print("Lean (version 4.34.1, fixture only)")\n')
    p=tmp_path/'out';r=invoke('--output',p,'--lean',binary,'--trust-project')
    assert r.returncode==1
    record=json.loads((p/'observation.json').read_text())
    assert record['status']=='failed' and 'Missing export completion' in record['error']
    assert 'kernel_judgements' not in record


def test_core_sample_is_explicit_not_the_openai_sample():
    assert len(gate.FIXTURES)==14 and len(gate.LIBRARY)==20
    assert len(set(gate.TARGETS))==34
    assert all(not n.startswith('OAI.') for n in gate.TARGETS)


def test_requests_are_not_taken_from_the_mutated_record():
    driver=gate.replay_driver('','requests.json')
    assert 'field req "name"' in driver and 'field req "paths"' in driver
    assert 'Replay.verify record target paths' in driver
    assert 'Snapshot source replay mismatch' in driver


def test_kernel_checker_forces_synchronous_checks_and_discards_failures():
    source=(ROOT/'lean/SourceExpressions.lean').read_text()
    assert 'withoutModifyingEnv <| withOptions' in source
    assert 'setBool `debug.skipKernelTC false' in source
    assert 'setBool `Elab.async false' in source
    assert 'ExprStructEq' in source
    assert '(allowNondep := true)' in source
    assert 'OAI.ComplexCancellation' not in source


def test_fixture_manifest_matches_source_and_bytes():
    base=ROOT/'tests/fixtures/source-expressions'
    with ZipFile(base/'records.zip') as z:
        assert z.namelist()==['records.json']
        records=json.loads(z.read('records.json'))
        manifest=json.loads(records['manifest.json'])
        data={name:records[name].encode('utf-8') for name in manifest['files']}
        assert set(records)==set(manifest['files'])|{'manifest.json'}
    assert manifest['kind']=='regression-fixtures-not-native-replay-evidence'
    assert manifest['fixture_source_sha256']==gate.file_digest(ROOT/'lean/SourceExpressionsFixtures.lean')
    assert set(manifest['files'])=={n+suffix for n in gate.FIXTURES for suffix in ('.json','.snapshot.json')}
    for name,sha in manifest['files'].items():assert hashlib.sha256(data[name]).hexdigest()==sha
