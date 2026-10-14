import json
from pathlib import Path
import sys
import pytest
from proofreader.lean import *


def test_explicit_consent_required(tmp_path):
    with pytest.raises(PermissionError):extract_module(tmp_path,'Example',tmp_path/'out')


def test_child_timeout_is_reported(tmp_path):
    r=run_bounded([sys.executable,'-c','import time; time.sleep(5)'],tmp_path,timeout=.1)
    assert r.status=='failed' and r.reason=='timeout'


def test_missing_executable_is_not_success(tmp_path):
    r=run_bounded(['not-a-real-proofreader-executable-82734'],tmp_path)
    assert r.status=='unavailable'


def test_output_overflow_fails(tmp_path):
    r=run_bounded([sys.executable,'-c','print("a"*50000)'],tmp_path,max_output=1000)
    assert r.status=='failed' and r.reason=='output budget exceeded'
    assert len(r.stdout)<=1000


def test_nonzero_exit_fails(tmp_path):
    assert run_bounded([sys.executable,'-c','raise SystemExit(3)'],tmp_path).status=='failed'


def test_stream_missing_inventory_fails(identity_export):
    with pytest.raises(ValueError):parse_export_stream(PREFIX+json.dumps(identity_export))


def test_stream_reconciles_inventory(identity_export):
    inv={'schema':'proofreader.module-inventory/v1','module':'Example','declarations':['Example.identity']}
    s=PREFIX+json.dumps(identity_export)+'\n'+PREFIX+json.dumps(inv)
    assert parse_export_stream(s)['complete']
    inv['declarations'].append('Example.missing')
    with pytest.raises(ValueError):parse_export_stream(PREFIX+json.dumps(identity_export)+'\n'+PREFIX+json.dumps(inv))


def test_stream_failure_stays_visible():
    inv={'schema':'proofreader.module-inventory/v1','module':'Example','declarations':['Example.failed']}
    fail={'schema':'proofreader.export-failure/v1','name':'Example.failed','reason':'budget'}
    r=parse_export_stream(PREFIX+json.dumps(fail)+'\n'+PREFIX+json.dumps(inv))
    assert not r['complete'] and r['failures']


def test_duplicate_records_rejected(identity_export):
    inv={'schema':'proofreader.module-inventory/v1','declarations':['Example.identity']}
    with pytest.raises(ValueError):parse_export_stream('\n'.join(PREFIX+json.dumps(x) for x in [identity_export,identity_export,inv]))


def test_driver_does_not_modify_imported_file():
    generated=export_driver('OAI.Analysis.Mahler.MainTheorem')
    assert 'import OAI.Analysis.Mahler.MainTheorem' in generated
    assert '#proofreader_export_module "OAI.Analysis.Mahler.MainTheorem"' in generated


def test_fingerprint_changes_only_relevant_source(tmp_path):
    (tmp_path/'Test.lean').write_text('a')
    a=source_fingerprint(tmp_path)
    (tmp_path/'notes.txt').write_text('a')
    assert source_fingerprint(tmp_path)==a
    (tmp_path/'Test.lean').write_text('b')
    assert source_fingerprint(tmp_path)!=a
