#!/usr/bin/env python3
"""Cumulative corpus effect of each source-math-en/0.5.0 renderer change.

Usage: python benchmarks/reading-kpis/stage_effects.py CORPUS [OUTPUT.json]

Each change that has a single switch point in proofreader/narrative.py is
disabled by replacing that function for the run, then enabled again in the
order of docs/READING_QUALITY.md. Row "none" therefore still contains the
changes without such a switch point. This measurement aid reproduces the
per-change table for 0.5.0; it is not part of CI and may need updating when
the renderer changes.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import proofreader.narrative as nm  # noqa: E402
from proofreader import reading_kpis  # noqa: E402

ORIGINAL = dict(instance=nm.Narrative.instance, automation=nm._automation, rewrite=dict(nm._REWRITE_TEXT),
                citation=nm._citation, transport=nm._equation_sides, stated=nm.Narrative.stated,
                unpack=nm.Narrative.named_conjunction)
DISABLED = dict(instance=lambda self, i: False, automation=lambda head: None, rewrite={},
                citation=lambda head: ('Apply '+head+' to the supplied arguments.', None),
                transport=lambda text: None, stated=lambda self, steps, statement: steps,
                unpack=lambda self, i: False)
TARGETS = dict(instance=(nm.Narrative, 'instance'), automation=(nm, '_automation'), rewrite=(nm, '_REWRITE_TEXT'),
               citation=(nm, '_citation'), transport=(nm, '_equation_sides'), stated=(nm.Narrative, 'stated'),
               unpack=(nm.Narrative, 'named_conjunction'))
ORDER = ['instance', 'automation', 'rewrite', 'citation', 'transport', 'stated', 'unpack']
KEYS = ['display_steps', 'gap_steps', 'gap_frames', 'citation_gap_steps', 'project_citation_gap_steps',
        'instance_frames', 'automation_frames', 'opaque_apply_steps', 'words']


def main(corpus: str, output: str | None = None) -> None:
    rows = {}
    try:
        for k in range(len(ORDER)+1):
            for name in ORDER:
                owner, attribute = TARGETS[name]
                setattr(owner, attribute, ORIGINAL[name] if name in ORDER[:k] else DISABLED[name])
            summary, _ = reading_kpis.measure_corpus(Path(corpus))
            if summary['rendering_failures']:
                raise SystemExit('Rendering failures: '+str(summary['rendering_failures'][:3]))
            rows['+'.join(ORDER[:k]) or 'none'] = {key: summary[key] for key in KEYS}
            print(list(rows)[-1], rows[list(rows)[-1]], flush=True)
    finally:
        for name in ORDER:
            owner, attribute = TARGETS[name]
            setattr(owner, attribute, ORIGINAL[name])
    if output:
        Path(output).write_text(json.dumps(rows, indent=1, ensure_ascii=False)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main(*sys.argv[1:3])
