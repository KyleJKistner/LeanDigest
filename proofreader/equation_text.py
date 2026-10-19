"""Read the frozen native equation/witness observations without executing Lean.

Only the reviewed records are accepted. Hash reconciliation is consistency
checking, not authentication or an independent Lean proof verifier.
"""
from __future__ import annotations
from html import escape
from pathlib import Path
import json

from .source_text import SOURCE_HASH, TARGET, digest, read_json
ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'artifacts/source-equations'
RECORD_HASHES = {'equations': 'b38de1ecc3328a7a034a70b894f5f685d2bfa83d6cc77455085114cc918ae8e7', 'witnesses': '10b85f68854f03b870221d65a26548648afed124ccc41201e3bdd92a90d49a49'}
FRAMES = {'equations':[18,20,22,23,45,58,68,70,78,79], 'witnesses':[13,63]}
MODULES = {'ControlledEnglish','ControlledEnglishText','ArithmeticEnglish','SourceCancellation',
           'EquationEnglish','SourceEquations','WitnessEnglish','SourceWitnesses',
           'EquationEnglishAudit','WitnessEnglishAudit'}
COMMON_NEGATIVES = {'proof-replacement','wrong-label-map','wrong-operation','text-tamper',
    'kernel-claim-tamper','kernel-flag-bypass','scope-escape','unknown-mode','wrong-path',
    'duplicate-path','missing-path'}
NEGATIVES = {**{f'equations-{n}': False for n in COMMON_NEGATIVES | {'wrong-chain','drop-link','reverse-links','duplicate-link'}},
             **{f'witnesses-{n}': False for n in COMMON_NEGATIVES | {'wrong-witness','swap-witnesses'}}}
CONTRACTS = {
    'EquationEnglish': {'Chain.endpoints','parseChain_chars','read_render','Chain.render_injective',
        'rendered_meaning','certify','readBytes_render','rendered_bytes_meaning','certifyBytes'},
    'WitnessEnglish': {'Frame.witnesses','parseFrame_chars','read_render','Frame.render_injective',
        'rendered_meaning','certify','readBytes_render','rendered_bytes_meaning','certifyBytes'},
}
POSITIVES = MODULES | {'version','equations-positive','equations-repeat','witnesses-positive','witnesses-repeat'}


def load_equations(path: Path = EVIDENCE) -> dict:
    try:
        report = read_json(path/'observation.json')
        if (not isinstance(report,dict) or report.get('schema') != 'leanglish.source-equations/v1'
                or report.get('status') != 'passed' or report.get('theorem') != TARGET
                or report.get('source_sha256') != SOURCE_HASH
                or report.get('upstream_commit') != '1581d4cbdd69a0faf34b2089614fe2a814316a6a'
                or report.get('source_frames') != FRAMES
                or report.get('repeat_byte_identical') is not True):
            raise ValueError('Incomplete equation observation')
        for name,wanted in [('certified_passage_count',12),('certified_equation_chain_count',10),
                            ('certified_witness_tuple_count',2),('adjacent_source_equalities',19),
                            ('native_negative_cases',28),('native_parser_guards',47)]:
            if type(report.get(name)) is not int or report[name] != wanted:
                raise ValueError('Equation coverage inventory changed')
        for flag in ['complete_english_proof_certified','original_project_replayed',
                     'html_semantics_proved','receipt_authenticated']:
            if report.get(flag) is not False:
                raise ValueError('Equation observation overstates its scope')
        if (report['environment']['mathlib_commit'] != 'd13f23b723b8a846827a245b89c10fc7d3f11612'
                or not report['lean_version'].startswith('Lean (version 4.34.1,')
                or report['import_adaptation']['theorem_body_unchanged'] is not True):
            raise ValueError('Equation environment differs from its pin')
        if digest(ROOT/'examples/openai/lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean') != SOURCE_HASH:
            raise ValueError('Original equation source changed')
        if report['snapshot_file_sha256'] != digest(ROOT/'artifacts/companion/native/current/snapshot.json'):
            raise ValueError('Equation source snapshot changed')
        if set(report['module_sha256']) != {n+'.lean' for n in MODULES}:
            raise ValueError('Equation module inventory changed')
        for name,expected in report['module_sha256'].items():
            if digest(ROOT/'lean'/name) != expected:
                raise ValueError('Equation module changed since checking: '+name)
        if (digest(ROOT/'scripts/check_source_equations.py') != report['gate_sha256']
                or digest(ROOT/'scripts/check_source_cancellation.py') != report['environment_checker_sha256']):
            raise ValueError('Equation gate changed since checking')
        wanted_commands = POSITIVES | NEGATIVES.keys()
        commands = report['commands']
        if len(commands) != 43 or {c['label'] for c in commands} != wanted_commands:
            raise ValueError('Equation command inventory changed')
        files = report['files_sha256']
        expected_files = {label+'.log' for label in wanted_commands}
        expected_files |= {label+'.lean' for label in wanted_commands if label.startswith(('equations-','witnesses-'))}
        expected_files |= {kind+'-'+run+'.json' for kind in FRAMES for run in ['positive','repeat']}
        expected_files |= {f'{kind}-{i}.txt' for kind,frames in FRAMES.items() for i in range(len(frames))}
        if not isinstance(files,dict) or set(files) != expected_files:
            raise ValueError('Equation evidence inventory changed')
        actual_files = {p.name for p in path.iterdir()}
        if actual_files != expected_files | {'observation.json'}:
            raise ValueError('Extra or missing equation evidence')
        for name,expected in files.items():
            member = path/name
            if member.is_symlink() or not member.is_file() or digest(member) != expected:
                raise ValueError('Changed equation evidence: '+name)
        for command in commands:
            rc = command.get('returncode')
            if (type(rc) is not int or command.get('timed_out')
                    or command.get('expected_outcome_observed') is not True
                    or ((rc == 0) != (command['label'] in POSITIVES))
                    or files[command['label']+'.log'] != command['stdout_sha256']):
                raise ValueError('Incomplete native equation check')
        contracts = report['contract_axioms']
        if set(contracts) != {'EquationEnglish','WitnessEnglish'}:
            raise ValueError('Equation contract inventory changed')
        for name,group in contracts.items():
            if set(group) != CONTRACTS[name] or any(not isinstance(v,list) or set(v) - {'propext','Classical.choice','Quot.sound'} for v in group.values()):
                raise ValueError('Unpermitted equation contract axiom')
        result = {'observation':report, 'record_sha256':RECORD_HASHES,
                  'observation_sha256':digest(path/'observation.json')}
        snapshot = read_json(ROOT/'artifacts/companion/native/current/snapshot.json')
        for kind,expected_hash in RECORD_HASHES.items():
            record_path = path/(kind+'-positive.json')
            if (digest(record_path) != expected_hash
                    or record_path.read_bytes() != (path/(kind+'-repeat.json')).read_bytes()):
                raise ValueError('Reviewed equation record changed')
            rows = read_json(record_path)
            paths = [snapshot['frames'][i]['path'] for i in FRAMES[kind]]
            if [r['path'] for r in rows] != paths:
                raise ValueError('Equation source occurrence changed')
            for i,row in enumerate(rows):
                if bytes(row['utf8']) != (path/f'{kind}-{i}.txt').read_bytes():
                    raise ValueError('Displayed equation differs from its checked bytes')
            result[kind] = rows
        return result
    except (OSError,KeyError,TypeError,AttributeError,UnicodeError,json.JSONDecodeError) as exc:
        raise ValueError('Equation evidence is missing or malformed') from exc


def calculation_panel(records: list[tuple[dict,int,str]], section: str) -> str:
    """Embed checked text verbatim. The surrounding labels are interface text."""
    rows=[]
    for record,frame,kind in records:
        rows.append(f'<div class="checked-calculation" data-kind="{escape(kind)}" data-source-frame="{frame}">'
                    f'<p class="checked-equation-text">{escape(record["text"])}</p>'
                    f'<button class="evidence-button" data-section="{escape(section)}" data-evidence-tab="frames" data-source-frame="{frame}">View source claim {frame}</button></div>')
    return (f'<details class="checked-equations" data-proof-section="{escape(section)}"><summary>Checked equations and witnesses</summary>'
            + ''.join(rows) +
            '<p class="small muted">Each passage is checked in its displayed proof section’s local context. '
            'A frame means the four equations in the statement, with tuple order (a, d, b, c).</p></details>')
