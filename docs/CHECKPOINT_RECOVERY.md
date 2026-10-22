# Compilation checkpoint recovery

## Observed failure

The NuclearUltrapower worker in run `39315174445` stopped at
2026-10-19T20:32:15Z. Job `118274980446` reported exit code 143 and a runner
shutdown signal. This observation does not establish a Lean kernel failure or
its underlying infrastructure cause.

Target: `OAI.Analysis.NuclearUltrapower.Main`.
Worker ID: `142c3d0f555a25666bb36dd1`.
Original recovery application head:
`4f9c1e823dd65023cfa7d8b9afe5e08390b8d2ad`.

The first compilation checkpoint had already been uploaded. The second
compilation stage stopped without a final proof report. The interrupted task
therefore remains outstanding; its cached files are not accepted as a proof.

## Independently executed restoration

A fresh runner restored that actual checkpoint successfully:

- Run: https://github.com/KyleJKistner/LeanDigest/actions/runs/39319564118
- Job: `118289786572`.
- Application head: `f6931795f8462193046372e8a6dd49383ec0366c`.
- Completed at 2026-10-19T20:33:56Z.
- Retained result artifact: `12220215487`, `original-checkpoint-cold-restore`.
- Result artifact SHA-256:
  `77957752ebfe865169987ec14ae1bdc1547ed27774d2fed31d17e676c5e5d1b2`.

The executed check restored **246 changed or new compiled files** into a fresh
seed containing **133,826 files**. It checked the exact resulting inventory of
**134,067 files**, rechecked all original source files and the **42 pinned and
patched dependencies**, and retained a successful result.

The counts concern build files, not theorems. The resulting record explicitly
states `proof_verified: false` and `new_lean_build_executed: false`. Subsequent
proof and comparison commands are still required.

Checkpoint artifact: `12217614568`,
`checkpoint-142c3d0f555a25666bb36dd1-1`.
Outer ZIP SHA-256:
`f0cb3658f6edbffc2e62cd8f538ea9a7529a0e4cbe4e27286241030441003523`.
Inner checkpoint SHA-256:
`87f52a446dfcdf14117bc864299782ccda1d81945483b5b6c3037cb8b76d8eb9`.
Original plan SHA-256:
`ea348a626b8653eaa75ddb05fcddb3fc754ce28fcc165f21f919d41adcc021e8`.
Original dependency-environment SHA-256:
`6e52b93542a77825d49e6cd40956a93ef6bf264e835a13e4ab2638990725807b`.

An earlier push-triggered restore attempt, run `39318853096`, could not access
the original base branch's dependency cache. The successful test ran in the PR's
base-branch cache scope. Neither attempt changed the original source or relaxed
the dependency audit.

## Native continuation

A separate continuation is executing the stopped worker's task:

https://github.com/KyleJKistner/LeanDigest/actions/runs/39321225048

Its application head is
`b717efc98e0cde96181c493b982814b2cdaa9394`, not the older matrix head.
The continuation checks that the earlier worker stopped, verifies the independent
restore gate, restores and audits the saved files again, and then continues in
bounded ten-minute stages. Each stage saves a new cumulative checkpoint before
the next one. Original proof extraction and Comparator execution remain separate
final steps.

As last observed at 2026-10-19T20:56:44Z, this continuation was still executing.
No new theorem or comparison acceptance is recorded here. The larger recovery
matrix remains independent and was not canceled or restarted.

## Combining accepted results

`completion_results.check_collection` requires explicit run, source revision and
workflow identity. The resumed workflow additionally requires its recorded
parent checkpoint and stopped-worker identity. It cannot be relabeled as the
original execution.

`completion_sets.gather` accepts at most eight explicitly identified frozen
collections and rejects two snapshots of the same execution. It preserves each
worker's provenance and the intersection of missing worker reports. It does not
itself accept a proof.

`scripts/assemble_completion_readings.py` accepts a `--continuations` JSON file.
Each entry must contain `root`, `run_id`, `source_commit`, and `workflow_path`.
The assembler invokes the original native-report validators and source-bound
proof loaders before adding any result to the catalog. Previous snapshots and
environment scopes are not upgraded. Previous failed attempts remain in the
record. Unsupported duplicate proof-worker results fail rather than being
silently selected.

The public checkpoint remains 492/536 readings, 341/416 original comparisons,
and 15/25 libraries until a newly collected and checked delivery establishes
otherwise. See COMPLETION_RECOVERY.md for the published release and its evidence.
