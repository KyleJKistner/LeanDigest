from pathlib import Path
import json
import pytest
from proofreader.finding_catalog import (PIN, build, digest, families, inline,
    load_statements, safe_child, upstream_url, config_inventory, verify_metadata)
from proofreader.catalog_audit import audit

def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value) if not isinstance(value,str) else value)

@pytest.fixture
def sample(tmp_path):
    u=tmp_path/'upstream';lean=u/'lean';stat=tmp_path/'statements';proof=tmp_path/'proofs';proof.mkdir()
    cfg={'challenge_module':'ComparatorChallenges.Sample','solution_module':'OAI.Algebra.Sample.Main',
         'theorem_names':['OAI.Sample.main'],'definition_names':['OAI.Sample.object']}
    write(u/'CONTENTS.md','**001. A sample result.** A result about $x$.\n\n[Paper](preprints/Sample/paper.pdf)\n\n**002. Another result.** Not formalized.\n')
    write(u/'LICENSE','Example public license')
    write(lean/'docs/001.md','# A sample result\n\n## Scope\nA partial result, not the entire paper.\n\n[Sample](../ComparatorChallenges/Sample.lean)\n')
    write(lean/'ComparatorChallenges/Sample.json',cfg)
    write(lean/'ComparatorChallenges/Sample.lean','-- comparison specification\n')
    write(lean/'OAI/Algebra/Sample/Main.lean','-- original theorem proof\n')
    records=[]
    for n in cfg['theorem_names']+cfg['definition_names']:
        records.append({'name':n,'status':'elaborated-specification','statement':{
            'name':n,'schema':'leanglish.finding-statement/v1','origin':'comparison-specification',
            'lean_version':'4.34.1','solution_proof_checked':False,
            'binders':[{'name':'P','type':'Prop','is_assumption':False,'is_instance':False}],
            'conclusion':'P → P','qualified_statement':'∀ (P : Prop), P → P'}})
    write(stat/'statements.json',{'schema':'leanglish.statement-shard/v1','upstream_commit':PIN,'configurations':[
        {'configuration':'Sample','solution_module':cfg['solution_module'],'status':'complete-statements-only',
         'challenge_sha256':digest((lean/'ComparatorChallenges/Sample.lean').read_bytes()),'targets':records}]})
    files=[p for p in u.rglob('*') if p.is_file()]
    entries=[{'path':p.relative_to(u).as_posix(),'sha256':digest(p.read_bytes())} for p in files]
    write(u/'acquisition.json',{'repository':'openai/math','commit':PIN,'fetched':entries})
    inv=tmp_path/'source-inventory.json';write(inv,[x for x in entries if x['path'].startswith('lean/')])
    return u,lean,stat,proof,inv

def test_complete_statement_access_is_not_proof_coverage(sample,tmp_path):
    u,l,s,p,i=sample;out=tmp_path/'site'
    r=build(u,l,[s],[p],out,source_inventory=i)
    assert r['findings']==2 and r['documented_findings']==1
    assert r['elaborated_statement_entries']==r['expected_statement_entries']==2
    assert r['expected_theorem_targets']==1 and r['definition_references']==1
    assert r['proof_readings']==0 and not r['all_theorem_readings_accessible']
    assert r['all_specification_entries_accessible']
    assert audit(out)['passed']
    assert 'specification is not a checked solution proof' in (out/'findings/001.html').read_text()
    assert not list(out.rglob('*.woff2'))

def test_missing_statement_does_not_shrink_denominator(sample,tmp_path):
    u,l,s,p,i=sample;(s/'statements.json').unlink()
    r=build(u,l,[s],[p],tmp_path/'site',source_inventory=i)
    assert r['expected_statement_entries']==2 and r['elaborated_statement_entries']==0
    assert not r['all_specification_entries_accessible']

@pytest.mark.parametrize('path',['../secret','/etc/passwd','a/../../secret','a\\..\\secret'])
def test_artifact_path_escape_rejected(tmp_path,path):
    with pytest.raises(ValueError):safe_child(tmp_path,path)

@pytest.mark.parametrize('url',['javascript:alert(1)','data:text/html,bad','http://bad','//example.org','../../../outside'])
def test_unsafe_upstream_links_rejected(url):
    with pytest.raises(ValueError):upstream_url(url,'lean/docs')

def test_safe_markdown_has_no_active_html():
    rendered=inline('<script>alert(1)</script> [bad](javascript:alert) $x$ `</code><img src=x onerror=x>`')
    assert '<script>' not in rendered and '<img' not in rendered
    assert 'href="javascript' not in rendered and 'data-tex="x"' in rendered

@pytest.mark.parametrize('relative',['lean/docs/001.md','CONTENTS.md','LICENSE'])
def test_altered_upstream_metadata_rejected(sample,relative):
    u,l,s,p,i=sample;(u/relative).write_text('changed')
    with pytest.raises(ValueError):verify_metadata(u,l,i)

def test_removed_scope_note_rejected(sample):
    u,l,s,p,i=sample;(l/'docs/001.md').unlink()
    with pytest.raises(ValueError,match='inventory is incomplete'):verify_metadata(u,l,i)

def test_removed_comparison_config_rejected(sample):
    u,l,s,p,i=sample;(l/'ComparatorChallenges/Sample.json').unlink()
    with pytest.raises(ValueError,match='universe is incomplete'):verify_metadata(u,l,i)

def test_foreign_statement_pin_rejected(sample):
    u,l,s,p,i=sample;r=json.loads((s/'statements.json').read_text());r['upstream_commit']='0'*40;write(s/'statements.json',r)
    with pytest.raises(ValueError):load_statements([s],config_inventory(l),l)

def test_conflicting_successful_statements_rejected(sample,tmp_path):
    u,l,s,p,i=sample;other=tmp_path/'other';r=json.loads((s/'statements.json').read_text())
    r['configurations'][0]['targets'][0]['statement']['conclusion']='False';write(other/'statements.json',r)
    with pytest.raises(ValueError,match='Conflicting'):load_statements([s,other],config_inventory(l),l)

def test_missing_statement_target_rejected(sample):
    u,l,s,p,i=sample;r=json.loads((s/'statements.json').read_text());r['configurations'][0]['targets'].pop();write(s/'statements.json',r)
    with pytest.raises(ValueError,match='Incomplete'):load_statements([s],config_inventory(l),l)

def test_placeholder_specification_cannot_claim_proof_check(sample):
    u,l,s,p,i=sample;r=json.loads((s/'statements.json').read_text());r['configurations'][0]['targets'][0]['statement']['solution_proof_checked']=True;write(s/'statements.json',r)
    with pytest.raises(ValueError,match='Invalid specification evidence'):load_statements([s],config_inventory(l),l)

def test_changed_solution_source_rejected(sample,tmp_path):
    u,l,s,p,i=sample;(l/'OAI/Algebra/Sample/Main.lean').write_text('changed')
    with pytest.raises(ValueError,match='Unverified original source'):build(u,l,[s],[p],tmp_path/'site',source_inventory=i)

def test_existing_output_is_not_overwritten(sample,tmp_path):
    u,l,s,p,i=sample;out=tmp_path/'site';out.mkdir();write(out/'keep','keep')
    with pytest.raises(ValueError):build(u,l,[s],[p],out)
    assert (out/'keep').read_text()=='keep'

def test_broken_link_audit(sample,tmp_path):
    u,l,s,p,i=sample;out=tmp_path/'site';build(u,l,[s],[p],out,source_inventory=i)
    (out/'findings/001.html').write_text((out/'findings/001.html').read_text()+'<a href="../missing.html">bad</a>')
    assert not audit(out)['passed']


def test_math_in_link_labels_is_rendered_and_remains_safe():
    result=inline('[A bound on $x^2$](preprints/Test/main.pdf)')
    assert 'data-tex="x^2"' in result and '<a ' in result
    result=inline('[<img onerror=x src=x>](preprints/Test/main.pdf)')
    assert '<img' not in result


def test_catalog_filter_options_are_distinct(sample,tmp_path):
    from html.parser import HTMLParser
    class Options(HTMLParser):
        def __init__(self):super().__init__();self.options=[]
        def handle_starttag(self,tag,attrs):
            if tag=='option':self.options.append(dict(attrs).get('value'))
    u,l,s,p,i=sample;out=tmp_path/'site';build(u,l,[s],[p],out,source_inventory=i)
    parser=Options();parser.feed((out/'index.html').read_text())
    assert all(parser.options.count(x)==1 for x in ['documented','readings','all'])


def test_catalog_cli_builds_without_executing_lean(sample,tmp_path,monkeypatch):
    from leanglish.cli import main
    import subprocess
    def fail(*args,**kwargs):raise AssertionError('The reading builder must not execute source')
    monkeypatch.setattr(subprocess,'run',fail)
    u,l,s,p,i=sample;out=tmp_path/'site'
    assert main(['catalog','--upstream',str(u),'--lean',str(l),'--statements',str(s),
                 '--proofs',str(p),'--source-inventory',str(i),'-o',str(out)])==0
    assert main(['audit-catalog',str(out)])==0


@pytest.fixture
def synthetic_proof(sample):
    """Synthetic consistency-check fixture, never a native observation/demo."""
    from proofreader.narrative import Snapshot
    from proofreader.model import canonical_json
    from hashlib import sha256
    u,l,s,p,i=sample
    name='OAI.Sample.main';module='OAI.Algebra.Sample.Main'
    ident=sha256((module+'\0'+name).encode()).hexdigest()[:24]
    directory=p/'targets'/ident
    record={'schema':'proofreader.narrative/v1','theorem':name,'lean_version':'4.34.1',
      'axioms':[],'statement':'True','judgements_checked':1,'formula_backend':'Lean pretty-printer',
      'frames':[{'id':0,'path':[],'statement':'True','role':'named','head':'True.intro',
          'context':[],'children':[],'premises':[],'objects':[],'budget_cut':False}]}
    snapshot=Snapshot(record)
    driver='-- synthetic consistency fixture, not executed\n'
    stdout='PR_NARRATIVE:'+canonical_json(record)+'\n'
    receipt={'status':'passed','schema':'proofreader.narrative-receipt/v1','theorem':name,'module':module,
        'lean_version':'4.34.1','selected_judgements':1,'backend':'native',
        'all_selected_judgements_kernel_checked':True,'path_linkage_checked_in_lean':True,
        'snapshot_sha256':snapshot.sha256,'source_sha256':digest(driver.encode())}
    write(directory/'Extract.lean',driver);write(directory/'snapshot.json',record)
    write(directory/'stdout.txt',stdout);write(directory/'receipt.json',receipt)
    write(directory/'run.json',{'status':'passed','exit_code':0,'stdout':stdout})
    row={'id':ident,'module':module,'name':name,'kind':'theorem','status':'reading-generated',
      'directory':'targets/'+ident,'kernel_checked':True,'snapshot_sha256':snapshot.sha256,
      'selected_judgements':1,'source_sha256':digest((l/(module.replace('.','/')+'.lean')).read_bytes())}
    write(p/'proofs.json',{'schema':'leanglish.finding-proof-shard/v1','upstream_commit':PIN,
                           'expected_targets':1,'targets':[row]})
    return directory


def test_proof_artifact_consistency_fixture(sample,synthetic_proof):
    from proofreader.finding_catalog import load_proofs
    u,l,s,p,i=sample
    chosen,attempts=load_proofs([p],config_inventory(l),l)
    assert len(chosen)==len(attempts)==1


@pytest.mark.parametrize('field,value', [('id','../../escape'),('directory','../escape'),
    ('snapshot_sha256','0'*64),('selected_judgements',2),('source_sha256','0'*64),
    ('kernel_checked',False),('kind','definition')])
def test_proof_queue_tampering_rejected(sample,synthetic_proof,field,value):
    from proofreader.finding_catalog import load_proofs
    u,l,s,p,i=sample;r=json.loads((p/'proofs.json').read_text())
    r['targets'][0][field]=value;write(p/'proofs.json',r)
    with pytest.raises(ValueError):load_proofs([p],config_inventory(l),l)


@pytest.mark.parametrize('field,value', [('source_sha256','0'*64),('selected_judgements',2),
    ('path_linkage_checked_in_lean',False),('status','failed'),('lean_version','4.34.0')])
def test_receipt_inconsistency_rejected(sample,synthetic_proof,field,value):
    from proofreader.finding_catalog import load_proofs
    u,l,s,p,i=sample;r=json.loads((synthetic_proof/'receipt.json').read_text())
    r[field]=value;write(synthetic_proof/'receipt.json',r)
    with pytest.raises(ValueError):load_proofs([p],config_inventory(l),l)


def test_failed_native_execution_cannot_supply_reading(sample,synthetic_proof):
    from proofreader.finding_catalog import load_proofs
    u,l,s,p,i=sample;r=json.loads((synthetic_proof/'run.json').read_text())
    r['exit_code']=1;write(synthetic_proof/'run.json',r)
    with pytest.raises(ValueError):load_proofs([p],config_inventory(l),l)


def test_proof_artifact_symlink_escape_rejected(sample,synthetic_proof,tmp_path):
    from proofreader.finding_catalog import load_proofs
    u,l,s,p,i=sample;f=synthetic_proof/'Extract.lean';outside=tmp_path/'outside.lean'
    outside.write_bytes(f.read_bytes());f.unlink();f.symlink_to(outside)
    with pytest.raises(ValueError):load_proofs([p],config_inventory(l),l)


def test_modified_saved_compiler_output_rejected(sample,synthetic_proof):
    from proofreader.finding_catalog import load_proofs
    u,l,s,p,i=sample;(synthetic_proof/'stdout.txt').write_text('No proof record')
    with pytest.raises(ValueError):load_proofs([p],config_inventory(l),l)
