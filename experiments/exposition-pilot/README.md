# Proof refactoring and exposition

This diagnostic pilot compares source minimization with mathematical exposition
on three selected proofs. It is not a corpus benchmark or a human-comprehension
study. Candidate proofs and repairs were proposed by the assistant during one
conversation, then run locally in fresh Lean processes. `run.py` replays a finite
queue; it does not call a model or run an unattended research agent.

## Sample

| Target | Source | Explanatory question |
| --- | --- | --- |
| `OAI.ComplexCancellation.BezoutFrame.exists_frame` | OpenAI supporting theorem | What forces the formula for the witness? |
| `List.reverse_reverse` | Lean library control | What happens to one position under two reversals? |
| `Function.cantor_surjective` | Mathlib control | How can one subset differ from every proposed value? |

The latter two are controls, not additional OpenAI results. Selection was
purposeful, before candidate development. The three cases have different
exposition problems; they do not establish performance on unfamiliar research.

## Result

Fifteen proposals, counting copied baselines and repaired attempts, were checked:
eleven accepted and four rejected. Six separate negative controls were all
rejected. Ten accepted records used in the comparisons reproduced byte for byte
in fresh processes. Failed proposals and logs are retained, not removed from
the denominator. There was no equal-compute allocation or exhaustive search.

| Proof | Original | Smallest accepted in this queue | Explanatory |
| --- | ---: | ---: | ---: |
| Bézout frame | 1,009 | 751 | 1,632 |
| List reversal | 119 | 93 | 263 |
| Cantor | 121 | 121 | 299 |

Sizes are non-whitespace source characters in the entire candidate declaration
block, including signatures and all new helpers. Existing library proofs are
background and are not charged as new source. These are not token counts or
comprehension scores. In particular, the original Cantor proof remains the
smallest accepted candidate; the failed automation attempt is not a result.

The Bézout candidate proves that the two desired equations force
`c = r*w + s*y`, then proves this value works from `a*r+d*s=1` and `a*y=d*w`.
These lemmas require only a commutative ring. A separate checked converse shows
why the original product hypothesis is necessary. The full refactored theorem
is checked against the unchanged original statement.

The positional list proof exposes the involution `i ↦ n-1-i`. Its arithmetic
lemma retains `i<n`; dropping that bound would be wrong for natural subtraction.
The compact proof instead calls the existing accumulator lemma. An initial
`by simp` proof was rejected because its dependency closure contains the target.

The Cantor refactoring constructs the omitted set first and proves that every
proposed value differs from it. The original proof already contains the idea;
refactoring names and separates it. A fixed-point alternative also checks but
is longer than the original.

## Reader

`book.json` contains conventional mathematical notes. The main page shows the
statement, construction where needed, and proof. Expandable questions expose
calculations and assumptions in place. Exact Lean statements, alternative source,
and check information are secondary. Integer and finite examples are marked as
illustrations and do not replace universal proofs.

The common renderer `build.py` consumes the same format for all three articles.
It checks source hashes, successful native observations, original target identity,
and referenced lemma names. It does **not** prove that an English paragraph or
its mathematical typesetting has the same meaning as its linked Lean statement.
The prose is AI-authored, not certified English. A formal proof badge must not be
interpreted as an exposition certificate.

KaTeX is used at build time, from the repository's existing vendored JavaScript,
to emit native MathML. The page is standalone, makes no network requests, and
contains no font files. A PDF reading copy can be printed from it with the
mathematical notes expanded.

## Native check

`PilotAudit.lean` installs the candidate proof body with the original declaration's
statement and universe parameters. It forces kernel checking on, rejects the
target anywhere in the transitive dependency closure, and allows only the stated
standard Lean axioms. Each local explanatory theorem is also checked for axioms
and target dependency, even if the final root does not use it.

The dependency walk includes declaration types and bodies. Its inventory is
sufficient to exclude target calls under this trusted environment; it is not a
minimal mathematical dependency graph. Source size includes new helper code so
moving a proof into a fresh helper does not make that code disappear from the
measurement. The checker does not prohibit an independent pre-existing equivalent
library lemma; its dependencies remain inspectable.

The negative controls exercise direct and hidden target calls, a changed statement,
an extra assumption, an admission, and a wrong witness sign. Lean elaboration
executes code. Candidates, the checker, the pinned runtime and dependencies are
trusted; this is not a sandbox for hostile Lean metaprograms. Hashes bind retained
files, not the authenticity of the process that produced them.

Lean: `4.34.1`. Mathlib: `d13f23b723b8a846827a245b89c10fc7d3f11612`.
The OpenAI theorem body uses the existing two-import adapter. The complete OpenAI
project was not rebuilt. The other two original statements come from the pinned
Lean and Mathlib environments, not from the proposed candidate text.

## Reproduce

From the repository root, with the pinned Mathlib environment and its imports built:

```sh
python experiments/exposition-pilot/run.py \
  --lean /path/to/lean-4.34.1/bin/lean \
  --project /path/to/pinned-mathlib \
  --output /tmp/exposition-native --trust-project
python experiments/exposition-pilot/build.py \
  --evidence /tmp/exposition-native --output /tmp/exposition-reader.html
EXPOSITION_PILOT_EVIDENCE=/tmp/exposition-native \
  python -m pytest experiments/exposition-pilot/test_pilot.py -q
python experiments/exposition-pilot/check_reader.py /tmp/exposition-reader.html \
  --output /tmp/exposition-browser --mode file
```

Use a fresh native output directory. `--only` selects a subset of candidate IDs;
a completed subset is not the whole experiment. Failed proofs are expected in
the queue; completion means the checks ran, not that every proposal was accepted.
The page build requires the selected accepted alternatives and rejects missing
or inconsistent records.

The local 17-test suite passed. The in-memory Chromium audit checked all three
articles, exact source downloads, mobile width, 138 integer examples, 18 list
positions, all 16 four-entry diagonal patterns, and 12 off-diagonal edits. It
observed no page errors or remote requests. Local `file://` navigation was blocked
by administrator policy and is recorded as a failed check, not a pass. These
checks are not evidence of human comprehension or a new full-repository CI run.

## Next experiment

For an unfamiliar OpenAI proof, identify a small number of reader questions before
proposing candidates. Ask the model to supply a mathematical claim answering each
question, a proof of that claim, and an exposition that uses it. Validate the
claims and reconstructed theorem; keep the exposition's interpretation obligation
separate. Compare with plain source minimization and an unrefactored explanation.

The target is an argument a reader can reconstruct and reuse. Useful new lemmas
may increase source size. Do not optimize those lemmas away merely to improve the
length score, and do not interpret a model reader's preference as human feedback.
