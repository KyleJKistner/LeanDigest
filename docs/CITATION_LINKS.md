# Citation links

A reading records the exact Lean name of each constant it applies, in
`Step.references` and `Declaration.dependencies`. In a catalog, each cited name
links to one of the following, in order:

1. A bundled proof reading of the same constant: `../<id>/reader.html`.
2. When the catalog includes supporting lemma readings (dependency cone), a
   supporting lemma reading of the same constant: `../../cone/<id>/reader.html`.
   The link carries `denominator: dependency-cone-level-1`. See
   [Entering the catalog](DEPENDENCY_CONE.md#entering-the-catalog).
3. Its declaration line on a bundled source page: `../../sources/<page>#L<n>`.

Otherwise the name stays plain text marked unresolved, with the reason recorded.
A supporting lemma reader page in `cone/<id>/` links a target reading as
`../../proofs/<id>/reader.html`; every other form is the same.

The bundled source pages are the solution modules of the comparison
configurations and the cited dependency modules described below.

## Declaration index

`proofreader/declaration_index.py` reads the bundled modules lexically; it does
not elaborate Lean. It tracks `namespace`, `section`, `end` and `mutual`
scopes; declaration modifiers and attributes; explicitly qualified and `_root_`
names; comments, string and character literals, escaped identifiers (`«…»`)
and syntax quotations. Private declarations are recorded under Lean's mangled
name. In a file that uses Lean's module system, a declaration outside
`public section` that is not marked `public` is private as well, as Lean's
`Visibility.isInferredPublic` decides, and is recorded under its mangled name.

The lexical rules are those of the Lean 4 lexer of the pinned toolchain
(v4.34.1):

- Identifier characters are those of `isIdFirst` and `isIdRest` in
  `Init/Meta/Defs.lean`: ASCII letters and digits, `_`, `'`, `!`, `?`, the
  letter-like ranges, which include `℘` and `ℝ`, and subscripts. Python's `\w`
  class is not used: it rejects `℘` and accepts Cyrillic letters.
- A block comment, including a doc comment (`/--` or `/-!`), nests from its
  fourth character, so `/--/` does not close it.
- An escaped identifier part `«…»` ends at the first `»`, on any line.
- A character literal or a raw string opens only at the start of a token.
- Nothing after `#exit` is read.

The index records a full name only when it was read without guessing:

- A name declared in more than one bundled module is listed as ambiguous. It is
  linked only from a reading whose module can see exactly one of those
  declarations.
- A module with an unmatched `end`, unbalanced brackets, or an import that is
  not one readable module name contributes no names.
- So does a module whose lexical reading depends on the grammar or on commands
  the index does not model: a string literal that ends at a different place
  when Lean reads it as an interpolated string (`s!"{"a"}"`, a notation token
  such as `"∂_{"`, or a plain `"{"` followed by other string literals), or a
  `with_weak_namespace` command, which sets the namespace of the command it
  contains. When only one reading of a string closes, that reading is used.
- Anonymous instances, `example`, quoted identifiers, structure projections,
  constructors and other generated names are not indexed.

Line numbers follow `str.splitlines()`, the numbering used by the source pages.

These rules were compared with those of commit `f787dae` by scanning every
`.lean` file of the fetched project tree described below and of Mathlib at the
pinned commit (`d13f23b`) with `declaration_index.scan` and `header_imports`.
For the 65,678 project files, the declarations, imports, skipped headers and
header imports are the same. Of the 8,529 Mathlib files, 96 now record some
declarations under private names: in 90 by the module-system default, and in 6
because a `meta` modifier after `private` no longer drops it. Another 29
Mathlib files are refused because a string literal ends at a different place
when read as an interpolated string. The first such literal is, in 19 files, an
interpolated string whose braces contain another string literal, such as
`s!"{stdText "-/"}"` in `Mathlib/Tactic/Linter/Header.lean`; in 6, a notation
or syntax token such as `"∂_{"`; and in 4, a plain string value such as `"{"`.
Mathlib modules are not indexed by the catalog.

## When a link is attached

Lean forbids two declarations with one name in a single environment. A link is
attached only when the target module is the citing module or is reachable from
it through recorded import headers, and the target is the only indexed
declaration of that name so reachable. The cited name then denotes the target
constant. The recorded import headers are those of the bundled modules and the
header-only records (`header_imports` in the declaration index) of upstream
modules that the builder read while following imports.

An import is recorded only when it puts the imported declarations into the
environment of every module that imports the importer. In a file that uses
Lean's module system (its header starts with `module`), that is a `public`
import; an import without `public`, and any `meta` import, is not recorded.
Leaving out an edge never attaches a wrong link, because every declaration that
stays reachable is in the citing module's environment. Of the upstream files
fetched for the local build described below, two use the module system, and
neither imports an `OAI.` module.

A link to a reading or a source line records its `module` and `basis`. The
module is the one whose environment fixes the constant: for a source line, the declaring module; for a
proof reading, the reading's solution module; for a supporting lemma reading,
its environment module. The basis says how the citing module reaches it:

| Basis | Meaning |
| --- | --- |
| `same-module` | The link's module is the citing module. |
| `imported-bundled-module` | An import path through bundled modules reaches the link's module. |
| `imported-via-recorded-headers` | Every import path to the link's module passes through a module that the index does not cover and whose import header was recorded. |

A reading's theorem can be declared in a module that the reading's module
imports. A reading link keeps the declaration line as `source` when the index
locates the one visible declaration, and that entry records its own `module`
and `basis`. In the full build below, 5 reading links have the basis
`same-module` and a `source` entry in another module: 2 with the basis
`imported-bundled-module` and 3 with `imported-via-recorded-headers`. The
`linked_by_import_basis` counts in `coverage.json` use the link's own basis.

The reasons for an unresolved citation are checked in this order:

| Reason | Meaning |
| --- | --- |
| `ambiguous-in-bundled-source` | More than one bundled declaration of this name is visible from the citing module. |
| `not-visibly-imported` | A bundled declaration or reading has this name, but the recorded import headers do not show it is the cited constant. |
| `this-reading` | The theorem of the citing reading, which does not link to itself, and no bundled source line is indexed for it. |
| `compiler-generated-auxiliary` | The name has the form of a Lean auxiliary, which has no source declaration: its last component is `_proof`, `proof` or `match` followed by one or more numeric suffixes, such as `_proof_1`, `_proof_1_3` or `match_1_1`. |
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
modules, has an incomplete closure. So does a citing module whose closure has
an `OAI.` import that is not recorded because a module-system file does not
re-export it (`import-not-re-exported`; the record lists these imports under
`imports_not_followed`). The walk does not follow such an import, not even
one in the citing module itself. The cited names of a citing module with an
incomplete closure carry `import_closure_complete: false`.

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
and line anchor exists. Each reading link must reach a reader page of the same
Lean name in its own denominator (`proofs/` or `cone/`). It does not recompute
the links from the declaration index. The gap inventory regenerates every target
reader page with its links, and the audit regenerates every supporting lemma
reader page.

## Limitations

A link locates an exact Lean name. It does not mean the citation is explained,
checked, or faithfully rendered in English. The lexical index assumes the bundled
source is the source Lean compiled; the catalog verifies source hashes but does
not elaborate them here. Import paths are read from headers, not from a Lean
build.

The index does not know the tokens that notation and syntax declarations add to
Lean's lexer, or commands that a project defines. A new token that contained a
comment or literal opener would be read differently, and a project command that
declares names or changes the namespace would be missed. A text search of the
one-line notation, syntax and macro declarations of Mathlib at the pinned commit
found no token that contains `--`, `/-` or `«`.

The 492 published readings were linked at commit `a9e98ba` against the
bundled solution modules of the published 0.4.1 catalog alone, as
`scripts/rerender_catalog.py` links them: one index of the 413 modules in
`originals/`, then `citation_links` for each reading as `write_bundle` renders
it. The index has 7,438 names, no failed module and no ambiguous name. Of the
1,762 distinct cited `OAI.*` names, it records 346 as declared in a bundled
module. 30 link to a proof reading, 320 only to a source line, and 1,412 stay
unresolved: 1,302 are not in the declaration index, 109 have the form of Lean
auxiliaries, and 1 is not visibly imported. 25 readings link to another
reading. With the 151 supporting lemma readings of the dependency-cone pilot
(run 39373979494), 151 of these names link to a supporting lemma reading; a
preview built at `a9e98ba` with `scripts/rerender_catalog.py --cone-shards`
passed the static audit. The counts and every link are the same at commit
`f787dae`, except that a reading link's `source` entry now has a `basis`. This
was a local measurement, not a published catalog.

## Local measurement of cited dependency sources

These local runs read upstream files fetched from the pinned commit
(`raw.githubusercontent.com`) into a scratch tree. The fetched copies of the
388 solution modules with readings equal the bundled originals of the published
0.4.1 catalog; the other 25 solution modules were copied from that catalog. No
upstream source inventory was available locally. The build below
used an inventory computed from the fetched files themselves, which exercises
the verification code but does not authenticate the files.

The sample run, recorded with commit `cbcc712`, used the 20 solution modules
whose readings had the most
`not-in-declaration-index` project citations: 38 readings. It called the walk,
selection, index and link functions directly. The closures had 3,115 modules
(28.5 MB). The run selected 150 dependency modules with 2.0 MB of source,
7.1 MB including their pages and copies. Of the 312 cited `OAI.*` names that
were `not-in-declaration-index`, 261 link to a source line and 51 stay
unresolved.

The full build ran `finding_catalog.build` and `audit-catalog` on all 492
retained readings of the published catalog, with the comparison configurations
and scope notes of the pinned commit and without statement shards, at commit
`a9e98ba`. The same inputs were also built at commit `4c072f1`, the parent of
`cbcc712`, which added cited dependency sources. At `a9e98ba` the walk started
from the 388 solution modules with readings, read 65,265 modules (579.7 MB),
scanned 1,649 of them, and found no unusable module and no incomplete closure.
The build selected 873 dependency modules with 10.2 MB of source. No cap was
reached, and the static audit passed. The walk, the selection and every link
are the same at commit `f787dae`, except for the `basis` of `source` entries.

| Cited `OAI.*` names (1,762) | Solution modules only | With cited dependencies |
| --- | ---: | ---: |
| Linked to a proof reading | 30 | 31 |
| Linked only to a source line | 320 | 1,526 |
| `compiler-generated-auxiliary` | 109 | 109 |
| `not-in-declaration-index` | 1,302 | 96 |
| `not-visibly-imported` | 1 | 0 |

The first column is the `4c072f1` build; the solution-only linking at
`a9e98ba` described under [Limitations](#limitations) gives the same counts.
Of the 96 names that stay `not-in-declaration-index`, 50 are
`parent-type-in-bundled-source`, and 46 are `not-declared-in-visited-modules`.
These 46 are 12 automatically named instances (`inst…`), 2 `casesOn` recursors
and 32 other names. For each of the 32, a text search of the fetched tree finds
a `structure` or `class` with the short name of its parent in a module that is
not bundled. Project citations, which count each reading-and-name pair, linked
to a source line rose from 328 to 1,638. Of the 1,669 linked project
citations, 654 have the basis `imported-via-recorded-headers`. Readings that
link to another reading rose from 25 to 26. Each of the 1,671 source-line links
in the built site, including those attached to reading links, points to a line
that contains the last component of the cited name. Real Chromium, opening the
pages by `file://`, followed four source-line links, which cover all three
bases, to their declaration lines, and one link to a proof reading.

| Local build | `4c072f1` | `a9e98ba` |
| --- | ---: | ---: |
| Build time on the local machine | 112 s | 239 s |
| Static audit time | 15 s | 26 s |
| Source pages | 413 | 1,286 |
| Site size | 589.1 MB | 619.7 MB |
| `evidence/declaration-index.json` | 1.3 MB | 5.9 MB |
| `evidence/cited-dependency-sources.json` | None | 1.2 MB |
| Deterministic release-style zip | 40.6 MB | 49.8 MB |

Sizes are in units of 10^6 bytes. The two commits also differ in the renderer
and the reader script, so not all of the difference comes from cited
dependencies. In the `a9e98ba` build, the 873 cited dependency source pages
take 25.5 MB and their copies under `originals/` 10.2 MB.

To repeat a build, fetch the pinned upstream tree into `UPSTREAM`, put the
retained reading directories of the published catalog under `INPUTS/proofs`,
leave `INPUTS/statements` empty, write the source inventory of the fetched
files to `INPUTS/source-inventory.json`, and check out the commit:

```sh
leanglish catalog --upstream UPSTREAM --lean UPSTREAM/lean --statements INPUTS/statements \
    --proofs INPUTS/proofs --source-inventory INPUTS/source-inventory.json --output SITE
leanglish audit-catalog SITE
```

The zip is `deterministic_zip(SITE, ZIP)` from
`scripts/assemble_finding_release.py`. The build times depend on the machine.

The local site has no statement records or original-project evidence, so it is
smaller than the published archive (49.1 MB). Adding the same dependency files
to that archive would add an estimated 9 MB. This is an estimate, not a
measurement of a published catalog.
