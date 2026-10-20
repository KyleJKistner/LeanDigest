"""Scope and printed-form checks added in source-math-en/0.7.0; Narrative inherits them.

Scope. A displayed proof that begins with a binder step (Let, Assume, Set,
Take, "Establish …; call this fact h", "From … obtain", "Since …, choose")
continues to the end of its list: the binder's scope is the rest of that list.
Where the proofs of several premises, conjuncts, calculation links or cases
share one list, each proof of more than one step is therefore nested under its
own step "Prove S." (S is the recorded statement of the premise), and
``require_scopes`` refuses any reading in which a binder's scope reaches a step
outside it. These container steps own no snapshot frame.

Printed form. A sentence that depends on a premise or a calculation link being
printed in a particular form compares the recorded strings; when they differ
the step keeps an explanation gap. One unfolding is allowed in the comparison:
a local definition that the reading displays as "Set x = v." and whose body
contains the step may be replaced by its value, with parentheses where Lean's
precedence needs them. Formulas with binders are never unfolded.
"""
from __future__ import annotations
import itertools
import re

from .formula_surface import _FORMULA_GROUPS, _formula_text, _outer, _plain_proposition, _same_formula
from .kernel import require
from .model import Step

# Lean precedence of the spaced infix operators read here (Init/Core, Init/Prelude, Mathlib).
_PRECEDENCE = {'↔': 20, '→': 25, '∨': 30, '∧': 35, '=': 50, '≠': 50, '<': 50, '>': 50, '≤': 50, '≥': 50,
               '∈': 50, '∉': 50, '⊆': 50, '⊂': 50, '⊇': 50, '⊃': 50, '∣': 50, '+': 65, '-': 65,
               '::': 67, '*': 70, '/': 70, '%': 70, '^': 75}
# Outer operator characters of a value (formula_surface._outer) whose precedence is known.
_VALUE_PRECEDENCE = {**{k: v for k, v in _PRECEDENCE.items() if len(k) == 1}, '·': 70, '×': 35, '¬': 40}
# Any binding construct: a name inside it may be bound, so nothing there is substituted.
_BINDERS = re.compile(r"[∀∃λ∑∏⋃⋂⨆⨅∫∮|]|↦|=>|(?<![\w.'])(?:fun|let|have|match|show|do)(?![\w'])")
_WHOLE_BINDER = re.compile(r"[∀∃λ|]|↦|=>|(?:fun|let|have|match|show|do)(?![\w'])")
# Binders whose names bound_names collects; integrals, tsums, a.e. quantifiers and let/have bind too.
_BINDER_START = re.compile(r"(?:∀ᶠ|∃ᶠ|∀ᵐ|∃ᵐ|∃!|∑'|∏'|∑ᶠ|∏ᶠ|∫⁻|[∀∃λ∑∏⋃⋂⨆⨅∫∮]|(?<![\w.'])(?:fun|let|have)(?![\w']))(?= )")
_IDENT = re.compile(r"[^\W\d][\w'!?₀-₉✝⁰-⁹]*(?:\.[^\W\d][\w'!?₀-₉]*)*")
_ATOM = re.compile(r"[^\W\d][\w'!?₀-₉✝⁰-⁹.]*|\d+|\[\]")
# The relations a calculation link may be written with.
_RELATIONS = set('=≠<>≤≥⊆⊂⊇⊃∣≃≅≡')
# Roles whose last child is proved under the binder (for a witness: the property of the value).
SCOPED = frozenset({'introduce', 'assume', 'have', 'define', 'witness'})


def _word(name: str) -> re.Pattern:
    return re.compile(r"(?<![\w.'!?₀-₉✝⁰-⁹])" + re.escape(name) + r"(?![\w'!?₀-₉✝⁰-⁹.])")


def _closing(text: str, k: int) -> int | None:
    """Index of the bracket closing the one opened at k."""
    depth = 0
    for m in range(k, len(text)):
        if text[m] in _FORMULA_GROUPS:
            depth += 1
        elif text[m] in _FORMULA_GROUPS.values():
            depth -= 1
            if depth == 0:
                return m
    return None


def _symbols(text: str) -> list[str]:
    """Space-separated tokens outside brackets that are infix operators.

    A token is an operand when it begins with a letter, digit or bracket, or
    with a prefix operator attached to its operand (↑x, -x, ¬p, ‖x‖); any
    other token (=, +, •, ⁻¹', ⬝ᵥ, ++ …) is an infix operator.
    """
    depth, token, out = 0, '', []
    for c in text+' ':
        depth += (c in _FORMULA_GROUPS) - (c in _FORMULA_GROUPS.values())
        if depth == 0 and c == ' ':
            first = token[:1]
            if first and not (first.isalnum() or first in _FORMULA_GROUPS or first in "_'"
                              or (first in '↑¬-√‖|⌊⌈!' and len(token) > 1)):
                out.append(token)
            token = ''
        else:
            token += c
    return out


def _value_precedence(value: str) -> int | None:
    """2000 for an atom or a bracketed group, 1024 for an application, else its outer operator's precedence.

    None when an infix operator outside brackets has no known precedence
    (•, ∪, ++, '' …): such a value is never treated as an application.
    """
    if _ATOM.fullmatch(value) or (value[0] in _FORMULA_GROUPS and _closing(value, 0) == len(value)-1):
        return 2000
    outer = _outer(value)
    if outer is None or 'keyword' in outer[1] or not outer[1] <= set(_VALUE_PRECEDENCE):
        return None
    infix = _symbols(outer[0])
    if not set(infix) <= set(_VALUE_PRECEDENCE):
        return None
    return min((_VALUE_PRECEDENCE[c] for c in outer[1] | set(infix)), default=1024)


def _neighbour(text: str, left: bool) -> int | None:
    """Precedence of the operator next to a position: -1 at a bracket, comma or the end; None otherwise."""
    if not text or (text[-1] if left else text[0]) in ('([{⟨⦃,' if left else ')]}⟩⦄,'):
        return -1
    if (text[-1] if left else text[0]) != ' ':
        return None
    rest = text[:-1] if left else text[1:]
    token = rest.rsplit(' ', 1)[-1] if left else rest.split(' ', 1)[0]
    if left and rest.endswith(','):
        return -1
    return _PRECEDENCE.get(token)


def _bare(before: str, after: str, value: str) -> bool:
    """value can replace a name here without parentheses and parse the same way."""
    p = _value_precedence(value)
    if p is None:
        return False
    if p == 2000:
        return True
    a, b = _neighbour(before, True), _neighbour(after, False)
    return a is not None and b is not None and p > a and p > b


def _replaced(t: str, found: list[tuple[int, int, str]], choices: list[list[str | None]], limit: int) -> list[str]:
    """Every combination of the choices at the found positions; beyond limit positions only the first choice.

    The first choice is the bare value where Lean prints no parentheses and the
    parenthesized value elsewhere, which is how Lean prints the substitution.
    """
    combinations = itertools.product(*choices) if len(found) <= limit else [tuple(c[0] for c in choices)]
    out = []
    for combination in combinations:
        if all(c is None for c in combination):
            continue
        pieces, last = [], 0
        for (start, end, _), c in zip(found, combination):
            pieces += [t[last:start], t[start:end] if c is None else c]
            last = end
        out.append(''.join(pieces)+t[last:])
    return out


def _options(t: str, start: int, end: int, value: str) -> list[str]:
    return [value, '('+value+')'] if _bare(t[:start], t[end:], value) else ['('+value+')']


def _substituted(text: str, values: dict[str, str], keep: bool, limit: int = 6) -> list[str]:
    """text with occurrences of the given names replaced by their values.

    Each occurrence takes the bare value where Lean would not print the
    parentheses, or the parenthesized value, or (with keep) stays. A text with
    binders is not changed: a bound occurrence would be replaced wrongly.
    """
    t = _formula_text(text)
    if t is None or _BINDERS.search(t):
        return []
    found = sorted((m.start(), m.end(), name) for name in values for m in _word(name).finditer(t))
    if not found:
        return []
    choices: list[list[str | None]] = []
    for start, end, name in found:
        v = _formula_text(values[name])
        if v is None:
            return []
        choices.append(_options(t, start, end, v)+([None] if keep else []))
    return _replaced(t, found, choices, limit)


_LEADING = re.compile(r"(∀ᶠ|∃ᶠ|∀ᵐ|∃ᵐ|∀|∃) \(([^\W\d][\w'₀-₉]*) : ")


def _outer_comma(t: str) -> int | None:
    depth = 0
    for k, c in enumerate(t):
        depth += (c in _FORMULA_GROUPS) - (c in _FORMULA_GROUPS.values())
        if depth == 0 and t[k:k+2] == ', ':
            return k
    return None


def same_reading(a: str, b: str) -> bool:
    """a and b differ only in notation a reader reads identically.

    The name of one leading bound variable (∀ᶠ (n : ℕ) in l, P n and
    ∀ᶠ (x : ℕ) in l, P x, renamed only in the body and only to a name the body
    does not use), ¬P written P → False, and a ≥ b (a > b) written b ≤ a (b < a).
    """
    from .formula_surface import _negated_operand
    if _same_formula(a, b):
        return True
    na, nb = _negated_operand(a), _negated_operand(b)
    if na is not None and nb is not None and _same_formula(na, nb):
        return True
    for x, y in ((a, b), (b, a)):
        sides = relation(x); t = _formula_text(x)
        if sides is not None and t[len(sides[0])+1] in '≥>':
            if _same_formula(sides[1]+(' ≤ ' if t[len(sides[0])+1] == '≥' else ' < ')+sides[0], y):
                return True
    ta, tb = _formula_text(a), _formula_text(b)
    ma, mb = (_LEADING.match(ta), _LEADING.match(tb)) if ta and tb else (None, None)
    if not (ma and mb and ma[1] == mb[1] and ma[2] != mb[2]):
        return False
    ka, kb = _outer_comma(ta), _outer_comma(tb)
    if ka is None or kb is None:
        return False
    x, y, body = ma[2], mb[2], ta[ka+2:]
    return (ta[:ka].replace('('+x+' : ', '('+y+' : ', 1) == tb[:kb] and not _word(y).search(body)
            and _same_formula(_word(x).sub(lambda m: y, body), tb[kb+2:]))


def bound_names(text: str) -> set[str] | None:
    """Names a binding construct may bind in text (an over-approximation), or None if unreadable."""
    names: set[str] = set()
    for m in _BINDER_START.finditer(text):
        k = m.end()
        while k < len(text):
            while k < len(text) and text[k] == ' ':
                k += 1
            if k < len(text) and text[k] in '({⦃[⟨':
                close = _closing(text, k)
                if close is None:
                    return None
                names.update(_IDENT.findall(text[k+1:close].split(' : ', 1)[0]))
                k = close+1
                continue
            word = _IDENT.match(text, k)
            if word is None:
                break
            names.add(word[0]); k = word.end()
    for m in re.finditer(r'\{([^{}|]*)\|', text):
        names.update(_IDENT.findall(m[1].split(' : ', 1)[0]))
    return names


def instance(body: str, name: str, value: str) -> list[str]:
    """Readings of body[value/name]: every occurrence replaced, none captured by a binder of body."""
    t = _formula_text(body)
    bound = bound_names(t) if t is not None else None
    if t is None or bound is None or name in bound or bound & set(_IDENT.findall(value)):
        return []
    found = [(m.start(), m.end(), name) for m in _word(name).finditer(t)]
    if value == name or not found:
        return [t]
    return _replaced(t, found, [_options(t, s, e, value) for s, e, _ in found], 6)


def motive(text: str) -> tuple[str, str] | None:
    """The binder and body of a printed motive fun x => B (also fun {x} =>, fun (x : T) =>)."""
    m = re.fullmatch(r'fun (?:([^\W\d][\w\'₀-₉]*)|[({]([^\W\d][\w\'₀-₉]*)(?: : [^(){}]+)?[)}]) =>\s+(.+)',
                     ' '.join(text.split()), re.S)
    return (m[1] or m[2], m[3]) if m else None


def relation(text: str) -> tuple[str, str] | None:
    """The two sides of a calculation link printed with one outer relation (or one outer ↔).

    A binder whose body extends to the end (∀, ∃, fun, …) outside brackets is
    refused; big operators (∑, ∏, ∫, ⋃, ⋂) bind their body tighter than a relation.
    """
    t = _formula_text(text)
    if t is None:
        return None
    depth, cuts, iff = 0, [], []
    for k, c in enumerate(t):
        if c in _FORMULA_GROUPS:
            depth += 1
        elif c in _FORMULA_GROUPS.values():
            depth -= 1
        elif depth == 0 and (_WHOLE_BINDER.match(t, k) and (k == 0 or not (t[k-1].isalnum() or t[k-1] in "_.'"))):
            return None
        elif depth == 0 and 0 < k < len(t)-1 and t[k-1] == t[k+1] == ' ':
            if c == '↔':
                iff.append(k)
            elif c in _RELATIONS:
                cuts.append(k)
            elif c in '∧∨→,':
                return None
    cut = iff if iff else cuts
    return (t[:cut[0]-1], t[cut[0]+2:]) if len(cut) == 1 else None


def forall_groups(text: str) -> tuple[list[tuple[str, str]], str] | None:
    """∀ (a : A) (b c : B), rest as [(a, A), (b, B), (c, B)] and rest; only parenthesized groups."""
    t = _formula_text(text)
    if t is None or not t.startswith('∀ ('):
        return None
    k, names = 2, []
    while k < len(t) and t[k] == '(':
        close = _closing(t, k)
        if close is None or ' : ' not in t[k+1:close]:
            return None
        head, kind = t[k+1:close].split(' : ', 1)
        names += [(n, kind) for n in head.split(' ')]
        k = close+1
        if t[k:k+2] == ', ':
            return names, t[k+2:]
        if t[k:k+1] != ' ':
            return None
        k += 1
    return None


class ReadingChecks:
    """Methods of Narrative; they use its frames, snapshot parents, sequence() and owners."""

    # --- scope -----------------------------------------------------------------

    def subproof(self, j: int, steps: list[Step]) -> Step:
        """One step holding the displayed proof of frame j, so the binders in it stay inside."""
        from .narrative import math_text
        f = self.frames[j]
        text = 'Derive False.' if _same_formula(f['statement'], 'False') else 'Prove '+math_text(f['statement'])+'.'
        return Step(self.sid(j)+':proof', 'subproof', text, evidence='source-bound-snapshot', children=steps,
                    context=f['context'], source=f['statement'],
                    detail='The steps below prove this claim. The binders they introduce are in scope only inside '
                           'this step. This step groups displayed steps; it owns no snapshot frame.')

    def joined(self, proofs: list[tuple[int, list[Step]]], after: list[Step] | None = None) -> list[Step]:
        """The displayed proofs of several premises in one list, each proof of more than one step nested.

        Only a list's last binder step may leave its scope open: when a proof
        shares the list with anything else, its steps are nested under "Prove S."
        """
        after = after or []
        if len(proofs)+len(after) < 2:
            return [s for _, steps in proofs for s in steps]+after
        return [s for j, steps in proofs for s in ([self.subproof(j, steps)] if len(steps) > 1 else steps)]+after

    def proofs(self, ids: list[int]) -> list[Step]:
        return self.joined([(j, self.sequence(j)) for j in ids])

    def case_proof(self, j: int, steps: list[Step]) -> list[Step]:
        """The proof of one recursor case, nested when it has more than one step, so a label names all of it."""
        return [self.subproof(j, steps)] if len(steps) > 1 else steps

    def require_scopes(self, steps: list[Step]) -> None:
        """No binder's displayed scope reaches a step outside it.

        A step owning a binder frame whose body it does not contain is followed,
        in its own list, by that body. Every later step of the list, with all
        its descendants, must then own only frames below the binder's body.
        """
        owned: dict[str, list[int]] = {}
        for i, sid in self.owners.items():
            owned.setdefault(sid, []).append(i)
        below: dict[int, set[int]] = {}
        frames: dict[int, set[int]] = {}

        def inner(s: Step) -> set[int]:
            if id(s) not in frames:
                frames[id(s)] = set(owned.get(s.id, ())).union(*(inner(c) for c in s.children))
            return frames[id(s)]

        def check(items: list[Step]) -> None:
            later: set[int] = set()
            for s in reversed(items):
                for b in owned.get(s.id, ()):
                    f = self.frames[b]
                    if f['role'] in SCOPED and f['children'] and f['children'][-1] not in inner(s):
                        body = f['children'][-1]
                        if body not in below:
                            below[body] = set(self.descendants(body))
                        require(later <= below[body], 'A displayed binder scope reaches a step outside it')
                later |= inner(s)
            for s in items:
                check(s.children)
        check(steps)

    # --- printed forms ---------------------------------------------------------

    def local_definitions(self, i: int) -> dict[str, str]:
        """Values of the displayed local definitions (Set x = v.) whose body contains frame i.

        Only the nearest binder of a name counts; a nearer binder of the same
        name hides the definition.
        """
        seen: set[str] = set(); values: dict[str, str] = {}; j = i
        while j in self.snapshot.parents:
            child, j = j, self.snapshot.parents[j]
            g = self.frames[j]
            if g['role'] in {'introduce', 'assume', 'have', 'define'} and child == g['children'][-1] and g['binder'] not in seen:
                seen.add(g['binder'])
                if g['role'] == 'define' and not g['budget_cut'] and '._@.' not in g['binder']:
                    values[g['binder']] = g['value']
        return values

    def printed_as(self, i: int, shown: str, expected: str) -> bool:
        """shown is printed as expected (same_reading), or is after unfolding local definitions displayed above frame i."""
        if same_reading(shown, expected):
            return True
        values = self.local_definitions(i)
        return bool(values) and (any(_same_formula(c, expected) for c in _substituted(shown, values, True))
                                 or any(_same_formula(shown, c) for c in _substituted(expected, values, True)))

    def forward_equivalence(self, i: int) -> list[Step] | None:
        """Iff.mp {a b} (h : a ↔ b) (ha : a) : b; None when its dictionary sentence applies.

        The sentence needs exact argument slots and paths, the equivalence
        printed as a ↔ b, the hypothesis as a and the conclusion as b; otherwise
        the step says so and stays a gap. Iff.mp not applied to exactly these
        two premises (unapplied, partially or further applied) is a cited
        constant, as Iff.mpr is.
        """
        from .narrative import _citation, math_text
        f = self.frames[i]; ch = f['children']
        if not self.logical_application(i, 2, [2, 3]):
            text, rule = _citation(f['head'])
            return [self.step(i, text, rule=rule, fallback=True, conclusion=math_text(f['statement']),
                              children=self.subproofs(ch))]
        if (self.equivalent(self.frames[ch[0]]['statement'], *f['objects'])
                and self.printed_as(i, self.frames[ch[1]]['statement'], f['objects'][0])
                and self.printed_as(i, f['statement'], f['objects'][1])):
            return None
        return [self.step(i, 'Apply the forward direction of the stated equivalence to the supplied hypothesis. '
                          'That the hypothesis and the conclusion have the printed forms of its two sides is not checked here.',
                          rule='unchecked-equivalence', fallback=True, conclusion=math_text(f['statement']),
                          children=self.subproofs(ch))]

    def same_assumption(self, i: int) -> bool:
        """id (fun h : A => body) h' with h' : A' and A printed as A' (or with displayed local definitions unfolded)."""
        f = self.frames[i]
        return self.printed_as(i, self.frames[f['children'][0]]['domain'], self.frames[f['children'][1]]['statement'])

    def existential(self, i: int) -> bool:
        """The premise of an Exists.casesOn choice is printed as ∃ …, or as a ∣ b with the choice giving b = a * c."""
        f = self.frames[i]; intro = self.frames[f['children'][1]]
        major = _formula_text(self.frames[f['children'][0]]['statement'])
        if major is None:
            return False
        if major.startswith('∃ '):
            return True
        sides = relation(major)
        if sides is None or major[len(sides[0])+1] != '∣':
            return False
        prop = self.frames[intro['children'][0]]['domain']
        return any(_same_formula(prop, b+' = '+a+' * '+intro['binder'])
                   for a in (sides[0], '('+sides[0]+')') for b in (sides[1], '('+sides[1]+')'))

    def conjunction_premise(self, i: int) -> bool:
        """The premise of an And.casesOn destructuring is printed as the two parts joined by ∧ (Lean precedence)."""
        f = self.frames[i]; text = self.frames[f['children'][0]]['statement']
        values = self.local_definitions(i)
        return any(self.projected(t, *f['objects'][:2])
                   for t in [text]+(_substituted(text, values, False) if values else []))

    def chained(self, i: int, leaves: list[int]) -> bool:
        """Each link ends where the next begins and the links join the two sides of the statement."""
        sides = [relation(self.frames[j]['statement']) for j in leaves]
        whole = relation(self.frames[i]['statement'])
        if whole is None or any(s is None for s in sides):
            return False
        return (self.printed_as(i, sides[0][0], whole[0]) and self.printed_as(i, sides[-1][1], whole[1])
                and all(self.printed_as(i, a[1], b[0]) for a, b in zip(sides, sides[1:])))

    def motive_cases(self, i: int, slots: list[int]) -> list[tuple[str, str | None, bool]]:
        """For each recursor case: its name, the motive instance it must prove (if read) and whether it is printed so.

        Nat.rec/recAux/recOn: P 0 and ∀ (n : ℕ), P n → P (n + 1); List.rec/recOn:
        P [] and ∀ (a : α) (l : List α), P l → P (a :: l). The motive is read
        from its printed form fun x => B and instantiated textually.
        """
        f = self.frames[i]; nat = f['head'].startswith('Nat.')
        premise = {p['argument']: p['statement'] for p in f['premises']}
        read = motive(f['objects'][0 if nat else 1])
        names = ('base case', 'successor step') if nat else ('empty-list case', 'constructor step')
        if read is None:
            return [(names[0], None, False), (names[1], None, False)]
        x, body = read
        base = [v for c in (('0', 'Nat.zero') if nat else ('[]',)) for v in instance(body, x, c)]
        cases = [(names[0], base[0] if base else None, any(_same_formula(premise[slots[0]], v) for v in base))]
        groups = forall_groups(premise[slots[1]]); step: tuple[str | None, bool] = (None, False)
        if groups is not None and len(groups[0]) == (1 if nat else 2):
            (n, kind), rest = groups[0][-1], groups[1]
            if (kind in ('ℕ', 'Nat')) if nat else kind.startswith('List '):
                prefix = '∀ '+' '.join('('+a+' : '+k+')' for a, k in groups[0])+', '
                hyps = instance(body, x, n)
                concs = instance(body, x, n+' + 1' if nat else groups[0][0][0]+' :: '+n)
                if hyps and concs:
                    outer = _outer(hyps[0])
                    shown = '('+hyps[0]+')' if outer is None or outer[1] & set('→↔∀∃,') or 'keyword' in outer[1] else hyps[0]
                    step = (prefix+shown+' → '+concs[0],
                            any(_same_formula(rest, h+' → '+c) for h in hyps+['('+h+')' for h in hyps] for c in concs))
        return cases+[(names[1],)+step]

    # --- wording ---------------------------------------------------------------

    # Instance lists print class statements as recorded, not as dictionary sentences.
    instance_gloss = False

    def definition_type(self, name: str, domain: str) -> str:
        """For a local definition with an automatic name (this, inst), whose name says nothing, the type."""
        from .narrative import _ANONYMOUS, _INSTANCE_BINDER
        return ' (of type '+domain+')' if _ANONYMOUS.fullmatch(name) or _INSTANCE_BINDER.fullmatch(name) else ''

    def introduction(self, f: dict) -> str:
        """The sentence for an inner ∀-introduction; types, propositions and instance arguments are named as such."""
        from .narrative import _INSTANCE_BINDER, _name, math_text
        name, domain = _name(f['binder']), f['domain']
        outer = _outer(domain)
        if domain == 'Prop':
            return 'Let '+name+' be an arbitrary proposition.'
        if re.match(r'(?:Type|Sort)(?![\w.])', domain) and outer is not None and not outer[1]:
            return 'Let '+name+' be an arbitrary type.'
        if _INSTANCE_BINDER.fullmatch(name) and _plain_proposition(domain) is not None:
            return 'Fix an instance of '+math_text(domain)+'.'
        return 'Let '+name+' ∈ '+math_text(domain)+' be arbitrary.'

    def function_text(self, i: int) -> str:
        """The function of a congruence step; a partially applied relation or operation, LE.le a, reads t ↦ a ≤ t.

        The new variable is the first of t, s, u, v, t₁, … that is neither in
        the frame's local context nor a name in the recorded function.
        """
        from .narrative import math_text
        value = self.frames[i]['objects'][-1]
        ops = {'LE.le': '≤', 'LT.lt': '<', 'GE.ge': '≥', 'GT.gt': '>', 'Eq': '=', 'Ne': '≠', 'HAdd.hAdd': '+',
               'HSub.hSub': '-', 'HMul.hMul': '*', 'HDiv.hDiv': '/', 'HPow.hPow': '^'}
        m = re.fullmatch(r'(\S+) (.+)', ' '.join(value.split()))
        if m is None or m[1] not in ops or _formula_text(m[2]) is None:
            return math_text(value)
        argument, depth = m[2], 0
        for c in argument:  # exactly one argument: no space outside brackets
            depth += (c in _FORMULA_GROUPS) - (c in _FORMULA_GROUPS.values())
            if depth == 0 and c == ' ':
                return math_text(value)
        if argument[0] == '(' and _closing(argument, 0) == len(argument)-1:
            p = _value_precedence(argument[1:-1])
            if p is not None and p > _PRECEDENCE[ops[m[1]]]:
                argument = argument[1:-1]
        used = set(_IDENT.findall(value)) | {c['name'] for c in self.frames[i]['context']}
        t = next(v for v in ('t', 's', 'u', 'v')+tuple('t'+chr(0x2080+k) for k in range(1, 10)) if v not in used)
        return math_text(t+' ↦ '+argument+' '+ops[m[1]]+' '+t)
