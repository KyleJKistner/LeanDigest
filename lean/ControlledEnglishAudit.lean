import ControlledEnglish

/-!
# Independent adversarial audit of the controlled logical fragment

These countermodels prove that several tempting invalid explanations cannot
inhabit the indexed derivation type. They test semantic scope and direction,
not source-proof correspondence, string/HTML display, or human usefulness.
-/

namespace ProofReader.ControlledEnglish.Audit

def p : Formula 3 := .atom ⟨0, by decide⟩
def q : Formula 3 := .atom ⟨1, by decide⟩
def r : Formula 3 := .atom ⟨2, by decide⟩

theorem local_assumption_cannot_escape : ¬ Nonempty (Derivation [] p) := by
  intro ⟨derivation⟩
  have falseClaim := derivation.sound (fun _ => False) trivial
  exact falseClaim

theorem implication_cannot_be_reversed :
    ¬ Nonempty (Derivation [.impl p q, q] p) := by
  intro ⟨derivation⟩
  let atoms : Fin 3 → Prop := fun i => i.val = 1
  have context : ContextHolds atoms [.impl p q, q] := by
    simp [ContextHolds, Formula.eval, p, q, atoms]
  have falseClaim := derivation.sound atoms context
  simp [Formula.eval, p, atoms] at falseClaim

theorem a_disjunction_does_not_supply_one_selected_side :
    ¬ Nonempty (Derivation [.disj p q] p) := by
  intro ⟨derivation⟩
  let atoms : Fin 3 → Prop := fun i => i.val = 1
  have context : ContextHolds atoms [.disj p q] := by
    simp [ContextHolds, Formula.eval, p, q, atoms]
  have falseClaim := derivation.sound atoms context
  simp [Formula.eval, p, atoms] at falseClaim

theorem an_unrelated_disjunction_cannot_replace_the_witness :
    ¬ Nonempty (Derivation [p] (.disj q r)) := by
  intro ⟨derivation⟩
  let atoms : Fin 3 → Prop := fun i => i.val = 0
  have context : ContextHolds atoms [p] := by
    simp [ContextHolds, Formula.eval, p, atoms]
  have falseClaim := derivation.sound atoms context
  simp [Formula.eval, q, r, atoms] at falseClaim

theorem contradiction_requires_a_premise :
    ¬ Nonempty (Derivation ([] : List (Formula 3)) .falsum) := by
  intro ⟨derivation⟩
  exact derivation.sound (fun _ => False) trivial

-- Positive scope control: a branch may reuse an assumption from outside it.
example : Derivation [r] (.impl (.disj p q) (.conj (.disj q p) r)) :=
  casesWithOuterAssumption p q r

-- Positive nested-grammar control preserves the conjunction's scope.
example : readFormula 3 [.ifWord, .both, .atom 0, .andWord, .atom 1,
    .endWord, .thenWord, .atom 2, .endWord] = some (.impl (.conj p q) r) := by
  decide

-- Atom environment bounds are strict, including the empty environment.
example : readFormula 0 [.atom 0] = none := rfl
example : readFormula 3 [.atom 3] = none := rfl
example : readFormula 3 [.atom 999] = none := rfl

-- Missing, switched, and trailing delimiters cannot acquire a formula meaning.
example : readFormula 3 [.both, .atom 0, .andWord, .atom 1] = none := rfl
example : readFormula 3 [.ifWord, .atom 0, .orWord, .atom 1, .endWord] = none := rfl
example : readFormula 3 [.either, .atom 0, .thenWord, .atom 1, .endWord] = none := rfl
example : readFormula 3 [.atom 0, .endWord] = none := rfl
example : readFormula 3 [.falseWord, .atom 0] = none := rfl

-- A grammatical inference can still be invalid; parsing is not acceptance.
def reversedImplication : Sentence 3 := .two (.impl p q) q p

example : readSentence 3 reversedImplication.render = some reversedImplication :=
  readSentence_render reversedImplication

theorem grammatical_inference_is_not_automatically_sound :
    ¬ SentenceTextMeans (fun i : Fin 3 => i.val = 1) reversedImplication.render := by
  rw [rendered_sentence_meaning]
  simp [reversedImplication, Sentence.eval, Formula.eval, p, q]

-- Correct right-disjunction alignment depends on implicit argument ordering.
def chooseRight : Derivation [q] (.disj p q) := .orRight (.assumption .here)
example : chooseRight.rootRule? = some (.orRight p q) := rfl
example : (Rule.orRight p q).sentence = .one q (.disj p q) := rfl

-- Unsupported binder/assumption prose remains absent, rather than certified.
example : (conjunctionSwap p q).rootRule? = none := rfl
example : (Derivation.assumption (Hypothesis.here : Hypothesis [p] p)).rootRule? = none := rfl

-- Sentence punctuation, atom bounds, and complete consumption are checked too.
example : readSentence 3 [.fromWord, .atom 0, .inferWord, .atom 1] = none := rfl
example : readSentence 3 [.fromWord, .atom 0, .inferWord, .atom 3, .period] = none := rfl
example : readSentence 3 [.fromWord, .atom 0, .inferWord, .atom 1, .period,
    .fromWord, .atom 0, .inferWord, .atom 0, .period] = none := rfl

#print axioms local_assumption_cannot_escape
#print axioms implication_cannot_be_reversed
#print axioms a_disjunction_does_not_supply_one_selected_side
#print axioms an_unrelated_disjunction_cannot_replace_the_witness
#print axioms contradiction_requires_a_premise
#print axioms grammatical_inference_is_not_automatically_sound

end ProofReader.ControlledEnglish.Audit
