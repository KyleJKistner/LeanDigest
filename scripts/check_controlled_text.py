#!/usr/bin/env python3
"""Run the pinned Lean component gate in a fresh workspace; retain every outcome.

This does not certify the Python renderer or promote a corpus/companion document.
It executes trusted Lean source. The caller must explicitly pass --trust-project.
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

ROOT = Path(__file__).resolve().parents[1]
MODULES = (
    'ControlledEnglish.lean', 'ControlledEnglishAudit.lean',
    'ControlledEnglishText.lean', 'ControlledEnglishTextAudit.lean',
    'ControlledEnglishTextExamples.lean',
)
ALLOWED_AXIOMS = frozenset({'propext', 'Classical.choice', 'Quot.sound'})
REQUIRED_THEOREMS = (
    'decodeUTF8_encode', 'lexBytes_renderBytes', 'renderBytes_injective',
    'readSentenceBytes_render', 'rendered_bytes_meaning', 'rendered_rule_bytes_sound',
    'lex_render', 'render_injective', 'readFormula_render', 'readSentence_render',
    'rendered_formula_meaning', 'rendered_sentence_meaning',
    'accepted_rule_sound', 'accepted_root_aligned',
)


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def audit_axioms(log: str) -> dict[str, list[str]]:
    """Require an inventory for every named contract and reject extra axioms."""
    if 'sorryAx' in log:
        raise ValueError('An admission occurred in the compiler output')
    found: dict[str, list[str]] = {}
    pattern = r"'ProofReader\.ControlledEnglish\.Text\.(\w+)' depends on axioms: \[([^\]]*)\]"
    for name, raw in re.findall(pattern, log):
        if name in found:
            raise ValueError(f'Duplicate axiom inventory: {name}')
        axioms = [item.strip() for item in raw.split(',') if item.strip()]
        if set(axioms) - ALLOWED_AXIOMS:
            raise ValueError(f'Unpermitted axioms in {name}: {axioms}')
        found[name] = axioms
    for name in re.findall(r"'ProofReader\.ControlledEnglish\.Text\.(\w+)' does not depend on any axioms", log):
        if name in found:
            raise ValueError(f'Duplicate axiom inventory: {name}')
        found[name] = []
    missing = set(REQUIRED_THEOREMS) - found.keys()
    if missing:
        raise ValueError(f'Missing theorem inventories: {sorted(missing)}')
    return found


def inventory(directory: Path) -> dict[str, str]:
    return {str(path.relative_to(directory)): sha256(path)
            for path in sorted(directory.rglob('*')) if path.is_file()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lean', default='lean', help='Pinned Lean executable or executable name')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--trust-project', action='store_true')
    args = parser.parse_args()
    if not args.trust_project:
        parser.error('Lean elaboration executes project code; --trust-project is required')
    output = args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error('Output must be a new or empty directory; stale evidence is not reused')
    output.mkdir(parents=True, exist_ok=True)
    report: dict = {
        'schema': 'leanglish.checked-text-observation/v1',
        'status': 'failed', 'commands': [],
        'full_document_english_certified': False,
        'original_proof_import_checked': False,
        'browser_semantics_checked': False,
        'observations_authenticated': False,
    }
    try:
        binary = shutil.which(args.lean)
        if binary is None:
            raise ValueError(f'Lean executable unavailable: {args.lean}')
        binary = str(Path(binary).resolve())
        report['invoked_executable_sha256'] = sha256(Path(binary))
        report['source_sha256'] = {name: sha256(ROOT / 'lean' / name) for name in MODULES}
        with tempfile.TemporaryDirectory(prefix='leanglish-checked-text-') as temporary:
            work = Path(temporary)
            for name in MODULES:
                shutil.copyfile(ROOT / 'lean' / name, work / name)
            environment = os.environ.copy()
            environment['LEAN_PATH'] = str(work)

            def run(label: str, arguments: list[str]) -> str:
                command = [binary, *arguments]
                entry = {'label': label, 'arguments': arguments, 'returncode': None}
                report['commands'].append(entry)
                try:
                    result = subprocess.run(command, cwd=work, env=environment,
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                            timeout=180, check=False)
                    data = result.stdout
                    entry['returncode'] = result.returncode
                except subprocess.TimeoutExpired as exc:
                    data = exc.stdout or b''
                    (output / f'{label}.log').write_bytes(data)
                    entry['timed_out'] = True
                    raise ValueError(f'Compiler timeout: {label}') from exc
                path = output / f'{label}.log'
                path.write_bytes(data)
                entry['stdout_sha256'] = sha256(path)
                text = data.decode('utf-8', errors='strict')
                if result.returncode != 0:
                    raise ValueError(f'Compiler failed: {label}; see {path.name}')
                if 'sorryAx' in text or 'warning: declaration uses' in text:
                    raise ValueError(f'Admission detected: {label}')
                return text

            version = run('version', ['--version']).strip()
            report['lean_version'] = version
            if not version.startswith('Lean (version 4.34.1,'):
                raise ValueError(f'Unexpected compiler version: {version}')
            run('foundation', ['-o', 'ControlledEnglish.olean', 'ControlledEnglish.lean'])
            run('foundation-audit', ['ControlledEnglishAudit.lean'])
            text_log = run('text-core', ['-o', 'ControlledEnglishText.olean', 'ControlledEnglishText.lean'])
            report['contract_axioms'] = audit_axioms(text_log)
            run('text-audit', ['ControlledEnglishTextAudit.lean'])
            for label in ('examples-first', 'examples-repeat'):
                run(label, ['--run', 'ControlledEnglishTextExamples.lean', str(work / label)])
            first, repeat = inventory(work / 'examples-first'), inventory(work / 'examples-repeat')
            if not first or first != repeat:
                raise ValueError('Canonical examples are absent or nondeterministic')
            manifest = json.loads((work / 'examples-first' / 'examples.json').read_text())
            records = manifest['examples']
            if len(records) != 8 or len({r['id'] for r in records}) != 8:
                raise ValueError('Expected exactly eight distinct logical rule examples')
            for record in records:
                data = (work / 'examples-first' / record['file']).read_bytes()
                if data != record['text'].encode('utf-8') or len(data) != record['utf8_bytes']:
                    raise ValueError(f"Example byte mismatch: {record['id']}")
            shutil.copytree(work / 'examples-first', output / 'examples')
            report['example_files_sha256'] = first
            report['repeat_byte_identical'] = True
            report['executable_guard_count'] = sum(
                line.lstrip().startswith('#guard ') for line in
                (ROOT / 'lean' / 'ControlledEnglishTextAudit.lean').read_text().splitlines())
            report['required_contracts_checked'] = len(REQUIRED_THEOREMS)
            report['status'] = 'passed'
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        report['error'] = str(exc)
    finally:
        (output / 'observation.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'status': report['status'], 'observation': str(output / 'observation.json')}))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
