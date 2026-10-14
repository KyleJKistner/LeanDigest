/- Independent decoder and source-path replay for exported expression DAGs.
   All selected judgements are reclosed over the ORIGINAL binders and sent to
   the Lean kernel. This does not prove the English renderer correct. -/
import Lean
import Lean.Util.CollectAxioms
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
