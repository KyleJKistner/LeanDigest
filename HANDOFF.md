# Leanglish all-findings checkpoint — 0.4.0

## Goal and current product

The user wants every OpenAI finding with full Lean documentation accessible to
mathematicians. Do not restart with another toy example or rename the repository.
The product is Leanglish, repository KyleJKistner/LeanDigest, legacy proofreader
package and formats retained. All new catalog commands use `leanglish`.

The finding catalog is generated from the pinned upstream scope notes and
comparison configurations, not from the subset of successful proof extractions.
See docs/ALL_FINDINGS.md and scripts/assemble_finding_release.py.

Frozen catalog coverage: 372 total findings, all 242 documented findings, all 416
comparison configurations, all 602 statement entries, 601 distinct formal targets
(536 theorem targets and 65 definition references), 413 direct solution modules.
The frozen proof inventory contains 109 readings from 4,090 checked frames,
including all 28 formerly failed extractions. There are 1,357 explicit explanation
gaps. 56 findings have any reading; 41 have readings for every listed theorem target.
These counts do not establish fully explained or certified English proofs.

## Exact inputs

Upstream commit: 1581d4cbdd69a0faf34b2089614fe2a814316a6a.
Source archive SHA256: 7f596ba4fe17fe0d7d55655e6e82d99d4d87181e0a9032721c048d7385163f3c.
All 123,565 source files in the Lean-directory inventory were locally verified.
The 122,458 OAI-file number from old turns has a narrower scope; do not mix them.

GitHub Actions input runs:
- 38822475057: complete-openai-lean-source.
- 39049596449: leanglish-all-finding-observations, containing original catalog,
  four statement shards and sixteen proof shards.
- 39050823104: both previously timed-out statement configurations recovered.
- 39065371645: all 28 extraction-failed proof targets recovered, 16 shards,
  exact application commit 375219a70949f3d3e3e698bd53ad2788de132cab.

The statements come from comparison specifications with placeholders. They are
NOT solution-proof observations. Proof snapshots have separate receipts, native
run logs, original source hashes, driver hashes and checked source-proof paths.
The catalog verifies consistency, not authenticity of unsigned observations.

## Native exporter repair already completed

Commit 0140dd37f1aa86fe45a06d0e9945283a461effc7 preserves the declared root type
(with definitional-equality and kernel checks) and alpha-renames shadowing local
binders before pretty-printing. Required native regression tests and repeat
extraction passed. All 28 real failures were then recovered. Do not weaken the
snapshot validator or repeat the previous declared-type/context problem.

Native Lean 4.34.1 runs in GitHub Actions. The local chat container lacks Lean and
outbound networking; this is not a blocker to native CI. Binary workflow artifacts
are downloaded with the GitHub artifact action and mounted automatically. Do not
revert to manually copying enormous base64 outputs or pretend independent coding
agents ran. Parallel GitHub jobs are native test workers, not AI agents.

## Active breadth work

Run 39067324637, commit 2a1f9a195b530d64682140516050c2be3bd18ffb, processes the
remaining 427 theorem targets (54 previous build timeouts plus 373 not attempted)
in 64 bounded shards, at most 16 concurrently. Each original module is built once
per shard. All failed, timed-out and unattempted targets remain in its output.
Inspect actual job/artifact results before reporting progress. This run does not
increase the frozen 109-reading release until its records are reconciled.

The workflow is .github/workflows/finding-proofs-remaining.yml and artifacts are
finding-proof-remaining-0 through -63. Some jobs may need larger build budgets or
unavailable original-project dependencies; do not omit them or claim completion.

## Catalog code and checks

- proofreader/catalog_inputs.py: frozen universe, source/provenance consistency.
- proofreader/finding_catalog.py and catalog_web/: offline finding/statement pages.
- proofreader/catalog_audit.py: every local file link and source-line anchor.
- scripts/assemble_finding_release.py: deterministic source-verified assembly.
- scripts/audit_finding_browser.py: actual offline file navigation in CI.
- tests/test_finding_catalog.py: hostile inputs and coverage/receipt regressions.

Local browser-admin policy blocks navigation; --document-harness is an explicitly
labelled local test route, not evidence of real offline file navigation. Public
packaging requires the real-file CI audit and an unchanged committed source tree.
The two different PYTHONHASHSEED catalog builds were byte-identical across 3,733
files after deterministic declaration-name ordering was fixed.

## Release gate and next steps

1. Run all-findings-release.yml and ordinary/native CI on the exact committed
   catalog source. Require real file navigation, no external resource requests,
   complete link inventory, and zero font files. Inspect resulting artifact.
2. Merge only after those checks pass. The main-only publication job creates the
   immutable prerelease leanglish-all-findings-v0.4.0; it does not overwrite one.
   Check the actual release before claiming publication.
3. Reconcile all 64 remaining-proof shards, integrate newly checked readings,
   diagnose remaining failures, and preserve every denominator and attempt.
4. Improve the large automation traces with mathematically meaningful checked
   summaries. Never replace explanation gaps with plausible invented prose.
5. The full original Lake project, its compatibility patches and Comparator,
   formally verified English semantics, and human comprehension study remain open.

An optional Vercel plugin connection was suggested on October 17 for a live URL.
It was not connected or deployed. Do not repeat the suggestion or claim a live
website. Offline artifacts and GitHub Releases do not depend on that connection.
