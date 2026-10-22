import BezoutOriginal
import Mathlib.Logic.Function.Basic
import PilotAudit
set_option maxHeartbeats 2000000
set_option maxRecDepth 4096
set_option Elab.async false
namespace PilotCandidate
def diagonal {α : Type u} (f : α → Set α) : Set α := {a | a ∉ f a}

theorem diagonalMisses {α : Type u} (f : α → Set α) (a : α) :
    diagonal f ≠ f a := by
  intro h
  have hiff : (a ∈ f a) ↔ (a ∉ f a) := by
    conv_lhs => rw [← h]
    rfl
  exact iff_not_self hiff

theorem result {α : Type u} (f : α → Set α) : ¬ Function.Surjective f := by
  intro hf
  obtain ⟨a,ha⟩ := hf (diagonal f)
  exact diagonalMisses f a ha.symm

end PilotCandidate
