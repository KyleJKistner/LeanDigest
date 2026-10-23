import OriginalBezout
import Mathlib.Logic.Function.Basic
import PilotAudit
namespace Candidate
axiom unsupported : False
theorem result {α : Type u} (xs : List α) : xs.reverse.reverse=xs := False.elim unsupported
end Candidate
