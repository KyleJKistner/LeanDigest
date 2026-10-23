import OriginalBezout
import Mathlib.Logic.Function.Basic
import PilotAudit
namespace Candidate
theorem result {α : Type u} (xs : List α) : xs.reverse.reverse=xs := by simp
end Candidate
