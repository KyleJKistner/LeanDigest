# String and UTF-8 serialization

This extension closes a specific gap in the earlier logical prototype: the
meaning-preservation theorem now reaches **actual Lean `String` values and their
serialized UTF-8 bytes**, not just an abstract list of tokens. It is an additional
canonical renderer, not a certification of the existing Python renderer,
`Sentence.display`, HTML, or the curated Bézout companion.

The implementation is `lean/ControlledEnglishText.lean`. It imports the existing
intrinsically typed logical language and Lean's pinned string/decimal library.
The new renderer is executable Lean code; the example files are emitted by that
same code, not by an unverified implementation in another language.

## Correctness requirements

For the supported local logical nodes, the chain is:

```text
Typed Derivation(context, goal)
        │ extract a supported local Rule
        ▼
Sentence with explicit premises and exact conclusion
        │ proved token renderer → proved String serializer → UTF-8
        ▼
Canonical bytes, including the exact proposition references
        │ checked decoder and parsers
        ▼
The same Sentence
        │ compare with the intended typed Rule, not merely any true inference
        ▼
Exact node conclusion + premises justified in their scopes + sentence validity
```

Three distinct requirements are essential here. Parsing establishes that the
text expresses a sentence in the grammar. Rule soundness establishes that the
inference is valid. **Alignment establishes that this is the intended inference,
not a different true sentence.** The `accepted_root_aligned` theorem combines
all three for a supported node in the typed intermediate representation.

This last qualification matters: the module does not yet import arbitrary Lean
proofs or establish original proof-occurrence identity. A typed node deliberately
constructed in Lean is not, by itself, evidence that a corresponding node was
extracted from the original OpenAI proof. That importer remains a separate gate.

## Required Lean theorems

Fourteen named theorem inventories must be present after compiling the module:

| Contract | Universal checked result |
| --- | --- |
| `lex_render` | Lexing a serialized token sequence recovers every token exactly. |
| `render_injective` | Two different token sequences cannot serialize to the same String. |
| `readFormula_render` | The complete String reader recovers the exact formula. |
| `readSentence_render` | The complete String reader recovers the exact inference sentence. |
| `rendered_formula_meaning` | The rendered String means exactly the represented formula under the supplied atom environment. |
| `rendered_sentence_meaning` | The rendered String means exactly the represented inference under that environment. |
| `accepted_rule_sound` | Text accepted for a particular supported rule has a valid inference semantics. |
| `accepted_root_aligned` | Accepted text agrees with the supported typed node's conclusion and its scoped premises, and is valid. |
| `decodeUTF8_encode` | UTF-8 decoding recovers an encoded Lean String. |
| `lexBytes_renderBytes` | Lexing serialized bytes recovers the exact token sequence. |
| `renderBytes_injective` | Different token sequences cannot serialize to the same byte array. |
| `readSentenceBytes_render` | The complete byte reader recovers the exact inference sentence. |
| `rendered_bytes_meaning` | Serialized sentence bytes retain the sentence's declared logical meaning. |
| `rendered_rule_bytes_sound` | The actual emitted bytes of a supported rule express a valid inference. |

Additional supporting theorems prove exact word consumption, decimal-reference
roundtripping, sufficient lexer fuel, and the rule-acceptance equivalence. The
fourteen are the required top-level contracts, not the total number of lemmas.

The universal results are Lean kernel-checked proofs. Their printed transitive
axiom inventories contain only `propext`, `Classical.choice`, and `Quot.sound`.
They are **not axiom-free**. No admission or `sorryAx` is permitted. These results
assume the pinned Lean kernel, standard library, and the explicit formal meaning
of the grammar. They are not a theorem about unrestricted human interpretation.

## Grammar

Atoms are canonical decimal references such as `@0` and `@17`. Their meaning is
entry zero or seventeen in the **same typed environment** `Fin n → Prop` used by
the logical derivation. The complete formula reader checks `index < n`. It never
treats a user-supplied display name or a pretty-printed Lean expression as a proof
of the atom's meaning.

Formula words are:

```text
@INDEX
False
both FORMULA and FORMULA end
either FORMULA or FORMULA end
if FORMULA then FORMULA end
```

Inference sentences have one, two, or three premises:

```text
From PREMISE infer CONCLUSION .
From PREMISE with PREMISE infer CONCLUSION .
From PREMISE with PREMISE with PREMISE infer CONCLUSION .
```

**Every word has exactly one following ASCII space, including the final period.**
For example, the full serialized String for a second projection is:

```lean
"From both @0 and @1 end infer @1 . "
```

The grammar is intentionally strict and visibly delimited. The final space is
part of the checked byte stream; trimming or reflowing is not silently included
in this theorem. The canonical text is the inspectable evidence representation,
not a claim that this syntax is the best mathematical prose. A more natural
surface must obtain its own semantics-preserving renderer and parser contract,
rather than inheriting certification because it looks similar.

The lexer rejects missing delimiters, unknown words, leading-zero atom aliases,
signs, and alternative whitespace. The UTF-8 decoder rejects invalid encodings.
The complete sentence reader rejects trailing tokens and out-of-bound atoms.
The resource-bounded parsers fail on insufficient fuel rather than truncating a
successful result. External input-size and execution-resource limits still belong
to the application hosting these functions; formal termination is not a denial-
of-service guarantee.

## Inference alignment

The following two sentences describe valid inferences, but only the first is the
specified second-projection rule for `P ∧ Q`:

```text
From both @0 and @1 end infer @1 .
From False infer @1 .
```

`accepts` rejects the second when the intended rule is `.andRight P Q`. It also
rejects changing the conclusion to `@0`, replacing conjunction with disjunction,
or silently swapping the two atom references. Validity is not substituted for
exact explanatory alignment.

Conversely, `From @0 infer @1 .` is grammatical but is false when `@0` is true and
`@1` is false. A kernel-checked countermodel in `ControlledEnglishTextAudit.lean`
exhibits this distinction. The gate never awards validity merely because a
sentence parsed successfully.

For case analysis, the serialized premises include both branch implications.
Those implications are established under separate branch scopes in the typed
derivation. The text layer does not flatten one branch's local assumption into a
fact available everywhere.

## Validation

`lean/ControlledEnglishTextAudit.lean` is a separately compiled adversarial suite.
It is **not an independent human or separate-agent audit**. It contains 44 native
executable `#guard` assertions, applications of the universal theorems, and a
kernel-checked semantic countermodel. The concrete `#guard` assertions are
regression executions, not universal mathematical theorems.

The guards cover all token constructors, multi-digit atoms, altered conclusions,
unrelated valid inferences, numeric aliases, Unicode confusables, zero-width
characters, noncanonical whitespace, malformed logical syntax, insufficient
fuel, out-of-bound atoms, trailing material, and malformed UTF-8. A finite suite
is not exhaustive security verification; the universal roundtrip and semantic
claims come from the separate theorems.

`scripts/check_controlled_text.py` provides the native gate. It:

- Requires explicit execution consent and a new or empty evidence directory.
- Copies all five modules into a fresh temporary workspace, compiles new objects,
  and retains every command's exit code and output. Missing Lean, a wrong version,
  a compilation error, or a timeout is a failure, never a skipped success.
- Requires every named theorem inventory, rejects admissions and non-allowlisted
  axioms, executes the adversarial suite, and emits eight rule examples twice
  using the Lean implementation. Both complete file inventories must match byte
  for byte, and manifest text must match the actual written UTF-8 bytes.

The gate itself has 32 Python regression tests in
`tests/test_controlled_text_gate.py`. The deliberately fake executables in those
tests falsify error handling; they are not used as native theorem evidence.

The first local clean-workspace run passed all seven compiler invocations, all
fourteen required contracts, all 44 guards, and the repeated eight-example check
with Lean 4.34.1. The standard local browser tests encountered the environment's
`ERR_BLOCKED_BY_ADMINISTRATOR` restriction on `file://` navigation; that failure
was not suppressed or called a pass. Real offline browser acceptance remains
with the existing GitHub Actions job. Check the exact PR commit's CI result
before claiming remote acceptance for this extension.

Evidence is an **unsigned execution observation**. File hashes establish
consistency and bind reports to the retained bytes; they do not authenticate
an adversarial compiler, runner, dependency, or edited log. The gate assumes the
checked-out Lean modules and the execution environment are trusted. It does not
turn arbitrary externally supplied logs into proof certificates.

## Reproduce

With Lean 4.34.1 installed, from the repository root:

```sh
python scripts/check_controlled_text.py \
  --lean /path/to/lean-4.34.1/bin/lean \
  --output artifacts/my-checked-text-run \
  --trust-project

python -m pytest tests/test_controlled_text_gate.py -q
```

The output includes `observation.json`, the command logs, and `examples/` with
eight canonical `.txt` files plus their manifest. Repeat runs use a new directory;
failed observations are not overwritten. Execution logs may contain temporary
paths. The byte-determinism claim is for emitted example files, not for every
field of an execution report.

The isolated workflow `.github/workflows/checked-text-boundary.yml` checks the
same command on a clean runner using the official Lean 4.34.1 archive pinned by
SHA-256. It uploads source and checking evidence, including failure logs, and
does not modify the existing full-project or exporter workflows.

## Limitations

This component does not establish complete English proofs, arithmetic
explanations, quantifiers, equality, induction, arbitrary dependent Lean terms,
original-proof import, the atom-label frontend, HTML escaping/layout, browser
pixels, or improved human comprehension. Assumption-reference and implication-
introduction prose still return `none` at the existing local-rule extraction
boundary. A complete scoped proof-tree rendering contract is still needed.

The Bézout companion remains a curated and separately reviewed six-step
explanation with its own native source-judgement evidence. Its nonzero
authorizations, gcd identities, witness construction, and arithmetic certificates
are **not instances of this small propositional grammar**. Neither its English
acceptance flag nor the corpus's coverage counts increase because this new module
compiles. The published release remains frozen.

The next architectural milestone is to combine an original-occurrence-bound
importer, a complete scope-aware document language, and one actual arithmetic
rule family. Each mathematical statement in the polished reader must then be
rendered from that representation; optional intuition stays visibly outside the
certified assertion layer. Readability and relevance to the reader's goals need
explicit evaluation even after logical alignment is proved.
