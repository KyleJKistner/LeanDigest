/-
ProofReader typed proof exporter, pinned to Lean 4.34.1.

This module is an extractor, not a proof of correctness of the English printer.
The accompanying Python code labels its output "typed export", never "English
verified". The release ledger records whether this exact file was compiled.
-/
import Lean
import Lean.Util.CollectAxioms

open Lean Meta Elab Command

namespace ProofReader

def obj (fields : List (String × Json)) : Json := Json.mkObj fields

def binderString : BinderInfo → String
  | .default => "explicit"
  | .implicit => "implicit"
  | .strictImplicit => "strict-implicit"
  | .instImplicit => "instance"

/-- Preserve internal name components; display strings alone are not reversible. -/
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
  | .mvar id => obj [("tag", toJson "mvar"), ("name", nameJson id.name)]

/-- Exact core constructor encoding, except semantically inert metadata is erased.
The budget is global over the tree, not a per-branch depth allowance. -/
partial def exprJson (e : Expr) : StateT Nat MetaM Json := do
  let remaining ← get
  if remaining == 0 then
    throwError "ProofReader raw expression budget exhausted; no complete export emitted"
  set (remaining - 1)
  match e with
  | .bvar i => return obj [("tag", toJson "bvar"), ("index", toJson i)]
  | .fvar id => return obj [("tag", toJson "fvar"), ("name", nameJson id.name)]
  | .mvar _ => throwError "ProofReader refuses unresolved expression metavariables"
  | .sort u => return obj [("tag", toJson "sort"), ("level", levelJson u)]
  | .const n us => return obj [("tag", toJson "const"), ("name", nameJson n), ("display", toJson n.toString), ("levels", toJson (us.map levelJson))]
  | .app f a =>
      let f ← exprJson f
      let a ← exprJson a
      return obj [("tag", toJson "app"), ("fn", f), ("arg", a)]
  | .lam n d b bi =>
      let d ← exprJson d
      let b ← exprJson b
      return obj [("tag", toJson "lam"), ("name", nameJson n), ("display", toJson n.toString), ("domain", d), ("body", b), ("binder", toJson (binderString bi))]
  | .forallE n d b bi =>
      let d ← exprJson d
      let b ← exprJson b
      return obj [("tag", toJson "forall"), ("name", nameJson n), ("display", toJson n.toString), ("domain", d), ("body", b), ("binder", toJson (binderString bi))]
  | .letE n t v b nondep =>
      let t ← exprJson t
      let v ← exprJson v
      let b ← exprJson b
      return obj [("tag", toJson "let"), ("name", nameJson n), ("display", toJson n.toString), ("type", t), ("value", v), ("body", b), ("nondep", toJson nondep)]
  | .lit (.natVal n) => return obj [("tag", toJson "nat"), ("value", toJson (toString n))]
  | .lit (.strVal s) => return obj [("tag", toJson "str"), ("value", toJson s)]
  | .mdata _ b => exprJson b
  | .proj n i b =>
      let b ← exprJson b
      return obj [("tag", toJson "proj"), ("name", nameJson n), ("display", toJson n.toString), ("index", toJson i), ("of", b)]


def pp (e : Expr) : MetaM String := do
  return (← ppExpr e).pretty


def contextJson : MetaM Json := do
  let mut items : Array Json := #[]
  for localDecl in (← getLCtx) do
    unless localDecl.isImplementationDetail do
      let value ← pp localDecl.type
      items := items.push <| obj [
        ("name", toJson localDecl.userName.toString),
        ("type", toJson value),
        ("context_index", toJson items.size),
        ("is_proposition", toJson (← isProp localDecl.type))]
  return toJson items

/-- A bounded reading tree. Budgets are reported explicitly, never hidden. -/
partial def view (e : Expr) (depth : Nat) : StateT Nat MetaM Json := do
  let remaining ← get
  let typ ← liftM <| inferType e
  let conclusion ← liftM <| pp typ
  let context ← liftM contextJson
  if remaining == 0 || depth == 0 then
    return obj [("rule", toJson "budget"), ("conclusion", toJson conclusion),
      ("context", context), ("fallback", toJson true), ("children", toJson (#[] : Array Json))]
  set (remaining - 1)
  let term ← liftM <| pp e
  let base := [("conclusion", toJson conclusion), ("term", toJson term), ("context", context)]
  match e with
  | .mdata _ b => view b depth
  | .lam n d b bi =>
      let assumption ← liftM <| isProp d
      let domain ← liftM <| pp d
      let state ← get
      let (child, newState) ← liftM <| withLocalDecl n bi d fun x =>
        (view (b.instantiate1 x) (depth - 1)).run state
      set newState
      return obj <| base ++ [
        ("rule", toJson (if assumption then "assume" else "introduce")),
        ("binder", toJson n.toString), ("domain", toJson domain),
        ("children", toJson #[child])]
  | .letE n t v b _ =>
      let typeText ← liftM <| pp t
      let valueText ← liftM <| pp v
      let valueIsProof ← liftM <| isProof v
      let mut children : Array Json := #[]
      if valueIsProof then
        children := children.push (← view v (depth - 1))
      let state ← get
      let (child, newState) ← liftM <| withLetDecl n t v fun x =>
        (view (b.instantiate1 x) (depth - 1)).run state
      set newState
      children := children.push child
      return obj <| base ++ [
        ("rule", toJson (if valueIsProof then "have" else "let")),
        ("binder", toJson n.toString), ("domain", toJson typeText),
        ("value", toJson valueText), ("children", toJson children)]
  | .app .. =>
      let head := e.getAppFn
      let headText ← liftM <| pp head
      let mut arguments : Array Json := #[]
      let mut children : Array Json := #[]
      for a in e.getAppArgs do
        let proof ← liftM <| isProof a
        let aType ← liftM <| inferType a
        arguments := arguments.push <| obj [
          ("term", toJson (← liftM <| pp a)),
          ("type", toJson (← liftM <| pp aType)),
          ("is_proof", toJson proof)]
        if proof then children := children.push (← view a (depth - 1))
      let refs := match head with
        | .const n _ => #[n.toString]
        | _ => #[]
      return obj <| base ++ [
        ("rule", toJson "apply"), ("head", toJson headText),
        ("arguments", toJson arguments), ("references", toJson refs),
        ("children", toJson children)]
  | .fvar id =>
      let localDecl ← liftM <| getLocalDecl id
      return obj <| base ++ [("rule", toJson "assumption"),
        ("binder", toJson localDecl.userName.toString), ("children", toJson (#[] : Array Json))]
  | .const n _ =>
      return obj <| base ++ [("rule", toJson "constant"),
        ("head", toJson n.toString), ("references", toJson #[n.toString]),
        ("children", toJson (#[] : Array Json))]
  | .proj n i b =>
      let child ← view b (depth - 1)
      return obj <| base ++ [("rule", toJson "projection"),
        ("head", toJson n.toString), ("index", toJson i), ("children", toJson #[child])]
  | .mvar _ => throwError "ProofReader refuses unresolved metavariables in a reading tree"
  | _ =>
      return obj <| base ++ [("rule", toJson "core-term"),
        ("fallback", toJson true), ("children", toJson (#[] : Array Json))]


def exportDeclaration (name : Name) : MetaM Json := do
  let env ← getEnv
  let some info := env.find? name | throwError "Unknown declaration {name}"
  let statement ← pp info.type
  let axioms ← collectAxioms name
  let rawType ← (exprJson info.type).run' 1000000
  let value? := match info with
    | .thmInfo v => some v.value
    | .defnInfo v => some v.value
    | .opaqueInfo v => some v.value
    | _ => none
  let kind := match info with
    | .thmInfo _ => "theorem"
    | .defnInfo _ => "definition"
    | .opaqueInfo _ => "opaque"
    | .axiomInfo _ => "axiom"
    | _ => "declaration"
  let mut fields := [
    ("schema", toJson "proofreader.lean-export/v1"),
    ("name", toJson name.toString), ("name_ast", nameJson name), ("kind", toJson kind),
    ("statement", toJson statement), ("raw_type", rawType),
    ("level_parameters", toJson (info.levelParams.map nameJson)),
    ("axioms", toJson (axioms.map Name.toString)),
    ("english_fidelity", toJson "not-certified")]
  if let some value := value? then
    let raw ← (exprJson value).run' 1000000
    fields := fields ++ [("raw_term", raw)]
    if ← isProp info.type then
      let tree ← (view value 120).run' 20000
      fields := fields ++ [("proof", tree)]
  return obj fields


def emit (name : Name) : CommandElabM Unit := do
  let result ← liftTermElabM <| exportDeclaration name
  liftIO <| IO.println ("PROOFREADER_JSON:" ++ result.compress)

elab "#proofreader_export " target:str : command =>
  emit target.getString.toName

/-- Environment-based discovery includes declarations generated by commands.
No source-regex declaration count is used as the denominator here. -/
elab "#proofreader_export_module " target:str : command => do
  let env ← getEnv
  let moduleName := target.getString.toName
  let names := env.constants.toList.filterMap fun (n, _) => do
    let idx ← env.getModuleIdxFor? n
    if env.header.moduleNames[idx.toNat]! == moduleName then some n else none
  let names := names.toArray.qsort Name.lt
  for name in names do
    try emit name
    catch ex =>
      let message ← ex.toMessageData.toString
      liftIO <| IO.println <| "PROOFREADER_JSON:" ++ (obj [
        ("schema", toJson "proofreader.export-failure/v1"),
        ("name", toJson name.toString), ("error", toJson message)]).compress
  liftIO <| IO.println <| "PROOFREADER_JSON:" ++ (obj [
    ("schema", toJson "proofreader.module-inventory/v1"),
    ("module", toJson moduleName.toString),
    ("declarations", toJson (names.map Name.toString))]).compress

end ProofReader
