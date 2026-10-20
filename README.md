# Leanglish

The [canonical Bézout proof](docs/companion/checked-proof.html) includes a
source-bound certificate for its complete fixed-language document. See
[the document contract and reproduction](docs/PROOF_DOCUMENT.md) for its scope.
The separately authored companion is not covered by that certificate.

Leanglish connects the OpenAI mathematics findings to their formalization scope,
explicit statements, original Lean source, and the structured proof readings
available so far. The renderer is deterministic and makes no language-model API
calls. Reading does not execute Lean or send source to a service.

## Bézout frame companion

The [Bézout companion](docs/companion/index.html) presents a compact supporting
theorem from the OpenAI source: an explicit determinant-one construction over
a Euclidean domain. It includes the full statement, both cases, all four witness
equations, source/frame links, and the precise scope of its checking evidence.
Its mathematical prose is curated and independently reviewed; it is not yet a
formally certified English translation.

The architecture for that stronger claim is a typed explanation language with
Lean-proved inference rules and a deterministic controlled renderer. See
[Correct by construction](docs/CORRECT_BY_CONSTRUCTION.md) for the contracts,
trust boundary, and implementation sequence. A proof of a restricted logical
fragment does not certify the complete companion or the corpus.

## Finding catalog

The all-findings catalog indexes **all 242 findings with Lean scope documentation**
in the pinned release. It retains the broader 372-finding table of contents,
all 416 comparison configurations, and all **602 statement entries**. Those
entries correspond to 601 distinct formal targets: 536 theorems and 65 definition
references. It also includes the 413 directly referenced solution modules.

**216 of the 536 theorem targets have structured proof readings** in this frozen
release. Their retained native observations check 9,272 selected proof frames;
the published readings contain 3,005 explicitly unexpanded passages. All remaining
targets stay visible, with recorded attempt status and original source access.

The reader changes on this branch produce 3,001 explicit gaps for the same frozen
216 snapshots: 91 logical passages gain guarded explanations, while 87 previously
unmarked conjunction applications are now exposed as gaps. This is a separately
validated development result; it does not change the published archive.

This is complete **finding and statement access**, not complete English-proof
coverage. Comparison specifications intentionally contain placeholders; an
elaborated specification is never counted as a checked solution proof. The native
solution runs used unchanged modules, Lean 4.34.1, and exact shared dependency pins,
not a complete replay of the original Lake project or its Comparator checks.

[Reading guide and exact limitations](docs/ALL_FINDINGS.md)

### Open the catalog

Use the `leanglish-all-findings.zip` asset from the
[GitHub releases](https://github.com/KyleJKistner/LeanDigest/releases). Extract it
and open `Leanglish/index.html`. No installation, account, API key, network
connection, or Lean runtime is needed for the included material. External papers
and upstream dependency-source links require a connection.

The initial view shows all documented findings. Search by topic, title, finding
number, or Lean declaration; open a finding to inspect its scope, assumptions,
formal targets and proof-reading availability. `coverage.html` and the JSON
records separate indexing, statement elaboration, native checking, and explanation
coverage. The older 14-proof gallery remains a historical preview, not the current
coverage denominator.

## Build from local observations

Python 3.11 or newer:

```sh
python -m pip install .
leanglish catalog --help
leanglish audit-catalog /path/to/generated/site
```

The catalog builder reads the frozen upstream metadata, original source inventory,
statement observations, and proof observations. It checks their identities and
rejects missing inventory members, contradictory successful statements, changed
source hashes, invalid proof paths, and mismatched receipts. It does not run Lean.

`.github/workflows/all-findings-release.yml` retrieves the frozen input artifacts,
rebuilds the catalog, audits every local link, and exercises real offline file
navigation in Chromium before packaging. Packaging records the exact application
commit and hashes. The separate release job publishes only after the build passes;
it never overwrites an existing immutable version.

## Read the bundled demonstration

```sh
python -m leanglish narrative-demo -o reader.html
python -m leanglish serve
```

Open `http://127.0.0.1:8765`. The bundled demonstration starts with the Bézout-frame
argument. The full finding catalog is distributed separately; starting this demo
server does not imply all findings are bundled in the installed Python package.

## Verification model

The source-bound reading route records selected intermediate statements and their
locations in the original proof. The Lean exporter kernel-checks the judgements
and independently follows the recorded source-proof paths. The earlier exact-DAG
route remains available. Arithmetic passages can include independently replayable
integer-polynomial certificates.

Neither route formally verifies the natural-language renderer. The compiler,
source, pretty-printer, extraction implementation, transport, and terminology
remain within the trust boundary. Saved execution observations are unsigned.
There are **zero formally certified English proofs** and no completed controlled
human-comprehension study. Upstream descriptions are presented as upstream claims,
not independent assessments of the mathematical papers.

Actual Lean extraction is explicit opt-in with `--trust-project`; remote checking
requires `--allow-remote`. Elaborating a Lean project may execute arbitrary code:
consent is not a sandbox. The browser has no source-execution endpoint.

## Development

```sh
python -m pip install '.[dev,webtest]'
python -m playwright install chromium
python -m pytest -q
```

Native integration requires the pinned Lean project in `lean/`. CI sets
`PROOFREADER_REQUIRE_LEAN=1`, so the required export/replay/tamper tests cannot
pass by silently skipping. A local run without Lean labels these tests as skipped.

Further documentation: [architecture](docs/ARCHITECTURE.md),
[narrative format](docs/NARRATIVE.md), [exact-DAG contract](docs/KERNEL_IR.md),
[trust boundaries](docs/TRUST.md), [historical validation](docs/VALIDATION_V0_3.md),
and [supervisor checkpoint](HANDOFF.md).

Leanglish is the product name; the repository remains `KyleJKistner/LeanDigest`.
The `proofreader` Python package, legacy CLI, distribution name `lean-proofreader`,
and historical proof-format identifiers remain compatible. New catalog commands
are exposed through the public `leanglish` entry point.
