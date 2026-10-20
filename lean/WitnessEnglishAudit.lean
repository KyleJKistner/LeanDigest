import WitnessEnglish
namespace ProofReader.WitnessEnglishAudit
open ArithmeticEnglish WitnessEnglish
private def x : Term := .var .x
private def y : Term := .var .y
private def z : Term := .var .z
private def f : Frame := ⟨x,y,z,.one,y,.zero,.one⟩
#guard f.render = "The tuple (1, y, 0, 1) is a frame for (x, y, z)."
#guard WitnessEnglish.read f.render = some f
#guard WitnessEnglish.read "The tuple (1, y, 0) is a frame for (x, y, z)." = none
#guard WitnessEnglish.read "The tuple (1, y, 0, 1, x) is a frame for (x, y, z)." = none
#guard WitnessEnglish.read "The tuple (1, y, 0, 1) is a frame for (x, y)." = none
#guard WitnessEnglish.read "The tuple (1, y, 0, 1) is a frame for (x, y, z, g)." = none
#guard WitnessEnglish.read "The tuple (1, y, 0, 1) is a frame for (x, y, z)" = none
#guard WitnessEnglish.read "The tuple (1, y, 0, 1) is a frame for (x, y, z). extra" = none
#guard WitnessEnglish.read "The tuple (1, y, 0, 1) is a frame for (x, y, z). " = none
#guard WitnessEnglish.read "The tuple (1, y, 0, 1) is a frame for (x, y, z).." = none
#guard WitnessEnglish.read "The tuple (1,y,0,1) is a frame for (x, y, z)." = none
#guard WitnessEnglish.read "The tuple (1, y, 0, 2) is a frame for (x, y, z)." = none
#guard WitnessEnglish.read "The tuple (1, y, 0, -1) is a frame for (x, y, z)." = none
#guard WitnessEnglish.read "The tuple (1, y, 0, (0 - 1)) is a frame for (x, y, z)." =
  some {f with c := .sub .zero .one}
#guard WitnessEnglish.read "The tuple (1, y, 0, 1) is not a frame for (x, y, z)." = none
#guard WitnessEnglish.read "The tuple (1, y, 0, 1) is a frame for (x, y, z).\u200b" = none
#guard WitnessEnglish.read "The tuple (1, у, 0, 1) is a frame for (x, y, z)." = none
#guard WitnessEnglish.readBytes ⟨#[192,175]⟩ = none
#guard WitnessEnglish.readBytes f.render.toUTF8 = some f
#guard parseFrame 0 f.chars = none

private def integers : Interpretation Int := ⟨fun _ => 0, 0, 1, (· + ·), (· * ·), (· - ·)⟩
private def bad : Frame := ⟨.zero,.zero,.zero,.zero,.zero,.zero,.zero⟩
/-- The target has a frame, but this particular tuple fails the determinant. -/
theorem target_true_tuple_false :
    Goal integers .zero .zero .zero ∧ ¬ bad.Holds integers := by
  constructor
  · exact ⟨1,0,0,1,by decide,by decide,by decide,by decide⟩
  · intro h
    have wrong : (0 : Int) = 1 := h.2.2.2
    exact (by decide : (0 : Int) ≠ 1) wrong

theorem parsed_tuple_is_not_a_certificate :
    WitnessEnglish.read bad.render = some bad ∧ ¬ WitnessEnglish.TextMeans integers bad.render := by
  exact ⟨read_render _, fun h => target_true_tuple_false.2 ((WitnessEnglish.rendered_meaning _ _).mp h)⟩
#print axioms target_true_tuple_false
#print axioms parsed_tuple_is_not_a_certificate
end ProofReader.WitnessEnglishAudit
