"""Download the dependency-cone artifacts of one workflow run and check their digests.

The run's artifact listing comes from the GitHub API through `gh api`. The plan,
summary and in-scope shard artifacts that the committed plan names are
downloaded as zips. Each zip's SHA-256 and size must equal the values the API
records before the zip is extracted, and extraction rejects unsafe paths, links
and oversized archives. The output directory then has the layout that
`scripts/rerender_catalog.py --cone-shards` and `plan_dependency_cone.py
reconcile` read, plus `cone-artifacts.json`. Nothing is executed. A matching
digest shows that the download is the artifact GitHub stored; it does not
authenticate the observations in it. On any failure the output directory is
removed and the exit status is 1, with the reason on the last line of stderr.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.cone_catalog import PLAN
from proofreader.dependency_cone import scope_shards, validate_plan
from proofreader.kernel_io import strict_json
from scripts.collect_original_evidence import unpack

SCHEMA='leanglish.cone-artifact-download/v1'
RECORD='cone-artifacts.json'  # scripts/rerender_catalog.py ARTIFACTS
SUMMARY_ARTIFACT='cone-summary-level-1'
COMMITTED=Path(__file__).resolve().parents[1]/'benchmarks/dependency-cone/plan.json'
REPOSITORY=re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+')
DIGEST=re.compile(r'sha256:[0-9a-f]{64}')


def expected(plan: dict, scope: str) -> list[str]:
    """The plan artifact, the summary artifact and one artifact per in-scope shard (dependency-cone.yml)."""
    return [PLAN,SUMMARY_ARTIFACT,*('dependency-cone-'+s['id'] for s in scope_shards(plan,scope))]


def run_gh(args: list[str]) -> bytes:
    result=subprocess.run(['gh','api',*args],capture_output=True,timeout=900,check=False)
    if result.returncode!=0:
        raise RuntimeError('gh api '+args[0]+' failed: '+result.stderr.decode('utf-8','replace').strip()[-500:])
    return result.stdout


def select(listing: dict, names: list[str], run_id: int) -> list[dict]:
    """Exactly one unexpired artifact of this run per expected name, each with a recorded digest."""
    artifacts=listing.get('artifacts') if isinstance(listing,dict) else None
    if not isinstance(artifacts,list) or listing.get('total_count')!=len(artifacts):
        raise ValueError('Incomplete artifact listing for run '+str(run_id))
    found={}
    for a in artifacts:
        if isinstance(a,dict) and a.get('name') in names:
            if a['name'] in found:raise ValueError('Duplicate artifact name: '+a['name'])
            found[a['name']]=a
    missing=[n for n in names if n not in found]
    if missing:raise ValueError('Run '+str(run_id)+' lacks the artifacts: '+', '.join(missing))
    for a in found.values():
        if (a.get('workflow_run') or {}).get('id')!=run_id:raise ValueError('Artifact '+a['name']+' belongs to another run')
        if a.get('expired') is not False:raise ValueError('Artifact '+a['name']+' expired at '+str(a.get('expires_at')))
        if not DIGEST.fullmatch(str(a.get('digest'))) or type(a.get('size_in_bytes')) is not int or type(a.get('id')) is not int:
            raise ValueError('GitHub records no digest or size for artifact '+a['name'])
    return [found[n] for n in names]


def download(repo: str, run_id: int, output: Path, *, plan: dict, scope: str = 'pilot', gh=None) -> dict:
    """``gh`` takes `gh api` arguments and returns the response body (default: run_gh)."""
    gh=gh or run_gh
    if not REPOSITORY.fullmatch(repo) or type(run_id) is not int or run_id<=0:raise ValueError('Invalid repository or run')
    if output.exists():raise ValueError('Use a new output directory')
    validate_plan(plan)
    chosen=select(strict_json(gh(['repos/'+repo+'/actions/runs/'+str(run_id)+'/artifacts?per_page=100'])),expected(plan,scope),run_id)
    output.mkdir(parents=True);staging=output.parent/(output.name+'.zips');staging.mkdir()
    try:
        rows=[]
        for a in chosen:
            data=gh(['repos/'+repo+'/actions/artifacts/'+str(a['id'])+'/zip'])
            actual='sha256:'+hashlib.sha256(data).hexdigest()
            if actual!=a['digest'] or len(data)!=a['size_in_bytes']:
                raise ValueError('Artifact '+a['name']+' differs from the digest GitHub records: expected '+a['digest']+', downloaded '+actual)
            archive=staging/(a['name']+'.zip');archive.write_bytes(data)
            unpack(archive,output/a['name']);archive.unlink()
            rows.append({k:a.get(k) for k in ('name','id','digest','size_in_bytes','created_at','expires_at')})
        record={'schema':SCHEMA,'repository':repo,'run_id':run_id,'scope':scope,'plan_sha256':plan['plan_sha256'],
                'artifacts':rows,'digests_matched':True,'observations_authenticated':False}
        (output/RECORD).write_text(json.dumps(record,indent=2,sort_keys=True)+'\n',encoding='utf-8')
        return record
    except BaseException:
        shutil.rmtree(output,ignore_errors=True);raise
    finally:
        shutil.rmtree(staging,ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('--repo',required=True,help='owner/name')
    p.add_argument('--run',required=True,type=int,help='Workflow run ID of dependency-cone.yml')
    p.add_argument('--output',required=True,type=Path,help='New directory for the extracted artifacts')
    p.add_argument('--scope',default='pilot')
    p.add_argument('--cone-plan',type=Path,default=COMMITTED,help='Plan that names the shard artifacts (default: the committed plan)')
    a=p.parse_args(argv)
    try:
        record=download(a.repo,a.run,a.output,plan=strict_json(a.cone_plan.read_text(encoding='utf-8')),scope=a.scope)
    except (ValueError,RuntimeError,OSError,subprocess.SubprocessError) as exc:
        print('Dependency-cone artifacts not downloaded: '+' '.join(str(exc).split()),file=sys.stderr);return 1
    print(json.dumps({'run_id':record['run_id'],'artifacts':len(record['artifacts']),'digests_matched':True},indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
