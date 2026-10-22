"""Reading-quality measurements on the bundled Bézout snapshot (a real retained
observation) and on small synthetic corpora built from it."""
import json
import shutil
from pathlib import Path

import pytest

from proofreader.reading_kpis import comparison, measure, measure_corpus, main

DATA = Path(__file__).parents[1]/'proofreader/data'
BEZOUT = json.loads((DATA/'bezout-snapshot.json').read_text())


def test_measure_accounts_for_every_frame():
    row = measure(BEZOUT)
    assert row['frames'] == len(BEZOUT['frames'])
    assert sum(row['frames_by_rule'].values()) == row['frames']
    assert 0 <= row['gap_frames'] <= row['frames']
    assert 0 <= row['gap_steps'] <= row['display_steps']
    assert row['opaque_apply_steps'] <= row['display_steps']


def test_corpus_summary_and_failures_are_separate(tmp_path):
    (tmp_path/'a').mkdir(); (tmp_path/'b').mkdir()
    shutil.copy(DATA/'bezout-snapshot.json', tmp_path/'a/snapshot.json')
    (tmp_path/'b/snapshot.json').write_text(json.dumps({**BEZOUT, 'schema': 'other'}))
    summary, rows = measure_corpus(tmp_path)
    assert summary['readings'] == 1 and len(rows) == 1
    assert [f['path'] for f in summary['rendering_failures']] == ['b/snapshot.json']
    assert summary['gap_step_share'] == round(rows[0]['gap_steps']/rows[0]['display_steps'], 4)
    assert main([str(tmp_path), '-o', str(tmp_path/'out.json')]) == 2


def test_corpus_digest_depends_on_content(tmp_path):
    (tmp_path/'a').mkdir()
    shutil.copy(DATA/'bezout-snapshot.json', tmp_path/'a/snapshot.json')
    first = measure_corpus(tmp_path)[0]['corpus_sha256']
    (tmp_path/'c').mkdir()
    shutil.copy(DATA/'bezout-snapshot.json', tmp_path/'c/snapshot.json')
    assert measure_corpus(tmp_path)[0]['corpus_sha256'] != first


def test_comparison_flags_different_corpora(tmp_path):
    (tmp_path/'a').mkdir()
    shutil.copy(DATA/'bezout-snapshot.json', tmp_path/'a/snapshot.json')
    summary = measure_corpus(tmp_path)[0]
    table = comparison({**summary, 'corpus_sha256': 'x', 'printer_version': 'old'}, summary)
    assert '| gap_steps |' in table and 'different corpora' in table


def test_empty_corpus_is_an_error(tmp_path):
    with pytest.raises(ValueError):
        measure_corpus(tmp_path)
