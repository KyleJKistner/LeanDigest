/-
# Source-bound proof decomposition

Lift selected source occurrences into named lemmas, replace those occurrences
with applications of the lemmas, and kernel-check the reconstructed theorem.
Selection and order are proposals. No source formula or hypothesis comes from
prose. This is a checked metaprogram, not a universal translation theorem.
-/
import SourceExpressions

open Lean Meta
namespace ProofReader.ProofDecomposition
open SourceExpressions

structure Replacement where
  frame : Nat
  path : Path
  name : Name
  needed : Array Nat

structure Rewritten where
  value : Expr
  uses : Array Nat := #[]

private def pathPrefix (a b : Path) : Bool :=
  a.size ≤ b.size && a == b.extract 0 a.size

/-- Only requested occurrences are replaced; other source subterms are retained.
Bindings are opened in their original context and then abstracted again. -/
private partial def replaceSource (e : Expr) (here : Path) (ctx : Array Local)
    (replacements : Array Replacement) (levels : List Name) : MetaM Rewritten := do
  let e := e.consumeMData
  if let some r := replacements.find? (fun r => r.path == here) then
    let xs := vars ctx
    let typ ← inferType e
    unless ← isProp typ do throwError "Replacement occurrence is not a proof"
    let needed ← dependencies e typ xs
    unless needed == r.needed do throwError "Replacement context changed"
    let mut args : Array Expr := #[]
    for k in needed do
      let d ← xs[k]!.fvarId!.getDecl
      if (d.value? (allowNondep := true)).isNone then args := args.push xs[k]!
    let use := mkAppN (mkConst r.name (levels.map Level.param)) args
    Replay.kernelCheck levels xs use typ
    return ⟨use, #[r.frame]⟩
  unless replacements.any (fun r => pathPrefix here r.path) do return ⟨e, #[]⟩
  match e with
  | .app f a =>
    let rf ← replaceSource f (here.push 0) ctx replacements levels
    let ra ← replaceSource a (here.push 1) ctx replacements levels
    return ⟨mkApp rf.value ra.value, rf.uses ++ ra.uses⟩
  | .lam n d b bi | .forallE n d b bi =>
    let rd ← replaceSource d (here.push 0) ctx replacements levels
    let rb ← withLocalDecl n bi d fun x => do
      let kind := if e.isLambda then "lambda" else "forall"
      let result ← replaceSource (b.instantiate1 x) (here.push 1)
        (ctx.push ⟨here, kind, x⟩) replacements levels
      return {result with value := result.value.abstract #[x]}
    let value := if e.isLambda then mkLambda n bi rd.value rb.value
      else mkForall n bi rd.value rb.value
    return ⟨value, rd.uses ++ rb.uses⟩
  | .letE n t v b nd =>
    let rt ← replaceSource t (here.push 0) ctx replacements levels
    let rv ← replaceSource v (here.push 1) ctx replacements levels
    let rb ← withLetDecl n t v (nondep := nd) fun x => do
      let result ← replaceSource (b.instantiate1 x) (here.push 2)
        (ctx.push ⟨here, "let", x⟩) replacements levels
      return {result with value := result.value.abstract #[x]}
    return ⟨.letE n rt.value rv.value rb.value nd, rt.uses ++ rv.uses ++ rb.uses⟩
  | .proj n i b =>
    let result ← replaceSource b (here.push 0) ctx replacements levels
    return ⟨.proj n i result.value, result.uses⟩
  | _ => throwError "Selected replacement is not below its source occurrence"

private def addTheorem (n : Name) (levels : List Name) (typ value : Expr) : MetaM Unit := do
  if (← getEnv).contains n then throwError "Decomposition name already exists"
  if typ.hasMVar || value.hasMVar || typ.hasFVar || value.hasFVar ||
      typ.hasLooseBVars || value.hasLooseBVars then
    throwError "Decomposition theorem is not closed"
  withOptions (fun o => (o.setBool `debug.skipKernelTC false).setBool `Elab.async false) do
    addDecl <| .thmDecl { name := n, levelParams := levels, type := typ, value := value }
  let axs ← collectAxioms n
  unless axs.all (fun a => #[`propext, `Classical.choice, `Quot.sound].contains a) do
    throwError "Decomposition introduced an unpermitted axiom"

/-- Check order by source containment. Independent subproofs can be scheduled
in either order; a containing lemma must follow its selected inner lemmas. -/
def checkSelection (paths : Array Path) (selected : Array Nat) : MetaM Unit := do
  unless selected.size ≤ 1000 do throwError "Decomposition selection budget exceeded"
  let mut seen : Array Nat := #[]
  for i in selected do
    unless i < paths.size do throwError "Decomposition frame outside source inventory"
    if paths[i]!.isEmpty then throwError "Root theorem cannot be selected as an intermediate lemma"
    if seen.contains i then throwError "Duplicate decomposition frame"
    for j in seen do
      if pathPrefix paths[j]! paths[i]! then
        throwError "Selected inner lemma must precede containing lemma"
    seen := seen.push i

/-- Regenerate the expected frontier from source containment, not supplied edges. -/
private def frontier (paths : Array Path) (selected : Array Nat) (here : Path) : Array Nat :=
  let descendants := selected.filter fun i => here != paths[i]! && pathPrefix here paths[i]!
  descendants.filter fun i => !(descendants.any fun j =>
    i != j && pathPrefix paths[j]! paths[i]!)

private def sameSet (a b : Array Nat) : Bool :=
  a.size == b.size && a.all b.contains && b.all a.contains

/-- The expected target and complete path inventory are external checker inputs.
All installed declarations are rolled back on any failure, including a kernel
failure after earlier lemmas succeeded. The returned result is an observation. -/
def compose (record : Json) (target : Name) (paths : Array Path)
    (selected : Array Nat) (destination : Name) : MetaM Json := do
  checkPaths paths
  checkSelection paths selected
  if destination.isAnonymous then throwError "Missing decomposition namespace"
  let finalName := Name.str destination "result"
  for i in selected do
    if (← getEnv).contains (Name.str destination ("lemma_" ++ toString i)) then
      throwError "Decomposition name already exists"
  if (← getEnv).contains finalName then throwError "Decomposition name already exists"
  let (result, nextEnv) ← withoutModifyingEnv' do
    let checked ← Replay.verify record target paths
    let (info, original, originalAxioms) ← source target
    let es ← Replay.decode record
    let frames ← Replay.arr (← Replay.field record "frames")
    let mut installed : Array Replacement := #[]
    let mut rows : Array Json := #[]
    let mut uses : Array Nat := #[]
    for i in selected do
      let p := paths[i]!
      let name := Name.str destination ("lemma_" ++ toString i)
      let expected ← Replay.getExpr es (← Replay.field frames[i]! "lifted_type")
      let (needed, row, direct) ← withSourceAt original p.toList #[] #[] fun e ctx => do
        let xs := vars ctx
        let typ ← inferType e
        let needed ← dependencies e typ xs
        let rewritten ← replaceSource e p ctx installed info.levelParams
        unless sameSet rewritten.uses (frontier paths selected p) do
          throwError "Decomposition did not replace its selected source frontier"
        let (ct, cv) ← close rewritten.value typ xs needed
        unless Expr.equal expected (ProofReaderJsonReplay.erase ct) do
          throwError "Decomposition changed an extracted claim"
        addTheorem name info.levelParams expected cv
        let row := obj [ ("frame", toJson i), ("path", toJson p),
          ("name", ProofReaderKernel.nameJson name), ("uses", toJson rewritten.uses),
          ("required_context", toJson needed), ("signature", toJson (← pp ct)) ]
        return (needed, row, rewritten.uses)
      installed := installed.push ⟨i, p, name, needed⟩
      rows := rows.push row
      uses := uses ++ direct
    let final ← replaceSource original #[] #[] installed info.levelParams
    unless sameSet final.uses (frontier paths selected #[]) do
      throwError "Decomposition root did not use its selected source frontier"
    uses := uses ++ final.uses
    unless sameSet uses selected do throwError "Decomposition omitted or duplicated a selected lemma"
    addTheorem finalName info.levelParams info.type final.value
    let finalAxioms ← collectAxioms finalName
    return obj [("schema", toJson "leanglish.proof-decomposition-result/v1"),
      ("source", ProofReaderKernel.nameJson target), ("selection", toJson selected),
      ("lemmas", toJson rows), ("root_uses", toJson final.uses),
      ("result", ProofReaderKernel.nameJson finalName), ("statement", toJson (← pp info.type)),
      ("source_kernel_judgements", toJson checked),
      ("composition_kernel_judgements", toJson (2 * selected.size + 1)),
      ("source_axioms", toJson (originalAxioms.map Name.toString)),
      ("result_axioms", toJson (finalAxioms.map Name.toString)),
      ("english_certified", toJson false)]
  setEnv nextEnv
  return result

end ProofReader.ProofDecomposition
