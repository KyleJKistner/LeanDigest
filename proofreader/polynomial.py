"""Small exact, independently replayable commutative-ring certificates.

No CAS, numerical tolerances or network calls are used. This is deliberately a
restricted parser: ASCII/Unicode identifiers from an explicitly supplied scalar
context, integers, +, -, *, parentheses and small natural powers. A certificate
asserts an *integer polynomial identity* G = sum(M_i A_i), not division in a field.
The surrounding Lean snapshot must independently establish that all variables
belong to the same commutative ring and that A_i=0 are available assumptions.
"""
from __future__ import annotations
from fractions import Fraction
from itertools import combinations, combinations_with_replacement
import re
from typing import Any

Monomial = tuple[tuple[str, int], ...]
Poly = dict[Monomial, Fraction]
MAX_TERMS = 512
MAX_DEGREE = 12
MAX_TOKENS = 300


class UnsupportedPolynomial(ValueError):
    pass


def guard(test: bool, message: str) -> None:
    if not test:
        raise UnsupportedPolynomial(message)


def degree(m: Monomial) -> int:
    return sum(p for _, p in m)


def tidy(p: Poly) -> Poly:
    p = {m: Fraction(c) for m, c in p.items() if c}
    guard(len(p) <= MAX_TERMS and all(degree(m) <= MAX_DEGREE for m in p), 'Polynomial expansion limit')
    return p


def add(p: Poly, q: Poly, scale: Fraction = Fraction(1)) -> Poly:
    r = dict(p)
    for m, c in q.items():
        r[m] = r.get(m, Fraction(0)) + scale * c
    return tidy(r)


def mul(p: Poly, q: Poly) -> Poly:
    guard(len(p) * len(q) <= 40_000, 'Polynomial product budget')
    r: Poly = {}
    for a, x in p.items():
        for b, y in q.items():
            d = dict(a)
            for v, power in b:
                d[v] = d.get(v, 0) + power
            m = tuple(sorted(d.items()))
            r[m] = r.get(m, Fraction(0)) + x * y
    return tidy(r)


def power(p: Poly, n: int) -> Poly:
    guard(0 <= n <= MAX_DEGREE, 'Power is outside the supported budget')
    result: Poly = {(): Fraction(1)}
    for _ in range(n):
        result = mul(result, p)
    return result


_TOKEN = re.compile(r'\s*(?:(\d+)|([^\W\d]\w*)|([()+*^\-]))', re.UNICODE)


class Parser:
    def __init__(self, s: str, variables: set[str]):
        guard(isinstance(s, str) and len(s) <= 10_000, 'Expression size limit')
        self.variables = variables
        self.tokens: list[str] = []
        i = 0
        while i < len(s):
            if s[i:].isspace():
                break
            m = _TOKEN.match(s, i)
            guard(m is not None, 'Unsupported polynomial notation')
            assert m is not None
            self.tokens.append(next(x for x in m.groups() if x is not None))
            i = m.end()
            guard(len(self.tokens) <= MAX_TOKENS, 'Polynomial token budget')
        self.i = 0

    def peek(self) -> str:
        return self.tokens[self.i] if self.i < len(self.tokens) else ''

    def pop(self) -> str:
        result = self.peek()
        guard(bool(result), 'Unexpected end of expression')
        self.i += 1
        return result

    def sum(self) -> Poly:
        p = self.product()
        while self.peek() in {'+', '-'}:
            sign = 1 if self.pop() == '+' else -1
            p = add(p, self.product(), Fraction(sign))
        return p

    def product(self) -> Poly:
        p = self.unary()
        while self.peek() == '*':
            self.pop()
            p = mul(p, self.unary())
        return p

    def unary(self) -> Poly:
        if self.peek() in {'-', '+'}:
            sign = -1 if self.pop() == '-' else 1
            return {m: sign * c for m, c in self.unary().items()}
        return self.exponent()

    def exponent(self) -> Poly:
        token = self.pop()
        if token == '(':
            p = self.sum()
            guard(self.pop() == ')', 'Unmatched parenthesis')
        elif token.isdecimal():
            guard(len(token) <= 12, 'Integer too large')
            n = int(token)
            p = {(): Fraction(n)} if n else {}
        else:
            guard(token in self.variables, 'Unbound or unsupported scalar: ' + token)
            p = {((token, 1),): Fraction(1)}
        if self.peek() == '^':
            self.pop()
            n = self.pop()
            guard(n.isdecimal() and len(n) <= 2, 'Expected a small natural exponent')
            p = power(p, int(n))
        return p

    def parse(self) -> Poly:
        p = self.sum()
        guard(self.i == len(self.tokens), 'Trailing polynomial tokens')
        return tidy(p)


def parse(s: str, variables: set[str]) -> Poly:
    return Parser(s, variables).parse()


def equality(s: str, variables: set[str]) -> Poly:
    guard(s.count('=') == 1, 'Expected one polynomial equality')
    lhs, rhs = s.split('=')
    return add(parse(lhs, variables), parse(rhs, variables), Fraction(-1))


def encode(p: Poly) -> list[list[Any]]:
    guard(all(c.denominator == 1 for c in p.values()), 'Rational multiplier is not valid in every ring')
    return [[[[v, e] for v, e in m], c.numerator] for m, c in sorted(p.items())]


def decode(rows: Any, variables: set[str]) -> Poly:
    guard(isinstance(rows, list) and len(rows) <= MAX_TERMS, 'Invalid polynomial rows')
    p: Poly = {}
    for row in rows:
        guard(isinstance(row, list) and len(row) == 2, 'Invalid monomial row')
        factors, coefficient = row
        guard(type(coefficient) is int and coefficient != 0 and abs(coefficient) < 10**30, 'Invalid integer coefficient')
        guard(isinstance(factors, list) and len(factors) <= MAX_DEGREE, 'Invalid factors')
        converted = []
        for f in factors:
            guard(isinstance(f, list) and len(f) == 2 and isinstance(f[0], str), 'Invalid factor')
            v, e = f
            guard(v in variables and type(e) is int and 0 < e <= MAX_DEGREE, 'Invalid variable or exponent')
            converted.append((v, e))
        m = tuple(converted)
        guard(list(m) == sorted(m) and len({v for v, _ in m}) == len(m) and m not in p, 'Noncanonical monomial')
        p[m] = Fraction(coefficient)
    p = tidy(p)
    guard(encode(p) == rows, 'Noncanonical polynomial')
    return p


def _order(m: Monomial) -> tuple:
    return degree(m), m


def solve(target: Poly, assumptions: list[Poly], max_columns: int = 600) -> list[Poly] | None:
    """Bounded exact ideal-membership search; replay uses only add/mul, not this solver.

    Linear algebra is over Q for efficiency, but a result with any noninteger
    coefficient is rejected: 2x=0 must never justify x=0 in a ring of characteristic 2.
    """
    if not target:
        return [{} for _ in assumptions]
    goal_degree = max(map(degree, target))
    variables = sorted({v for p in [target, *assumptions] for m in p for v, _ in m})
    columns: list[tuple[int, Monomial, Poly]] = []
    for i, a in enumerate(assumptions):
        if not a:
            continue
        d = max(map(degree, a))
        if d > goal_degree:
            continue
        for k in range(goal_degree - d + 1):
            for vs in combinations_with_replacement(variables, k):
                powers: dict[str, int] = {}
                for v in vs:
                    powers[v] = powers.get(v, 0) + 1
                m = tuple(sorted(powers.items()))
                columns.append((i, m, mul({m: Fraction(1)}, a)))
                if len(columns) > max_columns:
                    return None
    # pivot -> (normalized polynomial, combination of original columns)
    basis: dict[Monomial, tuple[Poly, dict[int, Fraction]]] = {}
    for index, (_, _, column) in enumerate(columns):
        p, combo = column.copy(), {index: Fraction(1)}
        while p:
            pivot = max(p, key=_order)
            c = p[pivot]
            if pivot not in basis:
                basis[pivot] = ({m: x/c for m, x in p.items()}, {k: x/c for k, x in combo.items()})
                break
            vector, vec_combo = basis[pivot]
            p = add(p, vector, -c)
            for k, x in vec_combo.items():
                combo[k] = combo.get(k, Fraction(0)) - c*x
                if not combo[k]:
                    del combo[k]
    p, answer = target.copy(), {}
    while p:
        pivot = max(p, key=_order)
        if pivot not in basis:
            return None
        c = p[pivot]
        vector, combo = basis[pivot]
        p = add(p, vector, -c)
        for k, x in combo.items():
            answer[k] = answer.get(k, Fraction(0)) + c*x
    multipliers: list[Poly] = [{} for _ in assumptions]
    for k, c in answer.items():
        if not c:
            continue
        i, m, _ = columns[k]
        multipliers[i][m] = multipliers[i].get(m, Fraction(0)) + c
    multipliers = [tidy(m) for m in multipliers]
    if any(c.denominator != 1 for p in multipliers for c in p.values()):
        return None
    total: Poly = {}
    for m, a in zip(multipliers, assumptions):
        total = add(total, mul(m, a))
    return multipliers if total == target else None


def scalar_context(frame: dict) -> tuple[str, set[str]]:
    """Only exact, recognized class applications; no substring-based ring guess."""
    types = [c['type'].strip() for c in frame['context']]
    rings = []
    for t in types:
        m = re.fullmatch(r'(?:EuclideanDomain|CommRing) ([^\W\d]\w*)', t, re.UNICODE)
        if m:
            rings.append(m[1])
    guard(len(set(rings)) == 1, 'No unique recognized commutative ring in local context')
    ring = rings[0]
    # Later binders shadow earlier names. Only expose scalar variables.
    last = {c['name']: c['type'].strip() for c in frame['context']}
    variables = {n for n, t in last.items() if t == ring and re.fullmatch(r'[^\W\d]\w*', n, re.UNICODE)}
    guard(0 < len(variables) <= 20, 'Scalar-context size is unsupported')
    return ring, variables


def _conjuncts(s: str) -> list[str]:
    # The restricted parser will reject embedded quantifiers, negation and
    # implication, so splitting only top-level conjunctions cannot strengthen them.
    out, depth, begin = [], 0, 0
    for i, ch in enumerate(s):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        elif ch == '∧' and depth == 0:
            out.append(s[begin:i].strip()); begin = i+1
    out.append(s[begin:].strip())
    return out


def assumptions(frame: dict, variables: set[str]) -> list[tuple[dict, Poly]]:
    result = []
    contexts = frame['context']
    last = {c['name']: i for i, c in enumerate(contexts)}
    for i, c in enumerate(contexts):
        if last[c['name']] != i:
            continue
        # Reject the WHOLE proposition if any part is not an equality.
        # In particular, (P → x=0 ∧ y=0) must not supply the unconditional y=0.
        parts = _conjuncts(c['type'])
        try:
            parsed = [equality(claim, variables) for claim in parts]
        except (UnsupportedPolynomial, RecursionError):
            continue
        for j, (claim, p) in enumerate(zip(parts, parsed)):
            if p:
                result.append(({'context_index': i, 'conjunct': j, 'name': c['name'], 'statement': claim}, p))
    return result


def certify(frame: dict, max_assumptions: int = 2) -> dict | None:
    """Find a small certificate, preferring fewer assumptions in fixed order."""
    try:
        ring, variables = scalar_context(frame)
        target = equality(frame['statement'], variables)
        available = assumptions(frame, variables)
        if len(available) > 20:
            return None
        for count in range(min(max_assumptions, len(available)) + 1):
            for selected in combinations(available, count):
                multipliers = solve(target, [p for _, p in selected])
                if multipliers is not None:
                    result = {'schema': 'proofreader.polynomial-certificate/v1', 'frame_id': frame['id'],
                              'ring': ring, 'variables': sorted(variables), 'goal': frame['statement'],
                              'assumptions': [a for a, _ in selected],
                              'multipliers': [encode(p) for p in multipliers]}
                    verify(frame, result)
                    return result
    except (UnsupportedPolynomial, RecursionError):
        return None
    return None


def verify(frame: dict, certificate: dict) -> None:
    """Independently reconstruct and check the claimed identity against a snapshot.

    A passing check does not authenticate the snapshot or establish its Lean
    provenance. Use source replay for that separate question.
    """
    guard(isinstance(certificate, dict), 'Invalid certificate')
    guard(set(certificate) == {'schema','frame_id','ring','variables','goal','assumptions','multipliers'}, 'Unknown certificate fields')
    guard(certificate['schema'] == 'proofreader.polynomial-certificate/v1', 'Unsupported certificate schema')
    guard(type(certificate['frame_id']) is int and certificate['frame_id'] == frame['id'], 'Wrong certificate frame')
    ring, variables = scalar_context(frame)
    guard(certificate['ring'] == ring and certificate['variables'] == sorted(variables), 'Wrong scalar context')
    guard(certificate['goal'] == frame['statement'], 'Certificate goal mismatch')
    target = equality(frame['statement'], variables)
    available = { (a['context_index'], a['conjunct']): (a,p) for a,p in assumptions(frame, variables) }
    aa, mm = certificate['assumptions'], certificate['multipliers']
    guard(isinstance(aa,list) and isinstance(mm,list) and len(aa) == len(mm) and len(aa) <= 20, 'Invalid certificate dimensions')
    total: Poly = {}
    seen = set()
    for a, encoded in zip(aa, mm):
        guard(isinstance(a,dict) and type(a.get('context_index')) is int and type(a.get('conjunct')) is int, 'Invalid assumption reference')
        key = a['context_index'], a['conjunct']
        guard(key in available and key not in seen, 'Missing or repeated assumption')
        seen.add(key)
        actual, p = available[key]
        guard(a == actual, 'Assumption changed from local context')
        total = add(total, mul(decode(encoded, variables), p))
    guard(total == target, 'Polynomial certificate identity failed')


def polynomial_text(p: Poly) -> str:
    if not p:
        return '0'
    pieces = []
    for m in sorted(p, key=_order, reverse=True):
        c = p[m]
        monomial = ' · '.join(v if n == 1 else f'{v}^{n}' for v, n in m)
        magnitude = abs(c)
        term = monomial if magnitude == 1 and monomial else str(magnitude) + (' · ' + monomial if monomial else '')
        pieces.append(('- ' if c < 0 else '+ ') + term)
    result = ' '.join(pieces)
    return result[2:] if result.startswith('+ ') else '−' + result[2:]


def certificate_text(certificate: dict) -> str:
    variables = set(certificate['variables'])
    terms = []
    for a, m in zip(certificate['assumptions'], certificate['multipliers']):
        lhs, rhs = a['statement'].split('=')
        terms.append(f"({polynomial_text(decode(m,variables))}) · (({lhs.strip()}) − ({rhs.strip()}))")
    return 'LHS − RHS = ' + (' + '.join(terms) if terms else '0') + '. Expand and compare integer coefficients.'
