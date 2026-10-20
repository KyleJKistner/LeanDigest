"""Audit a generated static catalog without executing its scripts."""
from __future__ import annotations
import argparse
from html.parser import HTMLParser
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from .declaration_index import MODULE_NAME, validate_links
from .model import digest

class Links(HTMLParser):
    def __init__(self):
        super().__init__();self.refs=[];self.ids=[];self.resources=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'id' in a:self.ids.append(a['id'])
        attr='href' if tag in {'a','link'} else 'src' if tag in {'script','img','iframe'} else None
        if attr and a.get(attr):
            self.refs.append(a[attr]);self.resources.append((tag,a[attr]))

def audit(site: Path) -> dict:
    site=site.resolve();summary=json.loads((site/'coverage.json').read_text())
    catalog=json.loads((site/'catalog.json').read_text())
    def require(condition,message):
        if not condition:raise ValueError(message)
    require(len(catalog)==summary['findings'],'Finding denominator mismatch')
    require(sum(x['documented'] for x in catalog)==summary['documented_findings'],'Documented finding mismatch')
    errors=[];links=anchors=0;parsed={}
    for page in sorted(site.rglob('*.html')):
        parser=Links();parser.feed(page.read_text());parsed[page.resolve()]=parser
        if len(parser.ids)!=len(set(parser.ids)):
            errors.append({'page':str(page.relative_to(site)),'error':'duplicate HTML ids'})
    for page,parser in parsed.items():
        for tag,ref in parser.resources:
            parts=urlsplit(ref)
            if parts.scheme or parts.netloc:
                allowed=(parts.scheme=='https' and tag=='a') or (parts.scheme=='mailto' and tag=='a') or (ref.startswith('data:image/') and tag=='img')
                if not allowed:errors.append({'page':str(page.relative_to(site)),'url':ref,'error':'active scheme or external resource'})
                continue
            target=(page.parent/unquote(parts.path)).resolve() if parts.path else page
            if parts.path:
                links+=1
                if not target.is_relative_to(site) or not target.is_file():
                    errors.append({'page':str(page.relative_to(site)),'url':ref,'error':'broken or escaping local link'})
                    continue
            if parts.fragment and target in parsed:
                anchors+=1
                if unquote(parts.fragment) not in parsed[target].ids:
                    errors.append({'page':str(page.relative_to(site)),'url':ref,'error':'missing local anchor'})
    # Citation links are created by the reader script, so audit their data island
    # statically: it must equal links.json and every target must exist.
    citations=0;ids={}
    for reader in sorted((site/'proofs').glob('*/reader.html')):
        island=re.findall(r'<script id="proofreader-links" type="application/json">(.*?)</script>',reader.read_text(),re.S)
        saved=reader.parent/'links.json'
        try:data=json.loads(saved.read_text()) if saved.is_file() else None;same=not island or json.loads(island[0])==data
        except ValueError:
            errors.append({'page':str(reader.relative_to(site)),'error':'malformed citation links'});continue
        if len(island)>1 or bool(island)!=saved.is_file() or not same:
            errors.append({'page':str(reader.relative_to(site)),'error':'citation links differ from links.json'});continue
        data=data if island else {'names':{}}
        entries=data.get('names') if isinstance(data,dict) else None
        if not isinstance(entries,dict):
            errors.append({'page':str(reader.relative_to(site)),'error':'malformed citation links'});continue
        for name,v in entries.items():
            refs=[v.get('href'),(v.get('source') or {}).get('href')] if isinstance(v,dict) and isinstance(v.get('source') or {},dict) else [0]
            if any(r is not None and not isinstance(r,str) for r in refs):
                errors.append({'page':str(reader.relative_to(site)),'citation':name,'error':'malformed citation entry'});continue
            for ref in refs:
                if not ref:continue
                citations+=1;parts=urlsplit(ref);target=(reader.parent/unquote(parts.path)).resolve()
                if parts.scheme or parts.netloc or not parts.path or not target.is_relative_to(site) or not target.is_file():
                    errors.append({'page':str(reader.relative_to(site)),'citation':name,'url':ref,'error':'broken or escaping citation link'});continue
                if parts.fragment and unquote(parts.fragment) not in ids.setdefault(target,set(parsed[target].ids) if target in parsed else set()):
                    errors.append({'page':str(reader.relative_to(site)),'citation':name,'url':ref,'error':'missing citation anchor'})
        if island:  # The writer's own rules: relative catalog targets and a stated reason for every unresolved name.
            try:validate_links(data)
            except ValueError as exc:errors.append({'page':str(reader.relative_to(site)),'error':'citation links fail validation','detail':str(exc)})
    expected={f['id']+'.html' for f in catalog}
    require(expected=={p.name for p in (site/'findings').glob('*.html')},'Finding page inventory mismatch')
    require(len(list((site/'evidence/statements').glob('*.json')))==summary['elaborated_statement_entries'],'Statement file inventory mismatch')
    require(len(list((site/'proofs').glob('*/reader.html')))==summary['proof_readings'],'Proof reader inventory mismatch')
    dependencies=summary.get('cited_dependency_source_modules',0)
    require(len(list((site/'sources').glob('*.html')))==summary['solution_source_modules']+dependencies,'Source module inventory mismatch')
    # Each cited dependency page names its module, and its original copy has the recorded hash.
    record=site/'evidence/cited-dependency-sources.json'
    selected=json.loads(record.read_text())['modules'] if record.is_file() else {}
    require(len(selected)==dependencies,'Cited dependency inventory mismatch')
    for module,row in sorted(selected.items()):
        if not MODULE_NAME.fullmatch(module) or not isinstance(row,dict):
            errors.append({'module':module,'error':'malformed cited dependency record'});continue
        relative=module.replace('.','/')+'.lean';page=site/'sources'/(sha256(module.encode()).hexdigest()[:24]+'.html')
        original=site/'originals'/relative
        if not page.is_file() or 'Cited dependency source' not in page.read_text() or not original.is_file() or digest(original.read_bytes())!=row.get('sha256'):
            errors.append({'module':module,'error':'cited dependency source does not match its record'})
    fonts=[str(p.relative_to(site)) for p in site.rglob('*') if p.suffix.lower() in {'.ttf','.otf','.woff','.woff2'}]
    if fonts:errors.append({'error':'font files included','paths':fonts})
    return {'schema':'leanglish.catalog-audit/v1','pages':len(parsed),'local_links_checked':links,
        'local_anchors_checked':anchors,'citation_links_checked':citations,'finding_page_denominator_reconciled':True,
        'statement_files_reconciled':True,'proof_reader_files_reconciled':True,
        'source_pages':summary['solution_source_modules']+dependencies,'cited_dependency_source_pages':dependencies,
        'font_files':len(fonts),'errors':errors,'passed':not errors}

def main(argv: list[str] | None = None, *, prog: str | None = None):
    p=argparse.ArgumentParser(prog=prog,description=__doc__);p.add_argument('site',type=Path);a=p.parse_args(argv)
    result=audit(a.site);print(json.dumps(result,indent=2));return 0 if result['passed'] else 2
if __name__=='__main__':raise SystemExit(main())
