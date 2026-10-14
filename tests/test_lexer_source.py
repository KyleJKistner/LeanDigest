from pathlib import Path
import pytest
from proofreader.lexer import lex,balanced_split
from proofreader.source import parse_source,merge_documents
from proofreader.model import walk_steps,report


def test_nested_comments_do_not_create_declarations():
    s='/- theorem fake : False := by sorry /- nested -/ -/\ntheorem real : True := by\n  trivial\n'
    d=parse_source(s)
    assert [x.name for x in d.declarations]==['real']
    assert not d.declarations[0].warnings


def test_strings_and_quoted_names():
    s='def «a b» : String := "theorem fake := by sorry"\ndef prime\' : String := r##"/- not comment -/"##\n'
    d=parse_source(s)
    assert len(d.declarations)==2
    assert not any(x.warnings for x in d.declarations)
    assert any(t.kind=='string' for t in lex(s).tokens)


def test_source_namespace_section_context():
    s='namespace A\nvariable (X : Type)\nsection\nvariable (x : X)\ntheorem t : x = x := by rfl\nend\ntheorem u : True := by trivial\nend A\ntheorem v : True := by trivial\n'
    d=parse_source(s)
    assert [x.name for x in d.declarations]==['A.t','A.u','v']
    assert len(d.declarations[0].context)==2
    assert len(d.declarations[1].context)==1
    assert len(d.declarations[2].context)==0


def test_assumptions_are_not_inferred_from_intro_names():
    d=parse_source('theorem f : ∀ n : Nat, n = n := by\n  intro n\n  rfl\n')
    assert 'objects or assumptions' in d.declarations[0].steps[0].text
    assert all(s.conclusion is None for s in walk_steps(d.declarations[0].steps))
    assert report(d)['checked_english_proofs']==0


def test_unknown_is_retained_not_counted():
    d=parse_source('theorem t : True := by\n  secret_solver\n')
    s=d.declarations[0].steps[0]
    assert s.fallback and s.source=='secret_solver'
    assert report(d)['source_steps_unclassified']==1


def test_compound_tactics_not_falsely_flattened():
    d=parse_source('theorem t : True ∧ True := by\n  constructor <;> trivial\n')
    assert d.declarations[0].steps[0].rule=='tactic-combinator'
    assert d.declarations[0].steps[0].fallback


def test_have_scope_and_source_spans():
    source='theorem t : True := by\n  have h : True := by\n    trivial\n  exact h\n'
    d=parse_source(source)
    steps=d.declarations[0].steps
    assert [s.rule for s in steps]==['intermediate','use-proof']
    assert steps[0].children[0].rule=='trivial'
    for s in walk_steps(steps):
        assert source[s.span.start:s.span.end]==s.source


def test_multiple_inline_steps_have_valid_spans():
    source='theorem t : True := by\n  have h : True := by trivial\n  exact h\n'
    d=parse_source(source)
    for s in walk_steps(d.declarations[0].steps):assert source[s.span.start:s.span.end]==s.source


def test_cases_nesting_preserved():
    source='theorem t (n : Nat) : n = n := by\n  cases n with\n  | zero => rfl\n  | succ k =>\n    rfl\n'
    steps=parse_source(source).declarations[0].steps
    assert [s.rule for s in steps]==['cases']
    assert [s.rule for s in steps[0].children]==['case','case']
    assert steps[0].children[0].children[0].rule=='rfl'
    assert steps[0].children[1].children[0].rule=='rfl'


def test_admissions_and_axioms_are_warning_evidence():
    d=parse_source('axiom mystery : False\ntheorem t : False := by sorry\n')
    assert len(d.declarations)==2
    assert all(x.warnings for x in d.declarations)
    assert report(d)['successful_local_lean_receipts']==0


def test_custom_commands_warn_and_do_not_claim_complete_discovery():
    d=parse_source('syntax "new_theorem" : command\nnew_theorem\n')
    assert d.warnings
    assert d.provenance['trust']=='not-elaborated'


def test_parameters_typeclasses_and_statement():
    d=parse_source('theorem t {X : Type} [Inhabited X] (x : X) : x = x := by rfl\n').declarations[0]
    assert d.statement=='x = x'
    assert [p['binder'] for p in d.parameters]==['{','[','(']
    assert d.parameters[1]['type']=='Inhabited X'


def test_utf16_column():
    source='😀 α\n'
    l=lex(source)
    assert l.lsp_position(source.index('α'))=={'line':0,'character':3}


def test_top_level_split_respects_nested_binders():
    assert balanced_split('a : (b : c) : d',':')==['a','(b : c)','d']


def test_document_is_deterministic():
    s='namespace N\ntheorem x : True := by trivial\nend N\n'
    assert parse_source(s).to_json()==parse_source(s).to_json()


def test_duplicate_source_paths_fail():
    d=parse_source('theorem t : True := by trivial')
    with pytest.raises(ValueError):merge_documents([d,d])


def test_nul_rejected():
    with pytest.raises(ValueError):parse_source('x\0y')


def test_unclosed_comment_reported():
    assert lex('/- unfinished').diagnostics


def test_source_statement_never_called_verified():
    d=parse_source('theorem t : False := by trivial')
    assert d.declarations[0].axes['statement']=='source-not-elaborated'
    assert d.declarations[0].evidence=='source'


def test_bullets_keep_branch_boundaries():
    source="theorem t : True := by\n  by_cases h : True\n  · have k : True := by\n      trivial\n    exact k\n  · contradiction\n"
    d=parse_source(source)
    branches=d.declarations[0].steps[0].children
    assert len(branches)==2
    assert all(s.rule=='case' for s in branches)
    assert branches[0].children[0].rule=='intermediate'
    assert branches[0].children[0].children[0].rule=='trivial'
    assert branches[0].children[1].rule=='use-proof'
    assert branches[1].children[0].rule=='contradiction'
    for s in walk_steps(d.declarations[0].steps): assert source[s.span.start:s.span.end]==s.source
