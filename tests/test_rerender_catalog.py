"""Catalog preview: re-render a published catalog's readings without running Lean.

Every catalog here is a synthetic consistency fixture built by the current
finding-catalog builder and then rewritten into the published 0.4.1 layout (no
citation links, no explanation-gap inventory, one extra gap in an older reading
label). Nothing is a native observation. The browser tests use real Chromium.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

import pytest

from proofreader.catalog_audit import audit
from proofreader.catalog_inputs import PIN
from proofreader.finding_catalog import build
from proofreader.model import digest
from proofreader.narrative import Snapshot
from proofreader.render import html_document, load_document
from scripts import rerender_catalog as preview
from scripts.assemble_finding_release import deterministic_zip
from scripts.fetch_reading_corpus import CORPUS

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 'OAI.Algebra.Alpha.Main', 'OAI.Algebra.Beta.Main'
SOURCES = {
    ALPHA: 'import OAI.Algebra.Beta.Main\n\nnamespace OAI.Alpha\n\ntheorem helper : True := trivial\n\n'
           'theorem main : True := trivial\n\nend OAI.Alpha\n',
    BETA: 'import Mathlib\n\nnamespace OAI.Beta\n\ntheorem target : True := trivial\n\nend OAI.Beta\n',
}
THEOREMS = {ALPHA: 'OAI.Alpha.main', BETA: 'OAI.Beta.target'}
NOTE = 'Retained native observation on unaltered source with shared upstream dependency pins; not a Comparator or complete-project replay.'


def ident(module):
    return sha256((module + '\0' + THEOREMS[module]).encode()).hexdigest()[:24]


def record(theorem, root, heads=()):
    def frame(i, path, head, children):
        return {'id': i, 'path': path, 'statement': 'True', 'role': 'application' if children else 'named',
                'head': head, 'context': [], 'children': children, 'premises': [], 'objects': [], 'budget_cut': False}
    frames = [frame(0, [], root, list(range(1, len(heads)+1)))]
    frames += [frame(i+1, [0]*i+[1], h, []) for i, h in enumerate(heads)]
    return {'schema': 'proofreader.narrative/v1', 'theorem': theorem, 'lean_version': '4.34.1', 'axioms': [],
            'statement': 'True', 'judgements_checked': len(frames), 'formula_backend': 'Lean pretty-printer', 'frames': frames}


RECORDS = {ALPHA: record(THEOREMS[ALPHA], 'OAI.Beta.target', ['OAI.Alpha.helper', 'Nat.succ_le', 'True.intro']),
           BETA: record(THEOREMS[BETA], 'Nat.le_refl')}


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value), encoding='utf-8')


def manifest(site):
    write(site / 'SHA256SUMS.json', json.dumps(preview.site_files(site), sort_keys=True, separators=(',', ':')) + '\n')


def current_catalog(tmp_path):
    """Two synthetic consistency-check readings; Alpha cites Beta. Built by the current builder."""
    upstream = tmp_path / 'upstream'; lean = upstream / 'lean'; proofs = tmp_path / 'proofs'; proofs.mkdir(parents=True)
    statements = tmp_path / 'statements'; statements.mkdir()
    write(upstream / 'CONTENTS.md', '**001. Linked results.** Synthetic.\n')
    write(upstream / 'LICENSE', 'Example public license')
    configs = {'Alpha': ALPHA, 'Beta': BETA}
    write(lean / 'docs/001.md', '# Linked results\n\n' + ''.join(f'[{k}](../ComparatorChallenges/{k}.lean)\n' for k in configs))
    for key, module in configs.items():
        write(lean / f'ComparatorChallenges/{key}.json', {'challenge_module': 'ComparatorChallenges.' + key,
              'solution_module': module, 'theorem_names': [THEOREMS[module]]})
        write(lean / f'ComparatorChallenges/{key}.lean', '-- comparison specification\n')
        write(lean / (module.replace('.', '/') + '.lean'), SOURCES[module])
    rows = []
    for module, rec in RECORDS.items():
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
    site = tmp_path / 'Leanglish'
    build(upstream, lean, [statements], [proofs], site, source_inventory=inventory)
    return site


def published_catalog(tmp_path):
    """Rewrite a current synthetic catalog into the published 0.4.1 layout, then add its manifest."""
    site = current_catalog(tmp_path)
    for page in site.rglob('*.html'):
        if page.relative_to(site).parts[0] != 'proofs':
            text = re.sub(r'<a href="(?:\.\./)*explanations\.html">Explanation gaps</a>', '', page.read_text())
            page.write_text(text, encoding='utf-8')
    for name in ('explanations.html', 'explanation-gaps.json', 'evidence/declaration-index.json'):
        (site / name).unlink()
    text = (site / 'coverage.html').read_text()
    text = re.sub('<tr><td>' + re.escape(preview.CITATION_ROWS[0]) + '.*?' + re.escape(preview.CITATION_ROWS[3]) + r'</td><td>\d+</td></tr>', '', text)
    (site / 'coverage.html').write_text(text.replace(preview.CITATION_NOTE, '').replace(preview.INDEX_LINK, ''), encoding='utf-8')
    coverage = json.loads((site / 'coverage.json').read_text()); del coverage['citation_links']
    for module in RECORDS:
        folder = site / 'proofs' / ident(module); (folder / 'links.json').unlink()
        reading = json.loads((folder / 'reading.json').read_text())
        dec = reading['declarations'][0]; dec['axes']['printer_version'] = 'source-math-en/0.4.1'
        if module == ALPHA:  # The older label left one more step unexplained.
            step = next(s for s in preview.walk(dec['steps']) if not s['fallback']); step['fallback'] = True
            folder_coverage = json.loads((folder / 'coverage.json').read_text())
            old = folder_coverage['source_bound_unexpanded_steps']; folder_coverage['source_bound_unexpanded_steps'] += 1
            write(folder / 'coverage.json', folder_coverage); coverage['explicit_explanation_gaps'] += 1
            page = site / 'findings/001.html'
            page.write_text(page.read_text().replace(f'{ident(ALPHA)}/reader.html">Open structured proof reading →</a> <span>4 checked frames · {old} ',
                                                     f'{ident(ALPHA)}/reader.html">Open structured proof reading →</a> <span>4 checked frames · {old+1} '))
        write(folder / 'reading.json', json.dumps(reading, ensure_ascii=False))
        (folder / 'reader.html').write_text(html_document(load_document((folder / 'reading.json').read_bytes())), encoding='utf-8')
        # A different, equivalent serialization: the preview must keep these bytes.
        write(folder / 'snapshot.json', json.dumps(RECORDS[module], separators=(',', ':')))
    write(site / 'coverage.json', json.dumps(coverage, sort_keys=True, separators=(',', ':')) + '\n')
    total = coverage['explicit_explanation_gaps']
    text = (site / 'coverage.html').read_text().replace(preview.GAP_ROW.format(total - 1), preview.GAP_ROW.format(total))
    (site / 'coverage.html').write_text(text, encoding='utf-8')
    (site / 'assets/catalog.js').write_text('/* earlier catalog script */\n')
    write(site / 'release.json', {'schema': 'synthetic', 'application_commit': '0' * 40, 'coverage': coverage})
    write(site / 'RELEASE-NOTES.md', '# Synthetic published notes\n\nUnchanged text.\n')
    write(site / 'START-HERE.txt', 'Open index.html in a browser.\n')
    write(site / 'browser-audit.json', {'passed': True, 'navigation_backend': 'real-offline-file-navigation'})
    write(site / 'static-audit.json', {'passed': True})
    manifest(site)
    return site


@pytest.fixture
def published(tmp_path):
    return published_catalog(tmp_path / 'input')


def run(site, out, **kwargs):
    return preview.build_preview(site, out, **kwargs)


def test_preview_rerenders_readings_and_updates_every_count(published, tmp_path):
    base = json.loads((published / 'SHA256SUMS.json').read_text())
    s = run(published, tmp_path / 'out')
    site = tmp_path / 'out/Leanglish'
    assert s['is_release'] is False and s['lean_executed'] is False and s['observations_authenticated'] is False
    assert s['readings'] == {'published': 2, 're_rendered': 2, 'added': 0, 'removed': 0, 'expected_theorem_targets': 2}
    gaps = s['explanation_gaps']
    assert gaps['published']['explicit_explanation_gaps'] == gaps['preview']['explicit_explanation_gaps'] + 1 == 5
    assert gaps['published']['frames_in_explanation_gaps'] == 5 and gaps['preview']['frames_in_explanation_gaps'] == 4
    assert s['published']['printer_versions'] == {'source-math-en/0.4.1': 2} and s['published']['release'] is None
    coverage = json.loads((site / 'coverage.json').read_text())
    assert coverage['explicit_explanation_gaps'] == 4 and coverage['citation_links']['names']['linked_to_reading'] == 1
    assert '<span>4 checked frames · 3 explicit explanation gaps</span>' in (site / 'findings/001.html').read_text()
    page = (site / 'coverage.html').read_text()
    assert preview.GAP_ROW.format(4) in page and preview.CITATION_NOTE in page and preview.INDEX_LINK in page
    assert all(label in page for label in preview.CITATION_ROWS)
    links = json.loads((site / 'proofs' / ident(ALPHA) / 'links.json').read_text())
    assert links['names']['OAI.Beta.target']['href'] == f'../{ident(BETA)}/reader.html'
    assert json.loads((site / 'explanation-gaps.json').read_text())['explicit_explanation_gaps'] == 4
    # Evidence keeps its published bytes even though the writer serializes JSON differently.
    for module in RECORDS:
        for name in preview.EVIDENCE:
            path = f'proofs/{ident(module)}/{name}'
            assert preview.file_digest(site / path) == base[path]
    assert (site / 'release.json').read_bytes() == (published / 'release.json').read_bytes()
    assert (site / 'assets/catalog.js').read_bytes() == (preview.ASSETS / 'catalog.js').read_bytes()
    for name in ('index.html', 'coverage.html', 'explanations.html', 'findings/001.html'):
        text = (site / name).read_text()
        assert text.count('Catalog preview, not a release.') == 1 and 'explanations.html">Explanation gaps</a>' in text
    assert 'Catalog preview, not a release.' not in (site / 'proofs' / ident(ALPHA) / 'reader.html').read_text()
    notes = (site / 'RELEASE-NOTES.md').read_text()
    assert notes.startswith('# Catalog preview\n') and notes.endswith('# Synthetic published notes\n\nUnchanged text.\n')
    assert 'Explicit explanation gaps: 5 published, 4 in this preview.' in notes and 'Browser audit: not run.' in notes
    assert (site / 'START-HERE.txt').read_text().endswith('Open index.html in a browser.\n')
    assert s['files']['proofs/*/snapshot.json'] == {'unchanged': 2} and s['files']['proofs/*/links.json'] == {'added': 2}
    assert s['files']['preview.html'] == {'added': 1} and s['files']['release.json'] == {'unchanged': 1}
    assert json.loads((site / 'browser-audit.json').read_text())['not_run'] is True
    assert audit(site)['passed'] and s['static_audit']['passed']
    assert json.loads((site / 'preview.json').read_text()) == {k: v for k, v in s.items() if k not in {'site', 'archive'}}


def test_manifest_and_zip_describe_the_final_site(published, tmp_path):
    s = run(published, tmp_path / 'out')
    site = tmp_path / 'out/Leanglish'
    sums = json.loads((site / 'SHA256SUMS.json').read_text())
    assert sums == preview.site_files(site)
    with zipfile.ZipFile(tmp_path / 'out' / preview.ARCHIVE) as z:
        names = set(z.namelist())
        assert names == {'Leanglish/' + n for n in sums} | {'Leanglish/SHA256SUMS.json'}
        assert all(sha256(z.read('Leanglish/' + n)).hexdigest() == h for n, h in sums.items())
    assert (tmp_path / 'out/SHA256SUMS').read_text() == s['archive']['sha256'] + '  ' + preview.ARCHIVE + '\n'
    assert preview.verify_manifest(site) == sums


def test_output_is_deterministic(published, tmp_path):
    first, second = run(published, tmp_path / 'a'), run(published, tmp_path / 'b')
    assert first == second
    files = lambda root: {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert files(tmp_path / 'a') == files(tmp_path / 'b')


def test_release_zip_input_requires_its_digest(published, tmp_path):
    archive = tmp_path / 'release.zip'
    checksum = deterministic_zip(published, archive)
    with pytest.raises(ValueError, match='digest does not match'):
        run(archive, tmp_path / 'wrong')
    s = run(archive, tmp_path / 'out', archive_sha256=checksum)
    assert s['published']['input'] == 'archive' and s['published']['archive_sha256'] == checksum
    directory = run(published, tmp_path / 'dir')
    assert (tmp_path / 'out/Leanglish/coverage.json').read_bytes() == (tmp_path / 'dir/Leanglish/coverage.json').read_bytes()
    assert directory['explanation_gaps'] == s['explanation_gaps']


@pytest.mark.parametrize('change,error', [
    (lambda site: (site / 'catalog.json').write_text('[]'), 'differ from the manifest'),
    (lambda site: (site / 'extra.txt').write_text('x'), 'manifest inventory'),
    (lambda site: (site / 'proofs' / ident(BETA) / 'run.json').unlink(), 'manifest inventory'),
])
def test_published_files_must_match_their_manifest(published, tmp_path, change, error):
    change(published)
    with pytest.raises(ValueError, match=error):
        run(published, tmp_path / 'out')


def test_symbolic_links_in_the_published_site_are_rejected(published, tmp_path):
    (published / 'link.txt').symlink_to(published / 'coverage.json')
    with pytest.raises(ValueError, match='symbolic link'):
        run(published, tmp_path / 'out')


def rewrite_consistently(site, path, change):
    target = site / path; target.write_text(change(target.read_text())); manifest(site)


@pytest.mark.parametrize('path,change,error', [
    ('findings/001.html', lambda t: t.replace('4 checked frames · 4 ', '4 checked frames · 9 '), 'finding-page counts'),
    ('coverage.json', lambda t: t.replace('"explicit_explanation_gaps":5', '"explicit_explanation_gaps":6'), 'release identity'),
    ('originals/OAI/Algebra/Beta/Main.lean', lambda t: t + '-- changed\n', 'Re-rendering failed'),
])
def test_inconsistent_published_records_stop_the_preview(published, tmp_path, path, change, error):
    rewrite_consistently(published, path, change)
    with pytest.raises(ValueError, match=error):
        run(published, tmp_path / 'out')


def test_a_rendering_failure_never_drops_a_published_reading(published, tmp_path, monkeypatch):
    original = preview.write_bundle
    def failing(record, *args, **kwargs):
        if record['theorem'] == THEOREMS[BETA]: raise ValueError('synthetic rendering failure')
        return original(record, *args, **kwargs)
    monkeypatch.setattr(preview, 'write_bundle', failing)
    with pytest.raises(ValueError, match='Re-rendering failed for 1 readings.*synthetic rendering failure'):
        run(published, tmp_path / 'out')


def test_coverage_page_text_matches_the_current_builder(tmp_path):
    page = (current_catalog(tmp_path) / 'coverage.html').read_text()
    assert preview.CITATION_NOTE in page and preview.INDEX_LINK in page
    assert all('<tr><td>' + label + '</td>' in page for label in preview.CITATION_ROWS)
    assert re.search(re.escape(preview.GAP_ROW).replace(r'\{\}', r'\d+'), page)


def test_a_current_catalog_is_updated_in_place_without_duplicates(tmp_path):
    site = current_catalog(tmp_path / 'input'); manifest(site)
    s = run(site, tmp_path / 'out')
    page = (tmp_path / 'out/Leanglish/coverage.html').read_text()
    assert page.count(preview.CITATION_ROWS[0]) == 1 and page.count(preview.CITATION_NOTE) == 1
    assert s['pages']['navigation_updated'] == 0 and s['files']['sources/*.html'] == {'unchanged': 2}


def test_cli_reports_failures_without_a_traceback(published, tmp_path, capsys):
    (published / 'catalog.json').write_text('[]')
    assert preview.main([str(published), str(tmp_path / 'out')]) == 2
    assert 'Preview failed: Published files differ from the manifest' in capsys.readouterr().err


def test_workflow_rerenders_the_pinned_release_and_never_publishes():
    yaml = pytest.importorskip('yaml')
    text = (ROOT / '.github/workflows/catalog-preview.yml').read_text()
    flow = yaml.safe_load(text)
    triggers = flow[True]
    assert triggers['push']['branches'] == ['claude/keen-archimedes-ihorkq'] and 'workflow_dispatch' in triggers
    assert sorted(triggers['push']['paths']) == ['.github/workflows/catalog-preview.yml', 'proofreader/**', 'scripts/rerender_catalog.py']
    assert flow['permissions'] == {'contents': 'read'}
    assert flow['env']['RELEASE_URL'] == CORPUS['url'] and flow['env']['RELEASE_SHA256'] == CORPUS['sha256']
    job = flow['jobs']['preview']
    runs = '\n'.join(step.get('run', '') for step in job['steps'])
    assert 'sha256sum -c' in runs and 'scripts/rerender_catalog.py' in runs and '--browser real' in runs
    uploads = [s for s in job['steps'] if s.get('uses', '').startswith('actions/upload-artifact')]
    assert uploads and all(s['with']['retention-days'] == 30 for s in uploads)
    assert 'git push' not in text and 'gh release' not in text and 'contents: write' not in text


pw = pytest.importorskip('playwright.sync_api')


@pytest.fixture(scope='module')
def chromium():
    executable = shutil.which('chromium') or shutil.which('google-chrome')
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
        except Exception as exc:
            if os.environ.get('PROOFREADER_REQUIRE_BROWSER') == '1': pytest.fail(f'Browser CI requires Chromium: {exc}')
            pytest.skip(f'Browser unavailable: {exc}')
        browser.close()


@pytest.mark.parametrize('harness', [False, True], ids=['real-file-navigation', 'document-harness'])
def test_preview_pages_work_in_chromium(chromium, published, tmp_path, harness):
    run(published, tmp_path / 'out')
    site = tmp_path / 'out/Leanglish'
    expect = preview.browser_expectations(site)
    assert expect['citation'] == 'OAI.Beta.target' and expect['gaps'] == 4
    result = preview.preview_browser_checks(site, harness, expect, tmp_path / 'shots')
    assert result['passed'] and result['navigation_backend'] == ('direct-document-test-harness' if harness else 'real-offline-file-navigation')
    assert (tmp_path / 'shots/preview-desktop.png').is_file()
