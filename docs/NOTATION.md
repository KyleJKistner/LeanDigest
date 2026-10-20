# Display notation

`proofreader/notation.py` changes how formula strings are shown in a source-bound
reading. It does not change what is recorded or checked. Lean's pretty-printer
output stays authoritative:

- every displayed step keeps its raw formula in `Step.source`, shown in the
  reader's step inspector as **Exact step source**;
- the snapshot keeps every raw frame;
- `_same_formula`, the logical-rule recognizers and the polynomial checker read
  raw strings only. Nothing in this module feeds back into a check.

The displayed text is part of the regenerated reading binding, so
`check_reading()` recomputes it, including the notation, from the snapshot.
The notation is a deterministic function of the snapshot and the code. It is a
display convention, not a translation with a correctness proof.

## Where it runs

| Hook | Location | Effect |
|---|---|---|
| `math_text()` | `narrative.py` | Applies `notation.display()` to the result of the existing gcd/`·`/`≠` dictionary (`_math_dictionary`). |
| `@notation.reading` | `Narrative.document()` | Builds one display context from the whole snapshot, then attaches the legend to the declaration's axes and appends it to its warnings. |
| `notation.legend()` | `prose()` | Prints the legend between the trust notice and the statement. |
| `notation.name(full)` | not yet called | Shortens one cited Lean name, for example a lemma in a step sentence, under the same collision rules, and records it for the legend. |

Outside a reading context, `display()` and `name()` are the identity, so
`math_text()` called on its own behaves as before.

The legend is stored in `Declaration.axes['notation']`:

```json
{"omitted_namespaces": ["OAI.TotientAsymptotic", "Filter", "Set"],
 "symbols": [["x ↦ e", "fun x => e"], ["log", "Real.log"]]}
```

It lists only namespaces and notations whose display forms occur in the
reading's displayed text (parameters, statement, step texts and conclusions).
The key is omitted when nothing applies, so the Bézout reading is byte-identical
to its previous output. `prose()` prints, for example:

```text
Notation (display only; the recorded Lean formulas are unchanged):
- Namespace prefixes not written: OAI.TotientAsymptotic, Filter, Set.
- log stands for Real.log.
- x ↦ e stands for fun x => e.
```

The same legend, as one paragraph, is the declaration's last warning. The HTML
reader lists warnings in its audit panel and the Markdown view prints them, so
every view that shows shortened names also shows the legend. `app.js` does not
yet read `axes['notation']` or show the legend beside the statement. Warnings
are outside the reading binding; `check_reading()` compares the bound copy in
`axes['notation']`. The per-step **Exact step source** keeps the full names.

## Corpus profile

The profile covers every formula string of the 492 retained snapshots: frame
statements (22,452), objects (29,174), binder domains (6,892), definition values
(210) and local-context types (374,794). **Occurrences** counts a string as often
as frames repeat it, which mostly reflects local contexts repeated in every
frame. **Distinct strings** counts each distinct string once per reading and is
the ranking key. **Readings** is the number of snapshots containing the name.
The tables use the qualified-name pattern of `reading_kpis.py` (an uppercase
first component followed by a dot), which also matches projections of local
binders such as `P.fst`. There are 3,959 distinct qualified names.

Reproduce with:

```sh
python -m proofreader.notation CORPUS --json profile.json
```

### Top 50 qualified constants

| # | Constant | Occurrences | Distinct strings | Readings |
|---:|---|---:|---:|---:|
| 1 | `OAI.CKSLorentz.bondiCharge` | 89,443 | 2,558 | 1 |
| 2 | `Real.log` | 23,405 | 2,481 | 51 |
| 3 | `Filter.atTop` | 27,388 | 2,134 | 66 |
| 4 | `OAI.CKSGeometricCuts.I3` | 32,335 | 1,748 | 1 |
| 5 | `Filter.Tendsto` | 18,404 | 1,473 | 54 |
| 6 | `ENNReal.ofReal` | 20,516 | 1,296 | 30 |
| 7 | `MeasureTheory.Measure.map` | 14,578 | 1,130 | 11 |
| 8 | `OAI.CurrentProjection.swapLast` | 9,453 | 915 | 8 |
| 9 | `OAI.CKSLorentz.hyperbolicHomeomorph` | 39,853 | 910 | 1 |
| 10 | `Real.exp` | 6,215 | 802 | 27 |
| 11 | `OAI.CKSFullCutArea.area` | 14,182 | 700 | 1 |
| 12 | `OAI.CurrentProjection.gaussianRows` | 8,130 | 649 | 9 |
| 13 | `Fintype.card` | 5,326 | 642 | 22 |
| 14 | `OAI.Solenoidal.scheduleVelocity` | 15,473 | 642 | 1 |
| 15 | `OAI.StandardMapEntropy.area` | 10,452 | 633 | 3 |
| 16 | `OAI.CurrentProjection.label` | 2,517 | 601 | 1 |
| 17 | `Bundle.ContMDiffRiemannianMetric.toContinuousRiemannianMetric` | 16,416 | 561 | 1 |
| 18 | `OAI.Release061.Hermitian.hermQuadratic` | 22,149 | 558 | 1 |
| 19 | `OAI.CurrentProjection.shannonEntropy` | 15,614 | 527 | 9 |
| 20 | `OAI.Release061.quadraticDomain` | 20,290 | 513 | 1 |
| 21 | `OAI.CKSLorentz.E` | 17,092 | 509 | 1 |
| 22 | `Set.univ` | 4,415 | 482 | 16 |
| 23 | `MeasureTheory.Measure` | 6,697 | 481 | 38 |
| 24 | `MeasureTheory.volume` | 3,176 | 479 | 19 |
| 25 | `OAI.CurrentProjection.Rows` | 4,307 | 468 | 11 |
| 26 | `OAI.CKSFullCutArea.minEnclosingArea` | 7,321 | 427 | 1 |
| 27 | `OAI.CKSSpatialManifold.endInner` | 6,986 | 422 | 1 |
| 28 | `MeasureTheory.IsProbabilityMeasure` | 5,168 | 417 | 37 |
| 29 | `OAI.AlternatingNS.Space` | 3,997 | 412 | 1 |
| 30 | `P.fst` | 14,962 | 406 | 7 |
| 31 | `OAI.CurrentProjection.Sphere` | 6,134 | 399 | 11 |
| 32 | `OAI.FiniteEntropySeparation.chosenP` | 4,063 | 387 | 1 |
| 33 | `Set.Icc` | 5,096 | 379 | 19 |
| 34 | `OAI.TraceReconstruction.sourceDepth` | 7,975 | 371 | 2 |
| 35 | `OAI.CurrentProjection.PositiveMessage` | 3,555 | 370 | 2 |
| 36 | `OAI.CurrentProjection.exactDensity` | 1,405 | 367 | 2 |
| 37 | `OAI.AlternatingNS.Construction.velocity` | 6,251 | 362 | 1 |
| 38 | `OAI.CurrentProjection.completeFamily` | 2,820 | 337 | 2 |
| 39 | `Function.Injective` | 4,118 | 327 | 20 |
| 40 | `OAI.CKSBending.paddingCharge` | 10,207 | 318 | 1 |
| 41 | `OAI.CurrentProjection.exposedInformation` | 5,875 | 317 | 4 |
| 42 | `OAI.StandardMapEntropy.standardMap` | 4,963 | 317 | 3 |
| 43 | `OAI.Release061.Affine` | 12,214 | 296 | 1 |
| 44 | `Set.range` | 5,079 | 293 | 15 |
| 45 | `OAI.Solenoidal.globalDirectForce` | 6,090 | 279 | 1 |
| 46 | `Equiv.Perm` | 3,599 | 272 | 8 |
| 47 | `MeasureTheory.Integrable` | 2,767 | 263 | 10 |
| 48 | `MeasureTheory.IntegrableOn` | 6,914 | 256 | 3 |
| 49 | `OAI.CKSSourceExterior.minimumEnclosingArea` | 440 | 254 | 2 |
| 50 | `OAI.InfiniteMatroidCounterexample.rayMatroid` | 1,148 | 254 | 2 |

### Syntax forms

| Syntax form | Occurrences | Distinct strings |
|---|---:|---:|
| ∀ binder | 222,702 | 20,012 |
| ↑ coercion arrow | 193,638 | 18,872 |
| ∃ binder | 68,482 | 7,298 |
| fun x => e | 45,141 | 5,974 |
| ‖x‖ norm | 107,748 | 5,590 |
| [inst : C] instance binder | 10,885 | 2,655 |
| absolute value bars | 33,948 | 2,491 |
| Filter.Tendsto | 18,404 | 1,473 |
| nhds a | 15,268 | 1,310 |
| √ square root | 15,857 | 1,075 |
| ⋯ elided proof | 9,783 | 1,000 |
| ∑ or ∏ big operator | 5,975 | 610 |
| ∫ integral | 7,905 | 578 |
| ⁻¹ inverse | 7,822 | 403 |
| if … then … else | 3,756 | 302 |
| ∀ᶠ or ∃ᶠ eventually | 4,994 | 274 |
| π | 718 | 246 |
| s.card field notation | 700 | 78 |
| Real.pi | 1,377 | 74 |
| nhdsWithin a s | 49 | 37 |
| Nat.choose | 44 | 5 |
| Finset.card | 5 | 3 |
| Real.sqrt | 0 | 0 |
| string literal | 0 | 0 |
| «guillemet name» | 0 | 0 |

### Namespace of each qualified occurrence

| Qualified name in distinct strings | Count |
|---|---:|
| theorem namespace | 62,692 |
| enclosing or other OAI namespace | 16,624 |
| other library namespace | 14,693 |
| opened library namespace (Filter, MeasureTheory, Set) | 8,909 |
| projection of a local binder | 8,703 |

Names in the theorem's own namespace account for 56% of qualified occurrences,
and names elsewhere in the project for another 15%. Opening a few library
namespaces reaches 8%. Local-binder projections (8%) cannot be shortened.

## Namespace shortening

A name is shown relative to the first applicable namespace in this order:

1. The theorem's namespace and then each enclosing namespace, down to the
   project root. For `OAI.CKSSourceExterior.area_controlled_end_replacement`,
   `OAI.CKSSourceExterior.minimumEnclosingArea` is shown as
   `minimumEnclosingArea` and `OAI.CKSLorentz.bondiCharge` as
   `CKSLorentz.bondiCharge`. This is Lean's own resolution of a name written
   inside `namespace OAI.CKSSourceExterior`, where the current namespace and its
   ancestors are searched before the root.
2. Three library namespaces: `Filter`, `MeasureTheory` and `Set`.

The library set comes from the `open` commands in the 413 original OAI solution
files (`originals/OAI/**/*.lean` in the release archive). Files with an `open`
command naming each namespace:

| Namespace | Files | Decision |
|---|---:|---|
| Filter | 119 | Opened. |
| Topology | 112 | No constants of its own; supports the `𝓝` notation below. |
| MeasureTheory | 106 | Opened. |
| BigOperators | 104 | Notation only; Lean already prints `∑` and `∏`. |
| Set | 92 | Opened, except reserved names such as `Set.Finite`. |
| ENNReal | 74 | Not opened. Its only displayed constant is `ENNReal.ofReal`, whose prefix states the target number system. |
| Classical | 53 | Not opened. The prefix of `Classical.choose` records the use of choice. |
| NNReal | 43 | No displayed constants. |
| ProbabilityTheory | 26 | Not opened (fewer than 30 files). |
| Metric | 23 | Not opened (fewer than 30 files). |
| Finset | 20 | Not opened; `Finset.range` and `Set.range` differ. |
| Real | 8 | Not opened. Only the textbook functions in the next table lose the prefix. |
| Function | 7 | Not opened (fewer than 30 files). |

Some names receive a fixed symbol instead:

| Lean | Shown | Note |
|---|---|---|
| `Real.log`, `Real.exp` | `log`, `exp` | Also `sin`, `cos`, `tan`, `arctan`, `sinh`, `cosh`, `tanh`, `artanh`. `Real.log` keeps Mathlib's conventions, including `log 0 = 0`; the legend names the constant. |
| `Real.pi` | `π` | Mathlib's notation. |
| `nhds` | `𝓝` | Mathlib's `Topology` notation. |

### Collision rules

The display context collects every name in the snapshot: statements, objects,
domains, values, context types, cited heads, binder names and context names.
It also reads each string as the narrative dictionary rewrites it, so a
shortened name cannot look like a word that the dictionary introduces, such as
`gcd` in `gcd(a, b)`. It is built before any step is rendered, so a
shortening is decided once for the whole reading. A shortening is refused, and
the name falls back to the next longer form (finally the full name), when any
of these holds:

- Two distinct full names would be shown as the same text in that reading.
- A dotted prefix of the shown text would denote something else. For example,
  `Real.log` is not shown as `log` when `OAI.….log.foo` would be shown as
  `log.foo`, and `OAI.X.G.size` is not shown as `G.size` when `G` is a local
  binder.
- The shown text, or its first component, equals a local binder, hypothesis or
  bound variable name in that reading.
- The shown text starts with a Lean keyword or a reserved root name (`RESERVED`
  in the module): root classes such as `Finite`, `Countable` and `Nonempty`,
  which a reader would take to be the library's own, major library namespaces
  such as `Real` or `Set`, and root names that project constants of the corpus
  repeat, such as `IsClosed`, `Field` and `Lattice`. The list is maintained by
  hand and is not complete.

Field names after `(…).` are not free names and do not block a shortening; the
`b` in `a..b` does. The decision does not depend on iteration order, and the
cross-process test runs it under several hash seeds.

Across the corpus, 6,177 qualified names could be shortened. Of these, 6,154 use
the first choice, 17 fall back to a longer form, and 6 keep the full name. Two
fallbacks are collisions: `OAI.AbhyankarSathaye.F` with the bound variable of
`∃ F`, and `OAI.CoordinateSweeps.a` with a local binder `a`. The other 15 start
with a reserved name and keep one more namespace component, for example
`TamingCompatibility.IsClosed` and `Routing.Field`. They are `Algebra`,
`Classical`, `Dense` (two names), `Field` (two), `IsClosed`, `Language` (two),
`Lattice`, `Multiplicative`, `Small` (two), `gradient` and `spectrum`. The six
refusals are `Set.Finite` and names under `Set.Finite`, `Set.Infinite` and
`Set.Nonempty`.

### Strings left unchanged

The tokenizer models identifiers (approximately Lean's lexer), numbers, string
and character literals, the bracket pairs `() [] {} ⟨⟩ ⦃⦄ ⟦⟧`, and a few
multi-character operators (`=>`, `:=`, `..`, `''`, `∑'`, `∏'`). A string with a
stray quote, a backtick, a guillemet name (`«…»`), comment syntax or unbalanced
brackets is displayed unchanged, including its names. A closed string literal
is one opaque token: names inside it are never shortened. The corpus has no
string literals or guillemet names, and all 11,312 distinct strings that the
corpus readings pass to `math_text()` are recognized by the tokenizer.

## Structural notation

Each rule needs the form at an application boundary: the head is not itself an
argument or a field, the arguments are atoms (a name, a number, a literal or a
bracketed group, optionally after `↑`), and no further argument follows. A
lambda body or binder body must have a known extent. Commas, `then`/`else` and
`in` are matched against pending binders, lambdas and `if`, and `let`, `have`,
`show`, `match`, `by`, `;` or `:=` stop the rule. When a rule does not match,
the text is printed as before, apart from name shortening.

| Lean | Shown | Conditions | Readings |
|---|---|---|---:|
| `fun x => e` | `x ↦ e` | One plain binder; parenthesized unless it fills its bracket group or the whole formula; not used if the reading already contains `↦`. | 125 |
| `Filter.Tendsto (fun x => e) Filter.atTop (nhds a)` | `e → a as x → ∞` | The lambda rule's binder conditions; the source filter is exactly `Filter.atTop`; the target is `nhds a` with an atomic `a`, `Filter.atTop` (`∞`) or `Filter.atBot` (`−∞`). `a` does not mention `x`, which `as x → ∞` would bind. `e` is parenthesized unless it uses only arithmetic operators; the whole form is parenthesized when it is an operand. Not used if `as` is a name in the reading or `∞` occurs in it. | 36 |
| `nhdsWithin a s` | `𝓝[s] a` | Mathlib's notation; only when `nhds` is shown as `𝓝` in that reading. | 1 |
| `Finset.card s` | `#s` | Mathlib's notation; not used if `#` already occurs. | 1 |
| `Real.sqrt x` | `√x` | Mathlib's notation. Lean already prints `√` in the corpus, so this never fires there. | 0 |
| `Nat.choose n k` | `(n choose k)` | Two atomic arguments; not used if `choose` is a name in the reading. Not parenthesized twice when it fills a parenthesized group, as in `↑(20 choose 10)`. | 1 |

`x → ∞` follows Mathlib's reading of `Filter.atTop`: for every `b`, eventually
`x ≥ b` in the order on the type of `x`. On `ℕ` and `ℝ` this is the usual
limit. On `Finset ℕ` it means "eventually containing every finite set", which
is not a real-valued limit. Formula strings do not record the binder's type,
so the rule cannot check it; the legend entry states the general meaning and
the exact Lean form. The rule fires on 101 distinct lambdas in 36 corpus
readings. They were inspected by hand: where the body (for example a cast `↑n`)
or the original source shows the binder's type, it is `ℕ` or `ℝ`. That
inspection is not an automated or recorded check.

The rule is not used when `∞` occurs in the reading. In `ENNReal`, `∞` is the
top element, so `Filter.atTop` is the principal filter of `{∞}`, while `𝓝 ∞` is
the neighborhood filter of `∞`; both limits would display as `→ ∞`. A limit `nhds a` whose
`a` mentions the bound variable is also left as printed: in
`Filter.Tendsto (fun n => f n) Filter.atTop (nhds n)` the limit's `n` is not
the lambda's `n`.

### Forms left as printed

- `↑` coercion arrows (9,643 of the remaining 10,125 Lean markers in displayed
  text). Removing them changes meaning: `↑(n / 2)` is natural-number division
  followed by a cast, and `↑n / 2` is real division.
- Lambdas with several binders, typed binders or patterns, such as
  `fun x x_1 => 0`. Rewriting `fun x y => e` as `(x, y) ↦ e` would change a
  curried function into one on pairs.
- `Filter.Tendsto f l₁ l₂` with a function that is not a lambda, or with other
  filters. The form `e → a as x → ∞` needs a bound variable, and inventing one
  would add a name the snapshot does not record. These print as
  `Tendsto f atTop (𝓝 a)`.
- `Fintype.card V`. Mathlib has no notation for it. `|V|` would reuse the
  absolute-value bars that Lean prints, and `#V` is Mathlib's notation for the
  cardinal `Cardinal.mk V`.
- `ENNReal.ofReal x`, instance names and tactic internals in object lists
  (for example `Mathlib.Meta.NormNum.IsNat`). These belong to the step
  templates, not to notation.
- Absolute values and norms, which Lean already prints as notation.

## Measurements

Measured with `python -m proofreader.reading_kpis CORPUS` over the 492 retained
snapshots, before and after this change. The renderer version string was not
changed; both columns therefore read `source-math-en/0.4.2`.

| Measure | Before | After |
|---|---:|---:|
| display_steps | 18,275 | 18,275 |
| gap_steps | 7,635 | 7,635 |
| gap_frame_share | 0.3401 | 0.3401 |
| opaque_apply_steps | 7,616 | 7,616 |
| words | 393,664 | 391,827 |
| characters | 3,557,369 | 2,917,425 |
| qualified names | 55,067 | 28,081 |
| qualified_names_per_1000_characters | 15.48 | 9.63 |
| Lean markers (`fun`, `=>`, `↑`) | 13,925 | 10,125 |
| lean_markers_per_1000_characters | 3.91 | 3.47 |

Notation changes no step, gap or ownership count. Most of the reduction comes
from omitting prefixes: a shortened name has the same meaning, and the reader
needs the legend to recover the prefix. The counts fall by 49% (qualified
names) and 27% (Lean markers). The per-1000-character rates fall less, because
the displayed text is also 18% shorter. The 28,081 qualified names that remain
in displayed text are:

| Remaining qualified names | Count |
|---|---:|
| Shortened but still dotted, such as `CKSLorentz.bondiCharge` or `Measure.map` | 12,551 |
| Cited names in `Apply … to the supplied arguments.` | 6,471 |
| Names in namespaces that are not opened, such as `ENNReal.ofReal`, `Fintype.card` and `Real.instIsOrderedRing` | 4,986 |
| Fields or projections of local binders, such as `P.fst` | 4,055 |
| Full project names in other step sentences | 18 |

The cited names are written by the step templates in `Narrative.sequence()`,
which this layer does not edit. `notation.name()` is available for them. The
legend lines in `prose()` are not part of the measured text.

## Limitations

- The tokenizer approximates Lean's lexer and grammar. A rule that misjudges
  an extent would misplace parentheses in the display, but not in the proof.
  The tests cover nested, partial and ambiguous forms, operators inside lambda
  bodies, string literals and idempotence.
- A shortened single-letter constant, such as `E` for `OAI.CKSLorentz.E`, can
  look like a variable. The collision rules guarantee only that no variable or
  other name in the same reading is displayed with the same text.
- A shortened project name can still coincide with a library root name that
  the reading does not contain and that `RESERVED` does not list.
- `x → ∞` is shown for `Filter.atTop` on every binder type, because formula
  strings do not record that type. The legend states the general meaning.
- The legend includes an entry when a recorded display form, or a shortened
  name as a whole word, occurs in the displayed text. A shortened name that is
  also an ordinary word of the text can add an entry that is not needed. An
  entry can be missed only if a template displays part of a structural
  notation form; the current templates do not.
- Display text is not English fidelity. No reader study has measured whether
  this notation helps comprehension.
