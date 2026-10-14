# ProofReader workstream: extractor

Run and repair the mandatory native Lean 4.34.1 v2 module pipeline without weakening source linkage or all-judgement assertions. Preserve known remote evidence separately. Retain a full real mathematical export and replay all its claims.

# Required return
Write SUMMARY.md with changed files, exact checks and exit codes, unrun checks, blockers, counterexamples and next task. Do not claim checks you did not execute.

# Ownership
lean/
proofreader/kernel.py
proofreader/kernel_io.py
proofreader/kernel_pipeline.py
proofreader/data/KernelExport.lean
tests/test_kernel.py
tests/test_kernel_io.py
tests/test_kernel_pipeline.py
tests/test_kernel_integration.py

# Acceptance
PROOFREADER_REQUIRE_LEAN=1 python -m pytest tests/test_kernel_integration.py -q
python -m pytest tests/test_kernel.py tests/test_kernel_io.py tests/test_kernel_pipeline.py -q
Retain exact pinned-project source/export/replay evidence; no adapted-import pass substitution

# Known blocker
Remote individual programs ran on 4.34.0. Native combined 4.34.1 pipeline is not yet executed; production runner needs Lean/Lake and the pinned dependencies.


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



# File: HANDOFF.md

# Supervisor handoff — 0.2.0

## Landed

The implementation now has a strict constructor-DAG argument layer, deterministic
mathematical-English renderer, generated Lean source-path/claim checker, offline
UI, explicit native/remote extraction and verification CLI, v2 corpus integration,
large-corpus ledger mode, and typed examples from actual Lean runs. Code and
observations are committed locally; no independent agents or remote repo exist.

Start with `docs/VALIDATION_V0_2.md`, `docs/KERNEL_IR.md` and `docs/TRUST.md`.
Do not repeat networking/base64 transport experiments. The container has no Lean
or outbound network. Wolfram can call AXLE using **ExportByteArray** UTF-8 JSON and
**ImportByteArray** responses. Long manually copied compressed inputs repeatedly
failed checksums; use ordinary source text. Large connector responses truncate.
The installed CLI's direct remote adapter does not have that connector text limit.

## Actual evidence

Five real typed exports are retained under `artifacts/v0.2/`. `and_swap` has an
observed Lean 4.34.0 check of its original proof, all original-subterm paths and
18 recorded term/type judgements. The latest exact source is
`path-check-valid.lean`; `live-path-tests.json` records rejection of changed paths,
version and intermediate type. Earlier tests also rejected a changed axiom list
and assumption/object classification. Imported observations are not signatures.

An OpenAI Bézout-frame body compiled and exported with minimal Mathlib imports
on 4.34.0: 7,008 nodes, 1,511 steps, 11 capped branches. The large export was not
retained locally. This does not count as exact pinned-project replay or completed
English translation. Its measured summary is saved separately.

Complete domain-subtree metadata: 122,458 Lean files, 1,571,301,358 bytes, 23
untruncated domain trees. This is not an actual file download, proof count or
whole-corpus build. Pinned commit: 1581d4cbdd69a0faf34b2089614fe2a814316a6a.
Pinned OpenAI Lean: 4.34.1. Observed remote checks: 4.34.0. Never conflate them.

## Highest-priority next work

1. **Native integration:** run the mandatory 4.34.1 job with no skips. It must
   compile KernelExport, enumerate ProofReader.Smoke, render all three theorems,
   check every judgement, and reject an altered original proof. Individual
   exporter/checker runs succeeded remotely; the integrated native command and
   full module driver have not yet executed together in this environment.
2. **Real mathematical expansion:** retain the complete Bézout record on a normal
   networked runner; check it in its exact dependency environment. Add structured
   recursor/cases/induction/witness handling and named-lemma statement expansion.
   Do not upgrade bare lemma citations to meaningful-explanation passes.
3. **Full-corpus accounting:** use `extract-corpus --engine kernel` in bounded
   shards and reconcile all reports. Large source benchmarks are ledger-only.
   Failures stay in the denominator. Expected theorem count remains unknown
   while any required module is missing. v2 only enumerates theorem declarations;
   proof-valued defs need an explicit scope extension rather than silent omission.
4. **Reader quality:** measure whether mathematicians can follow selected complete
   proofs without opening Lean. Add a read-time task benchmark and human review.
   Formal English semantics and conceptual reproof discovery are separate goals.

## Files by workstream

- Extractor/checker: `lean/KernelExport.lean`, `proofreader/kernel.py`,
  `proofreader/kernel_io.py`, `proofreader/kernel_pipeline.py`.
- Reader: `proofreader/english.py`, `proofreader/normalization.py`, `web/`.
- Corpus: `proofreader/corpus.py`, pinned metadata/observations under artifacts.
- Audit: regression tests, source hashes, generated Lean, negative outcomes.

The production exporter is copied into `proofreader/data/KernelExport.lean` by
`scripts/build_typed_demo.py`. The reader library is rebuilt from actual retained
exports. `scripts/publish.sh` defaults to a private KyleJKistner repository.
Never claim helper compilation, mocked transport, source indexing or imported
receipts establish an integrated native or whole-corpus proof run.



# File: lean/KernelExport.lean

/- Typed, path-bound proof export. No prose is accepted as evidence. -/
import Lean
import Lean.Util.CollectAxioms
open Lean Meta Elab Command
namespace ProofReaderKernel

def obj := Json.mkObj

def nameJson : Name → Json
  | .anonymous => obj [("tag", toJson "anonymous")]
  | .str p s => obj [("tag", toJson "str"), ("prefix", nameJson p), ("value", toJson s)]
  | .num p n => obj [("tag", toJson "num"), ("prefix", nameJson p), ("value", toJson (toString n))]

partial def levelJson : Level → Json
  | .zero => obj [("tag", toJson "zero")]
  | .succ u => obj [("tag", toJson "succ"), ("of", levelJson u)]
  | .max u v => obj [("tag", toJson "max"), ("left", levelJson u), ("right", levelJson v)]
  | .imax u v => obj [("tag", toJson "imax"), ("left", levelJson u), ("right", levelJson v)]
  | .param n => obj [("tag", toJson "param"), ("name", nameJson n)]
  | .mvar _ => panic! "Unresolved universe metavariable"

def binderString : BinderInfo → String
  | .default => "explicit"
  | .implicit => "implicit"
  | .strictImplicit => "strict-implicit"
  | .instImplicit => "instance"

structure S where
  exprs : Array Json := #[]
  seen : Std.HashMap Expr Nat := {}
  steps : Array Json := #[]

abbrev M := StateT S MetaM

/-- Topological sharing avoids repeating the same large subexpression. -/
partial def store (e : Expr) : M Nat := do
  let e := e.consumeMData
  if let some i := (← get).seen[e]? then return i
  if (← get).exprs.size ≥ 250000 then throwError "Expression budget exceeded"
  let j ← match e with
    | .bvar i => pure <| obj [("tag", toJson "bvar"), ("index", toJson i)]
    | .fvar _ => throwError "Unabstracted local variable"
    | .mvar _ => throwError "Unresolved expression metavariable"
    | .sort u => pure <| obj [("tag", toJson "sort"), ("level", levelJson u)]
    | .const n us => pure <| obj [("tag", toJson "const"), ("name", nameJson n), ("levels", toJson (us.map levelJson))]
    | .app f a => do
      let f ← store f
      let a ← store a
      pure <| obj [("tag", toJson "app"), ("fn", toJson f), ("arg", toJson a)]
    | .lam n d b bi | .forallE n d b bi => do
      let d ← store d
      let b ← store b
      pure <| obj [("tag", toJson (if e.isLambda then "lam" else "forall")),
        ("name", nameJson n), ("domain", toJson d), ("body", toJson b), ("binder", toJson (binderString bi))]
    | .letE n t v b nd => do
      let t ← store t
      let v ← store v
      let b ← store b
      pure <| obj [("tag", toJson "let"), ("name", nameJson n), ("type", toJson t),
        ("value", toJson v), ("body", toJson b), ("nondep", toJson nd)]
    | .lit (.natVal n) => pure <| obj [("tag", toJson "nat"), ("value", toJson (toString n))]
    | .lit (.strVal s) => pure <| obj [("tag", toJson "str"), ("value", toJson s)]
    | .proj n i b => do
      let b ← store b
      pure <| obj [("tag", toJson "proj"), ("name", nameJson n), ("index", toJson i), ("of", toJson b)]
    | .mdata _ _ => throwError "Metadata normalization failed"
  let i := (← get).exprs.size
  modify fun s => { s with exprs := s.exprs.push j, seen := s.seen.insert e i }
  return i

/-- Every judgement carries a path into the original raw term. Locals are abstracted
in binder order; replay closes them using the *original* enclosing binders. -/
partial def inspect (e : Expr) (xs : Array Expr) (path : Array Nat) (depth : Nat) : M Nat := do
  let e := e.consumeMData
  let i := (← get).steps.size
  modify fun s => { s with steps := s.steps.push Json.null }
  let typ ← liftM <| inferType e
  let te ← store (e.abstract xs)
  let ty ← store (typ.abstract xs)
  let proof ← liftM <| isProp typ
  let mut children : Array Nat := #[]
  let mut args : Array Json := #[]
  let mut fields := [("path", toJson path), ("term", toJson te), ("type", toJson ty), ("is_proof", toJson proof)]
  let exhausted := depth == 0 || i ≥ 1500
  if !exhausted then
    match e with
    | .lam n d b bi =>
      let dp ← liftM <| isProp d
      fields := fields ++ [("domain_is_prop", toJson dp)]
      let st ← get
      let (child, st) ← liftM <| withLocalDecl n bi d fun x =>
        (inspect (b.instantiate1 x) (xs.push x) (path.push 1) (depth-1)).run st
      set st
      children := children.push child
    | .letE n t v b nd =>
      if ← liftM <| isProof v then children := children.push (← inspect v xs (path.push 1) (depth-1))
      let st ← get
      let (child, st) ← liftM <| withLetDecl n t v (nondep := nd) fun x =>
        (inspect (b.instantiate1 x) (xs.push x) (path.push 2) (depth-1)).run st
      set st
      children := children.push child
    | .app .. =>
      let as := e.getAppArgs
      for ai in [:as.size] do
        let a := as[ai]!
        let ap := path ++ (Array.replicate (as.size-ai-1) 0) |>.push 1
        let argType ← liftM <| inferType a
        let isp ← liftM <| isProp argType
        let ar ← store (a.abstract xs)
        let atr ← store (argType.abstract xs)
        let mut af := [("path", toJson ap), ("term", toJson ar), ("type", toJson atr), ("is_proof", toJson isp)]
        if isp then
          let child ← inspect a xs ap (depth-1)
          children := children.push child
          af := af ++ [("step", toJson child)]
        args := args.push (obj af)
    | .proj _ _ b => children := children.push (← inspect b xs (path.push 0) (depth-1))
    | _ => pure ()
  fields := fields ++ [("children", toJson children), ("arguments", toJson args), ("truncated", toJson exhausted)]
  modify fun s => { s with steps := s.steps.set! i (obj fields) }
  return i

def exportOne (n : Name) : MetaM Json := do
  let info ← getConstInfo n
  let value ← match info with
    | .thmInfo v => pure v.value
    | _ => throwError "This exporter expects a theorem"
  let ax ← collectAxioms n
  let (_, s) ← (do
    let _ ← store info.type
    let _ ← store value
    let _ ← inspect value #[] #[] 80
    pure () : M Unit).run {}
  let some ty := s.seen[info.type.consumeMData]? | throwError "Missing type"
  let some te := s.seen[value.consumeMData]? | throwError "Missing term"
  return obj [("schema", toJson "proofreader.kernel-export/v2"),
    ("name", nameJson n), ("levels", toJson (info.levelParams.map nameJson)),
    ("axioms", toJson (ax.map Name.toString)), ("lean_version", toJson Lean.versionString),
    ("type", toJson ty), ("term", toJson te), ("exprs", toJson s.exprs), ("steps", toJson s.steps)]

elab "#proofreader_kernel " target:str : command => do
  let record ← liftTermElabM <| exportOne target.getString.toName
  logInfo ("PROOFREADER_KERNEL:" ++ record.compress)
end ProofReaderKernel

namespace ProofReaderKernel
/-- Preserve one outcome for every enumerated theorem, including failed exports. -/
def emitOutcome (n : Name) : CommandElabM Unit := do
  try
    let record ← liftTermElabM <| exportOne n
    logInfo ("PROOFREADER_KERNEL:" ++ record.compress)
  catch ex =>
    let message ← ex.toMessageData.toString
    logInfo <| "PROOFREADER_KERNEL:" ++ (obj [
      ("schema", toJson "proofreader.kernel-failure/v2"),
      ("name", nameJson n), ("error", toJson message)]).compress

def emitInventory (names : Array Name) (scope : String) : CommandElabM Unit := do
  for n in names do emitOutcome n
  logInfo <| "PROOFREADER_KERNEL:" ++ (obj [
    ("schema", toJson "proofreader.kernel-inventory/v2"),
    ("scope", toJson scope), ("declaration_kind", toJson "theorem"),
    ("names", toJson (names.map nameJson)),
    ("lean_version", toJson Lean.versionString)]).compress

/-- Enumerate all theorem declarations in an imported module, not a lexical scan. -/
elab "#proofreader_kernel_module " target:str : command => do
  let env ← getEnv
  let moduleName := target.getString.toName
  unless env.header.moduleNames.contains moduleName do
    throwError "ProofReader target module is not imported: {moduleName}"
  let names := env.constants.toList.filterMap fun (n, info) => do
    match info with
    | .thmInfo _ =>
      let idx ← env.getModuleIdxFor? n
      if env.header.moduleNames[idx.toNat]! == moduleName then some n else none
    | _ => none
  emitInventory (names.toArray.qsort Name.lt) ("imported-module:" ++ target.getString)

/-- Enumerate theorems elaborated in the current source context. -/
elab "#proofreader_kernel_local" : command => do
  let env ← getEnv
  let names := env.constants.toList.filterMap fun (n, info) =>
    match info with
    | .thmInfo _ => if (env.getModuleIdxFor? n).isNone && !(n.toString.startsWith "ProofReaderKernel.") && (n.toString.splitOn ".ProofReaderKernel.").length == 1 then some n else none
    | _ => none
  emitInventory (names.toArray.qsort Name.lt) "current-source-theorems-excluding-tool-namespace"
end ProofReaderKernel



# File: proofreader/kernel.py

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



# File: proofreader/kernel_pipeline.py

"""Source/project → typed exports → deterministic reader → opt-in kernel checks.

A full module inventory means all *theorem declarations* in that module. It
neither means all papers are formalized nor includes proof-valued `def`s yet.
No source is executed or transmitted without the corresponding explicit flag.
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import asdict
import json
import re
from .kernel import Argument, InvalidExport, SCHEMA, display_name, name_key, require
from .kernel_io import strict_json, axle_request, verify_remote, verify_native, write_bundle, _write_json
from .lean import run_bounded, driver_file, MODULE_RE
from .model import Document, digest
from .english import English
from .render import write_html

PREFIX = 'PROOFREADER_KERNEL:'
INVENTORY = 'proofreader.kernel-inventory/v2'
FAILURE = 'proofreader.kernel-failure/v2'


def extractor_source() -> str:
    return (Path(__file__).parent / 'data/KernelExport.lean').read_text(encoding='utf-8')


def extraction_source(*, module: str | None = None, context: str | None = None) -> tuple[str,str]:
    require((module is None) != (context is None), 'Supply exactly one imported module or source context')
    source = extractor_source()
    marker = 'open Lean Meta Elab Command'
    require(marker in source, 'Packaged extractor boundary is missing')
    if module:
        require(bool(MODULE_RE.fullmatch(module)), 'Unsafe module name')
        prefix = source.replace(marker, f'import {module}\n\n{marker}',1)
        return prefix + f'\n#proofreader_kernel_module "{module}"\n', prefix
    require(isinstance(context,str) and bool(context.strip()), 'Empty source context')
    # Keep the caller's complete source prefix. Kernel rechecking reuses this
    # exact combined context, including any notation/macros and the exporter.
    prefix = context.rstrip() + '\n' + source[source.index(marker):]
    return prefix + '\n#proofreader_kernel_local\n', prefix


def parse_stream(stdout: str) -> dict:
    records=[];failures=[];inventories=[]
    for line in stdout.splitlines():
        match=re.fullmatch(r'(?:[^\n]*?\binfo: )?'+re.escape(PREFIX)+r'(.*)',line)
        if not match: continue
        obj=strict_json(match[1]);require(isinstance(obj,dict),'Exporter record must be an object')
        tag=obj.get('schema')
        if tag==SCHEMA:Argument(obj);records.append(obj)
        elif tag==FAILURE:
            name_key(obj.get('name'));require(isinstance(obj.get('error'),str),'Missing failure description');failures.append(obj)
        elif tag==INVENTORY:inventories.append(obj)
        else:raise InvalidExport('Unknown exporter record schema')
    require(len(inventories)==1,'Missing or duplicated theorem inventory')
    inv=inventories[0]
    require(inv.get('declaration_kind')=='theorem','Unsupported inventory scope')
    require(isinstance(inv.get('names'),list),'Missing expected theorem names')
    expected=[name_key(n) for n in inv['names']]
    observed=[name_key(n['name']) for n in records+failures]
    require(len(expected)==len(set(expected)),'Duplicate inventory name')
    require(len(observed)==len(set(observed)),'Duplicate export outcome')
    require(set(observed)==set(expected),'Theorem inventory and outcomes do not reconcile')
    require(isinstance(inv.get('lean_version'),str),'Missing inventory Lean version')
    require(all(x['lean_version']==inv['lean_version'] for x in records),'Mixed export Lean versions')
    return {'records':records,'failures':failures,'inventory':inv,'complete':not failures}


def _response_stdout(response: dict, source: str) -> str:
    require(response.get('okay') is True, 'AXLE did not successfully compile the complete source')
    require(not response.get('failed_declarations'), 'AXLE reported failed declarations')
    for key in ('lean_messages','tool_messages'):
        messages=response.get(key,{})
        require(isinstance(messages,dict),'Malformed AXLE messages')
        require(not messages.get('errors'), 'AXLE reported errors')
    require(isinstance(response.get('content'),str) and response['content'].strip()==source.strip(),
            'AXLE changed the submitted source')
    infos=response.get('lean_messages',{}).get('infos',[])
    require(isinstance(infos,list) and all(isinstance(x,str) for x in infos),'Malformed AXLE info messages')
    return '\n'.join(infos)


def extract_kernel(output: Path, *, module: str | None = None, context: str | None = None,
                   project: Path | None = None, backend: str = 'native', version: str = '4.34.0',
                   trust_project: bool = False, allow_remote: bool = False,
                   verify: bool = False, timeout: float = 180,
                   permitted_axioms: list[str] | None = None) -> dict:
    require(backend in ('native','axle'),'Unknown execution backend')
    if backend=='native' and not trust_project:
        raise PermissionError('Lean source can execute arbitrary code. Pass --trust-project for a trusted or isolated project.')
    if backend=='axle' and not allow_remote:
        raise PermissionError('This uploads the complete source context to AXLE. Pass --allow-remote to consent.')
    require(0<timeout<=900,'Timeout must be between 0 and 900 seconds')
    if backend=='native':
        require(project is not None and project.is_dir(),'Native extraction needs an existing --project')
        project=project.resolve()
    else:
        require(context is not None and module is None,'Remote extraction requires self-contained --context, not a local module')
    source,prefix=extraction_source(module=module,context=context)
    output.mkdir(parents=True,exist_ok=True)
    (output/'Extract.lean').write_text(source,encoding='utf-8')
    (output/'Context.lean').write_text(prefix,encoding='utf-8')
    result={'schema':'proofreader.kernel-run/v2','status':'started','module':module,
            'backend':backend,'extractor_sha256':digest(extractor_source()),
            'submitted_source_sha256':digest(source),'verify_requested':verify,
            'inventory_scope':'theorem-declarations-only','english_formally_verified':False,
            'dependency_artifacts_authenticated':False,'rows':[],'failures':[]}
    def save():_write_json(output/'result.json',result)
    save()
    try:
        if backend=='native':
            if module:
                build=run_bounded(['lake','build',module],project,timeout=timeout)
                _write_json(output/'build.json',asdict(build))
                require(build.status=='passed' and build.exit_code==0,'Module build failed; see build.json')
            with driver_file(project,source) as driver:
                run=run_bounded(['lake','env','lean',str(driver)],project,timeout=timeout)
            _write_json(output/'export-run.json',asdict(run))
            (output/'stdout.txt').write_text(run.stdout,encoding='utf-8')
            require(run.status=='passed' and run.exit_code==0,'Exporter failed; see export-run.json')
            stdout=run.stdout
        else:
            response=axle_request(source,version,allow_remote=True,timeout=timeout)
            _write_json(output/'axle-export-response.json',response)
            stdout=_response_stdout(response,source)
            require(response.get('info',{}).get('environment')=='lean-'+version,'AXLE environment mismatch')
        stream=parse_stream(stdout)
        if backend=='axle':require(stream['inventory']['lean_version']==version,'Requested/exported versions differ')
        _write_json(output/'inventory.json',stream['inventory'])
        result['inventory']=stream['inventory'];result['failures']=stream['failures']
        docs=[]
        for record in stream['records']:
            a=Argument(record);key=a.sha256[:20];dest=output/'proofs'/key;receipt=None
            row={'name':a.name,'argument_sha256':a.sha256,'directory':f'proofs/{key}',
                 'exported':True,'rendered':False,'checked':False,**a.coverage()}
            result['rows'].append(row);save()
            try:
                if verify:
                    if backend=='native':
                        receipt=verify_native(record,project,dest/'verification',module=module,
                                              context=prefix if context is not None else None,
                                              trust_project=True,timeout=timeout,permitted_axioms=permitted_axioms)
                    else:
                        receipt=verify_remote(record,dest/'verification',context=prefix,allow_remote=True,
                                              timeout=timeout,permitted_axioms=permitted_axioms)
                    row['checked']=receipt['status']=='passed'
                write_bundle(record,dest,source=context or '',file=module or 'Source.lean',receipt=receipt,
                             imports=[module] if module else [],context=prefix if context is not None else None)
                docs.append(English(record).document(source=context or '',file=module or 'Source.lean',receipt=receipt))
                row['rendered']=True
            except (OSError,ValueError,RuntimeError,RecursionError) as ex:
                row['error']=str(ex)
            save()
        combined=Document('Typed proof library',[],[d for doc in docs for d in doc.declarations],
                          provenance={'backend':backend,'theorems_expected':len(stream['inventory']['names']),
                                      'scope':stream['inventory']['scope'],'whole_corpus_coverage':False,
                                      'source_sha256':digest(source),'pipeline_model_calls':0})
        (output/'reading.json').write_text(combined.to_json(),encoding='utf-8');write_html(combined,output/'index.html')
        good=stream['complete'] and all(r['rendered'] and (r['checked'] or not verify) for r in result['rows'])
        result['status']='complete' if good else 'partial'
        result['theorems_expected']=len(stream['inventory']['names'])
        result['theorems_exported']=len(result['rows'])
        result['theorems_checked']=sum(r['checked'] for r in result['rows'])
        result['checked_english_proofs']=0
    except (OSError,ValueError,RuntimeError,RecursionError) as ex:
        result['status']='failed';result['error']=str(ex)
    save();return result



# File: tests/test_kernel_integration.py

"""Mandatory live tests in native CI; no mock can satisfy this job."""
from pathlib import Path
import json,os,shutil,re
import pytest
from proofreader.kernel_pipeline import extract_kernel
from proofreader.kernel import read_record, replay_source, Argument
from proofreader.lean import driver_file, run_bounded

REQUIRED=os.environ.get('PROOFREADER_REQUIRE_LEAN')=='1'
@pytest.mark.skipif(not shutil.which('lake') and not REQUIRED,reason='Native v2 pipeline requires Lean/Lake; remote observations are recorded separately')
def test_native_v2_full_module_and_independent_claim_checks(tmp_path):
    if not shutil.which('lake'):pytest.fail('Required native Lean job cannot skip')
    project=Path(__file__).parents[1]/'lean'
    result=extract_kernel(tmp_path,module='ProofReader.Smoke',project=project,trust_project=True,verify=True,timeout=300)
    assert result['status']=='complete',result
    assert result['theorems_expected']==3 and result['theorems_checked']==3
    row=next(x for x in result['rows'] if x['name'].endswith('.and_commute'))
    record=read_record(tmp_path/row['directory']/'argument.json')
    source=replay_source(record,imports=['ProofReader.Smoke'])
    # A forced wrong root proof cannot pass the independent AST check.
    source=re.sub(r'(proofreaderEraseMetadata originalValue == )e\d+',r'\1(Lean.mkConst `True.intro)',source)
    with driver_file(project,source) as f:
        run=run_bounded(['lake','env','lean',str(f)],project,timeout=120)
    assert run.status!='passed'
    assert 'PROOFREADER_JUDGEMENTS_OK' not in run.stdout

