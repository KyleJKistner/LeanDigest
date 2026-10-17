"""Validate the frozen finding universe and source-bound observations.

These checks establish internal consistency, not the authenticity of a saved
compiler execution. Specification statements never become solution-proof checks.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import html
import posixpath
from pathlib import Path
import re
from urllib.parse import quote, urlparse
from .kernel_io import strict_json
from .model import canonical_json, digest
from .narrative import Snapshot
from .narrative_io import parse_stream

PIN = '1581d4cbdd69a0faf34b2089614fe2a814316a6a'
SAFE_NAME = re.compile(r'[A-Za-z_][A-Za-z0-9_.]*\Z')
LINK = re.compile(r'\[([^\]\n]+)\]\(([^\s)]+)\)')

def read_json(path: Path):
    return strict_json(path.read_text(encoding='utf-8'))

def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(value)+'\n', encoding='utf-8')

def safe_child(root: Path, relative: str) -> Path:
    if not isinstance(relative, str) or '\\' in relative or '..' in Path(relative).parts:
        raise ValueError('Unsafe local artifact path')
    result = (root/relative).resolve()
    if Path(relative).is_absolute() or not result.is_relative_to(root.resolve()):
        raise ValueError('Artifact path escapes its root')
    return result

def upstream_url(path: str, base: str = '') -> str:
    """Resolve upstream Markdown links without accepting active URL schemes."""
    if not isinstance(path, str) or any(c in path for c in '\x00\r\n\\'):
        raise ValueError('Unsafe link')
    if urlparse(path).scheme:
        if urlparse(path).scheme != 'https':
            raise ValueError('Only HTTPS external links are permitted')
        return path
    if path.startswith(('/', '//')):
        raise ValueError('Absolute repository link is not permitted')
    resolved = posixpath.normpath(posixpath.join(base, path))
    if resolved == '..' or resolved.startswith('../'):
        raise ValueError('Link escapes the upstream repository')
    return f'https://github.com/openai/math/blob/{PIN}/'+quote(resolved, safe='/#')

def config_inventory(lean: Path) -> dict:
    result={}
    for p in sorted((lean/'ComparatorChallenges').glob('*.json')):
        r=read_json(p)
        if not SAFE_NAME.fullmatch(p.stem) or r.get('challenge_module') != 'ComparatorChallenges.'+p.stem:
            raise ValueError('Configuration path/name mismatch')
        if not SAFE_NAME.fullmatch(r.get('solution_module','')) or not r['solution_module'].startswith('OAI.'):
            raise ValueError('Invalid solution module')
        names=r.get('theorem_names',[])+r.get('definition_names',[])
        if any(not isinstance(n,str) or not SAFE_NAME.fullmatch(n) for n in names) or len(set(names))!=len(names):
            raise ValueError('Invalid or repeated target names')
        result[p.stem]=r
    if not result: raise ValueError('The configuration inventory is empty')
    return result

def load_statements(roots: list[Path], configs: dict, lean: Path) -> tuple[dict,list]:
    chosen={}; attempts=[]
    for root in roots:
        for p in sorted(root.rglob('statements.json')):
            r=read_json(p)
            if r.get('schema')!='leanglish.statement-shard/v1' or r.get('upstream_commit')!=PIN:
                raise ValueError('Statement observations belong to another format or revision')
            for c in r['configurations']:
                key=c['configuration']
                if key not in configs or c['solution_module']!=configs[key]['solution_module']:
                    raise ValueError('Unknown statement configuration')
                attempts.append({'configuration':key,'status':c['status'],'artifact_sha256':digest(p.read_bytes())})
                if c['status']!='complete-statements-only': continue
                expected=configs[key].get('theorem_names',[])+configs[key].get('definition_names',[])
                if c.get('challenge_sha256')!=digest((lean/'ComparatorChallenges'/f'{key}.lean').read_bytes()):
                    raise ValueError('Comparison source hash differs from the statement observation')
                got=[x['name'] for x in c['targets']]
                if sorted(got)!=sorted(expected): raise ValueError('Incomplete statement outcome list')
                for t in c['targets']:
                    s=t['statement']
                    if (t.get('status')!='elaborated-specification' or s.get('name')!=t['name'] or
                        s.get('schema')!='leanglish.finding-statement/v1' or s.get('origin')!='comparison-specification' or
                        s.get('lean_version')!='4.34.1' or s.get('solution_proof_checked') is not False):
                        raise ValueError('Invalid specification evidence')
                    k=(key,t['name'])
                    if k in chosen and chosen[k]!=s: raise ValueError('Conflicting successful statement observations')
                    chosen[k]=s
    return chosen,attempts

def load_proofs(roots: list[Path], configs: dict, lean: Path) -> tuple[dict,list]:
    universe={(c['solution_module'],n) for c in configs.values() for n in c.get('theorem_names',[])}
    definitions={(c['solution_module'],n) for c in configs.values() for n in c.get('definition_names',[])}
    chosen={}; attempts=[]
    for root in roots:
        for p in sorted(root.rglob('proofs.json')):
            r=read_json(p)
            if r.get('schema')!='leanglish.finding-proof-shard/v1' or r.get('upstream_commit')!=PIN:
                raise ValueError('Proof observations belong to another format or revision')
            if len(r['targets'])!=r['expected_targets']: raise ValueError('Proof queue outcome count mismatch')
            seen=set()
            for row in r['targets']:
                key=(row['module'],row['name'])
                if key in seen: raise ValueError('Duplicate proof queue outcome')
                seen.add(key)
                if row['kind']=='definition':
                    if key not in definitions: raise ValueError('Unrecognized definition target')
                    continue
                if row['kind']!='theorem': raise ValueError('Unrecognized formal target kind')
                if key not in universe: raise ValueError('Proof target is outside the documented configuration universe')
                attempt={'module':key[0],'name':key[1],'status':row['status'],
                         'report_sha256':digest(p.read_bytes()),'errors':row.get('errors',[]),'reason':row.get('reason')}
                attempts.append(attempt)
                if row['status']!='reading-generated': continue
                expected_id=sha256((key[0]+'\0'+key[1]).encode()).hexdigest()[:24]
                if row.get('id')!=expected_id or row.get('directory')!='targets/'+expected_id:
                    raise ValueError('Noncanonical proof artifact identity')
                directory=safe_child(p.parent,row['directory'])
                for filename in ('snapshot.json','receipt.json','Extract.lean','stdout.txt','run.json'):
                    if not safe_child(directory,filename).is_file():
                        raise ValueError('Required proof artifact is missing')
                source=lean/(key[0].replace('.','/')+'.lean')
                if row.get('source_sha256')!=digest(source.read_bytes()): raise ValueError('Proof source hash mismatch')
                record=read_json(directory/'snapshot.json');snap=Snapshot(record)
                receipt=read_json(directory/'receipt.json')
                if (record['theorem']!=key[1] or receipt.get('theorem')!=key[1] or receipt.get('module')!=key[0] or
                    record['lean_version']!='4.34.1' or receipt.get('lean_version')!='4.34.1' or receipt.get('status')!='passed' or
                    receipt.get('selected_judgements')!=record['judgements_checked'] or
                    row.get('selected_judgements')!=record['judgements_checked'] or
                    receipt.get('all_selected_judgements_kernel_checked') is not True or
                    receipt.get('path_linkage_checked_in_lean') is not True or row.get('kernel_checked') is not True or
                    receipt.get('snapshot_sha256')!=snap.sha256 or row.get('snapshot_sha256')!=snap.sha256):
                    raise ValueError('Inconsistent source-bound proof observation')
                if receipt['source_sha256']!=digest((directory/'Extract.lean').read_bytes()):
                    raise ValueError('Executed driver hash mismatch')
                actual=parse_stream((directory/'stdout.txt').read_text(),theorem=key[1],version='4.34.1')
                if actual.sha256!=snap.sha256: raise ValueError('Saved compiler output disagrees with snapshot')
                run=read_json(directory/'run.json')
                if run.get('status')!='passed' or run.get('exit_code')!=0 or receipt.get('backend')!='native' or run.get('stdout')!=(directory/'stdout.txt').read_text():
                    raise ValueError('Missing successful native execution observation')
                # Later explicitly supplied attempts may replace a prior export;
                # both observations remain in the audit history.
                chosen[key]={'row':row,'directory':directory,'record':record,'receipt':receipt,'report_sha256':digest(p.read_bytes())}
    return chosen,attempts

def families(upstream: Path, configs: dict) -> list[dict]:
    contents=(upstream/'CONTENTS.md').read_text()
    marks=list(re.finditer(r'\*\*(\d{3})\.\s+(.+?)\.\*\*',contents))
    result=[]; linked=set()
    for i,m in enumerate(marks):
        block=contents[m.end():marks[i+1].start() if i+1<len(marks) else len(contents)]
        ident=m[1];doc=upstream/'lean/docs'/f'{ident}.md';scope=doc.read_text() if doc.is_file() else None
        keys=sorted(set(re.findall(r'ComparatorChallenges/([A-Za-z0-9_]+)\.lean',scope or '')))
        if any(k not in configs for k in keys): raise ValueError('Scope note references a missing configuration')
        linked.update(keys)
        subject=Counter(configs[k]['solution_module'].split('.')[1] for k in keys).most_common(1)
        papers=[]
        for match in LINK.finditer(block):
            if match[2].startswith('preprints/') and match[2].endswith('.pdf'):
                papers.append({'title':match[1],'url':upstream_url(match[2])})
        description=block.split('</td>',1)[0].strip()
        result.append({'id':ident,'title':html.unescape(m[2]),'description':description,'scope':scope,
            'configurations':keys,'subject':subject[0][0] if subject else 'Unassigned',
            'papers':papers,'documented':scope is not None})
    docs={p.stem for p in (upstream/'lean/docs').glob('*.md')}
    if len({f['id'] for f in result})!=len(result) or docs!={f['id'] for f in result if f['documented']}:
        raise ValueError('Scope-note and finding universe mismatch')
    if linked!=set(configs): raise ValueError('A comparison configuration has no documented finding')
    return result

def verify_metadata(upstream: Path, lean: Path, source_inventory: Path | None) -> None:
    """Derive expected files from retained manifests, never from success counts."""
    acquisition=read_json(upstream/'acquisition.json')
    if acquisition.get('repository')!='openai/math' or acquisition.get('commit')!=PIN:
        raise ValueError('Upstream metadata is not the selected repository revision')
    by={x['path']:x for x in acquisition['fetched']}
    if len(by)!=len(acquisition['fetched']): raise ValueError('Duplicate acquisition path')
    docs={k for k in by if re.fullmatch(r'lean/docs/\d{3}\.md',k)}
    actual={'lean/docs/'+p.name for p in (upstream/'lean/docs').glob('*.md')}
    if docs!=actual: raise ValueError('The documented finding inventory is incomplete')
    required=docs|{'CONTENTS.md','LICENSE'}
    for relative in required:
        p=safe_child(upstream,relative)
        if relative not in by or digest(p.read_bytes())!=by[relative]['sha256']:
            raise ValueError('Changed upstream scope or manuscript metadata')
    if source_inventory is not None:
        entries=read_json(source_inventory)
        source_paths={x['path'] for x in entries}
        if len(source_paths)!=len(entries): raise ValueError('Duplicate source inventory path')
        expected={k for k in source_paths if re.fullmatch(r'lean/ComparatorChallenges/[^/]+\.json',k)}
        actual={'lean/ComparatorChallenges/'+p.name for p in (lean/'ComparatorChallenges').glob('*.json')}
        if expected!=actual: raise ValueError('The comparison configuration universe is incomplete')
