"""Path-bound typed proof IR and replay. Python checks structure; Lean checks types.

This layer deliberately does NOT label an English document as formally verified.
It binds every rendered judgement to an actual original proof subterm and emits
kernel checks for the original proof, intermediate judgements, and data arguments.
Neither a supplied pretty-print string nor an imported receipt is trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import copy
import json
import re
from typing import Any, Iterable

from .core import InvalidExport, BINDERS, NORMALIZE_LEAN, lean_string, name_to_lean, level_to_lean
from .model import canonical_json, digest

SCHEMA = "proofreader.kernel-export/v2"
PATH_LEAN = 'private partial def proofreaderAtPath (e : Lean.Expr) (path : List Nat)\n    (context : List Lean.Expr := []) : Except String (Lean.Expr × List Lean.Expr) := do\n  match path with\n  | [] => return (e, context)\n  | k :: ks =>\n    match e, k with\n    | .app f _, 0 => proofreaderAtPath f ks context\n    | .app _ a, 1 => proofreaderAtPath a ks context\n    | .lam _ d _ _, 0 | .forallE _ d _ _, 0 => proofreaderAtPath d ks context\n    | .lam _ _ b _, 1 | .forallE _ _ b _, 1 => proofreaderAtPath b ks (e :: context)\n    | .letE _ t _ _ _, 0 => proofreaderAtPath t ks context\n    | .letE _ _ v _ _, 1 => proofreaderAtPath v ks context\n    | .letE _ _ _ b _, 2 => proofreaderAtPath b ks (e :: context)\n    | .proj _ _ b, 0 => proofreaderAtPath b ks context\n    | _, _ => throw "Invalid source proof path"\n\nprivate def proofreaderClose (e : Lean.Expr) (context : List Lean.Expr) : Except String Lean.Expr :=\n  context.foldlM (fun value binder => do\n    match binder with\n    | .lam n d _ bi | .forallE n d _ bi => return .lam n d value bi\n    | .letE n t v _ nd => return .letE n t v value nd\n    | _ => throw "Invalid source binder") e\n\nprivate def proofreaderClosedAt (root : Lean.Expr) (path : List Nat) : Except String Lean.Expr := do\n  let (term, context) ← proofreaderAtPath root path\n  proofreaderClose term context\n'

EDGES = {"app": ("fn", "arg"), "lam": ("domain", "body"),
         "forall": ("domain", "body"), "let": ("type", "value", "body"), "proj": ("of",)}
FIELDS = {
    "bvar": {"tag", "index"}, "sort": {"tag", "level"},
    "const": {"tag", "name", "levels"}, "app": {"tag", "fn", "arg"},
    "lam": {"tag", "name", "domain", "body", "binder"},
    "forall": {"tag", "name", "domain", "body", "binder"},
    "let": {"tag", "name", "type", "value", "body", "nondep"},
    "nat": {"tag", "value"}, "str": {"tag", "value"},
    "proj": {"tag", "name", "index", "of"},
}


def require(test: bool, message: str) -> None:
    if not test:
        raise InvalidExport(message)


def nat(x: Any, maximum: int = 2**63 - 1) -> int:
    require(type(x) is int and 0 <= x <= maximum, "Expected a bounded nonnegative integer")
    return x


def name_key(n: Any, depth: int = 0) -> tuple:
    require(isinstance(n, dict) and depth < 128, "Malformed or too deeply nested name")
    t = n.get("tag")
    if t == "anonymous":
        require(set(n) == {"tag"}, "Unknown name field")
        return ()
    require(t in {"str", "num"} and set(n) == {"tag", "prefix", "value"}, "Invalid name constructor")
    v = n["value"]
    require(isinstance(v, str) and len(v) < 100_000, "Invalid name component")
    if t == "num":
        require(bool(re.fullmatch(r"0|[1-9][0-9]*", v)), "Noncanonical numeric name")
    return name_key(n["prefix"], depth + 1) + ((t, v),)


def display_name(n: dict) -> str:
    """An injective spelling: numeric components and dotted string components differ."""
    parts = []
    for tag, v in name_key(n):
        if tag == "num":
            parts.append("#" + v)
        elif re.fullmatch(r"[^\W\d]\w*", v, re.UNICODE):
            parts.append(v)
        else:
            parts.append("[" + json.dumps(v, ensure_ascii=False) + "]")
    return ".".join(parts) or "[anonymous]"


def plain_name(n: dict) -> str | None:
    key = name_key(n)
    if all(t == "str" and re.fullmatch(r"[^\W\d]\w*", v, re.UNICODE) for t, v in key):
        return ".".join(v for _, v in key)
    return None


def validate_level(n: Any, params: set[tuple], depth: int = 0) -> None:
    require(isinstance(n, dict) and depth < 128, "Invalid universe expression")
    tag = n.get("tag")
    if tag == "zero":
        require(set(n) == {"tag"}, "Unknown universe field")
    elif tag == "succ":
        require(set(n) == {"tag", "of"}, "Unknown universe field")
        validate_level(n["of"], params, depth + 1)
    elif tag in {"max", "imax"}:
        require(set(n) == {"tag", "left", "right"}, "Unknown universe field")
        validate_level(n["left"], params, depth + 1)
        validate_level(n["right"], params, depth + 1)
    elif tag == "param":
        require(set(n) == {"tag", "name"}, "Unknown universe field")
        require(name_key(n["name"]) in params, "Undeclared universe parameter")
    else:
        raise InvalidExport("Unsupported/unresolved universe constructor")


class Dag:
    """Topological constructor DAG; open-variable demand and identity are bottom-up.

    The demand calculation permits million-node terms without recursively expanding
    shared terms. Hashes are used as identities, not as mathematical certificates.
    """
    def __init__(self, nodes: list[dict], params: list[dict], limit: int = 250_000):
        require(isinstance(nodes, list) and 0 < len(nodes) <= limit, "Invalid expression inventory size")
        require(isinstance(params, list), "Invalid universe inventory")
        self.params = {name_key(x) for x in params}
        require(len(self.params) == len(params), "Duplicate universe parameters")
        self.nodes = copy.deepcopy(nodes)
        self.hashes: list[str] = []
        self.demand: list[int] = []
        self.intern: dict[str, int] = {}
        for i, n in enumerate(self.nodes):
            self._append_index(n, i)

    def _append_index(self, n: dict, i: int) -> None:
        require(isinstance(n, dict) and n.get("tag") in FIELDS, "Unknown expression constructor")
        tag = n["tag"]
        require(set(n) == FIELDS[tag], f"Unknown/missing fields for {tag}")
        for field in EDGES.get(tag, ()):
            require(nat(n[field]) < i, "DAG edges must refer to earlier expressions")
        if "name" in n:
            name_key(n["name"])
        if tag == "sort":
            validate_level(n["level"], self.params)
        if tag == "const":
            require(isinstance(n["levels"], list), "Invalid constant universe list")
            for level in n["levels"]:
                validate_level(level, self.params)
        if tag in {"lam", "forall"}:
            require(n["binder"] in BINDERS, "Unknown binder kind")
        if tag == "let":
            require(type(n["nondep"]) is bool, "Invalid let binder flag")
        if tag in {"bvar", "proj"}:
            nat(n["index"], 1_000_000)
        if tag in {"nat", "str"}:
            require(isinstance(n["value"], str) and len(n["value"]) <= 100_000, "Invalid literal")
            if tag == "nat":
                require(bool(re.fullmatch(r"0|[1-9][0-9]*", n["value"])), "Invalid numeric literal")
        children = EDGES.get(tag, ())
        need = max((self.demand[n[f]] for f in children), default=0)
        if tag == "bvar":
            need = n["index"] + 1
        elif tag in {"lam", "forall"}:
            need = max(self.demand[n["domain"]], max(0, self.demand[n["body"]] - 1))
        elif tag == "let":
            need = max(self.demand[n["type"]], self.demand[n["value"]], max(0, self.demand[n["body"]] - 1))
        canonical = {k: self.hashes[v] if k in children else v for k, v in n.items()}
        fingerprint = digest(canonical_json(canonical))
        self.hashes.append(fingerprint)
        self.demand.append(need)
        self.intern.setdefault(fingerprint, i)

    def ref(self, i: Any) -> int:
        require(nat(i) < len(self.nodes), "Expression reference is outside the inventory")
        return i

    def add(self, n: dict) -> int:
        children = EDGES.get(n["tag"], ())
        h = digest(canonical_json({k: self.hashes[v] if k in children else v for k, v in n.items()}))
        if h in self.intern:
            return self.intern[h]
        i = len(self.nodes)
        self._append_index(n, i)
        self.nodes.append(n)
        return i

    def equal(self, a: int, b: int) -> bool:
        return self.hashes[self.ref(a)] == self.hashes[self.ref(b)]

    def app(self, i: int) -> tuple[int, list[int]]:
        args = []
        while self.nodes[i]["tag"] == "app":
            n = self.nodes[i]; args.append(n["arg"]); i = n["fn"]
        return i, list(reversed(args))

    def locate(self, root: int, path: list[int]) -> tuple[int, list[int]]:
        require(isinstance(path, list) and len(path) <= 512, "Invalid proof path")
        i = self.ref(root); ctx = []
        for edge in path:
            n = self.nodes[i]; tag = n["tag"]
            fields = EDGES.get(tag, ())
            require(nat(edge) < len(fields), "Invalid proof path edge")
            if (tag in {"lam", "forall"} and edge == 1) or (tag == "let" and edge == 2):
                ctx.append(i)
            i = n[fields[edge]]
        return i, ctx

    def close(self, expr: int, ctx: list[int], *, is_type: bool) -> int:
        require(self.demand[expr] <= len(ctx), "Open expression exceeds its local scope")
        for binder in reversed(ctx):
            b = self.nodes[binder]
            if b["tag"] == "let":
                expr = self.add({**b, "body": expr})
            else:
                expr = self.add({**b, "tag": "forall" if is_type else "lam", "body": expr})
        require(self.demand[expr] == 0, "Closure is not closed")
        return expr

    def uses_binder(self, i: int, depth: int = 0) -> bool:
        todo = [(i, depth)]; seen = set()
        while todo:
            j, d = todo.pop()
            if (j, d) in seen: continue
            seen.add((j, d)); n = self.nodes[j]; t = n["tag"]
            if t == "bvar" and n["index"] == d: return True
            for f in EDGES.get(t, ()):
                extra = int(f == "body" and t in {"lam", "forall", "let"})
                todo.append((n[f], d + extra))
        return False


@dataclass(frozen=True)
class Claim:
    label: str
    path: tuple[int, ...]
    term: int
    typ: int
    proof: bool
    ctx: tuple[int, ...]


class Argument:
    def __init__(self, record: dict):
        require(isinstance(record, dict) and record.get("schema") == SCHEMA, "Unsupported typed argument schema")
        self.record = copy.deepcopy(record)
        record = self.record  # Own the validated snapshot, including all step metadata.
        self.name = display_name(record.get("name"))
        self.dag = Dag(record.get("exprs"), record.get("levels"))
        self.root = self.dag.ref(record.get("term"))
        self.typ = self.dag.ref(record.get("type"))
        require(self.dag.demand[self.root] == self.dag.demand[self.typ] == 0, "Original theorem contains free variables")
        require(isinstance(record.get("axioms"), list) and all(isinstance(x, str) for x in record["axioms"]), "Invalid axiom inventory")
        require(len(set(record["axioms"])) == len(record["axioms"]), "Duplicate axiom inventory")
        require(isinstance(record.get("lean_version"), str), "Missing toolchain version")
        self.steps = record.get("steps")
        require(isinstance(self.steps, list) and 0 < len(self.steps) <= 20_000, "Invalid judgement inventory")
        self.claims: list[Claim] = []
        self.contexts: list[list[int]] = []
        self.domains: list[tuple[int, int, bool]] = []
        self._validate_steps()
        self.sha256 = digest(canonical_json(self.record))

    def _judgement(self, s: dict, label: str) -> Claim:
        require(isinstance(s, dict), "Malformed judgement")
        actual, ctx = self.dag.locate(self.root, s.get("path"))
        term = self.dag.ref(s.get("term")); typ = self.dag.ref(s.get("type"))
        require(self.dag.equal(term, actual), "Judgement term does not match its original proof path")
        require(self.dag.demand[term] <= len(ctx) and self.dag.demand[typ] <= len(ctx), "Judgement escapes its binder scope")
        require(type(s.get("is_proof")) is bool, "Invalid proof/data classification")
        c = Claim(label, tuple(s["path"]), term, typ, s["is_proof"], tuple(ctx))
        self.claims.append(c)
        return c

    def _validate_steps(self) -> None:
        counts = [0] * len(self.steps); paths = set()
        for i, s in enumerate(self.steps):
            c = self._judgement(s, f"step_{i}")
            require(c.path not in paths, "Duplicated proof path")
            paths.add(c.path); self.contexts.append(list(c.ctx))
            if i == 0:
                require(not c.path and self.dag.equal(c.term, self.root) and c.proof, "Missing proof-root judgement")
            require(type(s.get("truncated")) is bool, "Missing explicit expansion status")
            children, args = s.get("children"), s.get("arguments")
            require(isinstance(children, list) and isinstance(args, list), "Malformed children or arguments")
            require(all(type(ch) is int for ch in children), "Invalid child judgement reference")
            require(len(set(children)) == len(children), "Duplicated child judgement")
            for ch in children:
                require(i < nat(ch) < len(self.steps), "Reading graph is cyclic or out of range")
                counts[ch] += 1
            node = self.dag.nodes[c.term]; tag = node["tag"]
            expected_paths = []
            if s["truncated"]:
                require(not children and not args, "Truncated step has hidden children")
                continue
            if tag == "lam":
                require(type(s.get("domain_is_prop")) is bool, "Missing binder classification")
                self.domains.append((i, self.dag.close(node["domain"], list(c.ctx), is_type=True), s["domain_is_prop"]))
                expected_paths = [list(c.path) + [1]]
                require(not args, "Lambda has spurious application arguments")
            elif tag == "let":
                require(not args, "Let expression has spurious application arguments")
                # The current exporter records a value derivation only when it is a proof.
                # A skipped value is displayed as a definition, not as an explained claim.
                expected_paths = ([list(c.path) + [1]] if len(children) == 2 else []) + [list(c.path) + [2]]
            elif tag == "app":
                _, actual_args = self.dag.app(c.term)
                require(len(args) == len(actual_args), "Application argument inventory incomplete")
                for k, a in enumerate(args):
                    ac = self._judgement(a, f"step_{i}_arg_{k}")
                    ap = list(c.path) + [0] * (len(args) - k - 1) + [1]
                    require(list(ac.path) == ap and self.dag.equal(ac.term, actual_args[k]), "Application argument path mismatch")
                    if ac.proof:
                        require(type(a.get("step")) is int and a["step"] in children, "Proof argument lacks a supporting step")
                        cs = self.steps[a["step"]]
                        require(cs["path"] == ap and self.dag.equal(cs["term"], ac.term) and self.dag.equal(cs["type"], ac.typ), "Supporting judgement is for a different claim")
                        expected_paths.append(ap)
                    else:
                        require("step" not in a, "Data argument wrongly attached as proof")
            elif tag == "proj":
                expected_paths = [list(c.path) + [0]]
                require(not args, "Projection has spurious application arguments")
            else:
                require(not args, "Non-application has application arguments")
            require([self.steps[x]["path"] for x in children] == expected_paths, "Supporting proof tree does not reconcile with original term")
        require(counts[0] == 0 and all(n == 1 for n in counts[1:]), "Unreachable or multiply parented proof judgement")

    def closed_claims(self) -> list[tuple[str, int, int, bool]]:
        return [(c.label, self.dag.close(c.term, list(c.ctx), is_type=False),
                 self.dag.close(c.typ, list(c.ctx), is_type=True), c.proof) for c in self.claims]

    def coverage(self) -> dict:
        return {"typed_steps": len(self.steps), "typed_judgements": len(self.claims),
                "shared_expression_nodes": len(self.record["exprs"]),
                "truncated_steps": sum(s["truncated"] for s in self.steps),
                "path_binding_validated": True, "english_formally_verified": False}


def dag_lean_lines(dag: Dag) -> list[str]:
    """Generate linear-size, topological Lean constructor bindings."""
    out = []
    names: dict[tuple, str] = {}
    def nm(n):
        key = name_key(n)
        if key in names: return names[key]
        if n["tag"] == "anonymous": code = ".anonymous"
        else:
            prefix = nm(n["prefix"])
            value = lean_string(n["value"]) if n["tag"] == "str" else n["value"]
            code = f".{n['tag']} {prefix} {value}"
        label = f"n{len(names)}"
        out.append(f"  let {label} : Name := {code}")
        names[key] = label
        return label
    for i, n in enumerate(dag.nodes):
        t = n["tag"]
        if t == "bvar": code = f".bvar {n['index']}"
        elif t == "sort": code = f".sort {level_to_lean(n['level'])}"
        elif t == "const": code = f".const {nm(n['name'])} [{', '.join(level_to_lean(x) for x in n['levels'])}]"
        elif t == "app": code = f".app e{n['fn']} e{n['arg']}"
        elif t in {"lam", "forall"}:
            code = f".{('lam' if t == 'lam' else 'forallE')} {nm(n['name'])} e{n['domain']} e{n['body']} .{BINDERS[n['binder']]}"
        elif t == "let": code = f".letE {nm(n['name'])} e{n['type']} e{n['value']} e{n['body']} {str(n['nondep']).lower()}"
        elif t == "nat": code = f".lit (.natVal {n['value']})"
        elif t == "str": code = f".lit (.strVal {lean_string(n['value'])})"
        elif t == "proj": code = f".proj {nm(n['name'])} {n['index']} e{n['of']}"
        else: raise InvalidExport("Unsupported constructor")
        out.append(f"  let e{i} : Expr := {code}")
    return out


def replay_source(record: dict, *, imports: list[str] | None = None) -> str:
    a = Argument(record)
    claims = a.closed_claims()
    imports = imports or []
    require(all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*(\.[A-Za-z_][A-Za-z_0-9]*)*", m) for m in imports), "Unsafe import path")
    name = name_to_lean(record["name"])
    levels = "[" + ", ".join(name_to_lean(x) for x in record["levels"]) + "]"
    axioms = "#[" + ", ".join(lean_string(x) for x in record["axioms"]) + "]"
    cs = ",\n    ".join(f"({lean_string(label)}, e{tm}, e{tp}, {str(p).lower()})" for label, tm, tp, p in claims)
    ds = ", ".join(f"({i}, e{typ}, {str(p).lower()})" for i, typ, p in a.domains)
    ps = ",\n    ".join(f"({lean_string(c.label)}, [{', '.join(map(str,c.path))}], e{tm})" for c, (_,tm,_,_) in zip(a.claims, claims))
    lines = ["import Lean", "import Lean.Util.CollectAxioms"] + ["import " + m for m in imports]
    lines += ["open Lean Elab Command", NORMALIZE_LEAN, PATH_LEAN,
              "set_option maxRecDepth 10000 in", "set_option maxHeartbeats 2000000 in", "run_elab do"]
    lines += dag_lean_lines(a.dag)
    lines += [f'  unless Lean.versionString == {lean_string(record["lean_version"])} do throwError "Toolchain version mismatch"',
              f"  let original ← getConstInfo {name}",
              f"  unless original.levelParams == {levels} do throwError \"Universe inventory mismatch\"",
              f"  let actualAxioms := (← Lean.collectAxioms {name}).map Name.toString",
              f"  let expectedAxioms : Array String := {axioms}",
              "  unless actualAxioms.size == expectedAxioms.size && actualAxioms.all expectedAxioms.contains && expectedAxioms.all actualAxioms.contains do",
              "    throwError \"Axiom inventory mismatch\"",
              f"  unless proofreaderEraseMetadata original.type == e{a.typ} do throwError \"Statement AST mismatch\"",
              "  let originalValue ← match original with",
              "    | .thmInfo v => pure v.value",
              "    | _ => throwError \"Expected theorem\"",
              f"  unless proofreaderEraseMetadata originalValue == e{a.root} do throwError \"Proof AST mismatch\"",
              f"  let base := {lean_string('ProofReaderJudgements.h' + a.sha256[:20])}.toName",
              "  withOptions (fun o => o.setBool `debug.skipKernelTC false) do",
              f"    addDecl <| .thmDecl {{ name := .str base \"root\", levelParams := {levels}, type := e{a.typ}, value := e{a.root} }}",
              '  logInfo "PROOFREADER_REPLAY_OK"',
              f"  let sourceBindings : Array (String × List Nat × Expr) := #[{ps}]",
              "  for (label, path, expectedValue) in sourceBindings do",
              "    match proofreaderClosedAt (proofreaderEraseMetadata originalValue) path with",
              '    | .error message => throwError "{message}: {label}"',
              '    | .ok actual => unless actual == expectedValue do throwError "Source linkage mismatch: {label}"',
              '  logInfo "PROOFREADER_PATHS_OK"',
              f"  let claims : Array (String × Expr × Expr × Bool) := #[{cs}]",
              "  for (label, value, type, proof) in claims do",
              "    let isProp ← Meta.isProp type",
              '    unless isProp == proof do throwError "Proof/data classification mismatch: {label}"',
              "    withOptions (fun o => o.setBool `debug.skipKernelTC false) do",
              "      if proof then",
              f"        addDecl <| .thmDecl {{ name := .str base label, levelParams := {levels}, type := type, value := value }}",
              "      else",
              f"        addDecl <| .defnDecl {{ name := .str base label, levelParams := {levels}, type := type, value := value, hints := .abbrev, safety := .safe }}",
              f"  let domains : Array (Nat × Expr × Bool) := #[{ds}]",
              "  for (i, domain, expected) in domains do",
              "    let actual ← Meta.isProp domain",
              '    unless actual == expected do throwError "Assumption/object classification mismatch: {i}"',
              f'  logInfo "PROOFREADER_JUDGEMENTS_OK:{a.sha256}:{len(claims)}"', ""]
    return "\n".join(lines)


def read_record(path: str | Path) -> dict:
    p = Path(path)
    require(p.stat().st_size < 256_000_000, "Export exceeds size budget")
    from .kernel_io import strict_json
    d = strict_json(p.read_bytes())
    Argument(d)
    return d
