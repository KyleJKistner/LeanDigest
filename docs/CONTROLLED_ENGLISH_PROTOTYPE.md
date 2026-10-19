# Controlled English for propositional logic

`lean/ControlledEnglish.lean` is an isolated, executable Lean 4.34.1 prototype.
It establishes a semantic contract for a small controlled token language and
typed logical proof rules. It does **not** certify the existing Python printer,
the curated Bézout companion, arbitrary English, or the entire Leanglish corpus.

The substantive result is a checked chain from a typed proof node to an
unambiguous inference sentence: its conclusion matches the node, its premises
are justified in that node's context, and the emitted tokens have the declared
logical meaning. Deterministic regeneration alone would not establish this.

## Lean theorems

| Declaration | Checked claim |
| --- | --- |
| `Hypothesis.sound` | A hypothesis reference denotes a proposition in its indexed context. |
| `Derivation.sound` | Every represented derivation proves its conclusion under its context, for every interpretation of its atoms. |
| `SourceObligation.discharge` | A derivation discharges a supplied Lean judgement when an explicit Lean proof relates that judgement to the represented context and conclusion. |
| `parseFormula_render` | Parsing a rendered formula consumes exactly that formula and leaves an arbitrary suffix unchanged, given sufficient fuel. |
| `readFormula_render` | The complete formula reader satisfies `readFormula n formula.render = some formula`. It supplies sufficient fuel itself and rejects trailing tokens. |
| `rendered_formula_meaning` | A rendered formula token stream has exactly the formula's semantic interpretation. |
| `parseSentence_render` | The corresponding exact-consumption theorem holds for inference sentences with one, two, or three premises. |
| `readSentence_render` | The complete sentence reader satisfies `readSentence n sentence.render = some sentence`. |
| `rendered_sentence_meaning` | A rendered inference sentence token stream has exactly the inference's semantic interpretation. |
| `Rule.sound` | Every supported rule instance is logically valid under every atom interpretation. |
| `Rule.rendered_sound` | Every supported rule's emitted inference tokens have a valid semantic interpretation. |
| `Derivation.rootRule?_aligned` | A supported sentence extracted from a typed node has exactly its conclusion; its mentioned premises follow from the node's children in their proper scopes. |
| `discharge_swap` | A concrete typed proposition dictionary and correspondence proof connect the conjunction-swap derivation to the Lean proposition `p ∧ q → q ∧ p`. |

These are universal Lean theorems, not results inferred from a collection of
example strings. The file also contains executable parser examples, a displayed
case-analysis rule, and positive scoped derivations.

## Representation and atom meaning

`Formula n` has five constructors: a finite atom reference, `False`, conjunction,
disjunction, and implication. An atom is an element of `Fin n`; its meaning is
given by an explicit function `Fin n → Prop`. There is no constructor that
accepts a pretty-printed expression or an arbitrary formula string as evidence.

For example, `twoPropositions p q` interprets atom zero as the actual Lean
proposition `p` and atom one as the actual proposition `q`. The source example
supplies a checked correspondence between its formula and `p ∧ q → q ∧ p`.
Renaming a displayed label is not how that correspondence is established.

The semantic environment is part of the contract. The token `atom 0` has no
mathematical meaning independently of that environment. A future frontend that
replaces it with a name or a displayed formula must preserve this mapping; that
frontend is not implemented or verified here.

`ContextHolds` interprets a list of assumptions. `Hypothesis` is an indexed
reference into that list: `here` selects the most recent assumption, and `there`
moves outward. Its numeric index is a position in this scoped context, not a
user-supplied hypothesis name.

## Proof rules and scope

`Derivation context goal` is intrinsically typed. Its ten constructors cover a
scoped assumption reference, conjunction introduction and both projections,
implication introduction and application, both disjunction introductions,
disjunction elimination, and false elimination.

Implication introduction checks its body in the context extended by the
antecedent. Disjunction elimination has two separate branch contexts and requires
the same conclusion in each branch. The type system prevents a left-branch
assumption from being used as the right-branch assumption. The soundness theorem
proves these rules correct under every valuation; it does not rely on a fixed
set of example propositions.

There is no arithmetic cancellation rule in this fragment. In particular, no
nonzero hypothesis can be silently dropped from a cancellation explanation,
because such an explanation is not yet represented. Equality, quantifiers,
gcds, ring certificates, induction, dependent types, and classical reasoning
rules are also outside the grammar in this prototype.

## Token semantics

The proved text type is `List Token`. Formula tokens use an explicit finite
grammar:

```text
atom(index)
False
both FORMULA and FORMULA end
either FORMULA or FORMULA end
if FORMULA then FORMULA end
```

The formula parser checks the atom bound and every delimiter. A raw parsing call
with too little fuel returns failure. The complete readers select fuel from the
input length; the roundtrip theorems prove this is sufficient for their own
rendered output. Trailing tokens are rejected, rather than silently ignored.

The inference grammar is:

```text
From PREMISE, infer CONCLUSION.
From PREMISE, together with PREMISE, infer CONCLUSION.
From PREMISE, together with PREMISE, together with PREMISE, infer CONCLUSION.
```

Every premise and conclusion is a formula in the same grammar. Their meaning is
the corresponding curried implication. Eight rule instances emit these
sentences:

| Rule | Premises | Conclusion |
| --- | --- | --- |
| Conjunction introduction | `P`, `Q` | `P ∧ Q` |
| First projection | `P ∧ Q` | `P` |
| Second projection | `P ∧ Q` | `Q` |
| Implication application | `P → Q`, `P` | `Q` |
| Left disjunction introduction | `P` | `P ∨ Q` |
| Right disjunction introduction | `Q` | `P ∨ Q` |
| Disjunction elimination | `P ∨ Q`, `P → R`, `Q → R` | `R` |
| False elimination | `False` | `P` |

The branch premises in disjunction elimination express the two independently
scoped proof obligations. `Derivation.rootRule?_aligned` proves that extracting
this sentence from a represented proof node really supplies those implications
from its two branch bodies.

Parsing is deliberately separate from validity. For example, “From atom zero,
infer atom one” is grammatical. It is false under an environment where atom
zero is true and atom one is false. The Lean file both proves the parsing result
and exhibits that counterexample. Only a supported `Rule` instance has the
universal validity theorem; an arbitrary parsed `Sentence` does not receive it.

`Token.toString`, `Formula.display`, and `Sentence.display` provide a convenient
human-readable display. **No theorem in this prototype establishes the
correctness or injectivity of that String conversion, tokenization from String,
escaping, HTML generation, browser rendering, or the user's interpretation of
the words.** The roundtrip and text-meaning claims apply to the typed token
sequence and its fixed formal grammar. Extending the checked boundary through
string serialization is a separate remaining obligation.

## Source correspondence

`SourceObligation` contains a real Lean proposition, the atom environment, the
represented context and goal, and a proof of their semantic correspondence.
`SourceObligation.discharge` cannot be supplied with a source label, hash, or
English sentence in place of that proof.

The prototype does not fetch a named declaration, inspect its proof term, or
verify an original proof path. Its source theorem concerns the **supplied** Lean
judgement. Even a checked proof of the same proposition does not establish that
the explanation follows the original proof's steps. Integration must bind the
judgement and each rule node to checked declarations, binder identities and
original paths. Existing snapshot strings are not automatically accepted into
this representation.

The local extraction function `Derivation.rootRule?` operates only on this
intrinsically typed IR. Assumption references and implication-introduction prose
return `none`; there is no generic text that disguises those unsupported moves.
It does not yet traverse and render a complete proof tree. Consequently, the
module cannot claim that every represented derivation has a complete English
explanation, even though every such derivation has a sound logical semantics.

The Bézout construction and its six-step curated explanation are not instances
of this fragment: their arithmetic and gcd dependencies require additional
checked syntax, rules, correspondence proofs, and rendering contracts. No
acceptance flag for that companion or the existing corpus changes because this
module compiles.

## Reproduction and axiom inventory

From the repository root, with Lean 4.34.1 available:

```sh
lean lean/ControlledEnglish.lean
```

The implementation imports `Lean` only and needs no Mathlib installation. The
supervisor owns Lake and CI integration; the direct compiler command above is
sufficient for this module. In the implementation session the command was run
with the local distribution:

```sh
/workspace/scratch/fc6359c47bd2/lean-4.34.1-linux/bin/lean lean/ControlledEnglish.lean
```

That command completed with exit code zero. The module prints its axiom
inventory on every compile:

| Theorems | Reported axioms |
| --- | --- |
| `Derivation.sound`, `SourceObligation.discharge`, `Rule.sound`, `Derivation.rootRule?_aligned`, `discharge_swap` | None |
| Formula and sentence parser/render roundtrips, formula and sentence rendered-meaning theorems, `Rule.rendered_sound` | `propext`, `Classical.choice`, `Quot.sound` |

No admission or `sorryAx` appears in that inventory. This is a core Lean
prototype run, not an extraction or replay of the pinned OpenAI project.

## Remaining work

1. Preserve the token semantics through a proved string serializer and lexer.
2. Represent assumption references and binder introductions in the text grammar,
   then prove a complete scoped proof-tree rendering contract.
3. Implement a narrow importer that produces this typed IR from checked Lean
   judgements and original proof paths, returning explicit unsupported results
   for everything else.
4. Add one real mathematical fragment, such as nonzero cancellation with an
   explicit guard, with syntax, semantic soundness and rendering proofs together.

Readability and usefulness still require evaluation by readers. A sound but
unhelpful sentence is possible; neither the roundtrip theorem nor the rule
soundness theorem measures that product requirement.
