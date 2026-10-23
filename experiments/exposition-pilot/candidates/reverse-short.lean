import OriginalBezout
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 4000000
set_option maxRecDepth 8192
namespace Candidate
theorem result {α : Type u} (xs : List α) : xs.reverse.reverse=xs := by
  simpa only [List.reverse, List.reverseAux] using
    (List.reverseAux_reverseAux_nil (as := xs) (bs := []))

end Candidate
