from pathlib import Path
from dataclasses import asdict
import copy, json, os, subprocess, sys
import pytest
from proofreader.narrative import Snapshot,Narrative,check_reading,prose,reading_binding,math_text
from proofreader.model import canonical_json,digest,walk_steps,report
from proofreader.kernel import InvalidExport
from proofreader.render import load_document,html_document,markdown_document
from proofreader.polynomial import certify,verify,UnsupportedPolynomial,parse,equality,encode,decode,scalar_context,assumptions
from proofreader.narrative_io import verify_certificates

ROOT=Path(__file__).parents[1]
RECORD=ROOT/'artifacts/v0.3/bezout.narrative.json'
@pytest.fixture
def record():return json.loads(RECORD.read_text())
@pytest.fixture
def reading(record):return Narrative(record).document(source='source retained separately')


def test_live_snapshot_content_address(record):
    assert digest(canonical_json(record))=='dad8ef23a231904f37b73979f8284ea3662ffe8f8cd30c79066856f2095b4dd7'
    s=Snapshot(record)
    assert s.coverage()['frames']==86 and s.coverage()['budget_cuts']==0
    assert record['lean_version']=='4.34.1'
    assert set(record['axioms'])=={'propext','Classical.choice','Quot.sound'}


def test_all_frames_and_arithmetic_retained(record,reading):
    n=Narrative(record);d=n.document()
    assert set(n.owners)==set(range(86))
    assert len(set(s.id for s in walk_steps(d.declarations[0].steps)))==59
    assert not any(s.fallback for s in walk_steps(d.declarations[0].steps))
    assert len(n.certificates)==16
    assert report(d)['checked_english_proofs']==0
    assert report(d)['successful_local_lean_receipts']==0


def test_two_cases_and_witness_construction(reading):
    text=prose(reading)
    for expected in ['Let R be a Euclidean domain.','Let x, y, z be elements of R.',
                     'Case g = 0.','Case g ≠ 0.','(1, y, 0, 1)',
                     '(a, d, g, r · (z + 1) + s · y)','a · r + d · s = 1',
                     'a · y = d · (z + 1)','Verify the 4 required conclusions.']:
        assert expected in text
    assert 'ring\n' not in text


def test_repeat_and_cross_process_determinism(record):
    a=Narrative(record).document().to_json()
    assert a==Narrative(record).document().to_json()
    code="from proofreader.narrative import Snapshot,Narrative; print(Narrative(Snapshot.read('artifacts/v0.3/bezout.narrative.json').record).document().to_json(),end='')"
    for seed in ['1','382']:
        result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env={**os.environ,'PYTHONHASHSEED':seed},capture_output=True,text=True,check=True)
        assert result.stdout==a


@pytest.mark.parametrize('path,value',[
    (('schema',),'unknown'),(('axioms',),['sorryAx']), (('axioms',),['propext','propext']),
    (('lean_version',),'4.34'), (('lean_version',),None), (('judgements_checked',),85),
    (('judgements_checked',),True), (('statement',),'False'),
    (('frames',0,'path'),[1]), (('frames',2,'path'),[1]),
    (('frames',0,'children'),[0]), (('frames',0,'children'),[[1]]),
    (('frames',0,'children'),[1,1]), (('frames',1,'id'),3),
    (('frames',1,'context'),[]), (('frames',1,'context',0,'type'),'Prop'),
    (('frames',13,'role'),'combine'), (('frames',47,'role'),'named'),
    (('frames',1,'role'),[]), (('frames',1,'budget_cut'),1),
    (('frames',1,'context',0,'evil'),1), (('frames',0,'path'),[False]),
    (('frames',47,'children'),[48]), (('frames',13,'premises',0,'statement'),'False'),
    (('formula_backend',),'trusted-LLM'), (('frames',0,'unknown'),True)
])
def test_malformed_snapshot_rejected(record,path,value):
    ref=record
    for key in path[:-1]:ref=ref[key]
    ref[path[-1]]=value
    with pytest.raises(InvalidExport):Snapshot(record)


@pytest.mark.parametrize('field', ['text','conclusion','source','rule','context','term_id','fallback','detail'])
def test_changed_display_math_rejected(record,reading,field):
    s=reading.declarations[0].steps[0]
    replacement={'text':'Choose 0 = 1.','conclusion':'False','source':'Fake proof','rule':'invented',
       'context':[],'term_id':'f99','fallback':True,'detail':'Replacement justification'}[field]
    if getattr(s,field)==replacement:replacement=[{'name':'fake','type':'False'}]
    setattr(s,field,replacement)
    with pytest.raises(InvalidExport):check_reading(record,reading)


def test_cannot_delete_or_add_inferences(record,reading):
    reading.declarations[0].steps.pop()
    with pytest.raises(InvalidExport):check_reading(record,reading)


def test_mismatched_receipt_rejected(record):
    with pytest.raises(InvalidExport):Narrative(record).document(receipt={'snapshot_sha256':'0'*64})


def test_prose_and_markdown_keep_calculation_conclusions(reading):
    md=markdown_document(reading)
    for step in walk_steps(reading.declarations[0].steps):
        if step.conclusion:assert step.conclusion in md


def test_all_arithmetic_passes_and_every_coeff_tamper_rejected(record):
    n=Narrative(record)
    for i,cert in n.certificates.items():
        verify(n.frames[i],cert)
        corrupt=copy.deepcopy(cert)
        corrupt['goal']='0 = 1'
        with pytest.raises(UnsupportedPolynomial):verify(n.frames[i],corrupt)
        if cert['multipliers']:
            corrupt=copy.deepcopy(cert)
            corrupt['multipliers'][0][0][1]+=1
            with pytest.raises(UnsupportedPolynomial):verify(n.frames[i],corrupt)


def frame(goal,extra=(),ring='CommRing R'):
    return {'id':0,'statement':goal,'context':[{'name':'R','type':'Type'}, {'name':'inst','type':ring},
      *[{'name':x,'type':'R'} for x in ['x','y','z']],
      *[{'name':'h'+str(i),'type':h} for i,h in enumerate(extra)]]}


@pytest.mark.parametrize('premise',['P → x = 0 ∧ y = 0','¬(x = 0 ∧ y = 0)',
                                  '(P → x = 0) ∧ y = 0','∀ z, x = 0 ∧ y = 0','x = 0 ∨ y = 0'])
def test_conditional_assumptions_cannot_leak(premise):
    assert certify(frame('y = 0',[premise])) is None


def test_never_cancel_nonunit_integer_in_arbitrary_ring():
    assert certify(frame('x = 0',['2*x = 0'])) is None
    assert certify(frame('2*x = 0',['x = 0'])) is not None


def test_scope_shadowing_drops_old_assumption():
    f=frame('x = 0',['x = 0'])
    assert certify(f)
    f['context'].append({'name':'h0','type':'True'})
    assert certify(f) is None


@pytest.mark.parametrize('ring',['NoncommRing R','P → CommRing R','Fake.CommRing R','CommRing S'])
def test_no_fake_commutativity(ring):
    assert certify(frame('x*y = y*x',ring=ring)) is None


@pytest.mark.parametrize('expression',['x / x','unknown + 1','x**2','x^1000','__import__(x)','x; print(1)','x → y','x (y)','x^(-1)'])
def test_restricted_polynomial_parser(expression):
    with pytest.raises(UnsupportedPolynomial):parse(expression,{'x','y'})


def test_exact_polynomial_replay_is_independent_of_solver(monkeypatch,record):
    import proofreader.polynomial as p
    n=Narrative(record)
    monkeypatch.setattr(p,'solve',lambda *a,**k: (_ for _ in ()).throw(AssertionError('Solver invoked in checker')))
    for i,c in n.certificates.items():verify(n.frames[i],c)


def test_polynomial_certificate_refs_and_names_bound(record):
    n=Narrative(record);i=47;c=copy.deepcopy(n.certificates[i])
    c['assumptions'][0]['context_index']=0
    with pytest.raises(UnsupportedPolynomial):verify(n.frames[i],c)
    c=copy.deepcopy(n.certificates[i]);c['assumptions'][0]['name']='pretend'
    with pytest.raises(UnsupportedPolynomial):verify(n.frames[i],c)
    c=copy.deepcopy(n.certificates[i]);c['multipliers'][0][0][1]=True
    with pytest.raises(UnsupportedPolynomial):verify(n.frames[i],c)


def test_duplicate_certificate_not_counted(record):
    c=next(iter(Narrative(record).certificates.values()))
    with pytest.raises(InvalidExport):verify_certificates(record,[c,c])


def test_unsupported_frontier_honest(record):
    # Unsupported compound notation does not become an invented identity.
    record['frames'][47]['statement']='f (g + 1) = 0'
    parent=record['frames'][46]
    for p in parent['premises']:
        if p['frame']==47:p['statement']=record['frames'][47]['statement']
    n=Narrative(record);d=n.document()
    assert 47 not in n.certificates
    assert any(s.fallback for s in walk_steps(d.declarations[0].steps))


def test_snapshot_is_not_an_authentication_check(record):
    n=Narrative(record);d=n.document(receipt={'snapshot_sha256':n.snapshot.sha256,'status':'passed'})
    check_reading(record,d)
    assert d.provenance['receipt_authenticated'] is False
    assert d.provenance['source_replayed_by_rendering'] is False


def test_unknown_theorem_not_mislabeled_openai(record):
    record['theorem']='Other.test'
    d=Narrative(record).document()
    assert d.title=='Lean ProofReader · test'
    assert not any('OpenAI' in w for w in d.declarations[0].warnings)


def test_json_roundtrip_and_frozen_input(record,reading):
    before=copy.deepcopy(record); n=Narrative(record)
    d=n.document();check_reading(record,load_document(d.to_json()))
    assert record==before


def test_xss_in_snapshot_stays_escaped(record):
    attack='</script><script>globalThis.PWNED=1</script>'
    record['frames'][6]['value']=attack
    d=Narrative(record).document()
    h=html_document(d)
    assert attack not in h
    assert '\\u003c/script\\u003e' in h
