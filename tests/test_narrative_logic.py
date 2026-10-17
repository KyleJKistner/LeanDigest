"""Small synthetic renderer fixtures; native counterparts are tested separately."""
from proofreader.model import walk_steps
import copy
import pytest
from proofreader.narrative import Narrative, Snapshot, check_reading, prose
from proofreader.kernel import InvalidExport


def conjunction():
    contexts=[];fs=[]
    def f(role,statement,path,children=(),**extra):
        return dict(id=len(fs),role=role,statement=statement,path=path,children=list(children),
                    head='',objects=[],premises=[],context=copy.deepcopy(contexts),budget_cut=False,**extra)
    statement='∀ (P Q : Prop), P ∧ Q → P'
    for i,(name,domain,st) in enumerate([('P','Prop',statement),('Q','Prop','∀ (Q : Prop), P ∧ Q → P'),('h','P ∧ Q','P ∧ Q → P')]):
        fs.append(f('introduce' if i<2 else 'assume',st,[1]*i,[i+1],binder=name,domain=domain))
        contexts.append(dict(name=name,type=domain))
    node=f('application','P',[1,1,1],[4,5]);node.update(head='And.casesOn',objects=['P','Q','fun _ => P'],premises=[dict(argument=3,statement='P ∧ Q',frame=4),dict(argument=4,statement='P → Q → P',frame=5)])
    fs.append(node);fs.append(f('given','P ∧ Q',[1,1,1,0,1],binder='h'))
    fs.append(f('assume','P → Q → P',[1]*4,[6],binder='hp',domain='P'));contexts.append(dict(name='hp',type='P'))
    fs.append(f('assume','Q → P',[1]*5,[7],binder='hq',domain='Q'));contexts.append(dict(name='hq',type='Q'))
    fs.append(f('given','P',[1]*6,binder='hp'))
    return dict(schema='proofreader.narrative/v1',theorem='Synthetic.conjunction',lean_version='4.34.1',axioms=[],
                statement=statement,frames=fs,judgements_checked=len(fs),formula_backend='Lean pretty-printer')


def identity():
    base=dict(path=[],statement='True',head='id',role='identity',context=[],objects=['True'],
              children=[1],premises=[dict(argument=1,statement='True',frame=1)],budget_cut=False,id=0)
    child=dict(base,id=1,path=[1],head='True.intro',role='named',objects=[],children=[],premises=[])
    return dict(schema='proofreader.narrative/v1',theorem='Synthetic.identity',lean_version='4.34.1',axioms=[],
                statement='True',frames=[base,child],judgements_checked=2,formula_backend='Lean pretty-printer')


def test_conjunction_decomposition_preserves_every_frame_and_scope():
    r=conjunction();n=Narrative(r);d=n.document()
    assert 'obtain hp: P and hq: Q.' in prose(d)
    assert d.declarations[0].steps[0].rule=='unpack-conjunction'
    assert set(n.owners)==set(range(8))
    assert all(not s.fallback for s in walk_steps(d.declarations[0].steps))
    check_reading(r,d)
    d.declarations[0].steps[0].text='Obtain hp: False.'
    with pytest.raises(InvalidExport):check_reading(r,d)


@pytest.mark.parametrize('kind',['arity','domain','cut'])
def test_unrecognized_conjunction_shape_keeps_the_gap(kind):
    r=conjunction()
    if kind=='arity':r['frames'][3]['objects'].append('extra')
    if kind=='domain':r['frames'][3]['objects'][0]='Other'
    if kind=='cut':r['frames'][3]['budget_cut']=True
    d=Narrative(r).document()
    assert any(s.fallback for s in walk_steps(d.declarations[0].steps))
    assert not any(s.rule=='unpack-conjunction' for s in walk_steps(d.declarations[0].steps))


def test_identity_proof_remains_auditable():
    r=identity();n=Narrative(r);d=n.document()
    assert set(n.owners)=={0,1}
    assert d.declarations[0].steps[0].rule=='identity-proof'
    assert not any(s.fallback for s in walk_steps(d.declarations[0].steps))
    check_reading(r,d)


def test_oversaturated_identity_is_not_hidden():
    r=identity();r['frames'][0]['objects'].append('unexpected')
    d=Narrative(r).document()
    assert d.declarations[0].steps[0].fallback
