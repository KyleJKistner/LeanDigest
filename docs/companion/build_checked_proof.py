#!/usr/bin/env python3
"""Build the canonical proof page from the frozen native certificate.

The page contains the native text verbatim. Presentation markup is not included
in the formal certificate; tests separately compare the DOM text and downloads.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from proofreader.document_text import EVIDENCE, MODULES, SOURCE, TARGET, load_document

HERE = Path(__file__).resolve().parent
ORDER = [('equations', 0), ('equations', 1), ('equations', 2), ('equations', 3),
         ('witnesses', 0), ('equations', 4), ('cancellations', 0), ('equations', 5),
         ('cancellations', 1), ('equations', 6), ('equations', 7), ('equations', 8),
         ('equations', 9), ('witnesses', 1)]


def structural_markup(text: str) -> str:
    """Add presentation spans without changing the underlying characters."""
    parts, cursor = [], 0
    for match in re.finditer(r'(?m)^(Statement|Proof|Zero case|Nonzero case|Conclusion)$', text):
        parts.extend((escape(text[cursor:match.start()]),
                      '<span class="structural-heading">' + escape(match[0]) + '</span>'))
        cursor = match.end()
    parts.append(escape(text[cursor:]))
    return ''.join(parts)


def proof_markup(text: str, record: dict) -> str:
    parts, cursor = [], 0
    for kind, index in ORDER:
        passage = record[kind][index]['text']
        start = text.find(passage, cursor)
        if (start < cursor or text[start + len(passage):start + len(passage) + 2] != '\n\n'):
            raise ValueError('Document passage missing or out of sequence')
        parts.append(structural_markup(text[cursor:start]))
        parts.append(f'<span class="source-passage" role="button" tabindex="0" '
                     f'data-kind="{kind}" data-index="{index}" '
                     f'aria-label="View source for {escape(passage, quote=True)}">'
                     + escape(passage) + '</span>')
        cursor = start + len(passage)
    parts.append(structural_markup(text[cursor:]))
    return ''.join(parts)


def build(output: Path | None = None, *, evidence_root: Path = EVIDENCE) -> dict:
    output = HERE / 'checked-proof.html' if output is None else output
    checked = load_document(evidence_root)
    record = checked['record']
    payload = {'record': record, 'observation': checked['observation'],
               'text': checked['text'], 'source': (ROOT / SOURCE).read_text(encoding='utf-8')}
    # JSON is a data island, not code. Escape HTML delimiters to prevent script closure.
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    data = data.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    replacements = {
        '__PROOF__': proof_markup(checked['text'], record),
        '__SOURCE__': escape(payload['source']),
        '__DATA__': data,
        '__TEXT_HASH__': checked['text_sha256'],
        '__RECORD_HASH__': checked['record_sha256'],
        '__TARGET__': escape(TARGET),
        '__STYLE__': (HERE / 'checked-proof.css').read_text(encoding='utf-8'),
        '__SCRIPT__': (HERE / 'checked-proof.js').read_text(encoding='utf-8'),
    }
    template = (HERE / 'checked-proof-template.html').read_text(encoding='utf-8')
    for key in replacements:
        if template.count(key) != 1:
            raise ValueError('Checked proof template slot is missing or repeated: ' + key)
    # Single pass: no placeholders inside mathematical/source data are reinterpreted.
    page = re.sub('|'.join(map(re.escape, replacements)), lambda m: replacements[m[0]], template)
    manifest = {
        'schema': 'leanglish.canonical-proof-page/v1', 'theorem': TARGET,
        'canonical_text_sha256': checked['text_sha256'],
        'native_record_sha256': checked['record_sha256'],
        'native_observation_sha256': checked['observation_sha256'],
        'index_sha256': sha256(page.encode('utf-8')).hexdigest(),
        'canonical_document_certified': True, 'authored_companion_certified': False,
        'html_semantics_proved': False, 'lean_executed_by_build': False,
        'network_requests_by_build': False, 'source_passages': len(ORDER),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(page.encode('utf-8'))
    output.with_suffix('.manifest.json').write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--evidence-root', type=Path, default=EVIDENCE)
    args = parser.parse_args()
    print(json.dumps(build(args.output, evidence_root=args.evidence_root), indent=2))
