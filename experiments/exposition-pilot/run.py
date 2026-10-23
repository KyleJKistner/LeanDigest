#!/usr/bin/env python3
"""Bounded candidate checking for the three-proof exposition pilot.

Candidates are trusted Lean source, not sandboxed code. The manifest supplies
proposals; this runner does not call a model or certify the English presentation.
Every candidate starts in a fresh Lean process. Outputs must be new directories.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
REFERENCES = {'bezout': 'OAI.ComplexCancellation.BezoutFrame.exists_frame',
              'reverse': 'List.reverse_reverse', 'cantor': 'Function.cantor_surjective'}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def environment(project: Path, work: Path) -> dict[str, str]:
    paths = [work, project/'.lake/build/lib/lean',
             *sorted((project/'.lake/packages').glob('*/.lake/build/lib/lean'))]
    if not paths[1].is_dir():
        raise ValueError('Expected a built Mathlib project')
    return {**os.environ, 'LEAN_PATH': ':'.join(map(str, paths))}

def run(lean: str, project: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError('Output directory already exists; retained attempts are not overwritten')
    binary = shutil.which(lean)
    if binary is None: raise ValueError('Lean executable was not found')
    output.mkdir(parents=True)
    work = output/'workspace'; work.mkdir()
    logs = output/'logs'; logs.mkdir()
    env = environment(project.resolve(), work.resolve())
    observation = {'schema':'leanglish.proof-pilot/v1', 'status':'failed',
        'candidate_origin':'model-authored in this session; finite proposal set',
        'automated_model_search':False, 'human_evaluation':False,
        'english_certified':False, 'commands':[], 'candidates':[],
        'expected_mathlib_commit':'d13f23b723b8a846827a245b89c10fc7d3f11612',
        'runtime_lean_sha256':sha(Path(binary).resolve())}
    def command(label, args):
        started=time.monotonic()
        try:
            p=subprocess.run([binary,*args],cwd=work,env=env,
                             capture_output=True,text=True,timeout=120)
            code,text=p.returncode,p.stdout+p.stderr
        except subprocess.TimeoutExpired as exc:
            code,text=124,str(exc)
        (logs/(label+'.log')).write_text(text)
        observation['commands'].append({'label':label,'args':args,'exit_code':code,
            'seconds':round(time.monotonic()-started,3),'log_sha256':sha(logs/(label+'.log'))})
        return code,text
    try:
        rc,ver=command('version',['--version'])
        if rc or not ver.startswith('Lean (version 4.34.1,'):
            raise ValueError('Expected Lean 4.34.1')
        observation['lean_version']=ver.strip()
        for name in ['OriginalBezout','PilotAudit']:
            shutil.copyfile(ROOT/(name+'.lean'),work/(name+'.lean'))
            rc,text=command('compile-'+name,['-o',name+'.olean',name+'.lean'])
            if rc:raise ValueError('Compilation failed: '+name)
        inputs=json.loads((ROOT/'candidates.json').read_text())
        if len({x['id'] for x in inputs})!=len(inputs):raise ValueError('Duplicate candidate ID')
        rows=[dict(id=t+'-original',target=t,variant='original',file=None,
                   expected='accept',reason=None) for t in REFERENCES]+inputs
        all_ok=True
        for row in rows:
            original=row['variant']=='original'
            if row['target'] not in REFERENCES:raise ValueError('Unknown target')
            if original:
                source='import OriginalBezout\nimport Mathlib.Logic.Function.Basic\nimport PilotAudit\n'
            else:
                path=(ROOT/'candidates'/row['file']).resolve()
                if path.parent != (ROOT/'candidates').resolve():raise ValueError('Candidate path escapes input directory')
                source=path.read_text()
            ref=REFERENCES[row['target']]
            name=ref if original else 'Candidate.result'
            forbidden='#[]' if original else '#[`'+ref+']'
            driver=source+'\nrun_meta do\n  let j ← Leanglish.Pilot.check `'+name+' `'+ref+' '+forbidden+'\n  Lean.logInfo ("PILOT_RESULT:" ++ j.compress)\n'
            path=work/(row['id'].replace('-','_')+'.lean');path.write_text(driver)
            rc,text=command(row['id'],[path.name])
            marks=[line.split('PILOT_RESULT:',1)[1] for line in text.splitlines() if 'PILOT_RESULT:' in line]
            record={**row,'exit_code':rc,'source_sha256':sha(path),
                    'accepted':rc==0 and len(marks)==1,'source':source}
            if record['accepted']:
                record['audit']=json.loads(marks[0])
                if not record['audit']['kernel_checked']:raise ValueError('Missing kernel result')
            expected=row['expected']=='accept'
            record['expected_outcome']=record['accepted']==expected
            if not expected:
                reason='unsolved goals' if row['reason']=='elaboration' else row['reason']
                record['intended_rejection']=reason in text
                record['expected_outcome'] &= record['intended_rejection']
            all_ok &= record['expected_outcome']
            observation['candidates'].append(record)
        observation['accepted_count']=sum(r['accepted'] for r in observation['candidates'])
        observation['negative_controls']=sum(r['expected']=='reject' and r['expected_outcome'] for r in observation['candidates'])
        observation['status']='passed' if all_ok else 'failed'
    except (ValueError,OSError,KeyError) as exc:
        observation['error']=str(exc)
    finally:
        observation['input_sha256']={str(p.relative_to(ROOT)):sha(p) for p in sorted(ROOT.rglob('*'))
            if p.is_file() and p.suffix in {'.lean','.json','.py'} and '__pycache__' not in p.parts}
        (output/'observation.json').write_text(json.dumps(observation,indent=2,sort_keys=True)+'\n')
    return observation

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lean',default='lean');p.add_argument('--project',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--trust-project',action='store_true')
    a=p.parse_args()
    if not a.trust_project:p.error('Lean execution requires --trust-project')
    try:
        r=run(a.lean,a.project,a.output.resolve());print(json.dumps({k:r[k] for k in ['status','accepted_count','negative_controls'] if k in r}))
        return 0 if r['status']=='passed' else 1
    except (ValueError,OSError) as exc:
        print(str(exc));return 1
if __name__=='__main__':raise SystemExit(main())
