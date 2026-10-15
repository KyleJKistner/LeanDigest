"""Malformed input is an error, never a traceback or a completed denominator."""
from pathlib import Path
import json
from copy import deepcopy
import pytest
from proofreader import narrative_batch as batch
from proofreader.model import canonical_json,digest
from proofreader.cli import main
from proofreader.openai_acceptance import run as run_slice


def report():
    plan={'modules':['Demo'],'version':'4.34.1','max_declarations':1,
          'exporter_sha256':'a'*64,'batch_exporter_sha256':'b'*64}
    modules=[{'module':'Demo','status':'complete','expected':1,'excluded':[],
              'candidate_inventory':[{'name':'Demo.good','kind':'theorem'}],
              'rows':[{'name':'Demo.good','kind':'theorem','exported':True,'kernel_checked':True,
                       'path_checked':True,'rendered':True,'unexpanded_steps':0}]}]
    return {'schema':batch.REPORT,'plan':plan,'plan_sha256':digest(canonical_json(plan)),
            'project_source_fingerprint':'c'*64,'modules':modules,'shard_count':1,'shard_index':0,
            'summary':batch.summarize(modules)}


@pytest.mark.parametrize('mutation',[
    lambda r:r['plan'].update(modules=[['not','hashable']]),
    lambda r:r['plan'].update(version=[]),
    lambda r:r['modules'].__setitem__(0,[]),
    lambda r:r['modules'][0].update(module={}),
    lambda r:r['modules'][0]['rows'].__setitem__(0,False),
    lambda r:r['modules'][0]['rows'][0].update(name=[]),
])
def test_malformed_report_becomes_value_error(mutation):
    r=report();mutation(r);r['plan_sha256']=digest(canonical_json(r['plan']))
    with pytest.raises(ValueError):batch._validate_report(r)


def test_report_input_limit(tmp_path,monkeypatch):
    p=tmp_path/'report.json';p.write_text(json.dumps(report()))
    monkeypatch.setattr(batch,'MAX_OUTPUT',16)
    with pytest.raises(ValueError,match='budget'):batch.aggregate([p],tmp_path/'out.json')
    assert not (tmp_path/'out.json').exists()


@pytest.mark.parametrize('content',[[],None,{'modules':['Demo'],'execute':'unexpected'}])
def test_cli_plan_nonobject_is_rejected_before_execution(tmp_path,content,capsys):
    p=tmp_path/'plan.json';p.write_text(json.dumps(content))
    assert main(['batch-narrative','--plan',str(p),'--project',str(tmp_path),'-o',str(tmp_path/'out')])==2
    assert not (tmp_path/'out').exists()


def test_slice_output_cannot_contain_its_work_directory(tmp_path):
    plan=json.loads((Path(__file__).parents[1]/'benchmarks/openai-slice.json').read_text())
    with pytest.raises(ValueError,match='outside'):
        run_slice(plan,tmp_path/'results/work',tmp_path/'results',allow_download=True,trust_project=True)
    assert not (tmp_path/'results').exists()
