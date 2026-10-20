"""Real-file browser acceptance for the exact canonical proof page.

These tests do not formally prove browser behavior. They separately compare the
DOM and downloaded bytes with the native certificate, without a network server.
"""
from __future__ import annotations
import importlib.util
import json
import os
import shutil
from pathlib import Path
import pytest

from proofreader.document_text import load_document

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('browser_checked_builder', ROOT / 'docs/companion/build_checked_proof.py')
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


@pytest.fixture(scope='module')
def built(tmp_path_factory):
    path = tmp_path_factory.mktemp('checked-proof') / 'checked-proof.html'
    BUILDER.build(path)
    return path


@pytest.fixture(scope='module')
def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        if os.environ.get('PROOFREADER_REQUIRE_BROWSER') == '1': pytest.fail('Playwright is required')
        pytest.skip('Playwright unavailable; not browser acceptance')
    with sync_playwright() as p:
        try:
            executable = shutil.which('chromium') or shutil.which('google-chrome')
            instance = p.chromium.launch(executable_path=executable, args=['--no-sandbox']) if executable else p.chromium.launch()
        except Exception as exc:
            if os.environ.get('PROOFREADER_REQUIRE_BROWSER') == '1': pytest.fail(str(exc))
            pytest.skip('Chromium unavailable; not browser acceptance')
        yield instance
        instance.close()


@pytest.fixture
def page(browser, built):
    context = browser.new_context(accept_downloads=True)
    tab = context.new_page()
    requests = []
    tab.on('request', lambda req: requests.append(req.url) if req.url.startswith(('http:', 'https:')) else None)
    tab.goto(built.as_uri())
    yield tab, requests
    context.close()


def test_real_dom_contains_exact_certified_text_and_no_network_requests(page):
    tab, requests = page
    assert tab.locator('#proof-text').text_content() == load_document()['text']
    assert tab.locator('.source-passage').count() == 14
    assert tab.locator('.structural-heading').all_text_contents() == ['Statement','Proof','Zero case','Nonzero case','Conclusion']
    assert requests == []


@pytest.mark.parametrize('kind,index', BUILDER.ORDER)
def test_every_passage_opens_its_actual_source_context_and_returns_focus(page, kind, index):
    tab, _ = page
    selected = tab.locator(f'.source-passage[data-kind="{kind}"][data-index="{index}"]')
    selected.focus(); selected.press('Enter')
    assert tab.locator('#source-dialog').is_visible()
    expected = load_document()['record'][kind][index]
    assert tab.locator('#selected-passage').inner_text() == expected['text']
    assert json.loads(tab.locator('#selected-record').text_content()) == expected
    tab.keyboard.press('Escape')
    assert not tab.locator('#source-dialog').is_visible()
    assert selected.evaluate('(el) => document.activeElement === el')


@pytest.mark.parametrize('width', [375, 600, 1280])
def test_layout_and_text_survive_viewport_changes(page, width):
    tab, _ = page
    tab.set_viewport_size({'width': width, 'height': 812})
    assert tab.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
    assert tab.locator('#proof-text').text_content() == load_document()['text']


@pytest.mark.parametrize('button,kind', [('download-proof','text'),('download-source','source'),('download-record','record')])
def test_downloads_match_native_text_original_source_and_record(page, button, kind, tmp_path):
    tab, _ = page
    with tab.expect_download() as event:
        tab.locator('#' + button).click()
    download = event.value
    output = tmp_path / download.suggested_filename
    download.save_as(output)
    data = load_document()
    if kind == 'text': assert output.read_bytes() == data['text'].encode('utf-8')
    elif kind == 'source':
        assert output.read_bytes() == (ROOT/'examples/openai/lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean').read_bytes()
    else:
        assert json.loads(output.read_text()) == {'record':data['record'], 'observation':data['observation']}


def test_composition_record_discloses_restored_proof_definitions(page):
    tab, _ = page
    tab.locator('#verification summary').click()
    record = json.loads(tab.locator('#composition-record').inner_text())
    assert record['closed_outer_binders'] == 2
    assert record['zero_context'][-1]['definition_restored'] is True
    assert record['nonzero_context'][-1]['name'] == 'hrel'
    assert record['nonzero_context'][-1]['definition_restored'] is True
