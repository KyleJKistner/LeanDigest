#!/usr/bin/env python3
"""Render authored pilot exposition alongside the checked candidate records.

This is not a Lean-to-English compiler. Mathematical text is authored input.
The formula renderer preserves its tokens; correspondence with Lean is reviewed,
not formally proved. Native candidate acceptance is a separate input condition.
"""
from pathlib import Path
import argparse,html,json,re,hashlib
ROOT=Path(__file__).resolve().parent
EXPECTED={f'{t}-{v}' for t in ['bezout','reverse','cantor'] for v in ['original','short','structured']}

def mathml(source,display=False):
    # Static mathematical notation only; no inference or Lean parsing occurs.
    tokens=re.findall(r'rev|gcd|xs|ys|[0-9]+|[A-Za-zℤ𝒫]|.',source)
    out=[]
    for t in tokens:
        if t.isspace():
            if t=='\u2003':out.append('<mspace width="1em"/>')
            continue
        if t in {'rev','gcd'}:out.append('<mi mathvariant="normal">'+t+'</mi>')
        elif t in {'xs','ys'}:out.append('<mi>'+t+'</mi>')
        elif t.isdigit():out.append('<mn>'+t+'</mn>')
        elif t.isalpha() or t in {'ℤ','𝒫'}:out.append('<mi>'+html.escape(t)+'</mi>')
        else:out.append('<mo>'+html.escape(t)+'</mo>')
    return '<math xmlns="http://www.w3.org/1998/Math/MathML"'+(' display="block"' if display else '')+' aria-label="'+html.escape(source,quote=True)+'"><mrow>'+''.join(out)+'</mrow></math>'

def build(observation:Path,output:Path):
    r=json.loads(observation.read_text())
    if r.get('status')!='passed' or r.get('english_certified') is not False:
        raise ValueError('Need a passed native run with an explicit English boundary')
    accepted={x['id']:x for x in r['candidates'] if x.get('accepted')}
    if set(accepted)!=EXPECTED:raise ValueError('Accepted candidate inventory differs from pilot')
    for x in accepted.values():
        if not x['audit']['kernel_checked']:raise ValueError('Missing native check')
    sources={
      'bezout':(ROOT/'OriginalBezout.lean').read_text(),
      'cantor':'''theorem cantor_surjective {α} (f : α → Set α) : ¬Surjective f := fun hf ↦
  let ⟨a, ha⟩ := hf {a | a ∉ f a}
  iff_not_self <| .of_eq <| congrArg (a ∈ ·) ha''',
      'reverse':'''@[simp, grind =] theorem reverse_reverse (as : List α) : as.reverse.reverse = as := by
  simp only [reverse]; rw [reverseAux_reverseAux_nil]; rfl'''}
    for key,src in sources.items():accepted[key+'-original']['source']=src
    payload={'candidates':list(accepted.values()),'comparison':{
      'bezout':'The structured candidate factors the construction into a lemma for compatible values. The additional lemmas establish necessity and uniqueness; they are not free shortening of the main proof.',
      'cantor':'The original is already compact. The structured candidate separates the set construction from the contradiction that it differs from every image.',
      'reverse':'The shortest candidate uses the accumulator lemma. The structured candidate is longer and uses concatenation instead. Shorter code and a useful explanation are different objectives.'},
      'build':{'lean':r['lean_version'],'original_target_reuse':'rejected, including transitive aliases',
      'native_observation_sha256':hashlib.sha256(observation.read_bytes()).hexdigest(),
      'accepted':r['accepted_count'],'negative_controls':r['negative_controls'],
      'English':'authored; not formally certified','sample':'one OpenAI supporting theorem, two library controls',
      'search':'finite model-authored candidates; no autonomous model service','source': 'PR13 baseline plus standalone pilot files'}}
    # Refuse broken evidence links, even though the prose is not certified.
    page=(ROOT/'reader.html').read_text()
    for cid,names in re.findall(r'data-native="([^:"]+):([^"]+)"',page):
        present={c['name'] for c in accepted[cid]['audit']['claims']}
        if not set(names.split(','))<=present:raise ValueError('Missing linked Lean claim')
    # Some formulas contain a final list bracket. Delimiters are <<M ... M>> internally.
    prose, scripts = page.split('<script', 1)
    prose=re.sub(r'\[\[(.*?)\]\](?!\])',lambda m:mathml(m[1]),prose,flags=re.S)
    prose=re.sub(r'(<div class="display[^\"]*">)<math ',r'\1<math display="block" ',prose)
    page=prose+'<script'+scripts
    data=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    if page.count('@DATA@')!=1:raise ValueError('Data marker inventory mismatch')
    page=page.replace('@DATA@',data)
    output.write_text(page)
    return hashlib.sha256(page.encode()).hexdigest()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('observation',type=Path);p.add_argument('output',type=Path);a=p.parse_args();print(build(a.observation,a.output))
