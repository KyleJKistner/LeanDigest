/- Source-bound narrative snapshots: the complete proof stays in the Lean source.
   The compiler derives and kernel-checks every selected judgement. The reading
   record never transports the enormous low-level proof term. Formula strings
   use Lean's pretty-printer; source/renderer/pretty-printer remain trusted. -/
import Lean
import Lean.Util.CollectAxioms
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
  let rewrite := #["Eq.mpr", "Eq.mp", "of_eq_true", "congr", "congrFun", "congrFun'"].contains head
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
      let arity := if #["Nat.rec", "Nat.recOn", "Nat.recAux"].contains head then 4
        else if #["List.rec", "List.recOn", "Exists.casesOn", "Exists.elim", "dite", "ite"].contains head then 5
        else if #["Or.elim", "Or.casesOn"].contains head then 6 else 0
      if arity > 0 && args.size > arity then
        -- Preserve the proof of the quantified/conditional intermediate claim.
        -- Its original path is a function-prefix, not an invented new proof.
        let headProof := mkAppN e.getAppFn (args.extract 0 arity)
        let prefixType ← liftM <| inferType headProof
        if ← liftM <| isProp prefixType then
          role := "specialize"
          let prefixPath := path ++ Array.replicate (args.size-arity) 0
          let ch ← visit headProof xs prefixPath base levels (depth-1)
          children := children.push ch
          for k in [arity:args.size] do
            let a := args[k]!
            let atp ← liftM <| inferType a
            if ← liftM <| isProp atp then
              let p := (path ++ Array.replicate (args.size-k-1) 0).push 1
              let ch ← visit a xs p base levels (depth-1)
              premises := premises.push <| obj [("argument", toJson k), ("statement", toJson (← liftM <| pp atp)), ("frame", toJson ch)]
              children := children.push ch
            else objects := objects.push (← liftM <| pp a)
      if role != "specialize" then
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
       if let .fvar fid := e.getAppFn then
         let declaration ← liftM <| fid.getDecl
         let mut localIndex : Option Nat := none
         for k in [:xs.size] do
           if xs[k]! == .fvar fid then localIndex := some k
         let some k := localIndex | throwError "Local application head is outside the exported context"
         role := "local-application"
         fields := [("binder", toJson declaration.userName.toString),
           ("domain", toJson (← liftM <| pp declaration.type)), ("local_index", toJson k)]
       if head == "congrArg" then role := "congruence"
       if #["Nat.rec", "Nat.recOn", "Nat.recAux", "List.rec", "List.recOn"].contains head then role := "induction"
       if head == "Exists.intro" then role := "witness"
       if #["Exists.casesOn", "Exists.elim"].contains head then role := "choose"
       if #["dite", "ite", "Decidable.byCases", "Classical.byCases", "Or.elim", "Or.casesOn"].contains head then role := "cases"
       if head == "And.intro" then role := "combine"
       if #["Eq.trans", "Trans.trans"].contains head then role := "chain"
       if #["Eq.refl", "rfl"].contains head then role := "reflexivity"
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
    let actual ← match atPath original path with
      | .error message => throwError "{message}"
      | .ok e => pure e
    unless actual == erase state.terms[i]! do throwError "Original source linkage mismatch at frame {i}"

def exportOne (n : Name) : MetaM Json := do
  let info ← getConstInfo n
  let value ← match info with
    | .thmInfo v => pure v.value
    | .defnInfo v => pure v.value
    | .opaqueInfo v => pure v.value
    | _ => throwError "Expected a declaration with a proof body"
  unless ← isProp info.type do throwError "Expected a proof-valued declaration"
  let ax ← collectAxioms n
  unless ax.all (fun n => #[`propext, `Classical.choice, `Quot.sound].contains n) do throwError "Disallowed axiom"
  let base ← mkFreshUserName `PRNarrativeCheck
  let (_, s) ← (visit value #[] #[] base info.levelParams 160).run {}
  checkPaths value s
  return obj [("schema", toJson "proofreader.narrative/v1"), ("theorem", toJson n.toString),
    ("lean_version", toJson Lean.versionString), ("axioms", toJson (ax.map Name.toString)),
    ("statement", toJson (← pp info.type)), ("frames", toJson s.frames),
    ("judgements_checked", toJson s.frames.size), ("formula_backend", toJson "Lean pretty-printer")]
elab "#narrative " target:str : command => do
  let r ← liftTermElabM <| exportOne target.getString.toName
  logInfo ("PR_NARRATIVE:" ++ r.compress)
end ProofReaderNarrative
