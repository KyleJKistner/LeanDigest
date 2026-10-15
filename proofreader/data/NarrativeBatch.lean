/- Batch transport is separate from the narrative grammar. Enumerate before
   attempting any proof, emit one explicit outcome per candidate, and finish
   with a completion record. Individual failures must not shrink the inventory.
   This module deliberately does not trust an imported JSON receipt. -/
import Narrative
open Lean Meta Elab Command
namespace ProofReaderNarrativeBatch

abbrev obj := Json.mkObj

def emit (j : Json) : CommandElabM Unit := do
  let out ← liftM IO.getStdout
  liftM <| out.putStrLn ("PR_NARRATIVE_BATCH:" ++ j.compress)
  liftM <| out.flush

def proofKind (info : ConstantInfo) : String :=
  match info with
  | .thmInfo _ => "theorem"
  | .defnInfo _ => "proof-definition"
  | .opaqueInfo _ => "opaque-proof"
  | _ => ""

/-- The candidate set is frozen before the checker adds any declarations. -/
def enumerate (moduleName : Name) : CommandElabM (Array (Name × String) × Array Json) := do
  let env ← getEnv
  unless env.header.moduleNames.contains moduleName do
    throwError "Narrative batch target is not imported: {moduleName}"
  let names := env.constants.toList.filterMap fun (n, _) => do
    let idx ← env.getModuleIdxFor? n
    if env.header.moduleNames[idx.toNat]! == moduleName then some n else none
  let mut candidates := #[]
  let mut excluded := #[]
  for n in names.toArray.qsort Name.lt do
    let info ← getConstInfo n
    let prop ← liftTermElabM <| isProp info.type
    if prop then
      let kind := proofKind info
      if kind != "" then
        candidates := candidates.push (n, kind)
      else
        excluded := excluded.push <| obj [("name", toJson n.toString),
          ("reason", toJson "proposition-without-supported-proof-body")]
  return (candidates, excluded)

def run (moduleName : Name) (limit : Nat) : CommandElabM Unit := do
  let (names, excluded) ← enumerate moduleName
  let scope := "module:" ++ moduleName.toString
  emit <| obj [("schema", toJson "leanglish.narrative-inventory/v1"),
    ("scope", toJson scope), ("lean_version", toJson Lean.versionString),
    ("candidates", toJson (names.map fun (n, k) =>
      obj [("name", toJson n.toString), ("kind", toJson k)])),
    ("excluded", toJson excluded)]
  for i in [:min names.size limit] do
    let (n, kind) := names[i]!
    -- Kernel checks create temporary declarations. Restore the environment even
    -- on failure, so neither failed exports nor earlier checker constants can
    -- contaminate later outcomes or accumulate without bound.
    let saved ← get
    let event ← try
      let snapshot ← liftTermElabM <| ProofReaderNarrative.exportOne n
      pure <| obj [("schema", toJson "leanglish.narrative-outcome/v1"),
        ("name", toJson n.toString), ("kind", toJson kind),
        ("status", toJson "exported"), ("snapshot", snapshot)]
    catch ex =>
      let error ← ex.toMessageData.toString
      pure <| obj [("schema", toJson "leanglish.narrative-outcome/v1"),
        ("name", toJson n.toString), ("kind", toJson kind),
        ("status", toJson "failed"), ("error", toJson (error.take 4000).toString)]
    set saved
    emit event
  emit <| obj [("schema", toJson "leanglish.narrative-completion/v1"),
    ("scope", toJson scope), ("lean_version", toJson Lean.versionString),
    ("expected", toJson names.size), ("attempted", toJson (min names.size limit))]

elab "#narrative_batch " target:str " limit " limit:num : command =>
  run target.getString.toName limit.getNat
end ProofReaderNarrativeBatch
