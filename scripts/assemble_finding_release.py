"""Build the frozen all-findings catalog and verify its complete access inventory.

Only the surrounding GitHub workflow downloads inputs. This program reads local
artifacts, never executes Lean, and never upgrades a statement into a proof.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.finding_catalog import PIN, build, read_json, write_json, safe_child
from proofreader.catalog_audit import audit

SOURCE_SHA256='7f596ba4fe17fe0d7d55655e6e82d99d4d87181e0a9032721c048d7385163f3c'
INPUT_RUNS={'source':38822475057,'observations':39049596449,
            'statement_retries':39050823104,'proof_retries':39065371645}
FONT_SUFFIXES={'.ttf','.otf','.woff','.woff2'}


def unpack_source(inputs: Path, destination: Path) -> Path:
    archive=inputs/'source/openai-lean-source.tar.gz'
    if sha256(archive.read_bytes()).hexdigest()!=SOURCE_SHA256:
        raise ValueError('Complete original source archive hash mismatch')
    summary=read_json(inputs/'source/source-summary.json')
    if summary['commit']!=PIN or not summary['all_source_bytes_match_git']:
        raise ValueError('Wrong original source identity')
    if destination.exists():raise ValueError('Use a fresh source extraction directory')
    with tarfile.open(archive) as t:
        for member in t:
            if member.issym() or member.islnk() or Path(member.name).suffix.lower() in FONT_SUFFIXES:
                raise ValueError('Unexpected linked member or font file')
        t.extractall(destination,filter='data')
    entries=read_json(inputs/'source/source-inventory.json')
    for row in entries:
        p=safe_child(destination,row['path'])
        data=p.read_bytes()
        if sha256(data).hexdigest()!=row['sha256']:
            raise ValueError('Original source inventory hash mismatch: '+row['path'])
    expected={r['path'] for r in entries}
    actual={p.relative_to(destination).as_posix() for p in (destination/'lean').rglob('*') if p.is_file()}
    if expected!=actual:raise ValueError('Missing or extra original Lean source files')
    return destination/'lean'


def deterministic_zip(site: Path, output: Path) -> str:
    with ZipFile(output,'w',ZIP_DEFLATED,compresslevel=9) as z:
        for path in sorted(site.rglob('*')):
            if not path.is_file():continue
            if path.suffix.lower() in FONT_SUFFIXES:raise ValueError('Font distribution is excluded')
            info=ZipInfo('Leanglish/'+path.relative_to(site).as_posix(),date_time=(2026,10,17,0,0,0))
            info.compress_type=ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,path.read_bytes(),compress_type=ZIP_DEFLATED,compresslevel=9)
    with ZipFile(output) as z:
        if z.testzip() is not None:raise ValueError('Corrupt release archive')
    return sha256(output.read_bytes()).hexdigest()


def assemble(inputs: Path, output: Path) -> dict:
    if output.exists():raise ValueError('Use a fresh release output directory')
    output.mkdir(parents=True)
    lean=unpack_source(inputs,output/'original-source')
    obs=inputs/'observations'
    old_statements=list((obs/'inputs/statements').rglob('statements.json'))
    new_statements=list((inputs/'statement-retries').rglob('statements.json'))
    old_proofs=list((obs/'inputs/proofs').rglob('proofs.json'))
    new_proofs=list((inputs/'proof-retries').rglob('proofs.json'))
    if (len(old_statements),len(new_statements),len(old_proofs),len(new_proofs))!=(4,2,16,16):
        raise ValueError('A frozen input shard is missing')
    retries=[read_json(p) for p in new_proofs]
    if {r['shard'] for r in retries}!=set(range(16)) or any(r['shards']!=16 for r in retries):
        raise ValueError('Repeated or missing proof retry shard')
    targets=[r for batch in retries for r in batch['targets']]
    if len(targets)!=28 or len({(r['module'],r['name']) for r in targets})!=28:
        raise ValueError('The 28-target retry inventory does not reconcile')
    if any(r['status']!='reading-generated' or not r['kernel_checked'] for r in targets):
        raise ValueError('The retained 28-target retry is not complete')
    site=output/'site'
    coverage=build(obs/'inputs/catalog/upstream',lean,
        [obs/'inputs/statements',inputs/'statement-retries'],
        [obs/'inputs/proofs',inputs/'proof-retries'],site,
        math_assets=obs/'assets',source_inventory=inputs/'source/source-inventory.json')
    expected={'findings':372,'documented_findings':242,'configurations':416,
              'expected_statement_entries':602,'elaborated_statement_entries':602,
              'unique_formal_targets':601,'expected_theorem_targets':536,
              'definition_references':65,'proof_readings':109,'solution_source_modules':413}
    if any(coverage[k]!=v for k,v in expected.items()) or coverage['rendering_failures']:
        raise ValueError('Frozen release coverage regression')
    checks=audit(site)
    if not checks['passed']:raise ValueError('Catalog link audit failed: '+str(checks['errors']))
    repo=Path(__file__).resolve().parents[1]
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    identity={'schema':'leanglish.finding-release/v1','upstream_commit':PIN,
        'application_commit':commit,'application_tracked_tree_clean':not subprocess.check_output(['git','status','--porcelain','--untracked-files=no'],cwd=repo,text=True).strip(),
        'application_source_hashes':{p.relative_to(repo).as_posix():sha256(p.read_bytes()).hexdigest() for folder in ('proofreader','leanglish','scripts') for p in sorted((repo/folder).rglob('*')) if p.is_file() and p.suffix in {'.py','.js','.css','.html','.lean'}},
        'input_workflow_runs':INPUT_RUNS,
        'original_source_archive_sha256':SOURCE_SHA256,'coverage':coverage,
        'static_audit':checks,'proof_retry_targets_recovered':28,
        'native_lean_executed_by_builder':False,'observations_authenticated':False}
    write_json(site/'release.json',identity)
    write_json(site/'static-audit.json',checks)
    shutil.copy2(repo/'docs/ALL_FINDINGS.md',site/'RELEASE-NOTES.md')
    return identity


def package(output: Path) -> dict:
    site=output/'site';browser=read_json(output/'browser-audit.json')
    if browser.get('passed') is not True or browser.get('navigation_backend')!='real-offline-file-navigation':
        raise ValueError('Public packaging requires actual offline-file browser navigation')
    shutil.copy2(output/'browser-audit.json',site/'browser-audit.json')
    identity=read_json(site/'release.json')
    if identity.get('application_tracked_tree_clean') is not True:
        raise ValueError('Public packaging requires an unchanged committed source tree')
    identity['browser_audit']=browser
    write_json(site/'release.json',identity)
    # The site digest covers the records/HTML/code, not an unverifiable green badge.
    manifest={p.relative_to(site).as_posix():sha256(p.read_bytes()).hexdigest()
              for p in sorted(site.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.json'}
    write_json(site/'SHA256SUMS.json',manifest)
    dist=output/'dist';dist.mkdir(exist_ok=True)
    archive=dist/'leanglish-all-findings.zip'
    checksum=deterministic_zip(site,archive)
    (dist/'SHA256SUMS').write_text(checksum+'  '+archive.name+'\n')
    shutil.copy2(site/'coverage.json',dist/'coverage.json')
    shutil.copy2(site/'release.json',dist/'release.json')
    return {'archive':str(archive),'sha256':checksum,'bytes':archive.stat().st_size}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--package',action='store_true')
    a=p.parse_args()
    if a.package:r=package(a.output)
    else:
        if a.inputs is None:p.error('--inputs is required for assembly')
        r=assemble(a.inputs,a.output)
    print(json.dumps(r,indent=2))
if __name__=='__main__':main()
