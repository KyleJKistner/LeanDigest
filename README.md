# Leanglish

**Lean proofs, in mathematical English.**

Leanglish is the product name. The repository remains `KyleJKistner/LeanDigest`.
Use `leanglish` or `python -m leanglish`; the existing `proofreader` command,
Python package, installation name (`lean-proofreader`), and proof formats remain
compatible. This is the v0.3.0 development snapshot, now with the new public name.
See [naming and compatibility](docs/NAMING.md).

Read a formal argument as mathematical prose without starting in a Lean editor.
The renderer is deterministic and makes no language-model API calls. Source
outlines, typed evidence, successful checking observations, English fidelity and
reader comprehension remain separate measurements.

## Version 0.3.0 — a retained substantial proof

The OpenAI Bézout-frame existence theorem now has a complete retained mathematical
reading: two gcd cases, divisibility witnesses, a Bézout calculation, nonzero
cancellation, and verification of the four final equalities. Lean **4.34.1**
accepted **86 selected original-proof judgements** and their independent source
paths. Repeated extraction was identical; altered paths, a false intermediate
claim and an altered snapshot were rejected. The reader accounts for all 86
exported frames in 59 displayed steps, with **16 independently replayable exact
integer-polynomial certificates** and no budget cuts in this selected example.

The theorem body is unchanged; imports were adapted. This is **not** a build of
the entire pinned OpenAI project, a whole-corpus translation, or a formal proof
of English fidelity. Formula text uses Lean's pretty-printer. Imported lemma
statements appear as mathematical dependencies; their proofs are not all expanded.
No human comprehension study has run.

See [executed validation](docs/VALIDATION_V0_3.md),
[source-bound reading and trust boundaries](docs/NARRATIVE.md), and
[the earlier exact-DAG contract](docs/KERNEL_IR.md).

## Open the reader

Python 3.11 or later. No runtime Python dependencies, API key, network connection
or Lean installation is needed to read the bundled proofs.

```sh
python -m leanglish narrative-demo -o reader.html
python -m leanglish serve
```

Open `http://127.0.0.1:8765`. The default library starts with the Bézout argument.
It also retains five small constructor-DAG examples and eight source-only OpenAI
declaration candidates. **Typed** includes the five DAG examples and the one
source-bound snapshot; the evidence badge distinguishes the routes. Inspect an
arithmetic step for its coefficient certificate; expand an intermediate fact for
its supporting argument. The Evidence panel records limitations and exact hashes.

The generated HTML is self-contained. Attachment viewers that disable JavaScript
may need the local server. `kernel-demo` still opens the v0.2 small-proof library;
`demo` still opens the source-only demonstration.

## Recheck the displayed argument without Lean

```sh
python -m leanglish narrative-read proofreader/data/bezout-snapshot.json \
  --source proofreader/data/bezout-original.lean \
  --receipt proofreader/data/bezout-receipt.json -o output/bezout
python -m leanglish check-narrative proofreader/data/bezout-snapshot.json \
  output/bezout/reading.json --certificates output/bezout/polynomial-certificates.json
```

This regenerates the reading and independently checks the polynomial identities.
It does not authenticate the source snapshot. Actual Lean re-extraction is
explicit opt-in:

```sh
python -m leanglish verify-narrative proofreader/data/bezout-snapshot.json \
  --driver proofreader/data/bezout-reproduce.lean \
  --backend axle --allow-remote -o output/recheck
```

This sends the complete driver to AXLE. Native execution instead uses an existing
trusted project and `--trust-project`. Elaborating Lean can run arbitrary code;
consent is not a sandbox. The browser has no execution endpoint. The exact
metaprograms ran remotely; native and installed-CLI transport integration remain
separate gates, not implied by the local reader tests.

## A typed export → a complete offline reading bundle

```sh
python -m pip install .
leanglish kernel-read artifacts/v0.2/and_swap.kernel.json \
  -o output/and-swap --context examples/kernel/Smoke.lean \
  --receipt artifacts/v0.2/and_swap.receipt.json
leanglish check-reading artifacts/v0.2/and_swap.kernel.json \
  output/and-swap/reading.json
```

The output includes `reader.html`, `reading.json`, `proof.txt`, `argument.json`,
`Check.lean`, and `coverage.json`. Without `--context` or `--module`, the
generated checker still requires the original theorem environment before replay. Reading validates constructor shape, scope,
original-proof paths and argument inventories. It does **not** execute Lean.
`check-reading` detects any divergence from deterministic English regeneration;
it is not an English parser or a formal semantic equivalence proof.

## Extract and check a project module

Use an already configured project's pinned Lean toolchain and dependencies:

```sh
leanglish extract-kernel --project lean --module ProofReader.Smoke \
  --output output/native-smoke --trust-project --verify
```

The v2 extractor enumerates **theorem declarations** from Lean's environment,
retains individual failures, emits the expected inventory, builds the reading
library and optionally checks all intermediate judgements. Proof-valued `def`s
and informal manuscripts are not yet part of this v2 theorem denominator.
The combined native command is implemented and has a mandatory integration test;
it has not run in this container because Lean/Lake is absent.

**Lean elaboration can execute arbitrary code.** `--trust-project` is consent,
not isolation. Use a trusted project or an independently secured disposable
sandbox without credentials. The web reader has no execution endpoint.

## Optional remote compilation

The AXLE adapter is explicit opt-in. It sends the **entire provided source
context and generated checking code** to the third-party service. It never sends
anything during ordinary reading.

```sh
leanglish extract-kernel --backend axle --lean-version 4.34.0 \
  --context examples/kernel/Showcase.lean --output output/remote \
  --allow-remote --verify
```

Use a self-contained context with the necessary imports, including `Lean`.
`ProofReaderKernel` is a reserved tool namespace excluded from local-source
inventory. Native imported-module enumeration does not rely on that exclusion.
All service responses, the exact request source, inventories and failures are
saved. API authentication can be supplied via `AXLE_API_KEY`; tokens are not
written to artifacts. Service availability/dependency caches are external.

Do not change an exported argument's recorded Lean version to force replay.
Re-extract on the desired version instead. Earlier remote environments had missing cached dependencies; availability changed during testing. The v0.3 substantial experiment succeeded on Lean 4.34.1 with minimal imports. The exact pinned OpenAI dependency environment remains unvalidated.

## Complete OpenAI benchmark target

Pinned repository `openai/math`, commit
`1581d4cbdd69a0faf34b2089614fe2a814316a6a`.

A fresh metadata traversal of all 23 `lean/OAI` domain subtrees counted
**122,458 Lean files / 1,571,301,358 source bytes**. Every returned subtree was
untruncated. This is a file inventory observation, **not a theorem count or a
successful proof run**. The observation is saved under `artifacts/v0.2/`.

```sh
leanglish fetch-openai work/openai-math
leanglish benchmark work/openai-math -o output/inventory
leanglish extract-corpus work/openai-math -o output/shard-0 \
  --trust-project --engine kernel --shard-count 16 --shard-index 0
# Run the other shard indices, then reconcile every report.
leanglish aggregate work/openai-math output/shard-*/extraction.json \
  -o output/aggregate
```

The new kernel engine is the default for corpus extraction. Missing modules,
export failures and failed checks stay in the denominator. Large source
benchmarks use a ledger-only mode instead of retaining a multi-gigabyte proof
book in memory. Per-module readers are produced during typed extraction.
See [benchmark scope](docs/OPENAI_BENCHMARK.md).

## Tests

```sh
python -m pip install '.[dev,webtest]'
python -m playwright install chromium
python scripts/build_demo.py
python scripts/build_typed_demo.py
python scripts/build_narrative_demo.py
python -m pytest -q

# These tests may not skip in the native CI job.
PROOFREADER_REQUIRE_LEAN=1 python -m pytest \
  tests/test_lean_integration.py tests/test_kernel_integration.py tests/test_narrative_integration.py -q
```

Local results and exact successful/negative remote checking sources are included
under `artifacts/v0.2/` and `artifacts/v0.3/`.

Both native Lean integration and Python/browser CI passed on commit `2d6b60f`
([run 38667444089](https://github.com/KyleJKistner/LeanDigest/actions/runs/38667444089)).
This is the observed pre-rebranding baseline, not an assertion about future
commits. It does not establish the full pinned OpenAI dependency build.

## Repository and agent workflow

This repository is `KyleJKistner/LeanDigest`. It contains the v0.3.0 development
snapshot, including the application, Lean extraction/checking code, tests,
examples and retained validation evidence. Historical reports describe the
state at the time of each experiment; they are not claims that GitHub CI has
subsequently passed. There is no hosted deployment.

The original creation helper, `scripts/publish.sh`, now targets `LeanDigest`.
It fails rather than overwriting an existing repository; ordinary updates should
use a normal commit and push. See `docs/IMPORT_V0_3.md` for snapshot scope.

No independent coding agents were launched. `AGENTS.md`, `agents/tasks.json` and
`scripts/team.py` provide bounded work packages and an optional external-agent
launcher in separate worktrees. A work package is not evidence of agent execution.

The ideas of deterministic verbalization and expandable proof displays have
precedents in LeanInformal, Informath and Verbose Lean. This release makes no
novelty or publication claim. New code is MIT; OpenAI source samples retain their
Apache 2.0 license. See `THIRD_PARTY_NOTICES.md`.
