"""Mocked transport/protocol tests. Only the separate native test executes Lean."""
from pathlib import Path
import copy
import json
import math
import pytest
import proofreader.narrative_batch as batch
from proofreader.lean import RunResult
from proofreader.model import canonical_json, digest
from proofreader.cli import main

ROOT = Path(__file__).parents[1]
VERSION = '4.34.1'


def snapshot(name='Demo.good'):
    r = json.loads((ROOT / 'proofreader/data/bezout-snapshot.json').read_text())
    r['theorem'] = name
    return r


def events(module='Demo', *, failure=False, limit=False):
    candidates = [{'name': 'Demo.good', 'kind': 'theorem'}]
    if failure or limit:
        candidates.append({'name': 'Demo.bad', 'kind': 'proof-definition'})
    inv = {'schema': batch.INVENTORY, 'scope': 'module:' + module, 'lean_version': VERSION,
           'candidates': candidates, 'excluded': []}
    good = {'schema': batch.OUTCOME, 'name': 'Demo.good', 'kind': 'theorem', 'status': 'exported', 'snapshot': snapshot()}
    result = [inv, good]
    if failure:
        result.append({'schema': batch.OUTCOME, 'name': 'Demo.bad', 'kind': 'proof-definition',
                       'status': 'failed', 'error': 'Disallowed axiom'})
    result.append({'schema': batch.COMPLETION, 'scope': 'module:' + module, 'lean_version': VERSION,
                   'expected': len(candidates), 'attempted': len(result)-1})
    return result


def text(rows):
    return '\n'.join(batch.PREFIX + canonical_json(row) for row in rows) + '\n'


def parse(rows):
    return batch.parse_stream(text(rows), module='Demo', version=VERSION)


def test_complete_inventory():
    result = parse(events())
    assert result['protocol_ok'] and result['missing'] == 0
    assert len(result['rows']) == 1


def test_export_failure_remains_a_candidate():
    result = parse(events(failure=True))
    assert result['protocol_ok'] and result['missing'] == 0
    assert len(result['rows']) == 2
    assert result['rows'][1]['status'] == 'failed'


def test_limit_does_not_reduce_denominator():
    result = parse(events(limit=True))
    assert result['protocol_ok'] and result['missing'] == 1
    assert len(result['inventory']['candidates']) == 2


def test_interrupted_stream_preserves_inventory_not_success():
    result = parse(events(limit=True)[:-1])
    assert not result['protocol_ok'] and result['missing'] == 1
    assert len(result['rows']) == 2


@pytest.mark.parametrize('edit', [
    lambda rows: rows.append(rows[0]),
    lambda rows: rows.insert(2, copy.deepcopy(rows[1])),
    lambda rows: rows[0]['candidates'].append(copy.deepcopy(rows[0]['candidates'][0])),
    lambda rows: rows[1].update(name='unexpected'),
    lambda rows: rows[1].update(kind='opaque-proof'),
    lambda rows: rows[1]['snapshot'].update(theorem='other'),
    lambda rows: rows[1]['snapshot'].update(lean_version='4.34.0'),
    lambda rows: rows[-1].update(attempted=True),
    lambda rows: rows[-1].update(expected=100),
    lambda rows: rows[-1].update(scope='module:other'),
    lambda rows: rows[0].update(lean_version='4.34.0'),
    lambda rows: rows[0].update(extra='hidden'),
    lambda rows: rows[1].update(status='success'),
    lambda rows: rows[1]['snapshot']['frames'][0].update(statement='False'),
    lambda rows: rows.insert(1, {'schema': 'unknown'}),
    lambda rows: rows.pop(0),
])
def test_protocol_tampering(edit):
    rows = events()
    edit(rows)
    assert not parse(rows)['protocol_ok']


def test_missing_inventory_is_unknown():
    result = batch.parse_stream('error: import failed', module='Demo', version=VERSION)
    assert result['inventory'] is None and not result['protocol_ok']


def test_bad_json_after_good_inventory_preserves_denominator():
    stdout = text(events()[:1]) + batch.PREFIX + '{"schema":\n'
    result = batch.parse_stream(stdout, module='Demo', version=VERSION)
    assert result['inventory'] is not None and not result['protocol_ok']
    assert result['rows'][0]['status'] == 'missing'


def install_mock(monkeypatch, stdout, *, fail_export=False, fail_build=False):
    calls = []
    def run(cmd, cwd, **kwargs):
        calls.append(cmd)
        build = cmd[1] == 'build'
        bad = fail_build if build else fail_export
        return RunResult('failed' if bad else 'passed', cmd, 1 if bad else 0,
                         '' if build else stdout, 'deliberate failure' if bad else '', .01,
                         'timeout' if bad else '')
    monkeypatch.setattr(batch, 'run_bounded', run)
    return calls


def project(tmp_path):
    p = tmp_path / 'project'; p.mkdir()
    (p/'lean-toolchain').write_text('leanprover/lean4:v4.34.1\n')
    return p


def test_consent_before_artifacts_or_execution(tmp_path, monkeypatch):
    calls = install_mock(monkeypatch, '')
    with pytest.raises(PermissionError):
        batch.run_batch(['Demo'], project(tmp_path), tmp_path/'out')
    assert not calls and not (tmp_path/'out').exists()


@pytest.mark.parametrize('modules,opts', [
    ([], {}), (['Demo', 'Demo'], {}), (['Demo\n#eval 1'], {}),
    (['Demo'], {'timeout': math.nan}), (['Demo'], {'timeout': float('inf')}),
    (['Demo'], {'max_declarations': True}), (['Demo'], {'shard_count': 0}),
    (['Demo'], {'shard_count': 2, 'shard_index': 2}), (['Demo'], {'version': '4.34'}),
])
def test_validation_before_execution(tmp_path, monkeypatch, modules, opts):
    calls = install_mock(monkeypatch, '')
    with pytest.raises(ValueError):
        batch.run_batch(modules, project(tmp_path), tmp_path/'out', trust_project=True, **opts)
    assert not calls


def test_successful_run_and_artifacts(tmp_path, monkeypatch):
    calls = install_mock(monkeypatch, text(events()))
    result = batch.run_batch(['Demo'], project(tmp_path), tmp_path/'out', trust_project=True)
    assert result['status'] == 'complete'
    assert result['summary']['total_candidates'] == 1
    assert result['summary']['kernel_checked'] == result['summary']['rendered'] == 1
    assert result['summary']['certified_english_proofs'] == 0
    assert len(calls) == 2 and calls[0] == ['lake', 'build', 'Demo']
    row = result['modules'][0]['rows'][0]
    assert (tmp_path/'out'/row['reader']).is_file()
    assert row['polynomial_certificates'] == 16
    batch._validate_report(result)


def test_partial_run_preserves_failure(tmp_path, monkeypatch):
    install_mock(monkeypatch, text(events(failure=True)))
    result = batch.run_batch(['Demo'], project(tmp_path), tmp_path/'out', trust_project=True)
    assert result['status'] == 'partial' and result['summary']['total_candidates'] == 2
    assert result['summary']['rendered'] == 1 and result['summary']['not_rendered'] == 1
    assert 'Disallowed axiom' in (tmp_path/'out/index.html').read_text()
    batch._validate_report(result)


def test_build_failure_leaves_unknown_denominator(tmp_path, monkeypatch):
    install_mock(monkeypatch, '', fail_build=True)
    result = batch.run_batch(['Demo'], project(tmp_path), tmp_path/'out', trust_project=True)
    assert result['summary']['total_candidates'] is None
    assert result['summary']['unknown_denominator_modules'] == ['Demo']
    batch._validate_report(result)


def test_failed_process_cannot_borrow_valid_markers(tmp_path, monkeypatch):
    install_mock(monkeypatch, text(events()), fail_export=True)
    result = batch.run_batch(['Demo'], project(tmp_path), tmp_path/'out', trust_project=True)
    assert result['summary']['total_candidates'] == 1
    assert result['summary']['kernel_checked'] == result['summary']['rendered'] == 0
    assert result['modules'][0]['rows'][0]['status'] == 'unverified-export'
    batch._validate_report(result)


def test_stale_output_is_not_reused(tmp_path, monkeypatch):
    p = project(tmp_path)
    install_mock(monkeypatch, text(events()))
    first = batch.run_batch(['Demo'], p, tmp_path/'out', trust_project=True)
    install_mock(monkeypatch, '', fail_build=True)
    second = batch.run_batch(['Demo'], p, tmp_path/'out', trust_project=True)
    assert first['attempt_directory'] != second['attempt_directory']
    assert second['summary']['rendered'] == 0
    assert json.loads((tmp_path/'out/batch.json').read_text())['status'] == 'partial'
    assert first['modules'][0]['rows'][0]['reader'] not in (tmp_path/'out/index.html').read_text()


def test_source_change_invalidates_readers_and_receipts(tmp_path, monkeypatch):
    install_mock(monkeypatch, text(events()))
    fps = iter(['before', 'after'])
    monkeypatch.setattr(batch, 'source_fingerprint', lambda p: next(fps))
    result = batch.run_batch(['Demo'], project(tmp_path), tmp_path/'out', trust_project=True)
    assert result['status'] == 'source-changed'
    assert result['summary']['rendered'] == result['summary']['kernel_checked'] == 0
    assert not list((tmp_path/'out/attempts').rglob('reader.html'))
    assert all(json.loads(p.read_text())['status'] == 'source-changed'
               for p in (tmp_path/'out/attempts').rglob('receipt.json'))


def test_index_escapes_failure_message(tmp_path, monkeypatch):
    rows = events(failure=True); rows[-2]['error'] = '<script>alert(1)</script>'
    install_mock(monkeypatch, text(rows))
    batch.run_batch(['Demo'], project(tmp_path), tmp_path/'out', trust_project=True)
    page = (tmp_path/'out/index.html').read_text()
    assert '<script>' not in page and '&lt;script&gt;' in page


def test_symlink_attempt_directory_rejected(tmp_path):
    p = project(tmp_path); out=tmp_path/'out';out.mkdir(); other=tmp_path/'other';other.mkdir()
    (out/'attempts').symlink_to(other, target_is_directory=True)
    with pytest.raises(ValueError):batch.run_batch(['Demo'],p,out,trust_project=True)


def test_output_cannot_overwrite_project(tmp_path):
    p = project(tmp_path)
    with pytest.raises(ValueError):batch.run_batch(['Demo'], p, p/'output',trust_project=True)


def test_aggregation_reconciles_and_rejects_duplicate_shards(tmp_path, monkeypatch):
    install_mock(monkeypatch, text(events()))
    p = project(tmp_path)
    run = batch.run_batch(['Demo'], p, tmp_path/'out', trust_project=True)
    result = batch.aggregate([tmp_path/'out/batch.json'], tmp_path/'aggregate.json')
    assert result['summary']['pipeline_complete']
    with pytest.raises(ValueError, match='Overlapping'):
        batch.aggregate([tmp_path/'out/batch.json']*2, tmp_path/'bad.json')
    run['modules'][0]['expected'] = 0
    (tmp_path/'out/batch.json').write_text(json.dumps(run))
    with pytest.raises(ValueError):batch.aggregate([tmp_path/'out/batch.json'], tmp_path/'bad.json')


def test_missing_shards_leave_unknown_modules(tmp_path, monkeypatch):
    modules = ['Demo', 'Missing']
    count = 17
    idx = int(digest('Demo')[:16],16) % count
    assert int(digest('Missing')[:16],16) % count != idx
    install_mock(monkeypatch, text(events()))
    batch.run_batch(modules, project(tmp_path), tmp_path/'out', trust_project=True,
                    shard_count=count, shard_index=idx)
    result = batch.aggregate([tmp_path/'out/batch.json'], tmp_path/'aggregate.json')
    assert result['summary']['total_candidates'] is None
    assert result['summary']['known_candidate_count'] == 1
    assert result['summary']['unknown_denominator_modules'] == ['Missing']


def test_cli_consent_and_plan(tmp_path,monkeypatch):
    calls=install_mock(monkeypatch,text(events()));p=project(tmp_path)
    plan=tmp_path/'plan.json';plan.write_text('{"modules":["Demo"]}')
    args=['batch-narrative','--plan',str(plan),'--project',str(p),'-o',str(tmp_path/'out')]
    assert main(args)==2 and not calls
    assert main(args+['--trust-project'])==0


def test_packaged_batch_exporter_matches_source():
    assert (ROOT/'lean/NarrativeBatch.lean').read_bytes()==(ROOT/'proofreader/data/NarrativeBatch.lean').read_bytes()
