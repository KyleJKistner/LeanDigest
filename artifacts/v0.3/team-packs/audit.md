# ProofReader workstream: audit

Independently attack source-path binding, judgement closures, display normalization, grammar assumptions, forged receipts, transport and corpus denominators. Produce executable falsifiers and a trust-boundary report without patching runtime code.

# Required return
Write SUMMARY.md with changed files, exact checks and exit codes, unrun checks, blockers, counterexamples and next task. Do not claim checks you did not execute.

# Ownership
tests/audit/
docs/AUDIT.md

# Acceptance
Produce reproducible negative examples with commands, expected/actual behavior and artifact hashes
Separate kernel type validity from English interpretation and source-context correspondence

# Known blocker
No independent auditor or reader study ran. Live substantial-proof mutations are rejected, but pretty-printer and English semantics are not formally verified. Attack the new certificate and snapshot route.


# File: README.md

# Lean ProofReader

Read a formal argument as mathematical prose without starting in a Lean editor.
The renderer is deterministic and makes no language-model API calls. Source
outlines, typed evidence, successful checking observations, English fidelity and
reader comprehension remain separate measurements.

## Version 0.3.0 — a retained substantial proof

The OpenAI Bézout-frame existence theorem now has a complete retained mathematical
reading: two gcd cases, divisibility witnesses, a Bézout calculation, nonzero
cancellation, and verification of the four final equalities. Lean **4.34.1**
accepted **86 selected original-proof judgements** and their independent source
paths. Repeated extraction was identical; altered paths, a false intermediate
claim and an altered snapshot were rejected. The reader accounts for all 86
exported frames in 59 displayed steps, with **16 independently replayable exact
integer-polynomial certificates** and no budget cuts in this selected example.

The theorem body is unchanged; imports were adapted. This is **not** a build of
the entire pinned OpenAI project, a whole-corpus translation, or a formal proof
of English fidelity. Formula text uses Lean's pretty-printer. Imported lemma
statements appear as mathematical dependencies; their proofs are not all expanded.
No human comprehension study has run.

See [executed validation](docs/VALIDATION_V0_3.md),
[source-bound reading and trust boundaries](docs/NARRATIVE.md), and
[the earlier exact-DAG contract](docs/KERNEL_IR.md).

## Open the reader

Python 3.11 or later. No runtime Python dependencies, API key, network connection
or Lean installation is needed to read the bundled proofs.

```sh
python -m proofreader narrative-demo -o reader.html
python -m proofreader serve
```

Open `http://127.0.0.1:8765`. The default library starts with the Bézout argument.
It also retains five small constructor-DAG examples and eight source-only OpenAI
declaration candidates. **Typed** includes the five DAG examples and the one
source-bound snapshot; the evidence badge distinguishes the routes. Inspect an
arithmetic step for its coefficient certificate; expand an intermediate fact for
its supporting argument. The Evidence panel records limitations and exact hashes.

The generated HTML is self-contained. Attachment viewers that disable JavaScript
may need the local server. `kernel-demo` still opens the v0.2 small-proof library;
`demo` still opens the source-only demonstration.

## Recheck the displayed argument without Lean

```sh
python -m proofreader narrative-read proofreader/data/bezout-snapshot.json \
  --source proofreader/data/bezout-original.lean \
  --receipt proofreader/data/bezout-receipt.json -o output/bezout
python -m proofreader check-narrative proofreader/data/bezout-snapshot.json \
  output/bezout/reading.json --certificates output/bezout/polynomial-certificates.json
```

This regenerates the reading and independently checks the polynomial identities.
It does not authenticate the source snapshot. Actual Lean re-extraction is
explicit opt-in:

```sh
python -m proofreader verify-narrative proofreader/data/bezout-snapshot.json \
  --driver proofreader/data/bezout-reproduce.lean \
  --backend axle --allow-remote -o output/recheck
```

This sends the complete driver to AXLE. Native execution instead uses an existing
trusted project and `--trust-project`. Elaborating Lean can run arbitrary code;
consent is not a sandbox. The browser has no execution endpoint. The exact
metaprograms ran remotely; native and installed-CLI transport integration remain
separate gates, not implied by the local reader tests.

## A typed export → a complete offline reading bundle

```sh
python -m pip install .
proofreader kernel-read artifacts/v0.2/and_swap.kernel.json \
  -o output/and-swap --context examples/kernel/Smoke.lean \
  --receipt artifacts/v0.2/and_swap.receipt.json
proofreader check-reading artifacts/v0.2/and_swap.kernel.json \
  output/and-swap/reading.json
```

The output includes `reader.html`, `reading.json`, `proof.txt`, `argument.json`,
`Check.lean`, and `coverage.json`. Without `--context` or `--module`, the
generated checker still requires the original theorem environment before replay. Reading validates constructor shape, scope,
original-proof paths and argument inventories. It does **not** execute Lean.
`check-reading` detects any divergence from deterministic English regeneration;
it is not an English parser or a formal semantic equivalence proof.

## Extract and check a project module

Use an already configured project's pinned Lean toolchain and dependencies:

```sh
proofreader extract-kernel --project lean --module ProofReader.Smoke \
  --output output/native-smoke --trust-project --verify
```

The v2 extractor enumerates **theorem declarations** from Lean's environment,
retains individual failures, emits the expected inventory, builds the reading
library and optionally checks all intermediate judgements. Proof-valued `def`s
and informal manuscripts are not yet part of this v2 theorem denominator.
The combined native command is implemented and has a mandatory integration test;
it has not run in this container because Lean/Lake is absent.

**Lean elaboration can execute arbitrary code.** `--trust-project` is consent,
not isolation. Use a trusted project or an independently secured disposable
sandbox without credentials. The web reader has no execution endpoint.

## Optional remote compilation

The AXLE adapter is explicit opt-in. It sends the **entire provided source
context and generated checking code** to the third-party service. It never sends
anything during ordinary reading.

```sh
proofreader extract-kernel --backend axle --lean-version 4.34.0 \
  --context examples/kernel/Showcase.lean --output output/remote \
  --allow-remote --verify
```

Use a self-contained context with the necessary imports, including `Lean`.
`ProofReaderKernel` is a reserved tool namespace excluded from local-source
inventory. Native imported-module enumeration does not rely on that exclusion.
All service responses, the exact request source, inventories and failures are
saved. API authentication can be supplied via `AXLE_API_KEY`; tokens are not
written to artifacts. Service availability/dependency caches are external.

Do not change an exported argument's recorded Lean version to force replay.
Re-extract on the desired version instead. Earlier remote environments had missing cached dependencies; availability changed during testing. The v0.3 substantial experiment succeeded on Lean 4.34.1 with minimal imports. The exact pinned OpenAI dependency environment remains unvalidated.

## Complete OpenAI benchmark target

Pinned repository `openai/math`, commit
`1581d4cbdd69a0faf34b2089614fe2a814316a6a`.

A fresh metadata traversal of all 23 `lean/OAI` domain subtrees counted
**122,458 Lean files / 1,571,301,358 source bytes**. Every returned subtree was
untruncated. This is a file inventory observation, **not a theorem count or a
successful proof run**. The observation is saved under `artifacts/v0.2/`.

```sh
proofreader fetch-openai work/openai-math
proofreader benchmark work/openai-math -o output/inventory
proofreader extract-corpus work/openai-math -o output/shard-0 \
  --trust-project --engine kernel --shard-count 16 --shard-index 0
# Run the other shard indices, then reconcile every report.
proofreader aggregate work/openai-math output/shard-*/extraction.json \
  -o output/aggregate
```

The new kernel engine is the default for corpus extraction. Missing modules,
export failures and failed checks stay in the denominator. Large source
benchmarks use a ledger-only mode instead of retaining a multi-gigabyte proof
book in memory. Per-module readers are produced during typed extraction.
See [benchmark scope](docs/OPENAI_BENCHMARK.md).

## Tests

```sh
python -m pip install '.[dev,webtest]'
python -m playwright install chromium
python scripts/build_demo.py
python scripts/build_typed_demo.py
python -m pytest -q

# These tests may not skip in the native CI job.
PROOFREADER_REQUIRE_LEAN=1 python -m pytest \
  tests/test_lean_integration.py tests/test_kernel_integration.py -q
```

Local results and exact successful/negative remote checking sources are included
under `artifacts/v0.2/`. The CI workflow is provided; it has not run on GitHub.

## Repository and agent workflow

There is no hosted deployment and no GitHub repository was created during this
build. `scripts/publish.sh` uses your authenticated GitHub CLI to create
`KyleJKistner/lean-proofreader`, privately by default. No existing remote
repository was modified.

No independent coding agents were launched. `AGENTS.md`, `agents/tasks.json` and
`scripts/team.py` provide bounded work packages and an optional external-agent
launcher in separate worktrees. A work package is not evidence of agent execution.

The ideas of deterministic verbalization and expandable proof displays have
precedents in LeanInformal, Informath and Verbose Lean. This release makes no
novelty or publication claim. New code is MIT; OpenAI source samples retain their
Apache 2.0 license. See `THIRD_PARTY_NOTICES.md`.



# File: docs/TRUST.md

# Trust boundary — 0.2

## Three inputs, different authority

A `.lean` **source outline** is a lexical/layout reading aid. Recognizing `simp`
does not reveal a mathematical derivation. None of the nine OpenAI source-mode
demo declarations is relabelled as kernel checked.

A `proofreader.kernel-export/v2` **typed argument** is a constructor DAG plus a
set of typed proof-subterm judgements. Python validates a strict schema, universe
and binder scope, immutable original-root paths, exact child/argument inventories,
and resource budgets. It does not serve as a Lean type checker.

A **checking observation/receipt** records a run. An imported JSON file is not a
signature, an attestation, or proof of its own origin. The browser never claims to
authenticate it. The release's remote observations include request identifiers,
exact request-source hashes, positive markers and negative outcomes.

## What the generated Lean program checks

1. Exact Lean version and universe-parameter inventory.
2. Transitive axiom inventory matching the argument export.
3. Original declaration statement and proof AST identity, after erasing metadata.
   Proof irrelevance/definitional equality is not substituted for this exactness.
4. The original reconstructed proof submitted as a new kernel-checked theorem.
5. Every recorded proof path followed independently in Lean through that original
   proof; its real enclosing binders are used to close the subterm.
6. Each resulting term/type judgement submitted through `addDecl`: theorem
   declarations for proofs and safe definitions for data arguments.
7. Proposition/data and assumption/object classification checked in Lean.

`debug.skipKernelTC` is forced false around the new declarations. A failure after
root replay but before the final marker is an overall failure. The exact final
marker includes the argument hash and judgement count. The verifier also checks
process/API success, errors, failed declarations, returned source and version.

This still assumes a trusted Lean implementation, checking program, runtime,
project metaprograms, imported dependencies and service execution. It does not
cryptographically authenticate compiled dependencies, hardware, or the service.
An adversarial project with arbitrary metaprogram execution is not made logically
or operationally trustworthy merely by passing a command-line flag.

## What is not certified

The English printer is deterministic and regression-tested, not formally proved.
`check-reading` checks regeneration, not a formal interpretation of English.
Beta/zeta display simplification is bounded and capture-avoiding in the tested
implementation; original expression nodes remain authoritative. Unknown symbols,
recursors, large expressions and named lemmas can remain explicitly unexpanded.
Standard mathematical notation still needs its displayed types and instances.

No human comprehension study, full-corpus prose-completeness result, paper-to-Lean
correspondence proof, or correctness claim for OpenAI's manuscripts is implied.
The v2 enumerator covers theorem declarations, not all proof-valued definitions.
The legacy exporter retains a wider declaration inventory but does not provide
v2 intermediate-judgement verification.

## Axioms and admissions

Default permitted axioms: `propext`, `Classical.choice`, `Quot.sound`. These are
visible, not silently described as axiom-free. Additional axioms require explicit
`--permit-axiom` and remain visible. `sorryAx` / `Lean.sorryAx` cannot be permitted
through that option. An empty transitive axiom inventory is reported separately.

## Execution and transport

Offline reading makes no model, telemetry, CDN or service requests. The local
single-user server accepts source text, not arbitrary filesystem paths. It binds
to loopback and checks Host/Origin; it has no Lean build or shell endpoint.

Native compilation requires `--trust-project`; this does not sandbox anything.
Remote operations require `--allow-remote` and send complete code to AXLE. Remote
requests require UTF-8 JSON, fixed official host, bounded responses and no redirect
following. API keys are read from the environment and excluded from artifacts.

Source snapshots and module/source hashes do not authenticate every dependency
binary. Corpus reports are unsigned reproducible ledgers, not self-authenticating
mathematical certificates. Security tests are not an independent security audit.

## Source-bound route added in 0.3

`source-bound-snapshot` is not `typed-export`. Its formula strings use Lean's pretty-printer. Read docs/NARRATIVE.md for the full trust boundary, re-extraction checks and integer-polynomial certificates. No snapshot or imported receipt self-authenticates. Exact source paths and selected judgements ran on 4.34.1 for the retained example; the full pinned project did not.



# File: docs/KERNEL_IR.md

# Frozen v2 argument contract

Authority is `proofreader.kernel-export/v2`. Reader output remains the backwards-
compatible `proofreader.document/v1` format with additional typed metadata.

## Expression graph

`exprs` is a topological DAG. Every edge refers to an earlier node. Constructor
fields are exact; unknown fields, extra variables, unresolved metavariables and
unlisted universe parameters are rejected. Names preserve anonymous/str/num
constructors, avoiding collisions between a single dotted component and a
qualified name. Binder indices are de Bruijn indices, not text substitutions.
The root `type` and `term` must be closed under `levels`.

Each step records its `term`, Lean-inferred `type`, `is_proof`, `path`, `children`,
complete application `arguments`, optional `domain_is_prop`, and `truncated`.
No pretty-print string or prewritten English sentence is trusted as mathematics.

## Original-expression paths

- Application: 0 = function, 1 = argument.
- Lambda/forall: 0 = domain, 1 = body; entering the body adds the original binder.
- Let: 0 = type, 1 = value, 2 = body; the body adds the original let binder.
- Projection: 0 = object.

Python validates every path. The generated Lean program independently follows it
in the imported original proof and closes the result over the actual enclosing
context. The term must equal the submitted closed judgement term before typing.
Native kernel checks then validate all proof and data types.

## Coverage and omission

The raw expression graph retains the original proof. The typed reading expansion
has depth/step budgets; hitting them creates explicit truncated steps, not a
claim of conceptual explanation. In-flight siblings may cause the exporter to
exceed its 1,500-step expansion threshold slightly; the whole response remains
size-bounded. Explicit formula-normalization limits produce visible references.

Unknown named lemmas are cited, not purportedly explained. Imports may contain
arbitrary definitions; dictionary expansion and semantic abstraction remain work.
Do not redefine success as printing an opaque `apply` sentence for every theorem.

## Provenance states

`exported`, `structurally_validated`, `rendered`, `path_linkage_checked_in_lean`,
`all_judgements_kernel_checked`, `regeneration_matched`, `english_formally_verified`,
and `human_readability_evaluated` are distinct. Only actual checks may populate
execution states. A saved imported receipt never authenticates its own producer.

Keep the schema stable while improving explanations. Changes to the display
compiler require a printer version bump and determinism/regeneration tests.



# File: docs/ACCEPTANCE.md

# Acceptance gates — 0.2.0

These gates are independent. A successful build, readable page or positive receipt
must not be counted as an English fidelity or whole-corpus result.

## A0 — deterministic, usable reading software

Local tests cover source scanning, typed-expression validation, English
regeneration, capture-avoiding display reduction, the browser, packaging and CLI.
The default reader contains five real typed exports and nine source candidates.
Unsupported expressions remain visible. This is implemented, but it is not a
human comprehension result. See `VALIDATION_V0_2.md` for the executed test count.

## A1 — actual theorem and intermediate-judgement checking

Required: compile the exporter; reconstruct the original declaration; independently
follow each source path; kernel-check every displayed term/type judgement; retain
version, universe and axiom inventories. Negative cases must fail for the intended
reason, not merely because the driver has a syntax error.

Current: individual remote exporter and checker programs executed on Lean 4.34.0.
Five compact exports are retained. One retained example has all original-path and
18 term/type judgement checks observed, with source-path, intermediate-type and
version mutations rejected. Earlier tests reject axiom and binder-role mutations.
The complete native 4.34.1 module pipeline is still **unrun here**, and its mandatory
CI test must pass without skips before claiming native integrated acceptance.

## A2 — complete expected-corpus accounting and execution

Required: pin the source and dependencies; acquire all expected files; enumerate
actual theorem declarations from every required module; retain every build,
export and checking failure; reconcile independent shards.

Current: complete metadata observation for the 23 `lean/OAI` domain subtrees:
122,458 Lean files, 1,571,301,358 bytes. The file contents have not all been acquired
or built. Expected theorem count is unknown until all modules are enumerated.
The v2 denominator is `.thmInfo` theorem declarations, not proof-valued definitions
or manuscript claims. Expanding that scope requires an explicit contract change.
The adapted Bézout-body experiment is not an exact pinned-project pass.

## A3 — mathematical reading completeness

Required: expose all hypotheses, conclusions, witness conditions, branch scopes,
lemma statements and dependencies for every theorem in scope. A bare lemma name
is not a complete explanation. Generic terms, opaque computations, capped
branches and unresolved vocabulary remain separately visible and measurable.

Current: typed assumptions, introductions, basic logical constructors, witness
introduction, simple alternatives, equalities and injectivity application render
as mathematics. Arbitrary recursors, induction and dependency statements are not
fully explained. The large Bézout export hit explicit expansion caps. No full
corpus English completeness result is claimed.

## A4 — faithful language and compression

Required: bind each displayed inference to the exact original proof path and its
checked claim; make grammar interpretation and display-normalization semantics
explicit; prove the relevant interpretation/round-trip properties. Compression
must preserve an inspectable argument, not substitute a new plausible proof.

Current: the typed judgement and path checker exists and has live positive and
negative evidence. `check-reading` rejects changes to regenerated statements,
parameters and proof prose. The grammar, Python renderer and display normalizer
are **not formally proved correct**. Byte-for-byte regeneration is not semantic
certification. The English acceptance gate therefore remains false.

## A5 — reduced burden on mathematicians

Required: independently selected complete proofs and comprehension/error-detection
tasks with practicing mathematicians; compare review time and correctness against
Lean and relevant existing readers. Do not infer benefit from screenshots or
counts of grammatical sentences.

Current: no human study. This remains the ultimate product acceptance criterion.



# File: proofreader/kernel.py

"""Path-bound typed proof IR and replay. Python checks structure; Lean checks types.

This layer deliberately does NOT label an English document as formally verified.
It binds every rendered judgement to an actual original proof subterm and emits
kernel checks for the original proof, intermediate judgements, and data arguments.
Neither a supplied pretty-print string nor an imported receipt is trusted.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import copy
import json
import re
from typing import Any, Iterable

from .core import InvalidExport, BINDERS, NORMALIZE_LEAN, lean_string, name_to_lean, level_to_lean
from .model import canonical_json, digest

SCHEMA = "proofreader.kernel-export/v2"
PATH_LEAN = 'private partial def proofreaderAtPath (e : Lean.Expr) (path : List Nat)\n    (context : List Lean.Expr := []) : Except String (Lean.Expr × List Lean.Expr) := do\n  match path with\n  | [] => return (e, context)\n  | k :: ks =>\n    match e, k with\n    | .app f _, 0 => proofreaderAtPath f ks context\n    | .app _ a, 1 => proofreaderAtPath a ks context\n    | .lam _ d _ _, 0 | .forallE _ d _ _, 0 => proofreaderAtPath d ks context\n    | .lam _ _ b _, 1 | .forallE _ _ b _, 1 => proofreaderAtPath b ks (e :: context)\n    | .letE _ t _ _ _, 0 => proofreaderAtPath t ks context\n    | .letE _ _ v _ _, 1 => proofreaderAtPath v ks context\n    | .letE _ _ _ b _, 2 => proofreaderAtPath b ks (e :: context)\n    | .proj _ _ b, 0 => proofreaderAtPath b ks context\n    | _, _ => throw "Invalid source proof path"\n\nprivate def proofreaderClose (e : Lean.Expr) (context : List Lean.Expr) : Except String Lean.Expr :=\n  context.foldlM (fun value binder => do\n    match binder with\n    | .lam n d _ bi | .forallE n d _ bi => return .lam n d value bi\n    | .letE n t v _ nd => return .letE n t v value nd\n    | _ => throw "Invalid source binder") e\n\nprivate def proofreaderClosedAt (root : Lean.Expr) (path : List Nat) : Except String Lean.Expr := do\n  let (term, context) ← proofreaderAtPath root path\n  proofreaderClose term context\n'

EDGES = {"app": ("fn", "arg"), "lam": ("domain", "body"),
         "forall": ("domain", "body"), "let": ("type", "value", "body"), "proj": ("of",)}
FIELDS = {
    "bvar": {"tag", "index"}, "sort": {"tag", "level"},
    "const": {"tag", "name", "levels"}, "app": {"tag", "fn", "arg"},
    "lam": {"tag", "name", "domain", "body", "binder"},
    "forall": {"tag", "name", "domain", "body", "binder"},
    "let": {"tag", "name", "type", "value", "body", "nondep"},
    "nat": {"tag", "value"}, "str": {"tag", "value"},
    "proj": {"tag", "name", "index", "of"},
}


def require(test: bool, message: str) -> None:
    if not test:
        raise InvalidExport(message)


def nat(x: Any, maximum: int = 2**63 - 1) -> int:
    require(type(x) is int and 0 <= x <= maximum, "Expected a bounded nonnegative integer")
    return x


def name_key(n: Any, depth: int = 0) -> tuple:
    require(isinstance(n, dict) and depth < 128, "Malformed or too deeply nested name")
    t = n.get("tag")
    if t == "anonymous":
        require(set(n) == {"tag"}, "Unknown name field")
        return ()
    require(t in {"str", "num"} and set(n) == {"tag", "prefix", "value"}, "Invalid name constructor")
    v = n["value"]
    require(isinstance(v, str) and len(v) < 100_000, "Invalid name component")
    if t == "num":
        require(bool(re.fullmatch(r"0|[1-9][0-9]*", v)), "Noncanonical numeric name")
    return name_key(n["prefix"], depth + 1) + ((t, v),)


def display_name(n: dict) -> str:
    """An injective spelling: numeric components and dotted string components differ."""
    parts = []
    for tag, v in name_key(n):
        if tag == "num":
            parts.append("#" + v)
        elif re.fullmatch(r"[^\W\d]\w*", v, re.UNICODE):
            parts.append(v)
        else:
            parts.append("[" + json.dumps(v, ensure_ascii=False) + "]")
    return ".".join(parts) or "[anonymous]"


def plain_name(n: dict) -> str | None:
    key = name_key(n)
    if all(t == "str" and re.fullmatch(r"[^\W\d]\w*", v, re.UNICODE) for t, v in key):
        return ".".join(v for _, v in key)
    return None


def validate_level(n: Any, params: set[tuple], depth: int = 0) -> None:
    require(isinstance(n, dict) and depth < 128, "Invalid universe expression")
    tag = n.get("tag")
    if tag == "zero":
        require(set(n) == {"tag"}, "Unknown universe field")
    elif tag == "succ":
        require(set(n) == {"tag", "of"}, "Unknown universe field")
        validate_level(n["of"], params, depth + 1)
    elif tag in {"max", "imax"}:
        require(set(n) == {"tag", "left", "right"}, "Unknown universe field")
        validate_level(n["left"], params, depth + 1)
        validate_level(n["right"], params, depth + 1)
    elif tag == "param":
        require(set(n) == {"tag", "name"}, "Unknown universe field")
        require(name_key(n["name"]) in params, "Undeclared universe parameter")
    else:
        raise InvalidExport("Unsupported/unresolved universe constructor")


class Dag:
    """Topological constructor DAG; open-variable demand and identity are bottom-up.

    The demand calculation permits million-node terms without recursively expanding
    shared terms. Hashes are used as identities, not as mathematical certificates.
    """
    def __init__(self, nodes: list[dict], params: list[dict], limit: int = 250_000):
        require(isinstance(nodes, list) and 0 < len(nodes) <= limit, "Invalid expression inventory size")
        require(isinstance(params, list), "Invalid universe inventory")
        self.params = {name_key(x) for x in params}
        require(len(self.params) == len(params), "Duplicate universe parameters")
        self.nodes = copy.deepcopy(nodes)
        self.hashes: list[str] = []
        self.demand: list[int] = []
        self.intern: dict[str, int] = {}
        for i, n in enumerate(self.nodes):
            self._append_index(n, i)

    def _append_index(self, n: dict, i: int) -> None:
        require(isinstance(n, dict) and n.get("tag") in FIELDS, "Unknown expression constructor")
        tag = n["tag"]
        require(set(n) == FIELDS[tag], f"Unknown/missing fields for {tag}")
        for field in EDGES.get(tag, ()):
            require(nat(n[field]) < i, "DAG edges must refer to earlier expressions")
        if "name" in n:
            name_key(n["name"])
        if tag == "sort":
            validate_level(n["level"], self.params)
        if tag == "const":
            require(isinstance(n["levels"], list), "Invalid constant universe list")
            for level in n["levels"]:
                validate_level(level, self.params)
        if tag in {"lam", "forall"}:
            require(n["binder"] in BINDERS, "Unknown binder kind")
        if tag == "let":
            require(type(n["nondep"]) is bool, "Invalid let binder flag")
        if tag in {"bvar", "proj"}:
            nat(n["index"], 1_000_000)
        if tag in {"nat", "str"}:
            require(isinstance(n["value"], str) and len(n["value"]) <= 100_000, "Invalid literal")
            if tag == "nat":
                require(bool(re.fullmatch(r"0|[1-9][0-9]*", n["value"])), "Invalid numeric literal")
        children = EDGES.get(tag, ())
        need = max((self.demand[n[f]] for f in children), default=0)
        if tag == "bvar":
            need = n["index"] + 1
        elif tag in {"lam", "forall"}:
            need = max(self.demand[n["domain"]], max(0, self.demand[n["body"]] - 1))
        elif tag == "let":
            need = max(self.demand[n["type"]], self.demand[n["value"]], max(0, self.demand[n["body"]] - 1))
        canonical = {k: self.hashes[v] if k in children else v for k, v in n.items()}
        fingerprint = digest(canonical_json(canonical))
        self.hashes.append(fingerprint)
        self.demand.append(need)
        self.intern.setdefault(fingerprint, i)

    def ref(self, i: Any) -> int:
        require(nat(i) < len(self.nodes), "Expression reference is outside the inventory")
        return i

    def add(self, n: dict) -> int:
        children = EDGES.get(n["tag"], ())
        h = digest(canonical_json({k: self.hashes[v] if k in children else v for k, v in n.items()}))
        if h in self.intern:
            return self.intern[h]
        i = len(self.nodes)
        self._append_index(n, i)
        self.nodes.append(n)
        return i

    def equal(self, a: int, b: int) -> bool:
        return self.hashes[self.ref(a)] == self.hashes[self.ref(b)]

    def app(self, i: int) -> tuple[int, list[int]]:
        args = []
        while self.nodes[i]["tag"] == "app":
            n = self.nodes[i]; args.append(n["arg"]); i = n["fn"]
        return i, list(reversed(args))

    def locate(self, root: int, path: list[int]) -> tuple[int, list[int]]:
        require(isinstance(path, list) and len(path) <= 512, "Invalid proof path")
        i = self.ref(root); ctx = []
        for edge in path:
            n = self.nodes[i]; tag = n["tag"]
            fields = EDGES.get(tag, ())
            require(nat(edge) < len(fields), "Invalid proof path edge")
            if (tag in {"lam", "forall"} and edge == 1) or (tag == "let" and edge == 2):
                ctx.append(i)
            i = n[fields[edge]]
        return i, ctx

    def close(self, expr: int, ctx: list[int], *, is_type: bool) -> int:
        require(self.demand[expr] <= len(ctx), "Open expression exceeds its local scope")
        for binder in reversed(ctx):
            b = self.nodes[binder]
            if b["tag"] == "let":
                expr = self.add({**b, "body": expr})
            else:
                expr = self.add({**b, "tag": "forall" if is_type else "lam", "body": expr})
        require(self.demand[expr] == 0, "Closure is not closed")
        return expr

    def uses_binder(self, i: int, depth: int = 0) -> bool:
        todo = [(i, depth)]; seen = set()
        while todo:
            j, d = todo.pop()
            if (j, d) in seen: continue
            seen.add((j, d)); n = self.nodes[j]; t = n["tag"]
            if t == "bvar" and n["index"] == d: return True
            for f in EDGES.get(t, ()):
                extra = int(f == "body" and t in {"lam", "forall", "let"})
                todo.append((n[f], d + extra))
        return False


@dataclass(frozen=True)
class Claim:
    label: str
    path: tuple[int, ...]
    term: int
    typ: int
    proof: bool
    ctx: tuple[int, ...]


class Argument:
    def __init__(self, record: dict):
        require(isinstance(record, dict) and record.get("schema") == SCHEMA, "Unsupported typed argument schema")
        self.record = copy.deepcopy(record)
        record = self.record  # Own the validated snapshot, including all step metadata.
        self.name = display_name(record.get("name"))
        self.dag = Dag(record.get("exprs"), record.get("levels"))
        self.root = self.dag.ref(record.get("term"))
        self.typ = self.dag.ref(record.get("type"))
        require(self.dag.demand[self.root] == self.dag.demand[self.typ] == 0, "Original theorem contains free variables")
        require(isinstance(record.get("axioms"), list) and all(isinstance(x, str) for x in record["axioms"]), "Invalid axiom inventory")
        require(len(set(record["axioms"])) == len(record["axioms"]), "Duplicate axiom inventory")
        require(isinstance(record.get("lean_version"), str), "Missing toolchain version")
        self.steps = record.get("steps")
        require(isinstance(self.steps, list) and 0 < len(self.steps) <= 20_000, "Invalid judgement inventory")
        self.claims: list[Claim] = []
        self.contexts: list[list[int]] = []
        self.domains: list[tuple[int, int, bool]] = []
        self._validate_steps()
        self.sha256 = digest(canonical_json(self.record))

    def _judgement(self, s: dict, label: str) -> Claim:
        require(isinstance(s, dict), "Malformed judgement")
        actual, ctx = self.dag.locate(self.root, s.get("path"))
        term = self.dag.ref(s.get("term")); typ = self.dag.ref(s.get("type"))
        require(self.dag.equal(term, actual), "Judgement term does not match its original proof path")
        require(self.dag.demand[term] <= len(ctx) and self.dag.demand[typ] <= len(ctx), "Judgement escapes its binder scope")
        require(type(s.get("is_proof")) is bool, "Invalid proof/data classification")
        c = Claim(label, tuple(s["path"]), term, typ, s["is_proof"], tuple(ctx))
        self.claims.append(c)
        return c

    def _validate_steps(self) -> None:
        counts = [0] * len(self.steps); paths = set()
        for i, s in enumerate(self.steps):
            c = self._judgement(s, f"step_{i}")
            require(c.path not in paths, "Duplicated proof path")
            paths.add(c.path); self.contexts.append(list(c.ctx))
            if i == 0:
                require(not c.path and self.dag.equal(c.term, self.root) and c.proof, "Missing proof-root judgement")
            require(type(s.get("truncated")) is bool, "Missing explicit expansion status")
            children, args = s.get("children"), s.get("arguments")
            require(isinstance(children, list) and isinstance(args, list), "Malformed children or arguments")
            require(all(type(ch) is int for ch in children), "Invalid child judgement reference")
            require(len(set(children)) == len(children), "Duplicated child judgement")
            for ch in children:
                require(i < nat(ch) < len(self.steps), "Reading graph is cyclic or out of range")
                counts[ch] += 1
            node = self.dag.nodes[c.term]; tag = node["tag"]
            expected_paths = []
            if s["truncated"]:
                require(not children and not args, "Truncated step has hidden children")
                continue
            if tag == "lam":
                require(type(s.get("domain_is_prop")) is bool, "Missing binder classification")
                self.domains.append((i, self.dag.close(node["domain"], list(c.ctx), is_type=True), s["domain_is_prop"]))
                expected_paths = [list(c.path) + [1]]
                require(not args, "Lambda has spurious application arguments")
            elif tag == "let":
                require(not args, "Let expression has spurious application arguments")
                # The current exporter records a value derivation only when it is a proof.
                # A skipped value is displayed as a definition, not as an explained claim.
                expected_paths = ([list(c.path) + [1]] if len(children) == 2 else []) + [list(c.path) + [2]]
            elif tag == "app":
                _, actual_args = self.dag.app(c.term)
                require(len(args) == len(actual_args), "Application argument inventory incomplete")
                for k, a in enumerate(args):
                    ac = self._judgement(a, f"step_{i}_arg_{k}")
                    ap = list(c.path) + [0] * (len(args) - k - 1) + [1]
                    require(list(ac.path) == ap and self.dag.equal(ac.term, actual_args[k]), "Application argument path mismatch")
                    if ac.proof:
                        require(type(a.get("step")) is int and a["step"] in children, "Proof argument lacks a supporting step")
                        cs = self.steps[a["step"]]
                        require(cs["path"] == ap and self.dag.equal(cs["term"], ac.term) and self.dag.equal(cs["type"], ac.typ), "Supporting judgement is for a different claim")
                        expected_paths.append(ap)
                    else:
                        require("step" not in a, "Data argument wrongly attached as proof")
            elif tag == "proj":
                expected_paths = [list(c.path) + [0]]
                require(not args, "Projection has spurious application arguments")
            else:
                require(not args, "Non-application has application arguments")
            require([self.steps[x]["path"] for x in children] == expected_paths, "Supporting proof tree does not reconcile with original term")
        require(counts[0] == 0 and all(n == 1 for n in counts[1:]), "Unreachable or multiply parented proof judgement")

    def closed_claims(self) -> list[tuple[str, int, int, bool]]:
        return [(c.label, self.dag.close(c.term, list(c.ctx), is_type=False),
                 self.dag.close(c.typ, list(c.ctx), is_type=True), c.proof) for c in self.claims]

    def coverage(self) -> dict:
        return {"typed_steps": len(self.steps), "typed_judgements": len(self.claims),
                "shared_expression_nodes": len(self.record["exprs"]),
                "truncated_steps": sum(s["truncated"] for s in self.steps),
                "path_binding_validated": True, "english_formally_verified": False}


def dag_lean_lines(dag: Dag) -> list[str]:
    """Generate linear-size, topological Lean constructor bindings."""
    out = []
    names: dict[tuple, str] = {}
    def nm(n):
        key = name_key(n)
        if key in names: return names[key]
        if n["tag"] == "anonymous": code = ".anonymous"
        else:
            prefix = nm(n["prefix"])
            value = lean_string(n["value"]) if n["tag"] == "str" else n["value"]
            code = f".{n['tag']} {prefix} {value}"
        label = f"n{len(names)}"
        out.append(f"  let {label} : Name := {code}")
        names[key] = label
        return label
    for i, n in enumerate(dag.nodes):
        t = n["tag"]
        if t == "bvar": code = f".bvar {n['index']}"
        elif t == "sort": code = f".sort {level_to_lean(n['level'])}"
        elif t == "const": code = f".const {nm(n['name'])} [{', '.join(level_to_lean(x) for x in n['levels'])}]"
        elif t == "app": code = f".app e{n['fn']} e{n['arg']}"
        elif t in {"lam", "forall"}:
            code = f".{('lam' if t == 'lam' else 'forallE')} {nm(n['name'])} e{n['domain']} e{n['body']} .{BINDERS[n['binder']]}"
        elif t == "let": code = f".letE {nm(n['name'])} e{n['type']} e{n['value']} e{n['body']} {str(n['nondep']).lower()}"
        elif t == "nat": code = f".lit (.natVal {n['value']})"
        elif t == "str": code = f".lit (.strVal {lean_string(n['value'])})"
        elif t == "proj": code = f".proj {nm(n['name'])} {n['index']} e{n['of']}"
        else: raise InvalidExport("Unsupported constructor")
        out.append(f"  let e{i} : Expr := {code}")
    return out


def replay_source(record: dict, *, imports: list[str] | None = None) -> str:
    a = Argument(record)
    claims = a.closed_claims()
    imports = imports or []
    require(all(re.fullmatch(r"[A-Za-z_][A-Za-z_0-9]*(\.[A-Za-z_][A-Za-z_0-9]*)*", m) for m in imports), "Unsafe import path")
    name = name_to_lean(record["name"])
    levels = "[" + ", ".join(name_to_lean(x) for x in record["levels"]) + "]"
    axioms = "#[" + ", ".join(lean_string(x) for x in record["axioms"]) + "]"
    cs = ",\n    ".join(f"({lean_string(label)}, e{tm}, e{tp}, {str(p).lower()})" for label, tm, tp, p in claims)
    ds = ", ".join(f"({i}, e{typ}, {str(p).lower()})" for i, typ, p in a.domains)
    ps = ",\n    ".join(f"({lean_string(c.label)}, [{', '.join(map(str,c.path))}], e{tm})" for c, (_,tm,_,_) in zip(a.claims, claims))
    lines = ["import Lean", "import Lean.Util.CollectAxioms"] + ["import " + m for m in imports]
    lines += ["open Lean Elab Command", NORMALIZE_LEAN, PATH_LEAN,
              "set_option maxRecDepth 10000 in", "set_option maxHeartbeats 2000000 in", "run_elab do"]
    lines += dag_lean_lines(a.dag)
    lines += [f'  unless Lean.versionString == {lean_string(record["lean_version"])} do throwError "Toolchain version mismatch"',
              f"  let original ← getConstInfo {name}",
              f"  unless original.levelParams == {levels} do throwError \"Universe inventory mismatch\"",
              f"  let actualAxioms := (← Lean.collectAxioms {name}).map Name.toString",
              f"  let expectedAxioms : Array String := {axioms}",
              "  unless actualAxioms.size == expectedAxioms.size && actualAxioms.all expectedAxioms.contains && expectedAxioms.all actualAxioms.contains do",
              "    throwError \"Axiom inventory mismatch\"",
              f"  unless proofreaderEraseMetadata original.type == e{a.typ} do throwError \"Statement AST mismatch\"",
              "  let originalValue ← match original with",
              "    | .thmInfo v => pure v.value",
              "    | _ => throwError \"Expected theorem\"",
              f"  unless proofreaderEraseMetadata originalValue == e{a.root} do throwError \"Proof AST mismatch\"",
              f"  let base := {lean_string('ProofReaderJudgements.h' + a.sha256[:20])}.toName",
              "  withOptions (fun o => o.setBool `debug.skipKernelTC false) do",
              f"    addDecl <| .thmDecl {{ name := .str base \"root\", levelParams := {levels}, type := e{a.typ}, value := e{a.root} }}",
              '  logInfo "PROOFREADER_REPLAY_OK"',
              f"  let sourceBindings : Array (String × List Nat × Expr) := #[{ps}]",
              "  for (label, path, expectedValue) in sourceBindings do",
              "    match proofreaderClosedAt (proofreaderEraseMetadata originalValue) path with",
              '    | .error message => throwError "{message}: {label}"',
              '    | .ok actual => unless actual == expectedValue do throwError "Source linkage mismatch: {label}"',
              '  logInfo "PROOFREADER_PATHS_OK"',
              f"  let claims : Array (String × Expr × Expr × Bool) := #[{cs}]",
              "  for (label, value, type, proof) in claims do",
              "    let isProp ← Meta.isProp type",
              '    unless isProp == proof do throwError "Proof/data classification mismatch: {label}"',
              "    withOptions (fun o => o.setBool `debug.skipKernelTC false) do",
              "      if proof then",
              f"        addDecl <| .thmDecl {{ name := .str base label, levelParams := {levels}, type := type, value := value }}",
              "      else",
              f"        addDecl <| .defnDecl {{ name := .str base label, levelParams := {levels}, type := type, value := value, hints := .abbrev, safety := .safe }}",
              f"  let domains : Array (Nat × Expr × Bool) := #[{ds}]",
              "  for (i, domain, expected) in domains do",
              "    let actual ← Meta.isProp domain",
              '    unless actual == expected do throwError "Assumption/object classification mismatch: {i}"',
              f'  logInfo "PROOFREADER_JUDGEMENTS_OK:{a.sha256}:{len(claims)}"', ""]
    return "\n".join(lines)


def read_record(path: str | Path) -> dict:
    p = Path(path)
    require(p.stat().st_size < 256_000_000, "Export exceeds size budget")
    from .kernel_io import strict_json
    d = strict_json(p.read_bytes())
    Argument(d)
    return d



# File: proofreader/english.py

"""Deterministic mathematical reading views for the path-bound proof format.

No LLM, tactic-name interpretation, author prose, or untrusted pretty-print field
is used. This is a tested compiler/printer, not a machine-proved English semantics.
"""
from __future__ import annotations
from dataclasses import asdict, replace
import copy
import json
import re
from typing import Any
from .kernel import Argument, Dag, InvalidExport, display_name, plain_name, require
from .normalization import Reduction, DisplayLimit
from .model import Declaration, Document, Span, Step, canonical_json, digest, walk_steps

PRINTER_VERSION = "math-en/0.2.0"


def fresh_name(raw: dict, used: list[str], fallback: str = "x") -> str:
    text = plain_name(raw)
    base = text if text and "." not in text and not text.startswith("_") else fallback
    candidate = base; i = 2
    while candidate in used:
        candidate = f"{base}_{i}"; i += 1
    return candidate


class Formula:
    """A conservative notation dictionary, keyed by exact Lean constant identity."""
    INFIX = {"Eq": (3, "="), "And": (2, "∧"), "Or": (2, "∨"), "Iff": (2, "↔"),
             "LT.lt": (4, "<"), "LE.le": (4, "≤"), "HAdd.hAdd": (6, "+"),
             "HSub.hSub": (6, "−"), "HMul.hMul": (6, "·"), "HDiv.hDiv": (6, "/"),
             "Nat.add": (2, "+"), "Nat.mul": (2, "·"), "Nat.sub": (2, "−")}
    CONSTANTS = {"Nat": "ℕ", "Int": "ℤ", "Rat": "ℚ", "Real": "ℝ", "True": "True", "False": "False"}

    def __init__(self, dag: Dag, max_chars: int = 20000):
        self.dag = dag; self.max_chars = max_chars
        self.unknown_constants: set[str] = set()
        self.reduction = Reduction(dag)

    def level(self, n: dict) -> str:
        t = n["tag"]
        if t == "zero": return "0"
        if t == "param": return display_name(n["name"])
        if t == "succ": return f"({self.level(n['of'])}+1)"
        return f"{t}({self.level(n['left'])}, {self.level(n['right'])})"

    def render(self, i: int, ctx: list[str] | None = None) -> str:
        budget = [5000]
        text = self._render(i, ctx or [], 0, budget)
        if len(text) > self.max_chars:
            # Explicit reference, never silent truncation of a proposition.
            return f"[expression e{i}; expand its exact constructor record]"
        return text

    def _render(self, i: int, ctx: list[str], depth: int, budget: list[int]) -> str:
        budget[0] -= 1
        if depth > 100 or budget[0] < 0:
            return f"[expression e{i}; expansion limit]"
        try: i = self.reduction.head(i)
        except DisplayLimit: return f"[expression e{i}; normalization limit]"
        n = self.dag.nodes[i]; t = n["tag"]
        r = lambda j, cs=ctx: self._render(j, cs, depth + 1, budget)
        if t == "bvar":
            require(n["index"] < len(ctx), "Formula references an out-of-scope binder")
            return ctx[-n["index"] - 1]
        if t == "sort":
            lv = n["level"]
            if lv["tag"] == "zero": return "Prop"
            if lv == {"tag": "succ", "of": {"tag": "zero"}}: return "Type"
            return f"Sort({self.level(lv)})"
        if t == "const":
            name = plain_name(n["name"])
            if name in self.CONSTANTS: return self.CONSTANTS[name]
            shown = display_name(n["name"])
            self.unknown_constants.add(shown)
            return shown
        if t in {"nat", "str"}:
            return n["value"] if t == "nat" else json.dumps(n["value"], ensure_ascii=False)
        if t == "app":
            head, args = self.dag.app(i)
            hn = self.dag.nodes[head]
            name = plain_name(hn["name"]) if hn["tag"] == "const" else None
            arity = len(args)
            if name in self.INFIX and arity == self.INFIX[name][0]:
                return f"({r(args[-2])} {self.INFIX[name][1]} {r(args[-1])})"
            if name == "Not" and arity == 1: return f"¬{r(args[0])}"
            if name == "Ne" and arity == 3: return f"({r(args[1])} ≠ {r(args[2])})"
            if name == "OfNat.ofNat" and arity == 3 and self.dag.nodes[args[1]]["tag"] == "nat":
                return self.dag.nodes[args[1]]["value"]
            if name == "Nat.succ" and arity == 1: return f"({r(args[0])} + 1)"
            if name == "Exists" and arity == 2:
                p = self.dag.nodes[args[1]]
                if p["tag"] == "lam":
                    x = fresh_name(p["name"], ctx)
                    return f"∃ {x} : {r(args[0])}, {r(p['body'], ctx + [x])}"
                return f"∃ x : {r(args[0])}, {r(args[1])}(x)"
            if name == "Function.Injective" and arity == 3:
                return f"{r(args[-1])} is injective"
            if name == "Function.Surjective" and arity == 3:
                return f"{r(args[-1])} is surjective"
            if name == "Function.comp" and arity == 5:
                return f"({r(args[-2])} ∘ {r(args[-1])})"
            return f"{r(head)}({', '.join(r(x) for x in args)})"
        if t in {"lam", "forall"}:
            x = fresh_name(n["name"], ctx)
            dom = r(n["domain"]); body = r(n["body"], ctx + [x])
            if t == "lam": return f"({x} ↦ {body})"
            if not self.dag.uses_binder(n["body"]): return f"({dom} → {body})"
            return f"∀ {x} : {dom}, {body}"
        if t == "let":
            x = fresh_name(n["name"], ctx)
            return f"(let {x} : {r(n['type'])} = {r(n['value'])}; {r(n['body'], ctx + [x])})"
        if t == "proj": return f"component[{display_name(n['name'])}, {n['index']} ]({r(n['of'])})"
        raise InvalidExport("Cannot render unsupported constructor")


class English:
    def __init__(self, record: dict):
        self.argument = Argument(record)
        self.dag = self.argument.dag
        self.formula = Formula(self.dag)
        self.aid = self.argument.sha256[:20]

    def labels(self, ctx: list[int]) -> list[str]:
        labels: list[str] = []
        for binder in ctx:
            labels.append(fresh_name(self.dag.nodes[binder]["name"], labels))
        return labels

    def context(self, ctx: list[int]) -> list[dict[str, str]]:
        labels = self.labels(ctx)
        result = []
        for i, binder in enumerate(ctx):
            b = self.dag.nodes[binder]
            result.append({"name": labels[i], "type": self.formula.render(b.get("domain", b.get("type")), labels[:i])})
        return result

    def describe(self, i: int) -> Step:
        s = self.argument.steps[i]; ctx = self.argument.contexts[i]; labels = self.labels(ctx)
        n = self.dag.nodes[s["term"]]; t = n["tag"]
        con = self.formula.render(s["type"], labels)
        r = lambda e: self.formula.render(e, labels)
        rule = t; refs = []; fallback = s["truncated"]
        children = [self.describe(j) for j in s["children"]]
        if s["truncated"]:
            text = f"The recorded term establishes {con}; its internal derivation is not expanded."
        elif t == "lam":
            x = fresh_name(n["name"], labels)
            dom = r(n["domain"])
            rule = "assume" if s["domain_is_prop"] else "introduce"
            if s["domain_is_prop"]: text = f"Assume {dom}; denote this assumption by {x}."
            elif dom == "Prop": text = f"Let {x} be a proposition."
            elif dom == "Type": text = f"Let {x} be a type."
            elif dom.startswith("Sort("): text = f"Let {x} be a type in {dom}."
            else: text = f"Let {x} : {dom} be arbitrary."
        elif t == "let":
            x = fresh_name(n["name"], labels)
            rule = "have" if len(children) == 2 else "let"
            text = f"Establish {r(n['type'])} and call this fact {x}." if len(children) == 2 else f"Put {x} = {r(n['value'])}, of type {r(n['type'])}."
        elif t == "bvar":
            rule = "assumption" if s["is_proof"] else "given-object"
            text = f"This is the assumption {r(s['term'])}: {con}." if s["is_proof"] else f"Use the given object {r(s['term'])}."
        elif t == "app":
            head, args = self.dag.app(s["term"])
            hn = self.dag.nodes[head]
            name = plain_name(hn["name"]) if hn["tag"] == "const" else None
            if name: refs = [name]
            premises = [r(a["type"]) for a in s["arguments"] if a["is_proof"]]
            basis = "; ".join(premises)
            rule = "lemma-application"
            text = f"Apply {r(head)} to the recorded arguments to obtain {con}."
            if hn["tag"] == "bvar":
                rule = "hypothesis-application"
                pos = len(ctx) - hn["index"] - 1
                bn = self.dag.nodes[ctx[pos]]
                dom = bn.get("domain", bn.get("type"))
                dh, das = self.dag.app(dom); dn = self.dag.nodes[dh]
                dname = plain_name(dn["name"]) if dn["tag"] == "const" else None
                if dname == "Function.Injective" and len(das) == 3:
                    fn = self.formula.render(das[-1], labels[:pos])
                    text = f"Injectivity of {fn}, applied to {basis}, gives {con}."
                    rule = "injectivity"
                else:
                    text = f"Using {r(head)} and the established fact{'s' if len(premises) != 1 else ''} {basis}, conclude {con}." if premises else f"Specialize {r(head)} at the recorded objects to obtain {con}."
            templates = {
                ("And.intro", 4): ("conjunction", f"Combining the two established facts gives {con}."),
                ("And.left", 3): ("left-conjunct", f"The first conjunct of {basis} gives {con}."),
                ("And.right", 3): ("right-conjunct", f"The second conjunct of {basis} gives {con}."),
                ("Eq.refl", 2): ("reflexivity", f"By reflexivity, {con}."),
                ("Eq.symm", 4): ("symmetry", f"Reversing the supplied equality gives {con}."),
                ("Eq.trans", 6): ("transitivity", f"By transitivity of the established equalities, {con}."),
                ("Iff.intro", 4): ("equivalence", f"The two implications establish {con}."),
                ("False.elim", 2): ("contradiction", f"The contradiction implies {con}."),
                ("Or.inl", 3): ("left-alternative", f"The first alternative establishes {con}."),
                ("Or.inr", 3): ("right-alternative", f"The second alternative establishes {con}."),
                ("Or.elim", 6): ("cases", f"Separate the two alternatives. In either case, prove {con}."),
                ("Exists.elim", 5): ("existential-elimination", f"Use the existential premise, then prove {con} for its witness as follows."),
                ("Classical.byContradiction", 2): ("contradiction-proof", f"Suppose the desired conclusion fails; the following argument yields a contradiction, proving {con}."),
            }
            if (name, len(args)) in templates:
                rule, text = templates[(name, len(args))]
            if name == "Exists.intro" and len(args) == 4:
                rule = "witness"
                prop = r(s["arguments"][3]["type"])
                text = f"Take the witness {r(args[2])}. The supplied fact {prop} establishes {con}."
            if name == "Or.elim" and len(args) == 6:
                text = f"Use the disjunction {r(s['arguments'][3]['type'])}. In the {r(args[0])} case, use {r(args[4])}; in the {r(args[1])} case, use {r(args[5])}. In either case, conclude {con}."
            if rule == "lemma-application":
                # It is a faithful citation at lemma granularity, not a conceptual expansion.
                fallback = True
        elif t == "const":
            name = plain_name(n["name"])
            refs = [name] if name else []
            rule = "named-fact"
            text = f"The named result {r(s['term'])} gives {con}."
            if name == "True.intro": text = "The proposition True holds by its introduction rule."; rule = "truth"
            else: fallback = True
        elif t == "proj":
            rule = "projection"
            text = f"Take component {n['index']} of the recorded {display_name(n['name'])} object to obtain {con}."
            fallback = True
        else:
            text = f"Use the recorded expression to establish {con}."; fallback = True
        formula_gap = "[expression " in con or "[expression " in text
        return Step(f"{self.aid}:s{i}", rule, text, r(s["term"]), evidence="typed-export",
                    children=children, references=refs, conclusion=con, context=self.context(ctx),
                    term_id=f"e{s['term']} : e{s['type']}", fallback=fallback or formula_gap,
                    detail=f"Original proof path: {s['path']}. Claim: step_{i}. "
                           "Its closed term and type are included in the generated Lean judgement checks.")

    def prose_steps(self) -> list[Step]:
        """Flatten leading binders, then put small direct inferences in dependency order.

        Branching arguments retain nested scopes. Expansion only hides already-given
        assumption leaves; it never treats an unexpanded named lemma as an explanation.
        """
        root = self.describe(0)
        out = []
        while root.rule in {"introduce", "assume"} and len(root.children) == 1:
            child = root.children[0]
            root = replace(root, children=[], conclusion=None)
            out.append(root); root = child
        branch_rules = {"introduce", "assume", "have", "let", "cases", "existential-elimination", "contradiction-proof"}
        def flat(s: Step) -> list[Step]:
            if s.rule in branch_rules:
                return [s]
            result = []
            for child in s.children:
                if child.rule not in {"assumption", "given-object"}:
                    result.extend(flat(child))
            # Nontrivial premises already appear in dependency order. Link to
            # those steps instead of duplicating entire subtrees in the document.
            rendered = replace(s)
            rendered.supports = [child.id for child in s.children
                                 if child.rule not in {"assumption", "given-object"}]
            rendered.children = [child for child in s.children
                                 if child.rule in {"assumption", "given-object"}]
            result.append(rendered)
            return result
        out.extend(flat(root))
        return out

    def statement_parts(self) -> tuple[list[dict], int, list[str]]:
        """Move declared parameters out of the proof, preserving their scope.

        Only an exact matching raw forall/lambda prefix is split. Other proof
        shapes retain the full quantified statement instead of guessing.
        """
        typ = self.argument.typ; step_index = 0; parameters = []; labels = []
        while True:
            ty = self.dag.nodes[typ]; st = self.argument.steps[step_index]
            term = self.dag.nodes[st["term"]]
            if ty["tag"] != "forall" or term["tag"] != "lam" or st["truncated"]:break
            if not self.dag.equal(ty["domain"],term["domain"]):break
            label = fresh_name(term["name"],labels)
            dom = self.formula.render(term["domain"],labels)
            if st["domain_is_prop"]: text = f"Assume {dom}; denote this assumption by {label}."
            elif dom == "Prop": text = f"Let {label} be a proposition."
            elif dom == "Type": text = f"Let {label} be a type."
            elif dom.startswith("Sort("): text = f"Let {label} be a type in {dom}."
            else: text = f"Let {label} : {dom} be arbitrary."
            label = fresh_name(term["name"],labels)
            parameters.append({"names":label,"type":self.formula.render(term["domain"],labels),
                               "binder": "[" if term["binder"]=="instance" else "(",
                               "text":text,"source_step_id":f"{self.aid}:s{step_index}"})
            labels.append(label);typ = ty["body"];step_index=st["children"][0]
        return parameters, typ, labels

    def document(self, *, source: str = "", file: str = "typed-proof", receipt: dict | None = None) -> Document:
        a = self.argument
        steps = self.prose_steps()
        parameters, target, labels = self.statement_parts()
        steps = steps[len(parameters):]
        dependencies = sorted({r for s in walk_steps(steps) for r in s.references})
        d = Declaration(self.aid, a.name, "theorem", file, self.formula.render(target,labels), source,
                        Span(0, len(source), 1, source.count("\n") + 1), parameters=parameters, steps=steps,
                        evidence="typed-export", dependencies=dependencies, receipt=receipt,
                        axes={"discovery": "Lean-exported", "statement": "rendered-from-expression-DAG",
                              "proof": "path-bound-typed-judgements", "english_fidelity": "regenerable-not-formally-proved",
                              "argument_sha256": a.sha256, "printer": PRINTER_VERSION,
                              "fully_quantified_statement": self.formula.render(a.typ)},
                        warnings=["Named lemmas without an exposition template remain explicitly unexpanded.",
                                  "Kernel judgement checks do not constitute a formal proof of this English printer."])
        return Document(a.name, [{"path": file, "source": source, "sha256": digest(source)}] if source else [], [d],
                        provenance={"mode": "path-bound-typed-proof", "argument_sha256": a.sha256,
                                    "printer": PRINTER_VERSION, "pipeline_model_calls": 0,
                                    "lean_version": a.record["lean_version"], **a.coverage()},
                        generator="lean-proofreader/0.2.0")


def reading_binding(document: Document) -> dict:
    """Hash only generated mathematics, not source labels or receipt assertions."""
    def st(s: Step) -> dict:
        return {k: v for k, v in asdict(s).items() if k not in {"span", "evidence"}}
    return {"declarations": [{"name": d.name, "statement": d.statement,
                               "parameters": d.parameters, "context": d.context,
                               "steps": [st(s) for s in d.steps], "dependencies": d.dependencies}
                              for d in document.declarations], "printer": PRINTER_VERSION}


def check_reading(record: dict, document: Document) -> None:
    expected = English(record).document()
    require(reading_binding(expected) == reading_binding(document),
            "Reading text or proof structure differs from deterministic regeneration")


def prose_text(record: dict) -> str:
    doc = English(record).document()
    d = doc.declarations[0]
    return "\n\n".join([d.name] + [p["text"] for p in d.parameters] + ["Claim: " + d.statement, "Proof."] + [s.text for s in d.steps] + ["∎"]) + "\n"



# File: proofreader/kernel_io.py

"""Explicit, reproducible I/O for v2 typed arguments.

Reading and HTML export never execute Lean or make network requests. Native
execution requires trust_project; remote execution requires allow_remote.
Receipts record an observation, not a signature or a formal English guarantee.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json
import os
import re
import tempfile
import urllib.request
from typing import Any

from .kernel import Argument, InvalidExport, SCHEMA, replay_source, require
from .english import English, PRINTER_VERSION, prose_text
from .model import canonical_json, digest, Document
from .render import write_html
from .lean import run_bounded, driver_file

STANDARD_AXIOMS = frozenset({'propext', 'Classical.choice', 'Quot.sound'})
INCOMPLETE_AXIOMS = frozenset({'sorryAx', 'Lean.sorryAx'})
MAX_REQUEST_BYTES = 64_000_000
MAX_RESPONSE_BYTES = 128_000_000


def strict_json(text: str | bytes) -> Any:
    """Reject ambiguous duplicate object keys and non-finite numeric tokens."""
    def object_pairs(pairs):
        d = {}
        for k, v in pairs:
            if k in d: raise InvalidExport(f'Duplicate JSON key: {k}')
            d[k] = v
        return d
    def bad_constant(value):
        raise InvalidExport('Non-finite JSON number: ' + value)
    return json.loads(text, object_pairs_hook=object_pairs, parse_constant=bad_constant)


def axiom_status(record: dict, permitted: list[str] | None = None) -> dict:
    a = Argument(record)
    allowed = STANDARD_AXIOMS | frozenset(permitted or [])
    incomplete = sorted(set(a.record['axioms']) & INCOMPLETE_AXIOMS)
    extra = sorted(set(a.record['axioms']) - allowed)
    return {'axioms': a.record['axioms'], 'standard_axioms': sorted(STANDARD_AXIOMS),
            'explicitly_permitted': sorted(set(permitted or [])),
            'incomplete_axioms': incomplete, 'nonpermitted_axioms': extra,
            'acceptable': not incomplete and not extra}


def checked_source(record: dict, *, imports: list[str] | None = None,
                   context: str | None = None) -> str:
    """For source re-elaboration, preserve the original prefix exactly.

    `context` should be the exact input used at extraction, without export
    commands. A normal project should instead use pinned .olean imports.
    """
    require(not (context is not None and imports), "Choose source context or module imports, not both")
    driver = replay_source(record, imports=imports)
    if context is None: return driver
    marker = 'open Lean Elab Command'
    return context.rstrip() + '\n' + driver[driver.index(marker):]


def expected_markers(record: dict) -> tuple[str, ...]:
    a = Argument(record)
    return ('PROOFREADER_REPLAY_OK', 'PROOFREADER_PATHS_OK',
            f'PROOFREADER_JUDGEMENTS_OK:{a.sha256}:{len(a.claims)}')


def _has_marker(text: str, marker: str) -> bool:
    # Must be a complete emitted message line, not an error quoting source text.
    return any(line.strip() == marker or line.rstrip().endswith('info: ' + marker)
               for line in text.splitlines())


def judge_run(record: dict, source: str, *, okay: bool, stdout: str,
              errors: list[str], environment: str | None = None,
              source_preserved: bool = True, permitted_axioms: list[str] | None = None) -> dict:
    """Pure adjudicator used by both transports. No receipt can invoke execution."""
    a = Argument(record)
    policy = axiom_status(record, permitted_axioms)
    markers = expected_markers(record)
    missing = [m for m in markers if not _has_marker(stdout, m)]
    version_matches = environment is None or environment.removeprefix('lean-') == record['lean_version']
    passed = okay is True and not errors and not missing and version_matches and source_preserved and policy['acceptable']
    reasons = []
    if okay is not True: reasons.append('Lean execution did not succeed')
    if errors: reasons.append('Lean or service reported errors')
    if missing: reasons.append('Required completion markers are missing')
    if not version_matches: reasons.append('Exact Lean version mismatch')
    if not source_preserved: reasons.append('Service changed submitted source')
    if not policy['acceptable']: reasons.append('Axiom policy did not pass')
    return {'schema': 'proofreader.kernel-receipt/v2', 'status': 'passed' if passed else 'failed',
            'argument_sha256': a.sha256, 'checker_source_sha256': digest(source),
            'lean_version': record['lean_version'], 'environment': environment,
            'printer_version': PRINTER_VERSION, 'judgements_expected': len(a.claims),
            'completion_markers': {m: _has_marker(stdout, m) for m in markers},
            'path_linkage_checked_in_lean': passed, 'all_judgements_kernel_checked': passed,
            'english_formally_verified': False, 'receipt_authenticated': False,
            'axiom_policy': policy, 'source_preserved': source_preserved,
            'errors': errors, 'reasons': reasons,
            'trust_boundary': 'Requires trusted compiler, project, metaprograms, checker and recorded transport. Re-run before relying on an imported receipt.'}


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def write_bundle(record: dict, destination: Path, *, source: str = '', file: str = 'typed-proof',
                 receipt: dict | None = None, imports: list[str] | None = None,
                 context: str | None = None) -> dict:
    """Create a portable reader with its exact data, checks and prose binding."""
    from .english import reading_binding
    a = Argument(record)
    destination.mkdir(parents=True, exist_ok=True)
    if receipt is not None:
        require(receipt.get('argument_sha256') == a.sha256, 'Receipt belongs to a different argument')
    d = English(record).document(source=source, file=file, receipt=receipt)
    d.declarations[0].axes['axiom_status'] = axiom_status(record)
    # Axiom status is metadata, not prose; it is excluded from English binding.
    d.provenance['corpus_complete'] = False
    _write_json(destination / 'argument.json', record)
    (destination / 'reading.json').write_text(d.to_json(), encoding='utf-8')
    (destination / 'proof.txt').write_text(prose_text(record), encoding='utf-8')
    (destination / 'Check.lean').write_text(checked_source(record, imports=imports, context=context), encoding='utf-8')
    write_html(d, destination / 'reader.html')
    result = {**a.coverage(), 'argument_sha256': a.sha256,
              'reading_binding': reading_binding(d), 'axiom_status': axiom_status(record),
              'checker_context_supplied': bool(imports) or context is not None,
              'checker_setup_note': ('An input context is supplied; execution has not been implied.'
                 if imports or context is not None else
                 'Check.lean requires the original theorem environment. Recreate the bundle with --context or --module before replay.'),
              'native_or_remote_replay': 'not-run' if receipt is None else 'attached-observation-' + receipt.get('status', 'unknown'),
              'whole_corpus_coverage': False, 'readability_human_evaluated': False}
    _write_json(destination / 'coverage.json', result)
    if receipt is not None: _write_json(destination / 'receipt.json', receipt)
    return result


def verify_native(record: dict, project: Path, output: Path, *, module: str | None = None,
                  context: str | None = None, trust_project: bool = False,
                  timeout: float = 180, permitted_axioms: list[str] | None = None) -> dict:
    if not trust_project:
        raise PermissionError('Lean elaboration can execute arbitrary code. Pass --trust-project only for a trusted or isolated project.')
    require((module is None) != (context is None), 'Supply exactly one imported module or exact source context')
    project = project.resolve()
    require(project.is_dir(), 'Project directory does not exist')
    output.mkdir(parents=True, exist_ok=True)
    source = checked_source(record, imports=[module] if module else [], context=context)
    (output / 'Check.lean').write_text(source, encoding='utf-8')
    with driver_file(project, source) as driver:
        run = run_bounded(['lake', 'env', 'lean', str(driver)], project, timeout=timeout)
    _write_json(output / 'run.json', asdict(run))
    (output / 'stdout.txt').write_text(run.stdout, encoding='utf-8')
    (output / 'stderr.txt').write_text(run.stderr, encoding='utf-8')
    # A successful exit AND all check markers are needed. The driver itself checks version.
    errors = [] if run.status == 'passed' and run.exit_code == 0 else [run.reason or run.stderr or 'Lean failed']
    receipt = judge_run(record, source, okay=run.status == 'passed' and run.exit_code == 0,
                        stdout=run.stdout, errors=errors, permitted_axioms=permitted_axioms)
    receipt['backend'] = 'local-lake'
    _write_json(output / 'receipt.json', receipt)
    return receipt


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('Remote verification redirects are not followed')


def axle_request(source: str, version: str, *, allow_remote: bool = False,
                 timeout: float = 180) -> dict:
    if not allow_remote:
        raise PermissionError('This sends the complete Lean source to AXLE. Pass --allow-remote to consent.')
    require(0 < timeout <= 900, 'Timeout must be between 0 and 900 seconds')
    require(bool(re.fullmatch(r'4\.\d+\.\d+', version)), 'Expected an exact stable Lean version')
    request = {'content': source, 'environment': 'lean-' + version,
               'ignore_imports': False, 'theorems_only': False, 'timeout_seconds': timeout}
    body = canonical_json(request).encode('utf-8')
    require(len(body) <= MAX_REQUEST_BYTES, 'Remote source exceeds size budget')
    headers = {'Content-Type': 'application/json; charset=utf-8', 'User-Agent': 'lean-proofreader/0.2.0'}
    if token := os.environ.get('AXLE_API_KEY'): headers['Authorization'] = 'Bearer ' + token
    req = urllib.request.Request('https://axle.axiommath.ai/api/v1/check', body, headers, method='POST')
    with urllib.request.build_opener(NoRedirect).open(req, timeout=timeout+60) as response:
        data = response.read(MAX_RESPONSE_BYTES + 1)
    require(len(data) <= MAX_RESPONSE_BYTES, 'Remote response exceeds size budget')
    result = strict_json(data)
    require(isinstance(result, dict), 'Invalid AXLE response')
    return result


def judge_axle(record: dict, source: str, result: dict, *, permitted_axioms: list[str] | None = None) -> dict:
    require(isinstance(result, dict), 'Malformed AXLE response')
    lm, tm = result.get('lean_messages', {}), result.get('tool_messages', {})
    require(isinstance(lm, dict) and isinstance(tm, dict), 'Malformed AXLE message collection')
    for collection in (lm, tm):
        for key in ('errors','infos','warnings'):
            value=collection.get(key,[])
            require(isinstance(value,list) and all(isinstance(x,str) for x in value), 'Malformed AXLE message list')
    require(isinstance(result.get('info',{}),dict),'Malformed AXLE execution metadata')
    require(isinstance(result.get('failed_declarations',[]),list),'Malformed failed-declaration inventory')
    errors = list(lm.get('errors', [])) + list(tm.get('errors', []))
    if result.get('failed_declarations'): errors.append('AXLE reported failed declarations: ' + str(result['failed_declarations']))
    if not isinstance(result.get('content'), str): errors.append('AXLE did not return processed source')
    info = result.get('info', {})
    receipt = judge_run(record, source, okay=result.get('okay') is True,
                        stdout='\n'.join(lm.get('infos', [])), errors=errors,
                        environment=info.get('environment', 'unknown'),
                        source_preserved=isinstance(result.get('content'),str) and result['content'].strip() == source.strip(),
                        permitted_axioms=permitted_axioms)
    receipt.update({'backend': 'AXLE', 'request_id': info.get('request_id'),
                    'executor_commit_sha': info.get('_executor_commit_sha'),
                    'service_warnings': list(lm.get('warnings', [])) + list(tm.get('warnings', []))})
    return receipt


def verify_remote(record: dict, output: Path, *, context: str, allow_remote: bool = False,
                  timeout: float = 180, permitted_axioms: list[str] | None = None) -> dict:
    # Consent is checked before writing a request or making any call.
    if not allow_remote: raise PermissionError('Remote verification requires --allow-remote; source is sent to AXLE.')
    a = Argument(record)
    source = checked_source(record, context=context)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'Check.lean').write_text(source, encoding='utf-8')
    result = axle_request(source, a.record['lean_version'], allow_remote=True, timeout=timeout)
    _write_json(output / 'axle-response.json', result)
    receipt = judge_axle(record, source, result, permitted_axioms=permitted_axioms)
    _write_json(output / 'receipt.json', receipt)
    return receipt



# File: docs/NARRATIVE.md

# Source-bound mathematical reading

Version 0.3 adds a second typed reading route. The exact constructor-DAG route
remains in `kernel.py`; the source-bound route does not pretend to be that route.

## Data path

1. A trusted Lean source or imported module is elaborated in an explicit version.
2. `lean/Narrative.lean` obtains the original theorem value and transitive axioms.
   It walks mathematical structure rather than expanding every computation.
3. Each selected term is closed over its actual local context and submitted as a
   fresh theorem declaration to the Lean kernel, with kernel checking enabled.
4. A separate raw-expression traversal follows each recorded path in the original
   proof. The selected expression must match the original subterm after erasing
   nonsemantic metadata. This step does not consult the reading prose.
5. The exporter emits a small snapshot of goals, contexts, proof paths, argument
   relationships, object expressions and a role for each selected frame.
6. `narrative.py` creates the statement, cases, witnesses, intermediate claims,
   calculations and dependencies. It accounts for every exported frame, including
   those absorbed into a larger display step. Unknown shapes remain unexpanded.
7. `polynomial.py` independently proves supported arithmetic passages by exact
   coefficient comparison over integer polynomials, using only recorded scalar
   equalities in the corresponding local context.

The complete original proof stays in the supplied Lean source and dependencies.
A 1,500-step raw explanation is not made readable by truncating the proof itself.
The snapshot is a selected presentation of an intact source proof, not a standalone
kernel certificate or a complete expansion of every imported lemma.

## What is trusted

The Lean compiler, project/imports, exporter metaprogram, pretty-printer,
mathematical dictionary, renderer, and recorded transport remain trusted.
Snapshots contain **pretty-printed formula strings**, not a formally interpreted
English language. A malicious custom pretty-printer could misrepresent formulas.
The source must therefore be trusted or independently audited. No English
meaning-preservation theorem or human readability study is claimed.

Fresh re-extraction checks the supplied snapshot against the source. A local
regeneration check protects against divergence between the supplied snapshot and
the displayed mathematical argument. Neither operation authenticates an imported
receipt. Reading a file performs no Lean execution and makes no network call.

## Arithmetic certificates

For a goal `L = R`, the checker verifies the integer-polynomial identity

    L - R = M_1 (A_1 - B_1) + ... + M_k (A_k - B_k).

Every `A_i = B_i` must be an available equality in the recorded local context;
variables must belong to one recognized commutative ring. This is not rational
cancellation: `2*x=0` does not justify `x=0` in an arbitrary ring. A bounded search
may use rational linear algebra internally, but certificates with noninteger
multipliers are rejected. Verification uses only exact polynomial arithmetic,
not the certificate search routine. This checker is tested, not formally verified.

Conditional statements are rejected as a whole before their conjunctions are
considered. In particular, `P → x=0 ∧ y=0` never yields unconditional `y=0`.
Shadowed assumptions cannot be recovered by their old printed name. Unsupported
notation or resource limits produce a visible gap, not an invented identity.

## Commands

Offline:

```sh
python -m proofreader narrative-demo -o reader.html
python -m proofreader narrative-read proofreader/data/bezout-snapshot.json \
  --source proofreader/data/bezout-original.lean \
  --receipt proofreader/data/bezout-receipt.json -o output/bezout
python -m proofreader check-narrative proofreader/data/bezout-snapshot.json \
  output/bezout/reading.json --certificates output/bezout/polynomial-certificates.json
```

Actual source replay through AXLE (explicitly sends the complete source):

```sh
python -m proofreader verify-narrative proofreader/data/bezout-snapshot.json \
  --driver proofreader/data/bezout-reproduce.lean \
  --backend axle --allow-remote -o output/recheck
```

The supplied driver is the exact successful experimental input; the CLI appends
an exact-version guard without changing any earlier source. A self-contained new
context can instead be passed to `extract-narrative`:

```sh
python -m proofreader extract-narrative YourNamespace.theorem \
  --context YourProof.lean --project YourTrustedProject --trust-project \
  --lean-version 4.34.1 -o output/new-proof
```

Native elaboration is not a sandbox and can execute arbitrary code. Remote
availability and installed dependency versions are service properties. An error,
timeout, changed import header, missing completion record, wrong theorem/version,
disallowed axiom or unequal re-extraction leaves a failed receipt. A previous
successful reading is not left at the canonical output path after a failed run.

## Scope of the current corpus integration

This new route selects one explicitly named theorem per command. The existing
whole-corpus kernel engine still enumerates and shards theorem constants; it has
not been replaced with an untested narrative batch runner. Full-project narrative
coverage, proof-valued definitions, and unformalized manuscripts remain separate
work. Selected cases, conjunctions and witnesses work; arbitrary recursors and
induction do not yet have complete mathematical verbalizations.



# File: proofreader/narrative.py

"""Deterministic mathematical prose from source-bound Lean judgement snapshots.

This route is separate from the exact constructor-DAG route. The snapshot is
small because the complete proof remains in the supplied Lean source. Its
formula strings come from Lean's pretty-printer. Re-extraction and comparison
bind the snapshot to that source; reading alone never executes or authenticates
Lean. Our English templates and pretty-printer are not formally proved correct.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
import copy
from pathlib import Path
import re
from typing import Any

from .model import Declaration, Document, Span, Step, canonical_json, digest, walk_steps
from .kernel import InvalidExport, require
from .kernel_io import strict_json, STANDARD_AXIOMS
from .polynomial import certify, verify as verify_polynomial, certificate_text

SCHEMA = 'proofreader.narrative/v1'
PRINTER_VERSION = 'source-math-en/0.3.0'
ROLES = {'introduce','assume','have','define','witness','choose','cases','combine','chain',
         'reflexivity','cancel','identity','given','named','application','ring','rewrite','unexpanded'}
_HEAD_ROLES = {'Exists.intro':'witness','Exists.casesOn':'choose','Exists.elim':'choose',
               'And.intro':'combine','Trans.trans':'chain','Eq.trans':'chain',
               'mul_left_cancel₀':'cancel','id':'identity','Eq.refl':'reflexivity',
               'dite':'cases','ite':'cases','Decidable.byCases':'cases','Classical.byCases':'cases',
               'Or.elim':'cases','Or.casesOn':'cases'}
_REWRITES = {'Eq.mpr','Eq.mp','of_eq_true','congrArg','congr','congrFun',"congrFun'"}
_LEMMAS = {
    'EuclideanDomain.gcd_eq_zero_iff': 'A gcd is zero exactly when both entries are zero.',
    'EuclideanDomain.gcd_dvd_left': 'The gcd divides its first entry.',
    'EuclideanDomain.gcd_dvd_right': 'The gcd divides its second entry.',
    'EuclideanDomain.gcd_eq_gcd_ab': 'Use the Bézout identity supplied by the extended Euclidean algorithm.',
    'EuclideanDomain.instIsDomain': 'A Euclidean domain is an integral domain.',
    'IsDomain.toIsCancelMulZero': 'In an integral domain, multiplication by a nonzero element is cancellative.',
    'IsCancelMulZero.toIsLeftCancelMulZero': 'Use left cancellation away from zero.',
    'mul_one': 'Multiplication by one leaves the element unchanged.',
    'Eq.symm': 'Reverse the supplied equality.',
    'Iff.mp': 'Apply the forward direction of the stated equivalence to the supplied hypothesis.',
    'And.left': 'Take the first conjunct.',
    'And.right': 'Take the second conjunct.',
}
_BASE = {'id','path','statement','role','head','context','children','premises','objects','budget_cut'}
_EXTRAS = {'binder','domain','value'}
_TOP = {'schema','theorem','lean_version','axioms','statement','frames','judgements_checked','formula_backend'}


def _string(s: Any, limit: int = 20000) -> None:
    require(isinstance(s,str) and len(s) <= limit and '\x00' not in s, 'Invalid narrative string')


class Snapshot:
    def __init__(self, record: dict):
        require(isinstance(record,dict) and set(record) == _TOP, 'Unknown or missing snapshot fields')
        self.record = copy.deepcopy(record)
        r = self.record
        require(r['schema'] == SCHEMA, 'Unsupported narrative schema')
        _string(r['theorem']); _string(r['statement'],100000)
        require(isinstance(r['lean_version'],str) and bool(re.fullmatch(r'4\.\d+\.\d+',r['lean_version'])), 'Invalid exact Lean version')
        require(r['formula_backend'] == 'Lean pretty-printer', 'Unknown formula backend')
        ax = r['axioms']
        require(isinstance(ax,list) and all(isinstance(x,str) for x in ax) and len(set(ax)) == len(ax), 'Invalid axiom list')
        require(set(ax) <= STANDARD_AXIOMS, 'Snapshot has nonstandard or incomplete axioms')
        self.frames = r['frames']
        require(isinstance(self.frames,list) and 0 < len(self.frames) <= 1000, 'Narrative frame budget')
        require(type(r['judgements_checked']) is int and r['judgements_checked'] == len(self.frames), 'Judgement inventory mismatch')
        parents: dict[int,int] = {}
        paths = set()
        for i, f in enumerate(self.frames):
            require(isinstance(f,dict) and _BASE <= set(f) and set(f) <= _BASE | _EXTRAS, 'Invalid frame fields')
            require(type(f['id']) is int and f['id'] == i, 'Noncanonical frame id')
            path = f['path']
            require(isinstance(path,list) and len(path) <= 4096 and all(type(x) is int and x in (0,1,2) for x in path), 'Invalid proof path')
            require(tuple(path) not in paths, 'Repeated source path')
            paths.add(tuple(path))
            require(isinstance(f['role'],str) and f['role'] in ROLES and type(f['budget_cut']) is bool, 'Invalid frame role or budget flag')
            for k in ('statement','head'):
                _string(f[k])
            role,head = f['role'],f['head']
            if head.startswith('Mathlib.Tactic.Ring.'):
                require(role == 'ring', 'Arithmetic role mismatch')
            elif head in _REWRITES:
                require(role == 'rewrite', 'Rewrite role mismatch')
            elif head in _HEAD_ROLES and not f['budget_cut']:
                require(role == _HEAD_ROLES[head], 'Logical rule mismatch')
            require(isinstance(f['context'],list) and len(f['context']) <= 256, 'Context budget')
            for c in f['context']:
                require(isinstance(c,dict) and set(c) == {'name','type'}, 'Invalid context entry')
                _string(c['name']); _string(c['type'])
            require(isinstance(f['objects'],list) and len(f['objects']) <= 256, 'Object argument budget')
            for x in f['objects']:
                _string(x)
            ch = f['children']
            require(isinstance(ch,list) and all(type(j) is int for j in ch) and len(set(ch)) == len(ch), 'Invalid child list')
            for j in ch:
                require(type(j) is int and i < j < len(self.frames) and j not in parents, 'Invalid narrative tree')
                parents[j] = i
            require(isinstance(f['premises'],list) and len(f['premises']) <= 256, 'Invalid premises')
            arguments = []
            for p in f['premises']:
                require(isinstance(p,dict) and set(p) == {'argument','statement','frame'}, 'Invalid premise fields')
                require(type(p['argument']) is int and 0 <= p['argument'] <= 256 and type(p['frame']) is int and p['frame'] in ch, 'Invalid premise reference')
                arguments.append(p['argument']); _string(p['statement'])
            require(arguments == sorted(set(arguments)), 'Repeated or unordered argument indices')
            if role in {'introduce','assume','define','have'}:
                require({'binder','domain'} <= set(f), 'Missing binder metadata')
                require(len(ch) == (2 if role == 'have' else 1) and not f['premises'], 'Invalid binder children')
            if role == 'define':
                require('value' in f, 'Missing definition value')
            if role == 'given':
                require('binder' in f and not ch, 'Invalid hypothesis frame')
            if role in {'ring','rewrite'}:
                require(not ch and not f['premises'], 'A frontier cannot contain unaccounted children')
            for k in _EXTRAS & set(f):
                _string(f[k])
        require(self.frames[0]['path'] == [] and self.frames[0]['context'] == [], 'Missing root frame')
        require(self.frames[0]['statement'] == r['statement'], 'Root statement mismatch')
        require(set(parents) == set(range(1,len(self.frames))), 'Unreachable frames')
        self.parents = parents
        depths = {0:0}
        for i in range(1,len(self.frames)):
            depths[i] = depths[parents[i]] + 1
            require(depths[i] <= 160, 'Narrative tree depth limit')
            f, parent = self.frames[i], self.frames[parents[i]]
            prefix = parent['path']
            require(len(f['path']) > len(prefix) and f['path'][:len(prefix)] == prefix, 'Child escaped source scope')
            pc,fc = parent['context'],f['context']
            if parent['role'] in {'introduce','assume','have','define'}:
                is_body = i == parent['children'][-1]
                suffix = [1] if parent['role'] in {'introduce','assume'} else [2 if is_body else 1]
                require(f['path'] == prefix+suffix, 'Binder/body path mismatch')
                expected = pc + ([{'name':parent['binder'],'type':parent['domain']}] if is_body else [])
                require(fc == expected, 'Binder context mismatch')
            else:
                require(fc == pc, 'Application changed local context')
        for f in self.frames:
            for p in f['premises']:
                require(p['statement'] == self.frames[p['frame']]['statement'], 'Premise conclusion mismatch')
        self.sha256 = digest(canonical_json(r))

    @classmethod
    def read(cls, path: Path | str) -> 'Snapshot':
        data = Path(path).read_bytes()
        require(len(data) <= 16_000_000, 'Narrative input too large')
        return cls(strict_json(data))

    def coverage(self) -> dict:
        return {'frames':len(self.frames), 'roles':dict(sorted(Counter(f['role'] for f in self.frames).items())),
                'budget_cuts':sum(f['budget_cut'] for f in self.frames),
                'recorded_kernel_judgements':self.record['judgements_checked'],
                'receipt_authenticated':False,'english_formally_verified':False,
                'source_replayed_by_loading':False}


def math_text(s: str) -> str:
    """A small notation dictionary, not a free-form algebra simplifier.

    The exact Lean strings remain in every source-bound frame. Only recognized
    fully qualified gcd symbols with atomic arguments receive ordinary notation.
    """
    atom = r'([^\W\d]\w*|[0-9]+)'
    for constant, shown in [('gcdA','gcdA'),('gcdB','gcdB'),('gcd','gcd')]:
        s = re.sub(r'\bEuclideanDomain\.'+constant+r'\s+'+atom+r'\s+'+atom+r'(?![\w.])',
                   lambda m: f'{shown}({m[1]}, {m[2]})',s,flags=re.UNICODE)
    for symbol, explanation in [('IsDomain', 'an integral domain'),
                                 ('IsCancelMulZero', 'a ring with cancellation away from zero'),
                                 ('IsLeftCancelMulZero', 'a ring with left cancellation away from zero')]:
        m = re.fullmatch(symbol+r' ([^\W\d]\w*)', s, flags=re.UNICODE)
        if m:
            return m[1]+' is '+explanation
    s = s.replace(' * ',' · ').replace(' - ',' − ')
    m = re.fullmatch(r'¬([^\W\d]\w*) = 0',s.strip(),re.UNICODE)
    if m:
        return m[1]+' ≠ 0'
    return s


def _name(s: str) -> str:
    # Internal binder labels are not shown as mathematical objects.
    return s.split('._@.',1)[0]


class Narrative:
    def __init__(self, record: dict):
        self.snapshot = Snapshot(record)
        self.frames = self.snapshot.frames
        self.prefix = self.snapshot.sha256[:16]
        self.owners: dict[int,str] = {}
        self.certificates: dict[int,dict] = {}
        for f in self.frames:
            if f['role'] in {'ring','rewrite'}:
                c = certify(f)
                if c is not None:
                    verify_polynomial(f,c)
                    self.certificates[f['id']] = c
        self.heads: set[str] = set()

    def sid(self, i: int) -> str:
        return 'n'+self.prefix+':'+str(i)

    def claim(self, step: Step, ids: list[int]) -> Step:
        for i in ids:
            require(i not in self.owners, 'A snapshot frame was displayed twice')
            self.owners[i] = step.id
        step.term_id = ','.join('f'+str(i) for i in ids)
        paths = ['f'+str(i)+'='+(''.join(map(str,self.frames[i]['path'])) or 'root') for i in ids]
        step.detail += '\nOriginal proof paths: '+ '; '.join(paths)
        return step

    def step(self, i: int, text: str, *, rule: str | None = None,
             children: list[Step] | None = None, conclusion: str | None = None,
             fallback: bool = False, covered: list[int] | None = None, detail: str = '') -> Step:
        f = self.frames[i]
        if f['head']:
            self.heads.add(f['head'])
        s = Step(self.sid(i),rule or f['role'],text,evidence='source-bound-snapshot',
                 conclusion=conclusion,children=children or [],context=f['context'],
                 source=f['statement'],references=[f['head']] if f['head'] else [],
                 fallback=fallback or f['budget_cut'],detail=detail)
        return self.claim(s,covered or [i])

    def flat_chain(self, i: int) -> tuple[list[int],list[int]]:
        f = self.frames[i]
        if f['role'] != 'chain' or len(f['children']) != 2:
            return [i],[]
        left, li = self.flat_chain(f['children'][0]); right, ri = self.flat_chain(f['children'][1])
        return left+right,[i]+li+ri

    def flat_conjunction(self, i: int) -> tuple[list[int],list[int]]:
        f = self.frames[i]
        if f['role'] != 'combine' or len(f['children']) != 2:
            return [i],[]
        a,ai = self.flat_conjunction(f['children'][0]);b,bi = self.flat_conjunction(f['children'][1])
        return a+b,[i]+ai+bi

    def sequence(self, i: int) -> list[Step]:
        f = self.frames[i]; ch=f['children']; role=f['role']; con=math_text(f['statement'])
        if role in {'define','have'}:
            name=_name(f['binder']); domain=math_text(f['domain'])
            if role=='define':
                value=math_text(f['value'])
                note = (' This is the first Bézout coefficient.' if f['value'].startswith('EuclideanDomain.gcdA ') else
                        ' This is the second Bézout coefficient.' if f['value'].startswith('EuclideanDomain.gcdB ') else '')
                s=self.step(i,f'Set {name} = {value}.'+note,conclusion=None)
            else:
                s=self.step(i,f'Establish {domain}; call this fact {name}.',children=self.sequence(ch[0]))
            return [s]+self.sequence(ch[-1])
        if role=='cases' and len(ch)==2 and all(self.frames[j]['role']=='assume' for j in ch):
            branches=[]
            for j in ch:
                b=self.frames[j]
                if b['role']=='assume':
                    branches.append(self.step(j,'Case '+math_text(b['domain'])+'.',rule='case',children=self.sequence(b['children'][0])))
                else:
                    branches.extend(self.sequence(j))
            return [self.step(i,'Consider the following cases.',children=branches)]
        if role=='choose' and len(ch)==2:
            intro=self.frames[ch[1]]
            assumption=self.frames[intro['children'][0]] if intro['role']=='introduce' and intro['children'] else {}
            if assumption.get('role')=='assume':
                fact=math_text(self.frames[ch[0]]['statement'])
                name=_name(intro['binder']);typ=math_text(intro['domain']); prop=math_text(assumption['domain'])
                s=self.step(i,f'Since {fact}, choose {name} ∈ {typ} with {prop}.',
                            children=self.sequence(ch[0]),covered=[i,intro['id'],assumption['id']])
                return [s]+self.sequence(assumption['children'][0])
        if role=='identity' and len(ch)==2 and self.frames[ch[0]]['role']=='assume':
            binder=self.frames[ch[0]]
            s=self.step(i,'Use the same hypothesis in the form '+math_text(binder['domain'])+'.',
                        rule='equivalent-assumption',children=self.sequence(ch[1]),covered=[i,binder['id']])
            return [s]+self.sequence(binder['children'][0])
        if role=='witness':
            ids=[]; names=[]; values=[]; j=i
            while self.frames[j]['role']=='witness' and len(self.frames[j]['children'])==1:
                b=self.frames[j]
                if len(b['objects'])!=3:
                    break
                match=re.match(r'^∃\s+([^\s,:]+)',b['statement'])
                if match is None:
                    break
                ids.append(j);names.append(match[1]);values.append(math_text(b['objects'][-1]));j=b['children'][0]
            if ids:
                text='Take '+(', '.join(names) if len(names)==1 else '('+', '.join(names)+')')+' = '+(values[0] if len(values)==1 else '('+', '.join(values)+')')+'.'
                s=self.step(i,text,covered=ids)
                return [s]+self.sequence(j)
        if role=='combine' and len(ch)==2:
            leaves,parents=self.flat_conjunction(i)
            return [self.step(i,'Verify the '+str(len(leaves))+' required conclusions.',rule='verify-conclusions',
                              covered=parents,children=[s for j in leaves for s in self.sequence(j)])]
        if role=='chain' and len(ch)==2:
            leaves,parents=self.flat_chain(i)
            return [self.step(i,'The following calculation gives '+con+'.',rule='calculation',covered=parents,
                              children=[s for j in leaves for s in self.sequence(j)])]
        if i in self.certificates:
            c=self.certificates[i]
            assumptions=c['assumptions']
            if assumptions:
                basis=' and '.join(math_text(a['statement']) for a in assumptions)
                text='Using '+basis+', expand and collect terms.'
            else:
                text='Expand and collect terms.'
            return [self.step(i,text,rule='polynomial-identity',conclusion=con,
                              detail='Independent integer-polynomial certificate: '+certificate_text(c)+
                              '\nThis check is under the recorded local assumptions; it does not authenticate their Lean provenance.')]
        if role=='cancel':
            text='Cancel the nonzero common factor'+(' '+math_text(f['objects'][-3]) if len(f['objects'])>=3 else '')+' to obtain '+con+'.'
        elif role=='given':
            text='Use the hypothesis '+_name(f['binder'])+': '+con+'.'
        elif role=='assume':
            text='Assume '+math_text(f['domain'])+'.'
        elif role=='introduce':
            text='Let '+_name(f['binder'])+' ∈ '+math_text(f['domain'])+' be arbitrary.'
        elif role=='reflexivity':
            text='By reflexivity, '+con+'.'
        elif f['head'] in _LEMMAS:
            text=_LEMMAS[f['head']]
        else:
            text='Apply '+(f['head'] or 'the recorded term')+' to the supplied arguments.'
        fallback=role in {'ring','rewrite','unexpanded','cases','choose','identity','combine','chain','witness'} or (role in {'application','named'} and f['head'] not in _LEMMAS)
        child_steps=[s for j in ch for s in self.sequence(j)]
        s=self.step(i,text,children=child_steps,
                    conclusion=None if con in text or role in {'assume','introduce'} else con,fallback=fallback)
        if role in {'assume','introduce'}:
            s.children=[]
            return [s]+child_steps
        return [s]

    def document(self, *, source: str = '', file: str = 'Original.lean', receipt: dict | None = None, title: str | None = None, provenance_note: str | None = None) -> Document:
        self.owners={};self.heads=set();s=self.snapshot
        require(receipt is None or receipt.get('snapshot_sha256') == s.sha256, 'Receipt belongs to another snapshot')
        params=[];i=0;prefix=[]
        while self.frames[i]['role'] in {'introduce','assume'}:
            f=self.frames[i];prefix.append(i);name=_name(f['binder']);domain=math_text(f['domain'])
            if f['role']=='assume':
                text='Assume '+domain+'.'
                params.append({'text':text,'names':name,'type':domain,'binder':'('})
            else:
                m=re.fullmatch(r'EuclideanDomain (\w+)',domain)
                if m:
                    prior=next((p for p in params if p['names']==m[1] and p['type'].startswith('Type')),None)
                    if prior:
                        prior['text']='Let '+m[1]+' be a Euclidean domain.'
                    else:
                        params.append({'text':'Assume '+domain+'.','names':name,'type':domain,'binder':'['})
                elif domain == 'Prop':
                    params.append({'text':'Let '+name+' be a proposition.','names':name,'type':domain,'binder':'('})
                elif domain.startswith('Type') or domain.startswith('Sort'):
                    params.append({'text':'Let '+name+' be a type.','names':name,'type':domain,'binder':'('})
                elif params and params[-1]['type']==domain and params[-1]['binder']=='(' and params[-1]['text'].startswith('Let ') and ('elements of' in params[-1]['text'] or 'an element of' in params[-1]['text']):
                    prior=params[-1];prior['names']+=', '+name;prior['text']='Let '+prior['names']+' be elements of '+domain+'.'
                else:
                    params.append({'text':'Let '+name+' be an element of '+domain+'.','names':name,'type':domain,'binder':'('})
            i=f['children'][0]
        for j in prefix:
            self.owners[j]='statement'
        steps=self.sequence(i)
        require(set(self.owners)==set(range(len(self.frames))), 'Display omitted an exported frame')
        warnings=['Formula strings use Lean’s pretty-printer. The English renderer is deterministic, not formally verified.',
                  'Reading and certificate replay do not authenticate a Lean snapshot. Re-extract from trusted source before relying on imported evidence.']
        if provenance_note:
            warnings.append(provenance_note)
        dec=Declaration('narrative:'+self.prefix,s.record['theorem'],'theorem',file,math_text(self.frames[i]['statement']),source,
                        Span(0,len(source),1,max(1,len(source.splitlines()))),parameters=params,steps=steps,
                        warnings=warnings,evidence='source-bound-snapshot',dependencies=sorted(self.heads),receipt=receipt,
                        axes={'discovery':'named-Lean-theorem','statement':'Lean-derived formula snapshot',
                              'proof':'source-bound-kernel-snapshot','english_fidelity':'not-certified',
                              'snapshot_sha256':s.sha256,'lean_version':s.record['lean_version'],
                              'axiom_status':{'acceptable':True,'axioms':s.record['axioms']},
                              'printer_version':PRINTER_VERSION,'frame_owners':{str(k):v for k,v in sorted(self.owners.items())},
                              'polynomial_certificates':len(self.certificates)})
        doc=Document(title or ('Lean ProofReader · '+s.record['theorem'].split('.')[-1].replace('_',' ')),
                     [{'path':file,'sha256':digest(source),'source':source}], [dec],
                     provenance={'snapshot_sha256':s.sha256,'scope':'one selected theorem',
                                 'source_replayed_by_rendering':False,'pipeline_model_calls':0,
                                 'receipt_authenticated':False,'whole_corpus_coverage':False,
                                 'english_formally_verified':False,'formula_backend':s.record['formula_backend'],
                                 'snapshot_coverage':s.coverage(),'independent_polynomial_certificates':len(self.certificates)})
        return doc


def reading_binding(document: Document) -> str:
    require(len(document.declarations)==1, 'Expected one narrative declaration')
    d=asdict(document.declarations[0])
    for key in ('receipt','warnings','file','span'):
        d.pop(key,None)
    return digest(canonical_json(d))


def check_reading(record: dict, document: Document) -> None:
    require(len(document.declarations)==1, 'Expected one reading')
    d=document.declarations[0]
    expected=Narrative(record).document(source=d.source,file=d.file)
    require(reading_binding(expected)==reading_binding(document), 'Reading differs from deterministic regeneration')


def prose(document: Document) -> str:
    d=document.declarations[0]
    out=[document.title,'',*(p['text'] for p in d.parameters),'Then '+d.statement+'.','','Proof.']
    def emit(steps,depth=0):
        for s in steps:
            out.append('  '*depth+s.text)
            if s.conclusion:
                out.append('  '*(depth+1)+s.conclusion)
            emit(s.children,depth+1)
    emit(d.steps)
    return '\n'.join(out)+'\n'



# File: proofreader/polynomial.py

"""Small exact, independently replayable commutative-ring certificates.

No CAS, numerical tolerances or network calls are used. This is deliberately a
restricted parser: ASCII/Unicode identifiers from an explicitly supplied scalar
context, integers, +, -, *, parentheses and small natural powers. A certificate
asserts an *integer polynomial identity* G = sum(M_i A_i), not division in a field.
The surrounding Lean snapshot must independently establish that all variables
belong to the same commutative ring and that A_i=0 are available assumptions.
"""
from __future__ import annotations
from fractions import Fraction
from itertools import combinations, combinations_with_replacement
import re
from typing import Any

Monomial = tuple[tuple[str, int], ...]
Poly = dict[Monomial, Fraction]
MAX_TERMS = 512
MAX_DEGREE = 12
MAX_TOKENS = 300


class UnsupportedPolynomial(ValueError):
    pass


def guard(test: bool, message: str) -> None:
    if not test:
        raise UnsupportedPolynomial(message)


def degree(m: Monomial) -> int:
    return sum(p for _, p in m)


def tidy(p: Poly) -> Poly:
    p = {m: Fraction(c) for m, c in p.items() if c}
    guard(len(p) <= MAX_TERMS and all(degree(m) <= MAX_DEGREE for m in p), 'Polynomial expansion limit')
    return p


def add(p: Poly, q: Poly, scale: Fraction = Fraction(1)) -> Poly:
    r = dict(p)
    for m, c in q.items():
        r[m] = r.get(m, Fraction(0)) + scale * c
    return tidy(r)


def mul(p: Poly, q: Poly) -> Poly:
    guard(len(p) * len(q) <= 40_000, 'Polynomial product budget')
    r: Poly = {}
    for a, x in p.items():
        for b, y in q.items():
            d = dict(a)
            for v, power in b:
                d[v] = d.get(v, 0) + power
            m = tuple(sorted(d.items()))
            r[m] = r.get(m, Fraction(0)) + x * y
    return tidy(r)


def power(p: Poly, n: int) -> Poly:
    guard(0 <= n <= MAX_DEGREE, 'Power is outside the supported budget')
    result: Poly = {(): Fraction(1)}
    for _ in range(n):
        result = mul(result, p)
    return result


_TOKEN = re.compile(r'\s*(?:(\d+)|([^\W\d]\w*)|([()+*^\-]))', re.UNICODE)


class Parser:
    def __init__(self, s: str, variables: set[str]):
        guard(isinstance(s, str) and len(s) <= 10_000, 'Expression size limit')
        self.variables = variables
        self.tokens: list[str] = []
        i = 0
        while i < len(s):
            if s[i:].isspace():
                break
            m = _TOKEN.match(s, i)
            guard(m is not None, 'Unsupported polynomial notation')
            assert m is not None
            self.tokens.append(next(x for x in m.groups() if x is not None))
            i = m.end()
            guard(len(self.tokens) <= MAX_TOKENS, 'Polynomial token budget')
        self.i = 0

    def peek(self) -> str:
        return self.tokens[self.i] if self.i < len(self.tokens) else ''

    def pop(self) -> str:
        result = self.peek()
        guard(bool(result), 'Unexpected end of expression')
        self.i += 1
        return result

    def sum(self) -> Poly:
        p = self.product()
        while self.peek() in {'+', '-'}:
            sign = 1 if self.pop() == '+' else -1
            p = add(p, self.product(), Fraction(sign))
        return p

    def product(self) -> Poly:
        p = self.unary()
        while self.peek() == '*':
            self.pop()
            p = mul(p, self.unary())
        return p

    def unary(self) -> Poly:
        if self.peek() in {'-', '+'}:
            sign = -1 if self.pop() == '-' else 1
            return {m: sign * c for m, c in self.unary().items()}
        return self.exponent()

    def exponent(self) -> Poly:
        token = self.pop()
        if token == '(':
            p = self.sum()
            guard(self.pop() == ')', 'Unmatched parenthesis')
        elif token.isdecimal():
            guard(len(token) <= 12, 'Integer too large')
            n = int(token)
            p = {(): Fraction(n)} if n else {}
        else:
            guard(token in self.variables, 'Unbound or unsupported scalar: ' + token)
            p = {((token, 1),): Fraction(1)}
        if self.peek() == '^':
            self.pop()
            n = self.pop()
            guard(n.isdecimal() and len(n) <= 2, 'Expected a small natural exponent')
            p = power(p, int(n))
        return p

    def parse(self) -> Poly:
        p = self.sum()
        guard(self.i == len(self.tokens), 'Trailing polynomial tokens')
        return tidy(p)


def parse(s: str, variables: set[str]) -> Poly:
    return Parser(s, variables).parse()


def equality(s: str, variables: set[str]) -> Poly:
    guard(s.count('=') == 1, 'Expected one polynomial equality')
    lhs, rhs = s.split('=')
    return add(parse(lhs, variables), parse(rhs, variables), Fraction(-1))


def encode(p: Poly) -> list[list[Any]]:
    guard(all(c.denominator == 1 for c in p.values()), 'Rational multiplier is not valid in every ring')
    return [[[[v, e] for v, e in m], c.numerator] for m, c in sorted(p.items())]


def decode(rows: Any, variables: set[str]) -> Poly:
    guard(isinstance(rows, list) and len(rows) <= MAX_TERMS, 'Invalid polynomial rows')
    p: Poly = {}
    for row in rows:
        guard(isinstance(row, list) and len(row) == 2, 'Invalid monomial row')
        factors, coefficient = row
        guard(type(coefficient) is int and coefficient != 0 and abs(coefficient) < 10**30, 'Invalid integer coefficient')
        guard(isinstance(factors, list) and len(factors) <= MAX_DEGREE, 'Invalid factors')
        converted = []
        for f in factors:
            guard(isinstance(f, list) and len(f) == 2 and isinstance(f[0], str), 'Invalid factor')
            v, e = f
            guard(v in variables and type(e) is int and 0 < e <= MAX_DEGREE, 'Invalid variable or exponent')
            converted.append((v, e))
        m = tuple(converted)
        guard(list(m) == sorted(m) and len({v for v, _ in m}) == len(m) and m not in p, 'Noncanonical monomial')
        p[m] = Fraction(coefficient)
    p = tidy(p)
    guard(encode(p) == rows, 'Noncanonical polynomial')
    return p


def _order(m: Monomial) -> tuple:
    return degree(m), m


def solve(target: Poly, assumptions: list[Poly], max_columns: int = 600) -> list[Poly] | None:
    """Bounded exact ideal-membership search; replay uses only add/mul, not this solver.

    Linear algebra is over Q for efficiency, but a result with any noninteger
    coefficient is rejected: 2x=0 must never justify x=0 in a ring of characteristic 2.
    """
    if not target:
        return [{} for _ in assumptions]
    goal_degree = max(map(degree, target))
    variables = sorted({v for p in [target, *assumptions] for m in p for v, _ in m})
    columns: list[tuple[int, Monomial, Poly]] = []
    for i, a in enumerate(assumptions):
        if not a:
            continue
        d = max(map(degree, a))
        if d > goal_degree:
            continue
        for k in range(goal_degree - d + 1):
            for vs in combinations_with_replacement(variables, k):
                powers: dict[str, int] = {}
                for v in vs:
                    powers[v] = powers.get(v, 0) + 1
                m = tuple(sorted(powers.items()))
                columns.append((i, m, mul({m: Fraction(1)}, a)))
                if len(columns) > max_columns:
                    return None
    # pivot -> (normalized polynomial, combination of original columns)
    basis: dict[Monomial, tuple[Poly, dict[int, Fraction]]] = {}
    for index, (_, _, column) in enumerate(columns):
        p, combo = column.copy(), {index: Fraction(1)}
        while p:
            pivot = max(p, key=_order)
            c = p[pivot]
            if pivot not in basis:
                basis[pivot] = ({m: x/c for m, x in p.items()}, {k: x/c for k, x in combo.items()})
                break
            vector, vec_combo = basis[pivot]
            p = add(p, vector, -c)
            for k, x in vec_combo.items():
                combo[k] = combo.get(k, Fraction(0)) - c*x
                if not combo[k]:
                    del combo[k]
    p, answer = target.copy(), {}
    while p:
        pivot = max(p, key=_order)
        if pivot not in basis:
            return None
        c = p[pivot]
        vector, combo = basis[pivot]
        p = add(p, vector, -c)
        for k, x in combo.items():
            answer[k] = answer.get(k, Fraction(0)) + c*x
    multipliers: list[Poly] = [{} for _ in assumptions]
    for k, c in answer.items():
        if not c:
            continue
        i, m, _ = columns[k]
        multipliers[i][m] = multipliers[i].get(m, Fraction(0)) + c
    multipliers = [tidy(m) for m in multipliers]
    if any(c.denominator != 1 for p in multipliers for c in p.values()):
        return None
    total: Poly = {}
    for m, a in zip(multipliers, assumptions):
        total = add(total, mul(m, a))
    return multipliers if total == target else None


def scalar_context(frame: dict) -> tuple[str, set[str]]:
    """Only exact, recognized class applications; no substring-based ring guess."""
    types = [c['type'].strip() for c in frame['context']]
    rings = []
    for t in types:
        m = re.fullmatch(r'(?:EuclideanDomain|CommRing) ([^\W\d]\w*)', t, re.UNICODE)
        if m:
            rings.append(m[1])
    guard(len(set(rings)) == 1, 'No unique recognized commutative ring in local context')
    ring = rings[0]
    # Later binders shadow earlier names. Only expose scalar variables.
    last = {c['name']: c['type'].strip() for c in frame['context']}
    variables = {n for n, t in last.items() if t == ring and re.fullmatch(r'[^\W\d]\w*', n, re.UNICODE)}
    guard(0 < len(variables) <= 20, 'Scalar-context size is unsupported')
    return ring, variables


def _conjuncts(s: str) -> list[str]:
    # The restricted parser will reject embedded quantifiers, negation and
    # implication, so splitting only top-level conjunctions cannot strengthen them.
    out, depth, begin = [], 0, 0
    for i, ch in enumerate(s):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == '∧' and depth == 0:
            out.append(s[begin:i].strip()); begin = i+1
    out.append(s[begin:].strip())
    return out


def assumptions(frame: dict, variables: set[str]) -> list[tuple[dict, Poly]]:
    result = []
    contexts = frame['context']
    last = {c['name']: i for i, c in enumerate(contexts)}
    for i, c in enumerate(contexts):
        if last[c['name']] != i:
            continue
        # Reject the WHOLE proposition if any part is not an equality.
        # In particular, (P → x=0 ∧ y=0) must not supply the unconditional y=0.
        parts = _conjuncts(c['type'])
        try:
            parsed = [equality(claim, variables) for claim in parts]
        except (UnsupportedPolynomial, RecursionError):
            continue
        for j, (claim, p) in enumerate(zip(parts, parsed)):
            if p:
                result.append(({'context_index': i, 'conjunct': j, 'name': c['name'], 'statement': claim}, p))
    return result


def certify(frame: dict, max_assumptions: int = 2) -> dict | None:
    """Find a small certificate, preferring fewer assumptions in fixed order."""
    try:
        ring, variables = scalar_context(frame)
        target = equality(frame['statement'], variables)
        available = assumptions(frame, variables)
        if len(available) > 20:
            return None
        for count in range(min(max_assumptions, len(available)) + 1):
            for selected in combinations(available, count):
                multipliers = solve(target, [p for _, p in selected])
                if multipliers is not None:
                    result = {'schema': 'proofreader.polynomial-certificate/v1', 'frame_id': frame['id'],
                              'ring': ring, 'variables': sorted(variables), 'goal': frame['statement'],
                              'assumptions': [a for a, _ in selected],
                              'multipliers': [encode(p) for p in multipliers]}
                    verify(frame, result)
                    return result
    except (UnsupportedPolynomial, RecursionError):
        return None
    return None


def verify(frame: dict, certificate: dict) -> None:
    """Independently reconstruct and check the claimed identity against a snapshot.

    A passing check does not authenticate the snapshot or establish its Lean
    provenance. Use source replay for that separate question.
    """
    guard(isinstance(certificate, dict), 'Invalid certificate')
    guard(set(certificate) == {'schema','frame_id','ring','variables','goal','assumptions','multipliers'}, 'Unknown certificate fields')
    guard(certificate['schema'] == 'proofreader.polynomial-certificate/v1', 'Unsupported certificate schema')
    guard(type(certificate['frame_id']) is int and certificate['frame_id'] == frame['id'], 'Wrong certificate frame')
    ring, variables = scalar_context(frame)
    guard(certificate['ring'] == ring and certificate['variables'] == sorted(variables), 'Wrong scalar context')
    guard(certificate['goal'] == frame['statement'], 'Certificate goal mismatch')
    target = equality(frame['statement'], variables)
    available = { (a['context_index'], a['conjunct']): (a,p) for a,p in assumptions(frame, variables) }
    aa, mm = certificate['assumptions'], certificate['multipliers']
    guard(isinstance(aa,list) and isinstance(mm,list) and len(aa) == len(mm) and len(aa) <= 20, 'Invalid certificate dimensions')
    total: Poly = {}
    seen = set()
    for a, encoded in zip(aa, mm):
        guard(isinstance(a,dict) and type(a.get('context_index')) is int and type(a.get('conjunct')) is int, 'Invalid assumption reference')
        key = a['context_index'], a['conjunct']
        guard(key in available and key not in seen, 'Missing or repeated assumption')
        seen.add(key)
        actual, p = available[key]
        guard(a == actual, 'Assumption changed from local context')
        total = add(total, mul(decode(encoded, variables), p))
    guard(total == target, 'Polynomial certificate identity failed')


def polynomial_text(p: Poly) -> str:
    if not p:
        return '0'
    pieces = []
    for m in sorted(p, key=_order, reverse=True):
        c = p[m]
        monomial = ' · '.join(v if n == 1 else f'{v}^{n}' for v, n in m)
        magnitude = abs(c)
        term = monomial if magnitude == 1 and monomial else str(magnitude) + (' · ' + monomial if monomial else '')
        pieces.append(('- ' if c < 0 else '+ ') + term)
    result = ' '.join(pieces)
    return result[2:] if result.startswith('+ ') else '−' + result[2:]


def certificate_text(certificate: dict) -> str:
    variables = set(certificate['variables'])
    terms = []
    for a, m in zip(certificate['assumptions'], certificate['multipliers']):
        lhs, rhs = a['statement'].split('=')
        terms.append(f"({polynomial_text(decode(m,variables))}) · (({lhs.strip()}) − ({rhs.strip()}))")
    return 'LHS − RHS = ' + (' + '.join(terms) if terms else '0') + '. Expand and compare integer coefficients.'



# File: proofreader/narrative_io.py

"""Source-bound extraction/re-extraction and offline, reproducible reading bundles.

Remote execution sends the complete submitted source to AXLE only after explicit
consent. Native elaboration can execute arbitrary metaprograms: it is NOT a
sandbox. Imported receipts are observations, never authentication credentials.
"""
from __future__ import annotations
from dataclasses import asdict
from pathlib import Path
import re
from typing import Any

from .core import lean_string
from .kernel import InvalidExport, require
from .kernel_io import axle_request, strict_json, _write_json
from .lean import MODULE_RE, driver_file, run_bounded
from .model import digest, report
from .narrative import Snapshot, Narrative, reading_binding, prose, check_reading
from .polynomial import verify as verify_polynomial
from .render import write_html

PREFIX = 'PR_NARRATIVE:'
MAX_BYTES = 16_000_000
VERSION = re.compile(r'4\.\d+\.\d+')


def exporter_source() -> str:
    return (Path(__file__).parent / 'data' / 'Narrative.lean').read_text(encoding='utf-8')


def extraction_source(theorem: str, *, version: str, context: str | None = None,
                      module: str | None = None, driver: str | None = None) -> str:
    require(sum(x is not None for x in (context,module,driver)) == 1, 'Supply one source context, imported module or exact driver')
    require(isinstance(theorem,str) and 0 < len(theorem) <= 2000 and '\x00' not in theorem,
            'Invalid theorem name')
    require(isinstance(version,str) and VERSION.fullmatch(version) is not None, 'An exact Lean version is required')
    exporter = exporter_source()
    marker = 'open Lean Meta Elab Command'
    require(marker in exporter, 'Missing exporter boundary')
    if driver is not None:
        require(isinstance(driver,str) and bool(driver.strip()) and len(driver.encode('utf-8')) <= MAX_BYTES, 'Invalid exact driver')
        prefix = driver
    elif module is not None:
        require(bool(MODULE_RE.fullmatch(module)), 'Unsafe module name')
        prefix = exporter.replace(marker, 'import '+module+'\n'+marker, 1)
    else:
        require(isinstance(context,str) and bool(context.strip()), 'Empty source context')
        require(len(context.encode('utf-8')) <= MAX_BYTES, 'Source context exceeds the budget')
        # Required tool imports precede, rather than substitute, the caller's
        # complete import header. No source line or existing import is dropped.
        prefix = 'import Lean\nimport Lean.Util.CollectAxioms\n'+context.rstrip()+'\n'+exporter[exporter.index(marker):]
    gate = '\nrun_elab do\n  unless Lean.versionString == '+lean_string(version)+' do\n    throwError "ProofReader exact Lean version mismatch"\n'
    return prefix+gate+('' if driver is not None else '\n#narrative '+lean_string(theorem)+'\n')


def parse_stream(stdout: str, *, theorem: str, version: str) -> Snapshot:
    require(isinstance(stdout,str) and len(stdout.encode('utf-8')) <= MAX_BYTES, 'Exporter output budget')
    records = []
    for line in stdout.splitlines():
        m = re.fullmatch(r'(?:[^\n]*?\binfo: )?'+PREFIX+r'(.*)', line)
        if m:
            records.append(Snapshot(strict_json(m[1])))
    require(len(records) == 1, 'Expected exactly one complete narrative record')
    s = records[0]
    require(s.record['theorem'] == theorem, 'Unexpected exported theorem')
    require(s.record['lean_version'] == version, 'Exact Lean version mismatch')
    return s


def response_stdout(response: dict, source: str, version: str) -> str:
    require(isinstance(response,dict) and response.get('okay') is True,
            'Lean execution did not succeed: '+str(response.get('user_error', response.get('detail','missing success')))[:500])
    require(response.get('failed_declarations') == [], 'Incomplete or disallowed declarations were reported')
    require(isinstance(response.get('content'),str) and response['content'].rstrip('\n') == source.rstrip('\n'),
            'Service changed the submitted source')
    require(response.get('info',{}).get('environment') == 'lean-'+version, 'Service used another environment')
    for field in ('lean_messages','tool_messages'):
        messages=response.get(field)
        require(isinstance(messages,dict) and messages.get('errors') == [], 'Missing or unsuccessful '+field)
    infos=response['lean_messages'].get('infos')
    require(isinstance(infos,list) and all(isinstance(x,str) for x in infos), 'Malformed Lean messages')
    return '\n'.join(infos)


def extract_narrative(theorem: str, output: Path, *, context: str | None = None,
                      module: str | None = None, version: str = '4.34.1', backend: str = 'native',
                      project: Path | None = None, trust_project: bool = False,
                      allow_remote: bool = False, timeout: float = 180,
                      expected: dict | None = None, driver: str | None = None) -> dict:
    """Expected snapshot, when given, must match fresh extraction exactly."""
    require(backend in {'native','axle'}, 'Unknown execution backend')
    if backend == 'native' and not trust_project:
        raise PermissionError('Lean elaboration runs code. Pass --trust-project only for trusted or isolated source.')
    if backend == 'axle' and not allow_remote:
        raise PermissionError('This sends the full Lean source to AXLE. Pass --allow-remote to consent.')
    require(0 < timeout <= 900, 'Invalid execution timeout')
    if backend == 'native':
        require(project is not None and project.is_dir(), 'Native extraction needs an existing --project')
    else:
        require(module is None and (context is not None or driver is not None), 'Remote extraction requires self-contained source context or exact driver')
    expected_snapshot = Snapshot(expected) if expected is not None else None
    if expected_snapshot is not None:
        require(expected_snapshot.record['theorem'] == theorem and expected_snapshot.record['lean_version'] == version,
                'Expected snapshot theorem/version mismatch')
    source = extraction_source(theorem,version=version,context=context,module=module,driver=driver)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/'Extract.lean').write_text(source,encoding='utf-8')
    if driver is not None:
        (output/'OriginalDriver.lean').write_text(driver,encoding='utf-8')
    if context is not None:
        (output/'Context.lean').write_text(context,encoding='utf-8')
    # Never leave last run's successful record at the canonical output path.
    for name in ('snapshot.json','actual-snapshot.json','receipt.json','reading.json','reader.html','coverage.json','proof.txt','polynomial-certificates.json'):
        path=output/name
        if path.is_file():path.unlink()
    receipt={'schema':'proofreader.narrative-receipt/v1','status':'failed',
             'theorem':theorem,'lean_version':version,'backend':backend,
             'source_sha256':digest(source),'context_sha256':digest(context) if context is not None else None,
             'driver_sha256':digest(driver) if driver is not None else None, 'module':module,'receipt_authenticated':False,'english_formally_verified':False,
             'exact_openai_project_replayed':False,'errors':[], 'expected_snapshot_sha256':expected_snapshot.sha256 if expected_snapshot else None}
    try:
        if backend=='axle':
            response=axle_request(source,version,allow_remote=True,timeout=timeout)
            _write_json(output/'response.json',response)
            stdout=response_stdout(response,source,version)
            receipt['service_info']=response['info']
        else:
            assert project is not None
            with driver_file(project,source) as driver:
                run=run_bounded(['lake','env','lean',str(driver)],project.resolve(),timeout=timeout)
            _write_json(output/'run.json',asdict(run))
            (output/'stderr.txt').write_text(run.stderr,encoding='utf-8')
            require(run.status=='passed' and run.exit_code==0,run.reason or 'Native Lean did not succeed')
            stdout=run.stdout
        (output/'stdout.txt').write_text(stdout,encoding='utf-8')
        snapshot=parse_stream(stdout,theorem=theorem,version=version)
        # Preserve diagnostic actual snapshot separately on a comparison failure.
        _write_json(output/'actual-snapshot.json',snapshot.record)
        if expected_snapshot is not None:
            require(snapshot.record == expected_snapshot.record,'Re-extracted snapshot differs from the supplied record')
        receipt.update(status='passed',snapshot_sha256=snapshot.sha256,
                       selected_judgements=snapshot.record['judgements_checked'],
                       snapshot_reextraction_matched=expected_snapshot is not None,
                       all_selected_judgements_kernel_checked=True,
                       path_linkage_checked_in_lean=True,
                       trust_boundary='Trusted source, imports, Lean compiler, traversal, pretty-printer, renderer, and recorded transport. No formal English guarantee.')
        write_bundle(snapshot.record,output,source=context or driver or ('import '+str(module)+'\n'),file='Context.lean',receipt=receipt)
    except (ValueError,OSError,RuntimeError,RecursionError) as exc:
        receipt['status']='failed'
        receipt['all_selected_judgements_kernel_checked']=False
        receipt['path_linkage_checked_in_lean']=False
        receipt['errors']=[str(exc)[:4000]]
        for name in ('snapshot.json','reading.json','reader.html','coverage.json','proof.txt','polynomial-certificates.json'):
            stale=output/name
            if stale.is_file():stale.unlink()
    _write_json(output/'receipt.json',receipt)
    return receipt


def write_bundle(record: dict, output: Path, *, source: str = '', file: str = 'Original.lean',
                 receipt: dict | None = None, title: str | None = None,
                 provenance_note: str | None = None) -> dict:
    n=Narrative(record)
    d=n.document(source=source,file=file,receipt=receipt,title=title,provenance_note=provenance_note)
    check_reading(record,d)
    for i,c in n.certificates.items():verify_polynomial(n.frames[i],c)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    _write_json(output/'snapshot.json',record)
    _write_json(output/'polynomial-certificates.json',list(n.certificates.values()))
    (output/'reading.json').write_text(d.to_json(),encoding='utf-8')
    (output/'proof.txt').write_text(prose(d),encoding='utf-8')
    write_html(d,output/'reader.html')
    if receipt is not None:_write_json(output/'receipt.json',receipt)
    result={**n.snapshot.coverage(),**report(d),'snapshot_sha256':n.snapshot.sha256,
            'reading_binding':reading_binding(d),'polynomial_certificates_replayed':len(n.certificates),
            'exported_frames_accounted_for':len(n.owners),'whole_corpus_coverage':False,
            'formula_backend':record['formula_backend'],'model_calls':0}
    _write_json(output/'coverage.json',result)
    return result


def verify_certificates(record: dict, certificates: list[dict]) -> None:
    s=Snapshot(record)
    require(isinstance(certificates,list) and len(certificates)<=1000,'Certificate budget')
    seen=set()
    for c in certificates:
        require(isinstance(c,dict) and type(c.get('frame_id')) is int,'Invalid certificate')
        i=c['frame_id'];require(0<=i<len(s.frames) and i not in seen,'Invalid/repeated certificate frame')
        verify_polynomial(s.frames[i],c);seen.add(i)



# File: artifacts/v0.3/live-4.34.1-observations.json

{
  "schema": "proofreader.live-narrative-observations/v1",
  "environment": "lean-4.34.1",
  "method": "AXLE through Wolfram; HTTP JSON, ignore_imports=false, theorems_only=false",
  "valid": {
    "okay": true,
    "errors": [],
    "failed_declarations": [],
    "source_sha256": "b7d4fa6cbc3c9aac0160bdfa31556d2fd5e0ad1adcc693d55e7a7670583ff066",
    "record_sha256": "dad8ef23a231904f37b73979f8284ea3662ffe8f8cd30c79066856f2095b4dd7",
    "request_id": "fae2dc6e-9adf-4b54-b88e-612babf2b095",
    "completion_markers": [
      "PR_NARRATIVE_REPEAT_OK",
      "PR_NARRATIVE_MUTATION_REJECTED"
    ],
    "source_preserved": true,
    "execution_time_ms": 12773
  },
  "wrong_path": {
    "okay": false,
    "source_sha256": "116e4213b292dc64a594360399691ee461b4c3a8dc889e6d65d757f62dd62147",
    "request_id": "2bdcc3f2-8f49-45ed-abd6-c0aa7bcc6291",
    "errors": [
      "Original source linkage mismatch at frame 40"
    ]
  },
  "wrong_claim": {
    "okay": false,
    "source_sha256": "47d4a7254b16b43eb6f41946c7d9615df04f9220ca29948d72c134f0e161785e",
    "request_id": "fc74586b-c20a-4600-b7d8-2f75a47d956f",
    "errors": [
      "Kernel declaration type mismatch: the original judgement proves a*r+d*s=1, not False, in its actual local context."
    ],
    "error_text_is_summary": true
  },
  "executor_commit": "a1c7cfcab0a878791ac3fbae13ec37d0bc73c4e2",
  "executor_artifact_sha256": "4602ef53ada50e13c0b1197e10f7c126bc0f61f48edaa34d817cb5d2aaeb40c6",
  "receipt_authenticated": false,
  "record_recovery": "The retained 4.34.0 snapshot with only lean_version changed to 4.34.1 matches the SHA-256 of the complete newly exported JSON exactly; no other field was inferred or altered.",
  "exact_openai_project_replayed": false,
  "imports": "Original theorem body unchanged; minimal Mathlib imports replace the project Model import. Exact Mathlib revision and full project closure not verified."
}

