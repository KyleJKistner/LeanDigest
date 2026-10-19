import EquationEnglish
import SourceCancellation

/-!
# Source-bound equation chains

The importer is a trusted metaprogram. It preserves proof occurrences and opens
only their real contexts, then synchronously kernel-checks every displayed link
and the literal English String and bytes. No new proof search supplies a link.
-/
open Lean Meta Elab Command
namespace ProofReader.SourceEquations
open ArithmeticEnglish EquationEnglish
open SourceCancellation (eraseMetadata rawPath withSourceAt vars quoteTerm interpretation checkedDecl)

structure Bindings where
  values : Array Expr
  present : Array Bool

/-- A missing variable is not made available by its placeholder interpretation.
Only present source fvars/lets can be reified into a printed variable. -/
def bindings (xs : Array Expr) (scalarType : Expr) : MetaM Bindings := do
  let zero ← mkNumeral scalarType 0
  let mut values := #[]
  let mut present := #[]
  for v in vars do
    let label := String.singleton v.char
    let mut candidates := #[]
    for x in xs do
      let decl ← x.fvarId!.getDecl
      if decl.userName.eraseMacroScopes.toString == label then candidates := candidates.push x
    if candidates.size > 1 then throwError "Ambiguous equation variable: {label}"
    if candidates.isEmpty then
      values := values.push zero
      present := present.push false
    else
      let x := candidates[0]!
      unless ← isDefEq (← inferType x) scalarType do throwError "Equation variable type mismatch"
      values := values.push x
      present := present.push true
  return ⟨values, present⟩

/-- Only direct source locals and their exact let values receive these labels.
There is no unrestricted normalizer or pretty-printed-expression importer. -/
partial def reify (e : Expr) (b : Bindings) : MetaM ArithmeticEnglish.Term := do
  let e := e.consumeMData
  for i in [:vars.size] do
    if b.present[i]! then
      let x := b.values[i]!
      if eraseMetadata e == eraseMetadata x then return .var vars[i]!
      let decl ← x.fvarId!.getDecl
      if let some value := decl.value? then
        if eraseMetadata e == eraseMetadata value then return .var vars[i]!
  let args := e.getAppArgs
  let head := e.getAppFn
  if head.isConstOf ``OfNat.ofNat && args.size == 3 then
    if let .lit (.natVal n) := args[1]! then
      match n with
      | 0 => return .zero
      | 1 => return .one
      | _ => throwError "Unsupported equation numeral"
  if args.size == 6 then
    if head.isConstOf ``HAdd.hAdd then return .add (← reify args[4]! b) (← reify args[5]! b)
    if head.isConstOf ``HMul.hMul then return .mul (← reify args[4]! b) (← reify args[5]! b)
    if head.isConstOf ``HSub.hSub then return .sub (← reify args[4]! b) (← reify args[5]! b)
  throwError "Unsupported equation expression: {e}"

def quoteChain : Chain → Expr
  | .pair a b => mkApp2 (mkConst ``Chain.pair) (quoteTerm a) (quoteTerm b)
  | .cons a rest => mkApp2 (mkConst ``Chain.cons) (quoteTerm a) (quoteChain rest)

structure Link where
  proof : Expr
  path : List Nat
  deriving Inhabited

/-- Flatten only explicit equality transitivity nodes, in source order. -/
partial def links (node : Expr) (path : List Nat) (budget : Nat) : MetaM (Array Link) := do
  if budget == 0 then throwError "Equation traversal budget exceeded"
  let node := node.consumeMData
  let head := node.getAppFn
  let args := node.getAppArgs
  if head.isConstOf ``Eq.trans then
    unless args.size == 6 do throwError "Unsupported Eq.trans arity"
    return (← links args[4]! (path ++ [0, 1]) (budget - 1)) ++
      (← links args[5]! (path ++ [1]) (budget - 1))
  if head.isConstOf ``Trans.trans then
    unless args.size == 12 && args[6]!.getAppFn.isConstOf `instTransEq do
      throwError "Unsupported transitivity instance"
    return (← links args[10]! (path ++ [0, 1]) (budget - 1)) ++
      (← links args[11]! (path ++ [1]) (budget - 1))
  return #[⟨node, path⟩]

/-- Independent closed-expression pass. Every original transitivity leaf must
occur once, in order, in the proposed chain. Endpoint equality is not enough. -/
def expectedLeafPaths (node : Expr) (path : List Nat) : Nat → Except String (List (List Nat))
  | 0 => .error "Equation inventory budget exceeded"
  | fuel + 1 => do
      let args := node.getAppArgs
      let head := node.getAppFn
      if head.isConstOf ``Eq.trans then
        if args.size != 6 then throw "Unsupported raw Eq.trans arity"
        return (← expectedLeafPaths args[4]! (path ++ [0, 1]) fuel) ++
          (← expectedLeafPaths args[5]! (path ++ [1]) fuel)
      else if head.isConstOf ``Trans.trans then
        if args.size != 12 || !args[6]!.getAppFn.isConstOf `instTransEq then
          throw "Unsupported raw transitivity instance"
        return (← expectedLeafPaths args[10]! (path ++ [0, 1]) fuel) ++
          (← expectedLeafPaths args[11]! (path ++ [1]) fuel)
      else return [path]

def equality (proof : Expr) : MetaM (Expr × Expr × Expr) := do
  let type ← inferType proof
  unless type.getAppFn.isConstOf ``Eq && type.getAppArgs.size == 3 do
    throwError "Expected a source equality"
  let a := type.getAppArgs
  return (a[0]!, a[1]!, a[2]!)

/-- Preserve the source expression up to explicit, in-scope let abbreviations.
The kernel equality checks the denotation independently of the structural test. -/
def checkTerm (name : Name) (levels : List Name) (xs : Array Expr)
    (env source : Expr) (term : ArithmeticEnglish.Term) (b : Bindings) : MetaM Unit := do
  unless (← reify source b) == term do throwError "Equation expression alignment mismatch"
  let interpreted ← mkAppM ``ArithmeticEnglish.Term.eval #[env, quoteTerm term]
  checkedDecl name levels xs (← mkEq interpreted source) (← mkEqRefl source)

def checkedAxioms (name : Name) : MetaM (Array Name) := do
  let ax ← collectAxioms name
  unless ax.all (fun n => #[`propext, `Classical.choice, `Quot.sound].contains n) do
    throwError "Unpermitted equation certificate axiom"
  return ax

/-- A chain consists of precisely the checked adjacent source links. -/
def assemble (terms : Array ArithmeticEnglish.Term) (proofs : Array Expr) : MetaM (Chain × Expr) := do
  unless proofs.size > 0 && terms.size == proofs.size + 1 do throwError "Empty or incomplete equation chain"
  let mut chain := Chain.pair terms[terms.size - 2]! terms[terms.size - 1]!
  let mut proof := proofs[proofs.size - 1]!
  for j in [:proofs.size - 1] do
    let i := proofs.size - j - 2
    chain := .cons terms[i]! chain
    proof ← mkAppM ``And.intro #[proofs[i]!, proof]
  return (chain, proof)

def checkOne (target : Name) (original : Expr) (levels : List Name)
    (path : List Nat) (index : Nat) (variant : String) : MetaM Json := do
  withSourceAt original path #[] fun node xs => do
    let raw ← match rawPath (eraseMetadata original) path with
      | .ok v => pure v | .error err => throwError "{err}"
    let proposed ← if variant == "proof-replacement" then mkAppM ``id #[node] else pure node
    unless raw == eraseMetadata (proposed.abstract xs) do throwError "Original equation occurrence mismatch"
    let (scalar, _, _) ← equality node
    let b ← bindings xs scalar
    let envValues := if variant == "wrong-label-map" then b.values.set! 0 b.values[1]! else b.values
    let env ← interpretation scalar envValues (variant == "wrong-operation")
    let base := target.str "equationText" |>.num index
    checkedDecl (base.str "source") levels (if variant == "scope-escape" then xs.pop else xs)
      (← inferType node) node
    let allLinks ← links node path 128
    let selected := if variant == "drop-link" then allLinks.pop
      else if variant == "reverse-links" then allLinks.reverse
      else if variant == "duplicate-link" then allLinks ++ #[allLinks[0]!]
      else allLinks
    let expected ← match expectedLeafPaths raw path 128 with
      | .ok r => pure r | .error e => throwError "{e}"
    unless selected.toList.map Link.path == expected do throwError "Original equation link inventory mismatch"
    let mut terms := #[]
    let mut proofs := #[]
    let mut records := #[]
    for i in [:selected.size] do
      let link := selected[i]!
      let originalLink ← match rawPath (eraseMetadata original) link.path with
        | .ok v => pure v | .error err => throwError "{err}"
      unless originalLink == eraseMetadata (link.proof.abstract xs) do
        throwError "Original link occurrence mismatch"
      let (linkScalar, left, right) ← equality link.proof
      unless ← isDefEq scalar linkScalar do throwError "Equation chain changes scalar type"
      let lt ← reify left b
      let rt ← reify right b
      let lb := base.str "link" |>.num i
      checkTerm (lb.str "left") levels xs env left lt b
      checkTerm (lb.str "right") levels xs env right rt b
      if i == 0 then terms := terms.push lt
      else unless terms.back! == lt do throwError "Nonadjacent source equations"
      terms := terms.push rt
      let ltExpr ← mkAppM ``ArithmeticEnglish.Term.eval #[env, quoteTerm lt]
      let rtExpr ← mkAppM ``ArithmeticEnglish.Term.eval #[env, quoteTerm rt]
      checkedDecl (lb.str "source") levels xs (← mkEq ltExpr rtExpr) link.proof
      let _ ← checkedAxioms (lb.str "source")
      proofs := proofs.push link.proof
      records := records.push <| Json.mkObj [
        ("index", toJson i), ("path", toJson link.path),
        ("source_head", toJson (if let .const n _ := link.proof.getAppFn then n.toString else "local hypothesis")),
        ("statement", toJson (← ppExpr (← inferType link.proof)).pretty)]
    let (chain, proof) ← assemble terms proofs
    let candidate := if variant == "wrong-chain" then Chain.pair .zero .one else chain
    let proofType ← mkAppM ``Chain.Holds #[env, quoteChain candidate]
    checkedDecl (base.str "links") levels xs
      (if variant == "kernel-claim-tamper" then mkConst ``False else proofType) proof
    let text := if variant == "text-tamper" then chain.render ++ " Thus 0 = 1." else chain.render
    unless EquationEnglish.read text == some chain do throwError "Equation text alignment mismatch"
    let literal := mkStrLit text
    let cert ← mkAppM ``EquationEnglish.certify #[env, quoteChain chain, proof]
    checkedDecl (base.str "english") levels xs (← mkAppM ``EquationEnglish.TextMeans #[env, literal]) cert
    let byteCert ← mkAppM ``EquationEnglish.certifyBytes #[env, quoteChain chain, proof]
    let literalBytes ← mkAppM ``String.toUTF8 #[literal]
    checkedDecl (base.str "utf8") levels xs (← mkAppM ``EquationEnglish.BytesMean #[env, literalBytes]) byteCert
    let axioms ← checkedAxioms (base.str "english")
    let _ ← checkedAxioms (base.str "utf8")
    let mut context := #[]
    for position in [:xs.size] do
      let x := xs[position]!
      let decl ← x.fvarId!.getDecl
      let value ← match decl.value? with
        | some v => pure (toJson (← ppExpr v).pretty)
        | none => pure Json.null
      context := context.push <| Json.mkObj [
        ("name", toJson decl.userName.eraseMacroScopes.toString),
        ("type", toJson (← ppExpr decl.type).pretty), ("value", value),
        ("binder_index", toJson position)]
    return Json.mkObj [
      ("index", toJson index), ("path", toJson path), ("text", toJson text),
      ("utf8", toJson (text.toUTF8.data.toList.map UInt8.toNat)),
      ("context", Json.arr context), ("links", Json.arr records),
      ("link_count", toJson selected.size), ("term_count", toJson chain.length),
      ("text_theorem", toJson (base.str "english").toString),
      ("bytes_theorem", toJson (base.str "utf8").toString),
      ("axioms", toJson (axioms.map Name.toString)),
      ("source_ast_identity_checked", toJson true),
      ("literal_string_kernel_checked", toJson true),
      ("all_adjacent_equalities_checked", toJson true)]

elab "#source_equations " target:str " paths " spec:str " output " out:str " mode " variant:str : command => do
  unless #["ok", "proof-replacement", "wrong-label-map", "wrong-operation", "wrong-chain",
      "text-tamper", "kernel-claim-tamper", "scope-escape", "drop-link",
      "reverse-links", "duplicate-link"].contains variant.getString do
    throwError "Unknown equation-check variant"
  let input ← IO.FS.readFile spec.getString
  let rows ← match Json.parse input >>= Json.getArr? with
    | .ok r => pure r | .error e => throwError "{e}"
  unless rows.size == 10 do throwError "Expected ten original equation paths"
  let result ← liftTermElabM do
    let target := target.getString.toName
    let .thmInfo declaration ← getConstInfo target | throwError "Equation target must be a theorem"
    let _ ← checkedAxioms target
    let mut seen : Array (List Nat) := #[]
    let mut records := #[]
    for i in [:rows.size] do
      let path ← match (fromJson? rows[i]! : Except String (List Nat)) with
        | .ok p => pure p | .error e => throwError "{e}"
      if seen.contains path then throwError "Duplicate equation source path"
      seen := seen.push path
      records := records.push (← checkOne target declaration.value declaration.levelParams path i variant.getString)
    return records
  IO.FS.writeFile out.getString (Json.arr result |>.pretty)
  logInfo "SOURCE_EQUATIONS_CHECKED:10"
end ProofReader.SourceEquations
