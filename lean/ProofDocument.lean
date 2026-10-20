import Mathlib.Algebra.EuclideanDomain.Basic
import ProofDocumentSyntax

/-! # Scoped document semantics -/
namespace ProofReader.BezoutDocument
open ArithmeticEnglish EquationEnglish WitnessEnglish
noncomputable section
local instance {R : Type u} : DecidableEq R := Classical.decEq R
set_option maxHeartbeats 600000
set_option maxRecDepth 4096

/-- Only names introduced before the zero branch may occur there. -/
def zeroTerm : Term → Bool
  | .var .x | .var .y | .var .z | .var .g | .zero | .one => true
  | .var _ => false
  | .add a b | .mul a b | .sub a b => zeroTerm a && zeroTerm b

def zeroChain : Chain → Bool
  | .pair a b => zeroTerm a && zeroTerm b
  | .cons a rest => zeroTerm a && zeroChain rest

def zeroFrameScoped (f : Frame) : Bool :=
  [f.x,f.y,f.z,f.a,f.d,f.b,f.c].all zeroTerm

def frameInputs (f : Frame) : Bool :=
  f.x == .var .x && f.y == .var .y && f.z == .var .z

def Document.wellFormed (d : Document) : Bool :=
  frameInputs d.zeroFrame && frameInputs d.nonzeroFrame &&
  zeroFrameScoped d.zeroFrame && [d.zeroAB,d.zeroDC,d.zeroDB,d.zeroDet].all zeroChain

/-- The operations and labels have their ordinary Euclidean-domain meanings. -/
def environment {R : Type u} [EuclideanDomain R] (x y z g a d r s : R) : Interpretation R :=
  ⟨assignment x y z g a d r s, 0, 1, (· + ·), (· * ·), (· - ·)⟩

def zeroEnvironment {R : Type u} [EuclideanDomain R] (x y z : R) : Interpretation R :=
  environment x y z (EuclideanDomain.gcd x z) 0 0 0 0

def nonzeroEnvironment {R : Type u} [EuclideanDomain R] (x y z a d : R) : Interpretation R :=
  environment x y z (EuclideanDomain.gcd x z) a d
    (EuclideanDomain.gcdA x z) (EuclideanDomain.gcdB x z)

def Document.Zero {R : Type u} [EuclideanDomain R] (doc : Document) (x y z : R) : Prop :=
  (x = 0 ∧ z = 0) ∧
  EquationEnglish.TextMeans (zeroEnvironment x y z) doc.zeroAB.render ∧
  EquationEnglish.TextMeans (zeroEnvironment x y z) doc.zeroDC.render ∧
  EquationEnglish.TextMeans (zeroEnvironment x y z) doc.zeroDB.render ∧
  EquationEnglish.TextMeans (zeroEnvironment x y z) doc.zeroDet.render ∧
  WitnessEnglish.TextMeans (zeroEnvironment x y z) doc.zeroFrame.render

def Document.Nonzero {R : Type u} [EuclideanDomain R] (doc : Document) (x y z a d : R) : Prop :=
  EquationEnglish.TextMeans (nonzeroEnvironment x y z a d) doc.bezoutEq.render ∧
  ArithmeticEnglish.TextMeans (nonzeroEnvironment x y z a d) doc.bezoutCancel.render ∧
  EquationEnglish.TextMeans (nonzeroEnvironment x y z a d) doc.relationEq.render ∧
  ArithmeticEnglish.TextMeans (nonzeroEnvironment x y z a d) doc.relationCancel.render ∧
  EquationEnglish.TextMeans (nonzeroEnvironment x y z a d) doc.nonzeroAB.render ∧
  EquationEnglish.TextMeans (nonzeroEnvironment x y z a d) doc.nonzeroDC.render ∧
  EquationEnglish.TextMeans (nonzeroEnvironment x y z a d) doc.nonzeroDB.render ∧
  EquationEnglish.TextMeans (nonzeroEnvironment x y z a d) doc.nonzeroDet.render ∧
  WitnessEnglish.TextMeans (nonzeroEnvironment x y z a d) doc.nonzeroFrame.render

/-- Both cases are mandatory. The chosen quotients are introduced only inside
    the nonzero case; all printed assertions retain their local hypotheses. -/
def Document.Holds {R : Type u} [EuclideanDomain R] (doc : Document) (x y z : R) : Prop :=
  let g := EuclideanDomain.gcd x z
  (g = 0 → doc.Zero x y z) ∧
  (g ≠ 0 → (g ∣ x) ∧ (g ∣ z) ∧
    ∀ a : R, x = g*a → ∀ d : R, z = g*d → doc.Nonzero x y z a d)

def FrameExists {R : Type u} [EuclideanDomain R] (x y z : R) : Prop :=
  ∃ a d b c : R, a*b = x ∧ d*c = y ∧ d*b = z ∧ a*c-d*b = 1

def Statement (R : Type u) [EuclideanDomain R] : Prop :=
  ∀ x y z : R, x*y = z*(z+1) → FrameExists x y z

private theorem frameGoal {R : Type u} [EuclideanDomain R] (f : Frame)
    (x y z g a d r s : R) (inputs : frameInputs f = true)
    (proof : WitnessEnglish.TextMeans (environment x y z g a d r s) f.render) :
    FrameExists x y z := by
  have hp := (WitnessEnglish.rendered_meaning _ f).mp proof
  have h := Frame.witnesses _ f hp
  simp only [frameInputs, Bool.and_eq_true, beq_iff_eq] at inputs
  obtain ⟨⟨hx, hy⟩, hz⟩ := inputs
  simpa [FrameExists, Goal, hx, hy, hz, Term.eval, environment, assignment] using h

/-- A complete document yields the stated existential, with neither branch nor
    a source-local hypothesis silently omitted. -/
theorem Document.sound {R : Type u} [EuclideanDomain R] (doc : Document)
    (wf : doc.wellFormed = true) (x y z : R) (proof : doc.Holds x y z) :
    FrameExists x y z := by
  have hzInputs : frameInputs doc.zeroFrame = true := by
    simp only [Document.wellFormed, Bool.and_eq_true] at wf; exact wf.1.1.1
  have hnInputs : frameInputs doc.nonzeroFrame = true := by
    simp only [Document.wellFormed, Bool.and_eq_true] at wf; exact wf.1.1.2
  classical
  by_cases hg : EuclideanDomain.gcd x z = 0
  · have hz := proof.1 hg
    exact frameGoal doc.zeroFrame x y z _ 0 0 0 0 hzInputs hz.2.2.2.2.2
  · obtain ⟨left, right, body⟩ := proof.2 hg
    obtain ⟨a, ha⟩ := left
    obtain ⟨d, hd⟩ := right
    have hn := body a ha d hd
    exact frameGoal doc.nonzeroFrame x y z _ a d _ _ hnInputs hn.2.2.2.2.2.2.2.2

/-- Meaning of the entire literal document, including the quantified statement
    and every displayed local assertion. Parsing alone does not establish it. -/
def TextMeans (R : Type u) [EuclideanDomain R] (text : String) : Prop :=
  ∃ doc, read text = some doc ∧ doc.wellFormed = true ∧
    ∀ x y z : R, x*y = z*(z+1) → doc.Holds x y z

theorem rendered_meaning (R : Type u) [EuclideanDomain R] (doc : Document) :
    TextMeans R doc.render ↔ (doc.wellFormed = true ∧
      ∀ x y z : R, x*y = z*(z+1) → doc.Holds x y z) := by
  simp [TextMeans, read_render]

theorem packNonzero {R : Type u} [EuclideanDomain R] (doc : Document)
    (available : ∀ x y z : R, x*y = z*(z+1) →
      EuclideanDomain.gcd x z ≠ 0 →
      (EuclideanDomain.gcd x z ∣ x) ∧ (EuclideanDomain.gcd x z ∣ z))
    (body : ∀ x y z : R, x*y = z*(z+1) →
      EuclideanDomain.gcd x z ≠ 0 →
      ∀ a : R, x = EuclideanDomain.gcd x z*a →
      ∀ d : R, z = EuclideanDomain.gcd x z*d → doc.Nonzero x y z a d) :
    ∀ x y z : R, x*y = z*(z+1) → EuclideanDomain.gcd x z ≠ 0 →
      (EuclideanDomain.gcd x z ∣ x) ∧ (EuclideanDomain.gcd x z ∣ z) ∧
      ∀ a : R, x = EuclideanDomain.gcd x z*a →
      ∀ d : R, z = EuclideanDomain.gcd x z*d → doc.Nonzero x y z a d := by
  intro x y z h hg
  exact ⟨(available x y z h hg).1, (available x y z h hg).2, body x y z h hg⟩

theorem certify {R : Type u} [EuclideanDomain R] (doc : Document)
    (wf : doc.wellFormed = true)
    (zero : ∀ x y z : R, x*y = z*(z+1) →
      EuclideanDomain.gcd x z = 0 → doc.Zero x y z)
    (nonzero : ∀ x y z : R, x*y = z*(z+1) →
      EuclideanDomain.gcd x z ≠ 0 →
      (EuclideanDomain.gcd x z ∣ x) ∧ (EuclideanDomain.gcd x z ∣ z) ∧
      ∀ a : R, x = EuclideanDomain.gcd x z*a →
      ∀ d : R, z = EuclideanDomain.gcd x z*d → doc.Nonzero x y z a d) :
    TextMeans R doc.render :=
  (rendered_meaning R doc).mpr ⟨wf, fun x y z h => ⟨zero x y z h, nonzero x y z h⟩⟩

theorem text_implies_statement {R : Type u} [EuclideanDomain R] (text : String)
    (proof : TextMeans R text) : Statement R := by
  obtain ⟨doc, _, wf, holds⟩ := proof
  intro x y z h
  exact doc.sound wf x y z (holds x y z h)

def readBytes (bytes : ByteArray) : Option Document := do
  let text ← String.fromUTF8? bytes
  read text

theorem readBytes_render (doc : Document) : readBytes doc.render.toUTF8 = some doc := by
  unfold readBytes
  rw [ControlledEnglish.Text.decodeUTF8_encode]
  dsimp
  exact read_render doc

def BytesMean (R : Type u) [EuclideanDomain R] (bytes : ByteArray) : Prop :=
  ∃ doc, readBytes bytes = some doc ∧ doc.wellFormed = true ∧
    ∀ x y z : R, x*y = z*(z+1) → doc.Holds x y z

theorem rendered_bytes_meaning (R : Type u) [EuclideanDomain R] (doc : Document) :
    BytesMean R doc.render.toUTF8 ↔ (doc.wellFormed = true ∧
      ∀ x y z : R, x*y = z*(z+1) → doc.Holds x y z) := by
  unfold BytesMean
  rw [readBytes_render]
  simp

theorem certifyBytes {R : Type u} [EuclideanDomain R] (doc : Document)
    (proof : TextMeans R doc.render) : BytesMean R doc.render.toUTF8 :=
  (rendered_bytes_meaning R doc).mpr ((rendered_meaning R doc).mp proof)

theorem bytes_imply_statement {R : Type u} [EuclideanDomain R] (bytes : ByteArray)
    (proof : BytesMean R bytes) : Statement R := by
  obtain ⟨doc, _, wf, holds⟩ := proof
  intro x y z h
  exact doc.sound wf x y z (holds x y z h)

#print axioms parseFragments_chars
#print axioms read_render
#print axioms Document.render_injective
#print axioms Document.sound
#print axioms rendered_meaning
#print axioms certify
#print axioms text_implies_statement
#print axioms readBytes_render
#print axioms rendered_bytes_meaning
#print axioms certifyBytes
#print axioms bytes_imply_statement
end
end ProofReader.BezoutDocument
