/- Synthetic regression controls, not additional OpenAI corpus coverage. -/
import Lean

namespace ProofReaderBreadth
universe u v

theorem implication (P Q R : Prop) (f : P → Q) (g : Q → R) : P → R :=
  fun h => g (f h)

theorem alternatives (P Q : Prop) : P ∨ Q → Q ∨ P := by
  intro h
  cases h with
  | inl hp => exact Or.inr hp
  | inr hq => exact Or.inl hq

theorem witnesses {α : Sort u} (P Q : α → Prop)
    (h : ∃ x, P x) (f : ∀ x, P x → Q x) : ∃ x, Q x := by
  obtain ⟨x, hx⟩ := h
  exact ⟨x, f x hx⟩

theorem equivalence (P Q : Prop) (h : P ↔ Q) : Q ↔ P :=
  Iff.intro h.mpr h.mp

theorem equality_chain {α : Sort u} (x y z : α)
    (hxy : x = y) (hyz : y = z) : z = x :=
  Eq.symm (Eq.trans hxy hyz)

theorem local_let (P Q : Prop) (h : P) (f : P → Q) : Q := by
  let witness : P := h
  have result : Q := f witness
  exact result

theorem induction (P : Nat → Prop) (base : P 0)
    (step : ∀ n, P n → P (n+1)) : ∀ n, P n :=
  Nat.rec base step

theorem list_induction {α : Type u} (xs : List α) :
    List.map (fun x => x) xs = xs := by
  induction xs with
  | nil => rfl
  | cons a xs ih => exact congrArg (List.cons a) ih

theorem dependent {α : Sort u} (P : α → Prop)
    (f : ∀ x, P x) (x : α) : P x := f x

theorem contradiction (P : Prop) (h : False) : P := False.elim h

end ProofReaderBreadth
