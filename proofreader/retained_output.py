"""Reprocess a successful native run rejected solely by the old output-size gate.

No new Lean execution is claimed. Original worker audits, immutable archive
binding (the caller's collection gate), source bytes, driver, full output and
native exit status must agree. The new snapshot still passes every schema,
assumption-scope, rendering and arithmetic-certificate check.
"""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import shutil
from .original_project import read,write,file_hash,digest,child
from .proof_campaign import check_environment
from .narrative_io import parse_stream,extraction_source,write_bundle
from .catalog_inputs import load_proofs,config_inventory


def recover(project: Path, plan: dict, env: dict, worker: Path, target: dict, output: Path) -> dict:
    check_environment(plan,env)
    wrapper=read(worker/'original-proof-worker.json')
    if wrapper.get('environment_before')!=env or wrapper.get('environment_after')!=env:
        raise ValueError('Missing complete original-environment audits')
    report=read(worker/'reading/proofs.json')
    if wrapper.get('proof_report_sha256')!=file_hash(worker/'reading/proofs.json'):
        raise ValueError('Changed original outcome ledger')
    matches=[r for r in report['targets'] if (r['module'],r['name'])==(target['module'],target['name'])]
    if len(matches)!=1:
        raise ValueError('Recovery target is outside its original worker')
    row=deepcopy(matches[0])
    if row.get('status')!='extraction-failed' or row.get('errors')!=['Exporter output budget']:
        raise ValueError('Only an output-budget failure may use retained-output recovery')
    source=project.joinpath(*row['module'].split('.')).with_suffix('.lean')
    if file_hash(source)!=row.get('source_sha256'):
        raise ValueError('Changed original theorem source')
    original=child(worker/'reading','targets/'+row['id'])
    receipt=read(original/'receipt.json');run=read(original/'run.json')
    if (receipt.get('backend')!='native' or receipt.get('status')!='failed' or
        receipt.get('errors')!=['Exporter output budget'] or receipt.get('theorem')!=row['name'] or
        receipt.get('module')!=row['module'] or receipt.get('lean_version')!='4.34.1' or
        run.get('status')!='passed' or run.get('exit_code')!=0 or run.get('reason')):
        raise ValueError('The original native run did not complete successfully')
    stdout=(original/'stdout.txt').read_text()
    driver=(original/'Extract.lean').read_text()
    if run.get('stdout')!=stdout or file_hash(original/'Extract.lean')!=receipt.get('source_sha256'):
        raise ValueError('Changed retained output or executed driver')
    expected=extraction_source(row['name'],version='4.34.1',module=row['module'],
        max_heartbeats=receipt['execution_limits']['max_heartbeats'])
    if driver!=expected:
        raise ValueError('Recovery requires the exact trusted current exporter driver')
    command=run.get('command',[])
    if len(command)!=4 or command[:3]!=['lake','env','lean'] or Path(command[3]).name!='Driver.lean':
        raise ValueError('Wrong native invocation')
    snap=parse_stream(stdout,theorem=row['name'],version='4.34.1')
    if output.exists():
        raise ValueError('Do not overwrite a recovery observation')
    dest=output/'targets'/row['id'];dest.mkdir(parents=True)
    for name in ('Extract.lean','stdout.txt','stderr.txt','run.json'):
        shutil.copy2(original/name,dest/name)
    origin={'worker_report_sha256':file_hash(worker/'original-proof-worker.json'),
            'original_receipt_sha256':file_hash(original/'receipt.json'),
            'native_run_sha256':file_hash(original/'run.json'),
            'stdout_sha256':file_hash(original/'stdout.txt'),
            'prior_error':'Exporter output budget', 'native_execution_rerun':False}
    receipt.update(status='passed',errors=[],snapshot_sha256=snap.sha256,
                   selected_judgements=snap.record['judgements_checked'],
                   all_selected_judgements_kernel_checked=True,path_linkage_checked_in_lean=True,
                   retained_output_recovery=origin,receipt_authenticated=False)
    coverage=write_bundle(snap.record,dest,source=source.read_text(),file=str(source.relative_to(project)),receipt=receipt)
    row.update(status='reading-generated',kernel_checked=True,errors=[],directory='targets/'+row['id'],
               snapshot_sha256=snap.sha256,selected_judgements=snap.record['judgements_checked'],coverage=coverage)
    ledger={'schema':'leanglish.finding-proof-shard/v1','upstream_commit':plan['upstream_commit'],
            'scope':'lossless-reprocessing-of-retained-successful-native-output',
            'targets':[row],'expected_targets':1,'expected_theorems':1,'kernel_checked':1,'readers_written':1,
            'original_environment_sha256':env['environment_sha256'],'native_execution_rerun':False,
            'english_formally_certified':False,'whole_upstream_project_build':False}
    write(output/'proofs.json',ledger)
    recovery={'schema':'leanglish.retained-output-recovery/v1',**origin,
              'module':row['module'],'name':row['name'],'snapshot_sha256':snap.sha256,
              'original_plan_sha256':plan['plan_sha256'],'original_environment_sha256':env['environment_sha256'],
              'judgements':snap.record['judgements_checked'],'proof_report_sha256':file_hash(output/'proofs.json')}
    write(output/'recovery.json',recovery)
    selected,_=load_proofs([output],config_inventory(project),project)
    if len(selected)!=1:raise ValueError('Recovered observation failed the normal proof-loader gate')
    return recovery
