"""Lossless core-expression transport, validation, and Lean replay generation.

The Python validator checks the *transport structure*, not Lean typing. The
replay program compares reconstructed expressions with the imported source
constant structurally (not via proof-irrelevant definitional equality), then
asks Lean to kernel-check a fresh theorem. The replay must actually run before
any local-build status is attached. Metadata is the only erased constructor.
"""
from __future__ import annotations
import json
import re
from typing import Any
from .model import Declaration, Document, Span, Step, digest

EXPORT_SCHEMA = "proofreader.lean-export/v1"
BINDERS = {"explicit": "default", "implicit": "implicit", "strict-implicit": "strictImplicit", "instance": "instImplicit"}
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


class InvalidExport(ValueError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidExport(message)


def _string(value: Any, label: str) -> str:
    _require(isinstance(value, str), f"{label} must be a string")
    _require(len(value) <= 2_000_000, f"{label} exceeds the text limit")
    return value


def _natural(value: Any) -> int:
    _require(isinstance(value, int) and not isinstance(value, bool) and value >= 0, "Expected a nonnegative integer")
    return value


def validate_name(value: Any, depth: int = 0) -> None:
    _require(isinstance(value, dict), "Name must be an object")
    _require(depth < 256, "Name nesting limit exceeded")
    tag = value.get("tag")
    if tag == "anonymous":
        return
    _require(tag in {"str", "num"}, "Unknown name constructor")
    validate_name(value.get("prefix"), depth + 1)
    text = _string(value.get("value"), "Name component")
    if tag == "num":
        _require(bool(re.fullmatch(r"0|[1-9][0-9]*", text)), "Noncanonical numeral name component")


def name_text(value: dict) -> str:
    validate_name(value)
    if value["tag"] == "anonymous":
        return ""
    p = name_text(value["prefix"])
    v = value["value"]
    return f"{p}.{v}" if p else v


def make_name(text: str) -> dict:
    value: dict = {"tag": "anonymous"}
    # Only used for controlled fixtures and module paths, not internal Lean names.
    for part in text.split("."):
        value = {"tag": "str", "prefix": value, "value": part}
    return value


def validate_level(value: Any, parameters: set[str], depth: int = 0) -> None:
    _require(isinstance(value, dict), "Level must be an object")
    _require(depth < 256, "Universe nesting limit exceeded")
    tag = value.get("tag")
    if tag == "zero":
        return
    if tag == "succ":
        return validate_level(value.get("of"), parameters, depth + 1)
    if tag in {"max", "imax"}:
        validate_level(value.get("left"), parameters, depth + 1)
        validate_level(value.get("right"), parameters, depth + 1)
        return
    if tag == "param":
        validate_name(value.get("name"))
        _require(name_text(value["name"]) in parameters, "Undeclared universe parameter")
        return
    raise InvalidExport(f"Unsupported or unresolved universe constructor: {tag}")


def validate_expr(value: Any, parameters: set[str] | None = None, max_nodes: int = 1_000_000) -> int:
    """Bounded, iterative traversal so an imported JSON tree cannot exhaust recursion."""
    parameters = parameters or set()
    stack = [(value, 0, 0)]
    count = 0
    while stack:
        node, bound, nesting = stack.pop()
        count += 1
        _require(count <= max_nodes, "Expression node budget exceeded")
        _require(nesting <= 350, "Expression nesting limit exceeded")
        _require(isinstance(node, dict), "Expression must be an object")
        tag = node.get("tag")
        children: list[tuple[Any, int]] = []
        if tag == "bvar":
            _require(_natural(node.get("index")) < bound, "Loose de Bruijn variable in closed expression")
        elif tag == "const":
            validate_name(node.get("name"))
            _require(isinstance(node.get("levels"), list), "Constant levels must be a list")
            for level in node["levels"]:
                validate_level(level, parameters)
        elif tag == "sort":
            validate_level(node.get("level"), parameters)
        elif tag == "app":
            children = [(node.get("fn"), bound), (node.get("arg"), bound)]
        elif tag in {"lam", "forall"}:
            validate_name(node.get("name"))
            _require(node.get("binder") in BINDERS, "Unknown binder kind")
            children = [(node.get("domain"), bound), (node.get("body"), bound + 1)]
        elif tag == "let":
            validate_name(node.get("name"))
            _require(isinstance(node.get("nondep"), bool), "let nondep must be boolean")
            children = [(node.get("type"), bound), (node.get("value"), bound), (node.get("body"), bound + 1)]
        elif tag == "proj":
            validate_name(node.get("name"))
            _natural(node.get("index"))
            children = [(node.get("of"), bound)]
        elif tag == "nat":
            _require(bool(re.fullmatch(r"0|[1-9][0-9]*", _string(node.get("value"), "Natural literal"))), "Invalid natural literal")
        elif tag == "str":
            _string(node.get("value"), "String literal")
        else:
            raise InvalidExport(f"Unknown, open, or incomplete expression constructor: {tag}")
        stack.extend((child, nbound, nesting + 1) for child, nbound in children)
    return count


def lean_string(text: str) -> str:
    """Lean string literals, including non-JSON control-character escaping."""
    out = []
    for c in text:
        if c == "\\": out.append("\\\\")
        elif c == '"': out.append('\\"')
        elif c == "\n": out.append("\\n")
        elif c == "\r": out.append("\\r")
        elif c == "\t": out.append("\\t")
        elif ord(c) < 32 or ord(c) == 127: out.append(f"\\x{ord(c):02x}")
        else: out.append(c)
    return '"' + "".join(out) + '"'


def name_to_lean(node: dict) -> str:
    if node["tag"] == "anonymous": return "Lean.Name.anonymous"
    arg = lean_string(node["value"]) if node["tag"] == "str" else node["value"]
    return f"(Lean.Name.{node['tag']} {name_to_lean(node['prefix'])} {arg})"


def level_to_lean(node: dict) -> str:
    tag = node["tag"]
    if tag == "zero": return "Lean.Level.zero"
    if tag == "succ": return f"(Lean.Level.succ {level_to_lean(node['of'])})"
    if tag in {"max", "imax"}: return f"(Lean.Level.{tag} {level_to_lean(node['left'])} {level_to_lean(node['right'])})"
    if tag == "param": return f"(Lean.Level.param {name_to_lean(node['name'])})"
    raise InvalidExport("Cannot replay an unresolved universe")


def expr_to_lean(node: dict) -> str:
    t = node["tag"]
    if t == "bvar": return f"(Lean.Expr.bvar {node['index']})"
    if t == "sort": return f"(Lean.Expr.sort {level_to_lean(node['level'])})"
    if t == "const":
        levels = ", ".join(level_to_lean(u) for u in node["levels"])
        return f"(Lean.Expr.const {name_to_lean(node['name'])} [{levels}])"
    if t == "app": return f"(Lean.Expr.app {expr_to_lean(node['fn'])} {expr_to_lean(node['arg'])})"
    if t in {"lam", "forall"}:
        ctor = "lam" if t == "lam" else "forallE"
        return f"(Lean.Expr.{ctor} {name_to_lean(node['name'])} {expr_to_lean(node['domain'])} {expr_to_lean(node['body'])} Lean.BinderInfo.{BINDERS[node['binder']]})"
    if t == "let":
        return f"(Lean.Expr.letE {name_to_lean(node['name'])} {expr_to_lean(node['type'])} {expr_to_lean(node['value'])} {expr_to_lean(node['body'])} {str(node['nondep']).lower()})"
    if t == "proj": return f"(Lean.Expr.proj {name_to_lean(node['name'])} {node['index']} {expr_to_lean(node['of'])})"
    if t == "nat": return f"(Lean.Expr.lit (Lean.Literal.natVal {node['value']}))"
    if t == "str": return f"(Lean.Expr.lit (Lean.Literal.strVal {lean_string(node['value'])}))"
    raise InvalidExport(f"Cannot replay {t}")


NORMALIZE_LEAN = r'''
private partial def proofreaderEraseMetadata : Lean.Expr → Lean.Expr
  | .mdata _ b => proofreaderEraseMetadata b
  | .app f a => .app (proofreaderEraseMetadata f) (proofreaderEraseMetadata a)
  | .lam n d b bi => .lam n (proofreaderEraseMetadata d) (proofreaderEraseMetadata b) bi
  | .forallE n d b bi => .forallE n (proofreaderEraseMetadata d) (proofreaderEraseMetadata b) bi
  | .letE n t v b nd => .letE n (proofreaderEraseMetadata t) (proofreaderEraseMetadata v) (proofreaderEraseMetadata b) nd
  | .proj n i b => .proj n i (proofreaderEraseMetadata b)
  | e => e
'''


def validate_export(data: dict) -> dict[str, int]:
    _require(isinstance(data, dict) and data.get("schema") == EXPORT_SCHEMA, "Unsupported export schema")
    _string(data.get("name"), "Declaration name")
    _string(data.get("statement"), "Statement")
    validate_name(data.get("name_ast"))
    levels = data.get("level_parameters")
    _require(isinstance(levels, list), "Missing universe parameters")
    for level in levels: validate_name(level)
    params = {name_text(level) for level in levels}
    _require(len(params) == len(levels), "Duplicate universe parameters")
    count_type = validate_expr(data.get("raw_type"), params)
    count_term = validate_expr(data["raw_term"], params) if "raw_term" in data else 0
    _require(isinstance(data.get("axioms"), list) and all(isinstance(x, str) for x in data["axioms"]), "Invalid axiom inventory")
    return {"type_nodes": count_type, "term_nodes": count_term}


def replay_source(data: dict, module: str) -> str:
    validate_export(data)
    _require(bool(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_][A-Za-z_0-9]*)*", module)), "Unsafe or unsupported module identifier")
    _require("raw_term" in data, "Declaration has no proof term to replay")
    _require(data.get("kind") == "theorem", "This replayer checks theorem declarations only")
    name = name_to_lean(data["name_ast"])
    typ, term = expr_to_lean(data["raw_type"]), expr_to_lean(data["raw_term"])
    params = ", ".join(name_to_lean(n) for n in data["level_parameters"])
    fresh = name_to_lean(make_name("ProofReaderReplay.r" + digest(json.dumps(data, sort_keys=True))[:24]))
    return f'''import Lean
import {module}

open Lean Elab Command
{NORMALIZE_LEAN}
run_elab do
  let original ← getConstInfo {name}
  let expected : Lean.Expr := {typ}
  let reconstructed : Lean.Expr := {term}
  unless proofreaderEraseMetadata original.type == expected do
    throwError "ProofReader: statement AST does not match the imported declaration"
  let originalValue ← match original with
    | .thmInfo info => pure info.value
    | _ => throwError "ProofReader: expected a theorem"
  unless proofreaderEraseMetadata originalValue == reconstructed do
    throwError "ProofReader: proof AST does not match the imported declaration"
  withOptions (fun opts => opts.setBool `debug.skipKernelTC false) do
    addDecl <| .thmDecl {{ name := {fresh}, levelParams := [{params}], type := original.type, value := reconstructed }}
  liftM <| IO.println "PROOFREADER_REPLAY_OK"
'''


def _view_step(node: dict, prefix: str, serial: list[int], depth: int = 0) -> Step:
    _require(depth <= 160, "Reading tree is too deep")
    _require(isinstance(node, dict), "Reading step must be an object")
    serial[0] += 1
    _require(serial[0] <= 100_000, "Reading tree node limit exceeded")
    rule = node.get("rule", "unknown")
    conclusion = _string(node.get("conclusion", ""), "Step conclusion")
    binder = _string(node.get("binder", ""), "Binder")
    domain = _string(node.get("domain", ""), "Domain")
    head = _string(node.get("head", ""), "Application head")
    texts = {
        "introduce": f"Let {binder} be an arbitrary object of type {domain}.",
        "assume": f"Assume {domain}, and denote this assumption by {binder}.",
        "have": f"First establish {domain}; call this intermediate fact {binder}.",
        "let": f"Define {binder} of type {domain} by the recorded expression.",
        "apply": f"Apply {head} to the recorded arguments. This gives {conclusion}.",
        "assumption": f"This is the available assumption {binder}: {conclusion}.",
        "constant": f"Use {head}, whose instantiated conclusion is {conclusion}.",
        "projection": f"Take component {node.get('index', '?')} of the recorded object to obtain {conclusion}.",
        "budget": "The reading-tree expansion budget was reached here. The raw term is retained separately.",
        "core-term": "Use the recorded core term to establish the displayed proposition.",
    }
    refs = node.get("references", [])
    _require(isinstance(refs, list) and all(isinstance(x, str) for x in refs), "Invalid reference list")
    # These templates are keyed by the exported constant identity, not tactic names.
    exact_heads = {
        "Eq.refl": "The displayed equality holds by reflexivity.",
        "Eq.symm": "Reverse the supplied equality to obtain the displayed equality.",
        "Eq.trans": "Combine the supplied equalities by transitivity.",
        "And.intro": "Establish both conjuncts using the following two arguments.",
        "And.left": "Take the left conjunct of the supplied conjunction.",
        "And.right": "Take the right conjunct of the supplied conjunction.",
        "Iff.intro": "Establish the two directions of the equivalence.",
        "False.elim": "The established contradiction implies the displayed proposition.",
    }
    text = exact_heads.get(refs[0], texts.get(rule, "No English template is available for this typed step.")) if refs and rule == "apply" else texts.get(rule, "No English template is available for this typed step.")
    step_id = f"{prefix}:t{serial[0]}"
    children = node.get("children", [])
    _require(isinstance(children, list), "Step children must be a list")
    context = node.get("context", [])
    _require(isinstance(context, list), "Step context must be a list")
    clean_context = []
    for item in context:
        _require(isinstance(item, dict), "Context entries must be objects")
        clean_context.append({"name": _string(item.get("name", ""), "Context name"), "type": _string(item.get("type", ""), "Context type")})
    args = node.get("arguments", [])
    detail = "\n".join(f"{a.get('term', '')} : {a.get('type', '')}" for a in args if isinstance(a, dict))
    return Step(step_id, rule, text, _string(node.get("term", ""), "Term"), evidence="typed-export", references=refs,
                children=[_view_step(c, prefix, serial, depth + 1) for c in children], conclusion=conclusion, context=clean_context,
                term_id=step_id, fallback=rule in {"budget", "core-term"} or rule not in texts, detail=detail)


def export_document(data: dict, module: str = "", receipt: dict | None = None, fixture: bool = False) -> Document:
    counts = validate_export(data)
    identity = digest(data["name"] + json.dumps(data["raw_type"], sort_keys=True))[:20]
    proof = data.get("proof")
    steps = [_view_step(proof, identity, [0])] if proof else []
    warnings = [f"Additional axiom dependency: {a}" for a in data["axioms"] if a not in ALLOWED_AXIOMS]
    if fixture:
        warnings.insert(0, "Hand-authored exporter-format fixture; NOT output from a Lean execution.")
    if not receipt:
        warnings.append("No locally executed Lean build or replay receipt is attached.")
    declaration = Declaration(identity, data["name"], data.get("kind", "declaration"), module.replace(".", "/") + ".lean" if module else "typed-export",
                              data["statement"], "", Span(0, 0, 1, 1), steps=steps, warnings=warnings, evidence="typed-export", receipt=receipt,
                              axes={"discovery": "exported", "statement": "typed-export", "proof": "typed-export", "english_fidelity": "not-certified", "fixture": fixture})
    declaration.dependencies = sorted({r for r in _all_references(proof)} if proof else set())
    return Document(data["name"], [], [declaration], provenance={"mode": "typed-export", "module": module, "fixture": fixture, "transport_structure_validated": True, "typing_checked_here": bool(receipt and receipt.get("status") == "passed"), "counts": counts, "pipeline_model_calls": 0})


def _all_references(node: dict):
    yield from node.get("references", [])
    for child in node.get("children", []):
        yield from _all_references(child)
