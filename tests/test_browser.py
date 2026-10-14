"""Real Chromium interaction tests. Skip only when Playwright/browser is absent."""
from pathlib import Path
import json
import os
import shutil
import pytest
from proofreader.source import parse_source
from proofreader.render import html_document,load_document

pw=pytest.importorskip('playwright.sync_api')

@pytest.fixture(scope='module')
def browser():
    executable=shutil.which('chromium') or shutil.which('google-chrome')
    with pw.sync_playwright() as p:
        try:
            browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
        except Exception as exc:
            if os.environ.get('PROOFREADER_REQUIRE_BROWSER') == '1': pytest.fail(f'Browser CI requires Chromium: {exc}')
            pytest.skip(f'Browser unavailable: {exc}')
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    page=browser.new_page(viewport={'width':1360,'height':960})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    yield page
    assert not errors,errors
    page.close()


def test_search_navigation_source_and_inspector(page):
    d=parse_source('theorem first : True := by\n  have h : True := by trivial\n  exact h\ntheorem second : True := by trivial\n')
    page.set_content(html_document(d))
    assert page.locator('#theorem-title').inner_text()=='first'
    page.locator('#expand-btn').click()
    assert page.locator('#proof-steps details[open]').count()>0
    page.locator('.step-inspect').first.click()
    assert page.locator('#inspector').is_visible()
    assert 'have h' in page.locator('#inspector-source').inner_text()
    page.locator('#inspector-close').click()
    page.locator('#search').fill('second')
    assert page.locator('#declaration-list button').count()==1
    assert page.locator('#theorem-title').inner_text()=='second'
    page.locator('#tab-source').click()
    assert 'theorem second' in page.locator('#exact-source').inner_text()
    page.locator('#tab-audit').click()
    assert 'Not certified' in page.locator('#audit').inner_text()


def test_xss_source_and_title_remain_text(page):
    attack='</script><script>globalThis.PWNED=1</script>'
    d=parse_source('/- '+attack+' -/\ntheorem t : True := by trivial')
    d.title=attack+'__DOCUMENT_DATA__'
    page.set_content(html_document(d))
    assert page.evaluate('globalThis.PWNED') is None
    assert page.locator('#library-title').inner_text()==d.title
    assert len(page.query_selector_all('script'))==2


def test_empty_filter_recovery_and_coverage(page):
    d=parse_source('theorem t : True := by secret_solver')
    page.set_content(html_document(d))
    page.locator('[data-filter="typed"]').click()
    assert page.locator('#empty').is_visible()
    page.locator('[data-filter="all"]').click()
    assert page.locator('#reader').is_visible()
    page.locator('#coverage-btn').click()
    assert page.locator('#coverage-dialog').is_visible()
    assert page.locator('.metric strong').last.inner_text()=='0'


def test_mobile_has_no_horizontal_overflow(page):
    page.set_viewport_size({'width':390,'height':844})
    d=parse_source('theorem ordinary : True := by\n  trivial\n')
    page.set_content(html_document(d))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def test_real_openai_demo_all_nine_declarations(page):
    from proofreader.corpus import local_manifest
    from proofreader.source import merge_documents
    root=Path(__file__).resolve().parents[1]/'examples/openai'
    d=merge_documents([parse_source((root/e['path']).read_text(),e['path']) for e in local_manifest(root)['files']])
    page.set_content(html_document(d))
    assert page.locator('#declaration-list button').count()==9
    for name in ['symmetric_mahler','exists_growth_constant','nonpolynomiality','logarithmic_independence_bound']:
        page.locator('#search').fill(name)
        assert page.locator('#declaration-list button').count()==1
        assert page.locator('#reader').is_visible()
        page.locator('#expand-btn').click()
        page.locator('#collapse-btn').click()


def typed_demo():
    return load_document((Path(__file__).parents[1]/'proofreader/data/kernel-demo.json').read_bytes())

def test_typed_parameters_are_assumptions_not_objects(page):
    page.set_content(html_document(typed_demo()))
    assert page.locator('#theorem-title').inner_text()=='injective comp'
    p=page.locator('#parameters').inner_text()
    assert 'Assume f is injective' in p and 'Assume g is injective' in p
    assert 'Let X be a type' in p
    assert '(x = y)' in page.locator('#proof-steps').inner_text()
    assert page.locator('.support-link').count()>=1
    page.locator('.support-link').last.click()
    assert page.locator('#inspector').is_visible()
    assert 'Original proof path:' in page.locator('#inspector-detail').inner_text()

def test_typed_receipt_scope_is_visible(page):
    page.set_content(html_document(typed_demo()))
    page.locator('#search').fill('PRSmoke.and_swap')
    page.locator('#tab-audit').click()
    audit=page.locator('#audit').inner_text()
    assert 'independently replayed original proof paths' in audit
    assert 'Not authenticated' in audit and 'Not certified' in audit
    assert '4.34.0' in audit and 'None reported by Lean' in audit

def test_typed_filter_separates_source_from_export(page):
    page.set_content(html_document(typed_demo()))
    page.locator('[data-filter="typed"]').click()
    assert page.locator('#declaration-list button').count()==5
    page.locator('[data-filter="all"]').click()
    assert page.locator('#declaration-list button').count()==14

def test_typed_mobile_no_horizontal_overflow(page):
    page.set_viewport_size({'width':390,'height':844})
    page.set_content(html_document(typed_demo()))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#tab-audit').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def narrative_demo():
    return load_document((Path(__file__).parents[1]/'proofreader/data/narrative-demo.json').read_bytes())


def test_substantial_narrative_cases_visible(page):
    page.set_content(html_document(narrative_demo()))
    assert page.locator('#evidence-badge').text_content()=='Source-bound snapshot'
    assert 'pretty-printer' in page.locator('#trust-banner').inner_text()
    assert 'Euclidean domain' in page.locator('#parameters').inner_text()
    assert page.get_by_text('Case g = 0.',exact=True).is_visible()
    assert page.get_by_text('Case g ≠ 0.',exact=True).is_visible()
    assert page.get_by_text('Take (a, d, b, c) = (1, y, 0, 1).',exact=True).is_visible()
    assert 'y' in page.locator('#statement').inner_text()


def test_substantial_narrative_polynomial_inspector(page):
    page.set_content(html_document(narrative_demo()))
    page.locator('#expand-btn').click()
    step=page.locator('[data-step-id="n'+narrative_demo().provenance['snapshot_sha256'][:16]+':47"]')
    step.locator('.step-inspect').first.click()
    assert 'integer-polynomial certificate' in page.locator('#inspector-detail').inner_text()
    assert 'Original proof paths: f47=' in page.locator('#inspector-detail').inner_text()
    assert 'ha' in page.locator('#inspector-context').inner_text()


def test_substantial_receipt_scope_and_proof_source(page):
    d=narrative_demo();page.set_content(html_document(d))
    page.locator('#tab-audit').click()
    audit=page.locator('#audit').inner_text()
    assert '86 selected original proof subterms' in audit
    assert '4.34.1' in audit and '16 exact integer-polynomial' in audit
    assert 'Not authenticated' in audit and 'Not certified' in audit
    page.locator('#tab-source').click()
    assert 'theorem exists_frame' in page.locator('#exact-source').inner_text()
    assert 'gcd_eq_gcd_ab' in page.locator('#exact-source').inner_text()


def test_mixed_library_narrative_filter_and_search(page):
    d=load_document((Path(__file__).parents[1]/'proofreader/data/reader-demo.json').read_bytes())
    page.set_content(html_document(d))
    page.locator('[data-filter="typed"]').click()
    assert page.locator('#declaration-list button').count()==6
    page.locator('#search').fill('BezoutFrame')
    assert page.locator('#declaration-list button').count()==1
    page.locator('#coverage-btn').click()
    assert '1 source-bound snapshots' in page.locator('#coverage-summary').inner_text()
    assert page.locator('.metric strong').last.inner_text()=='0'


def test_substantial_mobile_expansion_and_audit_no_overflow(page):
    page.set_viewport_size({'width':390,'height':844})
    page.set_content(html_document(narrative_demo()))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#expand-btn').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#tab-audit').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
