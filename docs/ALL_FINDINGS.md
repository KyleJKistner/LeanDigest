# Leanglish — all documented OpenAI findings

Leanglish is an offline reading companion for the OpenAI mathematics release at
commit `1581d4cbdd69a0faf34b2089614fe2a814316a6a`. It connects each finding to the
upstream mathematical description, unabridged formalization scope, explicit
formal statements, original solution source, and available structured readings.

## Use the product

Download `leanglish-all-findings.zip`, extract it, and open `Leanglish/index.html`
in a browser. Reading the included material requires no installation, account,
API key, internet connection, or Lean runtime. Links to external manuscripts and
upstream repositories require a connection.

Search by mathematical topic, finding number, or Lean declaration. The initial
view includes all **242 findings with Lean scope documentation**. The broader
view retains all 372 findings in the upstream table of contents. Open a finding
to read its scope and assumptions before interpreting any claimed result.

## Exact coverage of this frozen release

* All 242 documented findings, all 416 comparison configurations, and all 602
  statement entries are included. Repeated entries correspond to 601 distinct
  targets: 536 theorem obligations and 65 definition references.
* All 413 directly referenced solution modules are included as original text and
  line-linked source pages. Imported dependency source and manuscript PDFs are
  linked upstream rather than being described as embedded English proofs.
* **109 of 536 theorem targets** have structured proof readings. Their retained
  native observations check 4,090 selected intermediate frames. All 28 previous
  statement/context extraction failures were recovered with the repaired exporter.
* The generated readings contain **1,357 explicitly unexpanded passages**.
  Availability of a reading does not mean every inference is explained.

## Verification boundaries

An elaborated comparison **specification is not a solution proof**. Specifications
intentionally contain placeholders. The site labels them separately from the
native solution-proof observations and never counts them as checked solutions.

The solution runs used unchanged source modules, Lean 4.34.1, and the nine recorded
shared upstream dependency revisions. They did not run the complete original Lake
project with every compatibility patch or its Comparator checks. Original source
hashes, executed drivers, compiler output, snapshots, receipts and arithmetic
certificates are retained. The observations are consistency-checked but unsigned.

Lean's compiler, source, pretty-printer, extraction implementation, transport, and
English renderer remain inside the trust boundary. No English proof has a formal
meaning-preservation certificate. No controlled mathematician comprehension study
has been completed. Upstream scope limitations are preserved, not upgraded into
claims about entire papers or longstanding conjectures.

## Reproduce and extend

The source is `KyleJKistner/LeanDigest`. `leanglish catalog --help` describes the
local-input builder; `leanglish audit-catalog SITE` checks the generated inventory,
all local links and source-line anchors. `.github/workflows/all-findings-release.yml`
rebuilds from frozen workflow artifacts and requires real offline browser tests
before packaging. It does not rewrite the application source during its run.

`coverage.json`, `release.json`, `static-audit.json`, `browser-audit.json` and
`SHA256SUMS.json` provide machine-readable accounting. All missing theorem readings
remain visible. The remaining 427 target attempts have a separate bounded native
queue; queued or failed attempts do not increase this release's coverage.
