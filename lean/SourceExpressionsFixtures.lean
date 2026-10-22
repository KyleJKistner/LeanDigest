import Lean

/- Deliberately small regression proofs. These are not OpenAI corpus results. -/
namespace SourceExpressionsFixtures
universe u

theorem dependent (n : Nat) (xs : Fin n → Nat) (_unused : Nat) (i : Fin n) :
    xs i = xs i := rfl

theorem witness (α : Type u) (P : α → Prop) (x : α) (h : P x) : ∃ y, P y := ⟨x, h⟩

theorem localFact (n : Nat) (_unused : Nat) : n = n := by
  have h : n = n := rfl
  exact h

theorem shadow (P Q : Prop) (h : P) : Q → P := by
  intro h
  assumption

theorem twoProofs (P : Prop) (_h : P) (h : P) : P := h

theorem localApplication (P Q : Prop) (f : P → Q) (h : P) : Q := f h

theorem implicitInstance {α : Type u} [Inhabited α] (_unused : Nat) :
    (default : α) = default := rfl

theorem localDefinitions (_unused : Nat) : True := by
  let n := 2
  let i : Fin n := ⟨0, by decide⟩
  have _h : i.val < n := i.isLt
  exact True.intro

theorem branches (P : Prop) : P ∨ ¬P := by
  classical
  by_cases h : P
  · exact Or.inl h
  · exact Or.inr h

theorem quantified (α : Type u) (P : α → Prop) (h : ∀ x, P x) : ∀ x : α, ∃ y, P y := by
  intro x
  exact ⟨x, h x⟩

theorem hiddenDependency (P Q : Prop) (f : P → Q) (h : P) : Q := by
  have result : Q := f h
  exact result

-- The name is intentionally repeated in the two distinct branch scopes.
theorem siblingNames (P Q : Prop) : (P → P) ∧ (Q → Q) :=
  ⟨fun h => h, fun h => h⟩

def proofDefinition (P : Prop) (h : P) : P := h

-- The two quantified propositions share the same expression-DAG node.
theorem sharedBinderNodes : (∀ n : Nat, n = n) ∧ (∀ n : Nat, n = n) :=
  ⟨fun _ => rfl, fun _ => rfl⟩

end SourceExpressionsFixtures
