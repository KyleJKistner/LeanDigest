"""Offline finding-level access with separate statement and proof coverage.

The input universe is the pinned upstream scope-note listing and comparison
configurations, not whichever proofs happened to compile. No Lean or network
request is executed by this builder. Observations are checked for consistency,
not authenticated. A comparison specification is never counted as a proof.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import html
import json
from pathlib import Path
import re
import shutil

from .model import canonical_json, digest
from .narrative import Snapshot
from .narrative_io import write_bundle
from .catalog_inputs import (PIN, read_json, write_json, safe_child, upstream_url,
    config_inventory, load_statements, load_proofs, families, verify_metadata)

ASSETS = Path(__file__).parent/'catalog_web'


def inline(text: str, base: str = '') -> str:
    """Small safe Markdown subset; everything not recognized stays literal."""
    text = html.unescape(text)
    text = re.sub(r'</?(?:i|em)>', '', text)
    text = re.sub(r'\$`([^`]+)`\$', r'$\1$', text)
    pattern = re.compile(r'\[([^\]\n]+)\]\(([^\s)]+)\)|\$\$([\s\S]*?)\$\$|\$([^$\n]+)\$|`([^`]+)`|\*\*([^*]+)\*\*')
    out=[]; end=0
    for m in pattern.finditer(text):
        out.append(html.escape(text[end:m.start()]))
        if m[1] is not None:
            try:
                url=upstream_url(m[2], base)
                out.append('<a rel="noreferrer" href="'+html.escape(url, quote=True)+'">'+inline(m[1],base)+'</a>')
            except ValueError:
                out.append(html.escape(m[0]))
        elif m[3] is not None or m[4] is not None:
            tex=m[3] if m[3] is not None else m[4]
            out.append('<span class="tex" data-display="'+str(m[3] is not None).lower()+'" data-tex="'+html.escape(tex, quote=True)+'">'+html.escape(tex)+'</span>')
        elif m[5] is not None:
            out.append('<code>'+html.escape(m[5])+'</code>')
        else:
            out.append('<strong>'+html.escape(m[6])+'</strong>')
        end=m.end()
    out.append(html.escape(text[end:]))
    return ''.join(out)


def markdown(text: str, base: str = '') -> str:
    blocks=[]; paragraph=[]; in_list=False; code=None
    def flush():
        if paragraph:
            blocks.append('<p>'+inline(' '.join(paragraph),base)+'</p>'); paragraph.clear()
    for line in text.splitlines():
        if line.startswith('```'):
            flush()
            if code is None: code=[]
            else: blocks.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>'); code=None
            continue
        if code is not None: code.append(line); continue
        if in_list and not line.startswith('- '): blocks.append('</ul>'); in_list=False
        if not line.strip(): flush(); continue
        if line.startswith('#'):
            flush(); n=min(4,len(line)-len(line.lstrip('#'))+1)
            blocks.append(f'<h{n}>'+inline(line.lstrip('# ').strip(),base)+f'</h{n}>')
        elif line.startswith('- '):
            flush()
            if not in_list: blocks.append('<ul>'); in_list=True
            blocks.append('<li>'+inline(line[2:],base)+'</li>')
        elif line.startswith('|'):
            flush()
            if re.fullmatch(r'[| :\-]+',line): continue
            cells=[x.strip() for x in line.strip('|').split('|')]
            blocks.append('<p class="scope-row">'+' · '.join(inline(x,base) for x in cells)+'</p>')
        else: paragraph.append(line)
    flush()
    if in_list: blocks.append('</ul>')
    if code is not None: blocks.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>')
    return '\n'.join(blocks)


def source_name(module: str) -> str:
    return sha256(module.encode()).hexdigest()[:24]+'.html'


def shell(title: str, body: str, *, root: str = '', page: str = '') -> str:
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data:; base-uri \'none\'; form-action \'none\'">'
        '<title>'+html.escape(title)+' · Leanglish</title><link rel="stylesheet" href="'+root+'assets/catalog.css">'
        '<script defer src="'+root+'assets/katex.min.js"></script><script defer src="'+root+'assets/catalog.js"></script></head>'
        '<body data-page="'+page+'"><a class="skip" href="#content">Skip to content</a><header><a class="brand" href="'+root+'index.html">Leanglish<span>.</span></a><nav aria-label="Main"><a href="'+root+'index.html">Findings</a><a href="'+root+'explanations.html">Explanation gaps</a><a href="'+root+'coverage.html">Coverage &amp; evidence</a><a href="https://github.com/KyleJKistner/LeanDigest">GitHub ↗</a></nav></header>'
        '<main id="content">'+body+'</main><footer>OpenAI mathematics collection · pinned '+PIN[:12]+' · Deterministic reading, not certified English.</footer></body></html>')


def statement_html(s: dict) -> str:
    bits=['<div class="assumptions">']
    for b in s['binders']:
        phrase='Assume ' if b['is_assumption'] or b['is_instance'] else 'Let '
        text=(b['type'] if b['is_instance'] else b['name']+' : '+b['type'])
        bits.append('<p>'+phrase+'<span class="formula">'+html.escape(text)+'</span>.</p>')
    bits+=['</div><p class="conclusion"><strong>Then</strong> <span class="formula">'+html.escape(s['conclusion'])+'</span>.</p>',
        '<details><summary>Exact qualified statement</summary><pre>'+html.escape(s['qualified_statement'])+'</pre></details>']
    return ''.join(bits)


def build(upstream: Path, lean: Path, statement_roots: list[Path], proof_roots: list[Path],
          output: Path, *, math_assets: Path | None = None, source_inventory: Path | None = None) -> dict:
    if output.exists(): raise ValueError('Use a new output directory')
    verify_metadata(upstream,lean,source_inventory)
    configs=config_inventory(lean);fs=families(upstream,configs)
    statements,statement_attempts=load_statements(statement_roots,configs,lean)
    proofs,proof_attempts=load_proofs(proof_roots,configs,lean)
    targets={(c['solution_module'],n) for c in configs.values() for n in c.get('theorem_names',[])}
    definitions={(c['solution_module'],n) for c in configs.values() for n in c.get('definition_names',[])}
    if targets & definitions: raise ValueError('A target has conflicting theorem and definition roles')
    modules={c['solution_module'] for c in configs.values()}
    required=['ComparatorChallenges/'+k+ext for k in configs for ext in ('.json','.lean')]
    required += [m.replace('.','/')+'.lean' for m in modules]
    if source_inventory is not None:
        manifest={x['path']:x for x in read_json(source_inventory)}
        for relative in required:
            path=lean/relative; entry=manifest.get('lean/'+relative)
            if not entry or digest(path.read_bytes())!=entry['sha256']: raise ValueError('Unverified original source: '+relative)
    output.mkdir(parents=True);(output/'findings').mkdir();(output/'sources').mkdir();(output/'assets').mkdir()
    for p in ASSETS.iterdir():
        if p.is_file(): shutil.copy2(p,output/'assets'/p.name)
    if math_assets is not None:
        for name in ('katex.min.js','KATEX-LICENSE'): shutil.copy2(math_assets/name,output/'assets'/name)
    else:
        (output/'assets/katex.min.js').write_text('/* MathML rendering unavailable; literal TeX is retained. */\n')
    shutil.copy2(upstream/'LICENSE',output/'OPENAI-LICENSE.txt')
    reading_rows={};errors=[]
    for key,p in sorted(proofs.items()):
        ident=p['row']['id'];dest=output/'proofs'/ident
        try:
            source=lean/(key[0].replace('.','/')+'.lean')
            coverage=write_bundle(p['record'],dest,source=source.read_text(),file='lean/'+source.relative_to(lean).as_posix(),
                receipt=p['receipt'],title=key[1],provenance_note='Retained native observation on unaltered source with shared upstream dependency pins; not a Comparator or complete-project replay.')
            for name in ('Extract.lean','run.json','stdout.txt'): shutil.copy2(p['directory']/name,dest/name)
            reading_rows[key]={'id':ident,'gaps':coverage['source_bound_unexpanded_steps'],
                'frames':p['record']['judgements_checked'],'snapshot_sha256':Snapshot(p['record']).sha256}
        except (ValueError,OSError,RuntimeError,RecursionError) as exc:
            errors.append({'module':key[0],'name':key[1],'error':str(exc)})
    for module in sorted(modules):
        relative=module.replace('.','/')+'.lean';source=(lean/relative).read_text()
        lines='\n'.join('<span class="line" id="L'+str(i)+'"><a href="#L'+str(i)+'">'+str(i)+'</a> '+html.escape(line)+'</span>' for i,line in enumerate(source.splitlines(),1))
        body='<p class="eyebrow">Exact source · not an English translation</p><h1 class="long">'+html.escape(module)+'</h1><p><a href="'+upstream_url('lean/'+relative)+'">Pinned upstream file ↗</a> · SHA-256 <code>'+digest(source)+'</code></p><pre class="source">'+lines+'</pre>'
        (output/'sources'/source_name(module)).write_text(shell(module,body,root='../'),encoding='utf-8')
        path=output/'originals'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source)
    cards=[];ledger=[]
    for f in fs:
        names={(configs[k]['solution_module'],n) for k in f['configurations'] for n in configs[k].get('theorem_names',[])}
        available=names & reading_rows.keys();full=bool(names) and available==names
        item={k:v for k,v in f.items() if k not in {'scope','description'}}
        item.update(expected_theorem_targets=len(names),proof_readings=len(available),all_target_readings_available=full)
        ledger.append(item)
        search_names=sorted({n for k in f['configurations'] for field in ('theorem_names','definition_names') for n in configs[k].get(field,[])})
        search=' '.join([f['id'],f['title'],f['description'],f['scope'] or '',*f['configurations'],*search_names])
        badge='Documented Lean scope' if f['documented'] else 'No Lean scope note in this pin'
        note=(f'{len(available)} of {len(names)} target proof readings' if f['documented'] else 'Manuscript access only')
        cards.append('<article class="card" data-search="'+html.escape(search,quote=True)+'" data-subject="'+html.escape(f['subject'])+'" data-documented="'+str(f['documented']).lower()+'" data-readers="'+str(bool(available)).lower()+'"><div class="card-top"><span>Finding '+f['id']+'</span><span>'+html.escape(f['subject'])+'</span></div><h2><a href="findings/'+f['id']+'.html">'+html.escape(f['title'])+'</a></h2><span class="badge">'+badge+'</span><p class="muted">'+note+'</p></article>')
        body='<a class="back" href="../index.html">← All findings</a><p class="eyebrow">Finding '+f['id']+' · '+html.escape(f['subject'])+'</p><h1>'+html.escape(f['title'])+'</h1>'
        body+='<div class="notice">'+(f'{len(available)} of {len(names)} theorem targets have source-bound proof readings. ' if f['documented'] else 'This finding has no Lean scope note in the pinned release. ')+'A Lean-derived specification is not a checked solution proof. English semantics and paper-to-Lean correspondence are not certified.</div>'
        body+='<section><h2>What the release claims</h2><p>'+inline(f['description'])+'</p><p class="muted">Description supplied by OpenAI; reproduced as a claim, not an independent mathematical review.</p></section>'
        if f['scope']:
            body+='<section id="scope"><h2>Formalization scope &amp; limitations</h2><p class="muted">Unabridged upstream scope note. “Documented” does not imply every result in the paper is formalized. <a href="'+upstream_url('lean/docs/'+f['id']+'.md')+'">Exact original note ↗</a></p><div class="scope">'+markdown('\n'.join(f['scope'].splitlines()[1:]),'lean/docs')+'</div></section>'
        body+='<section id="targets"><h2>Formal targets</h2>'
        for k in f['configurations']:
            c=configs[k];body+='<div class="configuration"><h3>'+html.escape(k)+'</h3><p><a href="'+upstream_url('lean/ComparatorChallenges/'+k+'.lean')+'">Comparison specification ↗</a> · <a href="../sources/'+source_name(c['solution_module'])+'">Read original solution source</a></p>'
            original=lean/'ComparatorChallenges'/f'{k}.lean'
            dest=output/'originals/ComparatorChallenges'/original.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(original,dest)
            shutil.copy2(lean/'ComparatorChallenges'/f'{k}.json',dest.with_suffix('.json'))
            for kind in ('theorem','definition'):
                for name in c.get(kind+'_names',[]):
                    s=statements.get((k,name)); key=(c['solution_module'],name);r=reading_rows.get(key)
                    body+='<article class="target"><p class="target-kind">'+kind.upper()+'</p><h4>'+html.escape(name)+'</h4>'
                    body+=(statement_html(s) if s else '<p class="notice">The statement extraction is missing. The target remains in the coverage denominator.</p>')
                    if r:
                        body+='<p class="reading-link"><a class="button" href="../proofs/'+r['id']+'/reader.html">Open structured proof reading →</a> <span>'+str(r['frames'])+' checked frames · '+str(r['gaps'])+' explicit explanation gaps</span></p>'
                    elif kind=='theorem':
                        latest=next((x for x in reversed(proof_attempts) if (x['module'],x['name'])==key),None)
                        status=latest['status'] if latest else 'not-attempted'
                        body+='<p class="muted">Proof reading not yet available. Recorded status: <code>'+html.escape(status)+'</code>. The exact solution source remains accessible above.</p>'
                    else: body+='<p class="muted">Definition reference; not counted as a theorem-proof obligation.</p>'
                    if s:
                        sid=sha256((k+'\0'+name).encode()).hexdigest()[:24]
                        write_json(output/'evidence/statements'/f'{sid}.json',s)
                        body+='<p class="small"><a href="../evidence/statements/'+sid+'.json">Inspect the Lean-derived statement record</a></p>'
                    body+='</article>'
            body+='<details><summary>Exact comparison source (includes specification placeholders)</summary><pre>'+html.escape(original.read_text())+'</pre></details></div>'
        if not f['configurations']: body+='<p>No documented Lean targets in this revision.</p>'
        body+='</section><section><h2>Manuscripts</h2><ul>'+''.join('<li><a href="'+html.escape(p['url'],quote=True)+'">'+inline(p['title'])+'</a></li>' for p in f['papers'])+'</ul></section>'
        (output/'findings'/f"{f['id']}.html").write_text(shell(f['title'],body,root='../',page='finding'),encoding='utf-8')
    total_occurrences=sum(len(c.get('theorem_names',[]))+len(c.get('definition_names',[])) for c in configs.values())
    summary={'schema':'leanglish.finding-catalog/v1','upstream_commit':PIN,'findings':len(fs),
        'documented_findings':sum(f['documented'] for f in fs),'configurations':len(configs),
        'expected_statement_entries':total_occurrences,'elaborated_statement_entries':len(statements),
        'unique_formal_targets':len(targets|definitions),'expected_theorem_targets':len(targets),'definition_references':len(definitions),
        'proof_readings':len(reading_rows),'findings_with_any_reading':sum(x['proof_readings']>0 for x in ledger),
        'findings_with_all_target_readings':sum(x['all_target_readings_available'] for x in ledger),
        'selected_checked_frames':sum(x['frames'] for x in reading_rows.values()),
        'explicit_explanation_gaps':sum(x['gaps'] for x in reading_rows.values()),
        'solution_source_modules':len(modules),'all_documented_findings_indexed':True,
        'all_specification_entries_accessible':len(statements)==total_occurrences,
        'all_theorem_readings_accessible':set(reading_rows)==targets,
        'source_hashes_checked':source_inventory is not None,'full_project_build':False,
        'comparator_executed':False,'formally_certified_english_proofs':0,'human_readability_evaluated':False,
        'rendering_failures':errors,'receipts_authenticated':False}
    subjects=sorted({f['subject'] for f in fs if f['documented']})
    body='<p class="eyebrow">The OpenAI mathematics collection · finding-level access</p><h1>Read the finding.<br>Inspect the formalization.</h1><p class="lede">One place for every documented Lean finding in the release: mathematical scope, explicit assumptions, formal statements, original source, and the proof readings available so far.</p>'
    body+='<div class="stats">'+''.join('<div><strong>'+str(n)+'</strong><span>'+label+'</span></div>' for n,label in [(summary['documented_findings'],'documented findings, all indexed'),(len(statements),'elaborated statement entries'),(len(reading_rows),'available proof readings'),(len(configs),'comparison configurations')])+'</div>'
    body+='<div class="notice">All documented findings are indexed. '+str(len(reading_rows))+' of '+str(len(targets))+' theorem targets have proof readings; the rest remain visible. <a href="coverage.html">Inspect exact coverage and limitations.</a></div>'
    body+='<form class="filters" role="search"><label>Search findings, titles, or declarations<input id="search" type="search" placeholder="Try quasi-Riemann, Catalan, Hodge, or a Lean declaration"></label><label>Coverage<select id="coverage"><option value="documented">With Lean documentation</option><option value="readings">With a proof reading</option><option value="all">All findings in the release</option></select></label><label>Subject<select id="subject"><option value="">All subjects</option>'+''.join('<option>'+html.escape(s)+'</option>' for s in subjects)+'</select></label></form><p id="result-count" role="status"></p><div class="cards" id="cards">'+''.join(cards)+'</div><p id="empty" hidden>No findings match these filters.</p>'
    (output/'index.html').write_text(shell('OpenAI findings',body,page='catalog'),encoding='utf-8')
    body='<p class="eyebrow">Coverage is multidimensional</p><h1>What is accessible.<br>What is checked.</h1><p class="lede">An upstream scope note, an elaborated specification, a source-bound proof reading, and a faithful English proof are different deliverables.</p><table><thead><tr><th>Layer</th><th>Observed result</th></tr></thead><tbody>'
    for label,value in [('Documented findings indexed',f"{summary['documented_findings']} / {summary['documented_findings']}"),('Comparison configurations',str(len(configs))),('Statement entries',f'{len(statements)} / {total_occurrences}'),('Unique formal targets',str(summary['unique_formal_targets'])),('Theorem targets with a proof reading',f'{len(reading_rows)} / {len(targets)}'),('Definition references (separate denominator)',str(len(definitions))),('Source modules included',str(len(modules))),('Selected proof frames checked',str(summary['selected_checked_frames'])),('Explicit explanation gaps',str(summary['explicit_explanation_gaps'])),('Whole original project / Comparator execution','Not completed'),('Formally certified English proofs','0'),('Human comprehension benchmark','Not performed')]:
        body+='<tr><td>'+label+'</td><td>'+value+'</td></tr>'
    body+='</tbody></table><section><h2>Interpretation</h2><p>The statements were elaborated from comparison specifications. These specifications intentionally contain placeholders. They are not solution proofs. The linked proof readings instead use retained native Lean observations, with source hashes and original-proof paths checked. The runs used original solution modules with the recorded shared dependency pins, not a complete replay of the original project or its Comparator checks.</p><p>Imported evidence is an unsigned observation. The Lean compiler, source, pretty-printer, extraction code, transport and English renderer remain within the trust boundary. A missing explanation is shown as a gap, not replaced by plausible prose.</p><p>Scope notes are reproduced without changing their claims or limitations. Neither indexing a finding nor reading its statement establishes the correctness of the paper.</p></section><p><a href="coverage.json">Machine-readable coverage</a> · <a href="catalog.json">Finding inventory</a> · <a href="evidence/attempts.json">Every retained attempt</a> · <a href="OPENAI-LICENSE.txt">Upstream license</a></p>'
    (output/'coverage.html').write_text(shell('Coverage and evidence',body),encoding='utf-8')
    write_json(output/'coverage.json',summary);write_json(output/'catalog.json',ledger)
    write_json(output/'evidence/attempts.json',{'statements':statement_attempts,'proofs':proof_attempts})
    from .explanation_gaps import write_report
    write_report(output)
    (output/'START-HERE.txt').write_text('Open index.html in a browser. No installation, network connection, API key, or Lean runtime is needed to read the included material. External paper and upstream links require a connection. See coverage.html before interpreting verification labels.\n')
    return summary


def main(argv: list[str] | None = None, *, prog: str | None = None):
    p=argparse.ArgumentParser(prog=prog,description=__doc__)
    p.add_argument('--upstream',required=True,type=Path);p.add_argument('--lean',required=True,type=Path)
    p.add_argument('--statements',action='append',required=True,type=Path);p.add_argument('--proofs',action='append',required=True,type=Path)
    p.add_argument('--output','-o',required=True,type=Path);p.add_argument('--math-assets',type=Path);p.add_argument('--source-inventory',type=Path)
    a=p.parse_args(argv);result=build(a.upstream,a.lean,a.statements,a.proofs,a.output,math_assets=a.math_assets,source_inventory=a.source_inventory)
    print(json.dumps(result,indent=2));return 0 if result['all_specification_entries_accessible'] and not result['rendering_failures'] else 2
if __name__=='__main__':raise SystemExit(main())
