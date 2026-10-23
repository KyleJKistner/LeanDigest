"""Agent-facing proof outlines backed by source extraction and reconstruction.

Native commands execute trusted Lean code. An outline's prose is commentary;
only its source claims and reconstructed theorem are checked by this workflow.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

from .kernel import display_name, require
from .kernel_io import strict_json
from .model import canonical_json, digest
from .proof_decomposition import make_plan, validate_result
from .source_expressions import Expressions, fields

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('KernelExport', 'JsonReplay', 'Narrative', 'SourceExpressions', 'ProofDecomposition')
SCHEMA = 'leanglish.agent-outline/v1'
NAMESPACE = 'LeanglishOutlineAccepted'
NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9']*(?:\.[A-Za-z_][A-Za-z_0-9']*)*")
ID = re.compile(r'[a-zA-Z][a-zA-Z0-9_-]{0,63}')
HASH = re.compile(r'[0-9a-f]{64}')

# The expected declaration is separate from the imported source record. The
# snapshot and path inventory are regenerated from that declaration on each run.
DRIVER = '''import ProofDecomposition
import Narrative
import {module}
open Lean Meta Elab Command ProofReader.SourceExpressions
set_option maxHeartbeats 20000000
set_option maxRecDepth 10000
set_option debug.skipKernelTC false
set_option Elab.async false
run_elab do
  let req ← Replay.liftJ <| Json.parse (← IO.FS.readFile "request.json")
  let imports ← (← getEnv).header.moduleNames.mapM (fun name => do
    return toJson (← findOLean name).toString)
  IO.FS.writeFile "imports.json" (toJson imports).compress
  let target ← Replay.liftJ <| ProofReaderJsonReplay.name (← Replay.field req "target")
  let snap ← ProofReaderNarrative.exportOne target
  let paths ← (← Replay.arr (← Replay.field snap "frames")).mapM
    (fun f => do return ← Replay.nums (← Replay.field f "path"))
  let actual ← exportOne target paths
  let mode ← Replay.str (← Replay.field req "mode")
  if mode == "open" then
    let count ← Replay.verify actual target paths
    IO.FS.writeFile "record.json" actual.compress
    IO.FS.writeFile "snapshot.json" snap.compress
    IO.FS.writeFile "result.json" (Json.mkObj [("source_kernel_judgements", toJson count)]).compress
  else
    unless mode == "check" do throwError "Unknown outline operation"
    let recorded ← Replay.liftJ <| Json.parse (← IO.FS.readFile "source.json")
    let snapshot ← Replay.liftJ <| Json.parse (← IO.FS.readFile "source.snapshot.json")
    Replay.equalJson actual recorded "Outline source changed"
    Replay.equalJson snap snapshot "Outline snapshot changed"
    let selected ← Replay.nums (← Replay.field req "selected")
    let result ← ProofReader.ProofDecomposition.compose recorded target paths selected
      `LeanglishOutlineAccepted
    IO.FS.writeFile "result.json" result.compress
  logInfo "LEANGLISH_OUTLINE_COMPLETE"
'''


def named(s: str) -> dict:
    require(isinstance(s, str) and NAME.fullmatch(s) is not None, 'Unsupported declaration name')
    value = {'tag': 'anonymous'}
    for component in s.split('.'):
        value = {'tag': 'str', 'prefix': value, 'value': component}
    return value


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read(path: Path, limit: int = 64_000_000):
    require(path.stat().st_size <= limit, 'Input size budget exceeded')
    return strict_json(path.read_text(encoding='utf-8'))


def write(path: Path, value) -> None:
    path.write_text(canonical_json(value) + '\n', encoding='utf-8')


def atomic(path: Path, value) -> None:
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        write(temporary, value)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def lock(session: Path):
    guard = session / '.lock'
    try:
        guard.mkdir()
    except FileExistsError as exc:
        raise ValueError('Another outline operation holds the session lock') from exc
    try:
        yield
    finally:
        guard.rmdir()


def validate_proposal(record: dict, proposal: dict) -> list[int]:
    """Check editorial references, not the meaning of editorial text."""
    fields(proposal, {'schema', 'source_sha256', 'parent', 'title', 'introduction', 'blocks'})
    view = Expressions(record)
    require(proposal['schema'] == SCHEMA and proposal['source_sha256'] == view.sha256,
            'Outline belongs to another source')
    require(proposal['parent'] is None or (isinstance(proposal['parent'], str)
            and HASH.fullmatch(proposal['parent'])), 'Invalid parent revision')
    require(isinstance(proposal['title'], str) and 0 < len(proposal['title']) <= 200
            and '\n' not in proposal['title'], 'Invalid outline title')
    require(isinstance(proposal['introduction'], str) and len(proposal['introduction']) <= 20000,
            'Invalid outline introduction')
    require(isinstance(proposal['blocks'], list), 'Invalid outline blocks')
    used, labels, selected = set(), set(), []

    def visit(blocks, parent_path, depth=0):
        require(depth <= 32, 'Outline nesting budget exceeded')
        siblings = []
        for block in blocks:
            fields(block, {'id', 'frame', 'title', 'text', 'children'})
            i, key = block['frame'], block['id']
            require(isinstance(key, str) and ID.fullmatch(key) and key not in labels,
                    'Invalid or duplicate block identity')
            require(type(i) is int and 0 <= i < len(view.frames) and i not in used,
                    'Invalid or duplicate source occurrence')
            require(len(used) < 1000, 'Outline node budget exceeded')
            p = tuple(view.frames[i]['path'])
            require(len(p) > len(parent_path) and p[:len(parent_path)] == parent_path,
                    'Outline block escapes its source parent')
            require(not any(p[:len(q)] == q or q[:len(p)] == p for q in siblings),
                    'Nested source occurrences must be nested outline blocks')
            siblings.append(p); used.add(i); labels.add(key)
            require(isinstance(block['title'], str) and 0 < len(block['title']) <= 200
                    and '\n' not in block['title'], 'Invalid block title')
            require(isinstance(block['text'], str) and len(block['text']) <= 20000,
                    'Invalid block commentary')
            require(isinstance(block['children'], list), 'Invalid child inventory')
            visit(block['children'], p, depth + 1)
            selected.append(i)
    visit(proposal['blocks'], ())
    make_plan(record, selected)
    return selected


def block_map(proposal: dict) -> dict:
    found = {}
    def visit(blocks):
        for b in blocks:
            found[b['id']] = b
            visit(b['children'])
    visit(proposal['blocks'])
    return found


def expand(record: dict, proposal: dict, block_id: str, children: list[dict]) -> dict:
    validate_proposal(record, proposal)
    result = deepcopy(proposal)
    nodes = block_map(result)
    require(block_id in nodes, 'Unknown outline block')
    require(not nodes[block_id]['children'], 'Block is already expanded')
    nodes[block_id]['children'] = deepcopy(children)
    validate_proposal(record, result)
    return result


def delta(old: dict | None, new: dict) -> dict:
    before = block_map(old) if old else {}
    after = block_map(new)
    def local(b):
        return {k: v for k, v in b.items() if k != 'children'}
    return {'added': sorted(after.keys() - before.keys()),
            'removed': sorted(before.keys() - after.keys()),
            'changed': sorted(k for k in before.keys() & after.keys()
                              if local(before[k]) != local(after[k])),
            'expanded': sorted(k for k in before.keys() & after.keys()
                               if before[k]['children'] != after[k]['children']),
            'unchanged': sorted(k for k in before.keys() & after.keys()
                                if before[k] == after[k])}


def _run(binary: str, args: list[str], cwd: Path, env: dict, label: str,
         observation: dict, timeout: int = 180) -> None:
    row = {'label': label, 'arguments': args, 'returncode': None}
    observation['commands'].append(row)
    try:
        p = subprocess.run([binary, *args], cwd=cwd, env=env, stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=timeout, check=False)
        data = p.stdout; row['returncode'] = p.returncode
    except subprocess.TimeoutExpired as exc:
        data = exc.stdout or b''; row['timed_out'] = True
        (cwd / (label + '.log')).write_bytes(data)
        raise ValueError('Lean timeout: ' + label) from exc
    log = cwd / (label + '.log'); log.write_bytes(data); row['log_sha256'] = sha(log)
    text = data.decode('utf-8', errors='strict')
    require(p.returncode == 0, 'Lean failed: ' + label + '; see ' + str(log))
    require('sorryAx' not in text and 'warning: declaration uses' not in text,
            'Lean admission: ' + label)


def environment_files(paths: list[str]) -> dict[str, str]:
    """Bind loaded .olean files and their existing sidecars; not authentication."""
    require(isinstance(paths, list) and 0 < len(paths) <= 20000
            and all(isinstance(p, str) for p in paths), 'Invalid loaded-module inventory')
    files = {}
    for name in paths:
        path = Path(name).resolve()
        require(path.suffix == '.olean' and path.is_file(), 'Compiled module missing')
        candidates = [path, path.with_suffix('.olean.private'), path.with_suffix('.olean.server'),
                      path.with_suffix('.ir'), path.with_suffix('.ir.sig')]
        for candidate in candidates:
            if candidate.is_file(): files[str(candidate)] = sha(candidate)
    return files


def _observation() -> dict:
    return {'status': 'failed', 'commands': [], 'english_certified': False,
            'observations_authenticated': False}


def start(session: Path, binary: str, module: str, declaration: str,
          search: list[Path], trust: bool) -> dict:
    require(trust, 'Native execution requires --trust-project')
    require(NAME.fullmatch(module) is not None, 'Unsupported module name')
    target = named(declaration)
    executable = shutil.which(binary)
    require(executable is not None, 'Lean executable unavailable')
    executable = str(Path(executable).resolve())
    require(not session.exists(), 'Session already exists')
    search = [p.resolve() for p in search]
    require(all(p.is_dir() for p in search), 'Lean search path is not a directory')
    session.mkdir(parents=True)
    backend = session / 'backend'; backend.mkdir()
    observation = _observation()
    env = os.environ.copy(); env['LEAN_PATH'] = os.pathsep.join(map(str, [backend, *search]))
    try:
        _run(executable, ['--version'], backend, env, 'version', observation)
        version = (backend / 'version.log').read_text().strip()
        require(version.startswith('Lean (version 4.34.1,'), 'Expected Lean 4.34.1')
        for name in MODULES:
            shutil.copyfile(ROOT / 'lean' / (name + '.lean'), backend / (name + '.lean'))
            _run(executable, ['-Ddebug.skipKernelTC=false', '-DElab.async=false',
                             '-o', name + '.olean', name + '.lean'], backend, env, name, observation)
        (backend / 'Driver.lean').write_text(DRIVER.format(module=module), encoding='utf-8')
        write(backend / 'request.json', {'mode': 'open', 'target': target})
        _run(executable, ['-Ddebug.skipKernelTC=false', '-DElab.async=false', 'Driver.lean'],
             backend, env, 'open', observation)
        require((backend / 'open.log').read_text().splitlines().count('LEANGLISH_OUTLINE_COMPLETE') == 1,
                'Native completion marker missing or repeated')
        record, snapshot = read(backend / 'record.json'), read(backend / 'snapshot.json')
        view = Expressions(record); view.bind_snapshot(snapshot)
        require(record['name'] == target, 'Exported declaration changed')
        shutil.copyfile(backend / 'record.json', session / 'source.json')
        shutil.copyfile(backend / 'snapshot.json', session / 'snapshot.json')
        (session / 'attempts').mkdir(); (session / 'revisions').mkdir()
        state = {'schema': SCHEMA, 'module': module, 'target': target,
                 'source_sha256': view.sha256, 'snapshot_sha256': sha(session / 'snapshot.json'),
                 'binary': executable, 'binary_sha256': sha(Path(executable)),
                 'lean_version': version, 'search_path': list(map(str, search)),
                 'backend_sha256': {p.name: sha(p) for p in sorted(backend.iterdir())
                                    if p.suffix in {'.lean', '.olean'}},
                 'loaded_modules': read(backend / 'imports.json'),
                 'environment_sha256': environment_files(read(backend / 'imports.json')),
                 'head': None}
        write(session / 'state.json', state)
        observation['status'] = 'passed'
        return {'session': str(session), 'frames': len(view.frames), 'source_sha256': view.sha256,
                'head': None, 'english_certified': False}
    except Exception as exc:
        observation['error'] = str(exc)
        raise
    finally:
        write(backend / 'observation.json', observation)


def load(session: Path) -> tuple[dict, dict, dict]:
    state, record, snapshot = read(session / 'state.json'), read(session / 'source.json'), read(session / 'snapshot.json')
    require(state['schema'] == SCHEMA, 'Unknown outline session')
    view = Expressions(record); view.bind_snapshot(snapshot)
    require(view.sha256 == state['source_sha256'] and record['name'] == state['target']
            and sha(session / 'snapshot.json') == state['snapshot_sha256'], 'Session source changed')
    return state, record, snapshot


def revision(session: Path, identifier: str) -> dict:
    require(isinstance(identifier, str) and HASH.fullmatch(identifier), 'Invalid revision identity')
    item = read(session / 'revisions' / (identifier + '.json'))
    fields(item, {'proposal', 'result'})
    require(digest(canonical_json(item)) == identifier, 'Revision content changed')
    _, record, _ = load(session)
    selected = validate_proposal(record, item['proposal'])
    validate_result(record, make_plan(record, selected), item['result'], named(NAMESPACE))
    return item


def draft(session: Path) -> dict:
    state, record, _ = load(session)
    if state['head']:
        result = deepcopy(revision(session, state['head'])['proposal'])
        result['parent'] = state['head']
        return result
    return {'schema': SCHEMA, 'source_sha256': state['source_sha256'], 'parent': None,
            'title': display_name(record['name']), 'introduction': '', 'blocks': []}


def check(session: Path, proposal: dict, trust: bool) -> dict:
    require(trust, 'Native execution requires --trust-project')
    with lock(session):
        state, record, snapshot = load(session)
        selected = validate_proposal(record, proposal)
        require(proposal['parent'] == state['head'], 'Stale outline revision; reread the current draft')
        old = revision(session, state['head'])['proposal'] if state['head'] else None
        require(sha(Path(state['binary'])) == state['binary_sha256'], 'Lean executable changed')
        backend = session / 'backend'
        for name, expected in state['backend_sha256'].items():
            require(sha(backend / name) == expected, 'Native outline backend changed')
        require(environment_files(state['loaded_modules']) == state['environment_sha256'],
                'Imported Lean environment changed; open a new session')
        attempt = session / 'attempts' / uuid.uuid4().hex; attempt.mkdir()
        observation = _observation()
        write(attempt / 'proposal.json', proposal)
        write(attempt / 'request.json', {'mode': 'check', 'target': state['target'], 'selected': selected})
        shutil.copyfile(session / 'source.json', attempt / 'source.json')
        shutil.copyfile(session / 'snapshot.json', attempt / 'source.snapshot.json')
        shutil.copyfile(backend / 'Driver.lean', attempt / 'Driver.lean')
        env = os.environ.copy()
        env['LEAN_PATH'] = os.pathsep.join([str(backend), *state['search_path']])
        try:
            _run(state['binary'], ['-Ddebug.skipKernelTC=false', '-DElab.async=false', 'Driver.lean'],
                 attempt, env, 'check', observation)
            require((attempt / 'check.log').read_text().splitlines().count('LEANGLISH_OUTLINE_COMPLETE') == 1,
                    'Native completion marker missing or repeated')
            require(read(attempt / 'imports.json') == state['loaded_modules'], 'Loaded module resolution changed')
            require(environment_files(state['loaded_modules']) == state['environment_sha256'],
                    'Imported Lean environment changed during checking')
            result = read(attempt / 'result.json')
            validate_result(record, make_plan(record, selected), result, named(NAMESPACE))
            item = {'proposal': proposal, 'result': result}
            identifier = digest(canonical_json(item))
            # Install the immutable revision first. HEAD changes only after every
            # source, kernel and result check has succeeded.
            destination = session / 'revisions' / (identifier + '.json')
            if destination.exists():
                require(read(destination) == item, 'Existing revision content differs')
            else:
                with destination.open('x', encoding='utf-8') as stream:
                    stream.write(canonical_json(item) + '\n')
            state['head'] = identifier
            atomic(session / 'state.json', state)
            observation.update(status='passed', revision=identifier, delta=delta(old, proposal),
                               result_sha256=sha(attempt / 'result.json'))
            return {'revision': identifier, 'attempt': str(attempt), 'delta': observation['delta'],
                    'selected_lemmas': len(selected), 'english_certified': False}
        except Exception as exc:
            observation['error'] = str(exc)
            raise
        finally:
            write(attempt / 'observation.json', observation)


def follow(session: Path, frame: int, destination: Path, trust: bool) -> dict:
    """Open the actual called theorem, never a theorem inferred from prose."""
    require(trust, 'Native execution requires --trust-project')
    state, record, _ = load(session)
    require(type(frame) is int and 0 <= frame < len(record['frames']), 'Invalid source frame')
    application = record['frames'][frame]['application']
    require(application is not None and application['constant'] is not None,
            'Source frame is not a named declaration application')
    require(environment_files(state['loaded_modules']) == state['environment_sha256'],
            'Imported Lean environment changed; open a new session')
    target = display_name(application['constant'])
    result = start(destination, state['binary'], state['module'], target,
                   [Path(p) for p in state['search_path']], trust)
    origin = {'source_sha256': state['source_sha256'], 'frame': frame,
              'head_path': application['head_path'], 'called_declaration': application['constant']}
    write(destination / 'origin.json', origin)
    return {**result, 'origin': origin}


def inventory(session: Path, frame: int | None = None) -> dict:
    state, record, snapshot = load(session)
    require(frame is None or (type(frame) is int and 0 <= frame < len(record['frames'])), 'Invalid source frame')
    return {'source_sha256': state['source_sha256'], 'head': state['head'],
            'theorem': display_name(record['name']),
            'frames': [{'frame': i, 'path': f['path'], 'role': snapshot['frames'][i]['role'],
                        'claim': f['display']['claim'], 'closed_claim': f['display']['lifted'],
                        'children': snapshot['frames'][i]['children'],
                        'called_declaration': f['application']['constant'] if f['application'] else None}
                       for i, f in enumerate(record['frames']) if frame is None or i == frame]}


def markdown(session: Path, identifier: str | None = None) -> str:
    state, record, _ = load(session)
    identifier = identifier or state['head']
    require(identifier is not None, 'No checked outline revision')
    item = revision(session, identifier); proposal, result = item['proposal'], item['result']
    def prose(s): return escape(s, quote=False)
    def code(s):
        size = max([len(x) for x in re.findall(r'`+', s)] + [2]) + 1
        fence = '`' * size
        return fence + 'lean\n' + s + '\n' + fence
    lines = ['# ' + prose(proposal['title']), '', prose(proposal['introduction']), '',
             '<details><summary>Formal statement</summary>', '', code(result['statement']), '', '</details>', '']
    rows = {r['frame']: r for r in result['lemmas']}
    def visit(blocks, depth=2):
        for b in blocks:
            lines.extend(['#' * min(depth, 6) + ' ' + prose(b['title']), '', prose(b['text']), '',
                          '<details><summary>Formal claim</summary>', '', code(rows[b['frame']]['signature']), '',
                          'Source occurrence: `' + str(record['frames'][b['frame']]['path']) + '`.', '', '</details>', ''])
            visit(b['children'], depth + 1)
    visit(proposal['blocks'])
    lines.extend(['## Verification', '', '| Check | Result |', '| --- | --- |',
                  '| Source claims and reconstructed theorem | Checked with Lean 4.34.1 |',
                  '| English commentary | Not certified |', '',
                  '<details><summary>Build record</summary>', '',
                  'Revision: `' + identifier + '`. Source: `' + state['source_sha256'] + '`.', '',
                  'This records a run in the supplied trusted Lean environment; it is not an authenticated receipt.',
                  '', '</details>', ''])
    return '\n'.join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('open'); p.add_argument('--lean', required=True); p.add_argument('--module', required=True)
    p.add_argument('--declaration', required=True); p.add_argument('--search-path', action='append', default=[], type=Path)
    p.add_argument('--session', required=True, type=Path); p.add_argument('--trust-project', action='store_true')
    for command in ('inspect', 'draft', 'check', 'expand', 'render', 'follow'):
        p = sub.add_parser(command); p.add_argument('--session', required=True, type=Path)
        if command == 'inspect': p.add_argument('--frame', type=int)
        if command == 'follow':
            p.add_argument('--frame', required=True, type=int); p.add_argument('--destination', required=True, type=Path)
            p.add_argument('--trust-project', action='store_true')
        if command == 'check':
            p.add_argument('--proposal', required=True, type=Path); p.add_argument('--trust-project', action='store_true')
        if command == 'expand':
            p.add_argument('--block', required=True); p.add_argument('--children', required=True, type=Path)
        if command == 'render': p.add_argument('--revision')
    args = parser.parse_args(argv)
    try:
        session = args.session.resolve()
        if args.command == 'open':
            answer = start(session, args.lean, args.module, args.declaration, args.search_path, args.trust_project)
        elif args.command == 'inspect': answer = inventory(session, args.frame)
        elif args.command == 'follow': answer = follow(session, args.frame, args.destination.resolve(), args.trust_project)
        elif args.command == 'draft': answer = draft(session)
        elif args.command == 'check': answer = check(session, read(args.proposal, 2_000_000), args.trust_project)
        elif args.command == 'expand':
            _, record, _ = load(session)
            answer = expand(record, draft(session), args.block, read(args.children, 2_000_000))
        else:
            print(markdown(session, args.revision)); return 0
        print(json.dumps(answer, indent=2, ensure_ascii=False)); return 0
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        print(json.dumps({'status': 'rejected', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
