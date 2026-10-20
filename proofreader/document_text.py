"""Load one frozen, source-bound canonical proof document.

This reconciles an unsigned native observation with reviewed bytes and source.
It neither executes Lean nor authenticates an untrusted compiler or runner.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

from .source_text import SOURCE_HASH, TARGET, digest, read_json

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'artifacts/source-document'
RECORD_HASH = 'a616f24f83f634bedd4ae329623141eae02d4176f77d87ef5339ad834d634a5d'
UPSTREAM = '1581d4cbdd69a0faf34b2089614fe2a814316a6a'
MATHLIB = 'd13f23b723b8a846827a245b89c10fc7d3f11612'
MODULES = ('ControlledEnglish', 'ControlledEnglishText', 'ArithmeticEnglish', 'SourceCancellation',
           'EquationEnglish', 'SourceEquations', 'WitnessEnglish', 'SourceWitnesses',
           'ProofDocumentSyntax', 'ProofDocument', 'SourceProofDocument', 'ProofDocumentAudit')
CONTRACTS = ('parseFragments_chars', 'read_render', 'Document.render_injective', 'Document.sound',
             'rendered_meaning', 'certify', 'text_implies_statement', 'readBytes_render',
             'rendered_bytes_meaning', 'certifyBytes', 'bytes_imply_statement')
NEGATIVES = {
    'wrong-case': 'Document case condition mismatch',
    'scope-name': 'Document contains unbound names or different frame inputs',
    'wrong-input': 'Document contains unbound names or different frame inputs',
    'unproved-let': 'Application type mismatch',
    'unproved-alias': 'Application type mismatch',
    'text-tamper': 'Document literal text mismatch',
    'wrong-branch': 'Application type mismatch',
    'kernel-claim': '(kernel) declaration type mismatch',
    'kernel-bypass': '(kernel) declaration type mismatch',
    'missing-equation': 'Incomplete document passage inventory',
    'duplicate-equation': 'Document equation order or inventory mismatch',
    'reordered-equations': 'Document equation order or inventory mismatch',
    'missing-branch': 'Incomplete document passage inventory',
    'swapped-branches': 'Document branch occurrence mismatch',
    'wrong-prerequisite': 'Document cancellation prerequisite mismatch',
    'unknown-variant': 'Unknown document-check variant',
}
ALLOWED_AXIOMS = {'propext', 'Classical.choice', 'Quot.sound'}
POSITIVES = ('version', *MODULES, 'positive', 'repeat')
COMMANDS = (*POSITIVES, *NEGATIVES)
SOURCE = 'examples/openai/lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean'
HELPERS = ('check_source_cancellation.py', 'check_source_equations.py')
FLAGS_FALSE = ('curated_explanation_certified', 'original_project_replayed',
               'html_semantics_proved', 'receipt_authenticated', 'human_readability_evaluated')
EXPECTED_FILES = ({label + '.log' for label in COMMANDS}
                  | {label + suffix for label in ('positive', 'repeat', *NEGATIVES)
                     for suffix in ('.lean', '-config.json')}
                  | {'positive.json', 'repeat.json', 'proof.txt'})


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _axioms(value) -> bool:
    return (isinstance(value, list) and all(isinstance(a, str) for a in value)
            and len(value) == len(set(value)) and not set(value) - ALLOWED_AXIOMS)


def load_document(path: Path = EVIDENCE) -> dict:
    """Accept only the reviewed document and a complete, consistent observation."""
    try:
        _require(not path.is_symlink(), 'Document evidence directory is a symlink')
        report = read_json(path / 'observation.json')
        _require(isinstance(report, dict), 'Document observation must be an object')
        for key, expected in [('schema', 'leanglish.source-document/v1'), ('status', 'passed'),
                              ('theorem', TARGET), ('upstream_commit', UPSTREAM),
                              ('source_sha256', SOURCE_HASH),
                              ('certified_surface', 'bezout-scoped-document/v1')]:
            _require(report.get(key) == expected, 'Document observation identity changed: ' + key)
        for key in ('complete_canonical_document_certified', 'repeat_byte_identical'):
            _require(report.get(key) is True, 'Incomplete canonical document check')
        for key in FLAGS_FALSE:
            _require(report.get(key) is False, 'Document observation overstates its scope')
        for key, expected in [('canonical_document_count', 1), ('source_passage_count', 14),
                              ('equation_link_count', 19), ('source_negative_cases', 16),
                              ('parser_guards', 30)]:
            _require(type(report.get(key)) is int and report[key] == expected,
                     'Document coverage inventory changed: ' + key)
        files = report['files_sha256']
        _require(isinstance(files, dict) and set(files) == EXPECTED_FILES,
                 'Document file inventory changed')
        _require({p.name for p in path.iterdir()} == EXPECTED_FILES | {'observation.json'},
                 'Missing or additional document evidence')
        for name, expected in files.items():
            member = path / name
            _require(not member.is_symlink() and member.is_file() and digest(member) == expected,
                     'Document evidence bytes changed: ' + name)
        _require(digest(path / 'positive.json') == RECORD_HASH,
                 'Reviewed document record changed')
        _require((path / 'positive.json').read_bytes() == (path / 'repeat.json').read_bytes(),
                 'Document native records did not repeat')
        record = read_json(path / 'positive.json')
        document = record['document']
        text = document['text']
        _require(isinstance(text, str) and (path / 'proof.txt').read_bytes() == text.encode('utf-8')
                 and bytes(document['utf8']) == text.encode('utf-8'),
                 'Document text differs from certified bytes')
        _require(type(document['closed_outer_binders']) is int
                 and document['closed_outer_binders'] == 2,
                 'Document has residual outer assumptions')
        _require(all(document[k] is True for k in ('both_branches_composed',
                 'literal_document_kernel_checked', 'source_statement_kernel_checked')),
                 'Incomplete document composition')
        _require(_axioms(document['axioms']), 'Unpermitted document axioms')
        _require(report['environment']['mathlib_commit'] == MATHLIB,
                 'Document Mathlib revision changed')
        _require(digest(ROOT / SOURCE) == SOURCE_HASH, 'Original theorem source changed')
        version = (path / 'version.log').read_text(encoding='utf-8').strip()
        _require(version == report['lean_version'] and version.startswith('Lean (version 4.34.1,'),
                 'Document compiler version changed')
        required_modules = {m + '.lean' for m in MODULES}
        _require(set(report['module_sha256']) == required_modules, 'Document module inventory changed')
        for name, expected in report['module_sha256'].items():
            _require(digest(ROOT / 'lean' / name) == expected, 'Document checked module changed: ' + name)
        _require(report['gate_sha256'] == digest(ROOT / 'scripts/check_source_document.py'),
                 'Document native gate changed since checking')
        _require(set(report['helper_sha256']) == set(HELPERS), 'Document helper inventory changed')
        for name, expected in report['helper_sha256'].items():
            _require(digest(ROOT / 'scripts' / name) == expected, 'Document checking helper changed')
        _require(report['configuration'] == read_json(path / 'positive-config.json')
                 == read_json(path / 'repeat-config.json'), 'Document path configuration changed')
        for kind, name in [('equations', 'equation'), ('witnesses', 'witness'),
                           ('cancellations', 'cancellation')]:
            _require(report['configuration'][kind] == read_json(ROOT / f'docs/companion/{name}-paths.json'),
                     'Document path manifest changed')
            _require([row['path'] for row in record[kind]] == report['configuration'][kind],
                     'Document original occurrence paths changed')
        prefix = 'import OAI.Algebra.AffineCancellation.Model\n'
        source = (ROOT / SOURCE).read_text(encoding='utf-8')
        _require(source.startswith(prefix), 'Document original import boundary changed')
        from hashlib import sha256
        _require(report['import_adaptation'] == {
            'removed': ['OAI.Algebra.AffineCancellation.Model'],
            'added': ['Mathlib.Algebra.EuclideanDomain.Basic', 'Mathlib.Tactic.Ring', 'SourceProofDocument'],
            'body_sha256': sha256(source[len(prefix):].encode()).hexdigest(),
            'theorem_body_unchanged': True}, 'Document import adaptation changed')
        commands = report['commands']
        _require(isinstance(commands, list) and [c['label'] for c in commands] == list(COMMANDS),
                 'Document command inventory changed')
        for command in commands:
            label = command['label']
            rc = command.get('returncode')
            _require(type(rc) is int and not command.get('timed_out')
                     and command.get('expected_outcome_observed') is True
                     and ((rc == 0) == (label in POSITIVES)), 'Incomplete document native check')
            _require(command['stdout_sha256'] == files[label + '.log'], 'Document log identity mismatch')
            log = (path / (label + '.log')).read_text(encoding='utf-8')
            if label in NEGATIVES:
                _require(NEGATIVES[label] in log and 'SOURCE_DOCUMENT_CHECKED:1' not in log,
                         'Document negative control has the wrong outcome')
            elif label in ('positive', 'repeat'):
                _require(log.count('SOURCE_DOCUMENT_CHECKED:1') == 1,
                         'Document acceptance marker missing or repeated')
        contracts = report['contract_axioms']
        _require(isinstance(contracts, dict) and set(contracts) == set(CONTRACTS)
                 and all(_axioms(v) for v in contracts.values()), 'Document contract inventory changed')
        log = (path / 'ProofDocument.log').read_text(encoding='utf-8')
        pattern = r"'ProofReader\.BezoutDocument\.([^']+)' (?:depends on axioms: \[([^\]]*)\]|does not depend on any axioms)"
        observations = re.findall(pattern, log)
        _require(len(observations) == len(CONTRACTS), 'Missing or repeated document axiom inventory')
        found = {name: [a.strip() for a in raw.split(',') if a.strip()] for name, raw in observations}
        _require(found == contracts and 'sorryAx' not in log, 'Document axiom log mismatch')
        return {'record': record, 'text': text, 'observation': report,
                'record_sha256': RECORD_HASH, 'text_sha256': digest(path / 'proof.txt'),
                'observation_sha256': digest(path / 'observation.json')}
    except (OSError, KeyError, TypeError, AttributeError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('Document evidence is missing or malformed') from exc
