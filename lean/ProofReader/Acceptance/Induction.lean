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
end BatchAcceptance.Induction
