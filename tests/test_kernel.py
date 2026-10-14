import copy
import json
from pathlib import Path
import pytest
from proofreader.kernel import Argument, Dag, InvalidExport, name_key, display_name, replay_source
from proofreader.english import English, Formula, check_reading, prose_text

ROOT = Path(__file__).resolve().parents[1] / 'artifacts' / 'v0.2'
@pytest.fixture
def swap(): return json.loads((ROOT/'and_swap.kernel.json').read_text())
@pytest.fixture
def trans(): return json.loads((ROOT/'trans.kernel.json').read_text())

def test_actual_lean_export(swap):
    a=Argument(swap)
    assert a.name=='PRSmoke.and_swap'
    assert len(a.claims)==18
    assert a.coverage()['truncated_steps']==0
    assert a.coverage()['english_formally_verified'] is False

def test_subterm_path_binding(swap):
    swap['steps'][4]['term']=swap['steps'][6]['term']
    with pytest.raises(InvalidExport,match='path|different claim'): Argument(swap)

def test_omitted_proof_child(swap):
    swap['steps'][3]['children'].pop()
    with pytest.raises(InvalidExport):Argument(swap)

def test_omitted_argument(swap):
    swap['steps'][3]['arguments'].pop()
    with pytest.raises(InvalidExport,match='inventory'):Argument(swap)

def test_false_proof_argument_classification(swap):
    swap['steps'][3]['arguments'][0]['is_proof']=True
    with pytest.raises(InvalidExport):Argument(swap)

def test_wrong_scope(swap):
    swap['exprs'][4]['index']=100
    with pytest.raises(InvalidExport,match='free'):Argument(swap)

def test_forward_edge(swap):
    swap['exprs'][3]['fn']=4
    with pytest.raises(InvalidExport,match='earlier'):Argument(swap)

def test_unknown_expression_field(swap):
    swap['exprs'][3]['display']='evil'
    with pytest.raises(InvalidExport):Argument(swap)

def test_bool_reference(swap):
    swap['steps'][1]['term']=True
    with pytest.raises(InvalidExport):Argument(swap)

def test_unreachable_step(swap):
    swap['steps'].append(copy.deepcopy(swap['steps'][7]))
    with pytest.raises(InvalidExport):Argument(swap)

def test_shared_expression_dag(swap):
    a=Argument(swap)
    assert len(a.dag.nodes)==32  # Includes three generated domain-closure nodes.
    claims=a.closed_claims()
    assert len(claims)==18
    assert all(a.dag.demand[t]==a.dag.demand[p]==0 for _,t,p,_ in claims)

def test_exact_name_identity():
    anon={'tag':'anonymous'}
    a={'tag':'str','prefix':anon,'value':'A.B'}
    b={'tag':'str','prefix':{'tag':'str','prefix':anon,'value':'A'},'value':'B'}
    assert name_key(a)!=name_key(b) and display_name(a)!=display_name(b)
    x={'tag':'str','prefix':anon,'value':'12'}
    y={'tag':'num','prefix':anon,'value':'12'}
    assert name_key(x)!=name_key(y) and display_name(x)!=display_name(y)

def test_reading_is_deterministic(swap):
    assert English(swap).document().to_json()==English(swap).document().to_json()
    text=prose_text(swap)
    assert 'Let P be a proposition' in text and 'Let Q be a proposition' in text
    assert '(Q ∧ P)' in text
    assert 'And.intro' not in text

def test_transitivity_reading(trans):
    text=prose_text(trans)
    assert 'Using a and the established fact P, conclude Q.' in text
    assert 'Using b and the established fact Q, conclude R.' in text

def test_forged_prose_rejected(swap):
    doc=English(swap).document()
    check_reading(swap,doc)
    doc.declarations[0].steps[-1].text='Therefore every proposition is true.'
    with pytest.raises(InvalidExport,match='regeneration'):check_reading(swap,doc)

def test_forged_conclusion_rejected(swap):
    doc=English(swap).document();doc.declarations[0].statement='False'
    with pytest.raises(InvalidExport):check_reading(swap,doc)

def test_replay_checks_all_claims_and_preserves_root(swap):
    code=replay_source(swap)
    assert 'proofreaderEraseMetadata originalValue == e26' in code
    assert 'addDecl' in code and 'debug.skipKernelTC false' in code
    assert '.defnDecl' in code and '.thmDecl' in code
    assert 'Axiom inventory mismatch' in code
    assert 'Proof/data classification mismatch' in code
    assert 'Assumption/object classification mismatch' in code
    assert 'PROOFREADER_JUDGEMENTS_OK' in code

@pytest.mark.parametrize('mod',['A\nimport X','../../x','A;eval',''])
def test_unsafe_import_rejected(swap,mod):
    with pytest.raises(InvalidExport):replay_source(swap,imports=[mod])

def test_deep_shared_dag_does_not_expand_exponentially():
    nodes=[{'tag':'sort','level':{'tag':'zero'}}]
    for i in range(1,10000):nodes.append({'tag':'app','fn':i-1,'arg':i-1})
    d=Dag(nodes,[])
    assert d.demand[-1]==0 and len(d.hashes)==10000

def test_argument_owns_validated_snapshot(swap):
    a=Argument(swap)
    original_hash=a.sha256
    original_path=list(a.steps[4]['path'])
    swap['steps'][4]['path']=[100]
    swap['exprs'][0]['tag']='untrusted_mutation'
    swap['axioms'].append('untrusted.axiom')
    assert a.steps[4]['path']==original_path
    assert a.record['exprs'][0]['tag']=='sort'
    assert not a.record['axioms']
    assert a.sha256==original_hash
    assert len(a.closed_claims())==18

@pytest.mark.parametrize('child',[{},[],True,'4',None])
def test_malformed_child_rejected_as_invalid_export(swap,child):
    swap['steps'][3]['children']=[child]
    with pytest.raises(InvalidExport,match='reference'):Argument(swap)
