# Glossary of cited lemmas

A gloss is a short mathematical phrase for one cited library constant, such as
"transitivity of ≤" for `le_trans`. Glosses are written when the dictionary is
built, not when a reading is rendered: `proofreader/data/glossary.json` is
fixed data, and rendering makes no model call. A model may propose a gloss; a
named human reviewer must accept it before it changes any default reading.

## Status

The glossary has 85 entries. All 85 were proposed by a model and have status
`proposed`; none has been reviewed, because no reviewer has looked at them yet.
Default readings are therefore unchanged: `benchmarks/reading-kpis/current.json`
regenerates byte for byte, and so does every per-reading row.

`docs/glossary-review/README.md` is the review document for these proposals.

## Data format

`proofreader/glossary.py` validates the schema `leanglish.glossary/v1`:

| Field | Meaning |
|---|---|
| `schema`, `description` | Schema name and a description of the file. |
| `sources` | Each quoted repository (an https URL) with its revision: `mathlib4` at `d13f23b723b8a846827a245b89c10fc7d3f11612` (the corpus pin) and `lean4` at tag `v4.34.1`. That tag is the toolchain that Mathlib's `lean-toolchain` file names at the pin, and the Lean version recorded in every corpus snapshot. |
| `entries[].name` | The exact Lean constant, as it appears as a frame head. |
| `entries[].gloss` | A phrase of at most 80 characters that reads after "By". |
| `entries[].statement` | `source`, `path`, `line` and `text`: the exact source lines of the declaration, from the line given. `context` lists further exact excerpts needed to read it: the target of an alias and the `variable` lines in scope. |
| `entries[].status` | `proposed` or `reviewed`. |
| `entries[].proposed_by` | `model` or `human`. |
| `entries[].reviewed_by` | `null` for a proposal; the reviewer's name for a reviewed entry. |
| `entries[].notes` | How the statement was located, and anything a reviewer must know. |

Validation refuses unknown or missing fields, duplicate JSON keys, duplicate
entries, a reviewed entry without a reviewer, a proposed entry that names one,
glosses that are empty, longer than 80 characters, on several lines, end in a
period or colon, or contain the preview marker, project constants (`OAI.*`),
Lean-generated names (`X._simp_n`, `X._proof_n`), constants the renderer words
itself (`Subtype.property`, `cast`, `id`), source paths that are absolute or
leave the repository, and source repositories that are not https URLs. The
glossary digest is the SHA-256 of its canonical JSON.

## Rendering modes

| Mode | Applies | Citation step | Gap |
|---|---|---|---|
| `reviewed` (default) | Reviewed entries only | "By transitivity of ≤ (le_trans):" with rule `reviewed-gloss` | No, unless the frame is a budget cut |
| `preview` (opt-in) | Reviewed entries, and proposed entries with a marker | "By transitivity of ≤ (le_trans) [unreviewed gloss]:" with rule `citation` | Yes, for every proposed entry |

A gloss applies only to an `application` or `named` frame whose head is the
entry's exact name and that no earlier renderer rule has displayed (an
instance derivation, an automation certificate, a logical rule or a dictionary
lemma comes first). The cited constant stays in the step's references and the
reading's dependency list, and its name is shortened by the same notation
legend as other citations. The conclusion and premises are displayed as
before. A reviewed gloss does not expand the cited proof; it says what the
cited statement is.

The preview mode exists for reviewers. Select it with
`Narrative(record, glossary='preview')`, `proofreader narrative-read --glossary preview`
or `leanglish reading-kpis --glossary preview`. A preview reading records
`axes['glossary']` with the mode, the glossary digest and a note that its
marked glosses are unreviewed; a default reading has no such entry.

`check_reading` regenerates a reading in the mode it records. It refuses a
malformed mode record, a record that claims the default mode, and a reading
without a record that shows the unreviewed marker. A reading that presents a
gloss as reviewed when the packaged glossary has not reviewed it differs from
regeneration and is refused. A change to the glossary digest is also refused,
because `axes` is part of the reading binding.

## Selection of the proposals

The candidates are the heads of library citation gap steps (rule `citation`)
in the default rendering of the 492-snapshot corpus: 1,440 steps citing 385
constants. They were ranked by step count. The proposals cover 897 of these
steps; the remainder is:

| Excluded group | Steps | Constants | Reason |
|---|---:|---:|---|
| Logical primitives (`And.*`, `Iff.*`, `Or.*`, `Eq.*`, `Classical.*`, `Nonempty.*`, `Decidable.*`) | 76 | 17 | Logical rules belong in the renderer, not in a dictionary of lemmas; the group includes the one-step `Eq.trans_le` |
| Equational forms generated for simp (`X._simp_n`) | 52 | 7 | No declaration in source states them |
| Instance constructors, parent projections and instance declarations | 42 | 9 | Structure and typeclass plumbing, such as `Fact.mk`, `Filter.atTop_neBot` and the structure projection `Ergodic.toMeasurePreserving` |
| Constants worded by the renderer, and eliminators of empty types | 38 | 5 | `Subtype.property`, `cast`, `Fin.elim0`, `isEmptyElim`, `of_decide_eq_true` |
| Recursors (`Nat.casesAuxOn`) | 11 | 5 | Case analysis, not a lemma |
| Constants cited at most twice | 324 | 257 | Not proposed |

Each proposed constant was located in the pinned Mathlib tree, or for six
entries (`funext`, `Function.Injective.comp`, `Nat.exists_eq_add_of_le`,
`Nat.mul_le_mul_right`, `Subsingleton.elim`, `Subtype.ext`) in Lean core at
`v4.34.1`, because they are not in the Mathlib tree. The declaration lines
were copied, not retyped. `scripts/glossary_review.py verify` compares every
excerpt with the source lines: all 287 excerpts matched the pinned Mathlib
tree and the `v4.34.1` Lean sources, downloaded from raw.githubusercontent.com.

Eight entries are aliases, quoted with their target as context. For eight
more, Mathlib generates the declaration, so its statement is not written in
source:

- `le_max_left`, `le_max_right` and `LT.lt.ne'` by `@[to_dual]`;
- `add_le_add`, `add_pos'`, `add_pos_of_pos_of_nonneg` and
  `Right.add_pos_of_nonneg_of_pos` by `@[to_additive]`, the last three through
  chains of aliases;
- `inv_pos_of_pos` by `alias ⟨_, inv_pos_of_pos⟩` from an equivalence.

For these, the quoted text is the declaration that generates the constant,
and the notes state the generated statement. The `@[to_additive]` chains have more
general statements than their names suggest: `add_pos'` proves
`b < c → 0 < a → b < c + a`, and the corpus uses it with `b = 0`. Their glosses
describe the general statement. A reviewer should check these eight with
particular care.

Every gloss was compared with the quoted statement and with recorded corpus
instances of the cited frame. The model that proposed the glosses made this
comparison, so it is not a review. Glosses use the statement's own variable
names (for example "the bound b ≤ max a b"), which need not match the names in
a reading.

## Measurements

Default mode: `benchmarks/reading-kpis/current.json` and the per-reading rows
are byte-identical to the measurement before the glossary was added.

Preview mode (`docs/glossary-review/preview-kpis.json`, renderer
`source-math-en/0.5.0`, corpus `9b34751d…55ae`):

| Measure | Default | Preview |
|---|---:|---:|
| Gap steps | 5,098 | 5,098 |
| Gap frames | 8,171 | 8,171 |
| Citation gap steps | 3,508 | 3,508 |
| Steps showing an unreviewed gloss | 0 | 897 |
| Readings showing an unreviewed gloss | 0 | 135 |
| Distinct glosses shown | 0 | 85 |
| Words | 307,735 | 316,913 |
| Qualified names per 1,000 characters | 7.78 | 7.59 |

The preview changes wording only; every count of gaps is unchanged.

Projection if all 85 proposals were reviewed as written:

| Measure | Default | Projected |
|---|---:|---:|
| Gap steps | 5,098 | 4,201 |
| Gap step share | 0.3533 | 0.2911 |
| Gap frames | 8,171 | 7,274 |
| Gap frame share | 0.3639 | 0.3240 |
| Citation gap steps | 3,508 | 2,611 |
| Readings with more than half gap steps | 191 | 174 |
| Readings without gaps | 0 | 0 |

The projection is arithmetic on the preview rendering: each step that shows an
unreviewed gloss is counted as explained unless its frame is a budget cut
(none is). It was checked against a rendering in which every entry was marked
reviewed by a synthetic reviewer, held only in memory: all the projected
counts above matched, and that rendering had 315,953 words.
`tests/test_glossary.py` repeats this check on real fixture subtrees. No
reading would become free of gaps: every reading that cites these lemmas also
has other gaps.

## Review procedure

1. Read `docs/glossary-review/README.md`. For each entry, compare the gloss
   with the quoted statement, its context and the two recorded corpus
   instances. A gloss must describe what the declaration proves and claim
   nothing more; it may leave hypotheses to the premises and instance facts
   that the reading lists below the step.
2. Accept an entry with
   `python scripts/glossary_review.py mark NAME --reviewer "Full name" --confirm`,
   adding `--gloss "revised phrase"` to change the wording. Delete a rejected
   entry with `python scripts/glossary_review.py remove NAME`.
3. Regenerate `benchmarks/reading-kpis/current.json`, the preview measurement
   and the review document
   (`python scripts/glossary_review.py review CORPUS -o docs/glossary-review/README.md`)
   in the same change, because accepted entries change default readings.
4. Run `python scripts/glossary_review.py verify --source mathlib4=DIR --source lean4=DIR`
   with checkouts at the recorded revisions. It exits with status 1 when an
   excerpt differs and 3 when a source was not supplied.

## Limitations

- A gloss is editorial text. It is not formally checked against the Lean
  statement, and a reviewed gloss records a human judgement, not a proof.
- A gloss names the cited fact; it does not show the instantiation, the
  typeclass hypotheses or the proof of the cited lemma. The step's conclusion
  and premises remain the recorded Lean statements.
- Statements are quoted at one Mathlib revision and one Lean tag. A corpus
  extracted against other versions would need new excerpts.
- The `verify` check and the variable context come from a line-based reading
  of the source files. The check confirms that the quoted lines exist at the
  stated positions; it does not confirm that the context is complete or that
  every listed line is used.
- The review document's coverage counts and instances depend on the renderer
  and corpus; regenerate it when either changes.
- A reviewed-gloss step does not name its reviewer, its quoted statement or
  the glossary digest; the glossary file records them. `check_reading` refuses
  a saved default reading whose glosses differ from the packaged glossary, but
  the printer version does not change when an entry is reviewed.
- Two renderer rules that shorten citation steps do not apply to a
  reviewed-gloss step. Under a `have`, it repeats the claim that the `have`
  states, and when it proves the theorem itself it is not reworded to "The
  statement follows from …".
- No reviewer exists yet. Until one reviews entries, the glossary changes no
  default reading and explains nothing.
