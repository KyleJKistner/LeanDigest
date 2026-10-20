from pathlib import Path
import pytest
from proofreader.original_project import read, write
from scripts.completion_diagnostics import diagnose


def test_retained_zip_and_extracted_directory_do_not_collide(tmp_path):
    root=tmp_path/'collection';root.mkdir()
    (root/'completion-result-a.zip').write_bytes(b'archived observation')
    write(root/'completion-result-a/identity.json',{'worker_id':'a'})
    write(root/'completion-result-a/round-1/execution.json',{
        'status':'failed','reason':'timeout','exit_code':-9,'stdout':'partial','stderr':''})
    result=diagnose([root],tmp_path/'delivery')
    assert len(result['workers'])==1
    assert result['workers'][0]['rounds'][0]['reason']=='timeout'
    assert result['proof_acceptance_established'] is False
    assert result['remaining'] is None


def test_only_actual_missing_readings_are_reported(tmp_path):
    out=tmp_path/'delivery'
    write(out/'site/original-verification.json',{
        'theorems':[{'module':'OAI.A','name':'done','reading_available':True},
                    {'module':'OAI.B','name':'pending','reading_available':False}],
        'tasks':[{'id':'first','status':'passed','diagnosis':'passed'},
                 {'id':'second','status':'timeout','diagnosis':'time-budget-exhausted'}]})
    result=diagnose([],out)
    assert result['remaining']['theorems']==[{'module':'OAI.B','name':'pending'}]
    assert len(result['remaining']['tasks'])==1
    assert read(out/'remaining-obligations.json')==result['remaining']
    assert result['proof_acceptance_established'] is False


def test_review_keeps_failed_proof_error_and_execution_tail(tmp_path):
    root=tmp_path/'collection';worker=root/'completion-result-a'
    write(worker/'identity.json',{'worker_id':'a'})
    write(worker/'proofs/original-proof-worker.json',{'module':'OAI.A','status':'partial','validated_readings':0})
    write(worker/'proofs/reading/proofs.json',{'targets':[{
        'module':'OAI.A','name':'t','status':'extraction-failed','errors':['scope mismatch']}]})
    write(worker/'comparisons/worker.json',{'targets':[{'id':'compare:A','status':'failed','log':'logs/a.json'}]})
    write(worker/'comparisons/logs/a.json',{'stdout':'failure detail','stderr':'checker stopped'})
    result=diagnose([root],tmp_path/'delivery')
    assert result['workers'][0]['proof_outcomes'][1]['errors']==['scope mismatch']
    assert result['workers'][0]['unsuccessful_checks'][0]['stderr_tail']=='checker stopped'


def test_linked_diagnostic_directory_is_rejected(tmp_path):
    root=tmp_path/'collection';root.mkdir()
    (root/'completion-result-a').symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(ValueError,match='Linked'):diagnose([root],tmp_path/'delivery')
