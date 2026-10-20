"""Reading rules added in source-math-en/0.6.0; Narrative inherits them.

Each rule reads only recorded frame data: roles, heads, argument slots and
paths, binder names and domains, and printed statements. When a check fails
the frame keeps its earlier wording and gap flag. These rules change what is
shown and how frames are grouped into displayed steps, never which frames are
checked, and every frame stays owned by exactly one displayed step.
"""
from __future__ import annotations
import re

from .formula_surface import _FORMULA_GROUPS, _binary_formula, _formula_text, _joins_conjunction, _outer, _same_formula
from .model import Step


# Binders whose body is a whole term: as the right operand of ∧ or ↔ they extend to the end.
# Big operators (∑, ∏, ⋃) are not listed: their body stops at a relation.
_BINDER_LEAD = re.compile(r'(?:∀|∃!?|∀ᶠ|∃ᶠ) ')


def _plain_left(left: str, excluded: str) -> list[str]:
    """left parenthesized, and unparenthesized if it has no outer operator in excluded, binder or keyword."""
    a = _outer(left)
    return ['('+left+')'] + ([left] if a is not None and not a[1] & (set(excluded+'∀∃∑∏,:') | {'keyword'}) else [])


def joins_conjunction(text: str, left: str, right: str) -> bool:
    """text is left ∧ right with Lean's precedence; extends _joins_conjunction to a binder on the right.

    A ∧ ∀ x, P x → Q is A ∧ (∀ x, (P x → Q)): the binder's body takes the
    rest of the formula, so its outer → or ∨ cannot bind outside the conjunct.
    """
    if _joins_conjunction(text, left, right):
        return True
    r = _formula_text(right)
    return (r is not None and _BINDER_LEAD.match(r) is not None
            and any(_same_formula(text, x+' ∧ '+r) for x in _plain_left(left, '∧∨→↔')))


def joins_equivalence(text: str, left: str, right: str) -> bool:
    """text is the printed equivalence of left and right, read with Lean's precedence.

    ↔ is non-associative with precedence 20, below every other connective.
    The left side may appear unparenthesized only without an outer ↔, binder,
    comma or keyword (∀ x, P x ↔ Q is ∀ x, (P x ↔ Q)); the right side only
    without an outer ↔, which is rejected even inside a binder's body. A
    binder on the right (A ↔ ∀ x, P x → Q) takes the rest of the formula.
    """
    if _binary_formula(text, '↔', left, right):
        return True
    b = _outer(right)
    if b is None:
        return False
    rights = ['('+right+')'] + ([right] if '↔' not in b[1] else [])
    return any(_same_formula(text, x+' ↔ '+y) for x in _plain_left(left, '↔') for y in rights)


def leading_binder(text: str) -> tuple[str, str, str] | None:
    """Split ∃ (x : A) …, B into x, A and the rest ∃ …, B or B; else None.

    Only an explicit, parenthesized first binder group with one name is read.
    The rest is the printed remainder; Lean prints consecutive existentials as
    one ∃ with several groups, so the rest of ∃ (x : A) (y : B), C is ∃ (y : B), C.
    """
    text = _formula_text(text)
    if text is None or not text.startswith('∃ ('):
        return None
    depth, colon = 0, None
    for k in range(2, len(text)):
        c = text[k]
        if c in _FORMULA_GROUPS:
            depth += 1
        elif c in _FORMULA_GROUPS.values():
            depth -= 1
            if depth == 0:
                break
        elif depth == 1 and colon is None and text[k-1:k+2] == ' : ':
            colon = k
    else:
        return None
    name, kind, after = text[3:colon-1] if colon else '', text[colon+2:k] if colon else '', text[k+1:]
    if not name or not kind or any(c in name for c in ' ,()'):
        return None
    if after.startswith(', '):
        return name, kind, after[2:]
    if after.startswith(' ('):
        return name, kind, '∃' + after
    return None


class ReadingRules:
    """Methods of Narrative; they use its frames, step(), sequence() and owners."""

    def projected(self, text: str, left: str, right: str) -> bool:
        """The printed premise is left ∧ right, read with Lean's precedence (A ∧ ∃ p, … included)."""
        return joins_conjunction(text, left, right)

    def equivalent(self, text: str, left: str, right: str) -> bool:
        """The printed premise is left ↔ right, read with Lean's precedence (binders on the right included)."""
        return joins_equivalence(text, left, right)

    def applied_projection(self, i: int) -> list[Step] | None:
        """And.left/And.right h applied to further arguments: a conjunct used as a rule.

        And.left {a b} (h : a ∧ b) : a, followed by object arguments and
        premises that the conjunct a (a ∀ or → statement) is applied to.
        Required: exact argument slots and paths and h printed as a ∧ b. Only
        modus ponens with exact printing is explained: no object arguments, one
        further premise P, the conjunct printed P → Q or ¬P and the conclusion
        printed Q or False. Otherwise the instantiation or a definitional
        unfolding between the printed premise and the conjunct is not checked,
        and the step stays a gap (tests/audit/test_retained_reader_regressions.py).
        """
        from .formula_surface import _implication_formula
        from .narrative import math_text
        f = self.frames[i]; slots = [p['argument'] for p in f['premises']]
        if not (f['head'] in {'And.left', 'And.right'} and len(f['objects']) >= 2 and slots[:1] == [2]
                and len(f['objects'])+len(slots) > 3 and self.logical_application(i, len(f['objects']), slots)):
            return None
        left, right = f['objects'][:2]
        if not self.projected(self.frames[f['children'][0]]['statement'], left, right):
            return None
        # Object arguments fill the slots after h that hold no premise, in order.
        values = iter(f['objects'][2:])
        named = [math_text(next(values)) for k in range(3, len(f['objects'])+len(slots)) if k not in slots]
        further = len(slots)-1
        named += ['the further premise'+('s' if further > 1 else '')+' below'] if further else []
        side = 'first' if f['head'] == 'And.left' else 'second'; conjunct = left if side == 'first' else right
        exact = (len(f['objects']) == 2 and further == 1
                 and _implication_formula(conjunct, self.frames[f['children'][1]]['statement'], f['statement']))
        text = ('Take the '+side+' conjunct, '+math_text(conjunct)+', of the '
                + ('first premise' if further else 'premise')+' below and apply it to '
                + (named[0] if len(named) == 1 else ', '.join(named[:-1])+' and '+named[-1])
                + ('.' if exact else '; that this gives the statement shown is not checked here.'))
        return [self.step(i, text, rule='applied-projection' if exact else 'unchecked-application', fallback=not exact,
                          conclusion=math_text(f['statement']), children=[s for j in f['children'] for s in self.sequence(j)])]

    def nonempty_element(self, i: int) -> list[Step] | None:
        """Nonempty.intro {α} (v : α) with v a variable of the local context whose type is printed as α."""
        from .narrative import _name, math_text
        f = self.frames[i]
        if f['head'] != 'Nonempty.intro' or f['budget_cut'] or f['children'] or len(f['objects']) != 2:
            return None
        kind, value = f['objects']
        entry = next((c for c in reversed(f['context']) if c['name'] == value), None)
        if (entry is None or not _same_formula(entry['type'], kind)
                or not any(_same_formula(f['statement'], 'Nonempty '+t) for t in (kind, '('+kind+')'))):
            return None
        return [self.step(i, 'Since '+_name(value)+' ∈ '+math_text(kind)+', '+math_text(f['statement'])+' holds.',
                          rule='nonempty-intro')]

    def hypothesis(self, s: Step) -> int | None:
        """The frame of a displayed one-frame hypothesis line, else None.

        Facts from an anonymous `have` ("Use the fact … established above"),
        budget cuts and anything else that owns other frames are left alone,
        and so is a line whose sentence carries a label ("Forward direction. ",
        "Base case (zero). "): merging it would drop the label.
        """
        from .narrative import _ANONYMOUS, _name, math_text
        if s.rule != 'given' or s.fallback or s.children or not s.term_id or ',' in s.term_id:
            return None
        i = int(s.term_id[1:]); f = self.frames[i]
        if (f['role'] != 'given' or f['budget_cut']
                or (_ANONYMOUS.fullmatch(_name(f['binder'])) and self.introducer(i) == 'have')
                or s.text != 'Use the hypothesis '+_name(f['binder'])+': '+math_text(f['statement'])+'.'):
            return None
        return i

    def grouped(self, steps: list[Step]) -> list[Step]:
        """Merge each run of adjacent hypothesis lines with one local context into one line.

        The merged step owns exactly the hypothesis frames of the run, lists
        them in their original order and is not a gap: each is a recorded
        hypothesis. Other steps keep their position.
        """
        from .narrative import _name, math_text
        out: list[Step] = []
        run: list[tuple[Step, int]] = []

        def flush() -> None:
            if len(run) == 1:
                out.append(run[0][0])
            elif run:
                ids = [i for _, i in run]
                for i in ids:
                    del self.owners[i]
                items = [_name(self.frames[i]['binder'])+': '+math_text(self.frames[i]['statement']) for i in ids]
                # A statement printed over several lines gets one line per hypothesis.
                listed = ':\n'+';\n'.join(items) if any('\n' in x for x in items) else ' '+'; '.join(items)
                step = self.step(ids[0], 'Use the hypotheses'+listed+'.', rule='hypotheses', covered=ids,
                                 detail='Hypotheses (recorded binders and statements):\n'
                                 + '\n'.join(_name(self.frames[i]['binder'])+' : '+self.frames[i]['statement'] for i in ids))
                out.append(step)
            run.clear()

        for s in steps:
            s.children = self.grouped(s.children)
            i = self.hypothesis(s)
            if i is not None and (not run or run[0][0].context == s.context):
                run.append((s, i))
                continue
            flush()
            if i is not None:
                run.append((s, i))
            else:
                out.append(s)
        flush()
        return out

    def local_instances(self, covered: list[int]) -> list[str]:
        """Local instance hypotheses (inst, inst_2, inst✝¹ …) absorbed into an instance derivation."""
        from .narrative import _name, math_text
        return list(dict.fromkeys(_name(self.frames[j]['binder'])+': '+math_text(self.frames[j]['statement'])
                                  for j in covered if self.frames[j]['role'] == 'given'))

    def proof_witness(self, i: int) -> list[Step] | None:
        """Exists.intro {α} {p} (w : α) (h : p w) whose witness w is a proof of a proposition α.

        ∃ (_ : A), B states A together with B, so the step reads "Prove A, and
        then the remaining claim." A chain of such introductions is one step.
        Required: exact argument slots and paths, the statement printed as
        ∃ (x : A) … with A printed as the object α, and the witness's statement
        printed as α. With the anonymous binder _ the remaining claim must also
        be printed as the rest of the statement. A named binder may occur in
        it, with the proof substituted, and the sentence says so.
        """
        from .narrative import _name, math_text
        chain, proofs, names, j = [], [], [], i
        while True:
            f = self.frames[j]
            if not (f['head'] == 'Exists.intro' and self.logical_application(j, 2, [2, 3], role='witness')):
                break
            binder = leading_binder(f['statement'])
            witness, rest = f['children']
            if (binder is None or not _same_formula(binder[1], f['objects'][0])
                    or not _same_formula(self.frames[witness]['statement'], f['objects'][0])
                    or (binder[0] == '_' and not _same_formula(binder[2], self.frames[rest]['statement']))):
                break
            chain.append(j); proofs.append(witness)
            names.append(None if binder[0] == '_' else _name(binder[0]))
            j = rest
        if not chain:
            return None
        items = [(name+': ' if name else '')+math_text(self.frames[k]['statement']) for k, name in zip(proofs, names)]
        used = [name for name in names if name]
        text = 'Prove '+', then '.join(items)+', and then the remaining claim'
        if used:
            text += (', which may depend on the proof'+('s ' if len(used) > 1 else ' ')
                     + (used[0] if len(used) == 1 else ', '.join(used[:-1])+' and '+used[-1]))
        return [self.step(i, text+'.', rule='witness-proof', conclusion=math_text(self.frames[i]['statement']),
                          covered=chain, children=[s for k in proofs+[j] for s in self.sequence(k)])]

    def proof_cases(self, i: int) -> list[Step] | None:
        """Exists.casesOn {α} {p} {motive} (t : ∃ x, p x) (h : ∀ w (h : p w), …) with α a proposition.

        The two binders are assumptions: a proof of α and a proof of p of it.
        Required: exact argument slots and paths, the first binder's domain and
        the major premise's leading binder both printed as the object α, the
        rest of the major premise printed as the second binder's domain, and a
        constant motive (the body proves the printed conclusion). A hypothesis
        as major premise is then named and owned by this step, as for a
        conjunction: its statement is the two displayed parts.
        """
        from .narrative import _ANONYMOUS, _name, math_text
        f = self.frames[i]
        if not (f['head'] == 'Exists.casesOn' and self.logical_application(i, 3, [3, 4], role='choose')):
            return None
        major, first = self.frames[f['children'][0]], self.frames[f['children'][1]]
        second = self.frames[first['children'][0]] if first['role'] == 'assume' and len(first['children']) == 1 else {}
        binder = leading_binder(major['statement'])
        if not (second.get('role') == 'assume' and len(second['children']) == 1 and not first['budget_cut']
                and not second['budget_cut'] and _same_formula(first['domain'], f['objects'][0])
                and binder is not None and _same_formula(binder[1], f['objects'][0])
                and _same_formula(binder[2], second['domain'])
                and _same_formula(self.frames[second['children'][0]]['statement'], f['statement'])):
            return None
        parts = (_name(first['binder'])+': '+math_text(first['domain'])+' and '
                 + _name(second['binder'])+': '+math_text(second['domain'])+'.')
        if major['role'] == 'given' and not major['budget_cut'] and not self.instance(major['id']):
            anonymous = _ANONYMOUS.fullmatch(_name(major['binder'])) and self.introducer(major['id']) == 'have'
            source = 'the fact established above' if anonymous else _name(major['binder'])
            step = self.step(i, 'From '+source+', obtain '+parts, rule='unpack-existential',
                             covered=[i, major['id'], first['id'], second['id']])
        else:
            step = self.step(i, 'From the existential statement, obtain '+parts, rule='unpack-existential',
                             children=self.sequence(major['id']), covered=[i, first['id'], second['id']])
        return [step]+self.sequence(second['children'][0])
