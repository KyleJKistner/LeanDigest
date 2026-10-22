# Reading-quality measurements

`leanglish reading-kpis CORPUS` re-renders every retained source-bound snapshot
with the installed renderer and measures what a reader is shown. The corpus is
the 492 snapshots in the `leanglish-original-project-317dc31` release, fetched
and digest-checked by `scripts/fetch_reading_corpus.py`.

| File | Meaning |
|---|---|
| `baseline-source-math-en-0.4.1.json` | The renderer that produced the published release (reproduces its 7,587 gaps). |
| `current.json` | The committed renderer. CI (`reading-kpis.yml`) fails if it is stale. Earlier renderers' values are in its history, for example `git show 04df977:benchmarks/reading-kpis/current.json` for `source-math-en/0.4.2`. |

Headline measures:

- **gap_step_share**: displayed steps marked as explanation gaps.
- **gap_frame_share**: checked proof frames owned by a gap step. Collapsing
  several opaque frames into one displayed gap does not lower this number, so
  tidier output cannot pass for a better explanation.
- **citation_gap_steps**, **instance_frames**, **automation_frames**: counted from
  the renderer's rule tags and frame classifier, so rewording cannot change them.
- **opaque_apply_share**: a wording measure only; steps that read
  `Apply <name> to the supplied arguments.` Since 0.5.0 citations are worded
  differently, so this no longer tracks unexplained citations.
- **qualified_names_per_1000_characters** and **lean_markers_per_1000_characters**
  (`fun`, `=>`, `↑`): rough proxies for how much of the text is still Lean syntax.

`stage_effects.py` reproduces the per-change table in `docs/READING_QUALITY.md`.

These are displayed-reading measurements. They are not English fidelity,
paper correspondence, or human comprehension results.

To update after a renderer change:

```sh
python scripts/fetch_reading_corpus.py /tmp/corpus
leanglish reading-kpis /tmp/corpus -o benchmarks/reading-kpis/current.json \
  --baseline benchmarks/reading-kpis/baseline-source-math-en-0.4.1.json
```
