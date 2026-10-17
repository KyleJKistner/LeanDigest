# Leanglish

**Lean proofs, in mathematical English.**

Leanglish connects the OpenAI mathematics findings to their formalization scope,
explicit statements, original Lean source, and the structured proof readings
available so far. The renderer is deterministic and makes no language-model API
calls. Reading does not execute Lean or send source to a service.

## All documented findings: version 0.4.0

The all-findings catalog indexes **all 242 findings with Lean scope documentation**
in the pinned release. It retains the broader 372-finding table of contents,
all 416 comparison configurations, and all **602 statement entries**. Those
entries correspond to 601 distinct formal targets: 536 theorems and 65 definition
references. It also includes the 413 directly referenced solution modules.

**109 of the 536 theorem targets have structured proof readings** in this frozen
release. Their retained native observations check 4,090 selected proof frames;
the generated readings contain 1,357 explicitly unexpanded passages. All remaining
targets stay visible, with recorded attempt status and original source access.

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
