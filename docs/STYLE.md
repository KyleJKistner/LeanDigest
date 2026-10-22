# Editorial style

Use the [Google developer documentation style guide](https://developers.google.com/style)
for general writing conventions. The mathematical conventions below take
precedence where they differ. These conventions apply to page titles, headings,
interface labels, documentation, pull request descriptions, and progress reports.
They do not authorize changes to mathematical meaning or verification records.

## Headings

Name the section's subject or task. Do not describe how impressive, readable,
rigorous, complete, or useful the writing is. Remove a heading's promotional
qualifier rather than replacing it with a different compliment.

Use sentence case. Use noun phrases for reference material and verbs for
instructions. Avoid sentence-ending periods, slogans, rhetorical questions, and
numbered sequences in heading text. Proof steps may have separate numbers for
navigation. Proper names, abbreviations, and mathematical notation retain their
standard capitalization.

Use these section names where applicable: **Statement**, **Definitions and
lemmas**, **Proof**, **Examples**, **Verification**, and **Limitations**. Name
individual proof sections after their mathematical content. A count of steps is
not a reason to invent a new heading. Do not add an overline or subtitle that
repeats the heading.

| Replace | With |
| --- | --- |
| Six steps, with the algebra visible. | Proof |
| A readable argument with its record attached. | Verification |
| See the construction over the integers. | Integer examples |
| The facts the proof uses | Definitions and lemmas |
| The determinant is exactly one. | Determinant |
| Validation, with different kinds of evidence kept separate | Validation |
| Truth is not relevance | Inference alignment |

For the companion, `docs/companion/headings.json` is the editable heading
inventory. The builder uses it for the page, contents, and source inspector.
Do not independently rewrite those labels in the HTML or JavaScript. The
regression tests compare the generated headings and navigation against this
inventory. An approved heading is an editorial choice, not a theorem.

Google references: [Headings and titles](https://developers.google.com/style/headings)
and [Voice and tone](https://developers.google.com/style/tone).

## Prose and interface text

State the fact, operation, or limitation. Remove sentences that announce the
quality of the answer, advertise a future explanation, or ask the reader to be
impressed. Avoid stock transitions and repeated contrasts when ordinary
sentences convey the distinction.

Use button labels that identify the action and its object, such as **View Lean
source**. Use **Print** for the browser print action. Keep the same name for the
same section across navigation, dialogs, and documentation.

Technical terms are not forbidden words. Keep **exact sequence**, **complete
lattice**, **simply connected**, **faithful functor**, and **canonical form** when
they name mathematical concepts. Likewise, **exact integer arithmetic** describes
the calculation method rather than the quality of the prose. Do not run a global
adjective-removal pass over mathematical text.

## Mathematical writing

Use conventional proof language: “Let”, “Suppose”, “Choose”, “Since”, and
“Therefore” where they express the argument. The usual mathematical “we” is
acceptable; the preference for second person in procedural documentation does
not require rewriting proofs as user instructions.

Retain quantifiers, assumptions, domains, binder scopes, types, dependencies,
and nonzero conditions. Do not shorten a proof by dropping a hypothesis or by
calling an unproved step obvious. Distinguish explanatory commentary from the
mathematical claims on which later steps depend.

Do not paraphrase text after a certified renderer produces it. A change to a
formal sentence template requires its own semantic review and checks. Editorial
changes to site navigation and surrounding prose do not extend the renderer's
certification boundary.

## Verification language

State what was checked, by which method, and with what scope. Put the main
limitations in the verification section, with a brief nearby notice when needed
to prevent misunderstanding. Do not replace necessary qualifications with a
slogan, and do not repeat the entire disclaimer at every heading.

Report failures, skipped checks, substituted imports, unsigned observations,
and unverified English accurately. Distinguish kernel-checked theorems from
executed regression tests and editorial review. Do not treat a passing style
check as evidence that mathematics is correct or that readers find it useful.

## Review

Read the headings without the body text. Each should identify what the section
contains, without claiming a benefit or describing the author's effort. Then
check that the heading, contents entry, and inspector title agree.

Review technical meaning separately. For a heading-only revision, compare the
proof paragraphs, formula inventory, source mappings, and evidence with the
previous version. Rebuild generated pages and run the companion tests.

The automated checks cover the heading inventory, selected previously rejected
phrases, navigation consistency, and unchanged proof content. They are not an
AI-text detector or a complete implementation of Google's style guide. New prose
still requires editorial review.
