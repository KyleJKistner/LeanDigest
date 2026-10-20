# Original-project completion

This document supersedes the 216-reading checkpoint at the top of HANDOFF.md for
the original-project workstream. It does not supersede the separate reader and
controlled-language work. Do not restart completed campaigns or change their
source pins.

## Published catalog

Release: https://github.com/KyleJKistner/LeanDigest/releases/tag/leanglish-original-project-317dc31

Application commit: `317dc31dddd3b34a1eb56aabb786da1fa8465450`.
Upstream commit: `1581d4cbdd69a0faf34b2089614fe2a814316a6a`.
Lean version: 4.34.1. The original environment has 42 audited dependencies.

The offline package was generated from the full preserved finding inventory and
independently validated retained proof observations. Extract
`leanglish-all-findings.zip` and open `Leanglish/index.html`.

| Item | Published result |
| --- | ---: |
| Documented findings accessible | 242 / 242 |
| Formal statement entries accessible | 602 / 602 |
| Theorem readings | 492 / 536 |
| Original comparison configurations passed | 341 / 416 |
| Original libraries built | 15 / 25 |
| Findings with at least one reading | 226 |
| Findings with all listed theorem readings | 219 |
| Selected checked judgements | 22,452 |
| Explicit explanation gaps | 7,587 |
| Site-manifest entries checked | 8,360 |

These are separate measures. A formal specification containing placeholders is
not a solution proof. An accessible reading is not necessarily a complete
explanation. Earlier receipts retain their recorded execution environments.
English semantics and observation authenticity are not certified.

Offline ZIP SHA-256:
`57f9e481a83ff64b7ae01e9cdf0b4b47919adf1899d28313ab3b7e7cf5be0e2b`.
Published summary SHA-256:
`927998e8e2f672da46bb6eb0fbb91f49b20d064cc7d0bd2dcfa5e345e0b3509e`.

Delivery run `39316344259` passed actual offline file-navigation, source/receipt
checks, all local-link audits and packaging. Python/browser and native Lean CI
passed on application commit 317dc31. Publication run `39317701378` separately
verified the delivery run, source CI, downloaded artifact and every site-manifest
entry before creating the prerelease. The release was not pushed to main and no
existing release was overwritten.

## Active recovery

Draft PR: https://github.com/KyleJKistner/LeanDigest/pull/8
Target branch: `work/full-original-project`.
This workstream branch: `work/completion-evidence-retries`.

Native run: https://github.com/KyleJKistner/LeanDigest/actions/runs/39315174445
Frozen native application head:
`4f9c1e823dd65023cfa7d8b9afe5e08390b8d2ad`.

The exact remaining complement contains 44 theorem readings, 75 comparison
configurations and 10 original library builds. There are 74 module jobs and 10
library jobs, with at most 12 modules and 3 libraries running concurrently.
Opening PR #8 started the matrix. Subsequent assembly commits do not restart it.
Do not relabel its source commit as the current branch head.

As observed on 2026-10-19 at approximately 20:15 UTC, the first 15 workers had all
uploaded their first build checkpoints and continued from those builds. No new
proof acceptance is inferred from those checkpoints. Check the actual current
run before reporting additional completed work.

Each worker retains bounded build rounds and cumulative compiled deltas. A
checkpoint is a performance input, never a proof receipt. Final verification
executes the original library build, original Comparator configuration, or
source-bound proof extraction separately. Original source files, dependency pins
and approved patches are audited before and after execution.

The cold-restore workflow tests a real NuclearUltrapower checkpoint in a fresh
runner. Its result must be checked independently; creating the test workflow
does not establish that restoration succeeded.

## Inputs that must remain bound

Completed initial-campaign evidence:
- Run `39270771889`, artifact `12195158110`, `completed-original-campaigns`.
- SHA-256 `4275b3fabc03eca1a4b7daa7a30121bf6b81ef1849f36f1a3392b755ad7cb5df`.

Validated recovery plan:
- Run `39276345053`, artifact `12197582957`, `validated-completion-plan`.
- SHA-256 `8164869bdd4972b89c7481be210ab559493017cdf9c563e834f65362f36b4d6a`.
- Plan digest `e91fbdf3bdb75bf5dd2dc105798a8512dd5f695f2ffdcad416e3eca0ff7c7d9c`.

Published delivery input:
- Run `39316344259`, artifact `12217842952`, `completion-reading-delivery`.
- SHA-256 `919003d51135808245dae1459fc6a09ce05b9727cb24be802bc244d61d87687b`.

The complete unchanged source is retained in run `38822475057`, artifact
`complete-openai-lean-source`. `scripts.assemble_finding_release.unpack_source`
checks its archive digest and all 123,565 source-inventory entries. Do not replace
it with a reduced Lake project.

## Collecting further results

`scripts/collect_completion_results.py` requires an explicit run, source head and
recovery plan. It freezes a stable artifact inventory at one cutoff and retains
only final result reports and the original recovery plan, not compiled caches.
Each archive is digest-checked and every extracted file is compared to its ZIP.

`scripts/assemble_completion_readings.py` revalidates the full old baseline, its
original attempts and the exact recovery complement. It then calls the existing
native report and proof-loader validators before adding any result. All preceding
failed attempts remain in the ledger. A missing report never shrinks the
536-theorem or 416-configuration denominator.

Generate future delivery in a fresh directory. Use a new release tag for a newly
validated catalog; never overwrite the published checkpoint. A resumed compiler
worker and a successful artifact download do not, by themselves, add a theorem.

## Remaining acceptance criteria

The original-project milestone requires all 25 libraries, all 416 original
comparison configurations and all 536 documented theorem readings. Exposition
coverage, faithful English semantics and human readability remain separate
acceptance criteria even after those three counts are complete.

Do not merge or modify the other session's reader/controlled-language branch as
part of this workstream. Native GitHub jobs are compilation and verification
workers, not independent AI coding agents.
