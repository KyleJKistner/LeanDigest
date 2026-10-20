"""Display notation for Lean pretty-printed formula strings.

Lean's pretty-printer output remains authoritative. Every displayed step keeps
its raw formula in ``Step.source``, the snapshot keeps every raw frame, and the
proof checks (``_same_formula`` and the polynomial checker) read raw strings
only. This module changes what a reader is shown, never what is checked.

Both passes are deterministic functions of one snapshot and run only inside a
reading context (``reading``); elsewhere ``display`` is the identity.

* Namespace shortening. A name is shown relative to the theorem's namespace and
  its enclosing namespaces (Lean's resolution inside ``namespace``), and
  relative to three library namespaces that the original sources open most
  often. A shortening is refused when the shown text could denote another name,
  a local binder or bound variable, or a reserved root name in that reading.
  A refused name falls back to a longer prefix, ultimately the full name.
* Structural notation for frequent library forms. A balanced-bracket tokenizer
  recognizes a form only at an application boundary with atomic arguments and
  a body of known extent. Anything else is left as printed.

``attach`` records the namespaces and notations a reading actually displays.
docs/NOTATION.md has the corpus profile and the justification of each rule.
"""
from __future__ import annotations
from collections import Counter
import contextvars
from dataclasses import dataclass, field
import functools
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

_IDENT = r"[^\W\d][\w'!?]*"
NAME = re.compile(_IDENT + r"(?:\.(?:" + _IDENT + r"|\d+))*")
_FREE = re.compile(r"(?<![\w'!?])(?<!(?<!\.)\.)" + NAME.pattern)
_TOKEN = re.compile(r'(?P<ws>\s+)|(?P<str>"(?:[^"\\]|\\.)*")|(?P<chr>\'(?:[^\'\\\n]|\\.)\')|(?P<id>'
                    + NAME.pattern + r")|(?P<num>\d+(?:\.\d+)?)|(?P<op>[∑∏]'|''|=>|:=|\.\.|<\||\|>|.)", re.S)
_OPEN = {'(': ')', '[': ']', '{': '}', '⟨': '⟩', '⦃': '⦄', '⟦': '⟧'}
_CLOSE = frozenset(_OPEN.values())
_UNMODELLED_OPS = frozenset('" \' « » `'.split())
_COMMENT = re.compile(r'--|/-|-/')
KEYWORDS = frozenset('fun λ let have show match if then else do by at from in with calc Type Sort Prop where deriving'.split())
_NO_EXTENT = frozenset('let have show match calc do by λ where deriving'.split())
_BINDERS = frozenset("∀ ∃ ∑ ∏ ∑' ∏' ∫ ∮ ⋃ ⋂ ⨆ ⨅".split())
# Lean lexes Σ and Π as tokens, not identifier letters. With the n-ary operator
# characters (∐, ∫…∳, ⨀…⨜, e.g. ⨍ ⨁ ⨂) they may open a binder whose comma
# must not be read as the end of an enclosing lambda body. ⋀ is left out: in
# Mathlib it is the exterior power ⋀[R]^n M, which takes no comma.
_BINDER_IDS = frozenset("Σ Σ' Π Π'".split())


def _nary(x: str) -> bool:
    return x in _BINDERS or (len(x) == 1 and (x == '∐' or '∫' <= x <= '∳' or '⨀' <= x <= '⨜'))


_PREFIX = frozenset('↑ ⇑ ↥'.split())
# Items that can begin a further application argument after whitespace.
_ARG_START = _PREFIX | _BINDERS | frozenset('¬ √ @ # | ‖ ⟪ ∂'.split())
# Operators binding more tightly than every relation and connective.
_ARITH = frozenset("+ - * / ^ • ∘ · − % ↑ ⇑ ↥ ⁻ | ‖ ! × '' . ∪ ∩ \\ ⊓ ⊔".split())

# Opened by at least 92 of the 413 original OAI source files each (Filter 119,
# MeasureTheory 106, Set 92); see docs/NOTATION.md. Real is opened by 8 files,
# so only its textbook functions below are written without the prefix.
LIBRARY = ('Filter', 'MeasureTheory', 'Set')
SYMBOLS = {'Real.log': 'log', 'Real.exp': 'exp', 'Real.sin': 'sin', 'Real.cos': 'cos', 'Real.tan': 'tan',
           'Real.arctan': 'arctan', 'Real.sinh': 'sinh', 'Real.cosh': 'cosh', 'Real.tanh': 'tanh',
           'Real.artanh': 'artanh', 'Real.pi': 'π', 'nhds': '𝓝'}
# A shortened name never starts with one of these: root-level Lean/Mathlib
# names and namespaces that a reader would take to be the library's own. The
# list is hand-maintained, not complete; the second line holds the root names
# that project constants of the corpus repeat (e.g. OAI.TamingCompatibility.
# IsClosed), with a few equally common library roots.
RESERVED = frozenset('''Finite Infinite Countable Nonempty Subsingleton Nontrivial Unique Inhabited IsEmpty Elem
    Field IsClosed Algebra Lattice Small Language Multiplicative Additive spectrum gradient Dense Group Monoid Ring
    CommRing Semiring Ideal Subgroup Continuous Differentiable Measurable MeasurableSet IsOpen IsCompact Convex
    Irrational Prime Even Odd Summable HasSum IsUnit Irreducible
    Mem Disjoint Pairwise Monotone Antitone StrictMono StrictAnti Injective Surjective Bijective Prod Sum Sigma
    Subtype Real Nat Int Rat Complex Set Finset Filter MeasureTheory ProbabilityTheory Function List Multiset Fin
    Fintype Matrix Polynomial MvPolynomial ENNReal NNReal EReal Metric TopologicalSpace Topology Module Submodule
    LinearMap Equiv Order Lean Mathlib Std Classical Decidable Eq Ne Iff And Or Not Exists True False id'''.split())
NOTATIONS = {  # legend key -> (shown form, Lean form)
    'lambda': ('x ↦ e', 'fun x => e'),
    'tendsto': ('e → a as x → ∞', 'Filter.Tendsto (fun x => e) Filter.atTop (nhds a); x → ∞ is Filter.atTop for the '
                'order on the type of x (eventually x ≥ b for every b; the usual limit on ℕ and ℝ), and a limit ∞ or −∞ '
                'is Filter.atTop or Filter.atBot'),
    'nhdsWithin': ('𝓝[s] a', 'nhdsWithin a s'),
    'card': ('#s', 'Finset.card s'),
    'sqrt': ('√x', 'Real.sqrt x'),
    'choose': ('(n choose k)', 'Nat.choose n k'),
}


@dataclass(frozen=True)
class Tok:
    kind: str
    text: str


@dataclass(frozen=True)
class Group:
    open: str
    items: tuple
    close: str


def tokens(text: str) -> list[Tok] | None:
    """Lex approximately like Lean; ``None`` for stray quotes, comments or guillemets.

    Closed string and character literals are single opaque tokens: names inside
    them are never shortened or parsed.
    """
    toks = [Tok(m.lastgroup or 'op', m[0]) for m in _TOKEN.finditer(text)]
    if any(t.kind == 'op' and t.text in _UNMODELLED_OPS for t in toks):
        return None
    if _COMMENT.search(''.join(' ' if t.kind in ('str', 'chr') else t.text for t in toks)):
        return None
    return toks


def parse(text: str) -> tuple | None:
    """Balanced bracket tree of the top-level items, or ``None`` when not recognized."""
    toks = tokens(text)
    if toks is None:
        return None
    stack: list[tuple[str, list]] = [('', [])]
    for t in toks:
        if t.kind == 'op' and t.text in _OPEN:
            stack.append((t.text, []))
            if len(stack) > 128:
                return None
        elif t.kind == 'op' and t.text in _CLOSE:
            opened, items = stack.pop()
            if not opened or _OPEN[opened] != t.text:
                return None
            stack[-1][1].append(Group(opened, tuple(items), t.text))
        else:
            stack[-1][1].append(t)
    return tuple(stack[0][1]) if len(stack) == 1 else None


def _prefixes(name: str) -> list[str]:
    parts = name.split('.')
    return ['.'.join(parts[:k]) for k in range(1, len(parts)+1)]


@dataclass
class Reading:
    """The display context of one reading: its name map and every word it shows."""
    theorem: str
    names: dict[str, str]
    via: dict[str, str]
    words: frozenset[str]
    ops: frozenset[str]
    cache: dict[str, str] = field(default_factory=dict)
    # Each displayed form and the legend entries it relies on.
    outputs: dict[str, frozenset[str]] = field(default_factory=dict)

    @classmethod
    def of(cls, record: dict, prepare: Any = None) -> 'Reading':
        """``prepare`` is the transformation applied before ``display`` (the
        narrative dictionary); its outputs count as displayed words, so a
        shortened name cannot look like a word it introduces, such as gcd."""
        strings: set[str] = set(); local: set[str] = set()
        for f in record['frames']:
            strings.add(f['statement']); strings.update(f['objects']); strings.add(f['head'])
            strings.update(f[k] for k in ('domain', 'value') if k in f)
            if 'binder' in f:
                local.add(f['binder'])
            for c in f['context']:
                local.add(c['name']); strings.add(c['type'])
        if prepare is not None:
            strings |= {prepare(s) for s in strings}
        return cls.build(record['theorem'], strings, local)

    @classmethod
    def build(cls, theorem: str, strings: Iterable[str], local: Iterable[str]) -> 'Reading':
        strings = set(strings)
        every = {n for s in strings for n in NAME.findall(s)}
        # A field after `(…).` is not a free name; `a..b` still binds b.
        found = {n for s in strings for n in _FREE.findall(s)}
        local = {x for b in local for x in (b, b.split('._@.', 1)[0], *NAME.findall(b))}
        found |= local
        if 'nhdsWithin' in found:  # 𝓝[s] a needs the 𝓝 symbol to be free as well
            found.add('nhds')
        parts = theorem.split('.')[:-1]
        opened = ['.'.join(parts[:k]) for k in range(len(parts), 0, -1)] + list(LIBRARY)
        options: dict[str, list[tuple[str, str]]] = {}
        for t in sorted(found - local):
            if '_@' in t or '_hyg' in t or t.split('.', 1)[0] in local:
                continue
            choice = [(SYMBOLS[t], 'sym:'+t)] if t in SYMBOLS else []
            for ns in opened:
                rest = t[len(ns)+1:]
                if t.startswith(ns+'.') and rest and not rest[0].isdigit():
                    head = rest.split('.', 1)[0]
                    if head not in KEYWORDS and head not in RESERVED:
                        choice.append((rest, 'ns:'+ns))
            if choice:
                options[t] = choice
        rank = dict.fromkeys(options, 0)
        while True:
            shown = {t: options[t][rank[t]] for t in rank if rank[t] < len(options[t])}
            owner: dict[str, set[str]] = {}
            for t in found:
                if t in shown:
                    s, key = shown[t]
                    pairs = ([(s, t)] if key.startswith('sym:') else
                             [(p, key[3:]+'.'+p) for p in _prefixes(s)])
                else:
                    pairs = [(p, p) for p in _prefixes(t)]
                for p, full in pairs:
                    owner.setdefault(p, set()).add(full)
            clash = {p for p, fulls in owner.items() if len(fulls) > 1}
            revoke = [t for t, (s, key) in shown.items()
                      if (s in clash if key.startswith('sym:') else any(p in clash for p in _prefixes(s)))]
            if not revoke:
                break
            for t in revoke:
                rank[t] += 1
        # Bare words a reader sees: unqualified names and leading components.
        words = frozenset(t.split('.', 1)[0] for t in every | found | {s for s, _ in shown.values()})
        ops = frozenset(c for s in strings for c in s if not (c.isalnum() or c.isspace()))
        return cls(theorem, {t: s for t, (s, _) in shown.items()}, {t: k for t, (_, k) in shown.items()}, words, ops)


_CURRENT: contextvars.ContextVar[Reading | None] = contextvars.ContextVar('leanglish_notation', default=None)


def current() -> Reading | None:
    return _CURRENT.get()


def name(full: str, r: Reading | None = None) -> str:
    """The shown form of one cited Lean name in the current reading (identity outside one)."""
    r = r or _CURRENT.get()
    if r is None or full not in r.names:
        return full
    r.outputs[r.names[full]] = r.outputs.get(r.names[full], frozenset()) | {r.via[full]}
    return r.names[full]


def display(text: str, r: Reading | None = None) -> str:
    """Display notation for one formula string; unrecognized text is unchanged."""
    r = r or _CURRENT.get()
    if r is None:
        return text
    out = r.cache.get(text)
    if out is None:
        tree = parse(text)
        used: set[str] = set()
        out = r.cache[text] = text if tree is None else _render(tree, r, used)
        if used:
            r.outputs[out] = r.outputs.get(out, frozenset()) | used
    return out


# --- structural recognizers -------------------------------------------------

def _is(item: Any, kind: str, text: str | None = None) -> bool:
    return isinstance(item, Tok) and item.kind == kind and (text is None or item.text == text)


def _next(items: tuple, i: int) -> int:
    while i < len(items) and _is(items[i], 'ws'):
        i += 1
    return i


def _prev(items: tuple, i: int) -> int:
    i -= 1
    while i >= 0 and _is(items[i], 'ws'):
        i -= 1
    return i


def _head_ok(items: tuple, i: int) -> bool:
    """The item at ``i`` starts a term, not an argument or a field."""
    p = _prev(items, i)
    if p < 0:
        return True
    q = items[p]
    if isinstance(q, Group) or q.kind in ('num', 'str', 'chr'):
        return False
    if q.kind == 'id':
        return q.text in KEYWORDS and q.text != 'fun'
    return q.text not in _PREFIX | {'@', '.', '#', '√'}


def _starts_term(item: Any) -> bool:
    if isinstance(item, Group):
        return True
    if item.kind == 'id':
        return item.text not in KEYWORDS or item.text == 'fun'
    return item.kind in ('num', 'str', 'chr') or item.text in _ARG_START


def _atom(items: tuple, j: int) -> int | None:
    """End of an atomic argument at ``j``: prefix coercions, then one primary."""
    while j < len(items) and _is(items[j], 'op') and items[j].text in _PREFIX:
        j += 1
    if j >= len(items):
        return None
    it = items[j]
    if not (isinstance(it, Group) or it.kind in ('num', 'str', 'chr')
            or (it.kind == 'id' and it.text not in KEYWORDS)):
        return None
    j += 1
    if j < len(items) and not (_is(items[j], 'ws') or (_is(items[j], 'op') and items[j].text in (',', '|', '‖'))):
        return None
    return j


def _app(items: tuple, i: int, head: str, arity: int) -> list[tuple[int, int]] | None:
    """Exactly ``arity`` atomic arguments of ``head`` at ``i``, and nothing more."""
    if not (_is(items[i], 'id', head) and _head_ok(items, i)):
        return None
    args, j = [], i+1
    for _ in range(arity):
        if not (j < len(items) and _is(items[j], 'ws')):
            return None
        end = _atom(items, j+1)
        if end is None:
            return None
        args.append((j+1, end)); j = end
    if j < len(items) and _is(items[j], 'ws'):
        q = _next(items, j)
        if q < len(items) and _starts_term(items[q]):
            return None
    return args


def _extent(items: tuple, start: int) -> int | None:
    """End of a maximal term (a lambda or binder body) at ``start``, or ``None``.

    The term ends at the region end or at a terminator that no pending binder,
    lambda or ``if`` consumes. Constructs of unknown extent bail out.
    """
    expect: list[str] = []
    for i in range(start, len(items)):
        t = items[i]
        if isinstance(t, Group) or t.kind == 'ws':
            continue
        x = t.text
        if t.kind == 'id':
            if x in _NO_EXTENT:
                return None
            if x == 'fun':
                expect.append('=>')
            elif x == 'if':
                expect.append('then')
            elif x in ('then', 'else'):
                if not expect or expect[-1] != x:
                    return i
                expect[-1:] = ['else'] if x == 'then' else []
            elif x in ('in', 'with'):
                if not expect or expect[-1] != ',':
                    return i
            elif x in ('at', 'from'):
                return i
            elif x in _BINDER_IDS:
                expect.append(',')
        elif t.kind == 'op':
            if _nary(x):
                expect.append(',')
            elif x == ',':
                if not expect or expect[-1] != ',':
                    return i
                expect.pop()
            elif x == '=>':
                if not expect or expect[-1] != '=>':
                    return None
                expect.pop()
            elif x == ':':
                if not expect or expect[-1] not in (',', 'then', '=>'):
                    return i
            elif x in (';', ':=', '<|', '|>', '←', '↦'):
                return None
    return None if expect else len(items)


def _simple(items: Iterable) -> bool:
    """No top-level relation, connective, binder or keyword."""
    for t in items:
        if isinstance(t, Group) or t.kind in ('ws', 'num', 'str', 'chr'):
            continue
        if (t.kind == 'id' and t.text in KEYWORDS) or (t.kind == 'op' and t.text not in _ARITH):
            return False
    return True


def _strip(items: tuple) -> tuple:
    a, b = 0, len(items)
    while a < b and _is(items[a], 'ws'):
        a += 1
    while b > a and _is(items[b-1], 'ws'):
        b -= 1
    return items[a:b]


def _unparen(items: tuple) -> tuple:
    """The contents of a lone parenthesized group, else ``items``."""
    if len(items) == 1 and isinstance(items[0], Group) and items[0].open == '(' and _strip(items[0].items):
        return _strip(items[0].items)
    return items


def _lambda(items: tuple) -> tuple[str, tuple] | None:
    """``fun x => body`` with one plain binder, as the whole of ``items``.

    Returns the binder and the body, which starts with the original whitespace.
    """
    items = _strip(items)
    if (len(items) >= 7 and _is(items[0], 'id', 'fun') and _is(items[1], 'ws') and _is(items[2], 'id')
            and '.' not in items[2].text and items[2].text not in KEYWORDS and _is(items[3], 'ws')
            and _is(items[4], 'op', '=>') and _is(items[5], 'ws') and _extent(items, 6) == len(items)):
        return items[2].text, items[5:]
    return None


def _ids(items: Iterable) -> Iterable[str]:
    for t in items:
        if isinstance(t, Group):
            yield from _ids(t.items)
        elif t.kind == 'id':
            yield t.text


def _render(items: tuple, r: Reading, used: set[str], paren: bool = False) -> str:
    """``paren``: ``items`` is the whole content of a parenthesized group."""
    out: list[str] = []
    i = 0
    while i < len(items):
        hit = _rule(items, i, r, used, paren)
        if hit is not None:
            out.append(hit[0]); i = hit[1]
            continue
        it = items[i]
        if isinstance(it, Group):
            out.append(it.open + _render(it.items, r, used, it.open == '(') + it.close)
        elif it.kind == 'id' and it.text in r.names and not (i and _is(items[i-1], 'op', '.')):
            out.append(r.names[it.text]); used.add(r.via[it.text])
        else:
            out.append(it.text)
        i += 1
    return ''.join(out)


def _wrap(items: tuple, start: int, end: int, text: str) -> str:
    """Parenthesize a low-precedence display form unless it fills its region."""
    alone = _prev(items, start) < 0 and _next(items, end) >= len(items)
    return text if alone else '('+text+')'


def _rule(items: tuple, i: int, r: Reading, used: set[str], paren: bool = False) -> tuple[str, int] | None:
    it = items[i]
    if not _is(it, 'id'):
        return None
    sub = lambda part: _render(tuple(part), r, used)
    if it.text == 'fun':
        end = _extent(items, i)
        if end is None or '↦' in r.ops or (i and _is(items[i-1], 'op') and items[i-1].text in _PREFIX | {'@', '.'}):
            return None
        while _is(items[end-1], 'ws'):
            end -= 1
        found = _lambda(items[i:end])
        if found is None:
            return None
        x, body = found
        used.add('lambda')
        return _wrap(items, i, end, x+' ↦'+sub(body)), end
    # Not when the reading prints ∞ itself (ENNReal or EReal ⊤): there atTop and
    # 𝓝 ∞ are different filters, and both would read as "→ ∞".
    if it.text == 'Filter.Tendsto' and 'as' not in r.words and '∞' not in r.ops:
        args = _app(items, i, 'Filter.Tendsto', 3)
        if args is None:
            return None
        (a0, a1), (b0, b1), (c0, c1) = args
        f, source, target = items[a0], items[b0:b1], items[c0:c1]
        found = _lambda(f.items) if isinstance(f, Group) and a1 == a0+1 and f.open == '(' else None
        if found is None or not (len(source) == 1 and _is(source[0], 'id', 'Filter.atTop')) or len(target) != 1:
            return None
        x, body = found
        # In `Tendsto (fun n => f n) atTop (nhds (g n))` the limit's n is not
        # the bound one; "as n → ∞" would bind it, so such a limit stays as printed.
        if any(t == x or t.startswith(x+'.') for t in _ids(target)):
            return None
        target = target[0]
        if _is(target, 'id', 'Filter.atTop'):
            limit = '∞'
        elif _is(target, 'id', 'Filter.atBot'):
            limit = '−∞'
        elif isinstance(target, Group) and target.open == '(':
            inner = _strip(target.items)
            if not (len(inner) >= 3 and _is(inner[0], 'id', 'nhds') and _is(inner[1], 'ws')
                    and _atom(inner, 2) == len(inner)):
                return None
            # The limit point's own parentheses are redundant before "as".
            point = _unparen(inner[2:])
            limit = sub(point if _simple(point) else inner[2:])
        else:
            return None
        shown = sub(_strip(body))
        if not _simple(body):
            shown = '('+shown+')'
        used.add('tendsto')
        return _wrap(items, i, c1, shown+' → '+limit+' as '+x+' → ∞'), c1
    if it.text == 'nhdsWithin' and r.names.get('nhds') == '𝓝':
        args = _app(items, i, 'nhdsWithin', 2)
        if args is None:
            return None
        (a0, a1), (b0, b1) = args
        used.add('nhdsWithin')
        return '𝓝['+sub(_unparen(items[b0:b1]))+'] '+sub(items[a0:a1]), b1
    if it.text == 'Finset.card' and '#' not in r.ops:
        args = _app(items, i, 'Finset.card', 1)
        if args is None:
            return None
        used.add('card')
        return '#'+sub(items[args[0][0]:args[0][1]]), args[0][1]
    if it.text == 'Real.sqrt':
        args = _app(items, i, 'Real.sqrt', 1)
        if args is None:
            return None
        used.add('sqrt')
        return '√'+sub(items[args[0][0]:args[0][1]]), args[0][1]
    if it.text == 'Nat.choose' and 'choose' not in r.words:
        args = _app(items, i, 'Nat.choose', 2)
        if args is None:
            return None
        (a0, a1), (b0, b1) = args
        used.add('choose')
        shown = sub(items[a0:a1])+' choose '+sub(items[b0:b1])
        # Not ((n choose k)) when the form already fills a parenthesized group.
        if paren and _prev(items, i) < 0 and _next(items, b1) >= len(items):
            return shown, b1
        return '('+shown+')', b1
    return None


# --- per-reading context and legend -----------------------------------------

def displayed_text(declaration: Any) -> str:
    """The text a reader is shown: parameters, statement, step texts and conclusions."""
    shown = [p.get('text', '') for p in declaration.parameters] + [declaration.statement]
    stack = list(declaration.steps)
    while stack:
        s = stack.pop()
        shown += [s.text, s.conclusion or '']
        stack.extend(s.children)
    return '\n'.join(shown)


def summary(r: Reading, text: str) -> dict:
    """Namespaces and notations whose display forms occur in ``text``, in a fixed order."""
    word = lambda s: s in text and re.search(r"(?<![\w.'])"+re.escape(s)+r"(?![\w'])", text) is not None
    keys: set[str] = set()
    for out, k in r.outputs.items():
        # A bare name must occur as a word, not inside a longer one.
        if not k <= keys and (word(out) if out.split() == [out] else out in text):
            keys |= k
    # A template may show part of a recorded form: then the shortened name
    # itself decides. This can over-report an entry but never omits one.
    for t, s in r.names.items():
        if r.via[t] not in keys and word(s):
            keys.add(r.via[t])
    parts = r.theorem.split('.')[:-1]
    order = ['.'.join(parts[:k]) for k in range(len(parts), 0, -1)] + list(LIBRARY)
    symbols = [[shown, lean] for lean, shown in SYMBOLS.items() if 'sym:'+lean in keys]
    symbols += [list(NOTATIONS[k]) for k in NOTATIONS if k in keys]
    return {'omitted_namespaces': [ns for ns in order if 'ns:'+ns in keys], 'symbols': symbols}


LEGEND_TITLE = 'Notation (display only; the recorded Lean formulas are unchanged):'


def attach(document: Any, r: Reading) -> None:
    """Record the reading's legend in ``axes['notation']``, which the UI can read.

    The same legend is appended to the declaration's warnings, which the reader
    page and the Markdown view already display, so no view shows shortened
    names without it. Warnings are outside the reading binding; the bound
    ``axes['notation']`` is what ``check_reading`` compares.
    """
    d = document.declarations[0]
    s = summary(r, displayed_text(d))
    if s['omitted_namespaces'] or s['symbols']:
        d.axes['notation'] = s
        d.warnings.append(LEGEND_TITLE+' '+' '.join(_entries(s)))


def reading(method):
    """Decorate ``Narrative.document``: one display context per rendered reading."""
    @functools.wraps(method)
    def document(self, *args, **kwargs):
        from .narrative import _math_dictionary  # applied to every string before display
        r = Reading.of(self.snapshot.record, _math_dictionary)
        token = _CURRENT.set(r)
        try:
            result = method(self, *args, **kwargs)
        finally:
            _CURRENT.reset(token)
        attach(result, r)
        return result
    return document


def _entries(n: dict) -> list[str]:
    out = ['Namespace prefixes not written: '+', '.join(n['omitted_namespaces'])+'.'] if n['omitted_namespaces'] else []
    return out+[shown+' stands for '+lean+'.' for shown, lean in n['symbols']]


def legend(declaration: Any) -> list[str]:
    """Plain-text legend lines for ``prose``; empty when no notation is displayed."""
    n = declaration.axes.get('notation')
    if not n:
        return []
    return [LEGEND_TITLE]+['- '+e for e in _entries(n)]+['']


# --- corpus profile (docs/NOTATION.md) --------------------------------------

FORMS = [('↑ coercion arrow', r'↑'), ('fun x => e', r'(?<![\w.])fun\b'), ('∀ binder', r'∀'),
         ('∃ binder', r'∃'), ('‖x‖ norm', r'‖'), ('absolute value bars', r'\|'), ('⋯ elided proof', r'⋯'),
         ('[inst : C] instance binder', r'\[inst'), ('∑ or ∏ big operator', r'[∑∏]'), ('∫ integral', r'∫'),
         ('√ square root', r'√'), ('nhds a', r'(?<![\w.])nhds\b'), ('nhdsWithin a s', r'(?<![\w.])nhdsWithin\b'),
         ('Filter.Tendsto', r'(?<![\w.])Filter\.Tendsto\b'), ('if … then … else', r'(?<![\w.])if\b'),
         ('⁻¹ inverse', r'⁻¹'), ('∀ᶠ or ∃ᶠ eventually', r'[∀∃]ᶠ'), ('Real.pi', r'(?<![\w.])Real\.pi\b'),
         ('π', r'π'), ('Real.sqrt', r'(?<![\w.])Real\.sqrt\b'), ('Finset.card', r'(?<![\w.])Finset\.card\b'),
         ('s.card field notation', r"(?<![\w.])[^\W\dA-Z][\w']*\.card\b"), ('Nat.choose', r'(?<![\w.])Nat\.choose\b'),
         ('string literal', r'"'), ('«guillemet name»', r'«')]


def profile(corpus: Path) -> dict:
    """Frequencies over every formula string of every snapshot under ``corpus``.

    ``occurrences`` counts each string as often as frames repeat it, mostly in
    local contexts. ``distinct`` counts each distinct string once per reading.
    """
    from .reading_kpis import QUALIFIED, snapshot_paths
    raw: Counter = Counter(); distinct: Counter = Counter(); readings: Counter = Counter()
    forms_raw: Counter = Counter(); forms: Counter = Counter(); relation: Counter = Counter()
    fields: Counter = Counter()
    paths = snapshot_paths(corpus)
    for p in paths:
        record = json.loads(p.read_bytes())
        seen: Counter = Counter(); local: set[str] = set()
        for f in record['frames']:
            values = [('statement', f['statement'])] + [('objects', x) for x in f['objects']]
            values += [(k, f[k]) for k in ('domain', 'value') if k in f]
            values += [('context', c['type']) for c in f['context']]
            local |= {c['name'] for c in f['context']} | ({f['binder']} if 'binder' in f else set())
            for k, v in values:
                fields[k] += 1; seen[v] += 1
        parts = record['theorem'].split('.')[:-1]
        mine: set[str] = set()
        for s, times in seen.items():
            for q in QUALIFIED.findall(s):
                raw[q] += times; distinct[q] += 1; mine.add(q)
                ns = q.split('.')
                if ns[0] in local:
                    relation['projection of a local binder'] += 1
                elif ns[:len(parts)] == parts:
                    relation['theorem namespace'] += 1
                elif ns[0] == parts[0]:
                    relation['enclosing or other '+parts[0]+' namespace'] += 1
                elif ns[0] in LIBRARY:
                    relation['opened library namespace ('+', '.join(LIBRARY)+')'] += 1
                else:
                    relation['other library namespace'] += 1
            for label, rx in FORMS:
                n = len(re.findall(rx, s))
                forms_raw[label] += n*times; forms[label] += n
        readings.update(mine)
    top = Counter({q: n for q, n in distinct.items()})
    return {'snapshots': len(paths), 'field_strings': dict(sorted(fields.items())),
            'distinct_qualified_names': len(distinct),
            'qualified': [[q, raw[q], n, readings[q]] for q, n in sorted(top.items(), key=lambda x: (-x[1], x[0]))],
            'relation': dict(relation.most_common()),
            'forms': [[label, forms_raw[label], forms[label]] for label, _ in FORMS]}


def markdown(p: dict, top: int = 50) -> str:
    out = ['| # | Constant | Occurrences | Distinct strings | Readings |', '|---:|---|---:|---:|---:|']
    out += [f'| {i} | `{q}` | {a:,} | {b:,} | {c} |' for i, (q, a, b, c) in enumerate(p['qualified'][:top], 1)]
    out += ['', '| Syntax form | Occurrences | Distinct strings |', '|---|---:|---:|']
    out += [f'| {label} | {a:,} | {b:,} |' for label, a, b in sorted(p['forms'], key=lambda x: -x[2])]
    out += ['', '| Qualified name in distinct strings | Count |', '|---|---:|']
    out += [f'| {k} | {v:,} |' for k, v in p['relation'].items()]
    return '\n'.join(out)+'\n'


def main(argv: list[str] | None = None) -> int:
    import argparse
    a = argparse.ArgumentParser(description='Profile qualified constants and syntax forms in snapshot formulas.')
    a.add_argument('corpus', type=Path)
    a.add_argument('--top', type=int, default=50)
    a.add_argument('--json', type=Path)
    args = a.parse_args(argv)
    p = profile(args.corpus)
    if args.json:
        args.json.write_text(json.dumps(p, indent=1, ensure_ascii=False)+'\n', encoding='utf-8')
    sys.stdout.write(markdown(p, args.top))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
