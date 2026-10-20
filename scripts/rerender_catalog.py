"""Re-render a published offline catalog's proof readings with the current renderer.

The published catalog (an extracted `Leanglish/` directory or its release zip)
is the only input. Its SHA256SUMS.json manifest is checked before anything else
is read. No Lean runs: every reading is regenerated from its retained snapshot,
and each reading's snapshot, receipt, run record, compiler output and extraction
driver stay byte-identical. The output is a preview, not a release. release.json
and the original-project ledger still describe the published release; the
preview's own identity, counts and audits are in preview.json.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
from hashlib import sha256
import html
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from proofreader import __version__
from proofreader.catalog_audit import audit as static_audit
from proofreader.catalog_inputs import read_json, write_json, safe_child
from proofreader.declaration_index import build_index, citation_links, reading_map, summarize
from proofreader.explanation_gaps import write_report
from proofreader.finding_catalog import ASSETS, shell, source_name
from proofreader.kernel_io import strict_json
from proofreader.model import digest
from proofreader.narrative import PRINTER_VERSION
from proofreader.narrative_io import write_bundle
from scripts.assemble_finding_release import deterministic_zip
from scripts.collect_original_evidence import unpack
from scripts.fetch_reading_corpus import CORPUS

SCHEMA='leanglish.catalog-preview/v1'
ARCHIVE='leanglish-catalog-preview.zip'
# SHA256SUMS.json of the pinned release: names a verified directory input.
PUBLISHED_MANIFESTS={'a8270ae31df10530940072a454406eaa11916125e8847a5682ffb7c3d8754245':CORPUS['release']}
# Retained evidence in each reading directory: restored and checked byte for byte.
EVIDENCE=('snapshot.json','receipt.json','run.json','stdout.txt','Extract.lean')
# Written after the static audit; their manifest status is declared in advance and checked.
LATE=('preview.json','RELEASE-NOTES.md','static-audit.json','browser-audit.json','original-browser-audit.json')
NAV=re.compile(r'<nav aria-label="Main">.*?</nav>')
BRAND=re.compile(r'<a class="brand" href="((?:\.\./)*)index\.html">')
READING_LINK=re.compile(r'(href="\.\./proofs/([a-f0-9]{24})/reader\.html">Open structured proof reading →</a> <span>)'
                        r'(\d+) checked frames · (\d+)( explicit explanation gaps</span>)')
# Coverage-page text of the current builder (proofreader/finding_catalog.py build);
# tests/test_rerender_catalog.py checks that each string still appears there.
GAP_ROW='<tr><td>Explicit explanation gaps</td><td>{}</td></tr>'
CITATION_ROWS=('Cited project names (OAI.*) in the readings','… linked to a proof reading of the same constant',
    '… linked only to a declaration line in bundled source',
    '… unresolved (not in the bundled declaration index, Lean-generated, ambiguous, or not visibly imported)')
CITATION_NOTE=('<p>Citation links are navigation aids outside each checked reading. A cited Lean name links to a bundled proof reading of the same constant, '
    'else to its declaration line in bundled source, only when the bundled import headers show it is that constant. Ambiguous names, Lean-generated names '
    'and names the lexical index of the bundled modules does not record stay visibly unresolved, each with its reason. A link does not mean the citation is explained or checked.</p>')
INDEX_LINK=' · <a href="evidence/declaration-index.json">Declaration index for citation links</a>'


def require(condition, message: str) -> None:
    if not condition:raise ValueError(message)


def file_digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def materialize(published: Path, site: Path, archive_sha256: str) -> dict:
    """Copy the published site, or safely extract the release zip, into a fresh directory."""
    require(not site.exists(),'Use a new output directory')
    if published.is_dir():
        require(not any(p.is_symlink() for p in [published,*published.rglob('*')]),'The published site contains a symbolic link')
        shutil.copytree(published,site)
        return {'input':'directory','archive_sha256':None}
    require(published.is_file() and published.suffix=='.zip','Supply the published site directory or its release zip')
    actual=file_digest(published)
    require(actual==archive_sha256,'Release archive digest does not match: '+actual)
    staging=site.parent/(site.name+'.extract')
    unpack(published,staging)
    require([p.name for p in staging.iterdir()]==['Leanglish'] and (staging/'Leanglish').is_dir(),'The archive must contain only the Leanglish/ site')
    (staging/'Leanglish').rename(site);staging.rmdir()
    return {'input':'archive','archive_sha256':actual}


def site_files(site: Path) -> dict[str,str]:
    files={}
    for p in sorted(site.rglob('*')):
        require(not p.is_symlink(),'Unexpected symbolic link: '+p.relative_to(site).as_posix())
        if p.is_file() and p.relative_to(site).as_posix()!='SHA256SUMS.json':
            files[p.relative_to(site).as_posix()]=file_digest(p)
    return files


def verify_manifest(site: Path) -> dict[str,str]:
    manifest=read_json(site/'SHA256SUMS.json')
    require(isinstance(manifest,dict) and manifest,'Missing site manifest')
    for name,value in manifest.items():
        p=PurePosixPath(name)
        require(isinstance(value,str) and re.fullmatch(r'[a-f0-9]{64}',value) and not p.is_absolute() and '..' not in p.parts
                and p.as_posix()==name and '\\' not in name,'Unsafe manifest entry: '+str(name))
    actual=site_files(site)
    require(set(actual)==set(manifest),'The site differs from its manifest inventory: '
            +str(sorted(set(actual)^set(manifest))[:5]))
    changed=[k for k in manifest if actual[k]!=manifest[k]]
    require(not changed,'Published files differ from the manifest: '+str(changed[:5]))
    return manifest


def walk(steps: list[dict]):
    for s in steps:
        yield s;yield from walk(s.get('children',[]))


def gap_profile(reading: dict) -> tuple[Counter,int]:
    """Gap steps by rule, and the checked frames owned by gap steps."""
    d=reading['declarations'][0];rules=Counter();gaps=set()
    for s in walk(d['steps']):
        if s.get('fallback'):rules[s['rule']]+=1;gaps.add(s['id'])
    return rules,sum(owner in gaps for owner in d['axes']['frame_owners'].values())


def application() -> dict:
    """The renderer's identity. The source digest also covers files git does not track."""
    repo=Path(__file__).resolve().parents[1]
    files={p.relative_to(repo).as_posix():file_digest(p) for folder in ('proofreader','leanglish','scripts')
           for p in sorted((repo/folder).rglob('*')) if p.is_file() and p.suffix in {'.py','.js','.css','.html','.lean'}}
    identity={'source_files':len(files),'source_sha256':sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()}
    try:
        git=lambda *a:subprocess.check_output(['git',*a],cwd=repo,text=True,stderr=subprocess.DEVNULL).strip()
        return {'commit':git('rev-parse','HEAD'),'tree':git('rev-parse','HEAD^{tree}'),
                'tracked_tree_clean':not git('status','--porcelain','--untracked-files=no'),**identity}
    except (OSError,subprocess.CalledProcessError):
        return {'commit':None,'tree':None,'tracked_tree_clean':None,**identity}


def rerender(site: Path) -> dict:
    """Regenerate every reading in place with citation links built as finding_catalog.build builds them."""
    originals=safe_child(site,'originals')
    modules=sorted({read_json(p)['solution_module'] for p in (originals/'ComparatorChallenges').glob('*.json')})
    sources={m:safe_child(originals,m.replace('.','/')+'.lean').read_text(encoding='utf-8') for m in modules}
    index=build_index(sources)
    keys={}
    for d in sorted((site/'proofs').iterdir()):
        require(d.is_dir() and re.fullmatch(r'[a-f0-9]{24}',d.name),'Unexpected proof directory: '+d.name)
        reading=read_json(d/'reading.json');require(len(reading['declarations'])==1,'Expected one declaration per reading')
        dec=reading['declarations'][0];file=dec['file']
        require(file.startswith('lean/') and file.endswith('.lean'),'Missing catalog solution module identity')
        key=(file[5:-5].replace('/','.'),dec['name'])
        require(key[0] in sources and sha256('\0'.join(key).encode()).hexdigest()[:24]==d.name,'Mismatched proof identity: '+d.name)
        keys[key]=d.name
    names=reading_map(keys);made={};rows={};failures=[]
    for key,ident in sorted(keys.items()):
        dest=site/'proofs'/ident
        try:
            base=read_json(dest/'reading.json');dec=base['declarations'][0]
            kept={n:(dest/n).read_bytes() for n in EVIDENCE}
            record=strict_json(kept['snapshot.json']);receipt=strict_json(kept['receipt.json'])
            require(record['theorem']==key[1],'Snapshot theorem differs from its reading')
            require(base['files'][0]['sha256']==digest(sources[key[0]]),'Bundled solution module differs from the published reading source')
            # The published title and provenance note are preserved. The renderer writes two fixed
            # warnings, then the note, then any display-notation warning of its own.
            note=dec['warnings'][2] if len(dec['warnings'])>2 else None
            before=read_json(dest/'coverage.json')['source_bound_unexpanded_steps']
            before_rules,before_frames=gap_profile(base)
            require(before==sum(before_rules.values()),'Published reading and coverage gap counts differ')
            coverage=write_bundle(record,dest,source=sources[key[0]],file=dec['file'],receipt=receipt,title=base['title'],
                provenance_note=note,links=lambda d,key=key:made.setdefault(key,citation_links(d,key[0],index,names,source_name)))
            for n,data in kept.items():
                if (dest/n).read_bytes()!=data:
                    require(not n.endswith('.json') or strict_json((dest/n).read_bytes())==strict_json(data),'Rewritten evidence differs: '+n)
                    (dest/n).write_bytes(data)
            after=read_json(dest/'reading.json');after_rules,after_frames=gap_profile(after)
            warnings=after['declarations'][0]['warnings']
            require(after['title']==base['title'] and len(set(warnings))==len(warnings) and (note is None or warnings[2]==note),
                    'Reading title or provenance note changed')
            rows[key]={'id':ident,'frames':record['judgements_checked'],
                'before':{'gaps':before,'gap_frames':before_frames,'rules':before_rules,'printer':dec['axes'].get('printer_version')},
                'after':{'gaps':coverage['source_bound_unexpanded_steps'],'gap_frames':after_frames,'rules':after_rules}}
        except (ValueError,KeyError,OSError,RuntimeError,RecursionError) as exc:
            failures.append({'proof_id':ident,'module':key[0],'name':key[1],'error':str(exc)[:500]})
    # Unlike a fresh build, a preview never drops a published reading: any failure stops it.
    require(not failures,'Re-rendering failed for '+str(len(failures))+' readings: '+json.dumps(failures[:5]))
    return {'index':index,'rows':rows,'payloads':[made[k] for k in sorted(rows)]}


def update_finding_pages(site: Path, rows: dict) -> int:
    by_id={r['id']:r for r in rows.values()};count=0
    for page in sorted((site/'findings').glob('*.html')):
        text=page.read_text(encoding='utf-8')
        def replace(m):
            nonlocal count
            r=by_id.get(m[2]);require(r is not None,'A finding page links to an unknown reading: '+m[2])
            require(int(m[3])==r['frames'] and int(m[4])==r['before']['gaps'],'Published finding-page counts differ for '+m[2])
            count+=1;return m[1]+m[3]+' checked frames · '+str(r['after']['gaps'])+m[5]
        page.write_text(READING_LINK.sub(replace,text),encoding='utf-8')
    return count


def update_coverage_page(site: Path, before: dict, after: dict) -> None:
    path=site/'coverage.html';text=path.read_text(encoding='utf-8')
    old=GAP_ROW.format(before['explicit_explanation_gaps'])
    require(text.count(old)==1,'Published coverage page gap row not found')
    text=text.replace(old,GAP_ROW.format(after['explicit_explanation_gaps']))
    pn=after['citation_links']['project_names']
    values=(pn['cited'],pn['linked_to_reading'],pn['linked_to_source'],pn['unresolved'])
    rows=''.join('<tr><td>'+label+'</td><td>'+str(v)+'</td></tr>' for label,v in zip(CITATION_ROWS,values))
    present=re.compile('<tr><td>'+re.escape(CITATION_ROWS[0])+r'</td>.*?'+re.escape(CITATION_ROWS[3])+r'</td><td>\d+</td></tr>')
    if present.search(text):text=present.sub(lambda m:rows,text,count=1)
    else:text=text.replace(GAP_ROW.format(after['explicit_explanation_gaps']),GAP_ROW.format(after['explicit_explanation_gaps'])+rows,1)
    if CITATION_NOTE not in text:
        require(text.count('</section><p><a href="coverage.json">')==1,'Coverage interpretation section not found')
        text=text.replace('</section><p><a href="coverage.json">',CITATION_NOTE+'</section><p><a href="coverage.json">',1)
    if INDEX_LINK not in text:
        anchor='<a href="catalog.json">Finding inventory</a>'
        require(text.count(anchor)==1,'Coverage evidence links not found');text=text.replace(anchor,anchor+INDEX_LINK,1)
    path.write_text(text,encoding='utf-8')


def update_navigation(site: Path) -> int:
    """Give every catalog page the current main navigation; links are only ever added."""
    count=0
    for page in sorted(site.rglob('*.html')):
        if page.relative_to(site).parts[0]=='proofs':continue
        text=page.read_text(encoding='utf-8');brand=BRAND.search(text);navs=NAV.findall(text)
        require(brand is not None and len(navs)==1,'Not a catalog page: '+page.relative_to(site).as_posix())
        current=NAV.search(shell('','',root=brand[1]))[0]
        links=lambda s:set(re.findall(r'<a [^>]*>.*?</a>',s))
        require(links(navs[0])<=links(current),'Navigation would lose a link: '+page.relative_to(site).as_posix())
        if navs[0]!=current:page.write_text(text.replace(navs[0],current,1),encoding='utf-8');count+=1
    return count


def notice(root: str, readings: int) -> str:
    return ('<p class="notice">Catalog preview, not a release. The '+str(readings)+' published proof readings were re-rendered with renderer <code>'
            +html.escape(PRINTER_VERSION)+'</code>. No Lean ran; snapshots, receipts and run records are unchanged. '
            '<a href="'+root+'preview.html">Changes in this preview</a></p>')


def add_notices(site: Path, readings: int) -> int:
    pages=[site/n for n in ('index.html','coverage.html','explanations.html','original-verification.html') if (site/n).is_file()]
    pages+=sorted((site/'findings').glob('*.html'))
    for page in pages:
        text=page.read_text(encoding='utf-8');root='../'*(len(page.relative_to(site).parts)-1)
        require(text.count('<main id="content">')==1,'Preview notice location is missing')
        page.write_text(text.replace('<main id="content">','<main id="content">'+notice(root,readings),1),encoding='utf-8')
    return len(pages)


def category(path: str) -> str:
    parts=path.split('/')
    if parts[0]=='proofs' and len(parts)==3:return 'proofs/*/'+parts[2]
    if parts[0] in {'findings','sources'} and len(parts)==2:return parts[0]+'/*.html'
    if parts[:2]==['evidence','statements']:return 'evidence/statements/*.json'
    if parts[0] in {'originals','original-evidence'}:return parts[0]+'/**'
    return path


def changes(base: dict, current: dict, declared: dict | None = None) -> dict:
    table={}
    for path in sorted(set(base)|set(current)|set(declared or {})):
        if declared and path in declared:status=declared[path]
        elif path not in current:status='removed'
        else:status='added' if path not in base else 'unchanged' if base[path]==current[path] else 'replaced'
        table.setdefault(category(path),Counter())[status]+=1
    return {k:dict(sorted(v.items())) for k,v in sorted(table.items())}


def per_reading(rows: dict) -> dict:
    """How many readings have fewer, the same or more gap steps and gap frames than published."""
    def compare(key):
        c=Counter('fewer' if r['after'][key]<r['before'][key] else 'more' if r['after'][key]>r['before'][key] else 'same' for r in rows.values())
        return {k:c[k] for k in ('fewer','same','more')}
    return {'gap_steps':compare('gaps'),'frames_in_gaps':compare('gap_frames')}


def profile(rows: dict, side: str) -> dict:
    rules=Counter()
    for r in rows.values():rules.update(r[side]['rules'])
    return {'explicit_explanation_gaps':sum(r[side]['gaps'] for r in rows.values()),
            'frames_in_explanation_gaps':sum(r[side]['gap_frames'] for r in rows.values()),
            'readings_without_gaps':sum(r[side]['gaps']==0 for r in rows.values()),
            'gaps_by_rule':dict(sorted(rules.items(),key=lambda x:(-x[1],x[0])))}


def preview_page(record: dict) -> str:
    esc=html.escape;p=record['published'];b,a=record['explanation_gaps']['published'],record['explanation_gaps']['preview']
    cl=record['citation_links']['preview']['project_names'];old=(record['citation_links']['published'] or {}).get('project_names')
    origin=('the published release <code>'+esc(p['release'])+'</code>' if p['release'] else
            'a published catalog with manifest SHA-256 <code>'+esc(p['manifest_sha256'])+'</code>')
    body=('<h1>Catalog preview</h1><p class="lede">This catalog is '+origin+' with its '
          +str(record['readings']['re_rendered'])+' proof readings re-rendered by renderer <code>'+esc(record['renderer']['printer_version'])
          +'</code>. No Lean ran. It is not a release.</p>')
    body+='<div class="stats">'+''.join('<div><strong>'+str(n)+'</strong><span>'+label+'</span></div>' for n,label in [
        (a['explicit_explanation_gaps'],'explicit explanation gaps (published: '+str(b['explicit_explanation_gaps'])+')'),
        (record['readings']['re_rendered'],'proof readings re-rendered'),(record['readings']['added'],'readings added'),
        (record['evidence']['files'],'evidence files byte-identical to the published manifest')])+'</div>'
    printers=', '.join(esc(k)+' ('+str(v)+')' for k,v in sorted(p['printer_versions'].items()))
    cells=[('Renderer',printers,esc(record['renderer']['printer_version'])),
           ('Explicit explanation gaps',b['explicit_explanation_gaps'],a['explicit_explanation_gaps']),
           ('Checked frames inside explanation gaps',b['frames_in_explanation_gaps'],a['frames_in_explanation_gaps']),
           ('Readings without explanation gaps',b['readings_without_gaps'],a['readings_without_gaps']),
           ('Selected proof frames checked',record['selected_checked_frames'],record['selected_checked_frames'])]
    for label,key in [('Cited project names (OAI.*)','cited'),('… linked to a proof reading','linked_to_reading'),
                      ('… linked only to a bundled source line','linked_to_source'),('… unresolved','unresolved')]:
        cells.append((label,old[key] if old else 'No citation links',cl[key]))
    body+='<section><h2>Changes</h2><table><thead><tr><th>Measure</th><th>Published</th><th>Preview</th></tr></thead><tbody>'
    body+=''.join('<tr><td>'+label+'</td><td>'+str(x)+'</td><td>'+str(y)+'</td></tr>' for label,x,y in cells)+'</tbody></table>'
    body+=('<p>Several checked frames can be grouped into one displayed step. Such grouping lowers the gap count without explaining '
           'those frames; the frame count above shows it.</p><h3>Change per reading</h3><table><thead><tr><th>Readings with</th>'
           '<th>Fewer</th><th>The same</th><th>More</th></tr></thead><tbody>')
    for label,key in [('Gap steps','gap_steps'),('Checked frames inside gaps','frames_in_gaps')]:
        c=record['explanation_gaps']['per_reading'][key]
        body+='<tr><td>'+label+'</td><td>'+str(c['fewer'])+'</td><td>'+str(c['same'])+'</td><td>'+str(c['more'])+'</td></tr>'
    body+=('</tbody></table><h3>Explanation gaps by rule</h3><table><thead><tr><th>Rule</th><th>Published</th><th>Preview</th></tr></thead><tbody>')
    rules=sorted(set(b['gaps_by_rule'])|set(a['gaps_by_rule']),key=lambda r:(-a['gaps_by_rule'].get(r,0),-b['gaps_by_rule'].get(r,0),r))
    body+=''.join('<tr><td><code>'+esc(r)+'</code></td><td>'+str(b['gaps_by_rule'].get(r,0))+'</td><td>'+str(a['gaps_by_rule'].get(r,0))+'</td></tr>' for r in rules)
    body+=('</tbody></table><p class="small">Rule tags come from each renderer version. A later version can split one earlier tag '
           'into several, so the rows are not a one-to-one mapping between versions.</p><h3>Files</h3>')
    body+='<p class="small">Grouped by path pattern and compared with the published manifest.</p><table><thead><tr><th>Path</th><th>Added</th><th>Replaced</th><th>Unchanged</th></tr></thead><tbody>'
    body+=''.join('<tr><td><code>'+esc(k)+'</code></td><td>'+str(v.get('added',0))+'</td><td>'+str(v.get('replaced',0))+'</td><td>'+str(v.get('unchanged',0))+'</td></tr>'
                  for k,v in record['files'].items())+'</tbody></table></section>'
    body+=('<section><h2>Unchanged</h2><ul><li>No Lean ran. Each reading was regenerated from its retained snapshot and the bundled solution module.</li>'
           '<li>The '+str(record['evidence']['files'])+' files '+', '.join('<code>'+n+'</code>' for n in EVIDENCE)+' in the reading directories are byte-identical to the published manifest.</li>'
           '<li>No reading was added or removed: '+str(record['readings']['re_rendered'])+' of '+str(record['readings']['expected_theorem_targets'])+' theorem targets have readings.</li>'
           '<li>Receipts and observations are the published ones. They are unsigned and not authenticated.</li>'
           '<li><code>release.json</code> and <code>original-verification.json</code> describe the published release, not this preview.</li></ul></section>')
    body+=('<section><h2>Verification</h2><p>Every saved reading was compared with deterministic regeneration from its snapshot, and every reader page '
           'with its reading and citation links. The static audit checked local links, anchors, citation targets and the catalog inventories. '
           'Results and the browser route are recorded in <a href="static-audit.json">static-audit.json</a> and <a href="browser-audit.json">browser-audit.json</a>. '
           'The English is not formally verified, and a reading without explanation gaps is not a certified complete proof.</p></section>'
           '<p><a href="preview.json">Machine-readable preview record</a> · <a href="explanations.html">Explanation gaps</a> · <a href="coverage.html">Coverage and evidence</a></p>')
    return shell('Catalog preview',body)


def release_notes(record: dict, published: str) -> str:
    p=record['published'];b,a=record['explanation_gaps']['published'],record['explanation_gaps']['preview']
    cl=record['citation_links']['preview']['project_names'];s=record['static_audit'];w=record['browser_audit']
    state=lambda r:'passed, route `'+r['navigation_backend']+'`' if r.get('passed') else 'not run' if r.get('not_run') else 'failed'
    browser=state(w)+('' if w.get('not_run') else '; original-verification pages '+state(record['original_browser_audit']))
    assets=[k for k,v in record['files'].items() if k.startswith('assets/') and v.get('replaced')]
    pr=record['explanation_gaps']['per_reading']
    lines=['# Catalog preview','',
        'This catalog is '+(f"the published release `{p['release']}`" if p['release'] else f"a published catalog with manifest SHA-256 `{p['manifest_sha256']}`")
        +f" with its {record['readings']['re_rendered']} proof readings "
        f"re-rendered by renderer `{record['renderer']['printer_version']}` from application commit `{record['application']['commit']}`. "
        'It is a preview, not a release.','',
        '## Changes','',
        f"- Explicit explanation gaps: {b['explicit_explanation_gaps']} published, {a['explicit_explanation_gaps']} in this preview. "
        f"Checked frames inside gaps: {b['frames_in_explanation_gaps']} published, {a['frames_in_explanation_gaps']} here."
        +(' One displayed gap step can group several checked frames, so the step count fell while more frames sit inside gaps.'
          if a['explicit_explanation_gaps']<b['explicit_explanation_gaps'] and a['frames_in_explanation_gaps']>b['frames_in_explanation_gaps'] else ''),
        f"- Per reading: {pr['gap_steps']['fewer']} fewer, {pr['gap_steps']['same']} the same and {pr['gap_steps']['more']} more gap steps; "
        f"{pr['frames_in_gaps']['fewer']} fewer, {pr['frames_in_gaps']['same']} the same and {pr['frames_in_gaps']['more']} more checked frames inside gaps.",
        f"- Citation links: of {cl['cited']} cited project names, {cl['linked_to_reading']} link to a proof reading, "
        f"{cl['linked_to_source']} only to a bundled source line, and {cl['unresolved']} stay unresolved.",
        '- Added `explanations.html` and `explanation-gaps.json`, the inventory of every explanation gap.',
        '- Updated gap counts on finding pages, `coverage.json` and `coverage.html`; added the explanation-gap link to the main navigation and a preview notice.',
        *(['- Replaced '+' and '.join('`'+n+'`' for n in assets)+' with the current catalog assets.'] if assets else []),
        '- `preview.html` and `preview.json` list every changed file group and the gap counts by rule.','',
        '## Unchanged','',
        f"- No Lean ran. No reading was added or removed: {record['readings']['re_rendered']} of {record['readings']['expected_theorem_targets']} theorem targets.",
        f"- {record['evidence']['files']} files ({', '.join('`'+n+'`' for n in EVIDENCE)} in each reading directory) are byte-identical to the published manifest.",
        '- Receipts and observations are the published, unsigned ones. `release.json` and `original-verification.json` describe the published release.',
        '- The English is not formally verified.','',
        '## Verification','',
        f"- Static audit: {'passed' if s['passed'] else 'failed'}; {s['pages']} pages, {s['local_links_checked']} local links, "
        f"{s['local_anchors_checked']} anchors and {s['citation_links_checked']} citation links checked.",
        f'- Browser audit: {browser}.','',
        'The published release notes follow unchanged.','','---','']
    return '\n'.join(lines)+'\n'+published


def browser_audits(site: Path, output: Path, route: str, *, expect: dict) -> tuple[dict,dict]:
    """Repository catalog audits plus checks of the pages this preview adds or changes."""
    from scripts.audit_finding_browser import audit as finding_audit
    harness=route=='document-harness'
    result=finding_audit(site,output/'screenshots',document_harness=harness)
    original={'not_run':True,'passed':False,'reason':'The site has no original-verification ledger.'}
    if (site/'original-verification.json').is_file():
        from scripts.audit_original_browser import audit as original_audit
        original=original_audit(site,document_harness=harness)
    result['preview_pages']=preview_browser_checks(site,harness,expect,output/'screenshots')
    return result,original


def preview_browser_checks(site: Path, harness: bool, expect: dict, shots: Path | None = None) -> dict:
    from playwright.sync_api import sync_playwright
    errors=[];external=[]
    with sync_playwright() as p:
        executable=shutil.which('chromium') or shutil.which('google-chrome')
        browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) else None)
        def load(relative):
            path=site/relative
            if not harness:page.goto(path.resolve().as_uri());return
            # Labelled document-test harness: inline the page's own local assets, then run them.
            text=path.read_text(encoding='utf-8')
            styles=re.findall(r'<link[^>]*href="([^"]+\.css)"[^>]*>',text);scripts=re.findall(r'<script[^>]*src="([^"]+)"[^>]*></script>',text)
            inline=re.findall(r'<script>([\s\S]*?)</script>',text)
            for pattern in (r'<script>[\s\S]*?</script>',r'<script[^>]*src="[^"]+"[^>]*></script>',r'<link[^>]*href="[^"]+\.css"[^>]*>'):text=re.sub(pattern,'',text)
            page.set_content(text)
            for name in styles:page.add_style_tag(content=(path.parent/name).read_text(encoding='utf-8'))
            for name in scripts:page.evaluate((path.parent/name).read_text(encoding='utf-8'))
            for script in inline:page.evaluate(script)
        load('index.html')
        link=page.locator('.notice a[href="preview.html"]')
        assert link.count()==1 and link.is_visible(),'Preview notice is not visible on the catalog page'
        if harness:load('preview.html')
        else:link.click()
        assert page.locator('h1').inner_text()=='Catalog preview'
        assert str(expect['gaps']) in page.locator('.stats').inner_text()
        if shots:page.screenshot(path=str(shots/'preview-desktop.png'),full_page=True)
        load('explanations.html')
        page.wait_for_function("document.getElementById('gap-result-count').textContent.length > 0")
        assert page.locator('.gap-reading:visible').count()==expect['readings_with_gaps']
        assert page.locator('#gap-result-count').inner_text().startswith(str(expect['gaps'])+' explanation gaps')
        head,count=expect['head']
        page.locator('#gap-head').select_option(head)
        assert page.locator('#gap-result-count').inner_text().startswith(str(count)+' explanation gaps'),'Gap filter count differs'
        if shots:page.screenshot(path=str(shots/'explanations-desktop.png'))
        load(expect['reader'])
        cited=page.locator('#dependencies a[data-citation="'+expect['citation']+'"]')
        assert cited.count()>=1 and cited.first.get_attribute('href')==expect['href'],'Citation link missing in the reader'
        browser.close()
    assert not errors,errors
    assert not external,external
    return {'navigation_backend':'direct-document-test-harness' if harness else 'real-offline-file-navigation',
            'preview_notice':True,'preview_page':True,'explanation_gap_filters':True,'reader_citation_link':True,
            'page_errors':errors,'external_requests':external,'passed':True}


def browser_expectations(site: Path) -> dict:
    """Values the browser must show, read from the site's own records."""
    gaps=read_json(site/'explanation-gaps.json')
    require(gaps['by_head'],'The explanation-gap inventory is empty; its filters cannot be exercised')
    for links in sorted((site/'proofs').glob('*/links.json')):
        names=read_json(links)['names']
        reading=next((n for n in sorted(names) if names[n]['status']=='reading'),None)
        if reading:
            return {'reader':links.parent.relative_to(site).as_posix()+'/reader.html','citation':reading,'href':names[reading]['href'],
                    'gaps':gaps['explicit_explanation_gaps'],'readings_with_gaps':gaps['readings_with_gaps'],
                    'head':next(iter(gaps['by_head'].items()))}
    raise ValueError('No reading links to another proof reading; the reader link check cannot run')


def build_preview(published: Path, output: Path, *, archive_sha256: str = CORPUS['sha256'],
                  browser: str = 'none', archive: bool = True) -> dict:
    require(browser in {'none','real','document-harness'},'Unknown browser route')
    require(not output.exists(),'Use a new output directory')
    output.mkdir(parents=True);site=output/'Leanglish'
    source=materialize(published,site,archive_sha256)
    base=verify_manifest(site)
    manifest_sha256=file_digest(site/'SHA256SUMS.json')
    before=read_json(site/'coverage.json');identity=read_json(site/'release.json') if (site/'release.json').is_file() else {}
    require(not identity or identity.get('coverage')==before,'Published release identity and coverage differ')
    previous={n:(site/n).read_text(encoding='utf-8') if (site/n).is_file() else None for n in ('RELEASE-NOTES.md','START-HERE.txt')}
    audits={n:read_json(site/n) if (site/n).is_file() else None for n in ('static-audit.json','browser-audit.json','original-browser-audit.json')}
    built=rerender(site);rows=built['rows']
    frames=sum(r['frames'] for r in rows.values())
    require(len(rows)==before['proof_readings'] and frames==before['selected_checked_frames'],'Published reading inventory differs from coverage')
    require(sum(r['before']['gaps'] for r in rows.values())==before['explicit_explanation_gaps'],'Published gap counts differ from coverage')
    after=dict(before,explicit_explanation_gaps=sum(r['after']['gaps'] for r in rows.values()),
               citation_links=summarize(built['payloads'],built['index']))
    write_json(site/'coverage.json',after);write_json(site/'evidence/declaration-index.json',built['index'])
    for p in sorted(ASSETS.iterdir()):
        if p.is_file():shutil.copy2(p,site/'assets'/p.name)
    linked=update_finding_pages(site,rows)
    update_coverage_page(site,before,after)
    gaps=write_report(site)
    navigation=update_navigation(site)
    noticed=add_notices(site,len(rows))
    start=(previous['START-HERE.txt'] or '')
    (site/'START-HERE.txt').write_text('This is a catalog preview, not a release: the published proof readings were re-rendered without running Lean. '
        'See preview.html for what changed.\n'+start,encoding='utf-8')
    evidence=[f'proofs/{r["id"]}/{n}' for r in rows.values() for n in EVIDENCE]
    require(all(base.get(p)==file_digest(site/p) for p in evidence),'Retained evidence changed')
    printers=Counter(r['before']['printer'] for r in rows.values())
    record={'schema':SCHEMA,'is_release':False,
        'published':{'release':PUBLISHED_MANIFESTS.get(manifest_sha256),
                     'input':source['input'],'archive_sha256':source['archive_sha256'],'manifest_sha256':manifest_sha256,
                     'manifest_entries_verified':len(base),'application_commit':identity.get('application_commit'),
                     'printer_versions':dict(sorted(printers.items())),'static_audit':audits['static-audit.json'],
                     'browser_audit':audits['browser-audit.json'],'original_browser_audit':audits['original-browser-audit.json']},
        'application':application(),'renderer':{'printer_version':PRINTER_VERSION,'package_version':__version__},
        'lean_executed':False,'observations_authenticated':False,'english_formally_verified':False,
        'readings':{'published':before['proof_readings'],'re_rendered':len(rows),'added':0,'removed':0,
                    'expected_theorem_targets':before['expected_theorem_targets']},
        'selected_checked_frames':frames,
        'evidence':{'files':len(evidence),'names':list(EVIDENCE),'byte_identical_to_published_manifest':True},
        'explanation_gaps':{'published':profile(rows,'before'),'preview':profile(rows,'after'),
                            'readings_with_gaps':gaps['readings_with_gaps'],'per_reading':per_reading(rows)},
        'citation_links':{'published':before.get('citation_links'),'preview':after['citation_links']},
        'pages':{'finding_reading_links_updated':linked,'navigation_updated':navigation,'preview_notices':noticed}}
    require(record['explanation_gaps']['preview']['explicit_explanation_gaps']==gaps['explicit_explanation_gaps'],'Gap inventory differs')
    declared={n:('added' if n not in base else 'replaced') for n in LATE+('preview.html',)}
    record['files']=changes(base,site_files(site),declared)
    require(not any('removed' in v for v in record['files'].values()),'A published file would be removed')
    (site/'preview.html').write_text(preview_page(record),encoding='utf-8')
    for name in ('static-audit.json','browser-audit.json','original-browser-audit.json'):
        write_json(site/name,{'not_run':True,'passed':False,'reason':'Pending.'})
    write_json(site/'preview.json',record)
    checks=static_audit(site)
    require(checks['passed'],'Static catalog audit failed: '+json.dumps(checks['errors'][:5]))
    record['static_audit']=checks
    if browser=='none':
        result={'not_run':True,'passed':False,'navigation_backend':None,'reason':'No browser audit was requested for this preview build.'}
        original=dict(result)
    else:
        expect=browser_expectations(site)
        try:
            result,original=browser_audits(site,output,browser,expect=expect)
        except Exception as exc:
            write_json(output/'browser-audit.json',{'passed':False,'route':browser,'error':str(exc)[:4000]})
            raise ValueError('Browser audit failed: '+str(exc)[:2000]) from exc
    record['browser_audit']=result;record['original_browser_audit']=original
    write_json(site/'static-audit.json',checks);write_json(site/'browser-audit.json',result)
    write_json(site/'original-browser-audit.json',original)
    (site/'RELEASE-NOTES.md').write_text(release_notes(record,previous['RELEASE-NOTES.md'] or ''),encoding='utf-8')
    write_json(site/'preview.json',record)
    current=site_files(site)
    require(changes(base,current)==record['files'],'The preview page misstates the changed files')
    require(all(base.get(p)==current[p] for p in evidence),'Retained evidence changed')
    write_json(site/'SHA256SUMS.json',current)
    require(static_audit(site)==checks,'The static audit changed after the final records were written')
    summary=dict(record,site={'files':len(current)+1,'bytes':sum((site/p).stat().st_size for p in current)+(site/'SHA256SUMS.json').stat().st_size,
                              'manifest_sha256':file_digest(site/'SHA256SUMS.json')})
    if archive:
        checksum=deterministic_zip(site,output/ARCHIVE)
        (output/'SHA256SUMS').write_text(checksum+'  '+ARCHIVE+'\n',encoding='utf-8')
        summary['archive']={'name':ARCHIVE,'sha256':checksum,'bytes':(output/ARCHIVE).stat().st_size}
    write_json(output/'summary.json',summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    p.add_argument('published',type=Path,help='Published Leanglish/ site directory or its release zip')
    p.add_argument('output',type=Path,help='New directory: Leanglish/ site, zip, summary and audit screenshots')
    p.add_argument('--archive-sha256',default=CORPUS['sha256'],help='Required digest of a zip input (default: the pinned release)')
    p.add_argument('--browser',choices=['none','real','document-harness'],default='none',
                   help='real: Chromium file:// navigation; document-harness: inlined local documents (labelled)')
    p.add_argument('--no-archive',action='store_true',help='Do not write the deterministic zip')
    a=p.parse_args(argv);started=time.monotonic()
    try:
        s=build_preview(a.published,a.output,archive_sha256=a.archive_sha256,browser=a.browser,archive=not a.no_archive)
    except ValueError as exc:
        print('Preview failed: '+str(exc),file=sys.stderr);return 2
    g=s['explanation_gaps']
    print(json.dumps({'readings':s['readings'],'explicit_explanation_gaps':{k:v['explicit_explanation_gaps'] for k,v in g.items() if isinstance(v,dict)},
        'static_audit_passed':s['static_audit']['passed'],'browser_audit':s['browser_audit'].get('navigation_backend') if s['browser_audit'].get('passed') else 'not run',
        'site':s['site'],'archive':s.get('archive')},indent=2))
    print(f'Elapsed: {time.monotonic()-started:.1f} s',file=sys.stderr)
    return 0


if __name__=='__main__':raise SystemExit(main())
