#!/usr/bin/env python3
"""Exercise the fixed-cohort explorer in Chromium and retain the observations."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from proofreader.argument_explorer import validate_bundle
from proofreader.model import digest
from playwright.sync_api import sync_playwright


def audit(path: Path, output: Path, mode: str) -> dict:
    markup = path.read_text(encoding='utf-8')
    match = re.search(r'<script id="argument-data" type="application/json">(.*?)</script>', markup, re.S)
    if not match: raise ValueError('Explorer data not found')
    bundle = json.loads(match[1]); validate_bundle(bundle)
    report = {'schema': 'leanglish.argument-browser/v1', 'status': 'failed', 'navigation': mode,
              'html_sha256': digest(markup), 'proofs': 0, 'frames': 0, 'plans': 0,
              'errors': [], 'external_requests': [], 'human_evaluation': False}
    output.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            executable = shutil.which('chromium') or shutil.which('google-chrome')
            browser = p.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
            page = browser.new_page(viewport={'width': 1360, 'height': 900}, accept_downloads=True)
            page.on('pageerror', lambda e: report['errors'].append(str(e)))
            page.on('request', lambda r: report['external_requests'].append(r.url) if r.url.startswith(('http:', 'https:')) else None)
            if mode == 'file': page.goto(path.resolve().as_uri())
            else: page.set_content(markup)
            for item in bundle['items']:
                record, index = item['snapshot'], item['index']
                ids = {0, index['entry'], len(record['frames'])-1}
                facts = [b for b in index['bindings'] if b['proof'] is not None]
                if facts: ids.add(facts[0]['proof'])
                references = [n['frame'] for n in index['nodes'] if n['reference']]
                if references: ids.add(references[0])
                for i in sorted(ids):
                    page.evaluate('''([id,i])=>{const url=new URL(location.href);url.searchParams.set('proof',id);url.searchParams.set('frame',String(i));history.pushState(null,'',url);window.dispatchEvent(new PopStateEvent('popstate'));}''', [item['id'], i])
                    actual = page.evaluate('''()=>({theorem:document.querySelector('#theorem-name').textContent,
                        goal:document.querySelector('#goal').textContent,
                        binders:[...document.querySelectorAll('#context .context-row')].map(x=>Number(x.dataset.binder)),
                        types:[...document.querySelectorAll('#context .context-type')].map(x=>x.textContent),
                        children:[...document.querySelectorAll('#inputs button')].map(x=>Number(x.dataset.frame)),
                        claims:[...document.querySelectorAll('#inputs .input-claim')].map(x=>x.textContent),
                        frame:JSON.parse(document.querySelector('#source-frame').textContent)})''')
                    frame = record['frames'][i]
                    assert actual['theorem'] == record['theorem']
                    assert actual['goal'] == frame['statement']
                    assert actual['binders'] == index['nodes'][i]['scope']
                    assert actual['types'] == [c['type'] for c in frame['context']]
                    assert actual['children'] == frame['children']
                    assert actual['claims'] == [record['frames'][c]['statement'] for c in frame['children']]
                    assert actual['frame'] == frame
                    report['frames'] += 1
                plan = {'schema': 'leanglish.reading-plan/v1', 'snapshot_sha256': item['id'], 'frames': sorted(ids, reverse=True)}
                page.locator('#plan-box').evaluate('(x)=>x.open=true')
                page.locator('#plan-file').set_input_files({'name':'reading-order.json','mimeType':'application/json', 'buffer':json.dumps(plan).encode()})
                page.wait_for_function("document.querySelector('#plan-message').textContent==='Reading order loaded.'")
                assert page.locator('#plan .plan-name').all_text_contents() == ['Step '+str(i) for i in plan['frames']]
                report['plans'] += 1
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), record['theorem']
                page.set_viewport_size({'width':1360,'height':900})
                report['proofs'] += 1
            sample = next((item for item in bundle['items'] if item['snapshot']['theorem'].endswith('add_mem_finiteSquareSet')), bundle['items'][0])
            page.evaluate('''([id,i])=>{const u=new URL(location.href);u.searchParams.set('proof',id);u.searchParams.set('frame',i);history.pushState(null,'',u);dispatchEvent(new PopStateEvent('popstate'));}''', [sample['id'], sample['index']['entry']])
            page.screenshot(path=str(output/'desktop.png'), full_page=True)
            page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(output/'mobile.png'), full_page=True)
            assert not report['errors'] and not report['external_requests']
            browser.close(); report['status'] = 'passed'
    except Exception as exc:
        report['failure'] = str(exc)
    finally:
        (output/'browser.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    return report


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('html',type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--mode',choices=['file','memory'],default='file')
    args=p.parse_args();report=audit(args.html,args.output,args.mode);print(json.dumps(report,indent=2))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__': raise SystemExit(main())
