import Lean
import Lean.Util.CollectAxioms
namespace PRSmoke
theorem and_swap (P Q : Prop) : P ∧ Q → Q ∧ P := fun h => ⟨h.2, h.1⟩
end PRSmoke
open Lean Elab Command

private partial def proofreaderEraseMetadata : Lean.Expr → Lean.Expr
  | .mdata _ b => proofreaderEraseMetadata b
  | .app f a => .app (proofreaderEraseMetadata f) (proofreaderEraseMetadata a)
  | .lam n d b bi => .lam n (proofreaderEraseMetadata d) (proofreaderEraseMetadata b) bi
  | .forallE n d b bi => .forallE n (proofreaderEraseMetadata d) (proofreaderEraseMetadata b) bi
  | .letE n t v b nd => .letE n (proofreaderEraseMetadata t) (proofreaderEraseMetadata v) (proofreaderEraseMetadata b) nd
  | .proj n i b => .proj n i (proofreaderEraseMetadata b)
  | e => e

private partial def proofreaderAtPath (e : Lean.Expr) (path : List Nat)
    (context : List Lean.Expr := []) : Except String (Lean.Expr × List Lean.Expr) := do
  match path with
  | [] => return (e, context)
  | k :: ks =>
    match e, k with
    | .app f _, 0 => proofreaderAtPath f ks context
    | .app _ a, 1 => proofreaderAtPath a ks context
    | .lam _ d _ _, 0 | .forallE _ d _ _, 0 => proofreaderAtPath d ks context
    | .lam _ _ b _, 1 | .forallE _ _ b _, 1 => proofreaderAtPath b ks (e :: context)
    | .letE _ t _ _ _, 0 => proofreaderAtPath t ks context
    | .letE _ _ v _ _, 1 => proofreaderAtPath v ks context
    | .letE _ _ _ b _, 2 => proofreaderAtPath b ks (e :: context)
    | .proj _ _ b, 0 => proofreaderAtPath b ks context
    | _, _ => throw "Invalid source proof path"

private def proofreaderClose (e : Lean.Expr) (context : List Lean.Expr) : Except String Lean.Expr :=
  context.foldlM (fun value binder => do
    match binder with
    | .lam n d _ bi | .forallE n d _ bi => return .lam n d value bi
    | .letE n t v _ nd => return .letE n t v value nd
    | _ => throw "Invalid source binder") e

private def proofreaderClosedAt (root : Lean.Expr) (path : List Nat) : Except String Lean.Expr := do
  let (term, context) ← proofreaderAtPath root path
  proofreaderClose term context

set_option maxRecDepth 10000 in
set_option maxHeartbeats 2000000 in
run_elab do
  let e0 : Expr := .sort Lean.Level.zero
  let n0 : Name := .anonymous
  let n1 : Name := .str n0 "And"
  let e1 : Expr := .const n1 []
  let e2 : Expr := .bvar 1
  let e3 : Expr := .app e1 e2
  let e4 : Expr := .bvar 0
  let e5 : Expr := .app e3 e4
  let e6 : Expr := .bvar 2
  let e7 : Expr := .app e3 e6
  let n2 : Name := .str n0 "a"
  let n3 : Name := .str n2 "_@"
  let n4 : Name := .str n3 "_internal"
  let n5 : Name := .str n4 "_hyg"
  let n6 : Name := .num n5 0
  let e8 : Expr := .forallE n6 e5 e7 .default
  let n7 : Name := .str n0 "Q"
  let e9 : Expr := .forallE n7 e0 e8 .default
  let n8 : Name := .str n0 "P"
  let e10 : Expr := .forallE n8 e0 e9 .default
  let n9 : Name := .str n1 "intro"
  let e11 : Expr := .const n9 []
  let e12 : Expr := .app e11 e2
  let e13 : Expr := .app e12 e6
  let n10 : Name := .str n1 "right"
  let e14 : Expr := .const n10 []
  let e15 : Expr := .app e14 e6
  let e16 : Expr := .app e15 e2
  let e17 : Expr := .app e16 e4
  let e18 : Expr := .app e13 e17
  let n11 : Name := .str n1 "left"
  let e19 : Expr := .const n11 []
  let e20 : Expr := .app e19 e6
  let e21 : Expr := .app e20 e2
  let e22 : Expr := .app e21 e4
  let e23 : Expr := .app e18 e22
  let n12 : Name := .str n0 "h"
  let e24 : Expr := .lam n12 e5 e23 .default
  let e25 : Expr := .lam n7 e0 e24 .default
  let e26 : Expr := .lam n8 e0 e25 .default
  let e27 : Expr := .app e1 e6
  let e28 : Expr := .app e27 e2
  let e29 : Expr := .forallE n8 e0 e0 .default
  let e30 : Expr := .forallE n7 e0 e5 .default
  let e31 : Expr := .forallE n8 e0 e30 .default
  let e32 : Expr := .forallE n12 e5 e7 .default
  let e33 : Expr := .forallE n7 e0 e32 .default
  let e34 : Expr := .forallE n8 e0 e33 .default
  let e35 : Expr := .lam n12 e5 e2 .default
  let e36 : Expr := .lam n7 e0 e35 .default
  let e37 : Expr := .lam n8 e0 e36 .default
  let e38 : Expr := .forallE n12 e5 e0 .default
  let e39 : Expr := .forallE n7 e0 e38 .default
  let e40 : Expr := .forallE n8 e0 e39 .default
  let e41 : Expr := .lam n12 e5 e6 .default
  let e42 : Expr := .lam n7 e0 e41 .default
  let e43 : Expr := .lam n8 e0 e42 .default
  let e44 : Expr := .lam n12 e5 e17 .default
  let e45 : Expr := .lam n7 e0 e44 .default
  let e46 : Expr := .lam n8 e0 e45 .default
  let e47 : Expr := .forallE n12 e5 e2 .default
  let e48 : Expr := .forallE n7 e0 e47 .default
  let e49 : Expr := .forallE n8 e0 e48 .default
  let e50 : Expr := .lam n12 e5 e22 .default
  let e51 : Expr := .lam n7 e0 e50 .default
  let e52 : Expr := .lam n8 e0 e51 .default
  let e53 : Expr := .forallE n12 e5 e6 .default
  let e54 : Expr := .forallE n7 e0 e53 .default
  let e55 : Expr := .forallE n8 e0 e54 .default
  let e56 : Expr := .lam n12 e5 e4 .default
  let e57 : Expr := .lam n7 e0 e56 .default
  let e58 : Expr := .lam n8 e0 e57 .default
  let e59 : Expr := .forallE n12 e5 e28 .default
  let e60 : Expr := .forallE n7 e0 e59 .default
  let e61 : Expr := .forallE n8 e0 e60 .default
  unless Lean.versionString == "4.34.1" do throwError "Toolchain version mismatch"
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
  let sourceBindings : Array (String × List Nat × Expr) := #[("step_0", [], e26),
    ("step_1", [1], e26),
    ("step_2", [1, 1], e26),
    ("step_3", [1, 1, 1], e26),
    ("step_3_arg_0", [1, 1, 1, 0, 0, 0, 1], e37),
    ("step_3_arg_1", [1, 1, 1, 0, 0, 1], e43),
    ("step_3_arg_2", [1, 1, 1, 0, 1], e46),
    ("step_3_arg_3", [1, 1, 1, 1], e52),
    ("step_4", [1, 1, 1, 0, 1], e46),
    ("step_4_arg_0", [1, 1, 1, 0, 1, 0, 0, 1], e43),
    ("step_4_arg_1", [1, 1, 1, 0, 1, 0, 1], e37),
    ("step_4_arg_2", [1, 1, 1, 0, 1, 1], e58),
    ("step_5", [1, 1, 1, 0, 1, 1], e58),
    ("step_6", [1, 1, 1, 1], e52),
    ("step_6_arg_0", [1, 1, 1, 1, 0, 0, 1], e43),
    ("step_6_arg_1", [1, 1, 1, 1, 0, 1], e37),
    ("step_6_arg_2", [1, 1, 1, 1, 1], e58),
    ("step_7", [1, 1, 1, 1, 1], e58)]
  for (label, path, expectedValue) in sourceBindings do
    match proofreaderClosedAt (proofreaderEraseMetadata originalValue) path with
    | .error message => throwError "{message}: {label}"
    | .ok actual => unless actual == expectedValue do throwError "Source linkage mismatch: {label}"
  logInfo "PROOFREADER_PATHS_OK"
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
    let isProp ← Meta.isProp type
    unless isProp == proof do throwError "Proof/data classification mismatch: {label}"
    withOptions (fun o => o.setBool `debug.skipKernelTC false) do
      if proof then
        addDecl <| .thmDecl { name := .str base label, levelParams := [], type := type, value := value }
      else
        addDecl <| .defnDecl { name := .str base label, levelParams := [], type := type, value := value, hints := .abbrev, safety := .safe }
  let domains : Array (Nat × Expr × Bool) := #[(0, e0, false), (1, e29, false), (2, e31, true)]
  for (i, domain, expected) in domains do
    let actual ← Meta.isProp domain
    unless actual == expected do throwError "Assumption/object classification mismatch: {i}"
  logInfo "PROOFREADER_JUDGEMENTS_OK:921aea7e2ab844d073360876f507d01aa5500d0de5b319dc12aa7104f8406e91:18"
