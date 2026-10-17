# Leanglish 0.4.1 — broader documented-proof access

Leanglish is an offline mathematical reading companion to the pinned OpenAI
mathematics collection. Extract `leanglish-all-findings.zip` and open
`Leanglish/index.html`. No account, API key, installation or Lean runtime is
needed to read the included material.

## Finding access and proof coverage

All 242 findings with Lean scope documentation are accessible, together with all
602 comparison-statement entries, all 416 comparison configurations and original
source for all 413 directly referenced solution modules. The broader catalog
retains all 372 findings. This is documentation access, not a claim that each
proof has been completely explained.

The release incorporates 107 additional receipt-validated proof readings from the
retained breadth-run snapshot: **216 of 536 theorem targets** now have structured
readings, covering 128 findings. For 90 findings, every listed theorem target has
a reading. There are 9,272 selected source-bound frames, and 3,005 explicitly
unexpanded passages. Missing readings remain visible. Definitions (65 distinct
references) and specification placeholders are not counted as solution proofs.

The new progress page records every target in the 427-target breadth queue. At
this frozen collection, 223 targets have reports, 107 have new readings, and 204
have no retained artifact yet. Among reported targets, 61 have build failures,
52 were not attempted within their shard deadline, one was not extracted before
its deadline, and two failed extraction. A missing artifact does not establish
whether its job eventually succeeded or failed. These are pipeline states, not
verdicts on the validity of the mathematics.

## Reading improvements

Exact supported conjunction eliminations now read as obtaining the two component
facts from a proved conjunction. Identity wrappers preserve their supplying proof
without adding a false explanation gap. On the same 216 retained snapshots,
237 conjunction gaps were removed across 70 readings (3,242 to 3,005 remaining
gaps). Identity handling is separately regression-tested; it did not reduce the
gap count in this frozen snapshot. The transformations keep all source-frame
ownership and assumption scope; unsupported shapes remain explicitly unexpanded.

Extraction now has an explicit, bounded heartbeat option for difficult terms,
recorded with the wall-time budget in its observation. Failed native compiler
output is retained for diagnosis. Increasing an execution budget is not a claim
that the corresponding target has passed.

## Evidence and limitations

Upstream commit: `1581d4cbdd69a0faf34b2089614fe2a814316a6a`.
The original source archive and complete Lean-directory inventory are checked.
Native solution runs use unchanged source, Lean 4.34.1, and the recorded shared
upstream dependency revisions. They did not build the entire original Lake
project with every compatibility patch or run Comparator for the full release.

Source hashes, drivers, compiler output, snapshots and receipts are retained.
They are checked for consistency, not cryptographically authenticated. The Lean
compiler, source, pretty-printer, extraction code, transport and English renderer
remain inside the trust boundary. No formally certified English proof or controlled
mathematician-comprehension result is claimed.

`progress.html`, `breadth.json`, `coverage.json`, `release.json`, the static and
browser audits, and `SHA256SUMS.json` give reproducible accounting. The original
0.4.0 release is not overwritten. This product still needs additional readings
and better explanations of long automated arguments to meet the full goal.
