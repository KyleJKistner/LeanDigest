"""Lossless compact transport for kernel exports. Never use text truncation.

The wire encoding interns structural Names and encodes paths as ternary strings.
The decoded record must still pass Argument validation before rendering/checking.
No trust level is acquired by decoding a wire package or checking a checksum.
"""
from __future__ import annotations
import copy
from typing import Any
from .kernel import Argument, InvalidExport, FIELDS, name_key, require

SCHEMA = 'proofreader.kernel-wire/v1'
TAGS = ['bvar','sort','const','app','lam','forall','let','nat','str','proj']
NF = {
 'bvar':['index'], 'sort':['level'], 'const':['name','levels'], 'app':['fn','arg'],
 'lam':['name','domain','body','binder'], 'forall':['name','domain','body','binder'],
 'let':['name','type','value','body','nondep'], 'nat':['value'], 'str':['value'],
 'proj':['name','index','of']}
BINDERS = ['explicit','implicit','strict-implicit','instance']

def pack(record: dict) -> dict:
    Argument(record)
    names, cache = [], {}
    def nm(n):
        key = name_key(n)
        if key not in cache:
            row = [0] if n['tag']=='anonymous' else [1 if n['tag']=='str' else 2,nm(n['prefix']),n['value']]
            cache[key] = len(names); names.append(row)
        return cache[key]
    def lv(n):
        t=n['tag']
        if t=='zero': return [0]
        if t=='succ': return [1,lv(n['of'])]
        if t in ('max','imax'): return [2 if t=='max' else 3,lv(n['left']),lv(n['right'])]
        return [4,nm(n['name'])]
    def path(xs):
        require(all(type(x) is int and x in (0,1,2) for x in xs),'Non-ternary path')
        return ''.join(map(str,xs))
    def arg(a):
        require(set(a)<= {'path','term','type','is_proof','step'}, 'Unknown argument field')
        return [path(a['path']),a['term'],a['type'],a['is_proof'],a.get('step',None)]
    nodes=[]
    for n in record['exprs']:
        row=[TAGS.index(n['tag'])]
        for f in NF[n['tag']]:
            v=n[f]
            if f=='name': v=nm(v)
            elif f=='level': v=lv(v)
            elif f=='levels': v=list(map(lv,v))
            elif f=='binder': v=BINDERS.index(v)
            row.append(v)
        nodes.append(row)
    steps=[]
    for s in record['steps']:
        require(set(s)<={'path','term','type','is_proof','children','arguments','domain_is_prop','truncated','frontier_reason'},'Unknown step field')
        steps.append([path(s['path']),s['term'],s['type'],s['is_proof'],s['children'],list(map(arg,s['arguments'])),s.get('domain_is_prop',None),s['truncated'],s.get('frontier_reason',None)])
    meta = {k:copy.deepcopy(v) for k,v in record.items() if k not in ('exprs','steps')}
    return {'schema':SCHEMA,'meta':meta,'names':names,'nodes':nodes,'steps':steps}

def unpack(w: Any) -> dict:
    require(isinstance(w,dict) and set(w)=={'schema','meta','names','nodes','steps'} and w['schema']==SCHEMA,'Invalid compact envelope')
    require(isinstance(w['names'],list) and len(w['names'])<=250000,'Name table exceeds budget')
    require(isinstance(w['meta'],dict),'Invalid metadata')
    names=[]
    def at(table,i):
        require(type(i) is int and 0<=i<len(table),'Invalid compact reference')
        return copy.deepcopy(table[i])
    for n in w['names']:
        require(isinstance(n,list) and len(n)>0 and type(n[0]) is int,'Invalid name row')
        if n==[0]: v={'tag':'anonymous'}
        else:
            require(len(n)==3 and n[0] in (1,2) and isinstance(n[2],str),'Invalid name row')
            v={'tag':'str' if n[0]==1 else 'num','prefix':at(names,n[1]),'value':n[2]}
        name_key(v); names.append(v)
    def lv(n,depth=0):
        require(isinstance(n,list) and n and type(n[0]) is int and depth<128,'Invalid universe row')
        t=n[0]
        if n==[0]: return {'tag':'zero'}
        if t==1 and len(n)==2: return {'tag':'succ','of':lv(n[1],depth+1)}
        if t in (2,3) and len(n)==3: return {'tag':'max' if t==2 else 'imax','left':lv(n[1],depth+1),'right':lv(n[2],depth+1)}
        if t==4 and len(n)==2: return {'tag':'param','name':at(names,n[1])}
        raise InvalidExport('Invalid universe row')
    def path(s):
        require(isinstance(s,str) and len(s)<=512 and all(c in '012' for c in s),'Invalid compact path')
        return [int(c) for c in s]
    require(isinstance(w['nodes'],list) and len(w['nodes'])<=250000,'Invalid compact expression table')
    nodes=[]
    for row in w['nodes']:
        require(isinstance(row,list) and row and type(row[0]) is int and 0<=row[0]<len(TAGS),'Invalid expression row')
        t=TAGS[row[0]]; fields=NF[t]; require(len(row)==len(fields)+1,'Invalid expression row arity')
        n={'tag':t}
        for f,v in zip(fields,row[1:]):
            if f=='name':v=at(names,v)
            elif f=='level':v=lv(v)
            elif f=='levels':
                require(isinstance(v,list),'Invalid universe list');v=list(map(lv,v))
            elif f=='binder':v=at(BINDERS,v)
            n[f]=v
        nodes.append(n)
    def arg(r):
        require(isinstance(r,list) and len(r)==5,'Invalid argument row')
        a={'path':path(r[0]),'term':r[1],'type':r[2],'is_proof':r[3]}
        if r[4] is not None:a['step']=r[4]
        return a
    require(isinstance(w['steps'],list) and len(w['steps'])<=20000,'Invalid compact step inventory')
    steps=[]
    for r in w['steps']:
        require(isinstance(r,list) and len(r)==9 and isinstance(r[5],list),'Invalid step row')
        s={'path':path(r[0]),'term':r[1],'type':r[2],'is_proof':r[3],'children':r[4],'arguments':list(map(arg,r[5])),'truncated':r[7]}
        if r[6] is not None:s['domain_is_prop']=r[6]
        if r[8] is not None:s['frontier_reason']=r[8]
        steps.append(s)
    require(not {'exprs','steps'} & set(w['meta']), 'Payload fields smuggled into metadata')
    record={**copy.deepcopy(w['meta']),'exprs':nodes,'steps':steps}
    Argument(record)
    return record
