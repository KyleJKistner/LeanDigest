import Mathlib.Algebra.EuclideanDomain.Basic
import Mathlib.Tactic.Ring
import Lean
import Lean.Util.CollectAxioms
set_option maxHeartbeats 8000000
set_option maxRecDepth 12000
/- Typed, path-bound proof export. No prose is accepted as evidence. -/
open Lean Meta Elab Command
namespace ProofReaderFrontier

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
  let head := e.getAppFn
  let headName := match head with | .const n _ => n.toString | _ => ""
  let arithmetic := headName.startsWith "Mathlib.Tactic.Ring."
  let exhausted := depth == 0 || i ≥ 1500 || arithmetic
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
  fields := fields ++ [("children", toJson children), ("arguments", toJson args), ("truncated", toJson exhausted), ("frontier_reason", toJson (if arithmetic then "ring-certificate" else if exhausted then "budget" else ""))]
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
    ("type", toJson ty), ("term", toJson te), ("exprs", toJson s.exprs), ("steps", toJson s.steps),
    ("selection_policy", toJson "ring-frontier/v1")]

elab "#proofreader_frontier " target:str : command => do
  let record ← liftTermElabM <| exportOne target.getString.toName
  logInfo ("PROOFREADER_KERNEL:" ++ record.compress)
end ProofReaderFrontier
/- Independent decoder and source-path replay for exported expression DAGs.
   All selected judgements are reclosed over the ORIGINAL binders and sent to
   the Lean kernel. This does not prove the English renderer correct. -/
open Lean Meta Elab Command
namespace ProofReaderJsonReplay
abbrev J := Except String
def field (j : Json) (s : String) : J Json := j.getObjVal? s
def str (j : Json) : J String := j.getStr?
def num (j : Json) : J Nat := j.getNat?
def arr (j : Json) : J (Array Json) := j.getArr?
def flag (j : Json) : J Bool := j.getBool?
partial def name (j : Json) : J Name := do
  match ← str (← field j "tag") with
  | "anonymous" => return .anonymous
  | "str" => return .str (← name (← field j "prefix")) (← str (← field j "value"))
  | "num" =>
    let some n := (← str (← field j "value")).toNat? | throw "Invalid numeric name"
    return .num (← name (← field j "prefix")) n
  | _ => throw "Invalid name"
partial def level (j : Json) : J Level := do
  match ← str (← field j "tag") with
  | "zero" => return .zero
  | "succ" => return .succ (← level (← field j "of"))
  | "max" => return .max (← level (← field j "left")) (← level (← field j "right"))
  | "imax" => return .imax (← level (← field j "left")) (← level (← field j "right"))
  | "param" => return .param (← name (← field j "name"))
  | _ => throw "Invalid universe"
def binder (j : Json) : J BinderInfo := do
  match ← str j with
  | "explicit" => return .default
  | "implicit" => return .implicit
  | "strict-implicit" => return .strictImplicit
  | "instance" => return .instImplicit
  | _ => throw "Invalid binder"
def ref (xs : Array Expr) (j : Json) : J Expr := do
  let i ← num j
  if let some e := xs[i]? then return e else throw "Non-topological expression edge"
def expr (xs : Array Expr) (j : Json) : J Expr := do
  let get (s : String) := field j s
  let r (s : String) := get s >>= ref xs
  match ← str (← get "tag") with
  | "bvar" => return .bvar (← num (← get "index"))
  | "sort" => return .sort (← level (← get "level"))
  | "const" => return .const (← name (← get "name")) (← (← arr (← get "levels")).toList.mapM level)
  | "app" => return .app (← r "fn") (← r "arg")
  | "lam" => return .lam (← name (← get "name")) (← r "domain") (← r "body") (← binder (← get "binder"))
  | "forall" => return .forallE (← name (← get "name")) (← r "domain") (← r "body") (← binder (← get "binder"))
  | "let" => return .letE (← name (← get "name")) (← r "type") (← r "value") (← r "body") (← flag (← get "nondep"))
  | "nat" =>
    let some n := (← str (← get "value")).toNat? | throw "Invalid numeral"
    return .lit (.natVal n)
  | "str" => return .lit (.strVal (← str (← get "value")))
  | "proj" => return .proj (← name (← get "name")) (← num (← get "index")) (← r "of")
  | _ => throw "Invalid expression constructor"
partial def erase : Expr → Expr
  | .mdata _ b => erase b
  | .app f a => .app (erase f) (erase a)
  | .lam n d b i => .lam n (erase d) (erase b) i
  | .forallE n d b i => .forallE n (erase d) (erase b) i
  | .letE n t v b nd => .letE n (erase t) (erase v) (erase b) nd
  | .proj n i b => .proj n i (erase b)
  | e => e
partial def locate (e : Expr) (path : List Nat) (ctx : List Expr := []) : J (Expr × List Expr) := do
  match path with
  | [] => return (e, ctx)
  | k :: ks => match e, k with
    | .app f _, 0 => locate f ks ctx
    | .app _ a, 1 => locate a ks ctx
    | .lam _ d _ _, 0 | .forallE _ d _ _, 0 => locate d ks ctx
    | .lam _ _ b _, 1 | .forallE _ _ b _, 1 => locate b ks (e :: ctx)
    | .letE _ t _ _ _, 0 => locate t ks ctx
    | .letE _ _ v _ _, 1 => locate v ks ctx
    | .letE _ _ _ b _, 2 => locate b ks (e :: ctx)
    | .proj _ _ b, 0 => locate b ks ctx
    | _, _ => throw "Invalid original proof path"
def close (e : Expr) (ctx : List Expr) (typ : Bool) : J Expr :=
  ctx.foldlM (fun e b => do
    match b with
    | .lam n d _ i | .forallE n d _ i => return if typ then .forallE n d e i else .lam n d e i
    | .letE n t v _ nd => return .letE n t v e nd
    | _ => throw "Invalid binder context") e
def liftJ {α : Type} (x : J α) : TermElabM α :=
  match x with | .ok a => pure a | .error msg => throwError "{msg}"
def verify (record : Json) (base : Name) : TermElabM Nat := do
  let get (s : String) := liftJ (field record s)
  let n ← liftJ <| name (← get "name")
  let vs ← liftJ <| str (← get "lean_version")
  unless vs == Lean.versionString do throwError "Toolchain mismatch"
  let levels ← liftJ do (← arr (← field record "levels")).toList.mapM name
  let mut xs : Array Expr := #[]
  for j in (← liftJ <| arr (← get "exprs")) do
    xs := xs.push (← liftJ <| expr xs j)
  let value ← liftJ <| ref xs (← get "term")
  let typ ← liftJ <| ref xs (← get "type")
  let info ← getConstInfo n
  let original ← match info with | .thmInfo v => pure (erase v.value) | _ => throwError "Not a theorem"
  unless info.levelParams == levels do throwError "Universe inventory mismatch"
  unless erase info.type == typ do throwError "Statement AST mismatch"
  unless original == value do throwError "Proof AST mismatch"
  let axioms ← collectAxioms n
  unless axioms.all (fun n => #[`propext, `Classical.choice, `Quot.sound].contains n) do throwError "Disallowed axiom"
  let ax ← liftJ do (← arr (← field record "axioms")).mapM str
  unless axioms.map Name.toString == ax do throwError "Axiom inventory mismatch"
  withOptions (fun o => o.setBool `debug.skipKernelTC false) do
    addDecl <| .thmDecl {name := .str base "root", levelParams := levels, type := typ, value := value}
  let steps ← liftJ <| arr (← get "steps")
  let mut count := 0
  for s in steps do
    let args ← liftJ (field s "arguments" >>= arr)
    for c in #[s] ++ args do
      let path ← liftJ do (← arr (← field c "path")).toList.mapM num
      let (actual, ctx) ← liftJ <| locate original path
      let te ← liftJ do ref xs (← field c "term")
      unless actual == te do throwError "Source linkage mismatch at claim {count}"
      let ty ← liftJ do ref xs (← field c "type")
      let proof ← liftJ (field c "is_proof" >>= flag)
      let closedTerm ← liftJ <| close te ctx false
      let closedType ← liftJ <| close ty ctx true
      unless (← Meta.isProp closedType) == proof do throwError "Proof/data classification mismatch"
      withOptions (fun o => o.setBool `debug.skipKernelTC false) do
        if proof then
          addDecl <| .thmDecl {name := .num base count, levelParams := levels, type := closedType, value := closedTerm}
        else
          addDecl <| .defnDecl {name := .num base count, levelParams := levels, type := closedType, value := closedTerm, hints := .abbrev, safety := .safe}
      if let .ok dp := field c "domain_is_prop" then
        if let .lam _ d _ _ := actual then
          let cd ← liftJ <| close d ctx true
          unless (← Meta.isProp cd) == (← liftJ <| flag dp) do throwError "Binder classification mismatch"
      count := count + 1
  return count
end ProofReaderJsonReplay

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
elab "#checked_frontier " target:str : command => do
  let record ← liftTermElabM <| ProofReaderFrontier.exportOne target.getString.toName
  let n ← liftTermElabM <| ProofReaderJsonReplay.verify record `PRChecked.good
  logInfo s!"PR_JSON_REPLAY_OK:{n}"
  logInfo ("PROOFREADER_KERNEL:" ++ record.compress)
#checked_frontier "OAI.ComplexCancellation.BezoutFrame.exists_frame"
