"""Glosses for cited library lemmas (schema ``leanglish.glossary/v1``).

A gloss is a short mathematical phrase for one cited Lean constant, such as
"transitivity of ≤" for ``le_trans``. Glosses are written when the dictionary
is built, never while a reading is rendered: ``data/glossary.json`` is fixed
data and rendering makes no model call. Each entry quotes the declaration it
glosses (repository, path, line and exact source lines) so that a reviewer can
compare the phrase with the statement.

An entry stays ``proposed`` until a named human reviewer marks it ``reviewed``
(``scripts/glossary_review.py mark``). In the default mode only reviewed
entries apply: the citation step "By X:" becomes the explained step
"By <gloss> (X):". The opt-in ``preview`` mode, for reviewers, also shows
proposed glosses, marked "[unreviewed gloss]"; those steps remain explanation
gaps. A reading records a non-default mode in ``axes['glossary']``, and
``check_reading`` regenerates the reading in the recorded mode.
"""
from __future__ import annotations
from collections import Counter
import functools
import json
from pathlib import Path
import re
from typing import Any

from .kernel import require
from .kernel_io import strict_json
from .model import canonical_json, digest, walk_steps

SCHEMA = 'leanglish.glossary/v1'
DEFAULT = 'reviewed'
MODES = (DEFAULT, 'preview')
MARKER = '[unreviewed gloss]'
MAX_GLOSS = 80
STATUSES = ('proposed', 'reviewed')
PROPOSERS = ('model', 'human')
REVIEWED_RULE = 'reviewed-gloss'
PATH = Path(__file__).parent/'data'/'glossary.json'
AXES_NOTE = ('Glosses marked [unreviewed gloss] are proposals that no reviewer has accepted; '
             'their steps remain explanation gaps.')
_TOP = {'schema', 'description', 'sources', 'entries'}
_SOURCE = {'repository', 'revision'}
_ENTRY = {'name', 'gloss', 'statement', 'status', 'proposed_by', 'reviewed_by', 'notes'}
_STATEMENT = {'source', 'path', 'line', 'text', 'context'}
_EXCERPT = {'source', 'path', 'line', 'text'}
_AXES = {'mode', 'glossary_sha256', 'note'}
_NAME = re.compile(r"[^\W\d][\w'!?]*(?:\.[^\W\d][\w'!?]*)*")
# The renderer words these itself; project lemmas get their own readings; Lean
# generates the auxiliary names, so there is no declaration to quote.
_RESERVED = frozenset({'Subtype.property', 'cast', 'id'})
_GENERATED = re.compile(r'.*\._(?:simp|proof)_\d+(?:_\d+)*')
_REPOSITORY = re.compile(r'https://[A-Za-z0-9.-]+(?:/[A-Za-z0-9._-]+)+')
_REVISION = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]*')


def _text(value: Any, limit: int, what: str, *, empty: bool = False) -> None:
    require(isinstance(value, str) and len(value) <= limit and '\x00' not in value and (empty or value.strip()),
            'Invalid glossary '+what)


def _excerpt(x: Any, sources: dict, keys: set[str]) -> None:
    require(isinstance(x, dict) and set(x) == keys, 'Unknown or missing glossary statement fields')
    require(isinstance(x['source'], str) and x['source'] in sources, 'Glossary statement names an unknown source')
    _text(x['path'], 400, 'source path')
    parts = x['path'].split('/')
    require(not x['path'].startswith('/') and '\\' not in x['path'] and '..' not in parts and '' not in parts,
            'Glossary source path must be relative')
    require(type(x['line']) is int and x['line'] >= 1, 'Invalid glossary source line')
    _text(x['text'], 4000, 'source text')
    require(not x['text'].endswith('\n'), 'Glossary source text has a trailing newline')


def _entry(e: Any, sources: dict) -> None:
    require(isinstance(e, dict) and set(e) == _ENTRY, 'Unknown or missing glossary entry fields')
    name = e['name']
    require(isinstance(name, str) and _NAME.fullmatch(name) is not None, 'Invalid glossary constant name')
    require(name not in _RESERVED and not _GENERATED.fullmatch(name), 'Glossary entry for a renderer-worded or generated name: '+name)
    require(not name.startswith(('OAI.', '_private.')), 'Glossary entry for a project constant: '+name)
    gloss = e['gloss']
    _text(gloss, MAX_GLOSS, 'gloss for '+name)
    require(gloss == gloss.strip() and '\n' not in gloss and MARKER not in gloss and not gloss.endswith(('.', ':')),
            'Glossary gloss must be one phrase without a final period or colon: '+name)
    _excerpt(e['statement'], sources, _STATEMENT)
    require(isinstance(e['statement']['context'], list), 'Invalid glossary statement context')
    for c in e['statement']['context']:
        _excerpt(c, sources, _EXCERPT)
    require(e['status'] in STATUSES, 'Unknown glossary status: '+name)
    require(e['proposed_by'] in PROPOSERS, 'Unknown glossary proposer: '+name)
    if e['status'] == 'reviewed':
        require(isinstance(e['reviewed_by'], str) and e['reviewed_by'].strip() != '' and len(e['reviewed_by']) <= 200
                and e['reviewed_by'] == e['reviewed_by'].strip() and '\n' not in e['reviewed_by'] and '\x00' not in e['reviewed_by'],
                'A reviewed glossary entry needs a named reviewer: '+name)
    else:
        require(e['reviewed_by'] is None, 'A proposed glossary entry cannot name a reviewer: '+name)
    _text(e['notes'], 2000, 'notes for '+name, empty=True)


def validate(data: Any) -> dict:
    """Check a ``leanglish.glossary/v1`` document; unknown fields and duplicates are refused."""
    require(isinstance(data, dict) and set(data) == _TOP, 'Unknown or missing glossary fields')
    require(data['schema'] == SCHEMA, 'Unsupported glossary schema')
    _text(data['description'], 2000, 'description')
    sources = data['sources']
    require(isinstance(sources, dict) and sources, 'Invalid glossary sources')
    for s in sources.values():
        require(isinstance(s, dict) and set(s) == _SOURCE, 'Unknown or missing glossary source fields')
        for v in s.values():
            _text(v, 400, 'source field')
        # The review document links each statement through this URL.
        require(_REPOSITORY.fullmatch(s['repository']) is not None and _REVISION.fullmatch(s['revision']) is not None,
                'Glossary source must name an https repository URL and a plain revision')
    require(isinstance(data['entries'], list), 'Invalid glossary entries')
    seen: set[str] = set()
    for e in data['entries']:
        _entry(e, sources)
        require(e['name'] not in seen, 'Duplicate glossary entry: '+e['name'])
        seen.add(e['name'])
    return data


class Glossary:
    """A validated glossary. Treat it as read-only: ``sha256`` is computed once."""

    def __init__(self, data: Any):
        validate(data)
        self.data = json.loads(canonical_json(data))
        self.entries = {e['name']: e for e in self.data['entries']}
        self.sha256 = digest(canonical_json(self.data))

    @classmethod
    def read(cls, path: Path | str) -> 'Glossary':
        return cls(strict_json(Path(path).read_bytes()))

    def select(self, mode: str = DEFAULT) -> 'Selection':
        return Selection(self, mode)


class Selection:
    """The glosses one rendering applies: reviewed entries, and proposed ones in preview."""

    def __init__(self, glossary: Glossary, mode: str):
        require(mode in MODES, 'Unknown glossary mode')
        self.glossary, self.mode = glossary, mode
        self.entries = {n: e for n, e in glossary.entries.items() if e['status'] == 'reviewed' or mode == 'preview'}

    def __contains__(self, head: str) -> bool:
        return head in self.entries

    def explains(self, head: str) -> bool:
        """True when a reviewed gloss turns the citation of ``head`` into an explained step."""
        return head in self.entries and self.entries[head]['status'] == 'reviewed'

    def sentence(self, head: str, shown: str) -> tuple[str, str]:
        """The step text and rule for a cited ``head`` displayed as ``shown``."""
        gloss = self.entries[head]['gloss']
        if self.explains(head):
            return 'By '+gloss+' ('+shown+'):', REVIEWED_RULE
        return 'By '+gloss+' ('+shown+') '+MARKER+':', 'citation'

    def axes(self) -> dict | None:
        """The reading's ``axes['glossary']`` record; None in the default mode."""
        if self.mode == DEFAULT:
            return None
        return {'mode': self.mode, 'glossary_sha256': self.glossary.sha256, 'note': AXES_NOTE}


@functools.lru_cache(maxsize=1)
def packaged() -> Glossary:
    return Glossary.read(PATH)


def selection(choice: str | Selection = DEFAULT) -> Selection:
    """A mode of the packaged glossary, or an explicit selection (used by tests and measurements)."""
    if isinstance(choice, Selection):
        return choice
    require(isinstance(choice, str) and choice in MODES, 'Unknown glossary mode')
    return packaged().select(choice)


def recorded_mode(declaration: Any) -> str:
    """The mode a saved reading claims; refuses a malformed record or a hidden unreviewed gloss."""
    g = declaration.axes.get('glossary')
    if g is None:
        require(not any(MARKER in s.text for s in walk_steps(declaration.steps)),
                'A reading in the reviewed glossary mode shows an unreviewed gloss')
        return DEFAULT
    require(isinstance(g, dict) and set(g) == _AXES and g['mode'] in MODES and g['mode'] != DEFAULT,
            'Invalid glossary mode record')
    return g['mode']


# --- measurement (reading_kpis --glossary) -----------------------------------

def measure(narrative: Any, steps: list) -> dict:
    """Glossary counts for one reading rendered in a non-default mode.

    A step "carries an unreviewed gloss" when it is a citation gap that shows
    the marker for a proposed entry. Reviewing that entry changes only that
    step: it becomes explained unless its frame is a budget cut. The projected
    counts below are that arithmetic, not a rendering.
    """
    g = narrative.glosses
    head = lambda s: narrative.frames[int(s.id.rsplit(':', 1)[1])]['head']
    marked = [s for s in steps if s.rule == 'citation' and s.fallback and MARKER in s.text
              and head(s) in g and not g.explains(head(s))]
    would = [s for s in marked if not any(narrative.frames[int(t[1:])]['budget_cut'] for t in s.term_id.split(','))]
    owned = Counter(narrative.owners.values())
    return {'mode': g.mode, 'glossary_sha256': g.glossary.sha256,
            'reviewed_gloss_steps': sum(s.rule == REVIEWED_RULE for s in steps),
            'unreviewed_gloss_steps': len(marked),
            'unreviewed_gloss_frames': sum(owned[s.id] for s in marked),
            'explained_if_reviewed_steps': len(would),
            'explained_if_reviewed_frames': sum(owned[s.id] for s in would),
            'unreviewed_glosses': dict(sorted(Counter(head(s) for s in marked).items()))}


def summarize(rows: list[dict]) -> dict:
    """Corpus totals of ``measure`` rows, with the counts projected if every shown proposal were reviewed."""
    total = lambda k: sum(r['glossary'][k] for r in rows)
    shown: Counter = Counter(); readings: Counter = Counter()
    for r in rows:
        shown.update(r['glossary']['unreviewed_glosses'])
        readings.update(r['glossary']['unreviewed_glosses'].keys())
    steps = sum(r['display_steps'] for r in rows); frames = sum(r['frames'] for r in rows)
    gap_steps = sum(r['gap_steps'] for r in rows) - total('explained_if_reviewed_steps')
    gap_frames = sum(r['gap_frames'] for r in rows) - total('explained_if_reviewed_frames')
    ratio = lambda a, b: round(a/b, 4) if b else 0.0
    return {'mode': rows[0]['glossary']['mode'] if rows else None,
            'glossary_sha256': rows[0]['glossary']['glossary_sha256'] if rows else None,
            'reviewed_gloss_steps': total('reviewed_gloss_steps'),
            'unreviewed_gloss_steps': total('unreviewed_gloss_steps'),
            'unreviewed_gloss_frames': total('unreviewed_gloss_frames'),
            'distinct_unreviewed_glosses_shown': len(shown),
            'readings_with_unreviewed_glosses': sum(bool(r['glossary']['unreviewed_glosses']) for r in rows),
            'unreviewed_glosses': {k: {'steps': v, 'readings': readings[k]} for k, v in sorted(shown.items())},
            'projected_if_all_shown_reviewed': {
                'gap_steps': gap_steps, 'gap_step_share': ratio(gap_steps, steps),
                'gap_frames': gap_frames, 'gap_frame_share': ratio(gap_frames, frames),
                'citation_gap_steps': sum(r['citation_gap_steps'] for r in rows) - total('explained_if_reviewed_steps'),
                'readings_without_gaps': sum(r['gap_steps'] == r['glossary']['explained_if_reviewed_steps'] for r in rows),
                'readings_over_half_gap_steps': sum(
                    ratio(r['gap_steps'] - r['glossary']['explained_if_reviewed_steps'], r['display_steps']) > 0.5 for r in rows),
                'method': 'Arithmetic on the preview rendering: each step showing an unreviewed gloss is counted as '
                          'explained unless its frame is a budget cut. Words and other counts are not projected.'}}
