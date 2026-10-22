import ControlledEnglishText

/-!
# Adversarial checks for the canonical String boundary

These are separately compiled executable guards and kernel-checked semantic
countermodels, not an independent human audit. No test equates grammatical text with a justified step.
-/
namespace ProofReader.ControlledEnglish.TextAudit
open ProofReader.ControlledEnglish

private def p : Formula 2 := .atom ⟨0, by decide⟩
private def q : Formula 2 := .atom ⟨1, by decide⟩
private def projectRight : Rule 2 := .andRight p q

-- Every Token constructor and a multi-digit atom in one executable round trip.
example : Text.lex (Text.render [.atom 1024, .falseWord, .both, .andWord, .either,
    .orWord, .ifWord, .thenWord, .endWord, .fromWord, .withPremise, .inferWord,
    .period]) = some [.atom 1024, .falseWord, .both, .andWord, .either,
    .orWord, .ifWord, .thenWord, .endWord, .fromWord, .withPremise, .inferWord,
    .period] := Text.lex_render _

#guard Text.render projectRight.sentence.render =
    "From both @0 and @1 end infer @1 . "
#guard Text.accepts projectRight "From both @0 and @1 end infer @1 . " = true

-- Structurally valid but wrong for this particular inference.
#guard Text.accepts projectRight "From both @0 and @1 end infer @0 . " = false
#guard Text.accepts projectRight "From False infer @1 . " = false
#guard Text.accepts projectRight "From either @0 or @1 end infer @1 . " = false
#guard Text.accepts projectRight "From both @1 and @0 end infer @1 . " = false

-- No numeric aliases or confusable Unicode atom IDs.
#guard Text.lex "@00 " = none
#guard Text.lex "@01 " = none
#guard Text.lex "@+1 " = none
#guard Text.lex "@-1 " = none
#guard Text.lex "@1_0 " = none
#guard Text.lex "@١ " = none
#guard Text.lex "@１ " = none
#guard Text.lex "@ " = none
#guard Text.lex "@1x " = none

-- No empty words, alternative whitespace, keyword aliases or trailing garbage.
#guard Text.lex " From " = none
#guard Text.lex "From  @0 " = none
#guard Text.lex "From\t@0 " = none
#guard Text.lex "From\n@0 " = none
#guard Text.lex "From\u00a0@0 " = none
#guard Text.lex "from " = none
#guard Text.lex "Frоm " = none -- Cyrillic o
#guard Text.lex "From\u200b " = none
#guard Text.lex "<script> " = none
#guard Text.lex "." = none
#guard Text.lex ".  " = none
#guard Text.lex ". junk " = none

-- Invalid and overlong UTF-8 encodings do not enter the token parser.
#guard Text.lexBytes ⟨#[255]⟩ = none
#guard Text.lexBytes ⟨#[192, 175]⟩ = none
#guard Text.lexBytes ⟨#[237, 160, 128]⟩ = none
#guard Text.lexBytes ⟨#[226, 130]⟩ = none
#guard Text.readSentenceBytes 2
    (Text.renderBytes projectRight.sentence.render) = some projectRight.sentence

-- Syntax and bound checks at the complete reader, not merely at the lexer.
#guard Text.readFormula 0 "@0 " = none
#guard Text.readFormula 2 "@2 " = none
#guard Text.readFormula 2 "@20 " = none
#guard Text.readFormula 2 "both @0 or @1 end " = none
#guard Text.readFormula 2 "both @0 and @1 " = none
#guard Text.readFormula 2 "@0 @1 " = none
#guard Text.readSentence 2 "From @0 infer @1 " = none
#guard Text.readSentence 2 "From @0 infer @1 . @0 " = none
#guard Text.readSentence 2 "From @0 infer @1 ." = none
#guard Text.readSentence 2 "From @0 infer @1 . . " = none
#guard Text.readSentence 2 "From @0 with @1 with @0 with @1 infer @0 . " = none
#guard Text.lexChars 0 (Text.render [.atom 0]).toList = none

-- Well-formed text can still express a false inference. No validity flag is
-- inferred merely because parsing succeeded.
theorem grammatical_false_inference :
    Text.readSentence 2 (Text.render (Sentence.one p q).render) = some (.one p q) :=
  Text.readSentence_render _

theorem grammatical_does_not_imply_sound :
    ¬ Text.SentenceMeans (twoPropositions True False)
      (Text.render (Sentence.one p q).render) := by
  rintro ⟨sentence, parsed, valid⟩
  rw [grammatical_false_inference] at parsed
  cases parsed
  exact valid trivial

-- The canonical string and the original scoped typed node agree.
private def projection : Derivation [Formula.conj p q] q :=
  .andRight (.assumption .here)

example (atoms : Fin 2 → Prop) :
    Text.readSentence 2 (Text.render projectRight.sentence.render) = some projectRight.sentence ∧
      projectRight.sentence.conclusion = q ∧
      (ContextHolds atoms [Formula.conj p q] → ContextHolds atoms projectRight.sentence.premises) ∧
      Text.SentenceMeans atoms (Text.render projectRight.sentence.render) :=
  Text.accepted_root_aligned projection projectRight rfl _ (Text.accepts_render _) atoms

-- Implication-introduction prose remains unsupported, never counted as coverage.
example : (conjunctionSwap p q).rootRule? = none := rfl

-- A case split retains both branch obligations in the emitted sentence.
example : Text.readSentence 2
    (Text.render (Rule.orCases p q p).sentence.render) =
    some (.three (.disj p q) (.impl p p) (.impl q p) p) :=
  Text.readSentence_render _

#print axioms grammatical_false_inference
#print axioms grammatical_does_not_imply_sound
#eval Text.render projectRight.sentence.render
#eval Text.render (Rule.orCases p q p).sentence.render

end ProofReader.ControlledEnglish.TextAudit
