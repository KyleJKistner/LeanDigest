from pathlib import Path
import json
import pytest
from proofreader.kernel import read_record, InvalidExport
from proofreader.kernel_pipeline import parse_stream, extraction_source, extract_kernel, PREFIX, INVENTORY, FAILURE
from proofreader.english import check_reading
from proofreader.render import load_document

ROOT=Path(__file__).parents[1]/'artifacts/v0.2'
@pytest.fixture
def record():return read_record(ROOT/'and_swap.kernel.json')
def stream(record):
    inv={'schema':INVENTORY,'declaration_kind':'theorem','names':[record['name']],
         'lean_version':record['lean_version'],'scope':'current-source-theorems'}
    return '\n'.join(PREFIX+json.dumps(x) for x in (record,inv))

def test_real_record_inventory(record):
    r=parse_stream(stream(record));assert r['complete'] and len(r['records'])==1

def test_info_message_transport(record):
    stdout='\n'.join('file:12:0: info: '+x for x in stream(record).splitlines())
    assert parse_stream(stdout)['complete']

def test_missing_inventory_and_missing_outcome(record):
    for source in (stream(record).splitlines()[0],stream(record).splitlines()[1]):
        with pytest.raises(InvalidExport):parse_stream(source)

def test_explicit_failed_export_retained(record):
    lines=stream(record).splitlines()
    lines[0]=PREFIX+json.dumps({'schema':FAILURE,'name':record['name'],'error':'step budget'})
    r=parse_stream('\n'.join(lines));assert not r['complete'] and len(r['failures'])==1

def test_duplicate_outcome_rejected(record):
    s=stream(record)
    with pytest.raises(InvalidExport):parse_stream(s+'\n'+s.splitlines()[0])

def test_unknown_schema_rejected(record):
    with pytest.raises(InvalidExport):parse_stream(stream(record)+'\n'+PREFIX+'{"schema":"made-up"}')

def test_module_import_injection():
    with pytest.raises(InvalidExport):extraction_source(module='A\n#eval bad')

def test_no_execution_without_consent(tmp_path):
    with pytest.raises(PermissionError):extract_kernel(tmp_path/'out',module='A',project=tmp_path)
    with pytest.raises(PermissionError):extract_kernel(tmp_path/'out',backend='axle',context='import Lean')
    assert not (tmp_path/'out').exists()

def test_mocked_remote_transport_pipeline(record,tmp_path,monkeypatch):
    # Test orchestration only. Export data are real; no real service call here.
    def fake(source,version,**kwargs):
        return {'okay':True,'content':source,'lean_messages':{'infos':stream(record).splitlines(),'errors':[]},
                'tool_messages':{},'info':{'environment':'lean-'+version}}
    monkeypatch.setattr('proofreader.kernel_pipeline.axle_request',fake)
    r=extract_kernel(tmp_path,backend='axle',context='import Lean',allow_remote=True)
    assert r['status']=='complete' and r['theorems_exported']==1 and r['theorems_checked']==0
    p=tmp_path/r['rows'][0]['directory']
    check_reading(record,load_document((p/'reading.json').read_bytes()))
    assert (p/'Check.lean').is_file() and (tmp_path/'index.html').is_file()

def test_failed_service_run_persists_expected_failure(tmp_path,monkeypatch):
    monkeypatch.setattr('proofreader.kernel_pipeline.axle_request',lambda *a,**kw:{'okay':False})
    r=extract_kernel(tmp_path,backend='axle',context='import Lean',allow_remote=True)
    assert r['status']=='failed'
    assert json.loads((tmp_path/'result.json').read_text())['status']=='failed'
