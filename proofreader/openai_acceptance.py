"""Reproducible *selected dependency slice*, never a whole-project build.

Original OAI sources and imports are retained byte-for-byte. The small Lake
harness is new and pins the shared dependencies to the upstream manifest.
Download and arbitrary Lean execution each require explicit opt-in. Cached
compiled dependencies, the compiler and the source pretty-printer remain trusted.
"""
from __future__ import annotations

import argparse
import base64
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote
from urllib.request import Request, urlopen

from .kernel import require
from .kernel_io import strict_json
from .lean import MODULE_RE, run_bounded
from .lexer import lex
from .narrative_batch import run_batch, _write

PIN = '1581d4cbdd69a0faf34b2089614fe2a814316a6a'
MATHLIB = 'd13f23b723b8a846827a245b89c10fc7d3f11612'
VERSION = '4.34.1'
SCOPE = 'selected-dependency-slice-not-full-project'
SHA = re.compile(r'[0-9a-f]{40}')
MAX_SOURCE = 1_000_000
MAX_FILES = 256
MAX_BYTES = 16_000_000


def blob(data: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()


def validate_plan(plan: dict) -> dict:
    require(isinstance(plan, dict) and plan.get('schema') == 'leanglish.openai-acceptance-plan/v1', 'Invalid acceptance plan')
    require(plan.get('repository') == 'openai/math' and plan.get('commit') == PIN,
            'This acceptance runner uses the frozen OpenAI commit only')
    require(plan.get('mathlib_revision') == MATHLIB and plan.get('lean_version') == VERSION
            and plan.get('scope') == SCOPE, 'Pin or scope mismatch')
    roots = plan.get('roots')
    require(isinstance(roots, list) and 0 < len(roots) <= 32, 'Invalid root inventory')
    seen = set()
    for row in roots:
        require(isinstance(row, dict) and set(row) == {'module','blob'}, 'Invalid root')
        name = row['module']
        require(isinstance(name,str) and name.startswith('OAI.') and MODULE_RE.fullmatch(name), 'Unsafe root module')
        require(isinstance(row['blob'], str) and SHA.fullmatch(row['blob']), 'Root needs a Git blob hash')
        require(name not in seen, 'Duplicate root')
        seen.add(name)
    return plan


def header_imports(source: str) -> list[str]:
    """Restricted header parser. Unsupported multiline syntax fails explicitly.

    This is acquisition plumbing, not semantic enumeration. A successful native
    build, not this lexer, establishes that the requested imports were resolved.
    """
    parsed = lex(source)
    require(not parsed.diagnostics, 'Unparseable source header')
    lines = {}
    for token in parsed.tokens:
        lines.setdefault(token.line, []).append(token)
    result = []
    for tokens in lines.values():
        words = [t.text for t in tokens]
        while words and words[0] in {'public','private','meta'}:
            words.pop(0)
        if words == ['module'] or words == ['prelude']:
            continue
        if not words or words[0] != 'import':
            break
        require(len(words) > 1 and all(MODULE_RE.fullmatch(w) for w in words[1:]),
                'Unsupported import syntax; refusing to guess a dependency closure')
        result.extend(words[1:])
    return sorted(set(result))


def github_file(repository: str, revision: str, path: str, *, token: str | None = None) -> tuple[bytes, str]:
    require(repository in {'openai/math','leanprover-community/mathlib4'}, 'Unapproved source repository')
    require(SHA.fullmatch(revision) is not None, 'Unpinned source fetch')
    rel = Path(path)
    require(not rel.is_absolute() and '..' not in rel.parts, 'Unsafe source path')
    url = f'https://api.github.com/repos/{repository}/contents/{quote(path,safe="/")}?ref={revision}'
    headers = {'Accept':'application/vnd.github+json','User-Agent':'Leanglish-acceptance'}
    if token:
        headers['Authorization'] = 'Bearer '+token
    with urlopen(Request(url,headers=headers),timeout=30) as response:
        raw = response.read(2*MAX_SOURCE+1)
    require(len(raw) <= 2*MAX_SOURCE, 'Source response too large')
    item = strict_json(raw)
    require(isinstance(item,dict) and item.get('type') == 'file' and item.get('encoding') == 'base64', 'No complete source content returned')
    data = base64.b64decode(''.join(item['content'].split()),validate=True)
    require(len(data) <= MAX_SOURCE and len(data) == item['size'] and blob(data) == item['sha'], 'Source Git hash/size mismatch')
    data.decode('utf-8')
    return data,item['sha']


def acquire(plan: dict, project: Path, output: Path, fetch) -> dict:
    """Download each reachable OAI source once; retain independently failing roots."""
    nodes, errors = {}, {}
    expected = {r['module']:r['blob'] for r in plan['roots']}
    total = 0
    def visit(module, active):
        nonlocal total
        require(module not in active, 'Cyclic OAI import closure')
        if module in errors:
            raise ValueError(errors[module])
        if module in nodes:
            return nodes[module]['closure']
        try:
            require(len(nodes)+len(active) < MAX_FILES, 'Dependency source-file budget exceeded')
            rel = module.replace('.','/')+'.lean'
            data, sha = fetch('openai/math',PIN,'lean/'+rel)
            require(module not in expected or sha == expected[module], 'Selected root hash mismatch')
            require(total+len(data) <= MAX_BYTES, 'Dependency byte budget exceeded')
            total += len(data)
            imports = header_imports(data.decode('utf-8'))
            path = project/rel
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
            closure = {module}
            for dependency in imports:
                if dependency.startswith('OAI.'):
                    closure.update(visit(dependency,active|{module}))
            nodes[module] = {'module':module,'path':rel,'blob':sha,'sha256':hashlib.sha256(data).hexdigest(),
                             'bytes':len(data),'imports':imports,'closure':sorted(closure)}
            return sorted(closure)
        except (OSError,ValueError,KeyError,RecursionError) as exc:
            errors[module] = str(exc)[:2000]
            raise ValueError(errors[module]) from exc
    roots = []
    for root in plan['roots']:
        try:
            closure = visit(root['module'],set())
            roots.append({**root,'status':'acquired','closure':closure})
        except ValueError as exc:
            roots.append({**root,'status':'acquisition-failed','error':str(exc),'closure':None})
    result = {'roots':roots,'files':list(nodes.values()),'errors':errors,'source_bytes':total,
              'original_imports_rewritten':False,'closure_parser':'restricted-header-only',
              'complete_openai_project':False}
    _write(output/'acquisition.json',result)
    return result


def dependency_pins(upstream: dict, mathlib: dict) -> list[dict]:
    expected = {p['name']:p for p in upstream['packages']}
    names = sorted({p['name'] for p in mathlib['packages']} | {'mathlib'})
    result = []
    for name in names:
        require(name in expected, 'Shared dependency absent from original OAI manifest: '+name)
        entry = expected[name]
        require(entry.get('type') == 'git' and entry.get('subDir') is None
                and isinstance(entry.get('rev'),str) and SHA.fullmatch(entry['rev']), 'Unsupported dependency pin')
        require(isinstance(entry.get('url'),str) and re.fullmatch(r'https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:\.git)?',entry['url']),
                'Expected a public GitHub dependency')
        result.append({'name':name,'url':entry['url'],'rev':entry['rev']})
    require(next(p['rev'] for p in result if p['name']=='mathlib') == MATHLIB, 'Mathlib upstream pin mismatch')
    return result


def lake_config(pins: list[dict]) -> str:
    text = 'name = "oai_slice"\nversion = "0.0.0"\nfixedToolchain = true\nleanOptions = {autoImplicit = false}\n'
    for p in pins:
        text += '\n[[require]]\nname = '+json.dumps(p['name'])+'\ngit = '+json.dumps(p['url'])+'\nrev = '+json.dumps(p['rev'])+'\n'
    return text+'\n[[lean_lib]]\nname = "OAI"\n'


def run(plan: dict, project: Path, output: Path, *, allow_download=False, trust_project=False) -> dict:
    if not allow_download or not trust_project:
        raise PermissionError('Pass --allow-download and --trust-project; Lean executes the selected sources and pinned dependencies.')
    validate_plan(plan)
    project, output = Path(project), Path(output)
    require(not project.exists() and not project.is_symlink(), 'Use a new empty project path')
    require(not output.exists() and not output.is_symlink(), 'Use a new output path')
    require(project.resolve()!=output.resolve() and project.resolve() not in output.resolve().parents
            and output.resolve() not in project.resolve().parents,
            'Put results outside the Lean project')
    project.mkdir(parents=True);output.mkdir(parents=True)
    project, output = project.resolve(),output.resolve()
    token = os.environ.pop('GH_TOKEN',None)  # do not pass download credentials to Lean subprocesses
    def fetch(repo,revision,path):
        return github_file(repo,revision,path,token=token)
    result = {'schema':'leanglish.openai-acceptance/v1','scope':SCOPE,'plan':plan,'status':'setup',
              'complete_openai_project':False,'certified_english_proofs':0,'steps':[]}
    _write(output/'acceptance.json',result)
    try:
        upstream_bytes,_ = fetch('openai/math',PIN,'lean/lake-manifest.json')
        toolchain,_ = fetch('openai/math',PIN,'lean/lean-toolchain')
        require(toolchain.decode().strip() == 'leanprover/lean4:v'+VERSION, 'Original toolchain mismatch')
        mathlib_bytes,_ = fetch('leanprover-community/mathlib4',MATHLIB,'lake-manifest.json')
        (output/'upstream-lake-manifest.json').write_bytes(upstream_bytes)
        (output/'mathlib-lake-manifest.json').write_bytes(mathlib_bytes)
        pins = dependency_pins(strict_json(upstream_bytes),strict_json(mathlib_bytes))
        _write(output/'selected-dependency-pins.json',pins)
        result['acquisition'] = acquire(plan,project,output,fetch)
        (project/'lean-toolchain').write_bytes(toolchain)
        (project/'lakefile.toml').write_text(lake_config(pins))
        (output/'slice-lakefile.toml').write_text(lake_config(pins))
        for label, command, timeout in [('resolve',['lake','update'],900),('cache',['lake','exe','cache','get'],1200)]:
            execution=run_bounded(command,project,timeout=timeout,max_output=16_000_000)
            _write(output/(label+'.json'),asdict(execution))
            result['steps'].append({'step':label,'status':execution.status})
            _write(output/'acceptance.json',result)
            require(execution.status=='passed',label+' failed; see retained log')
        manifest = strict_json((project/'lake-manifest.json').read_bytes())
        actual = {p['name']:p for p in manifest['packages']}
        require(set(actual)=={p['name'] for p in pins}, 'Resolved dependency inventory differs from the pinned slice')
        checked = []
        for p in pins:
            require(actual[p['name']]['rev']==p['rev'] and actual[p['name']]['url']==p['url'], 'Resolved shared dependency pin mismatch')
            proc=run_bounded(['git','-C',str(project/'.lake/packages'/p['name']),'rev-parse','HEAD'],project,timeout=10)
            require(proc.status=='passed' and proc.stdout.strip()==p['rev'], 'Dependency checkout mismatch')
            checked.append(p)
        result['shared_dependency_revisions_verified']=checked
        (output/'resolved-lake-manifest.json').write_bytes((project/'lake-manifest.json').read_bytes())
        roots=[r['module'] for r in plan['roots']]
        # All original selections remain, including roots whose acquisition failed.
        batch=run_batch(roots,project,output/'batch',trust_project=True,version=VERSION,timeout=600,max_declarations=1000)
        result['summary']=batch['summary']
        result['status']=batch['status']
        require(all(blob((project/r['path']).read_bytes())==r['blob'] for r in result['acquisition']['files']),
                'An acquired original source changed during execution')
        result['original_source_hashes_rechecked']=True
    except (OSError,ValueError,KeyError,RecursionError) as exc:
        result['status']='failed'
        result['error']=str(exc)[:2000]
        result.setdefault('summary',{'total_candidates':None,'reason':'setup or acquisition not completed'})
    finally:
        _write(output/'acceptance.json',result)
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan',type=Path)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--output','-o',type=Path,required=True)
    parser.add_argument('--allow-download',action='store_true')
    parser.add_argument('--trust-project',action='store_true')
    args=parser.parse_args(argv)
    try:
        result=run(strict_json(args.plan.read_bytes()),args.work,args.output,
                   allow_download=args.allow_download,trust_project=args.trust_project)
    except (ValueError,OSError) as exc:
        parser.exit(2,str(exc)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in {'acquisition','plan'}},ensure_ascii=False,indent=2))
    return 0 if result['status']=='complete' else 2


if __name__=='__main__':
    sys.exit(main())
