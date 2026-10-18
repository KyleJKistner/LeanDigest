# Independent audit workstream summary

## Changed files and result

- `tests/audit/test_retained_reader_regressions.py`: exact-release regressions
  for oversaturated conjunction projection, standalone text labeling, original
  snapshot identity, complete frame ownership, and a branch-scope control.
- `tests/audit/test_logical_rule_adversarial.py`: 87 independent synthetic tests
  for logical direction, connective scope, compact notation, argument inventory,
  paths, and frame preservation.
- `tests/audit/fixtures/`: two unchanged retained snapshots, provenance hashes,
  and a statement of their evidentiary limits.
- `tests/audit/inspect_release.py`: read-only full-frozen-release measurements.
- `docs/SWARM_READER_AUDIT.md`: findings, observed outcomes, and limits.

No production files or remote GitHub state were changed by this workstream.

## Commands and results

Working directory for baseline commands:
`/workspace/scratch/fc6359c47bd2/leandigest-audit`.
Interpreter:
`/workspace/scratch/fc6359c47bd2/leandigest-env/bin/python`.

1. `python -m pytest tests/audit/test_retained_reader_regressions.py -q`:
   exit 1; 7 failures expose the old reader, 2 controls pass.
2. `python -m pytest tests/audit/test_logical_rule_adversarial.py -q` before
   adding the nine compact-connective cases: exit 1; 19 failed, 59 passed.
3. `python tests/audit/inspect_release.py
   /workspace/scratch/fc6359c47bd2/leanglish-v0.4.1/Leanglish`: exit 0;
   216 snapshots, 9,272 frames, 3,005 gaps, eight projection false passes,
   216 standalone text marker mismatches.
4. From `/workspace/scratch/fc6359c47bd2/leandigest-logical`,
   `python -m pytest
   /workspace/scratch/fc6359c47bd2/leandigest-audit/tests/audit -q`:
   exit 0; all 96 tests passed.
5. Imported the audit inspection function after loading the candidate reader:
   exit 0; 216 snapshots, 9,272 frames, 3,001 gaps, no unmarked oversaturated
   projection and no plain-text marker mismatches.

Candidate reader file SHA-256:
`bd2e056fe00f6cfd71216261c107faf59d6fc026a825b0e191d2515938fd63eb`.

## Falsifiers and trust boundaries

The two published-reader defects are incomplete explanations of conjunction
projections subsequently applied to further arguments, and missing gap/trust
labels in `proof.txt`. During review of new rules, compact `¬P∧Q` was incorrectly
treated like `¬(P∧Q)`; the logical-explanations agent reproduced and fixed this.
Native Lean, authentication, original-project/Comparator execution, and formal
English meaning are not tested here. No human comprehension result is claimed.

## Integration and follow-up

Cherry-pick these tests with the logical-explanations production commit; they
intentionally fail against the old reader and have no `xfail` suppression. Rerun
the full integrated suite. The supervisor should preserve separate counts for
new explanations and newly exposed gaps. The earlier independent exact-DAG
layout checker is useful complementary work and has been referred to the
supervisor for recovery.

## Inventory and gap-report follow-up

`inspect_release.py` now reconciles coverage, saved comparison configurations,
exact snapshot/reading identities, frame ownership/counts, and saved gap totals.
Its report records current and saved printer versions separately and supplies a
structured byte-hash inventory. Optional `--verify-manifest` validates the exact
saved `SHA256SUMS.json` inventory without claiming publisher authentication.
The source corpus is never modified.

Added 20 tests in `test_release_inventory.py`, four independent gap-report
falsifiers in `test_gap_report_integrity.py`, and a clearly synthetic shared
fixture in `conftest.py`. Missing reader pages, an erased theorem denominator,
specification/solution confusion, and differing saved source text now all cause
the supervisor's report to reject the input.

Executed from `/workspace/scratch/fc6359c47bd2/leandigest-swarm` with the same
interpreter: `python -m pytest
/workspace/scratch/fc6359c47bd2/leandigest-audit/tests/audit -q`; exit 0,
**120 passed**. The strengthened full-corpus inspector also exited 0 with
manifest verification: all 4,809 entries matched; 416 configurations, 536
targets, 216 readings, 320 unavailable, 9,272 frames, 3,005 saved gaps versus
3,001 current gaps. Source inventory SHA-256:
`807e661eb7d5e4c5f7fa67e1a6e6b3c18b401e16f8c48f3eb5a36c048f4564bc`.
Current printer still identifies itself as `source-math-en/0.4.1`; the supervisor
was notified that the changed implementation requires a distinct release
identity. Native Lean and mathematical interpretation remain unrun in these
accounting checks.

## Selected theorem and architecture review

Added a complete independent mathematical audit of
`OAI.ComplexCancellation.BezoutFrame.exists_frame` to
`docs/SWARM_READER_AUDIT.md`: every hypothesis, zero-gcd case, both nonzero
cancellations, extended Euclidean coefficients, witness order, all four scalar
equations, arbitrary-characteristic scope, and exact source/frame correspondence.
No mathematical defect was found. The audit prefers this supporting theorem for
the demonstrator over the shorter, valid elementary entropy helper, and explains
why neither should be presented as a headline result.

Confirmed the original proof body is unchanged in the adapted context. Original
source file SHA-256 is
`d108afa98f200bfce183b8afc0af586b70734f7ad2cce1bc5e49853a2f555c6f`;
the retained snapshot's canonical digest is
`dad8ef23a231904f37b73979f8284ea3662ffe8f8cd30c79066856f2095b4dd7`.
`python -m proofreader check-narrative proofreader/data/bezout-snapshot.json
artifacts/v0.3/bezout-reader/reading.json --certificates
artifacts/v0.3/bezout-reader/polynomial-certificates.json` exited 0 from the
supervisor's worktree: deterministic regeneration and 16 supplied polynomial
certificates passed. No native Lean rerun or imported receipt authentication was
performed. The saved receipt explicitly excludes exact original-project replay.

The architectural critique distinguishes semantic soundness, original-proof
correspondence, displayed-text meaning, coverage, relevance, and usefulness. A
controlled-language soundness theorem needs a typed interpretation and a checked
text bridge; it cannot certify arbitrary pretty strings or subjective usefulness.
Raw source occurrence checking remains separate because Lean proof irrelevance
does not identify the original proof. Prototype review was pending at that
checkpoint; its completed outcome is recorded in the following section.

## Completed controlled-language and native evidence follow-up

New `lean/ControlledEnglishAudit.lean` was explicitly assigned to this audit
lane by the supervisor. It proves six independent countermodels and includes
positive scope, exact right-disjunction extraction, malformed token, atom-bound,
and unsupported-prose controls. It imports the production prototype instead of
copying its semantics. Reviewed the prototype and both architecture documents;
no substantive semantic escape or guarantee overstatement was found after the
supervisor corrected ambiguous corpus-wide acceptance wording.

Executed the local Lean 4.34.1 binary on
`leandigest-logical/lean/ControlledEnglish.lean` with
`-o /tmp/ControlledEnglish.olean`, then from this worktree's `lean/` directory
ran `LEAN_PATH=/tmp /workspace/scratch/fc6359c47bd2/lean-4.34.1-linux/bin/lean
ControlledEnglishAudit.lean`. Both final commands exited 0 without warnings.
The toolchain directory required the environment's reviewed elevated access.
The independent audit contains no admissions; printed axiom dependencies are
limited to the standard `propext`, `Classical.choice`, and `Quot.sound`.

The bounded old/fresh Bézout snapshot comparison is retained as
`tests/audit/bezout-native-comparison.json`. All 86 frame structures, paths,
premises, and mathematical formulas are identical; only three binder display
renamings, their context labels, and six printed instance references change.
The complete records agree after those exact substitutions. Fresh canonical
digest is `e93e0455259fc3283983f3a47f956cdac4b1a28869bc5027bcc694b4a124d8d0`.
This comparison did not run native extraction and does not turn the failed
historical exact comparison into a successful replay.

`test_companion_failure_state.py` exposes a prior passed observation surviving a
new failed project preflight. It failed before the supervisor's correction and
passed afterward. It performs only local file and Git checks, never Lean or
network access. The native checker also now binds the original source digest and
the packaged fresh snapshot; these production changes remain supervisor-owned.

## Final companion review

Reviewed the completed reader-navigation companion's actual HTML/template,
source ranges, fresh snapshot frame grouping, complete algebra, matrix placement,
scope/evidence language, and integer examples. No mathematical or correspondence
blocker was found. A copied-evidence alteration to the deterministic reading,
with its manifest digest recomputed, was correctly rejected by the builder's
regeneration check. The theorem/proof line count was corrected to 34: original
source lines 11 through 44 inclusive, excluding a trailing blank line.

Final integrated Python command from the supervisor's worktree:
`python -m pytest /workspace/scratch/fc6359c47bd2/leandigest-audit/tests/audit -q`;
exit 0, **121 passed**. Final independent Lean audit also exited 0 without
warnings. Browser and visual verification belongs to reader-navigation;
full original-project replay and Comparator remain with the concurrent Pro
session. All requested audit work is complete, with no production or remote
changes by this workstream.
