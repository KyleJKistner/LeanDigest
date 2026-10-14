# ProofReader workstream: reader

Turn complete typed proofs into mathematics that a mathematician can follow. Add recursor/case/induction and named-lemma statement expansion, preserving scope and checked source paths. Unknown references and capped branches must not become explanation passes.

# Required return
Write SUMMARY.md with changed files, exact checks and exit codes, unrun checks, blockers, counterexamples and next task. Do not claim checks you did not execute.

# Ownership
proofreader/english.py
proofreader/normalization.py
proofreader/render.py
proofreader/web/
tests/test_normalization.py
tests/test_browser.py
tests/test_render_cli.py
tests/reader/
proofreader/narrative.py
proofreader/polynomial.py
tests/test_narrative.py

# Acceptance
python -m pytest tests/test_kernel.py tests/test_normalization.py tests/test_browser.py tests/test_render_cli.py -q
Reproduce counterexamples for any changed scope, hypothesis or normalization rule
Report explanation gaps separately from term/type validity

# Known blocker
One retained substantial proof now reads through 86 frames and 16 polynomial certificates. Generalize to independently selected unseen domains and measure readability; do not overfit this example.


# File: docs/TRUST.md

# Trust boundary — 0.2

## Three inputs, different authority

A `.lean` **source outline** is a lexical/layout reading aid. Recognizing `simp`
does not reveal a mathematical derivation. None of the nine OpenAI source-mode
demo declarations is relabelled as kernel checked.

A `proofreader.kernel-export/v2` **typed argument** is a constructor DAG plus a
set of typed proof-subterm judgements. Python validates a strict schema, universe
and binder scope, immutable original-root paths, exact child/argument inventories,
and resource budgets. It does not serve as a Lean type checker.

A **checking observation/receipt** records a run. An imported JSON file is not a
signature, an attestation, or proof of its own origin. The browser never claims to
authenticate it. The release's remote observations include request identifiers,
exact request-source hashes, positive markers and negative outcomes.

## What the generated Lean program checks

1. Exact Lean version and universe-parameter inventory.
2. Transitive axiom inventory matching the argument export.
3. Original declaration statement and proof AST identity, after erasing metadata.
   Proof irrelevance/definitional equality is not substituted for this exactness.
4. The original reconstructed proof submitted as a new kernel-checked theorem.
5. Every recorded proof path followed independently in Lean through that original
   proof; its real enclosing binders are used to close the subterm.
6. Each resulting term/type judgement submitted through `addDecl`: theorem
   declarations for proofs and safe definitions for data arguments.
7. Proposition/data and assumption/object classification checked in Lean.

`debug.skipKernelTC` is forced false around the new declarations. A failure after
root replay but before the final marker is an overall failure. The exact final
marker includes the argument hash and judgement count. The verifier also checks
process/API success, errors, failed declarations, returned source and version.

This still assumes a trusted Lean implementation, checking program, runtime,
project metaprograms, imported dependencies and service execution. It does not
cryptographically authenticate compiled dependencies, hardware, or the service.
An adversarial project with arbitrary metaprogram execution is not made logically
or operationally trustworthy merely by passing a command-line flag.

## What is not certified

The English printer is deterministic and regression-tested, not formally proved.
`check-reading` checks regeneration, not a formal interpretation of English.
Beta/zeta display simplification is bounded and capture-avoiding in the tested
implementation; original expression nodes remain authoritative. Unknown symbols,
recursors, large expressions and named lemmas can remain explicitly unexpanded.
Standard mathematical notation still needs its displayed types and instances.

No human comprehension study, full-corpus prose-completeness result, paper-to-Lean
correspondence proof, or correctness claim for OpenAI's manuscripts is implied.
The v2 enumerator covers theorem declarations, not all proof-valued definitions.
The legacy exporter retains a wider declaration inventory but does not provide
v2 intermediate-judgement verification.

## Axioms and admissions

Default permitted axioms: `propext`, `Classical.choice`, `Quot.sound`. These are
visible, not silently described as axiom-free. Additional axioms require explicit
`--permit-axiom` and remain visible. `sorryAx` / `Lean.sorryAx` cannot be permitted
through that option. An empty transitive axiom inventory is reported separately.

## Execution and transport

Offline reading makes no model, telemetry, CDN or service requests. The local
single-user server accepts source text, not arbitrary filesystem paths. It binds
to loopback and checks Host/Origin; it has no Lean build or shell endpoint.

Native compilation requires `--trust-project`; this does not sandbox anything.
Remote operations require `--allow-remote` and send complete code to AXLE. Remote
requests require UTF-8 JSON, fixed official host, bounded responses and no redirect
following. API keys are read from the environment and excluded from artifacts.

Source snapshots and module/source hashes do not authenticate every dependency
binary. Corpus reports are unsigned reproducible ledgers, not self-authenticating
mathematical certificates. Security tests are not an independent security audit.

## Source-bound route added in 0.3

`source-bound-snapshot` is not `typed-export`. Its formula strings use Lean's pretty-printer. Read docs/NARRATIVE.md for the full trust boundary, re-extraction checks and integer-polynomial certificates. No snapshot or imported receipt self-authenticates. Exact source paths and selected judgements ran on 4.34.1 for the retained example; the full pinned project did not.



# File: docs/KERNEL_IR.md

# Frozen v2 argument contract

Authority is `proofreader.kernel-export/v2`. Reader output remains the backwards-
compatible `proofreader.document/v1` format with additional typed metadata.

## Expression graph

`exprs` is a topological DAG. Every edge refers to an earlier node. Constructor
fields are exact; unknown fields, extra variables, unresolved metavariables and
unlisted universe parameters are rejected. Names preserve anonymous/str/num
constructors, avoiding collisions between a single dotted component and a
qualified name. Binder indices are de Bruijn indices, not text substitutions.
The root `type` and `term` must be closed under `levels`.

Each step records its `term`, Lean-inferred `type`, `is_proof`, `path`, `children`,
complete application `arguments`, optional `domain_is_prop`, and `truncated`.
No pretty-print string or prewritten English sentence is trusted as mathematics.

## Original-expression paths

- Application: 0 = function, 1 = argument.
- Lambda/forall: 0 = domain, 1 = body; entering the body adds the original binder.
- Let: 0 = type, 1 = value, 2 = body; the body adds the original let binder.
- Projection: 0 = object.

Python validates every path. The generated Lean program independently follows it
in the imported original proof and closes the result over the actual enclosing
context. The term must equal the submitted closed judgement term before typing.
Native kernel checks then validate all proof and data types.

## Coverage and omission

The raw expression graph retains the original proof. The typed reading expansion
has depth/step budgets; hitting them creates explicit truncated steps, not a
claim of conceptual explanation. In-flight siblings may cause the exporter to
exceed its 1,500-step expansion threshold slightly; the whole response remains
size-bounded. Explicit formula-normalization limits produce visible references.

Unknown named lemmas are cited, not purportedly explained. Imports may contain
arbitrary definitions; dictionary expansion and semantic abstraction remain work.
Do not redefine success as printing an opaque `apply` sentence for every theorem.

## Provenance states

`exported`, `structurally_validated`, `rendered`, `path_linkage_checked_in_lean`,
`all_judgements_kernel_checked`, `regeneration_matched`, `english_formally_verified`,
and `human_readability_evaluated` are distinct. Only actual checks may populate
execution states. A saved imported receipt never authenticates its own producer.

Keep the schema stable while improving explanations. Changes to the display
compiler require a printer version bump and determinism/regeneration tests.



# File: docs/ACCEPTANCE.md

# Acceptance gates — 0.2.0

These gates are independent. A successful build, readable page or positive receipt
must not be counted as an English fidelity or whole-corpus result.

## A0 — deterministic, usable reading software

Local tests cover source scanning, typed-expression validation, English
regeneration, capture-avoiding display reduction, the browser, packaging and CLI.
The default reader contains five real typed exports and nine source candidates.
Unsupported expressions remain visible. This is implemented, but it is not a
human comprehension result. See `VALIDATION_V0_2.md` for the executed test count.

## A1 — actual theorem and intermediate-judgement checking

Required: compile the exporter; reconstruct the original declaration; independently
follow each source path; kernel-check every displayed term/type judgement; retain
version, universe and axiom inventories. Negative cases must fail for the intended
reason, not merely because the driver has a syntax error.

Current: individual remote exporter and checker programs executed on Lean 4.34.0.
Five compact exports are retained. One retained example has all original-path and
18 term/type judgement checks observed, with source-path, intermediate-type and
version mutations rejected. Earlier tests reject axiom and binder-role mutations.
The complete native 4.34.1 module pipeline is still **unrun here**, and its mandatory
CI test must pass without skips before claiming native integrated acceptance.

## A2 — complete expected-corpus accounting and execution

Required: pin the source and dependencies; acquire all expected files; enumerate
actual theorem declarations from every required module; retain every build,
export and checking failure; reconcile independent shards.

Current: complete metadata observation for the 23 `lean/OAI` domain subtrees:
122,458 Lean files, 1,571,301,358 bytes. The file contents have not all been acquired
or built. Expected theorem count is unknown until all modules are enumerated.
The v2 denominator is `.thmInfo` theorem declarations, not proof-valued definitions
or manuscript claims. Expanding that scope requires an explicit contract change.
The adapted Bézout-body experiment is not an exact pinned-project pass.

## A3 — mathematical reading completeness

Required: expose all hypotheses, conclusions, witness conditions, branch scopes,
lemma statements and dependencies for every theorem in scope. A bare lemma name
is not a complete explanation. Generic terms, opaque computations, capped
branches and unresolved vocabulary remain separately visible and measurable.

Current: typed assumptions, introductions, basic logical constructors, witness
introduction, simple alternatives, equalities and injectivity application render
as mathematics. Arbitrary recursors, induction and dependency statements are not
fully explained. The large Bézout export hit explicit expansion caps. No full
corpus English completeness result is claimed.

## A4 — faithful language and compression

Required: bind each displayed inference to the exact original proof path and its
checked claim; make grammar interpretation and display-normalization semantics
explicit; prove the relevant interpretation/round-trip properties. Compression
must preserve an inspectable argument, not substitute a new plausible proof.

Current: the typed judgement and path checker exists and has live positive and
negative evidence. `check-reading` rejects changes to regenerated statements,
parameters and proof prose. The grammar, Python renderer and display normalizer
are **not formally proved correct**. Byte-for-byte regeneration is not semantic
certification. The English acceptance gate therefore remains false.

## A5 — reduced burden on mathematicians

Required: independently selected complete proofs and comprehension/error-detection
tasks with practicing mathematicians; compare review time and correctness against
Lean and relevant existing readers. Do not infer benefit from screenshots or
counts of grammatical sentences.

Current: no human study. This remains the ultimate product acceptance criterion.



# File: proofreader/english.py

"""Deterministic mathematical reading views for the path-bound proof format.

No LLM, tactic-name interpretation, author prose, or untrusted pretty-print field
is used. This is a tested compiler/printer, not a machine-proved English semantics.
"""
from __future__ import annotations
from dataclasses import asdict, replace
import copy
import json
import re
from typing import Any
from .kernel import Argument, Dag, InvalidExport, display_name, plain_name, require
from .normalization import Reduction, DisplayLimit
from .model import Declaration, Document, Span, Step, canonical_json, digest, walk_steps

PRINTER_VERSION = "math-en/0.2.0"


def fresh_name(raw: dict, used: list[str], fallback: str = "x") -> str:
    text = plain_name(raw)
    base = text if text and "." not in text and not text.startswith("_") else fallback
    candidate = base; i = 2
    while candidate in used:
        candidate = f"{base}_{i}"; i += 1
    return candidate


class Formula:
    """A conservative notation dictionary, keyed by exact Lean constant identity."""
    INFIX = {"Eq": (3, "="), "And": (2, "∧"), "Or": (2, "∨"), "Iff": (2, "↔"),
             "LT.lt": (4, "<"), "LE.le": (4, "≤"), "HAdd.hAdd": (6, "+"),
             "HSub.hSub": (6, "−"), "HMul.hMul": (6, "·"), "HDiv.hDiv": (6, "/"),
             "Nat.add": (2, "+"), "Nat.mul": (2, "·"), "Nat.sub": (2, "−")}
    CONSTANTS = {"Nat": "ℕ", "Int": "ℤ", "Rat": "ℚ", "Real": "ℝ", "True": "True", "False": "False"}

    def __init__(self, dag: Dag, max_chars: int = 20000):
        self.dag = dag; self.max_chars = max_chars
        self.unknown_constants: set[str] = set()
        self.reduction = Reduction(dag)

    def level(self, n: dict) -> str:
        t = n["tag"]
        if t == "zero": return "0"
        if t == "param": return display_name(n["name"])
        if t == "succ": return f"({self.level(n['of'])}+1)"
        return f"{t}({self.level(n['left'])}, {self.level(n['right'])})"

    def render(self, i: int, ctx: list[str] | None = None) -> str:
        budget = [5000]
        text = self._render(i, ctx or [], 0, budget)
        if len(text) > self.max_chars:
            # Explicit reference, never silent truncation of a proposition.
            return f"[expression e{i}; expand its exact constructor record]"
        return text

    def _render(self, i: int, ctx: list[str], depth: int, budget: list[int]) -> str:
        budget[0] -= 1
        if depth > 100 or budget[0] < 0:
            return f"[expression e{i}; expansion limit]"
        try: i = self.reduction.head(i)
        except DisplayLimit: return f"[expression e{i}; normalization limit]"
        n = self.dag.nodes[i]; t = n["tag"]
        r = lambda j, cs=ctx: self._render(j, cs, depth + 1, budget)
        if t == "bvar":
            require(n["index"] < len(ctx), "Formula references an out-of-scope binder")
            return ctx[-n["index"] - 1]
        if t == "sort":
            lv = n["level"]
            if lv["tag"] == "zero": return "Prop"
            if lv == {"tag": "succ", "of": {"tag": "zero"}}: return "Type"
            return f"Sort({self.level(lv)})"
        if t == "const":
            name = plain_name(n["name"])
            if name in self.CONSTANTS: return self.CONSTANTS[name]
            shown = display_name(n["name"])
            self.unknown_constants.add(shown)
            return shown
        if t in {"nat", "str"}:
            return n["value"] if t == "nat" else json.dumps(n["value"], ensure_ascii=False)
        if t == "app":
            head, args = self.dag.app(i)
            hn = self.dag.nodes[head]
            name = plain_name(hn["name"]) if hn["tag"] == "const" else None
            arity = len(args)
            if name in self.INFIX and arity == self.INFIX[name][0]:
                return f"({r(args[-2])} {self.INFIX[name][1]} {r(args[-1])})"
            if name == "Not" and arity == 1: return f"¬{r(args[0])}"
            if name == "Ne" and arity == 3: return f"({r(args[1])} ≠ {r(args[2])})"
            if name == "OfNat.ofNat" and arity == 3 and self.dag.nodes[args[1]]["tag"] == "nat":
                return self.dag.nodes[args[1]]["value"]
            if name == "Nat.succ" and arity == 1: return f"({r(args[0])} + 1)"
            if name == "Exists" and arity == 2:
                p = self.dag.nodes[args[1]]
                if p["tag"] == "lam":
                    x = fresh_name(p["name"], ctx)
                    return f"∃ {x} : {r(args[0])}, {r(p['body'], ctx + [x])}"
                return f"∃ x : {r(args[0])}, {r(args[1])}(x)"
            if name == "Function.Injective" and arity == 3:
                return f"{r(args[-1])} is injective"
            if name == "Function.Surjective" and arity == 3:
                return f"{r(args[-1])} is surjective"
            if name == "Function.comp" and arity == 5:
                return f"({r(args[-2])} ∘ {r(args[-1])})"
            return f"{r(head)}({', '.join(r(x) for x in args)})"
        if t in {"lam", "forall"}:
            x = fresh_name(n["name"], ctx)
            dom = r(n["domain"]); body = r(n["body"], ctx + [x])
            if t == "lam": return f"({x} ↦ {body})"
            if not self.dag.uses_binder(n["body"]): return f"({dom} → {body})"
            return f"∀ {x} : {dom}, {body}"
        if t == "let":
            x = fresh_name(n["name"], ctx)
            return f"(let {x} : {r(n['type'])} = {r(n['value'])}; {r(n['body'], ctx + [x])})"
        if t == "proj": return f"component[{display_name(n['name'])}, {n['index']} ]({r(n['of'])})"
        raise InvalidExport("Cannot render unsupported constructor")


class English:
    def __init__(self, record: dict):
        self.argument = Argument(record)
        self.dag = self.argument.dag
        self.formula = Formula(self.dag)
        self.aid = self.argument.sha256[:20]

    def labels(self, ctx: list[int]) -> list[str]:
        labels: list[str] = []
        for binder in ctx:
            labels.append(fresh_name(self.dag.nodes[binder]["name"], labels))
        return labels

    def context(self, ctx: list[int]) -> list[dict[str, str]]:
        labels = self.labels(ctx)
        result = []
        for i, binder in enumerate(ctx):
            b = self.dag.nodes[binder]
            result.append({"name": labels[i], "type": self.formula.render(b.get("domain", b.get("type")), labels[:i])})
        return result

    def describe(self, i: int) -> Step:
        s = self.argument.steps[i]; ctx = self.argument.contexts[i]; labels = self.labels(ctx)
        n = self.dag.nodes[s["term"]]; t = n["tag"]
        con = self.formula.render(s["type"], labels)
        r = lambda e: self.formula.render(e, labels)
        rule = t; refs = []; fallback = s["truncated"]
        children = [self.describe(j) for j in s["children"]]
        if s["truncated"]:
            text = f"The recorded term establishes {con}; its internal derivation is not expanded."
        elif t == "lam":
            x = fresh_name(n["name"], labels)
            dom = r(n["domain"])
            rule = "assume" if s["domain_is_prop"] else "introduce"
            if s["domain_is_prop"]: text = f"Assume {dom}; denote this assumption by {x}."
            elif dom == "Prop": text = f"Let {x} be a proposition."
            elif dom == "Type": text = f"Let {x} be a type."
            elif dom.startswith("Sort("): text = f"Let {x} be a type in {dom}."
            else: text = f"Let {x} : {dom} be arbitrary."
        elif t == "let":
            x = fresh_name(n["name"], labels)
            rule = "have" if len(children) == 2 else "let"
            text = f"Establish {r(n['type'])} and call this fact {x}." if len(children) == 2 else f"Put {x} = {r(n['value'])}, of type {r(n['type'])}."
        elif t == "bvar":
            rule = "assumption" if s["is_proof"] else "given-object"
            text = f"This is the assumption {r(s['term'])}: {con}." if s["is_proof"] else f"Use the given object {r(s['term'])}."
        elif t == "app":
            head, args = self.dag.app(s["term"])
            hn = self.dag.nodes[head]
            name = plain_name(hn["name"]) if hn["tag"] == "const" else None
            if name: refs = [name]
            premises = [r(a["type"]) for a in s["arguments"] if a["is_proof"]]
            basis = "; ".join(premises)
            rule = "lemma-application"
            text = f"Apply {r(head)} to the recorded arguments to obtain {con}."
            if hn["tag"] == "bvar":
                rule = "hypothesis-application"
                pos = len(ctx) - hn["index"] - 1
                bn = self.dag.nodes[ctx[pos]]
                dom = bn.get("domain", bn.get("type"))
                dh, das = self.dag.app(dom); dn = self.dag.nodes[dh]
                dname = plain_name(dn["name"]) if dn["tag"] == "const" else None
                if dname == "Function.Injective" and len(das) == 3:
                    fn = self.formula.render(das[-1], labels[:pos])
                    text = f"Injectivity of {fn}, applied to {basis}, gives {con}."
                    rule = "injectivity"
                else:
                    text = f"Using {r(head)} and the established fact{'s' if len(premises) != 1 else ''} {basis}, conclude {con}." if premises else f"Specialize {r(head)} at the recorded objects to obtain {con}."
            templates = {
                ("And.intro", 4): ("conjunction", f"Combining the two established facts gives {con}."),
                ("And.left", 3): ("left-conjunct", f"The first conjunct of {basis} gives {con}."),
                ("And.right", 3): ("right-conjunct", f"The second conjunct of {basis} gives {con}."),
                ("Eq.refl", 2): ("reflexivity", f"By reflexivity, {con}."),
                ("Eq.symm", 4): ("symmetry", f"Reversing the supplied equality gives {con}."),
                ("Eq.trans", 6): ("transitivity", f"By transitivity of the established equalities, {con}."),
                ("Iff.intro", 4): ("equivalence", f"The two implications establish {con}."),
                ("False.elim", 2): ("contradiction", f"The contradiction implies {con}."),
                ("Or.inl", 3): ("left-alternative", f"The first alternative establishes {con}."),
                ("Or.inr", 3): ("right-alternative", f"The second alternative establishes {con}."),
                ("Or.elim", 6): ("cases", f"Separate the two alternatives. In either case, prove {con}."),
                ("Exists.elim", 5): ("existential-elimination", f"Use the existential premise, then prove {con} for its witness as follows."),
                ("Classical.byContradiction", 2): ("contradiction-proof", f"Suppose the desired conclusion fails; the following argument yields a contradiction, proving {con}."),
            }
            if (name, len(args)) in templates:
                rule, text = templates[(name, len(args))]
            if name == "Exists.intro" and len(args) == 4:
                rule = "witness"
                prop = r(s["arguments"][3]["type"])
                text = f"Take the witness {r(args[2])}. The supplied fact {prop} establishes {con}."
            if name == "Or.elim" and len(args) == 6:
                text = f"Use the disjunction {r(s['arguments'][3]['type'])}. In the {r(args[0])} case, use {r(args[4])}; in the {r(args[1])} case, use {r(args[5])}. In either case, conclude {con}."
            if rule == "lemma-application":
                # It is a faithful citation at lemma granularity, not a conceptual expansion.
                fallback = True
        elif t == "const":
            name = plain_name(n["name"])
            refs = [name] if name else []
            rule = "named-fact"
            text = f"The named result {r(s['term'])} gives {con}."
            if name == "True.intro": text = "The proposition True holds by its introduction rule."; rule = "truth"
            else: fallback = True
        elif t == "proj":
            rule = "projection"
            text = f"Take component {n['index']} of the recorded {display_name(n['name'])} object to obtain {con}."
            fallback = True
        else:
            text = f"Use the recorded expression to establish {con}."; fallback = True
        formula_gap = "[expression " in con or "[expression " in text
        return Step(f"{self.aid}:s{i}", rule, text, r(s["term"]), evidence="typed-export",
                    children=children, references=refs, conclusion=con, context=self.context(ctx),
                    term_id=f"e{s['term']} : e{s['type']}", fallback=fallback or formula_gap,
                    detail=f"Original proof path: {s['path']}. Claim: step_{i}. "
                           "Its closed term and type are included in the generated Lean judgement checks.")

    def prose_steps(self) -> list[Step]:
        """Flatten leading binders, then put small direct inferences in dependency order.

        Branching arguments retain nested scopes. Expansion only hides already-given
        assumption leaves; it never treats an unexpanded named lemma as an explanation.
        """
        root = self.describe(0)
        out = []
        while root.rule in {"introduce", "assume"} and len(root.children) == 1:
            child = root.children[0]
            root = replace(root, children=[], conclusion=None)
            out.append(root); root = child
        branch_rules = {"introduce", "assume", "have", "let", "cases", "existential-elimination", "contradiction-proof"}
        def flat(s: Step) -> list[Step]:
            if s.rule in branch_rules:
                return [s]
            result = []
            for child in s.children:
                if child.rule not in {"assumption", "given-object"}:
                    result.extend(flat(child))
            # Nontrivial premises already appear in dependency order. Link to
            # those steps instead of duplicating entire subtrees in the document.
            rendered = replace(s)
            rendered.supports = [child.id for child in s.children
                                 if child.rule not in {"assumption", "given-object"}]
            rendered.children = [child for child in s.children
                                 if child.rule in {"assumption", "given-object"}]
            result.append(rendered)
            return result
        out.extend(flat(root))
        return out

    def statement_parts(self) -> tuple[list[dict], int, list[str]]:
        """Move declared parameters out of the proof, preserving their scope.

        Only an exact matching raw forall/lambda prefix is split. Other proof
        shapes retain the full quantified statement instead of guessing.
        """
        typ = self.argument.typ; step_index = 0; parameters = []; labels = []
        while True:
            ty = self.dag.nodes[typ]; st = self.argument.steps[step_index]
            term = self.dag.nodes[st["term"]]
            if ty["tag"] != "forall" or term["tag"] != "lam" or st["truncated"]:break
            if not self.dag.equal(ty["domain"],term["domain"]):break
            label = fresh_name(term["name"],labels)
            dom = self.formula.render(term["domain"],labels)
            if st["domain_is_prop"]: text = f"Assume {dom}; denote this assumption by {label}."
            elif dom == "Prop": text = f"Let {label} be a proposition."
            elif dom == "Type": text = f"Let {label} be a type."
            elif dom.startswith("Sort("): text = f"Let {label} be a type in {dom}."
            else: text = f"Let {label} : {dom} be arbitrary."
            label = fresh_name(term["name"],labels)
            parameters.append({"names":label,"type":self.formula.render(term["domain"],labels),
                               "binder": "[" if term["binder"]=="instance" else "(",
                               "text":text,"source_step_id":f"{self.aid}:s{step_index}"})
            labels.append(label);typ = ty["body"];step_index=st["children"][0]
        return parameters, typ, labels

    def document(self, *, source: str = "", file: str = "typed-proof", receipt: dict | None = None) -> Document:
        a = self.argument
        steps = self.prose_steps()
        parameters, target, labels = self.statement_parts()
        steps = steps[len(parameters):]
        dependencies = sorted({r for s in walk_steps(steps) for r in s.references})
        d = Declaration(self.aid, a.name, "theorem", file, self.formula.render(target,labels), source,
                        Span(0, len(source), 1, source.count("\n") + 1), parameters=parameters, steps=steps,
                        evidence="typed-export", dependencies=dependencies, receipt=receipt,
                        axes={"discovery": "Lean-exported", "statement": "rendered-from-expression-DAG",
                              "proof": "path-bound-typed-judgements", "english_fidelity": "regenerable-not-formally-proved",
                              "argument_sha256": a.sha256, "printer": PRINTER_VERSION,
                              "fully_quantified_statement": self.formula.render(a.typ)},
                        warnings=["Named lemmas without an exposition template remain explicitly unexpanded.",
                                  "Kernel judgement checks do not constitute a formal proof of this English printer."])
        return Document(a.name, [{"path": file, "source": source, "sha256": digest(source)}] if source else [], [d],
                        provenance={"mode": "path-bound-typed-proof", "argument_sha256": a.sha256,
                                    "printer": PRINTER_VERSION, "pipeline_model_calls": 0,
                                    "lean_version": a.record["lean_version"], **a.coverage()},
                        generator="lean-proofreader/0.2.0")


def reading_binding(document: Document) -> dict:
    """Hash only generated mathematics, not source labels or receipt assertions."""
    def st(s: Step) -> dict:
        return {k: v for k, v in asdict(s).items() if k not in {"span", "evidence"}}
    return {"declarations": [{"name": d.name, "statement": d.statement,
                               "parameters": d.parameters, "context": d.context,
                               "steps": [st(s) for s in d.steps], "dependencies": d.dependencies}
                              for d in document.declarations], "printer": PRINTER_VERSION}


def check_reading(record: dict, document: Document) -> None:
    expected = English(record).document()
    require(reading_binding(expected) == reading_binding(document),
            "Reading text or proof structure differs from deterministic regeneration")


def prose_text(record: dict) -> str:
    doc = English(record).document()
    d = doc.declarations[0]
    return "\n\n".join([d.name] + [p["text"] for p in d.parameters] + ["Claim: " + d.statement, "Proof."] + [s.text for s in d.steps] + ["∎"]) + "\n"



# File: proofreader/normalization.py

"""Bounded capture-avoiding beta/zeta reduction for mathematical display.

The original DAG remains authoritative. Added display nodes never replace its
proof certificate. The algorithm is tested, not a formal proof of the printer.
"""
from __future__ import annotations
from .kernel import Dag, EDGES, InvalidExport

class DisplayLimit(ValueError):
    pass

class Reduction:
    def __init__(self, dag: Dag, node_budget: int = 20000):
        self.dag = dag
        self.limit = len(dag.nodes) + node_budget
        self.shift_cache: dict[tuple[int,int,int], int] = {}
        self.subst_cache: dict[tuple[int,int,int], int] = {}
        self.head_cache: dict[int, int] = {}

    def add(self, node: dict) -> int:
        if len(self.dag.nodes) >= self.limit: raise DisplayLimit('Display reduction budget')
        return self.dag.add(node)

    def _transform(self, root: int, amount_or_arg: int, *, mode: str) -> int:
        """Postorder with (node, binder depth) memoization; no recursive expansion."""
        cache = self.shift_cache if mode == 'shift' else self.subst_cache
        initial = (root, amount_or_arg, 0)
        stack = [(root,0,False)]
        visits = 0
        while stack:
            i, depth, ready = stack.pop();key = (i,amount_or_arg,depth)
            if key in cache: continue
            visits += 1
            if visits > 150000: raise DisplayLimit('Display traversal budget')
            n = self.dag.nodes[i];tag = n['tag']
            if tag == 'bvar':
                k=n['index']
                if mode == 'shift':
                    v = self.add({'tag':'bvar','index':k+amount_or_arg}) if k>=depth else i
                elif k == depth:
                    v = self.shift(amount_or_arg, depth)
                elif k > depth:
                    v = self.add({'tag':'bvar','index':k-1})
                else:v=i
                cache[key]=v;continue
            edges = EDGES.get(tag,())
            if not edges:cache[key]=i;continue
            def edepth(field):return depth + int(field=='body' and tag in {'lam','forall','let'})
            if not ready:
                stack.append((i,depth,True))
                for f in reversed(edges):
                    ck=(n[f],amount_or_arg,edepth(f))
                    if ck not in cache:stack.append((n[f],edepth(f),False))
            else:
                node={**n,**{f:cache[(n[f],amount_or_arg,edepth(f))] for f in edges}}
                cache[key]=self.add(node)
        return cache[initial]

    def shift(self, root: int, amount: int) -> int:
        if amount == 0:return root
        if amount < 0:raise ValueError('Display shift must be nonnegative')
        return self._transform(root,amount,mode='shift')

    def instantiate(self, body: int, arg: int) -> int:
        return self._transform(body,arg,mode='instantiate')

    def spine(self, root: int) -> tuple[int,list[int]]:
        args=[];cur=root
        while self.dag.nodes[cur]['tag']=='app':
            if len(args)>=2048:raise DisplayLimit('Display application-spine budget')
            n=self.dag.nodes[cur];args.append(n['arg']);cur=n['fn']
        return cur,list(reversed(args))

    def head(self, root: int, fuel: int = 64) -> int:
        if root in self.head_cache:return self.head_cache[root]
        head,args=self.spine(root)
        changed=False
        for _ in range(fuel):
            n=self.dag.nodes[head]
            if n['tag']=='lam' and args:
                head=self.instantiate(n['body'],args.pop(0));changed=True
            elif n['tag']=='let':
                head=self.instantiate(n['body'],n['value']);changed=True
            else:break
            head,new_args=self.spine(head);args=new_args+args
        else:raise DisplayLimit('Display head-reduction fuel')
        if changed:
            for a in args:head=self.add({'tag':'app','fn':head,'arg':a})
            self.head_cache[root]=head
        else:self.head_cache[root]=root
        return self.head_cache[root]



# File: proofreader/model.py

"""Versioned, evidence-labelled reading IR. Strings never constitute proof evidence."""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any

SCHEMA = "proofreader.document/v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(data: str | bytes) -> str:
    return hashlib.sha256(data.encode("utf-8") if isinstance(data, str) else data).hexdigest()


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    line: int
    end_line: int
    column: int = 0


@dataclass
class Step:
    id: str
    rule: str
    text: str
    source: str = ""
    span: Span | None = None
    evidence: str = "source"
    references: list[str] = field(default_factory=list)
    supports: list[str] = field(default_factory=list)
    children: list[Step] = field(default_factory=list)
    conclusion: str | None = None
    context: list[dict[str, str]] = field(default_factory=list)
    term_id: str | None = None
    fallback: bool = False
    detail: str = ""


@dataclass
class Declaration:
    id: str
    name: str
    kind: str
    file: str
    statement: str
    source: str
    span: Span
    context: list[str] = field(default_factory=list)
    parameters: list[dict[str, str]] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence: str = "source"
    dependencies: list[str] = field(default_factory=list)
    docstring: str = ""
    receipt: dict[str, Any] | None = None
    axes: dict[str, Any] = field(default_factory=dict)


@dataclass
class Document:
    title: str
    files: list[dict[str, Any]]
    declarations: list[Declaration]
    warnings: list[str] = field(default_factory=list)
    provenance: dict[str, Any] = field(default_factory=dict)
    schema: str = SCHEMA
    generator: str = "lean-proofreader/0.3.0"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return canonical_json(self.to_dict()) + "\n"


def walk_steps(steps: list[Step]):
    for step in steps:
        yield step
        yield from walk_steps(step.children)


def report(document: Document) -> dict[str, Any]:
    """Keep syntactic rendering, Lean validation and semantic fidelity distinct."""
    declarations = document.declarations
    steps = [s for d in declarations for s in walk_steps(d.steps)]
    source_steps = [s for d in declarations if d.evidence == "source" for s in walk_steps(d.steps)]
    typed_steps = [s for d in declarations if d.evidence == "typed-export" for s in walk_steps(d.steps)]
    classified = sum(not s.fallback for s in source_steps)
    unique_steps = {s.id: s for s in steps}
    kernel_declarations = [d for d in declarations if d.axes.get("proof") == "path-bound-typed-judgements"]
    source_only = sum(d.evidence == "source" for d in declarations)
    return {
        "schema": "proofreader.coverage/v1",
        "files_indexed": len(document.files),
        "declaration_candidates": len(declarations),
        "declaration_discovery": ("mixed-source-and-exported" if 0 < source_only < len(declarations)
                                  else "source-heuristic" if source_only else "exported-or-empty"),
        "display_steps": len(steps),
        "typed_display_steps": len(typed_steps),
        "typed_display_steps_unexpanded": sum(s.fallback for s in typed_steps),
        "source_steps": len(source_steps),
        "source_steps_classified": classified,
        "source_steps_unclassified": len(source_steps) - classified,
        "source_character_classification": None,
        "source_character_classification_note": "Not measured: nested source spans overlap.",
        "source_only_declarations": source_only,
        "typed_export_declarations": sum(d.evidence == "typed-export" for d in declarations),
        "source_bound_snapshot_declarations": sum(d.evidence == "source-bound-snapshot" for d in declarations),
        "source_bound_snapshot_frames": sum(len(d.axes.get("frame_owners",{})) for d in declarations if d.evidence == "source-bound-snapshot"),
        "source_bound_polynomial_certificates": sum(d.axes.get("polynomial_certificates",0) for d in declarations if d.evidence == "source-bound-snapshot"),
        "source_bound_unexpanded_steps": sum(s.fallback for d in declarations if d.evidence == "source-bound-snapshot" for s in walk_steps(d.steps)),
        "successful_local_lean_receipts": 0,
        "receipt_trust_note": "Imported receipts are not authenticated. Attached observations are reported separately.",
        "attached_passed_receipt_records": sum(bool(d.receipt and d.receipt.get("status") == "passed") for d in declarations),
        "unique_display_step_ids": len(unique_steps),
        "path_bound_kernel_declarations": len(kernel_declarations),
        "checked_english_proofs": 0,
        "readability_human_evaluated": False,
        "unclassified_rules": sorted({s.rule for s in steps if s.fallback}),
        "limitations": [
            "Source classification is not semantic explanation coverage.",
            "A build receipt does not establish fidelity of English or paper-to-Lean correspondence.",
            "Source discovery is heuristic; custom command-generated declarations need the Lean exporter.",
        ],
    }



# File: tests/test_browser.py

"""Real Chromium interaction tests. Skip only when Playwright/browser is absent."""
from pathlib import Path
import json
import os
import shutil
import pytest
from proofreader.source import parse_source
from proofreader.render import html_document,load_document

pw=pytest.importorskip('playwright.sync_api')

@pytest.fixture(scope='module')
def browser():
    executable=shutil.which('chromium') or shutil.which('google-chrome')
    with pw.sync_playwright() as p:
        try:
            browser=p.chromium.launch(executable_path=executable,headless=True,args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
        except Exception as exc:
            if os.environ.get('PROOFREADER_REQUIRE_BROWSER') == '1': pytest.fail(f'Browser CI requires Chromium: {exc}')
            pytest.skip(f'Browser unavailable: {exc}')
        yield browser
        browser.close()

@pytest.fixture
def page(browser):
    page=browser.new_page(viewport={'width':1360,'height':960})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    yield page
    assert not errors,errors
    page.close()


def test_search_navigation_source_and_inspector(page):
    d=parse_source('theorem first : True := by\n  have h : True := by trivial\n  exact h\ntheorem second : True := by trivial\n')
    page.set_content(html_document(d))
    assert page.locator('#theorem-title').inner_text()=='first'
    page.locator('#expand-btn').click()
    assert page.locator('#proof-steps details[open]').count()>0
    page.locator('.step-inspect').first.click()
    assert page.locator('#inspector').is_visible()
    assert 'have h' in page.locator('#inspector-source').inner_text()
    page.locator('#inspector-close').click()
    page.locator('#search').fill('second')
    assert page.locator('#declaration-list button').count()==1
    assert page.locator('#theorem-title').inner_text()=='second'
    page.locator('#tab-source').click()
    assert 'theorem second' in page.locator('#exact-source').inner_text()
    page.locator('#tab-audit').click()
    assert 'Not certified' in page.locator('#audit').inner_text()


def test_xss_source_and_title_remain_text(page):
    attack='</script><script>globalThis.PWNED=1</script>'
    d=parse_source('/- '+attack+' -/\ntheorem t : True := by trivial')
    d.title=attack+'__DOCUMENT_DATA__'
    page.set_content(html_document(d))
    assert page.evaluate('globalThis.PWNED') is None
    assert page.locator('#library-title').inner_text()==d.title
    assert len(page.query_selector_all('script'))==2


def test_empty_filter_recovery_and_coverage(page):
    d=parse_source('theorem t : True := by secret_solver')
    page.set_content(html_document(d))
    page.locator('[data-filter="typed"]').click()
    assert page.locator('#empty').is_visible()
    page.locator('[data-filter="all"]').click()
    assert page.locator('#reader').is_visible()
    page.locator('#coverage-btn').click()
    assert page.locator('#coverage-dialog').is_visible()
    assert page.locator('.metric strong').last.inner_text()=='0'


def test_mobile_has_no_horizontal_overflow(page):
    page.set_viewport_size({'width':390,'height':844})
    d=parse_source('theorem ordinary : True := by\n  trivial\n')
    page.set_content(html_document(d))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def test_real_openai_demo_all_nine_declarations(page):
    from proofreader.corpus import local_manifest
    from proofreader.source import merge_documents
    root=Path(__file__).resolve().parents[1]/'examples/openai'
    d=merge_documents([parse_source((root/e['path']).read_text(),e['path']) for e in local_manifest(root)['files']])
    page.set_content(html_document(d))
    assert page.locator('#declaration-list button').count()==9
    for name in ['symmetric_mahler','exists_growth_constant','nonpolynomiality','logarithmic_independence_bound']:
        page.locator('#search').fill(name)
        assert page.locator('#declaration-list button').count()==1
        assert page.locator('#reader').is_visible()
        page.locator('#expand-btn').click()
        page.locator('#collapse-btn').click()


def typed_demo():
    return load_document((Path(__file__).parents[1]/'proofreader/data/kernel-demo.json').read_bytes())

def test_typed_parameters_are_assumptions_not_objects(page):
    page.set_content(html_document(typed_demo()))
    assert page.locator('#theorem-title').inner_text()=='injective comp'
    p=page.locator('#parameters').inner_text()
    assert 'Assume f is injective' in p and 'Assume g is injective' in p
    assert 'Let X be a type' in p
    assert '(x = y)' in page.locator('#proof-steps').inner_text()
    assert page.locator('.support-link').count()>=1
    page.locator('.support-link').last.click()
    assert page.locator('#inspector').is_visible()
    assert 'Original proof path:' in page.locator('#inspector-detail').inner_text()

def test_typed_receipt_scope_is_visible(page):
    page.set_content(html_document(typed_demo()))
    page.locator('#search').fill('PRSmoke.and_swap')
    page.locator('#tab-audit').click()
    audit=page.locator('#audit').inner_text()
    assert 'independently replayed original proof paths' in audit
    assert 'Not authenticated' in audit and 'Not certified' in audit
    assert '4.34.0' in audit and 'None reported by Lean' in audit

def test_typed_filter_separates_source_from_export(page):
    page.set_content(html_document(typed_demo()))
    page.locator('[data-filter="typed"]').click()
    assert page.locator('#declaration-list button').count()==5
    page.locator('[data-filter="all"]').click()
    assert page.locator('#declaration-list button').count()==14

def test_typed_mobile_no_horizontal_overflow(page):
    page.set_viewport_size({'width':390,'height':844})
    page.set_content(html_document(typed_demo()))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#tab-audit').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def narrative_demo():
    return load_document((Path(__file__).parents[1]/'proofreader/data/narrative-demo.json').read_bytes())


def test_substantial_narrative_cases_visible(page):
    page.set_content(html_document(narrative_demo()))
    assert page.locator('#evidence-badge').text_content()=='Source-bound snapshot'
    assert 'pretty-printer' in page.locator('#trust-banner').inner_text()
    assert 'Euclidean domain' in page.locator('#parameters').inner_text()
    assert page.get_by_text('Case g = 0.',exact=True).is_visible()
    assert page.get_by_text('Case g ≠ 0.',exact=True).is_visible()
    assert page.get_by_text('Take (a, d, b, c) = (1, y, 0, 1).',exact=True).is_visible()
    assert 'y' in page.locator('#statement').inner_text()


def test_substantial_narrative_polynomial_inspector(page):
    page.set_content(html_document(narrative_demo()))
    page.locator('#expand-btn').click()
    step=page.locator('[data-step-id="n'+narrative_demo().provenance['snapshot_sha256'][:16]+':47"]')
    step.locator('.step-inspect').first.click()
    assert 'integer-polynomial certificate' in page.locator('#inspector-detail').inner_text()
    assert 'Original proof paths: f47=' in page.locator('#inspector-detail').inner_text()
    assert 'ha' in page.locator('#inspector-context').inner_text()


def test_substantial_receipt_scope_and_proof_source(page):
    d=narrative_demo();page.set_content(html_document(d))
    page.locator('#tab-audit').click()
    audit=page.locator('#audit').inner_text()
    assert '86 selected original proof subterms' in audit
    assert '4.34.1' in audit and '16 exact integer-polynomial' in audit
    assert 'Not authenticated' in audit and 'Not certified' in audit
    page.locator('#tab-source').click()
    assert 'theorem exists_frame' in page.locator('#exact-source').inner_text()
    assert 'gcd_eq_gcd_ab' in page.locator('#exact-source').inner_text()


def test_mixed_library_narrative_filter_and_search(page):
    d=load_document((Path(__file__).parents[1]/'proofreader/data/reader-demo.json').read_bytes())
    page.set_content(html_document(d))
    page.locator('[data-filter="typed"]').click()
    assert page.locator('#declaration-list button').count()==6
    page.locator('#search').fill('BezoutFrame')
    assert page.locator('#declaration-list button').count()==1
    page.locator('#coverage-btn').click()
    assert '1 source-bound snapshots' in page.locator('#coverage-summary').inner_text()
    assert page.locator('.metric strong').last.inner_text()=='0'


def test_substantial_mobile_expansion_and_audit_no_overflow(page):
    page.set_viewport_size({'width':390,'height':844})
    page.set_content(html_document(narrative_demo()))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#expand-btn').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#tab-audit').click()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')



# File: proofreader/narrative.py

"""Deterministic mathematical prose from source-bound Lean judgement snapshots.

This route is separate from the exact constructor-DAG route. The snapshot is
small because the complete proof remains in the supplied Lean source. Its
formula strings come from Lean's pretty-printer. Re-extraction and comparison
bind the snapshot to that source; reading alone never executes or authenticates
Lean. Our English templates and pretty-printer are not formally proved correct.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
import copy
from pathlib import Path
import re
from typing import Any

from .model import Declaration, Document, Span, Step, canonical_json, digest, walk_steps
from .kernel import InvalidExport, require
from .kernel_io import strict_json, STANDARD_AXIOMS
from .polynomial import certify, verify as verify_polynomial, certificate_text

SCHEMA = 'proofreader.narrative/v1'
PRINTER_VERSION = 'source-math-en/0.3.0'
ROLES = {'introduce','assume','have','define','witness','choose','cases','combine','chain',
         'reflexivity','cancel','identity','given','named','application','ring','rewrite','unexpanded'}
_HEAD_ROLES = {'Exists.intro':'witness','Exists.casesOn':'choose','Exists.elim':'choose',
               'And.intro':'combine','Trans.trans':'chain','Eq.trans':'chain',
               'mul_left_cancel₀':'cancel','id':'identity','Eq.refl':'reflexivity',
               'dite':'cases','ite':'cases','Decidable.byCases':'cases','Classical.byCases':'cases',
               'Or.elim':'cases','Or.casesOn':'cases'}
_REWRITES = {'Eq.mpr','Eq.mp','of_eq_true','congrArg','congr','congrFun',"congrFun'"}
_LEMMAS = {
    'EuclideanDomain.gcd_eq_zero_iff': 'A gcd is zero exactly when both entries are zero.',
    'EuclideanDomain.gcd_dvd_left': 'The gcd divides its first entry.',
    'EuclideanDomain.gcd_dvd_right': 'The gcd divides its second entry.',
    'EuclideanDomain.gcd_eq_gcd_ab': 'Use the Bézout identity supplied by the extended Euclidean algorithm.',
    'EuclideanDomain.instIsDomain': 'A Euclidean domain is an integral domain.',
    'IsDomain.toIsCancelMulZero': 'In an integral domain, multiplication by a nonzero element is cancellative.',
    'IsCancelMulZero.toIsLeftCancelMulZero': 'Use left cancellation away from zero.',
    'mul_one': 'Multiplication by one leaves the element unchanged.',
    'Eq.symm': 'Reverse the supplied equality.',
    'Iff.mp': 'Apply the forward direction of the stated equivalence to the supplied hypothesis.',
    'And.left': 'Take the first conjunct.',
    'And.right': 'Take the second conjunct.',
}
_BASE = {'id','path','statement','role','head','context','children','premises','objects','budget_cut'}
_EXTRAS = {'binder','domain','value'}
_TOP = {'schema','theorem','lean_version','axioms','statement','frames','judgements_checked','formula_backend'}


def _string(s: Any, limit: int = 20000) -> None:
    require(isinstance(s,str) and len(s) <= limit and '\x00' not in s, 'Invalid narrative string')


class Snapshot:
    def __init__(self, record: dict):
        require(isinstance(record,dict) and set(record) == _TOP, 'Unknown or missing snapshot fields')
        self.record = copy.deepcopy(record)
        r = self.record
        require(r['schema'] == SCHEMA, 'Unsupported narrative schema')
        _string(r['theorem']); _string(r['statement'],100000)
        require(isinstance(r['lean_version'],str) and bool(re.fullmatch(r'4\.\d+\.\d+',r['lean_version'])), 'Invalid exact Lean version')
        require(r['formula_backend'] == 'Lean pretty-printer', 'Unknown formula backend')
        ax = r['axioms']
        require(isinstance(ax,list) and all(isinstance(x,str) for x in ax) and len(set(ax)) == len(ax), 'Invalid axiom list')
        require(set(ax) <= STANDARD_AXIOMS, 'Snapshot has nonstandard or incomplete axioms')
        self.frames = r['frames']
        require(isinstance(self.frames,list) and 0 < len(self.frames) <= 1000, 'Narrative frame budget')
        require(type(r['judgements_checked']) is int and r['judgements_checked'] == len(self.frames), 'Judgement inventory mismatch')
        parents: dict[int,int] = {}
        paths = set()
        for i, f in enumerate(self.frames):
            require(isinstance(f,dict) and _BASE <= set(f) and set(f) <= _BASE | _EXTRAS, 'Invalid frame fields')
            require(type(f['id']) is int and f['id'] == i, 'Noncanonical frame id')
            path = f['path']
            require(isinstance(path,list) and len(path) <= 4096 and all(type(x) is int and x in (0,1,2) for x in path), 'Invalid proof path')
            require(tuple(path) not in paths, 'Repeated source path')
            paths.add(tuple(path))
            require(isinstance(f['role'],str) and f['role'] in ROLES and type(f['budget_cut']) is bool, 'Invalid frame role or budget flag')
            for k in ('statement','head'):
                _string(f[k])
            role,head = f['role'],f['head']
            if head.startswith('Mathlib.Tactic.Ring.'):
                require(role == 'ring', 'Arithmetic role mismatch')
            elif head in _REWRITES:
                require(role == 'rewrite', 'Rewrite role mismatch')
            elif head in _HEAD_ROLES and not f['budget_cut']:
                require(role == _HEAD_ROLES[head], 'Logical rule mismatch')
            require(isinstance(f['context'],list) and len(f['context']) <= 256, 'Context budget')
            for c in f['context']:
                require(isinstance(c,dict) and set(c) == {'name','type'}, 'Invalid context entry')
                _string(c['name']); _string(c['type'])
            require(isinstance(f['objects'],list) and len(f['objects']) <= 256, 'Object argument budget')
            for x in f['objects']:
                _string(x)
            ch = f['children']
            require(isinstance(ch,list) and all(type(j) is int for j in ch) and len(set(ch)) == len(ch), 'Invalid child list')
            for j in ch:
                require(type(j) is int and i < j < len(self.frames) and j not in parents, 'Invalid narrative tree')
                parents[j] = i
            require(isinstance(f['premises'],list) and len(f['premises']) <= 256, 'Invalid premises')
            arguments = []
            for p in f['premises']:
                require(isinstance(p,dict) and set(p) == {'argument','statement','frame'}, 'Invalid premise fields')
                require(type(p['argument']) is int and 0 <= p['argument'] <= 256 and type(p['frame']) is int and p['frame'] in ch, 'Invalid premise reference')
                arguments.append(p['argument']); _string(p['statement'])
            require(arguments == sorted(set(arguments)), 'Repeated or unordered argument indices')
            if role in {'introduce','assume','define','have'}:
                require({'binder','domain'} <= set(f), 'Missing binder metadata')
                require(len(ch) == (2 if role == 'have' else 1) and not f['premises'], 'Invalid binder children')
            if role == 'define':
                require('value' in f, 'Missing definition value')
            if role == 'given':
                require('binder' in f and not ch, 'Invalid hypothesis frame')
            if role in {'ring','rewrite'}:
                require(not ch and not f['premises'], 'A frontier cannot contain unaccounted children')
            for k in _EXTRAS & set(f):
                _string(f[k])
        require(self.frames[0]['path'] == [] and self.frames[0]['context'] == [], 'Missing root frame')
        require(self.frames[0]['statement'] == r['statement'], 'Root statement mismatch')
        require(set(parents) == set(range(1,len(self.frames))), 'Unreachable frames')
        self.parents = parents
        depths = {0:0}
        for i in range(1,len(self.frames)):
            depths[i] = depths[parents[i]] + 1
            require(depths[i] <= 160, 'Narrative tree depth limit')
            f, parent = self.frames[i], self.frames[parents[i]]
            prefix = parent['path']
            require(len(f['path']) > len(prefix) and f['path'][:len(prefix)] == prefix, 'Child escaped source scope')
            pc,fc = parent['context'],f['context']
            if parent['role'] in {'introduce','assume','have','define'}:
                is_body = i == parent['children'][-1]
                suffix = [1] if parent['role'] in {'introduce','assume'} else [2 if is_body else 1]
                require(f['path'] == prefix+suffix, 'Binder/body path mismatch')
                expected = pc + ([{'name':parent['binder'],'type':parent['domain']}] if is_body else [])
                require(fc == expected, 'Binder context mismatch')
            else:
                require(fc == pc, 'Application changed local context')
        for f in self.frames:
            for p in f['premises']:
                require(p['statement'] == self.frames[p['frame']]['statement'], 'Premise conclusion mismatch')
        self.sha256 = digest(canonical_json(r))

    @classmethod
    def read(cls, path: Path | str) -> 'Snapshot':
        data = Path(path).read_bytes()
        require(len(data) <= 16_000_000, 'Narrative input too large')
        return cls(strict_json(data))

    def coverage(self) -> dict:
        return {'frames':len(self.frames), 'roles':dict(sorted(Counter(f['role'] for f in self.frames).items())),
                'budget_cuts':sum(f['budget_cut'] for f in self.frames),
                'recorded_kernel_judgements':self.record['judgements_checked'],
                'receipt_authenticated':False,'english_formally_verified':False,
                'source_replayed_by_loading':False}


def math_text(s: str) -> str:
    """A small notation dictionary, not a free-form algebra simplifier.

    The exact Lean strings remain in every source-bound frame. Only recognized
    fully qualified gcd symbols with atomic arguments receive ordinary notation.
    """
    atom = r'([^\W\d]\w*|[0-9]+)'
    for constant, shown in [('gcdA','gcdA'),('gcdB','gcdB'),('gcd','gcd')]:
        s = re.sub(r'\bEuclideanDomain\.'+constant+r'\s+'+atom+r'\s+'+atom+r'(?![\w.])',
                   lambda m: f'{shown}({m[1]}, {m[2]})',s,flags=re.UNICODE)
    for symbol, explanation in [('IsDomain', 'an integral domain'),
                                 ('IsCancelMulZero', 'a ring with cancellation away from zero'),
                                 ('IsLeftCancelMulZero', 'a ring with left cancellation away from zero')]:
        m = re.fullmatch(symbol+r' ([^\W\d]\w*)', s, flags=re.UNICODE)
        if m:
            return m[1]+' is '+explanation
    s = s.replace(' * ',' · ').replace(' - ',' − ')
    m = re.fullmatch(r'¬([^\W\d]\w*) = 0',s.strip(),re.UNICODE)
    if m:
        return m[1]+' ≠ 0'
    return s


def _name(s: str) -> str:
    # Internal binder labels are not shown as mathematical objects.
    return s.split('._@.',1)[0]


class Narrative:
    def __init__(self, record: dict):
        self.snapshot = Snapshot(record)
        self.frames = self.snapshot.frames
        self.prefix = self.snapshot.sha256[:16]
        self.owners: dict[int,str] = {}
        self.certificates: dict[int,dict] = {}
        for f in self.frames:
            if f['role'] in {'ring','rewrite'}:
                c = certify(f)
                if c is not None:
                    verify_polynomial(f,c)
                    self.certificates[f['id']] = c
        self.heads: set[str] = set()

    def sid(self, i: int) -> str:
        return 'n'+self.prefix+':'+str(i)

    def claim(self, step: Step, ids: list[int]) -> Step:
        for i in ids:
            require(i not in self.owners, 'A snapshot frame was displayed twice')
            self.owners[i] = step.id
        step.term_id = ','.join('f'+str(i) for i in ids)
        paths = ['f'+str(i)+'='+(''.join(map(str,self.frames[i]['path'])) or 'root') for i in ids]
        step.detail += '\nOriginal proof paths: '+ '; '.join(paths)
        return step

    def step(self, i: int, text: str, *, rule: str | None = None,
             children: list[Step] | None = None, conclusion: str | None = None,
             fallback: bool = False, covered: list[int] | None = None, detail: str = '') -> Step:
        f = self.frames[i]
        if f['head']:
            self.heads.add(f['head'])
        s = Step(self.sid(i),rule or f['role'],text,evidence='source-bound-snapshot',
                 conclusion=conclusion,children=children or [],context=f['context'],
                 source=f['statement'],references=[f['head']] if f['head'] else [],
                 fallback=fallback or f['budget_cut'],detail=detail)
        return self.claim(s,covered or [i])

    def flat_chain(self, i: int) -> tuple[list[int],list[int]]:
        f = self.frames[i]
        if f['role'] != 'chain' or len(f['children']) != 2:
            return [i],[]
        left, li = self.flat_chain(f['children'][0]); right, ri = self.flat_chain(f['children'][1])
        return left+right,[i]+li+ri

    def flat_conjunction(self, i: int) -> tuple[list[int],list[int]]:
        f = self.frames[i]
        if f['role'] != 'combine' or len(f['children']) != 2:
            return [i],[]
        a,ai = self.flat_conjunction(f['children'][0]);b,bi = self.flat_conjunction(f['children'][1])
        return a+b,[i]+ai+bi

    def sequence(self, i: int) -> list[Step]:
        f = self.frames[i]; ch=f['children']; role=f['role']; con=math_text(f['statement'])
        if role in {'define','have'}:
            name=_name(f['binder']); domain=math_text(f['domain'])
            if role=='define':
                value=math_text(f['value'])
                note = (' This is the first Bézout coefficient.' if f['value'].startswith('EuclideanDomain.gcdA ') else
                        ' This is the second Bézout coefficient.' if f['value'].startswith('EuclideanDomain.gcdB ') else '')
                s=self.step(i,f'Set {name} = {value}.'+note,conclusion=None)
            else:
                s=self.step(i,f'Establish {domain}; call this fact {name}.',children=self.sequence(ch[0]))
            return [s]+self.sequence(ch[-1])
        if role=='cases' and len(ch)==2 and all(self.frames[j]['role']=='assume' for j in ch):
            branches=[]
            for j in ch:
                b=self.frames[j]
                if b['role']=='assume':
                    branches.append(self.step(j,'Case '+math_text(b['domain'])+'.',rule='case',children=self.sequence(b['children'][0])))
                else:
                    branches.extend(self.sequence(j))
            return [self.step(i,'Consider the following cases.',children=branches)]
        if role=='choose' and len(ch)==2:
            intro=self.frames[ch[1]]
            assumption=self.frames[intro['children'][0]] if intro['role']=='introduce' and intro['children'] else {}
            if assumption.get('role')=='assume':
                fact=math_text(self.frames[ch[0]]['statement'])
                name=_name(intro['binder']);typ=math_text(intro['domain']); prop=math_text(assumption['domain'])
                s=self.step(i,f'Since {fact}, choose {name} ∈ {typ} with {prop}.',
                            children=self.sequence(ch[0]),covered=[i,intro['id'],assumption['id']])
                return [s]+self.sequence(assumption['children'][0])
        if role=='identity' and len(ch)==2 and self.frames[ch[0]]['role']=='assume':
            binder=self.frames[ch[0]]
            s=self.step(i,'Use the same hypothesis in the form '+math_text(binder['domain'])+'.',
                        rule='equivalent-assumption',children=self.sequence(ch[1]),covered=[i,binder['id']])
            return [s]+self.sequence(binder['children'][0])
        if role=='witness':
            ids=[]; names=[]; values=[]; j=i
            while self.frames[j]['role']=='witness' and len(self.frames[j]['children'])==1:
                b=self.frames[j]
                if len(b['objects'])!=3:
                    break
                match=re.match(r'^∃\s+([^\s,:]+)',b['statement'])
                if match is None:
                    break
                ids.append(j);names.append(match[1]);values.append(math_text(b['objects'][-1]));j=b['children'][0]
            if ids:
                text='Take '+(', '.join(names) if len(names)==1 else '('+', '.join(names)+')')+' = '+(values[0] if len(values)==1 else '('+', '.join(values)+')')+'.'
                s=self.step(i,text,covered=ids)
                return [s]+self.sequence(j)
        if role=='combine' and len(ch)==2:
            leaves,parents=self.flat_conjunction(i)
            return [self.step(i,'Verify the '+str(len(leaves))+' required conclusions.',rule='verify-conclusions',
                              covered=parents,children=[s for j in leaves for s in self.sequence(j)])]
        if role=='chain' and len(ch)==2:
            leaves,parents=self.flat_chain(i)
            return [self.step(i,'The following calculation gives '+con+'.',rule='calculation',covered=parents,
                              children=[s for j in leaves for s in self.sequence(j)])]
        if i in self.certificates:
            c=self.certificates[i]
            assumptions=c['assumptions']
            if assumptions:
                basis=' and '.join(math_text(a['statement']) for a in assumptions)
                text='Using '+basis+', expand and collect terms.'
            else:
                text='Expand and collect terms.'
            return [self.step(i,text,rule='polynomial-identity',conclusion=con,
                              detail='Independent integer-polynomial certificate: '+certificate_text(c)+
                              '\nThis check is under the recorded local assumptions; it does not authenticate their Lean provenance.')]
        if role=='cancel':
            text='Cancel the nonzero common factor'+(' '+math_text(f['objects'][-3]) if len(f['objects'])>=3 else '')+' to obtain '+con+'.'
        elif role=='given':
            text='Use the hypothesis '+_name(f['binder'])+': '+con+'.'
        elif role=='assume':
            text='Assume '+math_text(f['domain'])+'.'
        elif role=='introduce':
            text='Let '+_name(f['binder'])+' ∈ '+math_text(f['domain'])+' be arbitrary.'
        elif role=='reflexivity':
            text='By reflexivity, '+con+'.'
        elif f['head'] in _LEMMAS:
            text=_LEMMAS[f['head']]
        else:
            text='Apply '+(f['head'] or 'the recorded term')+' to the supplied arguments.'
        fallback=role in {'ring','rewrite','unexpanded','cases','choose','identity','combine','chain','witness'} or (role in {'application','named'} and f['head'] not in _LEMMAS)
        child_steps=[s for j in ch for s in self.sequence(j)]
        s=self.step(i,text,children=child_steps,
                    conclusion=None if con in text or role in {'assume','introduce'} else con,fallback=fallback)
        if role in {'assume','introduce'}:
            s.children=[]
            return [s]+child_steps
        return [s]

    def document(self, *, source: str = '', file: str = 'Original.lean', receipt: dict | None = None, title: str | None = None, provenance_note: str | None = None) -> Document:
        self.owners={};self.heads=set();s=self.snapshot
        require(receipt is None or receipt.get('snapshot_sha256') == s.sha256, 'Receipt belongs to another snapshot')
        params=[];i=0;prefix=[]
        while self.frames[i]['role'] in {'introduce','assume'}:
            f=self.frames[i];prefix.append(i);name=_name(f['binder']);domain=math_text(f['domain'])
            if f['role']=='assume':
                text='Assume '+domain+'.'
                params.append({'text':text,'names':name,'type':domain,'binder':'('})
            else:
                m=re.fullmatch(r'EuclideanDomain (\w+)',domain)
                if m:
                    prior=next((p for p in params if p['names']==m[1] and p['type'].startswith('Type')),None)
                    if prior:
                        prior['text']='Let '+m[1]+' be a Euclidean domain.'
                    else:
                        params.append({'text':'Assume '+domain+'.','names':name,'type':domain,'binder':'['})
                elif domain == 'Prop':
                    params.append({'text':'Let '+name+' be a proposition.','names':name,'type':domain,'binder':'('})
                elif domain.startswith('Type') or domain.startswith('Sort'):
                    params.append({'text':'Let '+name+' be a type.','names':name,'type':domain,'binder':'('})
                elif params and params[-1]['type']==domain and params[-1]['binder']=='(' and params[-1]['text'].startswith('Let ') and ('elements of' in params[-1]['text'] or 'an element of' in params[-1]['text']):
                    prior=params[-1];prior['names']+=', '+name;prior['text']='Let '+prior['names']+' be elements of '+domain+'.'
                else:
                    params.append({'text':'Let '+name+' be an element of '+domain+'.','names':name,'type':domain,'binder':'('})
            i=f['children'][0]
        for j in prefix:
            self.owners[j]='statement'
        steps=self.sequence(i)
        require(set(self.owners)==set(range(len(self.frames))), 'Display omitted an exported frame')
        warnings=['Formula strings use Lean’s pretty-printer. The English renderer is deterministic, not formally verified.',
                  'Reading and certificate replay do not authenticate a Lean snapshot. Re-extract from trusted source before relying on imported evidence.']
        if provenance_note:
            warnings.append(provenance_note)
        dec=Declaration('narrative:'+self.prefix,s.record['theorem'],'theorem',file,math_text(self.frames[i]['statement']),source,
                        Span(0,len(source),1,max(1,len(source.splitlines()))),parameters=params,steps=steps,
                        warnings=warnings,evidence='source-bound-snapshot',dependencies=sorted(self.heads),receipt=receipt,
                        axes={'discovery':'named-Lean-theorem','statement':'Lean-derived formula snapshot',
                              'proof':'source-bound-kernel-snapshot','english_fidelity':'not-certified',
                              'snapshot_sha256':s.sha256,'lean_version':s.record['lean_version'],
                              'axiom_status':{'acceptable':True,'axioms':s.record['axioms']},
                              'printer_version':PRINTER_VERSION,'frame_owners':{str(k):v for k,v in sorted(self.owners.items())},
                              'polynomial_certificates':len(self.certificates)})
        doc=Document(title or ('Lean ProofReader · '+s.record['theorem'].split('.')[-1].replace('_',' ')),
                     [{'path':file,'sha256':digest(source),'source':source}], [dec],
                     provenance={'snapshot_sha256':s.sha256,'scope':'one selected theorem',
                                 'source_replayed_by_rendering':False,'pipeline_model_calls':0,
                                 'receipt_authenticated':False,'whole_corpus_coverage':False,
                                 'english_formally_verified':False,'formula_backend':s.record['formula_backend'],
                                 'snapshot_coverage':s.coverage(),'independent_polynomial_certificates':len(self.certificates)})
        return doc


def reading_binding(document: Document) -> str:
    require(len(document.declarations)==1, 'Expected one narrative declaration')
    d=asdict(document.declarations[0])
    for key in ('receipt','warnings','file','span'):
        d.pop(key,None)
    return digest(canonical_json(d))


def check_reading(record: dict, document: Document) -> None:
    require(len(document.declarations)==1, 'Expected one reading')
    d=document.declarations[0]
    expected=Narrative(record).document(source=d.source,file=d.file)
    require(reading_binding(expected)==reading_binding(document), 'Reading differs from deterministic regeneration')


def prose(document: Document) -> str:
    d=document.declarations[0]
    out=[document.title,'',*(p['text'] for p in d.parameters),'Then '+d.statement+'.','','Proof.']
    def emit(steps,depth=0):
        for s in steps:
            out.append('  '*depth+s.text)
            if s.conclusion:
                out.append('  '*(depth+1)+s.conclusion)
            emit(s.children,depth+1)
    emit(d.steps)
    return '\n'.join(out)+'\n'



# File: proofreader/polynomial.py

"""Small exact, independently replayable commutative-ring certificates.

No CAS, numerical tolerances or network calls are used. This is deliberately a
restricted parser: ASCII/Unicode identifiers from an explicitly supplied scalar
context, integers, +, -, *, parentheses and small natural powers. A certificate
asserts an *integer polynomial identity* G = sum(M_i A_i), not division in a field.
The surrounding Lean snapshot must independently establish that all variables
belong to the same commutative ring and that A_i=0 are available assumptions.
"""
from __future__ import annotations
from fractions import Fraction
from itertools import combinations, combinations_with_replacement
import re
from typing import Any

Monomial = tuple[tuple[str, int], ...]
Poly = dict[Monomial, Fraction]
MAX_TERMS = 512
MAX_DEGREE = 12
MAX_TOKENS = 300


class UnsupportedPolynomial(ValueError):
    pass


def guard(test: bool, message: str) -> None:
    if not test:
        raise UnsupportedPolynomial(message)


def degree(m: Monomial) -> int:
    return sum(p for _, p in m)


def tidy(p: Poly) -> Poly:
    p = {m: Fraction(c) for m, c in p.items() if c}
    guard(len(p) <= MAX_TERMS and all(degree(m) <= MAX_DEGREE for m in p), 'Polynomial expansion limit')
    return p


def add(p: Poly, q: Poly, scale: Fraction = Fraction(1)) -> Poly:
    r = dict(p)
    for m, c in q.items():
        r[m] = r.get(m, Fraction(0)) + scale * c
    return tidy(r)


def mul(p: Poly, q: Poly) -> Poly:
    guard(len(p) * len(q) <= 40_000, 'Polynomial product budget')
    r: Poly = {}
    for a, x in p.items():
        for b, y in q.items():
            d = dict(a)
            for v, power in b:
                d[v] = d.get(v, 0) + power
            m = tuple(sorted(d.items()))
            r[m] = r.get(m, Fraction(0)) + x * y
    return tidy(r)


def power(p: Poly, n: int) -> Poly:
    guard(0 <= n <= MAX_DEGREE, 'Power is outside the supported budget')
    result: Poly = {(): Fraction(1)}
    for _ in range(n):
        result = mul(result, p)
    return result


_TOKEN = re.compile(r'\s*(?:(\d+)|([^\W\d]\w*)|([()+*^\-]))', re.UNICODE)


class Parser:
    def __init__(self, s: str, variables: set[str]):
        guard(isinstance(s, str) and len(s) <= 10_000, 'Expression size limit')
        self.variables = variables
        self.tokens: list[str] = []
        i = 0
        while i < len(s):
            if s[i:].isspace():
                break
            m = _TOKEN.match(s, i)
            guard(m is not None, 'Unsupported polynomial notation')
            assert m is not None
            self.tokens.append(next(x for x in m.groups() if x is not None))
            i = m.end()
            guard(len(self.tokens) <= MAX_TOKENS, 'Polynomial token budget')
        self.i = 0

    def peek(self) -> str:
        return self.tokens[self.i] if self.i < len(self.tokens) else ''

    def pop(self) -> str:
        result = self.peek()
        guard(bool(result), 'Unexpected end of expression')
        self.i += 1
        return result

    def sum(self) -> Poly:
        p = self.product()
        while self.peek() in {'+', '-'}:
            sign = 1 if self.pop() == '+' else -1
            p = add(p, self.product(), Fraction(sign))
        return p

    def product(self) -> Poly:
        p = self.unary()
        while self.peek() == '*':
            self.pop()
            p = mul(p, self.unary())
        return p

    def unary(self) -> Poly:
        if self.peek() in {'-', '+'}:
            sign = -1 if self.pop() == '-' else 1
            return {m: sign * c for m, c in self.unary().items()}
        return self.exponent()

    def exponent(self) -> Poly:
        token = self.pop()
        if token == '(':
            p = self.sum()
            guard(self.pop() == ')', 'Unmatched parenthesis')
        elif token.isdecimal():
            guard(len(token) <= 12, 'Integer too large')
            n = int(token)
            p = {(): Fraction(n)} if n else {}
        else:
            guard(token in self.variables, 'Unbound or unsupported scalar: ' + token)
            p = {((token, 1),): Fraction(1)}
        if self.peek() == '^':
            self.pop()
            n = self.pop()
            guard(n.isdecimal() and len(n) <= 2, 'Expected a small natural exponent')
            p = power(p, int(n))
        return p

    def parse(self) -> Poly:
        p = self.sum()
        guard(self.i == len(self.tokens), 'Trailing polynomial tokens')
        return tidy(p)


def parse(s: str, variables: set[str]) -> Poly:
    return Parser(s, variables).parse()


def equality(s: str, variables: set[str]) -> Poly:
    guard(s.count('=') == 1, 'Expected one polynomial equality')
    lhs, rhs = s.split('=')
    return add(parse(lhs, variables), parse(rhs, variables), Fraction(-1))


def encode(p: Poly) -> list[list[Any]]:
    guard(all(c.denominator == 1 for c in p.values()), 'Rational multiplier is not valid in every ring')
    return [[[[v, e] for v, e in m], c.numerator] for m, c in sorted(p.items())]


def decode(rows: Any, variables: set[str]) -> Poly:
    guard(isinstance(rows, list) and len(rows) <= MAX_TERMS, 'Invalid polynomial rows')
    p: Poly = {}
    for row in rows:
        guard(isinstance(row, list) and len(row) == 2, 'Invalid monomial row')
        factors, coefficient = row
        guard(type(coefficient) is int and coefficient != 0 and abs(coefficient) < 10**30, 'Invalid integer coefficient')
        guard(isinstance(factors, list) and len(factors) <= MAX_DEGREE, 'Invalid factors')
        converted = []
        for f in factors:
            guard(isinstance(f, list) and len(f) == 2 and isinstance(f[0], str), 'Invalid factor')
            v, e = f
            guard(v in variables and type(e) is int and 0 < e <= MAX_DEGREE, 'Invalid variable or exponent')
            converted.append((v, e))
        m = tuple(converted)
        guard(list(m) == sorted(m) and len({v for v, _ in m}) == len(m) and m not in p, 'Noncanonical monomial')
        p[m] = Fraction(coefficient)
    p = tidy(p)
    guard(encode(p) == rows, 'Noncanonical polynomial')
    return p


def _order(m: Monomial) -> tuple:
    return degree(m), m


def solve(target: Poly, assumptions: list[Poly], max_columns: int = 600) -> list[Poly] | None:
    """Bounded exact ideal-membership search; replay uses only add/mul, not this solver.

    Linear algebra is over Q for efficiency, but a result with any noninteger
    coefficient is rejected: 2x=0 must never justify x=0 in a ring of characteristic 2.
    """
    if not target:
        return [{} for _ in assumptions]
    goal_degree = max(map(degree, target))
    variables = sorted({v for p in [target, *assumptions] for m in p for v, _ in m})
    columns: list[tuple[int, Monomial, Poly]] = []
    for i, a in enumerate(assumptions):
        if not a:
            continue
        d = max(map(degree, a))
        if d > goal_degree:
            continue
        for k in range(goal_degree - d + 1):
            for vs in combinations_with_replacement(variables, k):
                powers: dict[str, int] = {}
                for v in vs:
                    powers[v] = powers.get(v, 0) + 1
                m = tuple(sorted(powers.items()))
                columns.append((i, m, mul({m: Fraction(1)}, a)))
                if len(columns) > max_columns:
                    return None
    # pivot -> (normalized polynomial, combination of original columns)
    basis: dict[Monomial, tuple[Poly, dict[int, Fraction]]] = {}
    for index, (_, _, column) in enumerate(columns):
        p, combo = column.copy(), {index: Fraction(1)}
        while p:
            pivot = max(p, key=_order)
            c = p[pivot]
            if pivot not in basis:
                basis[pivot] = ({m: x/c for m, x in p.items()}, {k: x/c for k, x in combo.items()})
                break
            vector, vec_combo = basis[pivot]
            p = add(p, vector, -c)
            for k, x in vec_combo.items():
                combo[k] = combo.get(k, Fraction(0)) - c*x
                if not combo[k]:
                    del combo[k]
    p, answer = target.copy(), {}
    while p:
        pivot = max(p, key=_order)
        if pivot not in basis:
            return None
        c = p[pivot]
        vector, combo = basis[pivot]
        p = add(p, vector, -c)
        for k, x in combo.items():
            answer[k] = answer.get(k, Fraction(0)) + c*x
    multipliers: list[Poly] = [{} for _ in assumptions]
    for k, c in answer.items():
        if not c:
            continue
        i, m, _ = columns[k]
        multipliers[i][m] = multipliers[i].get(m, Fraction(0)) + c
    multipliers = [tidy(m) for m in multipliers]
    if any(c.denominator != 1 for p in multipliers for c in p.values()):
        return None
    total: Poly = {}
    for m, a in zip(multipliers, assumptions):
        total = add(total, mul(m, a))
    return multipliers if total == target else None


def scalar_context(frame: dict) -> tuple[str, set[str]]:
    """Only exact, recognized class applications; no substring-based ring guess."""
    types = [c['type'].strip() for c in frame['context']]
    rings = []
    for t in types:
        m = re.fullmatch(r'(?:EuclideanDomain|CommRing) ([^\W\d]\w*)', t, re.UNICODE)
        if m:
            rings.append(m[1])
    guard(len(set(rings)) == 1, 'No unique recognized commutative ring in local context')
    ring = rings[0]
    # Later binders shadow earlier names. Only expose scalar variables.
    last = {c['name']: c['type'].strip() for c in frame['context']}
    variables = {n for n, t in last.items() if t == ring and re.fullmatch(r'[^\W\d]\w*', n, re.UNICODE)}
    guard(0 < len(variables) <= 20, 'Scalar-context size is unsupported')
    return ring, variables


def _conjuncts(s: str) -> list[str]:
    # The restricted parser will reject embedded quantifiers, negation and
    # implication, so splitting only top-level conjunctions cannot strengthen them.
    out, depth, begin = [], 0, 0
    for i, ch in enumerate(s):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == '∧' and depth == 0:
            out.append(s[begin:i].strip()); begin = i+1
    out.append(s[begin:].strip())
    return out


def assumptions(frame: dict, variables: set[str]) -> list[tuple[dict, Poly]]:
    result = []
    contexts = frame['context']
    last = {c['name']: i for i, c in enumerate(contexts)}
    for i, c in enumerate(contexts):
        if last[c['name']] != i:
            continue
        # Reject the WHOLE proposition if any part is not an equality.
        # In particular, (P → x=0 ∧ y=0) must not supply the unconditional y=0.
        parts = _conjuncts(c['type'])
        try:
            parsed = [equality(claim, variables) for claim in parts]
        except (UnsupportedPolynomial, RecursionError):
            continue
        for j, (claim, p) in enumerate(zip(parts, parsed)):
            if p:
                result.append(({'context_index': i, 'conjunct': j, 'name': c['name'], 'statement': claim}, p))
    return result


def certify(frame: dict, max_assumptions: int = 2) -> dict | None:
    """Find a small certificate, preferring fewer assumptions in fixed order."""
    try:
        ring, variables = scalar_context(frame)
        target = equality(frame['statement'], variables)
        available = assumptions(frame, variables)
        if len(available) > 20:
            return None
        for count in range(min(max_assumptions, len(available)) + 1):
            for selected in combinations(available, count):
                multipliers = solve(target, [p for _, p in selected])
                if multipliers is not None:
                    result = {'schema': 'proofreader.polynomial-certificate/v1', 'frame_id': frame['id'],
                              'ring': ring, 'variables': sorted(variables), 'goal': frame['statement'],
                              'assumptions': [a for a, _ in selected],
                              'multipliers': [encode(p) for p in multipliers]}
                    verify(frame, result)
                    return result
    except (UnsupportedPolynomial, RecursionError):
        return None
    return None


def verify(frame: dict, certificate: dict) -> None:
    """Independently reconstruct and check the claimed identity against a snapshot.

    A passing check does not authenticate the snapshot or establish its Lean
    provenance. Use source replay for that separate question.
    """
    guard(isinstance(certificate, dict), 'Invalid certificate')
    guard(set(certificate) == {'schema','frame_id','ring','variables','goal','assumptions','multipliers'}, 'Unknown certificate fields')
    guard(certificate['schema'] == 'proofreader.polynomial-certificate/v1', 'Unsupported certificate schema')
    guard(type(certificate['frame_id']) is int and certificate['frame_id'] == frame['id'], 'Wrong certificate frame')
    ring, variables = scalar_context(frame)
    guard(certificate['ring'] == ring and certificate['variables'] == sorted(variables), 'Wrong scalar context')
    guard(certificate['goal'] == frame['statement'], 'Certificate goal mismatch')
    target = equality(frame['statement'], variables)
    available = { (a['context_index'], a['conjunct']): (a,p) for a,p in assumptions(frame, variables) }
    aa, mm = certificate['assumptions'], certificate['multipliers']
    guard(isinstance(aa,list) and isinstance(mm,list) and len(aa) == len(mm) and len(aa) <= 20, 'Invalid certificate dimensions')
    total: Poly = {}
    seen = set()
    for a, encoded in zip(aa, mm):
        guard(isinstance(a,dict) and type(a.get('context_index')) is int and type(a.get('conjunct')) is int, 'Invalid assumption reference')
        key = a['context_index'], a['conjunct']
        guard(key in available and key not in seen, 'Missing or repeated assumption')
        seen.add(key)
        actual, p = available[key]
        guard(a == actual, 'Assumption changed from local context')
        total = add(total, mul(decode(encoded, variables), p))
    guard(total == target, 'Polynomial certificate identity failed')


def polynomial_text(p: Poly) -> str:
    if not p:
        return '0'
    pieces = []
    for m in sorted(p, key=_order, reverse=True):
        c = p[m]
        monomial = ' · '.join(v if n == 1 else f'{v}^{n}' for v, n in m)
        magnitude = abs(c)
        term = monomial if magnitude == 1 and monomial else str(magnitude) + (' · ' + monomial if monomial else '')
        pieces.append(('- ' if c < 0 else '+ ') + term)
    result = ' '.join(pieces)
    return result[2:] if result.startswith('+ ') else '−' + result[2:]


def certificate_text(certificate: dict) -> str:
    variables = set(certificate['variables'])
    terms = []
    for a, m in zip(certificate['assumptions'], certificate['multipliers']):
        lhs, rhs = a['statement'].split('=')
        terms.append(f"({polynomial_text(decode(m,variables))}) · (({lhs.strip()}) − ({rhs.strip()}))")
    return 'LHS − RHS = ' + (' + '.join(terms) if terms else '0') + '. Expand and compare integer coefficients.'



# File: docs/NARRATIVE.md

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

