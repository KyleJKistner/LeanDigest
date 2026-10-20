# Research tracks

The product line of this repository is the corpus reader. It renders the 492
retained source-bound readings and is measured by `leanglish reading-kpis`
(see `benchmarks/reading-kpis/README.md`). A research track is work whose result
does not yet reach those readings. Each track below states what it established,
what it cost, the conditions for continuing it, and the point at which that
decision is made.

## Certified English

> **Research track: certified English.** This line certifies one proof document
> for one proof schema: the supporting lemma
> `OAI.ComplexCancellation.BezoutFrame.exists_frame`. That lemma is not one of
> the 492 corpus readings, and no corpus reading is rendered through a certified
> grammar. The corpus measurements do not depend on the certified Lean modules.
> **Recommended status:** frozen until the [decision point](#decision-point).

### Pull requests

All six branches are contained in this consolidation branch through merge
2d5c837. The pull requests are open drafts; see docs/REPOSITORY_STATE.md.

| Pull request | Branch and head | Contents | New `lean/` modules (lines) |
| --- | --- | --- | --- |
| #5 | `work/swarm-reader-completion-20261018`, d6a0cb4 | `ControlledEnglish.lean`: a typed propositional derivation language, a token grammar with parse/render roundtrip, and rule soundness. The same commit adds the curated Bézout companion and the product contributions listed in [Contributions to the product line](#contributions-to-the-product-line). | 2 (650) |
| #6 | `work/checked-text-boundary-20261019`, 5c20704 | `ControlledEnglishText.lean`: extends the token theorems to Lean `String` values and UTF-8 bytes, and proves alignment with the intended rule (docs/CHECKED_TEXT_BOUNDARY.md). | 3 (437) |
| none | `work/editorial-style-20261019`, 8bcf420 | docs/STYLE.md and the companion heading inventory. No Lean. | 0 |
| #7 | `work/source-bound-cancellation-20261019`, 0742966 | The two `mul_left_cancel₀` sentences, at source frames 40 and 53, checked against their original proof occurrences (docs/SOURCE_BOUND_CANCELLATION.md). | 3 (579) |
| #9 | `work/source-bound-equations-20261019`, 84fa7ff | Ten equation chains with 19 adjacent source equalities, and two witness tuples (docs/SOURCE_BOUND_EQUATIONS.md). | 6 (801) |
| #10 | `work/proof-document-20261019`, 85d19cc | The complete canonical document: syntax, semantics, source binding, and `String` and UTF-8 certificates (docs/PROOF_DOCUMENT.md). | 4 (821) |

### Established results

According to docs/PROOF_DOCUMENT.md, and under the trust boundary stated there,
the native gate checks the following for `exists_frame`:

- The canonical text `artifacts/source-document/proof.txt`, as a Lean `String`
  and as UTF-8 bytes, is the rendering of a document in the grammar of
  `lean/ProofDocumentSyntax.lean`. The checked parser recovers that document,
  and no other document renders to the same text. The meaning of the document
  implies the theorem's statement for an arbitrary Euclidean domain.
- The document's case split, divisibility proofs, fourteen calculation and
  witness passages, and witness constructions are bound to their occurrences in
  the original elaborated proof. The branch-local facts are discharged from their
  original definitions rather than assumed.
- Eleven universal contracts hold, including the parser/renderer roundtrip,
  render injectivity and document soundness. Their axiom inventories contain
  only `propext`, `Classical.choice` and `Quot.sound`.
- The retained gate records sixteen intended negative controls, each rejected
  for its specified reason.

Separately, `ControlledEnglish.lean` and `ControlledEnglishText.lean` prove
universal theorems for an eight-rule propositional fragment: parse/render
roundtrip through `String` and UTF-8, rule soundness, and alignment of an
extracted sentence with its typed proof node. No importer connects this fragment
to a Lean declaration or proof path (docs/CONTROLLED_ENGLISH_PROTOTYPE.md).

The Actions run listing records these native gate runs as successful. Their
artifacts were not inspected for this page.

| Workflow | Run | Head |
| --- | --- | --- |
| `proof-document.yml` | 39346545246 | 85d19cc (PR #10) |
| `source-bound-equations.yml` | 39346545135 | 85d19cc (PR #10) |
| `source-bound-cancellation.yml` | 39346545311 | 85d19cc (PR #10) |
| `checked-companion.yml` | 39346545308 | 85d19cc (PR #10) |
| `checked-text-boundary.yml` | 39276117654 | 5c20704 (PR #6) |

### Scope limits

- **One schema and one proof.** `ArithmeticEnglish.lean` has a variable type
  with exactly the eight source names `x`, `y`, `z`, `g`, `a`, `d`, `r` and `s`.
  `ProofDocumentSyntax.lean` is a fixed sequence of fourteen typed fields and
  fixed statement, definition, case and conclusion paragraphs for this schema.
  A proof with a different structure or different variable names needs new
  syntax, new source-binding code and new native controls.
- **No corpus effect.** The 492 retained snapshots include
  `OAI.ComplexCancellation.main` but not `exists_frame`. The corpus reader is
  the Python renderer, and it does not use any certified grammar.
- **Outside the certificate.** The Python renderer, the curated companion prose,
  the HTML and JavaScript presentation, and a reader's interpretation of the
  words are outside the certificate. The original `ring` and rewrite leaf proofs
  remain dependencies, not explained steps.
- **Substituted imports.** The source theorem is rechecked under explicitly
  substituted minimal Mathlib imports. This is not a replay of the original
  OpenAI project or Comparator.

### Cost

Measured with `git diff --shortstat 01dfd1e 85d19cc`, the line's 20 commits
(2026-10-18 to 2026-10-20) change 358 files with 106,875 insertions and 194
deletions. The figures include the product contributions of PR #5.

| Area | Files | Inserted lines | Notes |
| --- | ---: | ---: | --- |
| Lean modules under `lean/` | 18 | 3,288 | All new modules. |
| Lean run inputs and negative controls under `artifacts/` | 72 | 5,120 | |
| All of `artifacts/` | 255 | 79,691 | 248 new files in `companion/`, `source-cancellation/`, `source-equations/` and `source-document/`, 2,697,526 bytes in total. This is 13.7% of the tracked `artifacts/` bytes at 04df977. |
| `proofreader/` | 15 | 1,204 | 421 of these lines are `source_text.py`, `equation_text.py` and `document_text.py`. |
| `scripts/` | 5 | 1,153 | Five `check_*.py` scripts. |
| `tests/` | 25 | 16,277 | Includes the audit fixtures. |
| `docs/` | 30 | 4,707 | Includes the companion pages. |
| `.github/workflows/` | 5 | 380 | Five native gates. |

Measured against 04df977 instead, `git diff --stat 01dfd1e 04df977 -- '*.lean'`
reports 92 files and 8,456 insertions. The two extra files and 48 lines are
commit 153bc35 on `work/full-original-project`, which changed
`lean/Narrative.lean` and its packaged copy `proofreader/data/Narrative.lean`.

The source-bound increments added their own Lean modules and native controls.
The two cancellation sentences added 579 lines of Lean modules and 14 generated
Lean files. The twelve equation and witness passages added 801 lines and 32
files. Assembling the document added 821 lines and 18 files.

Recurring CI cost: the five gates run on pull requests that touch their paths.
`checked-companion.yml` also runs on every pull request that changes
`proofreader/narrative.py`. On 85d19cc, the four gates that ran took between 2
minutes 45 seconds and 4 minutes 37 seconds each, measured from run creation to
the last update in the run listing.

### Effect of the merged reader stack on the corpus

The merged 0.4.2 reader stack moved the corpus from 7,587 gap steps
(`source-math-en/0.4.1`) to 7,635 gap steps (`source-math-en/0.4.2`), on the same
492 snapshots (corpus SHA-256 `9b34751d…`). See
`benchmarks/reading-kpis/baseline-source-math-en-0.4.1.json` and
`benchmarks/reading-kpis/current.json`.

| Measure | 0.4.1 | 0.4.2 |
| --- | ---: | ---: |
| Display steps | 18,275 | 18,275 |
| Gap steps | 7,587 | 7,635 |
| Gap step share | 0.4152 | 0.4178 |
| Gap frame share | 0.3379 | 0.3401 |
| Readings without gaps | 0 | 0 |

The certified-English Lean modules do not cause this change, because no corpus
reading uses them. It comes from the logical explanation rules that PR #5 added
to the Python renderer. Rendering every snapshot with both renderers and matching
steps by the frames they own gives the following:

- 191 steps that were gaps in 0.4.1 are explained in 0.4.2:
  `Decidable.byContradiction` 108, `Iff.mpr` 44, `Iff.intro` 15, `False.elim` 12,
  `Or.inl` 4, `Or.inr` 4, `Not.intro` 2, `absurd` 1 and
  `Classical.byContradiction` 1.
- 135 `And.left` and `And.right` steps moved from a fixed sentence, “Take the
  first conjunct.” or “Take the second conjunct.”, to the checked
  conjunction-projection rule.
- 239 `And.left` and `And.right` steps (120 and 119) that 0.4.1 described with
  the fixed sentence became gaps. The checked rule does not accept them. In
  224 the recorded premise does not print as the conjunction of the recorded
  components. In 15 the projection is applied to further arguments.
  docs/LOGICAL_EXPLANATIONS.md describes why the fixed sentence was not an
  explanation for such steps.
- 30 steps changed only by gaining a “Forward direction” or “Reverse
  direction” label, and kept their gap status; 18 of them are gaps in both
  versions.
- The other 17,680 steps have the same rule, text and gap status in both
  versions.

The net change is 191 fewer gaps and 239 more, an increase of 48. The increase
comes from no longer counting an unchecked, name-keyed sentence as an
explanation, not from removing a checked one. The measurement also shows that
the new rules have a small corpus effect: they explain 191 of the 7,587 gaps.

### Exit criteria

Continue this line only if one bounded increment demonstrates all of the
following.

1. **Reuse without per-proof modules.** One grammar and importer certify text in
   at least 10 of 20 corpus proofs. The 20 proofs are selected before work
   starts by a recorded rule that does not depend on whether the grammar fits,
   such as a seeded draw over the 492 snapshot digests. No proof may add a Lean
   module, a variable enumeration or a syntax definition. Per-proof input is
   data that the importer derives from the snapshot or the source. Proofs that
   do not fit are reported as unsupported, not replaced.
2. **Marginal cost.** After the first of these proofs, each additional proof adds
   no hand-written Lean. Its native check time and any added committed bytes are
   recorded per proof.
3. **Corpus effect.** `reading-kpis` reports the number of displayed steps whose
   text comes from a certified grammar; this measure does not exist yet. On the
   pinned corpus the count is at least 1% of display steps (183 of 18,275), and
   `gap_frame_share` does not increase.
4. **Unchanged boundaries.** Unsupported constructs fail closed. A certificate
   does not extend to surrounding prose, and no reading is relabelled as
   certified without its gate.

### Decision point

Make the decision before any new Lean module, native workflow or
proof-specific source binding is added to this line. Record it in this file with
the measurements for criteria 1 to 3.

- If the criteria are met, continue and set the next increment's criteria.
- If they are not met in one bounded increment, keep the line frozen. Frozen
  means that its modules, gates, documents and evidence stay in place and
  receive fixes, but the proof-specific modules are not extended.

### Contributions to the product line

Several results from this line already serve the corpus reader:

- **Logical explanation rules.** PR #5 added guarded rules for equivalence,
  disjunction, negation, contradiction and conjunction projection to
  `proofreader/narrative.py` (docs/LOGICAL_EXPLANATIONS.md). They explain the
  191 corpus steps above, and they replaced name-only conjunction text with a
  checked rule.
- **Gap accounting.** `proofreader/explanation_gaps.py` reconciles every
  unexpanded passage of a catalog against the deterministic renderer and the
  complete theorem denominator. The reader gained gap navigation
  (docs/READER_NAVIGATION.md).
- **Editorial conventions.** docs/STYLE.md and the companion heading inventory
  govern headings, labels and documentation across the repository.
- **Specification.** The correctness requirements in
  docs/CORRECT_BY_CONSTRUCTION.md separate soundness, source correspondence,
  rendering fidelity, coverage and usefulness. The alignment requirement in
  docs/CHECKED_TEXT_BOUNDARY.md, that a true sentence need not be the intended
  inference, applies to any future explanation rule.
- **Negative controls.** The native gates require specified rejections, such as
  altered text, a false kernel claim or a kernel-bypass setting, as well as
  positive runs.
