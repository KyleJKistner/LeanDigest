# Lean ProofReader 0.2.0 — executed validation

## Delivered

A runnable offline typed-proof reader, constructor-DAG exporter, original-proof
path validator, deterministic English renderer, generated Lean intermediate-claim
checker, source/typed UI, explicit native/AXLE commands, corpus sharding and
accounting, tests, CI configuration and four bounded agent work packages.

The implementation remains a development preview, not the complete general-purpose
Lean-to-English product. **No whole-corpus translation, formal English guarantee,
human comprehension result or remote GitHub deployment is claimed.**

## Executed checks

| Check | Observed result |
|---|---|
| Local automated test suite | 190 passed; 2 native-Lean tests skipped |
| Real compact typed exports retained | 5 |
| Retained example with observed root, original-path and all-judgement checking | 1: conjunction reversal |
| Term/type judgements checked for that example | 18, including proof and data arguments; not 18 English inferences |
| Changed source path | Rejected: source linkage mismatch |
| Changed intermediate claim, unchanged original theorem | Original root and paths passed; kernel rejected the intermediate type |
| Changed Lean version | Rejected before success markers |
| Earlier changed binder classification / axiom inventory | Both rejected in separate live tests |
| Current checker reproduces exact successful live source | Byte-for-byte match; retained positive and negative source hashes match observations |
| Original six OpenAI sample Git-blob hashes | 6 of 6 match |
| Browser interactions | Chromium search, filters, source, typed assumptions, support links, evidence and mobile overflow checks passed |
| Wheel build / installed operation outside checkout | Passed, with packaged exporter and typed demo |
| Native integrated 4.34.1 module extraction/checking | Not run here; mandatory CI test included |
| Independent coding agents / GitHub CI / hosted deployment | Not executed |

Local tests include mocked-transport and malformed-fixture unit tests. Those do
not substitute for native or remote integration runs. The local runtime had no
Lean/Lake. Its two native integration tests remain explicitly skipped; the CI job
sets `PROOFREADER_REQUIRE_LEAN=1` so they cannot silently skip there.

## Exact live checking evidence

Remote experiments used **Lean 4.34.0 through AXLE**. The final positive checking
program is `artifacts/v0.2/path-check-valid.lean`, SHA-256:

```
04616eb7b1576b7599180492b29ffac16c516530ab166640aa9ffa57440a8c9a
```

The observed request identifier is `6b3986d5-cbf9-4a51-988f-50bf037d8004`.
It emitted all three required markers:

```
PROOFREADER_REPLAY_OK
PROOFREADER_PATHS_OK
PROOFREADER_JUDGEMENTS_OK:921aea7e2ab844d073360876f507d01aa5500d0de5b319dc12aa7104f8406e91:18
```

`live-path-tests.json` records exact request/source identities and the corresponding
negative outcomes. These are retained tool observations, **not signed certificates**.
A reader must trust the compiler, project, checker, Python renderer and transport,
or rerun them on trusted infrastructure. The English grammar and display
normalization do not have a formal correctness proof.

The crucial negative test changed the claim attached to a proof of
`∀ P Q, P ∧ Q → Q` into `∀ P Q, P ∧ Q → P`. Checking the original theorem alone
would not catch that mismatch. Here the root and path checks succeeded, then the
kernel rejected the incorrect intermediate declaration.

## Five retained typed examples

The demo generates its prose from these actual exported records, with no
language-model calls at reading time:

| Example | Shared expression nodes | Typed steps | Recorded judgements | Capped steps |
|---|---:|---:|---:|---:|
| Conjunction reversal | 29 | 8 | 18 | 0 |
| Implication transitivity | 22 | 9 | 11 | 0 |
| Composition of injective functions | 80 | 13 | 19 | 0 |
| Existential witness introduction | 26 | 5 | 9 | 0 |
| Reasoning from alternatives | 35 | 10 | 16 | 0 |

Only conjunction reversal has the final retained all-judgement checking
observation attached. The other four records do not inherit its result. They
were produced by real Lean extraction and pass structural/path validation locally.
The displayed source snippets are readable restatements; the recorded exact
checking source is authoritative for replaying the observed result.

## OpenAI experiment and corpus boundary

Pinned repository: `openai/math` at
`1581d4cbdd69a0faf34b2089614fe2a814316a6a`.
The pinned project's Lean toolchain is **4.34.1**, not the observed remote 4.34.0.

A freshly repeated traversal of all 23 `lean/OAI` domain subtrees reported
**122,458 Lean files, totaling 1,571,301,358 source bytes**. Every subtree response
was untruncated. `openai-inventory-observation.json` preserves the counts and
subtree identities. This is metadata, **not** a theorem count, full content
acquisition, build, export or translation result. Actual theorem counts remain
unknown while required modules are unenumerated. v2 enumeration currently covers
theorem constants, not proof-valued definitions or unformalized manuscripts.

Separately, `OAI.ComplexCancellation.BezoutFrame.exists_frame` compiled and exported
with its proof body unchanged but imports adapted to minimal Mathlib modules on
4.34.0. The result contained **7,008 shared expression nodes and 1,511 typed steps,
with 11 explicitly capped branches**. Its 151,278-byte compressed record exceeded
the connector's practical response transport; the complete record was not retained
locally. The measured summary is saved in `bezout-adapted-observation.json`.
This is **not** exact pinned-project replay, all-judgement checking, or completed
English translation. The adapted attempt with `import Mathlib` failed because a
cached dependency was missing; the minimal-import attempt succeeded.

A lightweight isolated probe also compiled the new inventory command definitions
and enumerated exactly two test theorems. It used a stub exporter and is explicitly
recorded as **inventory-only**, not an integrated typed pipeline pass. Failed
manual compressed-input transport attempts are not counted as Lean tests.

## What the release still needs

First run native 4.34.1 integration without skips, then retain and check complete
large proofs in their exact environments. Extend recursor/case/induction handling
and lemma-statement expansion; publish every explanation gap. Run the full corpus
in bounded shards, retaining failures and unknown theorem denominators. Finally,
measure mathematician comprehension and formalize the English interpretation.

The reader presently reduces Lean syntax on the supported examples. Whether it
reduces review time on advanced mathematical proofs remains an empirical question.
`checked_english_proofs` remains **0**; the whole-corpus English gate remains false.

## Reproduce

```sh
python -m pip install '.[dev,webtest]'
python -m playwright install chromium
python scripts/build_demo.py
python scripts/build_typed_demo.py
python -m pytest -q --junitxml=artifacts/local-rerun.xml
python -m proofreader kernel-demo -o reader.html
```

On a trusted Lean runner:

```sh
PROOFREADER_REQUIRE_LEAN=1 python -m pytest \
  tests/test_lean_integration.py tests/test_kernel_integration.py -q
```

All artifacts, tests, pipeline code and the supervisor handoff are included in the
source archive. `scripts/publish.sh` creates the repository using the user's own
authenticated GitHub CLI, privately by default. No existing remote was modified.
