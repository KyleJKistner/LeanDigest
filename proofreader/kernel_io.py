"""Explicit, reproducible I/O for v2 typed arguments.

Reading and HTML export never execute Lean or make network requests. Native
execution requires trust_project; remote execution requires allow_remote.
Receipts record an observation, not a signature or a formal English guarantee.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import os
import re
import tempfile
import urllib.request
from typing import Any

from .kernel import Argument, InvalidExport, SCHEMA, replay_source, require
from .english import English, PRINTER_VERSION, prose_text
from .model import canonical_json, digest, Document
from .render import write_html
from .lean import run_bounded, driver_file

STANDARD_AXIOMS = frozenset({'propext', 'Classical.choice', 'Quot.sound'})
INCOMPLETE_AXIOMS = frozenset({'sorryAx', 'Lean.sorryAx'})
MAX_REQUEST_BYTES = 64_000_000
MAX_RESPONSE_BYTES = 128_000_000


def strict_json(text: str | bytes) -> Any:
    """Reject ambiguous duplicate object keys and non-finite numeric tokens."""
    def object_pairs(pairs):
        d = {}
        for k, v in pairs:
            if k in d: raise InvalidExport(f'Duplicate JSON key: {k}')
            d[k] = v
        return d
    def bad_constant(value):
        raise InvalidExport('Non-finite JSON number: ' + value)
    return json.loads(text, object_pairs_hook=object_pairs, parse_constant=bad_constant)


def axiom_status(record: dict, permitted: list[str] | None = None) -> dict:
    a = Argument(record)
    allowed = STANDARD_AXIOMS | frozenset(permitted or [])
    incomplete = sorted(set(a.record['axioms']) & INCOMPLETE_AXIOMS)
    extra = sorted(set(a.record['axioms']) - allowed)
    return {'axioms': a.record['axioms'], 'standard_axioms': sorted(STANDARD_AXIOMS),
            'explicitly_permitted': sorted(set(permitted or [])),
            'incomplete_axioms': incomplete, 'nonpermitted_axioms': extra,
            'acceptable': not incomplete and not extra}


def checked_source(record: dict, *, imports: list[str] | None = None,
                   context: str | None = None) -> str:
    """For source re-elaboration, preserve the original prefix exactly.

    `context` should be the exact input used at extraction, without export
    commands. A normal project should instead use pinned .olean imports.
    """
    require(not (context is not None and imports), "Choose source context or module imports, not both")
    driver = replay_source(record, imports=imports)
    if context is None: return driver
    marker = 'open Lean Elab Command'
    return context.rstrip() + '\n' + driver[driver.index(marker):]


def expected_markers(record: dict) -> tuple[str, ...]:
    a = Argument(record)
    return ('PROOFREADER_REPLAY_OK', 'PROOFREADER_PATHS_OK',
            f'PROOFREADER_JUDGEMENTS_OK:{a.sha256}:{len(a.claims)}')


def _has_marker(text: str, marker: str) -> bool:
    # Must be a complete emitted message line, not an error quoting source text.
    return any(line.strip() == marker or line.rstrip().endswith('info: ' + marker)
               for line in text.splitlines())


def judge_run(record: dict, source: str, *, okay: bool, stdout: str,
              errors: list[str], environment: str | None = None,
              source_preserved: bool = True, permitted_axioms: list[str] | None = None) -> dict:
    """Pure adjudicator used by both transports. No receipt can invoke execution."""
    a = Argument(record)
    policy = axiom_status(record, permitted_axioms)
    markers = expected_markers(record)
    missing = [m for m in markers if not _has_marker(stdout, m)]
    version_matches = environment is None or environment.removeprefix('lean-') == record['lean_version']
    passed = okay is True and not errors and not missing and version_matches and source_preserved and policy['acceptable']
    reasons = []
    if okay is not True: reasons.append('Lean execution did not succeed')
    if errors: reasons.append('Lean or service reported errors')
    if missing: reasons.append('Required completion markers are missing')
    if not version_matches: reasons.append('Exact Lean version mismatch')
    if not source_preserved: reasons.append('Service changed submitted source')
    if not policy['acceptable']: reasons.append('Axiom policy did not pass')
    return {'schema': 'proofreader.kernel-receipt/v2', 'status': 'passed' if passed else 'failed',
            'argument_sha256': a.sha256, 'checker_source_sha256': digest(source),
            'lean_version': record['lean_version'], 'environment': environment,
            'printer_version': PRINTER_VERSION, 'judgements_expected': len(a.claims),
            'completion_markers': {m: _has_marker(stdout, m) for m in markers},
            'path_linkage_checked_in_lean': passed, 'all_judgements_kernel_checked': passed,
            'english_formally_verified': False, 'receipt_authenticated': False,
            'axiom_policy': policy, 'source_preserved': source_preserved,
            'errors': errors, 'reasons': reasons,
            'trust_boundary': 'Requires trusted compiler, project, metaprograms, checker and recorded transport. Re-run before relying on an imported receipt.'}


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def write_bundle(record: dict, destination: Path, *, source: str = '', file: str = 'typed-proof',
                 receipt: dict | None = None, imports: list[str] | None = None,
                 context: str | None = None) -> dict:
    """Create a portable reader with its exact data, checks and prose binding."""
    from .english import reading_binding
    a = Argument(record)
    destination.mkdir(parents=True, exist_ok=True)
    if receipt is not None:
        require(receipt.get('argument_sha256') == a.sha256, 'Receipt belongs to a different argument')
    d = English(record).document(source=source, file=file, receipt=receipt)
    d.declarations[0].axes['axiom_status'] = axiom_status(record)
    # Axiom status is metadata, not prose; it is excluded from English binding.
    d.provenance['corpus_complete'] = False
    _write_json(destination / 'argument.json', record)
    (destination / 'reading.json').write_text(d.to_json(), encoding='utf-8')
    (destination / 'proof.txt').write_text(prose_text(record), encoding='utf-8')
    (destination / 'Check.lean').write_text(checked_source(record, imports=imports, context=context), encoding='utf-8')
    write_html(d, destination / 'reader.html')
    result = {**a.coverage(), 'argument_sha256': a.sha256,
              'reading_binding': reading_binding(d), 'axiom_status': axiom_status(record),
              'checker_context_supplied': bool(imports) or context is not None,
              'checker_setup_note': ('An input context is supplied; execution has not been implied.'
                 if imports or context is not None else
                 'Check.lean requires the original theorem environment. Recreate the bundle with --context or --module before replay.'),
              'native_or_remote_replay': 'not-run' if receipt is None else 'attached-observation-' + receipt.get('status', 'unknown'),
              'whole_corpus_coverage': False, 'readability_human_evaluated': False}
    _write_json(destination / 'coverage.json', result)
    if receipt is not None: _write_json(destination / 'receipt.json', receipt)
    return result


def verify_native(record: dict, project: Path, output: Path, *, module: str | None = None,
                  context: str | None = None, trust_project: bool = False,
                  timeout: float = 180, permitted_axioms: list[str] | None = None) -> dict:
    if not trust_project:
        raise PermissionError('Lean elaboration can execute arbitrary code. Pass --trust-project only for a trusted or isolated project.')
    require((module is None) != (context is None), 'Supply exactly one imported module or exact source context')
    project = project.resolve()
    require(project.is_dir(), 'Project directory does not exist')
    output.mkdir(parents=True, exist_ok=True)
    source = checked_source(record, imports=[module] if module else [], context=context)
    (output / 'Check.lean').write_text(source, encoding='utf-8')
    with driver_file(project, source) as driver:
        run = run_bounded(['lake', 'env', 'lean', str(driver)], project, timeout=timeout)
    _write_json(output / 'run.json', asdict(run))
    (output / 'stdout.txt').write_text(run.stdout, encoding='utf-8')
    (output / 'stderr.txt').write_text(run.stderr, encoding='utf-8')
    # A successful exit AND all check markers are needed. The driver itself checks version.
    errors = [] if run.status == 'passed' and run.exit_code == 0 else [run.reason or run.stderr or 'Lean failed']
    receipt = judge_run(record, source, okay=run.status == 'passed' and run.exit_code == 0,
                        stdout=run.stdout, errors=errors, permitted_axioms=permitted_axioms)
    receipt['backend'] = 'local-lake'
    _write_json(output / 'receipt.json', receipt)
    return receipt


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Remote verification redirects are not followed')


def axle_request(source: str, version: str, *, allow_remote: bool = False,
                 timeout: float = 180) -> dict:
    if not allow_remote:
        raise PermissionError('This sends the complete Lean source to AXLE. Pass --allow-remote to consent.')
    require(0 < timeout <= 900, 'Timeout must be between 0 and 900 seconds')
    require(bool(re.fullmatch(r'4\.\d+\.\d+', version)), 'Expected an exact stable Lean version')
    request = {'content': source, 'environment': 'lean-' + version,
               'ignore_imports': False, 'theorems_only': False, 'timeout_seconds': timeout}
    body = canonical_json(request).encode('utf-8')
    require(len(body) <= MAX_REQUEST_BYTES, 'Remote source exceeds size budget')
    headers = {'Content-Type': 'application/json; charset=utf-8', 'User-Agent': 'lean-proofreader/0.2.0'}
    if token := os.environ.get('AXLE_API_KEY'): headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request('https://axle.axiommath.ai/api/v1/check', body, headers, method='POST')
    with urllib.request.build_opener(NoRedirect).open(req, timeout=timeout+60) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
    require(len(data) <= MAX_RESPONSE_BYTES, 'Remote response exceeds size budget')
    result = strict_json(data)
    require(isinstance(result, dict), 'Invalid AXLE response')
    return result


def judge_axle(record: dict, source: str, result: dict, *, permitted_axioms: list[str] | None = None) -> dict:
    require(isinstance(result, dict), 'Malformed AXLE response')
    lm, tm = result.get('lean_messages', {}), result.get('tool_messages', {})
    require(isinstance(lm, dict) and isinstance(tm, dict), 'Malformed AXLE message collection')
    for collection in (lm, tm):
        for key in ('errors','infos','warnings'):
            value=collection.get(key,[])
            require(isinstance(value,list) and all(isinstance(x,str) for x in value), 'Malformed AXLE message list')
    require(isinstance(result.get('info',{}),dict),'Malformed AXLE execution metadata')
    require(isinstance(result.get('failed_declarations',[]),list),'Malformed failed-declaration inventory')
    errors = list(lm.get('errors', [])) + list(tm.get('errors', []))
    if result.get('failed_declarations'): errors.append('AXLE reported failed declarations: ' + str(result['failed_declarations']))
    if not isinstance(result.get('content'), str): errors.append('AXLE did not return processed source')
    info = result.get('info', {})
    receipt = judge_run(record, source, okay=result.get('okay') is True,
                        stdout='\n'.join(lm.get('infos', [])), errors=errors,
                        environment=info.get('environment', 'unknown'),
                        source_preserved=isinstance(result.get('content'),str) and result['content'].strip() == source.strip(),
                        permitted_axioms=permitted_axioms)
    receipt.update({'backend': 'AXLE', 'request_id': info.get('request_id'),
                    'executor_commit_sha': info.get('_executor_commit_sha'),
                    'service_warnings': list(lm.get('warnings', [])) + list(tm.get('warnings', []))})
    return receipt


def verify_remote(record: dict, output: Path, *, context: str, allow_remote: bool = False,
                  timeout: float = 180, permitted_axioms: list[str] | None = None) -> dict:
    # Consent is checked before writing a request or making any call.
    if not allow_remote: raise PermissionError('Remote verification requires --allow-remote; source is sent to AXLE.')
    a = Argument(record)
    source = checked_source(record, context=context)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'Check.lean').write_text(source, encoding='utf-8')
    result = axle_request(source, a.record['lean_version'], allow_remote=True, timeout=timeout)
    _write_json(output / 'axle-response.json', result)
    receipt = judge_axle(record, source, result, permitted_axioms=permitted_axioms)
    _write_json(output / 'receipt.json', receipt)
    return receipt
