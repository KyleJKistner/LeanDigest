#!/usr/bin/env python3
"""Cumulative corpus effect of each source-math-en/0.5.0, 0.6.0 and 0.7.0 renderer change.

Usage: python benchmarks/reading-kpis/stage_effects.py CORPUS [OUTPUT.json]

Each change that has a single switch point in proofreader/narrative.py,
proofreader/narrative_rules.py or proofreader/narrative_checks.py is disabled
by replacing the attributes listed for it, then enabled again in the order of
docs/READING_QUALITY.md. Row "none" therefore still contains the changes
without such a switch point. Disabling the 0.7.0 scope change also disables
the scope requirement in document(), which the flat 0.6.0 lists do not meet.
This measurement aid reproduces the per-change tables; it is not part of CI
and may need updating when the renderer changes.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import proofreader.narrative as nm  # noqa: E402
import proofreader.narrative_rules as nr  # noqa: E402
from proofreader import reading_kpis  # noqa: E402
from proofreader.formula_surface import _binary_formula, _outer  # noqa: E402

N = nm.Narrative


def _bare_conjunct_060(right):
    b = _outer(right)
    return b is not None and (not b[1] & set('∨→↔') or nr._BINDER_LEAD.match(b[0]) is not None)


_AUTOMATION_060 = dict(nm._AUTOMATION_TEXT,
                       linarith='Linear arithmetic (linarith) proves this; the certificate is not expanded.')

# name: [(owner, attribute, disabled value)]
CHANGES = {
    'instance': [(N, 'instance', lambda self, i: False)],
    'automation': [(nm, '_automation', lambda head: None)],
    'rewrite': [(nm, '_REWRITE_TEXT', {})],
    'citation': [(nm, '_citation', lambda head: ('Apply '+head+' to the supplied arguments.', None))],
    'transport': [(nm, '_equation_sides', lambda text: None)],
    'stated': [(N, 'stated', lambda self, steps, statement: steps)],
    'unpack': [(N, 'named_conjunction', lambda self, i: False)],
    'hypotheses': [(N, 'grouped', lambda self, steps: steps)],
    'projection': [(N, 'projected', lambda self, text, left, right: _binary_formula(text, '∧', left, right))],
    'equivalence': [(N, 'equivalent', lambda self, text, left, right: _binary_formula(text, '↔', left, right))],
    'proof_witness': [(N, 'proof_witness', lambda self, i: None)],
    'proof_cases': [(N, 'proof_cases', lambda self, i: None)],
    'applied_projection': [(N, 'applied_projection', lambda self, i: None)],
    'nonempty_element': [(N, 'nonempty_element', lambda self, i: None)],
    'local_instances': [(N, 'local_instances', lambda self, covered: [])],
    # 0.7.0
    'scope': [(N, 'joined', lambda self, proofs, after=None: [s for _, steps in proofs for s in steps]+(after or [])),
              (N, 'case_proof', lambda self, j, steps: steps), (N, 'require_scopes', lambda self, steps: None)],
    'line_breaks': [(nm, '_SPACED', r'(?= )')],
    'linarith': [(nm, '_AUTOMATION_TEXT', _AUTOMATION_060)],
    'forward_equivalence': [(N, 'forward_equivalence', lambda self, i: None)],
    'same_assumption': [(N, 'same_assumption', lambda self, i: True)],
    'motive': [(N, 'motive_cases', lambda self, i, slots: [('', None, True), ('', None, True)])],
    'existential': [(N, 'existential', lambda self, i: True)],
    'conjunct_precedence': [(nr, '_bare_conjunct', _bare_conjunct_060)],
    'conjunction_premise': [(N, 'conjunction_premise', lambda self, i: True)],
    'chained': [(N, 'chained', lambda self, i, leaves: True)],
    'wording': [(nm, '_KINDS', {}), (N, 'definition_type', lambda self, name, domain: ''),
                (N, 'introduction', lambda self, f: 'Let '+nm._name(f['binder'])+' ∈ '+nm.math_text(f['domain'])+' be arbitrary.'),
                (N, 'function_text', lambda self, i: nm.math_text(self.frames[i]['objects'][-1])), (N, 'instance_gloss', True)],
}
ORIGINAL = {(id(owner), attribute): getattr(owner, attribute) for parts in CHANGES.values() for owner, attribute, _ in parts}
# 0.5.0 changes, then 0.6.0 and 0.7.0 changes, in the order of docs/READING_QUALITY.md.
ORDER = list(CHANGES)
KEYS = ['display_steps', 'gap_steps', 'gap_frames', 'citation_gap_steps', 'project_citation_gap_steps',
        'other_gap_steps', 'instance_frames', 'automation_frames', 'opaque_apply_steps', 'words']


def _set(enabled: set[str]) -> None:
    for name, parts in CHANGES.items():
        for owner, attribute, disabled in parts:
            setattr(owner, attribute, ORIGINAL[(id(owner), attribute)] if name in enabled else disabled)


def main(corpus: str, output: str | None = None) -> None:
    rows = {}
    try:
        for k in range(len(ORDER)+1):
            _set(set(ORDER[:k]))
            summary, _ = reading_kpis.measure_corpus(Path(corpus))
            if summary['rendering_failures']:
                raise SystemExit('Rendering failures: '+str(summary['rendering_failures'][:3]))
            rows['+'.join(ORDER[:k]) or 'none'] = {key: summary[key] for key in KEYS}
            print(ORDER[k-1] if k else 'none', rows[list(rows)[-1]], flush=True)
    finally:
        _set(set(ORDER))
    if output:
        Path(output).write_text(json.dumps(rows, indent=1, ensure_ascii=False)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main(*sys.argv[1:3])
