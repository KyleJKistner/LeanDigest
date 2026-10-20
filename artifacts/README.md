# Committed run outputs

This directory holds run outputs that tests, documents or packaged demos read
directly from the repository. Each subdirectory records one run or one
evidence set, such as `pinned-openai-slice/38767243074/` for Actions run
38767243074. These files are evidence of what a run produced. Do not edit them
for style, and do not regenerate them in place under the same run identity.

## Size budget

`scripts/check_artifact_budget.py` measures the tracked files under this
directory from the Git index. Untracked local outputs are not counted.
`tests/test_artifact_budget.py` runs it in ordinary CI (`ci.yml`). The check fails
in any of these cases:

- The total tracked size exceeds `BUDGET_BYTES`.
- A tracked file exceeds 1,000,000 bytes and has no entry with a reason in
  `ALLOWED_LARGE`.
- An `ALLOWED_LARGE` entry names a file that is no longer tracked, or that is
  now within the limit.
- No tracked file is found, so nothing was measured.

At 04df977 the directory held 1,022 tracked files and 19,659,106 bytes. The
budget is 21,000,000 bytes. The test also fails when the budget exceeds 1.25
times the measured total. The budget therefore cannot be set far above the
tracked size, and it must be lowered after a large removal.

```sh
python scripts/check_artifact_budget.py          # summary; exit 1 on a violation
python scripts/check_artifact_budget.py --json   # full report and largest files
```

Raising the budget or adding an allowlist entry is a reviewed change to
`scripts/check_artifact_budget.py`. State the reason in the same commit.

## Where new run outputs go

Put bulky run outputs in GitHub Actions artifacts or release assets, not in this
directory. Bulky outputs include native logs, compiler stdout, extracted
snapshot trees, offline catalogs, archives and browser screenshots.

Cite each one where it is used, with the following details:

- The run ID, and the job ID when the job matters.
- The artifact ID and name, or the release tag and asset name.
- The SHA-256 of the downloaded archive or asset. GitHub reports artifact digests
  as `sha256:...`.
- The commit the run was built from.
- For an Actions artifact, its expiry date. The workflows here set 14, 30 or 90
  days of retention, or use the repository default. Evidence that must outlive
  that period belongs in a release asset.

Small summaries may be committed here when a test or document needs them in
the repository. Examples are a coverage or acceptance JSON file, a receipt, or a
short checker log. Record the run ID and SHA-256 next to the summary. Before
adding a directory, check that the total stays within the budget.

A digest binds bytes; it does not authenticate the runner that produced them
(see docs/TRUST.md). Committing an output here does not make it more
trustworthy than the run that produced it.

## Existing contents

The existing directories are retained unchanged, including those that predate
this policy. The largest file,
`pinned-openai-slice/38767243074/batch/attempts/.../run.json` (1,595,064 bytes),
is allowlisted. `run-provenance.json` in the same run directory records its byte
count and SHA-256, so it cannot be trimmed without breaking that record.
