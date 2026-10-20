"""Static reader integration for the two checked cancellation sentences.

This validates an unsigned, reviewed native observation. It does not run Lean or
turn arbitrary JSON into a proof. The complete positive record is pinned, in
addition to all declared hashes and source/module identities.
"""
from __future__ import annotations

from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'artifacts/source-cancellation'
TARGET = 'OAI.ComplexCancellation.BezoutFrame.exists_frame'
SOURCE_HASH = 'd108afa98f200bfce183b8afc0af586b70734f7ad2cce1bc5e49853a2f555c6f'
RECORD_HASH = 'f8eea70b40b08772d17bd222e41548d6afa097e721216b64cd9e5cf5cf227751'


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def read_json(path: Path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate source-text JSON key')
            result[key] = value
        return result
    if path.is_symlink():
        raise ValueError('Source-text evidence must not be a symlink')
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique)


def load_cancellations(path: Path = EVIDENCE) -> dict:
    try:
        report = read_json(path / 'observation.json')
        if not isinstance(report, dict):
            raise ValueError('Source-text observation must be an object')
        if (report.get('schema') != 'leanglish.source-cancellation/v1'
                or report.get('status') != 'passed' or report.get('theorem') != TARGET
                or report.get('source_sha256') != SOURCE_HASH
                or type(report.get('certified_sentence_count')) is not int
                or report.get('certified_sentence_count') != 2
                or report.get('repeat_byte_identical') is not True
                or type(report.get('native_negative_cases')) is not int
                or report.get('native_negative_cases') != 12
                or type(report.get('native_parser_guards')) is not int
                or report.get('native_parser_guards') != 32):
            raise ValueError('Incomplete source-text observation')
        for flag in ('complete_english_proof_certified', 'original_project_replayed',
                     'receipt_authenticated', 'html_semantics_proved'):
            if report.get(flag) is not False:
                raise ValueError('Source-text observation overstates its scope')
        files = report['files_sha256']
        if not isinstance(files, dict) or not files:
            raise ValueError('Missing source-text file inventory')
        for name, expected in files.items():
            if not isinstance(name, str) or Path(name).name != name or name in {'.', '..'} or '\\' in name:
                raise ValueError('Invalid source-text evidence path')
            member = path / name
            if member.is_symlink() or digest(member) != expected:
                raise ValueError('Changed source-text evidence file: ' + name)
        for name in ('positive.json', 'repeat.json', 'cancellation-0.txt', 'cancellation-1.txt'):
            if name not in files:
                raise ValueError('Required source-text evidence missing')
        if digest(path / 'positive.json') != RECORD_HASH or (path / 'positive.json').read_bytes() != (path / 'repeat.json').read_bytes():
            raise ValueError('Reviewed source-text record changed')
        if report['environment']['mathlib_commit'] != 'd13f23b723b8a846827a245b89c10fc7d3f11612':
            raise ValueError('Source-text Mathlib pin changed')
        required = {'ControlledEnglish.lean', 'ControlledEnglishText.lean',
                    'ArithmeticEnglish.lean', 'SourceCancellation.lean', 'ArithmeticEnglishAudit.lean'}
        if set(report['module_sha256']) != required:
            raise ValueError('Source-text module inventory changed')
        for name, expected in report['module_sha256'].items():
            if digest(ROOT / 'lean' / name) != expected:
                raise ValueError('Source-text module has changed since checking: ' + name)
        if digest(ROOT / 'scripts/check_source_cancellation.py') != report['gate_sha256']:
            raise ValueError('Source-text gate has changed since checking')
        negatives = {'wrong-nonzero', 'wrong-premise', 'wrong-conclusion', 'text-tamper',
                     'wrong-label-map', 'wrong-operation', 'proof-replacement', 'unknown-mode',
                     'kernel-claim-tamper', 'kernel-flag-bypass', 'wrong-path', 'duplicate-path'}
        positives = {'version', 'ControlledEnglish', 'ControlledEnglishText', 'ArithmeticEnglish',
                     'SourceCancellation', 'ArithmeticEnglishAudit', 'positive', 'repeat'}
        commands = report['commands']
        if len(commands) != 20 or {c['label'] for c in commands} != positives | negatives:
            raise ValueError('Source-text command inventory changed')
        for command in commands:
            rc = command.get('returncode')
            if (type(rc) is not int or command.get('timed_out')
                    or command.get('expected_outcome_observed') is not True
                    or ((rc == 0) != (command['label'] in positives))):
                raise ValueError('Incomplete native source-text check')
            name = command['label'] + '.log'
            if files.get(name) != command['stdout_sha256']:
                raise ValueError('Native source-text log identity mismatch')
        records = read_json(path / 'positive.json')
        for i, record in enumerate(records):
            if bytes(record['utf8']) != (path / f'cancellation-{i}.txt').read_bytes():
                raise ValueError('Displayed cancellation differs from certified bytes')
        return {'observation': report, 'sentences': records,
                'record_sha256': RECORD_HASH,
                'observation_sha256': digest(path / 'observation.json')}
    except (OSError, KeyError, TypeError, AttributeError, json.JSONDecodeError) as exc:
        raise ValueError('Source-text evidence is missing or malformed') from exc


def cancellation_panel(record: dict, frame: int) -> str:
    # No reformulation, math pretty-printer, or language-model call after Lean.
    return (f'<details class="checked-cancellation" data-source-frame="{frame}">'
            '<summary>Checked cancellation sentence</summary>'
            f'<p class="checked-sentence">{escape(record["text"])}</p>'
            f'<p class="small muted">Source frame {frame}. The text and its UTF-8 bytes '
            'have kernel-checked meanings in this source context.</p></details>')
