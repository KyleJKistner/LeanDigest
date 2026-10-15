"""Synthetic format/renderer contracts, not observed Lean proof certificates."""
import pytest
from proofreader.narrative import Snapshot,Narrative
from proofreader.model import walk_steps


def frame(i,path,role,head,statement='0 = 0',children=None,objects=None):
    return dict(id=i,path=path,role=role,head=head,statement=statement,
                children=children or [],objects=objects or [],context=[],premises=[],budget_cut=False)


def record(frames):
    return dict(schema='proofreader.narrative/v1',theorem='Synthetic.contract',lean_version='4.34.1',
                statement=frames[0]['statement'],axioms=[],frames=frames,judgements_checked=len(frames),
                formula_backend='Lean pretty-printer')


def specialized():
    return record([frame(0,[],'specialize','Nat.rec',children=[1],objects=['0']),
                   frame(1,[0],'induction','Nat.rec',statement='∀ z : Nat, 0 = 0')])


@pytest.mark.parametrize('mutation',[
    lambda r:r['frames'][1].update(path=[1]),
    lambda r:r['frames'][0].update(objects=[]),
    lambda r:r['frames'][0].update(children=[]),
    lambda r:r['frames'][0].update(head='Unknown.rec'),
])
def test_specialization_requires_its_original_proof_prefix(mutation):
    r=specialized();mutation(r)
    with pytest.raises(ValueError):Snapshot(r)


def test_unexpanded_prefix_is_not_hidden_by_specialization():
    d=Narrative(specialized()).document()
    assert any(s.fallback for s in walk_steps(d.declarations[0].steps))
    assert d.declarations[0].steps[0].text.startswith('Use the intermediate claim')


@pytest.mark.parametrize('role,gap',[('application',True),('reflexivity',False)])
def test_legacy_rfl_application_and_new_reflexivity_are_readable(role,gap):
    r=record([frame(0,[],role,'rfl',objects=['Nat','0'])])
    d=Narrative(r).document()
    assert d.declarations[0].steps[0].fallback is gap
    assert d.provenance['english_formally_verified'] is False
