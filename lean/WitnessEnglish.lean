import ArithmeticEnglish

/-! # Witness tuples

The defined term "frame" means the four equations in `Frame.Holds`. The tuple
order is (a, d, b, c). Both this dictionary and the scalar interpretation are
explicit parts of the formal language, not inferred from ordinary English.
-/
namespace ProofReader.WitnessEnglish
set_option maxHeartbeats 400000
open ArithmeticEnglish

structure Frame where
  x : Term
  y : Term
  z : Term
  a : Term
  d : Term
  b : Term
  c : Term
  deriving DecidableEq, Repr, Inhabited

def Frame.ab (f : Frame) : Term := .mul f.a f.b
def Frame.dc (f : Frame) : Term := .mul f.d f.c
def Frame.db (f : Frame) : Term := .mul f.d f.b
def Frame.det (f : Frame) : Term := .sub (.mul f.a f.c) f.db

def Frame.chars (f : Frame) : List Char :=
  "The tuple (".toList ++ f.a.chars ++ ", ".toList ++ f.d.chars ++ ", ".toList ++
  f.b.chars ++ ", ".toList ++ f.c.chars ++ ") is a frame for (".toList ++
  f.x.chars ++ ", ".toList ++ f.y.chars ++ ", ".toList ++ f.z.chars ++ ").".toList

def Frame.render (f : Frame) : String := String.ofList f.chars

def parseFrame (fuel : Nat) (chars : List Char) : Option (Frame × List Char) := do
  let cs ← literal "The tuple (".toList chars
  let (a, cs) ← parseTerm fuel cs
  let cs ← literal ", ".toList cs
  let (d, cs) ← parseTerm fuel cs
  let cs ← literal ", ".toList cs
  let (b, cs) ← parseTerm fuel cs
  let cs ← literal ", ".toList cs
  let (c, cs) ← parseTerm fuel cs
  let cs ← literal ") is a frame for (".toList cs
  let (x, cs) ← parseTerm fuel cs
  let cs ← literal ", ".toList cs
  let (y, cs) ← parseTerm fuel cs
  let cs ← literal ", ".toList cs
  let (z, cs) ← parseTerm fuel cs
  let cs ← literal ").".toList cs
  some (⟨x,y,z,a,d,b,c⟩,cs)

def Frame.height (f : Frame) : Nat :=
  f.x.height + f.y.height + f.z.height + f.a.height + f.d.height + f.b.height + f.c.height + 3

theorem parseFrame_chars (f : Frame) (suffix : List Char) (fuel : Nat)
    (enough : f.height ≤ fuel) :
    parseFrame fuel (f.chars ++ suffix) = some (f, suffix) := by
  have hx : f.x.height ≤ fuel := by simp [Frame.height] at enough; omega
  have hy : f.y.height ≤ fuel := by simp [Frame.height] at enough; omega
  have hz : f.z.height ≤ fuel := by simp [Frame.height] at enough; omega
  have ha : f.a.height ≤ fuel := by simp [Frame.height] at enough; omega
  have hd : f.d.height ≤ fuel := by simp [Frame.height] at enough; omega
  have hb : f.b.height ≤ fuel := by simp [Frame.height] at enough; omega
  have hc : f.c.height ≤ fuel := by simp [Frame.height] at enough; omega
  simp [Frame.chars, List.append_assoc, parseFrame, literal,
    parseTerm_chars f.x _ _ hx, parseTerm_chars f.y _ _ hy, parseTerm_chars f.z _ _ hz,
    parseTerm_chars f.a _ _ ha, parseTerm_chars f.d _ _ hd, parseTerm_chars f.b _ _ hb,
    parseTerm_chars f.c _ _ hc]

theorem Frame.height_le_length (f : Frame) : f.height ≤ f.chars.length := by
  have := f.x.height_le_length
  have := f.y.height_le_length
  have := f.z.height_le_length
  have := f.a.height_le_length
  have := f.d.height_le_length
  have := f.b.height_le_length
  have := f.c.height_le_length
  simp [Frame.height, Frame.chars]; omega

def read (text : String) : Option Frame := do
  let (f, rest) ← parseFrame text.toList.length text.toList
  if rest.isEmpty then some f else none

theorem read_render (f : Frame) : read f.render = some f := by
  have hp := parseFrame_chars f [] f.chars.length f.height_le_length
  simp only [List.append_nil] at hp
  simp [read, Frame.render, hp]

theorem Frame.render_injective {f g : Frame} (h : f.render = g.render) : f = g := by
  have := congrArg read h
  simpa only [read_render, Option.some.injEq] using this

def Frame.Holds (env : Interpretation R) (f : Frame) : Prop :=
  f.ab.eval env = f.x.eval env ∧ f.dc.eval env = f.y.eval env ∧
  f.db.eval env = f.z.eval env ∧ f.det.eval env = env.one

def Goal (env : Interpretation R) (x y z : Term) : Prop :=
  ∃ a d b c : R, env.mul a b = x.eval env ∧ env.mul d c = y.eval env ∧
    env.mul d b = z.eval env ∧ env.sub (env.mul a c) (env.mul d b) = env.one

theorem Frame.witnesses (env : Interpretation R) (f : Frame) (proof : f.Holds env) :
    Goal env f.x f.y f.z :=
  ⟨f.a.eval env, f.d.eval env, f.b.eval env, f.c.eval env, proof⟩

def TextMeans (env : Interpretation R) (text : String) : Prop :=
  ∃ f, read text = some f ∧ f.Holds env

theorem rendered_meaning (env : Interpretation R) (f : Frame) :
    TextMeans env f.render ↔ f.Holds env := by simp [TextMeans, read_render]

theorem certify (env : Interpretation R) (f : Frame) (proof : f.Holds env) :
    TextMeans env f.render := (rendered_meaning env f).mpr proof

def readBytes (bytes : ByteArray) : Option Frame := do
  let text ← String.fromUTF8? bytes
  read text

theorem readBytes_render (f : Frame) : readBytes f.render.toUTF8 = some f := by
  unfold readBytes
  rw [ControlledEnglish.Text.decodeUTF8_encode]
  dsimp
  exact read_render f

def BytesMean (env : Interpretation R) (bytes : ByteArray) : Prop :=
  ∃ f, readBytes bytes = some f ∧ f.Holds env

theorem rendered_bytes_meaning (env : Interpretation R) (f : Frame) :
    BytesMean env f.render.toUTF8 ↔ f.Holds env := by
  unfold BytesMean
  rw [readBytes_render]
  simp

theorem certifyBytes (env : Interpretation R) (f : Frame) (proof : f.Holds env) :
    BytesMean env f.render.toUTF8 := (rendered_bytes_meaning env f).mpr proof

#print axioms parseFrame_chars
#print axioms read_render
#print axioms Frame.render_injective
#print axioms Frame.witnesses
#print axioms rendered_meaning
#print axioms certify
#print axioms readBytes_render
#print axioms rendered_bytes_meaning
#print axioms certifyBytes
end ProofReader.WitnessEnglish
