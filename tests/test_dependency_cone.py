"""Dependency-cone planner, shard worker and loader.

SYNTHETIC FIXTURES: every project, snapshot, Lean process and shard below is
fabricated for accounting tests. No Lean ran and none of it is a native
observation. Only the committed-plan tests read real retained data (the plan).
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import zipfile
import pytest
from proofreader import dependency_cone as cone
from proofreader.lean import RunResult
from proofreader.model import canonical_json, digest as data_digest
from proofreader.narrative import Snapshot
from proofreader.narrative_io import exporter_source
from proofreader.original_project import audit_environment, file_hash, make_plan as original_plan, read, write
from test_original_project import fixture_project

ROOT = Path(__file__).resolve().parents[1]
ALPHA, BETA, GAMMA = 'OAI.Alpha.Main', 'OAI.Beta.Main', 'OAI.Gamma.Main'
IDENTITY = {'release': 'synthetic', 'url': 'https://example.invalid/synthetic.zip', 'sha256': '0'*64}


def snapshot(theorem: str, heads: list[str]) -> dict:
    """A valid synthetic record whose root applies heads[0] to proofs named by heads[1:]."""
    kids = [{'id': i, 'path': [0]*(len(heads)-1-i)+[1], 'statement': f'P{i}', 'role': 'named', 'head': h,
             'context': [], 'children': [], 'premises': [], 'objects': [], 'budget_cut': False}
            for i, h in enumerate(heads[1:], 1)]
    root = {'id': 0, 'path': [], 'statement': 'Q', 'role': 'application' if kids else 'named', 'head': heads[0],
            'context': [], 'children': [k['id'] for k in kids], 'objects': [], 'budget_cut': False,
            'premises': [{'argument': k['id']-1, 'statement': k['statement'], 'frame': k['id']} for k in kids]}
    return {'schema': 'proofreader.narrative/v1', 'theorem': theorem, 'lean_version': '4.34.1', 'axioms': [],
            'statement': 'Q', 'frames': [root]+kids, 'judgements_checked': 1+len(kids),
            'formula_backend': 'Lean pretty-printer'}


CITATIONS = {
    (ALPHA, 'OAI.Alpha.main'): ['OAI.Alpha.lemma1', 'OAI.Alpha.lemma2', 'OAI.Shared.lemma', 'OAI.Beta.main',
                                'OAI.Gamma.unread', 'OAI.Alpha.instFoo', '_private.OAI.Alpha.Main.0.OAI.Alpha.hidden'],
    (ALPHA, 'OAI.Alpha.second'): ['OAI.Alpha.lemma1', 'OAI.Alpha.main._proof_1', 'OAI.Alpha.lemma1'],
    (BETA, 'OAI.Beta.main'): ['OAI.Shared.lemma', 'OAI.Beta.size', 'OAI.Beta.T.mk', 'OAI.Beta.helper', 'Nat.succ'],
}
PLANNED = {ALPHA: ['OAI.Alpha.lemma1', 'OAI.Alpha.lemma2', 'OAI.Alpha.main._proof_1', 'OAI.Shared.lemma'],
           BETA: ['OAI.Beta.helper']}


@pytest.fixture
def world(tmp_path):
    """Synthetic original project, environment audit, retained readings and worker evidence."""
    project, _, _ = fixture_project(tmp_path)
    for module, theorems, definitions in [(ALPHA, ['OAI.Alpha.main', 'OAI.Alpha.second'], []),
                                          (BETA, ['OAI.Beta.main'], ['OAI.Beta.size']), (GAMMA, ['OAI.Gamma.unread'], [])]:
        stem = module.split('.')[1]
        write(project/f'ComparatorChallenges/{stem}.json', {'challenge_module': 'ComparatorChallenges.'+stem,
              'solution_module': module, 'theorem_names': theorems, 'definition_names': definitions})
        path = project/(module.replace('.', '/')+'.lean')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('-- synthetic source, never compiled\n')
    inventory = [{'path': 'lean/'+f.relative_to(project).as_posix(), 'sha256': file_hash(f)}
                 for f in project.rglob('*') if f.is_file() and '.lake' not in f.parts]
    plan = original_plan(project, inventory)
    env = audit_environment(project, plan)
    proofs = {}
    for (module, theorem), heads in CITATIONS.items():
        record = snapshot(theorem, ['Synthetic.assemble']+heads)
        receipt = {'module': module, 'theorem': theorem, 'status': 'passed', 'snapshot_sha256': Snapshot(record).sha256}
        proofs[cone.lemma_id(module, theorem)] = {'snapshot.json': canonical_json(record).encode(),
                                                  'receipt.json': canonical_json(receipt).encode()}
    def worker(module, status, elapsed):
        return {'original-proof-worker.json': json.dumps({'module': module, 'status': status,
                    'environment_before': env, 'environment_after': env}).encode(),
                'proofs.json': json.dumps({'elapsed_seconds': elapsed}).encode()}
    workers = {'a'*64: worker(ALPHA, 'complete', 100.0), 'b'*64: worker(BETA, 'partial', 50.0)}
    inputs = {'proofs': proofs, 'workers': workers, 'original_plan': plan, 'environment': env}
    return {'project': project, 'original': plan, 'environment': env, 'inputs': inputs,
            'plan': cone.make_plan(inputs, IDENTITY)}


def test_denominator_is_explicit_and_separate(world):
    plan = world['plan']
    d = plan['denominator']
    assert d['cited_constants'] == 11 and d['already_read'] == 1 and d['excluded'] == 5 and d['planned_lemmas'] == 5
    assert d['excluded_by_reason'] == {'constructor-by-name': 1, 'documented-definition': 1, 'documented-theorem-target': 1,
                                       'instance-by-name': 1, 'not-addressable-by-exporter': 1}
    assert {s['module']: [l['name'] for l in s['lemmas']] for s in plan['shards']} == PLANNED
    assert all(l['kind'] == 'unknown-kind' for s in plan['shards'] for l in s['lemmas'])
    lemma1 = plan['shards'][0]['lemmas'][0]
    assert lemma1['citations'] == 3 and len(lemma1['cited_by']) == 2
    assert plan['shards'][0]['lemmas'][2]['hint'] == 'compiler-abstracted-proof'
    assert plan['already_read'][0]['name'] == 'OAI.Beta.main' and d['planned_compiler_abstracted_proofs'] == 1
    assert plan['counts_toward_documented_target_coverage'] is False and plan['denominator_name'] == 'dependency-cone-level-1'
    # Shared.lemma is cited from both modules; its home is the module citing more planned lemmas.
    assert 'OAI.Shared.lemma' in PLANNED[ALPHA]
    assert plan['pilot']['shards'] == [cone.module_id(ALPHA)] and plan['pilot']['lemmas'] == 4


def test_plan_is_deterministic_and_bound(world):
    again = cone.make_plan(deepcopy(world['inputs']), IDENTITY)
    assert again == world['plan'] and cone.validate_plan(again) is again
    cone.bind_original(world['plan'], world['original'], world['environment'])


@pytest.mark.parametrize('edit', [
    lambda p: p['shards'][0]['lemmas'].pop(),
    lambda p: p['shards'][0]['lemmas'][0].update(citations=0),
    lambda p: p['shards'][0]['lemmas'][0].update(kind='theorem'),
    lambda p: p['shards'][1].update(module=ALPHA),
    lambda p: p['excluded'][0].update(reason='constructor-by-name'),
    lambda p: p['excluded'][0].update(reason='no-such-reason'),
    lambda p: p['pilot']['shards'].append(cone.module_id(BETA)),
    lambda p: p['execution'].update(extract_timeout=1),
    lambda p: p.update(counts_toward_documented_target_coverage=True),
    lambda p: p['shards'][0]['lemmas'].append({'name': 'OAI.Alpha.instBar', 'citations': 1, 'kind': 'unknown-kind',
                                               'cited_by': p['shards'][0]['lemmas'][0]['cited_by'][:1], 'hint': None}),
])
def test_plan_tampering_rejected(world, edit):
    plan = deepcopy(world['plan'])
    edit(plan)
    plan['plan_sha256'] = cone.digest({k: v for k, v in plan.items() if k != 'plan_sha256'})
    with pytest.raises(ValueError):
        cone.validate_plan(plan)


def test_documented_reasons_are_checked_against_the_original_plan(world):
    plan = deepcopy(world['plan'])
    row = next(r for r in plan['excluded'] if r['reason'] == 'documented-definition')
    row['reason'] = 'documented-theorem-target'
    plan['denominator'] = cone.denominator(plan)
    plan['plan_sha256'] = cone.digest({k: v for k, v in plan.items() if k != 'plan_sha256'})
    cone.validate_plan(plan)
    with pytest.raises(ValueError, match='original target'):
        cone.bind_original(plan, world['original'], world['environment'])


def test_moving_a_lemma_to_another_citing_module_is_rejected(world):
    plan = deepcopy(world['plan'])
    shared = plan['shards'][0]['lemmas'].pop(3)
    plan['shards'][1]['lemmas'] = sorted(plan['shards'][1]['lemmas']+[shared], key=lambda l: l['name'])
    plan['denominator'] = cone.denominator(plan)
    plan['pilot']['lemmas'] = 3
    plan['plan_sha256'] = cone.digest({k: v for k, v in plan.items() if k != 'plan_sha256'})
    with pytest.raises(ValueError, match='planned environment module'):
        cone.validate_plan(plan)


def test_unknown_or_unbound_reading_identity_rejected(world):
    inputs = deepcopy(world['inputs'])
    ident = next(iter(inputs['proofs']))
    receipt = json.loads(inputs['proofs'][ident]['receipt.json'])
    receipt['module'] = GAMMA
    inputs['proofs'][ident]['receipt.json'] = json.dumps(receipt).encode()
    with pytest.raises(ValueError, match='identity'):
        cone.make_plan(inputs, IDENTITY)


def test_archive_digest_and_members(world):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        for ident, files in world['inputs']['proofs'].items():
            for name, data in files.items():
                z.writestr(f'Leanglish/proofs/{ident}/{name}', data)
        for key, files in world['inputs']['workers'].items():
            for name, data in files.items():
                z.writestr(f'Leanglish/original-evidence/proof-workers/{key}/{name}', data)
        z.writestr('Leanglish/original-evidence/plan.json', json.dumps(world['original']))
        z.writestr('Leanglish/original-evidence/environment.json', json.dumps(world['environment']))
    data = buffer.getvalue()
    with pytest.raises(ValueError, match='digest'):
        cone.read_archive(data, '0'*64)
    inputs = cone.read_archive(data, sha256(data).hexdigest())
    assert cone.make_plan(inputs, IDENTITY) == world['plan']


def test_dispatch_scopes(world):
    plan = world['plan']
    assert [s['module'] for s in cone.scope_shards(plan, 'full-1')] == [ALPHA, BETA]
    assert [s['module'] for s in cone.scope_shards(plan, 'pilot')] == [ALPHA]
    for scope in ['full-2', 'full-0', 'everything']:
        with pytest.raises(ValueError):
            cone.scope_shards(plan, scope)


# Synthetic Lean process. Lemma behaviour is chosen by name; nothing is compiled.
BEHAVIOUR = {'OAI.Alpha.lemma1': 'ok', 'OAI.Alpha.lemma2': 'declined', 'OAI.Alpha.main._proof_1': 'ok',
             'OAI.Shared.lemma': 'timeout', 'OAI.Beta.helper': 'ok'}


def fake_lean(build='passed'):
    def run(command, cwd, timeout=120, max_output=128_000_000):
        if command == ['lake', 'env', 'lean', '--version']:
            return RunResult('passed', command, 0, 'Lean (version 4.34.1, synthetic)\n', '', 0.1)
        if command[:2] == ['lake', 'build']:
            return (RunResult('passed', command, 0, 'synthetic build', '', 0.2) if build == 'passed' else
                    RunResult('failed', command, None, '', '', 0.2, 'timeout') if build == 'timeout' else
                    RunResult('failed', command, 1, '', 'error: synthetic failure', 0.2))
        name = json.loads(Path(command[3]).read_text().rsplit('#narrative ', 1)[1])
        behaviour = BEHAVIOUR[name]
        if behaviour == 'ok':
            return RunResult('passed', command, 0, 'PR_NARRATIVE:'+canonical_json(snapshot(name, ['True.intro']))+'\n', '', 0.3)
        if behaviour == 'declined':
            return RunResult('failed', command, 1, 'Driver.lean:1:0: error: Expected a proof-valued declaration\n', '', 0.3)
        return RunResult('failed', command, None, '', '', 0.3, 'timeout')
    return run


def shard_output(world, monkeypatch, tmp_path, module=ALPHA, build='passed', **kw):
    monkeypatch.setattr('proofreader.dependency_cone.run_bounded', fake_lean(build))
    monkeypatch.setattr('proofreader.narrative_io.run_bounded', fake_lean(build))
    out = tmp_path/('shard-'+module)
    report = cone.run_shard(world['project'], world['original'], world['environment'], world['plan'],
                            cone.module_id(module), out, trust_project=True, **kw)
    return out, report


def test_worker_records_every_outcome(world, monkeypatch, tmp_path):
    out, report = shard_output(world, monkeypatch, tmp_path)
    assert report['status'] == 'partial' and report['readings_generated'] == 2 and not report['complete']
    assert {r['name']: r['status'] for r in report['lemmas']} == {
        'OAI.Alpha.lemma1': 'reading-generated', 'OAI.Alpha.lemma2': 'not-proof-valued',
        'OAI.Alpha.main._proof_1': 'reading-generated', 'OAI.Shared.lemma': 'extraction-timeout'}
    report_, rows, accepted = cone.load_shard(out, world['plan'], world['environment'])
    assert sorted(accepted) == ['OAI.Alpha.lemma1', 'OAI.Alpha.main._proof_1']
    summary, _ = cone.reconcile(world['plan'], world['environment'], [out], 'full-1')
    assert summary['statuses'] == {'extraction-timeout': 1, 'not-proof-valued': 1, 'reading-generated': 2,
                                   'shard-artifact-missing': 1}
    assert summary['missing_shards'] == [cone.module_id(BETA)] and summary['planned_lemmas'] == 5
    assert cone.reading_map(summary)['OAI.Alpha.lemma1']['module'] == ALPHA
    assert summary['counts_toward_documented_target_coverage'] is False
    pilot, _ = cone.reconcile(world['plan'], world['environment'], [out], 'pilot')
    assert pilot['statuses']['not-in-run-scope'] == 1 and not pilot['missing_shards']


def test_complete_shard_and_failed_build(world, monkeypatch, tmp_path):
    out, report = shard_output(world, monkeypatch, tmp_path, module=BETA)
    assert report['status'] == 'complete' and report['readings_generated'] == 1
    out2, report2 = shard_output(world, monkeypatch, tmp_path/'b', module=ALPHA, build='failed')
    assert report2['status'] == 'partial' and set(report2['statuses']) == {'build-failed'}
    out3, report3 = shard_output(world, monkeypatch, tmp_path/'c', module=ALPHA, build='timeout')
    assert set(report3['statuses']) == {'build-timeout'}
    summary, accepted = cone.reconcile(world['plan'], world['environment'], [out, out2], 'full-1')
    assert summary['statuses'] == {'build-failed': 4, 'reading-generated': 1} and list(accepted) == ['OAI.Beta.helper']


def test_missing_dependency_cache_is_a_retained_failure(world, monkeypatch, tmp_path):
    out, report = shard_output(world, monkeypatch, tmp_path, dependency_cache=False)
    assert report['status'] == 'failed' and 'cache' in report['error'] and report['statuses'] == {'not-attempted': 4}
    summary, accepted = cone.reconcile(world['plan'], world['environment'], [out], 'pilot')
    assert summary['statuses'] == {'shard-failed': 4, 'not-in-run-scope': 1} and not accepted


def test_environment_drift_invalidates_successes(world, monkeypatch, tmp_path):
    real = cone.audit_environment
    calls = []
    def drifting(project, plan):
        calls.append(1)
        result = real(project, plan)
        return result if len(calls) == 1 else {**result, 'environment_sha256': '0'*64}
    monkeypatch.setattr('proofreader.dependency_cone.audit_environment', drifting)
    out, report = shard_output(world, monkeypatch, tmp_path)
    assert report['status'] == 'failed' and report['readings_generated'] == 0
    assert 'reading-generated' not in report['statuses'] and report['statuses']['environment-invalidated'] == 2
    _, _, accepted = cone.load_shard(out, world['plan'], world['environment'])
    assert accepted == {}


def test_worker_requires_consent_fresh_output_and_planned_shard(world, tmp_path):
    args = (world['project'], world['original'], world['environment'], world['plan'])
    with pytest.raises(PermissionError):
        cone.run_shard(*args, cone.module_id(ALPHA), tmp_path/'x')
    with pytest.raises(ValueError, match='Unknown'):
        cone.run_shard(*args, 'f'*24, tmp_path/'x', trust_project=True)
    (tmp_path/'x').mkdir()
    with pytest.raises(ValueError, match='fresh'):
        cone.run_shard(*args, cone.module_id(ALPHA), tmp_path/'x', trust_project=True)
    other = deepcopy(world['environment']); other['environment_sha256'] = '0'*64
    with pytest.raises(ValueError):
        cone.run_shard(world['project'], world['original'], other, world['plan'], cone.module_id(ALPHA), tmp_path/'y', trust_project=True)


def tamper_report(out, edit):
    report = read(out/cone.REPORT)
    edit(report)
    write(out/cone.REPORT, report)


def first(report, status):
    return next(r for r in report['lemmas'] if r['status'] == status)


@pytest.mark.parametrize('edit', [
    lambda r: r['lemmas'].pop(),
    lambda r: r['lemmas'].append(dict(r['lemmas'][0], name='OAI.Alpha.extra')),
    lambda r: r['lemmas'].reverse(),
    lambda r: r.update(cone_plan_sha256='0'*64),
    lambda r: r.update(module=BETA),
    lambda r: r.update(counts_toward_documented_target_coverage=True),
    lambda r: r.update(readings_generated=3),
    lambda r: r.update(status='complete', complete=True),
    lambda r: r.update(environment_after=None),
    lambda r: first(r, 'not-proof-valued').update(status='no-proof-body'),
    lambda r: first(r, 'extraction-timeout').update(status='not-proof-valued'),
    lambda r: first(r, 'not-proof-valued').update(kernel_checked=True),
    lambda r: first(r, 'reading-generated').update(snapshot_sha256='0'*64),
    lambda r: first(r, 'reading-generated').update(selected_judgements=7),
    lambda r: first(r, 'reading-generated').update(status='bogus'),
    lambda r: first(r, 'reading-generated').pop('directory'),
    lambda r: r['build'].update(log_sha256='0'*64),
    lambda r: r.update(source_sha256='0'*64),
])
def test_shard_tampering_rejected(world, monkeypatch, tmp_path, edit):
    out, _ = shard_output(world, monkeypatch, tmp_path)
    tamper_report(out, lambda r: (edit(r), r.update(statuses=dict(sorted(Counter(x['status'] for x in r['lemmas']).items())))))
    with pytest.raises(ValueError):
        cone.load_shard(out, world['plan'], world['environment'])


@pytest.mark.parametrize('target,edit', [
    ('Extract.lean', lambda p: p.write_text(p.read_text().replace('import OAI.Alpha.Main', 'import OAI.Beta.Main'))),
    ('stdout.txt', lambda p: p.write_text('no record')),
    ('snapshot.json', lambda p: p.write_text(p.read_text().replace('"Q"', '"R"'))),
    ('receipt.json', lambda p: write(p, {**read(p), 'module': BETA})),
    ('run.json', lambda p: write(p, {**read(p), 'exit_code': 1})),
])
def test_reading_artifact_tampering_rejected(world, monkeypatch, tmp_path, target, edit):
    out, report = shard_output(world, monkeypatch, tmp_path)
    edit(out/first(report, 'reading-generated')['directory']/target)
    with pytest.raises(ValueError):
        cone.load_shard(out, world['plan'], world['environment'])


def test_declined_outcome_must_match_its_run_observation(world, monkeypatch, tmp_path):
    out, report = shard_output(world, monkeypatch, tmp_path)
    run = out/first(report, 'not-proof-valued')['directory']/'run.json'
    write(run, {**read(run), 'stdout': 'error: unknown constant'})
    with pytest.raises(ValueError, match='run observation'):
        cone.load_shard(out, world['plan'], world['environment'])


def test_unplanned_output_and_symlinks_rejected(world, monkeypatch, tmp_path):
    out, report = shard_output(world, monkeypatch, tmp_path)
    (out/'lemmas/unplanned').mkdir()
    with pytest.raises(ValueError, match='outside the planned'):
        cone.load_shard(out, world['plan'], world['environment'])
    (out/'lemmas/unplanned').rmdir()
    target = out/first(report, 'reading-generated')['directory']/'snapshot.json'
    outside = tmp_path/'outside.json'
    outside.write_bytes(target.read_bytes()); target.unlink(); target.symlink_to(outside)
    with pytest.raises(ValueError):
        cone.load_shard(out, world['plan'], world['environment'])


def test_duplicate_or_out_of_scope_shards_rejected(world, monkeypatch, tmp_path):
    out, _ = shard_output(world, monkeypatch, tmp_path, module=BETA)
    with pytest.raises(ValueError, match='Duplicate or out-of-scope'):
        cone.reconcile(world['plan'], world['environment'], [out, out], 'full-1')
    with pytest.raises(ValueError, match='Duplicate or out-of-scope'):
        cone.reconcile(world['plan'], world['environment'], [out], 'pilot')


def test_interrupted_shard_is_never_accepted(world, monkeypatch, tmp_path):
    out, report = shard_output(world, monkeypatch, tmp_path)
    tamper_report(out, lambda r: r.update(status='running', complete=False, readings_generated=0))
    summary, accepted = cone.reconcile(world['plan'], world['environment'], [out], 'full-1')
    assert not accepted and summary['statuses']['shard-running'] == 4


def test_classification_markers(tmp_path):
    def outcome(**run):
        d = tmp_path/str(len(list(tmp_path.iterdir())))
        d.mkdir(); write(d/'run.json', run)
        return cone.classify(d)
    assert outcome(status='failed', stdout='x: error: Expected a declaration with a proof body') == 'no-proof-body'
    assert outcome(status='failed', stdout='x: error: Disallowed axiom') == 'disallowed-axiom'
    assert outcome(status='failed', stdout='', stderr='Unknown constant `OAI.x`') == 'unknown-constant'
    assert outcome(status='failed', reason='timeout') == 'extraction-timeout'
    assert outcome(status='failed', stdout='x: error: Narrative frame budget exceeded; no complete record') == 'frame-budget-exceeded'
    assert outcome(status='failed', stdout='something else') == 'extraction-failed'
    empty = tmp_path/'empty'; empty.mkdir()
    assert cone.classify(empty) == 'extraction-failed'


@pytest.mark.parametrize('name,reason', [
    ('_private.OAI.X.Main.0.OAI.X.y', 'not-addressable-by-exporter'), ('OAI.X.«weird name»', 'not-addressable-by-exporter'),
    ('OAI.X.f.match_1', 'compiler-matcher-or-recursor'), ('OAI.X.f.match_1_1', 'compiler-matcher-or-recursor'),
    ('OAI.X.T.casesOn', 'compiler-matcher-or-recursor'), ('OAI.X.instNeZeroNatM', 'instance-by-name'),
    ('OAI.X.T.mk', 'constructor-by-name'), ('OAI.X.instance_exists', None), ('OAI.X.below_threshold', None),
    ('OAI.X.rec_main', None), ('OAI.X.main._proof_1_2', None),
])
def test_name_rules(name, reason):
    assert cone.exclusion(name) == reason


# Committed plan: real retained data, validated without executing anything.
COMMITTED = ROOT/'benchmarks/dependency-cone/plan.json'


def test_committed_plan_is_valid_and_honest():
    plan = cone.validate_plan(json.loads(COMMITTED.read_text(encoding='utf-8')))
    d = plan['denominator']
    assert (d['cited_constants'], d['already_read'], d['planned_lemmas'], d['environment_modules']) == (1764, 31, 1708, 379)
    assert d['already_read']+d['excluded']+d['planned_lemmas'] == d['cited_constants']
    assert d['full_dispatch_parts'] == 2 and len(cone.scope_shards(plan, 'full-1')) == 256
    assert len(plan['pilot']['shards']) == 8 and plan['pilot']['lemmas'] == 151
    kpis = json.loads((ROOT/'benchmarks/reading-kpis/current.json').read_text())
    assert plan['inputs']['corpus_sha256'] == kpis['corpus_sha256'] and plan['inputs']['readings'] == kpis['readings']
    assert plan['execution']['exporter_sha256'] == data_digest(exporter_source()), 'Regenerate the plan after an exporter change'


def test_matrix_cli_on_committed_plan(tmp_path):
    from scripts.plan_dependency_cone import main
    output = tmp_path/'github-output'
    assert main(['matrix', '--scope', 'pilot', '--github-output', str(output)]) == 0
    lines = dict(line.split('=', 1) for line in output.read_text().splitlines())
    matrix = json.loads(lines['matrix'])
    assert lines['count'] == '8' and len(matrix['include']) == 8
    assert sum(x['lemmas'] for x in matrix['include']) == 151
    with pytest.raises(ValueError):
        main(['matrix', '--scope', 'full-3'])


def test_malformed_shard_report_rejected(world, monkeypatch, tmp_path):
    out, _ = shard_output(world, monkeypatch, tmp_path)
    write(out/cone.REPORT, [])
    with pytest.raises(ValueError, match='Malformed'):
        cone.load_shard(out, world['plan'], world['environment'])


def test_committed_plan_text_is_canonical():
    from scripts.plan_dependency_cone import plan_text
    text = COMMITTED.read_text(encoding='utf-8')
    assert plan_text(json.loads(text)) == text


@pytest.mark.skipif(not os.environ.get('LEANGLISH_RELEASE_ARCHIVE'), reason='Set LEANGLISH_RELEASE_ARCHIVE to the pinned release zip')
def test_committed_plan_regenerates_from_the_pinned_release():
    from scripts.plan_dependency_cone import main
    assert main(['plan', '--archive', os.environ['LEANGLISH_RELEASE_ARCHIVE'], '--check']) == 0


def test_workflow_is_bounded_and_never_publishes():
    yaml = pytest.importorskip('yaml')
    text = (ROOT/'.github/workflows/dependency-cone.yml').read_text()
    flow = yaml.safe_load(text)
    triggers = flow[True]
    assert triggers['push']['branches'] == ['claude/keen-archimedes-ihorkq']
    assert sorted(triggers['push']['paths']) == ['.github/workflows/dependency-cone.yml', 'benchmarks/dependency-cone/**']
    assert triggers['workflow_dispatch']['inputs']['scope']['default'] == 'pilot'
    assert flow['permissions'] == {'contents': 'read', 'actions': 'read'}
    extract = flow['jobs']['extract']
    assert extract['strategy']['max-parallel'] <= 8 and extract['timeout-minutes'] == 225
    uploads = [s for s in extract['steps'] if s.get('uses', '').startswith('actions/upload-artifact')]
    assert len(uploads) == 1 and uploads[0]['if'] == 'always()' and '${{ matrix.id }}' in uploads[0]['with']['name']
    assert 'git push' not in text and 'gh release' not in text and 'contents: write' not in text
