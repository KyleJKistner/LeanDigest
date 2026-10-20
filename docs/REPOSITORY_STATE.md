# Repository state

This inventory was read on 2026-10-20, after `git fetch origin`, from the Git
remote and the GitHub pull-request, release and Actions listings. Counts are
relative to 04df977, the head of the consolidation branch
`claude/keen-archimedes-ihorkq` when this page was written. No branch, pull
request, release or artifact was changed. The recommendations are proposals
for the repository owner.

## Consolidation branch

`claude/keen-archimedes-ihorkq` is built in three steps:

1. The PR #8 branch, `work/completion-evidence-retries`, through 423e4e4. Its
   history contains `main` at 01dfd1e.
2. Merge 2d5c837 of `work/proof-document-20261019` at 85d19cc, the PR #10 head.
   That head contains the stack of PRs #5, #6, #7 and #9 and the
   `work/editorial-style-20261019` branch.
3. Commit 04df977, which adds the corpus reading measurements.

The PR #8 branch has 19 further commits that this branch does not contain.

## Pull requests

GitHub reports a pull request as merged when its head is merged into its base.
"Contained" below means that the head commit is an ancestor of 04df977.

| PR | State | Head → base | Head | Contained | Relationship to this branch | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| #1 | Merged 2026-10-15 | `work/realization-v0.4` → `main` | 19bdbd4 | No | It landed on `main` as 76f95d2, whose tree is identical to 19bdbd4. The branch commits are not ancestors. | None. |
| #2 | Merged 2026-10-17 | `work/all-findings-delivery` → `main` | 206120c | Yes | Merge e180315 on `main`. | None. |
| #3 | Merged 2026-10-17 | `work/breadth-recovery` → `main` | 1809a78 | Yes | Merge e5b0685 on `main`. | None. |
| #4 | Merged 2026-10-19 | `work/original-project-evidence` → `work/full-original-project` | 9d32ccc | Yes | Merge 5b9ea6e on the base branch. | None. |
| #5 | Open draft | `work/swarm-reader-completion-20261018` → `main` | d6a0cb4 | Yes | Part of merge 2d5c837. | Leave open until this branch reaches `main`; GitHub then normally reports it as merged. |
| #6 | Open draft | `work/checked-text-boundary-20261019` → `work/swarm-reader-completion-20261018` | 5c20704 | Yes | Part of merge 2d5c837. | After this branch reaches `main`, close it as included in the consolidation merge. |
| #7 | Open draft | `work/source-bound-cancellation-20261019` → `work/editorial-style-20261019` | 0742966 | Yes | Part of merge 2d5c837. | As for #6. |
| #8 | Open draft | `work/completion-evidence-retries` → `work/full-original-project` | efc679d | No, 19 commits ahead | This branch contains it through 423e4e4. The later commits change `completion-delivery.yml`, `completion-recovery.yml`, `completion-resume.yml` and `publish-completion.yml`, add `atomic-completion-worker.yml`, and add proof-attempt reconciliation and stopped-module retries. | Keep open. Merge its remaining commits into this branch after the recovery work finishes, then check moved workflow files (see below). |
| #9 | Open draft | `work/source-bound-equations-20261019` → `work/source-bound-cancellation-20261019` | 84fa7ff | Yes | Part of merge 2d5c837. | As for #6. |
| #10 | Open draft | `work/proof-document-20261019` → `work/source-bound-equations-20261019` | 85d19cc | Yes | Second parent of merge 2d5c837. | As for #6. |

### PR #8 activity

On 2026-10-20 the Actions listing showed the following PR #8 activity:

- Recovery run 39315174445 (`completion-recovery.yml`), started on 2026-10-19
  at 19:56 UTC, concluded with failure on 2026-10-20 at 03:50 UTC.
- Later recovery runs 39354572756 and 39356533826 concluded with failure.
- Publication run 39356177518 (`publish-completion.yml`) succeeded. It created
  release `leanglish-original-project-2149131`, tagged at 2149131.

When PR #8 is merged here, check moved workflow files:

```sh
git diff --name-status -M ORIG_HEAD HEAD -- .github
```

None of the files moved to `.github/workflow-archive/` changed on the PR #8
branch after 423e4e4. The five completion workflows it does change remain in
`.github/workflows/` (see `.github/workflow-archive/README.md`).

## Remote branches

"Ahead" counts commits on the branch that are not in 04df977. "Behind" counts
commits in 04df977 that are not on the branch. "After merge" means after this
consolidation branch is merged into `main`. "Content check" compares, for
every file the branch changed since its merge base with 04df977, the branch's
version with the versions in the history of 04df977.

| Branch | Tip | Contained | Ahead | Behind | Relationship and content check | Recommendation |
| --- | --- | --- | ---: | ---: | --- | --- |
| `claude/keen-archimedes-ihorkq` | 04df977 | Yes (equal) | 0 | 0 | The consolidation branch. | Keep. |
| `main` | 01dfd1e | Yes | 0 | 70 | Default branch. | Keep. |
| `work/completion-evidence-retries` | efc679d | No | 19 | 22 | PR #8 head. | Keep. |
| `release/validated-2149131` | 2149131 | No | 5 | 22 | Its five commits are on the PR #8 branch. Release `leanglish-original-project-2149131` is tagged at 2149131. | Keep until PR #8 is resolved. The tag preserves the commit if the branch is later deleted. |
| `work/full-original-project` | 5b9ea6e | No | 1 | 61 | The one commit is the PR #4 merge; its tree is identical to 9d32ccc, which is contained. Base of PR #8. | Keep while PR #8 is open. |
| `work/swarm-reader-completion-20261018` | d6a0cb4 | Yes | 0 | 69 | PR #5 head; base of PR #6. | Delete after PRs #5 and #6 are closed. |
| `work/checked-text-boundary-20261019` | 5c20704 | Yes | 0 | 65 | PR #6 head. | Delete after PR #6 is closed. |
| `work/editorial-style-20261019` | 8bcf420 | Yes | 0 | 63 | No pull request of its own; base of PR #7. | Delete after PR #7 is closed. |
| `work/source-bound-cancellation-20261019` | 0742966 | Yes | 0 | 59 | PR #7 head; base of PR #9. | Delete after PRs #7 and #9 are closed. |
| `work/source-bound-equations-20261019` | 84fa7ff | Yes | 0 | 54 | PR #9 head; base of PR #10. | Delete after PRs #9 and #10 are closed. |
| `work/proof-document-20261019` | 85d19cc | Yes | 0 | 50 | PR #10 head. | Delete after PR #10 is closed. |
| `work/presentation-ir-20261020` | 85d19cc | Yes | 0 | 50 | Same commit as the PR #10 head; no pull request and no unique commits. | Keep until its owner confirms it is unused, then delete. |
| `work/finding-catalog` | 45a0e83 | Yes | 0 | 81 | Branch of the archived finding workflows. | Delete after merge. |
| `work/all-findings-delivery` | 206120c | Yes | 0 | 75 | PR #2 head. | Delete after merge. |
| `work/breadth-recovery` | 1809a78 | Yes | 0 | 72 | PR #3 head. | Delete after merge. |
| `work/original-project-evidence` | 9d32ccc | Yes | 0 | 61 | PR #4 head. | Delete after merge. |
| `work/realization-v0.4` | 19bdbd4 | No | 23 | 96 | PR #1 head. Its tree is identical to 76f95d2 on `main`. | Superseded. Delete after merge. |
| `work/batch-integration` | 163374f | No | 20 | 96 | An ancestor of `work/realization-v0.4`. Every other changed file has its branch version in the history of 04df977. The seven staging workflows it adds were dropped by merge 4fd28f7. | Superseded. Delete after merge. |
| `work/narrative-batch` | bbf6df7 | No | 11 | 96 | An ancestor of `work/realization-v0.4`. | Superseded. Delete after merge. |
| `work/openai-slice` | d89a170 | No | 8 | 96 | Shares six commits with `work/realization-v0.4`. Its two other commits add pinned-slice acceptance and the run 38767243074 outputs. The outputs are identical in 04df977. The acceptance code is present in a different version, introduced by 76f95d2. | Superseded. Delete after merge. |
| `work/leanglish-branding` | 3192b30 | No | 2 | 97 | Every changed file except staging workflow `stage-leanglish.yml` has its branch version in the history of 04df977. The name change landed as 3cd6269. | Superseded. Delete after merge. |
| `import/recover-v0.3.0` | 86e9fc5 | No | 5 | 102 | Transport branch for the v0.3.0 import. Every changed file except three import workflows and `.snapshot-import/recovery.json` has its branch version in the history of 04df977, through import commit 3091033. | Superseded. Delete after merge. |
| `import/breadth-code-v041` | 56bf4be | No | 1 | 73 | Transport branch: base64 parts under `.transport/` and an import workflow. The breadth code landed as 1809a78. The payload was not decoded for this check. | Superseded. Delete after merge. |
| `import/original-evidence-io` | 48eade9 | No | 2 | 62 | Transport branch: base64 parts under `transfer/` and a transfer workflow. Its tree removes the rest of the repository. The next commit after its merge base on `work/original-project-evidence` is 9d32ccc. The payload was not decoded for this check. | Probably superseded. Decode and compare with 9d32ccc, then delete. |
| `dev/native-and-corpus` | 65dfc8e | No | 12 | 97 | Work from 2026-10-14 and 2026-10-15. Three of its 29 changed files are identical in 04df977: `proofreader/layout.py`, `docs/LAYOUT_CHECK.md` and `artifacts/v0.3/Narrative.lean`, which PR #5 imported. The others differ, and eight are absent, including `lean/ProofReader/Breadth.lean`, `scripts/index_full_openai.py` and `tests/test_english_scopes.py`. | Keep. Review the absent files before deleting. |

## Releases

| Tag | Commit | Contained |
| --- | --- | --- |
| `leanglish-research-preview-2026-10-15` | 76f95d2 | Yes |
| `leanglish-all-findings-v0.4.0` | e180315 | Yes |
| `leanglish-all-findings-v0.4.1` | e5b0685 | Yes |
| `leanglish-original-project-317dc31` | 317dc31 | Yes |
| `leanglish-original-project-2149131` | 2149131 | No (PR #8) |

The reading-measurement corpus is a release asset of
`leanglish-original-project-317dc31` (see `benchmarks/reading-kpis/README.md`).

## Artifact expiry

Kept workflows download artifacts of earlier runs by ID. Actions artifacts
expire, and a workflow fails when an input it downloads has expired. This table
was refreshed on 2026-10-20 at about 07:00 UTC from read-only Actions API
listings, against the consolidation branch at 4c072f1. It lists the artifacts
that kept workflows download and one that a kept script reads.
docs/INPUT_PRESERVATION.md also lists inputs that only archived workflows use.

| Artifact | Run | Expires (UTC) | Downloaded by |
| --- | --- | --- | --- |
| `cancellation-env-a` (12202194378) | 39285448721 | 2026-10-20 16:27 | No kept workflow. The optional `--retained-environment` input of `scripts/check_source_cancellation.py`. |
| `checkpoint-142c3d0f555a25666bb36dd1-1` (12217614568) | 39315174445 | 2026-11-02 20:14 | `completion-resume.yml` |
| `complete-openai-lean-source` (12012738377) | 38822475057 | 2026-11-14 23:16 | `all-findings-release.yml`, `atomic-completion-worker.yml`, `breadth-release.yml`, `completion-delivery.yml`, `completion-resume.yml`, `completion-worker.yml`, `dependency-cone.yml` |
| `finding-statement-retry-*` (12107274354, 12108605282) | 39050823104 | 2026-11-16 16:52 and 17:06 | `all-findings-release.yml`, `breadth-release.yml`, `completion-delivery.yml` |
| `leanglish-all-finding-observations` (12107445952) | 39049596449 | 2027-01-15 16:29 | `all-findings-release.yml`, `breadth-release.yml`, `completion-delivery.yml` |
| `finding-proof-retry-*` (16 artifacts) | 39065371645 | 2027-01-15 20:07 | `all-findings-release.yml`, `breadth-release.yml` |
| `leanglish-breadth-observations` (12116428595) | 39076207515 | 2027-01-15 22:43 | `breadth-release.yml` |
| `original-nanoda-toolchain` (12152481984) | 39170206904 | 2027-01-16 21:58 | `atomic-completion-worker.yml`, `completion-resume.yml`, `completion-worker.yml` |
| `completed-original-campaigns` (12195158110) | 39270771889 | 2027-01-17 14:38 | `completion-delivery.yml` |
| `validated-completion-plan` (12197582957) | 39276345053 | 2027-01-17 15:15 | `completion-delivery.yml`, `completion-recovery.yml`, `completion-resume.yml` |
| `completion-result-*` (74 and 1 artifacts) | 39315174445 and 39321225048 | 2027-01-17 19:56 and 20:40 | `completion-delivery.yml` (through `scripts/collect_completion_results.py`), `completion-recovery.yml` (run 39315174445 only) |
| `completion-reading-delivery` (12234627856) | 39353736010 | 2027-01-18 01:29 | `publish-completion.yml` |

Among the inputs that kept workflows download, the checkpoint expires first.
`completion-worker.yml` produced it in recovery run 39315174445 and keeps
checkpoints for 14 days. All 294 artifacts of run 39315174445 and all 5 of run
39321225048 were listed; every `completion-result-*` artifact of the two runs
expires on 2027-01-17. `publish-completion.yml` now pins delivery artifact
12234627856 of run 39353736010. The acceptance run 38792262410 artifacts cited
by docs/MATHEMATICIAN_PREVIEW.md expire on 2027-01-13.

After 2026-11-02, a run of `completion-resume.yml` fails at the checkpoint
check. After 2026-11-14, a push to `main` that matches the path filters of
`all-findings-release.yml` or `breadth-release.yml` fails at the source
download unless that input is preserved and the workflows are repinned.
docs/INPUT_PRESERVATION.md describes the dispatch-only
`preserve-inputs.yml`, which copies these inputs into new 90-day artifacts, and
the alternative of release assets. It also describes the consumer edits, which
`scripts/preserve_inputs.py repin` prints. Neither option has been carried out.
