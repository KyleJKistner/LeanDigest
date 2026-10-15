"""Offline file-ledger tests. No test below acquires or builds the OpenAI corpus."""
import hashlib
import importlib.util
from pathlib import Path
import pytest

path=Path(__file__).parents[1]/'scripts/index_full_openai.py'
spec=importlib.util.spec_from_file_location('full_source_index',path)
index=importlib.util.module_from_spec(spec);spec.loader.exec_module(index)


def entry(data=b'theorem tiny : True := True.intro\n',path='lean/OAI/Algebra/Small.lean'):
    return {'path':path,'git_blob_sha':hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
            'size':len(data),'mode':'100644','role':'proof-library'}


def test_nul_tree_parser_handles_unicode_and_spaces():
    e=entry(path='lean/OAI/Algebra/κ alpha.lean')
    text=f"100644 blob {e['git_blob_sha']} {e['size']}\t{e['path']}\0"
    assert index.parse_tree(text)==[e]


@pytest.mark.parametrize('name',['../outside.lean','lean/OAI/../../outside.lean','/lean/OAI/X.lean','lean/OAI/.git/a.lean','lean/OAI//X.lean'])
def test_unsafe_inventory_paths_fail_before_file_reads(name):
    with pytest.raises(ValueError):index.parse_tree('100644 blob '+'a'*40+' 10\t'+name+'\0')


def test_duplicate_inventory_never_inflates_coverage():
    text='100644 blob '+'a'*40+' 10\tlean/OAI/A/X.lean\0'
    with pytest.raises(ValueError):index.parse_tree(text+text)


def test_file_hash_is_bound_before_heuristic_indexing(tmp_path):
    data=b'/- theorem fake : False := sorry -/\nnamespace X\ntheorem actual : True := True.intro\nend X\n'
    e=entry(data);p=tmp_path/e['path'];p.parent.mkdir(parents=True);p.write_bytes(data)
    row=index.verify_file(tmp_path,e);assert row['source_hash_verified']
    got=index.index_headers((str(tmp_path),row,10000,2))
    assert got['header_status']=='source-indexed' and got['declaration_candidates']==1
    summary=index.aggregate([got]);assert summary['all_source_hashes_verified']
    assert summary['environment_discovered_theorems'] is None
    assert summary['candidate_count_is_heuristic'] and not summary['whole_corpus_english_coverage']
    assert summary['proofs_compiled']==summary['proofs_replayed']==0


def test_missing_changed_and_budgeted_files_stay_in_denominator(tmp_path):
    e=entry();missing=index.verify_file(tmp_path,e)
    assert not missing['source_hash_verified']
    p=tmp_path/e['path'];p.parent.mkdir(parents=True);p.write_bytes(b'changed')
    changed=index.verify_file(tmp_path,e);assert not changed['source_hash_verified']
    p.write_bytes(b'theorem tiny : True := True.intro\n')
    good=index.verify_file(tmp_path,e)
    capped=index.index_headers((str(tmp_path),good,1,2))
    assert capped['header_status']=='byte-budget'
    summary=index.aggregate([missing,changed,capped])
    assert summary['expected_files']==3 and summary['source_hashes_verified']==1
    assert not summary['all_headers_indexed'] and not summary['all_source_hashes_verified']


def test_symlink_is_not_read_as_a_source_file(tmp_path):
    data=b'theorem tiny : True := True.intro\n'
    other=tmp_path/'elsewhere';other.write_bytes(data)
    e=entry(data);p=tmp_path/e['path'];p.parent.mkdir(parents=True);p.symlink_to(other)
    assert not index.verify_file(tmp_path,e)['source_hash_verified']
