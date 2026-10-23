import OriginalBezout
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 4000000
set_option maxRecDepth 8192
namespace Candidate
theorem result {α : Type u} (xs : List α) : xs.reverse.reverse=xs := by
  induction xs with
  | nil => rfl
  | cons a xs ih =>
    calc
      (a::xs).reverse.reverse = (xs.reverse++[a]).reverse := by rw [List.reverse_cons]
      _ = [a].reverse++xs.reverse.reverse := List.reverse_append
      _ = [a]++xs := by rw [List.reverse_singleton, ih]
      _ = a::xs := rfl

end Candidate
