import EquationEnglish
namespace ProofReader.EquationEnglishAudit
open ArithmeticEnglish EquationEnglish
private def x : Term := .var .x
private def y : Term := .var .y
private def g : Term := .var .g
private def chain : Chain := .cons (.mul g x) (.pair (.mul g y) .one)
#guard EquationEnglish.read chain.render = some chain
#guard chain.length = 3
#guard chain.render = "We have (g * x) = (g * y) = 1."
#guard EquationEnglish.read "We have x = y." = some (.pair x y)
#guard EquationEnglish.read "We have x = y = g." = some (.cons x (.pair y g))
#guard EquationEnglish.read "We have x." = none
#guard EquationEnglish.read "We have x = ." = none
#guard EquationEnglish.read "We have = x = y." = none
#guard EquationEnglish.read "We have x = y" = none
#guard EquationEnglish.read "We have x = y. extra" = none
#guard EquationEnglish.read "We have x = y. = g." = none
#guard EquationEnglish.read "We have x = y.." = none
#guard EquationEnglish.read "We have x=y." = none
#guard EquationEnglish.read "We have x = y ." = none
#guard EquationEnglish.read "We have x = y = g" = none
#guard EquationEnglish.read "We have x = y = g. " = none
#guard EquationEnglish.read "We have x = y = g = ." = none
#guard EquationEnglish.read "We have x = y = g = 2." = none
#guard EquationEnglish.read "We have x = y = (g / 1)." = none
#guard EquationEnglish.read "We have x = y = (g * 1." = none
#guard EquationEnglish.read "We have x = у." = none -- Cyrillic character
#guard EquationEnglish.read "We have x = y.\u200b" = none
#guard EquationEnglish.read "We have x = y.\n" = none
#guard EquationEnglish.read "We have x = y; g = 1." = none
#guard EquationEnglish.readBytes ⟨#[255]⟩ = none
#guard EquationEnglish.readBytes chain.render.toUTF8 = some chain
#guard parseChain 0 chain.chars = none

private def integers : Interpretation Int := ⟨fun _ => 0, 0, 1, (· + ·), (· * ·), (· - ·)⟩
private def invalid : Chain := .cons .zero (.pair .one .zero)
/-- Matching endpoints do not certify the intermediate equality 0 = 1. -/
theorem equal_endpoints_false_middle :
    invalid.first.eval integers = invalid.last.eval integers ∧ ¬ invalid.Holds integers := by
  constructor
  · rfl
  · intro h
    have bad : (0 : Int) = 1 := h.1
    exact (by decide : (0 : Int) ≠ 1) bad

theorem parsed_false_chain :
    EquationEnglish.read invalid.render = some invalid ∧
    ¬ EquationEnglish.TextMeans integers invalid.render := by
  constructor
  · exact read_render _
  · intro h
    exact equal_endpoints_false_middle.2 ((EquationEnglish.rendered_meaning _ _).mp h)
#print axioms equal_endpoints_false_middle
#print axioms parsed_false_chain
end ProofReader.EquationEnglishAudit
