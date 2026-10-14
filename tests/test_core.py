import copy
import pytest
from proofreader.core import *
from proofreader.model import report,walk_steps


def test_valid_transport_is_not_proof_validation(identity_export):
    assert validate_export(identity_export)['term_nodes']==5
    document=export_document(identity_export,fixture=True)
    assert report(document)['successful_local_lean_receipts']==0
    assert report(document)['checked_english_proofs']==0
    assert 'fixture' in ' '.join(document.declarations[0].warnings).lower()


def test_replay_uses_structural_original_and_new_kernel_decl(identity_export):
    generated=replay_source(identity_export,'Example')
    assert 'originalValue == reconstructed' in generated
    assert 'original.type == expected' in generated
    assert 'addDecl' in generated
    assert 'isDefEq' not in generated
    assert 'PROOFREADER_REPLAY_OK' in generated


@pytest.mark.parametrize('module',['A\nimport Evil','A;bad','../A','', 'A.B"'])
def test_replay_module_injection_rejected(identity_export,module):
    with pytest.raises(InvalidExport):replay_source(identity_export,module)


def test_transport_binder_scoping(identity_export):
    identity_export['raw_term']['body']['body']['index']=2
    with pytest.raises(InvalidExport,match='Loose'):validate_export(identity_export)


@pytest.mark.parametrize('tag',['fvar','mvar','truncated','mdata','something-new'])
def test_open_unknown_or_incomplete_constructor_rejected(tag):
    with pytest.raises(InvalidExport):validate_expr({'tag':tag})


def test_universe_parameters_not_guessed():
    e={'tag':'sort','level':{'tag':'param','name':make_name('u')}}
    with pytest.raises(InvalidExport):validate_expr(e)
    assert validate_expr(e,{'u'})==1


def test_internal_names_remain_structured():
    n={'tag':'num','prefix':make_name('_private.Module'),'value':'12'}
    validate_name(n)
    code=name_to_lean(n)
    assert 'Lean.Name.num' in code and '12' in code
    assert name_text(n)=='_private.Module.12'


def test_unsafe_literal_is_escaped():
    s='"\nrun_elab IO.println "BAD"\0\\'
    lit=lean_string(s)
    assert '\n' not in lit
    assert '\\n' in lit and '\\x00' in lit and '\\"' in lit


def test_nat_literals_reject_code():
    with pytest.raises(InvalidExport):validate_expr({'tag':'nat','value':'0; evil'})
    with pytest.raises(InvalidExport):validate_expr({'tag':'nat','value':'01'})


def test_node_budget(identity_export):
    with pytest.raises(InvalidExport,match='budget'):validate_expr(identity_export['raw_term'],max_nodes=2)


def test_boolean_not_a_variable_index():
    with pytest.raises(InvalidExport):validate_expr({'tag':'bvar','index':True})


def test_missing_proof_cannot_replay(identity_export):
    del identity_export['raw_term']
    with pytest.raises(InvalidExport):replay_source(identity_export,'Example')


def test_typed_view_has_propositions_and_context(identity_export):
    d=export_document(identity_export,fixture=True)
    steps=list(walk_steps(d.declarations[0].steps))
    assert steps[-1].conclusion=='P'
    assert steps[-1].context[-1]=={'name':'h','type':'P'}
    assert all(s.evidence=='typed-export' for s in steps)


def test_unsupported_typed_view_is_visible(identity_export):
    identity_export['proof']={'rule':'future-constructor','conclusion':'P'}
    s=export_document(identity_export).declarations[0].steps[0]
    assert s.fallback


def test_axiom_policy_is_distinct(identity_export):
    identity_export['axioms']=['sorryAx']
    d=export_document(identity_export)
    assert any('sorryAx' in w for w in d.declarations[0].warnings)
    assert report(d)['checked_english_proofs']==0
