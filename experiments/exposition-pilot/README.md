# Three-proof exposition pilot

A finite refactoring experiment and an authored mathematical reader. The targets
are one retained OpenAI supporting theorem (the Bézout frame) and two library
controls (Cantor's theorem and list reversal). This is not a generic English
compiler, an autonomous model service, or a human-comprehension evaluation.

## Question

Does shortening or refactoring a checked proof make it easier to produce an
explanation of the mathematical construction? Keep the original, a short
candidate, and a structured candidate. Do not make source length the acceptance
criterion for the exposition.

For Bézout, the useful intermediate problem is solving `a*c=w` and `d*c=y`.
Given `a*r+d*s=1`, compatibility `a*y=d*w` is necessary and sufficient, and the
only possible solution is `r*w+s*y`. The structured candidate checks existence,
the forced value, necessity, and the original frame theorem. This supplies a
mathematical reason for the witness, not just a list of its properties.

For Cantor, the explanation chooses a witness of disagreement with each `f(a)`:
use `a` itself. For reversal, the explanation uses reversal of concatenation;
the existing accumulator proof is shorter. These examples do not establish a
universal exposition strategy.

## Run

Use Lean 4.34.1 and a built Mathlib checkout at
`d13f23b723b8a846827a245b89c10fc7d3f11612`. The runner checks the Lean version, but
does not authenticate the supplied Mathlib checkout or its compiled objects.
Candidates are trusted executable Lean source; this is not a security sandbox.

```sh
python run.py --lean /path/to/lean --project /path/to/mathlib \
  --output /tmp/pilot-first --trust-project
python run.py --lean /path/to/lean --project /path/to/mathlib \
  --output /tmp/pilot-repeat --trust-project
python build.py /tmp/pilot-first/observation.json /tmp/pilot.html

PILOT_OBSERVATION=/tmp/pilot-first/observation.json \
PILOT_REPEAT=/tmp/pilot-repeat/observation.json \
PILOT_HTML=/tmp/pilot.html \
python -m pytest regression.py -q
```

The regression command needs pytest, BeautifulSoup and Playwright with Chromium.
`PILOT_CHROMIUM` selects the Chromium executable; the default is
`/usr/bin/chromium`. Browser tests explicitly use in-memory pages. They do not
claim successful `file://` navigation. `build.py` has no external dependencies
and writes a self-contained HTML file with native MathML. The PDF was printed
from that HTML after calling `preparePrint()`.

`OriginalBezout.lean` retains the theorem body but substitutes imports
`Mathlib.Algebra.EuclideanDomain.Basic` and `Mathlib.Tactic.Ring`. It is not a
whole-project replay. The originals for the controls are the pinned library
`Function.cantor_surjective` and `List.reverse_reverse`.

## Native acceptance

The runner compiles each proposal in a fresh process. `PilotAudit.check` checks
the candidate's proof body at the externally selected original theorem's type.
It forces kernel checking and rejects axioms outside `propext`,
`Classical.choice`, and `Quot.sound`. It also follows declaration types and
bodies transitively to reject references to the original target, including
aliases and simplifier shortcuts. Candidate-supplied definitions and proofs of
helpers must compile too.

The engine is a metaprogram, not a universally verified compiler. The compiler,
imports and execution environment remain trusted. The observed log and hashes
are not authenticated certificates. A matching theorem statement permits a
different proof; it does not prove the original author's intent or preserve the
original argument's sequence.

The candidate manifest contains six positive proposals and seven negative
controls. Three original-source baselines are added by the runner. A failure is
not a pass merely because it returns a nonzero code: each negative control also
requires its intended diagnostic. The missing-compatibility proposal is rejected
during elaboration; it also contains a forbidden final-target reference. It is
not an isolated kernel mutation. A separate checked integer counterexample in
the positive structured Bézout module establishes that compatibility cannot be
dropped from the general lemma.

## Recorded local result

Two complete runs accepted all nine baseline/candidate proofs and rejected all
seven controls. The nine positive audit objects and all sixteen generated driver
hashes repeated identically. Runtime timings are not compared. The final focused
regression suite passed 38 tests without skips. Its browser checks cover the
three tabs, native lemma text, all editable diagonal cells, exact-integer
construction examples including zero and negative inputs, invalid inputs, safe
text insertion, mobile width, and print inclusion.

Actual local file navigation was attempted and blocked with
`ERR_BLOCKED_BY_ADMINISTRATOR`. The browser's in-memory tests and the generated
PDF are separate results. No remote native CI or full repository regression is
claimed for this experiment.

## Measurements

The observation records root expression-tree node occurrences and the bodies of
reachable newly introduced helper declarations. These are not runtime cost,
minimality, or comprehension scores. Auxiliary explanatory lemmas that the final
root does not call are not in the reachable-helper total; all their source is
retained and compiled. Compare the full candidate source, including helpers,
rather than treating extracted lemmas as free. Established library dependencies
are recorded but their bodies are not added to the local-node count.

The short candidate is a proposal, not a claim of global or even local optimum.
The proof and prose candidates were authored by the assistant in this session
and revised using Lean diagnostics. Selection of the structured exposition is
editorial. There is no independent model judge or mathematician evaluation.

## Presentation boundary

The reader presents a mathematical construction, followed by a proof, optional
lemma details, and examples. Exact checked Lean signatures and candidate source
are expandable. The prose and MathML rendering are not formally certified.
Deterministic generation and a passing proof do not establish faithful English.
The integer and matrix examples illustrate the argument; they are not proof
certificates.

The next reusable operation to investigate is not merely `shorten proof`, but
`propose an intermediate mathematical problem, justify its reduction, and check
its solution`. For a witness, this may mean deriving the expression from its
obligations, then checking necessity, sufficiency and uniqueness. Other proof
families may require different explanatory choices. The reader is a concrete
output target for that work, not evidence that automatic generation is solved.
