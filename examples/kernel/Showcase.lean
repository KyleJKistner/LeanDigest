import Lean
import Lean.Util.CollectAxioms
namespace PRShowcase
theorem injective_comp {X Y Z : Type} (f : X → Y) (g : Y → Z)
    (hf : Function.Injective f) (hg : Function.Injective g) :
    Function.Injective (fun x => g (f x)) := by
  intro x y h
  exact hf (hg h)
theorem witnessed (P : Nat → Prop) (n : Nat) (h : P n) : ∃ k, P k := ⟨n, h⟩
theorem alternatives (P Q R : Prop) (h : P ∨ Q) (hp : P → R) (hq : Q → R) : R := Or.elim h hp hq
end PRShowcase
