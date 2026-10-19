"""Build an offline catalog from original-project evidence and a frozen recovery run.

No Lean code runs here. Only successfully replayed source-bound observations may
add a reading or satisfy an original comparison. Missing workers remain explicit.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.original_project import read, write, file_hash, child
from proofreader.original_status import build_status, attach_status
from proofreader.original_attempts import reconcile_attempts
from proofreader.proof_campaign import reconcile as reconcile_proofs
from proofreader.completion_results import check_collection, join_status
from proofreader.catalog_inputs import config_inventory, load_proofs
from proofreader.finding_catalog import build
from proofreader.catalog_audit import audit
from scripts.prepare_completion_recovery import recovery_plan, checked_retry_roots


def retain_worker_files(destination: Path, roots: list[Path], name: str) -> None:
    """Keep result ledgers and the logs to which they refer; omit executable caches."""
    group=destination/name;group.mkdir(parents=True)
    for root in roots:
        report_path=root/'worker.json'
        identity=file_hash(report_path)
        target=group/identity
        if target.exists():
            raise ValueError('Duplicate evidence in delivery')
        target.mkdir()
        shutil.copy2(report_path,target/'worker.json')
        for row in read(report_path)['targets']:
            if row.get('log'):
                src=child(root,row['log']);dst=child(target,row['log'])
                dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)


def assemble(evidence: Path, completion: Path, seed: Path, inputs: Path,
             source: Path, inventory: Path, output: Path, *, run_id: int,
             expected_head: str) -> dict:
    if output.exists():
        raise ValueError('Use a fresh completion delivery directory')
    output.mkdir(parents=True)
    original_seed=evidence/'original-proofs/original-proof-campaign-plan'
    plan,env=[read(original_seed/(n+'.json')) for n in ('plan','environment')]
    if read(seed/'plan.json')!=plan or read(seed/'environment.json')!=env:
        raise ValueError('Completion plan has different original source or dependencies')
    base,baseline_roots=build_status(source,evidence,recovery_output=output/'recovered-native-output')
    prior_builds=[p.parent for p in sorted((evidence/'original-build').rglob('worker.json'))]
    prior_builds+=checked_retry_roots(evidence)
    prior_attempts=reconcile_attempts(plan,prior_builds,environment=env)
    recovery=read(seed/'recovery.json')
    if recovery!=recovery_plan(plan,env,base,prior_attempts):
        raise ValueError('Recovery work is not the exact complement of the verified baseline')
    collected=check_collection(completion,recovery,expected_run=run_id,expected_head=expected_head)
    proof_summary,new_roots=reconcile_proofs(source,plan,env,recovery['campaign'],
                                              baseline_roots,collected['proof_roots'])
    all_builds=prior_builds+collected['build_roots']
    attempts=reconcile_attempts(plan,all_builds,environment=env)
    all_roots=baseline_roots+new_roots
    selected,_=load_proofs(all_roots,config_inventory(source),source)
    status=join_status(base,attempts,proof_summary,selected,collected['collection'])
    status['completion']['workers']=collected['workers']
    status['completion']['missing_workers']=collected['missing_workers']
    from proofreader.original_project import digest
    status['status_sha256']=digest({k:v for k,v in status.items() if k!='status_sha256'})
    site=output/'site';obs=inputs/'observations'
    coverage=build(obs/'inputs/catalog/upstream',source,
        [obs/'inputs/statements',inputs/'statement-retries'],all_roots,site,
        math_assets=obs/'assets',source_inventory=inventory)
    if (coverage['rendering_failures'] or coverage['proof_readings']!=len(selected) or
        not coverage['all_documented_findings_indexed'] or
        not coverage['all_specification_entries_accessible']):
        raise ValueError('Rendered catalog does not match the complete validated inventory')
    attach_status(site,status)
    dest=site/'original-evidence';dest.mkdir()
    retain_worker_files(dest,all_builds,'verification-workers')
    for n,value in [('plan',plan),('environment',env),('baseline-status',base),
                    ('recovery-plan',recovery),('attempts',attempts),
                    ('completion-proofs',proof_summary)]:write(dest/(n+'.json'),value)
    for label,root in [('original',evidence),('completion',completion)]:
        shutil.copy2(root/'collection.json',dest/(label+'-collection.json'))
    proof_workers=[p.parent for p in sorted((evidence/'original-proofs').rglob('original-proof-worker.json'))]
    proof_workers+=collected['proof_roots']
    for root in proof_workers:
        marker=root/'original-proof-worker.json';target=dest/'proof-workers'/file_hash(marker)
        target.mkdir(parents=True)
        shutil.copy2(marker,target/marker.name)
        if (root/'reading/proofs.json').is_file():
            shutil.copy2(root/'reading/proofs.json',target/'proofs.json')
    checks=audit(site)
    if not checks['passed']:
        raise ValueError('Offline catalog audit failed: '+str(checks['errors'])[:2000])
    repo=Path(__file__).resolve().parents[1]
    clean=not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo,text=True).strip()
    if not clean:
        raise ValueError('Delivery must be generated by an unchanged committed checkout')
    release={'schema':'leanglish.completion-reading-delivery/v1','upstream_commit':status['upstream_commit'],
        'application_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
        'application_tree':subprocess.check_output(['git','rev-parse','HEAD^{tree}'],cwd=repo,text=True).strip(),
        'application_tracked_tree_clean':clean,'coverage':coverage,
        'original_build_summary':{k:v for k,v in attempts.items() if k!='tasks'},
        'original_proof_summary':{k:v for k,v in status['proof_summary'].items() if k not in {'targets','completion_campaign'}},
        'completion':status['completion'],'status_sha256':status['status_sha256'],
        'static_audit':checks,'native_lean_executed_by_builder':False,
        'observations_authenticated':False,'english_formally_verified':False}
    write(site/'release.json',release);write(site/'static-audit.json',checks)
    (site/'RELEASE-NOTES.md').write_text(
        '# Original-project proof readings\n\n'
        f"{len(selected)} of {coverage['expected_theorem_targets']} documented theorem targets have readings. "
        f"{attempts['comparator_passed']} of {attempts['comparator_expected']} original comparisons passed; "
        f"{attempts['library_passed']} of {attempts['library_expected']} original libraries built.\n\n"
        'See original-verification.html for every obligation and its retained history. '
        'Earlier reading receipts retain their original execution scope. '
        'Failed or missing jobs remain outstanding, and explanation gaps remain visible. '
        'These readings are not formally verified English.\n',encoding='utf-8')
    compact={'proof_readings':len(selected),'new_readings':status['completion']['new_readings'],
             'theorem_targets':coverage['expected_theorem_targets'],
             'comparators_passed':attempts['comparator_passed'],'comparators_expected':attempts['comparator_expected'],
             'libraries_passed':attempts['library_passed'],'libraries_expected':attempts['library_expected'],
             'findings_with_any_reading':coverage['findings_with_any_reading'],
             'findings_with_all_target_readings':coverage['findings_with_all_target_readings'],
             'selected_checked_frames':coverage['selected_checked_frames'],
             'explicit_explanation_gaps':coverage['explicit_explanation_gaps'],
             'static_audit_passed':checks['passed'], 'status_sha256':status['status_sha256'],
             'original_obligations_and_readings_complete':status['original_obligations_and_readings_complete']}
    write(output/'summary.json',compact)
    print('COMPLETION_DELIVERY',compact,flush=True)
    return release


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence','completion','seed','inputs','source','inventory','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--run-id',type=int,required=True)
    parser.add_argument('--expected-head',required=True)
    a=parser.parse_args()
    assemble(a.evidence,a.completion,a.seed,a.inputs,a.source,a.inventory,a.output,
             run_id=a.run_id,expected_head=a.expected_head)
    return 0

if __name__=='__main__':raise SystemExit(main())
