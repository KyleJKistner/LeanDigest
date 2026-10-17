"""Exercise the real all-findings site in Chromium, with no external requests."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import re
import posixpath
from playwright.sync_api import sync_playwright


def audit(site: Path, screenshots: Path | None = None, *, document_harness: bool = False) -> dict:
    errors=[];external=[]
    with sync_playwright() as p:
        executable=shutil.which('chromium') or shutil.which('google-chrome')
        browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000})
        page.on('pageerror',lambda error: errors.append(str(error)))
        page.on('request',lambda r: external.append(r.url) if r.url.startswith(('https:','http:')) else None)
        current='index.html'
        def load(relative):
            nonlocal current
            current=relative
            path=site/relative
            if not document_harness:
                page.goto(path.resolve().as_uri())
                return
            text=path.read_text()
            styles=re.findall(r'<link[^>]*href="([^"]+\.css)"[^>]*>',text)
            scripts=re.findall(r'<script[^>]*src="([^"]+)"[^>]*></script>',text)
            apps=re.findall(r'<script>([\s\S]*?)</script>',text)
            text=re.sub(r'<script>[\s\S]*?</script>','',text)
            # Only the local test copy is inlined. Browser-admin navigation is
            # unavailable here; static link auditing and real-file CI are separate.
            text=re.sub(r'<script[^>]*src="[^"]+"[^>]*></script>','',text)
            text=re.sub(r'<link[^>]*href="[^"]+\.css"[^>]*>','',text)
            page.set_content(text)
            for name in styles: page.add_style_tag(content=(path.parent/name).read_text())
            for name in scripts: page.evaluate((path.parent/name).read_text())
            for app in apps: page.evaluate(app)
            page.evaluate("document.addEventListener('click', e => { const a=e.target.closest('a'); if(a) e.preventDefault(); })")
        def follow(locator):
            target=locator.get_attribute('href')
            locator.click()
            if document_harness: load(posixpath.normpath(posixpath.join(posixpath.dirname(current),target)))
        load('index.html')
        coverage=json.loads((site/'coverage.json').read_text())
        page.wait_for_function("document.getElementById('result-count').textContent.length > 0")
        assert page.locator('.card:visible').count()==coverage['documented_findings']
        page.locator('#coverage').select_option('all')
        assert page.locator('.card:visible').count()==coverage['findings']
        page.locator('#coverage').select_option('documented')
        page.locator('#search').fill('quasi-Riemann')
        assert page.locator('.card:visible').count()>=1
        follow(page.locator('.card:visible h2 a').first)
        assert '003' in (current if document_harness else page.url) and page.locator('.target').count()>=1
        assert 'Formalization scope' in page.locator('#scope').inner_text()
        assert page.locator('math').count()>0, 'Native MathML formulas did not render'
        if screenshots:
            screenshots.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(screenshots/'finding-desktop.png'))
        load('index.html')
        page.locator('#search').fill('leanglish-impossible-search-token')
        assert page.locator('#empty').is_visible()
        page.locator('#search').fill('')
        page.locator('#coverage').select_option('readings')
        assert page.locator('.card:visible').count()==coverage['findings_with_any_reading']
        follow(page.locator('.card:visible h2 a').first)
        follow(page.locator('a.button').first)
        assert page.locator('#theorem-title').inner_text()
        page.locator('#tab-source').click()
        assert 'import' in page.locator('#exact-source').inner_text()
        load('index.html')
        page.wait_for_function("document.getElementById('result-count').textContent.length > 0")
        if screenshots:page.screenshot(path=str(screenshots/'catalog-desktop.png'))
        page.set_viewport_size({'width':390,'height':844})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if screenshots:page.screenshot(path=str(screenshots/'catalog-mobile.png'))
        page.locator('#search').fill('quasi-Riemann')
        follow(page.locator('.card:visible h2 a').first)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        if screenshots:page.screenshot(path=str(screenshots/'finding-mobile.png'))
        if (site/'breadth.json').exists():
            load('index.html')
            follow(page.locator('a[href="progress.html"]').first)
            assert 'Proof-reading coverage' in page.locator('h1').inner_text()
            ledger=json.loads((site/'breadth.json').read_text())
            assert str(ledger['total_retained_readings'])+' of '+str(ledger['expected_theorem_targets']) in page.locator('#content').inner_text()
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('a[href="breadth.json"]').count()==1
        page.close();browser.close()
    assert not errors,errors
    assert not external,external
    return {'navigation_backend':'direct-document-test-harness' if document_harness else 'real-offline-file-navigation','browser':'Chromium','catalog_filtering':True,'search':True,'empty_result_recovery':True,
        'breadth_progress_navigation':(site/'breadth.json').exists(),'finding_navigation':True,'proof_reader_navigation':True,'exact_source_panel':True,
        'mathml_rendering':True,'mobile_overflow':False,'external_requests':external,'page_errors':errors,'passed':True}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('site',type=Path);parser.add_argument('--screenshots',type=Path);parser.add_argument('--document-harness',action='store_true')
    a=parser.parse_args();print(json.dumps(audit(a.site,a.screenshots,document_harness=a.document_harness),indent=2))
