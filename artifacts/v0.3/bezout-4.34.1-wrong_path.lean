import Mathlib.Algebra.EuclideanDomain.Basic
import Mathlib.Tactic.Ring
import Lean
import Lean.Util.CollectAxioms
set_option maxRecDepth 10000
set_option maxHeartbeats 8000000
open Lean Meta Elab Command
namespace ProofReaderNarrative
abbrev obj := Json.mkObj
structure State where
  frames : Array Json := #[]
  terms : Array Expr := #[]
abbrev M := StateT State MetaM
def pp (e : Expr) : MetaM String := do
  return (← ppExpr e).pretty
def nameOf (e : Expr) : String :=
  match e.getAppFn with | .const n _ => n.toString | _ => ""
partial def visit (e : Expr) (xs : Array Expr) (path : Array Nat)
    (base : Name) (levels : List Name) (depth : Nat) : M Nat := do
  let e := e.consumeMData
  let i := (← get).frames.size
  if i ≥ 1000 then throwError "Narrative frame budget exceeded; no complete record"
  modify fun s => {s with frames := s.frames.push Json.null, terms := s.terms.push (e.abstract xs)}
  let typ ← liftM <| inferType e
  let isProof ← liftM <| isProp typ
  let ct ← liftM <| mkForallFVars xs typ (usedLetOnly := false)
  let cv ← liftM <| mkLambdaFVars xs e (usedLetOnly := false)
  if !isProof then throwError "Narrative visits must be proof-valued"
  withOptions (fun o => o.setBool `debug.skipKernelTC false) do
    addDecl <| .thmDecl {name := .num base i, levelParams := levels, type := ct, value := cv}
  let goal ← liftM <| pp typ
  let mut context : Array Json := #[]
  for x in xs do
    let d ← liftM <| x.fvarId!.getDecl
    context := context.push <| obj [("name", toJson d.userName.toString), ("type", toJson (← liftM <| pp d.type))]
  let head := nameOf e
  let arithmetic := head.startsWith "Mathlib.Tactic.Ring."
  let rewrite := #["Eq.mpr", "Eq.mp", "of_eq_true", "congrArg", "congr", "congrFun", "congrFun'"].contains head
  let stopHere := depth == 0 || arithmetic || rewrite
  let mut role := if arithmetic then "ring" else if rewrite then "rewrite" else "application"
  let mut children : Array Nat := #[]
  let mut premises : Array Json := #[]
  let mut objects : Array String := #[]
  let mut fields : List (String × Json) := []
  if !stopHere then
    match e with
    | .lam n d b bi =>
      let dp ← liftM <| isProp d
      role := if dp then "assume" else "introduce"
      fields := [("binder", toJson n.toString), ("domain", toJson (← liftM <| pp d))]
      let st ← get
      let (ch, st) ← liftM <| withLocalDecl n bi d fun x =>
        (visit (b.instantiate1 x) (xs.push x) (path.push 1) base levels (depth-1)).run st
      set st
      children := #[ch]
    | .letE n t v b nd =>
      let vp ← liftM <| isProp t
      role := if vp then "have" else "define"
      fields := [("binder", toJson n.toString), ("domain", toJson (← liftM <| pp t))]
      if vp then children := children.push (← visit v xs (path.push 1) base levels (depth-1))
      else fields := fields ++ [("value", toJson (← liftM <| pp v))]
      let st ← get
      let (ch, st) ← liftM <| withLetDecl n t v (nondep := nd) fun x =>
        (visit (b.instantiate1 x) (xs.push x) (path.push 2) base levels (depth-1)).run st
      set st
      children := children.push ch
    | .app .. =>
      let args := e.getAppArgs
      for k in [:args.size] do
        let a := args[k]!
        let atp ← liftM <| inferType a
        let proof ← liftM <| isProp atp
        if proof then
          let p := (path ++ Array.replicate (args.size-k-1) 0).push 1
          let ch ← visit a xs p base levels (depth-1)
          premises := premises.push <| obj [("argument", toJson k), ("statement", toJson (← liftM <| pp atp)), ("frame", toJson ch)]
          children := children.push ch
        else objects := objects.push (← liftM <| pp a)
      if head == "Exists.intro" then role := "witness"
      if #["Exists.casesOn", "Exists.elim"].contains head then role := "choose"
      if #["dite", "ite", "Decidable.byCases", "Classical.byCases", "Or.elim", "Or.casesOn"].contains head then role := "cases"
      if head == "And.intro" then role := "combine"
      if #["Eq.trans", "Trans.trans"].contains head then role := "chain"
      if head == "Eq.refl" then role := "reflexivity"
      if head == "mul_left_cancel₀" then role := "cancel"
      if head == "id" then role := "identity"
    | .fvar id =>
      role := "given"
      fields := [("binder", toJson (← liftM <| id.getDecl).userName.toString)]
    | .const .. => role := "named"
    | _ => role := "unexpanded"
  fields := fields ++ [("id", toJson i), ("path", toJson path), ("statement", toJson goal),
    ("role", toJson role), ("head", toJson head), ("context", toJson context),
    ("children", toJson children), ("premises", toJson premises), ("objects", toJson objects),
    ("budget_cut", toJson (depth == 0))]
  modify fun s => {s with frames := s.frames.set! i (obj fields)}
  return i
private partial def erase : Expr → Expr
  | .mdata _ b => erase b
  | .app f a => .app (erase f) (erase a)
  | .lam n d b bi => .lam n (erase d) (erase b) bi
  | .forallE n d b bi => .forallE n (erase d) (erase b) bi
  | .letE n t v b nd => .letE n (erase t) (erase v) (erase b) nd
  | .proj n i b => .proj n i (erase b)
  | e => e
private partial def atPath (e : Expr) (path : List Nat) : Except String Expr := do
  match path with
  | [] => return e
  | k :: ks => match e, k with
    | .app f _, 0 => atPath f ks
    | .app _ a, 1 => atPath a ks
    | .lam _ d _ _, 0 | .forallE _ d _ _, 0 => atPath d ks
    | .lam _ _ b _, 1 | .forallE _ _ b _, 1 => atPath b ks
    | .letE _ t _ _ _, 0 => atPath t ks
    | .letE _ _ v _ _, 1 => atPath v ks
    | .letE _ _ _ b _, 2 => atPath b ks
    | .proj _ _ b, 0 => atPath b ks
    | _, _ => throw "Invalid original source path"
private def checkPaths (original : Expr) (state : State) : MetaM Unit := do
  let original := erase original
  for i in [:state.frames.size] do
    let path ← match state.frames[i]!.getObjVal? "path" >>= Json.getArr? with
      | .error message => throwError "{message}"
      | .ok values =>
        match values.toList.mapM Json.getNat? with
        | .error message => throwError "{message}"
        | .ok path => pure path
    let actual ← match atPath original (if i == 40 then [] else path) with
      | .error message => throwError "{message}"
      | .ok e => pure e
    unless actual == erase state.terms[i]! do throwError "Original source linkage mismatch at frame {i}"
def exportOne (n : Name) : MetaM Json := do
  let info ← getConstInfo n
  let .thmInfo v := info | throwError "Expected theorem"
  let ax ← collectAxioms n
  unless ax.all (fun n => #[`propext, `Classical.choice, `Quot.sound].contains n) do throwError "Disallowed axiom"
  let base ← mkFreshUserName `PRNarrativeCheck
  let (_, s) ← (visit v.value #[] #[] base v.levelParams 160).run {}
  checkPaths v.value s
  return obj [("schema", toJson "proofreader.narrative/v1"), ("theorem", toJson n.toString),
    ("lean_version", toJson Lean.versionString), ("axioms", toJson (ax.map Name.toString)),
    ("statement", toJson (← pp v.type)), ("frames", toJson s.frames),
    ("judgements_checked", toJson s.frames.size), ("formula_backend", toJson "Lean pretty-printer")]
elab "#narrative " target:str : command => do
  let r ← liftTermElabM <| exportOne target.getString.toName
  logInfo ("PR_NARRATIVE:" ++ r.compress)
end ProofReaderNarrative

namespace OAI

noncomputable section

namespace ComplexCancellation.BezoutFrame

/-- Principalization of an SL₂/diagonal-torus point over a Euclidean domain.
This supplies the invariant-localization frame over the slice polynomial ring. -/
theorem exists_frame {R : Type*} [EuclideanDomain R] (x y z : R)
    (h : x*y = z*(z+1)) :
    ∃ a d b c : R, a*b = x ∧ d*c = y ∧ d*b = z ∧ a*c-d*b = 1 := by
  classical
  let g := EuclideanDomain.gcd x z
  by_cases hg : g = 0
  · have hxz : x = 0 ∧ z = 0 := EuclideanDomain.gcd_eq_zero_iff.mp hg
    exact ⟨1, y, 0, 1, by simp [hxz.1], by simp, by simp [hxz.2], by simp⟩
  · obtain ⟨a, ha⟩ := EuclideanDomain.gcd_dvd_left x z
    obtain ⟨d, hd⟩ := EuclideanDomain.gcd_dvd_right x z
    change x = g*a at ha
    change z = g*d at hd
    let r := EuclideanDomain.gcdA x z
    let s := EuclideanDomain.gcdB x z
    have hbez : a*r+d*s=1 := by
      apply mul_left_cancel₀ hg
      calc g * (a*r+d*s) = x*r+z*s := by rw [ha, hd]; ring
        _ = g := (EuclideanDomain.gcd_eq_gcd_ab x z).symm
        _ = g*1 := (mul_one g).symm
    have hrel : a*y=d*(z+1) := by
      apply mul_left_cancel₀ hg
      calc g*(a*y) = x*y := by rw [ha]; ring
        _ = z*(z+1) := h
        _ = g*(d*(z+1)) := by rw [hd]; ring
    refine ⟨a,d,g,r*(z+1)+s*y, ?_, ?_, ?_, ?_⟩
    · rw [mul_comm, ← ha]
    · calc d*(r*(z+1)+s*y) = r*(d*(z+1))+d*s*y := by ring
        _ = r*(a*y)+d*s*y := by rw [hrel]
        _ = (a*r+d*s)*y := by ring
        _ = y := by rw [hbez, one_mul]
    · rw [mul_comm, ← hd]
    · calc a*(r*(z+1)+s*y)-d*g = a*r*(z+1)+s*(a*y)-z := by rw [hd]; ring
        _ = (a*r+d*s)*(z+1)-z := by rw [hrel]; ring
        _ = 1 := by rw [hbez]; ring

end ComplexCancellation.BezoutFrame

end

end OAI

open Lean Elab Command in
elab "#probe_narrative " target:str : command => do
  let n := target.getString.toName
  let r ← liftTermElabM <| ProofReaderNarrative.exportOne n
  let r2 ← liftTermElabM <| ProofReaderNarrative.exportOne n
  unless r.compress == r2.compress do throwError "Nondeterministic snapshot"
  let changed := r.compress.replace "\"statement\":\"a * r + d * s = 1\"" "\"statement\":\"0 = 1\""
  unless changed != r.compress do throwError "Tamper target not found"
  let bad ← match Lean.Json.parse changed with
    | .ok j => pure j
    | .error e => throwError "{e}"
  let validate (expected : Lean.Json) : CommandElabM Unit := do
    let actual ← liftTermElabM <| ProofReaderNarrative.exportOne n
    unless actual.compress == expected.compress do throwError "Snapshot mismatch"
  let rejected ← try
    validate bad
    pure false
  catch ex =>
    pure ((← ex.toMessageData.toString) == "Snapshot mismatch")
  unless rejected do throwError "Corrupted snapshot was not rejected"
  logInfo "PR_NARRATIVE_REPEAT_OK"
  logInfo "PR_NARRATIVE_MUTATION_REJECTED"
  logInfo ("PR_NARRATIVE:" ++ r.compress)
#probe_narrative "OAI.ComplexCancellation.BezoutFrame.exists_frame"
