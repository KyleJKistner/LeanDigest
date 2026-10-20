import EquationEnglish
import WitnessEnglish

/-! # Scoped proof-document syntax

The three fixed paragraphs declare the statement, scopes, and definitions for
one Bezout proof schema. Calculation, cancellation, and frame fragments retain
their existing grammars. No raw prose escape is available.
-/
namespace ProofReader.BezoutDocument
open ArithmeticEnglish EquationEnglish WitnessEnglish
set_option maxHeartbeats 600000
set_option maxRecDepth 4096

structure Document where
  zeroAB : Chain
  zeroDC : Chain
  zeroDB : Chain
  zeroDet : Chain
  zeroFrame : Frame
  bezoutEq : Chain
  bezoutCancel : Cancellation
  relationEq : Chain
  relationCancel : Cancellation
  nonzeroAB : Chain
  nonzeroDC : Chain
  nonzeroDB : Chain
  nonzeroDet : Chain
  nonzeroFrame : Frame

def startChars : List Char :=
  ['S', 't', 'a', 't', 'e', 'm', 'e', 'n', 't', '\n', 'L', 'e', 't', ' ', 'R', ' ', 'b', 'e', ' ', 'a',
   ' ', 'E', 'u', 'c', 'l', 'i', 'd', 'e', 'a', 'n', ' ', 'd', 'o', 'm', 'a', 'i', 'n', '.', ' ', 'L',
   'e', 't', ' ', 'x', ',', ' ', 'y', ',', ' ', 'z', ' ', 'b', 'e', ' ', 'e', 'l', 'e', 'm', 'e', 'n',
   't', 's', ' ', 'o', 'f', ' ', 'R', ' ', 'w', 'i', 't', 'h', ' ', 'x', '*', 'y', ' ', '=', ' ', 'z',
   '*', '(', 'z', '+', '1', ')', '.', '\n', 'T', 'h', 'e', 'r', 'e', ' ', 'e', 'x', 'i', 's', 't', ' ',
   'a', ',', ' ', 'd', ',', ' ', 'b', ',', ' ', 'c', ' ', 'i', 'n', ' ', 'R', ' ', 'w', 'i', 't', 'h',
   ' ', 'a', '*', 'b', ' ', '=', ' ', 'x', ',', ' ', 'd', '*', 'c', ' ', '=', ' ', 'y', ',', ' ', 'd',
   '*', 'b', ' ', '=', ' ', 'z', ',', ' ', 'a', 'n', 'd', ' ', 'a', '*', 'c', ' ', '-', ' ', 'd', '*',
   'b', ' ', '=', ' ', '1', '.', '\n', 'A', ' ', 't', 'u', 'p', 'l', 'e', ' ', '(', 'a', ',', ' ', 'd',
   ',', ' ', 'b', ',', ' ', 'c', ')', ' ', 'w', 'i', 't', 'h', ' ', 't', 'h', 'e', 's', 'e', ' ', 'f',
   'o', 'u', 'r', ' ', 'p', 'r', 'o', 'p', 'e', 'r', 't', 'i', 'e', 's', ' ', 'i', 's', ' ', 'c', 'a',
   'l', 'l', 'e', 'd', ' ', 'a', ' ', 'f', 'r', 'a', 'm', 'e', ' ', 'f', 'o', 'r', ' ', '(', 'x', ',',
   ' ', 'y', ',', ' ', 'z', ')', '.', '\n', '\n', 'P', 'r', 'o', 'o', 'f', '\n', 'S', 'e', 't', ' ', 'g',
   ' ', '=', ' ', 'g', 'c', 'd', '(', 'x', ',', ' ', 'z', ')', '.', '\n', '\n', 'Z', 'e', 'r', 'o', ' ',
   'c', 'a', 's', 'e', '\n', 'S', 'u', 'p', 'p', 'o', 's', 'e', ' ', 'g', ' ', '=', ' ', '0', '.', ' ',
   'T', 'h', 'e', 'n', ' ', 'x', ' ', '=', ' ', '0', ' ', 'a', 'n', 'd', ' ', 'z', ' ', '=', ' ', '0',
   '.']
def nonzeroChars : List Char :=
  ['N', 'o', 'n', 'z', 'e', 'r', 'o', ' ', 'c', 'a', 's', 'e', '\n', 'S', 'u', 'p', 'p', 'o', 's', 'e',
   ' ', 'g', ' ', 'i', 's', ' ', 'n', 'o', 'n', 'z', 'e', 'r', 'o', '.', ' ', 'T', 'h', 'e', ' ', 'e',
   'l', 'e', 'm', 'e', 'n', 't', ' ', 'g', ' ', 'd', 'i', 'v', 'i', 'd', 'e', 's', ' ', 'x', ' ', 'a',
   'n', 'd', ' ', 'z', '.', '\n', 'C', 'h', 'o', 'o', 's', 'e', ' ', 'a', ' ', 'w', 'i', 't', 'h', ' ',
   'x', ' ', '=', ' ', 'g', '*', 'a', ',', ' ', 'a', 'n', 'd', ' ', 'd', ' ', 'w', 'i', 't', 'h', ' ',
   'z', ' ', '=', ' ', 'g', '*', 'd', '.', '\n', 'S', 'e', 't', ' ', 'r', ' ', '=', ' ', 'g', 'c', 'd',
   'A', '(', 'x', ',', ' ', 'z', ')', ' ', 'a', 'n', 'd', ' ', 's', ' ', '=', ' ', 'g', 'c', 'd', 'B',
   '(', 'x', ',', ' ', 'z', ')', ',', ' ', 't', 'h', 'e', ' ', 'E', 'u', 'c', 'l', 'i', 'd', 'e', 'a',
   'n', '-', 'd', 'o', 'm', 'a', 'i', 'n', ' ', 'B', 'e', 'z', 'o', 'u', 't', ' ', 'c', 'o', 'e', 'f',
   'f', 'i', 'c', 'i', 'e', 'n', 't', ' ', 'f', 'u', 'n', 'c', 't', 'i', 'o', 'n', 's', '.']
def conclusionChars : List Char :=
  ['C', 'o', 'n', 'c', 'l', 'u', 's', 'i', 'o', 'n', '\n', 'E', 'a', 'c', 'h', ' ', 'c', 'a', 's', 'e',
   ' ', 'p', 'r', 'o', 'v', 'i', 'd', 'e', 's', ' ', 'a', ' ', 'f', 'r', 'a', 'm', 'e', ' ', 'f', 'o',
   'r', ' ', '(', 'x', ',', ' ', 'y', ',', ' ', 'z', ')', ',', ' ', 's', 'o', ' ', 't', 'h', 'e', ' ',
   's', 't', 'a', 't', 'e', 'm', 'e', 'n', 't', ' ', 'f', 'o', 'l', 'l', 'o', 'w', 's', '.']

inductive Fragment where
  | start | nonzero | conclusion
  | equation : Chain → Fragment
  | cancellation : Cancellation → Fragment
  | frame : Frame → Fragment

def Fragment.chars : Fragment → List Char
  | .start => startChars
  | .nonzero => nonzeroChars
  | .conclusion => conclusionChars
  | .equation c => "We have ".toList ++ c.chars
  | .cancellation c => c.chars
  | .frame f => f.chars

def Fragment.height : Fragment → Nat
  | .start | .nonzero | .conclusion => 1
  | .equation c => c.height
  | .cancellation c => c.height
  | .frame f => f.height

def parseFragment (fuel : Nat) (cs : List Char) : Option (Fragment × List Char) :=
  match cs with
  | 'S' :: 't' :: _ => do
      let tail ← literal startChars cs
      some (.start, tail)
  | 'N' :: _ => do
      let tail ← literal nonzeroChars cs
      some (.nonzero, tail)
  | 'C' :: _ => do
      let tail ← literal conclusionChars cs
      some (.conclusion, tail)
  | 'W' :: _ => do
      let tail ← literal "We have ".toList cs
      let (c, tail) ← parseChain fuel tail
      some (.equation c, tail)
  | 'S' :: 'i' :: _ => do
      let (c, tail) ← parseCancellation fuel cs
      some (.cancellation c, tail)
  | 'T' :: _ => do
      let (f, tail) ← parseFrame fuel cs
      some (.frame f, tail)
  | _ => none

theorem parseFragment_chars (f : Fragment) (suffix : List Char) (fuel : Nat)
    (enough : f.height ≤ fuel) :
    parseFragment fuel (f.chars ++ suffix) = some (f, suffix) := by
  cases f with
  | start =>
      change (do let tail ← literal startChars (startChars ++ suffix)
                 pure (Fragment.start, tail)) = _
      rw [literal_append]; rfl
  | nonzero =>
      change (do let tail ← literal nonzeroChars (nonzeroChars ++ suffix)
                 pure (Fragment.nonzero, tail)) = _
      rw [literal_append]; rfl
  | conclusion =>
      change (do let tail ← literal conclusionChars (conclusionChars ++ suffix)
                 pure (Fragment.conclusion, tail)) = _
      rw [literal_append]; rfl
  | equation c =>
      change (do let tail ← literal "We have ".toList
                    (("We have ".toList ++ c.chars) ++ suffix)
                 let (v, tail) ← parseChain fuel tail
                 pure (Fragment.equation v, tail)) = _
      rw [List.append_assoc, literal_append]
      dsimp
      rw [parseChain_chars c suffix fuel enough]
      rfl
  | cancellation c =>
      change (do let (v, tail) ← parseCancellation fuel (c.chars ++ suffix)
                 pure (Fragment.cancellation v, tail)) = _
      rw [parseCancellation_chars c suffix fuel enough]; rfl
  | frame f =>
      change (do let (v, tail) ← parseFrame fuel (f.chars ++ suffix)
                 pure (Fragment.frame v, tail)) = _
      rw [parseFrame_chars f suffix fuel enough]; rfl

theorem Fragment.height_le_length (f : Fragment) : f.height ≤ f.chars.length := by
  cases f with
  | start | nonzero | conclusion => decide
  | equation c =>
      have := c.height_le_length
      simp [Fragment.height, Fragment.chars]; omega
  | cancellation c => exact c.height_le_length
  | frame f => exact f.height_le_length

def fragmentsChars : List Fragment → List Char
  | [] => []
  | f :: rest => f.chars ++ ['\n','\n'] ++ fragmentsChars rest

def fragmentsHeight : List Fragment → Nat
  | [] => 0
  | f :: rest => max f.height (fragmentsHeight rest) + 1

def parseFragments : Nat → List Char → Option (List Fragment)
  | _, [] => some []
  | 0, _ :: _ => none
  | fuel + 1, cs@(_ :: _) => do
      let (f, tail) ← parseFragment fuel cs
      let tail ← literal ['\n','\n'] tail
      let rest ← parseFragments fuel tail
      some (f :: rest)

theorem fragments_cons_ne_nil (f : Fragment) (rest : List Fragment) :
    fragmentsChars (f :: rest) ≠ [] := by
  intro h
  have := congrArg List.length h
  simp [fragmentsChars] at this

theorem parseFragments_nonempty (fuel : Nat) (cs : List Char) (h : cs ≠ []) :
    parseFragments (fuel+1) cs = (do
      let (f, tail) ← parseFragment fuel cs
      let tail ← literal ['\n','\n'] tail
      let rest ← parseFragments fuel tail
      some (f :: rest)) := by
  cases cs with
  | nil => contradiction
  | cons => rfl

theorem parseFragments_chars (fs : List Fragment) (fuel : Nat)
    (enough : fragmentsHeight fs ≤ fuel) :
    parseFragments fuel (fragmentsChars fs) = some fs := by
  induction fs generalizing fuel with
  | nil => cases fuel <;> rfl
  | cons f rest ih =>
      cases fuel with
      | zero => simp [fragmentsHeight] at enough
      | succ fuel =>
          have hf : f.height ≤ fuel := by simp [fragmentsHeight] at enough; omega
          have hr : fragmentsHeight rest ≤ fuel := by simp [fragmentsHeight] at enough; omega
          rw [parseFragments_nonempty fuel _ (fragments_cons_ne_nil f rest)]
          simp only [fragmentsChars, List.append_assoc]
          rw [parseFragment_chars f _ fuel hf]
          dsimp
          change ((parseFragments fuel (fragmentsChars rest)).bind
            fun more => some (f :: more)) = some (f :: rest)
          rw [ih fuel hr]
          rfl

theorem fragmentsHeight_le_length (fs : List Fragment) :
    fragmentsHeight fs ≤ (fragmentsChars fs).length := by
  induction fs with
  | nil => simp [fragmentsHeight,fragmentsChars]
  | cons f rest ih =>
      have := f.height_le_length
      simp [fragmentsHeight,fragmentsChars]; omega

def readFragments (text : String) : Option (List Fragment) :=
  parseFragments text.toList.length text.toList

theorem readFragments_render (fs : List Fragment) :
    readFragments (String.ofList (fragmentsChars fs)) = some fs := by
  simp only [readFragments, String.toList_ofList]
  exact parseFragments_chars fs _ (fragmentsHeight_le_length fs)

def Document.fragments (d : Document) : List Fragment :=
  [.start, .equation d.zeroAB, .equation d.zeroDC, .equation d.zeroDB,
   .equation d.zeroDet, .frame d.zeroFrame, .nonzero, .equation d.bezoutEq,
   .cancellation d.bezoutCancel, .equation d.relationEq, .cancellation d.relationCancel,
   .equation d.nonzeroAB, .equation d.nonzeroDC, .equation d.nonzeroDB,
   .equation d.nonzeroDet, .frame d.nonzeroFrame, .conclusion]

/-- Accept exactly one statement, both branches, their passages, and closure. -/
def fromFragments : List Fragment → Option Document
  | [.start, .equation zab, .equation zdc, .equation zdb, .equation zdet,
     .frame zf, .nonzero, .equation beq, .cancellation bc, .equation req,
     .cancellation rc, .equation ab, .equation dc, .equation db, .equation det,
     .frame nf, .conclusion] =>
      some ⟨zab,zdc,zdb,zdet,zf,beq,bc,req,rc,ab,dc,db,det,nf⟩
  | _ => none

theorem fromFragments_fragments (d : Document) : fromFragments d.fragments = some d := rfl

def Document.render (d : Document) : String := String.ofList (fragmentsChars d.fragments)

def read (text : String) : Option Document := do
  let fs ← readFragments text
  fromFragments fs

theorem read_render (d : Document) : read d.render = some d := by
  simp only [read, Document.render, readFragments_render]
  exact fromFragments_fragments d

theorem Document.render_injective {d e : Document} (h : d.render = e.render) : d = e := by
  have := congrArg read h
  simpa only [read_render, Option.some.injEq] using this

end ProofReader.BezoutDocument
