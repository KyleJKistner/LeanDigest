import ArithmeticEnglish
import Lean.Util.CollectAxioms

/-!
# Source-bound cancellation import

This is an audited-algorithm boundary, not a mechanized proof of Lean's extractor.
It submits the exact source proof and concrete rendered-text meaning as closed
kernel-checked declarations. It compares proof syntax at original occurrence
paths; proof irrelevance is not used as a source-identity check.
-/
open Lean Meta Elab Command
namespace ProofReader.SourceCancellation
open ArithmeticEnglish

partial def eraseMetadata : Expr → Expr
  | .mdata _ b => eraseMetadata b
  | .app f a => .app (eraseMetadata f) (eraseMetadata a)
  | .lam n d b bi => .lam n (eraseMetadata d) (eraseMetadata b) bi
  | .forallE n d b bi => .forallE n (eraseMetadata d) (eraseMetadata b) bi
  | .letE n t v b nd => .letE n (eraseMetadata t) (eraseMetadata v) (eraseMetadata b) nd
  | .proj n i b => .proj n i (eraseMetadata b)
  | e => e

/-- Independent traversal of the original closed expression for identity checks. -/
def rawPath : Expr → List Nat → Except String Expr
  | e, [] => .ok e
  | .app f _, 0 :: ks => rawPath f ks
  | .app _ a, 1 :: ks => rawPath a ks
  | .lam _ d _ _, 0 :: ks | .forallE _ d _ _, 0 :: ks => rawPath d ks
  | .lam _ _ b _, 1 :: ks | .forallE _ _ b _, 1 :: ks => rawPath b ks
  | .letE _ t _ _ _, 0 :: ks => rawPath t ks
  | .letE _ _ v _ _, 1 :: ks => rawPath v ks
  | .letE _ _ _ b _, 2 :: ks => rawPath b ks
  | .proj _ _ b, 0 :: ks => rawPath b ks
  | _, _ => .error "Invalid original proof path"

/-- Open only the binders along the selected source occurrence. -/
partial def withSourceAt (e : Expr) (path : List Nat) (xs : Array Expr)
    (action : Expr → Array Expr → MetaM Json) : MetaM Json := do
  let e := e.consumeMData
  match path, e with
  | [], _ => action e xs
  | 0 :: ks, .app f _ => withSourceAt f ks xs action
  | 1 :: ks, .app _ a => withSourceAt a ks xs action
  | 1 :: ks, .lam n d b bi =>
      withLocalDecl n bi d fun x => withSourceAt (b.instantiate1 x) ks (xs.push x) action
  | 2 :: ks, .letE n t v b nd =>
      withLetDecl n t v (nondep := nd) fun x =>
        withSourceAt (b.instantiate1 x) ks (xs.push x) action
  | 1 :: ks, .letE _ _ v _ _ => withSourceAt v ks xs action
  | _, _ => throwError "Unsupported source traversal: only proof bodies and arguments are allowed"

def vars : Array Variable := #[.x, .y, .z, .g, .a, .d, .r, .s]

def quoteVar (v : Variable) : Expr :=
  mkConst <| (``Variable).str (String.singleton v.char)

def quoteTerm : ArithmeticEnglish.Term → Expr
  | .var v => mkApp (mkConst ``ArithmeticEnglish.Term.var) (quoteVar v)
  | .zero => mkConst ``ArithmeticEnglish.Term.zero
  | .one => mkConst ``ArithmeticEnglish.Term.one
  | .add p q => mkApp2 (mkConst ``ArithmeticEnglish.Term.add) (quoteTerm p) (quoteTerm q)
  | .mul p q => mkApp2 (mkConst ``ArithmeticEnglish.Term.mul) (quoteTerm p) (quoteTerm q)
  | .sub p q => mkApp2 (mkConst ``ArithmeticEnglish.Term.sub) (quoteTerm p) (quoteTerm q)

def quoteCancellation (c : Cancellation) : Expr :=
  mkApp3 (mkConst ``Cancellation.mk) (quoteTerm c.factor) (quoteTerm c.left) (quoteTerm c.right)

/-- Names select a finite labeling; semantic identity is the actual fvar. -/
def bindings (xs : Array Expr) (scalarType : Expr) : MetaM (Array Expr) := do
  vars.mapM fun v => do
    let label := String.singleton v.char
    let mut candidates := #[]
    for x in xs do
      let decl ← x.fvarId!.getDecl
      if decl.userName.eraseMacroScopes.toString == label then candidates := candidates.push x
    unless candidates.size == 1 do throwError "Missing or ambiguous source variable: {label}"
    let x := candidates[0]!
    unless ← isDefEq (← inferType x) scalarType do throwError "Source variable has the wrong type: {label}"
    return x

/-- No arbitrary strings or opaque expressions enter the arithmetic grammar. -/
partial def reify (e : Expr) (values : Array Expr) : MetaM ArithmeticEnglish.Term := do
  let e := e.consumeMData
  for i in [:values.size] do
    if e == values[i]! then return .var vars[i]!
  let args := e.getAppArgs
  let head := e.getAppFn
  if head.isConstOf ``OfNat.ofNat && args.size == 3 then
    if let .lit (.natVal n) := args[1]! then
      match n with
      | 0 => return .zero
      | 1 => return .one
      | _ => throwError "Unsupported arithmetic numeral"
  if args.size == 6 then
    let p ← reify args[4]! values
    let q ← reify args[5]! values
    if head.isConstOf ``HAdd.hAdd then return .add p q
    if head.isConstOf ``HMul.hMul then return .mul p q
    if head.isConstOf ``HSub.hSub then return .sub p q
  throwError "Unsupported arithmetic source expression: {e}"

def operation (name : Name) (scalarType : Expr) : MetaM Expr :=
  withLocalDeclD `u scalarType fun u =>
    withLocalDeclD `v scalarType fun v => do
      let body ← mkAppM name #[u, v]
      mkLambdaFVars #[u, v] body

def interpretation (scalarType : Expr) (values : Array Expr) (corruptAdd : Bool := false) : MetaM Expr := do
  let assignment ← mkAppM ``ArithmeticEnglish.assignment values
  let zero ← mkNumeral scalarType 0
  let one ← mkNumeral scalarType 1
  let add ← operation (if corruptAdd then ``HMul.hMul else ``HAdd.hAdd) scalarType
  let mul ← operation ``HMul.hMul scalarType
  let sub ← operation ``HSub.hSub scalarType
  mkAppM ``Interpretation.mk #[assignment, zero, one, add, mul, sub]

/-- Kernel check with no residual metavariables and the exact enclosing binders. -/
def checkedDecl (name : Name) (levels : List Name) (xs : Array Expr)
    (type value : Expr) : MetaM Unit := do
  let type ← instantiateMVars type
  let value ← instantiateMVars value
  if type.hasMVar || value.hasMVar then throwError "Unresolved certificate metavariable"
  let type ← mkForallFVars xs type (usedLetOnly := false)
  let value ← mkLambdaFVars xs value (usedLetOnly := false)
  if type.hasFVar || value.hasFVar then throwError "Escaped source-local binder"
  -- Use the synchronous kernel API: elaborator `addDecl` can defer checking
  -- and recover a failed declaration as an axiom. No record is emitted early.
  let decl := Declaration.thmDecl {name, levelParams := levels, type, value}
  let opts ← getOptions
  let next ← ofExceptKernelException <| (← getEnv).addDeclCore
    (Core.getMaxHeartbeats opts).toUSize (maxRecDepth.get opts).toUSize decl none true
  setEnv next

/-- Strict reconstruction for a cheap precheck. The following kernel equality
remains authoritative. This avoids unfolding unrelated gcd definitions merely
to discover that a proposed multiplication was changed into an addition. -/
def materialize (env : Expr) : ArithmeticEnglish.Term → Expr
  | .var v =>
      let params := env.getAppArgs[1]!.getAppArgs
      let index := vars.toList.idxOf v
      params[index + 1]!
  | .zero => env.getAppArgs[2]!
  | .one => env.getAppArgs[3]!
  | .add p q => (mkApp2 env.getAppArgs[4]! (materialize env p) (materialize env q)).headBeta
  | .mul p q => (mkApp2 env.getAppArgs[5]! (materialize env p) (materialize env q)).headBeta
  | .sub p q => (mkApp2 env.getAppArgs[6]! (materialize env p) (materialize env q)).headBeta

/-- Reification cannot change operations, instances, labels, or scalar values. -/
def checkTerm (name : Name) (levels : List Name) (xs : Array Expr)
    (env source : Expr) (term : ArithmeticEnglish.Term) : MetaM Unit := do
  let interpreted ← mkAppM ``ArithmeticEnglish.Term.eval #[env, quoteTerm term]
  let direct ← instantiateMVars (materialize env term)
  unless eraseMetadata direct == eraseMetadata source do
    throwError "Arithmetic denotation mismatch"
  let eq ← mkEq interpreted source
  checkedDecl name levels xs eq (← mkEqRefl source)

/-- Establish meaning for the concrete literal String, not merely `render c`. -/
def checkOne (target : Name) (original : Expr) (levels : List Name)
    (path : List Nat) (index : Nat) (mode : String) : MetaM Json := do
  withSourceAt original path #[] fun node xs => do
    let node ← if mode == "proof-replacement" then mkAppM ``id #[node] else pure node
    let raw ← match rawPath (eraseMetadata original) path with
      | .ok raw => pure raw
      | .error err => throwError "{err}"
    unless raw == eraseMetadata (node.abstract xs) do
      throwError "Original proof occurrence mismatch"
    unless node.getAppFn.isConstOf `mul_left_cancel₀ && node.getAppArgs.size == 9 do
      throwError "Expected a fully applied source mul_left_cancel₀ node"
    let args := node.getAppArgs
    let values ← bindings xs args[0]!
    let envValues := if mode == "wrong-label-map" then values.set! 4 values[5]! else values
    let env ← interpretation args[0]! envValues (mode == "wrong-operation")
    let factor ← reify args[4]! values
    let left ← reify args[5]! values
    let right ← reify args[6]! values
    let sentence : Cancellation := ⟨factor, left, right⟩
    let base := target.str "sourceText" |>.num index
    checkTerm (base.str "factor") levels xs env args[4]! factor
    checkTerm (base.str "left") levels xs env args[5]! left
    checkTerm (base.str "right") levels xs env args[6]! right
    -- Record a kernel-checked copy of the exact source subterm, not a new proof.
    let nodeType ← inferType node
    checkedDecl (base.str "source") levels xs
      (if mode == "kernel-claim-tamper" then mkConst ``False else nodeType) node
    let law := mkAppN node.getAppFn (args.extract 0 4)
    let nonzero := if mode == "wrong-nonzero" then args[8]! else args[7]!
    let premise := if mode == "wrong-premise" then args[7]! else args[8]!
    let candidate := if mode == "wrong-conclusion" then
      {sentence with right := .zero} else sentence
    let proof ← mkAppM ``certify #[env, quoteCancellation candidate, law, nonzero, premise]
    let text := if mode == "text-tamper" then sentence.render ++ " Therefore 0 = 1." else sentence.render
    unless readCancellation text == some sentence do
      throwError "English sentence alignment mismatch"
    let literal := mkStrLit text
    let textType ← mkAppM ``TextMeans #[env, literal]
    checkedDecl (base.str "english") levels xs textType proof
    let bytesProof ← mkAppM ``certifyBytes #[env, quoteCancellation sentence, law, args[7]!, args[8]!]
    let literalBytes ← mkAppM ``String.toUTF8 #[literal]
    let bytesType ← mkAppM ``BytesMean #[env, literalBytes]
    checkedDecl (base.str "utf8") levels xs bytesType bytesProof
    let ax ← collectAxioms (base.str "english")
    unless ax.all (fun n => #[`propext, `Classical.choice, `Quot.sound].contains n) do
      throwError "Unpermitted axiom in source text certificate: {ax}"
    let mut context := #[]
    for x in xs do
      let decl ← x.fvarId!.getDecl
      context := context.push <| Json.mkObj [("name", toJson decl.userName.eraseMacroScopes.toString),
        ("type", toJson (← ppExpr decl.type).pretty)]
    return Json.mkObj [("index", toJson index), ("path", toJson path),
      ("text", toJson text), ("utf8", toJson (text.toUTF8.data.toList.map UInt8.toNat)), ("context", toJson context),
      ("statement", toJson (← ppExpr (← inferType node)).pretty),
      ("text_theorem", toJson (base.str "english").toString),
      ("bytes_theorem", toJson (base.str "utf8").toString),
      ("axioms", toJson (ax.map Name.toString)),
      ("source_ast_identity_checked", toJson true),
      ("literal_string_kernel_checked", toJson true)]

elab "#source_cancellations " target:str " paths " spec:str " output " out:str " mode " mode:str : command => do
  unless #["ok", "wrong-nonzero", "wrong-premise", "wrong-conclusion", "text-tamper",
      "wrong-label-map", "wrong-operation", "proof-replacement", "kernel-claim-tamper"].contains mode.getString do
    throwError "Unknown source-check mode"
  let specText ← IO.FS.readFile spec.getString
  let json ← match Json.parse specText with
    | .ok j => pure j | .error e => throwError "{e}"
  let rows ← match json.getArr? with
    | .ok j => pure j | .error e => throwError "{e}"
  unless rows.size == 2 do throwError "This integration requires the two expected Bézout cancellations"
  if rows[0]! == rows[1]! then throwError "Duplicate original proof path"
  let result ← liftTermElabM do
    let target := target.getString.toName
    let info ← getConstInfo target
    let .thmInfo declaration := info | throwError "Target must be a theorem"
    let ax ← collectAxioms target
    unless ax.all (fun n => #[`propext, `Classical.choice, `Quot.sound].contains n) do
      throwError "Unpermitted original theorem axiom"
    let mut records := #[]
    for i in [:rows.size] do
      let path ← match (fromJson? rows[i]! : Except String (List Nat)) with
        | .ok p => pure p | .error e => throwError "{e}"
      records := records.push (← checkOne target declaration.value declaration.levelParams path i mode.getString)
    pure records
  IO.FS.writeFile out.getString (Json.arr result |>.pretty)
  logInfo "SOURCE_CANCELLATIONS_CHECKED:2"
end ProofReader.SourceCancellation
