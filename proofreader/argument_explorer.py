"""Build an offline argument explorer; formulas remain the snapshot's exact strings."""
from __future__ import annotations

from pathlib import Path
import re

from .argument_index import ArgumentIndex, validate_index
from .kernel import require
from .model import canonical_json, digest

SCHEMA = 'leanglish.argument-explorer/v1'
ROOT = Path(__file__).resolve().parent / 'web'


def make_item(record: dict, source: dict | None = None) -> dict:
    index = ArgumentIndex(record)
    navigation = index.to_dict()
    validate_index(index.snapshot.record, navigation)
    if source is not None:
        require(isinstance(source, dict) and set(source) == {'path', 'sha256', 'source'},
                'Invalid explorer source record')
        require(all(isinstance(v, str) for v in source.values())
                and digest(source['source']) == source['sha256'], 'Source file digest mismatch')
    return {'id': index.snapshot.sha256, 'snapshot': index.snapshot.record,
            'index': navigation, 'source': source}


def validate_bundle(bundle: dict) -> None:
    require(isinstance(bundle, dict) and set(bundle) == {'schema', 'title', 'cohort_sha256', 'items'},
            'Unknown or missing explorer fields')
    require(bundle['schema'] == SCHEMA and isinstance(bundle['title'], str)
            and len(bundle['title']) <= 200, 'Invalid explorer metadata')
    require(bundle['cohort_sha256'] is None or (isinstance(bundle['cohort_sha256'], str)
            and len(bundle['cohort_sha256']) == 64
            and all(c in '0123456789abcdef' for c in bundle['cohort_sha256'])), 'Invalid cohort digest')
    require(isinstance(bundle['items'], list) and 0 < len(bundle['items']) <= 1000,
            'Explorer needs between one and one thousand proofs')
    seen: set[str] = set()
    for item in bundle['items']:
        require(isinstance(item, dict) and set(item) == {'id', 'snapshot', 'index', 'source'},
                'Invalid explorer item')
        validate_index(item['snapshot'], item['index'])
        require(isinstance(item['id'], str) and item['id'] == item['index']['snapshot_sha256']
                and item['id'] not in seen, 'Duplicate or incorrect explorer identity')
        seen.add(item['id'])
        if item['source'] is not None:
            source = item['source']
            require(isinstance(source, dict) and set(source) == {'path', 'sha256', 'source'}
                    and all(isinstance(v, str) for v in source.values())
                    and digest(source['source']) == source['sha256'], 'Source file digest mismatch')


def html(bundle: dict) -> str:
    validate_bundle(bundle)
    payload = canonical_json(bundle).replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    payload = payload.replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    template = (ROOT / 'argument-explorer.html').read_text(encoding='utf-8')
    replacements = {'@STYLE@': (ROOT / 'argument-explorer.css').read_text(encoding='utf-8'),
                    '@DATA@': payload,
                    '@SCRIPT@': (ROOT / 'argument-explorer.js').read_text(encoding='utf-8')}
    require(all(template.count(marker) == 1 for marker in replacements),
            'Explorer template marker mismatch')
    # Replace markers only in the template, never in inserted source text.
    return re.sub(r'@(?:STYLE|DATA|SCRIPT)@', lambda m: replacements[m[0]], template)
