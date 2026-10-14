"""Bounded capture-avoiding beta/zeta reduction for mathematical display.

The original DAG remains authoritative. Added display nodes never replace its
proof certificate. The algorithm is tested, not a formal proof of the printer.
"""
from __future__ import annotations
from .kernel import Dag, EDGES, InvalidExport

class DisplayLimit(ValueError):
    pass

class Reduction:
    def __init__(self, dag: Dag, node_budget: int = 20000):
        self.dag = dag
        self.limit = len(dag.nodes) + node_budget
        self.shift_cache: dict[tuple[int,int,int], int] = {}
        self.subst_cache: dict[tuple[int,int,int], int] = {}
        self.head_cache: dict[int, int] = {}

    def add(self, node: dict) -> int:
        if len(self.dag.nodes) >= self.limit: raise DisplayLimit('Display reduction budget')
        return self.dag.add(node)

    def _transform(self, root: int, amount_or_arg: int, *, mode: str) -> int:
        """Postorder with (node, binder depth) memoization; no recursive expansion."""
        cache = self.shift_cache if mode == 'shift' else self.subst_cache
        initial = (root, amount_or_arg, 0)
        stack = [(root,0,False)]
        visits = 0
        while stack:
            i, depth, ready = stack.pop();key = (i,amount_or_arg,depth)
            if key in cache: continue
            visits += 1
            if visits > 150000: raise DisplayLimit('Display traversal budget')
            n = self.dag.nodes[i];tag = n['tag']
            if tag == 'bvar':
                k=n['index']
                if mode == 'shift':
                    v = self.add({'tag':'bvar','index':k+amount_or_arg}) if k>=depth else i
                elif k == depth:
                    v = self.shift(amount_or_arg, depth)
                elif k > depth:
                    v = self.add({'tag':'bvar','index':k-1})
                else:v=i
                cache[key]=v;continue
            edges = EDGES.get(tag,())
            if not edges:cache[key]=i;continue
            def edepth(field):return depth + int(field=='body' and tag in {'lam','forall','let'})
            if not ready:
                stack.append((i,depth,True))
                for f in reversed(edges):
                    ck=(n[f],amount_or_arg,edepth(f))
                    if ck not in cache:stack.append((n[f],edepth(f),False))
            else:
                node={**n,**{f:cache[(n[f],amount_or_arg,edepth(f))] for f in edges}}
                cache[key]=self.add(node)
        return cache[initial]

    def shift(self, root: int, amount: int) -> int:
        if amount == 0:return root
        if amount < 0:raise ValueError('Display shift must be nonnegative')
        return self._transform(root,amount,mode='shift')

    def instantiate(self, body: int, arg: int) -> int:
        return self._transform(body,arg,mode='instantiate')

    def spine(self, root: int) -> tuple[int,list[int]]:
        args=[];cur=root
        while self.dag.nodes[cur]['tag']=='app':
            if len(args)>=2048:raise DisplayLimit('Display application-spine budget')
            n=self.dag.nodes[cur];args.append(n['arg']);cur=n['fn']
        return cur,list(reversed(args))

    def head(self, root: int, fuel: int = 64) -> int:
        if root in self.head_cache:return self.head_cache[root]
        head,args=self.spine(root)
        changed=False
        for _ in range(fuel):
            n=self.dag.nodes[head]
            if n['tag']=='lam' and args:
                head=self.instantiate(n['body'],args.pop(0));changed=True
            elif n['tag']=='let':
                head=self.instantiate(n['body'],n['value']);changed=True
            else:break
            head,new_args=self.spine(head);args=new_args+args
        else:raise DisplayLimit('Display head-reduction fuel')
        if changed:
            for a in args:head=self.add({'tag':'app','fn':head,'arg':a})
            self.head_cache[root]=head
        else:self.head_cache[root]=root
        return self.head_cache[root]
