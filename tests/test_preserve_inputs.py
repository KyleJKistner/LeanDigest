"""Input preservation: copy checks, preservation records and printed repins.

All artifacts, archives, run IDs, digests and records here are synthetic. Tests
whose names contain 'checkout' also read this checkout's consumer files, still
with a synthetic record. No test downloads anything: gh is replaced by fakes.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('preserve_inputs', ROOT/'scripts/preserve_inputs.py')
pi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pi)

RUN, HEAD = 40000000001, 'a'*40
RUN2, HEAD2 = 40000000002, 'b'*40


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_zip(path: Path, files: dict[str, bytes], directories: tuple[str, ...] = ()) -> bytes:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, 'w') as z:
        for name in directories:
            z.writestr(zipfile.ZipInfo(name.rstrip('/')+'/'), b'')
        for name, data in files.items():
            z.writestr(name, data)
    return path.read_bytes()


def upload(payload: Path, path: Path) -> bytes:
    """What upload-artifact stores: the payload's files at the archive root."""
    return make_zip(path, {p.relative_to(payload).as_posix(): p.read_bytes()
                           for p in sorted(payload.rglob('*')) if p.is_file()})


def synthetic_origin(key: str, layout: str, data: bytes, *, group: str | None = None) -> pi.Origin:
    return pi.Origin(key, 'synthetic-'+key, 1000+len(key), 2000, 'c'*40, sha(data), len(data),
                     '2026-11-01T00:00:00Z', layout, group or key)


def meta_for(origin: pi.Origin, pin: dict, size: int, **changes) -> dict:
    meta = {'id': pin['artifact_id'], 'name': origin.name, 'size_in_bytes': size, 'expired': False,
            'digest': 'sha256:'+pin['digest'], 'created_at': '2026-10-01T00:00:00Z',
            'expires_at': '2026-10-31T00:00:00Z',
            'workflow_run': {'id': pin['run_id'], 'head_sha': pin['head_sha']}}
    meta.update(changes)
    return meta


def origin_pin(origin: pi.Origin) -> dict:
    return {'artifact_id': origin.artifact_id, 'run_id': origin.run_id, 'head_sha': origin.head_sha,
            'digest': origin.digest, 'copy': False}


def copy_meta(name: str, data: bytes, ident: int = 5000, **changes) -> dict:
    meta = {'id': ident, 'name': name, 'size_in_bytes': len(data), 'expired': False,
            'digest': 'sha256:'+sha(data), 'created_at': '2026-10-21T00:00:00Z',
            'expires_at': '2027-01-19T00:00:00Z', 'workflow_run': {'id': RUN, 'head_sha': HEAD}}
    meta.update(changes)
    return meta


def synthetic_record(name: str, *, run: int = RUN, head: str = HEAD, current: dict | None = None,
                     base: int = 13000000000) -> dict:
    items = []
    for n, key in enumerate(pi.keys_of(name)):
        o, pin = pi.ORIGINS[key], pi.pin_of(key, current or {})
        items.append({'schema': pi.ITEM, 'status': 'preserved', 'key': key, 'name': o.name, 'layout': o.layout,
                      'group': o.group, 'origin': pi.origin_record(o),
                      'copied_from': {k: pin[k] for k in ('artifact_id', 'run_id', 'head_sha', 'digest')},
                      'recorded_digests': [],
                      'content': {'files': 1, 'bytes': 1, 'content_sha256': sha(b'%d' % (base+n)),
                                  'empty_directories': []},
                      'round_trip_verified': True,
                      'preserved': {'artifact_id': base+n, 'run_id': run, 'head_sha': head,
                                    'digest': sha(b'copy %d' % (base+n)), 'size_in_bytes': 1,
                                    'created_at': '2026-10-21T00:00:00Z', 'expires_at': '2027-01-19T00:00:00Z',
                                    'retention_days_requested': 90, 'retention_days_observed': 90.0}})
    record = {'schema': pi.SCHEMA, 'repository': pi.REPOSITORY, 'workflow': pi.WORKFLOW, 'set': name,
              'preservation_run_id': run, 'preservation_head_sha': head, 'artifacts': items, 'failed': [],
              'missing': [], 'earliest_copy_expiry': '2027-01-19T00:00:00Z', 'release_published': False,
              'consumers_repinned': False}
    record['record_sha256'] = pi.digest(record)
    return record


def apply(root: Path, plan: dict) -> None:
    """Apply a printed plan to a scratch tree (the tool itself never does this)."""
    by_path: dict[str, list[dict]] = {}
    for edit in plan['edits']:
        by_path.setdefault(edit['path'], []).append(edit)
    for path, edits in by_path.items():
        lines = (root/path).read_text().split('\n')
        for edit in sorted(edits, key=lambda e: -e['line']):
            i = edit['line']-1
            assert lines[i:i+len(edit['old'])] == edit['old']
            lines[i:i+len(edit['old'])] = edit['new']
        (root/path).write_text('\n'.join(lines))


def current_block(text: str) -> dict:
    lines = text.split('\n')
    start = lines.index(next(line for line in lines if line.startswith('CURRENT: dict[str, dict] = {')))
    end = start if lines[start].endswith('{}') else lines.index('}', start)
    scope: dict = {}
    exec('\n'.join(lines[start:end+1]), {}, scope)
    return scope['CURRENT']


# Registry ---------------------------------------------------------------

def test_registry_is_consistent():
    assert len({o.name for o in pi.ORIGINS.values()}) == len(pi.ORIGINS)
    assert len({o.artifact_id for o in pi.ORIGINS.values()}) == len(pi.ORIGINS)
    assert set(pi.GROUPS) == {o.group for o in pi.ORIGINS.values()}
    assert {g for groups in pi.SETS.values() for g in groups} == set(pi.GROUPS)
    assert pi.keys_of('expiring-2026-11') == ['checkpoint', 'source', 'statement-retry-CoarseAssembly',
                                              'statement-retry-CharacterVarietiesAllSeamsSupport']
    assert len(pi.keys_of('expiring-2027-01')) == 21 and len(pi.members('proof-retries')) == 16
    for o in pi.ORIGINS.values():
        assert o.layout in {'files', 'archive'} and len(o.digest) == 64 and len(o.head_sha) == 40
        assert 0 < o.size <= pi.MAX_ARCHIVE_BYTES and o.expires_at.endswith('Z')
    for group, (refs, keeps) in pi.GROUPS.items():
        found = pi.members(group)
        assert len({(o.run_id, o.head_sha, o.layout) for o in found}) == 1
        if found[0].layout == 'archive':
            assert len(found) == 1, 'archive references name one artifact'
        if len(found) > 1:
            for text in [r.origin for r in refs]+[r.copy or '' for r in refs]+[k.text for k in keeps]:
                assert not any(p in text for p in pi.ARTIFACT_PLACEHOLDERS), text
    for key, rows in pi.RECORDED.items():
        for member, wanted, where in rows:
            assert member or wanted == pi.ORIGINS[key].digest
            assert where and all(isinstance(path, str) for path in where)
    assert pi.render_current(pi.CURRENT) in (ROOT/'scripts/preserve_inputs.py').read_text()


def test_recorded_digests_are_in_the_cited_checkout_files():
    for key, rows in pi.RECORDED.items():
        if key in pi.CURRENT:
            continue
        for _, wanted, where in rows:
            for path in where:
                assert wanted in (ROOT/path).read_text(), (key, path)


def test_inventory_table_in_docs_matches_the_checkout_registry():
    assert pi.inventory() in (ROOT/'docs/INPUT_PRESERVATION.md').read_text()


# Copy checks --------------------------------------------------------------

def test_files_copy_round_trip_keeps_layout_hidden_files_and_reports_empty_directories(tmp_path):
    files = {'statements/a/statements.json': b'{"x": 1}\n', '.hidden/state.json': b'[]\n'}
    data = make_zip(tmp_path/'in/original.zip', files, directories=('empty/',))
    o = synthetic_origin('files-input', 'files', data)
    pin = origin_pin(o)
    fetched = pi.stage(o, pin, meta_for(o, pin, len(data)), tmp_path/'in/original.zip', tmp_path/'work')
    assert fetched['content']['files'] == 2 and fetched['content']['empty_directories'] == ['empty']
    assert (tmp_path/'work/payload/.hidden/state.json').read_bytes() == b'[]\n'
    assert fetched['copied_from']['is_preserved_copy'] is False
    copy = upload(tmp_path/'work/payload', tmp_path/'copy.zip')
    item = pi.check_copy(fetched, copy_meta(o.name, copy), tmp_path/'copy.zip', tmp_path/'work',
                         run_id=RUN, head=HEAD, artifact_id=5000)
    assert item['status'] == 'preserved' and item['round_trip_verified'] is True
    assert item['preserved']['digest'] == sha(copy) and item['preserved']['retention_days_observed'] == 90.0
    assert item['origin']['artifact_id'] == o.artifact_id


def test_archive_copy_holds_the_original_zip_bytes(tmp_path, monkeypatch):
    data = make_zip(tmp_path/'in/original.zip', {'checkpoint-1/build.tar.gz': b'\x1f\x8b synthetic'})
    o = synthetic_origin('archive-input', 'archive', data)
    monkeypatch.setitem(pi.RECORDED, o.key, (('', o.digest, ('docs/SYNTHETIC.md',)),))
    pin = origin_pin(o)
    fetched = pi.stage(o, pin, meta_for(o, pin, len(data)), tmp_path/'in/original.zip', tmp_path/'work')
    inner = tmp_path/'work/payload'/('original-%d.zip' % o.artifact_id)
    assert inner.read_bytes() == data and fetched['content']['files'] == 1
    assert fetched['recorded_digests'][0]['checked_against'] == 'downloaded artifact ZIP'
    copy = upload(tmp_path/'work/payload', tmp_path/'copy.zip')
    item = pi.check_copy(fetched, copy_meta(o.name, copy), tmp_path/'copy.zip', tmp_path/'work', run_id=RUN, head=HEAD)
    # The second copy of this copy unwraps the same original bytes again.
    again = {'artifact_id': 5000, 'run_id': RUN, 'head_sha': HEAD, 'digest': sha(copy),
             'content_sha256': item['content']['content_sha256'], 'copy': True}
    second = pi.stage(o, again, meta_for(o, again, len(copy)), tmp_path/'copy.zip', tmp_path/'work2')
    assert (tmp_path/'work2/payload'/inner.name).read_bytes() == data
    assert second['content'] == fetched['content']
    assert second['recorded_digests'][0]['checked_against'] == 'original ZIP inside the copy'
    extra = make_zip(tmp_path/'extra.zip', {inner.name: data, 'other.txt': b'x'})
    extra_pin = {**again, 'digest': sha(extra)}
    with pytest.raises(ValueError, match='exactly the original'):
        pi.stage(o, extra_pin, meta_for(o, extra_pin, len(extra)), tmp_path/'extra.zip', tmp_path/'work3')


def test_recorded_member_digest_is_checked(tmp_path, monkeypatch):
    data = make_zip(tmp_path/'original.zip', {'openai-lean-source.tar.gz': b'synthetic source'})
    o = synthetic_origin('source-like', 'files', data)
    pin = origin_pin(o)
    monkeypatch.setitem(pi.RECORDED, o.key, (('', o.digest, ('a.py',)),
                                             ('openai-lean-source.tar.gz', sha(b'synthetic source'), ('b.py',))))
    fetched = pi.stage(o, pin, meta_for(o, pin, len(data)), tmp_path/'original.zip', tmp_path/'ok')
    assert [r['checked_against'] for r in fetched['recorded_digests']] == ['downloaded artifact ZIP',
                                                                           'file in the artifact']
    monkeypatch.setitem(pi.RECORDED, o.key, (('openai-lean-source.tar.gz', sha(b'other'), ('b.py',)),))
    with pytest.raises(ValueError, match='Recorded digest mismatch'):
        pi.stage(o, pin, meta_for(o, pin, len(data)), tmp_path/'original.zip', tmp_path/'bad')


@pytest.mark.parametrize('change,message', [
    ({'expired': True}, 'expired'),
    ({'digest': 'sha256:'+'0'*64}, 'reported artifact digest'),
    ({'workflow_run': {'id': 1, 'head_sha': 'c'*40}}, 'another run'),
    ({'workflow_run': {'id': 2000, 'head_sha': 'd'*40}}, 'another run'),
    ({'name': 'other'}, 'different artifact'),
    ({'id': 1}, 'different artifact'),
    ({'size_in_bytes': 1}, 'size'),
])
def test_metadata_that_differs_from_the_pin_is_rejected(tmp_path, change, message):
    data = make_zip(tmp_path/'original.zip', {'a.json': b'{}'})
    o = synthetic_origin('meta', 'files', data)
    pin = origin_pin(o)
    with pytest.raises(ValueError, match=message):
        pi.stage(o, pin, meta_for(o, pin, len(data), **change), tmp_path/'original.zip', tmp_path/'work')


def test_unsafe_or_changed_archives_are_rejected(tmp_path):
    data = make_zip(tmp_path/'original.zip', {'a.json': b'{}'})
    o = synthetic_origin('bytes', 'files', data)
    (tmp_path/'original.zip').write_bytes(data[:10]+bytes([data[10] ^ 1])+data[11:])
    with pytest.raises(ValueError, match='differs from its reported digest'):
        pi.stage(o, origin_pin(o), meta_for(o, origin_pin(o), len(data)), tmp_path/'original.zip', tmp_path/'w1')
    for n, entry in enumerate(['../escape.json', '/absolute.json', 'a\\b.json', 'c:d.json']):
        bad = make_zip(tmp_path/('bad%d.zip' % n), {entry: b'{}'})
        o = synthetic_origin('unsafe%d' % n, 'files', bad)
        with pytest.raises(ValueError, match='Unsafe'):
            pi.stage(o, origin_pin(o), meta_for(o, origin_pin(o), len(bad)), tmp_path/('bad%d.zip' % n),
                     tmp_path/('w%d' % (n+2)))
    link = tmp_path/'link.zip'
    with zipfile.ZipFile(link, 'w') as z:
        info = zipfile.ZipInfo('link')
        info.external_attr = (0o120777 << 16)
        z.writestr(info, 'target')
    o = synthetic_origin('link', 'files', link.read_bytes())
    with pytest.raises(ValueError, match='Non-regular'):
        pi.stage(o, origin_pin(o), meta_for(o, origin_pin(o), o.size), link, tmp_path/'w9')


def test_a_changed_or_foreign_copy_is_rejected(tmp_path):
    data = make_zip(tmp_path/'original.zip', {'a.json': b'{"a": 1}'})
    o = synthetic_origin('copy-check', 'files', data)
    fetched = pi.stage(o, origin_pin(o), meta_for(o, origin_pin(o), len(data)), tmp_path/'original.zip', tmp_path/'w')
    changed = make_zip(tmp_path/'changed.zip', {'a.json': b'{"a": 2}'})
    with pytest.raises(ValueError, match='differs from the staged contents'):
        pi.check_copy(fetched, copy_meta(o.name, changed), tmp_path/'changed.zip', tmp_path/'c1', run_id=RUN, head=HEAD)
    good = upload(tmp_path/'w/payload', tmp_path/'good.zip')
    for n, change in enumerate([{'workflow_run': {'id': 1, 'head_sha': HEAD}}, {'id': 6000}, {'expired': True}]):
        with pytest.raises(ValueError, match='not the upload of this run'):
            pi.check_copy(fetched, copy_meta(o.name, good, **change), tmp_path/'good.zip', tmp_path/('d%d' % n),
                          run_id=RUN, head=HEAD, artifact_id=5000)
    with pytest.raises(ValueError, match='no digest'):
        pi.check_copy(fetched, copy_meta(o.name, good, digest=None), tmp_path/'good.zip', tmp_path/'e',
                      run_id=RUN, head=HEAD)
    copy_pin = {'artifact_id': 5000, 'run_id': RUN, 'head_sha': HEAD, 'digest': sha(changed),
                'content_sha256': fetched['content']['content_sha256'], 'copy': True}
    with pytest.raises(ValueError, match='differs from the contents first copied'):
        pi.stage(o, copy_pin, meta_for(o, copy_pin, len(changed)), tmp_path/'changed.zip', tmp_path/'f')


# Records ----------------------------------------------------------------

def test_merge_lists_every_missing_or_failed_copy(tmp_path):
    records = tmp_path/'records'
    complete = synthetic_record('statement-retries')
    for item in complete['artifacts']:
        pi.write(records/(item['key']+'.json'), item)
    (records/'statement-retry-CoarseAssembly.manifest.json').write_text('[]')
    result = pi.merge('statement-retries', records, run_id=RUN, head=HEAD)
    assert result['missing'] == [] and result['failed'] == [] and len(result['artifacts']) == 2
    assert result['record_sha256'] == pi.digest({k: v for k, v in result.items() if k != 'record_sha256'})
    assert result['release_published'] is False and result['consumers_repinned'] is False
    (records/'statement-retry-CoarseAssembly.json').unlink()
    assert pi.merge('statement-retries', records, run_id=RUN, head=HEAD)['missing'] == ['statement-retry-CoarseAssembly']
    pi.write(records/'statement-retry-CoarseAssembly.json', {'schema': pi.ITEM, 'key': 'statement-retry-CoarseAssembly',
                                                             'status': 'failed', 'stage': 'fetch', 'error': 'expired'})
    result = pi.merge('statement-retries', records, run_id=RUN, head=HEAD)
    assert result['missing'] == [] and result['failed'] == [{'key': 'statement-retry-CoarseAssembly',
                                                             'stage': 'fetch', 'error': 'expired'}]
    assert {f['stage'] for f in pi.merge('statement-retries', records, run_id=RUN2, head=HEAD)['failed']} == \
        {'fetch', 'preserved'}, 'a copy from another run is not accepted'
    out = tmp_path/'out/preservation-record.json'
    assert pi.main(['merge', '--set', 'statement-retries', '--records', str(records), '--run-id', str(RUN),
                    '--head', HEAD, '--output', str(out)]) == 1
    assert (tmp_path/'out/manifests/statement-retry-CoarseAssembly.manifest.json').is_file()
    pi.write(records/'stray.json', {'schema': pi.ITEM, 'key': 'source', 'status': 'preserved'})
    with pytest.raises(ValueError, match='Unexpected'):
        pi.merge('statement-retries', records, run_id=RUN, head=HEAD)


def test_matrix_names_each_artifact_once(tmp_path):
    out = tmp_path/'github-output'
    assert pi.main(['matrix', '--set', 'expiring-2026-11', '--github-output', str(out)]) == 0
    text = out.read_text().splitlines()
    matrix = json.loads(text[0].removeprefix('matrix='))
    assert [r['key'] for r in matrix['include']] == pi.keys_of('expiring-2026-11') and text[1] == 'count=4'
    assert {r['key']: r['level'] for r in matrix['include']}['checkpoint'] == 0
    with pytest.raises(ValueError, match='Unknown artifact set'):
        pi.main(['matrix', '--set', 'everything'])


def test_cli_fetch_and_verify_use_only_the_supplied_gh(tmp_path, monkeypatch, capsys):
    data = make_zip(tmp_path/'served/original.zip', {'a/statements.json': b'{"s": 1}'})
    o = synthetic_origin('cli', 'files', data, group='cli-group')
    monkeypatch.setitem(pi.ORIGINS, o.key, o)
    monkeypatch.setitem(pi.SETS, 'cli-set', ('cli-group',))
    served = {o.artifact_id: tmp_path/'served/original.zip'}
    listings = {}
    def api(path):
        if path == f'actions/artifacts/{o.artifact_id}':
            return meta_for(o, origin_pin(o), len(data))
        if path.startswith(f'actions/runs/{RUN}/artifacts?name={o.name}'):
            return {'artifacts': listings.get(o.name, [])}
        raise AssertionError(path)
    def download(ident, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(served[ident], destination)
    monkeypatch.setattr(pi, 'api', api)
    monkeypatch.setattr(pi, 'download', download)
    with pytest.raises(SystemExit):
        pi.main(['fetch', '--key', o.key, '--work', str(tmp_path/'w')])
    assert pi.main(['fetch', '--key', o.key, '--work', str(tmp_path/'w'), '--allow-download']) == 0
    copy = upload(tmp_path/'w/payload', tmp_path/'served/copy.zip')
    served[5000] = tmp_path/'served/copy.zip'
    listings[o.name] = [copy_meta(o.name, copy)]
    assert pi.main(['verify', '--key', o.key, '--work', str(tmp_path/'w'), '--artifact-id', '5000',
                    '--run-id', str(RUN), '--head', HEAD, '--allow-download']) == 0
    item = pi.read(tmp_path/'w/record/cli.json')
    assert item['preserved']['artifact_id'] == 5000 and item['copied_from']['artifact_id'] == o.artifact_id
    assert pi.main(['merge', '--set', 'cli-set', '--records', str(tmp_path/'w/record'), '--run-id', str(RUN),
                    '--head', HEAD, '--output', str(tmp_path/'final/preservation-record.json')]) == 0
    final = pi.read(tmp_path/'final/preservation-record.json')
    assert final['missing'] == [] and final['earliest_copy_expiry'] == '2027-01-19T00:00:00Z'
    listings[o.name] = []
    assert pi.main(['verify', '--key', o.key, '--work', str(tmp_path/'w'), '--run-id', str(RUN), '--head', HEAD,
                    '--allow-download']) == 1
    assert pi.read(tmp_path/'w/record/cli.json')['status'] == 'failed'
    monkeypatch.setattr(pi, 'api', lambda path: meta_for(o, origin_pin(o), len(data), expired=True))
    assert pi.main(['fetch', '--key', o.key, '--work', str(tmp_path/'x'), '--allow-download']) == 1
    failure = pi.read(tmp_path/'x/record/cli.json')
    assert failure['status'] == 'failed' and failure['stage'] == 'fetch' and 'expired' in failure['error']
    assert 'GH_TOKEN' not in json.dumps(failure)


# Repin --------------------------------------------------------------------

def synthetic_tree(root: Path, groups: tuple[str, ...]) -> None:
    """Consumer files that hold exactly the origin references (a synthetic checkout)."""
    lines: dict[str, list[str]] = {'scripts/preserve_inputs.py': ['CURRENT: dict[str, dict] = {}']}
    for group in groups:
        refs, keeps = pi.GROUPS[group]
        o = pi.members(group)[0]
        for text, path in [(r.origin, r.path) for r in refs]+[(k.text, k.path) for k in keeps]:
            lines.setdefault(path, []).append('    '+pi.fill(text, origin_pin(o), o))
    for path, body in lines.items():
        (root/path).parent.mkdir(parents=True, exist_ok=True)
        (root/path).write_text('\n'.join(body)+'\n')


def test_repin_prints_edits_that_can_be_repeated_for_later_copies(tmp_path):
    synthetic_tree(tmp_path, ('checkpoint', 'statement-retries'))
    record = synthetic_record('checkpoint')
    before = {p: p.read_text() for p in tmp_path.rglob('*') if p.is_file()}
    plan = pi.plan_repin(record, tmp_path, current={})
    assert before == {p: p.read_text() for p in tmp_path.rglob('*') if p.is_file()}, 'planning changes no file'
    assert plan['missing'] == [] and plan['unclassified'] == [] and len(plan['unchanged']) == 4
    zip_edit = next(e for e in plan['edits'] if 'actions/artifacts/12217614568/zip' in e['old'][0])
    assert zip_edit['new'] == [
        '    gh run download %d -R "$GITHUB_REPOSITORY" -n checkpoint-142c3d0f555a25666bb36dd1-1 '
        '-D /tmp/preserved/12217614568' % RUN,
        '    mv /tmp/preserved/12217614568/original-12217614568.zip /tmp/acquired/checkpoint.zip']
    acquisition = [e['new'][0].strip() for e in plan['edits'] if 'artifact_id' in e['new'][0] or 'source_commit' in e['new'][0]]
    assert acquisition == ["{'artifact_id':12217614568,'run_id':39315174445,",
                           "'source_commit':'4f9c1e823dd65023cfa7d8b9afe5e08390b8d2ad','archive_sha256':"
                           "'f0cb3658f6edbffc2e62cd8f538ea9a7529a0e4cbe4e27286241030441003523'})"]
    text = pi.format_plan(plan)
    assert 'Nothing has been changed' in text and 'artifacts/input-preservation/%d.json' % RUN in text
    apply(tmp_path, plan)
    assert current_block((tmp_path/'scripts/preserve_inputs.py').read_text()) == plan['current']
    # A later copy of the copy: consumers now pin the first copy.
    with pytest.raises(ValueError, match='another pin'):
        pi.plan_repin(record, tmp_path, current=plan['current'])
    second = synthetic_record('checkpoint', run=RUN2, head=HEAD2, current=plan['current'], base=14000000000)
    later = pi.plan_repin(second, tmp_path, current=plan['current'])
    assert later['missing'] == [] and later['unclassified'] == []
    changed = [e['new'] for e in later['edits']]
    assert ['    gh run download %d -R "$GITHUB_REPOSITORY" -n checkpoint-142c3d0f555a25666bb36dd1-1 '
            '-D /tmp/preserved/12217614568' % RUN2,
            '    mv /tmp/preserved/12217614568/original-12217614568.zip /tmp/acquired/checkpoint.zip'] in changed
    assert not any("'artifact_id':12217614568" in line for e in later['edits'] for line in e['old']+e['new']), \
        'the acquisition record already names the original'
    apply(tmp_path, later)
    assert '14000000000' in (tmp_path/'.github/workflows/completion-resume.yml').read_text()


def test_repin_reports_drift_and_unhandled_references(tmp_path, capsys):
    synthetic_tree(tmp_path, ('statement-retries',))
    record = synthetic_record('statement-retries')
    path = tmp_path/'.github/workflows/breadth-release.yml'
    path.write_text(path.read_text().replace('39050823104', '39050823105'))
    (tmp_path/'scripts/other.py').write_text("RUN = 39050823104  # synthetic unhandled reference\n")
    plan = pi.plan_repin(record, tmp_path, current={})
    assert [m['path'] for m in plan['missing']] == ['.github/workflows/breadth-release.yml']
    assert [(u['path'], u['token']) for u in plan['unclassified']] == [('scripts/other.py', '39050823104')]
    pi.write(tmp_path/'record.json', record)
    assert pi.main(['repin', '--record', str(tmp_path/'record.json'), '--root', str(tmp_path)]) == 1
    assert 'This plan is incomplete' in capsys.readouterr().out


def test_repin_refuses_partial_changed_or_unverified_records(tmp_path):
    synthetic_tree(tmp_path, ('statement-retries',))
    record = synthetic_record('statement-retries')
    partial = dict(record, artifacts=record['artifacts'][:1])
    partial['record_sha256'] = pi.digest({k: v for k, v in partial.items() if k != 'record_sha256'})
    with pytest.raises(ValueError, match='part of the statement-retries group'):
        pi.plan_repin(partial, tmp_path, current={})
    with pytest.raises(ValueError, match='unchanged preservation record'):
        pi.plan_repin(dict(record, preservation_run_id=RUN2), tmp_path, current={})
    for change, message in [({'failed': [{'key': 'x'}]}, 'did not copy every'), ({'missing': ['x']}, 'did not copy every'),
                            ({'repository': 'someone/fork'}, 'another repository')]:
        bad = dict(record, **change)
        bad['record_sha256'] = pi.digest({k: v for k, v in bad.items() if k != 'record_sha256'})
        with pytest.raises(ValueError, match=message):
            pi.plan_repin(bad, tmp_path, current={})
    pi.write(tmp_path/'changed.json', dict(record, set='source'))
    assert pi.main(['repin', '--record', str(tmp_path/'changed.json'), '--root', str(tmp_path)]) == 1
    unverified = json.loads(json.dumps(record))
    unverified['artifacts'][0]['round_trip_verified'] = False
    unverified['record_sha256'] = pi.digest({k: v for k, v in unverified.items() if k != 'record_sha256'})
    with pytest.raises(ValueError, match='not verified'):
        pi.plan_repin(unverified, tmp_path, current={})


@pytest.mark.parametrize('field,value', [
    ('preservation_run_id', '40000000001; gh release create x'),
    ('preservation_run_id', 0),
    ('preservation_head_sha', 'A'*40),
    ('artifact_id', '13000000000'),
    ('digest', "0'}; import os  #"+'0'*40),
    ('content_sha256', None),
    ('expires_at', None),
    ('set', 'everything'),
])
def test_repin_refuses_values_that_would_be_printed_unquoted(tmp_path, field, value):
    """Synthetic records whose run, commit or copy identity is not a plain number or digest."""
    synthetic_tree(tmp_path, ('statement-retries',))
    record = synthetic_record('statement-retries')
    if field in record:
        record[field] = value
    else:
        item = record['artifacts'][0]
        (item['content'] if field == 'content_sha256' else item['preserved'])[field] = value
    record['record_sha256'] = pi.digest({k: v for k, v in record.items() if k != 'record_sha256'})
    with pytest.raises(ValueError, match='malformed'):
        pi.plan_repin(record, tmp_path, current={})


def scratch_checkout(destination: Path) -> None:
    for pattern in pi.SCANNED:
        for path in ROOT.glob(pattern):
            if path.is_file():
                target = destination/path.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, target)


@pytest.mark.parametrize('name', ['expiring-2026-11', 'expiring-2027-01'])
def test_repin_covers_every_reference_in_this_checkout(tmp_path, name):
    scratch_checkout(tmp_path)
    plan = pi.plan_repin(synthetic_record(name), tmp_path, current={})
    assert plan['missing'] == [] and plan['unclassified'] == [], plan['missing']+plan['unclassified']
    assert all(e['old'] != e['new'] for e in plan['edits'])
    apply(tmp_path, plan)
    assert current_block((tmp_path/'scripts/preserve_inputs.py').read_text()) == plan['current']
    # After the printed edits, no consumer downloads an origin: its run (for
    # extracted contents) or its API download (for archives) survives only on
    # lines that the plan lists as unchanged.
    kept = {(u['path'], u['text']) for u in plan['unchanged']}
    for key in pi.keys_of(name):
        o = pi.ORIGINS[key]
        needles = ([str(o.run_id), str(o.artifact_id)] if o.layout == 'files' else
                   ['actions/artifacts/%d' % o.artifact_id, "'workflow_run']['id']==%d" % o.run_id])
        for pattern in pi.SCANNED:
            for path in tmp_path.glob(pattern):
                rel = path.relative_to(tmp_path).as_posix()
                for line in path.read_text().split('\n') if rel not in pi.SELF else []:
                    if any(n in line for n in needles):
                        assert (rel, line.strip()) in kept, (rel, line)
    later = pi.plan_repin(synthetic_record(name, run=RUN2, head=HEAD2, current=plan['current'], base=14000000000),
                          tmp_path, current=plan['current'])
    assert later['missing'] == [] and later['unclassified'] == []


# Workflow ---------------------------------------------------------------

def top_level_block(text: str, key: str) -> list[str]:
    """The lines under a top-level YAML key, read without a YAML parser."""
    lines = text.split('\n')
    start = lines.index(key+':')
    end = next((i for i in range(start+1, len(lines)) if lines[i] and not lines[i][0].isspace()), len(lines))
    return [line for line in lines[start+1:end] if line.strip() and not line.lstrip().startswith('#')]


def test_workflow_is_dispatch_only_and_never_publishes():
    # PyYAML is not among the dev or webtest extras that ci.yml and the plan
    # job install, so the trigger and permission checks read the text.
    text = (ROOT/'.github/workflows/preserve-inputs.yml').read_text()
    for forbidden in ('push:', 'schedule:', 'pull_request', 'contents: write', 'actions: write', 'gh release',
                      'git push', 'actions/cache', 'workflow_run'):
        assert forbidden not in text, forbidden
    assert text.count('retention-days: 90') == text.count('actions/upload-artifact@v4') == 3
    assert "-k 'not checkout'" in text and '--allow-download' in text
    triggers = [line for line in top_level_block(text, 'on') if not line.startswith('   ')]
    assert triggers == ['  workflow_dispatch:']
    assert top_level_block(text, 'permissions') == ['  contents: read', '  actions: read']
    assert text.count('permissions:') == 1 and 'secrets.' not in text


def test_workflow_structure_when_yaml_is_available():
    yaml = pytest.importorskip('yaml')
    text = (ROOT/'.github/workflows/preserve-inputs.yml').read_text()
    flow = yaml.safe_load(text)
    assert set(flow[True]) == {'workflow_dispatch'}
    choice = flow[True]['workflow_dispatch']['inputs']['set']
    assert choice['options'] == list(pi.SETS) and choice['default'] == 'expiring-2026-11'
    assert flow['permissions'] == {'contents': 'read', 'actions': 'read'}
    assert all('permissions' not in job for job in flow['jobs'].values())
    copy = flow['jobs']['copy']
    uploads = [s for s in copy['steps'] if s.get('uses', '').startswith('actions/upload-artifact')]
    assert uploads[0]['with']['name'] == '${{ matrix.name }}' and uploads[0]['with']['include-hidden-files'] is True
    assert copy['strategy']['fail-fast'] is False and flow['jobs']['record']['needs'] == ['plan', 'copy']
