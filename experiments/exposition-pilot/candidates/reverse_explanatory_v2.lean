import BezoutOriginal
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 2000000
set_option maxRecDepth 4096
set_option Elab.async false
namespace PilotCandidate
theorem reverseSnoc {α : Type u} (xs : List α) (a : α) :
    (xs ++ [a]).reverse = a :: xs.reverse := by
  induction xs with
  | nil => rfl
  | cons x xs ih =>
      simp only [List.cons_append, List.reverse_cons, ih]

theorem result {α : Type u} (xs : List α) : xs.reverse.reverse = xs := by
  induction xs with
  | nil => rfl
  | cons a xs ih =>
      rw [List.reverse_cons, reverseSnoc, ih]

end PilotCandidate
