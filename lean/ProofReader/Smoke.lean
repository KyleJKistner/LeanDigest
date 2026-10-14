import Lean

namespace ProofReaderSmoke

theorem implication_transitivity (P Q R : Prop) (hpq : P → Q) (hqr : Q → R) : P → R := by
  intro hp
  exact hqr (hpq hp)

theorem and_commute (P Q : Prop) : P ∧ Q → Q ∧ P := by
  intro h
  exact ⟨h.2, h.1⟩

theorem composition_injective {X Y Z : Type} (f : X → Y) (g : Y → Z)
    (hf : Function.Injective f) (hg : Function.Injective g) :
    Function.Injective (fun x => g (f x)) := by
  intro x y h
  exact hf (hg h)

end ProofReaderSmoke

