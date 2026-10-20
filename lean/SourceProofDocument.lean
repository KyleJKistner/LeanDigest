import ProofDocument
import SourceWitnesses

/-! # Source-bound proof-document composition

Reuse original passage certificates, restore the definitions of proof lets and
applied identity aliases, and check a closed certificate for the full document.
The importer is trusted code; the kernel checks its concrete output claims.
-/
open Lean Meta Elab Command
namespace ProofReader.SourceProofDocument
open ArithmeticEnglish EquationEnglish WitnessEnglish BezoutDocument
open SourceCancellation (eraseMetadata rawPath checkedDecl)
set_option maxHeartbeats 4000000
set_option maxRecDepth 4096

structure Origin where
  path : List Nat
  argument : Bool
  deriving Inhabited

/-- The original passage exporter turns nondependent proof lets into arguments.
Record those positions from the source AST rather than guessing from names. -/
def origins (e : Expr) (steps : List Nat) (trail : List Nat := []) : Except String (List Origin) :=
  match steps, e with
  | [], _ => .ok []
  | 0 :: ks, .app f _ => origins f ks (trail ++ [0])
  | 1 :: ks, .app _ a => origins a ks (trail ++ [1])
  | 1 :: ks, .lam _ _ b _ => do
      pure (⟨trail,true⟩ :: (← origins b ks (trail ++ [1])))
  | 2 :: ks, .letE _ _ _ b nd => do
      pure (⟨trail,nd⟩ :: (← origins b ks (trail ++ [2])))
  | 1 :: ks, .letE _ _ v _ _ => origins v ks (trail ++ [1])
  | _, _ => .error "Unsupported document source context"

/-- Unlike isolated passage checking, document composition keeps the proofs of
nondependent lets. A source `id (fun h => ...) oldH` also keeps its actual argument.
Unrecognized binder patterns remain assumptions and cannot pass final closure. -/
partial def withDocumentAt (e : Expr) (steps : List Nat) (xs : Array Expr)
    (restore : Bool) (aliases : Bool) (action : Expr → Array Expr → MetaM Json) : MetaM Json := do
  let e := e.consumeMData
  if aliases then
    if let 0 :: 1 :: 1 :: ks := steps then
      let args := e.getAppArgs
      if e.getAppFn.isConstOf ``id && args.size == 3 then
        if let .lam n t b _ := args[1]!.consumeMData then
          return ← withLetDecl n t args[2]! (nondep := false) fun x =>
            withDocumentAt (b.instantiate1 x) ks (xs.push x) restore aliases action
  match steps, e with
  | [], _ => action e xs
  | 0 :: ks, .app f _ => withDocumentAt f ks xs restore aliases action
  | 1 :: ks, .app _ a => withDocumentAt a ks xs restore aliases action
  | 1 :: ks, .lam n t b bi =>
      withLocalDecl n bi t fun x =>
        withDocumentAt (b.instantiate1 x) ks (xs.push x) restore aliases action
  | 2 :: ks, .letE n t v b nd =>
      withLetDecl n t v (nondep := if restore then false else nd) fun x =>
        withDocumentAt (b.instantiate1 x) ks (xs.push x) restore aliases action
  | 1 :: ks, .letE _ _ v _ _ => withDocumentAt v ks xs restore aliases action
  | _, _ => throwError "Unsupported document traversal"

/-- Apply a prior certificate only to the identical source binder occurrences.
Recovered lets are supplied as actual proofs, not new external assumptions. -/
def applyPassage (original : Expr) (levels : List Name) (name : Name)
    (selected live : List Nat) (xs : Array Expr) : MetaM Expr := do
  let selectedOrigins ← ofExcept (origins (eraseMetadata original) selected)
  let liveOrigins ← ofExcept (origins (eraseMetadata original) live)
  unless liveOrigins.length == xs.size && selectedOrigins.length ≤ xs.size do
    throwError "Document binder inventory mismatch"
  let mut args := #[]
  for i in [:selectedOrigins.length] do
    unless selectedOrigins[i]!.path == liveOrigins[i]!.path do
      throwError "Passage crosses a document scope"
    if selectedOrigins[i]!.argument then args := args.push xs[i]!
  return mkAppN (mkConst name (levels.map Level.param)) args

def quoteDocument (d : Document) : Expr :=
  mkAppN (mkConst ``Document.mk) #[
    SourceEquations.quoteChain d.zeroAB, SourceEquations.quoteChain d.zeroDC,
    SourceEquations.quoteChain d.zeroDB, SourceEquations.quoteChain d.zeroDet,
    SourceWitnesses.quoteFrame d.zeroFrame, SourceEquations.quoteChain d.bezoutEq,
    SourceCancellation.quoteCancellation d.bezoutCancel, SourceEquations.quoteChain d.relationEq,
    SourceCancellation.quoteCancellation d.relationCancel, SourceEquations.quoteChain d.nonzeroAB,
    SourceEquations.quoteChain d.nonzeroDC, SourceEquations.quoteChain d.nonzeroDB,
    SourceEquations.quoteChain d.nonzeroDet, SourceWitnesses.quoteFrame d.nonzeroFrame]

def conjunction (proofs : Array Expr) : MetaM Expr := do
  unless !proofs.isEmpty do throwError "Empty document conjunction"
  let mut proof := proofs.back!
  for j in [:proofs.size-1] do
    let i := proofs.size-j-2
    proof ← mkAppM ``And.intro #[proofs[i]!,proof]
  return proof

def textOf (j : Json) : MetaM String :=
  ofExcept (j.getObjVal? "text" >>= Json.getStr?)

def scopeRecord (xs : Array Expr) : MetaM Json := do
  let mut rows := #[]
  for i in [:xs.size] do
    let d ← xs[i]!.fvarId!.getDecl
    rows := rows.push <| Json.mkObj [
      ("index",toJson i), ("name",toJson d.userName.eraseMacroScopes.toString),
      ("type",toJson (← ppExpr d.type).pretty),
      ("definition_restored",toJson d.value?.isSome),
      ("definition",← match d.value? with
        | some v => pure (toJson (← ppExpr v).pretty)
        | none => pure Json.null)]
  return Json.arr rows

def checkOccurrence (original node : Expr) (selected : List Nat) (xs : Array Expr) : MetaM Unit := do
  let raw ← ofExcept (rawPath (eraseMetadata original) selected)
  unless raw == eraseMetadata (node.abstract xs) do
    throwError "Document occurrence identity mismatch"

/-- Check the source case split and the two original gcd-divisibility arguments. -/
def checkSkeleton (target : Name) (original : Expr) (levels : List Name)
    (variant : String) : MetaM Json := do
  let splitPath := List.replicate 6 1 ++ [2]
  let splitRecord ← withDocumentAt original splitPath #[] true true fun node xs => do
    checkOccurrence original node splitPath xs
    unless xs.size == 7 && node.getAppFn.isConstOf ``dite && node.getAppArgs.size == 5 do
      throwError "Expected original gcd case split"
    let args := node.getAppArgs
    let zero ← mkNumeral xs[0]! (if variant == "wrong-case" then 1 else 0)
    unless eraseMetadata args[1]! == eraseMetadata (← mkEq xs[6]! zero) do
      throwError "Document case condition mismatch"
    let gd ← xs[6]!.fvarId!.getDecl
    let some gvalue := gd.value? | throwError "Missing original gcd definition"
    let ga := gvalue.getAppArgs
    unless gvalue.getAppFn.isConstOf ``EuclideanDomain.gcd && ga.size == 5 &&
        ga[3]! == xs[2]! && ga[4]! == xs[4]! do
      throwError "Document gcd definition mismatch"
    unless args[3]!.isLambda && args[4]!.isLambda do throwError "Missing original case branches"
    return Json.mkObj [("case_path",toJson splitPath), ("condition",toJson (← ppExpr args[1]!).pretty),
      ("gcd_definition",toJson (← ppExpr gvalue).pretty)]
  let nzRoot := splitPath ++ [1,1]
  let _ ← withDocumentAt original nzRoot #[] true true fun node xs => do
    checkOccurrence original node nzRoot xs
    let args := node.getAppArgs
    unless node.getAppFn.isConstOf ``Exists.casesOn && args.size == 5 do
      throwError "Expected source quotient elimination"
    let left := args[3]!
    let .lam _ _ tail _ := args[4]!.consumeMData | throwError "Missing first quotient binder"
    let .lam _ _ tail _ := tail.consumeMData | throwError "Missing first quotient equality"
    let rightNode := tail.consumeMData
    unless rightNode.getAppFn.isConstOf ``Exists.casesOn && rightNode.getAppArgs.size == 5 do
      throwError "Missing second quotient elimination"
    let right := rightNode.getAppArgs[3]!
    unless left.getAppFn.isConstOf ``EuclideanDomain.gcd_dvd_left &&
        right.getAppFn.isConstOf ``EuclideanDomain.gcd_dvd_right &&
        !left.hasLooseBVars && !right.hasLooseBVars do
      throwError "Unexpected source divisibility proofs"
    let proof ← conjunction #[left,right]
    checkedDecl (target.str "documentAvailable") levels xs (← inferType proof) proof
    pure Json.null
  return splitRecord

/-- Build a complete certificate from the original facts in their actual scopes. -/
def checkDocument (target : Name) (equationPaths witnessPaths cancellationPaths : Array (List Nat))
    (variant : String) : MetaM Json := do
  let .thmInfo info ← getConstInfo target | throwError "Document target must be a theorem"
  let original := info.value
  let levels := info.levelParams
  let _ ← SourceEquations.checkedAxioms target
  unless equationPaths.size == 10 && witnessPaths.size == 2 && cancellationPaths.size == 2 do
    throwError "Incomplete document passage inventory"
  let splitPath := List.replicate 6 1 ++ [2]
  unless witnessPaths[0]! == splitPath ++ [0,1,1,2] &&
      witnessPaths[1]! == splitPath ++ [1,1,1,1,1,1,1,1,0,1,1,0,1,1,2,2,2,2] do
    throwError "Document branch occurrence mismatch"
  unless equationPaths[4]! == cancellationPaths[0]! ++ [1] &&
      equationPaths[5]! == cancellationPaths[1]! ++ [1] do
    throwError "Document cancellation prerequisite mismatch"
  let zeroRoot := witnessPaths[0]! ++ [1,1,1,1]
  let nonzeroRoot := witnessPaths[1]! ++ [1,1,1,1]
  let zeroEquations := #[zeroRoot ++ [0,1], zeroRoot ++ [1,0,1],
    zeroRoot ++ [1,1,0,1], zeroRoot ++ [1,1,1]]
  let finalEquations := #[nonzeroRoot ++ [0,1], nonzeroRoot ++ [1,0,1],
    nonzeroRoot ++ [1,1,0,1], nonzeroRoot ++ [1,1,1]]
  unless equationPaths.extract 0 4 == zeroEquations && equationPaths.extract 6 10 == finalEquations do
    throwError "Document equation order or inventory mismatch"
  unless cancellationPaths == #[witnessPaths[1]!.dropLast.dropLast ++ [1],
      witnessPaths[1]!.dropLast ++ [1]] do
    throwError "Document local-fact source mismatch"
  let skeleton ← checkSkeleton target original levels variant
  let mut equations := #[]
  let mut equationRecords := #[]
  for i in [:10] do
    let record ← SourceEquations.checkOne target original levels equationPaths[i]! i "ok"
    let some c := EquationEnglish.read (← textOf record) | throwError "Unparsed equation passage"
    equations := equations.push c
    equationRecords := equationRecords.push record
  let mut frames := #[]
  let mut frameRecords := #[]
  for i in [:2] do
    let record ← SourceWitnesses.checkOne target original levels witnessPaths[i]! i "ok"
    let some f := WitnessEnglish.read (← textOf record) | throwError "Unparsed witness passage"
    frames := frames.push f
    frameRecords := frameRecords.push record
  let mut cancellations := #[]
  let mut cancellationRecords := #[]
  for i in [:2] do
    let record ← SourceCancellation.checkOne target original levels cancellationPaths[i]! i "ok"
    let some c := ArithmeticEnglish.readCancellation (← textOf record) | throwError "Unparsed cancellation passage"
    cancellations := cancellations.push c
    cancellationRecords := cancellationRecords.push record
  let doc : Document := ⟨equations[0]!,equations[1]!,equations[2]!,equations[3]!,frames[0]!,
    equations[4]!,cancellations[0]!,equations[5]!,cancellations[1]!,equations[6]!,
    equations[7]!,equations[8]!,equations[9]!,frames[1]!⟩
  let doc := if variant == "scope-name" then
      {doc with zeroFrame := {doc.zeroFrame with a := .var .a}}
    else if variant == "wrong-input" then
      {doc with nonzeroFrame := {doc.nonzeroFrame with x := .one}}
    else doc
  unless doc.wellFormed do throwError "Document contains unbound names or different frame inputs"
  let quoted := quoteDocument doc
  let restore := variant != "unproved-let"
  let aliases := variant != "unproved-alias"
  let zeroContext ← withDocumentAt original witnessPaths[0]! #[] restore aliases fun node xs => do
    checkOccurrence original node witnessPaths[0]! xs
    unless xs.size == 9 do throwError "Unexpected zero document context"
    let mut proofs := #[xs[8]!]
    for i in [:4] do
      proofs := proofs.push (← applyPassage original levels
        (target.str "equationText" |>.num i |>.str "english") equationPaths[i]! witnessPaths[0]! xs)
    proofs := proofs.push (← applyPassage original levels (target.str "witnessText" |>.num 0 |>.str "english")
      witnessPaths[0]! witnessPaths[0]! xs)
    let proof ← conjunction proofs
    let goal ← mkAppM ``Document.Zero #[quoted,xs[2]!,xs[3]!,xs[4]!]
    checkedDecl (target.str "documentZero") levels xs goal proof
    scopeRecord xs
  let nonzeroContext ← withDocumentAt original witnessPaths[1]! #[] restore aliases fun node xs => do
    checkOccurrence original node witnessPaths[1]! xs
    unless xs.size == 18 do throwError "Unexpected nonzero document context"
    let b ← SourceEquations.bindings xs xs[0]!
    let mut proofs := #[]
    for (kind,index) in #[("eq",4),("cancel",0),("eq",5),("cancel",1),
        ("eq",6),("eq",7),("eq",8),("eq",9),("frame",1)] do
      let (name,selected) := if kind == "eq" then
          (target.str "equationText" |>.num index |>.str "english",equationPaths[index]!)
        else if kind == "cancel" then
          (target.str "sourceText" |>.num index |>.str "english",cancellationPaths[index]!)
        else (target.str "witnessText" |>.num index |>.str "english",witnessPaths[index]!)
      proofs := proofs.push (← applyPassage original levels name selected witnessPaths[1]! xs)
    let proof ← conjunction proofs
    let goal ← mkAppM ``Document.Nonzero #[quoted,xs[2]!,xs[3]!,xs[4]!,b.values[4]!,b.values[5]!]
    checkedDecl (target.str "documentNonzero") levels xs goal proof
    scopeRecord xs
  let text := if variant == "text-tamper" then doc.render ++ "Therefore 0 = 1.\n" else doc.render
  unless text == doc.render do throwError "Document literal text mismatch"
  let finalRecord ← withDocumentAt original [1,1] #[] true true fun _ xs => do
    unless xs.size == 2 do throwError "Unexpected document outer context"
    let specialize (name : Name) := mkAppN (mkConst name (levels.map Level.param)) xs
    let wf ← mkDecideProof (← mkEq (← mkAppM ``Document.wellFormed #[quoted]) (mkConst ``Bool.true))
    let nz ← mkAppM ``packNonzero #[quoted,specialize (target.str "documentAvailable"),
      specialize (target.str "documentNonzero")]
    let zero := specialize (target.str (if variant == "wrong-branch" then "documentNonzero" else "documentZero"))
    let certificate ← mkAppM ``BezoutDocument.certify #[quoted,wf,zero,nz]
    let literal := mkStrLit text
    let meaning ← mkAppM ``BezoutDocument.TextMeans #[xs[0]!,literal]
    checkedDecl (target.str "documentEnglish") levels xs
      (if variant == "kernel-claim" then mkConst ``False else meaning) certificate
    let byteProof ← mkAppM ``BezoutDocument.certifyBytes #[quoted,certificate]
    let bytes ← mkAppM ``String.toUTF8 #[literal]
    checkedDecl (target.str "documentUTF8") levels xs
      (← mkAppM ``BezoutDocument.BytesMean #[xs[0]!,bytes]) byteProof
    let implication ← mkAppM ``BezoutDocument.text_implies_statement #[literal,certificate]
    let statement ← mkAppOptM ``Statement #[some xs[0]!,some xs[1]!]
    checkedDecl (target.str "documentConclusion") levels xs statement implication
    -- Kernel-check the original theorem against precisely the same statement.
    checkedDecl (target.str "documentOriginalStatement") levels xs statement (specialize target)
    let ax ← SourceEquations.checkedAxioms (target.str "documentEnglish")
    let _ ← SourceEquations.checkedAxioms (target.str "documentUTF8")
    let _ ← SourceEquations.checkedAxioms (target.str "documentConclusion")
    pure <| Json.mkObj [("text",toJson text),("utf8",toJson (text.toUTF8.data.toList.map UInt8.toNat)),
      ("text_theorem",toJson (target.str "documentEnglish").toString),
      ("bytes_theorem",toJson (target.str "documentUTF8").toString),
      ("conclusion_theorem",toJson (target.str "documentConclusion").toString),
      ("axioms",toJson (ax.map Name.toString)),
      ("closed_outer_binders",toJson (2 : Nat)),
      ("source_statement_kernel_checked",toJson true),
      ("literal_document_kernel_checked",toJson true),
      ("both_branches_composed",toJson true)]
  pure <| Json.mkObj [("document",finalRecord),("skeleton",skeleton),
    ("zero_context",zeroContext),("nonzero_context",nonzeroContext),
    ("equations",Json.arr equationRecords),("cancellations",Json.arr cancellationRecords),
    ("witnesses",Json.arr frameRecords)]

elab "#source_document " target:str " config " input:str " output " out:str " mode " variant:str : command => do
  unless #["ok","wrong-case","scope-name","wrong-input","unproved-let","unproved-alias",
      "text-tamper","wrong-branch","kernel-claim"].contains variant.getString do
    throwError "Unknown document-check variant"
  let parsed ← ofExcept (Json.parse (← IO.FS.readFile input.getString))
  let equations ← ofExcept (parsed.getObjVal? "equations" >>= fromJson? (α := Array (List Nat)))
  let witnesses ← ofExcept (parsed.getObjVal? "witnesses" >>= fromJson? (α := Array (List Nat)))
  let cancellations ← ofExcept (parsed.getObjVal? "cancellations" >>= fromJson? (α := Array (List Nat)))
  let record ← liftTermElabM do
    checkDocument target.getString.toName equations witnesses cancellations variant.getString
  IO.FS.writeFile out.getString record.pretty
  logInfo "SOURCE_DOCUMENT_CHECKED:1"
end ProofReader.SourceProofDocument
