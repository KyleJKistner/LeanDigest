import OriginalBezout
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 4000000
set_option maxRecDepth 8192
namespace Candidate
theorem aliasProof {α : Type u} (xs : List α) : xs.reverse.reverse=xs := List.reverse_reverse xs
theorem result {α : Type u} (xs : List α) : xs.reverse.reverse=xs := aliasProof xs

end Candidate
