"""Structural layout falsifiers; constructed records are NOT Lean observations."""
import copy
import json
from pathlib import Path
import pytest

from proofreader.core import make_name
from proofreader.english import English
from proofreader.kernel import Argument, Dag, InvalidExport, SCHEMA
from proofreader.layout import check_layout
from proofreader.model import Document, walk_steps


@pytest.fixture
def local_lambda():
    # forall P, ((P -> P) -> True) -> True, using f (fun h => h).
    # This closed constructor fixture is a printer/layout test, not a recorded
    # compiler run. The native suite separately exercises actual Lean exports.
    d=Dag([{'tag':'sort','level':{'tag':'zero'}}],[])
    prop=0
    true=d.add({'tag':'const','name':make_name('True'),'levels':[]})
    b=lambda n:d.add({'tag':'bvar','index':n})
    binder=lambda tag,n,domain,body:d.add({'tag':tag,'name':make_name(n),'domain':domain,'body':body,'binder':'explicit'})
    identity_type=binder('forall','h',b(0),b(1))
    function_type=binder('forall','k',identity_type,true)
    theorem_type=binder('forall','P',prop,binder('forall','f',function_type,true))
    identity=binder('lam','h',b(1),b(0))
    local_identity_type=binder('forall','h',b(1),b(2))
    application=d.add({'tag':'app','fn':b(0),'arg':identity})
    root=binder('lam','P',prop,binder('lam','f',function_type,application))
    def step(path,term,typ,children,arguments=None,**extra):
        return dict(path=path,term=term,type=typ,children=children,arguments=arguments or [],
                    is_proof=True,truncated=False,**extra)
    steps=[step([],root,theorem_type,[1],domain_is_prop=False),
           step([1],d.nodes[root]['body'],d.nodes[theorem_type]['body'],[2],domain_is_prop=True),
           step([1,1],application,true,[3],
                [dict(path=[1,1,1],term=identity,type=local_identity_type,is_proof=True,step=3)]),
           step([1,1,1],identity,local_identity_type,[4],domain_is_prop=True),
           step([1,1,1,1],b(0),b(2),[])]
    r=dict(schema=SCHEMA,name=make_name('LayoutFixture.local_lambda'),exprs=d.nodes,levels=[],
           type=theorem_type,term=root,steps=steps,axioms=[],lean_version='4.34.1')
    Argument(r)
    return r


def nested_reading(record):
    """Use the valid uncompressed layout for deliberate placement mutations.

    Current English already hoists the complete closed lambda with an explicit
    support link. Restore that lambda as a nested application argument so each
    falsifier can move precisely the intended scope boundary.
    """
    doc=English(record).document();d=doc.declarations[0]
    steps={s.id.rsplit(':s',1)[-1]:s for s in walk_steps(d.steps)}
    application,local=steps['2'],steps['3']
    application.children=[local];application.supports=[]
    d.steps=[application]
    check_layout(record,doc)
    return doc


def test_local_assumption_stays_inside_subargument(local_lambda):
    doc=English(local_lambda).document()
    result=check_layout(local_lambda,doc)
    assert result['selected_steps_accounted']==5
    assert not result['typing_checked_here'] and not result['english_formally_verified']
    local=next(s for s in walk_steps(doc.declarations[0].steps) if s.id.endswith(':s3'))
    assert [s.id.rsplit(':s',1)[-1] for s in local.children]==['4']


def test_hoisting_local_hypothesis_is_rejected_without_rendering_again(local_lambda):
    doc=nested_reading(local_lambda);d=doc.declarations[0]
    parent=d.steps[0];local=parent.children[0];body=local.children.pop()
    local.supports=[body.id]
    d.steps.insert(0,body)
    with pytest.raises(InvalidExport,match='Escaped original binder scope'):
        check_layout(local_lambda,doc)


def test_one_branch_cannot_become_a_global_parameter(local_lambda):
    doc=nested_reading(local_lambda);d=doc.declarations[0]
    local=d.steps[0].children[0]
    d.parameters.append(dict(source_step_id=local.id))
    with pytest.raises(InvalidExport,match='leading proof prefix'):
        check_layout(local_lambda,doc)


def test_deleted_subargument_is_not_implicitly_proved(local_lambda):
    doc=nested_reading(local_lambda);doc.declarations[0].steps[0].children=[]
    with pytest.raises(InvalidExport,match='omits'):
        check_layout(local_lambda,doc)


def test_future_support_cannot_discharge_missing_local_proof(local_lambda):
    doc=nested_reading(local_lambda);d=doc.declarations[0]
    root=d.steps[0];local=root.children.pop();root.supports=[local.id]
    d.steps.append(local)
    with pytest.raises(InvalidExport,match='earlier established'):
        check_layout(local_lambda,doc)


def test_closed_subargument_may_be_moved_earlier_with_explicit_link(local_lambda):
    doc=nested_reading(local_lambda);d=doc.declarations[0]
    root=d.steps[0];local=root.children.pop();root.supports=[local.id]
    d.steps.insert(0,local)
    assert check_layout(local_lambda,doc)['selected_steps_accounted']==5


def test_duplicate_ids_and_unknown_ids_are_rejected(local_lambda):
    for change in ('duplicate','unknown'):
        doc=English(local_lambda).document();d=doc.declarations[0]
        if change=='duplicate':d.steps.append(copy.deepcopy(d.steps[0]))
        else:d.steps[0].id='nonexistent'
        with pytest.raises(InvalidExport):check_layout(local_lambda,doc)


def test_scope_check_does_not_pretend_to_check_english_wording(local_lambda):
    doc=English(local_lambda).document();doc.declarations[0].steps[0].text='untrusted prose'
    # Wording is checked by deterministic regeneration; this independent pass
    # only checks the structural layout and must not claim otherwise.
    assert not check_layout(local_lambda,doc)['english_formally_verified']


def test_reordering_parent_parameters_fails(local_lambda):
    doc=English(local_lambda).document();doc.declarations[0].parameters.reverse()
    with pytest.raises(InvalidExport,match='leading proof prefix'):
        check_layout(local_lambda,doc)


@pytest.mark.parametrize('name',['and_swap','trans','injective_comp','witnessed','alternatives'])
def test_retained_real_exports_obey_layout(name):
    path=Path(__file__).parents[1]/f'artifacts/v0.2/{name}.kernel.json'
    record=json.loads(path.read_text())
    doc=English(record).document()
    result=check_layout(record,doc)
    assert result['selected_steps_accounted']==len(record['steps'])
