#!/usr/bin/env python3
"""Rebuild the full retained Bézout reader offline; no Lean or model calls."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader.kernel_io import strict_json
from proofreader.narrative import Snapshot
from proofreader.narrative_io import write_bundle
from proofreader.render import load_document,write_html
from proofreader.model import digest

ROOT=Path(__file__).resolve().parents[1]
def main():
    a=ROOT/'artifacts/v0.3'
    record=Snapshot.read(a/'bezout.narrative.json').record
    receipt=strict_json((a/'bezout.receipt.json').read_bytes())
    src_path='lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean'
    source=(ROOT/'examples/openai'/src_path).read_text(encoding='utf-8')
    assert digest((a/'bezout-4.34.1-valid.lean').read_bytes())==receipt['source_sha256']
    summary=write_bundle(record,a/'bezout-reader',source=source,file=src_path,receipt=receipt,
         title='Bézout-frame construction',provenance_note=receipt['provenance_note'])
    for source_name,target in [('bezout.narrative.json','bezout-snapshot.json'),('bezout.receipt.json','bezout-receipt.json'),
        ('bezout-4.34.1-valid.lean','bezout-reproduce.lean'),('bezout-minimal-context.lean','bezout-context.lean')]:
        (ROOT/'proofreader/data'/target).write_bytes((a/source_name).read_bytes())
    (ROOT/'proofreader/data/bezout-original.lean').write_text(source,encoding='utf-8')
    (ROOT/'proofreader/data/Narrative.lean').write_bytes((ROOT/'lean/Narrative.lean').read_bytes())
    data=load_document((a/'bezout-reader/reading.json').read_bytes())
    (ROOT/'proofreader/data/narrative-demo.json').write_text(data.to_json(),encoding='utf-8')
    old=load_document((ROOT/'proofreader/data/kernel-demo.json').read_bytes())
    old.declarations=[x for x in old.declarations if x.name!=record['theorem']]
    data.declarations.extend(old.declarations)
    known={f['path'] for f in data.files}
    data.files.extend(f for f in old.files if f['path'] not in known)
    data.title='Leanglish · Mathematical proof library'
    data.provenance['scope']='One source-bound substantial proof, five exact-DAG examples, eight source-only candidates'
    data.provenance['source_bound_experiments']=1
    (ROOT/'proofreader/data/reader-demo.json').write_text(data.to_json(),encoding='utf-8')
    write_html(data,a/'reader-library.html')
    print(summary)
if __name__=='__main__': main()
