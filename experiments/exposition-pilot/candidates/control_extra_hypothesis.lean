import BezoutOriginal
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 2000000
set_option maxRecDepth 4096
set_option Elab.async false
namespace PilotCandidate
theorem result {α : Type u} (xs : List α) (h : xs.reverse.reverse=xs) : xs.reverse.reverse=xs := h
end PilotCandidate
