# Bézout proof document

`docs/companion/checked-proof.html` displays a complete canonical proof document
whose formal meaning is checked against the original Bézout proof. Its statement,
definitions, zero case, nonzero case, fourteen calculation/witness passages, and
conclusion are one certified text, rather than separately valid paragraphs with
unchecked connections. The canonical UTF-8 text is retained as
`artifacts/source-document/proof.txt`.

This is a narrow document language for one proof schema. It is not a translator
for arbitrary Lean proofs or unrestricted English. The separately authored
companion at `docs/companion/index.html` remains outside this document certificate.
Neither its prose nor a subsequent paraphrase inherits the new guarantee.

## Document syntax

`lean/ProofDocumentSyntax.lean` defines fourteen typed fields: ten equation chains,
two cancellations, and two frame assertions. It uses the existing component
grammars and adds fixed statement, definition, case, and conclusion paragraphs.
There is no field accepting arbitrary prose as a justified assertion.

The parser requires the prescribed sequence of sections and components. It
consumes the whole input, including separators and the final two newline
characters. Missing, duplicated, reordered, or additional fragments do not become
a valid instance of that syntax. Fuel is computed from the input length; bounded
parser calls fail when insufficient. The universal renderer/parser roundtrip
proves recovery of every representable document, not only the retained example.
A separate injectivity theorem prevents two represented documents from having
the same canonical String.

The fixed text is encoded as literal character lists in the Lean module. This
avoids expensive normalization of long String conversions during kernel checking.
The readable result is the emitted `proof.txt`; the implementation does not use
an unverified Python copy to generate the proof text.

## Semantics and composition

`lean/ProofDocument.lean` supplies the meaning of the complete document under an
arbitrary Euclidean domain. The source labels refer to the actual ring elements
and the actual Mathlib gcd and Bézout coefficient functions. A frame for
`(x, y, z)` means the ordered tuple `(a, d, b, c)` satisfies:

```text
a*b = x, d*c = y, d*b = z, a*c - d*b = 1.
```

The zero branch allows only names already introduced there. It asserts `x = 0`
and `z = 0`, all four calculations, and the particular zero-branch frame. The
nonzero branch asserts divisibility of `x` and `z` by `g`, and introduces `a` and
`d` only under their quotient equations. Its remaining nine component assertions
are interpreted in that environment. Both branches are required. A vacuously
true nonzero implication at `g = 0` is not enough.

`Document.sound` proves that these conditions imply the existential conclusion.
`text_implies_statement` and `bytes_imply_statement` lift the result to the entire
literal String and UTF-8 byte stream. `TextMeans` requires every displayed local
assertion, even though the frame assertions alone suffice to conclude existence.
The original leaf proofs used by ring normalization or rewriting remain checked
source dependencies; the text does not invent an account of their internal tactics.

## Source binding

`lean/SourceProofDocument.lean` builds the document from the existing source-bound
component checks. It additionally verifies the original `dite` case split on
`g = 0`, the gcd definition, the two divisibility proofs in the original
existential eliminations, the complete component occurrence inventory, and the
four nested witness constructions in each branch. Equation links retain their
original order. A duplicate or reordered equality is not accepted as the required
source passage even when another proof could establish the same conclusion.

Closing the branch requires more than passing its list of local hypotheses to
the kernel. The earlier local-passage certificates legitimately quantified over
facts such as `hxz`, `hbez`, and `hrel`. In the complete document they must not
remain assumptions. The document importer restores their original defining proof
terms as local definitions. It also restores the applied identity-lambda aliases
introduced by the source's `change ... at ha` and `change ... at hd` operations.
An independent original-expression traversal supplies the binder-origin paths
used to match each component's parameters to the restored context.

The final text and byte certificates have only the outer domain and its instance
as parameters. The variables `x`, `y`, `z` and the original hypothesis are
quantified in the document meaning. The branch-local facts have been discharged
from their actual source definitions. Omitting proof-let restoration or alias
restoration is rejected by the native negative controls.

The final declarations are:

```text
OAI.ComplexCancellation.BezoutFrame.exists_frame.documentEnglish
OAI.ComplexCancellation.BezoutFrame.exists_frame.documentUTF8
OAI.ComplexCancellation.BezoutFrame.exists_frame.documentConclusion
OAI.ComplexCancellation.BezoutFrame.exists_frame.documentOriginalStatement
```

The first two establish the literal text and byte meanings. The third derives the
statement from the text certificate. The fourth checks the unchanged original
theorem against that same statement. Certificates use the existing synchronous
kernel-submission helper with checking explicitly enabled. No record is emitted
before the final declarations are accepted.

## Verification

The retained local gate passed 31 compiler invocations: one version check, twelve
module checks, two positive document runs, and sixteen intended negative
rejections. The positive records and canonical proof bytes repeat exactly.

Eleven top-level universal contracts are required:

```text
parseFragments_chars       read_render
Document.render_injective  Document.sound
rendered_meaning           certify
text_implies_statement     readBytes_render
rendered_bytes_meaning     certifyBytes
bytes_imply_statement
```

Their printed transitive axiom inventories contain only `propext`,
`Classical.choice`, and `Quot.sound`. No admitted proof is permitted.
`ProofDocumentAudit.lean` adds thirty executable guards and two kernel-checked
countermodels distinguishing grammatical text and one vacuous branch from a
valid whole document. Executable guards and mutation tests are not universal
proofs or an independent human/agent audit.

The native mutations include a wrong case condition, unavailable names, a changed
frame goal, missing proof definitions, missing aliases, swapped branch proofs,
altered literal text, false kernel claims, an attempted kernel-bypass setting,
missing/duplicated/reordered source equations, absent/swapped witness branches,
and a changed cancellation prerequisite. Every negative must fail for its
specified reason and leave no successful document record.

The local static suite has 99 passing tests. Real-file browser navigation is
blocked by the local container's administrator policy. An in-memory preview
checked exact DOM text, fourteen source dialogs, keyboard focus, mobile width,
and no remote requests; it is not offline-file browser acceptance. The dedicated
GitHub workflow requires the real-file suite and a fresh pinned native replay.
Inspect the exact PR commit's artifacts before claiming remote acceptance.

## Reader and evidence

`proofreader/document_text.py` accepts only the pinned positive record and a
complete observation matching the current source modules, checking scripts,
source paths, import adaptation, logs, and expected outcomes. It also reconciles
the exact text bytes and repeated record. Changing the text and recomputing the
file hashes does not replace the reviewed positive-record pin. Missing evidence
stops the build; it does not retain a certification label.

`docs/companion/build_checked_proof.py` embeds the canonical text verbatim with
presentation-only spans. The browser tests compare its exact `textContent` and
proof download with the native bytes. Calculations and witness statements open
their original context; a separate record shows how proof definitions were
restored for document closure. This HTML/JavaScript implementation has regression
checks, not a formal browser-rendering theorem.

## Reproduction

With a trusted checkout of Mathlib at
`d13f23b723b8a846827a245b89c10fc7d3f11612`, its pinned dependencies, and Lean 4.34.1:

```sh
python scripts/check_source_document.py \
  --project /path/to/pinned-mathlib \
  --lean /path/to/lean-4.34.1/bin/lean \
  --output artifacts/fresh-document-run \
  --trust-project

python docs/companion/build_checked_proof.py
python -m pytest tests/test_proof_document.py -q
PROOFREADER_REQUIRE_BROWSER=1 python -m pytest tests/reader/test_checked_proof.py -q
```

Use a new evidence directory for each run. The optional retained-environment
argument accepts the previously pinned dependency archive, not arbitrary
archives claiming the same revision. The gate records failed attempts rather
than changing them into skipped successes.

## Trust boundary

The formal claim concerns the stated grammar and semantics. Its correspondence
to ordinary mathematical English is an explicit design interpretation, not a
theorem about every possible human reading of a phrase. A new wording requires
new rendering/meaning checks. General source import, more compact notation,
other proof structures, and comprehension evaluation remain separate work.

The source importer is a trusted metaprogram with per-instance kernel checks,
not a universally verified Lean frontend. The kernel, compiler, imported
dependencies and execution environment remain assumptions. The source theorem's
body is unchanged under explicitly substituted minimal Mathlib imports; this is
not a replay of the entire original OpenAI project or Comparator. The retained
observations are unsigned. Hashes bind checked bytes and detect inconsistencies;
they do not authenticate a malicious runner, compiler, or edited validator.
