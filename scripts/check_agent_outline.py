#!/usr/bin/env python3
"""Exercise the agent outline commands with a real compiler in a fresh directory.

These declarations are protocol regression fixtures, not research results or a
model comparison. The caller supplies a trusted Lean 4.34.1 installation.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from proofreader import outline as o
from proofreader.source_expressions import Expressions

SOURCE = '''import Init
namespace OutlineFixture
theorem pair (P Q : Prop) (hp : P) (hq : Q) : P ∧ Q := And.intro hp hq
theorem result (P Q R : Prop) (hp : P) (hq : Q) (hr : R) : (P ∧ Q) ∧ R := by
  have hpq : P ∧ Q := pair P Q hp hq
  exact And.intro hpq hr
end OutlineFixture
'''


def run(binary: str, output: Path) -> dict:
    if output.exists(): raise ValueError('Use a new evidence directory')
    output.mkdir(parents=True)
    report = {'status': 'failed', 'commands': [], 'rejections': [], 'english_certified': False,
              'independent_model_runs': 0, 'human_evaluation': False}
    project = output / 'project'; project.mkdir()
    source = project / 'OutlineFixture.lean'; source.write_text(SOURCE)
    compiler = shutil.which(binary)
    if not compiler: raise ValueError('Lean executable unavailable')
    compiler = str(Path(compiler).resolve())
    def execute(label, args, expected=0):
        p = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=240)
        (output / (label + '.stdout')).write_bytes(p.stdout)
        (output / (label + '.stderr')).write_bytes(p.stderr)
        report['commands'].append({'label': label, 'arguments': args, 'returncode': p.returncode})
        o.write(output / 'observation.json', report)
        if p.returncode != expected: raise ValueError(f'{label}: unexpected exit {p.returncode}: {p.stderr.decode()}')
        return p
    def compile_fixture(label):
        execute(label, [compiler, '-R', str(project), '-Ddebug.skipKernelTC=false', '-DElab.async=false',
                        '-o', str(project/'OutlineFixture.olean'), str(source)])
    def cli(label, command, session, *extra, expected=0):
        proc = execute(label, [sys.executable, '-m', 'proofreader.outline', command,
                              '--session', str(session), *map(str, extra)], expected)
        return json.loads(proc.stdout if expected == 0 else proc.stderr)
    def node(frame, name):
        return {'id': name, 'frame': frame, 'title': 'Claim', 'text': '', 'children': []}
    def reject(label, session, proposal, message):
        previous = o.read(session/'state.json')['head']; path=output/(label+'.json');o.write(path,proposal)
        row = cli(label, 'check', session, '--proposal', path, '--trust-project', expected=1)
        if message not in row['error']: raise ValueError('Wrong rejection: '+label+': '+row['error'])
        if o.read(session/'state.json')['head'] != previous: raise ValueError('Rejected update changed HEAD')
        report['rejections'].append({'case': label, 'diagnostic': row['error'], 'head_unchanged': True})
    try:
        compile_fixture('compile-fixture')
        heads = []
        for n in range(2):
            session = output/f'session-{n}'
            cli(f'open-{n}', 'open', session, '--lean', compiler, '--module', 'OutlineFixture',
                '--declaration', 'OutlineFixture.result', '--search-path', project, '--trust-project')
            index = cli(f'inspect-{n}', 'inspect', session)
            outer = next(f for f in index['frames'] if f['role']=='have')
            proposal = cli(f'draft-{n}', 'draft', session);proposal['blocks']=[node(outer['frame'],'argument')]
            path=output/f'initial-{n}.json';o.write(path,proposal)
            a=cli(f'check-initial-{n}', 'check', session, '--proposal',path,'--trust-project')
            children=[node(i,'premise-'+str(i)) for i in outer['children']]
            childfile=output/f'children-{n}.json';o.write(childfile,children)
            expanded=cli(f'expand-{n}','expand',session,'--block','argument','--children',childfile)
            expath=output/f'expanded-{n}.json';o.write(expath,expanded)
            b=cli(f'check-expanded-{n}','check',session,'--proposal',expath,'--trust-project')
            assert b['delta']['changed']==[] and b['delta']['removed']==[]
            heads.append([a['revision'],b['revision']])
            execute(f'render-{n}',[sys.executable,'-m','proofreader.outline','render','--session',str(session)])
        assert heads[0]==heads[1]
        assert (output/'render-0.stdout').read_bytes()==(output/'render-1.stdout').read_bytes()
        report['repeat_revisions_identical']=True
        report['repeat_markdown_identical']=True
        session=output/'session-0'; current=o.draft(session)
        reject('stale-parent',session,o.read(output/'initial-0.json'),'Stale outline')
        changed=deepcopy(current);changed['blocks'][0]['claim']='False'
        reject('replacement-claim',session,changed,'Unexpected or missing')
        changed=deepcopy(current);changed['blocks'][0]['children'][0]['frame']=0
        reject('scope-escape',session,changed,'escapes')
        # Test native source replay after bypassing the Python digest comparison.
        # Corrupt matching display fields in both records; neither is accepted
        # as authority for the original loaded declaration.
        original_record=(session/'source.json').read_bytes();original_snapshot=(session/'snapshot.json').read_bytes()
        original_state=o.read(session/'state.json')
        try:
            r=o.read(session/'source.json');s=o.read(session/'snapshot.json')
            r['frames'][0]['display']['claim']='False';s['frames'][0]['statement']='False';s['statement']='False'
            o.write(session/'source.json',r);o.write(session/'snapshot.json',s)
            state=deepcopy(original_state);state['source_sha256']=Expressions(r).sha256
            state['snapshot_sha256']=o.sha(session/'snapshot.json');state['head']=None
            o.write(session/'state.json',state)
            changed=deepcopy(current);changed['parent']=None;changed['source_sha256']=state['source_sha256']
            reject('native-source-forgery',session,changed,'Lean failed: check')
            attempts=sorted((session/'attempts').iterdir(),key=lambda p:p.stat().st_mtime_ns)
            assert 'Outline source changed' in (attempts[-1]/'check.log').read_text()
        finally:
            (session/'source.json').write_bytes(original_record)
            (session/'snapshot.json').write_bytes(original_snapshot)
            o.write(session/'state.json',original_state)
        index=o.inventory(session)
        call=next(f for f in index['frames'] if f['called_declaration']==o.named('OutlineFixture.pair'))
        followed=cli('follow','follow',session,'--frame',call['frame'],'--destination',output/'followed','--trust-project')
        assert followed['origin']['called_declaration']==o.named('OutlineFixture.pair')
        report['followed_actual_callee']=True
        # A dependency body changes while the target statement and target body
        # remain unchanged. The module fingerprint must still invalidate the run.
        source.write_text(SOURCE.replace(':= And.intro hp hq', ':= (fun h : P => And.intro h hq) hp'))
        compile_fixture('compile-changed-dependency')
        reject('changed-dependency',session,o.draft(session),'environment changed')
        report['accepted_revisions']=4;report['status']='passed'
    except Exception as exc:
        report['error']=str(exc)
    finally:
        o.write(output/'observation.json',report)
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--lean',required=True)
    p.add_argument('--output',required=True,type=Path);p.add_argument('--trust-project',action='store_true')
    a=p.parse_args()
    if not a.trust_project:p.error('--trust-project is required')
    result=run(a.lean,a.output.resolve());print(json.dumps({k:v for k,v in result.items() if k!='commands'},indent=2))
    return 0 if result['status']=='passed' else 1
if __name__=='__main__':raise SystemExit(main())
