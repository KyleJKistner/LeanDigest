# Reading quality in source-math-en/0.5.0

This page records what renderer version `source-math-en/0.5.0` changes in the
source-bound readings, how each new sentence is derived from snapshot data, the
measured effect on the retained corpus, and what remains unexplained. The
measurements describe the displayed readings. They are not English-fidelity,
paper-correspondence or human-comprehension results.

## Corpus and method

The corpus is the 492 retained snapshots of the `leanglish-original-project-317dc31`
release (corpus digest `9b34751d…55ae`, 22,452 checked frames). Every snapshot
is re-rendered by `leanglish reading-kpis`; `benchmarks/reading-kpis/current.json`
is the committed result and CI fails when it is stale.

`benchmarks/reading-kpis/stage_effects.py` produced the per-change table. It
disables each change at its single switch point in `proofreader/narrative.py`
and enables the changes again in table order, so every row is a cumulative
difference on the same corpus. Changes without a single switch point (listed in
the first row) cannot be disabled; that row is the difference between 0.4.2 and
0.5.0 with every switchable change disabled.

## Corpus effect

| Measure | 0.4.2 | 0.5.0 |
|---|---:|---:|
| Displayed steps | 18,275 | 14,430 |
| Gap steps | 7,635 | 5,098 |
| Gap step share | 0.4178 | 0.3533 |
| Gap frames | 7,635 | 8,171 |
| Gap frame share | 0.3401 | 0.3639 |
| Citation gap steps (by rule) | not tagged | 3,508 |
| Project citation gap steps (OAI.*) | not tagged | 2,068 |
| Frames classified as typeclass side conditions | not classified | 2,791 |
| Frames owned by an automation step | — | 1,723 |
| Steps reading "Apply X to the supplied arguments." (wording) | 7,616 | 37 |
| Readings with more than half gap steps | 225 | 191 |
| Readings without gaps | 0 | 0 |
| Words | 393,664 | 311,107 |
| Qualified names per 1,000 characters | 15.48 | 15.19 |
| `fun`, `=>`, `↑` per 1,000 characters | 3.91 | 4.48 |

The gap frame share **rose**. Grouping and collapsing moved frames that 0.4.2
displayed as separate, non-gap lines (numeral reflexivity checks inside norm_num
certificates, binders over instance families, instance hypotheses under a
library instance) into steps that are explanation gaps. Fewer unexplained lines
are shown, but more of the checked proof sits inside an unexplained step. The
Lean-marker density also rose: the formulas are unchanged while the surrounding
text is shorter.

## Per-change effect

Cumulative, in table order. Δ is the change from the row above (the first row
is compared with 0.4.2).

| Change | Δ displayed steps | Δ gap steps | Δ gap frames | Citation gap steps | Instance frames | Δ words |
|---|---:|---:|---:|---:|---:|---:|
| Changes without a switch point: Nonempty elimination, unfolded projections, substitution, restatement, named-goal witness, anonymous `have`, `Subtype.property`, `ring` wording | −28 | −28 | −28 | — | — | +8,639 |
| 1. Typeclass side conditions grouped | −1,888 | −1,588 | +166 | — | 2,791 | −16,371 |
| 2. norm_num, positivity and linarith certificates collapsed | −1,319 | −879 | +440 | — | 2,791 | −9,807 |
| 3. Rewrite frontiers described by their head | 0 | 0 | 0 | — | 2,791 | +4,081 |
| 4. Citations reworded and tagged | 0 | 0 | 0 | 3,550 | 2,791 | −6,957 |
| 5. `cast` along a recorded equation explained | 0 | −42 | −42 | 3,508 | 2,791 | +570 |
| 6. A claim stated by `have` or `choose` is not repeated under its sole unexplained proof | 0 | 0 | 0 | 3,508 | 2,791 | −13,730 |
| 7. A destructured hypothesis is named, and nested destructuring is one step | −610 | 0 | 0 | 3,508 | 2,791 | −48,982 |

Changes 3 and 4 only reword or tag steps; they do not explain anything, and the
gap counts show that. Change 4 is why `opaque_apply_steps` fell from 7,616 to
37: that measure is kept only as a wording measure. `citation_gap_steps` counts
the rule tag, so rewording a citation cannot change it (see
`tests/test_reader_quality.py::test_citation_count_does_not_depend_on_wording`).

## Derivation of each phrasing

Every sentence uses only the frame's head, statement, objects, premises,
binder, domain and context. "Gap" means the step keeps `fallback=True` and is
shown as an explanation gap. Every exported frame is still owned by exactly one
displayed step, and `check_reading` still regenerates the reading.

| Rule | Recognized from | Sentence | Gap |
|---|---|---|---|
| `instance-facts` | A frame that is a typeclass side condition (below), grouped per parent after the mathematical premises | "Standard instance fact(s) used: S₁; S₂." listing the root statements; the detail lists every absorbed frame and head. Non-instance premises of an instance derivation stay visible as children. | Yes |
| `instance-assumptions` | A hypothesis whose binder is Lean's automatic instance name (`inst`, `inst_2`, `inst✝¹`) and whose statement is a plain proposition | "Instance assumption(s) used: S." | No |
| `automation` | An application whose head is in `Mathlib.Meta.NormNum.`, `Mathlib.Meta.Positivity.` or `Mathlib.Tactic.Linarith.` | "Numerical evaluation (norm_num) verifies this", "Sign analysis (positivity) proves this", "Linear arithmetic (linarith) proves this" or, for a conclusion False, "derives a contradiction"; each ends "the computation/certificate is not expanded" | Yes |
| `rewrite` | A frontier rewrite without a polynomial certificate | `Eq.mpr`: rewrite the goal to an equal proposition and prove that; `Eq.mp`: obtain this by rewriting another proposition; `of_eq_true`: simplification reduces this to True; `congrArg`, `congrFun`, `congrFun'`, `congr`: congruence from equations that are not expanded | Yes |
| `citation`, `project-citation` | Any other application or constant with a head; `project-citation` when the head is in `OAI.` | "By X:" or "By the project lemma X:" (or "project instance" for an `instX` name), with the conclusion and premises below. `X._simp_n` reads "By X (in the equational form generated for simp):"; `X._proof_n` reads "By an auxiliary proof that Lean extracted while elaborating X:". `Subtype.property` names the element. | Yes |
| `transport` | `cast` with exactly two objects α, β and premises at argument slots 2 and 3, where the premises print as `α = β` (one outer `=`) and α, and the conclusion prints as β | "From α, obtain β by rewriting with the equation of propositions below." | No |
| `choose-element` | `Nonempty.casesOn` with exact argument paths, a premise printed `Nonempty α`, a binder over α and a body proving the same printed statement (constant motive) | "Since Nonempty α, choose a ∈ α." | No |
| `unpack-conjunction` (named) | An existing exact `And.casesOn` destructuring whose major premise is a hypothesis printed as the two displayed parts joined by ∧ with the right precedence | "From h, obtain a: A and b: B." A part destructured again in the same way, and used nowhere else, is replaced by its own parts: "From h, obtain a: A, c: C and d: D." | No |
| `unchecked-projection` | `And.left`/`And.right` with exact argument paths whose conclusion is the recorded component, but whose premise is printed differently (for example `s ∈ Set.Ioc 0 1`) | "Take the first conjunct, P, of the premise below; its second conjunct is Q. That the premise has this form is not checked here." | Yes |
| `substitution` | `Eq.ndrec` or `Eq.rec` with proof arguments at slots 3 and 5 | "Rewrite the statement proved below along the equation a = b; which occurrences are rewritten is not displayed." | Yes |
| `restatement` | `id` with one type argument and one proof printed differently | "Restate this in the definitionally equal form proved below; the unfolding is not expanded." | Yes |
| `witness` (named goal) | `Exists.intro` with three objects whose goal is printed as a definition rather than `∃` | "Provide the witness w; the property it must satisfy is proved below. That the goal unfolds to an existential statement is not checked here." | Yes |
| `have` (anonymous) | A `have` whose binder is `this` or `this_n` | "Establish S." without "call this fact this"; a later use of that hypothesis reads "Use the fact S established above." only when the nearest enclosing binder of that name is that `have` | No |

A frame is a **typeclass side condition** when it is not a budget cut, not
certified, not a dictionary lemma and its head is not in `OAI.`, and one of the
following holds:

- its head's last component is `instX` (an uppercase letter after `inst`) or the
  head is `inferInstance`/`inferInstanceAs`, and its statement is a plain
  proposition (no outer relation, connective, binder or keyword);
- its head is a parent projection `X.toC` and its statement is `C a₁ … aₙ`, and
  every premise is itself a side condition;
- its statement is `C a₁ … aₙ` for a class `C` in the reviewed list
  `_INSTANCE_CLASSES`, its head is not a constructor (`mk`, `intro`), and every
  premise is itself a side condition;
- it binds an instance family, `∀ i, C (β i)`, whose body is a side condition;
- it is an instance hypothesis as described for `instance-assumptions`.

The premise requirement keeps theorems such as `Ergodic.toMeasurePreserving h`
visible. Named hypotheses such as `hPM : Nonempty G.Matching`, and project
lemmas such as `OAI.UniformSparsestCut.SourceUniform.instance_exists`, are not
side conditions. These real cases are fixtures in the tests.

An automation step absorbs only the root, frames whose head belongs to one of
the three families, reflexivity frames, `Nat.cast_zero`/`Nat.cast_one` directly
under a norm_num frame, typeclass side conditions and, for linarith, its frontier
rewrites. Hypotheses, project lemmas, library lemmas and certified frames stay
visible as children. Polynomial certificates for `ring` and `rewrite` frames are
unchanged; the Bézout reading is reproduced exactly.

## What remains a gap

| Rule | Gap steps | Meaning |
|---|---:|---|
| `project-citation` | 2,068 | A project lemma cited without its own proof in this reading |
| `citation` | 1,440 | A library or other non-project constant cited without proof |
| `instance-facts` | 522 | Library typeclass instances (2,132 frames) |
| `rewrite` | 346 | Rewrites and simplifications whose equations are not exported |
| `automation` | 260 | norm_num, positivity and linarith certificates (1,723 frames) |
| `unchecked-projection` | 224 | A conjunct of a premise printed in unfolded form |
| `restatement` | 124 | Definitional restatements |
| `substitution` | 56 | `Eq.ndrec`/`Eq.rec` substitutions |
| `witness` | 35 | Witnesses for goals printed as definitions, and proof witnesses |
| `choose` | 12 | `Exists.casesOn` whose bound variable is a proof |
| `application` | 7 | Applications without a recorded head |
| `ring` | 4 | `ring` normalizations without a polynomial certificate |

No reading is free of gaps. Citations are 69% of the remaining gap steps: they
become explained only when the cited lemma gets its own reading or a reviewed
dictionary sentence.

## Compatibility and trust boundary

- `check_reading` still requires byte-identical regeneration of the reading
  binding. The one exception: a saved reading labelled `source-math-en/0.4.2`
  (the only entry in `EARLIER_PRINTERS`) is accepted when regeneration is
  identical except for that label. The retained native Bézout companion reading
  depends on this; 0.5.0 reproduces its text exactly.
- Frames absorbed into a grouped step add their heads to the reading's
  dependency list. Earlier versions listed only the first frame's head of a
  multi-frame step.
- Instance and automation recognition uses Lean and Mathlib naming conventions
  and a reviewed class list, not Lean's typeclass database. A misclassified
  frame stays owned and visible in the step detail, and every absorbed library
  instance is counted as a gap frame.
- `proofreader/data/narrative-demo.json` and `reader-demo.json` still carry the
  0.4.2 label: their text is unchanged, and rebuilding them would also rewrite
  retained artifacts.

## Tests

`tests/test_reader_quality.py` covers each rule. Its real fixtures in
`tests/fixtures/reader_quality.json` are subtrees of corpus snapshots, rebuilt
by `tests/fixtures/extract_reader_quality.py`, which records each source
snapshot and original frame ids and refuses a subtree that renders differently
from the full snapshot. Tests that build records by hand say so; they are
format fixtures, not Lean observations.
