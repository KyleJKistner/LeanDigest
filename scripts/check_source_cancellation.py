#!/usr/bin/env python3
"""Check the two original Bézout cancellation sentences and retain native evidence.

Lean elaboration executes code. Requires --trust-project and a new evidence
folder. This certifies only the two literal sentences, not the complete reader.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
MATHLIB = 'd13f23b723b8a846827a245b89c10fc7d3f11612'
UPSTREAM = '1581d4cbdd69a0faf34b2089614fe2a814316a6a'
SOURCE = 'examples/openai/lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean'
SOURCE_SHA = 'd108afa98f200bfce183b8afc0af586b70734f7ad2cce1bc5e49853a2f555c6f'
TARGET = 'OAI.ComplexCancellation.BezoutFrame.exists_frame'
ARCHIVE_SHA = 'b5d80a41ea2961052c55a09cfffc26c399d08efe9c3599a9bf27501d63c2f779'
# Retained Actions artifact 12202194378 from run 39285448721. Optional offline
# path verifies EVERY extracted project file, not just a commit-name text file.
MODULES = ('ControlledEnglish.lean', 'ControlledEnglishText.lean',
           'ArithmeticEnglish.lean', 'SourceCancellation.lean', 'ArithmeticEnglishAudit.lean')
CONTRACTS = ('parseTerm_chars', 'parseCancellation_chars', 'readCancellation_render',
             'Cancellation.render_injective', 'rendered_meaning', 'certify',
             'readBytes_render', 'rendered_bytes_meaning', 'certifyBytes')
NEGATIVES = {
    'wrong-nonzero': 'Application type mismatch',
    'wrong-premise': 'Application type mismatch',
    'wrong-conclusion': 'Application type mismatch',
    'text-tamper': 'English sentence alignment mismatch',
    'wrong-label-map': 'Arithmetic denotation mismatch',
    'wrong-operation': 'Arithmetic denotation mismatch',
    'proof-replacement': 'Original proof occurrence mismatch',
    'unknown-mode': 'Unknown source-check mode',
    'kernel-claim-tamper': '(kernel) declaration type mismatch',
    'kernel-flag-bypass': '(kernel) declaration type mismatch',
    'wrong-path': 'Expected a fully applied source mul_left_cancel₀ node',
    'duplicate-path': 'Duplicate original proof path',
}
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_archive(project: Path, archive: Path) -> dict:
    if digest(archive) != ARCHIVE_SHA:
        raise ValueError('Retained environment archive identity mismatch')
    expected: set[str] = set()
    with ZipFile(archive) as z:
        data = z.read('part-aa')
        expected_digest = z.read('SHA256SUMS').decode().split()[0]
        if hashlib.sha256(data).hexdigest() != expected_digest:
            raise ValueError('Retained environment payload mismatch')
        if z.read('mathlib-commit.txt').decode().strip() != MATHLIB:
            raise ValueError('Retained environment commit mismatch')
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
            for item in tar:
                if item.isdir():
                    continue
                if not (item.isfile() or item.issym()) or not item.name.startswith('mathlib/'):
                    raise ValueError('Unexpected environment archive member')
                relative = item.name[len('mathlib/'):]
                path = project / relative
                if not path.resolve().is_relative_to(project):
                    raise ValueError('Environment path escapes project')
                if item.issym():
                    if not path.is_symlink() or os.readlink(path) != item.linkname:
                        raise ValueError('Retained environment symlink mismatch')
                    expected.add(relative)
                    continue
                if path.is_symlink():
                    raise ValueError('File replaced by symlink')
                member = tar.extractfile(item)
                assert member is not None
                wanted = hashlib.file_digest(member, 'sha256').hexdigest()
                if not path.is_file() or digest(path) != wanted:
                    raise ValueError(f'Changed retained environment file: {relative}')
                expected.add(relative)
    actual = {p.relative_to(project).as_posix() for p in project.rglob('*') if p.is_file() or p.is_symlink()}
    if actual != expected:
        raise ValueError('Extra or missing files in retained environment')
    return {'kind': 'retained-actions-archive', 'archive_sha256': ARCHIVE_SHA,
            'run_id': 39285448721, 'artifact_id': 12202194378,
            'files_checked': len(expected), 'mathlib_commit': MATHLIB}


def check_project(project: Path, archive: Path | None) -> dict:
    if archive is not None:
        return check_archive(project, archive)
    def git(path: Path, *args: str) -> str:
        return subprocess.check_output(['git', *args], cwd=path, text=True, timeout=20).strip()
    if git(project, 'rev-parse', 'HEAD') != MATHLIB:
        raise ValueError('Mathlib checkout is not the pinned revision')
    if git(project, 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('Mathlib tracked sources changed')
    manifest = json.loads((project / 'lake-manifest.json').read_text())
    revisions = []
    for item in manifest['packages']:
        path = project / manifest['packagesDir'] / item['name']
        if git(path, 'rev-parse', 'HEAD') != item['rev'] or git(path, 'status', '--porcelain', '--untracked-files=no'):
            raise ValueError(f"Dependency differs from its pin: {item['name']}")
        revisions.append({'name': item['name'], 'commit': item['rev']})
    return {'kind': 'pinned-git-checkout', 'mathlib_commit': MATHLIB, 'dependencies': revisions}


def checked_axioms(text: str) -> dict:
    if 'sorryAx' in text:
        raise ValueError('Admission in arithmetic contracts')
    prefix = 'ProofReader.ArithmeticEnglish.'
    found = {}
    pattern = r"'ProofReader\.ArithmeticEnglish\.([^']+)' depends on axioms: \[([^\]]*)\]"
    for name, raw in re.findall(pattern, text):
        if name in found:
            raise ValueError('Duplicate contract inventory')
        axioms = [word.strip() for word in raw.split(',') if word.strip()]
        if set(axioms) - ALLOWED_AXIOMS:
            raise ValueError('Unpermitted arithmetic contract axiom')
        found[name] = axioms
    if set(found) != set(CONTRACTS):
        raise ValueError('Arithmetic contract inventory incomplete or unexpected')
    return found


def validate_records(records: list, paths: list) -> None:
    if len(records) != 2 or [r['index'] for r in records] != [0, 1]:
        raise ValueError('Expected precisely two certified source sentences')
    if [r['path'] for r in records] != paths:
        raise ValueError('Sentence/source occurrence mismatch')
    for record in records:
        if not record.get('literal_string_kernel_checked') or not record.get('source_ast_identity_checked'):
            raise ValueError('Incomplete source certificate')
        if set(record['axioms']) - ALLOWED_AXIOMS:
            raise ValueError('Unpermitted source sentence axiom')
        if bytes(record['utf8']) != record['text'].encode('utf-8'):
            raise ValueError('Native text/byte mismatch')
        if not record['text_theorem'].startswith(TARGET + '.sourceText.'):
            raise ValueError('Wrong certificate declaration')


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
    report = {'schema': 'leanglish.source-cancellation/v1', 'status': 'failed',
              'theorem': TARGET, 'upstream_commit': UPSTREAM, 'commands': [],
              'complete_english_proof_certified': False, 'original_project_replayed': False,
              'receipt_authenticated': False, 'html_semantics_proved': False,
              'certified_sentence_count': 0}
    (output / 'observation.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    try:
        original = ROOT / SOURCE
        if digest(original) != SOURCE_SHA:
            raise ValueError('Original source identity mismatch')
        report['source_sha256'] = SOURCE_SHA
        report['environment'] = check_project(project, args.retained_environment)
        binary = shutil.which(args.lean)
        if binary is None:
            raise ValueError('Lean executable unavailable')
        report['executable_sha256'] = digest(Path(binary).resolve())
        report['module_sha256'] = {n: digest(ROOT / 'lean' / n) for n in MODULES}
        report['gate_sha256'] = digest(Path(__file__))
        paths = json.loads((ROOT / 'docs/companion/cancellation-paths.json').read_text())
        frames = json.loads((ROOT / 'artifacts/companion/native/current/snapshot.json').read_text())['frames']
        if paths != [frames[40]['path'], frames[53]['path']]:
            raise ValueError('The two original cancellation paths changed')
        report['source_frames'] = [40, 53]
        with tempfile.TemporaryDirectory(prefix='leanglish-source-cancellation-') as temporary:
            work = Path(temporary)
            for name in MODULES:
                shutil.copyfile(ROOT / 'lean' / name, work / name)
            env = os.environ.copy()
            search = [work, project / '.lake/build/lib/lean', *sorted((project / '.lake/packages').glob('*/.lake/build/lib/lean'))]
            env['LEAN_PATH'] = os.pathsep.join(map(str, search))
            def run(label: str, arguments: list[str], expected_error: str | None = None) -> str:
                entry = {'label': label, 'arguments': arguments, 'returncode': None}
                report['commands'].append(entry)
                try:
                    proc = subprocess.run([binary, *arguments], cwd=work, env=env,
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=180, check=False)
                except subprocess.TimeoutExpired as exc:
                    (output / (label + '.log')).write_bytes(exc.stdout or b'')
                    entry['timed_out'] = True
                    raise ValueError(f'Native timeout: {label}') from exc
                text = proc.stdout.decode('utf-8', errors='strict')
                (output / (label + '.log')).write_bytes(proc.stdout)
                entry.update(returncode=proc.returncode, stdout_sha256=hashlib.sha256(proc.stdout).hexdigest())
                if expected_error is None:
                    if proc.returncode != 0 or 'sorryAx' in text or 'declaration uses `sorry`' in text:
                        raise ValueError(f'Native check failed: {label}')
                elif proc.returncode == 0 or expected_error not in text:
                    raise ValueError(f'Mutation not rejected for the intended reason: {label}')
                entry['expected_outcome_observed'] = True
                return text
            version = run('version', ['--version']).strip()
            if not version.startswith('Lean (version 4.34.1,'):
                raise ValueError('Wrong Lean version')
            report['lean_version'] = version
            for name in MODULES:
                if name.endswith('Audit.lean'):
                    run(name[:-5], [name])
                else:
                    log = run(name[:-5], ['-o', name[:-5] + '.olean', name])
                    if name == 'ArithmeticEnglish.lean':
                        report['contract_axioms'] = checked_axioms(log)
            header = 'import OAI.Algebra.AffineCancellation.Model\n'
            source = original.read_text()
            if not source.startswith(header):
                raise ValueError('Original import boundary changed')
            body = source[len(header):]
            imports = 'import Mathlib.Algebra.EuclideanDomain.Basic\nimport Mathlib.Tactic.Ring\nimport SourceCancellation\n'
            report['import_adaptation'] = {'removed': [header.strip()[7:]],
                'added': imports.strip().splitlines(), 'body_sha256': hashlib.sha256(body.encode()).hexdigest(),
                'theorem_body_unchanged': True}
            def driver(label: str, mode: str, selected: list, expected_error: str | None = None) -> list | None:
                pathfile = work / (label + '-paths.json')
                pathfile.write_text(json.dumps(selected))
                result = work / (label + '.json')
                command = f'#source_cancellations "{TARGET}" paths {json.dumps(str(pathfile))} output {json.dumps(str(result))} mode "{mode}"\n'
                if label == 'kernel-flag-bypass':
                    command = 'set_option debug.skipKernelTC true in\n' + command
                program = imports + body + '\n' + command
                filename = label + '.lean'
                (work / filename).write_text(program)
                (output / filename).write_text(program)
                run(label, [filename], expected_error)
                if expected_error is not None:
                    if result.exists():
                        raise ValueError('Rejected check emitted a certificate')
                    return None
                data = json.loads(result.read_text())
                validate_records(data, paths)
                (output / (label + '.json')).write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
                return data
            first = driver('positive', 'ok', paths)
            repeated = driver('repeat', 'ok', paths)
            if first != repeated:
                raise ValueError('Source-bound output did not repeat exactly')
            for label, error in NEGATIVES.items():
                selected = [[], paths[1]] if label == 'wrong-path' else [paths[0], paths[0]] if label == 'duplicate-path' else paths
                mode = 'ok' if label in {'wrong-path', 'duplicate-path'} else 'kernel-claim-tamper' if label == 'kernel-flag-bypass' else label
                driver(label, mode, selected, error)
            assert first is not None
            for i, record in enumerate(first):
                (output / f'cancellation-{i}.txt').write_bytes(bytes(record['utf8']))
            report.update(status='passed', certified_sentence_count=2,
                repeat_byte_identical=True, native_negative_cases=len(NEGATIVES),
                native_parser_guards=sum(line.lstrip().startswith('#guard ') for line in
                    (ROOT / 'lean/ArithmeticEnglishAudit.lean').read_text().splitlines()))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError, tarfile.TarError) as exc:
        report['error'] = str(exc)
    finally:
        report['files_sha256'] = {p.name: digest(p) for p in sorted(output.iterdir()) if p.is_file() and p.name != 'observation.json'}
        (output / 'observation.json').write_text(json.dumps(report, sort_keys=True, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'sentences': report['certified_sentence_count'], 'output': str(output)}))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
