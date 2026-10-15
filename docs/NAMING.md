# Leanglish: name and compatibility

The product is **Leanglish**: Lean proofs, in mathematical English.
The repository remains `KyleJKistner/LeanDigest`; it has not been renamed.

## Commands

After `python -m pip install .`, either `leanglish` or `proofreader` invokes the
same parser and command implementations. From a checkout, both
`python -m leanglish` and `python -m proofreader` work. The new command shows its
own name in help and error messages; it does not bypass execution or remote
submission consent. The version remains 0.3.0 for this branding-only change.

The distribution name stays `lean-proofreader` and the implementation package
stays `proofreader`. Existing output filenames and `proofreader.*` JSON schema
identifiers remain unchanged. No migration of saved proofs is needed.

## Scope of the change

The header, page title, server identification, current documentation and command
help use Leanglish. Rebuilt demo library titles use Leanglish. Saved theorem
names, statements, proof expressions, source hashes, receipts, certificates,
and historical experiment reports are not relabelled or silently changed.
Deterministically generated reader pages are rebuilt from the same records.
This is a naming change, not a new mathematical verification claim.
