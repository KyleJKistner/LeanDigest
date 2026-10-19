# Agent and supervisor contract

**No independent coding agents ran during this release.** These are executable
handoff packages for an environment with an actual agent provider. A file named
AGENTS.md does not itself launch agents or establish independent review.

## Editorial conventions

Read `docs/STYLE.md` before writing headings, labels, documentation, or summaries.
Use the Google developer documentation style guide as the general reference,
with the mathematical conventions in that file taking precedence. Headings name
content; they do not praise the explanation. Edit companion titles in
`docs/companion/headings.json` and regenerate the page. Do not paraphrase
certified mathematical text or alter source/evidence records for a style edit.

## Shared invariants

Read `docs/TRUST.md` and `docs/ACCEPTANCE.md` first. Never equate source parsing,
raw-term replay, English fidelity, readability or paper correspondence. Do not
turn missing toolchains, failed builds, unsupported constructs, truncated trees,
admissions or empty inventories into passed coverage. The source-path and typed-judgement checker now exists; its live evidence
is limited to the recorded examples. The English gate remains red until the
output interpretation is established, not merely deterministic regeneration. Do not invent experiment results, agent identities or run logs.

Four bounded roles are specified in `agents/tasks.json`: extractor, reader,
corpus and audit. The supervisor owns schemas, cross-component integration,
final acceptance, release ledger and packaging. Agents propose schema changes;
they do not silently change shared meaning. The audit role writes falsifiers and
reports rather than patching the system under evaluation.

## Prepare context without running anything

```sh
python scripts/team.py --output .agent-runs/first
```

Each task receives selected file contents, acceptance criteria, blockers and the
required return format. These context packets reduce repeated whole-repository
reading and can be used in independent sessions.

## Optional real dispatch

Install and configure your chosen coding-agent executable separately. Supply a
JSON array of its actual command arguments containing `{prompt}` and optionally
`{worktree}`. Review `--help` and run the preparation step first. Then explicitly
pass `--execute --command-json '...'` from a clean committed Git checkout.

The launcher creates one branch/worktree per task, dispatches at most four
bounded processes, captures output, and reports changed paths and ownership
violations. It never auto-merges or pushes. It is not a security sandbox: external
agents can execute code, use credentials, or reach outside a worktree according
to their provider's settings. Only run on appropriately isolated infrastructure.

## Required agent return

Return `SUMMARY.md` in the worktree with:
- Changed files and the smallest substantive result.
- Exact commands run, exit codes and artifact paths.
- Unrun checks and genuine blockers.
- Newly discovered fallbacks, counterexamples and trust-boundary changes.
- Suggested follow-up task requiring the least additional context.

The supervisor must inspect diffs, rerun integration and adversarial tests, and
reconcile source/coverage ledgers before merging. A confident narrative is not
an acceptance result. Tests used only with synthetic fixtures must be labelled.
