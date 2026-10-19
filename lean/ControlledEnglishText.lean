import ControlledEnglish
import Std.Data.String.ToNat

/-!
# Canonical controlled English at the String boundary

An additional, deliberately strict surface language. This is NOT the legacy
`Sentence.display` printer. Atom `@i` means entry i in the same typed proposition
environment used by `Formula.eval`. No arbitrary display labels are accepted.

Each word is followed by exactly one ASCII space, including the final period.
Rejecting noncanonical whitespace makes the serialized object unambiguous.
-/
namespace ProofReader.ControlledEnglish
namespace Text

/-- Finite English keywords and canonical decimal proposition references. -/
def word : Token → List Char
  | .atom i => '@' :: i.repr.toList
  | .falseWord => "False".toList
  | .both => "both".toList
  | .andWord => "and".toList
  | .either => "either".toList
  | .orWord => "or".toList
  | .ifWord => "if".toList
  | .thenWord => "then".toList
  | .endWord => "end".toList
  | .fromWord => "From".toList
  | .withPremise => "with".toList
  | .inferWord => "infer".toList
  | .period => ".".toList

/-- Reject leading zeroes, underscores, signs, and other numeric aliases. -/
def readWord : List Char → Option Token
  | '@' :: chars => do
      let i ← (String.ofList chars).toNat?
      if i.repr.toList = chars then some (.atom i) else none
  | chars =>
      match String.ofList chars with
      | "False" => some .falseWord
      | "both" => some .both
      | "and" => some .andWord
      | "either" => some .either
      | "or" => some .orWord
      | "if" => some .ifWord
      | "then" => some .thenWord
      | "end" => some .endWord
      | "From" => some .fromWord
      | "with" => some .withPremise
      | "infer" => some .inferWord
      | "." => some .period
      | _ => none

theorem readWord_word (token : Token) : readWord (word token) = some token := by
  cases token with
  | atom i =>
      simp only [word, readWord]
      rw [String.ofList_toList, Nat.toNat?_repr]
      simp
  | falseWord | both | andWord | either | orWord | ifWord | thenWord | endWord |
      fromWord | withPremise | inferWord | period => rfl

/-- Consume exactly one mandatory space-terminated word. -/
def takeWord : List Char → Option (List Char × List Char)
  | [] => none
  | c :: rest =>
      if c = ' ' then some ([], rest) else do
        let (head, tail) ← takeWord rest
        some (c :: head, tail)

theorem takeWord_delimited (head tail : List Char) (h : ' ' ∉ head) :
    takeWord (head ++ ' ' :: tail) = some (head, tail) := by
  induction head with
  | nil => simp [takeWord]
  | cons c rest ih =>
      have hc : c ≠ ' ' := by intro eq; subst c; simp at h
      have hr : ' ' ∉ rest := by intro hm; exact h (List.mem_cons_of_mem c hm)
      simp [takeWord, hc, ih hr]

-- The decimal representation lemma below is discharged using the pinned
-- standard library's digit-property theorem, not an example enumeration.
theorem word_no_space (token : Token) : ' ' ∉ word token := by
  cases token with
  | atom i =>
      simp only [word, List.mem_cons, Char.reduceEq, false_or]
      intro h
      have hd := Nat.isDigit_of_mem_toDigits (by decide : 0 < 10)
        (by decide : 10 ≤ 10) (by simpa [Nat.repr] using h)
      simp at hd
  | falseWord | both | andWord | either | orWord | ifWord | thenWord | endWord |
      fromWord | withPremise | inferWord | period => decide

def renderChars : List Token → List Char
  | [] => []
  | token :: rest => word token ++ ' ' :: renderChars rest

theorem renderChars_cons_ne_nil (token : Token) (rest : List Token) :
    renderChars (token :: rest) ≠ [] := by
  intro h
  have hl := congrArg List.length h
  simp [renderChars] at hl

theorem length_le_renderChars (tokens : List Token) :
    tokens.length ≤ (renderChars tokens).length := by
  induction tokens with
  | nil => simp [renderChars]
  | cons _ _ ih => simp [renderChars]; omega

/-- Fuel is explicit. Insufficient fuel, unknown words, or truncation fail. -/
def lexChars (fuel : Nat) (chars : List Char) : Option (List Token) :=
  if chars = [] then some [] else
  match fuel with
  | 0 => none
  | fuel + 1 => do
      let (head, tail) ← takeWord chars
      let token ← readWord head
      let rest ← lexChars fuel tail
      some (token :: rest)

theorem lexChars_renderChars (tokens : List Token) (fuel : Nat)
    (enough : tokens.length ≤ fuel) :
    lexChars fuel (renderChars tokens) = some tokens := by
  induction tokens generalizing fuel with
  | nil => cases fuel <;> simp [renderChars, lexChars]
  | cons token rest ih =>
      cases fuel with
      | zero => simp at enough
      | succ fuel =>
          have hr : rest.length ≤ fuel := by simpa using enough
          rw [lexChars, ite_eq_right (renderChars_cons_ne_nil token rest)]
          simp only [renderChars, takeWord_delimited _ _ (word_no_space token)]
          dsimp
          rw [readWord_word]
          dsimp
          rw [ih fuel hr]
          rfl

/-- The canonical String, not an unchecked duplicate in another language. -/
def render (tokens : List Token) : String := String.ofList (renderChars tokens)

def lex (text : String) : Option (List Token) :=
  lexChars text.toList.length text.toList

/-- Universal String round trip: every token, every finite token sequence. -/
theorem lex_render (tokens : List Token) : lex (render tokens) = some tokens := by
  simp only [lex, render, String.toList_ofList]
  exact lexChars_renderChars tokens _ (length_le_renderChars tokens)

theorem render_injective {a b : List Token} (h : render a = render b) : a = b := by
  have := congrArg lex h
  simpa only [lex_render, Option.some.injEq] using this

def readFormula (n : Nat) (text : String) : Option (Formula n) := do
  let tokens ← lex text
  ControlledEnglish.readFormula n tokens

def readSentence (n : Nat) (text : String) : Option (Sentence n) := do
  let tokens ← lex text
  ControlledEnglish.readSentence n tokens

theorem readFormula_render (formula : Formula n) :
    readFormula n (render formula.render) = some formula := by
  simp [readFormula, lex_render, ControlledEnglish.readFormula_render]

theorem readSentence_render (sentence : Sentence n) :
    readSentence n (render sentence.render) = some sentence := by
  simp [readSentence, lex_render, ControlledEnglish.readSentence_render]

def FormulaMeans (atoms : Fin n → Prop) (text : String) : Prop :=
  ∃ formula, readFormula n text = some formula ∧ formula.eval atoms

def SentenceMeans (atoms : Fin n → Prop) (text : String) : Prop :=
  ∃ sentence, readSentence n text = some sentence ∧ sentence.eval atoms

theorem rendered_formula_meaning (atoms : Fin n → Prop) (formula : Formula n) :
    FormulaMeans atoms (render formula.render) ↔ formula.eval atoms := by
  simp [FormulaMeans, readFormula_render]

theorem rendered_sentence_meaning (atoms : Fin n → Prop) (sentence : Sentence n) :
    SentenceMeans atoms (render sentence.render) ↔ sentence.eval atoms := by
  simp [SentenceMeans, readSentence_render]

/-- A parsed sentence is not automatically a valid rule. This gate checks exact
alignment with an already typed rule instance, including all its atom indices. -/
def accepts (rule : Rule n) (text : String) : Bool :=
  decide (readSentence n text = some rule.sentence)

theorem accepts_iff (rule : Rule n) (text : String) :
    accepts rule text = true ↔ readSentence n text = some rule.sentence := by
  simp [accepts]

theorem accepts_render (rule : Rule n) :
    accepts rule (render rule.sentence.render) = true := by
  simp [accepts, readSentence_render]

theorem accepted_rule_sound (rule : Rule n) (text : String)
    (accepted : accepts rule text = true) (atoms : Fin n → Prop) :
    SentenceMeans atoms text :=
  ⟨rule.sentence, (accepts_iff rule text).mp accepted, rule.sound atoms⟩

/-- Local end-to-end contract within the typed IR: accepted String, exact goal,
scoped premises, and validity. It does not import an arbitrary Lean proof. -/
theorem accepted_root_aligned {context : List (Formula n)} {goal : Formula n}
    (derivation : Derivation context goal) (rule : Rule n)
    (found : derivation.rootRule? = some rule) (text : String)
    (accepted : accepts rule text = true) (atoms : Fin n → Prop) :
    readSentence n text = some rule.sentence ∧
      rule.sentence.conclusion = goal ∧
      (ContextHolds atoms context → ContextHolds atoms rule.sentence.premises) ∧
      SentenceMeans atoms text := by
  have aligned := derivation.rootRule?_aligned rule found atoms
  exact ⟨(accepts_iff rule text).mp accepted, aligned.1, aligned.2,
    accepted_rule_sound rule text accepted atoms⟩

/-- The serialized boundary also includes the exact UTF-8 bytes. -/
theorem decodeUTF8_encode (text : String) :
    String.fromUTF8? text.toUTF8 = some text := by
  cases text with
  | ofByteArray bytes valid => simp [String.fromUTF8?, String.fromUTF8, String.toUTF8, valid]

def renderBytes (tokens : List Token) : ByteArray := (render tokens).toUTF8

def lexBytes (bytes : ByteArray) : Option (List Token) := do
  let text ← String.fromUTF8? bytes
  lex text

theorem lexBytes_renderBytes (tokens : List Token) :
    lexBytes (renderBytes tokens) = some tokens := by
  unfold lexBytes renderBytes
  rw [decodeUTF8_encode]
  dsimp
  exact lex_render tokens

theorem renderBytes_injective {a b : List Token}
    (h : renderBytes a = renderBytes b) : a = b := by
  have := congrArg lexBytes h
  simpa only [lexBytes_renderBytes, Option.some.injEq] using this

def readSentenceBytes (n : Nat) (bytes : ByteArray) : Option (Sentence n) := do
  let tokens ← lexBytes bytes
  ControlledEnglish.readSentence n tokens

theorem readSentenceBytes_render (sentence : Sentence n) :
    readSentenceBytes n (renderBytes sentence.render) = some sentence := by
  simp [readSentenceBytes, lexBytes_renderBytes, ControlledEnglish.readSentence_render]

def SentenceBytesMean (atoms : Fin n → Prop) (bytes : ByteArray) : Prop :=
  ∃ sentence, readSentenceBytes n bytes = some sentence ∧ sentence.eval atoms

theorem rendered_bytes_meaning (atoms : Fin n → Prop) (sentence : Sentence n) :
    SentenceBytesMean atoms (renderBytes sentence.render) ↔ sentence.eval atoms := by
  simp [SentenceBytesMean, readSentenceBytes_render]

theorem rendered_rule_bytes_sound (rule : Rule n) (atoms : Fin n → Prop) :
    SentenceBytesMean atoms (renderBytes rule.sentence.render) :=
  (rendered_bytes_meaning atoms rule.sentence).mpr (rule.sound atoms)

#print axioms decodeUTF8_encode
#print axioms lexBytes_renderBytes
#print axioms renderBytes_injective
#print axioms readSentenceBytes_render
#print axioms rendered_bytes_meaning
#print axioms rendered_rule_bytes_sound
#print axioms lex_render
#print axioms render_injective
#print axioms readFormula_render
#print axioms readSentence_render
#print axioms rendered_formula_meaning
#print axioms rendered_sentence_meaning
#print axioms accepted_rule_sound
#print axioms accepted_root_aligned

end Text
end ProofReader.ControlledEnglish
