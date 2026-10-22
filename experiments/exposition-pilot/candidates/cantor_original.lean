import BezoutOriginal
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 2000000
set_option maxRecDepth 4096
set_option Elab.async false
namespace PilotCandidate
theorem result {α : Type u} (f : α → Set α) : ¬ Function.Surjective f := fun hf =>
  let ⟨a,ha⟩ := hf {a | a ∉ f a}
  iff_not_self <| .of_eq <| congrArg (a ∈ ·) ha

end PilotCandidate
