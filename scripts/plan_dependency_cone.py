"""Level-1 dependency-cone campaign: plan, dispatch matrix, one shard, reconciliation.

`plan` reads only the pinned release archive (digest-checked) and executes nothing.
`run` executes the unchanged original source and requires --trust-project; it is
not a sandbox. Cone readings are a separate denominator from the 536 targets.
"""
from hashlib import sha256
from pathlib import Path
import argparse,json,sys,urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.fetch_reading_corpus import CORPUS
from proofreader.dependency_cone import (make_plan,read_archive,validate_plan,scope_shards,run_shard,
                                         reconcile,REPORT)
from proofreader.kernel_io import strict_json
from proofreader.original_project import write

COMMITTED=Path(__file__).resolve().parents[1]/'benchmarks/dependency-cone/plan.json'


def plan_text(plan: dict) -> str:
    # One line per shard or cited-constant row keeps the committed plan diffable and compact.
    lines=[]
    for k in sorted(plan):
        v=plan[k]
        if isinstance(v,list) and v and isinstance(v[0],dict):
            body=',\n'.join('  '+json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':')) for x in v)
            lines.append(json.dumps(k)+':[\n'+body+'\n ]')
        else:
            lines.append(json.dumps(k)+':'+json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')))
    return '{\n '+',\n '.join(lines)+'\n}\n'


def archive_bytes(path: Path | None) -> bytes:
    return path.read_bytes() if path else urllib.request.urlopen(CORPUS['url'],timeout=300).read()


def load(path: Path):
    return strict_json(path.read_text(encoding='utf-8'))


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('mode',choices=['fetch','plan','inputs','matrix','run','reconcile'])
    p.add_argument('--archive',type=Path,help='Pinned release archive (default: download the pinned URL)')
    p.add_argument('--cone-plan',type=Path,default=COMMITTED)
    p.add_argument('--check',action='store_true',help='plan: require byte equality with --cone-plan')
    p.add_argument('--original-plan',type=Path)
    p.add_argument('--environment',type=Path)
    p.add_argument('--scope',default='pilot')
    p.add_argument('--github-output',type=Path)
    p.add_argument('--project',type=Path)
    p.add_argument('--shard')
    p.add_argument('--shards',type=Path,help='reconcile: directory searched for '+REPORT)
    p.add_argument('--dependency-cache',choices=['true','false',''],default='true',
                   help='run: whether the pinned dependency cache was restored (GitHub cache-hit output)')
    p.add_argument('--output',type=Path)
    p.add_argument('--trust-project',action='store_true')
    a=p.parse_args(argv)
    if a.mode=='fetch':
        if a.output is None:p.error('fetch requires --output')
        data=archive_bytes(None)
        if sha256(data).hexdigest()!=CORPUS['sha256']:
            print('Release archive digest does not match the pinned release',file=sys.stderr);return 1
        a.output.write_bytes(data);return 0
    if a.mode in {'plan','inputs'}:
        inputs=read_archive(archive_bytes(a.archive),CORPUS['sha256'])
        if a.mode=='inputs':
            if a.output is None:p.error('inputs requires --output')
            write(a.output/'original-plan.json',inputs['original_plan']);write(a.output/'environment.json',inputs['environment'])
            return 0
        text=plan_text(make_plan(inputs,{k:CORPUS[k] for k in ('release','url','sha256')}))
        if a.output:
            a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(text,encoding='utf-8')
        if a.check and a.cone_plan.read_text(encoding='utf-8')!=text:
            print('The committed dependency-cone plan is stale or was edited by hand',file=sys.stderr);return 1
        plan=json.loads(text)
        print(json.dumps({'plan_sha256':plan['plan_sha256'],'denominator':plan['denominator'],
                          'pilot':{k:plan['pilot'][k] for k in ('shards','lemmas','eligible_shards')}},indent=2))
        return 0
    plan=validate_plan(load(a.cone_plan))
    if a.mode=='matrix':
        shards=scope_shards(plan,a.scope)
        matrix={'include':[{'id':s['id'],'module':s['module'],'lemmas':len(s['lemmas'])} for s in shards]}
        if a.github_output:
            with a.github_output.open('a',encoding='utf-8') as out:
                out.write('matrix='+json.dumps(matrix,separators=(',',':'))+'\n'+f'count={len(shards)}\n')
        print(json.dumps({'scope':a.scope,'shards':len(shards),'lemmas':sum(x['lemmas'] for x in matrix['include'])}))
        return 0
    if a.environment is None or a.output is None:p.error(a.mode+' requires --environment and --output')
    if a.mode=='run':
        if not (a.project and a.original_plan and a.shard):p.error('run requires --project, --original-plan and --shard')
        report=run_shard(a.project.resolve(),load(a.original_plan),load(a.environment),plan,a.shard,a.output.resolve(),
                         trust_project=a.trust_project,dependency_cache=a.dependency_cache=='true')
        print(json.dumps({k:report[k] for k in ('shard_id','module','status','error','statuses','readings_generated')},indent=2))
        return 0 if report['status'] in {'complete','partial'} else 2
    if a.shards is None:p.error('reconcile requires --shards')
    roots=[x.parent for x in sorted(a.shards.rglob(REPORT))]
    summary,_=reconcile(plan,load(a.environment),roots,a.scope)
    write(a.output,summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in {'lemmas','reading_index'}},indent=2))
    return 0 if not summary['missing_shards'] else 2


if __name__=='__main__':raise SystemExit(main())
