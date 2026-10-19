#!/usr/bin/env python3
"""Kernel-check source equation chains and witness tuples in a pinned environment.

The trusted importer preserves the source occurrences and contexts. Every chain
link and witness is checked; a passed run does not certify the entire companion.
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

MODULES = ('ControlledEnglish', 'ControlledEnglishText', 'ArithmeticEnglish',
           'SourceCancellation', 'EquationEnglish', 'SourceEquations',
           'WitnessEnglish', 'SourceWitnesses', 'EquationEnglishAudit', 'WitnessEnglishAudit')
CONTRACTS = {
    'EquationEnglish': ('Chain.endpoints', 'parseChain_chars', 'read_render',
        'Chain.render_injective', 'rendered_meaning', 'certify', 'readBytes_render',
        'rendered_bytes_meaning', 'certifyBytes'),
    'WitnessEnglish': ('parseFrame_chars', 'read_render', 'Frame.render_injective',
        'Frame.witnesses', 'rendered_meaning', 'certify', 'readBytes_render',
        'rendered_bytes_meaning', 'certifyBytes'),
}
SNAPSHOT_SHA256 = '7f0e3b36ec46ec3b5cf7ec660a627fb0bb3020b096b984af2f433bf8ce43a69f'
FRAMES = {'equations': [18,20,22,23,45,58,68,70,78,79], 'witnesses': [13,63]}
CONFIG = {'equations': ('SourceEquations','equation-paths.json'),
          'witnesses': ('SourceWitnesses','witness-paths.json')}
NEGATIVES = {
    'equations': {
        'proof-replacement': 'Original equation occurrence mismatch',
        'wrong-label-map': '(kernel) declaration type mismatch',
        'wrong-operation': '(kernel) declaration type mismatch',
        'wrong-chain': '(kernel) declaration type mismatch',
        'text-tamper': 'Equation text alignment mismatch',
        'kernel-claim-tamper': '(kernel) declaration type mismatch',
        'kernel-flag-bypass': '(kernel) declaration type mismatch',
        'scope-escape': 'Escaped source-local binder',
        'drop-link': 'Original equation link inventory mismatch',
        'reverse-links': 'Original equation link inventory mismatch',
        'duplicate-link': 'Original equation link inventory mismatch',
        'unknown-mode': 'Unknown equation-check variant',
        'wrong-path': 'Expected a source equality',
        'duplicate-path': 'Duplicate equation source path',
        'missing-path': 'Expected ten original equation paths',
    },
    'witnesses': {
        'proof-replacement': 'Original witness occurrence mismatch',
        'wrong-label-map': '(kernel) declaration type mismatch',
        'wrong-operation': '(kernel) declaration type mismatch',
        'wrong-witness': '(kernel) declaration type mismatch',
        'swap-witnesses': '(kernel) declaration type mismatch',
        'text-tamper': 'Witness text alignment mismatch',
        'kernel-claim-tamper': '(kernel) declaration type mismatch',
        'kernel-flag-bypass': '(kernel) declaration type mismatch',
        'scope-escape': 'Escaped source-local binder',
        'unknown-mode': 'Unknown witness-check mode',
        'wrong-path': 'Expected four explicit source witnesses',
        'duplicate-path': 'Duplicate witness source path',
        'missing-path': 'Expected both original witness branches',
    },
}


def checked_axioms(module: str, text: str) -> dict[str, list[str]]:
    if 'sorryAx' in text or 'declaration uses `sorry`' in text:
        raise ValueError('Admission in equation contracts')
    prefix = f'ProofReader.{module}.'
    found: dict[str, list[str]] = {}
    pattern = "'" + re.escape(prefix) + r"([^']+)' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)"
    for name, raw in re.findall(pattern, text):
        if name in found:
            raise ValueError('Duplicate equation contract inventory')
        axioms = [a.strip() for a in raw.split(',') if a.strip()]
        if set(axioms) - base.ALLOWED_AXIOMS:
            raise ValueError('Unpermitted equation contract axiom')
        found[name] = axioms
    if set(found) != set(CONTRACTS[module]):
        raise ValueError('Equation contract inventory incomplete or unexpected')
    return found


def validate_records(kind: str, records: list, paths: list) -> None:
    count = len(FRAMES[kind])
    if (not isinstance(records, list) or len(records) != count
            or [r.get('index') for r in records] != list(range(count))
            or [r.get('path') for r in records] != paths):
        raise ValueError('Source record inventory mismatch')
    for record in records:
        if (record.get('literal_string_kernel_checked') is not True
                or record.get('source_ast_identity_checked') is not True
                or set(record['axioms']) - base.ALLOWED_AXIOMS):
            raise ValueError('Incomplete source equation certificate')
        if bytes(record['utf8']) != record['text'].encode('utf-8'):
            raise ValueError('Native equation text/byte mismatch')
        prefix = base.TARGET + ('.equationText.' if kind == 'equations' else '.witnessText.')
        if any(record[key] != prefix + str(record['index']) + suffix
               for key, suffix in [('text_theorem','.english'),('bytes_theorem','.utf8')]):
            raise ValueError('Source theorem identity mismatch')
        context = record['context']
        if [row['binder_index'] for row in context] != list(range(len(context))):
            raise ValueError('Source context index mismatch')
        if kind == 'equations':
            links = record['links']
            if (record.get('all_adjacent_equalities_checked') is not True or not links
                    or type(record['link_count']) is not int or record['link_count'] != len(links)
                    or record['term_count'] != len(links) + 1
                    or [link['index'] for link in links] != list(range(len(links)))):
                raise ValueError('Incomplete equation link inventory')
            if any(link['path'][:len(record['path'])] != record['path'] for link in links):
                raise ValueError('Equation link escapes its source node')
            if len({tuple(link['path']) for link in links}) != len(links):
                raise ValueError('Duplicated equation link')
        else:
            root = record['path']
            expected = [root + [1]*i + [0,1] for i in range(4)]
            if (record.get('all_four_witnesses_checked') is not True
                    or record['witness_paths'] != expected
                    or record['conjunction_path'] != root + [1]*4
                    or record['existence_theorem'] != prefix + str(record['index']) + '.existence'):
                raise ValueError('Original witness inventory mismatch')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--lean', default='lean')
    parser.add_argument('--retained-environment', type=Path)
    parser.add_argument('--trust-project', action='store_true')
    args = parser.parse_args()
    if not args.trust_project:
        parser.error('Lean execution requires --trust-project')
    project, output = args.project.resolve(), args.output.resolve()
    if output.is_relative_to(project) or project.is_relative_to(output):
        parser.error('Project and evidence directories must be separate')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error('Evidence directory must be new or empty')
    output.mkdir(parents=True, exist_ok=True)
    report = {'schema':'leanglish.source-equations/v1', 'status':'failed',
        'theorem':base.TARGET, 'upstream_commit':base.UPSTREAM, 'commands':[],
        'complete_english_proof_certified':False, 'original_project_replayed':False,
        'html_semantics_proved':False, 'receipt_authenticated':False,
        'certified_passage_count':0}
    (output/'observation.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    try:
        if base.digest(ROOT / base.SOURCE) != base.SOURCE_SHA:
            raise ValueError('Original source identity mismatch')
        report['source_sha256'] = base.SOURCE_SHA
        report['environment'] = base.check_project(project, args.retained_environment)
        binary = shutil.which(args.lean)
        if binary is None:
            raise ValueError('Lean executable unavailable')
        binary = str(Path(binary).resolve())
        report['executable_sha256'] = base.digest(Path(binary))
        report['module_sha256'] = {n + '.lean':base.digest(ROOT / 'lean' / (n + '.lean')) for n in MODULES}
        report['gate_sha256'] = base.digest(Path(__file__))
        report['environment_checker_sha256'] = base.digest(Path(base.__file__))
        snapshot = ROOT / 'artifacts/companion/native/current/snapshot.json'
        if base.digest(snapshot) != SNAPSHOT_SHA256:
            raise ValueError('Pinned source snapshot changed')
        report['snapshot_file_sha256'] = SNAPSHOT_SHA256
        frames = json.loads(snapshot.read_text())['frames']
        paths = {k:json.loads((ROOT / 'docs/companion' / CONFIG[k][1]).read_text()) for k in CONFIG}
        if any(paths[k] != [frames[i]['path'] for i in FRAMES[k]] for k in CONFIG):
            raise ValueError('Original equation paths changed')
        report['source_frames'] = FRAMES
        with tempfile.TemporaryDirectory(prefix='leanglish-source-equations-') as tmp:
            work = Path(tmp)
            for name in MODULES:
                shutil.copyfile(ROOT / 'lean' / (name + '.lean'), work / (name + '.lean'))
            env = os.environ.copy()
            env['LEAN_PATH'] = os.pathsep.join(map(str,[work, project/'.lake/build/lib/lean',
                *sorted((project/'.lake/packages').glob('*/.lake/build/lib/lean'))]))
            def run(label: str, arguments: list[str], expected: str | None = None) -> str:
                entry = {'label':label, 'arguments':arguments, 'returncode':None}
                report['commands'].append(entry)
                try:
                    proc = subprocess.run([binary,*arguments],cwd=work,env=env,
                        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180,check=False)
                except subprocess.TimeoutExpired as exc:
                    (output/(label+'.log')).write_bytes(exc.stdout or b'')
                    entry['timed_out'] = True
                    raise ValueError(f'Native timeout: {label}') from exc
                text = proc.stdout.decode('utf-8',errors='strict')
                (output/(label+'.log')).write_bytes(proc.stdout)
                entry.update(returncode=proc.returncode,stdout_sha256=hashlib.sha256(proc.stdout).hexdigest())
                if expected is None:
                    if proc.returncode != 0 or 'sorryAx' in text or 'declaration uses `sorry`' in text:
                        raise ValueError(f'Native check failed: {label}')
                elif proc.returncode == 0 or expected not in text:
                    raise ValueError(f'Mutation not rejected for the intended reason: {label}')
                entry['expected_outcome_observed'] = True
                return text
            version = run('version',['--version']).strip()
            if not version.startswith('Lean (version 4.34.1,'):
                raise ValueError('Wrong Lean version')
            report['lean_version'] = version
            report['contract_axioms'] = {}
            for name in MODULES:
                arguments = [name+'.lean'] if name.endswith('Audit') else ['-o',name+'.olean',name+'.lean']
                log = run(name,arguments)
                if name in CONTRACTS:
                    report['contract_axioms'][name] = checked_axioms(name,log)
            source = (ROOT/base.SOURCE).read_text()
            header = 'import OAI.Algebra.AffineCancellation.Model\n'
            if not source.startswith(header): raise ValueError('Original import boundary changed')
            body = source[len(header):]
            report['import_adaptation'] = {'removed':[header.strip()[7:]],
                'added':['Mathlib.Algebra.EuclideanDomain.Basic','Mathlib.Tactic.Ring',
                         'SourceEquations','SourceWitnesses'],
                'body_sha256':hashlib.sha256(body.encode()).hexdigest(), 'theorem_body_unchanged':True}
            def driver(kind: str, label: str, variant: str, selected: list, expected: str | None = None):
                prefix = kind+'-'+label
                pathfile = work/(prefix+'-paths.json')
                pathfile.write_text(json.dumps(selected))
                result = work/(prefix+'.json')
                command = f'#source_{kind} "{base.TARGET}" paths {json.dumps(str(pathfile))} output {json.dumps(str(result))} mode "{variant}"\n'
                if label == 'kernel-flag-bypass':
                    command = 'set_option debug.skipKernelTC true in\n'+command
                program = 'import Mathlib.Algebra.EuclideanDomain.Basic\nimport Mathlib.Tactic.Ring\nimport '+CONFIG[kind][0]+'\n'+body+'\n'+command
                filename = prefix+'.lean'
                (work/filename).write_text(program)
                (output/filename).write_text(program)
                log = run(prefix,[filename],expected)
                if expected is not None:
                    if result.exists(): raise ValueError('Rejected check emitted a certificate')
                    return None
                if log.count(f'SOURCE_{kind.upper()}_CHECKED:{len(FRAMES[kind])}') != 1:
                    raise ValueError('Native positive marker missing or duplicated')
                data = json.loads(result.read_text())
                validate_records(kind,data,paths[kind])
                (output/(prefix+'.json')).write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
                return data
            observed_records = {}
            for kind in CONFIG:
                first = driver(kind,'positive','ok',paths[kind])
                again = driver(kind,'repeat','ok',paths[kind])
                if first != again: raise ValueError('Source text did not repeat exactly')
                for label,error in NEGATIVES[kind].items():
                    selected = list(paths[kind])
                    if label == 'wrong-path': selected[0] = []
                    if label == 'duplicate-path': selected[1] = selected[0]
                    if label == 'missing-path': selected.pop()
                    variant = 'ok' if label.endswith('-path') else 'kernel-claim-tamper' if label == 'kernel-flag-bypass' else label
                    driver(kind,label,variant,selected,error)
                assert first is not None
                observed_records[kind] = first
                for i,row in enumerate(first): (output/f'{kind}-{i}.txt').write_bytes(bytes(row['utf8']))
            adjacent = sum(len(row['links']) for row in observed_records['equations'])
            if adjacent != 19:
                raise ValueError('Original adjacent equality inventory changed')
            report.update(status='passed',certified_passage_count=12,
                certified_equation_chain_count=10,certified_witness_tuple_count=2,
                adjacent_source_equalities=adjacent,repeat_byte_identical=True,
                native_negative_cases=sum(len(n) for n in NEGATIVES.values()),
                native_parser_guards=sum(line.lstrip().startswith('#guard ') for name in
                    ['EquationEnglishAudit','WitnessEnglishAudit'] for line in
                    (ROOT/'lean'/(name+'.lean')).read_text().splitlines()))
    except (OSError,ValueError,KeyError,TypeError,AttributeError,subprocess.SubprocessError) as exc:
        report['error'] = str(exc)
    finally:
        report['files_sha256'] = {p.name:base.digest(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != 'observation.json'}
        (output/'observation.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'passages':report['certified_passage_count'],'output':str(output)}))
    return 0 if report['status']=='passed' else 1

if __name__ == '__main__':
    raise SystemExit(main())
