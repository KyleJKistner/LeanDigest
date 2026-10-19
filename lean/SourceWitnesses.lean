import WitnessEnglish
import SourceEquations

/-! # Original witness tuples

Read the four actual `Exists.intro` nodes without searching for alternative
witnesses. Kernel-check the original existence proof, its exact conjunction,
and the formal meaning of the literal sentence and its bytes.
-/
open Lean Meta Elab Command
namespace ProofReader.SourceWitnesses
open ArithmeticEnglish WitnessEnglish
open SourceCancellation (eraseMetadata rawPath withSourceAt vars quoteTerm interpretation checkedDecl)
open SourceEquations (bindings reify checkTerm checkedAxioms)

def quoteFrame (f : Frame) : Expr :=
  mkAppN (mkConst ``Frame.mk) (#[f.x, f.y, f.z, f.a, f.d, f.b, f.c].map quoteTerm)

def checkOne (target : Name) (original : Expr) (levels : List Name)
    (path : List Nat) (index : Nat) (variant : String) : MetaM Json := do
  withSourceAt original path #[] fun node xs => do
    let originalNode ← match rawPath (eraseMetadata original) path with
      | .ok n => pure n | .error e => throwError "{e}"
    let proposed ← if variant == "proof-replacement" then mkAppM ``id #[node] else pure node
    unless originalNode == eraseMetadata (proposed.abstract xs) do throwError "Original witness occurrence mismatch"
    let mut current := node
    let mut values := #[]
    let mut witnessPaths := #[]
    let mut proofPath := path
    let mut scalar := default
    for i in [:4] do
      let args := current.getAppArgs
      unless current.getAppFn.isConstOf ``Exists.intro && args.size == 4 do
        throwError "Expected four explicit source witnesses"
      if i == 0 then scalar := args[0]!
      else unless ← isDefEq scalar args[0]! do throwError "Witness scalar type mismatch"
      values := values.push args[2]!
      witnessPaths := witnessPaths.push (proofPath ++ [0, 1])
      current := args[3]!
      proofPath := proofPath ++ [1]
    let b ← bindings xs scalar
    for i in [:3] do
      unless b.present[i]! do throwError "Missing original frame input"
    let envValues := if variant == "wrong-label-map" then b.values.set! 0 b.values[1]! else b.values
    let env ← interpretation scalar envValues (variant == "wrong-operation")
    let mut terms := #[]
    let base := target.str "witnessText" |>.num index
    for i in [:4] do
      let raw ← match rawPath (eraseMetadata original) witnessPaths[i]! with
        | .ok n => pure n | .error e => throwError "{e}"
      unless raw == eraseMetadata (values[i]!.abstract xs) do throwError "Original witness value mismatch"
      let term ← reify values[i]! b
      checkTerm (base.str "value" |>.num i) levels xs env values[i]! term b
      terms := terms.push term
    let f : Frame := ⟨.var .x, .var .y, .var .z, terms[0]!, terms[1]!, terms[2]!, terms[3]!⟩
    let candidate := if variant == "wrong-witness" then {f with a := .zero}
      else if variant == "swap-witnesses" then {f with b := f.c, c := f.b} else f
    let goal ← mkAppM ``Goal #[env, quoteTerm f.x, quoteTerm f.y, quoteTerm f.z]
    checkedDecl (base.str "existence") levels xs goal node
    let finalRaw ← match rawPath (eraseMetadata original) proofPath with
      | .ok n => pure n | .error e => throwError "{e}"
    unless finalRaw == eraseMetadata (current.abstract xs) do throwError "Original frame conjunction mismatch"
    let holds ← mkAppM ``Frame.Holds #[env, quoteFrame candidate]
    checkedDecl (base.str "products") levels (if variant == "scope-escape" then xs.pop else xs)
      (if variant == "kernel-claim-tamper" then mkConst ``False else holds) current
    let text := if variant == "text-tamper" then f.render ++ " Therefore 0 = 1." else f.render
    unless WitnessEnglish.read text == some f do throwError "Witness text alignment mismatch"
    let literal := mkStrLit text
    let proof ← mkAppM ``WitnessEnglish.certify #[env, quoteFrame f, current]
    checkedDecl (base.str "english") levels xs (← mkAppM ``WitnessEnglish.TextMeans #[env, literal]) proof
    let byteProof ← mkAppM ``WitnessEnglish.certifyBytes #[env, quoteFrame f, current]
    let literalBytes ← mkAppM ``String.toUTF8 #[literal]
    checkedDecl (base.str "utf8") levels xs (← mkAppM ``WitnessEnglish.BytesMean #[env, literalBytes]) byteProof
    let axioms ← checkedAxioms (base.str "english")
    let _ ← checkedAxioms (base.str "utf8")
    let _ ← checkedAxioms (base.str "existence")
    let mut context := #[]
    for i in [:xs.size] do
      let decl ← xs[i]!.fvarId!.getDecl
      let value ← match decl.value? with
        | some v => pure (toJson (← ppExpr v).pretty)
        | none => pure Json.null
      context := context.push <| Json.mkObj [("binder_index", toJson i),
        ("name", toJson decl.userName.eraseMacroScopes.toString),
        ("type", toJson (← ppExpr decl.type).pretty), ("value", value)]
    return Json.mkObj [("index", toJson index), ("path", toJson path),
      ("witness_paths", toJson witnessPaths), ("conjunction_path", toJson proofPath),
      ("text", toJson text), ("utf8", toJson (text.toUTF8.data.toList.map UInt8.toNat)),
      ("context", Json.arr context), ("axioms", toJson (axioms.map Name.toString)),
      ("text_theorem", toJson (base.str "english").toString),
      ("bytes_theorem", toJson (base.str "utf8").toString),
      ("existence_theorem", toJson (base.str "existence").toString),
      ("source_ast_identity_checked", toJson true), ("literal_string_kernel_checked", toJson true),
      ("all_four_witnesses_checked", toJson true)]

elab "#source_witnesses " target:str " paths " spec:str " output " out:str " mode " variant:str : command => do
  unless #["ok", "proof-replacement", "wrong-witness", "swap-witnesses", "wrong-label-map",
      "wrong-operation", "text-tamper", "kernel-claim-tamper", "scope-escape"].contains variant.getString do
    throwError "Unknown witness-check mode"
  let input ← IO.FS.readFile spec.getString
  let rows ← match Json.parse input >>= Json.getArr? with
    | .ok r => pure r | .error e => throwError "{e}"
  unless rows.size == 2 do throwError "Expected both original witness branches"
  if rows[0]! == rows[1]! then throwError "Duplicate witness source path"
  let records ← liftTermElabM do
    let target := target.getString.toName
    let .thmInfo declaration ← getConstInfo target | throwError "Witness target must be a theorem"
    let _ ← checkedAxioms target
    let mut records := #[]
    for i in [:rows.size] do
      let path ← match (fromJson? rows[i]! : Except String (List Nat)) with
        | .ok p => pure p | .error e => throwError "{e}"
      records := records.push (← checkOne target declaration.value declaration.levelParams path i variant.getString)
    return records
  IO.FS.writeFile out.getString (Json.arr records |>.pretty)
  logInfo "SOURCE_WITNESSES_CHECKED:2"
end ProofReader.SourceWitnesses
