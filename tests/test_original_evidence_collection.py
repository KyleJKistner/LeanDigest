from pathlib import Path
import hashlib
import stat
import zipfile
from unittest.mock import patch
import pytest
from scripts.collect_original_evidence import unpack, retain, stable_artifacts


def archive_at(tmp_path, names):
    p=tmp_path/'artifact.zip'
    with zipfile.ZipFile(p,'w') as z:
        for name in names:z.writestr(name, b'not a proof observation')
    return p


def test_regular_archive_is_retained(tmp_path):
    p=archive_at(tmp_path,['a/worker.json','a/logs/log.json'])
    assert unpack(p,tmp_path/'out')==2
    assert (tmp_path/'out/a/worker.json').is_file()
    with pytest.raises(ValueError,match='fresh'):unpack(p,tmp_path/'out')


@pytest.mark.parametrize('name',['../outside','/absolute','a/../outside','a\\evil','a:evil','./a','a//b'])
def test_unsafe_archive_paths_rejected(tmp_path,name):
    p=archive_at(tmp_path,[name])
    with pytest.raises(ValueError):unpack(p,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_symlink_rejected(tmp_path):
    p=tmp_path/'link.zip'
    with zipfile.ZipFile(p,'w') as z:
        i=zipfile.ZipInfo('link');i.create_system=3;i.external_attr=(stat.S_IFLNK|0o777)<<16
        z.writestr(i,'/etc/passwd')
    with pytest.raises(ValueError,match='Non-regular'):unpack(p,tmp_path/'out')


def test_duplicate_archive_path_rejected(tmp_path):
    with pytest.warns(UserWarning):p=archive_at(tmp_path,['worker.json','worker.json'])
    with pytest.raises(ValueError):unpack(p,tmp_path/'out')


def test_cutoff_excludes_newly_appearing_artifacts():
    a={'id':1,'name':'original-proof-a','created_at':'2026-10-18T01:00:00Z'}
    b={'id':2,'name':'original-proof-b','created_at':'2026-10-18T03:00:00Z'}
    with patch('scripts.collect_original_evidence.api',side_effect=[ [{'artifacts':[a]}], [{'artifacts':[b,a]}] ]):
        assert stable_artifacts('owner/repo',1,('original-proof-',),'2026-10-18T02:00:00Z')==[a]


def test_false_archive_digest_blocks_extraction(tmp_path):
    source=archive_at(tmp_path,['worker.json'])
    item={'id':5,'name':'original-proof-a','workflow_run':{'id':1,'head_sha':'a'*40},
          'digest':'sha256:'+'0'*64,'expired':False,'size_in_bytes':source.stat().st_size}
    def fake_run(command,stdout,**kw):stdout.write(source.read_bytes())
    with patch('scripts.collect_original_evidence.subprocess.run',side_effect=fake_run):
        with pytest.raises(ValueError,match='differs'):retain('owner/repo',{'id':1,'head_sha':'a'*40},item,tmp_path)
    assert not (tmp_path/'original-proof-a').exists()


def test_foreign_run_is_rejected_before_network(tmp_path):
    with patch('scripts.collect_original_evidence.subprocess.run') as run:
        with pytest.raises(ValueError,match='another run'):
            retain('owner/repo',{'id':1,'head_sha':'a'},
                   {'name':'original-proof-a','workflow_run':{'id':2,'head_sha':'a'}},tmp_path)
        run.assert_not_called()


def test_digest_bound_artifact_retained(tmp_path):
    source=archive_at(tmp_path,['worker.json']);data=source.read_bytes()
    item={'id':5,'name':'original-proof-a','workflow_run':{'id':1,'head_sha':'a'*40},
          'digest':'sha256:'+hashlib.sha256(data).hexdigest(),'expired':False,'size_in_bytes':len(data)}
    def fake_run(command,stdout,**kw):stdout.write(data)
    with patch('scripts.collect_original_evidence.subprocess.run',side_effect=fake_run):
        got=retain('owner/repo',{'id':1,'head_sha':'a'*40},item,tmp_path)
    assert got['status']=='retained' and got['entries']==1
    assert (tmp_path/'original-proof-a/worker.json').is_file()
