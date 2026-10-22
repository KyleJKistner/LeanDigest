# Independent reading-layout check

`proofreader/layout.py` checks the exact-DAG reader's structural compression without
importing the English printer or its templates. It is run before a typed document
is returned and when `check_reading` verifies a supplied document.

A source binding is identified by its occurrence path in the original proof, not
by a printed name or a shared expression-node index. A branch-local assumption
therefore cannot become global merely because another branch reuses its name.

The pass accounts for every selected proof step, including steps moved into the
statement's parameter list. It rejects lost or duplicated steps, non-prefix
parameters, future or unrelated support links, and references outside a binding's
scope. Leading lambda binders may be presented sequentially; other local scopes
must remain nested. A closed subargument can be moved earlier with an explicit
support link. This is a conservative presentation contract, not every possible
valid way to rewrite a mathematical proof.

The tests deliberately move an assumption out of its local subargument while
leaving the supplied original proof unchanged. The independent scope pass rejects
that layout. Other falsifiers remove a subproof, promote a local binder to a
parameter, substitute a dependency, or cite a proof that has not yet been shown.
Constructed syntax fixtures are explicitly marked as such; the native integration
suite separately runs the pass over fresh Lean exports.

## Boundary

This pass does not type-check Lean terms or interpret English sentences. It can
accept structurally well-scoped text with altered wording; deterministic
regeneration is the separate wording check. Lean replay is the separate typing
check. Neither successful scope checking nor their combination is a formal proof
of the English dictionary, notation printer, or mathematical exposition quality.
The source-bound pretty-printed narrative format has a different contract; this
pass applies only to `proofreader.kernel-export/v2` exact-DAG readings.
