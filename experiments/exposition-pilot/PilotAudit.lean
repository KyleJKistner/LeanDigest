import Lean
import Lean.Util.CollectAxioms
open Lean Meta Elab Command
namespace PilotAudit

partial def size (e : Expr) : Nat :=
  match e with
  | .app f a => 1 + size f + size a
  | .lam _ d b _ | .forallE _ d b _ => 1 + size d + size b
  | .letE _ t v b _ => 1 + size t + size v + size b
  | .proj _ _ b | .mdata _ b => 1 + size b
  | _ => 1

/-- Complete reachable declaration inventory, including types and definition bodies.
Not a claim of minimal mathematical dependencies. -/
def closure (start : Name) : MetaM (Array Name) := do
  let mut seen : Std.HashSet Name := {}
  let mut queue : Array Name := #[start]
  let mut pos := 0
  while pos < queue.size do
    let name := queue[pos]!
    pos := pos + 1
    if seen.contains name then continue
    seen := seen.insert name
    if seen.size > 100000 then throwError "Dependency budget exceeded"
    let info ← getConstInfo name
    for n in info.getUsedConstantsAsSet do
      if !seen.contains n then queue := queue.push n
  return seen.toArray.qsort (fun a b => a.toString < b.toString)

def check (expected target : Name) (output : String) : TermElabM Unit := do
  let original ← getConstInfo expected
  let candidate ← getConstInfo target
  let .thmInfo ci := candidate | throwError "Candidate is not a theorem"
  unless original.levelParams.length == ci.levelParams.length do
    throwError "Universe arity mismatch"
  let value := ci.value.instantiateLevelParams ci.levelParams (original.levelParams.map Level.param)
  withOptions (fun opts => (opts.setBool `debug.skipKernelTC false).setBool `Elab.async false) do
    addDecl <| Declaration.thmDecl {
      name := `PilotAudit.CheckedOriginalStatement
      levelParams := original.levelParams
      type := original.type
      value := value }
  let deps ← closure target
  if deps.contains expected then throwError "Circular shortcut: target theorem in dependency closure"
  let axioms ← collectAxioms target
  unless axioms.all (fun a => #[`propext, `Classical.choice, `Quot.sound].contains a) do
    throwError "Disallowed axiom: {axioms}"
  let locals := (← getEnv).constants.toList.filter (fun (n, _) => (`PilotCandidate).isPrefixOf n)
  let mut helpers : Array Json := #[]
  for (n, _) in locals do
    if (`PilotCandidate).isPrefixOf n && n != target then
      let h ← getConstInfo n
      if let some v := h.value? (allowOpaque := true) then
        helpers := helpers.push <| Json.mkObj [("name",toJson n.toString),
          ("statement",toJson (← ppExpr h.type).pretty), ("expression_nodes",toJson (size v))]
  let mut facts : Array Json := #[]
  for (n, _) in locals do
    if (`PilotCandidate).isPrefixOf n then
      let h ← getConstInfo n
      if h.isTheorem then
        let ax ← collectAxioms n
        unless ax.all (fun a => #[`propext, `Classical.choice, `Quot.sound].contains a) do
          throwError "Disallowed explanatory-lemma axiom: {n}"
        let hd ← closure n
        if hd.contains expected then throwError "Circular explanatory lemma: {n}"
        facts := facts.push <| Json.mkObj [("name",toJson n.toString),
          ("statement",toJson (← ppExpr h.type).pretty)]
  let record := Json.mkObj [
    ("schema",toJson "leanglish.exposition-pilot-check/v1"),
    ("lean_version",toJson Lean.versionString),
    ("expected",toJson expected.toString), ("candidate",toJson target.toString),
    ("statement",toJson (← ppExpr original.type).pretty),
    ("candidate_statement",toJson (← ppExpr ci.type).pretty),
    ("root_expression_nodes",toJson (size ci.value)),
    ("helper_inventory",Json.arr (helpers.qsort (fun a b => a.compress < b.compress))), ("facts",Json.arr (facts.qsort (fun a b => a.compress < b.compress))),
    ("dependencies",toJson (deps.map Name.toString)),
    ("axioms",toJson (axioms.map Name.toString)),
    ("same_statement_kernel_checked",toJson true),
    ("target_in_dependency_closure",toJson false),
    ("english_certified",toJson false)]
  IO.FS.writeFile output (record.pretty ++ "\n")
  logInfo "EXPOSITION_PILOT_ACCEPTED"
end PilotAudit
