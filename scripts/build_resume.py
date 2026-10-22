"""Resume original-project compilation; no command creates proof acceptance."""
from __future__ import annotations
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader import build_resume as br
from proofreader.original_project import read


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['initialize','round','pack','restore'])
    for key in ('project','plan','environment','state'):
        parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--target')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--archive',type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--seconds',type=int,default=1800)
    parser.add_argument('--trust-project',action='store_true')
    a=parser.parse_args()
    args=(a.project.resolve(),read(a.plan),read(a.environment),a.state.resolve())
    if a.action=='initialize':
        if not a.target:parser.error('--target is required')
        result=br.initialize(*args,a.target,trust_project=a.trust_project)
        result={k:v for k,v in result.items() if k!='baseline'}
    elif a.action=='round':
        if not a.output:parser.error('--output is required')
        result=br.run_round(*args,a.output.resolve(),trust_project=a.trust_project,seconds=a.seconds)
        result={k:v for k,v in result.items() if k not in ('environment_before','environment_after')}
    elif a.action=='pack':
        if not a.archive:parser.error('--archive is required')
        result=br.pack(*args,a.archive.resolve())
    else:
        if not a.archive or not a.sha256:parser.error('--archive and --sha256 are required')
        result=br.restore(*args,a.archive.resolve(),a.sha256,trust_project=a.trust_project)
    import json
    print(json.dumps(result,indent=2))
    # A timeout is a retained checkpoint, not a successful build. Workflows inspect
    # its explicit round status before final verification and publication.
    return 0 if a.action!='round' or result['status'] in ('passed','timeout') else 2

if __name__=='__main__':raise SystemExit(main())
