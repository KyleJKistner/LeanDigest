# Argument explorer

The explorer supports reading a proof from its goal toward its inputs. It also
lists local facts and the recorded references to each one. It reads an unchanged
`proofreader.narrative/v1` snapshot; it does not translate formulas or certify
English.

## Reading order

A reading plan contains a snapshot digest and an ordered list of frame IDs.
There is no field for replacement prose, replacement assumptions, or a new
mathematical claim. The reader resolves every stop against the original snapshot
and displays its local context, even when a reader visits the end before the
beginning. Plans can be imported and exported as JSON.

Changing this itinerary is not a proof transformation. It does not establish
that the same steps could be placed in that order in a written argument. Moving
a premise, generalizing a local lemma, or discharging a branch is separate work
that requires checked mathematical justification.

This is a limited interface for an AI explanation planner: it can choose which
source claims to inspect and in what order, but cannot edit them through the
plan. It is not yet an AI-generated proof exposition.

## Scope and references

`proofreader/argument_index.py` identifies each binder by its source frame within
a digest-bound snapshot. The source occurrence path and ancestor body edges
establish its scope. Display names are labels, not binder identities.

For a `have`, the new fact is present in the continuation and absent from its own
proof. Two sibling branches may use the same display name without sharing a
binder. A changed scope, invented reference, missing node, or wrong snapshot
digest is rejected by the index checker.

Local applications record a context-slot index. Older `given` frames record only
a name. A unique context name can be linked under that recorded convention; two
matching names produce an ambiguity, not a guessed reference. The pinned corpus
contains one such case, in
`OAI.TraceConeClassification.ExtendedTrace.mul_mem_finiteIdeal_left`.

References are incomplete. Uses inside object expressions, types, implicit
arguments, or unexpanded proof terms need not appear as local proof references.
No reference found does not mean that an assumption is unused or unnecessary.
The index is not a minimal dependency graph.

## Evaluation input

`benchmarks/argument-explorer/cohort.json` fixes twenty proofs from the 492
retained snapshots measured by `reading-kpis`. Selection ranks each canonical
snapshot digest by SHA-256 of a recorded seed, a NUL byte, and that digest. It
uses neither theorem subject nor feature support. The local cohort was committed
before the index implementation; its bytes are fixed by a regression test.

The corpus is the existing `leanglish-original-project-317dc31` snapshot corpus,
with aggregate file-digest hash `9b34751d9a1e97f31993ba290ae26b82710a6ac956e3d81f2643dffdfcfa55ae`.
The local copy came from Opus's digest-checked catalog-preview artifact 12285517963;
each snapshot matched the preview manifest. CI fetches the pinned release using
the existing corpus-fetch script and requires the same aggregate and selected
member digests. Supporting-lemma readings are not added to this denominator.

The builder indexes and validates all 492 snapshots, checks repeat generation,
then builds a standalone page for the twenty selected proofs. It resolves a
reverse-order itinerary for each selected proof and compares every stop's claim
and context with the original. These are structural checks, not new Lean runs.

## Reproduce

```sh
python scripts/fetch_reading_corpus.py /tmp/leanglish-corpus
python scripts/build_argument_explorer.py \
  --corpus /tmp/leanglish-corpus --output /tmp/argument-explorer
python -m pytest tests/test_argument_index.py tests/reader/test_argument_explorer.py -q
python scripts/audit_argument_explorer.py /tmp/argument-explorer/index.html \
  --output /tmp/argument-explorer/browser
```

Open `index.html` locally. The page contains its data and makes no external
requests. Build outputs must go to a new or empty directory. `summary.json`
records the exact HTML digest and the separate index, itinerary, and mutation
checks. `rows.json` retains per-proof measurements.

Browser tests default to real file navigation. An explicit `memory` mode supports
local DOM development where browser navigation is restricted. That mode is not
an offline-file acceptance result. The workflow fixes file mode and retains its
browser record, screenshots, test report, generated page, and source archive.

## Next work

The index is reusable across the corpus without proof-specific modules, variable
enumerations, or layouts. It does not yet meet the certified-English reuse
criteria in `RESEARCH_TRACKS.md`; it adds zero certified passages or documents.

The next importer should retain stable binder identities inside source expressions,
not only local-application heads. It should then connect generic claims and
inferences to those identities. Proposed lemma extraction and proof reordering
can use that representation, with per-output checking. The existing fixed-schema
Bézout proof stays a separate regression example.

External reader feedback remains valuable, but is not a prerequisite for this
implementation work. Before that feedback, evaluate source correspondence,
wrong-scope rejection, repeated generation, real browser behavior, and usability
on the fixed cohort. Do not report those checks as a comprehension study.
