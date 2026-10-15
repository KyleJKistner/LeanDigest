import Lean
namespace BatchAcceptance.Logic

theorem implication (P Q R : Prop) (hp : P → Q) (hq : Q → R) : P → R :=
  fun h => hq (hp h)

theorem cases (P Q R : Prop) (h : P ∨ Q) (hp : P → R) (hq : Q → R) : R := by
  cases h with
  | inl p => exact hp p
  | inr q => exact hq q

theorem choose {α : Type} (P : α → Prop) (Q : Prop)
    (h : ∃ x, P x) (use : ∀ x, P x → Q) : Q := by
  rcases h with ⟨x, hx⟩
  exact use x hx

def proof_definition : True := True.intro
opaque opaque_proof : True := True.intro
end BatchAcceptance.Logic
