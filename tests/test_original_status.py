from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import zipfile
import pytest
from proofreader.original_project import read,write,file_hash
from proofreader.original_status import check_archive,diagnosis,task_rows
from test_original_project import successful_library_report


def test_summary_agrees_and_keeps_unknown_tasks(tmp_path):
    _,plan,root,_ = successful_library_report(tmp_path)
    summary,rows=task_rows(plan,[root])
    assert summary['library_passed']==1 and summary['comparator_passed']==0
    assert len(rows)==2 and rows[0]['status']=='passed' and rows[1]['status']=='not-retained'


def test_failed_logs_also_bound(tmp_path):
    _,plan,root,report=successful_library_report(tmp_path)
    report['targets'][0]['status']='timeout';report['status']='partial';report['complete']=False
    write(root/'worker.json',report)
    (root/'logs/a.json').write_text('changed')
    with pytest.raises(ValueError,match='unchanged execution log'):
        task_rows(plan,[root])


@pytest.mark.parametrize('status,log,expected',[
    ('timeout',{'reason':'timeout','exit_code':-9},'time-budget-exhausted'),
    ('failed',{'stderr':'nanoda_bin executable file not found'},'required-external-kernel-unavailable'),
    ('failed',{'exit_code':143},'process-terminated'),
    ('failed',{'exit_code':1,'stderr':'unknown error'},'unsuccessful-execution-needs-review'),
    ('running',None,'unfinished-or-unretained-execution')])
def test_failure_is_not_mathematical_refutation(status,log,expected):
    assert diagnosis({'status':status},log)==expected
    assert diagnosis(None,None)=='no-retained-outcome'


def test_archive_detects_changed_extracted_bytes(tmp_path):
    z=tmp_path/'in.zip';d=tmp_path/'data';d.mkdir()
    with zipfile.ZipFile(z,'w') as a:a.writestr('worker.json',b'original')
    (d/'worker.json').write_bytes(b'original')
    check_archive(z,d,file_hash(z))
    (d/'worker.json').write_bytes(b'modified')
    with pytest.raises(ValueError,match='differs'):check_archive(z,d,file_hash(z))


def test_archive_detects_extra_evidence(tmp_path):
    z=tmp_path/'in.zip';d=tmp_path/'data';d.mkdir()
    with zipfile.ZipFile(z,'w') as a:a.writestr('worker.json',b'original')
    (d/'worker.json').write_bytes(b'original');(d/'invented.json').write_text('true')
    with pytest.raises(ValueError,match='Extra'):check_archive(z,d,file_hash(z))


def test_wrong_archive_hash_rejected(tmp_path):
    z=tmp_path/'in.zip'
    with zipfile.ZipFile(z,'w') as a:a.writestr('worker.json','original')
    with pytest.raises(ValueError,match='digest'):check_archive(z,tmp_path/'data','0'*64)


def test_attachment_keeps_reader_bytes_and_uses_wrapping_table(tmp_path):
    from proofreader.original_status import attach_status,SCHEMA
    from proofreader.original_project import digest
    write(tmp_path/'coverage.json',{'proof_readings':1,'expected_theorem_targets':2})
    write(tmp_path/'catalog.json',[])
    for filename in ('index.html','coverage.html'):
        (tmp_path/filename).write_text('<main id="content">original</main>')
    reader=tmp_path/'proofs'/'one';reader.mkdir(parents=True)
    (reader/'reader.html').write_bytes(b'original reader and source proof')
    record={'schema':SCHEMA,'collection':{'cutoff':'2026-10-18T20:52:16Z'},
        'proof_summary':{'total_readings':1,'expected_theorem_targets':2,
                         'original_environment_new_readings':1,'baseline_readings':0},
        'build_summary':{'comparator_passed':0,'comparator_expected':1,
                         'library_passed':0,'library_expected':1},'dependency_count':42,
        'tasks':[{'id':'library:Test','kind':'library','library':'verylongname'*20,
                  'status':'not-retained','diagnosis':'no-retained-outcome'}]}
    record['status_sha256']=digest(record)
    attach_status(tmp_path,record)
    text=(tmp_path/'original-verification.html').read_text()
    assert 'table-layout:fixed' in text and 'overflow-wrap:anywhere' in text
    assert 'not formally verified English' in text
    assert (reader/'reader.html').read_bytes()==b'original reader and source proof'


def test_attachment_rejects_changed_summary(tmp_path):
    from proofreader.original_status import attach_status,SCHEMA
    write(tmp_path/'coverage.json',{'proof_readings':0,'expected_theorem_targets':2})
    with pytest.raises(ValueError,match='does not match'):
        attach_status(tmp_path,{'schema':SCHEMA,'status_sha256':'0'*64})
    assert not (tmp_path/'original-verification.json').exists()
