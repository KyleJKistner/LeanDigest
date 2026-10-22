import ArithmeticEnglish

/-!
# Equation chains

Every adjacent equality in the printed calculation is asserted. The semantics
is not just equality of the two endpoints, nor an implication whose premise
could be false. The source importer supplies each original proof separately.
-/
namespace ProofReader.EquationEnglish
open ArithmeticEnglish

inductive Chain where
  | pair : Term → Term → Chain
  | cons : Term → Chain → Chain
  deriving DecidableEq, Repr, Inhabited

def Chain.first : Chain → Term
  | .pair a _ | .cons a _ => a

def Chain.last : Chain → Term
  | .pair _ b => b
  | .cons _ rest => rest.last

def Chain.length : Chain → Nat
  | .pair _ _ => 2
  | .cons _ rest => rest.length + 1

def Chain.Holds (env : Interpretation R) : Chain → Prop
  | .pair a b => a.eval env = b.eval env
  | .cons a rest => a.eval env = rest.first.eval env ∧ rest.Holds env

theorem Chain.endpoints {env : Interpretation R} (chain : Chain)
    (proof : chain.Holds env) : chain.first.eval env = chain.last.eval env := by
  induction chain with
  | pair _ _ => exact proof
  | cons _ rest ih => exact proof.1.trans (ih proof.2)

def Chain.chars : Chain → List Char
  | .pair a b => a.chars ++ " = ".toList ++ b.chars ++ ".".toList
  | .cons a rest => a.chars ++ " = ".toList ++ rest.chars

def Chain.height : Chain → Nat
  | .pair a b => max a.height b.height + 1
  | .cons a rest => max a.height rest.height + 1

/-- Counted grammar: no successful prefix parses or silently discarded links. -/
def parseChain : Nat → List Char → Option (Chain × List Char)
  | 0, _ => none
  | fuel + 1, cs => do
      let (a, cs) ← parseTerm fuel cs
      let cs ← literal " = ".toList cs
      -- The next term must either end the chain, or begin another full link.
      let (b, tail) ← parseTerm fuel cs
      match tail with
      | '.' :: suffix => some (.pair a b, suffix)
      | _ => do
          let (rest, suffix) ← parseChain fuel cs
          some (.cons a rest, suffix)

/-- A chain rendering always begins with its first term and an equality. -/
theorem Chain.chars_first (chain : Chain) :
    ∃ tail, chain.chars = chain.first.chars ++ " = ".toList ++ tail := by
  cases chain with
  | pair a b => exact ⟨b.chars ++ ".".toList, by simp [Chain.chars, Chain.first, List.append_assoc]⟩
  | cons a rest => exact ⟨rest.chars, rfl⟩

theorem Chain.first_height_le (chain : Chain) : chain.first.height ≤ chain.height := by
  cases chain <;> simp [Chain.first, Chain.height] <;> omega

theorem parseChain_chars (chain : Chain) (suffix : List Char) (fuel : Nat)
    (enough : chain.height ≤ fuel) :
    parseChain fuel (chain.chars ++ suffix) = some (chain, suffix) := by
  induction chain generalizing suffix fuel with
  | pair a b =>
      cases fuel with
      | zero => simp [Chain.height] at enough
      | succ fuel =>
          have ha : a.height ≤ fuel := by simp [Chain.height] at enough; omega
          have hb : b.height ≤ fuel := by simp [Chain.height] at enough; omega
          simp [Chain.chars, List.append_assoc, parseChain, literal,
            parseTerm_chars a _ _ ha, parseTerm_chars b _ _ hb]
  | cons a rest ih =>
      cases fuel with
      | zero => simp [Chain.height] at enough
      | succ fuel =>
          have ha : a.height ≤ fuel := by simp [Chain.height] at enough; omega
          have hr : rest.height ≤ fuel := by simp [Chain.height] at enough; omega
          have hf : rest.first.height ≤ fuel := Nat.le_trans rest.first_height_le hr
          obtain ⟨tail, htail⟩ := rest.chars_first
          simp only [Chain.chars, List.append_assoc, parseChain]
          rw [parseTerm_chars a _ _ ha]
          dsimp
          simp only [literal, ↓reduceIte, Option.bind_some]
          rw [show rest.chars ++ suffix = rest.first.chars ++ (" = ".toList ++ tail ++ suffix) by rw [htail]; simp [List.append_assoc]]
          rw [parseTerm_chars rest.first _ _ hf]
          dsimp
          have hp := ih suffix fuel hr
          rw [htail] at hp
          simp only [List.append_assoc] at hp
          change parseChain fuel (rest.first.chars ++ ' ' :: '=' :: ' ' :: (tail ++ suffix)) = some (rest, suffix) at hp
          simp [hp]

theorem Chain.height_le_length (chain : Chain) : chain.height ≤ chain.chars.length := by
  induction chain with
  | pair a b =>
      have := a.height_le_length
      have := b.height_le_length
      simp [Chain.height, Chain.chars]; omega
  | cons a rest ih =>
      have := a.height_le_length
      simp [Chain.height, Chain.chars]; omega

def Chain.render (chain : Chain) : String := String.ofList ("We have ".toList ++ chain.chars)

def read (text : String) : Option Chain := do
  let cs ← literal "We have ".toList text.toList
  let (chain, rest) ← parseChain text.toList.length cs
  if rest.isEmpty then some chain else none

theorem read_render (chain : Chain) : read chain.render = some chain := by
  have h : chain.height ≤ ("We have ".toList ++ chain.chars).length := by
    have := chain.height_le_length
    simp; omega
  have hp := parseChain_chars chain [] _ h
  simp only [List.append_nil] at hp
  unfold read Chain.render
  simp only [String.toList_ofList]
  rw [literal_append]
  dsimp
  dsimp at hp
  rw [hp]
  rfl

theorem Chain.render_injective {a b : Chain} (h : a.render = b.render) : a = b := by
  have := congrArg read h
  simpa only [read_render, Option.some.injEq] using this

def TextMeans (env : Interpretation R) (text : String) : Prop :=
  ∃ chain, read text = some chain ∧ chain.Holds env

theorem rendered_meaning (env : Interpretation R) (chain : Chain) :
    TextMeans env chain.render ↔ chain.Holds env := by
  simp [TextMeans, read_render]

theorem certify (env : Interpretation R) (chain : Chain) (proof : chain.Holds env) :
    TextMeans env chain.render := (rendered_meaning env chain).mpr proof

def readBytes (bytes : ByteArray) : Option Chain := do
  let text ← String.fromUTF8? bytes
  read text

theorem readBytes_render (chain : Chain) : readBytes chain.render.toUTF8 = some chain := by
  unfold readBytes
  rw [ControlledEnglish.Text.decodeUTF8_encode]
  dsimp
  exact read_render chain

def BytesMean (env : Interpretation R) (bytes : ByteArray) : Prop :=
  ∃ chain, readBytes bytes = some chain ∧ chain.Holds env

theorem rendered_bytes_meaning (env : Interpretation R) (chain : Chain) :
    BytesMean env chain.render.toUTF8 ↔ chain.Holds env := by
  unfold BytesMean
  rw [readBytes_render]
  simp

theorem certifyBytes (env : Interpretation R) (chain : Chain) (proof : chain.Holds env) :
    BytesMean env chain.render.toUTF8 := (rendered_bytes_meaning env chain).mpr proof

#print axioms Chain.endpoints
#print axioms parseChain_chars
#print axioms read_render
#print axioms Chain.render_injective
#print axioms rendered_meaning
#print axioms certify
#print axioms readBytes_render
#print axioms rendered_bytes_meaning
#print axioms certifyBytes
end ProofReader.EquationEnglish
