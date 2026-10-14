import Lean
import Lean.Util.CollectAxioms
namespace PRSmoke
theorem and_swap (P Q : Prop) : P ∧ Q → Q ∧ P := fun h => ⟨h.2, h.1⟩
theorem trans (P Q R : Prop) (a : P → Q) (b : Q → R) : P → R := fun h => b (a h)
end PRSmoke
