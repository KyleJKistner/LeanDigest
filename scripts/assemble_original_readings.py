"""Build receipt-validated readings and original-configuration evidence offline."""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.original_project import read, write, file_hash, child
from proofreader.original_status import build_status, attach_status
from proofreader.finding_catalog import build
from proofreader.catalog_audit import audit


def assemble(evidence: Path, inputs: Path, source: Path, inventory: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError('Use a fresh original-reading delivery directory')
    output.mkdir(parents=True)
    status, roots = build_status(source, evidence, recovery_output=output/'recovered-native-output')
    site = output/'site';obs = inputs/'observations'
    coverage = build(obs/'inputs/catalog/upstream', source,
        [obs/'inputs/statements', inputs/'statement-retries'], roots, site,
        math_assets=obs/'assets', source_inventory=inventory)
    if coverage['rendering_failures'] or coverage['proof_readings'] != status['proof_summary']['total_readings']:
        raise ValueError('Rendered count does not match the verified proof inventory')
    if not coverage['all_documented_findings_indexed'] or not coverage['all_specification_entries_accessible']:
        raise ValueError('Finding/specification access regressed')
    attach_status(site, status)
    # Preserve inspection evidence, not executable tools or font files.
    dest = site/'original-evidence';dest.mkdir()
    for p in sorted((evidence/'original-build').rglob('worker.json')):
        target = dest/p.parent.name;target.mkdir()
        shutil.copy2(p, target/'worker.json')
        for row in read(p)['targets']:
            if row.get('log'):
                rel = row['log'];out = child(target,rel)
                out.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(child(p.parent,rel),out)
    seed = evidence/'original-proofs/original-proof-campaign-plan'
    for name in ('plan.json','environment.json','campaign.json'):
        shutil.copy2(seed/name,dest/name)
    shutil.copy2(evidence/'collection.json',dest/'collection.json')
    if (output/'recovered-native-output').is_dir():
        for p in sorted((output/'recovered-native-output').glob('*/recovery.json')):
            shutil.copy2(p,dest/('recovery-'+p.parent.name+'.json'))
    # Outer original-environment audits do not rewrite the old proof receipts.
    for p in sorted((evidence/'original-proofs').rglob('original-proof-worker.json')):
        out = dest/'proof-workers'/p.parent.name;out.mkdir(parents=True)
        shutil.copy2(p,out/p.name)
        if (p.parent/'reading/proofs.json').is_file():
            shutil.copy2(p.parent/'reading/proofs.json',out/'proofs.json')
    checks = audit(site)
    if not checks['passed']:
        raise ValueError('Offline catalog audit failed: '+str(checks['errors'])[:2000])
    repo = Path(__file__).resolve().parents[1]
    identity = {'schema':'leanglish.original-reading-delivery/v1','upstream_commit':status['upstream_commit'],
        'application_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
        'application_tracked_tree_clean':not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo,text=True).strip(),
        'source_hashes':{p.relative_to(repo).as_posix():file_hash(p)
                        for p in [repo/'proofreader/original_status.py',repo/'scripts/assemble_original_readings.py']},
        'coverage':coverage,'original_build_summary':status['build_summary'],
        'original_proof_summary':{k:v for k,v in status['proof_summary'].items() if k not in {'targets','missing_workers'}},
        'evidence_collection':status['collection'],'static_audit':checks,
        'native_lean_executed_by_builder':False,'observations_authenticated':False,'english_formally_verified':False}
    write(site/'release.json',identity);write(site/'static-audit.json',checks)
    (site/'RELEASE-NOTES.md').write_text(
        '# Original-project reading checkpoint\n\n'
        f"{coverage['proof_readings']} of {coverage['expected_theorem_targets']} theorem targets have readings. "
        f"{status['build_summary']['comparator_passed']} of {status['build_summary']['comparator_expected']} original comparisons passed.\n\n"
        'All original finding and formal target documentation remains available. See original-verification.html. '
        'Earlier receipts retain their own scope. Full original-project build, all comparisons, all readings, '
        'complete exposition and formally verified English are separate milestones, not claimed complete.\n')
    return identity


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence','inputs','source','inventory','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();r=assemble(a.evidence,a.inputs,a.source,a.inventory,a.output)
    print({k:r['coverage'][k] for k in ['proof_readings','findings_with_any_reading','findings_with_all_target_readings','selected_checked_frames','explicit_explanation_gaps']})
    return 0

if __name__=='__main__':raise SystemExit(main())
