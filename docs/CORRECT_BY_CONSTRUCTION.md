# Explanation compiler architecture

## Design

Leanglish should compile Lean proofs into a small, typed mathematical explanation
language and render that language deterministically. Mathematical statements and
inferences must be constructors with semantics, not strings that happen to look
right. The explanation compiler may be complicated, heuristic, or model-assisted;
the acceptance checker must be small, explicit, and fail closed.

This is the architectural target, not a description of the current complete
product. The present source-bound route records checked judgements as
pretty-printed formula strings. Its deterministic regeneration check and its
polynomial certificates are useful evidence, but do not prove the interpretation
of the whole English document. Promote an individual document only after its
end-to-end obligations are discharged for its claimed fragment. Corpus-wide
English acceptance remains false until the entire declared inventory passes.
A local mechanized prototype does not upgrade unrelated readings.

The first presentation case is the Bézout-frame supporting theorem from the
pinned OpenAI source. Its companion is curated mathematical exposition with
source/frame links and independently reviewed algebra. It is a test case for the
architecture, not a claim that arbitrary English or the entire OpenAI result has
been certified. See [the companion](companion/index.html) and
[the independent audit](SWARM_READER_AUDIT.md).

## Correctness requirements

| Contract | What an acceptance result must mean | What does not establish it |
| --- | --- | --- |
| Mathematical soundness | The interpreted explanation derives precisely the declared proposition in precisely its context. | A fluent sentence, a theorem name, or a green build unrelated to that sentence. |
| Correspondence | Each claimed source step or compression is anchored to the original elaborated proof and its scope. | Producing some other proof of the same proposition. |
| Rendering fidelity | Parsing the canonical displayed language recovers the checked meaning, including binders, types, and side conditions. | Regenerating identical bytes with the same possibly incorrect printer. |
| Explanatory coverage and relevance | Every necessary branch, witness obligation, and dependency has a visible account or an explicitly declared leaf; the main reading connects to its conclusion. | A small gap count, all terms having a label, or an arbitrary shorter proof. |
| Human usefulness | Mathematicians can understand, check, and find mistakes with acceptable effort. | Any of the previous four contracts, alone. |

"Correct by construction" should refer to an accepted object in a specified
language under a specified trust boundary. It cannot be an unqualified guarantee
about whatever a person might infer from unrestricted English.

## Representation

### Original proof and environment

Keep the fully elaborated declaration, its exact type, universe parameters,
transitive axiom inventory, dependency lock, Lean version, and source identity.
An original proof address is an occurrence path from its root, with its enclosing
binders. A shared DAG node ID or a printed variable name is not a scope identity.

The existing exact-DAG route and source-bound route provide useful pieces of
this layer. Source snapshots avoid transporting enormous terms, but their
pretty-printed strings must not become the semantic authority for the new layer.
Use typed expression references resolved in Lean. Names and notation are display
metadata with a separately checked binding to those expressions.

Rechecking a theorem under substituted imports is a separate observation from
replaying the original project. Record that distinction in machine-readable
evidence. Pinning the substituted Mathlib revision makes the adaptation
reproducible; it does not erase the adaptation.

### Typed explanation representation

An explanation judgement has the form `Γ ⊢ E : P`. Here Γ is a typed context with
stable binder identities, P is a formal proposition, and E is an explanatory
derivation. It includes the following kinds of node, added incrementally:

- **Assume / fix / define:** open a proposition assumption, an object binder, or
  a typed let-binding. The body records exactly which scope is open.
- **Apply a lemma:** bind its fully instantiated statement and all proof
  premises; account for implicit arguments and typeclass instances.
- **Cases / induction:** record the discriminator or induction principle and
  every required branch, with the hypotheses available only in that branch.
- **Choose / construct:** bind existential witnesses and all witness conditions;
  elimination and introduction are distinct operations.
- **Calculate / rewrite:** record a relation, endpoints, direction, and the
  congruence or transitivity rule. Rewriting through dependent types needs its
  own explicit rule; it is not a textual replacement operation.
- **Cancel:** expose the factor and its nonzero or cancellability premise.
- **Certified computation:** carry a certificate whose checker has a Lean
  soundness theorem for the declared arithmetic domain.
- **Use a dependency:** show the actual instantiated lemma statement and where
  its hypotheses were obtained. Expansion may be collapsed in the initial view,
  but the dependency contract and proof must remain inspectable.

`Unexplained` is an observation node, not a constructor of a complete verified
explanation. Partial documents can contain such observations, but cannot acquire
the complete-explanation status. A referenced theorem can be an allowed boundary
leaf only under an explicit dependency policy. The policy must list the allowed
background library or particular dependencies; it cannot silently accept every
named lemma.

The runtime may serialize untrusted candidate JSON. Acceptance elaborates it into
the indexed datatype or checks a certificate that produces an inhabitant of that
type. Do not trust a JSON field saying `verified: true`.

### Exposition plan

Mathematical proofs rarely become readable by exposing every kernel reduction.
The plan chooses a dependency-closed slice, names intermediate results, and
groups low-level steps. Each transformation has a local obligation:

- An omitted administrative node is accounted for by an allowed transformation.
- A displayed result has all of its prerequisites in scope or explicitly linked.
- A moved result contains no free dependency on a binder unavailable at its new
  location. Repeated variable names cannot satisfy this requirement.
- A calculation chain has exactly matching intermediate endpoints and relations.
- A compressed block has the same input context and output claim as the source
  block, with a checked source correspondence witness.
- Every retained step belongs to a backward dependency slice of the goal, or is
  explicitly marked as supporting context, an example, or motivation.

The last property is a useful formal relevance condition. It does not prove
that every retained lemma is the best pedagogical choice, or that the shortest
possible proof is the most useful one.

For an original-proof companion, source correspondence is not optional. Lean's
proof irrelevance means equality or definitional equality between proofs of the
same proposition cannot establish that they are the same argument. Preserve
structural comparison of raw expressions after the explicitly permitted metadata
erasure, or check a declared source-to-plan transformation relation. If the system
constructs a new proof, label it as an alternative proof instead of silently
presenting it as a reading of the original.

### Controlled mathematical English

Render semantic constructors using a versioned grammar. The grammar controls
negation scope, quantifiers, implication direction, witness conditions, and
reference binding. A formatter may choose line breaks and typography without
changing the semantic token stream.

A mathematical atom must be a typed symbol/formula reference, not an arbitrary
string that can inject a quantifier or end a sentence. A symbol table records
the expression, type, binder ID, notation policy, and display name. Printed
names must be fresh within their relevant scope; the resolved binder identity
survives renaming. Subscripts, Unicode confusables, omitted coercions, and
notation precedence are part of the display contract.

The complete target is a left inverse for the actual canonical serialization:

```
parseCanonical (renderCanonical E) = some E
meaning (renderCanonical E) = interpret E
```

A theorem about a list of semantic tokens is a useful intermediate milestone.
It does not yet prove a string lexer, HTML escaping, Unicode display, browser
DOM, or a reader's understanding. The proof boundary must state which of these
functions is covered. If Python or JavaScript reimplements the proved renderer,
that new implementation needs a checked refinement or must remain in the trusted
base. Prefer shipping output from the proved implementation, plus a small
verified parser for the canonical content, over maintaining several equivalent
printers by convention.

The HTML application provides navigation, collapsing, highlighting, and evidence
drawers around the canonical mathematical content. It must not independently
regenerate or paraphrase claims. A machine-checkable canonical export must remain
available. Browser and accessibility tests assess the presentation layer; they
are not substitutes for the formal rendering theorem.

## Proof obligations

The implementation should make each obligation a separate gate with its own
version and evidence. The core soundness theorem is:

```
∀ Γ P (E : Explanation Γ P), Realizes ρ Γ → Denotes ρ P
```

This establishes validity of the interpreted derivation for all interpretations
of its permitted atoms. To connect that theorem to a particular Lean theorem,
the atom environment, typed formulas, binder structure, and root proposition
must be resolved against that theorem's actual Lean environment. An abstract
soundness theorem with arbitrary atom IDs does not perform this connection.

Further obligations are:

1. **Source binding:** the recorded paths resolve to the original subterms under
   the correct context and the declared relation to the explanation is checked.
2. **Transformation preservation:** each accepted plan rewrite preserves the
   context, proposition, source correspondence, and dependency accounting.
3. **Rendering left inverse:** the parser recovers the exact checked canonical
   explanation, including all semantic annotations.
4. **Certificate soundness:** successful arithmetic, normalization, and rewriting
   certificates imply their stated proposition in their explicit algebraic
   domain. A Python polynomial checker alone does not prove this theorem.
5. **Coverage closure:** all required branches, side conditions, and goals reach
   either a checked constructor or a declared, inspectable dependency leaf.
6. **Artifact binding:** the displayed artifact, grammar, environment, evidence,
   and source identities match. A hash establishes consistency, not authenticity
   or mathematical truth. A fresh trusted run supplies a new observation.

The global claim must be the intersection of these gates for the actual
document. Do not infer it from a successful component proof or from a receipt
created by an older version of a component.

## Determinism

Make the renderer and plan selector pure functions of explicit inputs. Include
the following in a content-addressed build key:

```
source tree + dependency lock + Lean/exporter version + theorem identity
+ explanation IR schema + transformation policy + vocabulary policy
+ grammar/renderer version + presentation options
```

Traverse declarations and dependencies in a stable order. Choose fresh names by
a deterministic rule. Specify normal forms, tie-breaking, maximum expansion
budgets, and all other resource policies. A budget exhaustion is an explicit
partial result, not a shorter success. Do not let time of day, a network request,
an unpinned cache, or hash-table iteration order affect the canonical reading.

One may use a model offline to propose a better plan or a new grammar template.
The proposal has no authority: acceptance requires the same checked obligations,
and the accepted object and policy become versioned inputs. The production
rendering path needs no model call. A seed alone is not a guarantee of model
determinism or semantic correctness.

## Bézout implementation

The theorem assumes a Euclidean domain R and elements x, y, z satisfying
`x*y = z*(z+1)`. It constructs a, d, b, c with all four equations:

```
a*b = x     d*c = y     d*b = z     a*c - d*b = 1
```

The explanation plan has two branches. If `g = gcd(x,z)` is zero, then x and z
are zero, while y remains arbitrary. The witnesses `(1,y,0,1)` satisfy every
equation. In the nonzero branch, write `x = g*a` and `z = g*d`. Choose r and s
with `x*r + z*s = g`. Cancel g only after making `g ≠ 0` available to obtain
`a*r + d*s = 1`. The input equation and a second cancellation give
`a*y = d*(z+1)`. Set `b = g` and `c = r*(z+1) + s*y`, then discharge all four
witness conditions.

This example exercises exactly the features a serious reader needs: definitions,
case scope, existential elimination and introduction, side conditions for
cancellation, calculation chains, and inspectable algebra. The companion must
show these mathematical transitions; the fact that a source line says `ring`
does not supply an explanatory derivation by itself.

The next mechanized fragment after scoped propositional logic should cover
typed commutative-ring expressions, equality chains, nonzero cancellation, and
existential witness obligations needed here. Keep the existing gcd library
theorems as explicitly stated dependency leaves. This gives a small, meaningful
end-to-end target without requiring an immediate English explanation of all
Mathlib. Do not label the companion formally certified until those features,
source binding, and the concrete rendering contract are actually connected.

## Relevance and usability

The opening screen should answer: what is proved, under what assumptions, why
this result matters locally, and what construction or idea makes it work. The
proof should be readable without following source links; the links should make
checking and investigation easier. Define every nonstandard object, show the
statement of each dependency, and make the chosen background boundary visible.

Motivational commentary and examples deserve their own status. A motivation
such as "this produces a determinant-one matrix" can become a checked
consequence if it is formalized; otherwise it is reviewed commentary. Numerical
examples can be evaluated and checked without being mistaken for the universal
proof. Do not let commentary inherit a certified badge from nearby mathematics.

Evaluate comprehension with practicing mathematicians. Ask them to reconstruct
the construction, identify the exact role of each hypothesis, explain why each
cancellation is allowed, and find seeded scope/witness/direction errors. Measure
correctness and time against the Lean source and ordinary mathematical prose;
record the participants' relevant background. This tests the intended value of
the tool rather than its visual polish alone. No such human result is claimed
by the current companion.

## Implementation plan

1. Preserve the existing corpus and native pipeline evidence. Improve fail-closed
   source, scope, and missing-target checks without reclassifying English.
2. Mechanize the smallest useful explanation calculus and canonical grammar.
   The bounded starting point is [ControlledEnglish.lean](../lean/ControlledEnglish.lean);
   its exact scope and remaining obligations belong in its own documentation.
3. Connect the Bézout fragment to typed expressions in the actual Lean
   environment. Add one checked rule at a time with hostile counterexamples.
4. Prove the plan transformations and canonical renderer used by that fragment.
   Keep the curated companion available while this connection is incomplete.
5. Promote individual documents only after all required gates pass. Generalize
   using measured corpus gaps and mathematician feedback, preserving failures
   and the original denominator.

This branch owns reader correctness, the companion, and the explanation
architecture. The concurrent `work/full-original-project` session owns original
project closure and Comparator integration. Their work can strengthen native
source replay, but a complete original-project build still does not replace the
English semantic obligations above.
