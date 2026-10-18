"""Reconciled, source-linked inventory of a catalog's unexpanded passages.

This checks saved readings against the deterministic renderer. It does not run
Lean, authenticate receipts, or interpret the mathematical meaning of English.
The theorem denominator always comes from the complete catalog, never the subset
of readings that have an explanation gap.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import html
from pathlib import Path
import re
from urllib.parse import urlencode

from .catalog_inputs import config_inventory, read_json, safe_child, write_json
from .model import canonical_json, walk_steps
from .narrative import PRINTER_VERSION, Snapshot, check_reading
from .render import html_document, load_document


def collect(site: Path) -> dict:
    site = site.resolve()
    coverage = read_json(site / 'coverage.json')
    for field in ('proof_readings', 'expected_theorem_targets',
                  'selected_checked_frames', 'explicit_explanation_gaps', 'configurations'):
        if type(coverage.get(field)) is not int or coverage[field] < 0:
            raise ValueError('Invalid catalog denominator: ' + field)
    if coverage['proof_readings'] > coverage['expected_theorem_targets']:
        raise ValueError('More readings than expected theorem targets')
    originals = safe_child(site, 'originals')
    for path in (originals / 'ComparatorChallenges').glob('*.json'):
        safe_child(site, path.relative_to(site).as_posix())
    configs = config_inventory(originals)
    targets = {(c['solution_module'], name) for c in configs.values()
               for name in c.get('theorem_names', [])}
    definitions = {(c['solution_module'], name) for c in configs.values()
                   for name in c.get('definition_names', [])}
    if len(configs) != coverage['configurations'] or len(targets) != coverage['expected_theorem_targets']:
        raise ValueError('Explanation denominator differs from comparison configuration inventory')
    if targets & definitions:
        raise ValueError('Theorem and definition roles overlap')
    paths = sorted((site / 'proofs').glob('*/reading.json'))
    if len(paths) != coverage['proof_readings']:
        raise ValueError('Explanation inventory is missing a proof reading')
    snapshots = {p.parent for p in (site / 'proofs').glob('*/snapshot.json')}
    if snapshots != {p.parent for p in paths}:
        raise ValueError('Reading and snapshot inventories differ')
    readings = []
    passages = []
    identities = set()
    frames_checked = 0
    by_head = Counter()
    by_rule = Counter()
    for path in paths:
        ident = path.parent.name
        if not re.fullmatch(r'[a-f0-9]{24}', ident):
            raise ValueError('Invalid catalog proof identifier')
        path = safe_child(site, f'proofs/{ident}/reading.json')
        if not safe_child(site, f'proofs/{ident}/reader.html').is_file():
            raise ValueError('Explanation inventory is missing a proof reader page')
        snapshot = Snapshot.read(safe_child(site, f'proofs/{ident}/snapshot.json'))
        document = load_document(path.read_bytes())
        check_reading(snapshot.record, document)
        declaration = document.declarations[0]
        if not declaration.file.startswith('lean/') or not declaration.file.endswith('.lean'):
            raise ValueError('Missing catalog solution module identity')
        module = declaration.file[5:-5].replace('/', '.')
        key = (module, snapshot.record['theorem'])
        if key not in targets or key in identities or sha256(('\0'.join(key)).encode()).hexdigest()[:24] != ident:
            raise ValueError('Repeated or mismatched catalog proof identity')
        original_source = safe_child(originals, module.replace('.', '/') + '.lean')
        if original_source.read_text(encoding='utf-8') != declaration.source:
            raise ValueError('Reading source differs from original solution module')
        if safe_child(site, f'proofs/{ident}/reader.html').read_text(encoding='utf-8') != html_document(document):
            raise ValueError('Proof reader page differs from its validated reading')
        identities.add(key)
        frames_checked += len(snapshot.frames)
        proof_passages = []
        for step in walk_steps(declaration.steps):
            if not step.fallback:
                continue
            owned = [int(k) for k, v in declaration.axes['frame_owners'].items() if v == step.id]
            if not owned:
                raise ValueError('An explanation gap has no source frames')
            source_frames = [snapshot.frames[i] for i in owned]
            head = step.references[0] if step.references else '(recorded term)'
            link = f'proofs/{ident}/reader.html?' + urlencode({
                'declaration': declaration.id, 'step': step.id})
            gap = {
                'module': module, 'theorem': declaration.name, 'proof_id': ident,
                'snapshot_sha256': snapshot.sha256,
                'declaration_id': declaration.id, 'step_id': step.id,
                'reader_link': link, 'head': head, 'rule': step.rule,
                'displayed_text': step.text, 'statement': step.source,
                'context': step.context,
                'budget_cut': any(f['budget_cut'] for f in source_frames),
                'source_frames': [{'id': f['id'], 'path': f['path'],
                                   'role': f['role'], 'head': f['head']} for f in source_frames],
            }
            passages.append(gap)
            proof_passages.append(gap)
            by_head[head] += 1
            by_rule[step.rule] += 1
        groups = {}
        for gap in proof_passages:
            group = groups.setdefault(gap['head'], {'count': 0, 'reader_link': gap['reader_link']})
            group['count'] += 1
        readings.append({'module': module, 'theorem': declaration.name,
                         'proof_id': ident, 'snapshot_sha256': snapshot.sha256,
                         'selected_frames': len(snapshot.frames),
                         'gap_count': len(proof_passages),
                         'first_gap_link': proof_passages[0]['reader_link'] if proof_passages else None,
                         'groups': dict(sorted(groups.items()))})
    if frames_checked != coverage['selected_checked_frames']:
        raise ValueError('Explanation inventory frame count differs from catalog')
    if len(passages) != coverage['explicit_explanation_gaps']:
        raise ValueError('Explanation gap count differs from catalog')
    return {
        'schema': 'leanglish.explanation-gaps/v1', 'printer_version': PRINTER_VERSION,
        'scope': 'available-source-bound-readings',
        'expected_theorem_targets': coverage['expected_theorem_targets'],
        'proof_readings': len(readings),
        'missing_theorem_readings': coverage['expected_theorem_targets'] - len(readings),
        'readings_with_gaps': sum(r['gap_count'] > 0 for r in readings),
        'selected_frames': frames_checked, 'explicit_explanation_gaps': len(passages),
        'by_head': dict(sorted(by_head.items(), key=lambda x: (-x[1], x[0]))),
        'by_rule': dict(sorted(by_rule.items(), key=lambda x: (-x[1], x[0]))),
        'readings': sorted(readings, key=lambda r: (-r['gap_count'], r['module'], r['theorem'])),
        'passages': passages,
        'reading_regeneration_checked': True, 'reader_page_regeneration_checked': True,
        'source_replayed_here': False,
        'receipts_authenticated': False, 'english_formally_verified': False,
        'zero_reported_gaps_implies_complete_explanation': False,
    }


def page_body(report: dict) -> str:
    esc = html.escape
    body = ('<p class="eyebrow">Review the remaining explanations</p>'
            '<h1>Find the passages<br>that need more explanation.</h1>'
            '<p class="lede">Choose a proof or a Lean reference. Each review link opens the exact '
            'unexpanded step with its recorded statement, local assumptions, and source-proof paths.</p>')
    stats = [(report['explicit_explanation_gaps'], 'explicit explanation gaps'),
             (report['readings_with_gaps'], 'readings with gaps'),
             (report['proof_readings'], 'available proof readings'),
             (report['missing_theorem_readings'], 'theorem readings still unavailable')]
    body += '<div class="stats">' + ''.join(
        f'<div><strong>{n}</strong><span>{label}</span></div>' for n, label in stats) + '</div>'
    body += ('<div class="notice">This inventory covers the available readings. Missing theorem '
             'readings remain separate. A reading with no reported gaps is not a certified or '
             'independently established complete English proof.</div>')
    body += ('<form id="gap-filters" class="filters" role="search">'
             '<label>Search theorem, module, or reference<input id="gap-search" type="search" '
             'placeholder="Try contradiction, Iff, or a theorem name"></label>'
             '<label>Lean reference<select id="gap-head"><option value="">All references</option>')
    for head, count in report['by_head'].items():
        body += f'<option value="{esc(head, quote=True)}">{esc(head)} ({count})</option>'
    body += ('</select></label></form><p id="gap-result-count" role="status"></p>'
             '<div class="gap-table-wrap"><table class="gap-table"><thead><tr>'
             '<th scope="col">Proof reading</th><th scope="col">Matching gaps / all gaps</th>'
             '<th scope="col">Inspect</th></tr></thead><tbody>')
    for reading in report['readings']:
        if not reading['gap_count']:
            continue
        search = ' '.join([reading['module'], reading['theorem'], *reading['groups']])
        body += ('<tr class="gap-reading" data-search="' + esc(search, quote=True) + '" '
                 'data-groups="' + esc(canonical_json(reading['groups']), quote=True) + '" '
                 'data-first="' + esc(reading['first_gap_link'], quote=True) + '" '
                 'data-count="' + str(reading['gap_count']) + '"><td><strong>' +
                 esc(reading['theorem']) + '</strong><br><span class="small">' +
                 esc(reading['module']) + '</span></td><td class="gap-count">' +
                 str(reading['gap_count']) + ' / ' + str(reading['gap_count']) +
                 '</td><td><a class="gap-review" href="' + esc(reading['first_gap_link'], quote=True) +
                 '">Review passages →</a></td></tr>')
    body += ('</tbody></table></div><p id="gap-empty" hidden>No readings match these filters.</p>'
             '<p class="small">Reference counts identify the leading reference of each unexpanded '
             'step; they do not estimate the difficulty of finishing its explanation. Source frames '
             'absorbed into one passage remain individually listed in the JSON inventory.</p>'
             '<p><a href="explanation-gaps.json">Complete gap inventory with source paths</a> · '
             '<a href="coverage.html">Coverage and evidence</a></p>')
    return body


def write_report(site: Path) -> dict:
    # Local import avoids a cycle: the catalog shell also calls this report builder.
    from .finding_catalog import shell
    report = collect(site)
    write_json(site / 'explanation-gaps.json', report)
    (site / 'explanations.html').write_text(
        shell('Explanation gaps', page_body(report), page='explanations'), encoding='utf-8')
    return report
