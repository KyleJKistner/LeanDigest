# Lean ProofReader 0.3.0 — executed validation

## Result

A substantial theorem from the OpenAI source collection now has a fully retained
mathematical reading, source-bound evidence, explicit cases and witness
construction, and independently replayable arithmetic certificates.

This is **not complete coverage of the OpenAI release**, a formal proof of English
fidelity, or evidence of measured mathematician comprehension. It is one retained
substantial acceptance case plus the earlier small examples.

## Observed results

| Check | Observed result |
|---|---|
| Local automated tests | 304 passed; 3 native Lean tests explicitly skipped |
| Retained substantial snapshot | Bézout-frame existence theorem; Lean 4.34.1 |
| Selected original proof judgements | 86, freshly submitted to the kernel |
| Independent original-expression paths | All 86 matched in the successful experiment |
| Repeated extraction within one Lean session | Identical complete snapshots |
| Altered snapshot formula | Re-extraction rejected it |
| Wrong source path | Rejected at frame 40 |
| False intermediate conclusion | Kernel rejected the substituted `False` judgement |
| Snapshot frames accounted for in the reader | 86 of 86 |
| Displayed steps | 59, after deterministic grouping |
| Arithmetic/rewrite passages | 16 exact polynomial certificates, all independently replayed locally |
| Export budget cuts in the retained example | 0 |
| Additional unexpanded frame shapes in that example | 0; named imported lemmas remain dependencies |
| UI | Chromium cases, witnesses, inspector, provenance, search/filter and mobile overflow tests passed |
| Wheel build and clean-target installation outside the source checkout | Passed; installed CLI generated the reader and replayed all 16 certificates |
| Full pinned OpenAI dependency build | Not run |
| Native Lean/Lake in this container | Unavailable; the three native integration tests did not run |
| Independent coding agents / remote GitHub repository / GitHub CI | Not executed / not created / not run |
| Certified English proofs / human comprehension studies | 0 / 0 |

The test total includes local unit tests and mocked transport tests. Those do not
substitute for actual Lean execution. The live remote tests are recorded separately.
Browser tests use direct document loading; no new browser-to-localhost end-to-end
claim is made. Native CI requires Lean and cannot satisfy its gate by skipping.

## Live 4.34.1 experiment

`artifacts/v0.3/bezout-4.34.1-valid.lean` is the exact submitted program:

```
b7d4fa6cbc3c9aac0160bdfa31556d2fd5e0ad1adcc693d55e7a7670583ff066
```

Request `fae2dc6e-9adf-4b54-b88e-612babf2b095` succeeded with no compiler errors or
failed declarations and emitted `PR_NARRATIVE_REPEAT_OK` and
`PR_NARRATIVE_MUTATION_REJECTED`. Each extraction first kernel-checks the selected
judgements and independently checks the original proof paths.

The SHA-256 of the complete exported JSON, retained in
`artifacts/v0.3/bezout.narrative.json` (canonical JSON, excluding final newline), is:

```
dad8ef23a231904f37b73979f8284ea3662ffe8f8cd30c79066856f2095b4dd7
```

The retained 4.34.0 record with only the recorded version updated exactly matched
this newly observed 4.34.1 output hash. This recovered the entire output without
another oversized transport. No other record fields were guessed or changed.
Both versions remain available. This is content verification against a tool
observation, not a signature or authenticated attestation.

The negative source programs and their hashes are also retained. Wrong path:
`116e4213b292dc64a594360399691ee461b4c3a8dc889e6d65d757f62dd62147`, request
`2bdcc3f2-8f49-45ed-abd6-c0aa7bcc6291`. Wrong intermediate conclusion:
`47d4a7254b16b43eb6f41946c7d9615df04f9220ca29948d72c134f0e161785e`, request
`fc74586b-c20a-4600-b7d8-2f75a47d956f`.

All source hashes are checked in the local regression suite. The packaged
exporter's code body matches the compiled experimental body after removing blank
lines; the exact experimental source is separately supplied for reproduction.

## What the source bound does and does not establish

The original theorem body is unchanged from `openai/math` at commit
`1581d4cbdd69a0faf34b2089614fe2a814316a6a`, file
`lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean`.

The experimental harness replaces the project-specific Model import with minimal
Mathlib imports. **Lean 4.34.1 now ran successfully; the full pinned project and
exact Mathlib revision were not verified.** Earlier 4.34.1 requests were rejected
while the service was transitioning; later requests succeeded. That version block
is no longer the current blocker.

The mathematical snapshot covers the main argument: zero/nonzero gcd cases,
divisibility witnesses, the Bézout relation, cancellation, four final witnesses,
and all four required equalities. Imported named lemmas are cited with their
instantiated statements; their entire proofs are not recursively expanded.
Formula strings still use Lean's pretty-printer. The English templates and that
pretty-printer have not been formally verified to preserve intended meaning.

A separate earlier 4.34.0 stress experiment retained the complete original term in
its remote constructor DAG and checked 760 selected term/type judgements. Its
summary and exact source are stored, but its oversized DAG output was **not**
fully transported back. It is not conflated with the 86-frame retained snapshot.

## Arithmetic checking

All 16 arithmetic/rewrite frontiers in the retained argument have local, exact
integer-polynomial certificates. The checker expands
`goal_difference = sum(multiplier * assumption_difference)` and compares every
coefficient. Context references and scalar variable names are bound to the
snapshot. Tests reject modified multipliers, altered assumptions, conditional
conjunction leakage, duplicate certificate counts, invented ring structure,
shadowed hypotheses, and invalid cancellation in rings of positive characteristic.

A passing arithmetic check does not authenticate its supplied assumptions.
Source replay is the separate provenance check. These certificates are small
Python-checkable artifacts, not a substitute for every Lean inference.

## Reproduce locally

```sh
python scripts/build_demo.py
python scripts/build_typed_demo.py
python scripts/build_narrative_demo.py
python -m pytest -q --junitxml=artifacts/v0.3/local-tests.xml
python -m proofreader narrative-demo -o reader.html
python -m proofreader check-narrative proofreader/data/bezout-snapshot.json \
  artifacts/v0.3/bezout-reader/reading.json \
  --certificates artifacts/v0.3/bezout-reader/polynomial-certificates.json
```

For actual Lean re-extraction, use the opt-in native or remote instructions in
`docs/NARRATIVE.md`. The CLI transports are unit-tested, and the exact metaprogram
is live-tested through Wolfram/AXLE. The complete installed CLI-to-AXLE network
round trip was not executed from this network-isolated container.

## Remaining acceptance work

Run the native integration gate with the pinned dependency environment, extend
beyond this selected algebraic proof to independent unseen proofs and domains,
add safe induction/recursor presentation, measure reader comprehension, and
execute full-corpus shards without losing failures or unknown denominators.
Full-corpus narrative extraction is not claimed by the one-theorem command.
