"""Cold-restore a real original-project build checkpoint without claiming a proof.

The outer workflow supplies a digest-checked source archive, recorded plan and
checkpoint acquisition metadata. This command performs no downloads, and does
not change any source, theorem, specification, dependency pin, or patch.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import tarfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader import build_resume as br
from proofreader.original_project import read,write,file_hash,digest


def check(project: Path, seed: Path, checkpoint: Path, output: Path,
          *, trust_project: bool=False) -> dict:
    if not trust_project:
        raise PermissionError('Compiled checkpoint restoration requires --trust-project')
    if output.exists():
        raise ValueError('Use a fresh independent checkpoint-verification directory')
    plan,environment,recovery=[read(seed/(name+'.json')) for name in ('plan','environment','recovery')]
    if (recovery.get('recovery_plan_sha256') != digest({k:v for k,v in recovery.items() if k!='recovery_plan_sha256'}) or
        recovery.get('original_plan_sha256') != plan['plan_sha256'] or
        recovery.get('environment_sha256') != environment['environment_sha256']):
        raise ValueError('Checkpoint recovery-plan identity mismatch')
    acquired=read(checkpoint.parent/'checkpoint-acquisition.json')
    if (acquired.get('run_id') != 39315174445 or
        acquired.get('source_commit') != '4f9c1e823dd65023cfa7d8b9afe5e08390b8d2ad' or
        acquired.get('artifact_id') != 12217614568 or
        acquired.get('archive_sha256') != 'f0cb3658f6edbffc2e62cd8f538ea9a7529a0e4cbe4e27286241030441003523'):
        raise ValueError('Real-checkpoint acquisition is not the selected execution')
    identity=read(checkpoint/'identity.json');metadata=read(checkpoint/'build.tar.gz.json')
    matches=[j for j in recovery['module_jobs'] if j['id']==identity.get('worker_id')]
    if (len(matches)!=1 or identity.get('recovery_plan_sha256')!=recovery['recovery_plan_sha256'] or
        identity.get('checkpoint')!=metadata or identity.get('proof_verified') is not False or
        identity.get('target')!=matches[0]['module']):
        raise ValueError('Checkpoint worker assignment changed')
    archive=checkpoint/'build.tar.gz'
    state_dir=output/'state'
    state=br.initialize(project,plan,environment,state_dir,identity['target'],trust_project=True)
    restored=br.restore(project,plan,environment,state_dir,archive,metadata['archive_sha256'],trust_project=True)
    # Check the complete resulting build inventory, not just the stored count.
    with tarfile.open(archive,'r:gz') as tar:
        info=tar.getmember('CHECKPOINT.json')
        if info.size>br.MAX_MANIFEST:
            raise ValueError('Checkpoint manifest limit exceeded')
        record=json.load(tar.extractfile(info))
    expected={name:item for name,item in state['baseline'].items() if name not in record['removed']}
    expected.update(record['files'])
    actual=br.assets(project,plan['dependencies'])
    if actual!=expected or restored['restored_files']!=len(record['files']):
        raise ValueError('Cold restoration differs from the exact checkpoint build inventory')
    if read(state_dir/'state.json')['build_passed'] is not False:
        raise ValueError('A restored build must still undergo final verification')
    result={'schema':'leanglish.original-checkpoint-cold-restore/v1',
        'status':'passed','checkpoint_acquisition':acquired,
        'plan_sha256':plan['plan_sha256'],'environment_sha256':environment['environment_sha256'],
        'target':identity['target'],'checkpoint_sha256':record['checkpoint_sha256'],
        'baseline_build_files':len(state['baseline']),
        'restored_build_files':restored['restored_files'],'resulting_build_files':len(actual),
        'exact_resulting_build_inventory_verified':True,
        'original_source_audit_passed':True,'dependency_count':len(plan['dependencies']),
        'new_lean_build_executed':False,'proof_verified':False,
        'compiled_cache_authenticity_certified':False}
    write(output/'result.json',result)
    print('ORIGINAL_CHECKPOINT_RESTORED',result,flush=True)
    return result


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('project','seed','checkpoint','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--trust-project',action='store_true')
    a=parser.parse_args()
    check(a.project,a.seed,a.checkpoint,a.output,trust_project=a.trust_project)
    return 0

if __name__=='__main__':raise SystemExit(main())
