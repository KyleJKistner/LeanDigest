import Lean
open Lean Meta
namespace Leanglish.Pilot
set_option maxRecDepth 8192
set_option maxHeartbeats 4000000

def body? (ci : ConstantInfo) : Option Expr :=
  match ci with
  | .thmInfo v => some v.value
  | .defnInfo v => some v.value
  | .opaqueInfo v => some v.value
  | _ => none

partial def nodes : Expr → Nat
  | .app f a => 1 + nodes f + nodes a
  | .lam _ d b _ | .forallE _ d b _ => 1 + nodes d + nodes b
  | .letE _ t v b _ => 1 + nodes t + nodes v + nodes b
  | .mdata _ b | .proj _ _ b => 1 + nodes b
  | _ => 1

/-- Traverse types AND bodies. Aliases of forbidden targets are also forbidden. -/
def closure (start : Array Name) : MetaM (Array Name) := do
  let mut pending := start
  let mut seen : NameSet := {}
  let mut found : Array Name := #[]
  let mut cursor := 0
  while cursor < pending.size do
    if cursor > 200000 then throwError "dependency budget exceeded"
    let n := pending[cursor]!
    cursor := cursor + 1
    unless seen.contains n do
      seen := seen.insert n
      found := found.push n
      let ci ← getConstInfo n
      pending := pending ++ ci.type.getUsedConstants
      if let some v := body? ci then pending := pending ++ v.getUsedConstants
  return found

/-- Check the candidate BODY at the externally chosen reference TYPE.
    The proof script has already elaborated; this additionally disables kernel bypass.
    Logs are observations, not authenticated certificates or an English checker. -/
def check (candidate reference : Name) (forbidden : Array Name) : MetaM Json := do
  let ci ← getConstInfo candidate
  let ri ← getConstInfo reference
  unless ci.levelParams.length == ri.levelParams.length do
    throwError "universe parameter mismatch"
  let some val := body? ci | throwError "candidate has no proof body"
  let levels := ci.levelParams.map Level.param
  let expected := ri.type.instantiateLevelParams ri.levelParams levels
  unless ← isProp expected do throwError "reference is not a proposition"
  let ax ← collectAxioms candidate
  for a in ax do
    unless #[`propext, `Classical.choice, `Quot.sound].contains a do
      throwError "unpermitted axiom: {a}"
  let deps ← closure val.getUsedConstants
  for n in forbidden do
    if deps.contains n then throwError "forbidden dependency: {n}"
  withoutModifyingEnv <| withOptions (fun o =>
      (o.setBool `debug.skipKernelTC false).setBool `Elab.async false) do
    let name ← mkFreshUserName `PilotKernelCheck
    addDecl <| .thmDecl {name, levelParams := ci.levelParams, type := expected, value := val}
  let direct := val.getUsedConstants.map Name.toString
  let owned := deps.filter fun n => n.toString.startsWith "Candidate." || n.toString.startsWith (reference.toString ++ ".")
  let mut helperNodes := 0
  let mut helpers : Array Json := #[]
  for n in owned do
    let info ← getConstInfo n
    let count := (body? info).map nodes |>.getD 0
    helperNodes := helperNodes + count
    helpers := helpers.push <| Json.mkObj [
      ("name", toJson n.toString), ("statement", toJson (← ppExpr info.type).pretty),
      ("body_nodes", toJson count)]
  let mut claims : Array Json := #[]
  for (n, info) in (← getEnv).constants.toList do
    if n.toString.startsWith "Candidate." && !(n.toString.splitOn ".").any (fun p => p.startsWith "_" || p.startsWith "match") then
      if let .thmInfo _ := info then
        let axioms ← collectAxioms n
        unless axioms.all (fun a => #[`propext, `Classical.choice, `Quot.sound].contains a) do
          throwError "unpermitted auxiliary axiom"
        claims := claims.push <| Json.mkObj [("name", toJson n.toString),
          ("statement", toJson (← ppExpr info.type).pretty),
          ("axioms", toJson (axioms.map Name.toString))]
  return Json.mkObj [
    ("claims", toJson claims), ("candidate", toJson candidate.toString), ("reference", toJson reference.toString),
    ("statement", toJson (← ppExpr expected).pretty), ("kernel_checked", toJson true),
    ("axioms", toJson (ax.map Name.toString)), ("root_nodes", toJson (nodes val)),
    ("helper_nodes", toJson helperNodes), ("direct_constants", toJson direct),
    ("dependency_count", toJson deps.size), ("helpers", toJson helpers),
    ("english_certified", toJson false)]
end Leanglish.Pilot
