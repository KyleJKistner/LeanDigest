# Agent outline workflow

The command `python -m proofreader.outline` packages source-expression import,
lemma extraction, proof reconstruction, and revision storage. It uses the existing
constructor DAG and `ProofDecomposition.lean`; it introduces no mathematical
sentence language. Markdown is the interchange format, not a new website.

## Workflow

Prepare the target's normal Lean environment first. The command reads compiled
modules; editing `.lean` files without rebuilding does not change what it imports.
Pass the directories normally included in `LEAN_PATH` with repeated
`--search-path` arguments. Only Lean 4.34.1 is currently supported.

```sh
python -m proofreader.outline open \
  --lean /path/to/lean \
  --module OAI.Algebra.Universal.GraphCriterion \
  --declaration OAI.FiniteCongruence.labelCongruence_surjective \
  --search-path /path/to/compiled/project \
  --search-path /path/to/mathlib/.lake/build/lib/lean \
  --session /tmp/surjectivity --trust-project

python -m proofreader.outline inspect --session /tmp/surjectivity
python -m proofreader.outline inspect --session /tmp/surjectivity --frame 24
python -m proofreader.outline draft --session /tmp/surjectivity > proposal.json
# Edit only the editorial blocks in proposal.json.
python -m proofreader.outline check --session /tmp/surjectivity \
  --proposal proposal.json --trust-project
python -m proofreader.outline render --session /tmp/surjectivity > outline.md
```

Other imported packages need their compiled search paths too. No project-specific
Lean driver is needed; the same driver handles the supplied declaration.

The example data in `examples/agent-outline/` describes an initial three-block
outline, a two-direction expansion, and a supporting-lemma outline. It is bound
to the exact exported source digest. It is not accepted for a different proof.

```sh
python -m proofreader.outline expand --session /tmp/surjectivity \
  --block threshold --children examples/agent-outline/expanded-children.json \
  > expanded.json
python -m proofreader.outline check --session /tmp/surjectivity \
  --proposal expanded.json --trust-project

python -m proofreader.outline follow --session /tmp/surjectivity --frame 26 \
  --destination /tmp/path-lemma --trust-project
```

`follow` reads the actual constant in a source application. It does not search for
a lemma based on prose. Local applications, constructors, and non-proof-valued
declarations may not be openable as theorem outlines; rejection is not evidence
that they are mathematically unimportant. Private or escaped names outside the
current conservative CLI identifier syntax are also unsupported.

## Outline contract

A proposal contains a source digest, parent revision, title, introduction, and
nested blocks. Each block supplies an ID, source frame, title, commentary, and
children. Claims, assumptions, and source paths come from the existing expression
record. Proposals cannot supply replacement claims or proof terms.

Nested blocks must be strict source descendants of their parent. Source ancestors
cannot be disguised as independent siblings. Extraction is scheduled inner-first;
independent siblings can be displayed in either order. This permits a source-bound
decomposition, not arbitrary mathematical reordering or lemma invention.

`check` regenerates the source snapshot, compares the full expression record with
the original declaration, extracts the selected lemmas, replaces their occurrences
with applications, and kernel-checks the reconstructed theorem. Original source
reasoning outside the selected subproofs is retained, not claimed to be explained.
Empty outlines are allowed but count as zero intermediate lemmas.

Titles and commentary are deliberately unverified. Even a checked outline can
contain a wrong English explanation. The Markdown exposes exact closed claims
under each block and labels the commentary separately. There is no certified-
English or human-comprehension claim.

## Revisions

`draft` starts from the accepted revision. `expand` creates a proposal without
modifying the accepted state. `check` requires that proposal's parent to be the
current revision and holds an exclusive session lock through the native run.
Only a successful source replay, reconstruction, and result reconciliation may
advance the head. Accepted revisions are immutable and content-addressed.

The response identifies added, removed, changed, expanded, and unchanged blocks.
An expansion can preserve other blocks byte for byte. Rejected native attempts
retain their inputs, compiler logs, and observation records; static rejections are
returned as JSON errors before a native attempt is created. Failed session
initializations retain a backend observation and cannot be reused as success.

The session hashes its compiler, native backend, loaded `.olean` files, and existing
private/server/IR sidecars. Changes invalidate subsequent checking. File contents
are checked before and after a revision's native run; the run also verifies module
resolution. These are consistency checks, not authentication or a sandbox.
The runtime, shared libraries, metaprograms and compiled dependencies remain trusted.
A lock left by a killed process needs manual removal after confirming no writer
is active. The session is a local single-writer store, not a network service.

## Native checks

```sh
python -m pytest tests/test_agent_outline.py -q
python scripts/check_agent_outline.py --lean /path/to/lean \
  --output /tmp/outline-regression --trust-project
```

The second command runs synthetic declarations through the real CLI. It checks
initial and expanded outlines, byte-identical regeneration, actual-callee following,
stale revisions, invented claims, escaping scopes, forged source displays, and a
changed dependency body. The dependency change preserves the target statement and
body, so checking only the root expression would not detect it. Rejected updates
must leave the accepted head unchanged. A deliberate display forgery also bypasses
the Python hashes to test independent native source comparison.

No model runs in this regression. Passing it does not establish that the tool is
better than an agent using ordinary Lean facilities.

## Evaluation

The graph-criterion example remains the control from issue #16. The tool does not
get credit for discovering its mathematical explanation, which was already obtained
with ordinary tools. The functional test is whether an existing outline can be
expanded, followed into a supporting proof, and reconstructed without per-proof
checking code.

A fresh agent comparison remains separate. Both conditions should receive the
same raw sources, Lean environment, prompts, budget, and follow-ups. Only one gets
these commands. Record checked answers, unsupported requests, user interventions,
model/Lean cost, and custom driver code; do not substitute passing tests or a prose
preference score for mathematical understanding. No independent comparison result
is asserted by this implementation.
