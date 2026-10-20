"""Deterministic mathematical prose from source-bound Lean judgement snapshots.

This route is separate from the exact constructor-DAG route. The snapshot is
small because the complete proof remains in the supplied Lean source. Its
formula strings come from Lean's pretty-printer. Re-extraction and comparison
bind the snapshot to that source; reading alone never executes or authenticates
Lean. Our English templates and pretty-printer are not formally proved correct.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import asdict
import copy
from pathlib import Path
import re
from typing import Any

from .model import Declaration, Document, Span, Step, canonical_json, digest, walk_steps
from .kernel import InvalidExport, require
from .kernel_io import strict_json, STANDARD_AXIOMS
from .polynomial import certify, verify as verify_polynomial, certificate_text
from .formula_surface import (_same_formula, _plain_proposition, _joins_conjunction, _equation_sides, _binary_formula, _negated_operand, _negation_formula, _implication_formula)
from . import notation
from .narrative_rules import ReadingRules

SCHEMA = 'proofreader.narrative/v1'
PRINTER_VERSION = 'source-math-en/0.6.0'
# Earlier labels, each with the only snapshots whose retained reading under it
# this renderer reproduces exactly (the Bézout demo and native companion).
EARLIER_PRINTERS = {'source-math-en/0.4.2': frozenset({
    'dad8ef23a231904f37b73979f8284ea3662ffe8f8cd30c79066856f2095b4dd7',
    'e93e0455259fc3283983f3a47f956cdac4b1a28869bc5027bcc694b4a124d8d0'})}
ROLES = {'introduce','assume','have','define','witness','choose','cases','combine','chain',
         'reflexivity','cancel','identity','given','named','application','ring','rewrite','unexpanded','induction','congruence','local-application','specialize'}
_HEAD_ROLES = {'Exists.intro':'witness','Exists.casesOn':'choose','Exists.elim':'choose',
               'And.intro':'combine','Trans.trans':'chain','Eq.trans':'chain',
               'mul_left_cancel₀':'cancel','id':'identity','Eq.refl':'reflexivity','rfl':'reflexivity',
               'dite':'cases','ite':'cases','Decidable.byCases':'cases','Classical.byCases':'cases',
               'Or.elim':'cases','Or.casesOn':'cases',
               'Nat.rec':'induction','Nat.recOn':'induction','Nat.recAux':'induction','List.rec':'induction','List.recOn':'induction'}
_SPECIALIZATION_ARITIES = {'Nat.rec':4,'Nat.recOn':4,'Nat.recAux':4,'List.rec':5,'List.recOn':5,
                           'Exists.casesOn':5,'Exists.elim':5,'Or.elim':6,'Or.casesOn':6,'dite':5,'ite':5}
_REWRITES = {'Eq.mpr','Eq.mp','of_eq_true','congrArg','congr','congrFun',"congrFun'"}
_LEMMAS = {
    'EuclideanDomain.gcd_eq_zero_iff': 'A gcd is zero exactly when both entries are zero.',
    'EuclideanDomain.gcd_dvd_left': 'The gcd divides its first entry.',
    'EuclideanDomain.gcd_dvd_right': 'The gcd divides its second entry.',
    'EuclideanDomain.gcd_eq_gcd_ab': 'Use the Bézout identity supplied by the extended Euclidean algorithm.',
    'EuclideanDomain.instIsDomain': 'A Euclidean domain is an integral domain.',
    'IsDomain.toIsCancelMulZero': 'In an integral domain, multiplication by a nonzero element is cancellative.',
    'IsCancelMulZero.toIsLeftCancelMulZero': 'Use left cancellation away from zero.',
    'mul_one': 'Multiplication by one leaves the element unchanged.',
    'Eq.symm': 'Reverse the supplied equality.',
    'Iff.mp': 'Apply the forward direction of the stated equivalence to the supplied hypothesis.',
}
# Typeclass names (Lean core/Mathlib) used only for instance derivations whose
# head carries no instance naming convention, e.g. Real.borelSpace : BorelSpace ℝ.
# Reviewed against the retained corpus; a name here never makes a frame with a
# non-instance premise, a project (OAI.*) head or a constructor head an instance.
_INSTANCE_CLASSES = frozenset('''AddLeftMono AddLeftReflectLE AddLeftStrictMono AddRightMono AddRightReflectLE
 AddRightStrictMono Archimedean BorelSpace IsScalarTower RingHomInvPair SMulCommClass TopologicalSpace.PseudoMetrizableSpace
 CharZero ClosedIciTopology CompactSpace CompleteSpace CompletelyRegularSpace ConnectedSpace Countable DenselyOrdered
 DiscreteMeasurableSpace DiscreteTopology ExistsAddOfLE Fact Finite FiniteDimensional HasSolidNorm Infinite
 IsDedekindDomain IsDirectedOrder IsDomain IsLeftCancelAdd IsManifold IsOrderedAddMonoid IsOrderedCancelAddMonoid
 IsOrderedRing IsPrincipalIdealRing IsSimpleRing IsStrictOrderedRing IsTopologicalRing IsTopologicalSemiring
 LocallyCompactSpace MeasurableSingletonClass MeasureTheory.IsFiniteMeasure MeasureTheory.IsFiniteMeasureOnCompacts
 MeasureTheory.IsLocallyFiniteMeasure MeasureTheory.IsProbabilityMeasure MeasureTheory.IsZeroOrProbabilityMeasure
 MeasureTheory.SFinite MeasureTheory.SigmaFinite Module.Finite Module.FinitePresentation Module.IsTorsionFree
 MulPosMono MulPosReflectLE MulPosReflectLT MulPosStrictMono NeZero NoMaxOrder NoTopOrder NoZeroSMulDivisors Nonempty
 Nontrivial OpensMeasurableSpace OrderClosedTopology OrderTopology PathConnectedSpace PolishSpace PosMulMono
 PosMulReflectLE PosMulReflectLT PosMulStrictMono ProperSpace R1Space RegularSpace RingHomIsometric SecondCountableTopology
 StandardBorelSpace StarOrderedRing StrongRankCondition Subsingleton T0Space T2Space T35Space T3Space T4Space
 TopologicalSpace.IsCompletelyMetrizableSpace TopologicalSpace.IsCompletelyPseudoMetrizableSpace
 TopologicalSpace.MetrizableSpace TopologicalSpace.SeparableSpace WeaklyLocallyCompactSpace WellFoundedLT
 ZeroLEOneClass'''.split())
# Lean's automatic names for anonymous instance binders: inst, inst_1, inst✝, inst✝¹.
_INSTANCE_BINDER = re.compile(r'inst(?:_\d+)?(?:✝[⁰¹²³⁴⁵⁶⁷⁸⁹]*)?')
# Lean's names for an unlabelled `have`: this, this_1, …
_ANONYMOUS = re.compile(r'this(?:_\d+)?')
# Certificate lemmas of three Mathlib decision procedures, recognized by namespace.
_AUTOMATION = {'Mathlib.Meta.NormNum.':'norm_num', 'Mathlib.Meta.Positivity.':'positivity',
               'Mathlib.Tactic.Linarith.':'linarith'}
_AUTOMATION_TEXT = {'norm_num':'Numerical evaluation (norm_num) verifies this; the computation is not expanded.',
                    'positivity':'Sign analysis (positivity) proves this; the certificate is not expanded.',
                    'linarith':'Linear arithmetic (linarith) proves this; the certificate is not expanded.'}
# Numeral-cast facts that norm_num's numeral recognizers take as premises.
_NUMERAL_CASTS = {'Nat.cast_zero','Nat.cast_one'}
# Frontier rewrites export no equations; the text names only what the head itself does.
_REWRITE_TEXT = {
    'Eq.mpr': 'Rewrite the goal to an equal proposition and prove that instead; neither the rewriting equation nor that proof is expanded.',
    'Eq.mp': 'Obtain this by rewriting another proposition into it; neither the rewriting equation nor the earlier proof is expanded.',
    'of_eq_true': 'This proposition is proved equal to True; that equation is not expanded.',
    'congrArg': 'Apply the same function to both sides of an equation that is not expanded.',
    'congrFun': 'Evaluate both sides of an equation between functions at the same argument; that equation is not expanded.',
    "congrFun'": 'This equation follows by congruence from an equation that is not expanded.',
    'congr': 'This equation follows by congruence from equations between the functions and between the arguments; they are not expanded.'}
# Unexplained steps whose conclusion a parent `have` or `choose` already states.
_RESTATED = {'citation','project-citation','automation','restatement','rewrite','ring'}
_CLASS_HEAD = re.compile(r"[A-Z][\w'₀-₉]*(?:\.[A-Za-z][\w'₀-₉]*)*")
_BASE = {'id','path','statement','role','head','context','children','premises','objects','budget_cut'}
_EXTRAS = {'binder','domain','value'}
_TOP = {'schema','theorem','lean_version','axioms','statement','frames','judgements_checked','formula_backend'}


def _string(s: Any, limit: int = 20000) -> None:
    require(isinstance(s,str) and len(s) <= limit and '\x00' not in s, 'Invalid narrative string')


class Snapshot:
    def __init__(self, record: dict):
        require(isinstance(record,dict) and set(record) == _TOP, 'Unknown or missing snapshot fields')
        self.record = copy.deepcopy(record)
        r = self.record
        require(r['schema'] == SCHEMA, 'Unsupported narrative schema')
        _string(r['theorem']); _string(r['statement'],100000)
        require(isinstance(r['lean_version'],str) and bool(re.fullmatch(r'4\.\d+\.\d+',r['lean_version'])), 'Invalid exact Lean version')
        require(r['formula_backend'] == 'Lean pretty-printer', 'Unknown formula backend')
        ax = r['axioms']
        require(isinstance(ax,list) and all(isinstance(x,str) for x in ax) and len(set(ax)) == len(ax), 'Invalid axiom list')
        require(set(ax) <= STANDARD_AXIOMS, 'Snapshot has nonstandard or incomplete axioms')
        self.frames = r['frames']
        require(isinstance(self.frames,list) and 0 < len(self.frames) <= 1000, 'Narrative frame budget')
        require(type(r['judgements_checked']) is int and r['judgements_checked'] == len(self.frames), 'Judgement inventory mismatch')
        parents: dict[int,int] = {}
        paths = set()
        for i, f in enumerate(self.frames):
            require(isinstance(f,dict) and _BASE <= set(f) and set(f) <= _BASE | _EXTRAS | {'local_index'}, 'Invalid frame fields')
            require(type(f['id']) is int and f['id'] == i, 'Noncanonical frame id')
            path = f['path']
            require(isinstance(path,list) and len(path) <= 4096 and all(type(x) is int and x in (0,1,2) for x in path), 'Invalid proof path')
            require(tuple(path) not in paths, 'Repeated source path')
            paths.add(tuple(path))
            require(isinstance(f['role'],str) and f['role'] in ROLES and type(f['budget_cut']) is bool, 'Invalid frame role or budget flag')
            for k in ('statement','head'):
                _string(f[k])
            role,head = f['role'],f['head']
            if head.startswith('Mathlib.Tactic.Ring.'):
                require(role == 'ring', 'Arithmetic role mismatch')
            elif head in _REWRITES:
                require(role == 'rewrite' or (head == 'congrArg' and role == 'congruence'), 'Rewrite role mismatch')
            elif head in _HEAD_ROLES and not f['budget_cut']:
                require(role == _HEAD_ROLES[head] or (head == 'rfl' and role == 'application')
                        or (role == 'specialize' and head in _SPECIALIZATION_ARITIES), 'Logical rule mismatch')
            require(isinstance(f['context'],list) and len(f['context']) <= 256, 'Context budget')
            for c in f['context']:
                require(isinstance(c,dict) and set(c) == {'name','type'}, 'Invalid context entry')
                _string(c['name']); _string(c['type'])
            require(isinstance(f['objects'],list) and len(f['objects']) <= 256, 'Object argument budget')
            for x in f['objects']:
                _string(x)
            ch = f['children']
            require(isinstance(ch,list) and all(type(j) is int for j in ch) and len(set(ch)) == len(ch), 'Invalid child list')
            for j in ch:
                require(type(j) is int and i < j < len(self.frames) and j not in parents, 'Invalid narrative tree')
                parents[j] = i
            require(isinstance(f['premises'],list) and len(f['premises']) <= 256, 'Invalid premises')
            arguments = []
            for p in f['premises']:
                require(isinstance(p,dict) and set(p) == {'argument','statement','frame'}, 'Invalid premise fields')
                require(type(p['argument']) is int and 0 <= p['argument'] <= 256 and type(p['frame']) is int and p['frame'] in ch, 'Invalid premise reference')
                arguments.append(p['argument']); _string(p['statement'])
            require(arguments == sorted(set(arguments)), 'Repeated or unordered argument indices')
            if role in {'introduce','assume','define','have'}:
                require({'binder','domain'} <= set(f), 'Missing binder metadata')
                require(len(ch) == (2 if role == 'have' else 1) and not f['premises'], 'Invalid binder children')
            if role == 'specialize':
                require(head in _SPECIALIZATION_ARITIES, 'Unsupported specialization head')
                extra=len(f['objects'])+len(f['premises'])
                require(extra > 0 and len(ch)==len(f['premises'])+1
                        and ch[1:]==[p['frame'] for p in f['premises']], 'Missing quantified/conditional source proof')
                require(isinstance(self.frames[ch[0]],dict) and self.frames[ch[0]].get('path')==path+[0]*extra, 'Specialization prefix path mismatch')
                arity=_SPECIALIZATION_ARITIES[head]
                require(all(arity <= p['argument'] < arity+extra for p in f['premises']), 'Specialization argument mismatch')
            if role == 'local-application':
                require({'binder','domain','local_index'} <= set(f) and head == '', 'Invalid local application metadata')
                k=f['local_index']
                require(type(k) is int and 0 <= k < len(f['context']), 'Local application escaped its context')
                require(f['context'][k] == {'name':f['binder'],'type':f['domain']}, 'Local application context mismatch')
            elif 'local_index' in f:
                raise InvalidExport('Unexpected local application index')
            if role == 'define':
                require('value' in f, 'Missing definition value')
            if role == 'given':
                require('binder' in f and not ch, 'Invalid hypothesis frame')
            if role in {'ring','rewrite'}:
                require(not ch and not f['premises'], 'A frontier cannot contain unaccounted children')
            for k in _EXTRAS & set(f):
                _string(f[k])
        require(self.frames[0]['path'] == [] and self.frames[0]['context'] == [], 'Missing root frame')
        require(self.frames[0]['statement'] == r['statement'], 'Root statement mismatch')
        require(set(parents) == set(range(1,len(self.frames))), 'Unreachable frames')
        self.parents = parents
        depths = {0:0}
        for i in range(1,len(self.frames)):
            depths[i] = depths[parents[i]] + 1
            require(depths[i] <= 160, 'Narrative tree depth limit')
            f, parent = self.frames[i], self.frames[parents[i]]
            prefix = parent['path']
            require(len(f['path']) > len(prefix) and f['path'][:len(prefix)] == prefix, 'Child escaped source scope')
            pc,fc = parent['context'],f['context']
            if parent['role'] in {'introduce','assume','have','define'}:
                is_body = i == parent['children'][-1]
                suffix = [1] if parent['role'] in {'introduce','assume'} else [2 if is_body else 1]
                require(f['path'] == prefix+suffix, 'Binder/body path mismatch')
                expected = pc + ([{'name':parent['binder'],'type':parent['domain']}] if is_body else [])
                require(fc == expected, 'Binder context mismatch')
            else:
                require(fc == pc, 'Application changed local context')
        for f in self.frames:
            for p in f['premises']:
                require(p['statement'] == self.frames[p['frame']]['statement'], 'Premise conclusion mismatch')
        self.sha256 = digest(canonical_json(r))

    @classmethod
    def read(cls, path: Path | str) -> 'Snapshot':
        data = Path(path).read_bytes()
        # The retained corpus includes a 38 MB snapshot; the 1,000-frame budget still bounds its structure.
        require(len(data) <= 64_000_000, 'Narrative input too large')
        return cls(strict_json(data))

    def coverage(self) -> dict:
        return {'frames':len(self.frames), 'roles':dict(sorted(Counter(f['role'] for f in self.frames).items())),
                'budget_cuts':sum(f['budget_cut'] for f in self.frames),
                'recorded_kernel_judgements':self.record['judgements_checked'],
                'receipt_authenticated':False,'english_formally_verified':False,
                'source_replayed_by_loading':False}


def math_text(s: str) -> str:
    # Display only: inside a reading, notation.py then shortens names and
    # rewrites a few recognized library forms. Checks never read this text.
    return notation.display(_math_dictionary(s))


def _math_dictionary(s: str) -> str:
    """A small notation dictionary, not a free-form algebra simplifier.

    The exact Lean strings remain in every source-bound frame. Only recognized
    fully qualified gcd symbols with atomic arguments receive ordinary notation.
    """
    atom = r'([^\W\d]\w*|[0-9]+)'
    for constant, shown in [('gcdA','gcdA'),('gcdB','gcdB'),('gcd','gcd')]:
        s = re.sub(r'\bEuclideanDomain\.'+constant+r'\s+'+atom+r'\s+'+atom+r'(?![\w.])',
                   lambda m: f'{shown}({m[1]}, {m[2]})',s,flags=re.UNICODE)
    for symbol, explanation in [('IsDomain', 'an integral domain'),
                                 ('IsCancelMulZero', 'a ring with cancellation away from zero'),
                                 ('IsLeftCancelMulZero', 'a ring with left cancellation away from zero')]:
        m = re.fullmatch(symbol+r' ([^\W\d]\w*)', s, flags=re.UNICODE)
        if m:
            return m[1]+' is '+explanation
    s = s.replace(' * ',' · ').replace(' - ',' − ')
    m = re.fullmatch(r'¬([^\W\d]\w*) = 0',s.strip(),re.UNICODE)
    if m:
        return m[1]+' ≠ 0'
    return s


def _name(s: str) -> str:
    # Internal binder labels are not shown as mathematical objects.
    return s.split('._@.',1)[0]



def _class_application(text: str) -> str | None:
    """The constant C of a plain proposition C a₁ … aₙ (n ≥ 1), else None."""
    text = _plain_proposition(text)
    m = _CLASS_HEAD.match(text or '')
    return m[0] if m and text[m.end():m.end()+1] == ' ' else None


def _automation(head: str) -> str | None:
    return next((name for prefix, name in _AUTOMATION.items() if head.startswith(prefix)), None)


def _project(head: str) -> bool:
    return head.startswith('OAI.') or head.startswith('_private.OAI.')


def _citation(head: str) -> tuple[str,str]:
    """Wording and rule for a cited constant whose proof is not expanded here.

    The rule (project-citation for OAI.*, otherwise citation), not this
    wording, is what corpus measurements count. Lean-generated auxiliary
    names are described from their recorded suffix.
    """
    rule = 'project-citation' if _project(head) else 'citation'
    m = re.fullmatch(r'(.+)\._simp_\d+', head)
    if m:
        return 'By '+notation.name(m[1])+' (in the equational form generated for simp):', rule
    m = re.fullmatch(r'(.+)\._proof_\d+(?:_\d+)*', head)
    if m:
        return 'By an auxiliary proof that Lean extracted while elaborating '+notation.name(m[1])+':', rule
    if _project(head):
        kind = 'instance' if re.match(r'inst[A-Z]', head.rsplit('.',1)[-1]) else 'lemma'
        return 'By the project '+kind+' '+notation.name(head)+':', rule
    return 'By '+notation.name(head)+':', rule




class Narrative(ReadingRules):
    def __init__(self, record: dict):
        self.snapshot = Snapshot(record)
        self.frames = self.snapshot.frames
        self.prefix = self.snapshot.sha256[:16]
        self.owners: dict[int,str] = {}
        self.certificates: dict[int,dict] = {}
        for f in self.frames:
            if f['role'] in {'ring','rewrite'}:
                c = certify(f)
                if c is not None:
                    verify_polynomial(f,c)
                    self.certificates[f['id']] = c
        self.heads: set[str] = set()
        self._instances: dict[int,bool] = {}

    def sid(self, i: int) -> str:
        return 'n'+self.prefix+':'+str(i)

    def claim(self, step: Step, ids: list[int]) -> Step:
        for i in ids:
            require(i not in self.owners, 'A snapshot frame was displayed twice')
            self.owners[i] = step.id
            # Absorbed frames still contribute their constants to the dependency list.
            if self.frames[i]['head']:
                self.heads.add(self.frames[i]['head'])
        step.term_id = ','.join('f'+str(i) for i in ids)
        paths = ['f'+str(i)+'='+(''.join(map(str,self.frames[i]['path'])) or 'root') for i in ids]
        step.detail += '\nOriginal proof paths: '+ '; '.join(paths)
        return step

    def step(self, i: int, text: str, *, rule: str | None = None,
             children: list[Step] | None = None, conclusion: str | None = None,
             fallback: bool = False, covered: list[int] | None = None, detail: str = '',
             references: list[str] | None = None) -> Step:
        f = self.frames[i]
        s = Step(self.sid(i),rule or f['role'],text,evidence='source-bound-snapshot',
                 conclusion=conclusion,children=children or [],context=f['context'],
                 source=f['statement'],references=references or ([f['head']] if f['head'] else []),
                 fallback=fallback or any(self.frames[j]['budget_cut'] for j in covered or [i]),detail=detail)
        return self.claim(s,covered or [i])

    def instance(self, i: int) -> bool:
        """A typeclass side condition, recognized only from recorded names and statements.

        Hypotheses qualify only by Lean's automatic instance-binder name and a
        plain proposition. Instance-named heads (instX, inferInstance) qualify
        with a plain statement; their other premises stay visible. A parent
        projection X.toC proving C …, or a reviewed class statement from a
        non-constructor head, qualifies only if every premise is an instance:
        Ergodic.toMeasurePreserving h is a theorem about h. A binder over an
        instance family, ∀ i, C (β i), qualifies through its body. Project
        (OAI.*) heads, dictionary lemmas, budget cuts and certified frames never do.
        """
        if i in self._instances:
            return self._instances[i]
        f = self.frames[i]; head = f['head']; last = head.rsplit('.',1)[-1]; ok = False
        if f['budget_cut'] or i in self.certificates:
            ok = False
        elif f['role'] == 'given':
            # A named hypothesis such as hPM : Nonempty G.Matching is mathematics, not plumbing.
            ok = _INSTANCE_BINDER.fullmatch(_name(f['binder'])) is not None and _plain_proposition(f['statement']) is not None
        elif f['role'] == 'introduce':
            ok = len(f['children']) == 1 and self.instance(f['children'][0])
        elif f['role'] in {'application','named'} and head and head not in _LEMMAS and not _project(head):
            cls = _class_application(f['statement'])
            if re.match(r'inst(?:[A-Z]|$)', last) or head in {'inferInstance','inferInstanceAs'}:
                ok = _plain_proposition(f['statement']) is not None
            elif cls is not None:
                ok = ((last == 'to'+cls.rsplit('.',1)[-1] or (cls in _INSTANCE_CLASSES and last not in {'mk','intro'}))
                      and all(self.instance(j) for j in f['children']))
        self._instances[i] = ok
        return ok

    def instance_parts(self, roots: list[int]) -> tuple[list[int],list[int]]:
        """Instance frames below the roots, and the non-instance premises they rest on."""
        covered, visible = [], []
        def walk(j: int) -> None:
            covered.append(j)
            for k in self.frames[j]['children']:
                (walk if self.instance(k) else visible.append)(k)
        for r in roots:
            walk(r)
        return covered, visible

    def instance_step(self, roots: list[int]) -> Step:
        """One line for a parent's typeclass side conditions; not "Standard" if a premise stays visible."""
        covered, visible = self.instance_parts(roots)
        assumed = all(self.frames[r]['role'] == 'given' for r in roots)
        facts = list(dict.fromkeys(math_text(self.frames[r]['statement']) for r in roots))
        plural = 's' if len(facts) > 1 else ''
        # A derivation through a local instance hypothesis is not called standard.
        local = [] if assumed else self.local_instances(covered)
        label = ('Instance assumption'+plural+' used: ' if assumed else
                 'Instance fact'+plural+' used, derived using the premise'+('s' if len(visible) > 1 else '')+' below: ' if visible else
                 'Instance fact'+plural+' used: ' if local else
                 'Standard instance fact'+plural+' used: ')
        note = (' The derivation '+('also ' if visible else '')+'uses the local instance hypothes'+('es ' if len(local) > 1 else 'is ')
                +'; '.join(local)+'.' if local else '')
        lines = [math_text(self.frames[j]['statement'])+' — '+(self.frames[j]['head'] or
                 ('hypothesis '+_name(self.frames[j]['binder']) if self.frames[j]['role'] == 'given' else 'for each '+_name(self.frames[j]['binder'])))
                 for j in covered]
        heads = list(dict.fromkeys(self.frames[j]['head'] for j in covered if self.frames[j]['head']))
        return self.step(roots[0], label+'; '.join(facts)+'.'+note, rule='instance-assumptions' if assumed else 'instance-facts',
                         covered=covered, fallback=not assumed, references=heads,
                         children=[s for j in visible for s in self.sequence(j)],
                         detail='Typeclass derivations (not expanded):\n'+'\n'.join(lines))

    def descendants(self, i: int) -> list[int]:
        out, stack = [], [i]
        while stack:
            j = stack.pop(); out.append(j); stack.extend(self.frames[j]['children'])
        return out

    def unpacked(self, i: int) -> tuple[dict,dict] | None:
        """The two binders of an exact And.casesOn destructuring at frame i, else None."""
        f = self.frames[i]; ch = f['children']
        if not (f['role'] == 'application' and f['head'] == 'And.casesOn' and not f['budget_cut'] and len(ch) == 2
                and len(f['objects']) == 3 and [p['argument'] for p in f['premises']] == [3, 4]):
            return None
        left = self.frames[ch[1]]
        right = (self.frames[left['children'][0]]
                 if left['role'] == 'assume' and len(left['children']) == 1 else {})
        norm = lambda text: ' '.join(text.split())
        if (right.get('role') == 'assume' and len(right['children']) == 1
                and not left['budget_cut'] and not right['budget_cut']
                and norm(left['domain']) == norm(f['objects'][0])
                and norm(right['domain']) == norm(f['objects'][1])):
            return left, right
        return None

    def named_conjunction(self, i: int) -> bool:
        """The destructured proof is a hypothesis printed exactly as its two parts joined by ∧."""
        f = self.frames[i]; g = self.frames[f['children'][0]]
        return g['role'] == 'given' and not g['budget_cut'] and _joins_conjunction(g['statement'], *f['objects'][:2])

    def stated(self, steps: list[Step], statement: str) -> list[Step]:
        """Do not repeat, under a sole unexplained proof, the claim its parent just stated."""
        if (len(steps) == 1 and steps[0].rule in _RESTATED and steps[0].conclusion is not None
                and _same_formula(steps[0].source, statement)):
            steps[0].conclusion = None
            if steps[0].text.endswith(':'):
                steps[0].text = steps[0].text[:-1]+'.'
        return steps

    def introducer(self, i: int) -> str | None:
        """Role of the nearest enclosing binder frame that brought frame i's binder into scope."""
        name, j = self.frames[i]['binder'], i
        while j in self.snapshot.parents:
            child, j = j, self.snapshot.parents[j]
            g = self.frames[j]
            if g['role'] in {'introduce','assume','have','define'} and g['binder'] == name and child == g['children'][-1]:
                return g['role']
        return None

    def subproofs(self, ids: list[int]) -> list[Step]:
        """Displayed child proofs; typeclass side conditions follow the mathematical premises."""
        instances = [j for j in ids if self.instance(j)]
        steps = [s for j in ids if j not in instances for s in self.sequence(j)]
        for assumed in (False, True):
            group = [j for j in instances if (self.frames[j]['role'] == 'given') == assumed]
            if group:
                steps.append(self.instance_step(group))
        return steps

    def automation_step(self, i: int, family: str) -> Step:
        """Collapse a decision procedure's certificate into one unexplained step.

        Only that procedure family's lemmas, numeral reflexivity checks, norm_num's
        numeral casts, typeclass side conditions and, for linarith, its frontier
        rewrites are absorbed. Anything else, including hypotheses, project
        lemmas and certified frames, remains a visible child step.
        """
        covered, visible = [], []
        def visit(j: int, parent: str) -> None:
            g = self.frames[j]
            if j != i and j in self.certificates:
                visible.append(j)
            elif (j == i or _automation(g['head']) or (g['role'] == 'reflexivity' and not g['children'])
                    or (g['head'] in _NUMERAL_CASTS and not g['children'] and parent.startswith('Mathlib.Meta.NormNum.'))
                    or (family == 'linarith' and g['role'] == 'rewrite')):
                covered.append(j)
                for k in g['children']:
                    visit(k, g['head'])
            elif self.instance(j):
                inner, below = self.instance_parts([j])
                covered.extend(inner); visible.extend(below)
            else:
                visible.append(j)
        visit(i, '')
        f = self.frames[i]
        contradiction = family == 'linarith' and _same_formula(f['statement'], 'False')
        text = ('Linear arithmetic (linarith) derives a contradiction; the certificate is not expanded.'
                if contradiction else _AUTOMATION_TEXT[family])
        heads = list(dict.fromkeys(self.frames[j]['head'] for j in covered if self.frames[j]['head']))
        return self.step(i, text, rule='automation', conclusion=None if contradiction else math_text(f['statement']),
                         children=[s for j in visible for s in self.sequence(j)], covered=covered, fallback=True,
                         references=heads, detail='Automation family: '+family+'; '+str(len(covered))+' certificate frames absorbed.')

    def flat_chain(self, i: int) -> tuple[list[int],list[int]]:
        f = self.frames[i]
        if f['role'] != 'chain' or len(f['children']) != 2:
            return [i],[]
        left, li = self.flat_chain(f['children'][0]); right, ri = self.flat_chain(f['children'][1])
        return left+right,[i]+li+ri

    def flat_conjunction(self, i: int) -> tuple[list[int],list[int]]:
        f = self.frames[i]
        if f['role'] != 'combine' or len(f['children']) != 2:
            return [i],[]
        a,ai = self.flat_conjunction(f['children'][0]);b,bi = self.flat_conjunction(f['children'][1])
        return a+b,[i]+ai+bi

    def logical_application(self, i: int, object_count: int, premise_slots: list[int], role: str = 'application') -> bool:
        """Recognize a fully applied rule at the exact original argument paths."""
        f = self.frames[i]
        arity = object_count + len(premise_slots)
        return (f['role'] == role and not f['budget_cut']
                and len(f['objects']) == object_count
                and [p['argument'] for p in f['premises']] == premise_slots
                and f['children'] == [p['frame'] for p in f['premises']]
                and all(0 <= p['argument'] < arity
                        and self.frames[p['frame']]['path'] == f['path'] + [0]*(arity-p['argument']-1) + [1]
                        and self.frames[p['frame']]['context'] == f['context']
                        for p in f['premises']))

    def implication_premise(self, i: int, left: str, right: str) -> bool:
        f = self.frames[i]
        if not _implication_formula(f['statement'], left, right):
            return False
        if f['role'] == 'assume':
            return (_same_formula(f['domain'], left)
                    and _same_formula(self.frames[f['children'][0]]['statement'], right))
        return True

    def implication_direction(self, i: int, label: str) -> Step:
        """Keep each direction's assumption inside its own displayed subproof."""
        f = self.frames[i]
        if f['role'] == 'assume':
            return self.step(i, label + ': assume ' + math_text(f['domain']) + '.',
                             rule='implication-direction', children=self.sequence(f['children'][0]))
        steps = self.sequence(i)
        require(len(steps) == 1, 'Logical direction requires a single scoped source proof')
        steps[0].text = label + '. ' + steps[0].text
        return steps[0]

    def logical_steps(self, i: int) -> list[Step] | None:
        """Conservative explanations of small logical inferences, never new proofs.

        The rule's argument inventory, context, paths and printed types must all
        agree. No descendant is absorbed: unknown premises and budget cuts keep
        their own steps. Definitionally equal but differently printed statements
        deliberately remain outside these specializations.
        """
        f = self.frames[i]
        head, ch, objects = f['head'], f['children'], f['objects']
        con = math_text(f['statement'])
        if head in {'And.left', 'And.right'} and self.logical_application(i, 2, [2]):
            left, right = objects
            component = left if head == 'And.left' else right
            if self.projected(self.frames[ch[0]]['statement'], left, right) and _same_formula(f['statement'], component):
                side = 'first' if head == 'And.left' else 'second'
                return [self.step(i, 'Take the ' + side + ' conjunct, ' + con + '.',
                                  rule='conjunction-projection', children=self.sequence(ch[0]))]
            if _same_formula(f['statement'], component):
                # Typically membership in an interval or a definition that Lean
                # unfolds; the printed premise is not compared with the conjunction.
                side, other = ('first', 'second') if head == 'And.left' else ('second', 'first')
                return [self.step(i, 'Take the ' + side + ' conjunct, ' + con + ', of the premise below; its ' + other
                                  + ' conjunct is ' + math_text(right if head == 'And.left' else left)
                                  + '. That the premise has this form is not checked here.',
                                  rule='unchecked-projection', fallback=True, children=self.sequence(ch[0]))]
        if head == 'Iff.mpr' and self.logical_application(i, 2, [2,3]):
            left, right = objects
            if (self.equivalent(self.frames[ch[0]]['statement'], left, right)
                    and _same_formula(self.frames[ch[1]]['statement'], right)
                    and _same_formula(f['statement'], left)):
                text = ('Use the reverse direction of ' + math_text(self.frames[ch[0]]['statement'])
                        + ': from ' + math_text(right) + ', obtain ' + con + '.')
                return [self.step(i, text, rule='equivalence-reverse',
                                  children=[s for j in ch for s in self.sequence(j)])]
        if head == 'Iff.intro' and self.logical_application(i, 2, [2,3]):
            left, right = objects
            # These roles can emit a sequence spanning several scopes. They are
            # kept as gaps until a source-bound direction wrapper is supported.
            sequential = {'introduce','define','have','choose','identity','witness'}
            if (_binary_formula(f['statement'], '↔', left, right)
                    and self.implication_premise(ch[0], left, right)
                    and self.implication_premise(ch[1], right, left)
                    and all(self.frames[j]['role'] not in sequential
                            and self.frames[j]['head'] != 'And.casesOn' for j in ch)):
                return [self.step(i, 'Prove both directions of the equivalence.',
                    rule='equivalence-introduction', conclusion=con,
                    children=[self.implication_direction(ch[0], 'Forward direction'),
                              self.implication_direction(ch[1], 'Reverse direction')])]
        if head in {'Or.inl', 'Or.inr'} and self.logical_application(i, 2, [2]):
            left, right = objects
            chosen = left if head == 'Or.inl' else right
            if (_binary_formula(f['statement'], '∨', left, right)
                    and _same_formula(self.frames[ch[0]]['statement'], chosen)):
                side = 'left' if head == 'Or.inl' else 'right'
                return [self.step(i, 'Establish the ' + side + ' alternative, ' + math_text(chosen) + '.',
                                  rule='disjunction-introduction', conclusion=con,
                                  children=self.sequence(ch[0]))]
        if head == 'False.elim' and self.logical_application(i, 1, [1]):
            if (_same_formula(objects[0], f['statement'])
                    and _same_formula(self.frames[ch[0]]['statement'], 'False')):
                return [self.step(i, 'The contradiction False implies the required conclusion.',
                                  rule='false-elimination', conclusion=con, children=self.sequence(ch[0]))]
        if head == 'Not.intro' and self.logical_application(i, 1, [1]):
            if (_negation_formula(f['statement'], objects[0])
                    and self.implication_premise(ch[0], objects[0], 'False')):
                return [self.step(i, 'To prove ' + con + ', derive False from ' + math_text(objects[0]) + '.',
                                  rule='negation-introduction', children=self.sequence(ch[0]))]
        if head in {'Decidable.byContradiction', 'Classical.byContradiction'}:
            count = 2 if head == 'Decidable.byContradiction' else 1
            if self.logical_application(i, count, [count]):
                premise = self.frames[ch[0]]
                negative = _negated_operand(premise['statement'])
                if (negative is not None and _negation_formula(negative, objects[0])
                        and _same_formula(f['statement'], objects[0])
                        and self.implication_premise(ch[0], negative, 'False')):
                    basis = ('the recorded decision instance' if count == 2 else 'classical logic')
                    text = ('Prove ' + con + ' by contradiction, using ' + basis
                            + '. Assuming its negation leads to False as follows.')
                    return [self.step(i, text, rule='contradiction-proof', children=self.sequence(ch[0]))]
        # cast {α β} (h : α = β) (a : α) : β, with both printed sides matching.
        if head == 'cast' and self.logical_application(i, 2, [2,3]):
            sides = _equation_sides(self.frames[ch[0]]['statement'])
            if (sides is not None and _same_formula(sides[0], objects[0]) and _same_formula(sides[1], objects[1])
                    and _same_formula(self.frames[ch[1]]['statement'], objects[0])
                    and _same_formula(f['statement'], objects[1])):
                return [self.step(i, 'From ' + math_text(objects[0]) + ', obtain ' + con
                                  + ' by rewriting with the equation of propositions below.', rule='transport',
                                  children=[s for j in ch for s in self.sequence(j)])]
        # These two rules currently have synthetic regression coverage only.
        if head == 'Not.elim' and self.logical_application(i, 1, [1,2]):
            if (_negation_formula(self.frames[ch[0]]['statement'], objects[0])
                    and _same_formula(self.frames[ch[1]]['statement'], objects[0])
                    and _same_formula(f['statement'], 'False')):
                return [self.step(i, 'The supplied proposition and its negation contradict each other.',
                                  rule='negation-elimination', conclusion=con,
                                  children=[s for j in ch for s in self.sequence(j)])]
        if head == 'absurd' and self.logical_application(i, 2, [2,3]):
            if (_same_formula(self.frames[ch[0]]['statement'], objects[0])
                    and _negation_formula(self.frames[ch[1]]['statement'], objects[0])
                    and _same_formula(f['statement'], objects[1])):
                return [self.step(i, 'The supplied proposition and its negation yield a contradiction, which implies the conclusion.',
                                  rule='contradiction-elimination', conclusion=con,
                                  children=[s for j in ch for s in self.sequence(j)])]
        return None

    def sequence(self, i: int) -> list[Step]:
        f = self.frames[i]; ch=f['children']; role=f['role']; con=math_text(f['statement'])
        if self.instance(i):
            return [self.instance_step([i])]
        family = _automation(f['head'])
        if family and role == 'application':
            return [self.automation_step(i, family)]
        logical = self.logical_steps(i)
        if logical is None and role in {'witness', 'choose', 'application'}:
            logical = (self.proof_witness(i) if role == 'witness' else self.proof_cases(i) if role == 'choose'
                       else self.applied_projection(i) or self.nonempty_element(i))
        if logical is not None:
            return logical
        if role in {'define','have'}:
            name=_name(f['binder']); domain=math_text(f['domain'])
            if role=='define':
                value=math_text(f['value'])
                note = (' This is the first Bézout coefficient.' if f['value'].startswith('EuclideanDomain.gcdA ') else
                        ' This is the second Bézout coefficient.' if f['value'].startswith('EuclideanDomain.gcdB ') else '')
                s=self.step(i,f'Set {name} = {value}.'+note,conclusion=None)
            else:
                label='.' if _ANONYMOUS.fullmatch(name) else f'; call this fact {name}.'
                s=self.step(i,f'Establish {domain}'+label,children=self.stated(self.sequence(ch[0]),f['domain']))
            return [s]+self.sequence(ch[-1])
        # Exact conjunction eliminator shape, not a guess from tactic text.
        # The continuation's two binders are retained in the ownership ledger;
        # their proofs and every step of the continuation remain inspectable.
        parts = self.unpacked(i)
        if parts is not None:
            left, right = parts
            text = ('From the conjunction, obtain ' + _name(left['binder']) + ': ' +
                    math_text(left['domain']) + ' and ' + _name(right['binder']) + ': ' +
                    math_text(right['domain']) + '.')
            if not self.named_conjunction(i):
                step = self.step(i, text, rule='unpack-conjunction',
                    children=self.sequence(ch[0]), covered=[i, left['id'], right['id']])
                return [step] + self.sequence(right['children'][0])
            # A hypothesis printed exactly as the displayed parts joined by ∧ is
            # named, not repeated; a part that is only destructured again in the
            # same way (rcases ⟨a, b, c⟩) is listed instead of its own name.
            g = self.frames[ch[0]]
            source = ('the fact established above' if _ANONYMOUS.fullmatch(_name(g['binder'])) and self.introducer(ch[0]) == 'have'
                      else _name(g['binder']))
            covered, names, j = [i, ch[0], left['id'], right['id']], [left], right
            while True:
                k = j['children'][0]; nested = self.unpacked(k)
                if (nested is None or not self.named_conjunction(k)
                        or self.frames[self.frames[k]['children'][0]]['binder'] != j['binder']
                        or sum(self.frames[m].get('binder') == j['binder'] and self.frames[m]['role'] in {'given','local-application'}
                               for m in self.descendants(k)) != 1):
                    break
                covered += [k, self.frames[k]['children'][0], nested[0]['id'], nested[1]['id']]
                names.append(nested[0]); j = nested[1]
            names.append(j)
            listed = [_name(b['binder']) + ': ' + math_text(b['domain']) for b in names]
            step = self.step(i, 'From ' + source + ', obtain ' + ', '.join(listed[:-1]) + ' and ' + listed[-1] + '.',
                             rule='unpack-conjunction', covered=covered)
            return [step] + self.sequence(j['children'][0])
        # Nonempty.casesOn {α} {motive} (t : Nonempty α) (h : ∀ a, motive ⟨a⟩)
        # with a constant motive: the goal is proved for an arbitrary element.
        if (role == 'application' and f['head'] == 'Nonempty.casesOn' and self.logical_application(i, 2, [2, 3])):
            intro = self.frames[ch[1]]
            body = intro['children'][0] if intro['role'] == 'introduce' and len(intro['children']) == 1 else None
            if (body is not None and not intro['budget_cut'] and _same_formula(intro['domain'], f['objects'][0])
                    and any(_same_formula(self.frames[ch[0]]['statement'], 'Nonempty '+t) for t in (f['objects'][0], '('+f['objects'][0]+')'))
                    and _same_formula(self.frames[body]['statement'], f['statement'])):
                text = ('Since ' + math_text(self.frames[ch[0]]['statement']) + ', choose ' + _name(intro['binder'])
                        + ' ∈ ' + math_text(intro['domain']) + '.')
                step = self.step(i, text, rule='choose-element', children=self.sequence(ch[0]), covered=[i, intro['id']])
                return [step] + self.sequence(body)
        # Eq.ndrec/Eq.rec {α} {a} {motive} (m : motive a) {b} (h : a = b) …: the
        # motive is not displayed, so this stays a gap. The equation is h's own
        # statement: joining a and b with = misreads a = fun x => t.
        if (role == 'application' and f['head'] in {'Eq.ndrec', 'Eq.rec'} and len(f['objects']) >= 4
                and [p['argument'] for p in f['premises']][:2] == [3, 5]):
            extra = ', '.join(math_text(v) for v in f['objects'][4:]); more = len(f['premises']) > 2
            then = ((', then specialize the result to '+extra+(' and apply it to the further premises below' if more else ''))
                    if extra else ', then apply the result to the further premises below' if more else '')
            text = ('Rewrite the statement proved below along the equation ' + math_text(f['premises'][1]['statement'])
                    + then + '; which occurrences are rewritten is not displayed.')
            return [self.step(i, text, rule='substitution', conclusion=con, fallback=True, children=self.subproofs(ch))]
        # id has exactly one type argument and one proof argument here. Other,
        # oversaturated identity applications retain the existing explicit gap.
        if (role == 'identity' and not f['budget_cut'] and len(ch) == 1
                and len(f['objects']) == 1
                and [p['argument'] for p in f['premises']] == [1]
                and f['statement'] == self.frames[ch[0]]['statement']):
            return [self.step(i, 'The supplied proof establishes ' + con + '.',
                              rule='identity-proof', children=self.sequence(ch[0]))]
        if role=='specialize' and ch:
            claim=math_text(self.frames[ch[0]]['statement'])
            text='Use the intermediate claim '+claim+'.'
            if f['objects']:
                text+=' Specialize its object arguments to '+', '.join(math_text(v) for v in f['objects'])+'.'
            if f['premises']:
                text+=' Apply it to the additional premises shown below.'
            return [self.step(i,text,conclusion=con,children=self.subproofs(ch))]
        if role=='local-application':
            name=_name(f['binder'])
            if sum(c['name']==f['binder'] for c in f['context'])>1:
                name+=' (context entry '+str(f['local_index']+1)+')'
            text='Apply the hypothesis '+name+': '+math_text(f['domain'])+'.'
            if f['objects']:
                text+=' Substitute '+', '.join(math_text(v) for v in f['objects'])+' for its object arguments.'
            return [self.step(i,text,conclusion=con,children=self.subproofs(ch))]
        if role=='named' and f['head']=='True.intro' and not ch and f['statement']=='True':
            return [self.step(i,'The conclusion is the proposition True.',conclusion=None)]
        recursor_proofs = {'Nat.rec':[1,2], 'Nat.recAux':[1,2], 'Nat.recOn':[2,3],
                           'List.rec':[2,3], 'List.recOn':[3,4]}
        # Do not mistake an argument supplied *after* a recursor for its major
        # induction variable. Oversaturated/dependent variants stay explicit gaps.
        if (role=='induction' and len(ch)==2 and f['head'] in recursor_proofs
            and [p['argument'] for p in f['premises']]==recursor_proofs[f['head']]
            and len(f['objects'])==(2 if f['head'].startswith('Nat.') else 3)):
            # These constructor recursors are recognized by exact fully qualified
            # names, not an inferred tactic label or a theorem-specific template.
            major_slot={'Nat.rec':3,'Nat.recAux':3,'Nat.recOn':1,'List.rec':4,'List.recOn':2}[f['head']]
            object_slots=[k for k in range(len(f['objects'])+len(f['premises']))
                          if k not in recursor_proofs[f['head']]]
            branches=[self.sequence(j) for j in ch]
            labels=('Base case (zero). ', 'Successor step. ') if f['head'].startswith('Nat.') else ('Empty-list case. ', 'Constructor step. ')
            for branch,label in zip(branches,labels):
                if branch:
                    branch[0].text=label+branch[0].text
            return [self.step(i,'Proceed by induction on '+math_text(f['objects'][object_slots.index(major_slot)])+'.',
                              conclusion=con,children=[s for branch in branches for s in branch])]
        if role=='congruence' and f['head']=='congrArg' and len(ch)==1 and len(f['objects'])==5 and [p['argument'] for p in f['premises']]==[5]:
            return [self.step(i,'Apply '+math_text(f['objects'][-1])+' to both sides of the supplied equality.',
                              conclusion=con,children=self.sequence(ch[0]))]
        if role=='cases' and f['head'] in {'Or.elim','Or.casesOn'} and len(ch)==3 and all(self.frames[j]['role']=='assume' for j in ch[1:]):
            branches=self.sequence(ch[0])
            for j in ch[1:]:
                b=self.frames[j]
                branches.append(self.step(j,'Case '+math_text(b['domain'])+'.',rule='case',
                                          children=self.sequence(b['children'][0])))
            return [self.step(i,'Reason by cases from '+math_text(self.frames[ch[0]]['statement'])+'.',children=branches)]
        if role=='cases' and len(ch)==2 and all(self.frames[j]['role']=='assume' for j in ch):
            branches=[]
            for j in ch:
                b=self.frames[j]
                if b['role']=='assume':
                    branches.append(self.step(j,'Case '+math_text(b['domain'])+'.',rule='case',children=self.sequence(b['children'][0])))
                else:
                    branches.extend(self.sequence(j))
            return [self.step(i,'Consider the following cases.',children=branches)]
        if role=='choose' and len(ch)==2:
            intro=self.frames[ch[1]]
            assumption=self.frames[intro['children'][0]] if intro['role']=='introduce' and intro['children'] else {}
            if assumption.get('role')=='assume':
                fact=math_text(self.frames[ch[0]]['statement'])
                name=_name(intro['binder']);typ=math_text(intro['domain']); prop=math_text(assumption['domain'])
                s=self.step(i,f'Since {fact}, choose {name} ∈ {typ} with {prop}.',
                            children=self.stated(self.sequence(ch[0]),self.frames[ch[0]]['statement']),
                            covered=[i,intro['id'],assumption['id']])
                return [s]+self.sequence(assumption['children'][0])
        if role=='identity' and len(ch)==2 and self.frames[ch[0]]['role']=='assume':
            binder=self.frames[ch[0]]
            s=self.step(i,'Use the same hypothesis in the form '+math_text(binder['domain'])+'.',
                        rule='equivalent-assumption',children=self.sequence(ch[1]),covered=[i,binder['id']])
            return [s]+self.sequence(binder['children'][0])
        if role=='witness':
            ids=[]; names=[]; values=[]; j=i
            while self.frames[j]['role']=='witness' and len(self.frames[j]['children'])==1:
                b=self.frames[j]
                if len(b['objects'])!=3:
                    break
                match=re.match(r'^∃\s+([^\s,:]+)',b['statement'])
                if match is None:
                    break
                ids.append(j);names.append(match[1]);values.append(math_text(b['objects'][-1]));j=b['children'][0]
            if ids:
                text='Take '+(', '.join(names) if len(names)==1 else '('+', '.join(names)+')')+' = '+(values[0] if len(values)==1 else '('+', '.join(values)+')')+'.'
                s=self.step(i,text,covered=ids)
                return [s]+self.sequence(j)
            # A goal printed as a named definition (e.g. a MainStatement) that
            # Lean unfolds to ∃: the witness is recorded, the unfolding is not.
            if len(f['objects'])==3 and len(ch)==1 and [p['argument'] for p in f['premises']]==[3]:
                return [self.step(i,'Provide the witness '+math_text(f['objects'][-1])+'; the property it must satisfy is proved below. '
                                  'That the goal unfolds to an existential statement is not checked here.',
                                  conclusion=con,fallback=True,children=self.sequence(ch[0]))]
        if role=='combine' and len(ch)==2:
            leaves,parents=self.flat_conjunction(i)
            return [self.step(i,'Verify the '+str(len(leaves))+' required conclusions.',rule='verify-conclusions',
                              covered=parents,children=[s for j in leaves for s in self.sequence(j)])]
        if role=='chain' and len(ch)==2:
            leaves,parents=self.flat_chain(i)
            return [self.step(i,'The following calculation gives '+con+'.',rule='calculation',covered=parents,
                              children=[s for j in leaves for s in self.sequence(j)])]
        if i in self.certificates:
            c=self.certificates[i]
            assumptions=c['assumptions']
            if assumptions:
                basis=' and '.join(math_text(a['statement']) for a in assumptions)
                text='Using '+basis+', expand and collect terms.'
            else:
                text='Expand and collect terms.'
            return [self.step(i,text,rule='polynomial-identity',conclusion=con,
                              detail='Independent integer-polynomial certificate: '+certificate_text(c)+
                              '\nThis check is under the recorded local assumptions; it does not authenticate their Lean provenance.')]
        rule=None
        if role=='cancel':
            text='Cancel the nonzero common factor'+(' '+math_text(f['objects'][-3]) if len(f['objects'])>=3 else '')+' to obtain '+con+'.'
        elif role=='given' and _ANONYMOUS.fullmatch(_name(f['binder'])) and self.introducer(i)=='have':
            text='Use the fact '+con+' established above.'
        elif role=='given':
            text='Use the hypothesis '+_name(f['binder'])+': '+con+'.'
        elif role=='identity' and len(ch)==1 and len(f['objects'])==1 and [p['argument'] for p in f['premises']]==[1]:
            # id (α := claim) p with p printed differently: a kernel-checked
            # definitional restatement whose unfolding the snapshot does not record.
            text='Restate this in the definitionally equal form proved below; the unfolding is not expanded.'
            rule='restatement'
        elif role=='assume':
            text='Assume '+math_text(f['domain'])+'.'
        elif role=='introduce':
            text='Let '+_name(f['binder'])+' ∈ '+math_text(f['domain'])+' be arbitrary.'
        elif role=='reflexivity':
            text='By reflexivity, '+con+'.'
        elif f['head'] in _LEMMAS:
            text=_LEMMAS[f['head']]
        elif role=='rewrite' and f['head'] in _REWRITE_TEXT:
            text=_REWRITE_TEXT[f['head']]
        elif role=='ring':
            text='Ring normalization (ring) proves this identity; the normalization is not expanded.'
        elif f['head']=='Subtype.property' and len(f['objects'])==3 and not ch:
            text='By the defining property of the subtype element '+math_text(f['objects'][2])+':'; rule=_citation(f['head'])[1]
        elif f['head']=='Nonempty.intro' and len(f['objects'])==2 and not ch:
            # Still a counted gap: the element is shown, its construction is not.
            text=('Exhibit the element '+math_text(f['objects'][1])+' of '+math_text(f['objects'][0])
                  +'; its construction is not expanded here.'); rule=_citation(f['head'])[1]
        elif role in {'application','named'} and f['head']:
            # A cited constant: its own proof is outside this reading. The rule
            # tag keeps these countable whatever the sentence says.
            text,rule=_citation(f['head'])
        else:
            text='Apply '+(f['head'] or 'the recorded term')+' to the supplied arguments.'
        fallback=role in {'ring','rewrite','unexpanded','cases','choose','identity','combine','chain','witness','induction','congruence'} or (role in {'application','named'} and f['head'] not in _LEMMAS)
        child_steps=self.subproofs(ch)
        s=self.step(i,text,children=child_steps,rule=rule,
                    conclusion=None if con in text or role in {'assume','introduce'} else con,fallback=fallback)
        if role in {'assume','introduce'}:
            s.children=[]
            return [s]+child_steps
        return [s]

    @notation.reading
    def document(self, *, source: str = '', file: str = 'Original.lean', receipt: dict | None = None, title: str | None = None, provenance_note: str | None = None) -> Document:
        self.owners={};self.heads=set();s=self.snapshot
        require(receipt is None or receipt.get('snapshot_sha256') == s.sha256, 'Receipt belongs to another snapshot')
        params=[];i=0;prefix=[]
        while self.frames[i]['role'] in {'introduce','assume'}:
            f=self.frames[i];prefix.append(i);name=_name(f['binder']);domain=math_text(f['domain'])
            if f['role']=='assume':
                text='Assume '+domain+'.'
                params.append({'text':text,'names':name,'type':domain,'binder':'('})
            else:
                m=re.fullmatch(r'EuclideanDomain (\w+)',domain)
                if m:
                    prior=next((p for p in params if p['names']==m[1] and p['type'].startswith('Type')),None)
                    if prior:
                        prior['text']='Let '+m[1]+' be a Euclidean domain.'
                    else:
                        params.append({'text':'Assume '+domain+'.','names':name,'type':domain,'binder':'['})
                elif domain == 'Prop':
                    params.append({'text':'Let '+name+' be a proposition.','names':name,'type':domain,'binder':'('})
                elif domain.startswith('Type') or domain.startswith('Sort'):
                    params.append({'text':'Let '+name+' be a type.','names':name,'type':domain,'binder':'('})
                elif params and params[-1]['type']==domain and params[-1]['binder']=='(' and params[-1]['text'].startswith('Let ') and ('elements of' in params[-1]['text'] or 'an element of' in params[-1]['text']):
                    prior=params[-1];prior['names']+=', '+name;prior['text']='Let '+prior['names']+' be elements of '+domain+'.'
                else:
                    params.append({'text':'Let '+name+' be an element of '+domain+'.','names':name,'type':domain,'binder':'('})
            i=f['children'][0]
        for j in prefix:
            self.owners[j]='statement'
        steps=self.grouped(self.sequence(i))
        require(set(self.owners)==set(range(len(self.frames))), 'Display omitted an exported frame')
        statement=math_text(self.frames[i]['statement'])
        for st in steps:
            # A citation that proves the theorem itself need not reprint the statement shown above.
            if st.rule in {'citation','project-citation'} and st.conclusion==statement and st.text.startswith('By ') and st.text.endswith(':'):
                st.conclusion=None
                st.text='The statement follows from '+st.text[3:-1]+(', applied to the facts below.' if st.children else '.')
        warnings=['Formula strings use Lean’s pretty-printer. The English renderer is deterministic, not formally verified.',
                  'Reading and certificate replay do not authenticate a Lean snapshot. Re-extract from trusted source before relying on imported evidence.']
        if provenance_note:
            warnings.append(provenance_note)
        dec=Declaration('narrative:'+self.prefix,s.record['theorem'],'theorem',file,statement,source,
                        Span(0,len(source),1,max(1,len(source.splitlines()))),parameters=params,steps=steps,
                        warnings=warnings,evidence='source-bound-snapshot',dependencies=sorted(self.heads),receipt=receipt,
                        axes={'discovery':'named-Lean-theorem','statement':'Lean-derived formula snapshot',
                              'proof':'source-bound-kernel-snapshot','english_fidelity':'not-certified',
                              'snapshot_sha256':s.sha256,'lean_version':s.record['lean_version'],
                              'axiom_status':{'acceptable':True,'axioms':s.record['axioms']},
                              'printer_version':PRINTER_VERSION,'frame_owners':{str(k):v for k,v in sorted(self.owners.items())},
                              'polynomial_certificates':len(self.certificates)})
        doc=Document(title or ('Lean ProofReader · '+s.record['theorem'].split('.')[-1].replace('_',' ')),
                     [{'path':file,'sha256':digest(source),'source':source}], [dec],
                     provenance={'snapshot_sha256':s.sha256,'scope':'one selected theorem',
                                 'source_replayed_by_rendering':False,'pipeline_model_calls':0,
                                 'receipt_authenticated':False,'whole_corpus_coverage':False,
                                 'english_formally_verified':False,'formula_backend':s.record['formula_backend'],
                                 'snapshot_coverage':s.coverage(),'independent_polynomial_certificates':len(self.certificates)})
        return doc


def reading_binding(document: Document) -> str:
    require(len(document.declarations)==1, 'Expected one narrative declaration')
    d=asdict(document.declarations[0])
    for key in ('receipt','warnings','file','span'):
        d.pop(key,None)
    return digest(canonical_json(d))


def check_reading(record: dict, document: Document) -> None:
    require(len(document.declarations)==1, 'Expected one reading')
    d=document.declarations[0]
    expected=Narrative(record).document(source=d.source,file=d.file)
    # Only the label may differ: to a listed earlier label, for a listed snapshot.
    label=d.axes.get('printer_version'); e=expected.declarations[0].axes
    if isinstance(label,str) and e['snapshot_sha256'] in EARLIER_PRINTERS.get(label,()):
        e['printer_version']=label
    require(reading_binding(expected)==reading_binding(document), 'Reading differs from deterministic regeneration')


def prose(document: Document) -> str:
    d=document.declarations[0]
    out=[document.title,'',
         'Source-bound reading; the English is not formally verified. Reading this text does not authenticate the Lean snapshot.',
         '',*notation.legend(d),*(p['text'] for p in d.parameters),'Then '+d.statement+'.','','Proof.']
    def emit(steps,depth=0):
        for s in steps:
            out.append('  '*depth+('[Explanation gap] ' if s.fallback else '')+s.text)
            if s.conclusion:
                out.extend('  '*(depth+1)+line for line in s.conclusion.split('\n'))
            emit(s.children,depth+1)
    emit(d.steps)
    return '\n'.join(out)+'\n'
