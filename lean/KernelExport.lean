/- Typed, path-bound proof export. No prose is accepted as evidence. -/
import Lean
import Lean.Util.CollectAxioms
open Lean Meta Elab Command
namespace ProofReaderKernel

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
  let exhausted := depth == 0 || i ≥ 1500
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
  fields := fields ++ [("children", toJson children), ("arguments", toJson args), ("truncated", toJson exhausted)]
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
    ("type", toJson ty), ("term", toJson te), ("exprs", toJson s.exprs), ("steps", toJson s.steps)]

elab "#proofreader_kernel " target:str : command => do
  let record ← liftTermElabM <| exportOne target.getString.toName
  logInfo ("PROOFREADER_KERNEL:" ++ record.compress)
end ProofReaderKernel

namespace ProofReaderKernel
/-- Preserve one outcome for every enumerated theorem, including failed exports. -/
def emitOutcome (n : Name) : CommandElabM Unit := do
  try
    let record ← liftTermElabM <| exportOne n
    logInfo ("PROOFREADER_KERNEL:" ++ record.compress)
  catch ex =>
    let message ← ex.toMessageData.toString
    logInfo <| "PROOFREADER_KERNEL:" ++ (obj [
      ("schema", toJson "proofreader.kernel-failure/v2"),
      ("name", nameJson n), ("error", toJson message)]).compress

def emitInventory (names : Array Name) (scope : String) : CommandElabM Unit := do
  for n in names do emitOutcome n
  logInfo <| "PROOFREADER_KERNEL:" ++ (obj [
    ("schema", toJson "proofreader.kernel-inventory/v2"),
    ("scope", toJson scope), ("declaration_kind", toJson "theorem"),
    ("names", toJson (names.map nameJson)),
    ("lean_version", toJson Lean.versionString)]).compress

/-- Enumerate all theorem declarations in an imported module, not a lexical scan. -/
elab "#proofreader_kernel_module " target:str : command => do
  let env ← getEnv
  let moduleName := target.getString.toName
  unless env.header.moduleNames.contains moduleName do
    throwError "ProofReader target module is not imported: {moduleName}"
  let names := env.constants.toList.filterMap fun (n, info) => do
    match info with
    | .thmInfo _ =>
      let idx ← env.getModuleIdxFor? n
      if env.header.moduleNames[idx.toNat]! == moduleName then some n else none
    | _ => none
  emitInventory (names.toArray.qsort Name.lt) ("imported-module:" ++ target.getString)

/-- Enumerate theorems elaborated in the current source context. -/
elab "#proofreader_kernel_local" : command => do
  let env ← getEnv
  let names := env.constants.toList.filterMap fun (n, info) =>
    match info with
    | .thmInfo _ => if (env.getModuleIdxFor? n).isNone && !(n.toString.startsWith "ProofReaderKernel.") && (n.toString.splitOn ".ProofReaderKernel.").length == 1 then some n else none
    | _ => none
  emitInventory (names.toArray.qsort Name.lt) "current-source-theorems-excluding-tool-namespace"
end ProofReaderKernel
