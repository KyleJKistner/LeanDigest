"""Citation links between readings and source lines.

Every snapshot, source module and observation here is a synthetic consistency
fixture: no Lean runs and nothing is a native observation. The browser tests
use real Chromium on generated pages.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil

import pytest

from proofreader.catalog_audit import audit
from proofreader.catalog_inputs import PIN
from proofreader.declaration_index import build_index, citation_links, reading_map, summarize, validate_links
from proofreader.finding_catalog import build, source_name
from proofreader.model import digest
from proofreader.narrative import Narrative, Snapshot, check_reading
from proofreader.narrative_io import write_bundle
from proofreader.render import html_document, load_document

ALPHA, BETA, GAMMA = 'OAI.Algebra.Alpha.Main', 'OAI.Algebra.Beta.Main', 'OAI.Algebra.Gamma.Main'
SOURCES = {
    ALPHA: 'import OAI.Algebra.Beta.Main\n\nnamespace OAI.Alpha\n\ntheorem helper : True := trivial\n\n'
           'theorem main : True := trivial\n\nend OAI.Alpha\n',
    BETA: 'import Mathlib\n\nnamespace OAI.Beta\n\ntheorem target : True := trivial\n\nend OAI.Beta\n',
    GAMMA: 'namespace OAI.Gamma\n\ntheorem hidden : True := trivial\n\ntheorem top : True := trivial\n\nend OAI.Gamma\n',
}
THEOREMS = {ALPHA: 'OAI.Alpha.main', BETA: 'OAI.Beta.target', GAMMA: 'OAI.Gamma.top'}
CITED = ['OAI.Alpha.helper', 'OAI.Gamma.hidden', 'Nat.succ_le', 'OAI.Alpha.main._proof_1_1']


def ident(module):
    return sha256((module + '\0' + THEOREMS[module]).encode()).hexdigest()[:24]


def record(theorem, root, heads=()):
    def frame(i, path, head, children):
        return {'id': i, 'path': path, 'statement': 'True', 'role': 'application' if children else 'named',
                'head': head, 'context': [], 'children': children, 'premises': [], 'objects': [], 'budget_cut': False}
    frames = [frame(0, [], root, list(range(1, len(heads)+1)))]
    frames += [frame(i+1, [0]*i+[1], h, []) for i, h in enumerate(heads)]
    return {'schema': 'proofreader.narrative/v1', 'theorem': theorem, 'lean_version': '4.34.1', 'axioms': [],
            'statement': 'True', 'judgements_checked': len(frames), 'formula_backend': 'Lean pretty-printer',
            'frames': frames}


ALPHA_RECORD = record(THEOREMS[ALPHA], 'OAI.Beta.target', CITED)
BETA_RECORD = record(THEOREMS[BETA], 'Nat.le_refl')
FILE = 'lean/' + ALPHA.replace('.', '/') + '.lean'


def alpha_links(document, sources=SOURCES, readings=None):
    readings = readings if readings is not None else {(ALPHA, THEOREMS[ALPHA]): ident(ALPHA), (BETA, THEOREMS[BETA]): ident(BETA)}
    return citation_links(document, ALPHA, build_index(sources), reading_map(readings), source_name)


def alpha_document():
    return Narrative(ALPHA_RECORD).document(source=SOURCES[ALPHA], file=FILE)


def test_each_citation_resolves_to_a_reading_a_source_line_or_a_stated_reason():
    links = validate_links(alpha_links(alpha_document()))
    names = links['names']
    assert names['OAI.Beta.target'] == {
        'status': 'reading', 'href': f'../{ident(BETA)}/reader.html', 'module': BETA,
        'basis': 'imported-bundled-module',
        'source': {'href': f'../../sources/{source_name(BETA)}#L5', 'module': BETA, 'line': 5,
                   'basis': 'imported-bundled-module'}}
    assert names['OAI.Alpha.helper'] == {'status': 'source', 'href': f'../../sources/{source_name(ALPHA)}#L5',
                                         'module': ALPHA, 'line': 5, 'basis': 'same-module'}
    # Declared in a bundled module the citing module does not visibly import: not guessed.
    assert names['OAI.Gamma.hidden'] == {'status': 'unresolved', 'reason': 'not-visibly-imported'}
    assert names['Nat.succ_le'] == {'status': 'unresolved', 'reason': 'not-in-declaration-index'}
    assert names['OAI.Alpha.main._proof_1_1'] == {'status': 'unresolved', 'reason': 'compiler-generated-auxiliary'}
    assert set(names) == set(alpha_document().declarations[0].dependencies)
    assert links['counts'] == {'reading': 1, 'source': 1, 'unresolved': 3}


def test_a_reading_in_an_unimported_module_is_not_assumed_to_be_the_same_constant():
    sources = {**SOURCES, ALPHA: SOURCES[ALPHA].replace('import OAI.Algebra.Beta.Main\n', '')}
    names = alpha_links(alpha_document(), sources)['names']
    assert names['OAI.Beta.target'] == {'status': 'unresolved', 'reason': 'not-visibly-imported'}


def test_duplicate_declarations_are_ambiguous_even_when_visible():
    delta = 'OAI.Algebra.Delta.Main'
    sources = {**SOURCES, delta: 'namespace OAI.Alpha\ntheorem helper : True := trivial\nend OAI.Alpha\n',
               ALPHA: 'import ' + delta + '\n' + SOURCES[ALPHA]}
    names = alpha_links(alpha_document(), sources)['names']
    assert names['OAI.Alpha.helper'] == {'status': 'unresolved', 'reason': 'ambiguous-in-bundled-source'}


def test_a_duplicate_the_citing_module_cannot_see_does_not_block_the_visible_declaration():
    # Lean forbids two declarations of one name in one environment, so the only visible one is the constant.
    delta = 'OAI.Algebra.Delta.Main'
    sources = {**SOURCES, delta: 'namespace OAI.Beta\ntheorem target : True := trivial\nend OAI.Beta\n'}
    names = alpha_links(alpha_document(), sources, readings={})['names']
    assert names['OAI.Beta.target'] == {'status': 'source', 'href': f'../../sources/{source_name(BETA)}#L5',
                                        'module': BETA, 'line': 5, 'basis': 'imported-bundled-module'}
    both = {**sources, ALPHA: 'import ' + delta + '\n' + SOURCES[ALPHA]}
    assert alpha_links(alpha_document(), both, readings={})['names']['OAI.Beta.target'] == {
        'status': 'unresolved', 'reason': 'ambiguous-in-bundled-source'}


def test_a_reading_link_basis_names_the_reading_module_and_its_source_line_the_declaring_module():
    """A reading of an imported constant, kept under the citing module, as in five readings of the full build."""
    readings = {(ALPHA, THEOREMS[ALPHA]): ident(ALPHA), (ALPHA, 'OAI.Beta.target'): ident(BETA)}
    entry = alpha_links(alpha_document(), readings=readings)['names']['OAI.Beta.target']
    assert entry == {'status': 'reading', 'href': f'../{ident(BETA)}/reader.html', 'module': ALPHA, 'basis': 'same-module',
                     'source': {'href': f'../../sources/{source_name(BETA)}#L5', 'module': BETA, 'line': 5,
                                'basis': 'imported-bundled-module'}}
    # Without that reading the same citation links to the declaration line, with the same declaring-module basis.
    plain = alpha_links(alpha_document(), readings={(ALPHA, THEOREMS[ALPHA]): ident(ALPHA)})['names']['OAI.Beta.target']
    assert plain == {'status': 'source', **entry['source']}


def test_a_reading_never_links_to_itself():
    self_citing = record(THEOREMS[ALPHA], 'OAI.Alpha.main', ['OAI.Alpha.helper'])
    document = Narrative(self_citing).document(source=SOURCES[ALPHA], file=FILE)
    entry = alpha_links(document)['names']['OAI.Alpha.main']
    assert entry['status'] == 'source' and entry['line'] == 7
    # Without an indexed source line the reason names the self-citation, not a missing import.
    unindexed = {**SOURCES, ALPHA: SOURCES[ALPHA].replace('theorem main', 'theorem «main»')}
    assert alpha_links(document, unindexed)['names']['OAI.Alpha.main'] == {'status': 'unresolved', 'reason': 'this-reading'}


def test_unresolved_reasons_prefer_what_the_bundle_shows_over_name_shape():
    # A bundled but unreachable declaration whose name looks like an auxiliary is not called generated.
    sources = {**SOURCES, GAMMA: SOURCES[GAMMA].replace('theorem hidden', 'theorem hidden.proof_1')}
    cited = record(THEOREMS[ALPHA], 'OAI.Gamma.hidden.proof_1', ['OAI.Other.proof_2'])
    names = alpha_links(Narrative(cited).document(source=SOURCES[ALPHA], file=FILE), sources)['names']
    assert names['OAI.Gamma.hidden.proof_1'] == {'status': 'unresolved', 'reason': 'not-visibly-imported'}
    assert names['OAI.Other.proof_2'] == {'status': 'unresolved', 'reason': 'compiler-generated-auxiliary'}
    # A reading of the name in an unreachable module is reported the same way, without a source entry.
    readings = {(ALPHA, THEOREMS[ALPHA]): ident(ALPHA), (GAMMA, 'OAI.Other.proof_2'): ident(GAMMA)}
    names = alpha_links(Narrative(cited).document(source=SOURCES[ALPHA], file=FILE), sources, readings)['names']
    assert names['OAI.Other.proof_2'] == {'status': 'unresolved', 'reason': 'not-visibly-imported'}


@pytest.mark.parametrize('entry', [
    {'status': 'reading', 'href': 'javascript:alert(1)'},
    {'status': 'reading', 'href': 'https://example.org/reader.html'},
    {'status': 'source', 'href': '/etc/passwd'},
    {'status': 'source', 'href': '../../../outside.html#L1'},
    {'status': 'reading', 'href': '../abc/reader.html'},
    {'status': 'reading', 'href': '../' + 'a' * 24 + '/reader.html?x=1'},
    {'status': 'source', 'href': '../../sources/' + 'a' * 24 + '.html#L0'},
    {'status': 'reading', 'href': '../' + 'a' * 24 + '/reader.html', 'source': {'href': 'data:text/html,x'}},
    {'status': 'unresolved', 'reason': 'x', 'href': '../' + 'a' * 24 + '/reader.html'},
    {'status': 'reading'},
    {'status': 'linked', 'href': '../' + 'a' * 24 + '/reader.html'},
    {'status': 'reading', 'href': '../' + 'a' * 24 + '/reader.html', 'source': '../../sources/x.html#L1'},
    {'status': 'unresolved'},
    {'status': 'unresolved', 'reason': 'looks-fine'},
])
def test_unsafe_or_malformed_links_are_rejected(entry):
    with pytest.raises(ValueError):
        validate_links({'schema': 'leanglish.citation-links/v1', 'names': {'X.y': entry}})
    with pytest.raises(ValueError):
        html_document(alpha_document(), links={'schema': 'leanglish.citation-links/v1', 'names': {'X.y': entry}})


def test_links_stay_outside_the_checked_reading(tmp_path):
    made = []
    def links(document):
        made.append(alpha_links(document)); return made[-1]
    with_links = write_bundle(ALPHA_RECORD, tmp_path / 'with', source=SOURCES[ALPHA], file=FILE, links=links)
    without = write_bundle(ALPHA_RECORD, tmp_path / 'without', source=SOURCES[ALPHA], file=FILE)
    assert with_links == without and len(made) == 1
    for name in ('reading.json', 'snapshot.json', 'proof.txt', 'coverage.json', 'polynomial-certificates.json'):
        assert (tmp_path / 'with' / name).read_bytes() == (tmp_path / 'without' / name).read_bytes()
    assert json.loads((tmp_path / 'with/links.json').read_text()) == made[0]
    assert not (tmp_path / 'without/links.json').exists()
    document = load_document((tmp_path / 'with/reading.json').read_bytes())
    check_reading(ALPHA_RECORD, document)
    page = (tmp_path / 'with/reader.html').read_text()
    island = re.search(r'<script id="proofreader-links" type="application/json">.*?</script>', page, re.S)[0]
    assert page.replace(island, '') == (tmp_path / 'without/reader.html').read_text() == html_document(document)
    assert page == html_document(document, links=made[0])
    # Rewriting without links removes a stale links file.
    write_bundle(ALPHA_RECORD, tmp_path / 'with', source=SOURCES[ALPHA], file=FILE)
    assert not (tmp_path / 'with/links.json').exists()


def test_link_island_cannot_terminate_its_script():
    attack = '</script><script>globalThis.PWNED=1</script>'
    links = {'schema': 'leanglish.citation-links/v1',
             'names': {attack: {'status': 'unresolved', 'reason': 'not-in-declaration-index', 'note': attack}}}
    page = html_document(alpha_document(), links=links)
    assert attack not in page and page.count('<script') == 3
    island = re.search(r'<script id="proofreader-links" type="application/json">(.*?)</script>', page, re.S)[1]
    assert json.loads(island) == links
    assert '<script id="proofreader-links"' not in html_document(alpha_document())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value))


@pytest.fixture
def catalog(tmp_path):
    return make_catalog(tmp_path)


def make_catalog(tmp_path):
    """Three synthetic configurations; Alpha and Beta have synthetic consistency-check readings."""
    upstream = tmp_path / 'upstream'; lean = upstream / 'lean'; proofs = tmp_path / 'proofs'; proofs.mkdir()
    statements = tmp_path / 'statements'; statements.mkdir()
    write(upstream / 'CONTENTS.md', '**001. Linked results.** Synthetic.\n')
    write(upstream / 'LICENSE', 'Example public license')
    configs = {'Alpha': ALPHA, 'Beta': BETA, 'Gamma': GAMMA}
    write(lean / 'docs/001.md', '# Linked results\n\n' + ''.join(f'[{k}](../ComparatorChallenges/{k}.lean)\n' for k in configs))
    for key, module in configs.items():
        write(lean / f'ComparatorChallenges/{key}.json', {'challenge_module': 'ComparatorChallenges.' + key,
              'solution_module': module, 'theorem_names': [THEOREMS[module]]})
        write(lean / f'ComparatorChallenges/{key}.lean', '-- comparison specification\n')
        write(lean / (module.replace('.', '/') + '.lean'), SOURCES[module])
    rows = []
    for module, rec in [(ALPHA, ALPHA_RECORD), (BETA, BETA_RECORD)]:
        directory = proofs / 'targets' / ident(module)
        snapshot = Snapshot(rec); driver = '-- synthetic consistency fixture, not executed\n'
        stdout = 'PR_NARRATIVE:' + json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(',', ':')) + '\n'
        write(directory / 'Extract.lean', driver); write(directory / 'snapshot.json', rec); write(directory / 'stdout.txt', stdout)
        write(directory / 'receipt.json', {'status': 'passed', 'schema': 'proofreader.narrative-receipt/v1',
              'theorem': rec['theorem'], 'module': module, 'lean_version': '4.34.1',
              'selected_judgements': rec['judgements_checked'], 'backend': 'native',
              'all_selected_judgements_kernel_checked': True, 'path_linkage_checked_in_lean': True,
              'snapshot_sha256': snapshot.sha256, 'source_sha256': digest(driver.encode())})
        write(directory / 'run.json', {'status': 'passed', 'exit_code': 0, 'stdout': stdout})
        rows.append({'id': ident(module), 'module': module, 'name': rec['theorem'], 'kind': 'theorem',
                     'status': 'reading-generated', 'directory': 'targets/' + ident(module), 'kernel_checked': True,
                     'snapshot_sha256': snapshot.sha256, 'selected_judgements': rec['judgements_checked'],
                     'source_sha256': digest(SOURCES[module].encode())})
    write(proofs / 'proofs.json', {'schema': 'leanglish.finding-proof-shard/v1', 'upstream_commit': PIN,
                                   'expected_targets': len(rows), 'targets': rows})
    entries = [{'path': p.relative_to(upstream).as_posix(), 'sha256': digest(p.read_bytes())}
               for p in upstream.rglob('*') if p.is_file()]
    write(upstream / 'acquisition.json', {'repository': 'openai/math', 'commit': PIN, 'fetched': entries})
    inventory = tmp_path / 'source-inventory.json'
    write(inventory, [x for x in entries if x['path'].startswith('lean/')])
    site = tmp_path / 'site'
    summary = build(upstream, lean, [statements], [proofs], site, source_inventory=inventory)
    return site, summary


def test_catalog_links_readings_and_source_lines_and_passes_audit(catalog):
    site, summary = catalog
    assert not summary['rendering_failures'] and summary['proof_readings'] == 2
    cl = summary['citation_links']
    assert cl['readings'] == 2 and cl['readings_linking_another_reading'] == 1
    assert cl['names'] == {'cited': 6, 'linked_to_reading': 1, 'linked_to_source': 1, 'unresolved': 4}
    assert cl['project_names'] == {'cited': 4, 'linked_to_reading': 1, 'linked_to_source': 1, 'unresolved': 2}
    assert cl['citations']['unresolved_by_reason'] == {'compiler-generated-auxiliary': 1,
        'not-in-declaration-index': 2, 'not-visibly-imported': 1}
    assert cl['links_in_checked_reading'] is False and cl['citations_checked'] is False
    assert json.loads((site / 'coverage.json').read_text())['citation_links'] == cl
    index = json.loads((site / 'evidence/declaration-index.json').read_text())
    assert index['names']['OAI.Gamma.hidden'] == {'module': GAMMA, 'line': 3, 'kind': 'theorem'}
    links = json.loads((site / 'proofs' / ident(ALPHA) / 'links.json').read_text())
    assert links['names']['OAI.Beta.target']['href'] == f'../{ident(BETA)}/reader.html'
    result = audit(site)
    assert result['passed'], result['errors']
    assert result['citation_links_checked'] == 3
    assert 'Cited project names (OAI.*) in the readings' in (site / 'coverage.html').read_text()
    # The target line really is the declaration on the bundled source page.
    page = (site / 'sources' / source_name(ALPHA)).read_text()
    assert re.search(r'id="L5"><a href="#L5">5</a> theorem helper', page)


def test_a_reading_that_fails_to_render_is_never_a_link_target(tmp_path, monkeypatch):
    import proofreader.finding_catalog as finding_catalog
    original = finding_catalog.write_bundle
    def failing(record, *args, **kwargs):
        if record['theorem'] == THEOREMS[BETA]: raise ValueError('synthetic rendering failure')
        return original(record, *args, **kwargs)
    monkeypatch.setattr(finding_catalog, 'write_bundle', failing)
    site, summary = make_catalog(tmp_path)
    assert [f['name'] for f in summary['rendering_failures']] == [THEOREMS[BETA]] and summary['proof_readings'] == 1
    links = json.loads((site / 'proofs' / ident(ALPHA) / 'links.json').read_text())
    # The rebuilt bundle falls back to the declaration line; no link names the missing reading.
    assert links['names']['OAI.Beta.target'] == {'status': 'source', 'href': f'../../sources/{source_name(BETA)}#L5',
                                                 'module': BETA, 'line': 5, 'basis': 'imported-bundled-module'}
    assert ident(BETA) not in (site / 'proofs' / ident(ALPHA) / 'reader.html').read_text()
    assert summary['citation_links']['readings_linking_another_reading'] == 0


def rewrite(site, module, change):
    folder = site / 'proofs' / ident(module)
    links = json.loads((folder / 'links.json').read_text()); change(links)
    (folder / 'links.json').write_text(json.dumps(links))
    return folder, links


def test_audit_rejects_a_page_whose_links_differ_from_links_json(catalog):
    site, _ = catalog
    rewrite(site, ALPHA, lambda l: l['names']['OAI.Alpha.helper'].update(line=6))
    assert any(e['error'] == 'citation links differ from links.json' for e in audit(site)['errors'])


@pytest.mark.parametrize('href,error', [
    ('../' + 'c' * 24 + '/reader.html', 'broken or escaping citation link'),
    ('../../sources/' + 'c' * 24 + '.html#L1', 'broken or escaping citation link'),
    (None, 'missing citation anchor'),
])
def test_audit_rejects_broken_citation_targets(catalog, href, error):
    site, _ = catalog
    target = href or f'../../sources/{source_name(ALPHA)}#L999'
    folder, links = rewrite(site, ALPHA, lambda l: l['names']['OAI.Alpha.helper'].update(href=target))
    document = load_document((folder / 'reading.json').read_bytes())
    (folder / 'reader.html').write_text(html_document(document, links=links), encoding='utf-8')
    errors = audit(site)['errors']
    assert any(e['error'] == error and e.get('citation') == 'OAI.Alpha.helper' for e in errors), errors


@pytest.mark.parametrize('names,error', [({'X.y': 5}, 'malformed citation entry'),
                                          ({'X.y': {'href': 7}}, 'malformed citation entry'),
                                          ([], 'malformed citation links'),
                                          ({'X.y': {'status': 'unresolved', 'reason': 'guess'}}, 'citation links fail validation'),
                                          ({'X.y': {'status': 'source', 'href': '../../coverage.html'}}, 'citation links fail validation')])
def test_audit_reports_malformed_link_data_without_crashing(catalog, names, error):
    from proofreader.render import embedded_json
    site, _ = catalog
    folder = site / 'proofs' / ident(ALPHA)
    data = {'schema': 'leanglish.citation-links/v1', 'names': names}
    (folder / 'links.json').write_text(json.dumps(data))
    page = (folder / 'reader.html').read_text()
    island = re.compile(r'(<script id="proofreader-links" type="application/json">).*?(</script>)', re.S)
    (folder / 'reader.html').write_text(island.sub(lambda m: m[1] + embedded_json(data) + m[2], page))
    assert any(e['error'] == error for e in audit(site)['errors'])


def test_audit_reports_unparsable_links_json_without_crashing(catalog):
    site, _ = catalog
    (site / 'proofs' / ident(ALPHA) / 'links.json').write_text('{not json')
    assert {'page': f'proofs/{ident(ALPHA)}/reader.html', 'error': 'malformed citation links'} in audit(site)['errors']


def test_summary_keeps_every_cited_name_in_the_denominator():
    payload = alpha_links(alpha_document())
    other = dict(payload, names={'OAI.Gamma.hidden': {'status': 'source', 'href': '../../sources/' + 'a' * 24 + '.html#L3'}})
    s = summarize([payload, other], build_index(SOURCES))
    assert s['project_names']['cited'] == 4 and s['project_names']['linked_to_source'] == 2
    assert s['citations']['total'] == 6 and sum(s['names'][k] for k in ('linked_to_reading', 'linked_to_source', 'unresolved')) == 5


pw = pytest.importorskip('playwright.sync_api')


@pytest.fixture(scope='module')
def browser():
    executable = shutil.which('chromium') or shutil.which('google-chrome')
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
        except Exception as exc:
            if os.environ.get('PROOFREADER_REQUIRE_BROWSER') == '1': pytest.fail(f'Browser CI requires Chromium: {exc}')
            pytest.skip(f'Browser unavailable: {exc}')
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    page = browser.new_page(viewport={'width': 1360, 'height': 960})
    errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
    yield page
    assert not errors, errors
    page.close()


def test_citations_render_as_links_in_the_document_harness(page):
    """set_content harness: hrefs are checked as attributes; navigation is tested separately."""
    page.set_content(html_document(alpha_document(), links=alpha_links(alpha_document())))
    page.locator('#expand-btn').click()
    reading = page.locator('#proof-steps a[data-citation="OAI.Beta.target"]')
    assert reading.count() == 1 and reading.get_attribute('href') == f'../{ident(BETA)}/reader.html'
    # The sentence shows the namespace-shortened name; the link keeps the full Lean name.
    assert reading.inner_text() == 'Beta.target' and 'citation-reading' in reading.get_attribute('class')
    assert reading.get_attribute('title').startswith('OAI.Beta.target · ')
    source = page.locator('#proof-steps a[data-citation="OAI.Alpha.helper"]')
    assert source.get_attribute('href') == f'../../sources/{source_name(ALPHA)}#L5'
    # Unresolved names remain plain text with the recorded reason.
    assert page.locator('#proof-steps a[data-citation="Nat.succ_le"]').count() == 0
    unresolved = page.locator('#dependencies .unresolved', has_text='OAI.Gamma.hidden')
    assert unresolved.count() == 1 and 'import headers' in unresolved.get_attribute('title')
    assert page.locator('#dependencies a').count() == 2
    assert page.locator('#citation-summary').inner_text() == ('5 cited names: 1 linked to proof readings, '
                                                              '1 to declaration lines in bundled source, 3 unresolved.')
    page.locator('.step-inspect').first.click()
    cited = page.locator('#inspector-citations')
    assert cited.locator('a[data-citation="OAI.Beta.target"]').count() == 1
    assert cited.locator('a.citation-source').get_attribute('href') == f'../../sources/{source_name(BETA)}#L5'


def test_exact_dependency_names_never_match_a_declaration_by_suffix(page):
    # 'Alpha.main' is a different constant from the reading's OAI.Alpha.main.
    document = Narrative(record(THEOREMS[ALPHA], 'Alpha.main')).document(source=SOURCES[ALPHA], file=FILE)
    page.set_content(html_document(document))
    assert page.locator('#dependencies button').count() == 0
    assert page.locator('#dependencies .unresolved', has_text='Alpha.main').count() == 1


def test_reader_without_link_data_marks_names_unlinked(page):
    page.set_content(html_document(alpha_document()))
    assert page.locator('#proof-steps a.citation').count() == 0 and page.locator('#dependencies a').count() == 0
    assert page.locator('#citation-summary').is_hidden()
    assert 'No citation link data' in page.locator('#dependencies .unresolved').first.get_attribute('title')


def test_offline_file_navigation_follows_reading_and_source_links(page, catalog):
    """Real file:// navigation inside the generated catalog."""
    site, _ = catalog
    try:
        page.goto((site / 'proofs' / ident(ALPHA) / 'reader.html').as_uri())
    except Exception as exc:  # pragma: no cover - depends on local browser policy
        pytest.skip(f'Browser policy blocks file navigation: {exc}')
    page.locator('#expand-btn').click()
    page.locator('#proof-steps a[data-citation="OAI.Beta.target"]').click()
    page.wait_for_load_state()
    assert page.url.split('?')[0].endswith(f'/proofs/{ident(BETA)}/reader.html')
    assert page.locator('#qualified-name').inner_text() == THEOREMS[BETA]
    page.go_back(); page.wait_for_load_state()
    page.locator('#expand-btn').click()
    page.locator('#proof-steps a[data-citation="OAI.Alpha.helper"]').click()
    page.wait_for_load_state()
    assert page.url.endswith(f'/sources/{source_name(ALPHA)}#L5')
    assert page.locator('#L5').inner_text().endswith('theorem helper : True := trivial')
