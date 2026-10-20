"""Display notation: namespace shortening and structural rules.

Most cases here are synthetic formula strings (labelled per test group); the
integration tests at the end use the committed Bézout snapshot and the two
retained audit fixtures, which are real exported snapshots.
"""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from proofreader import notation
from proofreader.notation import Reading, display, parse
from proofreader.model import walk_steps
from proofreader.narrative import Narrative, check_reading, math_text, prose, reading_binding

ROOT = Path(__file__).resolve().parents[1]
BEZOUT = ROOT/'proofreader/data/bezout-snapshot.json'
FIXTURES = ROOT/'tests/audit/fixtures'


def reading(*strings, theorem='OAI.BinPackingGap.main_results', local=()):
    return Reading.build(theorem, strings, local)


def shown(text, *extra, theorem='OAI.BinPackingGap.main_results', local=()):
    return display(text, reading(text, *extra, theorem=theorem, local=local))


# --- namespace shortening (synthetic strings) --------------------------------

def test_own_enclosing_and_library_namespaces():
    assert shown('OAI.BinPackingGap.opt I ≤ 2 * OAI.BinPackingGap.lb I') == 'opt I ≤ 2 * lb I'
    assert shown('OAI.A.foo x = OAI.C.bar', theorem='OAI.A.B.thm') == 'foo x = C.bar'
    assert shown('OAI.A.B.Sub.f = 0', theorem='OAI.A.B.thm') == 'Sub.f = 0'
    assert shown('MeasureTheory.volume (Set.Icc 0 1) = 1 ∧ Filter.atTop ≤ Filter.atTop') == 'volume (Icc 0 1) = 1 ∧ atTop ≤ atTop'


def test_unopened_library_namespaces_stay_qualified():
    text = 'Finset.card s ≤ Fintype.card V ∧ ENNReal.ofReal x = Nat.succ n'
    assert shown(text) == '#s ≤ Fintype.card V ∧ ENNReal.ofReal x = Nat.succ n'


def test_two_full_names_never_share_a_shown_name():
    r = reading('OAI.BinPackingGap.map f = Filter.map f')
    assert display('OAI.BinPackingGap.map f = Filter.map f', r) == 'BinPackingGap.map f = Filter.map f'
    values = list(r.names.values())
    assert len(values) == len(set(values))


def test_local_binder_and_bound_variable_block_shortening():
    assert shown('OAI.BinPackingGap.opt I', local=['opt']) == 'BinPackingGap.opt I'
    assert shown('∀ opt, opt ≤ OAI.BinPackingGap.opt I') == '∀ opt, opt ≤ BinPackingGap.opt I'
    assert shown('OAI.BinPackingGap.opt I', local=['opt._@.Mathlib._hyg.12']) == 'BinPackingGap.opt I'


def test_shortened_prefix_cannot_read_as_a_local_projection():
    assert shown('G.size = OAI.BinPackingGap.G.size', local=['G']) == 'G.size = BinPackingGap.G.size'
    # Real.log → log would collide with the namespace of OAI…log.foo.
    assert shown('Real.log x = OAI.BinPackingGap.log.foo') == 'Real.log x = BinPackingGap.log.foo'


def test_reserved_root_names_and_library_namespaces():
    assert shown('Set.Finite s ∧ Set.Nonempty s') == 'Set.Finite s ∧ Set.Nonempty s'
    assert shown('OAI.BinPackingGap.Nonempty x') == 'BinPackingGap.Nonempty x'
    assert shown('OAI.Real.foo x', theorem='OAI.thm') == 'OAI.Real.foo x'
    # Project constants of the corpus that repeat a library root name.
    assert shown('OAI.BinPackingGap.IsClosed s ∧ OAI.BinPackingGap.Field') == 'BinPackingGap.IsClosed s ∧ BinPackingGap.Field'


def test_words_of_the_narrative_dictionary_block_shortening():
    from proofreader.narrative import _math_dictionary
    frame = {'statement': 'EuclideanDomain.gcd a b = OAI.BinPackingGap.gcd a', 'objects': [], 'head': '', 'context': []}
    record = {'theorem': 'OAI.BinPackingGap.t', 'frames': [frame]}
    assert Reading.of(record).names['OAI.BinPackingGap.gcd'] == 'gcd'
    r = Reading.of(record, _math_dictionary)
    assert r.names['OAI.BinPackingGap.gcd'] == 'BinPackingGap.gcd'
    assert display(_math_dictionary(frame['statement']), r) == 'gcd(a, b) = BinPackingGap.gcd a'


def test_names_in_string_literals_and_fields_are_untouched():
    assert shown('OAI.BinPackingGap.f "OAI.BinPackingGap.f" = 1') == 'f "OAI.BinPackingGap.f" = 1'
    assert shown("OAI.BinPackingGap.f 'a' = nhds 0") == "f 'a' = 𝓝 0"
    assert shown('(g x).nhds = nhds x') == '(g x).nhds = 𝓝 x'


@pytest.mark.parametrize('text', ['OAI.BinPackingGap.f "open', 'OAI.BinPackingGap.f «x y»',
                                  'OAI.BinPackingGap.f `n', 'OAI.BinPackingGap.f -- c',
                                  '(OAI.BinPackingGap.f x', 'OAI.BinPackingGap.f x)', '⟨OAI.BinPackingGap.f]'])
def test_unrecognized_text_is_returned_unchanged(text):
    assert shown(text) == text


def test_outside_a_reading_display_is_the_identity():
    assert display('Filter.Tendsto (fun x => x) Filter.atTop (nhds 0)') == 'Filter.Tendsto (fun x => x) Filter.atTop (nhds 0)'
    assert math_text('Real.log x * y') == 'Real.log x · y'
    assert notation.name('OAI.BinPackingGap.opt') == 'OAI.BinPackingGap.opt'


def test_shortening_is_order_independent():
    strings = ['OAI.BinPackingGap.map f', 'Filter.map f', 'Real.log x', 'Set.univ', 'OAI.BinPackingGap.log.a']
    a = Reading.build('OAI.BinPackingGap.t', strings, ['x', 'f'])
    b = Reading.build('OAI.BinPackingGap.t', list(reversed(strings)), ['f', 'x'])
    assert a.names == b.names and a.via == b.via


# --- structural notation (synthetic strings) ---------------------------------

def test_tendsto_lambda_at_top_to_a_limit():
    text = 'Filter.Tendsto (fun x => OAI.TotientAsymptotic.V x / OAI.TotientAsymptotic.mainTerm x) Filter.atTop (nhds 1)'
    assert shown(text, theorem='OAI.TotientAsymptotic.formula') == 'V x / mainTerm x → 1 as x → ∞'


def test_tendsto_variants():
    assert shown('Filter.Tendsto (fun n => f n) Filter.atTop Filter.atTop') == 'f n → ∞ as n → ∞'
    assert shown('Filter.Tendsto (fun n => f n) Filter.atTop Filter.atBot') == 'f n → −∞ as n → ∞'
    assert shown('Filter.Tendsto (fun n => f n) Filter.atTop (nhds (g 0))') == 'f n → g 0 as n → ∞'
    assert shown('Filter.Tendsto (fun n => f n) Filter.atTop (nhds (a, b))') == 'f n → (a, b) as n → ∞'
    # A low-precedence body is parenthesized; the whole form is when it is an operand.
    assert (shown('0 < c ∧ Filter.Tendsto (fun N => ∑ k ∈ s N, f k) Filter.atTop (nhds c)')
            == '0 < c ∧ ((∑ k ∈ s N, f k) → c as N → ∞)')
    assert shown('¬Filter.Tendsto (fun n => |f n|) Filter.atTop (nhds 0)') == '¬(|f n| → 0 as n → ∞)'


@pytest.mark.parametrize('text,expected', [
    # Not a lambda: only names change.
    ('Filter.Tendsto f Filter.atTop (nhds 0)', 'Tendsto f atTop (𝓝 0)'),
    # Another source filter.
    ('Filter.Tendsto (fun x => f x) (nhds 0) (nhds 0)', 'Tendsto (x ↦ f x) (𝓝 0) (𝓝 0)'),
    # Two binders, a typed binder, a pattern.
    ('Filter.Tendsto (fun x y => f x) Filter.atTop (nhds 0)', 'Tendsto (fun x y => f x) atTop (𝓝 0)'),
    ('Filter.Tendsto (fun (x : ℕ) => f x) Filter.atTop (nhds 0)', 'Tendsto (fun (x : ℕ) => f x) atTop (𝓝 0)'),
    ('Filter.Tendsto (fun ⟨a, b⟩ => f a) Filter.atTop (nhds 0)', 'Tendsto (fun ⟨a, b⟩ => f a) atTop (𝓝 0)'),
    # Partial and over-applied.
    ('Filter.Tendsto (fun x => f x) Filter.atTop', 'Tendsto (x ↦ f x) atTop'),
    ('Filter.Tendsto (fun x => f x) Filter.atTop (nhds 0) y', 'Tendsto (x ↦ f x) atTop (𝓝 0) y'),
    # As an argument of another function.
    ('P Filter.Tendsto (fun x => f x) Filter.atTop (nhds 0)', 'P Tendsto (x ↦ f x) atTop (𝓝 0)'),
    # The limit is not a single atom.
    ('Filter.Tendsto (fun x => f x) Filter.atTop (nhds a b)', 'Tendsto (x ↦ f x) atTop (𝓝 a b)'),
    ('Filter.Tendsto (fun x => f x) Filter.atTop (nhds x⁻¹)', 'Tendsto (x ↦ f x) atTop (𝓝 x⁻¹)'),
])
def test_tendsto_bails_out(text, expected):
    assert shown(text) == expected


def test_string_literals_are_atoms_for_structural_rules():
    assert (shown('Filter.Tendsto (fun x => g x "fun y => y") Filter.atTop (nhds "Real.pi")')
            == 'g x "fun y => y" → "Real.pi" as x → ∞')
    assert shown('P "fun x => Real.sqrt x" ∧ Real.sqrt "s"') == 'P "fun x => Real.sqrt x" ∧ √"s"'


def test_tendsto_word_collision_bails_out():
    text = 'Filter.Tendsto (fun x => f x) Filter.atTop (nhds as)'
    assert shown(text) == 'Tendsto (x ↦ f x) atTop (𝓝 as)'


@pytest.mark.parametrize('text,expected', [
    # The limit's n is free; "as n → ∞" would bind it.
    ('Filter.Tendsto (fun n => f n) Filter.atTop (nhds n)', 'Tendsto (n ↦ f n) atTop (𝓝 n)'),
    ('Filter.Tendsto (fun n => f n) Filter.atTop (nhds (g n.1))', 'Tendsto (n ↦ f n) atTop (𝓝 (g n.1))'),
])
def test_tendsto_limit_mentioning_the_bound_variable_bails_out(text, expected):
    assert shown(text) == expected


def test_tendsto_bails_out_when_the_reading_prints_infinity():
    # In ENNReal, atTop is the filter at ⊤ and differs from 𝓝 ∞.
    text = 'Filter.Tendsto (fun n => f n) Filter.atTop Filter.atTop'
    assert shown(text, 'f 0 < ∞') == 'Tendsto (n ↦ f n) atTop atTop'
    assert shown(text) == 'f n → ∞ as n → ∞'


def test_n_ary_binder_commas_stay_inside_a_lambda_body():
    assert shown('⟨fun x => Σ y, f x y, h⟩') == '⟨(x ↦ Σ y, f x y), h⟩'
    assert shown('⟨fun x => ⨁ i, f i x, h⟩') == '⟨(x ↦ ⨁ i, f i x), h⟩'
    assert shown('⟨fun x => ∫ t in a..b, f t x, h⟩') == '⟨(x ↦ ∫ t in a..b, f t x), h⟩'
    # The exterior power ⋀[R]^n M takes no comma.
    assert shown('⟨fun x => ⋀[R]^n M, h⟩') == '⟨(x ↦ ⋀[R]^n M), h⟩'


@pytest.mark.parametrize('text,expected', [
    ('fun x => x + 1', 'x ↦ x + 1'),
    ('(fun x => x + 1) 2', '(x ↦ x + 1) 2'),
    ('Finset.sum s fun i => f i', 'Finset.sum s (i ↦ f i)'),
    ('f = fun x => g x', 'f = (x ↦ g x)'),
    ('fun x => fun y => x', 'x ↦ y ↦ x'),
    ('fun n => ∑ i ∈ Finset.range n, f i', 'n ↦ ∑ i ∈ Finset.range n, f i'),
    ('fun x => if x < 0 then 0 else x', 'x ↦ if x < 0 then 0 else x'),
    ('⟨fun x => e x, h⟩', '⟨(x ↦ e x), h⟩'),
    ('(fun x => e x : ℕ → ℕ)', '((x ↦ e x) : ℕ → ℕ)'),
    ('Integrable (fun x =>\n    ‖f x‖) μ', 'Integrable (x ↦\n    ‖f x‖) μ'),
])
def test_lambda(text, expected):
    assert shown(text) == expected


@pytest.mark.parametrize('text', [
    'fun x y => x', 'fun (x : ℕ) => x', 'fun ⟨a, b⟩ => a', 'fun {x} [Fintype x] I => I.query',
    'fun x => match x with | 0 => 1 | _ => 2', 'have B := fun i => e i; P B', 'fun x => let y := x; y',
    'fun x => by simp', '↑fun x => x', 'fun x => x ↦ y', 'fun x =>', 'fun x => ∀ y',
])
def test_lambda_bails_out(text):
    assert shown(text) == text


def test_symbols():
    assert shown('Real.exp (Real.log x) = x ∧ 2 * Real.pi > 0') == 'exp (log x) = x ∧ 2 * π > 0'
    assert shown('Real.log x = Complex.log z') == 'log x = Complex.log z'
    assert shown('nhdsWithin 0 (Set.Ioi 0) ≤ nhds 0') == '𝓝[Ioi 0] 0 ≤ 𝓝 0'
    assert shown('Real.sqrt (x + 1) ^ 2 = x + 1') == '√(x + 1) ^ 2 = x + 1'
    assert shown('Nat.choose n 2 = n * (n - 1) / 2') == '(n choose 2) = n * (n - 1) / 2'
    assert shown('Finset.card (s ∪ t) ≤ Finset.card s + Finset.card t') == '#(s ∪ t) ≤ #s + #t'
    # A choose form that fills a parenthesized group is not parenthesized twice.
    assert shown('↑(Nat.choose 20 10) / 2') == '↑(20 choose 10) / 2'
    assert shown('(Nat.choose n k : ℝ)') == '((n choose k) : ℝ)'


@pytest.mark.parametrize('text,local,expected', [
    ('Real.pi = π', ['π'], 'Real.pi = π'),
    ('Real.exp x = exp', ['exp'], 'Real.exp x = exp'),
    ('𝓝 = nhds', ['𝓝'], '𝓝 = nhds'),
    ('Finset.card s = #t', [], 'Finset.card s = #t'),
    ('Nat.choose n k = choose', ['choose'], 'Nat.choose n k = choose'),
    ('f Real.sqrt x', [], 'f Real.sqrt x'),
    ('Real.sqrt x⁻¹', [], 'Real.sqrt x⁻¹'),
    ('Real.sqrt x y', [], 'Real.sqrt x y'),
    ('Nat.choose n', [], 'Nat.choose n'),
    ('Finset.card = g', [], 'Finset.card = g'),
    ('nhdsWithin a', [], 'nhdsWithin a'),
])
def test_symbol_bail_outs(text, local, expected):
    assert shown(text, local=local) == expected


IDEMPOTENT = ['OAI.BinPackingGap.opt I ≤ 2 * OAI.BinPackingGap.lb I',
              'Filter.Tendsto (fun x => OAI.BinPackingGap.V x / x) Filter.atTop (nhds 1) ∧ P',
              'Finset.sum s fun i => Real.log (f i)', 'nhdsWithin 0 (Set.Ioi 0)', 'Nat.choose n 2 + Finset.card s',
              '⟨fun x => e x, h⟩', 'Real.sqrt (x + 1) = 2 * Real.pi']


@pytest.mark.parametrize('text', IDEMPOTENT)
def test_idempotent(text):
    r = reading(text)
    once = display(text, r)
    assert display(once, r) == once
    assert display(once, reading(once)) == once


def test_parse_tree_is_balanced_and_lossless():
    text = 'f (g ⟨a, [b]⟩) {x | p x}'
    tree = parse(text)
    assert tree is not None
    def flat(items):
        return ''.join(i.open+flat(i.items)+i.close if isinstance(i, notation.Group) else i.text for i in items)
    assert flat(tree) == text
    assert parse('f (g ⟨a, b)⟩') is None


# --- integration with real snapshots -----------------------------------------

def without_notation(record, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(notation, 'display', lambda text, r=None: text)
        return Narrative(record).document()


def test_bezout_reading_is_unchanged(monkeypatch):
    record = json.loads(BEZOUT.read_text())
    with_layer = Narrative(record).document()
    assert 'notation' not in with_layer.declarations[0].axes
    assert with_layer.to_json() == without_notation(record, monkeypatch).to_json()


@pytest.mark.parametrize('fixture', ['infinite_matroid', 'diamond_distortion'])
def test_retained_fixture_legend_and_regeneration(fixture):
    record = json.loads((FIXTURES/(fixture+'.snapshot.json')).read_text())
    d = Narrative(record).document(source='retained separately')
    check_reading(record, d)
    axes = d.declarations[0].axes
    assert 'notation' in axes
    text = prose(d)
    assert 'Notation (display only; the recorded Lean formulas are unchanged):' in text
    for ns in axes['notation']['omitted_namespaces']:
        assert ns in text
    # The reader page and the Markdown view show the warnings: the same legend
    # is the last warning, so no view shows shortened names without it.
    legend = d.declarations[0].warnings[-1]
    assert legend.startswith(notation.LEGEND_TITLE)
    assert all(line[2:] in legend for line in notation.legend(d.declarations[0])[1:-1])
    # Raw Lean formulas stay attached to each step and are untouched.
    frames = {f['statement'] for f in record['frames']}
    assert all(s.source in frames for s in walk_steps(d.declarations[0].steps))


@pytest.mark.parametrize('fixture', ['infinite_matroid', 'diamond_distortion'])
def test_retained_fixture_name_map_is_injective_and_avoids_locals(fixture):
    record = json.loads((FIXTURES/(fixture+'.snapshot.json')).read_text())
    r = Reading.of(record)
    local = {f['binder'] for f in record['frames'] if 'binder' in f} | {c['name'] for f in record['frames'] for c in f['context']}
    shown = list(r.names.values())
    assert len(shown) == len(set(shown)) and not set(shown) & local
    assert not {s.split('.')[0] for s in shown} & local
    # Every omitted namespace in the legend is used by a displayed name.
    d = Narrative(record).document().declarations[0]
    text = notation.displayed_text(d)
    for ns in d.axes['notation']['omitted_namespaces']:
        assert any(r.via[t] == 'ns:'+ns and s in text for t, s in r.names.items())


def test_cited_names_use_the_same_map_and_reach_the_legend():
    r = reading('OAI.BinPackingGap.opt_le I', 'Filter.Tendsto_id')
    assert notation.name('OAI.BinPackingGap.opt_le', r) == 'opt_le'
    assert notation.name('Nat.succ_le', r) == 'Nat.succ_le'
    assert notation.summary(r, 'Apply opt_le.')['omitted_namespaces'] == ['OAI.BinPackingGap']
    assert notation.summary(r, 'Apply opt_lemma.')['omitted_namespaces'] == []


def test_changed_legend_is_rejected():
    record = json.loads((FIXTURES/'infinite_matroid.snapshot.json').read_text())
    d = Narrative(record).document()
    forged = copy.deepcopy(d)
    forged.declarations[0].axes['notation']['omitted_namespaces'].append('Real')
    assert reading_binding(forged) != reading_binding(d)
    with pytest.raises(ValueError):
        check_reading(record, forged)


def test_every_frame_still_owned_once():
    record = json.loads((FIXTURES/'diamond_distortion.snapshot.json').read_text())
    n = Narrative(record)
    n.document()
    assert set(n.owners) == set(range(len(record['frames'])))


def test_cross_process_determinism():
    path = FIXTURES/'infinite_matroid.snapshot.json'
    code = ('import json,sys;from proofreader.narrative import Narrative;'
            'print(Narrative(json.load(open(sys.argv[1]))).document().to_json(),end="")')
    outs = {subprocess.run([sys.executable, '-c', code, str(path)], cwd=ROOT, check=True, capture_output=True, text=True,
                           env={**os.environ, 'PYTHONHASHSEED': seed}).stdout for seed in ('0', '7', '4242')}
    assert len(outs) == 1
