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

SCHEMA = 'proofreader.narrative/v1'
PRINTER_VERSION = 'source-math-en/0.4.1'
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
    'And.left': 'Take the first conjunct.',
    'And.right': 'Take the second conjunct.',
}
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
        require(len(data) <= 16_000_000, 'Narrative input too large')
        return cls(strict_json(data))

    def coverage(self) -> dict:
        return {'frames':len(self.frames), 'roles':dict(sorted(Counter(f['role'] for f in self.frames).items())),
                'budget_cuts':sum(f['budget_cut'] for f in self.frames),
                'recorded_kernel_judgements':self.record['judgements_checked'],
                'receipt_authenticated':False,'english_formally_verified':False,
                'source_replayed_by_loading':False}


def math_text(s: str) -> str:
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


class Narrative:
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

    def sid(self, i: int) -> str:
        return 'n'+self.prefix+':'+str(i)

    def claim(self, step: Step, ids: list[int]) -> Step:
        for i in ids:
            require(i not in self.owners, 'A snapshot frame was displayed twice')
            self.owners[i] = step.id
        step.term_id = ','.join('f'+str(i) for i in ids)
        paths = ['f'+str(i)+'='+(''.join(map(str,self.frames[i]['path'])) or 'root') for i in ids]
        step.detail += '\nOriginal proof paths: '+ '; '.join(paths)
        return step

    def step(self, i: int, text: str, *, rule: str | None = None,
             children: list[Step] | None = None, conclusion: str | None = None,
             fallback: bool = False, covered: list[int] | None = None, detail: str = '') -> Step:
        f = self.frames[i]
        if f['head']:
            self.heads.add(f['head'])
        s = Step(self.sid(i),rule or f['role'],text,evidence='source-bound-snapshot',
                 conclusion=conclusion,children=children or [],context=f['context'],
                 source=f['statement'],references=[f['head']] if f['head'] else [],
                 fallback=fallback or f['budget_cut'],detail=detail)
        return self.claim(s,covered or [i])

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

    def sequence(self, i: int) -> list[Step]:
        f = self.frames[i]; ch=f['children']; role=f['role']; con=math_text(f['statement'])
        if role in {'define','have'}:
            name=_name(f['binder']); domain=math_text(f['domain'])
            if role=='define':
                value=math_text(f['value'])
                note = (' This is the first Bézout coefficient.' if f['value'].startswith('EuclideanDomain.gcdA ') else
                        ' This is the second Bézout coefficient.' if f['value'].startswith('EuclideanDomain.gcdB ') else '')
                s=self.step(i,f'Set {name} = {value}.'+note,conclusion=None)
            else:
                s=self.step(i,f'Establish {domain}; call this fact {name}.',children=self.sequence(ch[0]))
            return [s]+self.sequence(ch[-1])
        # Exact conjunction eliminator shape, not a guess from tactic text.
        # The continuation's two binders are retained in the ownership ledger;
        # their proofs and every step of the continuation remain inspectable.
        if (role == 'application' and f['head'] == 'And.casesOn'
                and not f['budget_cut'] and len(ch) == 2 and len(f['objects']) == 3
                and [p['argument'] for p in f['premises']] == [3, 4]):
            left = self.frames[ch[1]]
            right = (self.frames[left['children'][0]]
                     if left['role'] == 'assume' and len(left['children']) == 1 else {})
            norm = lambda text: ' '.join(text.split())
            if (right.get('role') == 'assume' and len(right['children']) == 1
                    and not left['budget_cut'] and not right['budget_cut']
                    and norm(left['domain']) == norm(f['objects'][0])
                    and norm(right['domain']) == norm(f['objects'][1])):
                text = ('From the conjunction, obtain ' + _name(left['binder']) + ': ' +
                        math_text(left['domain']) + ' and ' + _name(right['binder']) + ': ' +
                        math_text(right['domain']) + '.')
                step = self.step(i, text, rule='unpack-conjunction',
                    children=self.sequence(ch[0]), covered=[i, left['id'], right['id']])
                return [step] + self.sequence(right['children'][0])
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
            return [self.step(i,text,conclusion=con,children=[s for j in ch for s in self.sequence(j)])]
        if role=='local-application':
            name=_name(f['binder'])
            if sum(c['name']==f['binder'] for c in f['context'])>1:
                name+=' (context entry '+str(f['local_index']+1)+')'
            text='Apply the hypothesis '+name+': '+math_text(f['domain'])+'.'
            if f['objects']:
                text+=' Substitute '+', '.join(math_text(v) for v in f['objects'])+' for its object arguments.'
            return [self.step(i,text,conclusion=con,children=[s for j in ch for s in self.sequence(j)])]
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
                            children=self.sequence(ch[0]),covered=[i,intro['id'],assumption['id']])
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
        if role=='cancel':
            text='Cancel the nonzero common factor'+(' '+math_text(f['objects'][-3]) if len(f['objects'])>=3 else '')+' to obtain '+con+'.'
        elif role=='given':
            text='Use the hypothesis '+_name(f['binder'])+': '+con+'.'
        elif role=='assume':
            text='Assume '+math_text(f['domain'])+'.'
        elif role=='introduce':
            text='Let '+_name(f['binder'])+' ∈ '+math_text(f['domain'])+' be arbitrary.'
        elif role=='reflexivity':
            text='By reflexivity, '+con+'.'
        elif f['head'] in _LEMMAS:
            text=_LEMMAS[f['head']]
        else:
            text='Apply '+(f['head'] or 'the recorded term')+' to the supplied arguments.'
        fallback=role in {'ring','rewrite','unexpanded','cases','choose','identity','combine','chain','witness','induction','congruence'} or (role in {'application','named'} and f['head'] not in _LEMMAS)
        child_steps=[s for j in ch for s in self.sequence(j)]
        s=self.step(i,text,children=child_steps,
                    conclusion=None if con in text or role in {'assume','introduce'} else con,fallback=fallback)
        if role in {'assume','introduce'}:
            s.children=[]
            return [s]+child_steps
        return [s]

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
        steps=self.sequence(i)
        require(set(self.owners)==set(range(len(self.frames))), 'Display omitted an exported frame')
        warnings=['Formula strings use Lean’s pretty-printer. The English renderer is deterministic, not formally verified.',
                  'Reading and certificate replay do not authenticate a Lean snapshot. Re-extract from trusted source before relying on imported evidence.']
        if provenance_note:
            warnings.append(provenance_note)
        dec=Declaration('narrative:'+self.prefix,s.record['theorem'],'theorem',file,math_text(self.frames[i]['statement']),source,
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
    require(reading_binding(expected)==reading_binding(document), 'Reading differs from deterministic regeneration')


def prose(document: Document) -> str:
    d=document.declarations[0]
    out=[document.title,'',*(p['text'] for p in d.parameters),'Then '+d.statement+'.','','Proof.']
    def emit(steps,depth=0):
        for s in steps:
            out.append('  '*depth+s.text)
            if s.conclusion:
                out.append('  '*(depth+1)+s.conclusion)
            emit(s.children,depth+1)
    emit(d.steps)
    return '\n'.join(out)+'\n'
