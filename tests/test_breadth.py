"""Inventory-only fixtures: no invented successful native proof observation."""
from hashlib import sha256
import copy,json
import pytest
from proofreader.breadth import validate_shards,partition
from proofreader.catalog_inputs import PIN

@pytest.fixture
def case():
    universe={(f'OAI.Test.M{i}',f'Test.p{i}') for i in range(7)}
    baseline={('OAI.Test.M0','Test.p0')}
    selection=[dict(module=m,name=n) for m,n in sorted(universe-baseline)]
    reports=[]
    for s in range(3):
        rows=[dict(x,id=sha256((x['module']+'\0'+x['name']).encode()).hexdigest()[:24],kind='theorem',
                   status='deadline-not-attempted',kernel_checked=False)
              for x in selection if partition(x['module'],3)==s]
        reports.append(dict(schema='leanglish.finding-proof-shard/v1',upstream_commit=PIN,
            shard=s,shards=3,selection_count=6,selection_sha256=sha256(json.dumps(selection,sort_keys=True).encode()).hexdigest(),
            expected_targets=len(rows),expected_theorems=len(rows),targets=rows,
            kernel_checked=0,readers_written=0,pending=0))
    return selection,universe,baseline,reports

def run(c):return validate_shards(*c,shards=3)

def test_complete_reports_do_not_mean_complete_readings(case):
    r=run(case)
    assert r['expected_theorem_targets']==7 and r['selected_targets']==6
    assert r['all_shard_reports_retained'] and r['recorded_new_readings']==0
    assert not r['receipts_consistency_checked']

def test_missing_report_does_not_reduce_denominator(case):
    selection,u,b,reports=case
    removed=next(x for x in reports if x['targets'])
    remaining=[x for x in reports if x is not removed]
    r=validate_shards(selection,u,b,remaining,shards=3)
    assert r['expected_theorem_targets']==7 and r['selected_targets']==6
    assert r['targets_without_report']==len(removed['targets'])
    assert r['missing_report_shards']==[removed['shard']]
    assert sum(r['statuses'].values())==6

def test_incomplete_selection_rejected(case):
    selection,u,b,reports=case
    with pytest.raises(ValueError,match='complement'):validate_shards(selection[:-1],u,b,reports,3)

@pytest.mark.parametrize('edit',[
 lambda r:r.update(upstream_commit='0'*40),
 lambda r:r.update(shards=64),
 lambda r:r.update(shard=True),
 lambda r:r.update(expected_targets=999),
 lambda r:r.update(selection_count=5),
 lambda r:r.update(selection_sha256='0'*64),
 lambda r:r.update(kernel_checked=1),
 lambda r:r.update(pending=True),
 lambda r:r['targets'].pop(),
 lambda r:r['targets'][0].update(kernel_checked=True),
 lambda r:r['targets'][0].update(status='verified-English'),
 lambda r:r['targets'][0].update(id='wrong'),
 lambda r:r['targets'][0].update(name='Foreign.theorem'),
 lambda r:r['targets'][0].update(kind='definition'),
])
def test_invalid_shard_claims_rejected(case,edit):
    r=next(x for x in case[3] if x['targets']);edit(r)
    with pytest.raises(ValueError):run(case)

def test_duplicate_shard_rejected(case):
    case[3].append(copy.deepcopy(case[3][0]))
    with pytest.raises(ValueError,match='Duplicate'):run(case)

def test_unfinished_checkpoints_are_not_promoted(case):
    r=next(x for x in case[3] if x['targets'])
    r['targets'][0]['status']='extracting';r['pending']=1
    report=run(case)
    assert report['recorded_new_readings']==0 and report['statuses']['extracting']==1

def test_catalog_and_ledger_must_agree_before_attachment(tmp_path):
    from proofreader.breadth import attach
    (tmp_path/'coverage.json').write_text(json.dumps({'expected_theorem_targets':7,'proof_readings':1}))
    with pytest.raises(ValueError,match='disagrees'):
        attach(tmp_path,{'receipts_consistency_checked':True,'expected_theorem_targets':7,'total_retained_readings':2})
    assert not (tmp_path/'breadth.json').exists()


def test_progress_page_has_local_links_and_keeps_unknown_reports(tmp_path,case):
    from proofreader.breadth import attach
    ledger=run(case)
    ledger.update(receipts_consistency_checked=True,total_retained_readings=1,theorem_targets_without_reading=6)
    # This fixture tests HTML only, not authenticity of proof observations.
    (tmp_path/'coverage.json').write_text(json.dumps({'expected_theorem_targets':7,'proof_readings':1}))
    for name in ('index.html','coverage.html'):
        (tmp_path/name).write_text('<main id="content"></main>')
    attach(tmp_path,ledger)
    text=(tmp_path/'progress.html').read_text()
    assert '1 of 7' in text and '6 still lack a reading' in text
    assert 'href="breadth.json"' in text
    assert 'progress.html' in (tmp_path/'index.html').read_text()
    assert 'artifact-not-retained' not in text # all synthetic shards retained
