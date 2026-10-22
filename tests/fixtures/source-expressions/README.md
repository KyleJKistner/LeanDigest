# Source-expression fixtures

`records.zip` contains fourteen expression records and their lightweight snapshots,
exported from `lean/SourceExpressionsFixtures.lean` with Lean 4.34.1. The manifest
pins that source and every JSON file. These are regression inputs, not evidence
that a new checkout or compiler has passed native checking.

The native integration job of `ci.yml` regenerates these bytes, checks every
record against its original source in a fresh process, and exercises lemma
extraction and reapplication. The unit tests use the archive without running Lean.

The archive is data only. Tests read a single JSON member containing the original file
contents, without extracting paths or executing archive contents. It avoids repeating the same constructor and
context records in dozens of tracked text files. Native execution evidence stays
in the workflow artifacts, not in this fixture archive.
