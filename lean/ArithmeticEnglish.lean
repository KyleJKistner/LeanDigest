import ControlledEnglishText

/-!
# Arithmetic cancellation sentences

The interpreted sentence asserts its nonzero premise, multiplied equality, and
conclusion. Every displayed term is syntax with an interpretation, not a
pretty-printed Lean string. The source importer must supply the interpretation
and original proofs in their original local contexts.
-/
namespace ProofReader.ArithmeticEnglish

inductive Variable where
  | x | y | z | g | a | d | r | s
  deriving DecidableEq, Repr, Inhabited

def Variable.char : Variable → Char
  | .x => 'x' | .y => 'y' | .z => 'z' | .g => 'g'
  | .a => 'a' | .d => 'd' | .r => 'r' | .s => 's'

inductive Term where
  | var : Variable → Term
  | zero | one
  | add : Term → Term → Term
  | mul : Term → Term → Term
  | sub : Term → Term → Term
  deriving DecidableEq, Repr, Inhabited

structure Interpretation (R : Type u) where
  values : Variable → R
  zero : R
  one : R
  add : R → R → R
  mul : R → R → R
  sub : R → R → R

/-- Stable finite labels interpreted by the actual source-local scalar values. -/
def assignment (x y z g a d r s : R) : Variable → R
  | .x => x | .y => y | .z => z | .g => g
  | .a => a | .d => d | .r => r | .s => s

def Term.eval (env : Interpretation R) : Term → R
  | .var v => env.values v
  | .zero => env.zero
  | .one => env.one
  | .add p q => env.add (p.eval env) (q.eval env)
  | .mul p q => env.mul (p.eval env) (q.eval env)
  | .sub p q => env.sub (p.eval env) (q.eval env)

def Term.chars : Term → List Char
  | .var v => [v.char]
  | .zero => ['0']
  | .one => ['1']
  | .add p q => ['('] ++ p.chars ++ " + ".toList ++ q.chars ++ [')']
  | .mul p q => ['('] ++ p.chars ++ " * ".toList ++ q.chars ++ [')']
  | .sub p q => ['('] ++ p.chars ++ " - ".toList ++ q.chars ++ [')']

def Term.height : Term → Nat
  | .var _ | .zero | .one => 1
  | .add p q | .mul p q | .sub p q => max p.height q.height + 1

/-- Consume a literal; mismatches and premature ends fail. -/
def literal : List Char → List Char → Option (List Char)
  | [], rest => some rest
  | c :: cs, d :: ds => if c = d then literal cs ds else none
  | _ :: _, [] => none

theorem literal_append (head rest : List Char) :
    literal head (head ++ rest) = some rest := by
  induction head with
  | nil => rfl
  | cons c cs ih => simp [literal, ih]

/-- Fully parenthesized arithmetic. No external labels or parser extensions. -/
def parseTerm : Nat → List Char → Option (Term × List Char)
  | 0, _ => none
  | _ + 1, 'x' :: cs => some (.var .x, cs)
  | _ + 1, 'y' :: cs => some (.var .y, cs)
  | _ + 1, 'z' :: cs => some (.var .z, cs)
  | _ + 1, 'g' :: cs => some (.var .g, cs)
  | _ + 1, 'a' :: cs => some (.var .a, cs)
  | _ + 1, 'd' :: cs => some (.var .d, cs)
  | _ + 1, 'r' :: cs => some (.var .r, cs)
  | _ + 1, 's' :: cs => some (.var .s, cs)
  | _ + 1, '0' :: cs => some (.zero, cs)
  | _ + 1, '1' :: cs => some (.one, cs)
  | fuel + 1, '(' :: cs => do
      let (p, cs) ← parseTerm fuel cs
      let ' ' :: op :: ' ' :: cs := cs | none
      let (q, cs) ← parseTerm fuel cs
      let ')' :: cs := cs | none
      match op with
      | '+' => some (.add p q, cs)
      | '*' => some (.mul p q, cs)
      | '-' => some (.sub p q, cs)
      | _ => none
  | _ + 1, _ => none

theorem parseTerm_chars (term : Term) (suffix : List Char) (fuel : Nat)
    (enough : term.height ≤ fuel) :
    parseTerm fuel (term.chars ++ suffix) = some (term, suffix) := by
  induction term generalizing fuel suffix with
  | var v =>
      cases fuel with
      | zero => simp [Term.height] at enough
      | succ fuel => cases v <;> rfl
  | zero | one =>
      cases fuel with
      | zero => simp [Term.height] at enough
      | succ fuel => rfl
  | add p q ihp ihq | mul p q ihp ihq | sub p q ihp ihq =>
      cases fuel with
      | zero => simp [Term.height] at enough
      | succ fuel =>
          have hp : p.height ≤ fuel := by simp [Term.height] at enough; omega
          have hq : q.height ≤ fuel := by simp [Term.height] at enough; omega
          simp [Term.chars, List.append_assoc, parseTerm, ihp _ _ hp, ihq _ _ hq]

theorem Term.height_le_length (term : Term) : term.height ≤ term.chars.length := by
  induction term with
  | var _ | zero | one => simp [Term.height, Term.chars]
  | add _ _ ihp ihq | mul _ _ ihp ihq | sub _ _ ihp ihq =>
      simp [Term.height, Term.chars]; omega

structure Cancellation where
  factor : Term
  left : Term
  right : Term
  deriving DecidableEq, Repr, Inhabited

def Cancellation.chars (c : Cancellation) : List Char :=
  "Since ".toList ++ c.factor.chars ++ " is nonzero and ".toList ++
  (Term.mul c.factor c.left).chars ++ " = ".toList ++
  (Term.mul c.factor c.right).chars ++ ", cancel ".toList ++ c.factor.chars ++
  " to obtain ".toList ++ c.left.chars ++ " = ".toList ++ c.right.chars ++ ".".toList

def Cancellation.render (c : Cancellation) : String := String.ofList c.chars

def parseCancellation (fuel : Nat) (chars : List Char) :
    Option (Cancellation × List Char) := do
  let cs ← literal "Since ".toList chars
  let (factor, cs) ← parseTerm fuel cs
  let cs ← literal " is nonzero and ".toList cs
  let (premiseLeft, cs) ← parseTerm fuel cs
  let cs ← literal " = ".toList cs
  let (premiseRight, cs) ← parseTerm fuel cs
  let cs ← literal ", cancel ".toList cs
  let (repeatedFactor, cs) ← parseTerm fuel cs
  let cs ← literal " to obtain ".toList cs
  let (left, cs) ← parseTerm fuel cs
  let cs ← literal " = ".toList cs
  let (right, cs) ← parseTerm fuel cs
  let cs ← literal ".".toList cs
  if repeatedFactor = factor ∧ premiseLeft = .mul factor left ∧
      premiseRight = .mul factor right then
    some (⟨factor, left, right⟩, cs)
  else none

def Cancellation.height (c : Cancellation) : Nat :=
  max c.factor.height (max c.left.height c.right.height) + 1

theorem parseCancellation_chars (c : Cancellation) (suffix : List Char)
    (fuel : Nat) (enough : c.height ≤ fuel) :
    parseCancellation fuel (c.chars ++ suffix) = some (c, suffix) := by
  have hf : c.factor.height ≤ fuel := by simp [Cancellation.height] at enough; omega
  have hl : c.left.height ≤ fuel := by simp [Cancellation.height] at enough; omega
  have hr : c.right.height ≤ fuel := by simp [Cancellation.height] at enough; omega
  have hfl : (Term.mul c.factor c.left).height ≤ fuel := by
    simp [Term.height, Cancellation.height] at *; omega
  have hfr : (Term.mul c.factor c.right).height ≤ fuel := by
    simp [Term.height, Cancellation.height] at *; omega
  have pf (suf) := parseTerm_chars c.factor suf fuel hf
  have pl (suf) := parseTerm_chars c.left suf fuel hl
  have pr (suf) := parseTerm_chars c.right suf fuel hr
  have pfl (suf) := parseTerm_chars (.mul c.factor c.left) suf fuel hfl
  have pfr (suf) := parseTerm_chars (.mul c.factor c.right) suf fuel hfr
  simp [Cancellation.chars, List.append_assoc, parseCancellation,
    literal, pf, pl, pr, pfl, pfr]

theorem Cancellation.height_le_length (c : Cancellation) :
    c.height ≤ c.chars.length := by
  have hf := c.factor.height_le_length
  have hl := c.left.height_le_length
  have hr := c.right.height_le_length
  simp [Cancellation.height, Cancellation.chars, Term.chars]; omega

def readCancellation (text : String) : Option Cancellation := do
  let (sentence, rest) ← parseCancellation text.toList.length text.toList
  if rest.isEmpty then some sentence else none

theorem readCancellation_render (c : Cancellation) :
    readCancellation c.render = some c := by
  have hp := parseCancellation_chars c [] c.chars.length c.height_le_length
  simp only [List.append_nil] at hp
  simp [readCancellation, Cancellation.render, hp]

theorem Cancellation.render_injective {c d : Cancellation}
    (h : c.render = d.render) : c = d := by
  have := congrArg readCancellation h
  simpa only [readCancellation_render, Option.some.injEq] using this

/-- 'Since ...' asserts both premises; it is not merely a vacuous implication. -/
def Cancellation.Means (env : Interpretation R) (c : Cancellation) : Prop :=
  c.factor.eval env ≠ env.zero ∧
  env.mul (c.factor.eval env) (c.left.eval env) =
    env.mul (c.factor.eval env) (c.right.eval env) ∧
  c.left.eval env = c.right.eval env

def TextMeans (env : Interpretation R) (text : String) : Prop :=
  ∃ c, readCancellation text = some c ∧ c.Means env

theorem rendered_meaning (env : Interpretation R) (c : Cancellation) :
    TextMeans env c.render ↔ c.Means env := by
  simp [TextMeans, readCancellation_render]

/-- This property is supplied by the actual source's multiplication instance. -/
def LeftCancel (env : Interpretation R) : Prop :=
  ∀ k u v, k ≠ env.zero → env.mul k u = env.mul k v → u = v

/-- Proof-bearing certificate: the precise factor and premises are mandatory. -/
theorem certify (env : Interpretation R) (c : Cancellation)
    (law : LeftCancel env)
    (nonzero : c.factor.eval env ≠ env.zero)
    (premise : env.mul (c.factor.eval env) (c.left.eval env) =
      env.mul (c.factor.eval env) (c.right.eval env)) :
    TextMeans env c.render := by
  apply (rendered_meaning env c).mpr
  exact ⟨nonzero, premise, law _ _ _ nonzero premise⟩

def readBytes (bytes : ByteArray) : Option Cancellation := do
  let text ← String.fromUTF8? bytes
  readCancellation text

theorem readBytes_render (c : Cancellation) : readBytes c.render.toUTF8 = some c := by
  unfold readBytes
  rw [ControlledEnglish.Text.decodeUTF8_encode]
  dsimp
  exact readCancellation_render c

def BytesMean (env : Interpretation R) (bytes : ByteArray) : Prop :=
  ∃ c, readBytes bytes = some c ∧ c.Means env

theorem rendered_bytes_meaning (env : Interpretation R) (c : Cancellation) :
    BytesMean env c.render.toUTF8 ↔ c.Means env := by
  unfold BytesMean
  rw [readBytes_render]
  simp

theorem certifyBytes (env : Interpretation R) (c : Cancellation)
    (law : LeftCancel env)
    (nonzero : c.factor.eval env ≠ env.zero)
    (premise : env.mul (c.factor.eval env) (c.left.eval env) =
      env.mul (c.factor.eval env) (c.right.eval env)) :
    BytesMean env c.render.toUTF8 := by
  exact (rendered_bytes_meaning env c).mpr
    ((rendered_meaning env c).mp (certify env c law nonzero premise))

#print axioms parseTerm_chars
#print axioms parseCancellation_chars
#print axioms readCancellation_render
#print axioms Cancellation.render_injective
#print axioms rendered_meaning
#print axioms certify
#print axioms readBytes_render
#print axioms rendered_bytes_meaning
#print axioms certifyBytes
end ProofReader.ArithmeticEnglish
