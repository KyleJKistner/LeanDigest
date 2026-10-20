"""Checkpoint availability must never be treated as proof acceptance."""
import os
from pathlib import Path
import shutil
from unittest.mock import patch
import pytest
from proofreader import build_resume as br
from proofreader.lean import RunResult
from proofreader.original_project import make_plan, audit_environment, read, write, file_hash, TOOLCHAIN
from test_original_project import fixture_project


def setup_case(tmp_path):
    project, inventory, _ = fixture_project(tmp_path)
    # Real Lean dependencies ignore generated .lake output. Match that fixture
    # behavior without weakening the production dependency-source audit.
    exclude = project / '.lake/packages/example/.git/info/exclude'
    with exclude.open('a') as stream:
        stream.write('\n.lake/\n')
    plan = make_plan(project, inventory)
    environment = audit_environment(project, plan)
    state = tmp_path / 'state'
    br.initialize(project, plan, environment, state, 'OAI', trust_project=True)
    return project, plan, environment, state


def add_build_files(project):
    entries = {
        '.lake/build/lib/lean/OAI.olean': b'compiled-example',
        '.lake/packages/example/.lake/build/lib/lean/A.olean': b'compiled-dependency',
    }
    for relative, body in entries.items():
        path = project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(body)


@pytest.mark.parametrize('name', ['lakefile.lean', 'Solution.lean', '.lake/build',
                                  '.lake/packages/example/A.lean'])
def test_source_paths_are_not_build_paths(name):
    assert not br.allowed_path(name, {'example': {}})


def test_initialize_requires_permission_and_planned_target(tmp_path):
    project, inventory, _ = fixture_project(tmp_path)
    plan = make_plan(project, inventory)
    environment = audit_environment(project, plan)
    with pytest.raises(PermissionError):
        br.initialize(project, plan, environment, tmp_path / 'state', 'OAI')
    with pytest.raises(ValueError):
        br.initialize(project, plan, environment, tmp_path / 'state', 'Other', trust_project=True)


def test_delta_restore_keeps_proof_status_false(tmp_path):
    project, plan, environment, state = setup_case(tmp_path)
    add_build_files(project)
    archive = tmp_path / 'checkpoint.tar.gz'
    result = br.pack(project, plan, environment, state, archive)
    assert result['changed_files'] == 2
    assert result['proof_verified'] is False
    for name in br.assets(project, plan['dependencies']):
        br.child(project, name).unlink()
    restored = br.restore(project, plan, environment, state, archive,
                          result['archive_sha256'], trust_project=True)
    assert restored['restored_files'] == 2
    assert restored['build_passed'] is False
    assert restored['proof_verified'] is False
    assert audit_environment(project, plan) == environment


def test_old_success_flag_does_not_skip_actual_build(tmp_path):
    project, plan, environment, state = setup_case(tmp_path)
    record = read(state / 'state.json')
    record['build_passed'] = True
    write(state / 'state.json', record)
    def execute(command, cwd, **kwargs):
        assert command == ['lake', 'build', 'OAI']
        assert cwd == project
        return RunResult('passed', command, 0, 'Build completed', '', 1.0)
    with patch.object(br, 'run_bounded', side_effect=execute) as called:
        result = br.run_round(project, plan, environment, state, tmp_path / 'round',
                              trust_project=True, seconds=2)
    assert called.call_count == 1
    assert result['status'] == 'passed'
    assert result['proof_verified'] is False


def test_timeout_preserves_partial_build_without_success(tmp_path):
    project, plan, environment, state = setup_case(tmp_path)
    def execute(command, cwd, **kwargs):
        add_build_files(project)
        return RunResult('failed', command, -9, 'partial', '', 2.0, 'timeout')
    with patch.object(br, 'run_bounded', side_effect=execute):
        result = br.run_round(project, plan, environment, state, tmp_path / 'round',
                              trust_project=True, seconds=2)
    assert result['status'] == 'timeout'
    assert read(state / 'state.json')['build_passed'] is False
    assert br.pack(project, plan, environment, state, tmp_path / 'partial.tar.gz')['changed_files'] == 2


@pytest.mark.parametrize('field', ['plan_sha256', 'environment_sha256', 'baseline_sha256'])
def test_changed_state_identity_is_rejected(tmp_path, field):
    project, plan, environment, state = setup_case(tmp_path)
    record = read(state / 'state.json')
    record[field] = '0' * 64
    write(state / 'state.json', record)
    with pytest.raises(ValueError):
        br.pack(project, plan, environment, state, tmp_path / 'bad.tar.gz')


def test_changed_archive_digest_is_rejected(tmp_path):
    project, plan, environment, state = setup_case(tmp_path)
    archive = tmp_path / 'checkpoint.tar.gz'
    br.pack(project, plan, environment, state, archive)
    with pytest.raises(ValueError):
        br.restore(project, plan, environment, state, archive, '0' * 64, trust_project=True)


REQUIRED = os.environ.get('PROOFREADER_REQUIRE_LEAN') == '1'
@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED, reason='Native checkpoint integration requires Lean/Lake')
def test_native_checkpoint_roundtrip(tmp_path):
    if not shutil.which('lake'):
        pytest.fail('Required native checkpoint gate cannot skip')
    project = tmp_path / 'native'
    project.mkdir()
    (project / 'lean-toolchain').write_text(TOOLCHAIN + '\n')
    (project / 'lakefile.lean').write_text('import Lake\nopen Lake DSL\npackage OAI\n@[default_target] lean_lib OAI\n')
    write(project / 'lake-manifest.json', {'version': '1.2.0', 'packagesDir': '.lake/packages',
                                         'packages': [], 'name': 'OAI', 'lakeDir': '.lake'})
    (project / 'OAI.lean').write_text('theorem checked : True := True.intro\n')
    write(project / 'ComparatorChallenges/A.json', {'challenge_module': 'OAI',
          'solution_module': 'OAI', 'theorem_names': ['checked']})
    inventory = [{'path': 'lean/' + path.relative_to(project).as_posix(), 'sha256': file_hash(path)}
                 for path in project.rglob('*') if path.is_file()]
    plan = make_plan(project, inventory)
    environment = audit_environment(project, plan)
    state = tmp_path / 'state'
    br.initialize(project, plan, environment, state, 'OAI', trust_project=True)
    first = br.run_round(project, plan, environment, state, tmp_path / 'first', trust_project=True, seconds=90)
    assert first['status'] == 'passed'
    archive = tmp_path / 'native.tar.gz'
    info = br.pack(project, plan, environment, state, archive)
    assert info['changed_files'] > 0
    shutil.rmtree(project / '.lake/build')
    br.restore(project, plan, environment, state, archive, info['archive_sha256'], trust_project=True)
    assert read(state / 'state.json')['build_passed'] is False
    second = br.run_round(project, plan, environment, state, tmp_path / 'second', trust_project=True, seconds=90)
    assert second['status'] == 'passed'
    assert audit_environment(project, plan) == environment
