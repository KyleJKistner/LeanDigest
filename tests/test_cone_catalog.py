"""Supporting lemma readings (dependency cone, level 1) in the catalog and the preview.

SYNTHETIC FIXTURES: every project, source module, snapshot, Lean process, shard,
GitHub listing and catalog below is fabricated for consistency tests. No Lean ran
and nothing here is a native observation. The shard is written by the real
worker (proofreader.dependency_cone.run_shard) against a fake Lean process, then
loaded by the real loader. The browser tests use real Chromium on generated
pages. Only the workflow test reads repository files.
"""
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import shutil
import zipfile

import pytest

from proofreader import cone_catalog
from proofreader import dependency_cone as cone
from proofreader.catalog_audit import audit
from proofreader.catalog_inputs import PIN
from proofreader.declaration_index import (CONE_DENOMINATOR, build_index, citation_links, reading_map, summarize,
                                           validate_links)
from proofreader.finding_catalog import build, source_name
from proofreader.lean import RunResult
from proofreader.model import canonical_json, digest
from proofreader.narrative import Narrative, Snapshot
from proofreader.original_project import audit_environment, file_hash, make_plan as original_plan, read, write
from proofreader.render import embedded_json, html_document, load_document
from scripts import download_cone_artifacts as download
from scripts import rerender_catalog as preview
from test_dependency_cone import snapshot
from test_original_project import fixture_project

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA = 'OAI.Algebra.Alpha.Main', 'OAI.Algebra.Beta.Main'
SOURCES = {
    ALPHA: 'import OAI.Algebra.Beta.Main\n\nnamespace OAI.Alpha\n\ntheorem helper : True := trivial\n\n'
           'theorem main : True := trivial\n\nend OAI.Alpha\n',
    BETA: 'import Mathlib\n\nnamespace OAI.Beta\n\ntheorem target : True := trivial\n\nend OAI.Beta\n',
}
THEOREMS = {ALPHA: 'OAI.Alpha.main', BETA: 'OAI.Beta.target'}
# Alpha's proof applies Beta's target (a documented target) to two project lemmas and a library lemma.
# OAI.Alpha.helper is declared on line 5 of Alpha's source; OAI.Alpha.lemma is not in any bundled source.
RECORDS = {ALPHA: snapshot(THEOREMS[ALPHA], ['OAI.Beta.target', 'OAI.Alpha.helper', 'OAI.Alpha.lemma', 'Nat.succ_le']),
           BETA: snapshot(THEOREMS[BETA], ['Nat.le_refl', 'OAI.Beta.aux'])}
# Synthetic Lean output for each planned lemma: helper cites the other lemma and Beta's target.
LEMMAS = {'OAI.Alpha.helper': ['OAI.Alpha.lemma', 'OAI.Beta.target'], 'OAI.Alpha.lemma': ['True.intro']}
IDENTITY = {'release': 'synthetic', 'url': 'https://example.invalid/synthetic.zip', 'sha256': '0'*64}


def ident(module, name=None):
    return sha256((module+'\0'+(name or THEOREMS[module])).encode()).hexdigest()[:24]


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value if isinstance(value, str) else json.dumps(value), encoding='utf-8')


def configs():
    return {'Alpha': ALPHA, 'Beta': BETA}


def catalog_inputs(root, sources=SOURCES, modules=(ALPHA, BETA)):
    """Upstream tree, statements and synthetic consistency-check proof inputs for the catalog builder."""
    upstream = root/'upstream'; lean = upstream/'lean'; proofs = root/'proofs'; proofs.mkdir(parents=True)
    statements = root/'statements'; statements.mkdir()
    put(upstream/'CONTENTS.md', '**001. Linked results.** Synthetic.\n')
    put(upstream/'LICENSE', 'Example public license')
    put(lean/'docs/001.md', '# Linked results\n\n'+''.join(f'[{k}](../ComparatorChallenges/{k}.lean)\n' for k in configs()))
    for key, module in configs().items():
        put(lean/f'ComparatorChallenges/{key}.json', {'challenge_module': 'ComparatorChallenges.'+key,
            'solution_module': module, 'theorem_names': [THEOREMS[module]]})
        put(lean/f'ComparatorChallenges/{key}.lean', '-- comparison specification\n')
        put(lean/(module.replace('.', '/')+'.lean'), sources[module])
    rows = []
    for module in modules:
        rec = RECORDS[module]; directory = proofs/'targets'/ident(module)
        driver = '-- synthetic consistency fixture, not executed\n'; stdout = 'PR_NARRATIVE:'+canonical_json(rec)+'\n'
        put(directory/'Extract.lean', driver); put(directory/'snapshot.json', rec); put(directory/'stdout.txt', stdout)
        put(directory/'receipt.json', {'status': 'passed', 'schema': 'proofreader.narrative-receipt/v1', 'theorem': rec['theorem'],
            'module': module, 'lean_version': '4.34.1', 'selected_judgements': rec['judgements_checked'], 'backend': 'native',
            'all_selected_judgements_kernel_checked': True, 'path_linkage_checked_in_lean': True,
            'snapshot_sha256': Snapshot(rec).sha256, 'source_sha256': digest(driver.encode())})
        put(directory/'run.json', {'status': 'passed', 'exit_code': 0, 'stdout': stdout})
        rows.append({'id': ident(module), 'module': module, 'name': rec['theorem'], 'kind': 'theorem',
                     'status': 'reading-generated', 'directory': 'targets/'+ident(module), 'kernel_checked': True,
                     'snapshot_sha256': Snapshot(rec).sha256, 'selected_judgements': rec['judgements_checked'],
                     'source_sha256': digest(sources[module].encode())})
    put(proofs/'proofs.json', {'schema': 'leanglish.finding-proof-shard/v1', 'upstream_commit': PIN,
                               'expected_targets': len(rows), 'targets': rows})
    entries = [{'path': p.relative_to(upstream).as_posix(), 'sha256': digest(p.read_bytes())} for p in upstream.rglob('*') if p.is_file()]
    put(upstream/'acquisition.json', {'repository': 'openai/math', 'commit': PIN, 'fetched': entries})
    put(root/'source-inventory.json', [x for x in entries if x['path'].startswith('lean/')])
    return upstream, lean, statements, proofs, root/'source-inventory.json'


def make_catalog(root, **kwargs):
    upstream, lean, statements, proofs, inventory = catalog_inputs(root, **{k: kwargs.pop(k) for k in ('sources', 'modules') if k in kwargs})
    site = root/'site'
    return site, build(upstream, lean, [statements], [proofs], site, source_inventory=inventory, **kwargs)


def fake_lean(command, cwd, timeout=120, max_output=128_000_000):
    """Synthetic Lean process: nothing is compiled, and each planned lemma prints its LEMMAS record."""
    if command == ['lake', 'env', 'lean', '--version']:
        return RunResult('passed', command, 0, 'Lean (version 4.34.1, synthetic)\n', '', 0.1)
    if command[:2] == ['lake', 'build']:
        return RunResult('passed', command, 0, 'synthetic build', '', 0.2)
    name = json.loads(Path(command[3]).read_text().rsplit('#narrative ', 1)[1])
    return RunResult('passed', command, 0, 'PR_NARRATIVE:'+canonical_json(snapshot(name, LEMMAS[name]))+'\n', '', 0.3)


@pytest.fixture(scope='module')
def world(tmp_path_factory):
    """A synthetic original project, the plan from the two catalog readings and one pilot shard run by the worker."""
    tmp = tmp_path_factory.mktemp('cone-world')
    project, _, _ = fixture_project(tmp)
    for key, module in configs().items():
        write(project/f'ComparatorChallenges/{key}.json', {'challenge_module': 'ComparatorChallenges.'+key,
              'solution_module': module, 'theorem_names': [THEOREMS[module]], 'definition_names': []})
        put(project/(module.replace('.', '/')+'.lean'), SOURCES[module])
    inventory = [{'path': 'lean/'+f.relative_to(project).as_posix(), 'sha256': file_hash(f)}
                 for f in project.rglob('*') if f.is_file() and '.lake' not in f.parts]
    original = original_plan(project, inventory); environment = audit_environment(project, original)
    proofs = {ident(m): {'snapshot.json': canonical_json(r).encode(),
                         'receipt.json': canonical_json({'module': m, 'theorem': r['theorem'], 'status': 'passed',
                                                         'snapshot_sha256': Snapshot(r).sha256}).encode()}
              for m, r in RECORDS.items()}
    worker = {'original-proof-worker.json': json.dumps({'module': ALPHA, 'status': 'complete', 'environment_before': environment,
                                                        'environment_after': environment}).encode(),
              'proofs.json': json.dumps({'elapsed_seconds': 100.0}).encode()}
    plan = cone.make_plan({'proofs': proofs, 'workers': {'a'*64: worker}, 'original_plan': original,
                           'environment': environment}, IDENTITY)
    assert [l['name'] for s in plan['shards'] for l in s['lemmas']] == ['OAI.Alpha.helper', 'OAI.Alpha.lemma', 'OAI.Beta.aux']
    assert plan['pilot']['shards'] == [cone.module_id(ALPHA)]
    campaign = tmp/'campaign'
    for name, value in (('plan.json', plan), ('original-plan.json', original), ('environment.json', environment)):
        write(campaign/cone_catalog.PLAN/name, value)
    patch = pytest.MonkeyPatch()
    patch.setattr('proofreader.dependency_cone.run_bounded', fake_lean)
    patch.setattr('proofreader.narrative_io.run_bounded', fake_lean)
    try:
        report = cone.run_shard(project, original, environment, plan, cone.module_id(ALPHA),
                                campaign/('dependency-cone-'+cone.module_id(ALPHA)), trust_project=True)
    finally:
        patch.undo()
    assert report['status'] == 'complete' and report['readings_generated'] == 2
    summary, _ = cone.reconcile(plan, environment, [campaign/('dependency-cone-'+cone.module_id(ALPHA))], 'pilot')
    write(campaign/'cone-summary-level-1/dependency-cone-summary.json', summary)
    return {'campaign': campaign, 'plan': plan, 'original': original, 'environment': environment, 'summary': summary}


@pytest.fixture
def campaign(world, tmp_path):
    """A fresh copy, so a test can tamper with it."""
    copy = tmp_path/'campaign'; shutil.copytree(world['campaign'], copy)
    return copy


SUMMARY = 'cone-summary-level-1/dependency-cone-summary.json'
HELPER, LEMMA = ident(ALPHA, 'OAI.Alpha.helper'), ident(ALPHA, 'OAI.Alpha.lemma')


def test_catalog_links_supporting_readings_as_a_separate_denominator(campaign, tmp_path):
    site, s = make_catalog(tmp_path/'with', cone=campaign, cone_summary=campaign/SUMMARY)
    plain, p = make_catalog(tmp_path/'without')
    # The theorem-target coverage is exactly that of the same catalog without the cone.
    for key in ('proof_readings', 'expected_theorem_targets', 'selected_checked_frames', 'explicit_explanation_gaps',
                'findings_with_any_reading', 'all_theorem_readings_accessible', 'rendering_failures'):
        assert s[key] == p[key], key
    assert (site/'explanation-gaps.json').read_bytes() == (plain/'explanation-gaps.json').read_bytes()
    assert 'dependency_cone' not in p and not (plain/'cone').exists() and 'linked_to_cone_reading' not in p['citation_links']['names']
    c = s['dependency_cone']
    assert c['denominator_name'] == CONE_DENOMINATOR and c['counts_toward_documented_target_coverage'] is False
    assert (c['readings'], c['planned_lemmas'], c['statuses']) == (2, 3, {'not-in-run-scope': 1, 'reading-generated': 2})
    assert c['scope'] == 'pilot' and c['campaign_summary_matched'] is True and c['rendering_failures'] == []
    assert c['from_target_readings'] == {'citations_linked': 2, 'names_linked': 2, 'readings_linking': 1}
    assert s['citation_links']['project_names'] == {'cited': 4, 'linked_to_reading': 1, 'linked_to_cone_reading': 2,
                                                    'linked_to_source': 0, 'unresolved': 1}
    # The helper had a source line; it now links to its reading and keeps the source line.
    names = json.loads((site/'proofs'/ident(ALPHA)/'links.json').read_text())['names']
    assert names['OAI.Alpha.helper'] == {'status': 'reading', 'href': f'../../cone/{HELPER}/reader.html', 'module': ALPHA,
        'basis': 'same-module', 'denominator': CONE_DENOMINATOR,
        'source': {'href': f'../../sources/{source_name(ALPHA)}#L5', 'module': ALPHA, 'line': 5}}
    assert names['OAI.Beta.target']['href'] == f'../{ident(BETA)}/reader.html' and 'denominator' not in names['OAI.Beta.target']
    assert json.loads((plain/'proofs'/ident(ALPHA)/'links.json').read_text())['names']['OAI.Alpha.lemma']['status'] == 'unresolved'
    # A supporting reading links another supporting reading and a target reading, from cone/.
    lemma_links = json.loads((site/'cone'/HELPER/'links.json').read_text())['names']
    assert lemma_links['OAI.Alpha.lemma']['href'] == f'../../cone/{LEMMA}/reader.html'
    assert lemma_links['OAI.Beta.target']['href'] == f'../../proofs/{ident(BETA)}/reader.html'
    reading = json.loads((site/'cone'/HELPER/'reading.json').read_text())
    assert reading['title'] == 'OAI.Alpha.helper' and reading['files'][0] == {'path': 'Context.lean', 'source': 'import '+ALPHA+'\n',
                                                                             'sha256': digest('import '+ALPHA+'\n')}
    assert cone_catalog.note(ALPHA) in reading['declarations'][0]['warnings']
    # Shard evidence is kept byte for byte.
    shard = campaign/('dependency-cone-'+cone.module_id(ALPHA))/'lemmas'/HELPER
    for name in cone_catalog.EVIDENCE:
        assert (site/'cone'/HELPER/name).read_bytes() == (shard/name).read_bytes()
    assert json.loads((site/cone_catalog.SUMMARY_RECORD).read_text()) == json.loads((campaign/SUMMARY).read_text())
    finding = (site/'findings/001.html').read_text()
    section = re.search(r'<section id="supporting-lemmas">.*?</section>', finding)[0]
    assert section.count('<li>') == 2 and f'../cone/{HELPER}/reader.html' in section and 'pilot scope' in section
    assert finding.index('id="supporting-lemmas"') < finding.index('<h2>Manuscripts</h2>')
    page = (site/'coverage.html').read_text()
    assert '<tr><td>'+cone_catalog.ROW+'</td><td>2 of 3 planned; pilot scope</td></tr>' in page
    assert '<tr><td>'+cone_catalog.LINK_ROW+'</td><td>2</td></tr>' in page and cone_catalog.NOTE in page
    assert '<tr><td>Theorem targets with a proof reading</td><td>2 / 2</td></tr>' in page
    result = audit(site)
    assert result['passed'], result['errors']
    assert result['supporting_lemma_reader_pages'] == 2 and result['supporting_lemma_links_checked'] == 3
    assert audit(plain)['supporting_lemma_reader_pages'] == 0


def test_catalog_cli_accepts_a_campaign(campaign, tmp_path, capsys):
    from proofreader.finding_catalog import main
    upstream, lean, statements, proofs, inventory = catalog_inputs(tmp_path)
    status = main(['--upstream', str(upstream), '--lean', str(lean), '--statements', str(statements), '--proofs', str(proofs),
                   '--source-inventory', str(inventory), '-o', str(tmp_path/'site'), '--cone', str(campaign),
                   '--cone-summary', str(campaign/SUMMARY)])
    printed = json.loads(capsys.readouterr().out)
    # The fixture has no statement shards, so the builder reports incomplete statement access (status 2).
    assert status == 2 and printed['all_specification_entries_accessible'] is False
    assert printed['dependency_cone']['readings'] == 2 and not printed['dependency_cone']['rendering_failures']


def tamper_json(path, change):
    data = json.loads(path.read_text()); change(data); write(path, data)


@pytest.mark.parametrize('change,error', [
    (lambda c: (c/SUMMARY).write_text((c/SUMMARY).read_text().replace('"pilot"', '"full-1"')), 'campaign summary'),
    (lambda c: tamper_json(c/'dependency-cone-plan/environment.json', lambda e: e.update(environment_sha256='0'*64)), 'binding mismatch'),
    (lambda c: tamper_json(c/'dependency-cone-plan/plan.json', lambda p: p['pilot'].update(lemmas=1)), 'binding'),
    (lambda c: (c/('dependency-cone-'+cone.module_id(ALPHA))/'lemmas'/HELPER/'stdout.txt').write_text('no record'), 'narrative record'),
    (lambda c: shutil.rmtree(c/'dependency-cone-plan'), 'lacks dependency-cone-plan'),
    (lambda c: (c/'link').symlink_to(c/SUMMARY), 'symbolic link'),
    (lambda c: shutil.copytree(c/('dependency-cone-'+cone.module_id(ALPHA)), c/'again'), 'Duplicate'),
])
def test_an_unvalidated_campaign_is_never_accepted(campaign, tmp_path, change, error):
    change(campaign)
    with pytest.raises(ValueError, match=error):
        make_catalog(tmp_path, cone=campaign, cone_summary=campaign/SUMMARY)
    assert not (tmp_path/'site').exists()


def test_the_plan_must_come_from_this_catalogs_readings(campaign, tmp_path):
    with pytest.raises(ValueError, match='derived from other readings'):
        make_catalog(tmp_path/'one', cone=campaign, modules=(ALPHA,))
    changed = {**SOURCES, ALPHA: SOURCES[ALPHA]+'-- a different bundled source\n'}
    with pytest.raises(ValueError, match='differs from the planned source'):
        make_catalog(tmp_path/'source', cone=campaign, sources=changed)


def test_a_supporting_reading_that_fails_to_render_is_never_a_link_target(campaign, tmp_path, monkeypatch):
    original = cone_catalog.write_bundle
    def failing(record, *args, **kwargs):
        if record['theorem'] == 'OAI.Alpha.lemma': raise ValueError('synthetic rendering failure')
        return original(record, *args, **kwargs)
    monkeypatch.setattr(cone_catalog, 'write_bundle', failing)
    site, s = make_catalog(tmp_path, cone=campaign)
    c = s['dependency_cone']
    assert c['readings'] == 1 and [f['name'] for f in c['rendering_failures']] == ['OAI.Alpha.lemma'] and not (site/'cone'/LEMMA).exists()
    assert json.loads((site/'proofs'/ident(ALPHA)/'links.json').read_text())['names']['OAI.Alpha.lemma']['status'] == 'unresolved'
    assert 'OAI.Alpha.lemma' not in json.loads((site/'cone'/HELPER/'links.json').read_text())['names'] or \
        json.loads((site/'cone'/HELPER/'links.json').read_text())['names']['OAI.Alpha.lemma']['status'] == 'unresolved'
    assert '1 of 3 planned' in (site/'coverage.html').read_text() and audit(site)['passed']


@pytest.fixture
def cone_site(campaign, tmp_path):
    site, _ = make_catalog(tmp_path/'catalog', cone=campaign)
    return site


def relink(site, folder, change):
    links_path = site/folder/'links.json'; links = json.loads(links_path.read_text()); change(links)
    links_path.write_text(json.dumps(links))
    page = site/folder/'reader.html'
    island = re.compile(r'(<script id="proofreader-links" type="application/json">).*?(</script>)', re.S)
    page.write_text(island.sub(lambda m: m[1]+embedded_json(links)+m[2], page.read_text()))


@pytest.mark.parametrize('change,error', [
    (lambda site: shutil.rmtree(site/'cone'/LEMMA), 'broken or escaping'),
    (lambda site: relink(site, 'proofs/'+ident(ALPHA), lambda l: l['names']['OAI.Alpha.helper'].update(href=f'../../cone/{LEMMA}/reader.html')),
     'citation links to a reading of another name'),
    (lambda site: relink(site, 'proofs/'+ident(ALPHA), lambda l: l['names']['OAI.Alpha.helper'].pop('denominator')),
     'citation links fail validation'),
    (lambda site: (site/'cone'/HELPER/'reader.html').write_text((site/'cone'/HELPER/'reader.html').read_text().replace('Context.lean', 'Other.lean')),
     'differs from its validated reading'),
    (lambda site: tamper_json(site/'coverage.json', lambda c: c['dependency_cone'].update(counts_toward_documented_target_coverage=True)),
     'malformed dependency-cone coverage section'),
    (lambda site: tamper_json(site/'coverage.json', lambda c: c['dependency_cone']['from_target_readings'].update(citations_linked=5)),
     'differ from coverage'),
    (lambda site: tamper_json(site/'coverage.json', lambda c: c['dependency_cone'].pop('from_target_readings')),
     'malformed dependency-cone coverage section'),
    (lambda site: tamper_json(site/'coverage.json', lambda c: c['dependency_cone'].update(rendering_failures=None)),
     'malformed dependency-cone coverage section'),
    (lambda site: tamper_json(site/cone_catalog.SUMMARY_RECORD, lambda r: r['reading_index'].pop('OAI.Alpha.lemma')),
     'outcome record does not match'),
    (lambda site: shutil.copytree(site/'cone'/LEMMA, site/'cone'/('0'*24)), 'inventory mismatch'),
])
def test_static_audit_covers_supporting_pages_and_links(cone_site, change, error):
    assert audit(cone_site)['passed']
    change(cone_site)
    errors = audit(cone_site)['errors']
    assert any(error in e['error'] for e in errors), errors


def test_audit_rejects_supporting_readings_without_a_coverage_section(cone_site):
    tamper_json(cone_site/'coverage.json', lambda c: c.pop('dependency_cone'))
    assert any('without a dependency-cone coverage section' in e['error'] for e in audit(cone_site)['errors'])


def alpha_document():
    return Narrative(RECORDS[ALPHA]).document(source=SOURCES[ALPHA], file='lean/'+ALPHA.replace('.', '/')+'.lean')


def test_precedence_and_visibility_of_supporting_links():
    index = build_index(SOURCES)
    targets = reading_map({(BETA, THEOREMS[BETA]): ident(BETA)})
    lemmas = reading_map({(ALPHA, 'OAI.Alpha.lemma'): LEMMA, (BETA, 'OAI.Beta.target'): 'c'*24})
    names = citation_links(alpha_document(), ALPHA, index, targets, source_name, supporting=lemmas)['names']
    # A visible documented-target reading of the same name takes precedence over a supporting reading.
    assert names['OAI.Beta.target']['href'] == f'../{ident(BETA)}/reader.html' and 'denominator' not in names['OAI.Beta.target']
    assert names['OAI.Alpha.lemma'] == {'status': 'reading', 'href': f'../../cone/{LEMMA}/reader.html', 'module': ALPHA,
                                        'basis': 'same-module', 'denominator': CONE_DENOMINATOR}
    # A supporting reading read in an environment the citing module does not visibly import is not linked.
    hidden = reading_map({('OAI.Algebra.Gamma.Main', 'OAI.Alpha.lemma'): 'd'*24})
    names = citation_links(alpha_document(), ALPHA, index, targets, source_name, supporting=hidden)['names']
    assert names['OAI.Alpha.lemma'] == {'status': 'unresolved', 'reason': 'not-visibly-imported'}
    links = citation_links(alpha_document(), ALPHA, index, targets, source_name, supporting=lemmas)
    assert links['counts'] == {'reading': 1, 'cone-reading': 1, 'source': 1, 'unresolved': 1}
    s = summarize([links], index, supporting=True)
    assert s['project_names'] == {'cited': 3, 'linked_to_reading': 1, 'linked_to_cone_reading': 1, 'linked_to_source': 1, 'unresolved': 0}
    assert s['citations']['linked_to_cone_reading'] == 1 and s['readings_linking_a_supporting_lemma_reading'] == 1
    with pytest.raises(ValueError, match='supporting-reading accounting'):
        summarize([links], index)
    with pytest.raises(ValueError, match='Unknown reading directory'):
        citation_links(alpha_document(), ALPHA, index, targets, source_name, here='elsewhere')


@pytest.mark.parametrize('entry', [
    {'status': 'reading', 'href': '../'+'a'*24+'/reader.html', 'denominator': CONE_DENOMINATOR},
    {'status': 'reading', 'href': '../../proofs/'+'a'*24+'/reader.html', 'denominator': CONE_DENOMINATOR},
    {'status': 'reading', 'href': '../../cone/'+'a'*24+'/reader.html'},
    {'status': 'reading', 'href': '../../cone/'+'a'*24+'/reader.html', 'denominator': 'documented-targets'},
    {'status': 'source', 'href': '../../cone/'+'a'*24+'/reader.html', 'denominator': CONE_DENOMINATOR},
    {'status': 'unresolved', 'reason': 'not-in-declaration-index', 'denominator': CONE_DENOMINATOR},
    {'status': 'reading', 'href': '../../cone/'+'a'*23+'/reader.html', 'denominator': CONE_DENOMINATOR},
])
def test_supporting_links_are_marked_and_point_into_cone(entry):
    with pytest.raises(ValueError):
        validate_links({'schema': 'leanglish.citation-links/v1', 'names': {'X.y': entry}})


def test_the_denominator_names_agree():
    assert CONE_DENOMINATOR == cone.DENOMINATOR == cone_catalog.DENOMINATOR


# Preview: a published catalog built without the cone, re-rendered with it.
@pytest.fixture
def published(tmp_path, world):
    site, _ = make_catalog(tmp_path/'published')
    write(site/'original-evidence/plan.json', world['original']); write(site/'original-evidence/environment.json', world['environment'])
    put(site/'SHA256SUMS.json', json.dumps(preview.site_files(site), sort_keys=True, separators=(',', ':'))+'\n')
    return site


def test_preview_adds_supporting_readings_without_changing_target_counts(published, campaign, tmp_path):
    s = preview.build_preview(published, tmp_path/'out', cone=campaign, cone_summary=campaign/SUMMARY, archive=False)
    plain = preview.build_preview(published, tmp_path/'plain', archive=False)
    site = tmp_path/'out/Leanglish'
    assert s['explanation_gaps'] == plain['explanation_gaps'] and s['readings'] == plain['readings']
    assert s['selected_checked_frames'] == plain['selected_checked_frames']
    c = s['dependency_cone']
    assert c['included'] and c['readings'] == 2 and c['planned_lemmas'] == 3 and c['counts_toward_documented_target_coverage'] is False
    assert c['section']['original_records_compared'] is True and c['section']['campaign_summary_matched'] is True
    assert c['artifacts'] is None
    assert plain['dependency_cone'] == {'included': False, 'reason': preview.NO_CONE, 'counts_toward_documented_target_coverage': False}
    coverage = json.loads((site/'coverage.json').read_text())
    assert coverage['dependency_cone'] == c['section'] and coverage['proof_readings'] == 2
    assert s['files']['cone/*/reader.html'] == {'added': 2} and s['files'][cone_catalog.SUMMARY_RECORD] == {'added': 1}
    assert s['pages']['finding_supporting_sections'] == 1 and plain['pages']['finding_supporting_sections'] == 0
    finding = (site/'findings/001.html').read_text()
    assert 'id="supporting-lemmas"' in finding and finding.count('Catalog preview, not a release.') == 1
    assert 'adds 2 supporting lemma readings' in finding
    page = (site/'coverage.html').read_text()
    assert '2 of 3 planned; pilot scope' in page and page.count(cone_catalog.LINK_ROW) == 1 and cone_catalog.EVIDENCE_LINK in page
    notes = (site/'RELEASE-NOTES.md').read_text()
    assert '2 to a supporting lemma reading' in notes and 'Supporting lemma readings (dependency cone, level 1): 2 of 3 planned; pilot scope.' in notes
    assert 'reconciled outcomes equal the campaign summary' in (site/'preview.html').read_text()
    assert 'are not included in this preview. '+preview.NO_CONE in (tmp_path/'plain/Leanglish/preview.html').read_text()
    for name in cone_catalog.EVIDENCE:
        assert (site/'cone'/HELPER/name).read_bytes() == (campaign/('dependency-cone-'+cone.module_id(ALPHA))/'lemmas'/HELPER/name).read_bytes()
    assert s['static_audit']['passed'] and s['static_audit']['supporting_lemma_reader_pages'] == 2
    assert json.loads((site/'SHA256SUMS.json').read_text()) == preview.site_files(site)
    again = preview.build_preview(published, tmp_path/'again', cone=campaign, cone_summary=campaign/SUMMARY, archive=False)
    assert again == s


def test_preview_states_why_supporting_readings_are_missing(published, tmp_path):
    reason = 'The artifacts of dependency-cone run 1 were not used. Run 1 lacks the artifacts: dependency-cone-plan'
    s = preview.build_preview(published, tmp_path/'out', cone_unavailable=reason, archive=False)
    site = tmp_path/'out/Leanglish'
    assert s['dependency_cone'] == {'included': False, 'reason': reason, 'counts_toward_documented_target_coverage': False}
    assert reason in (site/'preview.html').read_text() and reason in (site/'RELEASE-NOTES.md').read_text()
    assert not (site/'cone').exists() and 'dependency_cone' not in json.loads((site/'coverage.json').read_text())
    with pytest.raises(ValueError, match='not both'):
        preview.build_preview(published, tmp_path/'both', cone=Path('x'), cone_unavailable=reason)
    with pytest.raises(ValueError, match='State why'):
        preview.build_preview(published, tmp_path/'empty', cone_unavailable=' ')


def test_preview_cli_with_campaign_and_with_a_reason(published, campaign, tmp_path, capsys):
    assert preview.main([str(published), str(tmp_path/'out'), '--no-archive', '--cone-shards', str(campaign),
                         '--cone-summary', str(campaign/SUMMARY)]) == 0
    assert json.loads(capsys.readouterr().out)['supporting_lemma_readings'] == 2
    assert preview.main([str(published), str(tmp_path/'plain'), '--no-archive', '--cone-unavailable', 'Synthetic reason.']) == 0
    assert json.loads(capsys.readouterr().out)['supporting_lemma_readings'] == 'not included: Synthetic reason.'


def test_preview_requires_the_published_original_records(published, campaign, world, tmp_path):
    other = dict(world['environment'], environment_sha256='0'*64)
    write(published/'original-evidence/environment.json', other)
    put(published/'SHA256SUMS.json', json.dumps(preview.site_files(published), sort_keys=True, separators=(',', ':'))+'\n')
    with pytest.raises(ValueError, match="catalog's original environment"):
        preview.build_preview(published, tmp_path/'out', cone=campaign, archive=False)


def test_preview_rejects_a_published_catalog_that_already_has_supporting_readings(campaign, tmp_path):
    site, _ = make_catalog(tmp_path/'published', cone=campaign)
    put(site/'SHA256SUMS.json', json.dumps(preview.site_files(site), sort_keys=True, separators=(',', ':'))+'\n')
    with pytest.raises(ValueError, match='already has supporting lemma readings'):
        preview.build_preview(site, tmp_path/'out', cone=campaign, archive=False)


# The download step of catalog-preview.yml, against a synthetic GitHub API.
def artifact_zip(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        for name, data in sorted(files.items()): z.writestr(name, data)
    return buffer.getvalue()


def synthetic_api(campaign, run_id=7, edit=None):
    """Zips of the campaign's directories, listed as the artifacts of one run, served like `gh api`."""
    zips = {}
    for folder in sorted(p for p in campaign.iterdir() if p.is_dir()):
        zips[folder.name] = artifact_zip({p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()})
    listing = [{'id': 100+i, 'name': name, 'digest': 'sha256:'+sha256(data).hexdigest(), 'size_in_bytes': len(data),
                'expired': False, 'expires_at': '2027-01-18T05:16:06Z', 'created_at': '2026-10-20T05:16:30Z',
                'workflow_run': {'id': run_id}} for i, (name, data) in enumerate(sorted(zips.items()))]
    if edit: edit(listing, zips)
    by_id = {a['id']: zips[a['name']] for a in listing}
    calls = []
    def gh(args):
        calls.append(args[0])
        if args[0].endswith('/artifacts?per_page=100'):
            return json.dumps({'total_count': len(listing), 'artifacts': listing}).encode()
        return by_id[int(re.fullmatch(r'repos/o/r/actions/artifacts/(\d+)/zip', args[0])[1])]
    return gh, calls


def test_download_checks_every_digest_and_writes_the_loader_layout(campaign, world, tmp_path):
    gh, calls = synthetic_api(campaign)
    record = download.download('o/r', 7, tmp_path/'cone', plan=world['plan'], gh=gh)
    assert [a['name'] for a in record['artifacts']] == ['dependency-cone-plan', 'cone-summary-level-1', 'dependency-cone-'+cone.module_id(ALPHA)]
    assert record['digests_matched'] is True and record['observations_authenticated'] is False and len(calls) == 4
    assert json.loads((tmp_path/'cone'/download.RECORD).read_text()) == record and not (tmp_path/'cone.zips').exists()
    loaded = cone_catalog.load(tmp_path/'cone', {i: (m, t, h) for r in world['plan']['readings'] for i, m, t, h in
                                                 [(r['id'], r['module'], r['theorem'], r['snapshot_sha256'])]},
                               SOURCES, summary=tmp_path/'cone'/SUMMARY)
    assert sorted(loaded['accepted']) == ['OAI.Alpha.helper', 'OAI.Alpha.lemma']
    assert preview.artifact_record(tmp_path/'cone') == record


def unsafe_zip(artifact, zips):
    """An artifact whose recorded digest matches a zip with a traversal path."""
    zips[artifact['name']] = data = artifact_zip({'../escape': b'x'})
    artifact.update(digest='sha256:'+sha256(data).hexdigest(), size_in_bytes=len(data))


@pytest.mark.parametrize('edit,error', [
    (lambda listing, zips: listing[0].update(digest='sha256:'+'0'*64), 'differs from the digest'),
    (lambda listing, zips: listing[0].update(size_in_bytes=1), 'differs from the digest'),
    (lambda listing, zips: listing[1].update(expired=True), 'expired'),
    (lambda listing, zips: listing.pop(), 'lacks the artifacts'),
    (lambda listing, zips: listing[0].update(digest=None), 'no digest'),
    (lambda listing, zips: listing[0].update(workflow_run={'id': 8}), 'another run'),
    (lambda listing, zips: listing.append(dict(listing[0], id=999)), 'Duplicate'),
    (lambda listing, zips: unsafe_zip(listing[0], zips), 'Unsafe'),
])
def test_download_failures_leave_nothing_behind(campaign, world, tmp_path, edit, error):
    gh, _ = synthetic_api(campaign, edit=edit)
    with pytest.raises(ValueError, match=error):
        download.download('o/r', 7, tmp_path/'cone', plan=world['plan'], gh=gh)
    assert not (tmp_path/'cone').exists() and not (tmp_path/'cone.zips').exists()


def test_download_cli_reports_one_line(world, tmp_path, monkeypatch, capsys):
    def unavailable(args): raise RuntimeError('gh api '+args[0]+' failed: HTTP 410: Artifact has expired\n(details)')
    monkeypatch.setattr(download, 'run_gh', unavailable)
    write(tmp_path/'plan.json', world['plan'])
    assert download.main(['--repo', 'o/r', '--run', '7', '--output', str(tmp_path/'cone'), '--cone-plan', str(tmp_path/'plan.json')]) == 1
    err = capsys.readouterr().err
    assert err.count('\n') == 1 and err.startswith('Dependency-cone artifacts not downloaded: gh api') and 'HTTP 410' in err


def test_preview_workflow_downloads_the_pilot_and_falls_back_with_a_reason():
    yaml = pytest.importorskip('yaml')
    text = (ROOT/'.github/workflows/catalog-preview.yml').read_text()
    flow = yaml.safe_load(text)
    assert flow['permissions'] == {'contents': 'read', 'actions': 'read'}
    assert flow['env']['CONE_RUN'] == '39373979494' and '39373979494' in (ROOT/'docs/DEPENDENCY_CONE.md').read_text()
    steps = flow['jobs']['preview']['steps']
    fetch = next(s for s in steps if s.get('id') == 'cone')
    assert 'if python scripts/download_cone_artifacts.py' in fetch['run'] and 'included=false' in fetch['run']
    assert '::warning::' in fetch['run'] and fetch['env'] == {'GH_TOKEN': '${{ github.token }}'}
    build_step = next(s for s in steps if 'scripts/rerender_catalog.py' in s.get('run', ''))
    assert '--cone-shards' in build_step['run'] and '--cone-unavailable' in build_step['run'] and '--cone-summary' in build_step['run']
    assert build_step['env']['CONE_REASON'] == '${{ steps.cone.outputs.reason }}'
    assert steps.index(fetch) < steps.index(build_step)
    assert {'scripts/download_cone_artifacts.py', 'tests/test_cone_catalog.py', 'benchmarks/dependency-cone/**'} <= set(flow[True]['push']['paths'])
    assert 'test_cone_catalog.py' in next(s for s in steps if 'pytest' in s.get('run', ''))['run']
    check = next(s for s in steps if 'reading-kpis/current.json' in s.get('run', ''))
    assert "summary['dependency_cone']" in check['run'] and 'GITHUB_STEP_SUMMARY' in check['run']
    assert 'git push' not in text and 'gh release' not in text and 'contents: write' not in text and 'actions: write' not in text


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
def test_supporting_readings_work_in_chromium(chromium, published, campaign, tmp_path, harness):
    preview.build_preview(published, tmp_path/'out', cone=campaign, archive=False)
    site = tmp_path/'out/Leanglish'
    expect = preview.browser_expectations(site)
    assert expect['citation'] == 'OAI.Beta.target'
    assert expect['cone'] == {'reader': f'proofs/{ident(ALPHA)}/reader.html', 'citation': 'OAI.Alpha.helper',
                              'href': f'../../cone/{HELPER}/reader.html', 'module': ALPHA, 'page': f'cone/{HELPER}/reader.html',
                              'finding': 'findings/001.html', 'finding_href': f'../cone/{HELPER}/reader.html'}
    result = preview.preview_browser_checks(site, harness, expect, tmp_path/'shots')
    assert result['passed'] and result['supporting_lemma_readings'] is True
    assert (tmp_path/'shots/supporting-lemma-reader.png').is_file()
