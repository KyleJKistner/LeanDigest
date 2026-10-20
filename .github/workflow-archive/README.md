# Archived one-shot workflows

GitHub Actions runs workflow files only from `.github/workflows/`. The files in
this directory were moved with `git mv` and are byte-for-byte the last committed
versions, so each recorded run can be read against the job definition that
produced it. Nothing in this directory runs.

A workflow was archived when all of the following held:

- Its push or pull-request trigger names a finished work branch, or its jobs
  download fixed earlier run and artifact IDs.
- Its run is recorded below.
- No kept workflow, test or module reads the file path.

Archiving does not delete any run, artifact, release or branch. Recorded
artifacts stay in Actions until they expire; see
[Artifact expiry](../../docs/REPOSITORY_STATE.md#artifact-expiry).

## Sources

Run IDs, events, conclusions and head commits come from the GitHub Actions run
listing for each file, read on 2026-10-20. Every archived file has exactly the
runs listed. A `failure` conclusion means at least one job failed. Several of
those runs deliberately retained partial outputs that later workflows reconciled.
The **Cited in** column lists tracked files outside this directory that name the
run, one of its artifacts, or the workflow file. It was regenerated on
2026-10-20, after merge f787dae, by searching every tracked text file for each
run ID, for the ID of every artifact that the Actions artifact listing reports
for those runs, and for the file name. Kept workflows are in
`.github/workflows/`. Archived consumers are named by file only.

## Archived files

| File | What it did | Bound to | Recorded runs | Cited in / consumed by |
| --- | --- | --- | --- | --- |
| `lean-source-bundle.yml` | Fetched the pinned OpenAI Lean subtree without executing it, checked every byte against the pinned Git tree, and uploaded `complete-openai-lean-source`. | push to `work/finding-catalog` | 38822475057 (success, af04fe9) | HANDOFF.md; docs/COMPLETION_RECOVERY.md; docs/DEPENDENCY_CONE.md; docs/INPUT_PRESERVATION.md, which also names the file; docs/REPOSITORY_STATE.md; `proofreader/dependency_cone.py`; `scripts/assemble_finding_release.py`; `scripts/preserve_inputs.py`; `tests/test_dependency_cone.py`. Kept `all-findings-release.yml`, `atomic-completion-worker.yml`, `breadth-release.yml`, `completion-delivery.yml`, `completion-resume.yml`, `completion-worker.yml` and `dependency-cone.yml` download this run. The error message of `dependency-cone.yml` names the file. |
| `finding-catalog.yml` | Acquired the upstream finding manifest, comparison statements and scope notes without executing upstream code; uploaded `leanglish-finding-inputs`. | push to `work/finding-catalog` | 38822102145 (success, 7cc7ca3) | Not cited. Input to `finding-delivery.yml`. |
| `finding-statements.yml` | Elaborated every finding comparison statement in four shards, statements only, with explicit non-proof status. | push to `work/finding-catalog` | 38823693854 (failure, 6884181); 38824968518 (failure, cb789bf); 38826598594 (failure, 2b68f6a) | Not cited. 38826598594 is an input to `finding-delivery.yml`. |
| `finding-statements-retry.yml` | Retried the two timed-out statement configurations, CharacterVarietiesAllSeamsSupport and CoarseAssembly, with 20-minute build budgets. | push to `work/finding-catalog` | 39050823104 (success, 45a0e83) | HANDOFF.md; docs/INPUT_PRESERVATION.md; docs/REPOSITORY_STATE.md; `scripts/assemble_finding_release.py`; `scripts/preserve_inputs.py`; `tests/test_preserve_inputs.py`. Kept `all-findings-release.yml`, `breadth-release.yml` and `completion-delivery.yml` download this run. |
| `finding-proofs.yml` | First proof-reader attempt for every documented theorem target, in 16 shards, with failures retained. | push to `work/finding-catalog` | 38824665068 (failure, 42f7ef5) | Not cited. Input to `finding-delivery.yml`, `finding-proofs-retry.yml` and `finding-proofs-remaining.yml`. |
| `finding-delivery.yml` | Combined the frozen finding observations into `leanglish-all-finding-observations`. | push to `work/finding-catalog` | 39049596449 (success, b3f691e) | HANDOFF.md; docs/INPUT_PRESERVATION.md; docs/REPOSITORY_STATE.md; `scripts/assemble_finding_release.py`; `scripts/preserve_inputs.py`. Kept `all-findings-release.yml`, `breadth-release.yml` and `completion-delivery.yml` download this run. |
| `finding-proofs-retry.yml` | Retried the 28 extraction-failed targets with the repaired exporter, in 16 shards. | push to `work/all-findings-delivery` (PR #2, merged) | 39065371645 (success, 375219a) | HANDOFF.md; docs/INPUT_PRESERVATION.md; docs/REPOSITORY_STATE.md; `scripts/assemble_finding_release.py`; `scripts/preserve_inputs.py`, which also names its 16 retry artifacts. Kept `all-findings-release.yml` and `breadth-release.yml` download this run. |
| `finding-proofs-remaining.yml` | Processed the remaining 427 theorem targets in 64 native shards. | push to `work/all-findings-delivery` | 39067324637 (failure, 2a1f9a1) | HANDOFF.md, which names this file by its archive path; docs/RELEASE_CHECKPOINT_V0_4_1.md (36 retained shard reports); `scripts/assemble_finding_release.py`. Input to `breadth-observations.yml`. |
| `breadth-observations.yml` | Collected the repaired proofs and the surviving shard outputs of run 39067324637, without calling missing shards successful; uploaded `leanglish-breadth-observations`. | push to `work/breadth-recovery` (PR #3, merged) | 39076207515 (success, 7e80297) | HANDOFF.md; docs/INPUT_PRESERVATION.md; docs/RELEASE_CHECKPOINT_V0_4_1.md (artifact 12116428595); docs/REPOSITORY_STATE.md; `scripts/assemble_finding_release.py`; `scripts/preserve_inputs.py`. Kept `breadth-release.yml` downloads this run. |
| `proof-budget-recovery.yml` | Retried the RotationWeights and TreewidthL1 extractions with larger heartbeat and time budgets. | push to `work/breadth-recovery` | 39078995651 (success, 1809a78) | docs/RELEASE_CHECKPOINT_V0_4_1.md (job 117531924551, artifact 12118476174); HANDOFF.md, which names this file by its archive path. Input to `original-project-preflight.yml`. |
| `research-preview.yml` | Built the 14-proof mathematician preview from acceptance run 38792262410. Its `deploy-pages` job runs only for a manual dispatch on `main`; no dispatch run is listed, so that job has never run. | push to `work/realization-v0.4` (PR #1, merged) | 38810122909 (push, success, 4e7592c) | Not cited by run ID. docs/MATHEMATICIAN_PREVIEW.md and `tests/test_research_preview.py` cite input run 38792262410. The test runs in `ci.yml` and does not read this file. |
| `release-preview.yml` | Built the same preview and published prerelease `leanglish-research-preview-2026-10-15`. It exits with an error when that tag exists, so any later run fails by design. | push to `main` (preview paths) | 38810924679 (success, 76f95d2) | Not cited by run ID. The release exists, tagged at 76f95d2. |
| `original-project-preflight.yml` | Acquired the original 42-dependency project, built Landrun, Comparator and the exporter, and collected the earlier breadth outputs. | push to `work/full-original-project` | 39140071998 (failure, 6ff680c) | Not cited. Input to `original-evidence.yml`, `original-proof-campaign.yml` and `completion-evidence.yml`. |
| `full-original-project.yml` | Ran all 25 original library builds and 416 Comparator configurations, with source and patch audits. | push to `work/full-original-project` | 39141760623 (failure, f70556c) | docs/DEPENDENCY_CONE.md, which also names the file; docs/INPUT_PRESERVATION.md; docs/ORIGINAL_PROJECT_PROGRESS.md; `scripts/collect_original_evidence.py`. A comment in `proofreader/dependency_cone.py` names the file. Input to `original-proof-campaign.yml`, `original-nanoda-recovery.yml` and `completed-campaign-evidence.yml`. |
| `runtime-parts.yml` | Split the runtime artifact of run 39142929511 (kept `development-runtime.yml`) into four parts of at most 200,000,000 bytes. | push to `work/full-original-project` | 39143936177 (success, c7941be) | Not cited. |
| `original-proof-campaign.yml` | Extracted the remaining documented theorem readings in the original environment, one worker per module. | push to `work/full-original-project` | 39144564607 (failure, 3da3bc4) | docs/INPUT_PRESERVATION.md; docs/ORIGINAL_PROJECT_PROGRESS.md; `scripts/collect_original_evidence.py`. Input to `completed-campaign-evidence.yml`. |
| `original-evidence.yml` | Froze the retained original-project outcomes at a fixed cutoff without restarting workers. | push to `work/original-project-evidence` (PR #4, merged into `work/full-original-project`) | 39165245813 (success, 36d1a72) | docs/ORIGINAL_PROJECT_PROGRESS.md (artifact 12150168878). Input to `original-reading-delivery.yml`. |
| `original-reading-delivery.yml` | Rebuilt the expanded offline catalog from frozen inputs with real-browser checks. | push to `work/original-project-evidence` | 39170160666 (success, 9d32ccc) | docs/ORIGINAL_PROJECT_PROGRESS.md names the file. |
| `original-nanoda-recovery.yml` | Built the pinned Nanoda external kernel with acceptance and rejection controls, and retried the ArtinParabolicIntersections configuration. | pull request into `work/full-original-project` | 39170206904 (pull request, success, 9d32ccc) | docs/INPUT_PRESERVATION.md; docs/ORIGINAL_PROJECT_PROGRESS.md names the file; docs/REPOSITORY_STATE.md; `scripts/preserve_inputs.py`. Input to `completion-evidence.yml`. Kept `atomic-completion-worker.yml`, `completion-resume.yml` and `completion-worker.yml` download its artifact `original-nanoda-toolchain` (12152481984) by ID. |
| `completion-evidence.yml` | Froze the original-project worker outcomes at a later cutoff, including the external-kernel retry; uploaded `original-completion-evidence` (artifact 12162982446). | push to `work/completion-evidence-retries` (PR #8, open) | 39198541227 (success, d1a174c) | Not cited. Input to `completed-campaign-evidence.yml`. |
| `completed-campaign-evidence.yml` | Required runs 39141760623 and 39144564607 to be finished, then reconciled their final outcomes without running Lean again; uploaded `completed-original-campaigns`. | push to `work/completion-evidence-retries` | 39270771889 (success, 2744ca3) | docs/COMPLETION_RECOVERY.md (artifact 12195158110); docs/INPUT_PRESERVATION.md; docs/REPOSITORY_STATE.md; `scripts/preserve_inputs.py`. Kept `completion-delivery.yml` downloads that artifact. Input to `completion-plan.yml`. |
| `completion-plan.yml` | Validated retry acceptance and derived the exact remaining work; uploaded `validated-completion-plan`. | push to `work/completion-evidence-retries` | 39276345053 (success, 58fceea) | docs/COMPLETION_RECOVERY.md (artifact 12197582957); docs/INPUT_PRESERVATION.md; docs/REPOSITORY_STATE.md; `scripts/preserve_inputs.py`. Kept `completion-recovery.yml`, `completion-resume.yml` and `completion-delivery.yml` download that artifact. |
| `original-checkpoint-restore.yml` | Restored the NuclearUltrapower compilation checkpoint (artifact 12217614568 of run 39315174445) on a fresh runner and hash-checked the resulting build inventory. | `workflow_dispatch` only since 8caf5fb; earlier versions ran on PR #8 push and pull-request events | 39318853096 (push, failure, 6c6c1f7); 39319564118 (pull request, success, f693179) | docs/CHECKPOINT_RECOVERY.md (both runs; result artifact 12220215487); docs/INPUT_PRESERVATION.md (run 39319564118). Kept `completion-resume.yml` checks run 39319564118 through the API, not this file. |
| `checkpoint-progress.yml` | Compared two NuclearUltrapower checkpoints (artifacts 12217614568 and 12220293017). It is a manifest-only diagnostic that records `proof_acceptance_established: false`. | push to `work/completion-evidence-retries` | 39324873056 (success, 423e4e4) | Not cited. docs/CHECKPOINT_RECOVERY.md cites its input checkpoint. |
| `publish-completion.yml` | Required the exact successful `completion-delivery.yml` run and its delivery artifact, then created a prerelease with `scripts/publish_completion_release.py`, which refuses an existing tag. The archived version pins run 39353736010, artifact 12234627856 and tag `leanglish-original-project-2149131`. Its whole job held a `contents: write` token. | push to `work/completion-evidence-retries` (PR #8, open) when the file changes; dispatch | 39317701378 (success, 9059f92), whose version created prerelease `leanglish-original-project-317dc31`; 39355010636 (failure, 15620e9); 39356177518 (success, 39c2f64), which created prerelease `leanglish-original-project-2149131` | docs/COMPLETION_RECOVERY.md (run 39317701378); docs/INPUT_PRESERVATION.md names the file; docs/REPOSITORY_STATE.md (run 39356177518). Archived on 2026-10-20 because both of its releases exist and `scripts/publish_completion_release.py` refuses to replace a release. |

Commit 8caf5fb made `original-checkpoint-restore.yml` dispatch-only so that the
successful check could be repeated without running on every PR #8 commit. It is
archived because it is bound to fixed artifact IDs of the open recovery run, and
`main`, the default branch, does not contain it (see [Dispatch](#dispatch)).
The PR #8 branch still holds its own copy, as it does of
`publish-completion.yml`.

## Kept active

The table lists every file in `.github/workflows/`. `tests/test_workflows.py`
checks that it does and that every kept file loads with `yaml.safe_load`. It
also checks that no kept file runs on a `schedule`, `workflow_run`, `release`
or `pull_request_target` event, grants a write permission or names a secret,
and that no step runs `gh release`, `git push` or `gh workflow run`.

| File | Reason it stays in `.github/workflows/` |
| --- | --- |
| `ci.yml` | Python, browser and native Lean tests on every push and pull request. It runs `tests/test_artifact_budget.py` and `tests/test_workflows.py`, and fails when the demo build or the tests change a tracked file. |
| `reading-kpis.yml` | Re-renders the 492-snapshot corpus and fails when `benchmarks/reading-kpis/current.json` is stale. Its path filters include `leanglish/**` and `pyproject.toml`, which define the `leanglish reading-kpis` command it runs. |
| `catalog-preview.yml` | Re-renders the published catalog of `leanglish-original-project-317dc31` with the committed renderer, adds the dependency-cone pilot readings when their artifacts download with matching digests, runs the static audit and Chromium file navigation, and uploads a 30-day preview artifact. Push to `claude/keen-archimedes-ihorkq` on the listed paths, or dispatch. It never publishes. Recorded runs: 39399318913 (ab2bfb3), 39425058262 (f787dae) and 39456773394 (bbc90ac), all success. See docs/CATALOG_PREVIEW.md. |
| `dependency-cone.yml` | Bounded native pilot (8 environment modules, 151 cited lemmas) for level-1 dependency-cone readings, triggered by pushes to `claude/keen-archimedes-ihorkq` that change the workflow or `benchmarks/dependency-cone/**`; full scopes by dispatch, which has not been tried (see [Dispatch](#dispatch)). Recorded runs: 39373979494 (push, success, 4c072f1); 39456773610 (push, success, bbc90ac). See docs/DEPENDENCY_CONE.md. |
| `preserve-inputs.yml` | Dispatch-only copy of expiring pinned inputs into new 90-day artifacts. It has never run, and on 2026-10-20 the Actions workflows API returned 404 for the file. See docs/INPUT_PRESERVATION.md. |
| `all-findings-release.yml`, `breadth-release.yml` | Dispatch only. Each re-assembles the frozen inputs of release `leanglish-all-findings-v0.4.0` or `leanglish-all-findings-v0.4.1` with the application at the dispatched commit, which renders with the current printer, and runs the browser audit. `release.json` records `release_version` `rebuild-of-0.4.0` or `rebuild-of-0.4.1` and the printer versions of the readings, the packaged notes start with the same statement, and the artifacts are `leanglish-all-findings-rebuild` and `leanglish-breadth-rebuild` (30 days). A first step requires every pinned input to be listed and unexpired. Neither has a publish job: both tags exist. The earlier versions, which `main` still holds, also run on pushes to `main` and have a `main`-only publish job; recorded `main` runs are 39070872779 and 39079463266 for the first and 39079463255 for the second. They stay here rather than in this directory because `scripts/preserve_inputs.py` registers their download lines for a repin. docs/ALL_FINDINGS.md names the first file. Their inputs expire; see docs/REPOSITORY_STATE.md. |
| `acceptance.yml` | General native pinned-slice acceptance with no hard-coded run inputs. Its push trigger names `work/realization-v0.4`, the head of merged PR #1; otherwise it runs only when dispatched. |
| `development-runtime.yml` | Dispatchable packaging of the pinned Lean 4.34.1 runtime, with no hard-coded inputs. Kept for sessions without a local Lean toolchain. |
| `build-resume-validation.yml` | Native gate for `proofreader/build_resume.py`. Its push trigger names the PR #8 branch; otherwise it runs only when dispatched. |
| `checked-companion.yml`, `checked-text-boundary.yml`, `source-bound-cancellation.yml`, `source-bound-equations.yml`, `proof-document.yml` | Path-filtered pull-request gates for the certified-English research files (see docs/RESEARCH_TRACKS.md). None has run on the consolidated tree; see [Native gates](../../docs/REPOSITORY_STATE.md#native-gates). |
| `completion-recovery.yml`, `atomic-completion-worker.yml`, `completion-resume.yml`, `completion-delivery.yml` | PR #8 recovery and delivery. Merge 4c072f1 brought in the PR #8 head efc679d, so each file equals its version on the PR #8 branch. `completion-recovery.yml` calls `atomic-completion-worker.yml`. Recovery runs 39315174445, 39354572756 and 39356533826 concluded with failure; on 2026-10-20 at about 16:40 UTC no PR #8 run was queued or in progress, and PR #8 was an open draft. `proofreader/completion_results.py` records `completion-recovery.yml` and `completion-resume.yml` as the workflow identity of collected runs. |
| `completion-worker.yml` | No workflow calls it at this commit. `completion-recovery.yml` called it in recovery run 39315174445 (at 4f9c1e8), whose worker jobs and checkpoint it produced; later versions call `atomic-completion-worker.yml`. It stays because `scripts/preserve_inputs.py` registers its pinned downloads for a repin. |

## Dispatch

GitHub's documentation on manually running a workflow states that a workflow
must be in the default branch for the `workflow_dispatch` event to trigger it.
The same page shows `gh workflow run WORKFLOW --ref BRANCH` for running a
workflow on another branch. Read together, the file must be on the default
branch, and the ref selects the branch whose version runs. Whether GitHub
accepts a dispatch of a file that exists only on another branch has not been
tested here: on 2026-10-20 the Actions API listed no `workflow_dispatch` run of
this repository.

`main` (01dfd1e) does not contain `dependency-cone.yml`, `preserve-inputs.yml`,
`catalog-preview.yml` or the PR #8 workflows. GitHub has registered
`dependency-cone.yml` (workflow 390162521) from its push run, and has no record
of `preserve-inputs.yml`. The documented route for each is to put the file on
`main` first. A command that dispatches one of them from another branch is
untested until a run records it.

## Restore a file

To run an archived workflow again, move it back:

```sh
git mv .github/workflow-archive/NAME.yml .github/workflows/
```

Most archived files download artifacts of fixed earlier runs by ID. Those
artifacts expire, so a restored file can fail for that reason alone.

## Merge hazards

A push event uses the workflow files in the pushed commit. A pull-request event
uses the files in the merge commit of the pull request with its base. The move
therefore affects this branch, and branches or pull requests that later merge
from or into it.

Git rename detection applies a branch's later edits of a moved file to the
archived copy, which does not run. Every archived file is identical to the
active copy on the PR #8 head efc679d. After any merge, check moved files:

```sh
git diff --name-status -M ORIG_HEAD HEAD -- .github
```

Move an edited file back to `.github/workflows/` if it is still needed.

`main` still holds active copies of 12 archived files and the earlier versions
of `all-findings-release.yml` and `breadth-release.yml`, whose push triggers
name `main`. Until this branch reaches `main`, a push to `main` that matches
their path filters runs those earlier versions.

Since commit 2954402, HANDOFF.md names `finding-proofs-remaining.yml` and
`proof-budget-recovery.yml` by their archive paths.
