"""Browser audit of original-project verification navigation and scope labels."""
from __future__ import annotations
import argparse,json,re,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright


def audit(site: Path, *, document_harness: bool = False) -> dict:
    record=json.loads((site/'original-verification.json').read_text())
    errors=[];external=[]
    with sync_playwright() as pw:
        executable=shutil.which('chromium') or shutil.which('google-chrome')
        browser=pw.chromium.launch(headless=True,executable_path=executable,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) else None)
        def load(name):
            path=site/name
            if not document_harness:
                page.goto(path.resolve().as_uri());return
            text=path.read_text()
            styles=re.findall(r'<link[^>]*href="([^"]+\.css)"[^>]*>',text)
            scripts=re.findall(r'<script[^>]*src="([^"]+)"[^>]*></script>',text)
            inline=re.findall(r'<script>([\s\S]*?)</script>',text)
            text=re.sub(r'<script>([\s\S]*?)</script>','',text)
            text=re.sub(r'<script[^>]*src="[^"]+"[^>]*></script>','',text)
            text=re.sub(r'<link[^>]*href="[^"]+\.css"[^>]*>','',text)
            page.set_content(text)
            for f in styles:page.add_style_tag(content=(path.parent/f).read_text())
            for f in scripts:page.evaluate((path.parent/f).read_text())
            for script in inline:page.evaluate(script)
        load('index.html')
        link=page.locator('a[href="original-verification.html"]').first
        assert link.count()==1
        if document_harness:load('original-verification.html')
        else:link.click()
        assert 'Original-project verification' in page.locator('h1').inner_text()
        assert page.locator('tbody tr').count()==record['build_summary']['expected_tasks']
        passed=page.locator('tbody tr').filter(has=page.locator('td:nth-child(2)',has_text=re.compile('^passed$'))).count()
        assert passed==record['build_summary']['library_passed']+record['build_summary']['comparator_passed']
        assert 'not formally verified English' in page.locator('#content').inner_text()
        assert page.locator('a[href="original-verification.json"]').count()==1
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Original task table overflows on mobile'
        page.screenshot(path=str(site.parent/'original-verification-mobile.png'))
        page.set_viewport_size({'width':1440,'height':1000})
        page.screenshot(path=str(site.parent/'original-verification-desktop.png'))
        fresh=next(r for r in record['theorems'] if r['reading_environment']=='full-original-dependency-audit')
        load('proofs/'+fresh['reading_id']+'/reader.html')
        assert page.locator('#qualified-name').inner_text()==fresh['name']
        page.locator('#tab-source').click()
        assert 'import' in page.locator('#exact-source').inner_text()
        browser.close()
    assert not errors,errors
    assert not external,external
    return {'passed':True,'navigation_backend':'direct-document-test-harness' if document_harness else 'real-offline-file-navigation',
        'original_task_rows':record['build_summary']['expected_tasks'],'outcome_count_checked':True,
        'fresh_reading_source_navigation':True,'mobile_overflow':False,'page_errors':errors,'external_requests':external}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('site',type=Path);p.add_argument('--document-harness',action='store_true')
    a=p.parse_args();print(json.dumps(audit(a.site,document_harness=a.document_harness),indent=2))
