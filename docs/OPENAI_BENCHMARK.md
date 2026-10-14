# OpenAI acceptance target

Repository `openai/math`, commit
`1581d4cbdd69a0faf34b2089614fe2a814316a6a`; `lean-toolchain` specifies 4.34.1.
The mathematics manuscripts, formalization catalog and actual Lean theorem
inventory are different sets. Do not report file counts as proof counts or say
that unformalized manuscripts have been translated.

## Observed metadata

`artifacts/v0.2/openai-inventory-observation.json` records a GitHub metadata
traversal across all 23 `lean/OAI` domain subtrees: 122,458 `.lean` files totaling
1,571,301,358 source bytes. Root and subtrees were untruncated. No whole-corpus
content acquisition, build, export, replay, English check or human study occurred.
The metadata service response supplies expected file counts, not proof truth.

The repository includes six original source files whose Git hashes are tested.
They contain nine source declaration candidates. A separate adapted-harness
Bézout experiment is recorded, but is not a pinned-project pass.

## Reproducible runner

```sh
proofreader fetch-openai work/openai-math
proofreader benchmark work/openai-math -o output/inventory
proofreader gate output/inventory/coverage.json --level inventory

# Execute each index from 0 through 15 on a trusted configured runner.
proofreader extract-corpus work/openai-math -o output/shard-0 \
  --engine kernel --trust-project --shard-count 16 --shard-index 0

proofreader aggregate work/openai-math output/shard-*/extraction.json \
  -o output/aggregate
proofreader gate output/aggregate/coverage.json --level replay
# English fidelity gate intentionally fails in 0.2.
proofreader gate output/aggregate/coverage.json --level english
```

Acquisition falls back from truncated recursive trees to independently complete
subtrees. Existing files that differ from pinned hashes are not overwritten.
Missing artifacts stay in the manifest. For corpora above 500 source files,
benchmarking emits a memory-bounded ledger rather than holding all proof documents.
Typed module extraction separately writes per-module/per-theorem readers.

Each v2 module report reconciles an environment-derived theorem inventory with
one result per expected theorem. The aggregator rejects missing/duplicate modules,
different corpus commits, missing theorem outcomes, duplicate declaration ownership,
failed replay and disallowed axioms. It reports an additional
`all_path_bound_theorem_judgements_checked` flag only for complete v2 runs; legacy
root-term-only replay cannot set it. These reports are unsigned run ledgers.

## Limits

The v2 denominator is theorem declarations in `lean/OAI` modules. Proof-valued
`def`s and all dependency definitions need explicit future coverage. Per-module
proof checking can be expensive and should be cached/batched on the runner;
performance at full target scale is not measured. Unexpected timeouts, expression
budgets, export caps or unsupported structures must remain visible. Do not tune
coverage by deleting hard files, assuming imported lemma names explain their
proofs, or relabelling an adapted Lean version as the pinned one.
