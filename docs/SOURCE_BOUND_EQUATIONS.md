# Source-bound equations and witnesses

The Bézout companion includes ten checked equation chains and two checked witness
tuples, in addition to the two cancellation sentences from the preceding change.
These fourteen passages have source-bound text certificates. The surrounding
explanation and the complete proof document are not certified by this work.

## Equation chains

`EquationEnglish.lean` defines a language for finite equality chains. Its formal
meaning requires **every adjacent equality**, not just equality of the endpoints.
For example, the meaning of `We have 0 = 1 = 0.` is false even though its endpoints
are equal. The audit module contains a kernel-checked countermodel for this case.

The determinant passage emitted for the original proof is:

```text
We have ((a * ((r * (z + 1)) + (s * y))) - (d * g)) = ((((a * r) * (z + 1)) + (s * (a * y))) - z) = ((((a * r) + (d * s)) * (z + 1)) - z) = 1.
```

The parentheses and ASCII operators preserve the represented syntax. The same
executable Lean renderer produces the displayed String and its UTF-8 bytes.
The parser consumes the complete sentence and rejects trailing material. The
serializer and meaning-preservation theorems apply to this defined language,
not to arbitrary English paraphrases or another renderer implementation.

The ten chains contain **19 adjacent source equalities**. They cover the four
zero-branch equations, the prerequisites for both nonzero cancellations, the
three prescribed products, and the determinant calculation. They do not explain
every tactic inside a `ring` or rewrite proof. Those original leaf proofs remain
inspectable dependencies, not invented explanations of how automation worked.

## Witness tuples

The second language, `WitnessEnglish.lean`, uses the defined term *frame*. A tuple
`(a, d, b, c)` is a frame for `(x, y, z)` precisely when all four equations hold:

```text
a*b = x,  d*c = y,  d*b = z,  a*c - d*b = 1.
```

The tuple order is part of this definition. It agrees with the original theorem's
witness order and the matrix `[[a,d],[b,c]]`. The native outputs are:

```text
The tuple (1, y, 0, 1) is a frame for (x, y, z).

The tuple (a, d, g, ((r * (z + 1)) + (s * y))) is a frame for (x, y, z).
```

The importer reads the four actual `Exists.intro` nodes in each branch. It does
not search for a different tuple proving the same existential statement. It
checks each chosen value at its original expression path and kernel-checks the
original final conjunction against the four equations for those exact values.
A separate theorem establishes that this conjunction provides the required
existential witness. A counterexample distinguishes existence of some valid
frame from validity of a particular incorrect tuple.

## Source correspondence and scope

`SourceEquations.lean` and `SourceWitnesses.lean` reuse the preceding source-path
and synchronous kernel-checking infrastructure without modifying it. The original
Bézout theorem body remains unchanged. The import context replaces
`OAI.Algebra.AffineCancellation.Model` with the pinned Mathlib imports and adds
the checking module. This is not a full OpenAI Lake-project or Comparator replay.

For equation chains, the importer follows the selected occurrence in the original
proof and opens only its enclosing binders and lets. It flattens explicit equality
transitivity nodes in their source order. A separate traversal of the closed
original expression determines the required leaf-path inventory. Omitting,
duplicating, or reversing a link is rejected, even when the final conclusion
could be proved another way.

Each leaf is checked against the original expression at its exact path, after
metadata erasure. Its denotation is reified into the arithmetic language and
checked again by Lean. Every adjacent proof is submitted to the kernel, as are
the meaning of the **literal output String** and the meaning of its bytes.
These declarations are closed over the actual original context. A hypothesis
from the nonzero branch does not become available in the zero branch.

Displayed scalar names are restricted to `x`, `y`, `z`, `g`, `a`, `d`, `r`, and
`s`. Only actual, uniquely identified in-scope variables and exact let values
receive these names. A missing variable's internal placeholder does not make it
available for reification. Let abbreviations such as `g`, `r`, and `s` have
kernel-checked denotations; their original definitions appear in the certificate
context. Arithmetic operations and their instances are checked as part of that
correspondence. Unsupported expressions fail rather than receiving generic text.

The importer remains a trusted metaprogram; its source traversal has not itself
been universally verified. The Lean kernel, compiler, dependencies, execution
environment, and declared language interpretation remain assumptions of the
result. Hashes establish consistency, not authenticity of unsigned observations.
No claim about unrestricted human interpretation or the upstream paper follows.

## Native verification

The new gate requires nine top-level contracts from each language module:

| Equation language | Witness language |
| --- | --- |
| `Chain.endpoints` | `Frame.witnesses` |
| `parseChain_chars` | `parseFrame_chars` |
| `read_render` | `read_render` |
| `Chain.render_injective` | `Frame.render_injective` |
| `rendered_meaning` | `rendered_meaning` |
| `certify` | `certify` |
| `readBytes_render` | `readBytes_render` |
| `rendered_bytes_meaning` | `rendered_bytes_meaning` |
| `certifyBytes` | `certifyBytes` |

These **18 contracts** are universal Lean theorems. The two introductory results
are axiom-free; the remaining inventories use only `propext`, `Classical.choice`,
and `Quot.sound`. No admission or `sorryAx` is permitted. Parser and serializer
lemmas supporting these contracts are also compiled.

The retained final local run in `artifacts/source-equations/` passed **43 compiler
invocations**: version checking, ten module checks, four positive/repeat source
runs, and 28 negative controls. Both positive records repeat byte for byte. The
arithmetic audit modules contain **47 executable guards**, distinct from the
universal proofs and not an independent human or separate-agent audit.

The negative source controls include changed interpretations, replaced proofs,
wrong witness values, swapped witnesses, altered text, lost or reordered equation
links, invalid source paths, escaped local binders, and false kernel claims under
both normal options and an attempted kernel-check bypass. Each must fail for the
specified reason and must leave no successful certificate record.

The source and environment pins are unchanged:

- OpenAI source: `1581d4cbdd69a0faf34b2089614fe2a814316a6a`.
- Source SHA-256: `d108afa98f200bfce183b8afc0af586b70734f7ad2cce1bc5e49853a2f555c6f`.
- Mathlib: `d13f23b723b8a846827a245b89c10fc7d3f11612`.
- Lean: 4.34.1.

Local execution used the exact retained Mathlib artifact accepted by the existing
cancellation gate. Its 13,818 source, compiled, and link entries were reconciled
before use. The isolated workflow repeats the gate with a fresh pinned checkout;
its final-commit result must be inspected separately. Failed development attempts
are not included as positive results.

## Reader integration

`proofreader/equation_text.py` checks the complete 92-file native evidence
inventory, exact command outcomes, module and gate hashes, and separately pinned
positive records. Rewriting a sentence and recomputing its declared hashes does
not make it pass. Missing, stale, or altered evidence stops the companion build.
This static reader check does not run Lean or authenticate an imported receipt.

Each of the six existing proof sections has a **Checked equations and witnesses**
panel. The source buttons select the exact original frame. The inspector shows
the literal checked sentence, its indexed context including let values, and the
native certificate record. Binder indices distinguish repeated hypothesis names.
The **Download checked text** action includes both preceding cancellations and
all new calculations with their records.

The six authored proof bodies, 63 formula strings, and 86-frame source inventory
remain unchanged. HTML escaping and browser `textContent` comparisons preserve
the tested literal output, but HTML, DOM semantics, browser rendering, and pixels
are not formally verified. The local container blocks real `file://` navigation;
an in-memory preview is not counted as offline-file acceptance. The GitHub browser
suite exercises actual offline navigation and downloads.

The 80 new static regression tests cover record pins, all source outcomes,
implementation identity, evidence inventories, consent, and attempted scope
promotion. Three additional real-browser tests cover the twelve literal passages,
exact source selection and certificate contexts, mobile layout, and the combined
download. These tests are not replacements for native proof checking.

## Reproduce

With a trusted checkout of the pinned Mathlib and its dependencies:

```sh
python scripts/check_source_equations.py \
  --project /path/to/pinned-mathlib \
  --lean /path/to/lean-4.34.1/bin/lean \
  --output artifacts/new-equation-run \
  --trust-project

python docs/companion/build.py
python -m pytest tests/test_source_equations.py -q
PROOFREADER_REQUIRE_BROWSER=1 python -m pytest tests/reader/test_bezout_companion.py -q
```

Use a new evidence directory for each run. The gate retains logs, original-source
drivers, records, and literal sentence files. New records require review before
changing the reader's frozen pins. Source outputs are byte deterministic; logs
can contain run-specific temporary paths.

## Remaining work

The next missing contract is a complete scoped proof document: statement and
quantifier introduction, the gcd case split, use of divisibility and Bézout
lemmas, scope discharge, and assembly of the checked passages into the theorem.
The existing local certificates do not certify every connective sentence or the
complete explanation of those dependencies. A formal document renderer must
preserve this structure instead of awarding a whole-proof label from a count of
successful passages. Its usefulness to mathematicians still needs direct testing.
