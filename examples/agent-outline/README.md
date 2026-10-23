# Graph-criterion outline

Source: `openai/math` at `1581d4cbdd69a0faf34b2089614fe2a814316a6a`,
`OAI/Algebra/Universal/GraphCriterion.lean`, under its original imports.
Use the Mathlib revision and Lean toolchain pinned by that repository.

The initial outline concerns `labelCongruence_surjective`: any congruence of the
constructed unary algebra is a color threshold. Its blocks collect related seed
pairs, show that the seeds are nonempty, and compare the threshold and congruence.

After opening that declaration, check `initial-proposal.json`. Expand its
`threshold` block using `expanded-children.json`, then check the new proposal.
The earlier seed blocks are unchanged. The two directions can also be displayed
in reverse order while retaining their own contexts.

Follow source frame 26 to `connected_below_congruence`. The command obtains this
callee from the expression, not from a name in this README. In the new session,
check `path-proposal.json`. Its four blocks correspond to the equivalence-closure
induction: admissible images, reflexivity, reversal, and concatenation.

All three files are source-bound editorial data. Their prose and selected steps
were chosen by the assistant, not automatically discovered by a planner. A source
change requires re-inspection and new data, rather than updating the digest alone.
