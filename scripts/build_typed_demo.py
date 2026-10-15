#!/usr/bin/env python3
"""Build the demo exclusively from actual Lean exports saved under artifacts/.

Does not execute Lean or claim to authenticate attached observations. It does
regenerate all English, verify path/argument structure and compare reading data.
"""
from pathlib import Path
import json,sys,shutil
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.kernel import read_record, Argument
from proofreader.kernel_io import axiom_status
from proofreader.english import English, check_reading, prose_text
from proofreader.model import Document, report, digest
from proofreader.render import load_document, write_html

ROOT=Path(__file__).resolve().parents[1]

def main():
    data=ROOT/'proofreader/data';data.mkdir(exist_ok=True)
    declarations=[];files=[];observations=[]
    for name in ['injective_comp','and_swap','trans','witnessed','alternatives']:
        raw=read_record(ROOT/f'artifacts/v0.2/{name}.kernel.json')
        source_file='examples/kernel/'+('Smoke.lean' if name in {'and_swap','trans'} else 'Showcase.lean')
        source=(ROOT/source_file).read_text()
        receipt=json.loads((ROOT/'artifacts/v0.2/and_swap.receipt.json').read_text()) if name=='and_swap' else None
        d=English(raw).document(source=source,file=source_file,receipt=receipt)
        dec=d.declarations[0]
        dec.axes['axiom_status']=axiom_status(raw);dec.axes['lean_version']=raw['lean_version']
        dec.warnings += ['Source panel is a readable restatement of the source snippets. Use the recorded exact checker file to reproduce the attached check.'] if receipt else []
        check_reading(raw,d)
        declarations.extend(d.declarations);files.extend(d.files)
        observations.append({'name':Argument(raw).name,**Argument(raw).coverage(),'receipt_attached':receipt is not None})
        (ROOT/f'artifacts/v0.2/{name}.proof.txt').write_text(prose_text(raw))
    source_demo=load_document((data/'demo.json').read_bytes())
    declarations.extend(source_demo.declarations);files.extend(source_demo.files)
    doc=Document('Leanglish · typed arguments',list({f['path']:f for f in files}.values()),declarations,
        provenance={'scope':'five actual typed logical/function examples plus six OpenAI source files',
            'lean_version':'4.34.0','required_openai_lean_version':'4.34.1',
            'pipeline_model_calls':0,'typed_examples':observations,
            'source_examples':{'files':6,'declarations':9,'pinned_project_replay':False},
            'external_all_judgement_checks_attached':1,'receipts_authenticated':False,
            'english_formally_verified':False,'whole_corpus_coverage':False,'human_readability_study':False})
    (data/'kernel-demo.json').write_text(doc.to_json())
    write_html(doc,ROOT/'artifacts/v0.2/reader.html')
    (ROOT/'artifacts/v0.2/demo-coverage.json').write_text(json.dumps(report(doc),indent=2)+'\n')
    shutil.copyfile(ROOT/'lean/KernelExport.lean',data/'KernelExport.lean')
    print(json.dumps({'typed_examples':len(observations),'source_declarations':len(source_demo.declarations),
                      'attached_check_records':1,'certified_english_proofs':0}))

if __name__=='__main__':main()
