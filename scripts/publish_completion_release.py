"""Publish an already validated offline catalog; never rebuild or relabel evidence.

The caller supplies the exact delivery execution, source commit and artifact
hash. A new prerelease is created only after source CI, real browser navigation,
the original-status ledger and every packaged file have been checked.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.collect_original_evidence import api, unpack
from proofreader.original_project import read, write, file_hash, digest

REPO='KyleJKistner/LeanDigest'
FONTS={'.ttf','.otf','.woff','.woff2'}
ASSETS=('leanglish-all-findings.zip','leanglish-application.zip','SHA256SUMS',
        'coverage.json','release.json','original-verification.json','summary.json')


def validate_identity(release: dict, status: dict, coverage: dict, application: str) -> None:
    if (release.get('schema')!='leanglish.completion-reading-delivery/v1' or
        release.get('application_commit')!=application or
        release.get('application_tracked_tree_clean') is not True or
        release.get('coverage')!=coverage or
        status.get('status_sha256')!=digest({k:v for k,v in status.items() if k!='status_sha256'}) or
        release.get('status_sha256')!=status['status_sha256']):
        raise ValueError('Publication source or original-evidence identity mismatch')
    if (release.get('static_audit',{}).get('passed') is not True or
        release.get('browser_audit',{}).get('passed') is not True or
        release['browser_audit'].get('navigation_backend')!='real-offline-file-navigation'):
        raise ValueError('Publication requires static and real offline browser checks')
    required={'documented_findings':242,'expected_theorem_targets':536,
              'expected_statement_entries':602,'elaborated_statement_entries':602}
    if (any(coverage.get(k)!=v for k,v in required.items()) or
        coverage.get('all_documented_findings_indexed') is not True or
        coverage.get('all_specification_entries_accessible') is not True or
        coverage.get('rendering_failures')):
        raise ValueError('The complete documented finding inventory regressed')
    proofs=status['proof_summary'];build=status['build_summary']
    if (proofs['expected_theorem_targets']!=536 or build['comparator_expected']!=416 or
        build['library_expected']!=25 or coverage['proof_readings']!=proofs['total_readings'] or
        not 492<=proofs['total_readings']<=536 or not 341<=build['comparator_passed']<=416 or
        not 15<=build['library_passed']<=25 or
        release.get('english_formally_verified') is not False or
        release.get('native_lean_executed_by_builder') is not False):
        raise ValueError('Publication counts or trust scope are inconsistent')


def check_site_archive(path: Path, release: dict, checksum: str) -> int:
    import zipfile
    if file_hash(path)!=checksum:
        raise ValueError('Offline catalog archive digest mismatch')
    with zipfile.ZipFile(path) as archive:
        infos=archive.infolist();names=[item.filename for item in infos]
        if (len(infos)>30_000 or sum(item.file_size for item in infos)>3_000_000_000 or
            len(names)!=len(set(names))):
            raise ValueError('Repeated or oversized published file inventory')
        for name in names:
            p=PurePosixPath(name)
            if (not name.startswith('Leanglish/') or p.is_absolute() or '..' in p.parts or
                str(p)!=name or '\\' in name or ':' in name or p.suffix.lower() in FONTS):
                raise ValueError('Unsafe path or excluded font in catalog')
        manifest=json.loads(archive.read('Leanglish/SHA256SUMS.json'))
        if set(names)!={'Leanglish/'+name for name in manifest}|{'Leanglish/SHA256SUMS.json'}:
            raise ValueError('The site manifest is not the exact archive inventory')
        for name,expected in manifest.items():
            with archive.open('Leanglish/'+name) as stream:
                actual=hashlib.file_digest(stream,'sha256').hexdigest()
            if actual!=expected:
                raise ValueError('A catalog file differs from its tested manifest')
        if json.loads(archive.read('Leanglish/release.json'))!=release:
            raise ValueError('Archived publication identity changed')
    return len(manifest)


def publish(run_id: int, artifact_id: int, artifact_sha256: str, application: str,
            tag: str, output: Path, *, allow_publish: bool=False) -> dict:
    if not allow_publish:
        raise PermissionError('Publication requires --allow-publish')
    if (type(run_id) is not int or run_id<=0 or type(artifact_id) is not int or artifact_id<=0 or
        re.fullmatch(r'[a-f0-9]{64}',artifact_sha256) is None or
        re.fullmatch(r'[a-f0-9]{40}',application) is None or
        re.fullmatch(r'leanglish-original-project-[a-f0-9]{7,40}',tag) is None or
        not application.startswith(tag.removeprefix('leanglish-original-project-')) or output.exists()):
        raise ValueError('Explicit immutable input identities and a fresh output are required')
    output.mkdir(parents=True)
    run=api(REPO,f'actions/runs/{run_id}');artifact=api(REPO,f'actions/artifacts/{artifact_id}')
    if (run.get('status')!='completed' or run.get('conclusion')!='success' or run.get('head_sha')!=application or
        run.get('path')!='.github/workflows/completion-delivery.yml' or artifact.get('expired') or
        artifact.get('workflow_run',{}).get('id')!=run_id or
        artifact.get('workflow_run',{}).get('head_sha')!=application or
        artifact.get('digest')!='sha256:'+artifact_sha256 or
        not 0<artifact.get('size_in_bytes',0)<=1_000_000_000):
        raise ValueError('Delivery did not pass on the specified application and artifact')
    pages=api(REPO,f'commits/{application}/check-runs?per_page=100',paged=True)
    checks=[check for page in pages for check in page['check_runs']]
    for name in ('python-and-browser','lean-integration'):
        matching=[check for check in checks if check['name']==name and check['head_sha']==application]
        if not matching:
            raise ValueError('Missing source CI gate: '+name)
        last=max(matching,key=lambda check:check['id'])
        if last['status']!='completed' or last['conclusion']!='success':
            raise ValueError('Latest source CI gate did not pass: '+name)
    outer=output/'delivery.zip'
    with outer.open('xb') as stream:
        subprocess.run(['gh','api',f'repos/{REPO}/actions/artifacts/{artifact_id}/zip'],
                       stdout=stream,stderr=subprocess.PIPE,timeout=300,check=True)
    if file_hash(outer)!=artifact_sha256 or outer.stat().st_size!=artifact['size_in_bytes']:
        raise ValueError('Downloaded delivery differs from its retained digest')
    unpack(outer,output/'frozen');dist=output/'frozen/dist'
    release,status,coverage=[read(dist/name) for name in ('release.json','original-verification.json','coverage.json')]
    validate_identity(release,status,coverage,application)
    browser=read(output/'frozen/original-browser-audit.json')
    if browser.get('passed') is not True:
        raise ValueError('Original verification pages did not pass the browser audit')
    checksum=(dist/'SHA256SUMS').read_text().split()[0]
    entries=check_site_archive(dist/'leanglish-all-findings.zip',release,checksum)
    summary=read(dist/'summary.json');summary['manifest_entries_verified']=entries
    proofs=status['proof_summary'];build=status['build_summary']
    notes=('# Original-project proof readings\n\n'
        'Extract `leanglish-all-findings.zip` and open `Leanglish/index.html`. '
        'No Lean installation or network connection is required to read the catalog.\n\n'
        '| Coverage | Retained result |\n|---|---:|\n'
        '| Documented findings accessible | 242 / 242 |\n'
        '| Formal statement entries accessible | 602 / 602 |\n'
        f"| Theorem readings | {proofs['total_readings']} / 536 |\n"
        f"| Original comparisons passed | {build['comparator_passed']} / 416 |\n"
        f"| Original libraries built | {build['library_passed']} / 25 |\n"
        f"| Selected checked proof judgements | {coverage['selected_checked_frames']} |\n"
        f"| Explicit explanation gaps | {coverage['explicit_explanation_gaps']} |\n\n"
        'This is a research checkpoint, not a claim that every original obligation or '
        'English explanation is complete. Earlier receipts retain their recorded '
        'environment. Missing work and previous failed attempts remain visible in '
        '`original-verification.html` and its JSON ledger.\n\n'
        'Python/browser and native Lean CI passed on this application commit. '
        'Real offline navigation, the original-verification pages and every site-manifest '
        'entry were checked before publication. Hashes establish consistency, not '
        'authenticity; the English is not formally verified.\n\n'
        f"Application: `{application}`. Upstream: `{release['upstream_commit']}`.\n\n"
        f'Offline ZIP SHA-256: `{checksum}`.\n')
    (output/'notes.md').write_text(notes,encoding='utf-8')
    upload=output/'assets';upload.mkdir()
    for name in ASSETS:
        shutil.copy2(dist/name,upload/name)
    write(upload/'summary.json',summary)
    # No overwrite or clobber flags: an existing release/tag is never replaced.
    existing=subprocess.run(['gh','release','view',tag,'-R',REPO],capture_output=True,text=True,timeout=60)
    if existing.returncode==0:
        raise ValueError('The release already exists; refusing to replace it')
    subprocess.run(['gh','release','create',tag,'-R',REPO,'--target',application,'--prerelease',
        '--title','Leanglish — original-project proof readings','--notes-file',str(output/'notes.md'),
        *[str(upload/name) for name in ASSETS]],check=True,timeout=300)
    # Read back every published byte rather than trusting the upload command alone.
    verify=output/'read-back';verify.mkdir()
    subprocess.run(['gh','release','download',tag,'-R',REPO,'--dir',str(verify)],check=True,timeout=300)
    if {p.name for p in verify.iterdir()}!=set(ASSETS):
        raise ValueError('Published release asset inventory differs from the intended delivery')
    for name in ASSETS:
        if file_hash(verify/name)!=file_hash(upload/name):
            raise ValueError('Published release bytes differ: '+name)
    result={'schema':'leanglish.completion-publication/v1','tag':tag,
        'url':f'https://github.com/{REPO}/releases/tag/{tag}',
        'application_commit':application,'delivery_run':run_id,'artifact_id':artifact_id,
        'artifact_sha256':artifact_sha256,'offline_archive_sha256':checksum,
        'published_assets_read_back_and_verified':True,'summary':summary}
    write(output/'published.json',result)
    print('PUBLISHED_ORIGINAL_READINGS',result,flush=True)
    return result


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run-id',type=int,required=True);p.add_argument('--artifact-id',type=int,required=True)
    p.add_argument('--artifact-sha256',required=True);p.add_argument('--application',required=True)
    p.add_argument('--tag',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-publish',action='store_true')
    a=p.parse_args()
    publish(a.run_id,a.artifact_id,a.artifact_sha256,a.application,a.tag,a.output,allow_publish=a.allow_publish)
    return 0

if __name__=='__main__':raise SystemExit(main())
