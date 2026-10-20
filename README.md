# Leanglish

Leanglish shows the Lean proofs in the OpenAI mathematics release
(`openai/math` at `1581d4cbdd69a0faf34b2089614fe2a814316a6a`) as mathematical
English. Every displayed step is bound to a kernel-checked piece of the original
proof. The renderer is deterministic and makes no language-model calls.

## Example

`OAI.CompleteCrouzeix.main`, as rendered by the current renderer
(`source-math-en/0.7.0`) from its retained snapshot:

```text
Then UniversalBound 2 ∧ ∀ (C : ℝ), UniversalBound C → 2 ≤ C.

Proof.
Verify the 2 required conclusions.
  Prove ∀ (n m d : ℕ),
      0 < n →
        0 < m →
          ∀ (A : Matrix (Fin n) (Fin n) ℂ) (B : Fin (d + 1) → Matrix (Fin m) (Fin m) ℂ),
            ‖polynomialAt A B‖ ≤ 2 · rangeMaximum A B.
    Let n ∈ ℕ be arbitrary.
    Let m ∈ ℕ be arbitrary.
    Let d ∈ ℕ be arbitrary.
    Assume 0 < n.
    Assume 0 < m.
    Let A ∈ Matrix (Fin n) (Fin n) ℂ be arbitrary.
    Let B ∈ Fin (d + 1) → Matrix (Fin m) (Fin m) ℂ be arbitrary.
    [Explanation gap] By the project lemma complete_crouzeix_bound:
      ‖polynomialAt A B‖ ≤ 2 · rangeMaximum A B
      Use the hypotheses hn: 0 < n; hm: 0 < m.
  Prove ∀ (C : ℝ), UniversalBound C → 2 ≤ C.
    Let C ∈ ℝ be arbitrary.
    Assume UniversalBound C.
    [Explanation gap] By the project lemma optimal_constant:
      2 ≤ C
      Use the hypothesis hC: UniversalBound C.
```

Names are shown relative to the theorem's namespace (`OAI.CompleteCrouzeix`), and
each reading states which prefixes it omits. Each conclusion is proved inside its
own block, so a variable or assumption introduced for one conclusion never
appears to govern the next. An explanation gap marks a step whose justification
is not expanded in this reading; here, each gap cites a project lemma. The
published release shows the same step as `Apply
OAI.CompleteCrouzeix.complete_crouzeix_bound to the supplied arguments.`

Cited names become links in rebuilt catalogs: to the lemma's own reading where
one exists, otherwise to its declaration line in the original source. How many
resolve depends on what the catalog bundles. A full build from the upstream
source tree links 1,557 of the 1,762 cited project names (local measurement).
The catalog preview, which bundles only the solution modules and the pilot
supporting-lemma readings, links 495 of them. The published release has no
citation links. In the preview, `complete_crouzeix_bound` links to its
declaration line; `optimal_constant` is declared in a module the preview does not
bundle, so it links only in a full build.

## Coverage

| Measure | Value |
| --- | --- |
| Documented findings indexed | 242 of 242 |
| Documented theorem targets with a reading (release `leanglish-original-project-317dc31`) | 492 of 536 |
| Checked proof frames in those readings | 22,452 |
| Explanation-gap steps in those readings, published renderer 0.4.1 → current 0.7.0 | 7,587 → 5,014 |
| Words in those readings, 0.4.1 → 0.7.0 | 390,871 → 321,137 |
| Readings without any explanation gap | 0 |
| Supporting lemmas with a reading (dependency-cone pilot, not yet in a release) | 151 of 1,722 planned |
| Cited project names linked to a reading or source line (local full build) | 1,557 of 1,762 |
| Human comprehension study | Not yet performed |

The numbers for renderer 0.7.0 come from re-rendering the 492 retained snapshots
with `leanglish reading-kpis`; CI fails if
`benchmarks/reading-kpis/current.json` disagrees with the committed renderer.
Fewer gap steps does not mean fewer checked frames inside gaps: grouping
instance facts and automation certificates, and marking unchecked definitional
unfoldings as gaps, raised that count from 7,587 to 8,175. See
[Reading quality](docs/READING_QUALITY.md).

Top-level theorems in this corpus mostly assemble project lemmas, so most of the
mathematics is in the cited lemmas. The [dependency cone](docs/DEPENDENCY_CONE.md)
reads those lemmas as a separate denominator. Its first native pilot produced
readings for all 151 planned lemmas in 8 environment modules.

## Open the catalog

Download `leanglish-all-findings.zip` from the latest
[GitHub release](https://github.com/KyleJKistner/LeanDigest/releases), extract it
and open `Leanglish/index.html`. No installation, account, network connection or
Lean runtime is needed for the included material.

The published release uses renderer 0.4.1. The `catalog-preview.yml` workflow
re-renders that release with the current renderer, notation and citation links,
adds the 151 pilot supporting-lemma readings as a separate section, audits the
result, and uploads it as a workflow artifact. It does not publish a release.
See [Catalog preview](docs/CATALOG_PREVIEW.md).

## Verification

For each reading, a Lean exporter submits the selected intermediate statements
to the kernel and independently follows their recorded paths in the original
proof term. Arithmetic passages can carry integer-polynomial certificates that
are replayed without Lean. Re-extraction and `check_reading` bind the displayed
reading to the snapshot by deterministic regeneration.

The English renderer, display notation, Lean pretty-printer, extraction code and
saved run records remain inside the trust boundary. Records are unsigned. See
[Trust boundary](docs/TRUST.md), [Narrative format](docs/NARRATIVE.md) and
[Acceptance gates](docs/ACCEPTANCE.md).

## Limitations

- No reading in the corpus is free of explanation gaps. Most remaining gaps cite
  a project or library lemma.
- No English proof in the catalog is formally certified. A fixed-grammar Bézout
  document is a separate research result; see
  [Research tracks](docs/RESEARCH_TRACKS.md).
- No mathematician has evaluated the readings. Measured counts are not a
  readability result.
- 85 proposed one-line glosses for frequent library lemmas await human review and
  do not affect default readings. See [Glossary](docs/GLOSSARY.md).
- Comparison specifications contain placeholders and are never counted as checked
  solution proofs. Upstream descriptions are reproduced as claims.
- Several pinned CI inputs expire in November 2026. See
  [Input preservation](docs/INPUT_PRESERVATION.md).

## Measure readings

```sh
python -m pip install .
python scripts/fetch_reading_corpus.py /tmp/corpus
leanglish reading-kpis /tmp/corpus --baseline benchmarks/reading-kpis/current.json
```

The corpus is the 492 retained snapshots of the latest release, checked against
a pinned SHA-256. `--per-reading FILE` writes one row per reading.

## Build and develop

```sh
python -m pip install '.[dev,webtest]'
python -m pytest -q
leanglish catalog --help
leanglish audit-catalog /path/to/generated/site
python -m leanglish narrative-demo -o reader.html
```

The catalog builder reads frozen upstream metadata, the original source
inventory, statement observations and proof observations, and rejects missing
inventory members, changed source hashes, invalid proof paths and mismatched
receipts. It does not run Lean. Native extraction is explicit opt-in with
`--trust-project`; elaborating a Lean project may execute arbitrary code.

CI sets `PROOFREADER_REQUIRE_LEAN=1` for the native tests. A local run without
Lean reports those tests as skipped.

## Documentation

- Readings: [Reading quality](docs/READING_QUALITY.md),
  [Notation](docs/NOTATION.md), [Citation links](docs/CITATION_LINKS.md),
  [Glossary](docs/GLOSSARY.md)
- Catalog: [All findings](docs/ALL_FINDINGS.md),
  [Catalog preview](docs/CATALOG_PREVIEW.md)
- Corpus runs: [Dependency cone](docs/DEPENDENCY_CONE.md),
  [Input preservation](docs/INPUT_PRESERVATION.md),
  [Repository state](docs/REPOSITORY_STATE.md)
- Trust: [Trust boundary](docs/TRUST.md), [Acceptance](docs/ACCEPTANCE.md),
  [Narrative format](docs/NARRATIVE.md), [Exact-DAG contract](docs/KERNEL_IR.md)
- Research: [Research tracks](docs/RESEARCH_TRACKS.md),
  [Proof document](docs/PROOF_DOCUMENT.md),
  [Correct by construction](docs/CORRECT_BY_CONSTRUCTION.md)
- Project: [Supervisor checkpoint](HANDOFF.md), [Agent contract](AGENTS.md),
  [Editorial style](docs/STYLE.md)

Leanglish is the product name; the repository is `KyleJKistner/LeanDigest`. The
`proofreader` package, the `proofreader` command and the `lean-proofreader`
distribution name remain compatible.
