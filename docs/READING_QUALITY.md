# Reading quality of source-bound readings

This page records what renderer versions `source-math-en/0.5.0` and
`source-math-en/0.6.0` change in the source-bound readings, how each new
sentence is derived from snapshot data, the measured effect on the retained
corpus, and what remains unexplained. The measurements describe the displayed
readings. They are not English-fidelity, paper-correspondence or
human-comprehension results.

## Corpus and method

The corpus is the 492 retained snapshots of the `leanglish-original-project-317dc31`
release (corpus digest `9b34751d…55ae`, 22,452 checked frames). Every snapshot
is re-rendered by `leanglish reading-kpis`; `benchmarks/reading-kpis/current.json`
is the committed result and CI fails when it is stale.

`benchmarks/reading-kpis/stage_effects.py` produced the per-change table. It
disables each change at its single switch point in `proofreader/narrative.py`
or `proofreader/narrative_rules.py` and enables the changes again in table
order, so every row is a cumulative difference on the same corpus. Changes
without a single switch point (listed in the first row) cannot be disabled;
that row is the difference between 0.4.2 and the current renderer with every
switchable change disabled.

## Corpus effect

| Measure | 0.4.2 | 0.5.0 | 0.6.0 |
|---|---:|---:|---:|
| Displayed steps | 18,275 | 14,430 | 13,088 |
| Gap steps | 7,635 | 5,098 | 4,961 |
| Gap step share | 0.4178 | 0.3533 | 0.3790 |
| Gap frames | 7,635 | 8,171 | 8,034 |
| Gap frame share | 0.3401 | 0.3639 | 0.3578 |
| Citation gap steps (by rule) | not tagged | 3,508 | 3,488 |
| Project citation gap steps (OAI.*) | not tagged | 2,068 | 2,068 |
| Frames classified as typeclass side conditions | not classified | 2,791 | 2,791 |
| Frames owned by an automation step | — | 1,723 | 1,723 |
| Hypothesis frames shown in a grouped line | — | — | 1,967 (667 lines) |
| Steps reading "Apply X to the supplied arguments." (wording) | 7,616 | 37 | 7 |
| Readings with more than half gap steps | 225 | 191 | 193 |
| Readings without gaps | 0 | 0 | 0 |
| Words | 393,664 | 307,735 | 301,158 |
| Qualified names per 1,000 characters | 15.48 | 7.78 | 7.87 |
| `fun`, `=>`, `↑` per 1,000 characters | 3.91 | 4.22 | 4.28 |

The 0.5.0 column is the committed `current.json` before 0.6.0, which includes
the notation layer described in `docs/NOTATION.md`. Before that layer was
integrated, the same version measured 311,412 words, 15.19 qualified names and
4.48 Lean markers per 1,000 characters; the step and gap counts are the same.

In 0.5.0 the gap frame share **rose**. Grouping and collapsing moved 606 frames
that 0.4.2 displayed as separate, non-gap lines into steps that are explanation
gaps: 440 numeral reflexivity checks inside norm_num (269) and positivity (171)
certificates, 122 binders over instance families, and 44 instance hypotheses
under a library instance derivation. In the other direction, 70 frames became
explained (42 `cast`, 28 `Nonempty.casesOn`); the net is +536 gap frames.
Fewer unexplained lines are shown, but more of the checked proof sits inside an
unexplained step. The Lean-marker density also rose: the formulas are unchanged
while the surrounding text is shorter.

In 0.6.0 the gap frame share fell from 0.3639 to 0.3578: 137 frames that 0.5.0
displayed inside gap steps are explained. They are 97 conjunct projections, 18
proof witnesses, 12 existential eliminations over a proposition, 7 reverse
directions of an equivalence, 2 nonempty types with a local element and 1
conjunct applied to a premise. The gap step share **rose** from 0.3533 to
0.3790, and two more readings have more than half gap steps, because the
denominator fell: 1,967 hypothesis frames that 0.5.0 showed as 1,967 non-gap
lines are now 667 lines. That is a change of presentation, not of explanation,
and it changes no gap count (row 8 below). The citation count fell by 20: 10
citations are explained and 10 oversaturated projections are relabelled
`unchecked-application`, which is still a gap.

## Per-change effect

Cumulative, in table order. Δ is the change from the row above (the first row
is compared with 0.4.2). Rows 1–7 are 0.5.0 and rows 8–15 are 0.6.0. The word
column of rows 1–7 now includes the notation layer, so it differs from the
values first recorded for 0.5.0; the other columns are unchanged.

| Change | Δ displayed steps | Δ gap steps | Δ gap frames | Citation gap steps | Instance frames | Δ words |
|---|---:|---:|---:|---:|---:|---:|
| Changes without a switch point: Nonempty elimination, unfolded projections, substitution, restatement, named-goal witness, anonymous `have`, `Subtype.property`, `ring` wording; in 0.6.0, the wording of `Nonempty.intro` with a constructed element | −28 | −28 | −28 | — | — | +7,097 |
| 1. Typeclass side conditions grouped | −1,888 | −1,588 | +166 | — | 2,791 | −16,106 |
| 2. norm_num, positivity and linarith certificates collapsed | −1,319 | −879 | +440 | — | 2,791 | −9,807 |
| 3. Rewrite frontiers described by their head | 0 | 0 | 0 | — | 2,791 | +4,081 |
| 4. Citations reworded and tagged | 0 | 0 | 0 | 3,550 | 2,791 | −9,128 |
| 5. `cast` along a recorded equation explained | 0 | −42 | −42 | 3,508 | 2,791 | +570 |
| 6. A claim stated by `have` or `choose` is not repeated under its sole unexplained proof | 0 | 0 | 0 | 3,508 | 2,791 | −13,647 |
| 7. A destructured hypothesis is named, and nested destructuring is one step | −610 | 0 | 0 | 3,508 | 2,791 | −48,728 |
| 8. Adjacent hypotheses are one line | −1,300 | 0 | 0 | 3,508 | 2,791 | −3,900 |
| 9. A conjunction premise is read with Lean's precedence, binder conjuncts included | 0 | −97 | −97 | 3,508 | 2,791 | −3,354 |
| 10. An equivalence premise is read with Lean's precedence | 0 | −7 | −7 | 3,501 | 2,791 | +500 |
| 11. An existential over a proposition is proved from a proof of it | −6 | −18 | −18 | 3,501 | 2,791 | −86 |
| 12. An existential over a proposition is unpacked | −36 | −12 | −12 | 3,501 | 2,791 | −808 |
| 13. A conjunct applied to further arguments is described | 0 | −1 | −1 | 3,490 | 2,791 | +533 |
| 14. A nonempty type with an element in the local context | 0 | −2 | −2 | 3,488 | 2,791 | −14 |
| 15. Local instance hypotheses are named in instance steps | 0 | 0 | 0 | 3,488 | 2,791 | +291 |

Changes 3, 4 and 15 only reword or tag steps; they do not explain anything, and
the gap counts show that. Change 4 is why `opaque_apply_steps` fell from 7,616
to 37: that measure is kept only as a wording measure. `citation_gap_steps`
counts the rule tag, so rewording a citation cannot change it (see
`tests/test_reader_quality.py::test_citation_count_does_not_depend_on_wording`).
Change 8 only regroups non-gap lines; its row and
`test_grouping_hypotheses_changes_no_gap_count` show that no gap count moves.
Of the 11 citations that change 13 removes, 10 are relabelled
`unchecked-application` and stay gaps; one is explained.

## Derivation of each phrasing

Every sentence uses only the frame's head, statement, objects, premises,
binder, domain and context. "Gap" means the step keeps `fallback=True` and is
shown as an explanation gap. Every exported frame is still owned by exactly one
displayed step, and `check_reading` still regenerates the reading.

| Rule | Recognized from | Sentence | Gap |
|---|---|---|---|
| `instance-facts` | A frame that is a typeclass side condition (below), grouped per parent after the mathematical premises | "Standard instance fact(s) used: S₁; S₂." listing the root statements; the detail lists every absorbed frame and head. Non-instance premises of an instance derivation (a project lemma, a local fact) stay visible as children, and then the step reads "Instance fact(s) used, derived using the premise(s) below: S." instead of "Standard". Since 0.6.0 a derivation that absorbs a local instance hypothesis is not called standard either: "Instance fact used: Countable U. The derivation uses the local instance hypothesis inst_1: Finite U." ("also uses" after a visible premise). | Yes |
| `instance-assumptions` | A hypothesis whose binder is Lean's automatic instance name (`inst`, `inst_2`, `inst✝¹`) and whose statement is a plain proposition | "Instance assumption(s) used: S." | No |
| `automation` | An application whose head is in `Mathlib.Meta.NormNum.`, `Mathlib.Meta.Positivity.` or `Mathlib.Tactic.Linarith.` | "Numerical evaluation (norm_num) verifies this", "Sign analysis (positivity) proves this", "Linear arithmetic (linarith) proves this" or, for a conclusion False, "derives a contradiction"; each ends "the computation/certificate is not expanded" | Yes |
| `rewrite` | A frontier rewrite without a polynomial certificate | `Eq.mpr`: rewrite the goal to an equal proposition and prove that; `Eq.mp`: obtain this by rewriting another proposition; `of_eq_true`: this proposition is proved equal to True (no tactic is named: the frontier does not record one); `congrArg`, `congrFun`, `congrFun'`, `congr`: congruence from equations that are not expanded | Yes |
| `citation`, `project-citation` | Any other application or constant with a head; `project-citation` when the head is in `OAI.` | "By X:" or "By the project lemma X:" (or "project instance" for an `instX` name), with the conclusion and premises below. `X._simp_n` reads "By X (in the equational form generated for simp):"; `X._proof_n` reads "By an auxiliary proof that Lean extracted while elaborating X:". `Subtype.property` names the element. Since 0.6.0 `Nonempty.intro` with an element that is not a local variable reads "Exhibit the element v of α; its construction is not expanded here." | Yes |
| `transport` | `cast` with exactly two objects α, β and premises at argument slots 2 and 3, where the premises print as `α = β` (one outer `=`) and α, and the conclusion prints as β | "From α, obtain β by rewriting with the equation of propositions below." | No |
| `choose-element` | `Nonempty.casesOn` with exact argument paths, a premise printed `Nonempty α`, a binder over α and a body proving the same printed statement (constant motive) | "Since Nonempty α, choose a ∈ α." | No |
| `unpack-conjunction` (named) | An existing exact `And.casesOn` destructuring whose major premise is a hypothesis printed as the two displayed parts joined by ∧ with the right precedence | "From h, obtain a: A and b: B." A part destructured again in the same way, and used nowhere else, is replaced by its own parts: "From h, obtain a: A, c: C and d: D." | No |
| `conjunction-projection` | `And.left`/`And.right` with exact argument paths whose premise prints as the two objects joined by ∧ and whose conclusion is the recorded component. Since 0.6.0 the premise is read with Lean's precedence (`_joins_conjunction`), and a right conjunct that begins with ∀, ∃, ∃!, ∀ᶠ or ∃ᶠ takes the rest of the formula: `A ∧ ∀ x, P x → Q` is `A ∧ (∀ x, (P x → Q))` | "Take the first conjunct, P." | No |
| `unchecked-projection` | The same projection whose premise is printed differently (for example `s ∈ Set.Ioc 0 1`) | "Take the first conjunct, P, of the premise below; its second conjunct is Q. That the premise has this form is not checked here." | Yes |
| `applied-projection` | `And.left`/`And.right` followed by further arguments, with exact argument paths, the premise printed as the conjunction, no object argument, one further premise printed P, the conjunct printed `P → Q` or `¬P` and the conclusion printed Q or False | "Take the second conjunct, P → Q, of the first premise below and apply it to the further premise below." | No |
| `unchecked-application` | The same projection with object arguments, several premises or other printing: the instantiation, or a definitional unfolding between the printed premise and the conjunct, is not checked | "Take the first conjunct, ∀ n, f n ≤ 1, of the premise below and apply it to m; that this gives the statement shown is not checked here." | Yes |
| `equivalence-reverse` | `Iff.mpr` with exact argument paths whose premise prints as L ↔ R and whose second premise and conclusion print as R and L. Since 0.6.0 the premise is read with ↔ at precedence 20: the left side unparenthesized only without an outer ↔, binder, comma or keyword, the right side only without an outer ↔ | "Use the reverse direction of L ↔ R: from R, obtain L." | No |
| `witness-proof` | `Exists.intro` with objects α, p and premises at slots 2 and 3 at exact paths, whose statement prints as `∃ (x : A) …` with A printed as α and whose witness is printed as α. With the anonymous binder `_` the second premise must print as the rest of the statement. A chain of such introductions along the second premise is one step | "Prove A₁, then A₂, and then the remaining claim." With a named binder: ", which may depend on the proof h." | No |
| `unpack-existential` | `Exists.casesOn` with objects α, p, motive and premises at slots 3 and 4 at exact paths; a first binder that is an assumption with domain printed as α, a second assumption, and a body proving the printed conclusion (constant motive); the major premise prints as `∃ (x : A) …` with A printed as α | "From h, obtain ha: A and hb: B." when the major premise is a hypothesis (the step owns it), otherwise "From the existential statement, obtain …" | No |
| `nonempty-intro` | `Nonempty.intro` with objects α and v, where v is the innermost local variable of that name, its recorded type prints as α and the statement prints as `Nonempty α` | "Since v ∈ α, Nonempty α holds." | No |
| `hypotheses` | Two or more adjacent displayed hypothesis lines in one list of steps, with the same local context, none a budget cut and none a fact from an anonymous `have` | "Use the hypotheses h₁: P₁; h₂: P₂." in the original order, one hypothesis per line when a statement is printed over several lines. The detail lists each recorded binder and statement. A single hypothesis still reads "Use the hypothesis h: P." | No |
| `substitution` | `Eq.ndrec` or `Eq.rec` with proof arguments at slots 3 and 5 | "Rewrite the statement proved below along the equation a = b; which occurrences are rewritten is not displayed." The equation is the recorded statement of the slot-5 premise, not the objects a and b joined by `=` (that would misread an a such as `fun x => t`). Further object arguments are named ("then specialize the result to x"), and further premises are mentioned. | Yes |
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

The precedence readings of ∧ and ↔ are a restricted display grammar, not a Lean
parser. They accept a printed premise only when it is textually the two
recorded sides joined in a way Lean parses as intended, and reject anything
else, including correct cases they cannot read (an outer ↔ inside a binder on
the right of ↔, a right conjunct with an outer → that does not begin with a
binder). Adversarial cases for both are synthetic tests.

## What remains a gap

| Rule | Gap steps | Meaning |
|---|---:|---|
| `project-citation` | 2,068 | A project lemma cited without its own proof in this reading |
| `citation` | 1,420 | A library or other non-project constant cited without proof, and 12 `Nonempty.intro` elements whose construction is not expanded |
| `instance-facts` | 522 | Typeclass instance derivations (2,132 frames); 50 of these steps rest on a visible premise such as a project lemma, and 29 on a local instance hypothesis |
| `rewrite` | 346 | Rewrites whose equations are not exported (including 30 `of_eq_true` frontiers) |
| `automation` | 260 | norm_num, positivity and linarith certificates (1,723 frames) |
| `unchecked-projection` | 127 | A conjunct of a premise printed in another form: 74 named definitions or other forms, 35 set memberships such as `s ∈ Ioc 0 1`, 10 conjunctions that the precedence reading does not accept, 8 premises printed with `have` or `let` |
| `restatement` | 124 | Definitional restatements |
| `substitution` | 56 | `Eq.ndrec`/`Eq.rec` substitutions |
| `witness` | 17 | Witnesses for goals printed as definitions |
| `unchecked-application` | 10 | A conjunct applied to arguments without a checked instantiation |
| `application` | 7 | Applications without a recorded head |
| `ring` | 4 | `ring` normalizations without a polynomial certificate |

No reading is free of gaps. Citations are 70% of the remaining gap steps: they
become explained only when the cited lemma gets its own reading or a reviewed
dictionary sentence.

## Readings with the fewest gaps

| Gap steps in the reading | 1 | 2 | 3 | 4 | 5 | 6–9 | 10 or more |
|---|---:|---:|---:|---:|---:|---:|---:|
| Readings | 65 | 104 | 52 | 31 | 26 | 65 | 149 |

The 221 readings with one to three gaps contain 429 gap steps: 379 project
citations, 22 frontier rewrites (19 `Eq.mpr`, 2 `Eq.mp`, 1 `congrFun`), 17
citations, 5 library instance derivations, 2 substitutions, 1 restatement, 1
application without a head, 1 unchecked projection and 1 unchecked application.
The 17 citations are 4 `Nonempty.intro` elements built from project
definitions, 2 `Iff.mpr` whose second premise is printed differently from the
equivalence, one `Nonempty.casesOn` over a premise printed as a definition, and
10 library lemmas cited once each. 178 of the 221 readings have only project
citations as gaps.

Of the 65 readings with one gap, 55 have a project citation, 8 a frontier
rewrite, and 2 a `Nonempty.intro` (`OAI.VertexCover.explicit_cover_gap` and
`OAI.MinUncut.main`). Each of those two theorems states that a type of
reductions is nonempty, and its proof exhibits a project construction. The
reading shows the construction but does not expand it, so it stays a gap: the
mathematical content of the theorem is in that construction. A frontier rewrite
records no equation, and a project citation needs the cited lemma's own reading
or a reviewed sentence, so none of the remaining blockers can be explained from
the recorded data of these snapshots.

## Limitations

- A single hypothesis under a citation is not folded into the citation's
  sentence: 807 citation steps (439 project, 368 library) show exactly one
  hypothesis line, and no grouped line, among their children. Folding would make the citation step own
  the hypothesis frame, and since a citation is a gap, 807 recorded hypotheses
  would become gap frames.
- 108 adjacent pairs of hypothesis lines are not merged because one is a fact
  from an anonymous `have` ("Use the fact … established above"), and 8 because
  the two lines live in different local contexts (one under a binder).
- A merged hypothesis line keeps the step identifier of its first hypothesis;
  the identifiers of the other hypothesis steps no longer exist.
- `Nonempty.casesOn` whose premise or body is printed in unfolded form (5
  steps) is still a citation, and the named-goal witness (17) is still a gap.

## Compatibility and trust boundary

- The renderer label is `source-math-en/0.6.0`. `check_reading` still requires
  byte-identical regeneration of the reading binding. The one exception: a
  saved reading labelled `source-math-en/0.4.2` (the only label in
  `EARLIER_PRINTERS`) is accepted when regeneration is identical except for
  that label, and only for the two snapshots listed with it: the Bézout demo
  snapshot (`dad8ef23…`) and the native companion snapshot (`e93e0455…`), whose
  retained 0.4.2 readings 0.6.0 reproduces exactly; none of the 0.6.0 rules
  applies to them. The companion, source-text and source-equation builds depend
  on this. For any other snapshot the 0.4.2 label is refused even when the text
  is identical, because no retained 0.4.2 reading of that snapshot shows the
  label to be true. No reading saved under the 0.5.0 label is retained, so that
  label is not listed; such a reading must be regenerated.
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
from the full snapshot. Only the root step may differ: its conclusion, and the
wording of a citation that proves the subtree's own statement ("The statement
follows from X" for "By X"). 0.6.0 adds 11 real fixtures. Tests that build
records by hand say so; they are format fixtures, not Lean observations. The
precedence traps for ∧ and ↔ and the hypothesis-grouping boundaries (budget
cuts, anonymous `have` facts, different scopes) are synthetic.
`tests/audit/test_retained_reader_regressions.py`, written for the audit role,
requires oversaturated projections in two retained snapshots to stay gaps:
the InfiniteMatroid projection is now an `unchecked-application` gap, and the
two DiamondDistortion projections, whose premise is printed as a definition,
remain citation gaps.
