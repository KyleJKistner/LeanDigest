"""Transport/adjudication unit tests are mocked, not live Lean observations."""
from pathlib import Path
import copy,json
import pytest
import proofreader.narrative_io as io
from proofreader.kernel import InvalidExport
from proofreader.narrative import Snapshot,check_reading
from proofreader.render import load_document
from proofreader.model import canonical_json,digest
from proofreader.lean import RunResult
from proofreader.cli import main

ROOT=Path(__file__).parents[1]
@pytest.fixture
def record():return json.loads((ROOT/'artifacts/v0.3/bezout.narrative.json').read_text())


def response(record,source):
    return {'okay':True,'content':source,'failed_declarations':[],
       'lean_messages':{'errors':[],'infos':['-:1:0: info: PR_NARRATIVE:'+canonical_json(record)+'\n'],'warnings':[]},
       'tool_messages':{'errors':[],'infos':[],'warnings':[]},'info':{'environment':'lean-4.34.1','request_id':'UNIT-TEST-MOCK'}}


def test_reading_bundle_never_runs_tools(tmp_path,record,monkeypatch):
    def fail(*args,**kwargs):raise AssertionError('Unexpected execution')
    monkeypatch.setattr(io,'axle_request',fail);monkeypatch.setattr(io,'run_bounded',fail)
    result=io.write_bundle(record,tmp_path)
    assert result['polynomial_certificates_replayed']==16
    assert result['exported_frames_accounted_for']==86
    check_reading(record,load_document((tmp_path/'reading.json').read_bytes()))


@pytest.mark.parametrize('backend', ['native','axle'])
def test_execution_consent_before_artifacts_or_call(tmp_path,record,monkeypatch,backend):
    def fail(*a,**kw):raise AssertionError('Remote call before consent')
    monkeypatch.setattr(io,'axle_request',fail);monkeypatch.setattr(io,'run_bounded',fail)
    with pytest.raises(PermissionError):io.extract_narrative(record['theorem'],tmp_path/'new',context='import Lean',backend=backend)
    assert not (tmp_path/'new').exists()


def test_remote_extraction_and_reverification_contract(tmp_path,record,monkeypatch):
    calls=[]
    def request(source,version,**opts):
        calls.append((source,version,opts));return response(record,source)
    monkeypatch.setattr(io,'axle_request',request)
    result=io.extract_narrative(record['theorem'],tmp_path,version='4.34.1',context='import Lean',backend='axle',allow_remote=True,expected=record)
    assert result['status']=='passed' and result['snapshot_reextraction_matched']
    assert result['path_linkage_checked_in_lean']
    assert not result['receipt_authenticated'] and not result['english_formally_verified']
    assert calls[0][1]=='4.34.1' and calls[0][2]['allow_remote'] is True
    assert '#narrative "OAI.ComplexCancellation.BezoutFrame.exists_frame"' in calls[0][0]
    assert (tmp_path/'Context.lean').read_text()=='import Lean'


@pytest.mark.parametrize('field,value',[
    (('okay',),False), (('failed_declarations',),['sorryTheorem']),
    (('failed_declarations',),None), (('content',),'replaced imports'),
    (('info','environment'),'lean-4.34.0'),
    (('lean_messages','errors'),['type mismatch']),
    (('tool_messages','errors'),['incomplete proof']),
    (('lean_messages','infos'),['error quoting PR_NARRATIVE:{}']),
    (('lean_messages','infos'),[])
])
def test_response_failures_fail_closed(tmp_path,record,monkeypatch,field,value):
    def request(source,*a,**kw):
        r=response(record,source);ref=r
        for k in field[:-1]:ref=ref[k]
        ref[field[-1]]=value;return r
    monkeypatch.setattr(io,'axle_request',request)
    result=io.extract_narrative(record['theorem'],tmp_path,version='4.34.1',context='import Lean',backend='axle',allow_remote=True)
    assert result['status']=='failed'
    assert not (tmp_path/'reader.html').exists()
    assert not (tmp_path/'snapshot.json').exists()


def test_previous_success_not_left_on_failure(tmp_path,record,monkeypatch):
    io.write_bundle(record,tmp_path)
    monkeypatch.setattr(io,'axle_request',lambda *a,**kw: {'detail':'service not ready'})
    result=io.extract_narrative(record['theorem'],tmp_path,version='4.34.1',context='import Lean',backend='axle',allow_remote=True)
    assert result['status']=='failed'
    assert not (tmp_path/'reader.html').exists()
    assert json.loads((tmp_path/'receipt.json').read_text())['status']=='failed'


def test_changed_expected_snapshot_is_rejected_not_silently_replaced(tmp_path,record,monkeypatch):
    monkeypatch.setattr(io,'axle_request',lambda source,*a,**k:response(record,source))
    altered=copy.deepcopy(record);altered['frames'][6]['value']='0'
    result=io.extract_narrative(record['theorem'],tmp_path,version='4.34.1',context='import Lean',backend='axle',allow_remote=True,expected=altered)
    assert result['status']=='failed' and 'differs' in result['errors'][0]
    assert (tmp_path/'actual-snapshot.json').exists()
    assert not (tmp_path/'snapshot.json').exists()


def test_dual_records_rejected(record):
    line='PR_NARRATIVE:'+canonical_json(record)
    with pytest.raises(InvalidExport):io.parse_stream(line+'\n'+line,theorem=record['theorem'],version='4.34.1')


def test_wrong_theorem_version_rejected(record):
    line='PR_NARRATIVE:'+canonical_json(record)
    for theorem,version in [('Other.theorem','4.34.1'),(record['theorem'],'4.34.0')]:
        with pytest.raises(InvalidExport):io.parse_stream(line,theorem=theorem,version=version)


@pytest.mark.parametrize('module', ['Foo\nrun_elab do panic! "hi"','../Foo','Foo;Bar','Foo.'])
def test_module_name_injection_rejected(module):
    with pytest.raises(InvalidExport):io.extraction_source('T',version='4.34.1',module=module)


def test_theorem_string_is_escaped():
    text=io.extraction_source('a"\n#eval panic! "evil"',version='4.34.1',context='import Lean')
    assert '\n#eval' not in text and '\\n#eval' in text


def test_original_driver_is_preserved_verbatim():
    original=(ROOT/'artifacts/v0.3/bezout-4.34.1-valid.lean').read_text()
    generated=io.extraction_source('T',version='4.34.1',driver=original)
    assert generated.startswith(original)
    assert generated.count('namespace ProofReaderNarrative')==1
    assert 'exact Lean version mismatch' in generated


def test_mutually_exclusive_source_choices():
    with pytest.raises(InvalidExport):io.extraction_source('T',version='4.34.1',module='M',context='import Lean')
    with pytest.raises(InvalidExport):io.extraction_source('T',version='4.34.1')


def test_native_contract(tmp_path,record,monkeypatch):
    def run(command,cwd,**opts):
        driver=Path(command[-1]);assert driver.exists()
        return RunResult('passed',command,0,'PR_NARRATIVE:'+canonical_json(record),'',0.001)
    monkeypatch.setattr(io,'run_bounded',run)
    result=io.extract_narrative(record['theorem'],tmp_path/'out',version='4.34.1',context='import Lean',project=tmp_path,trust_project=True)
    assert result['status']=='passed'


def test_native_failure_and_timeout(tmp_path,record,monkeypatch):
    monkeypatch.setattr(io,'run_bounded',lambda *a,**kw:RunResult('timeout',[],None,'','timeout',1,'Timeout'))
    result=io.extract_narrative(record['theorem'],tmp_path/'out',version='4.34.1',context='import Lean',project=tmp_path,trust_project=True)
    assert result['status']=='failed'


def test_cli_offline_read_and_check(tmp_path,record):
    inp=tmp_path/'input.json';inp.write_text(canonical_json(record))
    out=tmp_path/'bundle'
    assert main(['narrative-read',str(inp),'-o',str(out)])==0
    assert main(['check-narrative',str(inp),str(out/'reading.json'),'--certificates',str(out/'polynomial-certificates.json')])==0
    assert main(['narrative-demo','-o',str(tmp_path/'demo.html')])==0
    assert (tmp_path/'demo.html').stat().st_size>10000


def test_release_sources_reproduce_observed_hashes():
    a=ROOT/'artifacts/v0.3'
    obs=json.loads((a/'live-4.34.1-observations.json').read_text())
    for name in ['valid','wrong_path','wrong_claim']:
        assert digest((a/f'bezout-4.34.1-{name}.lean').read_bytes())==obs[name]['source_sha256']
    snapshot=Snapshot.read(a/'bezout.narrative.json')
    assert snapshot.sha256==obs['valid']['record_sha256']
    # Freeze the exporter used by the historical observation. New exporters
    # must pass current native integration; old evidence is not reassigned.
    packaged=(a/'Narrative.lean').read_text();body=packaged[packaged.index('open Lean Meta Elab Command'):]
    exact=(a/'bezout-4.34.1-valid.lean').read_text()
    assert '\n'.join(x for x in body.splitlines() if x.strip()) in exact


def test_cli_execution_not_accidentally_enabled(tmp_path,record):
    path=tmp_path/'context.lean';path.write_text('import Lean')
    assert main(['extract-narrative',record['theorem'],'--context',str(path),'-o',str(tmp_path/'out'),'--backend','axle'])==2
    assert not (tmp_path/'out').exists()


def test_native_module_driver_path_does_not_replace_source(tmp_path,record,monkeypatch):
    project=tmp_path/'project';project.mkdir()
    stdout='PR_NARRATIVE:'+canonical_json(record)+'\n'
    def run(cmd,cwd,**kw):return RunResult('passed',cmd,0,stdout,'',.01)
    monkeypatch.setattr(io,'run_bounded',run)
    result=io.extract_narrative(record['theorem'],tmp_path/'out',module='Example',
                                project=project,trust_project=True,version='4.34.1')
    assert result['status']=='passed',result
    document=load_document((tmp_path/'out/reading.json').read_bytes())
    assert document.declarations[0].source=='import Example\n'


def test_current_narrative_exporter_has_no_packaged_drift():
    assert io.exporter_source()==(ROOT/'lean/Narrative.lean').read_text()
