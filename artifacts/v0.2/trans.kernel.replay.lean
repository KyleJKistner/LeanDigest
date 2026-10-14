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
  let e1 : Expr := .bvar 2
  let e2 : Expr := .forallE (Lean.Name.num (Lean.Name.str (Lean.Name.str (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "a") "_@") "_internal") "_hyg") 0) e1 e1 .default
  let e3 : Expr := .bvar 4
  let e4 : Expr := .bvar 3
  let e5 : Expr := .forallE (Lean.Name.num (Lean.Name.str (Lean.Name.str (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "a") "_@") "_internal") "_hyg") 0) e3 e4 .default
  let e6 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "b") e2 e5 .default
  let e7 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "a") e2 e6 .default
  let e8 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "R") e0 e7 .default
  let e9 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e8 .default
  let e10 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e9 .default
  let e11 : Expr := .bvar 1
  let e12 : Expr := .bvar 0
  let e13 : Expr := .app e1 e12
  let e14 : Expr := .app e11 e13
  let e15 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "h") e3 e14 .default
  let e16 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "b") e2 e15 .default
  let e17 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "a") e2 e16 .default
  let e18 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "R") e0 e17 .default
  let e19 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "Q") e0 e18 .default
  let e20 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "P") e0 e19 .default
  let e21 : Expr := .bvar 5
  let e22 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e0 .default
  let e23 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e0 .default
  let e24 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e23 .default
  let e25 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "R") e0 e2 .default
  let e26 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e25 .default
  let e27 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e26 .default
  let e28 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "a") e2 e2 .default
  let e29 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "R") e0 e28 .default
  let e30 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e29 .default
  let e31 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e30 .default
  let e32 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "b") e2 e3 .default
  let e33 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "a") e2 e32 .default
  let e34 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "R") e0 e33 .default
  let e35 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e34 .default
  let e36 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e35 .default
  let e37 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "h") e3 e4 .default
  let e38 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "b") e2 e37 .default
  let e39 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "a") e2 e38 .default
  let e40 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "R") e0 e39 .default
  let e41 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e40 .default
  let e42 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e41 .default
  let e43 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "h") e3 e13 .default
  let e44 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "b") e2 e43 .default
  let e45 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "a") e2 e44 .default
  let e46 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "R") e0 e45 .default
  let e47 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "Q") e0 e46 .default
  let e48 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "P") e0 e47 .default
  let e49 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "h") e3 e3 .default
  let e50 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "b") e2 e49 .default
  let e51 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "a") e2 e50 .default
  let e52 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "R") e0 e51 .default
  let e53 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e52 .default
  let e54 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e53 .default
  let e55 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "h") e3 e12 .default
  let e56 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "b") e2 e55 .default
  let e57 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "a") e2 e56 .default
  let e58 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "R") e0 e57 .default
  let e59 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "Q") e0 e58 .default
  let e60 : Expr := .lam (Lean.Name.str Lean.Name.anonymous "P") e0 e59 .default
  let e61 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "h") e3 e21 .default
  let e62 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "b") e2 e61 .default
  let e63 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "a") e2 e62 .default
  let e64 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "R") e0 e63 .default
  let e65 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "Q") e0 e64 .default
  let e66 : Expr := .forallE (Lean.Name.str Lean.Name.anonymous "P") e0 e65 .default
  let original ← getConstInfo (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "PRSmoke") "trans")
  unless original.levelParams == [] do throwError "Universe inventory mismatch"
  let actualAxioms := (← Lean.collectAxioms (Lean.Name.str (Lean.Name.str Lean.Name.anonymous "PRSmoke") "trans")).map Name.toString
  let expectedAxioms : Array String := #[]
  unless actualAxioms.size == expectedAxioms.size && actualAxioms.all expectedAxioms.contains && expectedAxioms.all actualAxioms.contains do
    throwError "Axiom inventory mismatch"
  unless proofreaderEraseMetadata original.type == e10 do throwError "Statement AST mismatch"
  let originalValue ← match original with
    | .thmInfo v => pure v.value
    | _ => throwError "Expected theorem"
  unless proofreaderEraseMetadata originalValue == e20 do throwError "Proof AST mismatch"
  let base := "ProofReaderJudgements.he3919d4cd162600bfff6".toName
  withOptions (fun o => o.setBool `debug.skipKernelTC false) do
    addDecl <| .thmDecl { name := .str base "root", levelParams := [], type := e10, value := e20 }
  logInfo "PROOFREADER_REPLAY_OK"
  let claims : Array (String × Expr × Expr × Bool) := #[("step_0", e20, e10, true),
    ("step_1", e20, e10, true),
    ("step_2", e20, e10, true),
    ("step_3", e20, e10, true),
    ("step_4", e20, e10, true),
    ("step_5", e20, e10, true),
    ("step_6", e20, e42, true),
    ("step_6_arg_0", e48, e54, true),
    ("step_7", e48, e54, true),
    ("step_7_arg_0", e60, e66, true),
    ("step_8", e60, e66, true)]
  for (label, value, type, proof) in claims do
    let isProp ← liftTermElabM <| Meta.isProp type
    unless isProp == proof do throwError "Proof/data classification mismatch: {label}"
    withOptions (fun o => o.setBool `debug.skipKernelTC false) do
      if proof then
        addDecl <| .thmDecl { name := .str base label, levelParams := [], type := type, value := value }
      else
        addDecl <| .defnDecl { name := .str base label, levelParams := [], type := type, value := value, hints := .abbrev, safety := .safe }
  let domains : Array (Nat × Expr × Bool) := #[(0, e0, false), (1, e22, false), (2, e24, false), (3, e27, true), (4, e31, true), (5, e36, true)]
  for (i, domain, expected) in domains do
    let actual ← liftTermElabM <| Meta.isProp domain
    unless actual == expected do throwError "Assumption/object classification mismatch: {i}"
  logInfo "PROOFREADER_JUDGEMENTS_OK:e3919d4cd162600bfff6c41c4c595f348f3a329b9d2c920419b403b1448942d1:11"
