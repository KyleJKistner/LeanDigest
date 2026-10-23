"""Pilot regression tests. Native evidence is an explicit input; no fake compiler."""
from pathlib import Path
import importlib.util,json,os,subprocess,sys
import pytest
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pilot_build',ROOT/'build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
OBS=Path(os.environ['PILOT_OBSERVATION'])
REPEAT=Path(os.environ['PILOT_REPEAT'])
PAGE=Path(os.environ['PILOT_HTML'])
r=json.loads(OBS.read_text());repeated=json.loads(REPEAT.read_text())

@pytest.mark.parametrize('target',['bezout','cantor','reverse'])
def test_all_variants_native_checked(target):
    rows=[x for x in r['candidates'] if x['target']==target and x['expected']=='accept']
    assert {x['variant'] for x in rows}=={'original','short','structured'}
    for row in rows:
        assert row['accepted'] and row['audit']['kernel_checked']
        assert set(row['audit']['axioms'])<={'propext','Classical.choice','Quot.sound'}
        assert row['audit']['english_certified'] is False

@pytest.mark.parametrize('id',[x['id'] for x in r['candidates'] if x['expected']=='reject'])
def test_intended_negative_outcome(id):
    row=next(x for x in r['candidates'] if x['id']==id)
    assert row['exit_code']!=0 and not row['accepted']
    assert row['intended_rejection'] and row['expected_outcome']

def test_repeat_native_records_match():
    assert r['status']==repeated['status']=='passed'
    assert len(r['candidates'])==len(repeated['candidates'])==16
    for a,b in zip(r['candidates'],repeated['candidates']):
        assert a['id']==b['id'] and a['source_sha256']==b['source_sha256']
        assert a.get('audit')==b.get('audit')

def test_lean_and_driver_inputs_unchanged():
    import hashlib
    for name,want in r['input_sha256'].items():
        if name.endswith('.lean') or name in {'candidates.json','run.py'}:
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==want

def test_rebuild_is_identical(tmp_path):
    first=tmp_path/'one.html';second=tmp_path/'two.html'
    assert build.build(OBS,first)==build.build(OBS,second)
    assert first.read_bytes()==second.read_bytes()==PAGE.read_bytes()

@pytest.mark.parametrize('change',[lambda x:x.update(status='failed'),
    lambda x:x.update(english_certified=True),
    lambda x:x['candidates'].pop(0),
    lambda x:x['candidates'][0]['audit'].update(kernel_checked=False)])
def test_build_rejects_incomplete_evidence(tmp_path,change):
    value=json.loads(OBS.read_text());change(value);p=tmp_path/'bad.json';p.write_text(json.dumps(value))
    with pytest.raises(ValueError):build.build(p,tmp_path/'page.html')

def test_math_boundaries_and_script_arrays_preserved():
    html=PAGE.read_text();soup=BeautifulSoup(html,'html.parser')
    assert not any('[[' in str(x) for x in soup.select('article'))
    assert '[[\'Lean proofs\'' in html # JS arrays must not be converted to MathML.
    labels=[m['aria-label'] for m in soup.select('math')]
    assert 'rev((a::L)⧺M)' in labels
    assert ' =rev(L⧺M)⧺[a]' in labels
    assert 'D={x∈X:x∉f(x)}.' in labels

def test_runtime_consent(tmp_path):
    p=subprocess.run([sys.executable,str(ROOT/'run.py'),'--project','missing','--output',str(tmp_path/'none')],capture_output=True,text=True)
    assert p.returncode!=0 and '--trust-project' in p.stderr
    assert not (tmp_path/'none').exists()

@pytest.fixture(scope='module')
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=os.environ.get('PILOT_CHROMIUM','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
        yield b;b.close()

@pytest.fixture
def page(browser):
    p=browser.new_page(viewport={'width':1280,'height':900})
    errors=[];requests=[]
    p.on('pageerror',lambda e:errors.append(str(e)))
    p.on('request',lambda e:requests.append(e.url) if e.url.startswith(('http:','https:')) else None)
    # Explicit memory mode: not file-navigation acceptance.
    p.set_content(PAGE.read_text())
    yield p
    assert not errors and not requests
    p.close()

@pytest.mark.parametrize('id',['bezout','cantor','reverse'])
def test_tabs_and_mobile(page,id):
    page.locator('[data-tab='+id+']').click()
    assert page.locator('article:visible').get_attribute('id')==id
    assert page.locator('[data-tab='+id+']').get_attribute('aria-current')=='true'
    page.set_viewport_size({'width':390,'height':844})
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')

@pytest.mark.parametrize('x,y,z',[(6,2,3),(0,5,0),(-6,-2,3),(2,3,2),(0,4,-1),(1,0,0),(0,0,0)])
def test_integer_constructions(page,x,y,z):
    for name,value in zip('xyz',[x,y,z]):page.locator('#'+name).fill(str(value))
    page.locator('#construct').click()
    assert page.locator('#bezout-result').get_attribute('data-valid')=='true'
    a,d,b,c=map(int,page.locator('#bezout-result').get_attribute('data-frame').split(','))
    assert (a*b,d*c,d*b,a*c-d*b)==(x,y,z,1)

@pytest.mark.parametrize('values',[('1','1','1'),('x','2','3'),('9'*61,'0','0'),('1.5','2','3')])
def test_invalid_integer_input(page,values):
    for name,value in zip('xyz',values):page.locator('#'+name).fill(value)
    page.locator('#construct').click()
    assert page.locator('#bezout-result').get_attribute('data-valid')=='false'
    assert page.locator('#bezout-result').get_attribute('data-frame') is None

def test_diagonal_differs_after_each_edit(page):
    page.locator('[data-tab=cantor]').click()
    for i in range(4):
        for j in range(4):
            page.locator(f'#matrix button[data-row="{i}"][data-col="{j}"]').click()
            diag=list(map(int,page.locator('#matrix').get_attribute('data-diagonal')))
            for k in range(4):
                row=[int(page.locator(f'#matrix button[data-row="{k}"][data-col="{m}"]').text_content()) for m in range(4)]
                assert diag[k]!=row[k] and diag!=row

def test_linked_native_signatures_match(page):
    for id in ['bezout','cantor','reverse']:
        page.locator('[data-tab='+id+']').click()
        for element in page.locator('#'+id+' [data-native]').all():
            cid,names=element.get_attribute('data-native').split(':')
            a=next(x['audit'] for x in r['candidates'] if x['id']==cid)
            want=[next(c['statement'] for c in a['claims'] if c['name']==n) for n in names.split(',')]
            assert element.locator('pre').all_text_contents()==want

def test_math_details_and_comparison_work(page):
    page.locator('#compatible-detail > summary').click()
    assert page.locator('#compatible-detail').get_attribute('open') is not None
    page.locator('#bezout .comparison > details > summary').click()
    assert page.locator('#bezout .comparison details').count()==4
    assert 'theorem compatible' in page.locator('#bezout .comparison').text_content()

def test_reverse_examples_escape_text(page):
    page.locator('[data-tab=reverse]').click();page.locator('#reverse-input').fill('a,<img src=x onerror=alert(1)>,c')
    page.locator('#reverse-button').click()
    assert page.locator('#reverse-result img').count()==0
    assert '<img' in page.locator('#reverse-result').text_content()

def test_print_retains_all_proofs_and_lemma_proofs(page):
    page.evaluate('preparePrint()')
    assert page.locator('article:visible').count()==3
    assert page.locator('.math-details:not([open])').count()==0
