#!/usr/bin/env python3
"""Rebuild reader_quality.json from the pinned retained snapshot corpus.

Usage: python tests/fixtures/extract_reader_quality.py CORPUS tests/fixtures/reader_quality.json

CORPUS is the directory written by scripts/fetch_reading_corpus.py. Each
fixture keeps the recorded frames of one subtree unchanged except for
re-indexing, the path prefix and the enclosing local context, which every
frame of the subtree shares and which is removed. Extraction fails unless each
recorded frame is displayed with the same text, gap flag and rule as in the
full snapshot. Only the root step may differ: its conclusion, because a parent
that states the claim suppresses it there, and the wording of a citation that
proves the subtree's own statement ("The statement follows from X" for "By X").
"""
import hashlib
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from proofreader.model import walk_steps  # noqa: E402
from proofreader.narrative import Narrative, Snapshot  # noqa: E402

FIXTURES = [
    ('cast_with_instances', '001718adaf11cdf2e8ccc438', 14),
    ('norm_num', '001718adaf11cdf2e8ccc438', 154),
    ('linarith', '001718adaf11cdf2e8ccc438', 40),
    ('restatement', '001718adaf11cdf2e8ccc438', 39),
    ('project_citation', '001718adaf11cdf2e8ccc438', 27),
    ('positivity_with_premises', '6a50089d1011272202f4b6d6', 158),
    ('ergodic_projection', '11abd6d731eb86f8c3f704aa', 35),
    ('instance_named_project_lemma', '2394c557e6965a76614641cc', 112),
    ('instance_assumption', '0dc2e4d5752a367cabdec428', 35),
    ('pi_instance_family', '7f424240829ae53312ebe76f', 33),
    ('unfolded_projection', '041ad1b2c7d69a9a62c10c7f', 75),
    ('nonempty_cases', '163fb00f2e3d611b07ddbb90', 3),
    ('nonempty_intro', '163fb00f2e3d611b07ddbb90', 8),
    ('substitution', '459e6c5668380927d515a988', 19),
    ('anonymous_have', '18159986a68f8f5a56a4ee28', 70),
    ('of_eq_true', '2e1f01c9a8dfcfd39dc1eeba', 17),
    ('rcases_chain', '8593c0757421b0bc36918c20', 8),
    ('instance_from_project_lemma', '4a72a3f89a6e3a114dd76c34', 25),
    ('substitution_specialized', '130628592a176216f3d3f4e9', 33),
    # Added for source-math-en/0.6.0.
    ('hypotheses_mixed', '065eddd53975720f9d443d63', 105),
    ('binder_conjunct_projection', '041ad1b2c7d69a9a62c10c7f', 121),
    ('binder_right_projection', '2e1f01c9a8dfcfd39dc1eeba', 31),
    ('equivalence_binder', '151b0da1c1708a5b462d03ba', 46),
    ('witness_proof_named', 'eb2434f6266b34e6ae633b10', 16),
    ('witness_proof_anonymous', 'a9b0f23c43ac9dd9608b9e80', 16),
    ('unpack_existential', '4c998ca1a32a284762ae3319', 20),
    ('unchecked_application', '6bfcd5b628744719dae2584a', 41),
    ('applied_projection', '380d53f06e20517c2d1f4c4b', 10),
    ('local_instance', '3a43803ef4ef28944eac9eb2', 44),
    ('nonempty_construction', '9d371e576d1c015cba0577cc', 2),
]


def extract(rec, root):
    fr = rec['frames']
    ctx = len(fr[root]['context'])
    order, stack = [], [root]
    while stack:
        j = stack.pop(); order.append(j); stack.extend(reversed(fr[j]['children']))
    new = {old: k for k, old in enumerate(order)}
    rp = len(fr[root]['path']); frames = []
    for old in order:
        f = json.loads(json.dumps(fr[old]))
        if f['role'] == 'local-application' and f['local_index'] < ctx:
            raise ValueError('A local application refers outside the subtree')
        f['id'] = new[old]; f['path'] = f['path'][rp:]; f['context'] = f['context'][ctx:]
        if 'local_index' in f:
            f['local_index'] -= ctx
        f['children'] = [new[c] for c in f['children']]
        for p in f['premises']:
            p['frame'] = new[p['frame']]
        frames.append(f)
    out = {k: rec[k] for k in ('schema', 'theorem', 'lean_version', 'axioms', 'formula_backend')}
    out.update(statement=frames[0]['statement'], frames=frames, judgements_checked=len(frames))
    Snapshot(out)
    return out, order


def root_wording(text):
    m = re.fullmatch(r'The statement follows from (.+?)(?:, applied to the facts below)?\.', text)
    return 'By '+m[1] if m else text


def displayed(record, ids):
    n = Narrative(record); d = n.document().declarations[0]
    by = {s.id: s for s in walk_steps(d.steps)}
    return [((by[n.owners[i]].text if k else root_wording(by[n.owners[i]].text)).rstrip(':.'),
             by[n.owners[i]].conclusion if k else None, by[n.owners[i]].fallback, by[n.owners[i]].rule)
            for k, i in enumerate(ids)]


def main(corpus, dest):
    bundle = {'description': 'Subtrees of retained source-bound snapshots from the pinned 492-snapshot corpus '
              '(leanglish-original-project-317dc31), rebuilt by extract_reader_quality.py. Recorded frames are '
              'unchanged except for re-indexing, their path prefix and the removed enclosing local context.',
              'fixtures': {}}
    for name, ident, root in FIXTURES:
        raw = (Path(corpus)/ident/'snapshot.json').read_bytes(); rec = json.loads(raw)
        record, order = extract(rec, root)
        if displayed(rec, order) != displayed(record, range(len(order))):
            raise ValueError('Subtree renders differently from the full snapshot: '+name)
        bundle['fixtures'][name] = {'provenance': {'corpus_snapshot': ident, 'snapshot_file_sha256': hashlib.sha256(raw).hexdigest(),
                                                   'snapshot_sha256': Snapshot(rec).sha256, 'theorem': rec['theorem'],
                                                   'root_frame': root, 'recorded_frames': order},
                                    'record': record}
    Path(dest).write_text(json.dumps(bundle, ensure_ascii=False, indent=1, sort_keys=True)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main(*sys.argv[1:3])
