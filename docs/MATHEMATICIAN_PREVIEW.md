# Leanglish: research preview for readers of the OpenAI mathematics release

**Lean proofs, in mathematical English.**

The research preview is a static, offline-compatible index into selected genuine Lean
proofs from `openai/math` at commit `1581d4cbdd69a0faf34b2089614fe2a814316a6a`.
It is intended for mathematical readers who want a readable route through the proof
before opening Lean. It does **not** assert that the English text is a formal
certificate or that the entire OpenAI release has been translated.

## Start with Bézout-frame

That example uses a gcd split, Bézout coefficients and concrete witnesses. It has
no **recorded fallback** frames in the selected presentation, but the named
library lemmas remain dependencies. If any step looks suspicious, inspect the
source-bound path and local hypotheses rather than trusting the prose alone.

## How to read the evidence

- A **kernel-checked observation** means the extraction run checked selected
  judgements in Lean and checked their locations within the original proof term.
  It is reproducible but unsigned, and the browser does not authenticate it.
- An **unexpanded step** means the deterministic renderer could not produce a
  useful mathematical explanation for an inference. It retains the original
  information and displays the failure honestly.
- **Zero recorded fallback steps** is not proof that English faithfully expresses
  every dependency, nor that the output has been tested on human mathematicians.
- **Unknown denominator** means a selected module could not be enumerated or
  built. This must never be treated as zero declarations.

### Frozen OpenAI sample

GitHub Actions run `38792262410` used Lean 4.34.1 and the pinned Mathlib
revision. The source and imports were unchanged. Three selected OpenAI modules
completed and one timed out. Fourteen declarations were extracted, kernel-checked
and rendered; 13 had 796 recorded unexpanded steps between them. The failed
number-theory module has an unknown declaration denominator. This is **not**
representative sampling across the entire corpus.

The original source is visible at:
`https://github.com/openai/math/tree/1581d4cbdd69a0faf34b2089614fe2a814316a6a/lean`.
The original source license and notices are recorded in `THIRD_PARTY_NOTICES.md`.

## Reproduce on your own Lean project

```bash
python -m pip install .
python -m leanglish narrative-demo -o bezout.html
python -m leanglish serve

# Runs project code; opt in only with a trusted or isolated Lean environment.
python -m leanglish batch-narrative --help
```

The renderer makes no LLM calls. Feedback that is most valuable at this stage:
incorrect meanings, missing assumptions, genuinely confusing proof transitions,
and classes of proof that cannot be read without returning to Lean.

## Release gate

Before claiming general utility, require: repeatable exact-pinned extraction over
a broader precommitted sample, per-declaration gap accounting, expanded named
lemma statements and common rewrite patterns, and a blind mathematician study of
comprehension and review time. The success criterion is *improved review accuracy
and speed*, not merely a high extraction percentage.
