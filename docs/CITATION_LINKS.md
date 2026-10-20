# Citation links

A reading records the exact Lean name of each constant it applies, in
`Step.references` and `Declaration.dependencies`. In a catalog, each cited name
links to one of the following, in order:

1. A bundled proof reading of the same constant: `../<id>/reader.html`.
2. Its declaration line on a bundled source page: `../../sources/<page>#L<n>`.

Otherwise the name stays plain text marked unresolved, with the reason recorded.

The bundled source pages are the solution modules of the comparison
configurations and the cited dependency modules described below.

## Declaration index

`proofreader/declaration_index.py` reads the bundled modules lexically; it does
not elaborate Lean. It tracks `namespace`, `section`, `end` and `mutual`
scopes; declaration modifiers and attributes; explicitly qualified and `_root_`
names; nested comments, string and character literals, and syntax quotations.
Private declarations are recorded under Lean's mangled name.

The index records a full name only when it was read without guessing:

- A name declared in more than one bundled module is listed as ambiguous. It is
  linked only from a reading whose module can see exactly one of those
  declarations.
- A module with an unmatched `end` or unbalanced brackets contributes no names.
- Anonymous instances, `example`, quoted identifiers, structure projections,
  constructors and other generated names are not indexed.

Line numbers follow `str.splitlines()`, the numbering used by the source pages.

## When a link is attached

Lean forbids two declarations with one name in a single environment. A link is
attached only when the target module is the citing module or is reachable from
it through recorded import headers, and the target is the only indexed
declaration of that name so reachable. The cited name then denotes the target
constant. The recorded import headers are those of the bundled modules and the
header-only records (`header_imports` in the declaration index) of upstream
modules that the builder read while following imports.

Each link records its `basis`:

| Basis | Meaning |
| --- | --- |
| `same-module` | The target is in the citing module. |
| `imported-bundled-module` | An import path through bundled modules reaches the target. |
| `imported-via-recorded-headers` | Every import path to the target passes through a module that the index does not cover and whose import header was recorded. |

The reasons for an unresolved citation are checked in this order:

| Reason | Meaning |
| --- | --- |
| `ambiguous-in-bundled-source` | More than one bundled declaration of this name is visible from the citing module. |
| `not-visibly-imported` | A bundled declaration or reading has this name, but the recorded import headers do not show it is the cited constant. |
| `this-reading` | The theorem of the citing reading, which does not link to itself, and no bundled source line is indexed for it. |
| `compiler-generated-auxiliary` | The name has the form of a Lean auxiliary, such as `_proof_1` or `match_1`, which has no source declaration. |
| `not-in-declaration-index` | No bundled reading has this name and the lexical index records no declaration of it. |

`not-in-declaration-index` does not mean that no bundled module declares the
constant. It covers names from Mathlib and unbundled modules, but also names that
Lean generates from a bundled declaration, such as constructors, structure
fields, automatically named instances and `_simp_N` auxiliaries, and declarations
the index skipped.

## Cited dependency sources

Many cited project lemmas are declared in modules that a solution module
imports. The catalog build bundles those modules, not the whole upstream tree:

1. It collects the cited names of every rendered reading, from the same
   document that `write_bundle` renders.
2. From the solution modules of those readings, it follows import headers
   breadth-first through `OAI.*` modules, resolving `OAI.A.B` to
   `lean/OAI/A/B.lean`. A file's imports come from its header
   (`header_imports`), never from its body. Imports outside `OAI.` are counted
   and not followed. The walk visits a module when it tries to read the
   module's file; the solution modules are already read and are not counted.
3. It scans a visited module with the declaration indexer only when the text
   after its imports, with comments and literals masked, contains every
   component of a cited `OAI.*` name as an identifier. A declaration that the
   indexer records spells each component of its name there, so the filter skips
   no declaration that the indexer would find. A private name is searched by
   the name after Lean's `_private.<module>.0.` prefix. Cited names outside
   `OAI.` or with a quoted component are not searched.
4. It selects a module when, for some reading, the module holds the only
   declaration of a cited name that the reading's solution module can see.

A selected module is bundled like a solution module: an exact source page with
line anchors and the file's SHA-256, and an exact copy under `originals/`.
The page header reads **Cited dependency source**. The page lists the cited
names that the index locates in the module and an import path from a citing
solution module. The static audit counts these pages and checks that each
recorded module has its page and that its original copy has the recorded hash.
The release manifest (`SHA256SUMS.json`) covers every file of the site,
including these pages.

### Source verification

When a source inventory is supplied, every file that the walk reads must match
its inventory hash. A file that is absent from the inventory or differs from it
is recorded as `unverified-source`. Its header is not followed and it is never
bundled. Without an inventory, the record states `source_hashes_checked: false`.

### Records

`evidence/cited-dependency-sources.json`
(`leanglish.cited-dependency-sources/v1`) records the caps and counts; every
module that could not be used, with its reason; every module that failed to
index; the citing modules whose closure is incomplete; each bundled dependency
module with its hash, cited names and import path; and the final status of every
cited name. A name's final status is its best link, its unresolved reason if it
has no link, its search outcome, and whether every citing module's closure was
complete. `coverage.json` repeats the counts under `cited_dependency_sources`.

The declaration index keeps the header records only of modules on some import
path from a citing solution module to a bundled module. Removing the other
records changes no link.

| Module not used | Meaning |
| --- | --- |
| `missing-file` | The import names a module with no file in the upstream tree. |
| `unverified-source` | The file is absent from the source inventory or has a different hash. |
| `unreadable-source` | The file is not UTF-8 text. |
| `unreadable-header` | The header has an unterminated comment or an import that the reader does not parse, such as two module names after one `import`. |
| `unsupported-module-name` | The name is not a sequence of unquoted identifiers, so it has no file path. |
| `path-outside-tree` | The module's file path resolves outside the upstream tree, for example through a symbolic link. |
| `not-visited-cap` | A walk cap was reached before the module was read. |

A citing module that imports such a module, directly or through visited
modules, has an incomplete closure. Its cited names carry
`import_closure_complete: false`.

| Search outcome | Meaning |
| --- | --- |
| `declared-in-solution-module` | The only visible declaration is in a bundled solution module. |
| `declared-in-cited-dependency` | The only visible declaration is in a bundled dependency module. |
| `dropped-by-selection-cap` | The only visible declaration is in a module that a selection cap left out. |
| `ambiguous-in-visible-modules` | A citing module can see more than one declaration of the name. |
| `declared-only-in-modules-not-imported` | Visited or solution modules declare the name, but no citing module imports them. |
| `outside-searched-namespace` | The name is outside `OAI.` or has a quoted component, so it was not searched, and no visible solution module declares it. |
| `candidate-module-not-indexed` | A visited module or a solution module spells the name but failed to index. |
| `parent-type-in-bundled-source` | The conditions of `not-declared-in-visited-modules` hold, and the name without its last component is a structure, class or inductive type in a bundled module that a citing module imports. Lean generates fields, constructors and some instance names from such declarations; the index does not record them, and no link is made. |
| `not-declared-in-visited-modules` | No indexed solution module and no visited module that the walk could use declares the name. A module that could not be used is not searched; when one is in a citing module's closure, `import_closure_complete` is false. |

### Caps

| Cap | Default | Bound |
| --- | ---: | --- |
| `max_visited_modules` | 100,000 | Modules visited by the walk. |
| `max_read_bytes` | 1,200,000,000 | Bytes read by the walk. The bound is checked before each read, so the last module read can cross it. |
| `max_seconds` | None | Wall-clock time of the walk. It is opt-in, because whether it is reached depends on the machine. |
| `max_selected_modules` | 3,000 | Dependency modules bundled. |
| `max_selected_bytes` | 40,000,000 | Source bytes of the dependency modules bundled. |

`leanglish catalog --dependency-caps '{"max_selected_modules": 100}'` overrides
a cap. Each value is a non-negative integer, except that `max_seconds` can also
be `null` or a non-integer number. The command rejects an unknown cap or an
invalid value before it writes any output. When a walk cap is reached, the walk
reads no further modules and records the rest as `not-visited-cap`. A selection
cap keeps the modules that resolve the most cited names, then orders by module
name, and records the others as dropped. Each cap that is reached is printed
once to standard error and listed in `caps_hit`, in `coverage.json` and on the
coverage page.

## Storage and checks

Links are not part of the checked reading. `write_bundle(..., links=...)` writes
`links.json` beside `reading.json` and embeds the same data in a separate
`proofreader-links` script element. `reading.json`, `reading_binding` and
`check_reading` are unchanged by links. The reader accepts only relative
reading and source-line targets.

The catalog build indexes the bundled modules once, writes
`evidence/declaration-index.json` and `evidence/cited-dependency-sources.json`,
and adds `citation_links` and `cited_dependency_sources` summaries to
`coverage.json`. Name counts use the best link from any citing reading; citation
counts keep every reading-and-name pair, with unresolved citations by reason and
links by basis. `audit-catalog` checks that each embedded island equals
`links.json`, that it passes the writer's validation, and that every target file
and line anchor exists. It does not recompute the links from the declaration
index. The gap inventory regenerates every reader page with its links.

## Limitations

A link locates an exact Lean name. It does not mean the citation is explained,
checked, or faithfully rendered in English. The lexical index assumes the bundled
source is the source Lean compiled; the catalog verifies source hashes but does
not elaborate them here. Import paths are read from headers, not from a Lean
build.

A local rebuild of the 492 published readings, using the published bundled
modules, indexed 7,438 names in 413 modules with no failed module and no ambiguous
name. Of the 1,762 distinct cited `OAI.*` names, the index records 346 as
declared in a bundled module. 30 link to a proof reading, 320 only to a source line, and 1,412 stay
unresolved: 1,302 are not in the declaration index, 109 have the form of Lean
auxiliaries, and 1 is not visibly imported. These counts describe the solution
modules alone. 25 readings link to another reading. This was a local
measurement, not a published catalog.

## Local measurement of cited dependency sources

These local runs read upstream files fetched from the pinned commit
(`raw.githubusercontent.com`) into a scratch tree. The fetched copies of the
388 solution modules with readings equal the bundled originals of the published
0.4.1 catalog; the other 25 solution modules were copied from that catalog. No
upstream source inventory was available locally. The build below
used an inventory computed from the fetched files themselves, which exercises
the verification code but does not authenticate the files.

The sample run used the 20 solution modules whose readings had the most
`not-in-declaration-index` project citations: 38 readings. It called the walk,
selection, index and link functions directly. The closures had 3,115 modules
(28.5 MB). The run selected 150 dependency modules with 2.0 MB of source,
7.1 MB including their pages and copies. Of the 312 cited `OAI.*` names that
were `not-in-declaration-index`, 261 link to a source line and 51 stay
unresolved.

The full build ran `finding_catalog.build` and `audit-catalog` on all 492
retained readings of the published catalog, with the comparison configurations
and scope notes of the pinned commit and without statement shards. The same
inputs were also built with the code before this change. The walk started from
the 388 solution modules with readings, read 65,265 modules (579.7 MB), scanned
1,649 of them, and found no unusable module and no incomplete closure. The build
selected 873 dependency modules with 10.2 MB of source. No cap was reached, and
the static audit passed.

| Cited `OAI.*` names (1,762) | Solution modules only | With cited dependencies |
| --- | ---: | ---: |
| Linked to a proof reading | 30 | 31 |
| Linked only to a source line | 320 | 1,526 |
| `compiler-generated-auxiliary` | 109 | 109 |
| `not-in-declaration-index` | 1,302 | 96 |
| `not-visibly-imported` | 1 | 0 |

Of the 96 names that stay `not-in-declaration-index`, 50 are
`parent-type-in-bundled-source`, and 46 are `not-declared-in-visited-modules`.
These 46 are 12 automatically named instances (`inst…`), 2 `casesOn` recursors
and 32 other names. For each of the 32, a text search of the fetched tree finds
a `structure` or `class` with the short name of its parent in a module that is
not bundled. Project citations, which
count each reading-and-name pair, linked to a source line rose from 328 to
1,638. Of the 1,669 linked project citations, 654 have the basis
`imported-via-recorded-headers`. Readings that link to another reading rose
from 25 to 26. Each of the 1,671 source-line links in the
built site, including those attached to reading links, points to a line that
contains the last component of the cited name. Real Chromium followed five of
these links by `file://` navigation to the declaration lines.

| Local build | Before | After |
| --- | ---: | ---: |
| Build time on the local machine | 119 s | 252 s |
| Static audit time | 17 s | 26 s |
| Source pages | 413 | 1,286 |
| Site size | 589.1 MB | 631.0 MB |
| `evidence/declaration-index.json` | 1.3 MB | 5.9 MB |
| `evidence/cited-dependency-sources.json` | None | 1.2 MB |
| Deterministic release-style zip | 40.6 MB | 49.8 MB |

The local site has no statement records or original-project evidence, so it is
smaller than the published archive (49.1 MB). Adding the same dependency files
to that archive would add an estimated 9 MB. This is an estimate, not a
measurement of a published catalog.
