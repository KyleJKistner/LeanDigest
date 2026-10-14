from __future__ import annotations
import copy
from pathlib import Path
import pytest
from proofreader.core import make_name

ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture
def identity_export():
    """Hand-authored IR fixture, not a real Lean run or a proof certificate."""
    sort={"tag":"sort","level":{"tag":"zero"}}
    var=lambda i:{"tag":"bvar","index":i}
    bind=lambda kind,name,domain,body:{"tag":kind,"name":make_name(name),"binder":"explicit","domain":domain,"body":body}
    return {
        "schema":"proofreader.lean-export/v1", "name":"Example.identity", "name_ast":make_name("Example.identity"),
        "kind":"theorem", "statement":"∀ (P : Prop), P → P", "level_parameters":[], "axioms":[],
        "raw_type":bind("forall","P",sort,bind("forall","h",var(0),var(1))),
        "raw_term":bind("lam","P",sort,bind("lam","h",var(0),var(0))),
        "proof":{"rule":"introduce","binder":"P","domain":"Prop","conclusion":"∀ (P : Prop), P → P","children":[
            {"rule":"assume","binder":"h","domain":"P","conclusion":"P → P","context":[{"name":"P","type":"Prop"}],"children":[
                {"rule":"assumption","binder":"h","conclusion":"P","context":[{"name":"P","type":"Prop"},{"name":"h","type":"P"}]}]}]},
    }
