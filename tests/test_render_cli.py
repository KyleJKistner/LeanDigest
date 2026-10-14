import json
import subprocess
import sys
from pathlib import Path
import pytest
from proofreader.render import *
from proofreader.source import parse_source
from proofreader.cli import main


def test_embedded_data_cannot_close_script():
    source='/- </script><script>globalThis.pwned=true</script> -/\ntheorem t : True := by trivial\n'
    d=parse_source(source)
    h=html_document(d)
    assert '</script><script>globalThis.pwned' not in h
    assert '\\u003c/script' in h
    assert '<script src=' not in h


def test_html_is_self_contained_and_deterministic():
    d=parse_source('theorem t : True := by trivial')
    assert html_document(d)==html_document(d)
    assert 'cdn.' not in html_document(d)


def test_document_roundtrip_preserves_ir():
    d=parse_source('namespace N\ntheorem x : True := by trivial\nend N\n')
    assert load_document(d.to_json()).to_json()==d.to_json()


def test_unsupported_schema_fails():
    with pytest.raises(ValueError):load_document({'schema':'x'})


def test_markdown_keeps_evidence():
    md=markdown_document(parse_source('theorem t : True := by trivial'))
    assert 'not certified' in md and '```lean' in md


def test_cli_read_does_not_require_lean(tmp_path):
    f=tmp_path/'Proof.lean';f.write_text('theorem t : True := by trivial')
    out=tmp_path/'index.html'
    assert main(['read',str(f),'--output',str(out)])==0
    assert out.is_file() and 'ProofReader' in out.read_text()


def test_cli_gate_fails_closed(tmp_path):
    f=tmp_path/'coverage.json';f.write_text('{}')
    assert main(['gate',str(f),'--level','english'])==2


def test_cli_bad_input_is_controlled_error(tmp_path):
    assert main(['read',str(tmp_path/'missing.lean')])==2


def test_template_markers_inside_source_survive_exactly():
    d=parse_source('def x := "__TITLE__ /*__APP__*/ __DOCUMENT_DATA__"')
    h=html_document(d)
    import re
    payload=re.search(r'<script id="proofreader-data" type="application/json">(.*?)</script>',h,re.S).group(1)
    restored=json.loads(payload)['document']
    assert restored['files'][0]['source']==d.files[0]['source']
