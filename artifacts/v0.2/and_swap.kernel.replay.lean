import Lean
import Lean.Util.CollectAxioms
open Lean Elab Command

private partial def proofreaderEraseMetadata : Lean.Expr → Lean.Expr
  | .mdata _ b => proofreaderEraseMetadata b
  | .app f a => .app (proofreaderEraseMetadata f) (proofreaderEraseMetadata a)
  | .lam n d b bi => .lam n (proofreaderEraseMetadata d) (proofreaderEraseMetadata b) bi
  | .forallE n d b bi => .forallE n (proofreaderEraseMetadata d) (proofreaderEraseMetadata b) bi
  | .letE n t v b nd => .letE n (proofreaderEraseMetadata t) (proofreaderEraseMetadata v) (proofreaderEraseMetadata b) nd
  | .proj n i b => .proj n i (proofreaderEraseMetadata b)
  | e => e

set_option maxRecDepth 10000 in
set_option maxHeartbeats 2000000 in
run_elab do
  let e0 : Expr := .sort Lean.Level.zero
  let e1 : Expr := .const (Lean.Name.str Lean.Name.anonymous "And") []
  let e2 : Expr := .bvar 1
  let e3 : Expr := .app e1 e2
  let e4 : Expr := .bvar 0
  let e5 : Expr := .app e3 e4
  let e6 : Expr := .bvar 2
  let e7 : Expr := .app e3 e6
  let e8 : Expr := .forallE (Lean.Name.num (Lean.Name.str (Lean.Name.str (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "a") "_@") "_internal") "_hyg") 0) e5 e7 .default
  let e9 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e8 .default
  let e10 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e9 .default
  let e11 : Expr := .const (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "And") "intro") []
  let e12 : Expr := .app e11 e2
  let e13 : Expr := .app e12 e6
  let e14 : Expr := .const (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "And") "right") []
  let e15 : Expr := .app e14 e6
  let e16 : Expr := .app e15 e2
  let e17 : Expr := .app e16 e4
  let e18 : Expr := .app e13 e17
  let e19 : Expr := .const (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "And") "left") []
  let e20 : Expr := .app e19 e6
  let e21 : Expr := .app e20 e2
  let e22 : Expr := .app e21 e4
  let e23 : Expr := .app e18 e22
  let e24 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "h") e5 e23 .default
  let e25 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "Q") e0 e24 .default
  let e26 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "P") e0 e25 .default
  let e27 : Expr := .app e1 e6
  let e28 : Expr := .app e27 e2
  let e29 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e0 .default
  let e30 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e5 .default
  let e31 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e30 .default
  let e32 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "h") e5 e7 .default
  let e33 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e32 .default
  let e34 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e33 .default
  let e35 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "h") e5 e2 .default
  let e36 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "Q") e0 e35 .default
  let e37 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "P") e0 e36 .default
  let e38 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "h") e5 e0 .default
  let e39 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e38 .default
  let e40 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e39 .default
  let e41 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "h") e5 e6 .default
  let e42 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "Q") e0 e41 .default
  let e43 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "P") e0 e42 .default
  let e44 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "h") e5 e17 .default
  let e45 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "Q") e0 e44 .default
  let e46 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "P") e0 e45 .default
  let e47 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "h") e5 e2 .default
  let e48 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e47 .default
  let e49 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e48 .default
  let e50 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "h") e5 e22 .default
  let e51 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "Q") e0 e50 .default
  let e52 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "P") e0 e51 .default
  let e53 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "h") e5 e6 .default
  let e54 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e53 .default
  let e55 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e54 .default
  let e56 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "h") e5 e4 .default
  let e57 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "Q") e0 e56 .default
  let e58 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "P") e0 e57 .default
  let e59 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "h") e5 e28 .default
  let e60 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e59 .default
  let e61 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e60 .default
  let original ← getConstInfo (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "PRSmoke") "and_swap")
  unless original.levelParams == [] do throwError "Universe inventory mismatch"
  let actualAxioms := (← Lean.collectAxioms (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "PRSmoke") "and_swap")).map Name.toString
  let expectedAxioms : Array String := #[]
  unless actualAxioms.size == expectedAxioms.size && actualAxioms.all expectedAxioms.contains && expectedAxioms.all actualAxioms.contains do
    throwError "Axiom inventory mismatch"
  unless proofreaderEraseMetadata original.type == e10 do throwError "Statement AST mismatch"
  let originalValue ← match original with
    | .thmInfo v => pure v.value
    | _ => throwError "Expected theorem"
  unless proofreaderEraseMetadata originalValue == e26 do throwError "Proof AST mismatch"
  let base := "ProofReaderJudgements.h921aea7e2ab844d07336".toName
  withOptions (fun o => o.setBool `debug.skipKernelTC false) do
    addDecl <| .thmDecl { name := .str base "root", levelParams := [], type := e10, value := e26 }
  logInfo "PROOFREADER_REPLAY_OK"
  let claims : Array (String × Expr × Expr × Bool) := #[("step_0", e26, e10, true),
    ("step_1", e26, e10, true),
    ("step_2", e26, e10, true),
    ("step_3", e26, e34, true),
    ("step_3_arg_0", e37, e40, false),
    ("step_3_arg_1", e43, e40, false),
    ("step_3_arg_2", e46, e49, true),
    ("step_3_arg_3", e52, e55, true),
    ("step_4", e46, e49, true),
    ("step_4_arg_0", e43, e40, false),
    ("step_4_arg_1", e37, e40, false),
    ("step_4_arg_2", e58, e61, true),
    ("step_5", e58, e61, true),
    ("step_6", e52, e55, true),
    ("step_6_arg_0", e43, e40, false),
    ("step_6_arg_1", e37, e40, false),
    ("step_6_arg_2", e58, e61, true),
    ("step_7", e58, e61, true)]
  for (label, value, type, proof) in claims do
    let isProp ← liftTermElabM <| Meta.isProp type
    unless isProp == proof do throwError "Proof/data classification mismatch: {label}"
    withOptions (fun o => o.setBool `debug.skipKernelTC false) do
      if proof then
        addDecl <| .thmDecl { name := .str base label, levelParams := [], type := type, value := value }
      else
        addDecl <| .defnDecl { name := .str base label, levelParams := [], type := type, value := value, hints := .abbrev, safety := .safe }
  let domains : Array (Nat × Expr × Bool) := #[(0, e0, false), (1, e29, false), (2, e31, true)]
  for (i, domain, expected) in domains do
    let actual ← liftTermElabM <| Meta.isProp domain
    unless actual == expected do throwError "Assumption/object classification mismatch: {i}"
  logInfo "PROOFREADER_JUDGEMENTS_OK:921aea7e2ab844d073360876f507d01aa5500d0de5b319dc12aa7104f8406e91:18"
