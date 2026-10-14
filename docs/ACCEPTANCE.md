# Acceptance gates — 0.2.0

These gates are independent. A successful build, readable page or positive receipt
must not be counted as an English fidelity or whole-corpus result.

## A0 — deterministic, usable reading software

Local tests cover source scanning, typed-expression validation, English
regeneration, capture-avoiding display reduction, the browser, packaging and CLI.
The default reader contains five real typed exports and nine source candidates.
Unsupported expressions remain visible. This is implemented, but it is not a
human comprehension result. See `VALIDATION_V0_2.md` for the executed test count.

## A1 — actual theorem and intermediate-judgement checking

Required: compile the exporter; reconstruct the original declaration; independently
follow each source path; kernel-check every displayed term/type judgement; retain
version, universe and axiom inventories. Negative cases must fail for the intended
reason, not merely because the driver has a syntax error.

Current: individual remote exporter and checker programs executed on Lean 4.34.0.
Five compact exports are retained. One retained example has all original-path and
18 term/type judgement checks observed, with source-path, intermediate-type and
version mutations rejected. Earlier tests reject axiom and binder-role mutations.
The complete native 4.34.1 module pipeline is still **unrun here**, and its mandatory
CI test must pass without skips before claiming native integrated acceptance.

## A2 — complete expected-corpus accounting and execution

Required: pin the source and dependencies; acquire all expected files; enumerate
actual theorem declarations from every required module; retain every build,
export and checking failure; reconcile independent shards.

Current: complete metadata observation for the 23 `lean/OAI` domain subtrees:
122,458 Lean files, 1,571,301,358 bytes. The file contents have not all been acquired
or built. Expected theorem count is unknown until all modules are enumerated.
The v2 denominator is `.thmInfo` theorem declarations, not proof-valued definitions
or manuscript claims. Expanding that scope requires an explicit contract change.
The adapted Bézout-body experiment is not an exact pinned-project pass.

## A3 — mathematical reading completeness

Required: expose all hypotheses, conclusions, witness conditions, branch scopes,
lemma statements and dependencies for every theorem in scope. A bare lemma name
is not a complete explanation. Generic terms, opaque computations, capped
branches and unresolved vocabulary remain separately visible and measurable.

Current: typed assumptions, introductions, basic logical constructors, witness
introduction, simple alternatives, equalities and injectivity application render
as mathematics. Arbitrary recursors, induction and dependency statements are not
fully explained. The large Bézout export hit explicit expansion caps. No full
corpus English completeness result is claimed.

## A4 — faithful language and compression

Required: bind each displayed inference to the exact original proof path and its
checked claim; make grammar interpretation and display-normalization semantics
explicit; prove the relevant interpretation/round-trip properties. Compression
must preserve an inspectable argument, not substitute a new plausible proof.

Current: the typed judgement and path checker exists and has live positive and
negative evidence. `check-reading` rejects changes to regenerated statements,
parameters and proof prose. The grammar, Python renderer and display normalizer
are **not formally proved correct**. Byte-for-byte regeneration is not semantic
certification. The English acceptance gate therefore remains false.

## A5 — reduced burden on mathematicians

Required: independently selected complete proofs and comprehension/error-detection
tasks with practicing mathematicians; compare review time and correctness against
Lean and relevant existing readers. Do not infer benefit from screenshots or
counts of grammatical sentences.

Current: no human study. This remains the ultimate product acceptance criterion.
