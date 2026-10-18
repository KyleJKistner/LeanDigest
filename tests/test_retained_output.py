from copy import deepcopy
import pytest
from proofreader import narrative_io as io
from proofreader.kernel import InvalidExport


def test_context_and_output_budgets_are_distinct():
    assert io.MAX_BYTES==16_000_000
    assert io.MAX_OUTPUT_BYTES==64_000_000


def test_local_string_sharing_preserves_values_without_mutable_aliases():
    a=''.join(['large',' repeated',' local hypothesis']*100)
    b=a.encode().decode()
    assert a==b and a is not b
    original={'frames':[{'context':[{'type':a}]},{'context':[{'type':b}]}]}
    result=io._share_strings(original)
    assert result==original
    x=result['frames'][0]['context'][0];y=result['frames'][1]['context'][0]
    assert x is not y and x['type'] is y['type']
    x['type']='changed'
    assert y['type']==a and original['frames'][0]['context'][0]['type']==a


def test_output_byte_budget_still_rejects_before_parsing(monkeypatch):
    monkeypatch.setattr(io,'MAX_OUTPUT_BYTES',32)
    def forbidden_parse(*args,**kwargs):pytest.fail('Oversized input reached JSON parser')
    monkeypatch.setattr(io,'strict_json',forbidden_parse)
    with pytest.raises(InvalidExport,match='output budget'):
        io.parse_stream('α'*17,theorem='x',version='4.34.1')


def saved_run(tmp_path):
    from test_original_project import fixture_project
    from proofreader.original_project import make_plan,audit_environment,write,file_hash
    from pathlib import Path
    project,inventory,_=fixture_project(tmp_path)
    plan=make_plan(project,inventory);env=audit_environment(project,plan)
    worker=tmp_path/'saved';entry=worker/'reading/targets/fixture';entry.mkdir(parents=True)
    source=io.extraction_source('target',version='4.34.1',module='Solution',max_heartbeats=2000000)
    (entry/'Extract.lean').write_text(source);(entry/'stdout.txt').write_text('synthetic unparsed output')
    write(entry/'run.json',{'status':'passed','exit_code':0,'reason':'','stdout':'synthetic unparsed output',
                          'command':['lake','env','lean','/tmp/Driver.lean']})
    write(entry/'receipt.json',{'backend':'native','status':'failed','errors':['Exporter output budget'],
          'theorem':'target','module':'Solution','lean_version':'4.34.1','source_sha256':file_hash(entry/'Extract.lean'),
          'execution_limits':{'max_heartbeats':2000000}})
    target={'id':'fixture','module':'Solution','name':'target','status':'extraction-failed',
            'errors':['Exporter output budget'],'source_sha256':file_hash(project/'Solution.lean')}
    write(worker/'reading/proofs.json',{'targets':[target]})
    write(worker/'original-proof-worker.json',{'environment_before':env,'environment_after':env,
            'proof_report_sha256':file_hash(worker/'reading/proofs.json')})
    return project,plan,env,worker,entry,target


@pytest.mark.parametrize('change',['source','exit','stdout','driver','driver-hash','environment','wrong-error','wrong-target','run-command'])
def test_recovery_is_not_a_way_to_bypass_failed_native_execution(tmp_path,change):
    from proofreader.retained_output import recover
    from proofreader.original_project import read,write,file_hash
    project,plan,env,worker,entry,target=saved_run(tmp_path)
    if change=='source':(project/'Solution.lean').write_text('changed')
    elif change in ('exit','stdout','run-command'):
        r=read(entry/'run.json')
        if change=='exit':r['exit_code']=1
        elif change=='stdout':r['stdout']='different output'
        else:r['command']=['echo','fake success']
        write(entry/'run.json',r)
    elif change in ('driver','driver-hash'):
        (entry/'Extract.lean').write_text('different driver')
        if change=='driver-hash':
            r=read(entry/'receipt.json');r['source_sha256']=file_hash(entry/'Extract.lean');write(entry/'receipt.json',r)
    elif change=='environment':
        r=read(worker/'original-proof-worker.json');r['environment_after']=None;write(worker/'original-proof-worker.json',r)
    elif change=='wrong-error':
        r=read(entry/'receipt.json');r['errors']=['kernel rejected'];write(entry/'receipt.json',r)
    else:target['name']='another_theorem'
    with pytest.raises(ValueError):recover(project,plan,env,worker,target,tmp_path/'new')
    assert not (tmp_path/'new').exists()
