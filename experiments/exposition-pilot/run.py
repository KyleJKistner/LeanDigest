#!/usr/bin/env python3
"""Check a finite queue of trusted proof proposals; this is not an autonomous LLM service.

The theorem statement is supplied by the fixed selection, not by the candidate.
No source is executed without --trust-project. Lean elaboration is not sandboxed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def compact_size(source: str) -> int:
    """Non-whitespace characters in the complete candidate declaration block.

    Includes all newly written helpers and signatures, even explanatory lemmas
    not used by the root. This is not a tokenizer or a comprehension score.
    """
    block = source.split('namespace PilotCandidate\n', 1)[1].rsplit('end PilotCandidate', 1)[0]
    return len(re.sub(r'\s+', '', block))


def run(lean: Path, project: Path, output: Path, ids: list[str], timeout: int = 30) -> dict:
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Output must be a new or empty directory')
    selection = json.loads((HERE/'selection.json').read_text())
    rows = json.loads((HERE/'candidates.json').read_text())
    if ids:
        if set(ids) - {r['id'] for r in rows}:
            raise ValueError('Unknown candidate ID')
        rows = [r for r in rows if r['id'] in ids]
    expected = {x['name'] for x in selection['targets']}
    if not rows or any(r['target'] not in expected for r in rows):
        raise ValueError('Candidate must refer to a selected theorem')
    output.mkdir(parents=True, exist_ok=True)
    report = {'schema':'leanglish.exposition-search/v1','status':'failed',
              'selection_sha256':sha(HERE/'selection.json'),
              'checker_sha256':sha(HERE/'PilotAudit.lean'), 'runner_sha256':sha(Path(__file__)),
              'candidate_manifest_sha256':sha(HERE/'candidates.json'),
              'candidate_origin':'model-proposed in the current conversation; finite queue',
              'autonomous_model_calls':0, 'english_certified':False, 'human_study':False,
              'outcomes':[], 'setup':[]}
    try:
        version = subprocess.check_output([str(lean),'--version'],text=True,timeout=10).strip()
        if not version.startswith('Lean (version 4.34.1,'):
            raise ValueError('Wrong Lean version')
        report['lean_version']=version;report['invoked_binary_sha256']=sha(lean)
        original=ROOT/'proofreader/data/bezout-original.lean'
        if sha(original) != selection['targets'][0]['source_sha256']:
            raise ValueError('Original source identity changed')
        report['mathlib_source_hashes']={name:sha(project/name) for name in [
            'lean-toolchain','lake-manifest.json','Mathlib/Logic/Function/Basic.lean']}
        report['environment_note']='Lean and imported binaries are trusted; hashes are consistency records.'
        with tempfile.TemporaryDirectory(prefix='exposition-pilot-') as tmp:
            work=Path(tmp)
            (work/'PilotAudit.lean').write_bytes((HERE/'PilotAudit.lean').read_bytes())
            (work/'BezoutOriginal.lean').write_text(original.read_text().replace(
                'import OAI.Algebra.AffineCancellation.Model',
                'import Mathlib.Algebra.EuclideanDomain.Basic\nimport Mathlib.Tactic.Ring',1))
            paths=[work,project/'.lake/build/lib/lean',*sorted((project/'.lake/packages').glob('*/.lake/build/lib/lean'))]
            env=dict(os.environ,LEAN_PATH=os.pathsep.join(map(str,paths)))
            for module in ('PilotAudit','BezoutOriginal'):
                result=subprocess.run([str(lean),'-o',module+'.olean',module+'.lean'],cwd=work,
                    env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
                (output/(module+'.log')).write_bytes(result.stdout)
                report['setup'].append({'module':module,'returncode':result.returncode})
                if result.returncode:raise ValueError('Setup compilation failed: '+module)
            for row in rows:
                source=(HERE/row['source']).read_text()
                case=output/row['id'];case.mkdir()
                driver=source+f'\nrun_elab PilotAudit.check `{row["target"]} `PilotCandidate.result "accepted.json"\n'
                (case/'Candidate.lean').write_text(driver)
                started=time.monotonic()
                try:
                    result=subprocess.run([str(lean),'Candidate.lean'],cwd=case,env=env,
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
                    log=result.stdout;code=result.returncode;timed_out=False
                except subprocess.TimeoutExpired as exc:
                    log=exc.stdout or b'';code=None;timed_out=True
                (case/'compile.log').write_bytes(log)
                accepted=(code==0 and (case/'accepted.json').is_file()
                          and b'EXPOSITION_PILOT_ACCEPTED' in log)
                observation={**row,'accepted':accepted,'returncode':code,'timed_out':timed_out,
                    'elapsed_seconds':round(time.monotonic()-started,4),
                    'source_sha256':hashlib.sha256(source.encode()).hexdigest(),
                    'declaration_characters':compact_size(source),
                    'log_sha256':sha(case/'compile.log')}
                if accepted:
                    record=json.loads((case/'accepted.json').read_text())
                    if record['expected']!=row['target'] or not record['same_statement_kernel_checked']:
                        raise ValueError('Accepted result does not match requested target')
                    if record['target_in_dependency_closure'] or record['english_certified']:
                        raise ValueError('Invalid acceptance flags')
                    observation['record_sha256']=sha(case/'accepted.json')
                    observation['root_expression_nodes']=record['root_expression_nodes']
                    observation['new_helper_expression_nodes']=sum(x['expression_nodes'] for x in record['helper_inventory'])
                if row['kind']=='control':
                    observation['expected_rejection_observed']=(code is not None and code!=0 and not accepted
                        and row['expected_error'] in log.decode('utf-8',errors='strict'))
                (case/'outcome.json').write_text(json.dumps(observation,indent=2)+'\n')
                report['outcomes'].append(observation)
                print(row['id'], 'accepted' if accepted else 'rejected', flush=True)
            if any(r['kind']=='control' and not r['expected_rejection_observed'] for r in report['outcomes']):
                raise ValueError('A negative control failed for an unexpected reason or was accepted')
            report['status']='completed'
            report['accepted_candidates']=sum(x['accepted'] for x in report['outcomes'] if x['kind']=='candidate')
            report['rejected_candidates']=sum(not x['accepted'] for x in report['outcomes'] if x['kind']=='candidate')
            report['controls_rejected']=sum(x.get('expected_rejection_observed',False) for x in report['outcomes'])
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as exc:
        report['error']=str(exc)
    finally:
        (output/'observation.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lean',required=True,type=Path)
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--only',nargs='*',default=[])
    parser.add_argument('--trust-project',action='store_true')
    args=parser.parse_args()
    if not args.trust_project:parser.error('Lean elaboration executes code; --trust-project is required')
    try:report=run(args.lean.resolve(),args.project.resolve(),args.output.resolve(),args.only)
    except (ValueError,OSError) as exc:parser.error(str(exc))
    return 0 if report['status']=='completed' else 1

if __name__=='__main__':raise SystemExit(main())
