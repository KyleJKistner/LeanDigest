import OriginalBezout
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 4000000
set_option maxRecDepth 8192
namespace Candidate
theorem result {α : Type u} (f : α → Set α) : ¬Function.Surjective f := by sorry

end Candidate
