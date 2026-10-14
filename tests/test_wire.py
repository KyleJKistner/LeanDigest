from pathlib import Path
import copy,json
import pytest
from proofreader.wire import pack,unpack
from proofreader.kernel import InvalidExport
ROOT=Path(__file__).parents[1]
@pytest.mark.parametrize('name',['and_swap','trans','injective_comp','witnessed','alternatives'])
def test_lossless_on_real_exports(name):
    r=json.loads((ROOT/f'artifacts/v0.2/{name}.kernel.json').read_text())
    assert unpack(pack(r))==r
@pytest.mark.parametrize('mutator',[
    lambda w:w['names'].append([1,999999,'bad']),
    lambda w:w['nodes'].append([99]),
    lambda w:w['meta'].update(exprs=[]),
    lambda w:w['steps'][0].__setitem__(0,'x'),
    lambda w:w.update(unknown=1),
])
def test_corrupt_compact_encoding_rejected(mutator):
    r=json.loads((ROOT/'artifacts/v0.2/and_swap.kernel.json').read_text());w=pack(r);mutator(w)
    with pytest.raises(InvalidExport):unpack(w)
