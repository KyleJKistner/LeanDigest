"""Completion campaign for unchanged source modules in the full original environment."""
from pathlib import Path
import argparse,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.original_project import read,write
from proofreader.proof_campaign import from_artifacts,run_module,reconcile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['plan','run','reconcile'])
    p.add_argument('--project',type=Path,required=True)
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--environment',type=Path,required=True)
    p.add_argument('--campaign',type=Path)
    p.add_argument('--baseline',type=Path,action='append',default=[])
    p.add_argument('--workers',type=Path)
    p.add_argument('--module-id')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--matrix',type=Path)
    p.add_argument('--trust-project',action='store_true')
    a=p.parse_args();plan=read(a.plan);env=read(a.environment)
    if a.mode=='plan':
        report=from_artifacts(a.project,plan,env,a.baseline);write(a.output,report)
        if a.matrix:write(a.matrix,{'include':[{'id':t['id'],'module':t['module']} for t in report['module_tasks']]})
    elif a.mode=='run':
        if a.campaign is None or not a.module_id:p.error('run requires --campaign and --module-id')
        report=run_module(a.project,plan,env,read(a.campaign),a.module_id,a.output,trust_project=a.trust_project)
        return 0 if report['complete'] else 2
    else:
        if a.campaign is None or a.workers is None:p.error('reconcile requires --campaign and --workers')
        report,roots=reconcile(a.project,plan,env,read(a.campaign),a.baseline,
                              [p.parent for p in sorted(a.workers.rglob('original-proof-worker.json'))])
        report['accepted_reading_roots']=[str(p) for p in roots];write(a.output,report)
        return 0 if report['all_theorems_have_readings'] else 2
    print(json.dumps({k:v for k,v in report.items() if k not in {'baseline','module_tasks'}},indent=2))
    return 0

if __name__=='__main__':raise SystemExit(main())
