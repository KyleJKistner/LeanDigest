from pathlib import Path
import json
import pytest
from proofreader.corpus import *


def manifest(root,files,complete=False):
    (root/MANIFEST).write_text(json.dumps({'schema':'proofreader.corpus/v1','scope':'test-fixture','tree_complete':complete,'commit':OPENAI_COMMIT,'files':files}))


def test_pinned_real_samples_match_blob_hashes():
    root=Path(__file__).resolve().parents[1]/'examples/openai'
    m=local_manifest(root)
    assert len(m['files'])==6
    for e in m['files']:
        assert git_blob_sha((root/e['path']).read_bytes())==e['git_blob_sha']


def test_real_sample_benchmark_not_full_corpus(tmp_path):
    root=Path(__file__).resolve().parents[1]/'examples/openai'
    result=benchmark_sources(root,tmp_path/'out')
    assert result['source_files_indexed']==6
    assert result['declaration_candidates']==9
    assert result['checked_english_proofs']==0
    assert not coverage_gate(result,'english')[0]
    assert not coverage_gate(result,'inventory')[0]
    assert (tmp_path/'out/index.html').is_file()


def test_missing_expected_file_not_dropped(tmp_path):
    manifest(tmp_path,[{'path':'lean/OAI/Missing.lean','git_blob_sha':'0'*40}],True)
    r=benchmark_sources(tmp_path,tmp_path/'out')
    assert r['expected_lean_files']==1 and r['failed_or_missing_files']==1
    assert not coverage_gate(r)[0]


def test_changed_source_fails_pinned_integrity(tmp_path):
    (tmp_path/'Test.lean').write_text('theorem t : True := by trivial')
    manifest(tmp_path,[{'path':'Test.lean','git_blob_sha':'0'*40}],True)
    r=benchmark_sources(tmp_path,tmp_path/'out')
    assert r['rows'][0]['status']=='failed'


def test_empty_dataset_cannot_pass_gate():
    assert not coverage_gate({'expected_lean_files':0,'inventory_complete':True,'failed_or_missing_files':0,'source_files_indexed':0})[0]


def test_full_source_inventory_not_english_coverage():
    r={'expected_lean_files':1,'inventory_complete':True,'failed_or_missing_files':0,'source_files_indexed':1}
    assert coverage_gate(r,'inventory')[0]
    assert not coverage_gate(r,'replay')[0]
    assert not coverage_gate(r,'english')[0]


@pytest.mark.parametrize('path',['../evil','/evil','a/../../evil','a\\evil','a\0b'])
def test_unsafe_corpus_paths_rejected(tmp_path,path):
    with pytest.raises(ValueError):safe_destination(tmp_path,path)


def test_symlink_not_followed(tmp_path):
    (tmp_path/'real').mkdir();(tmp_path/'alias').symlink_to(tmp_path/'real',target_is_directory=True)
    with pytest.raises(ValueError):safe_destination(tmp_path,'alias/x.lean')


def test_truncated_remote_tree_walks_subtrees():
    class Mock(GitHubClient):
        def __init__(self):self.calls=[]
        def json(self,endpoint):
            self.calls.append(endpoint)
            if '?recursive' in endpoint:return {'truncated':True,'tree':[]}
            if endpoint.endswith('/'+OPENAI_COMMIT):return {'truncated':False,'tree':[{'path':'lean','type':'tree','sha':'1'*40}]}
            return {'truncated':False,'tree':[{'path':'X.lean','type':'blob','sha':'2'*40}]}
    c=Mock();rows=c.tree(OPENAI_COMMIT)
    assert any(r['path']=='lean/X.lean' for r in rows)
    assert len(c.calls)==4


def test_truncated_nonrecursive_tree_fails():
    class Mock(GitHubClient):
        def json(self,endpoint):return {'truncated':True,'tree':[]}
    with pytest.raises(AcquisitionError):Mock().tree(OPENAI_COMMIT)


def test_requires_pinned_commit():
    with pytest.raises(ValueError):GitHubClient().tree('main')


def test_duplicate_manifest_paths_fail(tmp_path):
    manifest(tmp_path,[{'path':'A.lean'},{'path':'A.lean'}])
    with pytest.raises(ValueError):local_manifest(tmp_path)


def test_corpus_extract_requires_consent(tmp_path):
    with pytest.raises(PermissionError):extract_corpus(tmp_path,tmp_path/'out')


def test_cannot_assert_english_success_by_setting_a_boolean():
    r={'expected_lean_files':1,'inventory_complete':True,'failed_or_missing_files':0,'source_files_indexed':1,'whole_corpus_english_coverage':True}
    assert not coverage_gate(r,'english')[0]


def test_missing_shard_prevents_full_replay(tmp_path):
    source=b'theorem t : True := by trivial\n'
    f=tmp_path/'lean/OAI/A.lean';f.parent.mkdir(parents=True);f.write_bytes(source)
    manifest(tmp_path,[{'path':'lean/OAI/A.lean','git_blob_sha':git_blob_sha(source)}],True)
    report=tmp_path/'empty-shard.json'
    report.write_text(json.dumps({'schema':'proofreader.extraction-benchmark/v1','commit':OPENAI_COMMIT,'shard_attempted':0,'rows':[]}))
    r=aggregate_extractions(tmp_path,[report],tmp_path/'out')
    assert r['failed_or_missing_modules']==1
    assert r['environment_discovered_theorems'] is None
    assert not coverage_gate(r,'replay')[0]


def test_synthetic_complete_replay_accounting(tmp_path):
    # Unit-test ledger accounting only: this fabricated log is not real proof evidence.
    source=b'theorem t : True := by trivial\n'
    f=tmp_path/'lean/OAI/A.lean';f.parent.mkdir(parents=True);f.write_bytes(source)
    manifest(tmp_path,[{'path':'lean/OAI/A.lean','git_blob_sha':git_blob_sha(source)}],True)
    report=tmp_path/'shard.json'
    row={'module':'OAI.A','status':'exported','inventory':{'declarations':['OAI.t']},'declarations':[{'name':'OAI.t','kind':'theorem','axioms':[]}],'replays':[{'name':'OAI.t','passed':True}]}
    report.write_text(json.dumps({'schema':'proofreader.extraction-benchmark/v1','commit':OPENAI_COMMIT,'shard_attempted':1,'rows':[row]}))
    r=aggregate_extractions(tmp_path,[report],tmp_path/'out')
    assert coverage_gate(r,'replay')[0]
    assert not coverage_gate(r,'english')[0]
    r=aggregate_extractions(tmp_path,[report,report],tmp_path/'duplicate-out')
    assert not coverage_gate(r,'replay')[0]


def test_complete_child_subtree_avoids_per_directory_fetch():
    class Mock(GitHubClient):
        def __init__(self):self.calls=[]
        def json(self,endpoint):
            self.calls.append(endpoint)
            if endpoint.endswith(OPENAI_COMMIT+'?recursive=1'):return {'truncated':True,'tree':[]}
            if endpoint.endswith(OPENAI_COMMIT):return {'truncated':False,'tree':[{'path':'lean','type':'tree','sha':'1'*40}]}
            assert endpoint.endswith('?recursive=1')
            return {'truncated':False,'tree':[{'path':'A/B.lean','type':'blob','sha':'2'*40}]}
    c=Mock();r=c.tree(OPENAI_COMMIT)
    assert any(x['path']=='lean/A/B.lean' for x in r) and len(c.calls)==3

def test_large_corpus_ledger_does_not_retain_proof_book(tmp_path):
    files=[]
    for i in range(501):
        name=f'File{i}.lean';data=f'theorem t{i} : True := by trivial\n'.encode()
        (tmp_path/name).write_bytes(data)
        files.append({'path':name,'git_blob_sha':git_blob_sha(data)})
    manifest(tmp_path,files,True)
    r=benchmark_sources(tmp_path,tmp_path/'out')
    assert r['memory_mode']=='ledger-only' and r['source_files_indexed']==501
    assert r['declaration_candidates']==501
    assert not r['reading_documents_emitted']
    assert not json.loads((tmp_path/'out/document.json').read_text())['declarations']
    assert coverage_gate(r,'inventory')[0] and not coverage_gate(r,'english')[0]
