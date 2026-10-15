import Lean
namespace BatchAcceptance.Induction

theorem addition_associates (a b c : Nat) : (a + b) + c = a + (b + c) := by
  induction c with
  | zero => rfl
  | succ c ih => exact congrArg Nat.succ ih

theorem zero_adds (n : Nat) : 0 + n = n := by
  induction n with
  | zero => rfl
  | succ n ih => exact congrArg Nat.succ ih
-- Explicitly oversaturated recursor: m is NOT the induction variable.
-- The reader must separate induction on n from subsequent specialization to m.
theorem rec_overapplied (n m : Nat) : 0 + n = n :=
  (Nat.rec (motive := fun k => ∀ _z : Nat, 0 + k = k)
    (fun _z => rfl)
    (fun k ih z => congrArg Nat.succ (ih z)) n) m
-- recOn has different proof-argument positions; check the actual major argument.
theorem zero_add_recOn (n : Nat) : 0 + n = n :=
  Nat.recOn n (motive := fun k => 0 + k = k) rfl
    (fun k ih => congrArg Nat.succ ih)
end BatchAcceptance.Induction
