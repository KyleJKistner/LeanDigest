"""The new public name is additive: no forked parsing or proof-format migration."""
from pathlib import Path
import json
import re
import subprocess
import sys
import tomllib
from unittest.mock import patch

import pytest

from leanglish import __version__
from leanglish.cli import main as leanglish_main
from proofreader.branding import PRODUCT_NAME, TAGLINE
from proofreader.cli import main as legacy_main, parser
from proofreader.render import html_document
from proofreader.source import parse_source

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('command', ['leanglish', 'proofreader'])
def test_cli_help_preserves_invocation_name(command):
    help_text = parser(command).format_help()
    assert help_text.startswith(f'usage: {command} ')
    assert PRODUCT_NAME in help_text
    assert 'extract-narrative' in help_text
    assert 'verify-kernel' in help_text


@pytest.mark.parametrize('main', [leanglish_main, legacy_main])
def test_public_version(main, capsys):
    with pytest.raises(SystemExit) as exc:
        main(['--version'])
    assert exc.value.code == 0
    assert capsys.readouterr().out.strip() == f'Leanglish {__version__}'


def test_alias_reading_json_is_identical(tmp_path):
    source = tmp_path / 'Proof.lean'
    source.write_text('theorem unchanged (P : Prop) (h : P) : P := h\n')
    a, b = tmp_path / 'a.json', tmp_path / 'b.json'
    assert leanglish_main(['read', str(source), '-o', str(a)]) == 0
    assert legacy_main(['read', str(source), '-o', str(b)]) == 0
    assert a.read_bytes() == b.read_bytes()
    assert json.loads(a.read_bytes())['schema'] == 'proofreader.document/v1'


def test_alias_error_keeps_command_name(tmp_path, capsys):
    assert leanglish_main(['read', str(tmp_path / 'absent.lean')]) == 2
    assert capsys.readouterr().err.startswith('leanglish: ')
    assert legacy_main(['read', str(tmp_path / 'absent.lean')]) == 2
    assert capsys.readouterr().err.startswith('proofreader: ')


@pytest.mark.parametrize('command', ['leanglish', 'proofreader'])
def test_module_entrypoints(command):
    result = subprocess.run([sys.executable, '-m', command, '--help'], cwd=ROOT,
                            text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(f'usage: {command} ')


def test_distribution_retains_old_name_and_both_scripts():
    project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']
    assert project['name'] == 'lean-proofreader'
    assert project['scripts']['proofreader'] == 'proofreader.cli:main'
    assert project['scripts']['leanglish'] == 'leanglish.cli:main'


def test_branding_is_single_pass_and_does_not_mutate_document():
    source = 'def marker := "__PRODUCT_NAME__ __TAGLINE__ __VERSION__"\n'
    doc = parse_source(source)
    doc.title = '<unsafe> __PRODUCT_NAME__'
    before = doc.to_json()
    page = html_document(doc)
    assert '<title>Leanglish — &lt;unsafe&gt; __PRODUCT_NAME__</title>' in page
    assert TAGLINE in page
    assert f'class="version">{__version__}</span>' in page
    assert doc.to_json() == before
    payload = re.search(r'<script id="proofreader-data" type="application/json">(.*?)</script>',
                        page, re.S)
    assert payload is not None
    data = json.loads(payload.group(1))['document']
    assert data['files'][0]['source'] == source
    assert data['title'] == doc.title


def test_alias_does_not_bypass_remote_consent(tmp_path):
    context = tmp_path / 'Example.lean'
    context.write_text('import Lean\ntheorem t : True := True.intro\n')
    with patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network')):
        assert leanglish_main(['extract-narrative', 't', '--backend', 'axle',
                              '--context', str(context), '-o', str(tmp_path / 'out')]) == 2


def test_alias_demo_remains_offline(tmp_path):
    output = tmp_path / 'reader.html'
    with patch('urllib.request.urlopen', side_effect=AssertionError('Unexpected network')):
        assert leanglish_main(['narrative-demo', '-o', str(output)]) == 0
    assert '<title>Leanglish — ' in output.read_text()
