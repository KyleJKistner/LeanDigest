import pytest
from proofreader.original_project import read,write
from proofreader.completion_sets import gather
from proofreader.completion_results import ORIGINAL_WORKFLOW
from test_completion_results import collection_fixture,RUN,HEAD


def request(root,run=RUN):
    return {'root':str(root),'run_id':run,'source_commit':HEAD,'workflow_path':ORIGINAL_WORKFLOW}


def second_execution(root,run):
    r=read(root/'run.json');r['id']=run;write(root/'run.json',r)
    r=read(root/'collection.json');r['run_id']=run
    for outcome in r['outcomes']:outcome['run_id']=run
    write(root/'collection.json',r)
    a=read(root/'frozen-artifacts.json')
    for item in a:item['workflow_run']['id']=run
    write(root/'frozen-artifacts.json',a)


def test_distinct_attempts_keep_their_identities_and_do_not_create_acceptance(tmp_path):
    a=tmp_path/'a';a.mkdir();b=tmp_path/'b';b.mkdir()
    root,recovery=collection_fixture(a)
    other,_=collection_fixture(b,worker=True)
    second_execution(other,RUN+1)
    result=gather(recovery,[request(root),request(other,RUN+1)])
    assert result['missing_workers']==[]
    assert result['build_roots']==[] and result['proof_roots']==[]
    assert [e['run_id'] for e in result['collection']['executions']]==[RUN,RUN+1]
    assert result['workers'][0]['run_id']==RUN+1
    assert result['collection']['proof_acceptance_from_collection'] is False


def test_missing_workers_remain_missing_across_seed_only_snapshots(tmp_path):
    a=tmp_path/'a';a.mkdir();b=tmp_path/'b';b.mkdir()
    root,recovery=collection_fixture(a)
    other,_=collection_fixture(b)
    second_execution(other,RUN+1)
    result=gather(recovery,[request(root),request(other,RUN+1)])
    assert result['missing_workers']==['completion-result-OAI']


def test_two_cutoffs_of_one_execution_cannot_double_count_results(tmp_path):
    a=tmp_path/'a';a.mkdir();b=tmp_path/'b';b.mkdir()
    root,recovery=collection_fixture(a)
    other,_=collection_fixture(b)
    with pytest.raises(ValueError,match='same execution'):
        gather(recovery,[request(root),request(other)])


def test_execution_expectations_cannot_be_inferred_from_an_arbitrary_directory(tmp_path):
    root,recovery=collection_fixture(tmp_path)
    with pytest.raises(ValueError):gather(recovery,[{'root':str(root)}])
    with pytest.raises(ValueError):gather(recovery,[])
    wrong=request(root,RUN+1)
    with pytest.raises(ValueError):gather(recovery,[wrong])
