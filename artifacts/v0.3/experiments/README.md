# Experimental programs, not release acceptance claims

`FormulaRoundtrip.lean` explores re-elaboration of pretty-printed formulas. It is
NOT a validated capability and no formula-roundtrip guarantee is claimed.
`NarrativePaths.lean` was the working independent-path variant; that same body was
subsequently compiled successfully in the exact `../bezout-4.34.1-valid.lean`
program and is now present in the packaged Narrative exporter.

Intermediate source programs elsewhere in this artifact directory record work
in progress. Only inputs whose hashes appear in `live-4.34.1-observations.json`
and `live-integrated-observation.json` have the corresponding claimed live run.
Transport checksum failures do not establish that Lean rejected those programs.
