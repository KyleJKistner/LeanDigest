"""Offline finding-level access with separate statement and proof coverage.

The input universe is the pinned upstream scope-note listing and comparison
configurations, not whichever proofs happened to compile. No Lean or network
request is executed by this builder. Observations are checked for consistency,
not authenticated. A comparison specification is never counted as a proof.

Optional dependency-cone inputs add supporting lemma readings under cone/ as a
separate denominator (proofreader/cone_catalog.py); they never enter the
theorem-target coverage.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import html
import json
from pathlib import Path
import re
import shutil
import sys

from .model import canonical_json, digest
from .narrative import Narrative, Snapshot
from .narrative_io import write_bundle
from .declaration_index import (build_index, citation_links, cited_names, reading_map, summarize,
    walk_imports, select_dependencies, dependency_report, reachable_headers, validate_caps, CAPS)
from .catalog_inputs import (PIN, read_json, write_json, safe_child, upstream_url,
    config_inventory, load_statements, load_proofs, families, verify_metadata)
from . import cone_catalog

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


def source_page(module: str, source: str, dependency: dict | None = None) -> str:
    """One exact source page; a cited dependency also states why it is bundled."""
    relative=module.replace('.','/')+'.lean'
    lines='\n'.join('<span class="line" id="L'+str(i)+'"><a href="#L'+str(i)+'">'+str(i)+'</a> '+html.escape(line)+'</span>' for i,line in enumerate(source.splitlines(),1))
    note=''
    if dependency is not None:
        names,roots,path=dependency['cited_names'],dependency['citing_modules'],dependency['import_path']
        code=lambda xs,sep:sep.join('<code>'+html.escape(x)+'</code>' for x in xs)
        hops=('imports it directly.' if len(path)==2 else 'imports it through '+str(len(path)-2)+' intermediate module'+'s'*(len(path)!=3)+'.')
        note=('<p class="notice">This module is not a solution module. Proof readings of '+str(len(roots))+' solution module'+'s'*(len(roots)!=1)
              +' cite '+str(len(names))+' Lean name'+'s'*(len(names)!=1)+' that the lexical declaration index locates here: '+code(names,', ')
              +'. The citing solution module '+code(path[:1],'')+' '+hops+'</p>'
              +('<details><summary>Import path read from import headers</summary><p>'+code(path,' → ')+'</p></details>' if len(path)>2 else ''))
    eyebrow='Cited dependency source · exact source' if dependency is not None else 'Exact source'
    eyebrow+=' · not an English translation'
    body='<p class="eyebrow">'+eyebrow+'</p><h1 class="long">'+html.escape(module)+'</h1>'+note+'<p><a href="'+upstream_url('lean/'+relative)+'">Pinned upstream file ↗</a> · SHA-256 <code>'+digest(source)+'</code></p><pre class="source">'+lines+'</pre>'
    return shell(module,body,root='../')


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
          output: Path, *, math_assets: Path | None = None, source_inventory: Path | None = None,
          dependency_caps: dict | None = None, cone: Path | None = None, cone_scope: str = 'pilot',
          cone_summary: Path | None = None) -> dict:
    """``cone`` is a dependency-cone campaign directory (cone_catalog.load): its readings
    are written under cone/ as a separate denominator and linked from citing readings."""
    if output.exists(): raise ValueError('Use a new output directory')
    validate_caps(dependency_caps)  # Before anything is written.
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
    manifest=None
    if source_inventory is not None:
        manifest={x['path']:x for x in read_json(source_inventory)}
        for relative in required:
            path=lean/relative; entry=manifest.get('lean/'+relative)
            if not entry or digest(path.read_bytes())!=entry['sha256']: raise ValueError('Unverified original source: '+relative)
    sources={m:(lean/(m.replace('.','/')+'.lean')).read_text() for m in sorted(modules)}
    # Supporting lemma readings are validated in full, and bound to these readings, before anything is written.
    supporting=None if cone is None else cone_catalog.load(cone,{p['row']['id']:(k[0],k[1],Snapshot(p['record']).sha256) for k,p in proofs.items()},
                                                           sources,scope=cone_scope,summary=cone_summary)
    output.mkdir(parents=True);(output/'findings').mkdir();(output/'sources').mkdir();(output/'assets').mkdir()
    for p in ASSETS.iterdir():
        if p.is_file(): shutil.copy2(p,output/'assets'/p.name)
    if math_assets is not None:
        for name in ('katex.min.js','KATEX-LICENSE'): shutil.copy2(math_assets/name,output/'assets'/name)
    else:
        (output/'assets/katex.min.js').write_text('/* MathML rendering unavailable; literal TeX is retained. */\n')
    shutil.copy2(upstream/'LICENSE',output/'OPENAI-LICENSE.txt')
    # One lexical index of the bundled modules locates cited names; links stay
    # outside each checked reading (links.json and a separate data island).
    def load(module):  # Cited dependency modules are read only from the verified upstream tree.
        relative=module.replace('.','/')+'.lean'
        try: path=safe_child(lean,relative)
        except ValueError: return None,'path-outside-tree'  # The walk accepts only plain module names.
        if not path.is_file(): return None,'missing-file'
        data=path.read_bytes();entry=manifest.get('lean/'+relative) if manifest is not None else None
        if manifest is not None and (not entry or digest(data)!=entry['sha256']): return None,'unverified-source'
        try: return data.decode('utf-8'),'read'
        except UnicodeDecodeError: return None,'unreadable-source'
    def arguments(key,p):
        return dict(source=sources[key[0]],file='lean/'+key[0].replace('.','/')+'.lean',receipt=p['receipt'],title=key[1],
                    provenance_note='Retained native observation on unaltered source with shared upstream dependency pins; not a Comparator or complete-project replay.')
    cited={}  # The names each reading cites, from the same document write_bundle renders.
    for key,p in sorted(proofs.items()):
        try: cited[key]=set(cited_names(Narrative(p['record']).document(**arguments(key,p))))
        except (ValueError,OSError,RuntimeError,RecursionError): pass
    log=lambda message:print(message,file=sys.stderr)
    base=build_index(sources)
    roots=sorted({k[0] for k in cited})
    walk=walk_imports(roots,sources,load,set().union(*cited.values()),caps=dependency_caps,failed_known=base['failed_modules'],log=log)
    def prepare(available):
        citing={}
        for key in sorted(available & cited.keys()): citing.setdefault(key[0],set()).update(cited[key])
        selection=select_dependencies(walk,citing,base,log=log);extra={}
        for module in selection['modules']:
            text,status=load(module)
            if text is None: raise ValueError('Cited dependency source changed during the build: '+module)
            extra[module]=text;selection['modules'][module]['sha256']=digest(text.encode('utf-8'))
        return selection,extra,build_index({**sources,**extra},reachable_headers(walk['headers'],roots,set(sources)|set(extra)))
    def bundles(available,index,lemmas=None):
        rows={};failures=[];made={};names=reading_map({k:proofs[k]['row']['id'] for k in available})
        cone_map=None if supporting is None else cone_catalog.supporting_map(supporting,lemmas)
        for key,p in sorted(proofs.items()):
            ident=p['row']['id'];dest=output/'proofs'/ident
            try:
                coverage=write_bundle(p['record'],dest,**arguments(key,p),
                    links=lambda d,key=key:made.setdefault(key,citation_links(d,key[0],index,names,source_name,supporting=cone_map)))
                for name in ('Extract.lean','run.json','stdout.txt'): shutil.copy2(p['directory']/name,dest/name)
                rows[key]={'id':ident,'gaps':coverage['source_bound_unexpanded_steps'],
                    'frames':p['record']['judgements_checked'],'snapshot_sha256':Snapshot(p['record']).sha256}
            except (ValueError,OSError,RuntimeError,RecursionError) as exc:
                failures.append({'module':key[0],'name':key[1],'error':str(exc)})
        if any(set(made[k]['names'])!=cited.get(k) for k in rows):
            raise ValueError('Cited names differ between the dependency selection and the rendered reading')
        lemma_rows,lemma_failures={},[]
        if supporting is not None:  # The same visibility rule; a supporting reading names its environment module.
            # Every accepted reading is written; only those that rendered before are link targets.
            lemma_rows,lemma_failures=cone_catalog.write_readings(output,supporting,
                link=lambda d,m:citation_links(d,m,index,names,source_name,supporting=cone_map,here='cone'))
        return rows,failures,{k:made[k] for k in sorted(rows)},lemma_rows,lemma_failures
    selection,extra,index=prepare(set(proofs))
    reading_rows,errors,made,lemma_rows,lemma_errors=bundles(set(proofs),index)
    if errors or lemma_errors:  # Never link to a reading that failed to render: rebuild against the rendered set.
        selection,extra,index=prepare(set(reading_rows))
        reading_rows,errors,made,lemma_rows,lemma_errors=bundles(set(reading_rows),index,set(lemma_rows))
    payloads=list(made.values())
    write_json(output/'evidence/declaration-index.json',index)
    dependencies=dependency_report(walk,selection,payloads,index,hashes_checked=manifest is not None)
    write_json(output/'evidence/cited-dependency-sources.json',dependencies)
    for module in sorted(modules):
        relative=module.replace('.','/')+'.lean';source=sources[module]
        (output/'sources'/source_name(module)).write_text(source_page(module,source),encoding='utf-8')
        path=output/'originals'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(source)
    for module,source in sorted(extra.items()):
        relative=module.replace('.','/')+'.lean'
        (output/'sources'/source_name(module)).write_text(source_page(module,source,selection['modules'][module]),encoding='utf-8')
        path=output/'originals'/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(source.encode('utf-8'))
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
        body+='</section>'
        if supporting is not None:  # Separate denominator: listed, never counted with the targets above.
            body+=cone_catalog.finding_section(cone_catalog.finding_items([(key[1],made[key]) for key in sorted(available)],lemma_rows),cone_scope)
        body+='<section><h2>Manuscripts</h2><ul>'+''.join('<li><a href="'+html.escape(p['url'],quote=True)+'">'+inline(p['title'])+'</a></li>' for p in f['papers'])+'</ul></section>'
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
        'rendering_failures':errors,'receipts_authenticated':False,
        'cited_dependency_source_modules':len(extra),'citation_links':summarize(payloads,index,supporting=supporting is not None),
        'cited_dependency_sources':{k:dependencies[k] for k in ('schema','method','followed_import_prefix','searched_name_namespace','source_hashes_checked',
            'caps','caps_hit','counts','names_by_link','names_by_search','project_names_by_search')}}
    if supporting is not None:
        summary['dependency_cone']=cone_catalog.section(supporting,lemma_rows,lemma_errors,payloads,
            summarize([r['links'] for _,r in sorted(lemma_rows.items())],index,supporting=True))
        write_json(output/cone_catalog.SUMMARY_RECORD,supporting['summary'])
    subjects=sorted({f['subject'] for f in fs if f['documented']})
    body='<p class="eyebrow">The OpenAI mathematics collection · finding-level access</p><h1>Read the finding.<br>Inspect the formalization.</h1><p class="lede">One place for every documented Lean finding in the release: mathematical scope, explicit assumptions, formal statements, original source, and the proof readings available so far.</p>'
    body+='<div class="stats">'+''.join('<div><strong>'+str(n)+'</strong><span>'+label+'</span></div>' for n,label in [(summary['documented_findings'],'documented findings, all indexed'),(len(statements),'elaborated statement entries'),(len(reading_rows),'available proof readings'),(len(configs),'comparison configurations')])+'</div>'
    body+='<div class="notice">All documented findings are indexed. '+str(len(reading_rows))+' of '+str(len(targets))+' theorem targets have proof readings; the rest remain visible. <a href="coverage.html">Inspect exact coverage and limitations.</a></div>'
    body+='<form class="filters" role="search"><label>Search findings, titles, or declarations<input id="search" type="search" placeholder="Try quasi-Riemann, Catalan, Hodge, or a Lean declaration"></label><label>Coverage<select id="coverage"><option value="documented">With Lean documentation</option><option value="readings">With a proof reading</option><option value="all">All findings in the release</option></select></label><label>Subject<select id="subject"><option value="">All subjects</option>'+''.join('<option>'+html.escape(s)+'</option>' for s in subjects)+'</select></label></form><p id="result-count" role="status"></p><div class="cards" id="cards">'+''.join(cards)+'</div><p id="empty" hidden>No findings match these filters.</p>'
    (output/'index.html').write_text(shell('OpenAI findings',body,page='catalog'),encoding='utf-8')
    body='<p class="eyebrow">Coverage is multidimensional</p><h1>What is accessible.<br>What is checked.</h1><p class="lede">An upstream scope note, an elaborated specification, a source-bound proof reading, and a faithful English proof are different deliverables.</p><table><thead><tr><th>Layer</th><th>Observed result</th></tr></thead><tbody>'
    cl=summary['citation_links'];pn=cl['project_names'];dc=summary['cited_dependency_sources']
    for label,value in [('Documented findings indexed',f"{summary['documented_findings']} / {summary['documented_findings']}"),('Comparison configurations',str(len(configs))),('Statement entries',f'{len(statements)} / {total_occurrences}'),('Unique formal targets',str(summary['unique_formal_targets'])),('Theorem targets with a proof reading',f'{len(reading_rows)} / {len(targets)}'),('Definition references (separate denominator)',str(len(definitions))),('Solution source modules included',str(len(modules))),('Cited dependency source modules included',str(len(extra))),('Project modules visited while following import headers',str(dc['counts']['modules_visited'])),('Cited dependency caps reached',', '.join(dc['caps_hit']) or 'None'),('Selected proof frames checked',str(summary['selected_checked_frames'])),('Explicit explanation gaps',str(summary['explicit_explanation_gaps'])),('Cited project names (OAI.*) in the readings',str(pn['cited'])),('… linked to a proof reading of the same constant',str(pn['linked_to_reading'])),*([(cone_catalog.LINK_ROW,str(pn['linked_to_cone_reading']))] if supporting is not None else []),('… linked only to a declaration line in bundled source',str(pn['linked_to_source'])),('… unresolved (not in the bundled declaration index, Lean-generated, ambiguous, or not visibly imported)',str(pn['unresolved'])),('Whole original project / Comparator execution','Not completed'),('Formally certified English proofs','0'),('Human comprehension benchmark','Not performed')]:
        body+='<tr><td>'+label+'</td><td>'+value+'</td></tr>'
    if supporting is not None: body+=cone_catalog.coverage_rows(summary['dependency_cone'])
    body+='</tbody></table><section><h2>Interpretation</h2><p>The statements were elaborated from comparison specifications. These specifications intentionally contain placeholders. They are not solution proofs. The linked proof readings instead use retained native Lean observations, with source hashes and original-proof paths checked. The runs used original solution modules with the recorded shared dependency pins, not a complete replay of the original project or its Comparator checks.</p><p>Imported evidence is an unsigned observation. The Lean compiler, source, pretty-printer, extraction code, transport and English renderer remain within the trust boundary. A missing explanation is shown as a gap, not replaced by plausible prose.</p><p>Scope notes are reproduced without changing their claims or limitations. Neither indexing a finding nor reading its statement establishes the correctness of the paper.</p><p>Citation links are navigation aids outside each checked reading. A cited Lean name links to a bundled proof reading of the same constant, else to its declaration line in bundled source, only when the recorded import headers show it is that constant. A cited dependency source page is an exact upstream file in which the lexical index locates a cited name and that a citing solution module imports, directly or through other modules; the import headers read to establish this are recorded with the declaration index. Ambiguous names, Lean-generated names and names the lexical index of the bundled modules does not record stay visibly unresolved, each with its reason. A link does not mean the citation is explained or checked.</p>'+(cone_catalog.NOTE if supporting is not None else '')+'</section><p><a href="coverage.json">Machine-readable coverage</a> · <a href="catalog.json">Finding inventory</a> · <a href="evidence/declaration-index.json">Declaration index for citation links</a> · <a href="evidence/cited-dependency-sources.json">Cited dependency sources</a>'+(cone_catalog.EVIDENCE_LINK if supporting is not None else '')+' · <a href="evidence/attempts.json">Every retained attempt</a> · <a href="OPENAI-LICENSE.txt">Upstream license</a></p>'
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
    p.add_argument('--dependency-caps',type=json.loads,help='JSON object overriding the cited dependency caps: '+', '.join(CAPS))
    p.add_argument('--cone',type=Path,help='Dependency-cone campaign directory: dependency-cone-plan/ and shard directories (separate denominator)')
    p.add_argument('--cone-scope',default='pilot',help='Dispatch scope of the cone shards (default: pilot)')
    p.add_argument('--cone-summary',type=Path,help='Campaign summary that the reconciled cone outcomes must equal')
    a=p.parse_args(argv)
    try: validate_caps(a.dependency_caps)
    except ValueError as exc: p.error(str(exc))
    result=build(a.upstream,a.lean,a.statements,a.proofs,a.output,math_assets=a.math_assets,source_inventory=a.source_inventory,dependency_caps=a.dependency_caps,
                 cone=a.cone,cone_scope=a.cone_scope,cone_summary=a.cone_summary)
    failed=result['rendering_failures'] or result.get('dependency_cone',{}).get('rendering_failures')
    print(json.dumps(result,indent=2));return 0 if result['all_specification_entries_accessible'] and not failed else 2
if __name__=='__main__':raise SystemExit(main())
