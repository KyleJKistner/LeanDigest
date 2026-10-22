# Reviewing explanation gaps

The offline reader can move directly between steps marked `fallback` in the
reading document. **Next gap** and **Previous gap** follow declaration order and
then the displayed proof tree in preorder. They open any collapsed ancestors,
select the correct proof, highlight the step, and show its attached source and
local context. The controls also appear inside the inspector, so they remain
available when inspecting a long proof or using a narrow screen.

The queue contains only declarations matching the library's current search and
filter. Search matches declaration names, paths, statements, and author notes.
The declaration list's display cap does not truncate the review queue: a proof
selected through a gap or deep link remains visible in that list. Navigation
stops at each end of the queue; it does not silently wrap.

The position `Gap 3 of 12` identifies a location in the current queue. It is not a
count of reviewed, corrected, verified, or certified steps. The per-proof count
reports steps explicitly marked as unexpanded. Neither visiting every gap nor
having no flagged gaps establishes a complete explanation. Existing proof,
receipt, axiom, and English-fidelity labels remain independent.

## Inspecting a step

The inspector identifies the full declaration name and hierarchical step number,
for example `1.2.1`. It separates the **recorded claim** from **exact step source**.
When no source string is attached, the claim is not substituted and presented as
source text. Local assumptions are shown exactly as attached to that step;
missing local-context metadata is labelled as missing rather than interpreted
as an empty mathematical assumption set.

**Full declaration source** switches to the source tab while retaining the
selected step. Closing the inspector retains the selected step and the queue
position. Reopening or following a link shows the same attached data. This
display does not authenticate metadata or infer missing derivations.

## Links and browser history

Links to embedded reading data use URL query parameters. Encode values with a
standard URL encoder, particularly when identifiers contain spaces, Unicode,
slashes, question marks, or ampersands.

| Parameter | Meaning | Default |
| --- | --- | --- |
| `declaration` | Exact declaration `id` in the reading document | First matching declaration |
| `step` | Exact step `id` within that declaration | Statement view |
| `tab` | `reading`, `source`, or `audit` | `reading` |
| `q` | Library search text | Empty |
| `filter` | `all`, `gaps`, or `typed` | `all` |

A catalog can link to a step using
`reader.html?declaration=<encoded-id>&step=<encoded-step-id>`. The reader opens
the inspector and expands the step's ancestors. **Link to this step** exposes
the current URL for copying or bookmarking, including the current tab, search,
and filter. Unrelated query parameters are preserved. Old
`reader.html#<encoded-declaration-id>` links still work and are converted to the
query form.

Explicit proof, step, filter, and tab changes create browser-history entries.
Typing in search replaces the current entry so each keystroke does not become a
separate Back operation. Reload, Back, and Forward restore the proof, selected
step, search, filter, and tab. A missing step is reported and does not select a
same-named step in a different proof. A linked declaration excluded by a saved
search or filter is reported rather than reintroduced into the queue.

Step identifiers must be unique **within a declaration**; declaration identifiers
must be unique within a reading document. Reusing a step identifier in another
proof is supported. Browser imports with ambiguous identifiers are rejected
without replacing the currently open document.

### Reading files opened after page load

A JSON or Lean file opened through **Open proof file** exists only in that tab;
the original HTML does not contain it. The reader therefore hides the shareable
step link and leaves the embedded document's URL intact while reviewing the
imported file. A note explains this limitation. To produce working links, export
the imported reading as JSON and render a new self-contained HTML file:

```sh
leanglish read proofreader.document.json -o reader.html
```

This command reads the document and writes HTML without compiling Lean. Open
that HTML and navigate to the desired step. The link refers to that same HTML
file; it does not upload or host a local file for another person.

## Keyboard access

All review controls are native buttons. Inspecting a step or using gap navigation
focuses the inspector heading; Escape returns focus to the selected step's
inspection button when the Argument tab is active. The source and evidence tabs
support Left/Right, Home, and End with one active tab in the normal Tab sequence.
The gap position is announced through a status region. No single-key shortcut
intercepts typing in the search box.

## Verification scope

`tests/reader/test_reader_navigation.py` covers real Chromium interactions against
explicitly synthetic navigation fixtures and retained shipped reading records.
It checks nested expansion, cross-proof scope, search/filter boundaries, queue
ends, legacy and query links, URL reload/history, absent or ambiguous targets,
keyboard focus, source/claim separation, imported-file limitations, and mobile
layout. The fixture asserts that the offline reader makes no HTTP(S) requests.
These are software interaction checks, not new Lean observations or an English
fidelity/comprehension study.

```sh
PROOFREADER_REQUIRE_BROWSER=1 python -m pytest \
  tests/test_browser.py tests/reader/test_reader_navigation.py -q
```
