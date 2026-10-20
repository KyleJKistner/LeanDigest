# Citation links

A reading records the exact Lean name of each constant it applies, in
`Step.references` and `Declaration.dependencies`. In a catalog, each cited name
links to one of the following, in order:

1. A bundled proof reading of the same constant: `../<id>/reader.html`.
2. Its declaration line on a bundled source page: `../../sources/<page>#L<n>`.

Otherwise the name stays plain text marked unresolved, with the reason recorded.

## Declaration index

`proofreader/declaration_index.py` reads the bundled solution modules lexically;
it does not elaborate Lean. It tracks `namespace`, `section`, `end` and `mutual`
scopes; declaration modifiers and attributes; explicitly qualified and `_root_`
names; nested comments, string and character literals, and syntax quotations.
Private declarations are recorded under Lean's mangled name.

The index records a full name only when it was read without guessing:

- A name declared in more than one bundled module is ambiguous and never linked.
- A module with an unmatched `end` or unbalanced brackets contributes no names.
- Anonymous instances, `example`, quoted identifiers, structure projections,
  constructors and other generated names are not indexed.

Line numbers follow `str.splitlines()`, the numbering used by the source pages.

## When a link is attached

Lean forbids two declarations with one name in a single environment. A link is
attached only when the target module is the citing module or is reachable from
it through the `import` headers of bundled modules, so the cited name denotes the
target constant. An import path through an unbundled module is not visible to the
builder; such a citation stays unresolved as `not-visibly-imported`.

| Reason | Meaning |
| --- | --- |
| `not-declared-in-bundled-source` | No bundled reading or declaration has this name (for example, Mathlib or an unbundled project module). |
| `ambiguous-in-bundled-source` | Several bundled declarations have this name. |
| `not-visibly-imported` | A bundled declaration or reading has this name, but the import headers do not show it is the cited constant. |
| `compiler-generated-auxiliary` | A Lean auxiliary such as `_proof_1` or `match_1`, which has no source declaration. |

## Storage and checks

Links are not part of the checked reading. `write_bundle(..., links=...)` writes
`links.json` beside `reading.json` and embeds the same data in a separate
`proofreader-links` script element. `reading.json`, `reading_binding` and
`check_reading` are unchanged by links. The reader accepts only relative
reading and source-line targets.

The catalog build indexes the bundled solution modules once, writes
`evidence/declaration-index.json`, and adds a `citation_links` summary to
`coverage.json`. Name counts use the best link from any citing reading; citation
counts keep every reading-and-name pair, with unresolved citations by reason.
`audit-catalog` checks that each embedded island equals `links.json` and that
every target file and line anchor exists. The gap inventory regenerates every
reader page with its links.

## Limitations

A link locates an exact Lean name. It does not mean the citation is explained,
checked, or faithfully rendered in English. The lexical index assumes the bundled
source is the source Lean compiled; the catalog verifies source hashes but does
not elaborate them here.

A local rebuild of the 492 published readings, using the published bundled
modules, indexed 7,438 names in 413 modules with no failed module and no ambiguous
name. Of the 1,762 distinct cited `OAI.*` names, 346 are declared in a bundled
module. 30 link to a proof reading, 320 only to a source line, and 1,412 stay
unresolved, mostly because they are declared in modules the catalog does not
bundle. 25 readings link to another reading. This was a local measurement, not a
published catalog.
