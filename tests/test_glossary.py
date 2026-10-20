"""Reviewed-gloss mechanism: proofreader/glossary.py and docs/GLOSSARY.md.

The packaged glossary holds model-proposed entries only; no entry is reviewed.
Records come from tests/fixtures/reader_quality.json, subtrees of retained
corpus snapshots. Glossaries that mark an entry reviewed are synthetic test
data built here; their reviewer name says so. Source trees in the verify tests
are synthetic files, except in the optional check against a local Mathlib
checkout named by LEANGLISH_MATHLIB_SRC.
"""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re

import pytest

import proofreader.narrative as narrative
from proofreader import glossary as G
from proofreader.cli import main as cli_main
from proofreader.kernel import InvalidExport
from proofreader.model import walk_steps
from proofreader.narrative import Narrative, check_reading, prose, reading_binding
from proofreader.render import load_document
from proofreader.reading_kpis import main as kpi_main, measure, measure_corpus

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = json.loads((ROOT/'tests/fixtures/reader_quality.json').read_text())['fixtures']
SYNTHETIC_REVIEWER = 'Synthetic Reviewer (test fixture, not a review)'
spec = importlib.util.spec_from_file_location('glossary_review', ROOT/'scripts/glossary_review.py')
review_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_script)


def real(name):
    return deepcopy(FIXTURES[name]['record'])


def steps(document):
    return list(walk_steps(document.declarations[0].steps))


def by_head(n, document, head):
    return [s for s in steps(document) if n.frames[int(s.id.rsplit(':', 1)[1])]['head'] == head]


def synthetic(reviewed=(), keep=None):
    """The packaged entries with ``reviewed`` marked reviewed by a synthetic reviewer (test data only)."""
    data = deepcopy(G.packaged().data)
    if keep is not None:
        data['entries'] = [e for e in data['entries'] if e['name'] in keep]
    for e in data['entries']:
        if e['name'] in reviewed:
            e['status'] = 'reviewed'; e['reviewed_by'] = SYNTHETIC_REVIEWER
    return G.Glossary(data)


# The packaged glossary.

def test_packaged_glossary_holds_unreviewed_model_proposals():
    g = G.packaged()
    assert len(g.entries) >= 80
    assert {e['status'] for e in g.entries.values()} == {'proposed'}
    assert {e['proposed_by'] for e in g.entries.values()} == {'model'}
    assert all(e['reviewed_by'] is None for e in g.entries.values())
    assert g.data['sources']['mathlib4']['revision'] == 'd13f23b723b8a846827a245b89c10fc7d3f11612'
    assert all(e['statement']['source'] in g.data['sources'] for e in g.entries.values())
    assert all(len(e['gloss']) <= G.MAX_GLOSS for e in g.entries.values())


def test_packaged_names_are_not_worded_by_another_renderer_rule():
    logical = ('And.', 'Iff.', 'Eq.', 'Exists.', 'Decidable.', 'Classical.', 'Or.', 'Nonempty.', 'Not.', 'False.', 'True.')
    for name in G.packaged().entries:
        assert name not in narrative._LEMMAS and name not in narrative._HEAD_ROLES and name not in narrative._REWRITES
        assert not name.startswith(logical) and narrative._automation(name) is None
        last = name.rsplit('.', 1)[-1]  # no instance, constructor or parent projection
        assert not re.match(r'inst[A-Z]', last) and last != 'mk' and not re.fullmatch(r'to[A-Z][A-Za-z]*', last), name


# Rendering modes.

@pytest.mark.parametrize('name', sorted(FIXTURES))
def test_default_mode_ignores_proposed_glosses(name):
    record = real(name)
    plain = Narrative(record, glossary=G.Glossary({**G.packaged().data, 'entries': []}).select()).document()
    default = Narrative(record).document()
    assert reading_binding(default) == reading_binding(plain)
    assert 'glossary' not in default.declarations[0].axes
    assert not any(G.MARKER in s.text for s in steps(default))
    check_reading(record, default)


def test_preview_marks_proposals_and_keeps_them_as_gaps():
    record = real('positivity_with_premises')
    n = Narrative(record, glossary='preview'); d = n.document()
    expected = {"Nat.cast_pos'": "By the equivalence 0 < ↑n ↔ 0 < n for the natural-number cast (Nat.cast_pos') [unreviewed gloss]:",
                'lt_of_lt_of_le': 'By combining a < b with b ≤ c to get a < c (lt_of_lt_of_le) [unreviewed gloss]:',
                "Nat.cast_nonneg'": "By nonnegativity of a natural number cast (Nat.cast_nonneg') [unreviewed gloss]:"}
    for head, text in expected.items():
        [s] = by_head(n, d, head)
        assert s.text == text
        assert s.fallback and s.rule == 'citation' and s.references == [head]
    axes = d.declarations[0].axes['glossary']
    assert axes == {'mode': 'preview', 'glossary_sha256': G.packaged().sha256, 'note': G.AXES_NOTE}
    assert '[Explanation gap] By combining a < b with b ≤ c to get a < c (lt_of_lt_of_le) [unreviewed gloss]:' in prose(d)
    check_reading(record, d)
    assert reading_binding(Narrative(record, glossary='preview').document()) == reading_binding(d)
    # Only the glossed steps differ from the default reading.
    default = Narrative(record).document()
    changed = [(a.text, b.text) for a, b in zip(steps(default), steps(d)) if (a.text, a.fallback, a.rule) != (b.text, b.fallback, b.rule)]
    assert len(changed) == 3 and len(steps(default)) == len(steps(d))


def test_preview_of_a_theorem_level_citation_keeps_the_marker():
    record = real('linarith')
    d = Narrative(record, glossary='preview').document()
    first = d.declarations[0].steps[0]
    assert first.text == ('The statement follows from the linear-order fact that ¬(b ≤ a) implies a < b '
                          '(lt_of_not_ge) [unreviewed gloss], applied to the facts below.')
    assert first.fallback
    check_reading(record, d)


def test_reviewed_gloss_explains_the_citation():
    """Synthetic reviewed entry: the packaged one is only proposed."""
    record = real('positivity_with_premises')
    n = Narrative(record, glossary=synthetic({"Nat.cast_nonneg'"}).select()); d = n.document()
    [s] = by_head(n, d, "Nat.cast_nonneg'")
    assert s.text == "By nonnegativity of a natural number cast (Nat.cast_nonneg'):"
    assert not s.fallback and s.rule == G.REVIEWED_RULE and s.references == ["Nat.cast_nonneg'"]
    assert s.conclusion == '0 ≤ ↑(hybridCount d)'
    assert "Nat.cast_nonneg'" in d.declarations[0].dependencies
    assert 'glossary' not in d.declarations[0].axes
    # Proposed entries stay plain citations in the reviewed mode.
    [p] = by_head(n, d, "Nat.cast_pos'")
    assert p.text == "By Nat.cast_pos':" and p.fallback


def test_a_budget_cut_keeps_a_reviewed_gloss_a_gap():
    record = real('positivity_with_premises')
    i = next(f['id'] for f in record['frames'] if f['head'] == "Nat.cast_nonneg'")
    record['frames'][i]['budget_cut'] = True
    n = Narrative(record, glossary=synthetic({"Nat.cast_nonneg'"}).select()); d = n.document()
    [s] = by_head(n, d, "Nat.cast_nonneg'")
    assert s.rule == G.REVIEWED_RULE and s.fallback


def test_reading_with_a_gloss_the_packaged_glossary_does_not_review_is_rejected():
    record = real('positivity_with_premises')
    d = Narrative(record, glossary=synthetic({"Nat.cast_nonneg'"}).select()).document()
    with pytest.raises(InvalidExport, match='deterministic regeneration'):
        check_reading(record, d)


@pytest.mark.parametrize('tamper', ['drop', 'reviewed', 'unknown', 'digest', 'extra'])
def test_tampered_glossary_mode_is_rejected(tamper):
    record = real('positivity_with_premises')
    d = Narrative(record, glossary='preview').document(); axes = d.declarations[0].axes
    if tamper == 'drop':
        del axes['glossary']
    elif tamper == 'reviewed':
        axes['glossary']['mode'] = 'reviewed'
    elif tamper == 'unknown':
        axes['glossary']['mode'] = 'draft'
    elif tamper == 'digest':
        axes['glossary']['glossary_sha256'] = '0'*64
    else:
        axes['glossary']['reviewer'] = SYNTHETIC_REVIEWER
    with pytest.raises(InvalidExport):
        check_reading(record, d)


@pytest.mark.parametrize('mode', ['preview', 'reviewed'])
def test_a_proposed_gloss_presented_as_explained_is_rejected(mode):
    record = real('positivity_with_premises')
    n = Narrative(record, glossary='preview'); d = n.document()
    [s] = by_head(n, d, "Nat.cast_nonneg'")
    s.text = s.text.replace(' '+G.MARKER, ''); s.fallback = False
    if mode == 'reviewed':
        del d.declarations[0].axes['glossary']
    with pytest.raises(InvalidExport):
        check_reading(record, d)


def test_unknown_mode_is_refused():
    with pytest.raises(InvalidExport):
        Narrative(real('linarith'), glossary='draft')


# Validation.

def mutate(change):
    data = deepcopy(G.packaged().data); e = data['entries'][0]
    change(data, e)
    return data


MUTATIONS = {
    'unknown top field': lambda d, e: d.update(extra=1),
    'wrong schema': lambda d, e: d.update(schema='leanglish.glossary/v0'),
    'unknown entry field': lambda d, e: e.update(coverage=3),
    'missing entry field': lambda d, e: e.pop('notes'),
    'unknown statement field': lambda d, e: e['statement'].update(url='x'),
    'unknown context field': lambda d, e: e['statement']['context'].append({**e['statement']['context'][0], 'kind': 'variable'}),
    'duplicate entry': lambda d, e: d['entries'].append(deepcopy(e)),
    'reviewed without reviewer': lambda d, e: e.update(status='reviewed'),
    'reviewed by blank reviewer': lambda d, e: e.update(status='reviewed', reviewed_by='  '),
    'proposed with reviewer': lambda d, e: e.update(reviewed_by=SYNTHETIC_REVIEWER),
    'unknown status': lambda d, e: e.update(status='accepted'),
    'unknown proposer': lambda d, e: e.update(proposed_by='script'),
    'long gloss': lambda d, e: e.update(gloss='x'*(G.MAX_GLOSS+1)),
    'multi-line gloss': lambda d, e: e.update(gloss='a\nb'),
    'gloss with final colon': lambda d, e: e.update(gloss='transitivity of ≤:'),
    'gloss with marker': lambda d, e: e.update(gloss='le '+G.MARKER),
    'empty gloss': lambda d, e: e.update(gloss=' '),
    'project constant': lambda d, e: e.update(name='OAI.MatchingEntropy.entropy_main'),
    'generated name': lambda d, e: e.update(name='Nat.cast_le._simp_1'),
    'renderer-worded name': lambda d, e: e.update(name='Subtype.property'),
    'malformed name': lambda d, e: e.update(name='le trans'),
    'line zero': lambda d, e: e['statement'].update(line=0),
    'line as text': lambda d, e: e['statement'].update(line='12'),
    'line as bool': lambda d, e: e['statement'].update(line=True),
    'absolute path': lambda d, e: e['statement'].update(path='/Mathlib/Order/Basic.lean'),
    'parent path': lambda d, e: e['statement'].update(path='Mathlib/../x.lean'),
    'unknown source': lambda d, e: e['statement'].update(source='batteries'),
    'unhashable source': lambda d, e: e['statement'].update(source=['mathlib4']),
    'trailing newline': lambda d, e: e['statement'].update(text=e['statement']['text']+'\n'),
    'unknown source field': lambda d, e: d['sources']['mathlib4'].update(branch='master'),
}


@pytest.mark.parametrize('name', sorted(MUTATIONS))
def test_validation_refuses(name):
    with pytest.raises(InvalidExport):
        G.Glossary(mutate(MUTATIONS[name]))


def test_validation_accepts_a_named_reviewer():
    data = mutate(lambda d, e: e.update(status='reviewed', reviewed_by=SYNTHETIC_REVIEWER))
    assert G.Glossary(data).select().explains(data['entries'][0]['name'])


def test_duplicate_json_keys_are_refused(tmp_path):
    p = tmp_path/'g.json'
    p.write_text('{"schema": "leanglish.glossary/v1", "schema": "x"}')
    with pytest.raises(InvalidExport):
        G.Glossary.read(p)


# Measurements.

def corpus(tmp_path, names=('positivity_with_premises', 'linarith', 'norm_num', 'project_citation')):
    for name in names:
        (tmp_path/name).mkdir(parents=True)
        (tmp_path/name/'snapshot.json').write_text(json.dumps(real(name), ensure_ascii=False))
    return tmp_path


def test_default_measurement_has_no_glossary_fields():
    assert 'glossary' not in measure(real('positivity_with_premises'))


def test_preview_projection_matches_a_reviewed_rendering(tmp_path):
    root = corpus(tmp_path)
    default, _ = measure_corpus(root)
    preview, rows = measure_corpus(root, 'preview')
    assert 'glossary' not in default
    g = preview['glossary']
    assert g['unreviewed_gloss_steps'] == 4 and g['readings_with_unreviewed_glosses'] == 2
    assert g['unreviewed_glosses']['lt_of_not_ge'] == {'steps': 1, 'readings': 1}
    for k in ('gap_steps', 'gap_frames', 'citation_gap_steps', 'display_steps', 'frames'):
        assert preview[k] == default[k]
    # Every shown proposal reviewed by a synthetic reviewer: the projection is exact.
    everything = synthetic(set(G.packaged().entries)).select()
    reviewed, _ = measure_corpus(root, everything)
    projected = g['projected_if_all_shown_reviewed']
    for k in ('gap_steps', 'gap_step_share', 'gap_frames', 'gap_frame_share', 'citation_gap_steps',
              'readings_without_gaps', 'readings_over_half_gap_steps'):
        assert projected[k] == reviewed[k], k
    assert reviewed['rules'][G.REVIEWED_RULE] == 4


def test_kpi_command_accepts_the_preview_flag(tmp_path):
    root = corpus(tmp_path/'c')
    assert kpi_main([str(root), '--glossary', 'preview', '-o', str(tmp_path/'p.json')]) == 0
    assert json.loads((tmp_path/'p.json').read_text())['glossary']['mode'] == 'preview'
    assert kpi_main([str(root), '-o', str(tmp_path/'d.json')]) == 0
    assert 'glossary' not in json.loads((tmp_path/'d.json').read_text())


def test_narrative_read_preview_is_checked_in_its_mode(tmp_path):
    snap = tmp_path/'snapshot.json'
    snap.write_text(json.dumps(real('positivity_with_premises'), ensure_ascii=False))
    assert cli_main(['narrative-read', str(snap), '-o', str(tmp_path/'p'), '--glossary', 'preview']) == 0
    reading = load_document((tmp_path/'p/reading.json').read_bytes())
    assert reading.declarations[0].axes['glossary']['mode'] == 'preview'
    assert G.MARKER in (tmp_path/'p/proof.txt').read_text()
    assert cli_main(['check-narrative', str(snap), str(tmp_path/'p/reading.json')]) == 0
    assert cli_main(['narrative-read', str(snap), '-o', str(tmp_path/'d')]) == 0
    assert G.MARKER not in (tmp_path/'d/proof.txt').read_text()


# Review tooling.

def test_review_document_lists_statement_instances_and_checkboxes(tmp_path):
    text = review_script.review(G.packaged(), corpus(tmp_path))
    assert text.startswith('# Glossary review\n')
    section = text.split("### `Nat.cast_pos'`", 1)[1].split('\n### ', 1)[0]
    assert 'theorem cast_pos\' {n : ℕ} : (0 : α) < n ↔ 0 < n' in section
    assert 'OAI.CurrentProjection.hybridBlockMain' in section and '0 < ↑m ↔ 0 < m' in section
    assert '- [ ] Accept' in section and '- [ ] Reject: ' in section
    assert 'Coverage: 1 citation gap step in 1 reading' in section


def test_committed_review_document_matches_the_glossary():
    text = (ROOT/'docs/glossary-review/README.md').read_text(encoding='utf-8')
    assert G.packaged().sha256 in text
    assert all(f"### `{name}`" in text for name in G.packaged().entries)


def test_mark_and_remove(tmp_path):
    path = tmp_path/'glossary.json'
    path.write_bytes(G.PATH.read_bytes())
    run = lambda *a: review_script.main(['--glossary', str(path), *a])
    assert run('mark', 'le_trans', '--reviewer', SYNTHETIC_REVIEWER) == 2  # --confirm is required
    assert run('mark', 'no_such_lemma', '--reviewer', SYNTHETIC_REVIEWER, '--confirm') == 2
    assert run('mark', 'le_trans', '--reviewer', ' ', '--confirm') == 2
    assert run('mark', 'le_trans', '--reviewer', SYNTHETIC_REVIEWER, '--confirm', '--gloss', 'transitivity of the order ≤') == 0
    e = G.Glossary.read(path).entries['le_trans']
    assert (e['status'], e['reviewed_by'], e['gloss']) == ('reviewed', SYNTHETIC_REVIEWER, 'transitivity of the order ≤')
    assert run('remove', 'le_rfl') == 0 and 'le_rfl' not in G.Glossary.read(path).entries
    assert run('remove', 'le_rfl') == 2
    assert G.PATH.read_bytes() != path.read_bytes()


def test_verify_compares_quoted_lines(tmp_path):
    g = synthetic(keep={'le_trans'})
    entry = g.entries['le_trans']
    tree = tmp_path/'mathlib'  # synthetic source tree holding only the quoted lines
    lines = {}
    for x in [entry['statement'], *entry['statement']['context']]:
        lines.setdefault(x['path'], {})[x['line']] = x['text']
    for path, at in lines.items():
        out = ['']*max(at)
        for k, text in at.items():
            out[k-1] = text
        (tree/path).parent.mkdir(parents=True, exist_ok=True)
        (tree/path).write_text('\n'.join(out)+'\n', encoding='utf-8')
    result = review_script.verify(g, {'mathlib4': tree})
    assert result['mismatches'] == [] and result['excerpts_checked'] == 1+len(entry['statement']['context'])
    first = tree/entry['statement']['path']
    first.write_text(first.read_text(encoding='utf-8').replace('le_trans', 'le_trans\''), encoding='utf-8')
    assert review_script.verify(g, {'mathlib4': tree})['mismatches'] == ['le_trans: mathlib4 '+entry['statement']['path']+':'+str(entry['statement']['line'])]
    assert review_script.verify(g, {})['unchecked_by_source'] == {'mathlib4': 1+len(entry['statement']['context'])}


@pytest.mark.skipif(not os.environ.get('LEANGLISH_MATHLIB_SRC'), reason='set LEANGLISH_MATHLIB_SRC to a Mathlib checkout at the pin')
def test_quoted_mathlib_statements_match_the_pinned_checkout():
    result = review_script.verify(G.packaged(), {'mathlib4': Path(os.environ['LEANGLISH_MATHLIB_SRC'])})
    assert result['mismatches'] == [] and result['excerpts_checked'] > 0
