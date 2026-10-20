# Input preservation

Kept workflows download inputs from artifacts of earlier GitHub Actions runs,
pinned by run ID or artifact ID. Actions artifacts expire, and a workflow fails
at the download step once its input has expired. This page lists those inputs
and their deadlines, describes two ways to keep them available (copies as new
artifacts, which expire again, and release assets, which are publication), and
gives the steps for pointing the consumers at preserved copies.

**Nothing on this page has been dispatched.** No artifact has been copied, no
release asset has been attached, and no consumer file has been repinned.
`.github/workflows/preserve-inputs.yml` has never run.

## Pinned inputs

The Actions API reported these values on 2026-10-20 at about 07:00 UTC, in a
read-only listing. A second read-only listing at about 08:30 UTC returned the
same ID, name, run, commit, digest, size and expiry for every artifact in the
registry, and none had expired. **Bytes** is the size of the artifact ZIP. For a group of
artifacts, **Expires** is the earliest expiry in the group. **Digest recorded
in** names the files that record a SHA-256 of the input independently of the
Actions API. For inputs with no recorded digest, only the digest that GitHub
reports at copy time can be checked. **Set** is the dispatch choice of
`preserve-inputs.yml` that copies the input.

| Artifact (ID) | Run | Bytes | Expires (UTC) | Digest recorded in | Downloaded by | Set |
| --- | --- | ---: | --- | --- | --- | --- |
| `checkpoint-142c3d0f555a25666bb36dd1-1` (12217614568) | 39315174445 | 22,385,891 | 2026-11-02 20:14 | `check_original_checkpoint.py`, `completion-resume.yml`, `completion_results.py` | `completion-resume.yml` | `expiring-2026-11`, `checkpoint` |
| `complete-openai-lean-source` (12012738377) | 38822475057 | 320,755,640 | 2026-11-14 23:16 | `assemble_finding_release.py`, `dependency_cone.py` | `all-findings-release.yml`, `atomic-completion-worker.yml`, `breadth-release.yml`, `completion-delivery.yml`, `completion-resume.yml`, `completion-worker.yml`, `dependency-cone.yml` | `expiring-2026-11`, `source` |
| `finding-statement-retry-*` (2 artifacts) | 39050823104 | 15,170 | 2026-11-16 16:52 | None | `all-findings-release.yml`, `breadth-release.yml`, `completion-delivery.yml` | `expiring-2026-11`, `statement-retries` |
| `leanglish-all-finding-observations` (12107445952) | 39049596449 | 12,872,783 | 2027-01-15 16:29 | None | `all-findings-release.yml`, `breadth-release.yml`, `completion-delivery.yml` | `expiring-2027-01` |
| `finding-proof-retry-*` (16 artifacts) | 39065371645 | 1,380,427 | 2027-01-15 20:07 | None | `all-findings-release.yml`, `breadth-release.yml` | `expiring-2027-01` |
| `leanglish-breadth-observations` (12116428595) | 39076207515 | 10,422,321 | 2027-01-15 22:43 | None | `breadth-release.yml` | `expiring-2027-01` |
| `original-nanoda-toolchain` (12152481984) | 39170206904 | 98,956,485 | 2027-01-16 21:58 | `atomic-completion-worker.yml`, `completion-resume.yml`, `completion-worker.yml` | `atomic-completion-worker.yml`, `completion-resume.yml`, `completion-worker.yml` | `expiring-2027-01` |
| `completed-original-campaigns` (12195158110) | 39270771889 | 289,240,254 | 2027-01-17 14:38 | `completion-delivery.yml` | `completion-delivery.yml` | `expiring-2027-01` |
| `validated-completion-plan` (12197582957) | 39276345053 | 14,615,062 | 2027-01-17 15:15 | `completion-delivery.yml`, `completion-recovery.yml`, `completion-resume.yml` | `completion-delivery.yml`, `completion-recovery.yml`, `completion-resume.yml` | `expiring-2027-01` |

`python scripts/preserve_inputs.py inventory` prints this table from the
registry in that script, and `tests/test_preserve_inputs.py` checks that the
two agree. The registry also records each artifact's run commit and digest.

The two statement retries are `finding-statement-retry-CoarseAssembly`
(12107274354, expires 16:52) and
`finding-statement-retry-CharacterVarietiesAllSeamsSupport` (12108605282,
expires 17:06). The recorded source digests are of the artifact ZIP
(`proofreader/dependency_cone.py`) and of `openai-lean-source.tar.gz` inside it
(`scripts/assemble_finding_release.py`). The set `expiring-2026-11` totals
343,156,701 bytes and `expiring-2027-01` totals 427,487,332 bytes.

## Deadlines

| Date (UTC) | Input expires | Consequence |
| --- | --- | --- |
| 2026-11-02 20:14 | Checkpoint 12217614568 | `completion-resume.yml` fails at its checkpoint metadata check. |
| 2026-11-14 23:16 | Source 12012738377 | The seven source consumers can no longer download the source. `dependency-cone.yml` fails in its preflight job. A push to `main` that matches the path filters of `all-findings-release.yml` or `breadth-release.yml` fails its build job. |
| 2026-11-16 16:52 and 17:06 | Statement retries | `all-findings-release.yml`, `breadth-release.yml` and `completion-delivery.yml` can no longer download the two retries. |
| 2027-01-15 to 2027-01-17 | The `expiring-2027-01` set | Their consumers can no longer download them. |

Whether `completion-resume.yml` needs to run again is the owner's decision. It
resumes one stopped worker of recovery run 39315174445. Two earlier runs of
`completion-resume.yml` are recorded: 39321225048 (success) and 39352981910
(failure).

## Inputs this workflow does not copy

- **`completion-result-*` artifacts.** Run 39315174445 holds 74 of them and run
  39321225048 holds 1; all 294 and 5 artifacts of the two runs were listed. They
  expire on 2027-01-17 at 19:56 and 20:40. `completion-delivery.yml` collects them
  through `scripts/collect_completion_results.py`, and `completion-recovery.yml`
  reads those of run 39315174445. Both require each artifact to belong to the
  producing run and commit. A copy cannot meet that check, so repinning requires
  a code change. Run 39353736010 retained the collected
  results as `completion-frozen-observations` (12234538263) and
  `continuation-frozen-observations` (12234168598), which expire on 2027-01-18.
- **`completion-reading-delivery` (12234627856, run 39353736010, 49,209,060
  bytes, expires 2027-01-18 01:29).** `publish-completion.yml` passes it to
  `scripts/publish_completion_release.py`, which requires a successful
  `completion-delivery.yml` run at application commit 2149131. A copy cannot
  meet that check. Release `leanglish-original-project-2149131` already exists.
- **`cancellation-env-a` (12202194378, run 39285448721, 193,506,791 bytes,
  expires 2026-10-20 16:27).** Only the optional `--retained-environment` path
  of `scripts/check_source_cancellation.py` reads it, and no kept workflow
  downloads it. Its digest is recorded in that script. It expires today, so it
  is not in any set.
- **Dependency cache `original-openai-deps-1581d4cb-4341-full-v1`.**
  `completion-worker.yml`, `atomic-completion-worker.yml` and
  `completion-resume.yml` restore it with `fail-on-cache-miss: true`. Caches are
  not artifacts. GitHub's caching documentation states that entries not accessed
  for 7 days are removed. The cache listing was not readable from this session,
  so the cache's current state is unknown. `dependency-cone.yml` re-creates the
  dependencies when the cache is missing.
- **Job and run records** that `completion-resume.yml` asserts (job
  118274980446 and runs 39319564118, 39321225048 and 39352981910). These are
  not artifacts. Whether they remain readable is not established here.
- **Original evidence runs 39141760623 and 39144564607.** The first holds 84
  artifacts and the second 144. Both listing pages of the second run were
  read on 2026-10-20 at about 08:30 UTC. Every artifact of the two runs expires
  on 2027-01-16. Only archived workflows run the collection mode of
  `scripts/collect_original_evidence.py`.
- **Acceptance run 38792262410** (2 artifacts, expiring on 2027-01-13).
  `docs/MATHEMATICIAN_PREVIEW.md` cites it, and only archived workflows
  download it.

## Copies as new artifacts

`preserve-inputs.yml` is dispatch-only and has `contents: read` and
`actions: read` permissions. The run token uploads the copies. For each
artifact of the selected set, one matrix job does the following:

1. Reads the artifact's metadata and requires the pinned ID, name, run, commit
   and digest, `expired: false`, and for an original its recorded size.
2. Downloads the artifact ZIP and requires its SHA-256 to equal the reported and
   pinned digest. Where the repository records a digest, it checks that digest
   too, including the source archive inside the ZIP.
3. Stages the payload. An input that consumers fetch with `gh run download` is
   staged as its extracted files, so `-n` and `-p` downloads keep their layout.
   An input that consumers fetch as a ZIP is staged as the original ZIP bytes,
   named `original-<artifact ID>.zip`, so the recorded `sha256sum -c` checks
   still apply to the restored file. Extraction rejects absolute paths, `..`,
   links, repeated paths, more than 25,000 entries and oversized contents.
4. Uploads the payload under the original name with `retention-days: 90`.
   GitHub's documentation on repository Actions settings states that a public
   repository's retention period is 1 to 90 days, and the repository API
   reported this repository as public on 2026-10-20. Hidden files are included.
5. Downloads the new artifact through the API, requires a reported digest that
   matches the downloaded bytes, and compares its extracted file list (paths,
   sizes and SHA-256) with the staged payload.
6. Writes an item record. A failure at any step writes a failure record instead.

A final job merges the item records into `preservation-record.json`, uploaded
as the artifact `preservation-record`. The record holds, for each artifact, the
original and copied-from identities, the recorded digests and what each was
checked against, the content digest, and the new artifact ID, run, commit,
digest, size, creation and expiry times, with requested and observed retention.
It lists missing and failed copies, and the job fails if any exist. The record
has `release_published: false` and `consumers_repinned: false`.

Copies expire at most 90 days after their upload, so this option must be
repeated. Each repetition copies the current copy, checks it against the
content digest of the first copy, and needs another repin. Empty directories
are not preserved; the record lists any that the original contained. For
extracted contents, file modes are not compared. Four such originals were
downloaded on 2026-10-20 for this review (the observations, the breadth
observations, `finding-statement-retry-CoarseAssembly` and
`finding-proof-retry-2`), and every entry had mode 0644; the others were not
inspected. A copied ZIP keeps the original bytes, modes included.

### Size

Each copy stores about as many bytes as its original for 90 days: about
343 MB for `expiring-2026-11` and 427 MB for `expiring-2027-01`. A dispatch
transfers each input about three times: one download, one upload and one
verification download. This page does not establish whether Actions storage
for this public repository is billed. Check the account's billing settings.

## Release assets

Release assets do not expire. Attaching the inputs to a release is
publication: anyone can download them. That requires the owner's explicit
decision, and `preserve-inputs.yml` never does it. The inputs include files from
`openai/math`, which are distributed under the Apache License 2.0 (see
`THIRD_PARTY_NOTICES.md`), compiled build files, toolchain binaries and recorded
observations. This page does not review the licenses of the binaries or build
files.

GitHub's documentation about releases states that each file in a release must
be under 2 GiB. The largest input, the source ZIP, has 320,755,640 bytes. To
keep the recorded digests valid, attach the original artifact ZIPs unchanged.
Consumers would then use `gh release download <tag> -p <file> -D <dir>` followed
by the existing digest checks. `scripts/preserve_inputs.py repin` does not
print edits for this option. A release asset can be deleted or replaced by a
maintainer; the recorded digests detect a replaced file. The reading corpus
already follows this pattern as an asset of `leanglish-original-project-317dc31`
(`scripts/fetch_reading_corpus.py`).

## Rebuilt source archive

The source artifact can also be rebuilt from `openai/math` at the pinned commit
with the archived `lean-source-bundle.yml`. That workflow runs `tar -czf`
without fixed timestamps or file order, so a rebuilt archive is not expected to
have the same SHA-256. Both recorded source digests would change.
`unpack_source` would still check every extracted file against
`source-inventory.json`, which that workflow regenerates after checking each
file against the Git blob of the pinned commit. The checkpoint, observations
and toolchain cannot be rebuilt without rerunning the jobs that produced them.

## Dispatch

GitHub's documentation on manually running a workflow states that the workflow
must be on the default branch for the `workflow_dispatch` event to trigger it.
`main` does not contain `preserve-inputs.yml`, and this change does not add it
there. To copy the checkpoint before 2026-11-02 20:14 UTC, the owner must
first put the workflow on `main`. The run then uses the files of the ref passed
to the dispatch. `scripts/preserve_inputs.py` uses only the Python standard
library and no other module of this repository, and the copy and record jobs
run it without installing the application. The plan job installs the package
with `pip install '.[dev]'` before it runs the tests, because
`tests/conftest.py` imports `proofreader`, so the dispatched ref must contain
the package as well as the script.

```sh
gh workflow run preserve-inputs.yml --ref <branch> -f set=expiring-2026-11
gh run list --workflow preserve-inputs.yml --limit 1
```

The plan job runs `tests/test_preserve_inputs.py` without the tests whose
names contain `checkout`. Those tests read consumer files, which the dispatched
ref may not contain; `ci.yml` runs them.

## Repin

Repinning edits consumer files and is a separate, reviewed commit. The repin
command reads a preservation record and the checkout, and prints the edits. It
does not apply them.

1. Confirm that the preservation run succeeded and that its `record` job passed.
2. Download the record:
   `gh run download <run> -n preservation-record -D /tmp/preservation`.
3. Print the edits:
   `python scripts/preserve_inputs.py repin --record /tmp/preservation/preservation-record.json`.
   The command exits with status 1 and prints **This plan is incomplete** when a
   consumer reference is not where the registry expects it, or when a scanned
   file names the replaced run or artifact in a way the registry does not
   cover. Resolve those items before editing.
4. Apply the printed edits in one commit, including the replacement of the
   `CURRENT` block in `scripts/preserve_inputs.py`. Copy the record to
   `artifacts/input-preservation/<run>.json` in the same commit.
5. Run the test suite, including `tests/test_preserve_inputs.py`,
   `tests/test_dependency_cone.py` and `tests/test_completion_resume.py`.
6. Apply the same commit on every branch from which a consumer is triggered. A
   workflow runs the file version of the ref that triggers it: for example
   `main` for the release workflows, the PR #8 head branch
   `work/completion-evidence-retries` for the completion workflows, and
   `claude/keen-archimedes-ihorkq` for `dependency-cone.yml`.
   Pushing the commit runs every consumer whose push filter matches an edited
   file. On `main`, `all-findings-release.yml` and `breadth-release.yml` filter
   on their own files and on `proofreader/**`, so both run their build jobs.
   Their publish jobs create a release only when the tag
   (`leanglish-all-findings-v0.4.0` or `leanglish-all-findings-v0.4.1`) does not
   exist; both tags existed on 2026-10-20. On
   `work/completion-evidence-retries`, `completion-delivery.yml` runs. On
   `claude/keen-archimedes-ihorkq`, an edit to `dependency-cone.yml` starts a
   run of that workflow with its default `pilot` scope. Decide whether those
   runs are wanted before pushing.
7. Before the copies expire, dispatch the same set again and repeat these steps.

The printed edits, by set, against this checkout:

| Set | File | Edits |
| --- | --- | ---: |
| `expiring-2026-11` | `.github/workflows/all-findings-release.yml` | 2 |
| | `.github/workflows/atomic-completion-worker.yml` | 1 |
| | `.github/workflows/breadth-release.yml` | 2 |
| | `.github/workflows/completion-delivery.yml` | 2 |
| | `.github/workflows/completion-resume.yml` | 8 |
| | `.github/workflows/completion-worker.yml` | 1 |
| | `.github/workflows/dependency-cone.yml` | 2 |
| | `proofreader/dependency_cone.py` | 2 |
| | `scripts/preserve_inputs.py` | 1 |
| | `tests/test_dependency_cone.py` | 3 |
| `expiring-2027-01` | `.github/workflows/all-findings-release.yml` | 2 |
| | `.github/workflows/atomic-completion-worker.yml` | 1 |
| | `.github/workflows/breadth-release.yml` | 3 |
| | `.github/workflows/completion-delivery.yml` | 3 |
| | `.github/workflows/completion-recovery.yml` | 1 |
| | `.github/workflows/completion-resume.yml` | 2 |
| | `.github/workflows/completion-worker.yml` | 1 |
| | `scripts/preserve_inputs.py` | 1 |

The edits change run IDs in `gh run download` lines and in `SOURCE_RUN`, and
artifact IDs and digests in `SOURCE_ARTIFACT` and its test. Each
`gh api .../artifacts/<ID>/zip` line becomes a `gh run download` of the copy
followed by a `mv` of the original ZIP to the same path, so the following
`sha256sum -c` line still checks the original bytes. In `completion-resume.yml`
the checkpoint metadata assertions name the copy, and the acquisition record
keeps the original checkpoint's artifact ID, run, commit and digest.
`proofreader/completion_results.py` and `scripts/check_original_checkpoint.py`
require that identity; the copied bytes are checked against its digest. After
the repin, the acquisition record therefore does not name the copy that the
bytes came from. The copy is named only in the repinned workflow and in the
preservation record. Recording it in the acquisition record would need a
reviewed change to both checks. The repin leaves `INPUT_RUNS` in
`scripts/assemble_finding_release.py` unchanged: it records the runs that
produced the inputs, which a copy does not change.

## Verification

`tests/test_preserve_inputs.py` runs on synthetic artifacts, synthetic records
and fake `gh` calls. It covers the copy checks, rejected archives and metadata,
the round trip, the merge of item and failure records, the printed edits, a
second copy of a copy, drift reports, and records whose run, commit or copy
identity is not a plain number or digest, which repin refuses. The trigger and
permission checks of `preserve-inputs.yml` read the workflow text, because
neither `ci.yml` nor the plan job installs PyYAML; a further structural test
runs only where PyYAML is installed. The tests whose names contain `checkout`
also run the repin against this checkout's consumer files with a synthetic
record. They require every reference to be found and no scanned file
to name a replaced run or artifact outside the edits and the listed unchanged
references. No test downloads an artifact or contacts GitHub.

## Limitations

- The digests are those that GitHub reports and those the repository recorded
  when the inputs were pinned. They are not signatures. The preservation record
  is not authenticated either.
- Copying checks bytes, not meaning. It does not re-run Lean, re-check a proof
  or re-validate an observation.
- The registry in `scripts/preserve_inputs.py` covers the inputs listed in the
  table above. A new pin in a consumer needs a new registry entry.
- Copies made by this workflow expire after at most 90 days.
