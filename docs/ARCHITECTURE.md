# Architecture — 0.2.0

## Reading paths

**Legacy source aid:** UTF-8 source → lossless scanner → conservative declaration
index → instruction outline → evidence-labelled reading document. This path does
not execute Lean and does not claim an elaborated mathematical proof.

**Typed mathematical reader:** Lean's elaborated theorem → shared constructor
DAG and typed source-path judgements → strict structural validation → deterministic
mathematical language → the same offline reading document. Native and AXLE
execution are explicit opt-in operations, separate from reading.

**Independent checking:** reconstruct the original statement and proof from the
DAG; compare their exact constructors to the original theorem after metadata
removal; independently follow each recorded path inside Lean; close every term
and claimed type over its original binders; submit those judgements to the kernel.
Version, universes, axioms and proof/data roles are separate checked constraints.

## Implementation map

| Component | Files | Contract |
|---|---|---|
| Source navigation | `lexer.py`, `source.py` | Source candidates and spans, never elaborated proof claims |
| Typed export | `lean/KernelExport.lean` | Shared Expr DAG, actual inferred types, source paths, explicit caps |
| Structural checker | `kernel.py` | Exact structured names, bounded constructors, scope and path reconciliation |
| Generated Lean checker | `kernel.py` | Root identity, independent path traversal and all term/type judgements |
| Mathematics printer | `english.py`, `normalization.py` | Rule-based mathematical notation, support links, bounded beta/zeta display reduction |
| Execution and observations | `kernel_io.py` | Explicit consent, recorded requests/results, all completion markers, axiom policy |
| Module/source pipeline | `kernel_pipeline.py` | Expected theorem inventory, per-theorem failures, readers and optional checking |
| Corpus orchestration | `corpus.py` | Pinned hashes, stable shards, complete aggregation and ledger-only source scale mode |
| Document/interface | `model.py`, `render.py`, `web/` | Static reading pages with separate evidence axes and source inspection |
| Legacy integration | `core.py`, `lean.py`, `lean/ProofReader.lean` | v1 compatibility, bounded process execution; not promoted to v2 fidelity |
| CLI/local server | `cli.py`, `server.py` | Offline defaults; no Lean execution endpoint in the server |

## Versioned contracts

See `KERNEL_IR.md` for `proofreader.kernel-export/v2` and its path convention.
Inventory and failure rows use `proofreader.kernel-inventory/v2` and
`proofreader.kernel-failure/v2`. Inventory enumeration currently covers theorem
constants; proof-valued `def`s need a future explicitly expanded scope.

`proofreader.document/v1` remains the UI contract; steps can link to preceding
supporting steps rather than duplicate whole subtrees. The original fully
quantified statement remains available even when assumptions are displayed
separately for reading.

`proofreader.kernel-receipt/v2` records a checking observation. It is not signed,
not self-authenticating, not a proof of grammar semantics, and not a complete
hash inventory of imported compiled dependencies. The accompanying generated
program is the re-executable evidence. Never trust an imported `status` field as
an independent attestation.

## Determinism and presentation

No language model is used by the reading pipeline. Stable constructor identities,
source paths, ordering, rule versions and canonical JSON bind regenerated prose.
Runtime logs include timings and are not deterministic content. Cross-machine
export identity requires pinning Lean, the exporter and project dependencies and
has not been benchmarked.

Display reduction is capture-avoiding and bounded; it appends derived display
nodes without replacing the authoritative proof DAG. Tests exercise binder
capture and hostile shared terms. Its implementation and the English grammar
are not formally verified. Unknown mathematical vocabulary stays visible.

## Scale boundaries

Raw export has an explicit 250,000-expression-node budget. Proof expansion uses
depth 80 and a 1,500-step threshold; in-flight siblings may produce a few extra
capped leaves. A full raw term can coexist with a capped explanation. The renderer
has separate visit, node and application-spine budgets.

Source benchmarks above 500 files are ledger-only, avoiding a monolithic proof
book in memory. Typed extraction produces per-module/per-theorem outputs. The
122,458-file target has not been run end to end; these mechanisms are not a
performance claim for the complete corpus.

## Next integration boundary

Individual 4.34.0 exporter/checker programs have live evidence. Native integrated
module extraction on the pinned 4.34.1 toolchain remains mandatory CI work. A
separate lightweight probe compiled the inventory driver; that does not replace
the complete native integration test.
