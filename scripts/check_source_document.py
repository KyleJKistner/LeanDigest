#!/usr/bin/env python3
"""Check the complete canonical Bezout proof document in a fresh Lean workspace.

This executes trusted Lean and requires --trust-project. The certificate covers
one specified document grammar, not the separately authored companion prose.
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
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import check_source_cancellation as base
from scripts import check_source_equations as equations

MODULES = ('ControlledEnglish','ControlledEnglishText','ArithmeticEnglish','SourceCancellation',
           'EquationEnglish','SourceEquations','WitnessEnglish','SourceWitnesses',
           'ProofDocumentSyntax','ProofDocument','SourceProofDocument','ProofDocumentAudit')
CONTRACTS = ('parseFragments_chars','read_render','Document.render_injective','Document.sound',
             'rendered_meaning','certify','text_implies_statement','readBytes_render',
             'rendered_bytes_meaning','certifyBytes','bytes_imply_statement')
NEGATIVES = {
    'wrong-case': 'Document case condition mismatch',
    'scope-name': 'Document contains unbound names or different frame inputs',
    'wrong-input': 'Document contains unbound names or different frame inputs',
    'unproved-let': 'Application type mismatch',
    'unproved-alias': 'Application type mismatch',
    'text-tamper': 'Document literal text mismatch',
    'wrong-branch': 'Application type mismatch',
    'kernel-claim': '(kernel) declaration type mismatch',
    'kernel-bypass': '(kernel) declaration type mismatch',
    'missing-equation': 'Incomplete document passage inventory',
    'duplicate-equation': 'Document equation order or inventory mismatch',
    'reordered-equations': 'Document equation order or inventory mismatch',
    'missing-branch': 'Incomplete document passage inventory',
    'swapped-branches': 'Document branch occurrence mismatch',
    'wrong-prerequisite': 'Document cancellation prerequisite mismatch',
    'unknown-variant': 'Unknown document-check variant',
}
ZERO_NAMES = ['R','inst','x','y','z','h','g','hg','hxz']
NONZERO_NAMES = ['R','inst','x','y','z','h','g','hg','a','ha','d','hd','ha','hd','r','s','hbez','hrel']
RESTORED = {'zero_context': {6,8}, 'nonzero_context': {6,12,13,14,15,16,17}}


def encoded(record: dict) -> bytes:
    return (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2)+'\n').encode('utf-8')


def contract_axioms(log: str) -> dict[str, list[str]]:
    if 'sorryAx' in log:
        raise ValueError('Admission in document contracts')
    pattern = r"'ProofReader\.BezoutDocument\.([^']+)' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)"
    found = {}
    for name, raw in re.findall(pattern, log):
        if name in found:
            raise ValueError('Duplicate document contract inventory')
        axioms = [a.strip() for a in raw.split(',') if a.strip()]
        if set(axioms) - base.ALLOWED_AXIOMS:
            raise ValueError('Unpermitted document contract axiom')
        found[name] = axioms
    if set(found) != set(CONTRACTS):
        raise ValueError('Document contract inventory incomplete or unexpected')
    return found


def configuration() -> dict:
    snapshot_path = ROOT/'artifacts/companion/native/current/snapshot.json'
    if base.digest(snapshot_path) != equations.SNAPSHOT_SHA256:
        raise ValueError('Original document snapshot changed')
    frames = json.loads(snapshot_path.read_text())['frames']
    config = {kind: [frames[i]['path'] for i in positions] for kind,positions in
              {**equations.FRAMES,'cancellations':[40,53]}.items()}
    for kind,filename in [('equations','equation-paths.json'),('witnesses','witness-paths.json'),
                          ('cancellations','cancellation-paths.json')]:
        if json.loads((ROOT/'docs/companion'/filename).read_text()) != config[kind]:
            raise ValueError('Document source path manifest changed')
    return config


def validate_record(record: dict, config: dict) -> None:
    if not isinstance(record,dict) or set(record) != {
        'document','skeleton','zero_context','nonzero_context','equations','witnesses','cancellations'}:
        raise ValueError('Document native record schema mismatch')
    for kind in ('equations','witnesses'):
        equations.validate_records(kind, record[kind], config[kind])
    base.validate_records(record['cancellations'],config['cancellations'])
    if sum(r['link_count'] for r in record['equations']) != 19:
        raise ValueError('Document equation link inventory changed')
    d = record['document']
    if (not isinstance(d,dict) or type(d.get('closed_outer_binders')) is not int
            or d['closed_outer_binders'] != 2):
        raise ValueError('Document has residual outer assumptions')
    for key in ('source_statement_kernel_checked','literal_document_kernel_checked','both_branches_composed'):
        if d.get(key) is not True:
            raise ValueError('Incomplete document certificate')
    for key,suffix in [('text_theorem','documentEnglish'),('bytes_theorem','documentUTF8'),
                       ('conclusion_theorem','documentConclusion')]:
        if d.get(key) != base.TARGET+'.'+suffix:
            raise ValueError('Document theorem identity mismatch')
    if not isinstance(d.get('axioms'),list) or set(d['axioms']) - base.ALLOWED_AXIOMS:
        raise ValueError('Unpermitted document axiom')
    data = d.get('utf8')
    if (not isinstance(d.get('text'),str) or not isinstance(data,list)
            or any(type(x) is not int or not 0 <= x <= 255 for x in data)
            or bytes(data) != d['text'].encode('utf-8')):
        raise ValueError('Document text/byte mismatch')
    for key,names in [('zero_context',ZERO_NAMES),('nonzero_context',NONZERO_NAMES)]:
        rows = record[key]
        if (not isinstance(rows,list) or [r.get('index') for r in rows] != list(range(len(names)))
                or [r.get('name') for r in rows] != names):
            raise ValueError('Document scope inventory mismatch')
        for i,row in enumerate(rows):
            wanted = i in RESTORED[key]
            if (row.get('definition_restored') is not wanted
                    or (wanted and not isinstance(row.get('definition'),str))
                    or (not wanted and row.get('definition') is not None)):
                raise ValueError('Source definition not discharged in document scope')
    if record['skeleton'].get('case_path') != [1]*6+[2]:
        raise ValueError('Document case-split identity mismatch')


def mutated_config(config: dict, label: str) -> tuple[dict,str]:
    candidate = json.loads(json.dumps(config))
    variant = label
    if label == 'missing-equation': candidate['equations'].pop(); variant='ok'
    elif label == 'duplicate-equation': candidate['equations'][1]=candidate['equations'][0]; variant='ok'
    elif label == 'reordered-equations': candidate['equations'][0:2]=candidate['equations'][1::-1]; variant='ok'
    elif label == 'missing-branch': candidate['witnesses'].pop(); variant='ok'
    elif label == 'swapped-branches': candidate['witnesses'].reverse(); variant='ok'
    elif label == 'wrong-prerequisite': candidate['cancellations'][0]=[]; variant='ok'
    elif label == 'kernel-bypass': variant='kernel-claim'
    elif label == 'unknown-variant': variant='unsupported'
    return candidate,variant


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',required=True,type=Path)
    parser.add_argument('--lean',default='lean')
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--retained-environment',type=Path)
    parser.add_argument('--trust-project',action='store_true')
    args=parser.parse_args()
    if not args.trust_project: parser.error('Lean execution requires --trust-project')
    project,output=args.project.resolve(),args.output.resolve()
    if output.is_relative_to(project) or project.is_relative_to(output):
        parser.error('Project and evidence directories must be separate')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error('Evidence directory must be new or empty')
    output.mkdir(parents=True,exist_ok=True)
    report={'schema':'leanglish.source-document/v1','status':'failed','commands':[],
            'theorem':base.TARGET,'upstream_commit':base.UPSTREAM,'source_sha256':base.SOURCE_SHA,
            'certified_surface':'bezout-scoped-document/v1',
            'complete_canonical_document_certified':False,'curated_explanation_certified':False,
            'original_project_replayed':False,'html_semantics_proved':False,'receipt_authenticated':False,
            'human_readability_evaluated':False}
    try:
        if base.digest(ROOT/base.SOURCE) != base.SOURCE_SHA: raise ValueError('Original source changed')
        config=configuration()
        report['environment']=base.check_project(project,args.retained_environment)
        binary=shutil.which(args.lean)
        if binary is None: raise ValueError('Lean executable unavailable')
        binary=str(Path(binary).resolve())
        report['executable_sha256']=base.digest(Path(binary))
        report['module_sha256']={n+'.lean':base.digest(ROOT/'lean'/(n+'.lean')) for n in MODULES}
        report['gate_sha256']=base.digest(Path(__file__))
        report['helper_sha256']={n:base.digest(ROOT/'scripts'/n) for n in
                                  ['check_source_cancellation.py','check_source_equations.py']}
        report['configuration']=config
        header='import OAI.Algebra.AffineCancellation.Model\n'
        source=(ROOT/base.SOURCE).read_text()
        if not source.startswith(header): raise ValueError('Original import boundary changed')
        body=source[len(header):]
        report['import_adaptation']={'removed':[header.strip()[7:]],
            'added':['Mathlib.Algebra.EuclideanDomain.Basic','Mathlib.Tactic.Ring','SourceProofDocument'],
            'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'theorem_body_unchanged':True}
        with tempfile.TemporaryDirectory(prefix='leanglish-document-') as temporary:
            work=Path(temporary)
            for name in MODULES:
                shutil.copyfile(ROOT/'lean'/(name+'.lean'),work/(name+'.lean'))
            env=os.environ.copy()
            env['LEAN_PATH']=os.pathsep.join(map(str,[work,project/'.lake/build/lib/lean',
                *sorted((project/'.lake/packages').glob('*/.lake/build/lib/lean'))]))
            def run(label: str,arguments: list[str],expected: str|None=None) -> str:
                entry={'label':label,'arguments':arguments,'returncode':None}
                report['commands'].append(entry)
                try:
                    proc=subprocess.run([binary,'-j1',*arguments],cwd=work,env=env,
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300,check=False)
                except subprocess.TimeoutExpired as exc:
                    (output/(label+'.log')).write_bytes(exc.stdout or b'')
                    entry['timed_out']=True
                    raise ValueError('Native document timeout: '+label) from exc
                log=proc.stdout.decode('utf-8',errors='strict')
                (output/(label+'.log')).write_bytes(proc.stdout)
                entry.update(returncode=proc.returncode,stdout_sha256=hashlib.sha256(proc.stdout).hexdigest())
                if expected is None:
                    if proc.returncode or 'sorryAx' in log or 'declaration uses `sorry`' in log:
                        raise ValueError('Native document check failed: '+label)
                elif proc.returncode == 0 or expected not in log:
                    raise ValueError('Document mutation not rejected for intended reason: '+label)
                entry['expected_outcome_observed']=True
                print(label,proc.returncode,flush=True)
                return log
            version=run('version',['--version']).strip()
            if not version.startswith('Lean (version 4.34.1,'): raise ValueError('Wrong Lean version')
            report['lean_version']=version
            for name in MODULES:
                arguments=[name+'.lean'] if name.endswith('Audit') else ['-o',name+'.olean',name+'.lean']
                log=run(name,arguments)
                if name=='ProofDocument': report['contract_axioms']=contract_axioms(log)
            def driver(label: str,variant: str,selected: dict,expected: str|None=None):
                result=work/(label+'.json'); cfg=work/(label+'-config.json')
                cfg.write_bytes(encoded(selected));(output/(label+'-config.json')).write_bytes(encoded(selected))
                command=f'#source_document "{base.TARGET}" config {json.dumps(str(cfg))} output {json.dumps(str(result))} mode "{variant}"\n'
                if label=='kernel-bypass': command='set_option debug.skipKernelTC true in\n'+command
                program='import Mathlib.Algebra.EuclideanDomain.Basic\nimport Mathlib.Tactic.Ring\nimport SourceProofDocument\n'+body
                program+='\nset_option maxRecDepth 8192\nset_option maxHeartbeats 8000000\n'+command
                (work/(label+'.lean')).write_text(program);(output/(label+'.lean')).write_text(program)
                log=run(label,[label+'.lean'],expected)
                if expected is not None:
                    if result.exists() or 'SOURCE_DOCUMENT_CHECKED:1' in log:
                        raise ValueError('Rejected document emitted a successful record')
                    return None
                if log.count('SOURCE_DOCUMENT_CHECKED:1')!=1:
                    raise ValueError('Missing or repeated document acceptance marker')
                record=json.loads(result.read_text());validate_record(record,config)
                (output/(label+'.json')).write_bytes(encoded(record))
                return record
            first=driver('positive','ok',config)
            repeat=driver('repeat','ok',config)
            if first!=repeat: raise ValueError('Canonical document record did not repeat exactly')
            for label,expected in NEGATIVES.items():
                selected,variant=mutated_config(config,label)
                driver(label,variant,selected,expected)
            assert first is not None
            (output/'proof.txt').write_bytes(bytes(first['document']['utf8']))
            report.update(status='passed',complete_canonical_document_certified=True,
                repeat_byte_identical=True,canonical_document_count=1,source_passage_count=14,
                equation_link_count=19,source_negative_cases=len(NEGATIVES),
                parser_guards=sum(l.lstrip().startswith('#guard ') for l in
                    (ROOT/'lean/ProofDocumentAudit.lean').read_text().splitlines()))
    except (OSError,ValueError,KeyError,TypeError,AttributeError,subprocess.SubprocessError) as exc:
        report['error']=str(exc)
    finally:
        report['files_sha256']={p.name:base.digest(p) for p in sorted(output.iterdir())
                                if p.is_file() and p.name!='observation.json'}
        (output/'observation.json').write_bytes(encoded(report))
    print(json.dumps({'status':report['status'],'output':str(output)}))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':
    raise SystemExit(main())
