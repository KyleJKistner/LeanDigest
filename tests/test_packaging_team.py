from pathlib import Path
import importlib.util
import json
import pytest
from proofreader.cli import demo_document, main
from proofreader.lean import exporter_path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('team_script', ROOT/'scripts/team.py')
team=importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)


def test_packaged_exporter_matches_source():
    assert exporter_path().read_bytes() == (ROOT/'lean/ProofReader.lean').read_bytes()


def test_packaged_demo_has_nine_unchecked_declarations(tmp_path):
    d=demo_document()
    assert len(d.declarations)==9
    assert all(x.evidence=='source' and not x.receipt for x in d.declarations)
    assert d.provenance['inventory_complete'] is False
    assert main(['demo','-o',str(tmp_path/'demo.html')])==0
    assert (tmp_path/'demo.html').stat().st_size>10000


def test_four_bounded_context_packs(tmp_path):
    tasks=team.load_tasks(ROOT)
    assert len(tasks)==4
    for task in tasks:
        packet=team.context_packet(ROOT,task)
        assert task['goal'] in packet and 'Required return' in packet
    assert team.main(['--output',str(tmp_path/'pack')])==0
    result=json.loads((tmp_path/'pack/team-results.json').read_text())
    assert result['mode']=='prepare' and result['independent_agents_started']==0


def test_agent_command_no_implicit_provider_or_shell():
    assert team.expand_command(['agent','{prompt}','{worktree}'],Path('/p'),Path('/w'))==['agent','/p','/w']
    with pytest.raises(ValueError):team.expand_command(['agent'],Path('/p'),Path('/w'))
    with pytest.raises(ValueError):team.expand_command([],Path('/p'),Path('/w'))
    assert team.owned('tests/audit/falsifier.py',['tests/audit/'])
    assert not team.owned('proofreader/core.py',['tests/audit/'])


def test_team_refuses_execution_without_explicit_command(tmp_path):
    assert team.main(['--output',str(tmp_path/'pack'),'--execute'])==2
    assert not (tmp_path/'pack/worktrees').exists()
