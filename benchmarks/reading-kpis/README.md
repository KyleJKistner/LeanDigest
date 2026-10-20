# Reading-quality measurements

`leanglish reading-kpis CORPUS` re-renders every retained source-bound snapshot
with the installed renderer and measures what a reader is shown. The corpus is
the 492 snapshots in the `leanglish-original-project-317dc31` release, fetched
and digest-checked by `scripts/fetch_reading_corpus.py`.

| File | Meaning |
|---|---|
| `baseline-source-math-en-0.4.1.json` | The renderer that produced the published release (reproduces its 7,587 gaps). |
| `current.json` | The committed renderer. CI (`reading-kpis.yml`) fails if it is stale. |

Headline measures:

- **gap_step_share**: displayed steps marked as explanation gaps.
- **gap_frame_share**: checked proof frames owned by a gap step. Collapsing
  several opaque frames into one displayed gap does not lower this number, so
  tidier output cannot pass for a better explanation.
- **opaque_apply_share**: steps that read `Apply <name> to the supplied arguments.`
- **qualified_names_per_1000_characters** and **lean_markers_per_1000_characters**
  (`fun`, `=>`, `↑`): rough proxies for how much of the text is still Lean syntax.

These are displayed-reading measurements. They are not English fidelity,
paper correspondence, or human comprehension results.

To update after a renderer change:

```sh
python scripts/fetch_reading_corpus.py /tmp/corpus
leanglish reading-kpis /tmp/corpus -o benchmarks/reading-kpis/current.json \
  --baseline benchmarks/reading-kpis/baseline-source-math-en-0.4.1.json
```
