#!/usr/bin/env python3
"""Validate a retained corpus and build the fixed-cohort argument explorer."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from proofreader.argument_explorer import SCHEMA, html, make_item
from proofreader.argument_index import ArgumentIndex, validate_index, validate_plan
from proofreader.kernel import require
from proofreader.model import canonical_json, digest
from proofreader.narrative import Snapshot

COHORT = ROOT / 'benchmarks' / 'argument-explorer' / 'cohort.json'


def build(corpus: Path, cohort_path: Path, output: Path) -> dict:
    require(not output.exists() or (output.is_dir() and not any(output.iterdir())),
            'Use a new or empty output directory')
    cohort_bytes = cohort_path.read_bytes()
    cohort = json.loads(cohort_bytes)
    require(cohort['schema'] == 'leanglish.argument-cohort/v1', 'Unsupported cohort')
    paths = sorted(corpus.rglob('snapshot.json'))
    require(len(paths) == cohort['corpus_count'], 'Corpus inventory changed')
    hashes = [digest(p.read_bytes()) for p in paths]
    require(digest('\n'.join(sorted(hashes))) == cohort['corpus_file_digests_sha256'],
            'Corpus content differs from the selection input')
    selected = {r['id']: r for r in cohort['selected']}
    require(len(selected) == 20, 'The fixed cohort must contain twenty distinct proofs')
    ranked, totals, items, rows = [], Counter(), {}, []
    mutations = 0
    for p, file_hash in zip(paths, hashes):
        snap = Snapshot.read(p)
        selection_key = digest(cohort['seed'] + '\0' + snap.sha256)
        ranked.append({'id': p.parent.name, 'theorem': snap.record['theorem'],
                       'snapshot_sha256': snap.sha256, 'file_sha256': file_hash,
                       'selection_key': selection_key})
        index = ArgumentIndex(snap.record).to_dict()
        validate_index(snap.record, index)
        require(index == ArgumentIndex(snap.record).to_dict(), 'Index is not deterministic')
        totals.update(index['summary'])
        row = {'id': p.parent.name, 'theorem': snap.record['theorem'],
               'snapshot_sha256': snap.sha256, 'index_sha256': digest(canonical_json(index)),
               **index['summary']}
        rows.append(row)
        if p.parent.name in selected:
            require(selected[p.parent.name] == ranked[-1], 'Cohort member changed')
            # Reverse all selected contexts as an inspection itinerary. This
            # does not move hypotheses or claim to produce a new proof.
            order = list(reversed(range(len(snap.frames))))
            plan = ArgumentIndex(snap.record).plan(order)
            resolved = validate_plan(snap.record, plan)
            require(all(stop['statement'] == snap.frames[i]['statement'] and
                        stop['context'] == snap.frames[i]['context']
                        for stop, i in zip(resolved, order)), 'Reading order changed a claim or context')
            changed = json.loads(canonical_json(index))
            changed['snapshot_sha256'] = '0' * 64
            try:
                validate_index(snap.record, changed)
            except ValueError:
                mutations += 1
            else:
                raise ValueError('Wrong-source index was accepted')
            items[p.parent.name] = make_item(snap.record)
    expected = sorted(ranked, key=lambda r: (r['selection_key'], r['snapshot_sha256']))[:20]
    require(expected == cohort['selected'], 'Cohort does not match its recorded selection rule')
    bundle = {'schema': SCHEMA, 'title': 'Argument', 'cohort_sha256': digest(cohort_bytes),
              'items': [items[row['id']] for row in expected]}
    page = html(bundle)
    require(page == html(bundle), 'Explorer output is not deterministic')
    summary = {'schema': 'leanglish.argument-explorer-observation/v1',
               'cohort_sha256': digest(cohort_bytes),
               'corpus_sha256': cohort['corpus_file_digests_sha256'],
               'corpus_proofs': len(paths), 'selected_proofs': len(items),
               'source_identity_mutations_rejected': mutations,
               'selected_reverse_itineraries_checked': len(items),
               'index_totals': dict(sorted(totals.items())), 'html_sha256': digest(page),
               'all_indices_repeat_identically': True, 'html_repeat_identical': True,
               'new_lean_runs': 0, 'certified_english_proofs_added': 0,
               'human_evaluation': 'not performed'}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'index.html').write_text(page, encoding='utf-8')
    (output / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    (output / 'rows.json').write_text(json.dumps(rows, indent=2, sort_keys=True) + '\n')
    (output / 'cohort.json').write_bytes(cohort_bytes)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--cohort', type=Path, default=COHORT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.corpus, args.cohort, args.output), indent=2))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
