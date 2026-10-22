#!/usr/bin/env python3
"""Render mathematical notes from data and bind the source links to recorded checks.

This checks file consistency and lemma references, not English semantics. It
makes no model calls. KaTeX is used only at build time to produce native MathML;
no font files or runtime rendering library are included in the output.
"""
from __future__ import annotations
import argparse
from html import escape
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent

def digest(data: bytes) -> str:return hashlib.sha256(data).hexdigest()


def validate_mathml(markup: str) -> None:
    """Reject nested MathML tokens that browsers can place on separate baselines.

    This is a layout/structure guard, not a theorem about notation semantics.
    """
    root=ET.fromstring(markup)
    for node in root.iter():
        tag=node.tag.rsplit('}',1)[-1]
        if tag in {'mi','mn','mo','ms','mtext'} and len(node):
            raise ValueError('Unsupported nested MathML token: '+tag)


def build(evidence: Path, destination: Path) -> dict:
    book=json.loads((HERE/'book.json').read_text())
    if book['english_certified'] is not False:raise ValueError('The notes must not claim certified English')
    specs={r['id']:r for r in json.loads((HERE/'candidates.json').read_text())}
    sources={};records={};outcomes={}
    requested={v for a in book['articles'] for v in a['variants'].values()}|{a['chosen'] for a in book['articles']}
    for id in sorted(requested):
        source=(HERE/specs[id]['source']).read_bytes()
        obs=json.loads((evidence/id/'outcome.json').read_text())
        raw=(evidence/id/'accepted.json').read_bytes();record=json.loads(raw)
        if not obs['accepted'] or obs['returncode']!=0 or obs['source_sha256']!=digest(source) or obs['record_sha256']!=digest(raw):
            raise ValueError('Source/check record mismatch: '+id)
        if (record['expected']!=specs[id]['target'] or record['english_certified'] is not False
            or record['target_in_dependency_closure'] is not False
            or record['same_statement_kernel_checked'] is not True or record['lean_version']!='4.34.1'):
            raise ValueError('Wrong native check: '+id)
        sources[id]=source.decode();records[id]=record;outcomes[id]=obs
    math=[]
    def register(tex,display):
        i=len(math);math.append({'tex':tex,'display':display});return f'<!--MATH:{i}-->'
    def prose(s):
        parts=re.split(r'(\\\(.*?\\\))',s,flags=re.S)
        return ''.join(register(x[2:-2],False) if x.startswith('\\(') else escape(x) for x in parts)
    def formal(ref,chosen):
        id,name=ref.split(':',1) if ':' in ref else (chosen,ref)
        matches=[f for f in records[id]['facts'] if f['name']==name]
        if len(matches)!=1:raise ValueError('Missing or ambiguous formal reference: '+ref)
        return '<details class="formal"><summary>Lean statement</summary><pre>'+escape(matches[0]['statement'])+'</pre></details>'
    def blocks(items,chosen):
        result=[]
        for b in items:
            if b['kind']=='paragraph':result.append('<p>'+prose(b['text'])+'</p>')
            elif b['kind']=='math':result.append('<div class="formula">'+register(b['tex'],True)+'</div>')
            elif b['kind']=='note':result.append('<details class="note"><summary>'+escape(b['title'])+'</summary><div class="answer">'+blocks(b['blocks'],chosen)+''.join(formal(r,chosen) for r in b['refs'])+'</div></details>')
            else:raise ValueError('Unsupported content block')
        return ''.join(result)
    example={
      'bezout':'''<section class="example"><h2>Integer example</h2><div class="controls"><label>x<input id="bx" value="6" inputmode="numeric"></label><label>y<input id="by" value="2" inputmode="numeric"></label><label>z<input id="bz" value="3" inputmode="numeric"></label><button id="bezout-run">Construct a frame</button></div><output id="bezout-output" aria-live="polite"></output><p class="hint">One choice of integer Bézout coefficients. Exact integer arithmetic; not a substitute for the general proof.</p></section>''',
      'reverse':'''<section class="example"><h2>Positions</h2><div class="controls"><label>Length<select id="reverse-length"><option>3</option><option selected>4</option><option>5</option><option>6</option></select></label><label>Position<input type="range" id="reverse-position" min="0" max="3" value="1"></label></div><div id="reverse-sequence" class="sequence"></div><output id="reverse-output" aria-live="polite"></output></section>''',
      'cantor':'''<section class="example"><h2>Finite illustration</h2><p>Each row is a proposed subset. A 1 means membership. Change any entry; D always flips the diagonal.</p><table class="diagonal-table"><thead><tr><th>Subset</th><th>0</th><th>1</th><th>2</th><th>3</th></tr></thead><tbody id="diagonal-body"></tbody></table><output id="diagonal-output" aria-live="polite"></output><p class="hint">D disagrees with row i in column i. The proof above applies to arbitrary A, not just this finite table.</p></section>'''}
    articles=[]
    for a in book['articles']:
        chosen=a['chosen']
        body='<article id="'+a['id']+'"'+(' hidden' if articles else '')+'><p class="origin">'+escape(a['origin'])+'</p><h1>'+escape(a['title'])+'</h1>'
        body+='<section class="statement"><h2 class="sr-only">Statement</h2>'+blocks(a['statement'],chosen)+'</section>'
        for sec in a['sections']:body+='<section><h2>'+escape(sec['title'])+'</h2>'+blocks(sec['blocks'],chosen)+'</section>'
        body+=example[a['example']]
        body+='<details class="comparison"><summary>Compare the Lean proofs</summary><p>'+prose(a['comparison'])+'</p><table><thead><tr><th>Version</th><th>Source characters, including new lemmas</th></tr></thead><tbody>'
        for label,id in a['variants'].items():body+='<tr><td>'+escape(label)+'</td><td class="numeric">'+str(outcomes[id]['declaration_characters'])+'</td></tr>'
        body+='</tbody></table><p class="meta">Whitespace excluded. This is a source-size measure, not a measure of understanding.</p><div class="source-tabs">'
        for j,(label,id) in enumerate(a['variants'].items()):body+=f'<button data-code="{a["id"]}-{j}" aria-pressed="{str(j==0).lower()}">'+escape(label)+'</button>'
        body+='</div>'
        for j,(label,id) in enumerate(a['variants'].items()):
            src=sources[id].split('namespace PilotCandidate\n',1)[1].rsplit('end PilotCandidate',1)[0].strip()
            body+=f'<div class="code-pane" id="{a["id"]}-{j}"'+(' hidden' if j else '')+'><pre>'+escape(src)+f'</pre><button data-download="{id}">Download Lean source</button></div>'
        body+='</details><details class="checks"><summary>Checks</summary><table><tr><td>Alternative proof</td><td>Checked against the original statement with Lean 4.34.1</td></tr><tr><td>Original theorem as a shortcut</td><td>Excluded from transitive dependencies</td></tr><tr><td>English exposition</td><td>AI-authored; not formally certified</td></tr></table><p class="meta">'+escape(a['limitations'])+'</p><details class="formal"><summary>Original Lean statement</summary><pre>'+escape(records[chosen]['statement'])+'</pre></details></details>'
        body+='<p class="print-status">Alternative Lean proof checked. Exposition is AI-authored, not formally certified. '+escape(a['limitations'])+'</p></article>'
        articles.append(body)
    nav=''.join('<button role="tab" data-open="'+a['id']+'" aria-selected="'+str(i==0).lower()+'">'+escape({'bezout':'Bézout frame','reverse':'List reversal','cantor':'Cantor'}[a['id']])+'</button>' for i,a in enumerate(book['articles']))
    payload=json.dumps({'articles':[{'id':a['id'],'title':a['title']} for a in book['articles']],'sources':sources},ensure_ascii=False).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e')
    markup='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'"><title>Proofs | Leanglish</title><style>'''+(HERE/'style.css').read_text()+'''</style></head><body><header><span class="brand">Leanglish</span><span class="label">Proofs</span></header><nav role="tablist" aria-label="Proof selection">'''+nav+'</nav><main>'+''.join(articles)+'</main><footer>Three-proof pilot · One OpenAI supporting theorem and two library controls.</footer><script type="application/json" id="reader-data">'+payload+'</script><script>'+(HERE/'reader.js').read_text()+'</script></body></html>'
    result=subprocess.run(['node',str(HERE/'render_math.js')],input=json.dumps(math),text=True,capture_output=True,check=True)
    rendered=json.loads(result.stdout)
    for formula in rendered:validate_mathml(formula)
    markup=re.sub(r'<!--MATH:(\d+)-->',lambda m:rendered[int(m[1])],markup)
    destination.parent.mkdir(parents=True,exist_ok=True);destination.write_text(markup,encoding='utf-8')
    summary={'schema':'leanglish.exposition-page/v1','html_sha256':digest(markup.encode()),'book_sha256':digest((HERE/'book.json').read_bytes()),'renderer_sha256':digest(Path(__file__).read_bytes()),'math_blocks':len(math),'articles':len(articles),'english_certified':False,'human_evaluation':False,'sources':{id:outcomes[id]['source_sha256'] for id in sources},'native_records':{id:outcomes[id]['record_sha256'] for id in records}}
    destination.with_suffix('.manifest.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',required=True,type=Path);p.add_argument('--output',required=True,type=Path);a=p.parse_args();print(json.dumps(build(a.evidence,a.output),indent=2))
