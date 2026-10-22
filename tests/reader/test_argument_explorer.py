"""Browser behavior of the argument explorer; never formal English evidence.

Default navigation uses actual file:// pages. Explicit memory mode exercises
DOM behavior where navigation is blocked; it is not offline-file acceptance.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
from urllib.parse import urlencode

import pytest

from proofreader.argument_explorer import html
from proofreader.argument_index import validate_plan

spec = importlib.util.spec_from_file_location('argument_fixture', Path(__file__).parents[1]/'test_argument_index.py')
fixtures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixtures)
pw = pytest.importorskip('playwright.sync_api')


@pytest.fixture(scope='module')
def browser():
    with pw.sync_playwright() as p:
        executable = shutil.which('chromium') or shutil.which('google-chrome')
        try:
            b = p.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
        except Exception as exc:
            if os.environ.get('PROOFREADER_REQUIRE_BROWSER') == '1': pytest.fail(str(exc))
            pytest.skip(str(exc))
        yield b
        b.close()


@pytest.fixture
def page(browser):
    p = browser.new_page(viewport={'width': 1320, 'height': 900}, accept_downloads=True)
    errors, remote = [], []
    p.on('pageerror', lambda e: errors.append(str(e)))
    p.on('request', lambda r: remote.append(r.url) if r.url.startswith(('http:', 'https:'))  else None)
    yield p
    assert not errors
    assert not remote
    p.close()


@pytest.fixture
def open_page(page, tmp_path):
    mode=os.environ.get('LEANGLISH_TEST_BROWSER_MODE','file')
    assert mode in {'file','memory'}
    def open_(bundle=None, params=None):
        path=tmp_path/'index.html'; markup=html(bundle or fixtures.bundle()); path.write_text(markup)
        query=('?' + urlencode(params) if params else '')
        if mode=='memory':
            page.evaluate('(url)=>history.replaceState(null,"",url)', 'about:blank'+query)
            page.set_content(markup)
        else:
            page.goto(path.as_uri()+query)
        return path
    return open_


def test_goal_and_context_match_source(page, open_page):
    open_page()
    assert page.locator('#goal').text_content() == 'P'
    assert page.locator('#context .context-row').count() == 2
    assert page.locator('#context .context-type').all_text_contents() == ['P','P']
    page.locator('#reference button').click()
    assert page.locator('#binding-title').text_content() == 'k'
    assert page.locator('#binding-uses button').count() == 1
    page.locator('#binding-uses button').click()
    assert not page.locator('#binding-dialog').is_visible()
    assert page.locator('#goal').text_content() == 'P'


def test_fact_proof_has_no_self_assumption(page, open_page):
    open_page(fixtures.bundle(fixtures.fact_fixture()))
    page.locator('#inputs button[data-frame="1"]').click()
    assert page.locator('#context .context-row').count() == 0
    page.locator('#parent-button').click()
    page.locator('#inputs button[data-frame="2"]').click()
    assert page.locator('#context .context-row').count() == 1
    page.locator('#reference button').click()
    assert page.locator('#binding-origin button').all_text_contents() == ['Introduction · step 0', 'Proof · step 1']


def test_ambiguity_visible_without_selecting_a_binder(page, open_page):
    open_page(fixtures.bundle(fixtures.fixture(duplicate_names=True)))
    assert 'does not distinguish' in page.locator('#reference').inner_text()
    assert page.locator('#reference button').count() == 2
    assert page.locator('#context .context-row').evaluate_all('(rows)=>rows.map(r=>r.dataset.binder)') == ['0','1']


def test_reading_order_and_download_keep_source_identity(page,open_page):
    b=fixtures.bundle(fixtures.branch_fixture());open_page(b)
    page.locator('#inputs button[data-frame="1"]').click();page.locator('#inputs button[data-frame="2"]').click()
    page.locator('#pin-button').click()
    page.locator('#statement-button').click();page.locator('#inputs button[data-frame="3"]').click();page.locator('#inputs button[data-frame="4"]').click()
    page.locator('#pin-button').click();page.get_by_role('button',name='Move step 4 earlier',exact=True).click()
    with page.expect_download() as info: page.locator('#download-plan').click()
    plan=json.loads(Path(info.value.path()).read_text())
    assert plan['frames']==[4,2]
    stops=validate_plan(b['items'][0]['snapshot'],plan)
    assert [s['scope'] for s in stops]==[[3],[1]]
    page.locator('#plan .plan-name').first.click()
    assert page.locator('#context .context-row').get_attribute('data-binder')=='3'
    page.locator('#plan .plan-name').last.click()
    assert page.locator('#context .context-row').get_attribute('data-binder')=='1'


def test_import_plan_rejects_changes_and_accepts_reference_only_order(page,open_page):
    b=fixtures.bundle();open_page(b);page.locator('#plan-box').evaluate('(x)=>x.open=true')
    good={'schema':'leanglish.reading-plan/v1','snapshot_sha256':b['items'][0]['id'],'frames':[2,0,1]}
    for bad in [{**good,'text':'False'}, {**good,'snapshot_sha256':'0'*64},{**good,'frames':[2,2]},{**good,'frames':[True]}]:
        page.locator('#plan-file').set_input_files({'name':'plan.json','mimeType':'application/json','buffer':json.dumps(bad).encode()})
        page.wait_for_function("document.getElementById('plan-message').textContent.length>0")
        assert page.locator('#plan li').count()==0
        assert page.locator('#plan-message').text_content()!='Reading order loaded.'
        page.locator('#plan-message').evaluate('(x)=>x.textContent=""')
    page.locator('#plan-file').set_input_files({'name':'plan.json','mimeType':'application/json','buffer':json.dumps(good).encode()})
    page.wait_for_function("document.getElementById('plan-message').textContent==='Reading order loaded.'")
    assert page.locator('#plan .plan-name').all_text_contents()==['Step 2','Step 0','Step 1']


def test_deep_links_and_history(page,open_page):
    b=fixtures.bundle();open_page(b,{'proof':b['items'][0]['id'],'frame':1})
    assert page.locator('#frame-label').text_content()=='Step 1'
    page.locator('#statement-button').click();assert page.locator('#frame-label').text_content()=='Step 0'
    page.go_back();assert page.locator('#frame-label').text_content()=='Step 1'
    page.go_forward();assert page.locator('#frame-label').text_content()=='Step 0'


def test_search_and_mobile_layout(page,open_page):
    page.set_viewport_size({'width':390,'height':844});open_page()
    assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
    page.locator('#search').fill('absent');assert page.locator('#empty').is_visible()
    page.locator('#search').fill('nested');assert page.locator('#reader').is_visible()


def test_payload_is_displayed_without_script_execution(page,open_page):
    r=fixtures.fixture();r['theorem']='</script><script>window.attacked=true</script>'
    open_page(fixtures.bundle(r))
    assert page.locator('#theorem-name').text_content()==r['theorem']
    assert page.evaluate('typeof window.attacked')=='undefined'


def test_snapshot_download_preserves_data(page,open_page):
    b=fixtures.bundle();open_page(b)
    page.locator('#download-snapshot').evaluate('(x)=>x.closest("details").open=true')
    with page.expect_download() as info:page.locator('#download-snapshot').click()
    assert json.loads(Path(info.value.path()).read_text())==b['items'][0]['snapshot']
