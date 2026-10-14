# Source-bound mathematical reading

Version 0.3 adds a second typed reading route. The exact constructor-DAG route
remains in `kernel.py`; the source-bound route does not pretend to be that route.

## Data path

1. A trusted Lean source or imported module is elaborated in an explicit version.
2. `lean/Narrative.lean` obtains the original theorem value and transitive axioms.
   It walks mathematical structure rather than expanding every computation.
3. Each selected term is closed over its actual local context and submitted as a
   fresh theorem declaration to the Lean kernel, with kernel checking enabled.
4. A separate raw-expression traversal follows each recorded path in the original
   proof. The selected expression must match the original subterm after erasing
   nonsemantic metadata. This step does not consult the reading prose.
5. The exporter emits a small snapshot of goals, contexts, proof paths, argument
   relationships, object expressions and a role for each selected frame.
6. `narrative.py` creates the statement, cases, witnesses, intermediate claims,
   calculations and dependencies. It accounts for every exported frame, including
   those absorbed into a larger display step. Unknown shapes remain unexpanded.
7. `polynomial.py` independently proves supported arithmetic passages by exact
   coefficient comparison over integer polynomials, using only recorded scalar
   equalities in the corresponding local context.

The complete original proof stays in the supplied Lean source and dependencies.
A 1,500-step raw explanation is not made readable by truncating the proof itself.
The snapshot is a selected presentation of an intact source proof, not a standalone
kernel certificate or a complete expansion of every imported lemma.

## What is trusted

The Lean compiler, project/imports, exporter metaprogram, pretty-printer,
mathematical dictionary, renderer, and recorded transport remain trusted.
Snapshots contain **pretty-printed formula strings**, not a formally interpreted
English language. A malicious custom pretty-printer could misrepresent formulas.
The source must therefore be trusted or independently audited. No English
meaning-preservation theorem or human readability study is claimed.

Fresh re-extraction checks the supplied snapshot against the source. A local
regeneration check protects against divergence between the supplied snapshot and
the displayed mathematical argument. Neither operation authenticates an imported
receipt. Reading a file performs no Lean execution and makes no network call.

## Arithmetic certificates

For a goal `L = R`, the checker verifies the integer-polynomial identity

    L - R = M_1 (A_1 - B_1) + ... + M_k (A_k - B_k).

Every `A_i = B_i` must be an available equality in the recorded local context;
variables must belong to one recognized commutative ring. This is not rational
cancellation: `2*x=0` does not justify `x=0` in an arbitrary ring. A bounded search
may use rational linear algebra internally, but certificates with noninteger
multipliers are rejected. Verification uses only exact polynomial arithmetic,
not the certificate search routine. This checker is tested, not formally verified.

Conditional statements are rejected as a whole before their conjunctions are
considered. In particular, `P → x=0 ∧ y=0` never yields unconditional `y=0`.
Shadowed assumptions cannot be recovered by their old printed name. Unsupported
notation or resource limits produce a visible gap, not an invented identity.

## Commands

Offline:

```sh
python -m proofreader narrative-demo -o reader.html
python -m proofreader narrative-read proofreader/data/bezout-snapshot.json \
  --source proofreader/data/bezout-original.lean \
  --receipt proofreader/data/bezout-receipt.json -o output/bezout
python -m proofreader check-narrative proofreader/data/bezout-snapshot.json \
  output/bezout/reading.json --certificates output/bezout/polynomial-certificates.json
```

Actual source replay through AXLE (explicitly sends the complete source):

```sh
python -m proofreader verify-narrative proofreader/data/bezout-snapshot.json \
  --driver proofreader/data/bezout-reproduce.lean \
  --backend axle --allow-remote -o output/recheck
```

The supplied driver is the exact successful experimental input; the CLI appends
an exact-version guard without changing any earlier source. A self-contained new
context can instead be passed to `extract-narrative`:

```sh
python -m proofreader extract-narrative YourNamespace.theorem \
  --context YourProof.lean --project YourTrustedProject --trust-project \
  --lean-version 4.34.1 -o output/new-proof
```

Native elaboration is not a sandbox and can execute arbitrary code. Remote
availability and installed dependency versions are service properties. An error,
timeout, changed import header, missing completion record, wrong theorem/version,
disallowed axiom or unequal re-extraction leaves a failed receipt. A previous
successful reading is not left at the canonical output path after a failed run.

## Scope of the current corpus integration

This new route selects one explicitly named theorem per command. The existing
whole-corpus kernel engine still enumerates and shards theorem constants; it has
not been replaced with an untested narrative batch runner. Full-project narrative
coverage, proof-valued definitions, and unformalized manuscripts remain separate
work. Selected cases, conjunctions and witnesses work; arbitrary recursors and
induction do not yet have complete mathematical verbalizations.
