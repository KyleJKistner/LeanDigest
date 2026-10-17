# Verified release checkpoint: Leanglish 0.4.1

This supplements HANDOFF.md with the final observations from the breadth release.
Do not rebuild the old 109-reading baseline or repeat the import-transport work.

## Published application and offline catalog

- PR #3 merged into main as `e5b0685466cf99d49c687b170200e69e1e3c427e`.
- Application tree: `a0c251d5cce18c6bd488d711d9b8d87dc0799ceb`.
- Release: https://github.com/KyleJKistner/LeanDigest/releases/tag/leanglish-all-findings-v0.4.1
- Release ID 416131502; this is a prerelease, not a production-completeness claim.
- Successful publication run: 39079463255. Both build and publish passed.
- Successful source-head CI: 39078995638; successful merged-main CI: 39079463290.
- All eight mandatory native integration tests passed with zero skips on the source head. Both native and Python/browser jobs also passed after merge.
- Local non-native test run: 506 passed. Native execution was in GitHub Actions, not the local container.
- Published delivery artifact: 12117969456, SHA-256 `42ebef5d46f53c70116d252c01b417ae2c4f0ff920218dd12b6386c3cc44cca8`.
- Published offline ZIP SHA-256: `1cc4f4cc5728095fb0e024f85c7fe53b80fc4e12e1525499b2ce3965b4fdd637`.
- Published application ZIP SHA-256: `785cc0fe54472269045eda250710da58d28e097faf3f7e3fa1eef039b6e173b5`.
- Downloaded bytes matched the published release asset digests. All 4,809 catalog manifest entries and 52 application source hashes were verified.
- Real offline file-navigation browser audit passed: filtering, search, progress, finding/proof/source navigation, MathML, no mobile overflow, external requests or page errors.
- Static audit: 1,004 HTML pages, 6,715 local links, 95,025 anchors, zero errors and zero font files.

## Exact frozen release coverage

Upstream pin: `1581d4cbdd69a0faf34b2089614fe2a814316a6a`.

- 372 catalog findings; all 242 with Lean scope documentation accessible.
- All 602 comparison-statement entries and 416 configurations accessible.
- 413 directly referenced original solution-source modules accessible.
- 536 distinct theorem targets plus 65 definition references.
- 216 retained source-bound theorem readings, across 128 findings.
- 90 findings have a reading for every listed theorem target.
- 9,272 selected checked frames; 3,005 explicit explanation gaps.
- 320 theorem targets still lack a reading in this release.
- On the same 216 snapshots, the prior renderer had 3,242 gaps: guarded conjunction elimination removed 237 across 70 readings.

The full Lean-directory source inventory was retained and checked: 123,565 files, no missing or extra files, all SHA-256 hashes matched. This source acquisition is not a full project build.

Statements are not solution proofs. Reading coverage is not complete exposition. Saved observations are unsigned. English and pretty-printing are not formally verified. The full original Lake project and Comparator were not executed. Named dependencies may remain unexpanded.

## Frozen breadth input versus ongoing jobs

Release 0.4.1 uses collection run 39076207515 / artifact 12116428595, sourced from native run 39067324637 and previous repaired proofs. It intentionally freezes 36 retained shard reports, 223 recorded targets and 107 new readings. Missing reports for 204 selected targets remain explicit. Do not silently replace this snapshot while retaining the same release identity or claim unretained job results.

The larger run had not completed at its last observation. Retrieve current metadata and any additional artifacts before counting more results. Do not restart the entire 64-worker run indiscriminately.

## Additional validated recovery, NOT in the 216-reading release

Focused run 39078995651, TreewidthL1 job 117531924551, succeeded. Artifact 12118476174 (`finding-proof-budget-TreewidthL1`), SHA-256 `bcc23d8eb3648076624ca8c4a3c877a1f2fa137a75b1384cbdfd3e6fd93051de`, was downloaded and validated through `catalog_inputs.load_proofs` and `check_reading` against the unchanged upstream source.

- Module: `OAI.Combinatorics.TreewidthL1.Main`.
- Theorem: `OAI.BoundedTreewidthL1.main_theorem`.
- 220 checked frames, no traversal budget cuts, 31 explicit explanation gaps.
- Snapshot SHA-256: `7a1fa8a98afc7f2f7ce8fad9519fd7b741b2e9750c9277a53394193a308e353b`.
- Successful retry limits: build 1,500 seconds; extraction 900 seconds; maxHeartbeats 2,000,000; worker wall budget 2,400 seconds.
- Original source hash, executed driver, saved compiler output, receipt and reading bindings agree. These observations are not authenticated attestations.
- The RotationWeights job in the same run was still in progress at the last check.

Next integrate this recovery and newly retained breadth shards under a new explicitly versioned input identity. Keep all 536 theorem targets in the ledger. The priority remains complete finding-level reading access, followed by reducing automation/dependency explanation gaps; do not stop at the current release.
