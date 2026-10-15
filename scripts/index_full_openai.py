#!/usr/bin/env python3
"""Acquire the entire pinned Lean source and produce a hash-bound file ledger.

This is NOT a Lean build, proof count, or English-translation coverage test.
Optional lexical header indexing is heuristic and never executes source code.
The source commit, expected inventory and failures are retained independently.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import multiprocessing as mp
from pathlib import Path, PurePosixPath
import re
import signal
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from proofreader.lean import run_bounded
from proofreader.source import _command_candidates, DECLARATIONS

COMMIT='1581d4cbdd69a0faf34b2089614fe2a814316a6a'
TREE='351061cd373017200b8e08122a9ecdf78ffd2f0c'
REPO='https://github.com/openai/math.git'
PREFIX='lean/OAI/'


def save(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)


def parse_tree(text: str) -> list[dict]:
    entries=[];seen=set()
    for item in text.split('\0'):
        if not item:continue
        meta,path=item.split('\t',1)
        mode,kind,sha,size=meta.split()
        rel=PurePosixPath(path)
        if not path.startswith(PREFIX) or str(rel)!=path or rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts:
            raise ValueError('Unexpected Git path: '+path)
        if kind!='blob' or not re.fullmatch('[0-9a-f]{40}',sha):
            raise ValueError('Unexpected Git object')
        if not path.endswith('.lean'):continue
        if path in seen:raise ValueError('Duplicate Git path')
        seen.add(path)
        size=int(size)
        if size<0:raise ValueError('Negative source size')
        entries.append({'path':path,'git_blob_sha':sha,'size':size,'mode':mode,'role':'proof-library'})
    entries.sort(key=lambda x:x['path'])
    if not entries or len(entries)>250_000 or sum(e['size'] for e in entries)>2_500_000_000:
        raise ValueError('Empty inventory or source acquisition budget exceeded')
    return entries


def verify_file(root: Path, entry: dict) -> dict:
    result=dict(entry,source_hash_verified=False,header_status='not-run')
    try:
        path=root/entry['path']
        if entry['mode'] not in {'100644','100755'} or path.is_symlink() or root.resolve() not in path.resolve().parents:
            raise ValueError('Not an in-tree regular source file')
        if path.stat().st_size!=entry['size']:raise ValueError('Source size mismatch')
        h=hashlib.sha1(b'blob '+str(entry['size']).encode()+b'\0')
        with path.open('rb') as stream:
            for chunk in iter(lambda:stream.read(1<<20),b''):h.update(chunk)
        if h.hexdigest()!=entry['git_blob_sha']:raise ValueError('Source Git-blob hash mismatch')
        result['source_hash_verified']=True
    except (OSError,ValueError) as exc:
        result.update(header_status='source-failed',error=str(exc))
    return result


def index_headers(task: tuple[str,dict,int,float]) -> dict:
    root,row,max_bytes,seconds=task
    result=dict(row)
    if not row['source_hash_verified']:return result
    if row['size']>max_bytes:
        result['header_status']='byte-budget';return result
    def expired(*_):raise TimeoutError('Per-file lexical indexing time budget exceeded')
    can_time=hasattr(signal,'setitimer')
    previous_handler=signal.getsignal(signal.SIGALRM) if can_time else None
    try:
        if can_time:
            signal.signal(signal.SIGALRM,expired)
            signal.setitimer(signal.ITIMER_REAL,seconds)
        data=(Path(root)/row['path']).read_bytes()
        if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=row['git_blob_sha']:
            raise ValueError('Source changed after verification')
        source=data.decode('utf-8')
        if '\0' in source:raise ValueError('NUL byte in source')
        commands=_command_candidates(source)
        kinds=Counter(t.text for t,_ in commands if t.text in DECLARATIONS)
        result.update(header_status='source-indexed',declaration_candidates=sum(kinds.values()),
                      candidate_kinds=dict(sorted(kinds.items())),
                      custom_syntax_seen=any(t.text in {'macro','macro_rules','elab','elab_rules','syntax'} for t,_ in commands))
    except Exception as exc:
        result.update(header_status='index-failed',error=type(exc).__name__+': '+str(exc)[:500])
    finally:
        if can_time:
            signal.setitimer(signal.ITIMER_REAL,0)
            signal.signal(signal.SIGALRM,previous_handler)
    return result


def aggregate(rows: list[dict]) -> dict:
    verified=sum(r['source_hash_verified'] for r in rows)
    indexed=sum(r['header_status']=='source-indexed' for r in rows)
    domains={}
    for row in rows:
        d=domains.setdefault(row['path'].split('/')[2],{'files':0,'source_hashes_verified':0,'headers_indexed':0})
        d['files']+=1;d['source_hashes_verified']+=int(row['source_hash_verified'])
        d['headers_indexed']+=int(row['header_status']=='source-indexed')
    return {'schema':'leandigest.source-ledger/v1','commit':COMMIT,'subtree':TREE,
            'scope':'all lean/OAI/**/*.lean files; not manuscripts or comparator harnesses',
            'expected_files':len(rows),'expected_bytes':sum(r['size'] for r in rows),
            'source_hashes_verified':verified,'all_source_hashes_verified':bool(rows) and verified==len(rows),
            'lexical_files_indexed':indexed,'all_headers_indexed':bool(rows) and indexed==len(rows),
            'header_outcomes':dict(Counter(r['header_status'] for r in rows)),
            'source_declaration_candidates':sum(r.get('declaration_candidates',0) for r in rows),
            'candidate_count_is_heuristic':True,'environment_discovered_theorems':None,
            'proofs_compiled':0,'proofs_replayed':0,'checked_english_proofs':0,
            'whole_corpus_english_coverage':False,'domains':domains}


def git(project: Path, output: Path, name: str, args: list[str], timeout: int=600) -> str:
    result=run_bounded(['git','-c','core.hooksPath=/dev/null',*args],project,timeout=timeout,max_output=64_000_000)
    save(output/(name+'.json'),{'status':result.status,'exit_code':result.exit_code,
                              'stderr':result.stderr[-20000:],'reason':result.reason})
    if result.status!='passed':raise RuntimeError(name+' failed: '+(result.stderr+result.stdout)[-3000:])
    return result.stdout


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--project',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--allow-network',action='store_true')
    p.add_argument('--index-headers',action='store_true')
    p.add_argument('--workers',type=int,default=2);p.add_argument('--index-seconds',type=float,default=1200)
    a=p.parse_args()
    if not a.allow_network:p.error('Explicit --allow-network is required for Git source acquisition')
    if not 1<=a.workers<=4 or not 0<a.index_seconds<=1800:p.error('Invalid bounded worker/time configuration')
    project,output=a.project.resolve(),a.output.resolve()
    if project==output or project in output.parents or output in project.parents:p.error('Use disjoint directories')
    if any(x.exists() and (not x.is_dir() or any(x.iterdir())) for x in (project,output)):
        p.error('Existing nonempty destinations are not overwritten')
    project.mkdir(parents=True,exist_ok=True);output.mkdir(parents=True,exist_ok=True)
    try:
        git(project,output,'init',['init'])
        git(project,output,'remote',['remote','add','origin',REPO])
        git(project,output,'promisor',['config','remote.origin.promisor','true'])
        git(project,output,'filter',['config','remote.origin.partialclonefilter','blob:none'])
        git(project,output,'fetch',['fetch','--depth=1','--filter=blob:none','origin',COMMIT],900)
        git(project,output,'sparse',['sparse-checkout','set','--cone','lean'])
        git(project,output,'checkout',['checkout','--detach',COMMIT],900)
        if git(project,output,'head',['rev-parse','HEAD']).strip()!=COMMIT:raise ValueError('Wrong commit')
        if git(project,output,'tree',['rev-parse','HEAD:lean/OAI']).strip()!=TREE:raise ValueError('Wrong subtree')
        entries=parse_tree(git(project,output,'inventory',['ls-tree','-rlz','HEAD','--','lean/OAI']))
        save(output/'inventory.json',{'commit':COMMIT,'tree':TREE,'files':entries})
        rows=[]
        for entry in entries:
            rows.append(verify_file(project,entry))
            if len(rows)%5000==0:print('SOURCE_HASHES',len(rows),'/',len(entries),flush=True)
        save(output/'summary.json',aggregate(rows))
        # Keep a snapshot consumable by the existing bounded corpus runner.
        save(project/'proofreader-corpus.json',{'repository':'openai/math','commit':COMMIT,
             'scope':'complete-OAI-source-subtree','tree_complete':True,'files':entries})
        if a.index_headers:
            deadline=time.monotonic()+a.index_seconds
            by_path={r['path']:r for r in rows}
            with mp.Pool(a.workers,maxtasksperchild=1000) as pool:
                it=pool.imap_unordered(index_headers,((str(project),r,2_000_000,5.0) for r in rows),chunksize=1)
                done=0
                while done<len(rows):
                    remaining=deadline-time.monotonic()
                    if remaining<=0:break
                    try:row=it.next(timeout=remaining)
                    except mp.TimeoutError:break
                    by_path[row['path']]=row;done+=1
                    if done%2000==0:
                        print('LEXICAL_HEADERS',done,'/',len(rows),flush=True)
                        save(output/'progress.json',{'attempted':done,'expected_files':len(rows),
                             'formal_theorem_count':None,'english_coverage':False})
                # Context-manager termination is deliberate on the global budget.
            rows=[by_path[r['path']] for r in rows]
        with (output/'files.jsonl').open('w',encoding='utf-8') as f:
            for row in rows:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
        summary=aggregate(rows);save(output/'summary.json',summary)
        print('SOURCE_INVENTORY '+json.dumps(summary,ensure_ascii=False,sort_keys=True),flush=True)
        return 0 if summary['all_source_hashes_verified'] else 1
    except Exception as exc:
        save(output/'failure.json',{'status':'failed','commit':COMMIT,'error':str(exc),
                                   'proofs_compiled':0,'whole_corpus_english_coverage':False})
        print(str(exc),file=sys.stderr);return 1

if __name__=='__main__':raise SystemExit(main())
