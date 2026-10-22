# Source expressions and lemma extraction

This component connects the argument explorer's source paths to typed Lean
expressions. It can extract a selected local proof as a standalone lemma and
check that the lemma can be used back at the original source step. The importer
and extraction operation do not contain theorem-specific cases.

It reuses the constructor-DAG format in `KernelExport.lean` and the decoder in
`JsonReplay.lean`. Mathematical expressions are not reconstructed by parsing their
printed forms. The existing narrative exporter and its retained snapshots are
unchanged.

## Source identity

A request identifies a declaration and an ordered set of original proof paths.
The replay checker receives that request separately from the imported record.
Changing the record's declaration or paths cannot change what the checker expects.

Within a pinned source environment, the importer follows those occurrences in the
actual proof. Each surrounding binder receives its source path as an identity.
Variables inside expressions use de Bruijn indices; displayed names are labels.
Identities exposed to Python are scoped to the expression bundle's digest.
They are not durable identifiers across arbitrary source edits or environments.

A shared DAG node is not a variable identity. Identical expressions under two
separate quantifiers can share a table row while referring to different binders.
`resolve_variable` therefore uses an expression occurrence and its binder stack,
not just a node number. It also resolves variables inside context types and
local definitions.

The new encoder uses `ExprStructEq`. Lean's ordinary expression equality ignores
binder names and annotations, which can merge two differently annotated nodes in
a hash table. The wire format is unchanged, but this encoder preserves those
fields. Replay uses `Expr.equal` after explicitly removing metadata; it does not
replace source correspondence with logical equivalence or proof irrelevance.

The declared theorem statement is retained at the root. A proof body's inferred
type can be definitionally equal without being syntactically identical. For
example, `Nat.mul_zero` states `n * 0 = 0`, but its proof body can infer the type
`n * 0 = n * 0`. The root claim must not silently become the latter.

## Claims and inferences

Each selected proof occurrence records its type, context, source path, direct
variable uses, and dependency closure. Applications also record the head, every
argument's original path and type, and whether the argument is proof or data.
Data arguments retain their expressions. Selected proof arguments remain source
references rather than being copied wholesale into another proof language.

The Python view recognizes the structural forms of conjunction, disjunction,
implication binders, equivalence, negation, equality, and existence using exact
constructor identities. Other predicates remain atoms. A `forall` node alone
does not authorize an English quantifier template: its domain and dependencies
still matter. No interpretation is inferred from a theorem-name suffix.

The lightweight snapshot and typed view can use different printed variable names.
The Python bridge checks source paths and context origins and reports display
differences. Native replay independently regenerates the snapshot from the
expected declaration. Printed-string equality is not used to guess binder
correspondence.

## Lemma extraction

For a selected proof `p : P`, extraction starts with the free variables in both
`p` and `P`. It then closes that set under dependencies in the retained variables'
types and local definitions. The order is the original context order.

A variable's type can introduce a dependency not visible in the goal. Keeping
`i : Fin n`, for example, requires keeping `n`. Conversely, a genuinely unused
parameter need not become a parameter of the extracted lemma.

A local fact is not turned into a new assumption. For the proof

```lean
have result : Q := f h
exact result
```

extraction retains the definition of `result`, the function `f : P → Q`, and the
hypothesis `h : P`. It does not produce a lemma that assumes an independently
supplied proof of `Q`. Lean's `LocalDecl.value?` hides nondependent `have` values
by default, so this component explicitly requests those values.

There are two native operations:

- `Replay.verify` reconstructs the supplied expressions, compares them with the
  selected source occurrences, recomputes their dependencies, and kernel-checks
  the source judgements and dependency-closed types.
- `extractAt` compares the proposed closed type with that closure, installs a new
  theorem, and applies it to the retained variables at the original occurrence.
  That application must prove the original local claim. An existing declaration
  cannot be overwritten.

Kernel checking is forced on and synchronous. Temporary checks discard their
auxiliary declarations on success or failure. Extraction commits its environment
change only after both the new theorem and its reapplication pass. A caught
kernel failure must not leave Lean's recovery axiom available for later steps.

This is a checked extraction operation, not a claim that any reading order is a
valid proof order. A local argument can be presented separately by stating its
remaining conditions explicitly. Moving an open claim outside its assumptions,
or replacing the argument with a different one, is not licensed.

## Tests

The core regression sample contains fourteen small test declarations and twenty
existing Lean library theorems. The test declarations exercise shadowed names,
dependent types, typeclass instances, local proof definitions, quantified
witnesses, and shared expression nodes under distinct binders. The library sample
was chosen for structural variety; it is not the seeded OpenAI cohort.

The optional Mathlib run adds the existing Bézout theorem. It uses the unchanged
body and the same disclosed two-import adapter as the earlier companion checks.
Its freshly generated 86-frame snapshot must match the retained snapshot. There
is no Bézout-specific branch in the importer or extraction operation.

The native gate compiles in a fresh workspace, exports twice, replays in separate
processes, and extracts and reapplies every selected source occurrence. The
exports and replay inventories must repeat exactly. The core run also regenerates
the committed JSON regression fixtures byte for byte.

Negative controls alter actual output records: source identities, binder paths,
annotations, proof references, dependencies, local definitions, argument order,
witnesses, claims, and display text. They include a different true claim,
alpha-equivalent binder changes, a corrupted lightweight snapshot, an invalid
extraction type, a declaration overwrite, and an attempted kernel-check bypass.
An unexpected rejection reason also fails the gate.

The Python checks independently reconstruct dependency closure and the closed
claim, including capture-avoiding de Bruijn remapping. They do not establish
source typing. Their summaries explicitly report that native replay has not been
performed by loading the file.

## Reproduce

From a checkout with Lean 4.34.1:

```sh
python scripts/check_source_expressions.py \
  --lean /path/to/lean-4.34.1/bin/lean \
  --output /tmp/source-expressions-core \
  --trust-project

python -m pytest tests/test_source_expressions.py \
  tests/test_source_expression_gate.py -q
```

To add the retained Bézout source, pass a Mathlib checkout at
`d13f23b723b8a846827a245b89c10fc7d3f11612` with the Euclidean-domain and ring-tactic
imports available:

```sh
python scripts/check_source_expressions.py \
  --lean /path/to/lean-4.34.1/bin/lean \
  --project /path/to/pinned-mathlib \
  --output /tmp/source-expressions-mathlib \
  --trust-project
```

The optional `--retained-environment` argument checks every file of the existing
pinned environment archive instead of requiring Git checkouts. Output directories
must be new or empty. Missing compilers, wrong versions, incomplete exports,
failed checks, and timeouts leave failed observations; they are never skipped
successes. The existing CI and companion workflows retain the records, requests, generated drivers,
negative inputs, logs, and source archive.

## Limitations

The current kernel checks apply to particular source judgements and extracted
lemmas. The metaprogram implementing the importer is not universally verified.
The Lean kernel, imported environment, and execution infrastructure remain trusted.
File hashes bind the retained bytes; they do not authenticate an adversarial
runtime. Source environments must be pinned independently of an imported record.

The dependency set is sufficient for the selected source proof, not mathematically
minimal. Definitions needed for closure can include substantial proof terms.
Resource limits reject inputs that exceed the current budgets; they are not a
completeness or denial-of-service theorem.

No new English passage is certified. The existing Bézout document and original
corpus measurements are unchanged. The fixed twenty-proof OpenAI sample has not
been run through this importer, and no full original-project build is claimed.
The certified-English research track therefore does not gain coverage or meet its
reuse exit criterion from this result alone.

The next use is an explanation planner that proposes intermediate lemmas and
checks their extraction with this API. Selecting an informative decomposition,
rendering it as mathematical prose, and checking the composition of the resulting
exposition remain separate tasks.
