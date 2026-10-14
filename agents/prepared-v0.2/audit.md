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
No independent auditor or mathematician study has run. Existing live negative tests cover a limited set of toy proof mutations; treat all attached receipts as unauthenticated observations.


# File: README.md

# Lean ProofReader

Read a formal argument as mathematical prose, without starting in a Lean editor.
The renderer is deterministic and uses no language-model API. ProofReader keeps
source outlines, typed proofs, replay observations and English fidelity separate.

## Version 0.2.0 — typed arguments and independently checked claims

This release adds a second, substantially stronger reading path:

**Lean proof expressions → source-linked typed judgements → mathematical English.**

A generated Lean checker reconstructs the original statement and proof, follows
every recorded path in the original proof, and submits every closed intermediate
term/type pair to the kernel. Incorrect intermediate claims, original-proof paths,
axiom inventories and toolchain versions cannot be treated as successful checks.

The demo contains **five actual Lean-exported examples** and the existing **nine
source-only OpenAI declaration candidates**. One typed example has a saved live
checking observation covering its original proof, source paths and all 18 recorded
judgements (including proof and data arguments). Other examples must not inherit
that result. The observations were made on **Lean 4.34.0 through AXLE**.

The OpenAI Bézout-frame theorem body also compiled and exported in an adapted
minimal-import harness. That is **not** a run of the pinned OpenAI project, which
requires **4.34.1**. It produced 7,008 expression nodes and 1,511 typed steps, with
11 explicitly capped branches; the full large record was not transferred back
through the chat connector. It is not presented as a completed English proof.

**Not complete:** the entire OpenAI corpus has not been built or translated,
English semantics is not formally certified, and mathematician comprehension has
not been evaluated. Whole-corpus English coverage remains false. Native build and
one-command extraction integration remain mandatory external CI checks.

See [the release validation](docs/VALIDATION_V0_2.md) for measured results and
[the trust contract](docs/TRUST.md) for the precise guarantees.

## Open the reader

Python 3.11 or later. No runtime Python dependencies or API key are needed for
reading, regeneration, or creating an offline HTML file.

```sh
python -m proofreader kernel-demo -o reader.html
python -m proofreader serve
```

Open `http://127.0.0.1:8765`. The default library starts with composition of
injective functions. Search `and_swap` for the attached checking observation.
The **Typed** filter separates the five proof-expression examples from the
OpenAI source outlines. The HTML file works without a server in a normal browser;
attachment previewers that disable JavaScript may require the local server.

`proofreader demo` still writes the legacy six-file OpenAI source-only demo.

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
Re-extract on the desired version instead. In our remote environment,
`import Mathlib` failed because a cached dependency was absent, while minimal
imports worked. The exact pinned OpenAI environment remains unvalidated.

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

