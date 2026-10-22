import BezoutOriginal
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 2000000
set_option maxRecDepth 4096
set_option Elab.async false
namespace PilotCandidate
theorem reverseIndex (n i : Nat) (hi : i < n) :
    n-1-(n-1-i)=i := by omega

theorem result {α : Type u} (xs : List α) : xs.reverse.reverse=xs := by
  apply List.ext_getElem
  · simp only [List.length_reverse]
  · intro i h₁ h₂
    simp only [List.getElem_reverse, List.length_reverse]
    congr 1
    exact reverseIndex xs.length i h₂

end PilotCandidate
