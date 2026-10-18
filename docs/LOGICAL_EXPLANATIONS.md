# Guarded logical explanations

This change improves the source-bound narrative reader. It does not change the
snapshot schema, infer a proof from tactic text, or turn a retained receipt into
an authenticated certificate. The exact constructor-DAG reader is unaffected.

## Supported rules

The new explanations use the existing source-bound object arguments, proof
premises, printed statements and original proof paths. The slots below are
zero-based positions in the complete Lean application, including implicit
arguments.

| Head | Object arguments | Proof slots | Required printed relationship | Explanation |
| --- | --- | --- | --- | --- |
| `Iff.mpr` | `P, Q` | `2, 3` | `P ↔ Q`, `Q`, conclusion `P` | Apply the reverse direction of the equivalence. |
| `Iff.intro` | `P, Q` | `2, 3` | `P → Q`, `Q → P`, conclusion `P ↔ Q` | Prove both directions in separate subproofs. |
| `Or.inl` | `P, Q` | `2` | `P`, conclusion `P ∨ Q` | Establish the left alternative. |
| `Or.inr` | `P, Q` | `2` | `Q`, conclusion `P ∨ Q` | Establish the right alternative. |
| `False.elim` | `P` | `1` | `False`, conclusion `P` | Derive the required conclusion from a contradiction. |
| `Not.intro` | `P` | `1` | `P → False`, conclusion `¬P` | Derive a contradiction from the proposition being negated. |
| `Decidable.byContradiction` | `P, decision instance` | `2` | `¬P → False`, conclusion `P` | Use the recorded decision instance for contradiction reasoning. |
| `Classical.byContradiction` | `P` | `1` | `¬P → False`, conclusion `P` | Use classical contradiction reasoning. |
| `Not.elim` | `P` | `1, 2` | `¬P`, `P`, conclusion `False` | Combine a proposition and its negation. |
| `absurd` | `P, Q` | `2, 3` | `P`, `¬P`, conclusion `Q` | Derive the conclusion from contradictory premises. |
| `And.left` / `And.right` | `P, Q` | `2` | `P ∧ Q`, conclusion `P` / `Q` | Take the corresponding conjunct. |

`Not.elim` and `absurd` have **synthetic regression coverage only** in this
change. They do not occur in the frozen 216-reading corpus used for the
measurement below. The conjunction rules replace older name-only descriptions;
they are a correctness tightening, not a newly supported proof family.

Every specialization requires all of the following:

- An uncut application frame with exactly the expected object count and proof
  argument slots.
- Children exactly equal to the ordered premise-frame inventory, with no extra
  child, proof or object argument.
- For argument `k` of an `arity`-argument application, the child's original path
  equals the parent path followed by `arity-k-1` zeros and a final `1`.
- The child context equals the application's context. The snapshot validator
  independently enforces enclosing binder scope and premise-statement identity.
- The displayed premise and result types have the required logical structure.
  If a premise is a lambda, its actual assumption domain and body conclusion
  must also match.

No descendant is absorbed by these new rules. Every original frame has exactly
one owner. An unexplained lemma or a budget-cut premise remains a separately
flagged child even when the surrounding logical inference is explained. For
equivalence introduction, each lambda assumption and its continuation stay
inside that direction's subproof. A limited set of sequence-producing branch
shapes remains unsupported rather than being flattened across directions.

## Formula matching and conservative fallbacks

The matcher is a small display grammar, not a Lean parser or type checker. It
ignores whitespace and balanced parentheses around an entire expression. It
does not rename binders, unfold definitions, substitute local definitions, or
decide definitional equality.

The grammar observes the relative precedence of `↔`, `→`, `∨` and `∧`. The last
three associate to the right. Unparenthesized iterated `↔` is rejected. Negation
is matched at its actual scope: `¬(P ∧ Q)` is supported, while `¬P ∧ Q` cannot be
used as its substitute. `P → False` may also represent negation. Compact or
partially spaced outer connectives such as `¬P∧Q` are rejected instead of being
mistaken for a single negated atom.

Unparenthesized binders and control syntax are deliberately not split at an
operator inside their body. Thus `(∀ n : Nat, n = n) ∧ Q` can expose the quantified
left component, whereas `∀ n : Nat, n = n ∧ Q` cannot. Quoted strings/names,
comments, unmatched delimiters and grouping deeper than 64 levels are outside
the matching grammar. Their frames remain readable as recorded terms with an
explanation gap.

The new conjunction guards expose two old limitations. An application of a
projection to extra arguments can specialize a quantified conjunct or apply a
negation to obtain `False`; saying only “take the first conjunct” does not explain
those subsequent inferences. Even an unsaturated projection may operate on a
named predicate whose conjunction expansion is absent from its printed premise.
That conversion remains an explicit gap when this matcher cannot establish it.

For example, a real retained counterexample proof projected `A ∉ U` from a
conjunction and then applied it to membership evidence to obtain `False`. The
old output marked that complete after describing only the projection. It now
retains the complete argument tree and marks the unexpanded application.

## Plain-text fidelity

`prose()` now prefixes each fallback step with `[Explanation gap]`. The marker is
emitted once per flagged step, including nested premises. The text also states
that the English is not formally verified and that reading it does not
authenticate the Lean snapshot. These distinctions previously existed in the
structured document and browser but disappeared from a standalone `proof.txt`.

## Measurement on the retained release

The comparison uses base commit
`01dfd1eea1b74150e48f9af1ec415792ef0bbd5b` and the unchanged Leanglish 0.4.1
release archive with SHA-256
`1cc4f4cc5728095fb0e024f85c7fe53b80fc4e12e1525499b2ce3965b4fdd637`.
This is regeneration from real retained snapshots, **not fresh Lean execution**.

| Measure | Before | After |
| --- | ---: | ---: |
| Retained readings | 216 | 216 |
| Selected source-bound frames | 9,272 | 9,272 |
| Displayed proof steps | 7,369 | 7,369 |
| Budget-cut frames | 0 | 0 |
| Explicit explanation gaps | 3,005 | 3,001 |

The small net decrease combines two substantial changes:

| Newly explained logical steps | Count |
| --- | ---: |
| `Decidable.byContradiction` | 44 |
| `Classical.byContradiction` | 1 |
| `Iff.mpr` | 22 |
| `Iff.intro` | 9 |
| `False.elim` | 7 |
| `Not.intro` | 2 |
| `Or.inl` | 3 |
| `Or.inr` | 3 |
| **Total** | **91** |

Conversely, **87 formerly unflagged conjunction projections become explicit
gaps**: eight oversaturated applications, plus 79 whose printed premise does not
match the supported conjunction relationship. Named predicate expansions and
quantifier-heavy printed forms occur in that latter group. This count should
not be hidden to make the coverage number look better. There are 2,914 unchanged
old gaps, 87 newly exposed gaps, and therefore 3,001 remaining gaps.

Fifty readings have a different gap count. For example,
`OAI.CirculantHadamard.exists_iff_order_one_or_four` decreases from 13 gaps to 7,
and `OAI.SubpolynomialLp.source_main` decreases from 18 to 16. Unknown arithmetic,
named dependencies, unsupported conversions and their original source paths
remain visible. No additional theorem target has been extracted by this patch.

## Verification and reproduction

The focused suite executed with 196 passing tests:

```sh
python -m pytest -q tests/reader/test_logical_explanations.py \
  tests/test_narrative.py tests/test_narrative_logic.py \
  tests/test_specialization_contracts.py tests/test_local_applications.py
```

The new file contains 101 tests. Most use explicitly labelled synthetic format
fixtures; two read the 14 unchanged OpenAI snapshots already retained under
`artifacts/pinned-openai-slice`. The latter observe two reverse-equivalence and
two negation-introduction improvements while retaining automated-proof gaps.

The independent audit workstream additionally challenged exact release
regressions and malformed logical shapes. Its tests and results are integrated
by the supervisor separately. In particular, it found and falsified an early
compact-negation ambiguity before this change was finalized.

To reproduce the full-release count after unpacking the pinned archive into
`/tmp/leanglish-v0.4.1/Leanglish`, run from the repository root:

```sh
python - <<'PY'
import json, subprocess, types
from pathlib import Path
from proofreader.model import walk_steps
from proofreader.narrative import Narrative

base = types.ModuleType('proofreader.logical_baseline')
base.__package__ = 'proofreader'
exec(subprocess.check_output([
    'git', 'show', '01dfd1eea1b74150e48f9af1ec415792ef0bbd5b:proofreader/narrative.py'
], text=True), base.__dict__)
root = Path('/tmp/leanglish-v0.4.1/Leanglish')
paths = sorted(root.rglob('snapshot.json'))
assert len(paths) == 216
totals = {'readings': 0, 'frames': 0, 'before_gaps': 0, 'after_gaps': 0}
for path in paths:
    record = json.loads(path.read_text())
    old, new = base.Narrative(record), Narrative(record)
    before, after = old.document(), new.document()
    assert set(old.owners) == set(new.owners) == set(range(len(record['frames'])))
    totals['readings'] += 1
    totals['frames'] += len(record['frames'])
    totals['before_gaps'] += sum(s.fallback for s in walk_steps(before.declarations[0].steps))
    totals['after_gaps'] += sum(s.fallback for s in walk_steps(after.declarations[0].steps))
print(totals)
PY
```

No Lean/Lake toolchain was available in this worktree, so no new native extraction
or kernel replay was executed. The release's source-bound observations remain
the input evidence. English semantic certification, human comprehension and
whole-corpus completion remain separate, unpassed gates. The supervisor owns the
printer-version bump, regenerated release artifacts and integration acceptance.
