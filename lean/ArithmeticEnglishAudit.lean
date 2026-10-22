import ArithmeticEnglish
open ProofReader.ArithmeticEnglish

namespace ProofReader.ArithmeticEnglishAudit
private def first : Cancellation :=
  ⟨.var .g, .add (.mul (.var .a) (.var .r)) (.mul (.var .d) (.var .s)), .one⟩
private def second : Cancellation :=
  ⟨.var .g, .mul (.var .a) (.var .y), .mul (.var .d) (.add (.var .z) .one)⟩

#guard first.render = "Since g is nonzero and (g * ((a * r) + (d * s))) = (g * 1), cancel g to obtain ((a * r) + (d * s)) = 1."
#guard second.render = "Since g is nonzero and (g * (a * y)) = (g * (d * (z + 1))), cancel g to obtain (a * y) = (d * (z + 1))."
#guard readCancellation first.render = some first
#guard readCancellation second.render = some second
#guard readBytes first.render.toUTF8 = some first
#guard readBytes ⟨#[255]⟩ = none
#guard readBytes ⟨#[192, 175]⟩ = none
#guard readCancellation "Since g is nonzero and (g * a) = (g * d), cancel g to obtain a = d." = some ⟨.var .g, .var .a, .var .d⟩
#guard readCancellation "Since g is nonzero and (g * a) = (g * d), cancel a to obtain a = d." = none
#guard readCancellation "Since g is nonzero and (g * a) = (g * d), cancel g to obtain d = a." = none
#guard readCancellation "Since g is nonzero and (g * a) = (g * d), cancel g to obtain a = 0." = none
#guard readCancellation "Since g is nonzero and (a * g) = (g * d), cancel g to obtain a = d." = none
#guard readCancellation "Since g is nonzero and (g + a) = (g * d), cancel g to obtain a = d." = none
#guard readCancellation "Since g is zero and (g * a) = (g * d), cancel g to obtain a = d." = none
#guard readCancellation "Since (g * a) = (g * d), cancel g to obtain a = d." = none
#guard readCancellation (first.render ++ " Therefore 0 = 1.") = none
#guard readCancellation (first.render ++ " ") = none
#guard readCancellation (" " ++ first.render) = none
#guard readCancellation ("\u200b" ++ first.render) = none
#guard readCancellation "Since g is nonzero and (g * a) = (g * d), cancel g to obtain a = d" = none
#guard readCancellation "Since g is nonzero and (g * a) = (g * d), cancel g to obtain a = d.." = none
#guard parseTerm 0 "a".toList = none
#guard parseTerm 1 "(a * r)".toList = none
#guard parseTerm 3 "((a * r) + (d * s))".toList = some (.add (.mul (.var .a) (.var .r)) (.mul (.var .d) (.var .s)), [])
#guard parseTerm 10 "(a / r)".toList = none
#guard parseTerm 10 "(a*r)".toList = none
#guard parseTerm 10 "(a * r".toList = none
#guard parseTerm 10 "(a * r]".toList = none
#guard parseTerm 10 "(а * r)".toList = none -- Cyrillic a
#guard parseTerm 10 "(a × r)".toList = none
#guard parseTerm 10 "b".toList = none -- outside this finite fragment
#guard parseTerm 10 "2".toList = none

private def integers : Interpretation Int where
  values := fun _ => 0
  zero := 0
  one := 1
  add := Int.add
  mul := Int.mul
  sub := Int.sub

/-- A true multiplied equality cannot authorize cancelling zero. -/
theorem zero_cancellation_rejected :
    ¬ TextMeans integers (Cancellation.mk (.var .g) .zero .one).render := by
  rw [rendered_meaning]
  intro h
  exact h.1 rfl

/-- The sentence asserts its premises, rather than proving a vacuous conditional. -/
theorem nonzero_is_asserted (env : Interpretation R) (c : Cancellation)
    (h : TextMeans env c.render) : c.factor.eval env ≠ env.zero :=
  ((rendered_meaning env c).mp h).1

#print axioms zero_cancellation_rejected
#print axioms nonzero_is_asserted
end ProofReader.ArithmeticEnglishAudit
