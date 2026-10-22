#!/usr/bin/env python3
"""Check rendered statements, interaction, and exact integer examples in Chromium.

Memory mode is DOM validation, not acceptance of local-file navigation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def check(html: Path, output: Path, mode: str) -> dict:
    output.mkdir(parents=True,exist_ok=True)
    text=html.read_text();report={'status':'failed','mode':mode,'html_sha256':hashlib.sha256(text.encode()).hexdigest(),'page_errors':[],'external_requests':[],'human_evaluation':False}
    try:
        with sync_playwright() as p:
            import shutil
            executable=shutil.which('chromium') or shutil.which('google-chrome')
            b=p.chromium.launch(headless=True,executable_path=executable,args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
            q=b.new_page(viewport={'width':1280,'height':1000},accept_downloads=True)
            q.on('pageerror',lambda e:report['page_errors'].append(str(e)))
            q.on('request',lambda r:report['external_requests'].append(r.url) if r.url.startswith(('http:','https:')) else None)
            if mode=='file':q.goto(html.resolve().as_uri())
            else:q.set_content(text)
            for id in ('bezout','reverse','cantor'):
                q.locator(f'[data-open="{id}"]').click()
                assert q.locator(f'article#{id}').is_visible()
                assert q.locator('article:visible').count()==1
                q.locator(f'#{id} .comparison').evaluate('(x)=>x.open=true')
                for tab in q.locator(f'#{id} [data-code]').all():
                    tab.click();assert q.locator(f'#{id} .code-pane:visible').count()==1
                    button=q.locator(f'#{id} .code-pane:visible [data-download]')
                    key=button.get_attribute('data-download')
                    with q.expect_download() as d:button.click()
                    source=Path(d.value.path()).read_text()
                    expected=q.evaluate('(id)=>JSON.parse(document.querySelector("#reader-data").textContent).sources[id]',key)
                    assert source==expected
                q.locator(f'#{id} .comparison').evaluate('(x)=>x.open=false')
                q.screenshot(path=str(output/(id+'-desktop.png')),full_page=True)
                q.locator(f'#{id} details.note').evaluate_all('(xs)=>xs.forEach(x=>x.open=true)')
                q.screenshot(path=str(output/(id+'-expanded-desktop.png')),full_page=True)
                q.set_viewport_size({'width':390,'height':844})
                assert q.evaluate('document.documentElement.scrollWidth<=innerWidth')
                q.screenshot(path=str(output/(id+'-mobile.png')),full_page=True)
                q.set_viewport_size({'width':1280,'height':1000})
                q.locator(f'#{id} details.note').evaluate_all('(xs)=>xs.forEach(x=>x.open=false)')
            report['articles_checked']=3
            # Verify examples independently with Python integer multiplication.
            triples=[(x,y,z) for x in range(-8,9) for y in range(-8,9) for z in range(-8,9) if x*y==z*(z+1)]
            q.locator('[data-open="bezout"]').click()
            records=q.evaluate('''(rows)=>rows.map(([x,y,z])=>{document.querySelector('#bx').value=x;document.querySelector('#by').value=y;document.querySelector('#bz').value=z;document.querySelector('#bezout-run').click();return {...document.querySelector('#bezout-output').dataset};})''',triples)
            for (x,y,z),r in zip(triples,records):
                assert r['valid']=='true';a,d,bb,c=map(int,r['tuple'].split(','))
                assert (a*bb,d*c,d*bb,a*c-d*bb)==(x,y,z,1)
            report['integer_examples_checked']=len(triples)
            for x,y,z in [('2','2','1'),('1.5','2','1'),('<script>','2','1'),('9'*13,'2','1')]:
                for key,v in [('bx',x),('by',y),('bz',z)]:q.locator('#'+key).fill(v)
                q.locator('#bezout-run').click();assert q.locator('#bezout-output').get_attribute('data-valid')=='false'
            report['invalid_example_inputs_rejected']=4
            q.locator('[data-open="reverse"]').click()
            count=0
            for n in (3,4,5,6):
                q.locator('#reverse-length').select_option(str(n))
                for i in range(n):
                    q.locator('#reverse-position').fill(str(i));q.locator('#reverse-position').dispatch_event('input')
                    assert q.locator('#reverse-output').get_attribute('data-returned')==str(i)
                    count+=1
            report['position_examples_checked']=count
            q.locator('[data-open="cantor"]').click()
            for mask in range(16):
                for i in range(4):
                    button=q.locator(f'[data-row="{i}"][data-col="{i}"]')
                    if button.text_content()!=str((mask>>i)&1):button.click()
                assert q.locator('#diagonal-output').get_attribute('data-bits')==''.join(str(1-((mask>>i)&1)) for i in range(4))
            before=q.locator('#diagonal-output').get_attribute('data-bits')
            for i in range(4):
                for j in range(4):
                    if i!=j:
                        q.locator(f'[data-row="{i}"][data-col="{j}"]').click()
                        assert q.locator('#diagonal-output').get_attribute('data-bits')==before
            report['diagonal_patterns_checked']=16;report['off_diagonal_edits_checked']=12
            assert not report['page_errors'] and not report['external_requests']
            b.close();report['status']='passed'
    except Exception as e:report['error']=str(e)
    (output/'browser.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('html',type=Path);p.add_argument('--output',required=True,type=Path);p.add_argument('--mode',choices=['file','memory'],default='file');a=p.parse_args();r=check(a.html,a.output,a.mode);print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='passed' else 1)
