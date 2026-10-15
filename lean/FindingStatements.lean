/-!
Read the type of a named declaration from an imported comparison specification.
Comparison modules intentionally contain admitted target proofs. This exporter
checks and exposes STATEMENTS; it does not verify the supplied solution proof.
The source file, compiler, pretty-printer and English renderer remain trusted.
-/
import Lean
import Lean.Util.CollectAxioms
open Lean Meta Elab Command
namespace LeanglishFindingStatements
private def pp (e : Expr) : MetaM String := do
  return (← ppExpr e).pretty
private def kindOf : ConstantInfo → String
  | .thmInfo _ => "theorem"
  | .defnInfo _ => "definition"
  | .opaqueInfo _ => "opaque"
  | .axiomInfo _ => "axiom"
  | .inductInfo _ => "inductive"
  | .ctorInfo _ => "constructor"
  | .recInfo _ => "recursor"
  | .quotInfo _ => "quotient"
private def exportStatement (name : Name) : MetaM Json := do
  let info ← getConstInfo name
  let statement ← pp info.type
  let fullStatement ← withOptions (fun o => o.setBool `pp.fullNames true |>.setBool `pp.universes true) <| pp info.type
  let proposition ← isProp info.type
  let (binders, conclusion) ← forallTelescope info.type fun xs body => do
    let mut binders : Array Json := #[]
    for x in xs do
      let decl ← x.fvarId!.getDecl
      binders := binders.push <| Json.mkObj [
        ("name", toJson (← pp x)),
        ("type", toJson (← pp decl.type)),
        ("is_assumption", toJson (← isProp decl.type)),
        ("is_instance", toJson (decl.binderInfo == .instImplicit)),
        ("implicit", toJson (decl.binderInfo != .default))]
    return (binders, ← pp body)
  let axioms ← collectAxioms name
  return Json.mkObj [
    ("schema", toJson "leanglish.finding-statement/v1"),
    ("name", toJson name.toString), ("declaration_kind", toJson (kindOf info)),
    ("lean_version", toJson Lean.versionString),
    ("statement", toJson statement), ("qualified_statement", toJson fullStatement),
    ("is_proposition", toJson proposition), ("binders", toJson binders),
    ("conclusion", toJson conclusion),
    ("specification_axioms", toJson (axioms.map Name.toString)),
    ("origin", toJson "comparison-specification"),
    ("solution_proof_checked", toJson false),
    ("english_formally_certified", toJson false)]
elab "#leanglish_statement " target:str : command => do
  let record ← liftTermElabM <| exportStatement target.getString.toName
  logInfo ("LEANGLISH_STATEMENT:" ++ record.compress)
end LeanglishFindingStatements
