"""Execute positive and rejection controls with the REAL Comparator and Landrun.

Only run in a disposable Linux worker. These synthetic controls are not evidence
that an OpenAI configuration passed. Toolchain overrides affect this external
verification tool only, never the original OpenAI source or project settings.
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import argparse
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.original_project import TOOLCHAIN, file_hash, write
from proofreader.lean import run_bounded


def run(bin_dir: Path, output: Path, *, nanoda_commit: str | None = None):
    bin_dir=bin_dir.resolve();output=output.resolve()
    output.mkdir(parents=True,exist_ok=True)
    report={'schema':'leanglish.comparator-toolchain/v1','target_toolchain':TOOLCHAIN,
            'comparator_commit':'d03acab154d269c06e60e4de7e4cc85deebff94b',
            'exporter_commit':'076e8e57707e813375e8f9da8bf989799ace9680',
            'landrun_commit':'5ed4a3db3a4ad930d577215c6b9abaa19df7f99f',
            'toolchain_override':'External Comparator and exporter rebuilt from 4.34.0 source pins on 4.34.1',
            'passed':False,'tests':{},'binaries':{n:file_hash(bin_dir/n) for n in ['comparator','lean4export','landrun']}}
    if nanoda_commit is not None:
        import re
        if not re.fullmatch(r'[a-f0-9]{40}',nanoda_commit):raise ValueError('An exact nanoda source revision is required')
        report['nanoda_commit']=nanoda_commit
        report['binaries']['nanoda_bin']=file_hash(bin_dir/'nanoda_bin')
        os.environ['COMPARATOR_NANODA']=str(bin_dir/'nanoda_bin')
    write(output/'toolchain.json',report)
    os.environ['COMPARATOR_LANDRUN']=str(bin_dir/'landrun')
    os.environ['COMPARATOR_LEAN4EXPORT']=str(bin_dir/'lean4export')
    cases={
        'positive':('theorem target (P : Prop) : P → P := by sorry\n', 'theorem target (P : Prop) : P → P := fun h => h\n', True),
        'type-mismatch':('theorem target : 0 = 0 := by sorry\n','theorem target : 1 = 1 := rfl\n',False),
        'extra-axiom':('theorem target : False := by sorry\n','axiom unjustified : False\ntheorem target : False := unjustified\n',False),
        'admitted-proof':('theorem target : True := by sorry\n','theorem target : True := by sorry\n',False),
        'definition-hole':('def value : Nat := sorry\ntheorem target : value = 1 := by sorry\n','def value : Nat := 1\ntheorem target : value = 1 := rfl\n',True),
    }
    if nanoda_commit is not None:
        cases['nanoda-positive']=cases['positive']
    for name,(challenge,solution,expected) in cases.items():
        p=output/name;p.mkdir()
        (p/'lean-toolchain').write_text(TOOLCHAIN+'\n')
        (p/'lakefile.toml').write_text('name = "comparator_control"\n[[lean_lib]]\nname = "Challenge"\n[[lean_lib]]\nname = "Solution"\n')
        (p/'Challenge.lean').write_text('import Lean\n'+challenge)
        (p/'Solution.lean').write_text('import Lean\n'+solution)
        config={'challenge_module':'Challenge','solution_module':'Solution','theorem_names':['target'],
                'definition_names':['value'] if name=='definition-hole' else [],
                'permitted_axioms':['propext','Classical.choice','Quot.sound'],'enable_nanoda':name=='nanoda-positive'}
        write(p/'config.json',config)
        # Resolve the empty package graph before entering the sandbox.
        init=run_bounded(['lake','update'],p,60)
        if init.status!='passed':raise RuntimeError(init.stderr)
        result=run_bounded(['lake','env',str(bin_dir/'comparator'),'config.json'],p,180)
        write(p/'run.json',asdict(result))
        success=result.status=='passed' and all(x in result.stdout for x in ['Your solution is okay!','Lean default kernel accepts the solution'])
        if name=='nanoda-positive':
            success=success and 'nanoda kernel accepts the solution' in result.stdout
        # Negative controls must reach export/comparison, not fail to start/build.
        comparison_reached='Exporting' in result.stdout and 'Solution' in result.stdout and 'error: ' not in result.stdout
        passed=success if expected else (result.exit_code not in (None,0) and not result.reason and comparison_reached and 'Your solution is okay!' not in result.stdout)
        report['tests'][name]={'passed':passed,'expected_acceptance':expected,'log_sha256':file_hash(p/'run.json')}
        write(output/'toolchain.json',report)
        if not passed:raise RuntimeError(name+': '+result.stdout[-4000:]+'\n'+result.stderr[-4000:])
    if nanoda_commit is not None:
        p=output/'nanoda-disallowed-axiom';p.mkdir()
        (p/'lean-toolchain').write_text(TOOLCHAIN+'\n')
        (p/'lakefile.toml').write_text('name = "nanoda_control"\n[[lean_lib]]\nname = "Solution"\n')
        (p/'Solution.lean').write_text('import Lean\naxiom forbidden : False\ntheorem target : False := forbidden\n')
        init=run_bounded(['lake','build','Solution'],p,90)
        if init.status!='passed':raise RuntimeError(init.stderr)
        export=run_bounded(['lake','env',str(bin_dir/'lean4export'),'Solution','--','target'],p,60)
        write(p/'export-run.json',asdict(export))
        if export.status!='passed' or 'forbidden' not in export.stdout:raise RuntimeError('Missing exact negative export')
        (p/'export.ndjson').write_text(export.stdout)
        write(p/'config.json',{'export_file_path':str(p/'export.ndjson'),'use_stdin':False,
              'permitted_axioms':['propext','Classical.choice','Quot.sound'],
              'unpermitted_axiom_hard_error':True,'nat_extension':True,'string_extension':True})
        negative=run_bounded([str(bin_dir/'nanoda_bin'),str(p/'config.json')],p,60)
        write(p/'run.json',asdict(negative))
        message=(negative.stdout+negative.stderr).lower()
        rejected=negative.exit_code not in (None,0) and not negative.reason and ('export file declares unpermitted axiom' in message and 'forbidden' in message)
        report['tests']['nanoda-disallowed-axiom']={'passed':rejected,'log_sha256':file_hash(p/'run.json')}
        if not rejected:raise RuntimeError('Nanoda did not reject the disallowed axiom export')
    forbidden=output/'forbidden-write.txt'
    sandbox=run_bounded([str(bin_dir/'landrun'),'--ro','/','--rw','/dev','-ldd','-add-exec','--','/bin/sh','-c','printf denied > "$1"','sh',str(forbidden)],output,30)
    write(output/'sandbox.json',asdict(sandbox))
    denied=sandbox.exit_code not in (None,0) and not forbidden.exists() and 'denied' in sandbox.stderr.lower()
    report['tests']['sandbox-write-denied']={'passed':denied,'log_sha256':file_hash(output/'sandbox.json')}
    report['passed']=all(x['passed'] for x in report['tests'].values())
    write(output/'toolchain.json',report)
    if not report['passed']:raise RuntimeError('Real sandbox write-denial control failed')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--bin',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--nanoda-commit');a=p.parse_args();print(run(a.bin,a.output,nanoda_commit=a.nanoda_commit))
