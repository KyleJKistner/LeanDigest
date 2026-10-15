# Leanglish supervisor checkpoint — 0.3.0

## Current name and verified baseline

The user chose **Leanglish** as the product name. Keep the GitHub repository
`KyleJKistner/LeanDigest` and implementation/proof-format identifiers unchanged.
The preferred command is `leanglish`; `proofreader` remains a supported alias.
See `docs/NAMING.md`. Do not rewrite historical evidence to update branding.

Both jobs in GitHub CI run 38667444089 passed on commit
`2d6b60f01112f63ff56792b881e7a17678ddf558`, including native Lean integration.
Do not repeat the missing-manifest blocker: it and the native API/IO issues
were fixed before this rename. The complete pinned OpenAI project build is still
unvalidated; passing local-project integration does not establish that result.

## Do not repeat the previous blocker

The substantial Bézout proof is now fully retained as a source-bound mathematical
snapshot. Lean **4.34.1** became usable during the run. Do not claim only 4.34.0 is
available or repeat the huge raw-DAG/base64 transfer attempts.

Start with `docs/VALIDATION_V0_3.md` and `docs/NARRATIVE.md`. The primary files are
`lean/Narrative.lean`, `proofreader/narrative.py`, `proofreader/polynomial.py`,
`proofreader/narrative_io.py`, and `artifacts/v0.3/bezout-4.34.1-valid.lean`.

## Retained evidence

* Exact successful driver: SHA b7d4fa6cbc3c9aac0160bdfa31556d2fd5e0ad1adcc693d55e7a7670583ff066.
* Canonical snapshot: SHA dad8ef23a231904f37b73979f8284ea3662ffe8f8cd30c79066856f2095b4dd7.
* 86 selected proof judgements, 86 independently matched original paths, repeat
  extraction identical, changed snapshot rejected, wrong path rejected, false
  intermediate type rejected. Exact source programs and observations are stored.
* All 86 frames accounted for in 59 display steps. Sixteen arithmetic/rewrite
  passages have independently replayable integer-polynomial certificates.
* The proof body is unchanged; minimal Mathlib imports were adapted. The exact
  pinned mathlib revision and complete OpenAI build have NOT run.
* All observations are unsigned. Pretty-printing and English semantics remain
  trusted. Zero formally certified English proofs, no human comprehension study.

The earlier 760-judgement raw-DAG experiment was successful remotely but the
oversized raw output was not retained. Do not merge that experiment's count with
the retained snapshot's 86 judgements or infer full corpus coverage.

## Execution and transport

This container has Python, Chromium/Playwright and git, but no Lean/Lake or direct
outbound networking. Wolfram can call AXLE via URLRead. Use ExportByteArray JSON
and ImportByteArray responses. `ImportByteArray[gzip,{"GZIP","Text"}] strips a
final newline; use `{ "GZIP", "Byte" }` then UTF-8 decoding for exact sources.
Source checksum failures are transport failures, not failed Lean proofs. Large
base64 output is truncated. Prefer source-bound snapshots and compare hashes.

The packaged direct AXLE adapter has no chat-message transport limit. It requires
explicit user consent. A saved source driver can be used with `verify-narrative`
so namespace/notation/source changes cannot silently alter re-extraction.

## Next acceptance work

1. Preserve the passing native CI tests. Run the exact OpenAI 4.34.1 dependency
   pin; native smoke integration is not a complete dependency-pinned corpus build.
2. Independently select several unseen proofs in different areas. Do not expand
   only the current sample or add theorem-name-specific prose. Extend safe cases,
   induction, recursors, scope-aware abbreviations and lemma statement expansion.
3. Add an honest narrative batch engine. Current narrative commands select one
   named theorem; the existing whole-corpus engine still uses constructor DAGs.
   Preserve unknown denominators and every failure. v2 enumerates theorem
   constants, not all proof-valued definitions or informal manuscripts.
4. Benchmark mathematicians' ability to follow proofs and their review time.
   Readability and a formal interpretation of English are separate deliverables.
5. Independently audit pretty-printer overrides, shadowed names, arithmetic
   assumptions, kernel options, source changes, failure receipts and UI omissions.

## Commands

```
python scripts/build_demo.py
python scripts/build_typed_demo.py
python scripts/build_narrative_demo.py
python -m pytest -q
python -m leanglish narrative-demo -o reader.html
```

The agent work packages remain preparation only; no independent coding agents
ran. The repository is already published at KyleJKistner/LeanDigest. Use ordinary
commits on top of its current history; do not rerun repository creation.
