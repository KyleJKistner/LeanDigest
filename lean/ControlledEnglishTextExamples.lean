import ControlledEnglishText

/-! Write examples using the proved renderer itself, not a Python/JS copy.
These are logical schemas over two abstract propositions, not OpenAI proofs. -/
open ProofReader.ControlledEnglish

private def p : Formula 2 := .atom ⟨0, by decide⟩
private def q : Formula 2 := .atom ⟨1, by decide⟩

private def examples : List (String × Rule 2) :=
  [("conjunction-introduction", .andIntro p q),
   ("first-projection", .andLeft p q),
   ("second-projection", .andRight p q),
   ("implication-application", .impApply p q),
   ("left-disjunction", .orLeft p q),
   ("right-disjunction", .orRight p q),
   ("case-split", .orCases p q p),
   ("contradiction", .falseElim p)]

def main (args : List String) : IO UInt32 := do
  let [destination] := args | do
    IO.eprintln "Usage: lean --run ControlledEnglishTextExamples.lean OUTPUT_DIRECTORY"
    return 2
  let output : System.FilePath := destination
  IO.FS.createDirAll output
  let mut records : Array Lean.Json := #[]
  for (name, rule) in examples do
    let text := Text.render rule.sentence.render
    let bytes := Text.renderBytes rule.sentence.render
    unless Text.accepts rule text && (Text.readSentenceBytes 2 bytes == some rule.sentence) do
      throw (IO.userError s!"Canonical example failed its own checked parser: {name}")
    IO.FS.writeBinFile (output / (name ++ ".txt")) bytes
    records := records.push <| Lean.Json.mkObj
      [("id", Lean.toJson name), ("file", Lean.toJson (name ++ ".txt")),
       ("text", Lean.toJson text), ("utf8_bytes", Lean.toJson bytes.size)]
  let manifest := Lean.Json.mkObj
    [("schema", Lean.toJson ("leanglish.controlled-text-examples/v1" : String)),
     ("atom_count", Lean.toJson (2 : Nat)),
     ("atom_environment", Lean.toJson ("Two abstract propositions; @0 and @1 are not display-name proofs." : String)),
     ("source_binding", Lean.toJson ("logical-schemas-not-imported-proofs" : String)),
     ("full_document_english_certified", Lean.toJson false),
     ("examples", Lean.Json.arr records)]
  IO.FS.writeFile (output / "examples.json") (manifest.pretty ++ "\n")
  return 0
