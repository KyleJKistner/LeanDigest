# Catalog preview

A catalog preview is a published offline catalog whose proof readings were
re-rendered with the current renderer. It shows renderer changes, display
notation and citation links on the published readings without a native Lean
rebuild. A preview is not a release: it adds no theorem-target reading, runs no
Lean, and keeps every retained observation byte for byte. It can also add the
supporting lemma readings of a dependency-cone campaign, a separate denominator
described in [Dependency-cone readings](DEPENDENCY_CONE.md#entering-the-catalog).

`scripts/rerender_catalog.py` builds a preview. The
`.github/workflows/catalog-preview.yml` workflow builds one from the pinned
release and uploads it as a workflow artifact.

## Build a preview

```sh
python scripts/rerender_catalog.py PUBLISHED OUTPUT [--archive-sha256 DIGEST] [--browser real|document-harness] [--no-archive]
    [--cone-shards DIR [--cone-scope SCOPE] [--cone-summary FILE] | --cone-unavailable REASON]
```

`--cone-shards DIR` adds supporting lemma readings from a dependency-cone
campaign directory: `dependency-cone-plan/` and the shard directories, as
`scripts/download_cone_artifacts.py` writes them. `--cone-scope` is the run's
dispatch scope (default `pilot`). With `--cone-summary FILE`, the reconciled
outcomes must equal that campaign summary. `--cone-unavailable REASON` builds
without supporting lemma readings and states the reason in the preview. With
neither option, the preview states that no dependency-cone shards were supplied.

`PUBLISHED` is an extracted `Leanglish/` site or its release zip. A zip must match
`--archive-sha256`, which defaults to the digest of
`leanglish-original-project-317dc31` in `scripts/fetch_reading_corpus.py`.
`OUTPUT` must be a new directory. It receives:

| Path | Content |
| --- | --- |
| `Leanglish/` | The preview site. Open `Leanglish/index.html`. |
| `leanglish-catalog-preview.zip` | The same site as a deterministic zip. |
| `SHA256SUMS` | The digest of the zip. |
| `summary.json` | The preview record with the site and zip sizes. |
| `screenshots/`, `original-verification-*.png` | Browser-audit screenshots, when a browser route runs. |

Without `--browser`, no browser audit runs, and `browser-audit.json` in the
site records `not_run`. With `--no-archive`, no zip or `SHA256SUMS` is written.

## Procedure

1. Copy the published site, or extract the zip after rejecting unsafe paths,
   links and oversized archives.
2. Check every file against the published `SHA256SUMS.json`, including the exact
   file inventory. Reject a site that is already a preview, or that already has
   supporting lemma readings. Check that `coverage.json` equals the coverage in
   `release.json`.
3. With `--cone-shards`, validate the campaign directory and bind it to the
   published readings and to the published `original-evidence/plan.json` and
   `original-evidence/environment.json`, as described in
   [Acceptance](DEPENDENCY_CONE.md#acceptance). Any failure stops the preview
   before a reading is re-rendered.
4. Index the bundled solution modules in `originals/` once, as the catalog
   builder does, and re-render each reading with `narrative_io.write_bundle`.
   The published title and provenance note are kept. Citation links are built
   with the builder's functions (`declaration_index.citation_links` and
   `finding_catalog.source_name`), including links to the supporting lemma
   readings when a campaign is supplied.
5. Restore the published bytes of `snapshot.json`, `receipt.json`, `run.json`,
   `stdout.txt` and `Extract.lean` in each reading directory, and check them
   against the published manifest.
6. With a campaign, write each accepted supporting lemma reading to `cone/<id>/`
   (`cone_catalog.write_readings`), restore the shard artifact's bytes of the same
   five evidence files, and write `evidence/dependency-cone-summary.json`. A
   supporting reading that fails to render stops the preview.
7. Update the counts that depend on the readings: the gap count beside each
   reading link on the finding pages, `explicit_explanation_gaps` and
   `citation_links` in `coverage.json`, and the matching rows of `coverage.html`.
   Each published count must equal the published readings before it is replaced,
   and every reading link on a finding page must have the recognized form. With
   a campaign, also add the `dependency_cone` section to `coverage.json`, the
   separate table body, interpretation paragraph and outcome-record link to
   `coverage.html`, and the **Supporting lemma readings** list to each finding
   page whose target readings cite one.
8. Write `evidence/declaration-index.json` and the explanation-gap inventory
   (`explanations.html`, `explanation-gaps.json`) of the target readings. Writing
   the inventory compares every saved target reading with deterministic
   regeneration from its snapshot and every target reader page with its reading
   and links.
9. Copy the current catalog assets (`assets/catalog.css`, `assets/catalog.js`),
   which the explanation-gap filters need. Add the explanation-gap link to the
   main navigation of the catalog's own pages (top level, `findings/` and
   `sources/`). A page's navigation may only gain links. Bundled originals and
   evidence are never rewritten.
10. Add a preview notice to every top-level page (catalog, coverage, explanation
   gaps, original verification) and every finding page, and write `preview.html`,
   `preview.json`, a preview section at the top of `RELEASE-NOTES.md`, and a
   first line in `START-HERE.txt`. Reader pages carry no notice, because each
   reader page must equal its regenerated reading. The notice, `preview.html`
   and the release notes state whether supporting lemma readings are included,
   with their counts, or why they are not.
11. Run the static catalog audit and stop on any error; it covers the supporting
   lemma pages and links ([Static audit](DEPENDENCY_CONE.md#static-audit)). Run
   the requested browser route. Write the audit records, regenerate
   `SHA256SUMS.json`, check that the file-change table on `preview.html` matches
   the final site, check the supporting lemma evidence against the shard artifacts
   again, and write the zip.

Any reading that fails to re-render stops the preview. A fresh catalog build
omits such a reading; a preview never drops a published reading.

The output is deterministic for a given input and application checkout. The
preview record names the application commit, whether the tracked tree was clean,
and a digest of every renderer, catalog and script source file, including
untracked files.

## Records

`preview.json` (`leanglish.catalog-preview/v1`) records the following:

- The published identity: release name (when the manifest digest is the pinned
  release's), archive digest, manifest digest, published application commit,
  published renderer labels and the published audit records.
- The application commit, tree, clean-tree flag and source digest.
- Reading counts, the number of evidence files checked, and
  `lean_executed: false`, `observations_authenticated: false` and
  `english_formally_verified: false`.
- Explanation gaps before and after: gap steps, checked frames inside gap steps,
  readings without gaps, gap steps by rule, and checked frames inside gap steps
  by the rule of the step.
- Citation-link summaries before (if any) and after. With supporting lemma
  readings, links to them are counted under `linked_to_cone_reading`, never
  under `linked_to_reading`.
- `dependency_cone`: either `included: false` with the stated reason, or
  `included: true` with the scope, the counts, the `dependency_cone` section of
  `coverage.json` and the download record `cone-artifacts.json` when the
  campaign directory has one. The download record is provenance; acceptance
  rests on the loader's checks.
- Every file group with its added, replaced and unchanged counts.
- The static audit, the catalog browser audit with the preview-page checks, and
  the original-verification browser audit.

`release.json` and `original-verification.json` still describe the published
release. Their coverage no longer equals the preview's `coverage.json`, so
`scripts/publish_completion_release.py` rejects a preview.

## Browser routes

`--browser real` opens each page from the file system in Chromium. It runs
`scripts/audit_finding_browser.py` and `scripts/audit_original_browser.py`, then
checks the pages the preview adds or changes:

- The notice on the catalog page links to `preview.html`.
- The preview page shows the gap count and fits a 390-pixel-wide viewport.
- The explanation-gap table lists every reading with gaps, and its filter for
  the most frequent reference shows the inventory's count.
- A reader page links a cited name to another proof reading.
- With supporting lemma readings: a finding page lists one and fits a 390-pixel
  viewport, the link opens the supporting lemma reader page, and a target reader
  page's labelled link to it navigates there.

The audits use Python assertions, so the script refuses a browser route under
`python -O`.

`--browser document-harness` loads each document with its local styles and
scripts inlined. Use it only where browser policy blocks `file://` navigation.
The record names the route as `direct-document-test-harness`. It does not test
navigation between files.

## Workflow

`catalog-preview.yml` runs on pushes to `claude/keen-archimedes-ihorkq` that
change `proofreader/**`, the script, the scripts it imports, its tests,
`benchmarks/reading-kpis/**`, `benchmarks/dependency-cone/**` or the workflow,
and on manual dispatch. It has no schedule. It runs the preview tests
(`tests/test_rerender_catalog.py`, `tests/test_cone_catalog.py`), downloads the
pinned release zip and checks its SHA-256.

It then runs `scripts/download_cone_artifacts.py` for the dependency-cone pilot
run 39373979494 (`CONE_RUN`). The script lists the run's artifacts with the
workflow token, downloads the plan, summary and 8 pilot shard artifacts that
the committed plan names, and requires each zip's SHA-256 and size to equal the
values the API records before it extracts the zip. This needs the `actions:
read` permission. If any artifact is missing, expired or different, the step
does not fail: it adds a warning annotation, and the preview is built with
`--cone-unavailable` and the reason, which the preview notes, `preview.html`,
`preview.json` and the job summary state. The pilot artifacts expire on
2027-01-18.

With verified artifacts, the preview is built with `--cone-shards` and
`--cone-summary`. A campaign that downloads correctly but fails the loader's
checks fails the run; it is never dropped silently. The workflow then extracts
the zip, checks every file against the packaged `SHA256SUMS.json`, runs the
static audit again, and requires the preview's 492 re-rendered target readings,
their gap steps and frames inside gaps, in total and by rule, to equal
`benchmarks/reading-kpis/current.json`. It writes the supporting lemma line,
"included" with counts or "not included" with the reason, to the job summary.

Only a successful run uploads the zip, its digest and `summary.json` as the
`leanglish-catalog-preview` artifact. Every run uploads `summary.json`, audit
records, screenshots, the cone download record and the download log as
`catalog-preview-diagnostics`. Both artifacts are kept for 30 days. The
workflow has read-only repository and Actions permissions. It never creates a
release and never pushes.

## Pinned release with renderer 0.5.0

A local run on the published `leanglish-original-project-317dc31` site, with
renderer `source-math-en/0.5.0`, gave the following. A later renderer changes
these numbers; `summary.json` in the workflow artifact records the current ones.

| Measure | Published | Preview |
| --- | ---: | ---: |
| Manifest entries verified | 8,360 | — |
| Proof readings | 492 | 492 (none added or removed) |
| Evidence files byte-identical to the published manifest | — | 2,460 |
| Selected checked frames | 22,452 | 22,452 |
| Explicit explanation gaps | 7,587 | 5,098 |
| Checked frames inside explanation gaps | 7,587 | 8,171 |
| Readings without explanation gaps | 0 | 0 |
| Cited project names | No links | 1,762 |
| … linked to a proof reading | — | 30 |
| … linked only to a bundled source line | — | 320 |
| … unresolved | — | 1,412 |

The gap-step count fell while more checked frames sit inside gaps. Renderer
0.5.0 groups several frames into one displayed step, and instance and
automation groups are counted as gaps: the 522 `instance-facts` gap steps hold
2,132 checked frames, and the 260 `automation` gap steps hold 1,723. Every other
gap step, published or preview, holds one frame. The step count is therefore
not a measure of explained frames. The totals and the counts by rule match
`benchmarks/reading-kpis/current.json`.

| Readings with | Fewer | The same | More |
| --- | ---: | ---: | ---: |
| Gap steps | 171 | 300 | 21 |
| Checked frames inside gaps | 65 | 324 | 103 |

Gap steps by rule in the preview: `project-citation` 2,068;
`citation` 1,440; `instance-facts` 522; `rewrite` 346; `automation` 260;
`unchecked-projection` 224; `restatement` 124; `substitution` 56; `witness` 35;
`choose` 12; `application` 7; `ring` 4. The published 0.4.1 readings used other
rule tags (`application` 5,502; `named` 1,476; `rewrite` 434; `identity` 124;
`witness` 35; `choose` 12; `ring` 4), so the rows are not a one-to-one mapping.

In every reading directory the preview replaced `reading.json`, `reader.html`,
`proof.txt` and `coverage.json` and added `links.json`;
`polynomial-certificates.json` is unchanged in all 492. It also replaced all 372
finding pages, all 413 source pages (navigation only), the catalog, coverage and
original-verification pages, two catalog assets, `coverage.json`, the release
notes, `START-HERE.txt` and the audit records. All 602 statement records, 1,245
bundled original files, 790 original-evidence files, `catalog.json`,
`release.json` and `original-verification.json` are unchanged.

The static audit passed on 1,282 pages with 9,328 local links, 95,027 anchors and
385 citation links. Real Chromium file navigation passed for the catalog, the
original-verification pages and the preview pages. The largest retained snapshot
(38 MB, `proofs/305b16dfae1b96214507073b`) re-rendered within the 64 MB snapshot
limit.

The preview site has 8,858 files and 635.5 MB; its zip is 52.2 MB. The
published site has 8,361 files and 659.3 MB; its zip is 49.1 MB. The run from the
release zip, including both browser audits and the zip, took about 165 s on
four CPU cores. Two runs from the same checkout produced byte-identical zips.

## Pinned release with the pilot supporting lemma readings

A local run at application commit `171ab5e` (renderer `source-math-en/0.6.0`)
used the pinned release zip and the artifacts of dependency-cone run
39373979494, downloaded with `scripts/download_cone_artifacts.py`. All 10
artifact digests matched the GitHub API. The table compares it with a run of
the same application code without `--cone-shards`.

| Measure | Without supporting readings | With them |
| --- | ---: | ---: |
| Target readings re-rendered | 492 | 492 |
| Explicit explanation gaps (target readings) | 4,961 | 4,961 |
| Supporting lemma readings | — | 151 of 1,722 planned |
| Cited project names linked to a target reading | 30 | 30 |
| … linked to a supporting lemma reading | — | 151 |
| … linked only to a source line | 320 | 314 |
| … unresolved | 1,412 | 1,267 |
| Static audit: pages | 1,282 | 1,433 |
| Static audit: local links | 9,328 | 9,480 |
| Static audit: citation links | 385 | 593 |
| Site files | 8,858 | 10,520 |
| Site size | 624.2 MB | 731.4 MB |
| Zip size | 52.1 MB | 60.0 MB |

Both static audits passed; the second also checked 151 supporting lemma pages
and 202 supporting lemma links. Real Chromium file navigation passed for the
catalog, the original-verification pages, the preview pages and the supporting
lemma checks. The target readings' gap counts, in total and by rule, equal
`benchmarks/reading-kpis/current.json` in both runs. The packaged zip was
extracted, checked against its `SHA256SUMS.json` and audited again. The run with
supporting readings took 219 s, including both browser audits and the zip.
[Pilot readings in the preview](DEPENDENCY_CONE.md#pilot-readings-in-the-preview)
lists the supporting lemma counts.

## Limitations

A preview is a rendering of retained, unsigned observations. It does not
re-extract any snapshot, authenticate a receipt, or replay the original project.
The English is deterministic and regression-tested, not formally verified, and a
reading without gaps is not a certified complete proof. The browser audits
exercise selected pages and interactions, not every page. The citation-link and
explanation-gap limitations in `docs/CITATION_LINKS.md` and `docs/TRUST.md`
apply unchanged.
