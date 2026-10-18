"""Fail-closed execution/accounting for the ORIGINAL pinned OpenAI Lake project.

No source/configuration rewriting, synthetic reduced Lake file, new axiom, or
missing-worker success is allowed. Saved observations establish consistency,
not authenticated attestations or formal English meaning preservation.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

from .lean import run_bounded

PIN = '1581d4cbdd69a0faf34b2089614fe2a814316a6a'
TOOLCHAIN = 'leanprover/lean4:v4.34.1'
PLAN_SCHEMA = 'leanglish.original-project-plan/v1'
RUN_SCHEMA = 'leanglish.original-project-worker/v1'
MODULE = re.compile(r'[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*')
HEX = re.compile(r'[a-f0-9]{64}')


def digest(value) -> str:
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


def file_hash(path: Path) -> str:
    with path.open('rb') as stream:
        h = sha256()
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
        return h.hexdigest()


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.pending')
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n', encoding='utf-8')
    temp.replace(path)


def read(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def child(root: Path, name: str) -> Path:
    p = Path(name)
    if p.is_absolute() or not p.parts or any(x in {'..', '.'} for x in p.parts):
        raise ValueError('Unsafe relative path')
    result = root.joinpath(p)
    if any(root.joinpath(*p.parts[:i]).is_symlink() for i in range(1, len(p.parts)+1)):
        raise ValueError('Symlinked input')
    if not result.resolve().is_relative_to(root.resolve()):
        raise ValueError('Path escaped root')
    return result


def pins(manifest: dict) -> dict:
    result = {}
    for p in manifest['packages']:
        name = p['name']
        if name.startswith('«') and name.endswith('»'):
            name = name[1:-1]
        if not re.fullmatch(r'[A-Za-z0-9_-]+', name) or name in result:
            raise ValueError('Invalid or duplicate dependency')
        if p.get('type') != 'git' or not re.fullmatch('[a-f0-9]{40}', p['rev']):
            raise ValueError('Dependencies must have exact Git revisions')
        if not p['url'].startswith('https://github.com/'):
            raise ValueError('Unexpected dependency host')
        if p.get('subDir') is not None:
            raise ValueError('Subdirectory dependencies need explicit auditing support')
        result[name] = {'url': p['url'], 'rev': p['rev']}
    return result


def make_plan(project: Path, source_inventory: list[dict]) -> dict:
    """Derive denominator BEFORE executing any solution: all declared libraries + configs."""
    project = project.resolve()
    source = {}
    for row in source_inventory:
        name = row['path']
        if not name.startswith('lean/') or name in source or not HEX.fullmatch(row['sha256']):
            raise ValueError('Malformed source inventory')
        source[name] = row['sha256']
    config_names = sorted(name[5:] for name in source if name.startswith('lean/ComparatorChallenges/') and name.endswith('.json'))
    tasks = []
    for name in config_names:
        p = child(project, name)
        if file_hash(p) != source['lean/' + name]:
            raise ValueError('Comparison source differs from frozen inventory')
        cfg = read(p)
        for key in ['challenge_module', 'solution_module']:
            if not MODULE.fullmatch(cfg[key]):
                raise ValueError('Unsafe comparison module')
        theorems = cfg['theorem_names']
        definitions = cfg.get('definition_names', [])
        for names in [theorems, definitions]:
            if not isinstance(names, list) or any(not isinstance(n, str) or not n for n in names) or len(names) != len(set(names)):
                raise ValueError('Malformed declaration inventory')
        if not theorems and not definitions:
            raise ValueError('Vacuous comparison')
        tasks.append({'id': 'compare:' + name, 'kind': 'comparator', 'config': name,
                      'sha256': source['lean/' + name], 'challenge_module': cfg['challenge_module'],
                      'solution_module': cfg['solution_module'], 'theorem_names': theorems,
                      'definition_names': definitions, 'enable_nanoda': cfg.get('enable_nanoda', False)})
    lakefile = project / 'lakefile.lean'
    if file_hash(lakefile) != source['lean/lakefile.lean']:
        raise ValueError('Original Lake configuration has changed')
    libraries = re.findall(r'^\s*(?:@\[default_target\]\s*)?lean_lib\s+([A-Za-z0-9_.]+)', lakefile.read_text(), re.M)
    if not libraries or len(set(libraries)) != len(libraries) or 'OAI' not in libraries:
        raise ValueError('Invalid original library inventory')
    for name in libraries:
        if not MODULE.fullmatch(name):
            raise ValueError('Unsafe library')
        tasks.append({'id': 'build:' + name, 'kind': 'library', 'library': name})
    if (project/'lean-toolchain').read_text().strip() != TOOLCHAIN:
        raise ValueError('Incorrect original toolchain')
    original_manifest = read(project/'lake-manifest.json')
    if file_hash(project/'lake-manifest.json') != source['lean/lake-manifest.json']:
        raise ValueError('Generate plan before dependency resolution')
    result = {'schema': PLAN_SCHEMA, 'upstream_commit': PIN, 'toolchain': TOOLCHAIN,
              'source_files': source, 'source_inventory_sha256': digest(source),
              'dependencies': pins(original_manifest), 'library_inventory': sorted(libraries),
              'tasks': sorted(tasks, key=lambda x:x['id'])}
    result['plan_sha256'] = digest(result)
    return result


def validate_plan(plan: dict) -> dict:
    if plan.get('schema') != PLAN_SCHEMA or plan.get('upstream_commit') != PIN or plan.get('toolchain') != TOOLCHAIN:
        raise ValueError('Wrong plan identity')
    if plan.get('plan_sha256') != digest({k:v for k,v in plan.items() if k != 'plan_sha256'}):
        raise ValueError('Plan binding mismatch')
    if plan['source_inventory_sha256'] != digest(plan['source_files']):
        raise ValueError('Source inventory binding mismatch')
    ids = [x['id'] for x in plan['tasks']]
    if ids != sorted(set(ids)) or not ids:
        raise ValueError('Plan has duplicate, unordered or missing tasks')
    configs = {n[5:] for n in plan['source_files'] if n.startswith('lean/ComparatorChallenges/') and n.endswith('.json')}
    if {t.get('config') for t in plan['tasks'] if t['kind']=='comparator'} != configs:
        raise ValueError('Comparator task inventory is incomplete')
    if sorted(t['library'] for t in plan['tasks'] if t['kind']=='library') != plan['library_inventory']:
        raise ValueError('Original library task inventory is incomplete')
    for task in plan['tasks']:
        if task['kind'] == 'library':
            if not MODULE.fullmatch(task['library']) or task['id'] != 'build:' + task['library']:
                raise ValueError('Invalid library task')
        elif task['kind'] == 'comparator':
            if task['id'] != 'compare:' + task['config'] or plan['source_files'].get('lean/'+task['config']) != task['sha256']:
                raise ValueError('Invalid comparator task')
        else:
            raise ValueError('Unknown original-project task kind')
    return plan


def verify_sources(project: Path, plan: dict, *, manifest_resolved: bool = False) -> dict:
    validate_plan(plan)
    checked = 0
    for name, expected in plan['source_files'].items():
        if manifest_resolved and name == 'lean/lake-manifest.json':
            continue
        path = child(project, name[5:])
        if not path.is_file() or file_hash(path) != expected:
            raise ValueError('Original source drift: '+name)
        checked += 1
    actual = set()
    for directory, dirs, names in os.walk(project):
        dirs[:] = [d for d in dirs if d not in {'.lake','.git','_proofreader_cache'}]
        for name in dirs + names:
            if (Path(directory)/name).is_symlink():raise ValueError('Unexpected source link')
        for name in names:
            actual.add('lean/'+(Path(directory)/name).relative_to(project).as_posix())
    if actual != set(plan['source_files']):
        raise ValueError('Original source file inventory drift')
    return {'checked_source_files':checked,'manifest_resolution_permitted':manifest_resolved}


def git(directory: Path, *args: str, env=None) -> str:
    return subprocess.check_output(['git','-C',str(directory),*args], text=True, env=env, stderr=subprocess.PIPE, timeout=90).strip()


def patched_tree(directory: Path, patch: Path | None, *, actual: bool) -> str:
    """Independent temporary index: verify EXACT patch effects, not reverse-check alone."""
    with tempfile.TemporaryDirectory() as tmp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(tmp)/'index'))
        git(directory,'read-tree','HEAD',env=env)
        if patch is not None:
            git(directory,'apply','--cached','--whitespace=nowarn',str(patch.resolve()),env=env)
        if actual:
            git(directory,'add','-A','--','.',env=env)
        return git(directory,'write-tree',env=env)


def audit_environment(project: Path, plan: dict, *, check_sources: bool = True) -> dict:
    validate_plan(plan)
    if pins(read(project/'lake-manifest.json')) != plan['dependencies']:
        raise ValueError('Original dependency manifest drift')
    source_check = verify_sources(project,plan,manifest_resolved=True) if check_sources else None
    results = {}
    for name, expected in sorted(plan['dependencies'].items()):
        p = child(project,'.lake/packages/'+name)
        if git(p,'rev-parse','HEAD') != expected['rev'] or git(p,'remote','get-url','origin') != expected['url']:
            raise ValueError('Wrong dependency revision or origin: '+name)
        patch = project/'patches'/(name+'-lean4341.patch')
        if not patch.is_file():patch = None
        expected_tree = patched_tree(p,patch,actual=False)
        actual_tree = patched_tree(p,patch,actual=True)
        if expected_tree != actual_tree:
            raise ValueError('Unapproved dependency modification: '+name)
        results[name] = dict(expected, tree=actual_tree, patch_sha256=file_hash(patch) if patch else None)
    return {'schema':'leanglish.original-environment/v1','plan_sha256':plan['plan_sha256'],
            'source_check':source_check,'dependencies':results,'environment_sha256':digest(results),
            'observations_authenticated':False}


def selection(plan: dict, kind: str, shard: int, shards: int) -> list[dict]:
    validate_plan(plan)
    if kind not in {'library','comparator'} or type(shards) is not int or type(shard) is not int or not 0 <= shard < shards <= 256:
        raise ValueError('Invalid worker selection')
    tasks=[x for x in plan['tasks'] if x['kind']==kind]
    return tasks[shard::shards]


def run_worker(project: Path, plan: dict, output: Path, *, kind: str, shard: int, shards: int,
               trust_project: bool = False, timeout: int = 1800, wall_seconds: int = 7200,
               comparator: Path | None = None, tool_receipt: Path | None = None) -> dict:
    if not trust_project:raise PermissionError('Execution requires --trust-project; this is not a sandbox')
    if not 1 <= timeout <= wall_seconds <= 20000:raise ValueError('Invalid bounded execution limits')
    targets=selection(plan,kind,shard,shards)
    output=output.resolve()
    if output.exists():raise ValueError('Use a fresh worker output; prior observations are immutable inputs')
    output.mkdir(parents=True)
    report={'schema':RUN_SCHEMA,'plan_sha256':plan['plan_sha256'],'kind':kind,'shard':shard,'shards':shards,
            'expected_tasks':len(targets),'environment_before':None,'environment_after':None,
            'targets':[{'id':x['id'],'status':'not-run','log':None} for x in targets],
            'status':'preflight','complete':False,'english_fidelity_certified':False}
    checkpoint=lambda:write(output/'worker.json',report)
    checkpoint();begin=time.monotonic()
    try:
        report['environment_before']=audit_environment(project,plan)
        if kind=='comparator':
            if comparator is None or tool_receipt is None:raise ValueError('Missing validated Comparator toolchain')
            tools=read(tool_receipt)
            if tools.get('passed') is not True or tools.get('target_toolchain') != TOOLCHAIN:
                raise ValueError('Comparator positive/negative smoke tests have not passed')
            for name in ['comparator','lean4export','landrun']:
                path=comparator.parent/name
                if file_hash(path) != tools['binaries'][name]:raise ValueError('Comparator binary drift')
            report['toolchain']=tools
            os.environ['COMPARATOR_LEAN4EXPORT']=str((comparator.parent/'lean4export').resolve())
            os.environ['COMPARATOR_LANDRUN']=str((comparator.parent/'landrun').resolve())
        report['status']='running';checkpoint()
        for task,row in zip(targets,report['targets']):
            remaining=wall_seconds-(time.monotonic()-begin)
            if remaining<10:
                row['status']='deadline-not-attempted';checkpoint();continue
            row['status']='running';checkpoint()
            command=['lake','build',task['library']] if kind=='library' else ['lake','env',str(comparator.resolve()),task['config']]
            run=run_bounded(command,project,timeout=min(timeout,remaining),max_output=32000000)
            name=sha256(task['id'].encode()).hexdigest()+'.json'
            write(output/'logs'/name,asdict(run))
            row.update(status='passed' if run.status=='passed' else ('timeout' if run.reason=='timeout' else 'failed'),
                       log='logs/'+name,log_sha256=file_hash(output/'logs'/name))
            if row['status']=='passed' and kind=='comparator':
                if 'Your solution is okay!' not in run.stdout or 'Lean default kernel accepts the solution' not in run.stdout:
                    row.update(status='failed',reason='Missing successful comparison and kernel-replay markers')
            checkpoint()
        report['environment_after']=audit_environment(project,plan)
        if report['environment_after']!=report['environment_before']:
            raise ValueError('Original environment changed during execution')
        report['complete']=all(x['status']=='passed' for x in report['targets'])
        report['status']='passed' if report['complete'] else 'partial'
    except (ValueError,OSError,subprocess.SubprocessError,KeyError) as exc:
        report['status']='environment-failed';report['error']=str(exc)
        report['complete']=False
        for row in report['targets']:
            if row['status']=='passed':row['status']='invalidated-by-environment'
    checkpoint();return report


def reconcile(plan: dict, roots: list[Path]) -> dict:
    """Retained logs required; unrelated/duplicate reports rejected; missing is not success."""
    validate_plan(plan)
    tasks={x['id']:x for x in plan['tasks']};observed={};workers=set()
    for root in roots:
        report=read(root/'worker.json')
        if report.get('schema')!=RUN_SCHEMA or report.get('plan_sha256')!=plan['plan_sha256']:
            raise ValueError('Worker source identity mismatch')
        key=(report['kind'],report['shard'],report['shards'])
        if key in workers:raise ValueError('Duplicate worker report')
        workers.add(key)
        expected=selection(plan,*key)
        rows=report['targets']
        if report['expected_tasks']!=len(expected) or [x['id'] for x in rows]!=[x['id'] for x in expected]:
            raise ValueError('Worker denominator mismatch')
        for row in rows:
            if row.get('status') not in {'not-run','running','passed','failed','timeout','deadline-not-attempted','invalidated-by-environment'}:
                raise ValueError('Unknown worker status')
            if row['id'] in observed:raise ValueError('Duplicate task outcome')
            if row['status']=='passed':
                if report.get('environment_before') is None or report.get('environment_before')!=report.get('environment_after') or report['status'] not in {'passed','partial'}:
                    raise ValueError('Success lacks matching original environment audits')
                environment = report['environment_before']
                if environment.get('schema')!='leanglish.original-environment/v1' or environment.get('plan_sha256')!=plan['plan_sha256'] or environment.get('source_check',{}).get('checked_source_files')!=len(plan['source_files'])-1:
                    raise ValueError('Wrong environment/source audit')
                deps = environment.get('dependencies',{})
                if environment.get('environment_sha256')!=digest(deps) or {n:{k:d[k] for k in ['url','rev']} for n,d in deps.items()}!=plan['dependencies']:
                    raise ValueError('Wrong dependency audit')
                p=child(root,row['log'])
                if file_hash(p)!=row.get('log_sha256'):raise ValueError('Changed or missing execution log')
                log=read(p);task=tasks[row['id']]
                command=log['command']
                if log['status']!='passed' or log['exit_code']!=0 or log.get('reason'):
                    raise ValueError('False success execution status')
                if task['kind']=='library':
                    if command!=['lake','build',task['library']]:raise ValueError('Wrong build target')
                else:
                    if len(command)!=4 or command[:2]!=['lake','env'] or command[-1]!=task['config'] or Path(command[2]).name!='comparator':raise ValueError('Wrong comparison target')
                    if report.get('toolchain',{}).get('passed') is not True:raise ValueError('Missing Comparator smoke evidence')
                    if not all(marker in log['stdout'] for marker in ['Your solution is okay!','Lean default kernel accepts the solution']):raise ValueError('Missing Comparator completion marker')
            observed[row['id']]=row
    result={'schema':'leanglish.original-project-summary/v1','plan_sha256':plan['plan_sha256'],
            'expected_tasks':len(tasks),'recorded_tasks':len(observed),'missing_tasks':sorted(set(tasks)-set(observed)),
            'statuses':dict(Counter(x['status'] for x in observed.values())),
            'full_project_build':False,'all_comparators_passed':False,'english_fidelity_certified':False,
            'observations_authenticated':False}
    for kind,field in [('library','full_project_build'),('comparator','all_comparators_passed')]:
        ids=[x['id'] for x in tasks.values() if x['kind']==kind]
        result[field]=bool(ids) and all(observed.get(i,{}).get('status')=='passed' for i in ids)
        result[kind+'_expected']=len(ids)
        result[kind+'_passed']=sum(observed.get(i,{}).get('status')=='passed' for i in ids)
    result['complete']=result['full_project_build'] and result['all_comparators_passed']
    return result
