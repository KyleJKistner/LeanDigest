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

# Acceptance
python -m pytest tests/test_kernel.py tests/test_normalization.py tests/test_browser.py tests/test_render_cli.py -q
Reproduce counterexamples for any changed scope, hypothesis or normalization rule
Report explanation gaps separately from term/type validity

# Known blocker
Five retained typed examples exist; no complete large proof reader or human comprehension benchmark. English grammar and display normalization lack a formal correctness proof.


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
    generator: str = "lean-proofreader/0.2.0"

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

