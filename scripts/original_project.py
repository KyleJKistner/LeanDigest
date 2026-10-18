"""Original-project command line. Network acquisition is kept in the workflow."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.original_project import make_plan,audit_environment,run_worker,reconcile,write,read


def main():
    p=argparse.ArgumentParser(description=__doc__);sp=p.add_subparsers(dest='mode',required=True)
    make=sp.add_parser('plan');make.add_argument('--project',type=Path,required=True);make.add_argument('--inventory',type=Path,required=True);make.add_argument('--output',type=Path,required=True)
    audit=sp.add_parser('audit');audit.add_argument('--project',type=Path,required=True);audit.add_argument('--plan',type=Path,required=True);audit.add_argument('--output',type=Path,required=True)
    run=sp.add_parser('run');run.add_argument('--project',type=Path,required=True);run.add_argument('--plan',type=Path,required=True);run.add_argument('--output',type=Path,required=True)
    run.add_argument('--kind',choices=['library','comparator'],required=True);run.add_argument('--shard',type=int,required=True);run.add_argument('--shards',type=int,required=True)
    run.add_argument('--timeout',type=int,default=1800);run.add_argument('--wall-seconds',type=int,default=7200);run.add_argument('--comparator',type=Path);run.add_argument('--tool-receipt',type=Path);run.add_argument('--trust-project',action='store_true')
    merge=sp.add_parser('reconcile');merge.add_argument('--plan',type=Path,required=True);merge.add_argument('--inputs',type=Path,required=True);merge.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.mode=='plan':result=make_plan(a.project,read(a.inventory))
    elif a.mode=='audit':result=audit_environment(a.project,read(a.plan))
    elif a.mode=='run':
        result=run_worker(a.project,read(a.plan),a.output,kind=a.kind,shard=a.shard,shards=a.shards,
            timeout=a.timeout,wall_seconds=a.wall_seconds,comparator=a.comparator,tool_receipt=a.tool_receipt,trust_project=a.trust_project)
        print(json.dumps({k:v for k,v in result.items() if k not in {'targets','environment_before','environment_after','toolchain'}},indent=2))
        return 0 if result['complete'] else 2
    else:result=reconcile(read(a.plan),[p.parent for p in sorted(a.inputs.rglob('worker.json'))])
    write(a.output,result)
    if a.mode=='reconcile':return 0 if result['complete'] else 2
    return 0

if __name__=='__main__':raise SystemExit(main())
