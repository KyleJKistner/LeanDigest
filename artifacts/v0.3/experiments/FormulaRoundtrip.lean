/- An additional check for source-bound snapshots. A printed Lean expression is
   parsed and elaborated in its actual local context. A fresh kernel theorem
   checks reflexive equality with the original expression. -/
import Lean
open Lean Meta Elab
namespace ProofReaderFormula

def checkedText (e : Expr) (xs : Array Expr) (levels : List Name)
    (checkName : Name) : MetaM String := do
  let text := (← ppExpr e).pretty
  let stx ← match Parser.runParserCategory (← getEnv) `term text with
    | .ok s => pure s
    | .error message => throwError "Printed expression does not parse: {message}"
  let expected ← inferType e
  let decls ← xs.toList.mapM fun x => x.fvarId!.getDecl
  let parsed ← withLocalInstances decls do
    let (parsed, _) ← (Term.withLevelNames levels do
      let parsed ← Term.elabTerm stx (some expected) (catchExPostpone := false)
      Term.synthesizeSyntheticMVarsNoPostponing
      instantiateMVars parsed).run
    pure parsed
  if parsed.hasMVar then throwError "Printed expression has unresolved metavariables"
  unless ← isDefEq e parsed do throwError "Printed expression changed meaning: {text}"
  let eqType ← mkEq e parsed
  let eqProof ← mkEqRefl e
  let closedType ← mkForallFVars xs eqType (usedLetOnly := false)
  let closedProof ← mkLambdaFVars xs eqProof (usedLetOnly := false)
  withOptions (fun opts => opts.setBool `debug.skipKernelTC false) do
    addDecl <| .thmDecl { name := checkName, levelParams := levels, type := closedType, value := closedProof }
  return text
end ProofReaderFormula
