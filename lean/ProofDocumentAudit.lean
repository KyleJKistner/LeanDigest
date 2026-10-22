import ProofDocument

/-! # Document parser and scope controls

The fixtures below are not source proofs. They distinguish grammatical, scoped
text from a valid complete document. Native source mutations are run separately.
-/
namespace ProofReader.BezoutDocument.Audit
open ArithmeticEnglish EquationEnglish WitnessEnglish
noncomputable section
local instance {R : Type u} : DecidableEq R := Classical.decEq R

private def f : Frame := ⟨.var .x,.var .y,.var .z,.zero,.zero,.zero,.zero⟩
private def c : Chain := .pair .zero .zero
private def cancel : Cancellation := ⟨.one,.zero,.zero⟩
private def sample : Document := ⟨c,c,c,c,f,c,cancel,c,cancel,c,c,c,c,f⟩

example : read sample.render = some sample := read_render _
example : readBytes sample.render.toUTF8 = some sample := readBytes_render _
#guard (read sample.render).isSome
#guard sample.wellFormed
#guard (read (sample.render ++ "An extra conclusion.")).isNone
#guard (read (sample.render.replace "Zero case" "Zero cases")).isNone
#guard (read (sample.render.replace "x*y = z*(z+1)" "x*y = z*z")).isNone
#guard (read (sample.render.replace "g is nonzero" "g = 0")).isNone
#guard (read (sample.render.replace "Choose a with x = g*a" "Choose a with x = g+a")).isNone
#guard (read (sample.render.replace "gcdA(x, z)" "gcdA(z, x)")).isNone
#guard (read (sample.render.replace "gcdB(x, z)" "gcdB(z, x)")).isNone
#guard (read (sample.render.replace "a*c - d*b = 1" "a*c + d*b = 1")).isNone
#guard (read (String.ofList sample.render.toList.dropLast)).isNone
#guard (read (sample.render.replace "\n\n" "\n")).isNone
#guard (read (sample.render.replace "\n" "\r\n")).isNone
#guard (read "").isNone
#guard (read "Statement").isNone
#guard (readBytes ⟨#[255]⟩).isNone
#guard (readBytes ⟨#[192,175]⟩).isNone
#guard (fromFragments sample.fragments.tail).isNone
#guard (fromFragments sample.fragments.dropLast).isNone
#guard (fromFragments (sample.fragments.take 6 ++ sample.fragments.drop 7)).isNone
#guard (fromFragments (sample.fragments.take 16 ++ [.start])).isNone
#guard (fromFragments (sample.fragments ++ [.conclusion])).isNone
#guard (fromFragments (sample.fragments.take 3 ++ [.equation c] ++ sample.fragments.drop 3)).isNone
#guard (parseFragments 0 (fragmentsChars sample.fragments)).isNone
#guard (read (sample.render.replace "Euclidean domain" "field")).isNone
#guard !({sample with zeroFrame := {f with a := .var .a}}).wellFormed
#guard !({sample with zeroFrame := {f with c := .var .r}}).wellFormed
#guard !({sample with nonzeroFrame := {f with x := .one}}).wellFormed
#guard !({sample with nonzeroFrame := {f with y := .var .z}}).wellFormed
#guard !({sample with zeroAB := .pair (.var .s) .zero}).wellFormed

/-- The nonzero implication alone can be vacuously true, without a valid proof. -/
theorem nonzero_alone_is_insufficient {R : Type u} [EuclideanDomain R] :
    EuclideanDomain.gcd (0 : R) 0 ≠ 0 → sample.Nonzero (0 : R) 0 0 0 0 := by
  classical
  intro hn
  exact (hn (EuclideanDomain.gcd_eq_zero_iff.mpr ⟨rfl,rfl⟩)).elim

/-- The grammar and scope check accept this fixture, but its zero branch asserts
    a tuple whose determinant is zero, not one. Full semantics rejects it. -/
theorem grammatical_document_can_be_false {R : Type u} [EuclideanDomain R] : ¬ sample.Holds (0 : R) 0 0 := by
  classical
  intro h
  have hg : EuclideanDomain.gcd (0 : R) 0 = 0 :=
    EuclideanDomain.gcd_eq_zero_iff.mpr ⟨rfl,rfl⟩
  have hz := h.1 hg
  have hp := (WitnessEnglish.rendered_meaning (zeroEnvironment (0 : R) 0 0)
    sample.zeroFrame).mp hz.2.2.2.2.2
  have bad := hp.2.2.2
  simp [sample, f, Frame.det, Frame.db, Term.eval, zeroEnvironment, environment] at bad

#print axioms nonzero_alone_is_insufficient
#print axioms grammatical_document_can_be_false
end
end ProofReader.BezoutDocument.Audit
