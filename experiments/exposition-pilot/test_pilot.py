"""Structural and evidence-accounting tests; not proofs of English fidelity."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import pytest

HERE=Path(__file__).resolve().parent

def load(name):
 spec=importlib.util.spec_from_file_location('pilot_'+name,HERE/(name+'.py'))
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

BUILD=load('build');RUN=load('run')

@pytest.fixture
def evidence(tmp_path):
 path=os.environ.get('EXPOSITION_PILOT_EVIDENCE')
 assert path, 'Set EXPOSITION_PILOT_EVIDENCE to a completed native run or reconciled evidence folder'
 target=tmp_path/'evidence';shutil.copytree(path,target);return target

def test_sample_is_three_proofs_not_fifteen_theorems():
 selection=json.loads((HERE/'selection.json').read_text())
 specs=json.loads((HERE/'candidates.json').read_text())
 assert len(selection['targets'])==3
 assert sum(r['kind']=='candidate' for r in specs)==15
 assert sum(r['kind']=='control' for r in specs)==6
 assert {r['target'] for r in specs}=={r['name'] for r in selection['targets']}
 assert len({r['id'] for r in specs})==len(specs)

@pytest.mark.parametrize('a,b', [('x y','xy'),('x\ny','xy'),('x\t y','xy')])
def test_size_ignores_whitespace_only(a,b):
 wrap=lambda s:'namespace PilotCandidate\n'+s+'\nend PilotCandidate'
 assert RUN.compact_size(wrap(a))==RUN.compact_size(wrap(b))

def test_size_counts_new_helpers():
 wrap=lambda s:'namespace PilotCandidate\n'+s+'\nend PilotCandidate'
 assert RUN.compact_size(wrap('theorem helper := proof\ntheorem result := helper'))>RUN.compact_size(wrap('theorem result := helper'))

def test_page_repeats_and_does_not_include_runtime_fonts(evidence,tmp_path):
 a=tmp_path/'a.html';b=tmp_path/'b.html'
 BUILD.build(evidence,a);BUILD.build(evidence,b)
 assert a.read_bytes()==b.read_bytes()
 assert 'font/woff' not in a.read_text() and '@font-face' not in a.read_text()
 assert 'english_certified' in a.with_suffix('.manifest.json').read_text()

@pytest.mark.parametrize('field,value', [
 ('expected','List.append_assoc'),('english_certified',True),
 ('target_in_dependency_closure',True),('same_statement_kernel_checked',False),
 ('lean_version','4.35.0'),
])
def test_invalid_native_contract_rejects_even_with_updated_hash(evidence,tmp_path,field,value):
 id='bezout_explanatory_v3';p=evidence/id/'accepted.json';r=json.loads(p.read_text());r[field]=value;p.write_text(json.dumps(r))
 op=evidence/id/'outcome.json';o=json.loads(op.read_text());o['record_sha256']=BUILD.digest(p.read_bytes());op.write_text(json.dumps(o))
 with pytest.raises(ValueError,match='Wrong native check'):BUILD.build(evidence,tmp_path/'bad.html')

def test_missing_record_does_not_render(evidence,tmp_path):
 (evidence/'cantor_explanatory'/'accepted.json').unlink()
 with pytest.raises(FileNotFoundError):BUILD.build(evidence,tmp_path/'bad.html')

def test_changed_record_rejected(evidence,tmp_path):
 p=evidence/'reverse_indexed'/'accepted.json';p.write_text(p.read_text()+' ')
 with pytest.raises(ValueError,match='Source/check record mismatch'):BUILD.build(evidence,tmp_path/'bad.html')

def test_missing_explanatory_lemma_rejected(evidence,tmp_path):
 id='bezout_explanatory_v3';p=evidence/id/'accepted.json';r=json.loads(p.read_text());r['facts']=[f for f in r['facts'] if f['name']!='PilotCandidate.forcedSolution'];p.write_text(json.dumps(r))
 op=evidence/id/'outcome.json';o=json.loads(op.read_text());o['record_sha256']=BUILD.digest(p.read_bytes());op.write_text(json.dumps(o))
 with pytest.raises(ValueError,match='Missing or ambiguous formal reference'):BUILD.build(evidence,tmp_path/'bad.html')

def test_failed_candidate_cannot_be_selected(evidence,tmp_path):
 p=evidence/'cantor_original'/'outcome.json';r=json.loads(p.read_text());r['accepted']=False;p.write_text(json.dumps(r))
 with pytest.raises(ValueError,match='Source/check record mismatch'):BUILD.build(evidence,tmp_path/'bad.html')

def test_original_source_is_frozen():
 selection=json.loads((HERE/'selection.json').read_text())
 original=HERE.parents[1]/'proofreader/data/bezout-original.lean'
 assert BUILD.digest(original.read_bytes())==selection['targets'][0]['source_sha256']

def test_notes_do_not_claim_certification():
 b=json.loads((HERE/'book.json').read_text());assert b['english_certified'] is False
 assert len({a['id'] for a in b['articles']})==3
 assert {a['chosen'] for a in b['articles']}=={'bezout_explanatory_v3','reverse_indexed','cantor_explanatory'}


def test_mathml_tokens_cannot_contain_other_tokens():
 with pytest.raises(ValueError,match='nested MathML token'):
  BUILD.validate_mathml('<math><mo><mo>+</mo><mo>+</mo></mo></math>')


def test_single_token_concatenation_notation_is_allowed():
 BUILD.validate_mathml('<math xmlns="http://www.w3.org/1998/Math/MathML"><mrow><mi>X</mi><mo>∥</mo><mi>Y</mi></mrow></math>')
