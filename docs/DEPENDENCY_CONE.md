# Dependency-cone readings

Most of the 536 documented theorem targets are assembly theorems. Their proofs
apply project lemmas (`OAI.*` constants) whose own proofs carry much of the
mathematics. The retained readings show those lemmas only as cited names. This
page describes the plan, the workflow and the loader that extend reading coverage
to the lemmas that the retained readings cite.

The [Denominator](#denominator) describes the plan. One workflow run has read the
pilot scope; [Pilot results](#pilot-results) gives its outcomes, and
[Entering the catalog](#entering-the-catalog) describes how a catalog includes
the readings.

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
| Excluded, with a recorded reason | 11 |
| Planned lemmas | 1,722 |
| Planned lemmas that are compiler-abstracted proofs (`…._proof_N`) | 106 |
| Planned lemmas with a generated instance name (`…inst…`) | 14 |
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
| `constructor-by-name` | A last component `mk`, which is a structure constructor name. | 4 |

The last three reasons are name conventions, not Lean facts. A structure
projection or a proof-valued definition is not detected by name. Those constants
stay in the plan as `unknown-kind`, and the exporter decides at extraction time.

Instances are not excluded. Every cited constant heads a frame of a checked
proof, so a cited instance is proof-valued: its type is a proposition, and the
exporter reads its body like any other lemma. For example,
`OAI.ThreeManifold.GluedConstruction.instCompactSpaceCarrierManifold` proves that
a constructed space is compact. The 14 cited constants whose last component is
Lean's generated instance name (`inst` followed by an uppercase letter) are
planned with the hint `instance-by-name`.

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

## Pilot results

Run [39373979494](https://github.com/KyleJKistner/LeanDigest/actions/runs/39373979494)
on commit `4c072f149df9c6e43fa2a87cf062746838fffade` (2026-10-20) ran the pilot
scope. The dependency cache was not restorable from this branch, so the
preflight job re-created the dependency tree with the seed commands (4 minutes
42 seconds) and its environment audit matched the pinned audit. All 8 shards
then took the `resolve` route.

All 151 planned pilot lemmas reached `reading-generated`. No shard artifact is
missing, and the other 1,571 planned lemmas are `not-in-run-scope`. The
summary artifact `cone-summary-level-1` has SHA-256
`f5a040a92258d77251a49b11a3520e861e4a8271716386a3da6aa6556de696c4`. The 8 shard
artifacts and the plan artifact were downloaded, their digests matched the
values GitHub records, and `scripts/plan_dependency_cone.py reconcile` on them
reproduced the CI summary byte for byte.

The run's 11 artifacts (the plan, the preflight record, the 8 shards and the
summary) are the only copy of these readings that the repository can name.
GitHub deletes all 11 on 2027-01-18 (their recorded `expires_at`,
2027-01-18T05:16:06Z). `scripts/preserve_inputs.py` does not copy them, and no
cone reading is committed. After that date the readings can be restored only
by a new run, which needs a source bundle that has not expired (see
[External inputs](#external-inputs)).

| Environment module | Readings | Checked frames | Displayed steps | Gap steps | Job time | Build and extraction step |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `OAI.Probability.ContinuumTransition.Main` | 30 | 1,107 | 584 | 296 | 25 min | 24 min |
| `OAI.Combinatorics.UniformKServer.Main` | 21 | 814 | 515 | 256 | 27 min | 26 min |
| `OAI.Probability.GaussianInformation.Main` | 21 | 1,472 | 999 | 585 | 13 min | 11 min |
| `OAI.Probability.CoordinateSweeps.Main` | 18 | 1,419 | 1,080 | 601 | 12 min | 10 min |
| `OAI.Probability.UnimodularPercolation.CayleyMain` | 17 | 936 | 546 | 228 | 19 min | 18 min |
| `OAI.MathematicalPhysics.SheetFlows.SheetProgram` | 15 | 397 | 261 | 115 | 11 min | 9 min |
| `OAI.Probability.ProjectionMoments.Main` | 15 | 2,248 | 1,253 | 403 | 12 min | 11 min |
| `OAI.MathematicalPhysics.NavierStokes.BalancedTransport.MainResult` | 14 | 917 | 751 | 270 | 13 min | 11 min |
| Total | 151 | 9,310 | 5,989 | 2,754 | | |

The frame, step and gap counts come from `leanglish reading-kpis` with renderer
`source-math-en/0.7.0` (commit `bbc90ac`) on the downloaded snapshots, grouped
by the `module` of each shard report. A later renderer changes the step and gap
counts; the checked frames do not change. The gap step share is 0.46 and the
gap frame share is 0.48. No pilot reading is free of gaps. By rule, the gap
steps are 1,334 library citations, 508 project citations, 239 instance-fact
groups, 201 rewrites, 166 restatements, 129 automation summaries, 87 unchecked
calculations and 90 others. Library lemmas are the largest gap category in
these supporting lemmas, unlike the documented targets, where project citations
dominate. When the pilot ran, renderer `source-math-en/0.5.0` gave 6,212
displayed steps and 2,654 gap steps for the same snapshots.

The two time columns come from the run's job records: a job's time runs from
its start to its completion, and the step is "Build this environment module
once and extract every planned lemma". Both are rounded to the minute. The rest
of each job restores the original source (42 to 70 seconds) and sets up the
runner and the Lean toolchain.

These are unsigned retained observations, and they do not count toward the 536
documented targets. The catalog preview includes them as supporting lemma
readings; see [Entering the catalog](#entering-the-catalog).

## Running the campaign

The workflow `.github/workflows/dependency-cone.yml` runs on pushes to
`claude/keen-archimedes-ihorkq` that change the workflow or
`benchmarks/dependency-cone/`, and on `workflow_dispatch`. A push always runs
the pilot, because a push has no inputs. The scopes are:

- `pilot` (default): the 8 pilot shards.
- `full-1`, then `full-2`: all 379 shards in two dispatches.

The full scopes can be started only by a dispatch, and no dispatch has been
tested. GitHub's documentation states that a workflow must be in the default
branch for the `workflow_dispatch` event to trigger it. `main`, the default
branch, does not contain `dependency-cone.yml`. GitHub has registered the file
(workflow 390162521) from its push run, but on 2026-10-20 the Actions API listed
no `workflow_dispatch` run of any workflow in this repository. The documented
route is to put `dependency-cone.yml` on `main` first and then dispatch it, for
example with `gh workflow run dependency-cone.yml --ref BRANCH -f scope=full-1`,
where `BRANCH` holds the version to run. A dispatch of the file from a branch
other than `main` is untested until a run records it; see
[Dispatch](../.github/workflow-archive/README.md#dispatch).

Each run has four jobs:

1. `plan` runs the synthetic tests, re-derives the committed plan from the pinned
   archive, extracts the original plan and environment audit, and emits the matrix.
2. `preflight` checks the external inputs once, before any shard starts. It
   fails with an error message, and no shard runs, if the source artifact is
   missing, expired or not the pinned artifact, or if the dependency route does
   not reproduce the pinned environment audit. See [External inputs](#external-inputs).
3. `extract` runs one job per shard with `max-parallel: 8` and a 225-minute
   timeout, the same per-job limits as the original-environment theorem campaign.
   It reuses that campaign's machinery: the `complete-openai-lean-source` artifact,
   `unpack_source`, the pinned dependency tree, `audit_environment` before and
   after, `lake build <module>`, and `extract_narrative` with the campaign budgets
   (3,600 s build, 900 s per extraction, 2,000,000 heartbeats, 12,000 s wall
   clock).
4. `summary` reconciles every planned lemma and uploads
   `dependency-cone-summary.json`.

Every shard uploads `dependency-cone-<shard id>` with its report, build log,
dependency logs and the retained output of each attempted lemma, including
failures. The extraction step also runs after an earlier step fails, so a
missing source archive or dependency tree is recorded in the shard report. The
workflow has read-only permissions. It never publishes, releases or pushes, and
it never saves a cache.

### External inputs

Each shard needs two inputs that are not in this repository.

- **Original source.** The artifact `complete-openai-lean-source` (artifact
  12012738377) of run 38822475057. An artifact is downloadable by run ID from any
  branch. GitHub deletes it on 2026-11-14 (its recorded `expires_at`). After that
  date the preflight fails until a new source bundle is pinned.
- **Dependency tree.** The 42 pinned dependencies, with Mathlib's build cache and
  the compatibility patches applied. The theorem campaign restored them from the
  Actions cache `original-openai-deps-1581d4cb-4341-full-v1`. That cache was
  saved by `full-original-project.yml` on `work/full-original-project`. GitHub
  restores a cache only from the run's own branch, the default branch (`main`)
  or, for a pull request, its base branch. The recovery campaign ran as a pull
  request into `work/full-original-project`. Its one run on a push to another
  branch (run 39352981910) stopped at the cache step. A run on
  `claude/keen-archimedes-ihorkq` cannot restore that cache.

The preflight looks up the cache in the run's own scope without downloading it.
On a hit, every shard restores the cache (route `cache`). On a miss, the shards
re-create the tree with the commands of the seed job that built the cache:
`lake update` (2,400 s budget), then `lake exe cache get` (900 s budget). This is
route `resolve`. The preflight first runs this route once and requires the
resulting environment audit to equal the pinned audit, so a moved upstream
reference fails once instead of in every shard. In run 39141760623 the seed
job's two commands took under four minutes together. No job
saves a cache, because a second copy of a multi-gigabyte cache could evict the
pinned one that other campaigns restore.

The route does not change what is accepted. On either route a shard must pass
`audit_environment` before and after extraction with a result equal to the
pinned audit. The shard report records the route, and on route `resolve` it
keeps both command logs.

The same steps run locally, with `--trust-project`, on an isolated machine:

```sh
python scripts/plan_dependency_cone.py inputs --archive /tmp/release.zip --output /tmp/cone
python scripts/plan_dependency_cone.py matrix --scope pilot
python scripts/plan_dependency_cone.py run --project /tmp/original-project/lean \
  --original-plan /tmp/cone/original-plan.json --environment /tmp/cone/environment.json \
  --shard 55b304b716a214a3517ae6a5 --dependencies resolve --output /tmp/shards/one --trust-project
python scripts/plan_dependency_cone.py reconcile --environment /tmp/cone/environment.json \
  --scope pilot --shards /tmp/shards --output /tmp/cone-summary.json
```

Pass `--dependencies cache` instead when `.lake/packages` already holds the
pinned tree. The `dependencies` mode runs the preflight's resolution check alone.

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
| `environment-invalidated` | The lemma was read, but the shard then failed, for example because the closing environment audit differed. The success is withdrawn. |
| `not-attempted` | The shard stopped before this lemma, for example because the dependency tree was missing. |
| `extracting` | The shard failed while this lemma was being extracted. It was never read. |

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
- The report records a dependency route. On route `resolve`, both seed-command
  logs exist, match their recorded hashes and record exit code 0.
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

A catalog includes cone readings as **supporting lemma readings**, a separate
denominator. The catalog builder (`leanglish catalog --cone DIR`) and the
catalog preview (`scripts/rerender_catalog.py --cone-shards DIR`) take a
campaign directory with the layout that the workflow's `summary` job downloads:
`dependency-cone-plan/` (`plan.json`, `original-plan.json`, `environment.json`)
and one directory per shard. `scripts/download_cone_artifacts.py` writes this
layout from a workflow run. Both commands also take `--cone-scope` (default
`pilot`) and `--cone-summary FILE`. The code is in `proofreader/cone_catalog.py`.

### Acceptance

A campaign directory is used only if all of these hold. Otherwise the build
stops before any reading is rendered; the catalog builder has then written
nothing.

- The directory contains no symbolic link, and `dependency-cone-plan/` holds the
  three files.
- `validate_plan` and `bind_original` accept the plan with that original plan and
  environment audit. In a preview, both also equal the catalog's own
  `original-evidence/plan.json` and `original-evidence/environment.json`.
- The plan's 492 readings are exactly the catalog's readings: the same
  identifiers, modules, theorems and snapshot hashes. A plan derived from other
  readings is rejected.
- `reconcile` accepts every shard for the scope, with every check in
  [Loader checks](#loader-checks). With `--cone-summary`, the reconciled summary
  must equal that campaign summary.
- No accepted lemma has the name of a target reading, and the catalog's bundled
  source of each environment module has the hash that the plan records.

### Pages and records

Each accepted reading is rendered from its snapshot by the current renderer and
written to `cone/<id>/`, where `<id>` is the lemma identifier from the shard
report. The reading embeds the context that the worker supplied,
`import <environment module>`, as `Context.lean`, and its provenance note names
the environment module. Its `snapshot.json`, `receipt.json`, `run.json`,
`stdout.txt` and `Extract.lean` are the bytes of the shard artifact. A reading
that fails to render is listed with its error and is not a link target; in a
preview, any such failure stops the build.

- `coverage.json` has a `dependency_cone` section with the scope, the plan
  denominator, the outcome counts of every planned lemma, the checked frames and
  explicit explanation gaps of the bundled readings, the citation-link counts and
  the flags `counts_toward_documented_target_coverage`,
  `english_formally_certified` and `observations_authenticated`, all `false`.
- `coverage.html` has a separate table body that starts with **Supporting lemma
  readings (dependency cone, level 1)**, for example "151 of 1,722 planned; pilot
  scope", followed by the plan denominator, each recorded outcome, the shards, the
  frames and the gaps. The theorem-target rows do not change.
- `evidence/dependency-cone-summary.json` is the reconciled summary: the outcome
  of every planned lemma, including lemmas outside the run's scope.
- A finding page whose target readings cite supporting lemma readings lists them
  under **Supporting lemma readings**, with the citing targets, checked frames and
  explicit explanation gaps.

The theorem-target counts, the explanation-gap inventory (`explanations.html`,
`explanation-gaps.json`) and the reading KPIs cover the target readings only.

### Citation links

A cited name links to a supporting lemma reading when the reading's environment
module is the citing module or is reachable from it through recorded import
headers. The citing environment then contains the environment in which the lemma
was read, and an environment holds one constant per name, so the cited name is
that constant. Without this evidence the name keeps its source line or its
recorded reason.

The order of precedence is a visible documented-target reading of the name, then
a visible supporting lemma reading, then a declaration line in bundled source.
The plan never plans a name that has a target reading, so the first rule never
has to choose between the two kinds. A supporting lemma link has the form
`../../cone/<id>/reader.html`, carries `denominator: dependency-cone-level-1`,
and keeps the declaration line as `source` when the index has one. Supporting
lemma readings link to target readings (`../../proofs/<id>/reader.html`), to each
other and to source lines by the same rule, with the environment module as the
citing module.

`coverage.json` counts these links apart from links to target readings:
`citation_links.project_names.linked_to_cone_reading` and
`citation_links.citations.linked_to_cone_reading` for the target readings, and
`dependency_cone.from_target_readings` and `dependency_cone.citation_links` for
the links of the supporting readings themselves.

### Static audit

`proofreader.catalog_audit` covers the supporting lemma pages as follows:

- Every local link and anchor on them, as on every page.
- Their citation data islands: each equals `links.json` and passes link
  validation.
- Every reading link reaches a reader page of the same Lean name, in `proofs/`
  for a target link and in `cone/` for a supporting lemma link.
- The `dependency_cone` section reconciles with the outcome record, the reader
  inventory and the number of supporting lemma links from target readings.
- Each reading names a lemma in the record's `reading_index`, under the canonical
  identifier, with the recorded snapshot hash and the `Context.lean` import of its
  environment module.
- Each reading is regenerated from its snapshot (`check_reading`), and each reader
  page is regenerated from its reading and links. The frame and gap totals equal
  the section.

### Pilot readings in the preview

The catalog-preview workflow run
[39456773394](https://github.com/KyleJKistner/LeanDigest/actions/runs/39456773394)
at commit `bbc90ac` (renderer `source-math-en/0.7.0`, clean tracked tree)
built a preview of the pinned release `leanglish-original-project-317dc31` with
the artifacts of run 39373979494, which `scripts/download_cone_artifacts.py`
downloaded with matching digests. Its `catalog-preview-diagnostics` artifact
(SHA-256 `3878dc00…`, matching the API) records the following. A local build of
the same application code with the same inputs gave the same counts.

| Measure | Count |
| --- | ---: |
| Supporting lemma readings bundled | 151 of 1,722 planned (pilot scope) |
| Checked frames | 9,310 |
| Explicit explanation gaps | 2,754 |
| Readings without explanation gaps | 0 |
| Citations in target readings newly linked to a supporting lemma reading | 153 |
| … distinct cited names | 151 |
| … target readings with such a link | 12 |
| … that previously linked only to a source line | 6 |
| … that were previously unresolved (132 not in the declaration index, 15 Lean auxiliary names) | 147 |
| Citations between supporting lemma readings | 49 |
| Finding pages that list supporting lemma readings | 6 |
| Evidence files byte-identical to the shard artifacts | 755 |

Every one of the 153 citing pairs is in the environment module of the cited
lemma, so the `same-module` rule decides all of them. No citation in a
supporting reading links to a target reading, and 6 link only to a source line.

The reconciled outcomes equal the campaign summary. The static audit passed and
checked 1,433 pages, including the 151 supporting lemma pages and 202
supporting lemma links. Real Chromium file navigation passed in the workflow
run, including a finding page's supporting lemma list, a supporting lemma
reader page and a target reader's link to it. The target readings' gap steps,
frames inside gaps and gap counts by rule equal
`benchmarks/reading-kpis/current.json`. The first local measurement, at commit
`171ab5e` with renderer 0.6.0, gave the same link counts and 2,649 explicit
explanation gaps.

Two local builds of the `bbc90ac` application code, with and without the
supporting readings, compare as follows. The supporting readings add 1,662
files to the site, which grows from 629.8 MB to 738.3 MB; the preview zip grows
from 52.6 MB to 60.6 MB (the workflow run's site has 738.3 MB and its zip
60.6 MB). Every other difference is in the 492 target `links.json` files and
their reader pages, `coverage.json`, `coverage.html`, the pages that carry the
preview notice, and the preview records. In `links.json` only the 153 newly
linked entries change, and the per-reading `counts` gain a `cone-reading` key.

These readings are unsigned observations from one CI run. A link to a
supporting lemma reading does not mean that the citation is explained or
checked, and no English fidelity is claimed.

## Limitations

- **Level 1 only.** The plan covers constants that the 492 retained readings
  cite. Lemmas cited by cone readings form level 2. Level 2 is planned from level-1
  readings by the same rules, after level-1 results exist.
- **Pilot only.** One workflow run (39373979494) read the 8 pilot shards; 1,571
  planned lemmas are outside its scope. No Lean toolchain ran locally. Apart from
  that run's artifacts, the planner, worker, loader and catalog code are tested
  only with synthetic fixtures.
- **Name-based exclusions.** The constructor and compiler rules, and the
  instance hint, are conventions. The exporter does not record whether an
  accepted constant is a theorem, a proof-valued definition, an instance or a
  projection; a reading states only that the declaration is proof-valued and
  kernel checked.
- **Private names.** The two private lemmas cannot be addressed by the current
  exporter.
- **External inputs.** The source artifact of run 38822475057 expires on
  2026-11-14, and the 11 artifacts of pilot run 39373979494, which hold the only
  copy of the 151 pilot readings, expire on 2027-01-18. Outside the cache's
  branch scope, each shard spends a few minutes
  re-creating the dependency tree. Route `resolve` relies on `lake update`
  resolving to the pinned revisions. The preflight checks this once per run, and
  every shard checks it again with the environment audit. In the pilot run both
  checks passed.
- **Trust.** The trust boundary of [Source-bound mathematical reading](NARRATIVE.md)
  applies unchanged. Shard artifacts are unsigned observations. The checks
  establish consistency, not authenticity, and no English fidelity is claimed.
