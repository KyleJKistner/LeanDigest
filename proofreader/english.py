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

PRINTER_VERSION = "math-en/0.3.1"


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
            if name == "List.nil" and arity == 1: return "[]"
            if name == "List.cons" and arity == 3: return f"({r(args[1])} :: {r(args[2])})"
            if name == "List.map" and arity == 4: return f"map({r(args[2])}, {r(args[3])})"
            if name == "Nat.succ" and arity == 1: return f"({r(args[0])} + 1)"
            if name == "Exists" and arity == 2:
                p = self.dag.nodes[args[1]]
                if p["tag"] == "lam":
                    x = fresh_name(p["name"], ctx)
                    return f"(∃ {x} : {r(args[0])}, {r(p['body'], ctx + [x])})"
                x = fresh_name({"tag": "anonymous"}, ctx)
                return f"(∃ {x} : {r(args[0])}, {r(args[1])}({x}))"
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
            return f"(∀ {x} : {dom}, {body})"
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
            # Recursor branches are scoped arguments, not facts established in
            # the parent context. Keep them nested even for an unknown recursor.
            if name in {"Or.elim", "Or.casesOn"} and len(args) >= 6:
                rule = "cases"
                text = (f"Use the disjunction {r(s['arguments'][3]['type'])}. "
                        f"Prove the result separately in the {r(args[0])} case and the {r(args[1])} case; "
                        f"then conclude {con}. Each branch keeps its own assumptions.")
                for k, label in ((4, "First case"), (5, "Second case")):
                    child_index = s['arguments'][k].get('step')
                    children = [replace(c, text=label + ": " + c.text)
                                if c.id == f"{self.aid}:s{child_index}" else c for c in children]
            if name in {"Exists.elim", "Exists.casesOn"} and len(args) == 5:
                rule = "existential-elimination"
                text = (f"Use the existential premise {r(s['arguments'][3]['type'])}. "
                        f"For its chosen witness, the following local argument establishes {con}.")
                child_index = s['arguments'][4].get('step')
                if child_index is not None:
                    child_term = self.dag.nodes[self.argument.steps[child_index]['term']]
                    if child_term['tag'] == 'lam':
                        label = fresh_name(child_term['name'], labels)
                        children = [replace(c, text=f"Fix {label} : {r(child_term['domain'])} as the chosen witness.")
                                    if c.id == f"{self.aid}:s{child_index}" else c for c in children]
            recursors = {
                ("Nat.rec", 4): (3, 1, 2, "natural number", "Zero case", "Successor step"),
                ("List.rec", 5): (4, 2, 3, "list", "Empty-list case", "Cons step"),
            }
            recursor = recursors.get((name, len(args)))
            if recursor is not None:
                major, base, step, kind, base_label, step_label = recursor
                if s['arguments'][base]['is_proof'] and s['arguments'][step]['is_proof']:
                    rule = "induction"
                    text = (f"We prove {con} by induction on the {kind} {r(args[major])}. "
                            f"{base_label}: {r(s['arguments'][base]['type'])}. "
                            f"{step_label}: {r(s['arguments'][step]['type'])}.")
                    for k, label in ((base, base_label), (step, step_label)):
                        child_index = s['arguments'][k].get('step')
                        children = [replace(c, text=label + ": " + c.text)
                                    if c.id == f"{self.aid}:s{child_index}" else c for c in children]
            if name == "congrArg" and len(args) == 6:
                rule = "congruence"
                text = (f"Apply the function {r(args[4])} to both sides of "
                        f"{r(s['arguments'][5]['type'])}. This gives {con}.")
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
        branch_rules = {"introduce", "assume", "have", "let", "cases", "existential-elimination", "contradiction-proof", "induction"}
        def flat(s: Step) -> list[Step]:
            if s.rule in branch_rules or any(c.rule in branch_rules for c in s.children):
                # An application of a locally proved implication/recursor takes
                # whole scoped subarguments. Lifting their assumptions into a
                # common surrounding context would change the displayed proof.
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
                        generator="lean-proofreader/0.3.0")


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
    lines = [d.name, ""] + [p["text"] for p in d.parameters] + ["", "Claim: " + d.statement, "", "Proof."]
    def visit(step: Step, depth: int) -> None:
        # Plain text must contain nested subproofs too; printing only top-level
        # introductions dropped the actual proofs of cases, witnesses and lets.
        lines.append("  " * depth + step.text)
        for child in step.children:
            visit(child, depth + 1)
    for step in d.steps:
        visit(step, 0)
    lines.extend(["", "∎", ""])
    return "\n".join(lines)
