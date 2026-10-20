# Dependency-cone readings

Most of the 536 documented theorem targets are assembly theorems. Their proofs
apply project lemmas (`OAI.*` constants) whose own proofs carry much of the
mathematics. The retained readings show those lemmas only as cited names. This
page describes the plan, the workflow and the loader that extend reading coverage
to the lemmas that the retained readings cite.

No dependency-cone extraction has run yet. The numbers below describe the plan,
not results.

## Level-1 cone

The level-1 cone is the set of project constants that appear as the head of a
proof frame in at least one retained reading. A frame head is a constant that
the checked proof applies, so every cone member is a constant that a kernel-checked
reading actually uses. Constants that occur only inside formulas, object
arguments or statements are not citations.

Each planned lemma is extracted in the original environment of a module whose
retained reading cites it: the extraction driver imports that solution module.
The cited constant is in scope there because the retained reading was extracted
after importing the same module, and the module source is pinned by hash. The
lemma may be defined in an imported module.

## Denominator

The committed plan is `benchmarks/dependency-cone/plan.json`
(`leanglish.dependency-cone-plan/v1`). It is derived from the 492 retained
readings of the pinned release `leanglish-original-project-317dc31`.

| Quantity | Count |
| --- | ---: |
| Retained readings | 492 |
| Readings that cite at least one project constant | 477 |
| Citing frames | 2,068 |
| Cited project constants (the cone) | 1,764 |
| Already read (the constant is itself a documented target with a reading) | 31 |
| Excluded, with a recorded reason | 25 |
| Planned lemmas | 1,708 |
| Planned lemmas that are compiler-abstracted proofs (`…._proof_N`) | 106 |
| Environment modules (one shard each) | 379 |

The count of 1,764 includes 2 mangled private names (`_private.OAI.…`), so 1,762
of the cited constants start with `OAI.`.

Cone readings are a separate denominator, named `dependency-cone-level-1`. They
never count toward the 536-target coverage, and a cone reading of a lemma does not
change the status of any documented target. Every plan, shard report and summary
records `counts_toward_documented_target_coverage: false`.

### Exclusions

A cited constant is excluded only for one of these reasons. The plan lists every
excluded name with its reason.

| Reason | Rule | Count |
| --- | --- | ---: |
| `documented-theorem-target` | The constant is a documented target without a reading; it stays in the target denominator. | 0 |
| `documented-definition` | The constant is a documented definition reference, not a proof obligation. | 0 |
| `not-addressable-by-exporter` | A mangled private name, or a name with numeric or escaped components. The exporter resolves names with `String.toName`, which cannot form these components. | 2 |
| `compiler-matcher-or-recursor` | A name ending in `match_N`, `casesOn`, `rec`, `recOn`, `brecOn`, `below` or a similar compiler-generated suffix. | 5 |
| `instance-by-name` | A last component of the form `inst` followed by an uppercase letter, which is Lean's generated instance name. | 14 |
| `constructor-by-name` | A last component `mk`, which is a structure constructor name. | 4 |

The last four reasons are name conventions, not Lean facts. A user-named
instance, a structure projection or a proof-valued definition is not detected by
name. Those constants stay in the plan as `unknown-kind`, and the exporter
decides at extraction time.

Some excluded instances carry mathematics. For example,
`OAI.ThreeManifold.GluedConstruction.instCompactSpaceCarrierManifold` proves
compactness of a constructed space. A later plan can include instances by
changing the rule; the exclusion is a scope decision for level 1.

### Planned lemmas

Every planned lemma has kind `unknown-kind`. The exporter in
`proofreader/data/Narrative.lean` accepts a declaration only if it has a proof
body and a proposition as its type. The worker records the exporter's decision
for each lemma, as described in [Outcomes](#outcomes).

Lemmas named `…._proof_N` or `…._proof_N_M` are auxiliary theorems that Lean
abstracts from a proof. By name, 100 of the 106 are abstracted from the proof of
a documented target that has a reading, for example
`OAI.AffineBernstein.affine_bernstein._proof_1_1`. Their readings show parts of
those target proofs that the target readings show only as cited names. They are
planned and carry the hint `compiler-abstracted-proof`.

### Environment module rule

A lemma can be cited from more than one module (38 lemmas are). The plan chooses,
among the citing modules, the module that cites the most planned lemmas, with
ties broken by module name. This rule is deterministic and reduces the number of
module builds. `validate_plan` recomputes it, so a lemma cannot be moved to another
shard without detection.

### Shards

A shard is one environment module and all of its planned lemmas. Its identifier
is the first 24 hexadecimal digits of the SHA-256 of the module name, the same
convention as the original-environment theorem campaign. A worker builds the
module once and then extracts each lemma against that build.

The largest shard has 59 lemmas. Shards are listed in module-name order. Full
dispatch uses two consecutive blocks, `full-1` (shards 1–256) and `full-2`
(shards 257–379), because a GitHub Actions matrix holds at most 256 jobs.

## Plan inputs

The planner reads one archive and executes nothing:

- `proofs/<id>/snapshot.json` and `proofs/<id>/receipt.json` for every retained
  reading. The receipt supplies the identity (`module`, `theorem`). The planner
  requires that the pair is one of the 536 documented targets in the original
  plan, that `<id>` is the hash of the pair, and that the receipt binds the exact
  snapshot.
- `original-evidence/plan.json` and `original-evidence/environment.json`, the
  original project plan and its dependency audit. These supply the target and
  definition inventory and the source hash of each environment module.
- `original-evidence/proof-workers/*`, the retained original-environment theorem
  workers. These are used only to choose the pilot.

The plan records the archive digest, the original plan and environment digests,
the exporter digest and a corpus digest. The corpus digest equals
`corpus_sha256` in `benchmarks/reading-kpis/current.json`, so both measurements
use the same 492 snapshots.

To regenerate the plan:

```sh
python scripts/plan_dependency_cone.py fetch --output /tmp/release.zip
python scripts/plan_dependency_cone.py plan --archive /tmp/release.zip \
  --output benchmarks/dependency-cone/plan.json
```

`--check` compares the derived plan with the committed plan byte for byte. The
workflow runs this check before any extraction. A change to the exporter changes
`execution.exporter_sha256`, so the plan must then be regenerated.

## Pilot

The default run is a bounded pilot of 8 shards and 151 lemmas. The pilot takes
the 8 environment modules with the most planned lemmas among modules that
already have a retained original-environment theorem worker that completed, with
identical before and after environment audits equal to the plan's environment,
in at most 1,800 seconds. Ties are broken by module name. Of the 379 modules, 95
qualify.

The pilot tests the machinery on modules that are known to build and extract in
this exact environment. The module with the most planned lemmas,
`OAI.Probability.GaussianReplacement.FiberEquality` (59), is not in the pilot
because no original-environment build of it is retained.

| Environment module | Planned lemmas | Retained worker time (s) |
| --- | ---: | ---: |
| `OAI.Probability.ContinuumTransition.Main` | 30 | 684 |
| `OAI.Combinatorics.UniformKServer.Main` | 21 | 840 |
| `OAI.Probability.GaussianInformation.Main` | 21 | 526 |
| `OAI.Probability.CoordinateSweeps.Main` | 18 | 340 |
| `OAI.Probability.UnimodularPercolation.CayleyMain` | 17 | 574 |
| `OAI.MathematicalPhysics.SheetFlows.SheetProgram` | 15 | 104 |
| `OAI.Probability.ProjectionMoments.Main` | 15 | 282 |
| `OAI.MathematicalPhysics.NavierStokes.BalancedTransport.MainResult` | 14 | 245 |

The retained worker times are unsigned observations. They select the pilot and
are never acceptance evidence.

## Running the campaign

The workflow `.github/workflows/dependency-cone.yml` runs on `workflow_dispatch`
and on pushes to `claude/keen-archimedes-ihorkq` that change the workflow or
`benchmarks/dependency-cone/`. Choose the scope on dispatch:

- `pilot` (default): the 8 pilot shards.
- `full-1`, then `full-2`: all 379 shards in two dispatches.

Each run has three jobs:

1. `plan` runs the synthetic tests, re-derives the committed plan from the pinned
   archive, extracts the original plan and environment audit, and emits the matrix.
2. `extract` runs one job per shard with `max-parallel: 8` and a 225-minute
   timeout, the same per-job limits as the original-environment theorem campaign.
   It reuses that campaign's machinery: the `complete-openai-lean-source` artifact,
   `unpack_source`, the `original-openai-deps-1581d4cb-4341-full-v1` dependency
   cache, `audit_environment` before and after, `lake build <module>`, and
   `extract_narrative` with the campaign budgets (3,600 s build, 900 s per
   extraction, 2,000,000 heartbeats, 12,000 s wall clock).
3. `summary` reconciles every planned lemma and uploads
   `dependency-cone-summary.json`.

Every shard uploads `dependency-cone-<shard id>` with its report, build log and
the retained output of each attempted lemma, including failures. The extraction
step also runs after an earlier step fails, so a missing source archive or
dependency cache is recorded in the shard report. The workflow has read-only
permissions and never publishes, releases or pushes.

The same steps run locally, with `--trust-project`, on an isolated machine:

```sh
python scripts/plan_dependency_cone.py inputs --archive /tmp/release.zip --output /tmp/cone
python scripts/plan_dependency_cone.py matrix --scope pilot
python scripts/plan_dependency_cone.py run --project /tmp/original-project/lean \
  --original-plan /tmp/cone/original-plan.json --environment /tmp/cone/environment.json \
  --shard 55b304b716a214a3517ae6a5 --output /tmp/shards/one --trust-project
python scripts/plan_dependency_cone.py reconcile --environment /tmp/cone/environment.json \
  --scope pilot --shards /tmp/shards --output /tmp/cone-summary.json
```

Native elaboration executes the project's code and is not a sandbox.

## Outcomes

Each planned lemma ends with exactly one status. A shard report
(`leanglish.dependency-cone-shard/v1`) lists every planned lemma of its shard in
plan order.

| Status | Meaning |
| --- | --- |
| `reading-generated` | The exporter produced a kernel-checked, source-bound snapshot and the reading bundle. |
| `not-proof-valued` | The exporter reported `Expected a proof-valued declaration`: the type is not a proposition (for example, a data definition). |
| `no-proof-body` | The exporter reported `Expected a declaration with a proof body` (for example, an axiom or a constructor). |
| `disallowed-axiom` | The proof uses an axiom outside `propext`, `Classical.choice` and `Quot.sound`. |
| `frame-budget-exceeded` | The proof needs more than 1,000 frames. |
| `unknown-constant` | Lean did not find the name in the environment module. |
| `extraction-timeout` | The extraction exceeded its time budget. |
| `rendering-failed` | Lean exported a snapshot, but the reading bundle failed. The snapshot is kept as `actual-snapshot.json`. |
| `extraction-failed` | Any other extraction failure. |
| `build-failed`, `build-timeout` | The environment module did not build; no lemma of the shard was attempted. |
| `toolchain-unavailable`, `source-missing`, `source-changed` | The toolchain or the pinned module source did not match. |
| `deadline-not-attempted` | The shard's wall-clock budget ran out before this lemma. |
| `environment-invalidated` | The environment audit failed after extraction; earlier successes are withdrawn. |
| `not-attempted` | The shard stopped before any work, for example without the dependency cache. |

The summary (`leanglish.dependency-cone-summary/v1`) also uses
`shard-artifact-missing` for an in-scope shard without an artifact,
`shard-failed`, `shard-running` or `shard-preflight` for a shard that did not
finish, and `not-in-run-scope` for shards outside the dispatched scope.

The worker derives the status of a failed extraction from the retained
`run.json`, using the exporter's exact error messages. The loader recomputes this
classification from the same file.

## Loader checks

`proofreader.dependency_cone.load_shard` and `reconcile` accept a reading only
if all of these hold. The checks extend `catalog_inputs.load_proofs`.

- The report names this plan's digest, a planned shard and its module, the
  planned execution limits and the `dependency-cone-level-1` denominator.
- The lemma rows are exactly the planned lemmas, in plan order, with canonical
  identifiers. Duplicate shards, shards outside the run's scope and directories
  that no row references are rejected.
- The shard finished, and its before and after environment audits equal the
  plan's original environment.
- The build log exists, matches its recorded hash, and records
  `lake build <module>` with exit code 0.
- The toolchain reported Lean 4.34.1, and the module source hash equals the hash
  in the original source inventory.
- `Extract.lean` is exactly the planned driver for this lemma and this
  environment module, and its hash equals the receipt's `source_sha256`.
- The snapshot, receipt and row agree on the theorem, module, version, judgement
  count, kernel-check flags, heartbeat budget and snapshot hash.
- The saved compiler output parses to the same snapshot, and `run.json` records
  a successful native `lake env lean` run with the same output.

Counts in a report are recomputed from its rows. A failed or interrupted shard is
retained for accounting, and none of its readings is accepted.

## Entering the catalog

Cone readings enter the catalog in a later change. The summary's
`reading_index` maps each read lemma name to its environment module, shard,
directory and snapshot hash, and `reading_map(summary)` returns that mapping. The
cross-link mechanism, built in another track, uses a name-to-reading map to
link a citation in a target reading to the cone reading of the cited lemma.

The catalog must report cone coverage as its own line, with the denominator
from the plan. A lemma that is excluded, not attempted or not read keeps its
reason. The catalog renderer regenerates readings from the retained snapshots,
so a renderer change does not require a new extraction.

## Limitations

- **Level 1 only.** The plan covers constants that the 492 retained readings
  cite. Lemmas cited by cone readings form level 2. Level 2 is planned from level-1
  readings by the same rules, after level-1 results exist.
- **No results yet.** No Lean toolchain ran locally. The workflow has not run, and
  the planner, worker and loader are tested only with synthetic fixtures. The
  first pilot run is the first native test of this route.
- **Name-based exclusions.** The instance, constructor and compiler rules are
  conventions. The exporter does not record whether an accepted constant is a
  theorem, a proof-valued definition, an instance or a projection; a reading
  states only that the declaration is proof-valued and kernel checked.
- **Private names.** The two private lemmas cannot be addressed by the current
  exporter.
- **External inputs.** The workflow depends on the source artifact from run
  38822475057, which can expire, and on the dependency cache. GitHub restores a
  cache only from the current branch or the default branch. A shard without them
  records a failed outcome; it does not read anything.
- **Trust.** The trust boundary of [Source-bound mathematical reading](NARRATIVE.md)
  applies unchanged. Shard artifacts are unsigned observations. The checks
  establish consistency, not authenticity, and no English fidelity is claimed.
