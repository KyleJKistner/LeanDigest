# Bézout-frame companion

Open [`index.html`](index.html) directly in a browser. It is a self-contained,
offline reading of the supporting theorem
`OAI.ComplexCancellation.BezoutFrame.exists_frame`. All mathematical prose,
MathML rendering, source, selected claims, local contexts, proof paths, and
recorded native evidence are embedded. It makes no network request and runs no
Lean code. The browser's **Print / save PDF** action has a print layout.

The page states all hypotheses and gives a six-step proof over an arbitrary
Euclidean domain. It treats the zero gcd separately, justifies both nonzero
cancellations, constructs the witnesses, and checks all four equations.
The matrix placement is explicitly `[[a,d],[b,c]]`. Three integer examples use
exact `BigInt` arithmetic and illustrate both branches and negative inputs.

## What kind of reading this is

This is curated mathematical prose with reviewed source correspondence. Its
English is not formally certified. The 86 frame IDs are grouped editorially;
the group assignment does not establish formal semantics for the prose. This
is one supporting theorem, not the affine-cancellation headline theorem and
not a claim that the result is globally shortest.

The native observation reports checking the unchanged theorem body with Lean
4.34.1 and the exact Mathlib revision pinned by the OpenAI release:
`d13f23b723b8a846827a245b89c10fc7d3f11612`. The imports
`Mathlib.Algebra.EuclideanDomain.Basic` and `Mathlib.Tactic.Ring` replace the
original `OAI.Algebra.AffineCancellation.Model` import. The observation records
all 86 selected judgements and original proof paths checked, an exact repeated
snapshot, and rejection of wrong-path and false-claim controls. It does not
replay the full original OAI project. The records are unsigned.

The fresh snapshot is distinct from the historical v0.3 snapshot. The earlier
snapshot's byte comparison failed because printed binder names differed;
that failure remains in the native observation's `historical_comparison`.
The companion's source/claim inspector and downloadable deterministic reader
use the fresh snapshot throughout.

## Rebuild the page

From the repository root, using the project's Python environment:

```sh
python docs/companion/build.py
```

The builder reads `artifacts/companion/native/observation.json` and its `current/`
artifacts. It verifies the original source's pinned byte hash, the reviewed
snapshot's canonical hash, the context and transport hashes, the observation's
file identities, the unchanged theorem body, exact version/revision, and the four
native check results. It also checks deterministic reading regeneration and
replays the polynomial certificates.
It rejects changed or incomplete evidence before producing a page. It performs
no Lean execution or network call. `build-manifest.json` records the output and
input identities. A build with unchanged inputs is byte deterministic.

For an isolated checkout, `--evidence-root /path/to/native` can point to the same
native evidence directory, and `--output /path/to/index.html` changes the output
destination. These options do not weaken the checks or execute the input.

`template.html`, `style.css`, and `app.js` are the editable presentation sources.
The builder embeds the locally bundled KaTeX renderer with MathML output, so
the page needs no font CDN or remote script. Its license is retained in
`assets/KATEX-LICENSE`. The deterministic reader download is rendered from the
native run's `reading.json`; it remains separate from the curated prose.

## Reproduce the native check

Use a separately prepared, trusted Mathlib checkout at the exact revision above
with Lean 4.34.1 and all dependencies at their manifest pins. This command
executes Lean and therefore requires the explicit `--trust-project` flag:

```sh
python scripts/check_bezout_companion.py \
  --project /path/to/pinned-mathlib \
  --output /path/to/fresh-native-evidence \
  --trust-project
```

The native gate checks the packaged expected snapshot, source identities,
Mathlib and dependency revisions, and clean tracked dependency sources. It
fails closed if preflight or any required check fails. The output directory
must be separate from the Mathlib project. The script does not prepare or
download the toolchain/dependencies. Inspect its new observation before using
that evidence for another build.

## Verify the browser behavior

With pytest, Playwright, and Chromium installed:

```sh
PROOFREADER_REQUIRE_BROWSER=1 python -m pytest tests/reader/test_bezout_companion.py -q
```

These tests check evidence binding and tamper rejection, reproducible output,
exact source-line and frame selection, preserved local contexts, modal keyboard
navigation, the three integer cases, source/reader downloads, mobile layout,
and absence of HTTP(S) requests. They do not replace the native gate or certify
the English. An isolated worktree can set
`LEANDIGEST_COMPANION_EVIDENCE_ROOT=/path/to/native` for this test command.
