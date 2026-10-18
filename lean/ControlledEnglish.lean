import Lean

/-!
# A small checked language for logical explanations

This module is an isolated prototype. It does not certify the existing Python
printer, pretty-printed Lean formulas, HTML, or a link to an original proof path.
Atoms refer to typed propositions, never to strings supplied as mathematical
evidence. The semantic theorem applies to every interpretation of these atoms.
-/

namespace ProofReader.ControlledEnglish

inductive Formula (n : Nat) where
  | atom : Fin n → Formula n
  | falsum : Formula n
  | conj : Formula n → Formula n → Formula n
  | disj : Formula n → Formula n → Formula n
  | impl : Formula n → Formula n → Formula n
  deriving DecidableEq, Repr

def Formula.eval (atoms : Fin n → Prop) : Formula n → Prop
  | .atom i => atoms i
  | .falsum => False
  | .conj p q => p.eval atoms ∧ q.eval atoms
  | .disj p q => p.eval atoms ∨ q.eval atoms
  | .impl p q => p.eval atoms → q.eval atoms

def ContextHolds (atoms : Fin n → Prop) : List (Formula n) → Prop
  | [] => True
  | p :: rest => p.eval atoms ∧ ContextHolds atoms rest

/-- A scoped reference to an assumption. The newest binder has index zero. -/
inductive Hypothesis : List (Formula n) → Formula n → Type where
  | here : Hypothesis (p :: context) p
  | there : Hypothesis context p → Hypothesis (q :: context) p

def Hypothesis.index : Hypothesis context p → Nat
  | .here => 0
  | .there h => h.index + 1

theorem Hypothesis.sound {context : List (Formula n)} {p : Formula n}
    (h : Hypothesis context p) (atoms : Fin n → Prop) :
    ContextHolds atoms context → p.eval atoms := by
  induction h with
  | here => exact fun h => h.1
  | there _ ih => exact fun h => ih h.2

/-- Every constructor is a rule with its premises and conclusion in its type. -/
inductive Derivation : List (Formula n) → Formula n → Type where
  | assumption : Hypothesis context p → Derivation context p
  | andIntro : Derivation context p → Derivation context q →
      Derivation context (.conj p q)
  | andLeft : Derivation context (.conj p q) → Derivation context p
  | andRight : Derivation context (.conj p q) → Derivation context q
  | impIntro : Derivation (p :: context) q → Derivation context (.impl p q)
  | impApply : Derivation context (.impl p q) → Derivation context p →
      Derivation context q
  | orLeft : Derivation context p → Derivation context (.disj p q)
  | orRight : Derivation context q → Derivation context (.disj p q)
  | orCases : Derivation context (.disj p q) →
      Derivation (p :: context) r → Derivation (q :: context) r →
      Derivation context r
  | falseElim : Derivation context .falsum → Derivation context p

/-- Universal semantic soundness, including the separate scopes of both cases. -/
theorem Derivation.sound {context : List (Formula n)} {goal : Formula n}
    (derivation : Derivation context goal)
    (atoms : Fin n → Prop) : ContextHolds atoms context → goal.eval atoms := by
  induction derivation with
  | assumption h => exact h.sound atoms
  | andIntro _ _ ih₁ ih₂ => exact fun h => ⟨ih₁ h, ih₂ h⟩
  | andLeft _ ih => exact fun h => (ih h).1
  | andRight _ ih => exact fun h => (ih h).2
  | impIntro _ ih => exact fun h hp => ih ⟨hp, h⟩
  | impApply _ _ ih₁ ih₂ => exact fun h => ih₁ h (ih₂ h)
  | orLeft _ ih => exact fun h => Or.inl (ih h)
  | orRight _ ih => exact fun h => Or.inr (ih h)
  | orCases _ _ _ ih₀ ih₁ ih₂ =>
      intro h
      cases ih₀ h with
      | inl hp => exact ih₁ ⟨hp, h⟩
      | inr hq => exact ih₂ ⟨hq, h⟩
  | falseElim _ ih => exact fun h => False.elim (ih h)

/-- A source judgement needs a checked correspondence proof, not a prose label.
This structure alone does not establish that the judgement came from a named
declaration or a specific path in its original proof term. -/
structure SourceObligation (n : Nat) where
  atoms : Fin n → Prop
  context : List (Formula n)
  goal : Formula n
  originalJudgement : Prop
  correspondence : originalJudgement ↔
    (ContextHolds atoms context → goal.eval atoms)

theorem SourceObligation.discharge (obligation : SourceObligation n)
    (derivation : Derivation obligation.context obligation.goal) :
    obligation.originalJudgement :=
  obligation.correspondence.mpr (derivation.sound obligation.atoms)

/-- Tokens form the formal text boundary. `toString` below is presentation only.
Numeric atom references are checked against the finite proposition environment.
There is deliberately no constructor for an arbitrary formula string. -/
inductive Token where
  | atom (index : Nat)
  | falseWord
  | both
  | andWord
  | either
  | orWord
  | ifWord
  | thenWord
  | endWord
  | fromWord
  | withPremise
  | inferWord
  | period
  deriving DecidableEq, Repr

def Formula.render : Formula n → List Token
  | .atom i => [.atom i.val]
  | .falsum => [.falseWord]
  | .conj p q => [.both] ++ p.render ++ [.andWord] ++ q.render ++ [.endWord]
  | .disj p q => [.either] ++ p.render ++ [.orWord] ++ q.render ++ [.endWord]
  | .impl p q => [.ifWord] ++ p.render ++ [.thenWord] ++ q.render ++ [.endWord]

def Formula.height : Formula n → Nat
  | .atom _ => 1
  | .falsum => 1
  | .conj p q | .disj p q | .impl p q => max p.height q.height + 1

/-- Executable bounded parser; malformed delimiters and atom indices fail. -/
def parseFormula (n : Nat) : Nat → List Token → Option (Formula n × List Token)
  | 0, _ => none
  | _ + 1, .atom i :: rest =>
      if h : i < n then some (.atom ⟨i, h⟩, rest) else none
  | _ + 1, .falseWord :: rest => some (.falsum, rest)
  | fuel + 1, .both :: rest => do
      let (p, rest) ← parseFormula n fuel rest
      let .andWord :: rest := rest | none
      let (q, rest) ← parseFormula n fuel rest
      let .endWord :: rest := rest | none
      some (.conj p q, rest)
  | fuel + 1, .either :: rest => do
      let (p, rest) ← parseFormula n fuel rest
      let .orWord :: rest := rest | none
      let (q, rest) ← parseFormula n fuel rest
      let .endWord :: rest := rest | none
      some (.disj p q, rest)
  | fuel + 1, .ifWord :: rest => do
      let (p, rest) ← parseFormula n fuel rest
      let .thenWord :: rest := rest | none
      let (q, rest) ← parseFormula n fuel rest
      let .endWord :: rest := rest | none
      some (.impl p q, rest)
  | _ + 1, _ => none

/-- Parsing a rendered formula consumes exactly its own tokens. This stronger
suffix theorem also covers nested formulas and disallows silent truncation. -/
theorem parseFormula_render (formula : Formula n) (suffix : List Token)
    (fuel : Nat) (enough : formula.height ≤ fuel) :
    parseFormula n fuel (formula.render ++ suffix) = some (formula, suffix) := by
  induction formula generalizing fuel suffix with
  | atom i =>
      cases fuel with
      | zero => simp [Formula.height] at enough
      | succ fuel => simp [Formula.render, parseFormula, i.isLt]
  | falsum =>
      cases fuel with
      | zero => simp [Formula.height] at enough
      | succ fuel => rfl
  | conj p q ihp ihq =>
      cases fuel with
      | zero => simp [Formula.height] at enough
      | succ fuel =>
          have hp : p.height ≤ fuel := by simp [Formula.height] at enough; omega
          have hq : q.height ≤ fuel := by simp [Formula.height] at enough; omega
          simp [Formula.render, List.append_assoc, parseFormula, ihp _ _ hp, ihq _ _ hq]
  | disj p q ihp ihq =>
      cases fuel with
      | zero => simp [Formula.height] at enough
      | succ fuel =>
          have hp : p.height ≤ fuel := by simp [Formula.height] at enough; omega
          have hq : q.height ≤ fuel := by simp [Formula.height] at enough; omega
          simp [Formula.render, List.append_assoc, parseFormula, ihp _ _ hp, ihq _ _ hq]
  | impl p q ihp ihq =>
      cases fuel with
      | zero => simp [Formula.height] at enough
      | succ fuel =>
          have hp : p.height ≤ fuel := by simp [Formula.height] at enough; omega
          have hq : q.height ≤ fuel := by simp [Formula.height] at enough; omega
          simp [Formula.render, List.append_assoc, parseFormula, ihp _ _ hp, ihq _ _ hq]

def readFormula (n : Nat) (tokens : List Token) : Option (Formula n) := do
  let (formula, rest) ← parseFormula n tokens.length tokens
  if rest.isEmpty then some formula else none

theorem Formula.height_le_render_length (formula : Formula n) :
    formula.height ≤ formula.render.length := by
  induction formula with
  | atom _ => simp [Formula.height, Formula.render]
  | falsum => simp [Formula.height, Formula.render]
  | conj _ _ ihp ihq | disj _ _ ihp ihq | impl _ _ ihp ihq =>
      simp [Formula.height, Formula.render, List.length_append]
      omega

theorem readFormula_render (formula : Formula n) :
    readFormula n formula.render = some formula := by
  have h := parseFormula_render formula [] formula.render.length
    formula.height_le_render_length
  simp only [List.append_nil] at h
  simp [readFormula, h]

/-- Formal meaning of a controlled formula token stream. -/
def FormulaTextMeans (atoms : Fin n → Prop) (tokens : List Token) : Prop :=
  ∃ formula, readFormula n tokens = some formula ∧ formula.eval atoms

theorem rendered_formula_meaning (atoms : Fin n → Prop) (formula : Formula n) :
    FormulaTextMeans atoms formula.render ↔ formula.eval atoms := by
  simp [FormulaTextMeans, readFormula_render]

/-- A declarative inference sentence with one, two, or three explicit premises.
Implication formulas can express the obligations in separate case branches.
This is not an imperative proof script or a translation of arbitrary prose. -/
inductive Sentence (n : Nat) where
  | one : Formula n → Formula n → Sentence n
  | two : Formula n → Formula n → Formula n → Sentence n
  | three : Formula n → Formula n → Formula n → Formula n → Sentence n
  deriving DecidableEq, Repr

def Sentence.eval (atoms : Fin n → Prop) : Sentence n → Prop
  | .one p conclusion => p.eval atoms → conclusion.eval atoms
  | .two p q conclusion => p.eval atoms → q.eval atoms → conclusion.eval atoms
  | .three p q r conclusion =>
      p.eval atoms → q.eval atoms → r.eval atoms → conclusion.eval atoms

def Sentence.premises : Sentence n → List (Formula n)
  | .one p _ => [p]
  | .two p q _ => [p, q]
  | .three p q r _ => [p, q, r]

def Sentence.conclusion : Sentence n → Formula n
  | .one _ conclusion | .two _ _ conclusion | .three _ _ _ conclusion => conclusion

def Sentence.render : Sentence n → List Token
  | .one p conclusion =>
      [.fromWord] ++ p.render ++ [.inferWord] ++ conclusion.render ++ [.period]
  | .two p q conclusion =>
      [.fromWord] ++ p.render ++ [.withPremise] ++ q.render ++
        [.inferWord] ++ conclusion.render ++ [.period]
  | .three p q r conclusion =>
      [.fromWord] ++ p.render ++ [.withPremise] ++ q.render ++
        [.withPremise] ++ r.render ++ [.inferWord] ++ conclusion.render ++ [.period]

def Sentence.height : Sentence n → Nat
  | .one p conclusion => max p.height conclusion.height
  | .two p q conclusion => max p.height (max q.height conclusion.height)
  | .three p q r conclusion => max p.height (max q.height (max r.height conclusion.height))

/-- The sentence parser deliberately has a finite grammar, never a raw-string
escape. Every premise and the conclusion use the checked formula parser. -/
def parseSentence (n fuel : Nat) (tokens : List Token) :
    Option (Sentence n × List Token) := do
  let .fromWord :: rest := tokens | none
  let (p, rest) ← parseFormula n fuel rest
  match rest with
  | .inferWord :: rest =>
      let (conclusion, rest) ← parseFormula n fuel rest
      let .period :: rest := rest | none
      some (.one p conclusion, rest)
  | .withPremise :: rest =>
      let (q, rest) ← parseFormula n fuel rest
      match rest with
      | .inferWord :: rest =>
          let (conclusion, rest) ← parseFormula n fuel rest
          let .period :: rest := rest | none
          some (.two p q conclusion, rest)
      | .withPremise :: rest =>
          let (r, rest) ← parseFormula n fuel rest
          let .inferWord :: rest := rest | none
          let (conclusion, rest) ← parseFormula n fuel rest
          let .period :: rest := rest | none
          some (.three p q r conclusion, rest)
      | _ => none
  | _ => none

theorem parseSentence_render (sentence : Sentence n) (suffix : List Token)
    (fuel : Nat) (enough : sentence.height ≤ fuel) :
    parseSentence n fuel (sentence.render ++ suffix) = some (sentence, suffix) := by
  cases sentence with
  | one p conclusion =>
      have hp : p.height ≤ fuel := by simp [Sentence.height] at enough; omega
      have hc : conclusion.height ≤ fuel := by simp [Sentence.height] at enough; omega
      simp [Sentence.render, List.append_assoc, parseSentence,
        parseFormula_render p _ _ hp, parseFormula_render conclusion _ _ hc]
  | two p q conclusion =>
      have hp : p.height ≤ fuel := by simp [Sentence.height] at enough; omega
      have hq : q.height ≤ fuel := by simp [Sentence.height] at enough; omega
      have hc : conclusion.height ≤ fuel := by simp [Sentence.height] at enough; omega
      simp [Sentence.render, List.append_assoc, parseSentence,
        parseFormula_render p _ _ hp, parseFormula_render q _ _ hq,
        parseFormula_render conclusion _ _ hc]
  | three p q r conclusion =>
      have hp : p.height ≤ fuel := by simp [Sentence.height] at enough; omega
      have hq : q.height ≤ fuel := by simp [Sentence.height] at enough; omega
      have hr : r.height ≤ fuel := by simp [Sentence.height] at enough; omega
      have hc : conclusion.height ≤ fuel := by simp [Sentence.height] at enough; omega
      simp [Sentence.render, List.append_assoc, parseSentence,
        parseFormula_render p _ _ hp, parseFormula_render q _ _ hq,
        parseFormula_render r _ _ hr, parseFormula_render conclusion _ _ hc]

theorem Sentence.height_le_render_length (sentence : Sentence n) :
    sentence.height ≤ sentence.render.length := by
  cases sentence with
  | one p conclusion =>
      have := p.height_le_render_length
      have := conclusion.height_le_render_length
      simp [Sentence.height, Sentence.render, List.length_append]
      omega
  | two p q conclusion =>
      have := p.height_le_render_length
      have := q.height_le_render_length
      have := conclusion.height_le_render_length
      simp [Sentence.height, Sentence.render, List.length_append]
      omega
  | three p q r conclusion =>
      have := p.height_le_render_length
      have := q.height_le_render_length
      have := r.height_le_render_length
      have := conclusion.height_le_render_length
      simp [Sentence.height, Sentence.render, List.length_append]
      omega

def readSentence (n : Nat) (tokens : List Token) : Option (Sentence n) := do
  let (sentence, rest) ← parseSentence n tokens.length tokens
  if rest.isEmpty then some sentence else none

theorem readSentence_render (sentence : Sentence n) :
    readSentence n sentence.render = some sentence := by
  have h := parseSentence_render sentence [] sentence.render.length
    sentence.height_le_render_length
  simp only [List.append_nil] at h
  simp [readSentence, h]

def SentenceTextMeans (atoms : Fin n → Prop) (tokens : List Token) : Prop :=
  ∃ sentence, readSentence n tokens = some sentence ∧ sentence.eval atoms

/-- The controlled sentence tokens mean exactly their declared inference. -/
theorem rendered_sentence_meaning (atoms : Fin n → Prop) (sentence : Sentence n) :
    SentenceTextMeans atoms sentence.render ↔ sentence.eval atoms := by
  simp [SentenceTextMeans, readSentence_render]

/-- Supported declarative rule explanations. Arbitrary parsed sentences do not
become valid rules merely because they are grammatical. -/
inductive Rule (n : Nat) where
  | andIntro : Formula n → Formula n → Rule n
  | andLeft : Formula n → Formula n → Rule n
  | andRight : Formula n → Formula n → Rule n
  | impApply : Formula n → Formula n → Rule n
  | orLeft : Formula n → Formula n → Rule n
  | orRight : Formula n → Formula n → Rule n
  | orCases : Formula n → Formula n → Formula n → Rule n
  | falseElim : Formula n → Rule n
  deriving DecidableEq, Repr

def Rule.sentence : Rule n → Sentence n
  | .andIntro p q => .two p q (.conj p q)
  | .andLeft p q => .one (.conj p q) p
  | .andRight p q => .one (.conj p q) q
  | .impApply p q => .two (.impl p q) p q
  | .orLeft p q => .one p (.disj p q)
  | .orRight p q => .one q (.disj p q)
  | .orCases p q r => .three (.disj p q) (.impl p r) (.impl q r) r
  | .falseElim p => .one .falsum p

theorem Rule.sound (rule : Rule n) (atoms : Fin n → Prop) :
    rule.sentence.eval atoms := by
  cases rule with
  | andIntro _ _ => exact fun hp hq => ⟨hp, hq⟩
  | andLeft _ _ => exact fun hpq => hpq.1
  | andRight _ _ => exact fun hpq => hpq.2
  | impApply _ _ => exact fun hpq hp => hpq hp
  | orLeft _ _ => exact fun hp => Or.inl hp
  | orRight _ _ => exact fun hq => Or.inr hq
  | orCases _ _ _ => exact fun hpq hpr hqr => hpq.elim hpr hqr
  | falseElim _ => exact fun h => False.elim h

/-- This theorem connects the emitted inference tokens to logical validity.
It is stronger than byte regeneration, and narrower than arbitrary English. -/
theorem Rule.rendered_sound (rule : Rule n) (atoms : Fin n → Prop) :
    SentenceTextMeans atoms rule.sentence.render :=
  (rendered_sentence_meaning atoms rule.sentence).mpr (rule.sound atoms)

/-- Local sentence extraction is tied to the typed constructor and its exact
formulas. Assumption references and binder-introduction prose are deliberately
unsupported here; their absence cannot be counted as complete proof prose. -/
def Derivation.rootRule? {context : List (Formula n)} {goal : Formula n} :
    Derivation context goal → Option (Rule n)
  | .assumption _ => none
  | @andIntro _ _ p q _ _ => some (.andIntro p q)
  | @andLeft _ _ p q _ => some (.andLeft p q)
  | @andRight _ _ p q _ => some (.andRight p q)
  | .impIntro _ => none
  | @impApply _ _ p q _ _ => some (.impApply p q)
  | @orLeft _ _ p q _ => some (.orLeft p q)
  | @orRight _ _ q p _ => some (.orRight p q)
  | @orCases _ _ p q r _ _ _ => some (.orCases p q r)
  | @falseElim _ _ p _ => some (.falseElim p)

/-- An extracted local sentence has exactly the typed source node's conclusion;
the premises it mentions are justified by that node's children in their scopes.
This relation is internal to this IR, not a theorem about imported snapshots. -/
theorem Derivation.rootRule?_aligned {context : List (Formula n)} {goal : Formula n}
    (derivation : Derivation context goal) (rule : Rule n)
    (found : derivation.rootRule? = some rule) (atoms : Fin n → Prop) :
    rule.sentence.conclusion = goal ∧
      (ContextHolds atoms context → ContextHolds atoms rule.sentence.premises) := by
  cases derivation with
  | assumption _ => cases found
  | andIntro left right =>
      cases found
      exact ⟨rfl, fun h => ⟨left.sound atoms h, right.sound atoms h, trivial⟩⟩
  | andLeft child =>
      cases found
      exact ⟨rfl, fun h => ⟨child.sound atoms h, trivial⟩⟩
  | andRight child =>
      cases found
      exact ⟨rfl, fun h => ⟨child.sound atoms h, trivial⟩⟩
  | impIntro _ => cases found
  | impApply fn arg =>
      cases found
      exact ⟨rfl, fun h => ⟨fn.sound atoms h, arg.sound atoms h, trivial⟩⟩
  | orLeft child =>
      cases found
      exact ⟨rfl, fun h => ⟨child.sound atoms h, trivial⟩⟩
  | orRight child =>
      cases found
      exact ⟨rfl, fun h => ⟨child.sound atoms h, trivial⟩⟩
  | orCases disjunction left right =>
      cases found
      exact ⟨rfl, fun h => ⟨disjunction.sound atoms h,
        (fun hp => left.sound atoms ⟨hp, h⟩),
        (fun hq => right.sound atoms ⟨hq, h⟩), trivial⟩⟩
  | falseElim child =>
      cases found
      exact ⟨rfl, fun h => ⟨child.sound atoms h, trivial⟩⟩

def Token.toString : Token → String
  | .atom i => "claim[" ++ Nat.repr i ++ "]"
  | .falseWord => "False"
  | .both => "both ("
  | .andWord => ") and ("
  | .either => "either ("
  | .orWord => ") or ("
  | .ifWord => "if ("
  | .thenWord => "), then ("
  | .endWord => ")"
  | .fromWord => "From"
  | .withPremise => ", together with"
  | .inferWord => ", infer"
  | .period => "."

/-- Convenience display only: the proved parser consumes `List Token`, not this
String. No claim about string, escaping, browser, or HTML fidelity is made. -/
def Formula.display (formula : Formula n) : String :=
  String.intercalate " " (formula.render.map Token.toString)

def Sentence.display (sentence : Sentence n) : String :=
  String.intercalate " " (sentence.render.map Token.toString)

def conjunctionSwap (p q : Formula n) :
    Derivation [] (.impl (.conj p q) (.conj q p)) :=
  .impIntro (.andIntro (.andRight (.assumption .here))
    (.andLeft (.assumption .here)))

def disjunctionSwap (p q : Formula n) :
    Derivation [] (.impl (.disj p q) (.disj q p)) :=
  .impIntro (.orCases (.assumption .here)
    (.orRight (.assumption .here)) (.orLeft (.assumption .here)))

/-- Both disjunction branches may use the outer assumption but cannot exchange
their respective local assumptions: these are different indexed contexts. -/
def casesWithOuterAssumption (p q r : Formula n) :
    Derivation [r] (.impl (.disj p q) (.conj (.disj q p) r)) :=
  .impIntro (.andIntro
    (.orCases (.assumption .here)
      (.orRight (.assumption .here)) (.orLeft (.assumption .here)))
    (.assumption (.there .here)))

def firstAtom : Formula 2 := .atom ⟨0, by decide⟩
def secondAtom : Formula 2 := .atom ⟨1, by decide⟩

def twoPropositions (p q : Prop) (i : Fin 2) : Prop :=
  if i.val = 0 then p else q

/-- The atom dictionary and original judgement are typed Lean propositions.
The bridge below is checked by Lean; a source label would not fill this field. -/
def swapObligation (p q : Prop) : SourceObligation 2 where
  atoms := twoPropositions p q
  context := []
  goal := .impl (.conj firstAtom secondAtom) (.conj secondAtom firstAtom)
  originalJudgement := p ∧ q → q ∧ p
  correspondence := by
    change (p ∧ q → q ∧ p) ↔ (True → (p ∧ q → q ∧ p))
    exact ⟨fun h _ => h, fun h => h trivial⟩

theorem discharge_swap (p q : Prop) : p ∧ q → q ∧ p :=
  (swapObligation p q).discharge (conjunctionSwap firstAtom secondAtom)

example : readFormula 2 [Token.atom 2] = none := rfl
example : readFormula 2 [Token.both, .atom 0, .orWord, .atom 1, .endWord] = none := rfl
example : readFormula 2 [Token.atom 0, .atom 1] = none := rfl
example : readSentence 2 [Token.fromWord, .atom 0, .inferWord, .atom 1] = none := rfl
example : readSentence 2
    [Token.fromWord, .atom 0, .inferWord, .atom 1, .period, .atom 0] = none := rfl
example : (conjunctionSwap firstAtom secondAtom).rootRule? = none := rfl

/-- Being grammatical is not being justified. This sentence parses, but its
inference fails when the first atom is true and the second is false. -/
example : readSentence 2 (Sentence.one firstAtom secondAtom).render =
    some (Sentence.one firstAtom secondAtom) := readSentence_render _
example : ¬ (Sentence.one firstAtom secondAtom).eval (twoPropositions True False) := by
  intro inference
  exact inference trivial

#eval (Rule.orCases firstAtom secondAtom firstAtom).sentence.display

#print axioms Derivation.sound
#print axioms SourceObligation.discharge
#print axioms parseFormula_render
#print axioms readFormula_render
#print axioms rendered_formula_meaning
#print axioms Rule.sound
#print axioms parseSentence_render
#print axioms readSentence_render
#print axioms rendered_sentence_meaning
#print axioms Rule.rendered_sound
#print axioms Derivation.rootRule?_aligned
#print axioms discharge_swap

end ProofReader.ControlledEnglish
