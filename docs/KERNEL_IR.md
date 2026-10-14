# Frozen v2 argument contract

Authority is `proofreader.kernel-export/v2`. Reader output remains the backwards-
compatible `proofreader.document/v1` format with additional typed metadata.

## Expression graph

`exprs` is a topological DAG. Every edge refers to an earlier node. Constructor
fields are exact; unknown fields, extra variables, unresolved metavariables and
unlisted universe parameters are rejected. Names preserve anonymous/str/num
constructors, avoiding collisions between a single dotted component and a
qualified name. Binder indices are de Bruijn indices, not text substitutions.
The root `type` and `term` must be closed under `levels`.

Each step records its `term`, Lean-inferred `type`, `is_proof`, `path`, `children`,
complete application `arguments`, optional `domain_is_prop`, and `truncated`.
No pretty-print string or prewritten English sentence is trusted as mathematics.

## Original-expression paths

- Application: 0 = function, 1 = argument.
- Lambda/forall: 0 = domain, 1 = body; entering the body adds the original binder.
- Let: 0 = type, 1 = value, 2 = body; the body adds the original let binder.
- Projection: 0 = object.

Python validates every path. The generated Lean program independently follows it
in the imported original proof and closes the result over the actual enclosing
context. The term must equal the submitted closed judgement term before typing.
Native kernel checks then validate all proof and data types.

## Coverage and omission

The raw expression graph retains the original proof. The typed reading expansion
has depth/step budgets; hitting them creates explicit truncated steps, not a
claim of conceptual explanation. In-flight siblings may cause the exporter to
exceed its 1,500-step expansion threshold slightly; the whole response remains
size-bounded. Explicit formula-normalization limits produce visible references.

Unknown named lemmas are cited, not purportedly explained. Imports may contain
arbitrary definitions; dictionary expansion and semantic abstraction remain work.
Do not redefine success as printing an opaque `apply` sentence for every theorem.

## Provenance states

`exported`, `structurally_validated`, `rendered`, `path_linkage_checked_in_lean`,
`all_judgements_kernel_checked`, `regeneration_matched`, `english_formally_verified`,
and `human_readability_evaluated` are distinct. Only actual checks may populate
execution states. A saved imported receipt never authenticates its own producer.

Keep the schema stable while improving explanations. Changes to the display
compiler require a printer version bump and determinism/regeneration tests.
