import BezoutOriginal
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 2000000
set_option maxRecDepth 4096
set_option Elab.async false
namespace PilotCandidate
theorem result {α : Type u} (f : α → Set α) : ¬ Function.Surjective f := by
  intro hf
  obtain ⟨p, hp⟩ := Function.exists_fixed_point_of_surjective f hf Not
  exact iff_not_self (Iff.of_eq hp.symm)

end PilotCandidate
