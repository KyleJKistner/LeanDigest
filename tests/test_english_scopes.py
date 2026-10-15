"""Printer-only tests with constructed syntax/steps, not Lean proof observations."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

from proofreader.core import make_name
from proofreader.kernel import Argument, Dag
from proofreader.english import English, Formula, prose_text
from proofreader.model import Step


def logical_dag():
    # Universe/type information here is just syntax for printer regression.
    d=Dag([{'tag':'sort','level':{'tag':'zero'}}],[])
    const=lambda n:d.add({'tag':'const','name':make_name(n),'levels':[]})
    app=lambda f,x:d.add({'tag':'app','fn':f,'arg':x})
    a,p,q=const('A'),const('P'),const('Q')
    exists=app(app(const('Exists'),a),p)
    implication=d.add({'tag':'forall','name':make_name('h'),'domain':exists,
                       'body':q,'binder':'explicit'})
    forall=d.add({'tag':'forall','name':make_name('x'),'domain':a,
                 'body':q,'binder':'explicit'})
    conjunction=app(app(const('And'),forall),p)
    return d,exists,implication,forall,conjunction


def test_quantifiers_do_not_capture_the_neighboring_connective():
    d,e,im,f,c=logical_dag();r=Formula(d)
    assert r.render(e)=='(∃ x : A, P(x))'
    assert r.render(im)=='((∃ x : A, P(x)) → Q)'
    # A non-dependent forall is printed as an arrow; dependent syntactic version
    # below exercises an actual quantifier scope.
    b=d.add({'tag':'bvar','index':0})
    f=d.add({'tag':'forall','name':make_name('x'),'domain':0,'body':b,'binder':'explicit'})
    and_c=d.add({'tag':'const','name':make_name('And'),'levels':[]})
    first=d.add({'tag':'app','fn':and_c,'arg':f})
    whole=d.add({'tag':'app','fn':first,'arg':e})
    assert r.render(whole)=='((∀ x : Prop, x) ∧ (∃ x : A, P(x)))'


def test_existential_display_binder_is_fresh_against_outer_names():
    d,e,*_=logical_dag()
    assert Formula(d).render(e,['x'])=='(∃ x_2 : A, P(x_2))'


def test_unknown_application_cannot_lift_branch_assumptions(monkeypatch):
    record=json.loads((Path(__file__).parents[1]/'artifacts/v0.2/and_swap.kernel.json').read_text())
    renderer=English(record)
    left=Step('left','assume','Assume P locally.','',children=[Step('lp','truth','Use P.','')])
    right=Step('right','assume','Assume Q locally.','',children=[Step('rq','truth','Use Q.','')])
    root=Step('root','lemma-application','Use the following two scoped arguments.','',children=[left,right],fallback=True)
    monkeypatch.setattr(renderer,'describe',lambda _:root)
    result=renderer.prose_steps()
    assert len(result)==1 and result[0].id=='root'
    assert [s.id for s in result[0].children]==['left','right']
    assert result[0].fallback


def test_plain_text_includes_the_nested_proof_not_only_its_introduction(monkeypatch):
    conclusion=Step('end','truth','This proves the branch conclusion.','')
    branch=Step('local','assume','Assume P locally.','',children=[conclusion])
    doc=SimpleNamespace(declarations=[SimpleNamespace(name='Printer test',parameters=[],statement='R',steps=[branch])])
    monkeypatch.setattr(English,'__init__',lambda *args:None)
    monkeypatch.setattr(English,'document',lambda *args:doc)
    output=prose_text({})
    assert '\nAssume P locally.\n  This proves the branch conclusion.\n' in output
