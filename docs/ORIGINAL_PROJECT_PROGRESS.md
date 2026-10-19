# Original-project verification and retained-output recovery

This workstream changes corpus evidence, verification-tool preflight and I/O, not
mathematical exposition rules or the original OpenAI project. The pinned source
is still `1581d4cbdd69a0faf34b2089614fe2a814316a6a`.

## Frozen native observations

Collector commit `36d1a72a18fb70eae37cd2c2926f0a1ad3d9bf0c`, run
39165245813, retained artifact 12150168878. Archive SHA-256:
`ca0353d174eceb0e9723f7947abfd43f75e9e20448458f075fcdba6d5ebc6fa5`.
The cutoff is 2026-10-18T20:52:16Z; later results are deliberately not implied.

The source and frozen artifacts were independently checked and reconciled:

- 441 original verification obligations: 25 library builds and 416 configurations.
- 125 retained outcomes: 6 library passes, 97 Comparator passes, 21 timeouts, and
  one failed configuration that could not find the required Nanoda binary.
- 316 obligations have no retained outcome in this collection.
- 323 baseline proof readings plus 64 newly retained original-environment readings.
- All 536 documented theorem targets remain in the proof ledger. Missing worker
  output is not counted as a failed theorem or silently omitted.
- Original-environment observations retain audits of all 42 dependencies and all
  23 approved compatibility patches. Earlier baseline observations keep their
  own narrower execution scope.

These are unsigned observations. The comparator's documentation describes
additional operating-system isolation assumptions; this release does not certify
adversarial sandbox security. Definitions filled into specification holes still
require mathematical-intent review. English semantics are not formally verified.

## Recovered output, without a new compiler run

The original native extraction of
`OAI.CKSSourceExterior.area_controlled_end_replacement` completed successfully,
but its 37,431,449-byte stdout exceeded the old Python input gate. Its 264 proof
frames satisfy the unchanged snapshot validator. A bounded output gate (64 MB)
and local immutable-string deduplication recover it; source input stays at 16 MB.
Mutable frames and contexts are not shared, and individual formula, frame-count,
scope, source-path and mathematical certificate guards remain unchanged.

`proofreader.retained_output.recover` requires matching original source bytes,
the complete before/after environment audits, original outcome hash, exact current
exporter driver, actual native exit zero, preserved compiler stdout, and the
specific previous output-budget error. It does not treat arbitrary old errors as
success. The normal catalog proof-loader verifies the recovered observation again.

Recovered snapshot SHA-256:
`d34561eb108e37217a094b47891d63c9e47eefd44293530e45d82915d37b5185`.
This makes 388 available readings, including 65 with the full original-environment
audit in this campaign. The other 148 targets remain outstanding. Reprocessing
is explicitly distinguished from running Lean again.

## Delivery and focused verification work

`original-reading-delivery.yml` rebuilds the expanded offline catalog from frozen
inputs, requires actual file-navigation browser checks and links every original
build/configuration obligation to its status. It does not rerun the active corpus
campaign or alter its evidence. Publication is a separate explicit action.

`original-nanoda-recovery.yml` builds the external checker at
`f67473ba5f9397266f89c7852082c9c914b5d219`, requires acceptance and disallowed-axiom
rejection controls, and retries only the diagnosed ArtinParabolicIntersections
configuration with its original `enable_nanoda: true` unchanged. A successful
built-in kernel result cannot substitute for the requested external-kernel pass.
The workflow runs on a PR to the full-project branch so that the audited shared
dependency cache is visible. Do not count the retry before inspecting its result.

## Resume

Keep original runs 39141760623 and 39144564607 undisturbed. Retrieve a new explicitly
versioned collection when more workers finish; never replace the frozen artifacts
while retaining their old hashes. Final completion requires all original build and
comparison obligations, all 536 readings, and separate explanation-quality work.
