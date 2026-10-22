"""Corpus-level reading-quality measurements for source-bound readings.

Every snapshot is re-rendered with the installed renderer, so a renderer change
can be measured against the whole retained corpus rather than one showcase.
These numbers describe what a reader is shown. They are not English-fidelity,
paper-correspondence or human-comprehension results.

Two opacity measures are reported because they answer different questions:

* gap steps / display steps: how cluttered the reading is with unexplained lines.
* gap frames / checked frames: how much of the checked proof sits inside an
  unexplained step. Collapsing several opaque frames into one displayed gap
  lowers the first number but not the second, so tidier output cannot pass for
  a better explanation.

Citation, instance and automation counts use the renderer's rule tags and
frame classifier, not sentence patterns, so rewording a step cannot change
them. ``opaque_apply_steps`` is kept as a wording measure only.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import statistics
import sys

from .model import digest, walk_steps
from .narrative import Narrative, PRINTER_VERSION
from . import glossary as _glossary

SCHEMA = 'leanglish.reading-kpis/v1'
# Wording measure: the 0.4 sentence for an unexplained application.
OPAQUE_APPLY = re.compile(r'^Apply (.+) to the supplied arguments\.$')
CITATION_RULES = {'citation', 'project-citation'}
INSTANCE_RULES = {'instance-facts', 'instance-assumptions'}
QUALIFIED = re.compile(r"(?<![\w.'])[A-Z][\w'₀-₉]*(?:\.[\w'₀-₉!?]+)+")
LEAN_MARKERS = re.compile(r'(?<![\w.])fun\b|=>|↑')


def snapshot_paths(corpus: Path) -> list[Path]:
    paths = sorted(Path(corpus).rglob('snapshot.json'))
    if not paths:
        raise ValueError('No snapshot.json files under '+str(corpus))
    return paths


def measure(record: dict, glossary: str = _glossary.DEFAULT) -> dict:
    """Render one snapshot and measure the displayed reading."""
    n = Narrative(record, glossary=glossary)
    d = n.document(title=record['theorem']).declarations[0]
    steps = list(walk_steps(d.steps))
    by_id = {s.id: s for s in steps}
    frames_by_rule: Counter = Counter(); gap_frames_by_rule: Counter = Counter()
    gap_frames = 0
    for owner in n.owners.values():
        if owner == 'statement':
            frames_by_rule['statement'] += 1
            continue
        s = by_id[owner]
        frames_by_rule[s.rule] += 1
        gap_frames += s.fallback
        gap_frames_by_rule[s.rule] += s.fallback
    gaps = [s for s in steps if s.fallback]
    cited = {r for s in steps if s.rule == 'project-citation' for r in s.references}
    shown = [p['text'] for p in d.parameters] + ['Then '+d.statement+'.']
    for s in steps:
        shown.append(s.text)
        if s.conclusion:
            shown.append(s.conclusion)
    text = '\n'.join(shown)
    data = {'theorem': record['theorem'], 'snapshot_sha256': n.snapshot.sha256,
            'frames': len(n.frames), 'display_steps': len(steps),
            'gap_steps': len(gaps), 'gap_frames': gap_frames,
            'citation_gap_steps': sum(s.rule in CITATION_RULES for s in gaps),
            'project_citation_gap_steps': sum(s.rule == 'project-citation' for s in gaps),
            'other_gap_steps': sum(s.rule not in CITATION_RULES | INSTANCE_RULES | {'automation'} for s in gaps),
            'instance_frames': sum(n.instance(i) for i in range(len(n.frames))),
            'automation_frames': frames_by_rule['automation'],
            'cited_project_constants': sorted(cited),
            'opaque_apply_steps': sum(bool(OPAQUE_APPLY.match(s.text)) for s in steps),
            'characters': len(text), 'words': len(text.split()),
            'qualified_names': len(QUALIFIED.findall(text)),
            'lean_markers': len(LEAN_MARKERS.findall(text)),
            'rules': dict(sorted(Counter(s.rule for s in steps).items())),
            'gap_rules': dict(sorted(Counter(s.rule for s in gaps).items())),
            'frames_by_rule': dict(sorted(frames_by_rule.items())),
            'gap_frames_by_rule': dict(sorted((k, v) for k, v in gap_frames_by_rule.items() if v))}
    if glossary != _glossary.DEFAULT:  # default-mode rows are unchanged
        data['glossary'] = _glossary.measure(n, steps)
    return data


def _ratio(a: int, b: int) -> float:
    return round(a/b, 4) if b else 0.0


def _quantiles(values: list[float]) -> dict:
    v = sorted(values)
    if not v:
        return {}
    pick = lambda q: round(v[min(len(v)-1, int(q*len(v)))], 4)
    return {'p10': pick(0.1), 'median': round(statistics.median(v), 4), 'p90': pick(0.9), 'max': round(v[-1], 4)}


def summarize(rows: list[dict], failures: list[dict], corpus_digest: str) -> dict:
    total = lambda k: sum(r[k] for r in rows)
    rules: Counter = Counter(); gap_rules: Counter = Counter(); frames_by_rule: Counter = Counter()
    gap_frames_by_rule: Counter = Counter(); cited: set = set()
    for r in rows:
        rules.update(r['rules']); gap_rules.update(r['gap_rules']); frames_by_rule.update(r['frames_by_rule'])
        gap_frames_by_rule.update(r['gap_frames_by_rule']); cited.update(r['cited_project_constants'])
    steps, frames, chars = total('display_steps'), total('frames'), total('characters')
    shares = [_ratio(r['gap_steps'], r['display_steps']) for r in rows]
    return {'schema': SCHEMA, 'printer_version': PRINTER_VERSION, 'corpus_sha256': corpus_digest,
            'readings': len(rows), 'rendering_failures': failures,
            'frames': frames, 'display_steps': steps,
            'gap_steps': total('gap_steps'), 'gap_frames': total('gap_frames'),
            'gap_step_share': _ratio(total('gap_steps'), steps),
            'gap_frame_share': _ratio(total('gap_frames'), frames),
            'citation_gap_steps': total('citation_gap_steps'),
            'citation_gap_share': _ratio(total('citation_gap_steps'), steps),
            'project_citation_gap_steps': total('project_citation_gap_steps'),
            'distinct_cited_project_constants': len(cited),
            'other_gap_steps': total('other_gap_steps'),
            'instance_frames': total('instance_frames'), 'automation_frames': total('automation_frames'),
            'opaque_apply_steps': total('opaque_apply_steps'),
            'opaque_apply_share': _ratio(total('opaque_apply_steps'), steps),
            'readings_without_gaps': sum(r['gap_steps'] == 0 for r in rows),
            'readings_over_half_gap_steps': sum(s > 0.5 for s in shares),
            'per_reading_gap_step_share': _quantiles(shares),
            'per_reading_gap_frame_share': _quantiles([_ratio(r['gap_frames'], r['frames']) for r in rows]),
            'words': total('words'),
            'qualified_names_per_1000_characters': round(1000*total('qualified_names')/chars, 2) if chars else 0.0,
            'lean_markers_per_1000_characters': round(1000*total('lean_markers')/chars, 2) if chars else 0.0,
            'rules': dict(sorted(rules.items())), 'gap_rules': dict(sorted(gap_rules.items())),
            'frames_by_rule': dict(sorted(frames_by_rule.items())),
            'gap_frames_by_rule': dict(sorted(gap_frames_by_rule.items())),
            'measure_notes': MEASURE_NOTES,
            'interpretation': 'Displayed-reading measurements only; not English fidelity or human comprehension.'}


def measure_corpus(corpus: Path, glossary: str = _glossary.DEFAULT) -> tuple[dict, list[dict]]:
    rows, failures, hashes = [], [], []
    for p in snapshot_paths(corpus):
        data = p.read_bytes()
        hashes.append(digest(data))
        try:
            rows.append({'path': p.relative_to(corpus).as_posix(), **measure(json.loads(data), glossary)})
        except (ValueError, KeyError, RecursionError) as exc:
            failures.append({'path': p.relative_to(corpus).as_posix(), 'error': str(exc)})
    summary = summarize(rows, failures, digest('\n'.join(sorted(hashes))))
    if glossary != _glossary.DEFAULT:
        summary['glossary'] = _glossary.summarize(rows)
    return summary, rows


HEADLINE = ['readings', 'display_steps', 'gap_steps', 'gap_step_share', 'gap_frames', 'gap_frame_share',
            'citation_gap_steps', 'project_citation_gap_steps', 'other_gap_steps', 'instance_frames',
            'automation_frames', 'opaque_apply_steps', 'opaque_apply_share', 'readings_without_gaps',
            'readings_over_half_gap_steps', 'words', 'qualified_names_per_1000_characters',
            'lean_markers_per_1000_characters']
MEASURE_NOTES = {
    'citation_gap_steps': 'Gap steps tagged citation or project-citation: a cited constant whose proof this reading does not expand.',
    'other_gap_steps': 'Gap steps that are not citations, typeclass instance facts or automation certificates.',
    'instance_frames': 'Frames the renderer classifies as typeclass side conditions, wherever they are displayed.',
    'automation_frames': 'Frames owned by one collapsed norm_num, positivity or linarith certificate step.',
    'opaque_apply_steps': 'Wording measure: steps reading "Apply <name> to the supplied arguments." Rewording lowers it without explaining anything.'}
LABELS = {'opaque_apply_steps': 'opaque_apply_steps (wording)', 'opaque_apply_share': 'opaque_apply_share (wording)'}


def comparison(old: dict, new: dict) -> str:
    lines = ['| Measure | '+old.get('printer_version', 'baseline')+' | '+new['printer_version']+' |', '|---|---:|---:|']
    for k in HEADLINE:
        lines.append(f'| {LABELS.get(k, k)} | {old.get(k, "—")} | {new[k]} |')
    if old.get('corpus_sha256') != new['corpus_sha256']:
        lines.append('\nWarning: the two measurements use different corpora.')
    return '\n'.join(lines)


def main(argv: list[str] | None = None, *, prog: str | None = None) -> int:
    p = argparse.ArgumentParser(prog=prog, description=__doc__.split('\n\n')[0])
    p.add_argument('corpus', type=Path, help='Directory searched recursively for snapshot.json files')
    p.add_argument('-o', '--output', type=Path, help='Write the corpus summary JSON here')
    p.add_argument('--per-reading', type=Path, help='Also write one measurement row per reading')
    p.add_argument('--baseline', type=Path, help='Compare against an earlier summary JSON')
    p.add_argument('--glossary', choices=_glossary.MODES, default=_glossary.DEFAULT,
                   help='preview: also show proposed glosses, marked and still counted as gaps (docs/GLOSSARY.md)')
    a = p.parse_args(argv)
    summary, rows = measure_corpus(a.corpus, a.glossary)
    text = json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True)+'\n'
    if a.output:
        a.output.write_text(text, encoding='utf-8')
    if a.per_reading:
        a.per_reading.write_text(json.dumps(rows, indent=1, ensure_ascii=False, sort_keys=True)+'\n', encoding='utf-8')
    if a.baseline:
        print(comparison(json.loads(a.baseline.read_text()), summary))
    elif not a.output:
        sys.stdout.write(text)
    return 2 if summary['rendering_failures'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
