"""Structure of the GitHub Actions workflows and the archive inventory.

These tests read the committed workflow files; none runs a workflow or contacts
GitHub. The input-check test runs the step's script against a fake `gh` that
returns synthetic artifact listings, and the release-label test uses a
synthetic site. PyYAML comes with the dev extra; under CI a missing PyYAML is a
failure, not a skip.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tomllib

import pytest

ROOT = Path(__file__).resolve().parents[1]
ACTIVE = ROOT/'.github/workflows'
ARCHIVE = ROOT/'.github/workflow-archive'
REBUILDS = {'all-findings-release.yml': ('leanglish-all-findings-rebuild', 'leanglish-all-findings-v0.4.0'),
            'breadth-release.yml': ('leanglish-breadth-rebuild', 'leanglish-all-findings-v0.4.1')}


@pytest.fixture(scope='module')
def yaml():
    try:
        import yaml as module
    except ImportError:
        if os.environ.get('CI') == 'true':
            pytest.fail('PyYAML is missing under CI; install the dev extra')
        pytest.skip('PyYAML is not installed')
    return module


@pytest.fixture(scope='module')
def flows(yaml):
    return {p.name: yaml.safe_load(p.read_text()) for p in sorted(ACTIVE.glob('*.yml'))}


def steps(flow):
    for name, job in flow['jobs'].items():
        for step in job.get('steps', []):
            yield name, step


def triggers(flow):
    on = flow[True]  # PyYAML reads the key `on` as True.
    return set(on) if isinstance(on, dict) else {on} if isinstance(on, str) else set(on)


def test_every_workflow_file_loads(yaml):
    files = sorted(ACTIVE.glob('*.y*ml')) + sorted(ARCHIVE.glob('*.y*ml'))
    assert files and all(p.suffix == '.yml' for p in files)
    for path in files:
        flow = yaml.safe_load(path.read_text())
        assert isinstance(flow, dict) and flow.get('jobs') and triggers(flow), path.name


def test_no_kept_workflow_publishes_pushes_or_runs_on_a_schedule(flows):
    for name, flow in flows.items():
        assert not triggers(flow) & {'schedule', 'workflow_run', 'release', 'pull_request_target'}, name
        for scope in [flow, *flow['jobs'].values()]:
            permissions = scope.get('permissions', {})
            assert isinstance(permissions, dict), name
            assert all(v in ('read', 'none') for v in permissions.values()), (name, permissions)
        for _, step in steps(flow):
            run = step.get('run', '')
            for forbidden in ('gh release', 'git push', 'gh workflow run', 'gh pr ', '--method', ' -X '):
                assert forbidden not in run, (name, forbidden)
            assert 'deploy-pages' not in step.get('uses', ''), name
        assert 'secrets.' not in (ACTIVE/name).read_text(), name


def test_every_checkout_drops_its_credentials(flows):
    count = 0
    for name, flow in flows.items():
        for job, step in steps(flow):
            if step.get('uses', '').startswith('actions/checkout'):
                count += 1
                assert (step.get('with') or {}).get('persist-credentials') is False, (name, job)
    assert count >= 20


def test_no_expression_is_interpolated_into_a_shell_command(flows):
    for name, flow in flows.items():
        for job, step in steps(flow):
            assert '${{' not in step.get('run', ''), (name, job, step.get('name'))


def test_release_rebuilds_are_dispatch_only_and_labelled_as_rebuilds(flows):
    for name, (artifact, tag) in REBUILDS.items():
        flow = flows[name]
        assert triggers(flow) == {'workflow_dispatch'} and list(flow['jobs']) == ['build'], name
        assert flow['permissions'] == {'contents': 'read', 'actions': 'read'}
        text = (ACTIVE/name).read_text()
        assert tag in text and 'rebuild-of-' in text
        build = flow['jobs']['build']['steps']
        uploads = [s for s in build if s.get('uses', '').startswith('actions/upload-artifact')]
        assert [s['with']['name'] for s in uploads] == [artifact]
        check = next(i for i, s in enumerate(build) if s.get('name', '').startswith('Require every pinned input'))
        install = next(i for i, s in enumerate(build) if 'pip install' in s.get('run', ''))
        download = next(i for i, s in enumerate(build) if re.search('gh run download [0-9]', s.get('run', '')))
        assert check < install < download
        assert build[check]['env']['WORKFLOW_FILE'] == '.github/workflows/'+name


def input_check(flow) -> str:
    step = next(s for _, s in steps(flow) if s.get('name', '').startswith('Require every pinned input'))
    body = step['run']
    assert body.startswith("python - <<'PY'\n") and body.rstrip().endswith('\nPY')
    return body.split('\n', 1)[1].rsplit('\nPY', 1)[0]


def fake_gh(tmp_path: Path, listings: dict) -> dict:
    """A synthetic `gh api` that serves artifact listings by run ID."""
    (tmp_path/'listings.json').write_text(json.dumps(listings))
    gh = tmp_path/'bin/gh'
    gh.parent.mkdir()
    gh.write_text(f'#!{sys.executable}\n' + '''import json, re, sys
listings = json.load(open(%r))
match = re.fullmatch(r'repos/synthetic/repo/actions/runs/([0-9]+)/artifacts\\?per_page=100', sys.argv[2])
if sys.argv[1] != 'api' or not match or match.group(1) not in listings:
    sys.exit('HTTP 404: Not Found')
print(json.dumps(listings[match.group(1)]))
''' % str(tmp_path/'listings.json'))
    gh.chmod(0o755)
    return {**os.environ, 'PATH': f'{gh.parent}{os.pathsep}{os.environ["PATH"]}', 'GITHUB_REPOSITORY': 'synthetic/repo'}


def pins(name: str) -> list[tuple[str, str]]:
    return re.findall(r"gh run download ([0-9]+) (?:-n (\S+)|-p '([^']+)')", (ACTIVE/name).read_text())


def listing(*artifacts):
    return {'total_count': len(artifacts), 'artifacts': [{'name': n, 'expired': e} for n, e in artifacts]}


@pytest.mark.parametrize('name', sorted(REBUILDS))
def test_input_check_reads_the_download_lines_and_names_an_expired_input(flows, tmp_path, name):
    script = input_check(flows[name])
    found = pins(name)
    assert len(found) == (5 if name == 'breadth-release.yml' else 4)
    live = {run: listing(((n or p).replace('*', 'synthetic'), False)) for run, n, p in found}
    env = fake_gh(tmp_path, live)
    env['WORKFLOW_FILE'] = '.github/workflows/'+name
    ok = subprocess.run([sys.executable, '-c', script], cwd=ROOT, env=env, capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert ok.stdout.count('none expired') == len(found)
    run, n, _ = found[0]
    expired = dict(live, **{run: listing((n, True))})
    del expired[found[-1][0]]
    (tmp_path/'listings.json').write_text(json.dumps(expired))
    bad = subprocess.run([sys.executable, '-c', script], cwd=ROOT, env=env, capture_output=True, text=True)
    assert bad.returncode != 0
    assert f'::error::Pinned input unavailable: run {run} ({n}): 1 listed, expired: {n}' in bad.stdout
    assert f'run {found[-1][0]} ' in bad.stdout and 'listing failed' in bad.stdout
    assert 'docs/INPUT_PRESERVATION.md' in bad.stderr


def test_dependency_cone_token_never_reaches_project_code(flows):
    flow = flows['dependency-cone.yml']
    assert 'GH_TOKEN' not in flow.get('env', {})
    for job, step in steps(flow):
        run = step.get('run', '')
        if 'plan_dependency_cone.py dependencies' in run or 'plan_dependency_cone.py run' in run or 'lake ' in run:
            assert 'GH_TOKEN' not in (step.get('env') or {}), (job, step.get('name'))
            assert 'gh run download' not in run, (job, step.get('name'))
    assert all('GH_TOKEN' not in (j.get('env') or {}) for j in flow['jobs'].values())
    extract = next(s for _, s in steps(flow) if 'plan_dependency_cone.py run' in s.get('run', ''))
    assert extract['env']['SHARD'] == '${{ matrix.id }}' and '--shard "$SHARD"' in extract['run']


def test_ci_installs_yaml_and_compares_every_tracked_file(flows):
    extras = tomllib.loads((ROOT/'pyproject.toml').read_text())['project']['optional-dependencies']
    assert any(r.lower().startswith('pyyaml') for r in extras['dev'])
    job = flows['ci.yml']['jobs']['python-and-browser']
    runs = [s.get('run', '') for s in job['steps']]
    install = next(r for r in runs if 'pip install' in r)
    assert re.search(r"\.\[(?:[a-z,]*,)?dev[,\]]", install)
    build = next(i for i, r in enumerate(runs) if 'scripts/build_narrative_demo.py' in r)
    drift = next(i for i, r in enumerate(runs) if 'git diff --quiet' in r)
    # No pathspec: the comparison covers the whole tracked tree.
    assert build < drift and 'git diff --quiet;' in runs[drift]
    for folder in ('proofreader/data', 'artifacts/openai-sample', 'artifacts/v0.2', 'artifacts/v0.3'):
        assert folder in runs[drift].split('git status', 1)[1]


def test_path_filters_include_the_command_line_entry_point(flows):
    kpis = flows['reading-kpis.yml'][True]
    for event in ('push', 'pull_request'):
        assert {'leanglish/**', 'pyproject.toml', 'proofreader/**'} <= set(kpis[event]['paths'])
    assert {'leanglish/**', 'pyproject.toml'} <= set(flows['catalog-preview.yml'][True]['push']['paths'])


def section(text: str, heading: str) -> str:
    return text.split('## '+heading+'\n', 1)[1].split('\n## ', 1)[0]


def test_archive_readme_accounts_for_every_workflow_file():
    text = (ARCHIVE/'README.md').read_text()
    archived = {p.name for p in ARCHIVE.glob('*.yml')}
    active = {p.name for p in ACTIVE.glob('*.yml')}
    rows = [line for line in section(text, 'Archived files').split('\n') if line.startswith('| `')]
    assert sorted(re.match(r'\| `([^`]+)`', r).group(1) for r in rows) == sorted(archived)
    kept = section(text, 'Kept active')
    first_cells = [line.split(' | ')[0] for line in kept.split('\n') if line.startswith('| `')]
    assert sorted(n for cell in first_cells for n in re.findall(r'`([^`]+\.yml)`', cell)) == sorted(active)
    assert not archived & active


def test_rebuild_label_names_the_frozen_inputs_and_the_printers(tmp_path):
    """Synthetic site: two readings with different printer labels."""
    from scripts.assemble_finding_release import rebuild_label, rebuild_notice
    for ident, printer in (('a'*24, 'synthetic-printer/2'), ('b'*24, 'synthetic-printer/1')):
        path = tmp_path/'proofs'/ident/'reading.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'declarations': [{'axes': {'printer_version': printer}}]}))
    for breadth, version in ((False, '0.4.0'), (True, '0.4.1')):
        label = rebuild_label(tmp_path, breadth)
        assert label == {'release_version': 'rebuild-of-'+version,
                         'rebuild': {'inputs_of_release': 'leanglish-all-findings-v'+version,
                                     'printer_versions': ['synthetic-printer/1', 'synthetic-printer/2'],
                                     'compared_with_published_assets': False}}
        notice = rebuild_notice({**label, 'application_commit': 'c'*40})
        assert 'leanglish-all-findings-v'+version in notice and 'c'*40 in notice
        assert 'It is not that release' in notice and notice.endswith('\n\n')
    assert rebuild_label(tmp_path/'empty', False)['rebuild']['printer_versions'] == []
