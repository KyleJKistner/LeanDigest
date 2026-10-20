"""Declaration index. Inline sources are synthetic; the Bezout case reads a real retained upstream module."""
import json
import os
from pathlib import Path

import pytest

from proofreader.declaration_index import build_index, closure, mask, scan

ROOT = Path(__file__).resolve().parents[1]


def names(source, module='M'):
    return {d['name']: d['line'] for d in scan(source, module)['declarations']}


def test_namespace_section_and_end_nesting():
    src = ('namespace A.B\n'
           'theorem one : True := trivial\n'
           'section Inner\n'
           'def two := 2\n'
           'end Inner\n'
           'noncomputable section\n'
           'lemma three : True := trivial\n'
           'end\n'
           'end B\n'
           'theorem four : True := trivial\n'
           'end A\n'
           'theorem five : True := trivial\n')
    assert names(src) == {'A.B.one': 2, 'A.B.two': 4, 'A.B.three': 7, 'A.four': 10, 'five': 12}


def test_modifiers_attributes_qualified_and_root_names():
    src = ('namespace N\n'
           '/-- doc with theorem fake -/\n'
           '@[simp, norm_cast]\n'
           'protected theorem Foo.bar : True := trivial\n'
           '@[simp] private lemma hidden : True := trivial\n'
           'noncomputable def _root_.Top.level : Nat := 0\n'
           'partial def loop (n : Nat) : Nat := loop n\n'
           'unsafe def raw : Nat := 0\n'
           'def withUniverse.{u} (α : Sort u) : Sort u := α\n'
           'theorem\n'
           '  split_header : True := trivial\n'
           'end N\n')
    assert names(src, 'Pkg.Mod') == {
        'N.Foo.bar': 4, '_private.Pkg.Mod.0.N.hidden': 5, 'Top.level': 6, 'N.loop': 7,
        'N.raw': 8, 'N.withUniverse': 9, 'N.split_header': 10}


def test_comments_strings_chars_and_quotations_declare_nothing():
    src = ('-- theorem line_comment : True\n'
           '/- outer /- nested theorem inner -/ still comment\n'
           'namespace Fake\n-/\n'
           'def s := "theorem in_string \\" end"\n'
           "def c := '\"'\n"
           'def r := r#"theorem raw "quoted" "#\n'
           'macro_rules | `(tactic| done) => `(tactic| theorem quoted)\n'
           "theorem f'' (s : Set Nat) : f '' s = s := rfl\n")
    assert names(src) == {'s': 5, 'c': 6, 'r': 7, "f''": 9}
    masked = mask(src)
    assert len(masked) == len(src) and masked.count('\n') == src.count('\n')
    assert 'in_string' not in masked and 'inner' not in masked and 'quoted' not in masked


def test_name_literals_and_dot_notation_are_not_commands():
    src = ('namespace N\n'
           'def k : Lean.Name := `instance\n'
           'def l : Lean.Name := ``theorem\n'
           'def m : Foo := .structure bogus\n'
           'def p (x : Nat × Nat) := x.1.end\n'
           'theorem real : True := trivial\n'
           'end N\n')
    result = scan(src, 'M')
    assert {d['name']: d['line'] for d in result['declarations']} == {'N.k': 2, 'N.l': 3, 'N.m': 4, 'N.p': 5, 'N.real': 6}
    assert not result['skipped']


def test_anonymous_generated_and_unsupported_names_are_reported_not_indexed():
    src = ('instance : Inhabited Nat := ⟨0⟩\n'
           'instance [Inhabited α] : Inhabited (List α) := ⟨[]⟩\n'
           'instance (priority := 100) named : Inhabited Bool := ⟨true⟩\n'
           'instance (priority := low) : Inhabited Unit := ⟨()⟩\n'
           'deriving instance Repr for Foo\n'
           'attribute [instance] named\n'
           'example : True := trivial\n'
           'theorem «quoted name» : True := trivial\n'
           'class inductive Choice\n  | a | b\n'
           'structure Pair where\n  fst : Nat\n')
    result = scan(src, 'M')
    assert {d['name'] for d in result['declarations']} == {'named', 'Choice', 'Pair'}
    reasons = sorted(s['reason'] for s in result['skipped'])
    assert reasons == ['anonymous-example', 'anonymous-instance', 'anonymous-instance',
                       'anonymous-instance', 'quoted-identifier']
    # Structure projections and constructors are generated names: never guessed.
    assert 'Pair.fst' not in names(src) and 'Pair.mk' not in names(src)


@pytest.mark.parametrize('source', [
    'namespace A\ntheorem t : True := trivial\nend B\n',
    'namespace A\nsection S\nend A\n',
    'namespace A\nend\n',
    'theorem t : True := (trivial\n',
    'theorem t : True := trivial)\n',
    '/- unterminated\ntheorem t : True := trivial\n',
    'def s := "unterminated\n',
])
def test_unbalanced_module_contributes_no_names(source):
    with pytest.raises(ValueError):
        scan(source, 'Bad')
    index = build_index({'Bad': source, 'Good': 'theorem t : True := trivial\n'})
    assert set(index['failed_modules']) == {'Bad'}
    assert index['names'] == {'t': {'module': 'Good', 'line': 1, 'kind': 'theorem'}}


def test_duplicate_names_are_ambiguous_and_never_linked():
    index = build_index({'X': 'namespace N\ntheorem t : True := trivial\nend N\n',
                         'Y': '\ntheorem N.t : True := trivial\n',
                         'Z': 'theorem u : True := trivial\n'})
    assert 'N.t' not in index['names'] and 'u' in index['names']
    assert index['ambiguous']['N.t'] == [{'module': 'X', 'line': 2, 'kind': 'theorem'},
                                         {'module': 'Y', 'line': 2, 'kind': 'theorem'}]


def test_line_numbers_match_source_page_numbering():
    # Source pages number str.splitlines(); form feeds and CRLF must agree.
    src = 'import A\r\n-- page\x0cbreak\ntheorem t : True := trivial\n def d := 1\n'
    found = names(src)
    lines = src.splitlines()
    assert lines[found['t']-1].startswith('theorem t') and lines[found['d']-1].startswith('def d')


def test_imports_and_visible_closure():
    index = build_index({'A': 'import B\nimport Mathlib\ntheorem a : True := trivial\n',
                         'B': 'import all C\nimport Outside\n', 'C': '', 'D': 'import A\n'})
    assert index['imports'] == {'A': ['B', 'Mathlib'], 'B': ['C', 'Outside'], 'C': [], 'D': ['A']}
    assert closure(index, 'A') == {'A', 'B', 'C'}
    assert closure(index, 'C') == {'C'}


def test_closure_follows_header_only_records_but_indexed_modules_keep_scanned_imports():
    index = build_index({'A': 'import H\n', 'B': 'theorem b : True := trivial\n', 'F': 'import B\ntheorem f : True := (\n'},
                        {'H': ['B'], 'A': ['ignored'], 'F': ['B']})
    # A failed module contributes no names, but its readable header still records an import.
    assert index['header_imports'] == {'F': ['B'], 'H': ['B']} and index['imports']['A'] == ['H']
    assert closure(index, 'A') == {'A', 'H', 'B'} and closure(index, 'A', recorded=False) == {'A'}
    assert closure(index, 'F') == {'F', 'B'} and 'F' in index['failed_modules']


def test_real_retained_module_matches_lean_recorded_theorem_name():
    """Not synthetic: the committed upstream module and the Lean-exported theorem name."""
    source = (ROOT / 'proofreader/data/bezout-original.lean').read_text(encoding='utf-8')
    theorem = json.loads((ROOT / 'proofreader/data/bezout-snapshot.json').read_text())['theorem']
    found = names(source, 'OAI.Algebra.AffineCancellation.BezoutFrame')
    assert found == {theorem: 11}
    assert source.splitlines()[10].startswith('theorem exists_frame')


def test_every_repository_lean_file_scans_without_failure():
    files = sorted(p for p in ROOT.rglob('*.lean') if '.lake' not in p.parts)
    index = build_index({p.relative_to(ROOT).as_posix(): p.read_text(encoding='utf-8') for p in files})
    assert len(files) > 100 and not index['failed_modules']
    # Copies of the retained Bezout module stay ambiguous rather than picking one.
    assert 'OAI.ComplexCancellation.BezoutFrame.exists_frame' in index['ambiguous']


RELEASE = os.environ.get('LEANGLISH_RELEASE_ROOT')


@pytest.mark.skipif(not RELEASE, reason='Set LEANGLISH_RELEASE_ROOT to an unpacked published catalog')
def test_published_solution_modules_agree_with_recorded_reading_names():
    """Real data when supplied: bundled originals and the Lean-recorded theorem of each reading."""
    site = Path(RELEASE)
    configs = [json.loads(p.read_text()) for p in (site / 'originals/ComparatorChallenges').glob('*.json')]
    modules = sorted({c['solution_module'] for c in configs})
    index = build_index({m: (site / 'originals' / (m.replace('.', '/') + '.lean')).read_text(encoding='utf-8')
                         for m in modules})
    assert not index['failed_modules'] and not index['ambiguous']
    found = mismatched = 0
    for reading in (site / 'proofs').glob('*/reading.json'):
        d = json.loads(reading.read_text())['declarations'][0]
        module = d['file'][5:-5].replace('/', '.')
        entry = index['names'].get(d['name'])
        found += bool(entry)
        mismatched += bool(entry) and entry['module'] != module
    assert found > 0 and mismatched == 0
