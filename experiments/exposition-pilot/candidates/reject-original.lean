import OriginalBezout
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 4000000
set_option maxRecDepth 8192
namespace Candidate
theorem result {R : Type u} [EuclideanDomain R] (x y z : R)
    (h : x*y = z*(z+1)) :
    ∃ a d b c : R, a*b = x ∧ d*c = y ∧ d*b = z ∧ a*c-d*b = 1 := by
  exact OAI.ComplexCancellation.BezoutFrame.exists_frame x y z h

end Candidate
