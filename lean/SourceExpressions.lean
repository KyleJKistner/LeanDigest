/-
# Source expressions

Read selected proof occurrences using the existing constructor-DAG codec. Local
variables are positional in expressions and identified by source paths in the
context. Names are labels only. Selected proof terms stay in the original module;
local let values needed for closure are retained in the DAG.
The replay checker decodes the expressions, compares them with the source, and
submits each source judgement and dependency-closed lemma to the Lean kernel.
This module does not interpret English.
-/
import KernelExport
import JsonReplay
import Lean.Util.CollectFVars

open Lean Meta
namespace ProofReader.SourceExpressions

abbrev obj := Json.mkObj
abbrev Path := Array Nat
structure Store where
  exprs : Array Json := #[]
  seen : Std.HashMap ExprStructEq Nat := {}

abbrev M := StateT Store MetaM

structure Local where
  path : Path
  kind : String
  expr : Expr
  deriving Inhabited

/-- Metadata is not a source-path edge. No beta, zeta, or proof reduction is used. -/
partial def withSourceAt {α : Type} (e : Expr) (remaining : List Nat) (path : Path)
    (locals : Array Local) (action : Expr → Array Local → MetaM α) : MetaM α := do
  let e := e.consumeMData
  match remaining with
  | [] => return ← action e locals
  | edge :: rest =>
    let nextPath := path.push edge
    match e, edge with
    | .app f _, 0 => return ← withSourceAt f rest nextPath locals action
    | .app _ a, 1 => return ← withSourceAt a rest nextPath locals action
    | .lam _ d _ _, 0 | .forallE _ d _ _, 0 =>
      return ← withSourceAt d rest nextPath locals action
    | .lam n d b bi, 1 =>
      return ← withLocalDecl n bi d (fun x =>
        withSourceAt (b.instantiate1 x) rest nextPath (locals.push ⟨path, "lambda", x⟩) action)
    | .forallE n d b bi, 1 =>
      return ← withLocalDecl n bi d (fun x =>
        withSourceAt (b.instantiate1 x) rest nextPath (locals.push ⟨path, "forall", x⟩) action)
    | .letE _ t _ _ _, 0 => return ← withSourceAt t rest nextPath locals action
    | .letE _ _ v _ _, 1 => return ← withSourceAt v rest nextPath locals action
    | .letE n t v b nd, 2 =>
      return ← withLetDecl n t v (nondep := nd) (fun x =>
        withSourceAt (b.instantiate1 x) rest nextPath (locals.push ⟨path, "let", x⟩) action)
    | .proj _ _ b, 0 => return ← withSourceAt b rest nextPath locals action
    | _, _ => throwError "Invalid source-expression path"

def vars (locals : Array Local) : Array Expr := locals.map (·.expr)

def pp (e : Expr) : MetaM String := return (← ppExpr e).pretty

/-- Syntactic free-variable uses, including occurrences inside types and terms. -/
def support (e : Expr) (xs : Array Expr) : MetaM (Array Nat) := do
  if e.hasMVar then throwError "Unresolved expression metavariable"
  let ids := (collectFVars {} e).fvarIds
  for fid in ids do
    unless xs.contains (.fvar fid) do throwError "Expression escapes its source context"
  return (List.range xs.size).toArray.filter fun i => ids.contains xs[i]!.fvarId!

/-- Dependencies of the proof AND claim, closed under local types and let values.
This is sufficient syntactic support, not mathematical hypothesis minimization. -/
def dependencies (e typ : Expr) (xs : Array Expr) : MetaM (Array Nat) := do
  let mut needed := (← support e xs) ++ (← support typ xs)
  for i in (List.range xs.size).reverse do
    if needed.contains i then
      let decl ← xs[i]!.fvarId!.getDecl
      let uses ← support decl.type (xs.extract 0 i)
      needed := needed ++ uses
      if let some value := (decl.value? (allowNondep := true)) then
        needed := needed ++ (← support value (xs.extract 0 i))
  return (List.range xs.size).toArray.filter needed.contains

/-- Close selected binders without promoting a let-bound fact to a hypothesis. -/
def close (e typ : Expr) (xs : Array Expr) (needed : Array Nat) : MetaM (Expr × Expr) := do
  let selected := needed.map fun i => xs[i]!
  let ct ← mkForallFVars selected typ (usedLetOnly := false) (generalizeNondepLet := false)
  let cv ← mkLambdaFVars selected e (usedLetOnly := false) (generalizeNondepLet := false)
  if ct.hasFVar || cv.hasFVar || ct.hasLooseBVars || cv.hasLooseBVars then
    throwError "Incomplete dependency closure"
  return (ct, cv)

/-- Same constructor-DAG wire format as KernelExport, but do not merge
alpha-equivalent nodes with different labels or binder annotations. -/
private partial def intern (e : Expr) : M Nat := do
  let e := e.consumeMData
  if let some i := (← get).seen[(⟨e⟩ : ExprStructEq)]? then return i
  if (← get).exprs.size ≥ 250000 then throwError "Expression budget exceeded"
  let j ← match e with
    | .bvar i => pure <| obj [("tag", toJson "bvar"), ("index", toJson i)]
    | .fvar _ => throwError "Unabstracted local variable"
    | .mvar _ => throwError "Unresolved expression metavariable"
    | .sort u => pure <| obj [("tag", toJson "sort"), ("level", ProofReaderKernel.levelJson u)]
    | .const n us => pure <| obj [("tag", toJson "const"), ("name", ProofReaderKernel.nameJson n), ("levels", toJson (us.map ProofReaderKernel.levelJson))]
    | .app f a => do
      let f ← intern f
      let a ← intern a
      pure <| obj [("tag", toJson "app"), ("fn", toJson f), ("arg", toJson a)]
    | .lam n d b bi | .forallE n d b bi => do
      let d ← intern d
      let b ← intern b
      pure <| obj [("tag", toJson (if e.isLambda then "lam" else "forall")),
        ("name", ProofReaderKernel.nameJson n), ("domain", toJson d), ("body", toJson b), ("binder", toJson (ProofReaderKernel.binderString bi))]
    | .letE n t v b nd => do
      let t ← intern t
      let v ← intern v
      let b ← intern b
      pure <| obj [("tag", toJson "let"), ("name", ProofReaderKernel.nameJson n), ("type", toJson t),
        ("value", toJson v), ("body", toJson b), ("nondep", toJson nd)]
    | .lit (.natVal n) => pure <| obj [("tag", toJson "nat"), ("value", toJson (toString n))]
    | .lit (.strVal s) => pure <| obj [("tag", toJson "str"), ("value", toJson s)]
    | .proj n i b => do
      let b ← intern b
      pure <| obj [("tag", toJson "proj"), ("name", ProofReaderKernel.nameJson n), ("index", toJson i), ("of", toJson b)]
    | .mdata _ _ => throwError "Metadata normalization failed"
  let i := (← get).exprs.size
  modify fun s => { s with exprs := s.exprs.push j, seen := s.seen.insert ⟨e⟩ i }
  return i

def store (e : Expr) (xs : Array Expr) : M Nat := intern (e.abstract xs)

def localRecord (l : Local) (xs : Array Expr) : M Json := do
  let d ← liftM <| l.expr.fvarId!.getDecl
  let ty ← store d.type xs
  let value ← match (d.value? (allowNondep := true)) with
    | some v => toJson <$> store v xs
    | none => pure Json.null
  return obj [("path", toJson l.path), ("kind", toJson l.kind),
    ("name", ProofReaderKernel.nameJson d.userName),
    ("binder", toJson (ProofReaderKernel.binderString d.binderInfo)),
    ("type", toJson ty), ("value", value),
    ("nondep", if (d.value? (allowNondep := true)).isSome then toJson d.isNondep else Json.null)]

def applicationRecord (e : Expr) (path : Path) (xs : Array Expr) : M Json := do
  if !e.isApp then return Json.null
  let head := e.getAppFn
  let args := e.getAppArgs
  let headType ← store (← liftM <| inferType head) xs
  let headPath := path ++ Array.replicate args.size 0
  let constant := match head with
    | .const n _ => ProofReaderKernel.nameJson n
    | _ => Json.null
  let localRef : Json ← if head.isFVar then do
    let used ← liftM <| support head xs
    pure (toJson used[0]!)
  else pure Json.null
  let mut rows : Array Json := #[]
  for k in [:args.size] do
    let arg := args[k]!
    let typ ← liftM <| inferType arg
    let proof ← liftM <| isProp typ
    let ty ← store typ xs
    let value ← if proof then pure Json.null else toJson <$> store arg xs
    rows := rows.push <| obj [("index", toJson k),
      ("path", toJson ((path ++ Array.replicate (args.size-k-1) 0).push 1)),
      ("is_proof", toJson proof), ("type", toJson ty), ("value", value)]
  return obj [("head_path", toJson headPath), ("head_type", toJson headType),
    ("constant", constant), ("local", localRef), ("arguments", toJson rows)]

def frameRecord (path : Path) (e : Expr) (locals : Array Local)
    (declaredType : Option Expr := none) : M Json := do
  let xs := vars locals
  let typ ← match declaredType with
    | some typ => pure typ
    | none => liftM <| inferType e
  unless ← liftM <| isProp typ do throwError "Selected occurrence is not a proof"
  let mut context : Array Json := #[]
  for k in [:locals.size] do
    context := context.push (← localRecord locals[k]! (xs.extract 0 k))
  let ty ← store typ xs
  let directTerm ← liftM <| support e xs
  let directType ← liftM <| support typ xs
  let needed ← liftM <| dependencies e typ xs
  let (closedType, _) ← liftM <| close e typ xs needed
  let lifted ← store closedType #[]
  let application ← applicationRecord e path xs
  let reference := if e.isFVar then toJson directTerm[0]! else Json.null
  return obj [("path", toJson path), ("context", toJson context), ("type", toJson ty),
    ("term_kind", toJson e.ctorName), ("reference", reference),
    ("proof_support", toJson directTerm), ("claim_support", toJson directType),
    ("required_context", toJson needed), ("lifted_type", toJson lifted),
    ("application", application),
    ("display", obj [("claim", toJson (← liftM <| pp typ)),
                     ("lifted", toJson (← liftM <| pp closedType))])]

def source (n : Name) : MetaM (ConstantInfo × Expr × Array Name) := do
  let info ← getConstInfo n
  let value ← match info with
    | .thmInfo v => pure v.value
    | .defnInfo v => pure v.value
    | .opaqueInfo v => pure v.value
    | _ => throwError "Expected a declaration with a proof body"
  unless ← isProp info.type do throwError "Expected a proof-valued declaration"
  let axioms ← collectAxioms n
  unless axioms.all (fun a => #[`propext, `Classical.choice, `Quot.sound].contains a) do
    throwError "Disallowed source axiom"
  return (info, value, axioms)

def checkPaths (paths : Array Path) : MetaM Unit := do
  unless 0 < paths.size && paths.size ≤ 1000 do throwError "Invalid requested path inventory"
  let mut seen : Array Path := #[]
  for p in paths do
    if p.size > 512 || seen.contains p then throwError "Invalid or duplicate requested path"
    seen := seen.push p

def exportOne (n : Name) (paths : Array Path) : MetaM Json := do
  checkPaths paths
  let (info, value, axioms) ← source n
  let (statement, init) ← (store info.type #[]).run {}
  let mut state := init
  let mut frames : Array Json := #[]
  for path in paths do
    let (record, next) ← withSourceAt value path.toList #[] #[] fun e ctx =>
      (frameRecord path e ctx (if path.isEmpty then some info.type else none)).run state
    frames := frames.push record
    state := next
  return obj [("schema", toJson "leanglish.source-expressions/v1"),
    ("name", ProofReaderKernel.nameJson n), ("lean_version", toJson Lean.versionString),
    ("levels", toJson (info.levelParams.map ProofReaderKernel.nameJson)),
    ("axioms", toJson (axioms.map Name.toString)), ("statement", toJson statement),
    ("exprs", toJson state.exprs), ("frames", toJson frames)]

/- Replay does not trust exported types, dependencies, or role classifications. -/
namespace Replay
abbrev J := Except String

def liftJ {α : Type} : J α → MetaM α
  | .ok a => pure a
  | .error msg => throwError "Invalid expression record: {msg}"

def field (j : Json) (s : String) : MetaM Json := liftJ (j.getObjVal? s)
def arr (j : Json) : MetaM (Array Json) := liftJ j.getArr?
def num (j : Json) : MetaM Nat := liftJ j.getNat?
def str (j : Json) : MetaM String := liftJ j.getStr?
def nums (j : Json) : MetaM (Array Nat) := do (← arr j).mapM num

def fields (j : Json) (names : List String) : MetaM Unit := do
  let o ← liftJ j.getObj?
  unless o.size == names.length && names.all (fun k => (j.getObjVal? k).isOk) do
    throwError "Unexpected or missing expression-record fields"

def getExpr (es : Array Expr) (j : Json) : MetaM Expr :=
  liftJ (ProofReaderJsonReplay.ref es j)

def equalExpr (es : Array Expr) (j : Json) (actual : Expr) : MetaM Unit := do
  unless Expr.equal (← getExpr es j) (ProofReaderJsonReplay.erase actual) do
    throwError "Source expression identity mismatch"

def equalJson (expected actual : Json) (message : String) : MetaM Unit := do
  unless expected == actual do throwError "{message}"

def checkContext (es : Array Expr) (record : Json) (locals : Array Local) : MetaM Unit := do
  let rows ← arr record
  unless rows.size == locals.size do throwError "Source context length mismatch"
  let xs := vars locals
  for k in [:locals.size] do
    let row := rows[k]!
    fields row ["path", "kind", "name", "binder", "type", "value", "nondep"]
    let binding := locals[k]!
    let decl ← binding.expr.fvarId!.getDecl
    equalJson (← field row "path") (toJson binding.path) "Source binder identity mismatch"
    equalJson (← field row "kind") (toJson binding.kind) "Source binder kind mismatch"
    equalJson (← field row "name") (ProofReaderKernel.nameJson decl.userName) "Source binder label mismatch"
    equalJson (← field row "binder") (toJson (ProofReaderKernel.binderString decl.binderInfo)) "Source binder annotation mismatch"
    equalExpr es (← field row "type") (decl.type.abstract (xs.extract 0 k))
    match (decl.value? (allowNondep := true)) with
    | some v => equalExpr es (← field row "value") (v.abstract (xs.extract 0 k))
    | none => equalJson (← field row "value") Json.null "Unexpected local definition"
    equalJson (← field row "nondep") (if (decl.value? (allowNondep := true)).isSome then toJson decl.isNondep else Json.null) "Let dependency flag mismatch"

def kernelCheck (levels : List Name) (xs : Array Expr) (e typ : Expr) : MetaM Unit := do
  let ct ← mkForallFVars xs typ (usedLetOnly := false) (generalizeNondepLet := false)
  let cv ← mkLambdaFVars xs e (usedLetOnly := false) (generalizeNondepLet := false)
  if ct.hasFVar || cv.hasFVar || ct.hasLooseBVars || cv.hasLooseBVars then
    throwError "Kernel judgement is not closed"
  let n ← mkFreshUserName `SourceExpressionCheck
  -- Wait for the kernel before reporting success. On either outcome discard
  -- the auxiliary declaration, including addDecl's recovery axiom on failure.
  withoutModifyingEnv <| withOptions (fun o =>
      (o.setBool `debug.skipKernelTC false).setBool `Elab.async false) do
    if ← isProp ct then
      addDecl <| .thmDecl { name := n, levelParams := levels, type := ct, value := cv }
    else
      addDecl <| .defnDecl { name := n, levelParams := levels, type := ct, value := cv, hints := .abbrev, safety := .safe }

def checkApplication (es : Array Expr) (record : Json) (e : Expr) (path : Path)
    (xs : Array Expr) (levels : List Name) : MetaM Nat := do
  if !e.isApp then
    equalJson record Json.null "Unexpected application"
    return 0
  fields record ["head_path", "head_type", "constant", "local", "arguments"]
  let head := e.getAppFn
  let args := e.getAppArgs
  equalJson (← field record "head_path") (toJson (path ++ Array.replicate args.size 0)) "Application head path mismatch"
  let ht ← inferType head
  equalExpr es (← field record "head_type") (ht.abstract xs)
  kernelCheck levels xs head ht
  equalJson (← field record "constant")
    (match head with | .const n _ => ProofReaderKernel.nameJson n | _ => Json.null)
    "Application constant mismatch"
  let localRef : Json ← if head.isFVar then do
    let used ← support head xs
    pure (toJson used[0]!)
  else pure Json.null
  equalJson (← field record "local") localRef "Application local identity mismatch"
  let rows ← arr (← field record "arguments")
  unless rows.size == args.size do throwError "Application argument inventory mismatch"
  for k in [:args.size] do
    let row := rows[k]!
    fields row ["index", "path", "is_proof", "type", "value"]
    equalJson (← field row "index") (toJson k) "Application argument order mismatch"
    equalJson (← field row "path") (toJson ((path ++ Array.replicate (args.size-k-1) 0).push 1)) "Application argument path mismatch"
    let a := args[k]!
    let typ ← inferType a
    equalExpr es (← field row "type") (typ.abstract xs)
    let suppliedType := (← getExpr es (← field row "type")).instantiateRev xs
    let proof ← isProp typ
    equalJson (← field row "is_proof") (toJson proof) "Argument proof/data classification mismatch"
    if proof then equalJson (← field row "value") Json.null "Proof body must remain source-bound"
    else equalExpr es (← field row "value") (a.abstract xs)
    kernelCheck levels xs a suppliedType
  return args.size + 1

def checkFrame (es : Array Expr) (record : Json) (e : Expr) (path : Path)
    (locals : Array Local) (levels : List Name) (declaredType : Option Expr := none) : MetaM Nat := do
  fields record ["path", "context", "type", "term_kind", "reference", "proof_support",
    "claim_support", "required_context", "lifted_type", "application", "display"]
  equalJson (← field record "path") (toJson path) "Requested source path mismatch"
  checkContext es (← field record "context") locals
  let xs := vars locals
  let typ ← match declaredType with
    | some typ => pure typ
    | none => inferType e
  unless ← isProp typ do throwError "Selected occurrence is not a proof"
  equalExpr es (← field record "type") (typ.abstract xs)
  equalJson (← field record "term_kind") (toJson e.ctorName) "Source term kind mismatch"
  let direct ← support e xs
  equalJson (← field record "proof_support") (toJson direct) "Source proof dependencies mismatch"
  equalJson (← field record "claim_support") (toJson (← support typ xs)) "Source claim dependencies mismatch"
  equalJson (← field record "reference") (if e.isFVar then toJson direct[0]! else Json.null) "Local reference identity mismatch"
  let needed ← dependencies e typ xs
  equalJson (← field record "required_context") (toJson needed) "Dependency closure mismatch"
  let suppliedType := (← getExpr es (← field record "type")).instantiateRev xs
  kernelCheck levels xs e suppliedType
  let (ct, cv) ← close e typ xs needed
  equalExpr es (← field record "lifted_type") ct
  -- The closed lemma uses the decoded claimed type, not just the inferred one.
  kernelCheck levels #[] cv (← getExpr es (← field record "lifted_type"))
  let shown ← field record "display"
  fields shown ["claim", "lifted"]
  equalJson (← field shown "claim") (toJson (← pp typ)) "Claim display mismatch"
  equalJson (← field shown "lifted") (toJson (← pp ct)) "Lifted display mismatch"
  return 2 + (← checkApplication es (← field record "application") e path xs levels)

/-- Decode only the shared expression wire format; no truth is inferred here. -/
def decode (record : Json) : MetaM (Array Expr) := do
  let raw ← arr (← field record "exprs")
  unless 0 < raw.size && raw.size ≤ 250000 do throwError "Expression node budget exceeded"
  let mut es : Array Expr := #[]
  for node in raw do
    let tag ← str (← field node "tag")
    let keys ← match tag with
      | "bvar" => pure ["tag", "index"]
      | "sort" => pure ["tag", "level"]
      | "const" => pure ["tag", "name", "levels"]
      | "app" => pure ["tag", "fn", "arg"]
      | "lam" | "forall" => pure ["tag", "name", "domain", "body", "binder"]
      | "let" => pure ["tag", "name", "type", "value", "body", "nondep"]
      | "nat" | "str" => pure ["tag", "value"]
      | "proj" => pure ["tag", "name", "index", "of"]
      | _ => throwError "Unknown expression constructor"
    fields node keys
    es := es.push (← liftJ <| ProofReaderJsonReplay.expr es node)
  return es

/-- The expected target and path inventory are supplied separately from the record. -/
def verify (record : Json) (target : Name) (paths : Array Path) : MetaM Nat := do
  checkPaths paths
  fields record ["schema", "name", "lean_version", "levels", "axioms", "statement", "exprs", "frames"]
  equalJson (← field record "schema") (toJson "leanglish.source-expressions/v1") "Expression schema mismatch"
  equalJson (← field record "name") (ProofReaderKernel.nameJson target) "Source declaration mismatch"
  equalJson (← field record "lean_version") (toJson Lean.versionString) "Toolchain mismatch"
  let (info, value, axioms) ← source target
  equalJson (← field record "levels") (toJson (info.levelParams.map ProofReaderKernel.nameJson)) "Universe inventory mismatch"
  equalJson (← field record "axioms") (toJson (axioms.map Name.toString)) "Axiom inventory mismatch"
  let es ← decode record
  equalExpr es (← field record "statement") info.type
  kernelCheck info.levelParams #[] value (← getExpr es (← field record "statement"))
  let frames ← arr (← field record "frames")
  unless frames.size == paths.size do throwError "Requested frame inventory mismatch"
  let mut checked := 1
  for i in [:paths.size] do
    checked := checked + (← withSourceAt value paths[i]!.toList #[] #[] fun e ctx =>
      checkFrame es frames[i]! e paths[i]! ctx info.levelParams
        (if paths[i]!.isEmpty then some info.type else none))
  return checked
end Replay

/-- Install a dependency-closed source lemma and check its use back in the
original context. The supplied type is compared structurally before installation.
The environment changes only after both kernel checks have succeeded. -/
def extractAt (target : Name) (path : Path) (destination : Name)
    (expectedType : Expr) : MetaM Json := do
  checkPaths #[path]
  if (← getEnv).contains destination then throwError "Extraction name already exists"
  let (result, nextEnv) ← withoutModifyingEnv' do
    let (info, value, _) ← source target
    withSourceAt value path.toList #[] #[] fun e ctx => do
      let xs := vars ctx
      let typ ← if path.isEmpty then pure info.type else inferType e
      unless ← isProp typ do throwError "Selected occurrence is not a proof"
      let needed ← dependencies e typ xs
      let (ct, cv) ← close e typ xs needed
      unless Expr.equal expectedType (ProofReaderJsonReplay.erase ct) do
        throwError "Extracted lemma type mismatch"
      withOptions (fun o => (o.setBool `debug.skipKernelTC false).setBool `Elab.async false) do
        addDecl <| .thmDecl { name := destination, levelParams := info.levelParams, type := expectedType, value := cv }
      let mut args : Array Expr := #[]
      for k in needed do
        let decl ← xs[k]!.fvarId!.getDecl
        if (decl.value? (allowNondep := true)).isNone then args := args.push xs[k]!
      let use := mkAppN (mkConst destination (info.levelParams.map Level.param)) args
      Replay.kernelCheck info.levelParams xs use typ
      return obj [("source", ProofReaderKernel.nameJson target), ("path",toJson path),
        ("name",ProofReaderKernel.nameJson destination), ("required_context",toJson needed),
        ("signature",toJson (← pp ct))]
  setEnv nextEnv
  return result

end ProofReader.SourceExpressions
