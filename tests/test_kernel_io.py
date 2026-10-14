from pathlib import Path
import json
import copy
import pytest
from proofreader.kernel import read_record, InvalidExport, Argument, replay_source
from proofreader.kernel_io import strict_json, judge_run, judge_axle, axiom_status, expected_markers, write_bundle, verify_native, verify_remote, axle_request, checked_source
from proofreader.english import check_reading, English
from proofreader.render import load_document
from proofreader.cli import main
from proofreader.model import walk_steps

ROOT=Path(__file__).resolve().parents[1]/'artifacts/v0.2'
@pytest.fixture
def record():return read_record(ROOT/'and_swap.kernel.json')

def good(record):
    return dict(okay=True, stdout='\n'.join(expected_markers(record)),errors=[],environment='lean-4.34.0')

def test_valid_receipt_is_not_english_certificate(record):
    r=judge_run(record,'source',**good(record))
    assert r['status']=='passed'
    assert r['all_judgements_kernel_checked']
    assert not r['english_formally_verified'] and not r['receipt_authenticated']

@pytest.mark.parametrize('change',[{'okay':False},{'okay':1},{'errors':['bad']},{'stdout':'PROOFREADER_REPLAY_OK'},{'source_preserved':False},{'environment':'lean-4.34.1'}])
def test_no_success_from_partial_or_mismatched_run(record,change):
    d={**good(record),**change};assert judge_run(record,'source',**d)['status']=='failed'

@pytest.mark.parametrize('text',['{"x":1,"x":2}','{"x":NaN}','{"x":Infinity}','{"a":{"x":1,"x":2}}'])
def test_strict_json(text):
    with pytest.raises(InvalidExport):strict_json(text)

def test_sorry_not_permitted_even_by_explicit_flag(record):
    record['axioms']=['sorryAx']
    assert not axiom_status(record,['sorryAx'])['acceptable']
    assert judge_run(record,'source',permitted_axioms=['sorryAx'],**good(record))['status']=='failed'

def test_custom_axioms_explicit_not_silent(record):
    record['axioms']=['User.assumedLemma']
    assert not axiom_status(record)['acceptable']
    assert axiom_status(record,['User.assumedLemma'])['acceptable']

def test_no_implicit_native_execution(record,tmp_path):
    with pytest.raises(PermissionError):verify_native(record,tmp_path,tmp_path/'out',module='X')
    assert not (tmp_path/'out').exists()

def test_no_implicit_remote_execution(record,tmp_path):
    with pytest.raises(PermissionError):verify_remote(record,tmp_path/'out',context='public')
    with pytest.raises(PermissionError):axle_request('public','4.34.0')
    assert not (tmp_path/'out').exists()

def test_bundle_and_regeneration(record,tmp_path):
    result=write_bundle(record,tmp_path)
    assert not result['english_formally_verified']
    check_reading(record,load_document((tmp_path/'reading.json').read_bytes()))
    assert 'Combining the two established facts' in (tmp_path/'reader.html').read_text()
    assert 'proofreaderClosedAt' in (tmp_path/'Check.lean').read_text()
    assert 'Toolchain version mismatch' in (tmp_path/'Check.lean').read_text()

def test_forged_receipt_for_other_proof(record,tmp_path):
    with pytest.raises(InvalidExport):write_bundle(record,tmp_path,receipt={'argument_sha256':'bad','status':'passed'})

def test_no_duplicate_rendered_step_ids(record):
    d=English(record).document();ids=[s.id for s in walk_steps(d.declarations[0].steps)]
    assert len(ids)==len(set(ids))
    assert d.declarations[0].steps[-1].supports

def test_cli_bundle(record,tmp_path,capsys):
    assert main(['kernel-read',str(ROOT/'and_swap.kernel.json'),'-o',str(tmp_path)])==0
    assert main(['check-reading',str(ROOT/'and_swap.kernel.json'),str(tmp_path/'reading.json')])==0
    d=json.loads((tmp_path/'reading.json').read_text());d['declarations'][0]['steps'][0]['text']='Wrong'
    (tmp_path/'reading.json').write_text(json.dumps(d))
    assert main(['check-reading',str(ROOT/'and_swap.kernel.json'),str(tmp_path/'reading.json')])==2

def test_axle_adjudication(record):
    r={'okay':True,'content':'source\n','lean_messages':{'infos':[f'file:1:0: info: {x}\n' for x in expected_markers(record)],'errors':[]},'tool_messages':{},'failed_declarations':[], 'info':{'environment':'lean-4.34.0','request_id':'test'}}
    assert judge_axle(record,'source',r)['status']=='passed'
    r['failed_declarations']=['lemma'];assert judge_axle(record,'source',r)['status']=='failed'

def test_context_source_prefix_preserved(record):
    text='import Lean\n-- exact original source\ntheorem t : True := .intro\n'
    s=checked_source(record,context=text)
    assert s.startswith(text+'open Lean Elab Command')
    assert 'PROOFREADER_PATHS_OK' in s

@pytest.mark.parametrize('result',[
    {'lean_messages':{'infos':'not-a-list'}},
    {'lean_messages':{'errors':[17]}},
    {'info':[]},
    {'failed_declarations':'not-a-list'}])
def test_malformed_remote_response_rejected(record,result):
    with pytest.raises(InvalidExport):judge_axle(record,'source',result)

def test_missing_remote_echo_fails_closed(record):
    r={'okay':True,'lean_messages':{'infos':list(expected_markers(record))},'info':{'environment':'lean-4.34.0'}}
    assert judge_axle(record,'source',r)['status']=='failed'

def test_conflicting_checker_context_rejected(record):
    with pytest.raises(InvalidExport,match='not both'):
        checked_source(record,imports=['Example'],context='import Lean\n')

def test_bundle_exposes_missing_original_context(record,tmp_path):
    result=write_bundle(record,tmp_path)
    assert not result['checker_context_supplied']
    assert '--context' in result['checker_setup_note']

def test_mixed_report_keeps_typed_and_source_denominators_separate(record):
    from proofreader.source import parse_source
    from proofreader.model import report
    d=English(record).document()
    src=parse_source('theorem t : True := by trivial')
    expected_source=report(src)['source_steps']
    d.declarations.extend(src.declarations)
    r=report(d)
    assert r['declaration_discovery']=='mixed-source-and-exported'
    assert r['source_steps']==expected_source
    assert r['typed_display_steps']>0
    assert r['display_steps']==r['source_steps']+r['typed_display_steps']

def test_current_checker_reproduces_exact_live_program(record):
    import hashlib
    observations=json.loads((ROOT/'live-path-tests.json').read_text())
    for label,row in observations['cases'].items():
        content=(ROOT/f'path-check-{label}.lean').read_bytes()
        assert hashlib.sha256(content).hexdigest()==row['source_sha256']
    valid=(ROOT/'path-check-valid.lean').read_text()
    context=valid[:valid.index('open Lean Elab Command')]
    assert checked_source(record,context=context)==valid
