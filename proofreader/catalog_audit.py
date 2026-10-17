"""Audit a generated static catalog without executing its scripts."""
from __future__ import annotations
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

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
    expected={f['id']+'.html' for f in catalog}
    require(expected=={p.name for p in (site/'findings').glob('*.html')},'Finding page inventory mismatch')
    require(len(list((site/'evidence/statements').glob('*.json')))==summary['elaborated_statement_entries'],'Statement file inventory mismatch')
    require(len(list((site/'proofs').glob('*/reader.html')))==summary['proof_readings'],'Proof reader inventory mismatch')
    require(len(list((site/'sources').glob('*.html')))==summary['solution_source_modules'],'Source module inventory mismatch')
    fonts=[str(p.relative_to(site)) for p in site.rglob('*') if p.suffix.lower() in {'.ttf','.otf','.woff','.woff2'}]
    if fonts:errors.append({'error':'font files included','paths':fonts})
    return {'schema':'leanglish.catalog-audit/v1','pages':len(parsed),'local_links_checked':links,
        'local_anchors_checked':anchors,'finding_page_denominator_reconciled':True,
        'statement_files_reconciled':True,'proof_reader_files_reconciled':True,
        'font_files':len(fonts),'errors':errors,'passed':not errors}

def main(argv: list[str] | None = None, *, prog: str | None = None):
    p=argparse.ArgumentParser(prog=prog,description=__doc__);p.add_argument('site',type=Path);a=p.parse_args(argv)
    result=audit(a.site);print(json.dumps(result,indent=2));return 0 if result['passed'] else 2
if __name__=='__main__':raise SystemExit(main())
