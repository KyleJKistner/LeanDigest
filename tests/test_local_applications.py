"""Local application display metadata is typed by Lean; mutations are rejected locally.

Synthetic records below exercise display contracts only. The native integration
suite obtains independent real records of implication and witness elimination.
"""
from copy import deepcopy
import pytest
from proofreader.narrative import Snapshot, Narrative
from proofreader.model import canonical_json


def sample(shadowed=False):
    context=[];frames=[]
    specs=[('P','Prop','introduce'),('Q','Prop','introduce'),('h','P → Q','assume'),('hp','P','assume')]
    if shadowed:specs.append(('h','Q','assume'))
    for i,(name,domain,role) in enumerate(specs):
        frames.append(dict(id=i,path=[1]*i,statement='∀ (P Q : Prop), (P → Q) → P → Q' if i==0 else 'Q',
            role=role,head='',context=deepcopy(context),children=[i+1],premises=[],objects=[],
            budget_cut=False,binder=name,domain=domain))
        context.append({'name':name,'type':domain})
    i=len(frames)
    frames.append(dict(id=i,path=[1]*i,statement='Q',role='local-application',head='',
        context=deepcopy(context),children=[i+1],premises=[{'argument':0,'statement':'P','frame':i+1}],
        objects=[],budget_cut=False,binder='h',domain='P → Q',local_index=2))
    frames.append(dict(id=i+1,path=[1]*(i+1),statement='P',role='given',head='',
        context=deepcopy(context),children=[],premises=[],objects=[],budget_cut=False,binder='hp'))
    return dict(schema='proofreader.narrative/v1',theorem='Synthetic.localApplication',lean_version='4.34.1',
        axioms=[],statement=frames[0]['statement'],frames=frames,judgements_checked=len(frames),formula_backend='Lean pretty-printer')


def test_application_names_the_original_hypothesis():
    r=sample();Snapshot(r);d=Narrative(r).document()
    text=d.to_json()
    assert 'Apply the hypothesis h: P → Q.' in text
    assert 'Apply the recorded term' not in text
    assert not any(step.fallback for step in d.declarations[0].steps)


def test_shadowed_name_keeps_original_context_index():
    d=Narrative(sample(True)).document()
    assert 'h (context entry 3)' in d.to_json()


@pytest.mark.parametrize('key,value',[('local_index',-1),('local_index',True),('local_index',99),
    ('local_index',3),('binder','outside'),('domain','Q → P'),('head','Bogus.lemma')])
def test_local_application_cannot_relabel_context(key,value):
    r=sample();r['frames'][-2][key]=value
    with pytest.raises(ValueError):Snapshot(r)


def test_non_application_may_not_smuggle_a_context_index():
    r=sample();r['frames'][-1]['local_index']=2
    with pytest.raises(ValueError):Snapshot(r)


def test_missing_index_is_not_guessed_from_a_similar_name():
    r=sample();del r['frames'][-2]['local_index']
    with pytest.raises(ValueError):Snapshot(r)


def test_legacy_unnamed_application_remains_unexpanded():
    r=sample();f=r['frames'][-2];f['role']='application'
    for k in ('binder','domain','local_index'):del f[k]
    d=Narrative(r).document()
    assert any(s.fallback for s in d.declarations[0].steps)
