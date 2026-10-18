# Independent reader audit — 2026-10-18

## Scope and result

This audit inspected the source-bound narrative reader independently of the
agent implementing new explanations. It found two issues in the published
v0.4.1 reader and one additional defect in the first proposed logical-rule
implementation. Reproducible regressions are in `tests/audit/`; this audit
workstream changes no production code.

The retained-input audit covered all **216 snapshots and 9,272 recorded frames**
in the frozen v0.4.1 offline catalog. It performs Python loading, rendering, frame
accounting, and output inspection. It does **not** rerun Lean, authenticate the
observations, validate the original project or Comparator, certify English
semantics, or measure comprehension by mathematicians.

Baseline application commit:
`01dfd1eea1b74150e48f9af1ec415792ef0bbd5b`.
Baseline `proofreader/narrative.py` SHA-256:
`111f885e1f1d7b44dd56e90d8780fac9c3329ad731c2178a2f626e454c1daa53`.

The candidate code from the logical-explanations workstream was independently
tested at file SHA-256
`bd2e056fe00f6cfd71216261c107faf59d6fc026a825b0e191d2515938fd63eb`.
This is a code checkpoint, not a claim that the existing release was republished.

## R1 — Projection was mistaken for the complete application

**Observed in real retained readings.** The old reader recognizes `And.left` and
`And.right` by their names and emits “Take the first conjunct” or “Take the
second conjunct” without checking whether additional arguments were supplied.
Eight affected frames occur across seven readings:

| Theorem suffix | Frames | Missing explanation |
| --- | --- | --- |
| `AbhyankarSathaye.exists_noncoordinate_polynomial` | 3 | Specialize the projected quantified claim to a dimension and its bound proof. |
| `InfiniteMatroidCounterexample.partitional_intersection_counterexample` | 41 | Apply a projected negation to a contrary membership hypothesis to derive `False`. |
| `Fifths.Single.unknown` | 32 | Specialize the projected claim to `T` and supply `T ≥ 2`. |
| `DiamondDistortion.headline_all_pairs` | 7, 20 | Specialize four object arguments and apply the distortion hypothesis. |
| `TraceConeClassification.ClosedIdeal.le_iff_add_weight` | 16 | Specialize two elements and apply ideal membership. |
| `HadwigerCounterexample.exists_counterexamples` | 31 | Apply three hypotheses to the projected conditional statement. |
| `RadialTransition.densityInterval` | 240 | Specialize the projected claim to `n`. |

The InfiniteMatroid case makes the difference especially clear: the first
conjunct is a non-membership statement. `False` is obtained only after that
negation is applied to the contrary membership proof. Calling the whole step
merely “Take the first conjunct” omits a real inference. All eight old steps had
`fallback=False`, so the existing explanation-gap ledger also omitted them.

The proof observations themselves remain unchanged. The corrective contract is
to explain the projection **and** the subsequent application, or keep the
unexplained application as a visible gap. The candidate chooses the conservative
gap and adds structural/type guards to the ordinary projection template.

Two complete, unmodified release snapshots are retained under
`tests/audit/fixtures/`. Their exact byte hashes and release locations appear in
`provenance.json`. These fixtures cover both left/right object specialization
and the projected-negation case. The read-only `inspect_release.py` script
enumerates all eight cases against the full extracted release.

## R2 — Plain-text export dropped explanation-gap and trust labels

**Observed across all 216 retained readings.** The original `prose()` emitted
step text and conclusions, but neither the fallback flag nor the document's
evidence boundary. The JSON and interactive reader retained those distinctions;
a standalone `proof.txt` did not.

The candidate inserts `[Explanation gap]` for each fallback step and a short
statement that the English is not formally verified and rendering does not
authenticate the snapshot. The audit checks the count against the actual step
inventory, including nested steps, and checks the standalone evidence statement.
It does not equate absence of gaps with certified English.

## R3 — Compact connectives could change the scope of negation

**Synthetic falsifier against the first candidate, caught before integration.**
The new small formula matcher initially ignored an outer logical connective
unless it had a space on both sides. This allowed a compact suffix to be treated
as a single atomic proposition after a negation.

For example, an explicitly synthetic `Not.intro` application with:

- Recorded proposition argument: `P∧Q`.
- Supplied premise: `¬(P∧Q)`.
- Claimed result: `¬P∧Q`.

was described as “To prove ¬P∧Q, derive False from P∧Q” with `fallback=False`.
The two negations have different scope: `¬P∧Q` means `(¬P) ∧ Q`, whereas the
premise negates the whole conjunction. Removing spaces does not change the
operator binding.

The implementing agent reproduced the counterexample and changed the matcher to
reject compact outer logical operators. Nine independent regressions cover
compact conjunction, disjunction, implication, equivalence, mixed whitespace,
and the same problem in a contradiction assumption. Unsupported notation now
stays a gap. These records are schema/renderer fixtures, not observed Lean runs.

## Independent controls and scope checks

The 96 audit tests consist of nine retained-observation checks and 87 synthetic
logical-rule checks. The synthetic tests build explicit proposition parameters
and proof hypotheses; they do not import the renderer's formula matcher. They
challenge wrong directions, changed conclusions, implication and negation scope,
proof-child reordering, altered source paths, incorrect premise slots, extra
arguments, and budget flags. Simple logical controls verify that supported
inferences still render and preserve every frame.

A real disjunction in the InfiniteMatroid fixture keeps its branch-local
assumption inside the case step. That control passed both before and after the
candidate change. Full frame ownership also passed for all 216 frozen snapshots.
No source-frame budget cuts occur in this particular frozen corpus, so it is not
evidence for every possible truncated-input presentation.

The audit also found an earlier exact-DAG layout checker on
`dev/native-and-corpus` at
`65dfc8e2b4d401cb3d85f49ca23ea1fc09100e1e`, absent from main. Its structural checks
identify binders by original occurrence paths, reject escaped local assumptions,
and enforce complete step/support accounting without importing English
templates. Recovery was recommended to the supervisor as a separate change.
That checker applies to the exact-DAG format; it does not validate narrative
formula strings or establish English semantics.

## Executed checks

The following local runs used Python 3.11+ and the isolated test environment:

| Check | Reader under test | Observed result |
| --- | --- | --- |
| `python -m pytest tests/audit/test_retained_reader_regressions.py -q` | Baseline | Exit 1: 7 failed, 2 passed; the failures expose R1/R2. |
| `python -m pytest tests/audit/test_logical_rule_adversarial.py -q` before the nine R3 tests were added | Baseline | Exit 1: 19 failed, 59 passed; includes eight unsupported new-rule positive controls and eleven old projection-guard failures. |
| `python -m pytest /path/to/audit-checkout/tests/audit -q` | Candidate | Exit 0: 96 passed. |
| `python tests/audit/inspect_release.py /path/to/Leanglish` | Baseline | Exit 0: 216 snapshots, 9,272 frames, 3,005 gaps; eight unmarked oversaturated projections; 216 plain-text marker mismatches. |
| Same inspection function, imported after the candidate reader | Candidate | Exit 0: same 216 snapshots and 9,272 frames; 3,001 gaps; zero unmarked oversaturated projections; zero plain-text marker mismatches. |

The candidate's net explanation-gap change at this checkpoint is **−4**. Newly
explained rules and newly exposed gaps must be reported separately; gross new
template matches are not the net reduction. The conservative projection guards
also flag ordinary cases whose recorded types are definitionally equal but
printed differently.

No tests are suppressed with `xfail`. The regressions intentionally fail against
the baseline and must be integrated together with their production fixes.

## Release inventory and report integrity follow-up

The independent release inspector now rejects missing, empty, duplicated,
misplaced, or mismatched snapshot/reading inputs. It reconciles coverage counts
with the saved comparison configurations, exact proof identities, full source
frame ownership, and the saved readings' own gap total. Saved gaps remain a
separate baseline from newly rendered gaps, since a reader improvement may
legitimately change that number. Its JSON includes the actual printer version,
byte hashes of all inventory inputs, and the SHA-256 of their sorted mapping.

The `--verify-manifest` option additionally checks the complete file inventory
and every byte digest against `SHA256SUMS.json`. This establishes consistency
with the saved manifest; it does not authenticate its publisher or replay Lean.
On the frozen release, all 4,809 manifest entries matched. The reconciled
inventory remains 416 configurations, 536 theorem targets, 216 available
readings, 320 unavailable readings, and 9,272 selected frames. Its inventory
SHA-256 is
`807e661eb7d5e4c5f7fa67e1a6e6b3c18b401e16f8c48f3eb5a36c048f4564bc`.
The original saved readings report printer `source-math-en/0.4.1`; the actual
candidate still reported that same version at this checkpoint, so the reader
file hash distinguishes the changed implementation.

Four further independent synthetic falsifiers challenge the supervisor's gap
report: a missing target reader page, a coverage edit that erases unread
theorems, a specification source renamed to a canonical proof directory, and
saved solution text that differs from the reading. The supervisor corrected all
four; these tests now pass. Together with 20 inspector integrity tests and the
previous 96 reader tests, the integrated candidate passed **120 audit tests**.
The fixture files explicitly identify these as synthetic accounting checks,
not Lean observations or mathematical verification.

## Remaining boundaries

This is a bounded independent reader audit. It does not prove the formula parser
correct for arbitrary Lean notation, give imported JSON authority, or validate
every historical logical template. Legacy named-lemma explanations and some
compression rules remain outside the new guarded fragment. Further progress
should use recorded argument/type information to explain compound applications
while preserving their intermediate claims, rather than changing the fixed
theorem denominator or hiding newly discovered gaps.

## Independent mathematical review: the Bézout frame

### Decision and scope

`OAI.ComplexCancellation.BezoutFrame.exists_frame` is suitable for a carefully
scoped companion reader. Its 34-line statement and proof contain a complete,
explicit construction, with a nontrivial use of the extended Euclidean algorithm
and two justified cancellations. The mathematical argument below has been
independently checked against the source body and the retained selected frames.
It is a supporting theorem in the affine-cancellation source tree. It is not the
headline affine-cancellation claim, and this review establishes no result about
that larger dependency chain.

The original source is
`examples/openai/lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean`, identical
to `proofreader/data/bezout-original.lean`, with file SHA-256
`d108afa98f200bfce183b8afc0af586b70734f7ad2cce1bc5e49853a2f555c6f`.
The namespace, theorem, and proof body in `bezout-context.lean` are unchanged;
its import header uses minimal Mathlib modules in place of the original
`OAI.Algebra.AffineCancellation.Model` import. The saved receipt explicitly
records that adaptation and `exact_openai_project_replayed: false`.

### Exact statement and definitions

Let $R$ be a Euclidean domain and let $x,y,z\in R$ satisfy
$xy=z(z+1)$. Then there exist $a,d,b,c\in R$ such that

$$ab=x,\qquad dc=y,\qquad db=z,\qquad ac-db=1.$$

A Euclidean domain supplies a commutative ring without zero divisors, a greatest
common divisor, and the extended Euclidean identity. The proof uses precisely
the following facts about $g=\gcd(x,z)$: it divides both entries; $g=0$ implies
$x=z=0$; and there are coefficients $r,s$ with $xr+zs=g$. A nonzero common
factor can be cancelled because the ring has no zero divisors. No order,
positivity, characteristic-zero assumption, or invertibility of a nonzero
element is used. In particular, the argument does not divide by an arbitrary
ring element. The theorem applies to the integers and to a univariate polynomial
ring over a field; it does not assert that an arbitrary ring is Euclidean.

For a matrix interpretation, fix the placement
$M=\begin{pmatrix}a&d\\b&c\end{pmatrix}$. The fourth equation says
$\det M=1$, and the other equations recover $(x,y,z)$ from its entries. Matrix
notation is explanatory context; the Lean theorem itself states the four
scalar equations. It does not claim a unique lift or a preferred normalization
of the gcd.

### Complete proof audit

Set $g=\gcd(x,z)$. If $g=0$, then $x=z=0$. Take
$(a,d,b,c)=(1,y,0,1)$. The required identities become
$1\cdot0=0$, $y\cdot1=y$, $y\cdot0=0$, and
$1\cdot1-y\cdot0=1$. This branch permits arbitrary $y$ and makes no
cancellation.

Suppose instead that $g\ne0$. Choose $a,d$ with $x=ga$ and $z=gd$.
For the extended Euclidean coefficients $r,s$, the equation $xr+zs=g$ gives

$$g(ar+ds)=xr+zs=g=g\cdot1.$$

Cancelling the nonzero factor $g$ yields

$$ar+ds=1.\tag{B}$$

The original hypothesis gives a second equality with a common factor:

$$g(ay)=xy=z(z+1)=g\bigl(d(z+1)\bigr).$$

Cancelling that same nonzero $g$ yields

$$ay=d(z+1).\tag{R}$$

Now define $b=g$ and $c=r(z+1)+sy$. Commutativity immediately gives
$ab=ag=x$ and $db=dg=z$. The second required product is

$$
\begin{aligned}
dc&=d\bigl(r(z+1)+sy\bigr)\\
  &=r\bigl(d(z+1)\bigr)+dsy\\
  &=r(ay)+dsy &&\text{by (R)}\\
  &=(ar+ds)y=y &&\text{by (B)}.
\end{aligned}
$$

Finally,

$$
\begin{aligned}
ac-db
 &=a\bigl(r(z+1)+sy\bigr)-dg\\
 &=ar(z+1)+s(ay)-z &&\text{since }dg=z\\
 &=(ar+ds)(z+1)-z &&\text{by (R)}\\
 &=(z+1)-z=1 &&\text{by (B)}.
\end{aligned}
$$

All four witness equations hold. Neither cancellation uses a hidden assumption
that $a$, $d$, $x$, $y$, or $z$ is nonzero. The special possibilities $x=0$,
$z=-1$, or $y=0$ are therefore not excluded. Classical choice in the Lean source
supplies decidability and chosen coefficients; an explicit mathematical formula
does not by itself make this an executable algorithm for every abstract $R$.

### Source-to-English correspondence

These frame identifiers belong to the retained snapshot with canonical digest
`dad8ef23a231904f37b73979f8284ea3662ffe8f8cd30c79066856f2095b4dd7`.
They identify selected original proof subterms, not source line numbers or a
complete expansion of imported facts.

| Mathematical passage | Retained frames | Audit result |
| --- | --- | --- |
| Domain, variables, and $xy=z(z+1)$ | 0–5 | The statement's only mathematical assumptions. |
| Define gcd and split $g=0$ versus $g\ne0$ | 6–8, 24 | Both exhaustive branches remain explicit. |
| Zero gcd implies $x=z=0$ | 9–12 | Forward use of the recorded gcd equivalence; $g$ unfolds to the gcd. |
| Zero-case tuple and its four identities | 13–23 | All equations checked above; no nonzero premise appears. |
| Gcd divisibility and choices of $a,d$ | 25–36, 84–85 | The later `change` steps only unfold the local definition of $g$. |
| Extended Euclidean coefficients and identity (B) | 37–51 | Cancellation frame 40 has explicit nonzero premise 44 and equality premise 45; frames 41–43 supply the domain cancellation instance. |
| Derive relation (R) | 52–62 | Cancellation frame 53 has nonzero premise 57 and equality premise 58; frame 61 is exactly the original hypothesis. |
| Choose $(a,d,g,r(z+1)+sy)$ | 63–67 | Witness order is $a,d,b,c$, matching the theorem. |
| Verify $ab=x$ and $db=z$ | 68, 78 | Use the appropriate factorization and commutativity. |
| Verify $dc=y$ | 70–76 | Rewrites use (R), then (B), in the active nonzero branch. |
| Verify $ac-db=1$ | 79–83 | Uses $z=gd$, then (R), then (B), preserving the subtraction sign. |

The local context at both cancellations contains $g\ne0$; at the final
calculation it also contains (B) and (R). No fact from the zero branch is used in
the nonzero branch. The displayed names `ha` and `hd` occur twice in this older
snapshot because `change` introduces definitionally equal hypotheses; their
types agree after unfolding $g$, and the audit did not treat a shadowed printed
name as an independent assumption.

The current deterministic rendering has 86 selected frames, 16 independent
polynomial certificates, and zero declared explanation gaps. The command
`python -m proofreader check-narrative proofreader/data/bezout-snapshot.json
artifacts/v0.3/bezout-reader/reading.json --certificates
artifacts/v0.3/bezout-reader/polynomial-certificates.json` exited 0:
regeneration passed and the supplied certificates replayed. It explicitly
reported `lean_rerun: false` and `english_formally_verified: false`. Those
mechanical results complement the mathematical audit above; the gap count alone
does not prove explanation completeness.

### Comparison with the shorter entropy helper

`OAI.MatchingEntropy.entropy_barrier_ge_id`, retained in
`originals/OAI/Combinatorics/PerfectMatching/Main.lean`, has a 22-line
statement/proof. It says $0\le t\le\log 8$ implies
$t\le8(1-e^{-t})$. Its full elementary argument is: set $u=e^t$, so
$1\le u\le8$; the logarithmic inequality gives $t=\log u\le u-1$;
then $tu\le8t\le8(u-1)$, and division by positive $u$ proves the claim.
Both uses of the interval hypotheses and the positivity needed for division are
explicit. This is mathematically sound and shorter in source lines.

The entropy helper is a familiar real-analysis estimate used inside a much
larger matching-entropy argument. The Bézout helper offers a more distinctive
complete construction and an already retained standalone reading. Neither is a
headline OpenAI result on its own. Prefer Bézout for the current demonstrator;
describe it as a selected supporting theorem, and do not advertise the
34-line count as a proved global minimum over all OpenAI results. This count is
the inclusive range from source line 11 to line 44; it excludes the trailing
blank line.

## Architectural audit: what correct-by-construction would establish

The existing source-bound route already checks selected Lean judgements and
their original expression paths during extraction. `checkPaths` compares
structural expressions after metadata erasure. Its exported formula fields,
however, are pretty-printed strings. Python's source-to-English templates,
string matching, arithmetic parser, and formatting are outside the Lean soundness
argument. Deterministic regeneration only proves that the same implementation
reproduces the same document. It cannot rule out a consistently wrong template,
as the oversaturated projection and negation-precedence falsifiers illustrate.

A stronger architecture needs separate, testable claims:

| Claim | Necessary contract | What the contract does not establish |
| --- | --- | --- |
| The explained inference is valid | A typed explanation term indexed by its exact local context and proposition, with a Lean theorem interpreting every constructor as a proof. | That the explanation follows the original proof, or that a person understands it. |
| The explanation reads this source proof | A checked mapping from explanation nodes to original expression occurrences and dependency edges, with defined, checked compression rules. | Semantic fidelity of free-form display text. |
| The displayed text has the proved formal meaning | A specified controlled grammar and semantics, plus a proved renderer/parser correspondence such as `parse(render(e)) = some e`. | That unrestricted natural language has that semantics. |
| The entire claimed explanation is covered | An exact inventory of owned source dependencies; unsupported steps represented as explicitly incomplete summaries rather than verified-proof constructors. | Expansion of every imported theorem or absence of every possible knowledge gap. |
| The explanation is relevant | Explicit connection of each claimed inference to the target and its dependency structure; no unrelated premises or ornamental steps presented as necessary. | That the chosen level of detail is useful to a particular reader. |
| The explanation is helpful | Reader evaluation with representative tasks and audiences, or a clearly labeled formal proxy for presentation quality. | A universal mathematical theorem about human comprehension. |

Proof validity and original-proof identity require different checks. In Lean,
proof irrelevance makes proofs of the same proposition indistinguishable for
some equality/definitional-equality purposes. Replacing a source subproof by a
fresh proof of its proposition can satisfy a semantic soundness theorem while
failing to explain the original argument. Retain the raw occurrence/path check;
do not replace it with equality of proof values.

Atoms, labels, and binders are the critical display boundary. An uninterpreted
atom with a human-selected label is not automatically the Lean proposition that
the label appears to describe. Arbitrary text must not smuggle logical operators,
change connective precedence, capture a binder, or impersonate another named
constant. Use typed formula syntax and stable identities for the formal payload;
derive visible names under a defined naming/escaping policy. A parser that
ignores human-visible text and reads hidden metadata would not close this gap.

The first prototype should be challenged with swapped implications, wrong
disjunction sides, a missing nonzero cancellation premise, escaped branch
assumptions, different witnesses, atom-label injection, and one-character output
changes. A sound propositional fragment is a valuable mechanized result, but it
cannot immediately certify the Bézout proof, arbitrary Lean constructs, the
existing snapshot pipeline, or a hand-authored companion. Any explanatory prose
outside the controlled grammar must be clearly outside the formal guarantee.

### Mechanized prototype audit completed

The final `lean/ControlledEnglish.lean` prototype was independently compiled with
Lean 4.34.1, followed by `lean/ControlledEnglishAudit.lean`. Both commands exited
0. The latter proves that a local assumption cannot escape to an empty context,
an implication cannot be reversed from its consequent, a disjunction cannot
supply one selected side, an unrelated disjunction cannot replace the supplied
alternative, and contradiction cannot appear without a premise. A sixth theorem
shows that a grammatical reversed-implication sentence has a false semantic
interpretation under a concrete atom valuation. This directly checks the
distinction between parsing and validity.

Positive controls permit outer assumptions within a case proof, preserve nested
formula scope, and require right-disjunction extraction to retain its exact
premise and conclusion. Malformed atom bounds, formula/sentence delimiters, and
trailing tokens are rejected. Assumption-reference and implication-introduction
prose deliberately remain unsupported (`rootRule? = none`). There are no admitted
proofs; the audit's axiom printout contains only `propext`, `Classical.choice`,
and `Quot.sound` where used, and no axioms for the empty-context contradiction
and scope countermodels.

The prototype's `Derivation.sound`, `Rule.sound`, typed source-obligation bridge,
and node/sentence alignment theorem are sound within their stated fragment. The
alignment theorem requires the extracted sentence's exact conclusion and proves
that its premises are available under the node's context. The formula and
sentence parser/render roundtrips cover typed `List Token`, and
`Rule.rendered_sound` connects a supported local inference's emitted tokens to
its formal logical meaning. This is more than formula formatting. It remains
short of complete proof-tree prose, a verified String/HTML bridge, an importer
from the snapshot pipeline, Bézout arithmetic, or proof of usefulness.

The independent review of `docs/CORRECT_BY_CONSTRUCTION.md` and
`docs/CONTROLLED_ENGLISH_PROTOTYPE.md` found these boundaries clearly stated. One
ambiguous sentence about global acceptance was referred to the supervisor and
corrected: certifying a fragment or one document cannot certify the whole corpus.

### Fresh native evidence and historical correspondence

The supervisor subsequently retained fresh native Bézout evidence using Lean
4.34.1 and Mathlib commit
`d13f23b723b8a846827a245b89c10fc7d3f11612`, under the explicitly adapted minimal
imports. Its snapshot has canonical digest
`e93e0455259fc3283983f3a47f956cdac4b1a28869bc5027bcc694b4a124d8d0`.
This audit compared the complete old and new records, not just their headline
statement or frame count. They are exactly equal after only these recognized
display changes: the generated instance binder becomes `inst`, rebound `ha`
and `hd` become `ha_1` and `hd_1`, and six object arrays replace the printed
instance reference `inst✝` with `inst`. Corresponding context labels change in
84 frames; context types and their ordering do not change.

All 86 frame IDs, original expression paths, roles, heads, child edges, premise
records, statements, domains, values, and budget flags match exactly. Thus the
mathematical frame mapping above still applies. Generated reader step IDs have a
different digest prefix, so links must use the identity of the snapshot actually
packaged with the companion. `tests/audit/bezout-native-comparison.json` records
the input identities and bounded comparison result; it is not a general semantic
equivalence checker or a native execution receipt.

The historical driver's exact re-extraction remains recorded as failed because
its older generated names depended on the temporary module. The fresh run has
its own exact repeat and hostile mutation results. A successful fresh observation
does not convert the failed historical comparison to a pass, nor does it replay
the original OpenAI project.

During review of the native checker, a real stale-evidence failure was reproduced:
a previous `observation.json` with `status: passed` survived a new run that
rejected the wrong project before preflight completed. The supervisor moved the
initial failed observation before source/project/dependency checks.
`test_companion_failure_state.py` failed before that correction and now passes;
it exercises no Lean compiler or network operation.

### Final companion review

The finished `docs/companion/index.html` and its editable template were reviewed
against the original source and fresh snapshot. The theorem, definitions, both
branches, four equations, explicit matrix placement, and necessity/sufficiency
motivation agree with the mathematical audit. All six source-line ranges end at
the relevant calculations, and every selected frame belongs to the intended
editorial group under the fresh snapshot identity. The three integer examples
use exact arithmetic and check the hypothesis, intermediate relations when
applicable, and every witness equation.

An additional copied-evidence challenge altered the saved deterministic reading
and recomputed its unsigned manifest hash. The companion builder rejected it
with a deterministic-regeneration error; matching hashes alone did not allow
the altered prose through. No mathematical or source-correspondence blocker was
found in the final companion. Browser interaction and visual checks remain the
reader-navigation workstream's responsibility. The complete independent Python
audit suite finished with **121 passed**.

