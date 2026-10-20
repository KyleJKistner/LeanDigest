# Retained reader-audit fixtures

The two snapshot files are unchanged copies from the published Leanglish v0.4.1
offline archive. `provenance.json` records exact byte hashes, original archive
locations, theorem names, and the frames used by the regressions.

These observations exercise the Python renderer. Loading them does not execute
Lean, authenticate the observations, certify English, or validate the full
original project. Their original source and receipts remain in the release.

The regression is the distinction between projecting a function or negation from
a conjunction and applying that result to further arguments. The original proof
observations are preserved; only the explanation/gap accounting is under test.
