"""Capture-avoiding beta and zeta reduction, including binder adversaries."""
import copy
from pathlib import Path
import pytest
from proofreader.kernel import Dag, Argument, read_record, InvalidExport
from proofreader.normalization import Reduction, DisplayLimit
from proofreader.english import Formula, English, check_reading

N={'tag':'str','prefix':{'tag':'anonymous'},'value':'x'}
@pytest.fixture
def dag():return Dag([{'tag':'sort','level':{'tag':'zero'}}],[])
def var(d,k):return d.add({'tag':'bvar','index':k})
def lam(d,b,domain=0):return d.add({'tag':'lam','name':N,'domain':domain,'body':b,'binder':'explicit'})
def app(d,f,a):return d.add({'tag':'app','fn':f,'arg':a})

def test_beta_identity(dag):
    x=var(dag,0);f=lam(dag,x);t=dag.add({'tag':'nat','value':'3'})
    assert dag.equal(Reduction(dag).head(app(dag,f,t)),t)

def test_outer_local_is_not_captured(dag):
    # (fun x => fun y => x) z -> fun y => z; z shifts to index 1.
    inner=lam(dag,var(dag,1));f=lam(dag,inner);z=var(dag,0)
    actual=Reduction(dag).head(app(dag,f,z))
    assert dag.equal(actual,lam(dag,var(dag,1)))
    assert Formula(dag).render(actual,['z'])=='(x ↦ z)'

def test_argument_with_its_own_binder(dag):
    # Substitution must not shift the identity's local binder.
    ident=lam(dag,var(dag,0));body=lam(dag,var(dag,1))
    actual=Reduction(dag).instantiate(body,ident)
    assert dag.equal(actual,lam(dag,ident))

def test_decrement_variables_beyond_removed_binder(dag):
    actual=Reduction(dag).instantiate(var(dag,2),var(dag,0))
    assert dag.equal(actual,var(dag,1))

def test_domain_not_in_scope_of_its_own_binder(dag):
    body=lam(dag,var(dag,0),var(dag,0));arg=dag.add({'tag':'nat','value':'12'})
    result=Reduction(dag).instantiate(body,arg)
    assert dag.equal(result,lam(dag,var(dag,0),arg))

def test_zeta(dag):
    v=dag.add({'tag':'nat','value':'7'})
    e=dag.add({'tag':'let','name':N,'type':0,'value':v,'body':var(dag,0),'nondep':False})
    assert dag.equal(Reduction(dag).head(e),v)

def test_many_shared_subterms_do_not_expand(dag):
    root=var(dag,0)
    for _ in range(400):root=app(dag,root,root)
    before=len(dag.nodes);r=Reduction(dag).instantiate(root,0)
    assert len(dag.nodes)<before+500
    assert dag.demand[r]==0

def test_bounded_nonterminating_untyped_display(dag):
    # Structural input may be untyped until Lean replay. Display must still terminate.
    v=var(dag,0);f=lam(dag,app(dag,v,v));omega=app(dag,f,f)
    with pytest.raises(DisplayLimit):Reduction(dag).head(omega,fuel=10)
    assert 'normalization limit' in Formula(dag).render(omega)

@pytest.mark.parametrize('field',['text','type','names'])
def test_assumption_text_and_binding_cannot_be_modified(field):
    p=Path(__file__).parents[1]/'artifacts/v0.2/injective_comp.kernel.json'
    r=read_record(p);d=English(r).document();d.declarations[0].parameters[-1][field]='False'
    with pytest.raises(InvalidExport):check_reading(r,d)

def test_injective_composition_reading_has_no_lambda_application_noise():
    r=read_record(Path(__file__).parents[1]/'artifacts/v0.2/injective_comp.kernel.json')
    d=English(r).document();texts=' '.join(s.text for s in d.declarations[0].steps)
    assert 'Injectivity of g' in texts and '(f(x) = f(y))' in texts
    assert 'Injectivity of f' in texts and '(x = y)' in texts
    assert '↦' not in texts

def test_huge_application_spine_stops_at_display_budget(dag):
    root=0
    for _ in range(5000):root=app(dag,root,0)
    assert 'normalization limit' in Formula(dag).render(root)
