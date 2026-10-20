# Catalog preview

A catalog preview is a published offline catalog whose proof readings were
re-rendered with the current renderer. It shows renderer changes, display
notation and citation links on the published readings without a native Lean
rebuild. A preview is not a release: it adds no reading, runs no Lean, and keeps
every retained observation byte for byte.

`scripts/rerender_catalog.py` builds a preview. The
`.github/workflows/catalog-preview.yml` workflow builds one from the pinned
release and uploads it as a workflow artifact.

## Build a preview

```sh
python scripts/rerender_catalog.py PUBLISHED OUTPUT [--browser real|document-harness]
```

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
site records `not_run`.

## Procedure

1. Copy the published site, or extract the zip after rejecting unsafe paths,
   links and oversized archives.
2. Check every file against the published `SHA256SUMS.json`, including the exact
   file inventory. Reject a site that is already a preview. Check that
   `coverage.json` equals the coverage in `release.json`.
3. Index the bundled solution modules in `originals/` once, as the catalog
   builder does, and re-render each reading with `narrative_io.write_bundle`.
   The published title and provenance note are kept. Citation links are built
   with the builder's functions (`declaration_index.citation_links` and
   `finding_catalog.source_name`).
4. Restore the published bytes of `snapshot.json`, `receipt.json`, `run.json`,
   `stdout.txt` and `Extract.lean` in each reading directory, and check them
   against the published manifest.
5. Update the counts that depend on the readings: the gap count beside each
   reading link on the finding pages, `explicit_explanation_gaps` and
   `citation_links` in `coverage.json`, and the matching rows of `coverage.html`.
   Each published count must equal the published readings before it is replaced,
   and every reading link on a finding page must have the recognized form.
6. Write `evidence/declaration-index.json` and the explanation-gap inventory
   (`explanations.html`, `explanation-gaps.json`). Writing the inventory compares
   every saved reading with deterministic regeneration from its snapshot and
   every reader page with its reading and links.
7. Copy the current catalog assets (`assets/catalog.css`, `assets/catalog.js`),
   which the explanation-gap filters need. Add the explanation-gap link to the
   main navigation of the catalog's own pages (top level, `findings/` and
   `sources/`). A page's navigation may only gain links. Bundled originals and
   evidence are never rewritten.
8. Add a preview notice to the catalog, coverage, explanation-gap,
   original-verification and finding pages, and write `preview.html`,
   `preview.json`, a preview section at the top of `RELEASE-NOTES.md`, and a
   first line in `START-HERE.txt`. Reader pages carry no notice, because each
   reader page must equal its regenerated reading.
9. Run the static catalog audit and stop on any error. Run the requested browser
   route. Write the audit records, regenerate `SHA256SUMS.json`, check that the
   file-change table on `preview.html` matches the final site, and write the zip.

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
- Citation-link summaries before (if any) and after.
- Every file group with its added, replaced and unchanged counts.
- The static audit, the catalog browser audit with the preview-page checks, and
  the original-verification browser audit.

`release.json` and `original-verification.json` still describe the published
release. Their coverage no longer equals the preview's `coverage.json`, so
`scripts/publish_completion_release.py` rejects a preview.

## Browser routes

`--browser real` opens each page from the file system in Chromium. It runs
`scripts/audit_finding_browser.py` and `scripts/audit_original_browser.py`, then
checks the pages the preview adds or changes: the notice links to
`preview.html`; the preview page shows the gap count; the explanation-gap table
lists every reading with gaps and its filter for the most frequent reference
shows the inventory's count; and a reader page links a cited name to another
proof reading. The audits use Python assertions, so the script refuses a browser
route under `python -O`.

`--browser document-harness` loads each document with its local styles and
scripts inlined. Use it only where browser policy blocks `file://` navigation.
The record names the route as `direct-document-test-harness`. It does not test
navigation between files.

## Workflow

`catalog-preview.yml` runs on pushes to `claude/keen-archimedes-ihorkq` that
change `proofreader/**`, the script, the scripts it imports, its tests,
`benchmarks/reading-kpis/**` or the workflow, and on manual dispatch. It has no
schedule. It runs the preview tests, downloads the pinned release zip, checks
its SHA-256, and builds the preview with `--browser real`. It then extracts the
zip, checks every file against the packaged `SHA256SUMS.json`, runs the static
audit again, and requires the preview's gap steps and frames inside gaps, in
total and by rule, to equal `benchmarks/reading-kpis/current.json`.

Only a successful run uploads the zip, its digest and `summary.json` as the
`leanglish-catalog-preview` artifact. Every run uploads `summary.json`, audit
records and screenshots as `catalog-preview-diagnostics`. Both artifacts are kept
for 30 days. The workflow has read-only repository permission. It never creates
a release and never pushes.

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
automation groups are counted as gaps, so the step count is not a measure of
explained frames. The totals match `benchmarks/reading-kpis/current.json`.

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
release zip, including both browser audits and the zip, took 166 s on four CPU
cores. Two runs from the same checkout produced byte-identical zips.

## Limitations

A preview is a rendering of retained, unsigned observations. It does not
re-extract any snapshot, authenticate a receipt, or replay the original project.
The English is deterministic and regression-tested, not formally verified, and a
reading without gaps is not a certified complete proof. The browser audits
exercise selected pages and interactions, not every page. The citation-link and
explanation-gap limitations in `docs/CITATION_LINKS.md` and `docs/TRUST.md`
apply unchanged.
