"""Bracket-aware reading of recorded Lean formula strings for logical explanations.

These helpers compare and split pretty-printed formulas without unfolding
definitions. They are a restricted display grammar, not a Lean parser: anything
outside it returns None, and the calling rule keeps its explanation gap.
"""
from __future__ import annotations
import re

_TOP_LEVEL_OPERATORS = set('=≠<>≤≥∣∈∉⊆⊂⊇⊃↔→∧∨¬∀∃∑∏+-*/·^×,:≃≅∘|')
_FORMULA_GROUPS = {'(':')', '[':']', '{':'}', '⟨':'⟩', '⦃':'⦄', '⟦':'⟧'}
_LOGICAL_PRECEDENCE = {'↔':20, '→':25, '∨':30, '∧':35}
_FORMULA_CONTROL = re.compile(r'(?:fun|let|have|show|match|if|then|else|by|do|calc)\b')


def _formula_text(text: str) -> str | None:
    """Compare recorded notation, without unfolding definitions or substituting.

    Only whitespace and parentheses around the *whole* expression are ignored.
    Quoted strings/names and comments are outside this tiny display grammar:
    whitespace inside them can be meaningful. The additional grouping bound
    keeps unusually nested notation outside these explanations.
    """
    if (len(text) > 20000 or any(c in text for c in ('"', '`', '«', '»'))
            or any(c in text for c in ('--', '/-', '-/'))):
        return None
    text = ' '.join(text.split())
    if not text:
        return None
    stack: list[tuple[str,int]] = []
    pairs: dict[int,int] = {}
    for i, c in enumerate(text):
        if c in _FORMULA_GROUPS:
            stack.append((c,i))
            if len(stack) > 64:
                return None
        elif c in _FORMULA_GROUPS.values():
            if not stack or _FORMULA_GROUPS[stack[-1][0]] != c:
                return None
            _, start = stack.pop()
            pairs[start] = i
    if stack:
        return None
    left, right = 0, len(text)-1
    while left < right and text[left] == '(' and pairs.get(left) == right:
        left += 1; right -= 1
        while left < right and text[left] == ' ':
            left += 1
        while left < right and text[right] == ' ':
            right -= 1
    return text[left:right+1] or None


def _same_formula(left: str, right: str) -> bool:
    a, b = _formula_text(left), _formula_text(right)
    return a is not None and b is not None and a == b


def _outer(text: str) -> tuple[str,set[str]] | None:
    """Normalized text and the operator characters (and 'keyword') outside all brackets."""
    text = _formula_text(text)
    if text is None:
        return None
    depth, found = 0, set()
    for i, c in enumerate(text):
        if c in _FORMULA_GROUPS:
            depth += 1
        elif c in _FORMULA_GROUPS.values():
            depth -= 1
        elif depth == 0 and c in _TOP_LEVEL_OPERATORS:
            found.add(c)
        elif depth == 0 and (i == 0 or not (text[i-1].isalnum() or text[i-1] in "_.'")) and _FORMULA_CONTROL.match(text, i):
            found.add('keyword')
    return text, found


def _plain_proposition(text: str) -> str | None:
    """Normalized text without a top-level operator, binder or keyword, else None.

    Typeclass propositions are bare applications such as CharZero ℝ or
    (uniformity X).IsCountablyGenerated. Relations, connectives and binders,
    including any inside an unparenthesized lambda, rule a statement out.
    """
    outer = _outer(text)
    return outer[0] if outer is not None and not outer[1] and outer[0] not in {'True', 'False'} else None


def _joins_conjunction(text: str, left: str, right: str) -> bool:
    """text is the printed conjunction of left and right, read with the right precedence.

    A side may appear unparenthesized only if A has no outer connective,
    binder or keyword and B no outer ∨, → or ↔; otherwise ∧ would bind differently.
    """
    if _binary_formula(text, '∧', left, right):
        return True
    a, b = _outer(left), _outer(right)
    if a is None or b is None:
        return False
    lefts = ['('+left+')'] + ([left] if not a[1] & (set('∧∨→↔∀∃∑∏,:') | {'keyword'}) else [])
    rights = ['('+right+')'] + ([right] if not b[1] & set('∨→↔') else [])
    return any(_same_formula(text, x+' ∧ '+y) for x in lefts for y in rights)


def _logical_surface(text: str) -> tuple[str,list[tuple[int,str]]] | None:
    """Find outer logical operators in a restricted Lean notation fragment.

    This is not a Lean parser. In particular, unparenthesized binders, matches,
    lets and big-operator binders are not split at a connective in their body.
    A formula using one as an operand can still match when Lean parenthesizes it.
    """
    text = _formula_text(text)
    if text is None:
        return None
    depth = 0
    operators = []
    for i, c in enumerate(text):
        if c in _FORMULA_GROUPS:
            depth += 1
        elif c in _FORMULA_GROUPS.values():
            depth -= 1
        elif depth == 0:
            if c in '∀∃∑∏⨅⨆⋂⋃,;':
                return None
            if ((i == 0 or not (text[i-1].isalnum() or text[i-1] in "_.'"))
                    and _FORMULA_CONTROL.match(text, i)):
                return None
            # Compact connectives and decorated arrows are outside this grammar;
            # silently treating ¬P∧Q as an atom would get negation scope wrong.
            if c in _LOGICAL_PRECEDENCE:
                if not (0 < i < len(text)-1 and text[i-1] == text[i+1] == ' '):
                    return None
                operators.append((i,c))
    return text, operators


def _equation_sides(text: str) -> tuple[str,str] | None:
    """Split A = B at its only outer equality sign; binders and connectives reject."""
    surface = _logical_surface(text)
    if surface is None or surface[1]:
        return None
    text, depth, cuts = surface[0], 0, []
    for i, c in enumerate(text):
        if c in _FORMULA_GROUPS:
            depth += 1
        elif c in _FORMULA_GROUPS.values():
            depth -= 1
        elif depth == 0 and c == '=' and text[i-1:i+2] == ' = ':
            cuts.append(i)
    return (text[:cuts[0]-1], text[cuts[0]+2:]) if len(cuts) == 1 else None


def _logical_split(text: str, operator: str) -> tuple[str,str] | None:
    surface = _logical_surface(text)
    if surface is None:
        return None
    text, operators = surface
    if not operators:
        return None
    precedence = min(_LOGICAL_PRECEDENCE[op] for _,op in operators)
    roots = [(i,op) for i,op in operators if _LOGICAL_PRECEDENCE[op] == precedence]
    if roots[0][1] != operator or (operator == '↔' and len(roots) != 1):
        return None
    # →, ∨ and ∧ associate to the right. Unparenthesized iterated ↔ is rejected.
    i, _ = roots[0]
    return text[:i].strip(), text[i+1:].strip()


def _binary_formula(text: str, operator: str, left: str, right: str) -> bool:
    parts = _logical_split(text, operator)
    return parts is not None and _same_formula(parts[0], left) and _same_formula(parts[1], right)


def _negated_operand(text: str) -> str | None:
    surface = _logical_surface(text)
    if surface is None:
        return None
    text, operators = surface
    if text.startswith('¬') and not operators:
        return _formula_text(text[1:])
    parts = _logical_split(text, '→')
    if parts is not None and _same_formula(parts[1], 'False'):
        return _formula_text(parts[0])
    return None


def _negation_formula(text: str, proposition: str) -> bool:
    operand = _negated_operand(text)
    return operand is not None and _same_formula(operand, proposition)


def _implication_formula(text: str, left: str, right: str) -> bool:
    return (_binary_formula(text, '→', left, right)
            or (_same_formula(right, 'False') and _negation_formula(text, left)))
