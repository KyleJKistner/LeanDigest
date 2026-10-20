"""Bundling the source of cited dependency modules.

Every source tree, snapshot and observation here is a synthetic consistency
fixture: no Lean runs and nothing is a native observation. Repository Lean files
are read only to compare two lexical readers. The browser test uses real
Chromium on a generated page.
"""
from hashlib import sha256
import json
import os
from pathlib import Path
import random
import re
import shutil

import pytest

from proofreader.catalog_audit import audit
from proofreader.catalog_inputs import PIN
from proofreader.declaration_index import (ATOM, CAPS, CHAR, LINE_BREAKS, RAW, _header, build_index, closure, header_imports,
                                           mask, reachable_headers, scan, searched_components, select_dependencies,
                                           walk_imports)
from proofreader.finding_catalog import build, source_name
from proofreader.model import digest

ROOT = Path(__file__).resolve().parents[1]
A, A_MID, A_LOOP, A_DEEP = 'OAI.Alg.A.Main', 'OAI.Alg.A.Mid', 'OAI.Alg.A.Loop', 'OAI.Alg.A.Deep'
B, B_BASIC, C, C_BASIC = 'OAI.Alg.B.Main', 'OAI.Alg.B.Basic', 'OAI.Alg.C.Main', 'OAI.Alg.C.Basic'
TREE = {
    A: 'import OAI.Alg.A.Mid\nimport Mathlib\n\nnamespace OAI.A\n\ntheorem main : True := trivial\n\nend OAI.A\n',
    A_MID: '/- An intermediate module; it declares nothing cited. -/\nimport OAI.Alg.A.Deep\nimport OAI.Alg.A.Loop\nimport OAI.Alg.A.Leaf\n',
    'OAI.Alg.A.Leaf': 'theorem leaf : True := trivial\n',  # Visited, but on no import path to a bundled module.
    A_LOOP: 'import OAI.Alg.A.Mid\n',  # A cycle, which Lean rejects; the walk must still terminate.
    A_DEEP: 'namespace OAI.A\n\ntheorem deep : True := trivial\n\nstructure Data where\n  x : Nat\n\nend OAI.A\n',
    B: 'import OAI.Alg.B.Basic\nimport OAI.Alg.B.Gone\n\nnamespace OAI.B\n\ntheorem main : True := trivial\n\nend OAI.B\n',
    B_BASIC: 'namespace OAI.Shared\n\ntheorem twin : True := trivial\n\nend OAI.Shared\n',
    C: 'import OAI.Alg.C.Basic\n\nnamespace OAI.C\n\ntheorem main : True := trivial\n\nend OAI.C\n',
    C_BASIC: 'namespace OAI.Shared\n\n\ntheorem twin : True := trivial\n\nend OAI.Shared\n',
    'OAI.Alg.Z.Unused': 'namespace OAI.A\ntheorem deep : True := trivial\nend OAI.A\n',
}
THEOREMS = {A: 'OAI.A.main', B: 'OAI.B.main', C: 'OAI.C.main'}
CITES = {A: ['OAI.A.deep', 'OAI.A.Data.x', 'OAI.Shared.twin', 'OAI.A.absent', 'Nat.succ_le'],
         B: ['OAI.Shared.twin'], C: ['OAI.Shared.twin']}
SOLUTIONS = {m: TREE[m] for m in THEOREMS}


def loader(tree, statuses=None):
    def load(module):
        if statuses and module in statuses: return None, statuses[module]
        return (tree[module], 'read') if module in tree else (None, 'missing-file')
    return load


def walk_and_select(tree=TREE, cites=CITES, caps=None, statuses=None, log=None, namespace='OAI.'):
    known = {m: tree[m] for m in cites}
    walk = walk_imports(sorted(cites), known, loader(tree, statuses), set().union(*map(set, cites.values())),
                        caps=caps, log=log, namespace=namespace)
    return walk, select_dependencies(walk, {m: set(v) for m, v in cites.items()}, build_index(known), log=log)


# Header reading


@pytest.mark.parametrize('source,imports', [
    ('import A\nimport B.C\n', ['A', 'B.C']),
    ('/- copyright /- nested -/ -/\nmodule\n\npublic import A -- why\nmeta import B\nimport all C\n\nnamespace X\nimport D\n', ['A', 'B', 'C']),
    ('import\n  A\ntheorem t : True := trivial\n', ['A']),
    ('prelude\nimport Init.Core\n', ['Init.Core']),
    ('theorem t : True := trivial\n', []),
    ('', []),
])
def test_header_imports_agree_with_scan(source, imports):
    assert header_imports(source) == imports == scan(source, 'M')['imports']


@pytest.mark.parametrize('source', ['import A B\n', 'import «A»\n', 'import\n', 'import A.\n', '/- unterminated\nimport A\n',
                                    'import A /- c -/ theorem t : True := trivial\n'])
def test_header_imports_never_guess_a_dependency(source):
    with pytest.raises(ValueError):
        header_imports(source)


def repository_lean_files():
    return sorted(p for p in ROOT.rglob('*.lean') if '.lake' not in p.parts)


def test_header_reader_and_atom_prefilter_on_repository_files():
    """Not synthetic: the repository's own Lean files, read lexically."""
    checked = 0
    for p in repository_lean_files():
        text = p.read_text(encoding='utf-8')
        try:
            result, imports = scan(text, 'M'), header_imports(text)
        except ValueError:
            continue
        assert imports == result['imports'], p
        # The walk's scan prefilter: every indexed name is spelled after the imports.
        atoms = set(ATOM.findall(mask(text), _header(text)[1]))
        assert all(set(searched_components(d['name'], '')) <= atoms for d in result['declarations']), p
        checked += 1
    assert checked > 100


# The optimised mask must equal the previous character-by-character implementation.


def reference_mask(source):
    """The previous mask() implementation, kept verbatim as the test oracle."""
    def ident_char(c): return c.isalnum() or c in "_'!?"
    out = list(source); n = len(source); i = 0
    def blank(a, b):
        for k in range(a, b):
            if out[k] not in LINE_BREAKS: out[k] = ' '
    while i < n:
        c = source[i]
        if source.startswith('--', i):
            j = source.find('\n', i); j = n if j < 0 else j
            blank(i, j); i = j
        elif source.startswith('/-', i):
            depth, j = 1, i+2
            while depth:
                a, b = source.find('/-', j), source.find('-/', j)
                if b < 0: raise ValueError('Unterminated block comment')
                if 0 <= a < b: depth, j = depth+1, a+2
                else: depth, j = depth-1, b+2
            blank(i, j); i = j
        elif c == '"' or (c == 'r' and (i == 0 or not ident_char(source[i-1])) and RAW.match(source, i)):
            if c == 'r':
                m = RAW.match(source, i); end = '"'+m[1]
                j = source.find(end, m.end())
                if j < 0: raise ValueError('Unterminated raw string literal')
                j += len(end)
            else:
                j = i+1
                while j < n and source[j] != '"': j += 2 if source[j] == '\\' else 1
                if j >= n: raise ValueError('Unterminated string literal')
                j += 1
            blank(i, j); i = j
        elif c == "'" and (i == 0 or not ident_char(source[i-1])) and CHAR.match(source, i):
            j = CHAR.match(source, i).end(); blank(i, j); i = j
        else:
            i += 1
    text = ''.join(out)
    for m in list(re.finditer(r'`\(', text)):
        if out[m.start()] != '`': continue
        depth, j = 1, m.end()
        while j < n and depth:
            depth += {'(': 1, ')': -1}.get(out[j], 0); j += 1
        if depth: raise ValueError('Unterminated syntax quotation')
        blank(m.start(), j)
    return ''.join(out)


def outcome(f, text):
    try:
        return f(text)
    except ValueError as exc:
        return ('error', str(exc))


def test_mask_matches_the_previous_implementation_on_random_text():
    """Synthetic fuzz over the characters that open and close comments and literals."""
    pieces = ['--', '/-', '-/', '"', '\\', "'", 'r"', 'r#"', '"#', '`(', '(', ')', 'a', 'r', '1', ' ', '\n', '\r\n',
              ' ', '\x0c', 'λ', 'é', "x'", '?', 'theorem t', '\\x41', "'\\''", "'a'"]
    rng = random.Random(20261020)
    for _ in range(4000):
        text = ''.join(rng.choice(pieces) for _ in range(rng.randrange(1, 30)))
        assert outcome(mask, text) == outcome(reference_mask, text), text


def test_mask_matches_the_previous_implementation_on_repository_files():
    for p in repository_lean_files():
        text = p.read_text(encoding='utf-8')
        assert outcome(mask, text) == outcome(reference_mask, text), p


# Walking import headers and selecting cited dependency modules


def test_walk_follows_closures_through_cycles_and_records_missing_files():
    walk, selection = walk_and_select()
    assert set(walk['headers']) == {A, A_MID, A_LOOP, A_DEEP, 'OAI.Alg.A.Leaf', B, B_BASIC, C, C_BASIC}
    assert walk['unused'] == {'OAI.Alg.B.Gone': 'missing-file'}
    assert walk['counts']['external_imports'] == 1 and walk['caps_hit'] == []
    assert selection['incomplete_closures'] == {B: ['missing-file']}
    assert set(selection['modules']) == {A_DEEP, B_BASIC, C_BASIC}
    assert selection['modules'][A_DEEP] == {'bytes': len(TREE[A_DEEP]), 'cited_names': ['OAI.A.deep'],
                                            'citing_modules': [A], 'import_path': [A, A_MID, A_DEEP]}
    names = selection['names']
    assert names['OAI.A.deep'] == {'search': 'declared-in-cited-dependency', 'citing_modules': 1, 'import_closure_complete': True}
    # The same name in two environments: each citing module sees exactly one declaration.
    assert names['OAI.Shared.twin']['search'] == 'declared-in-cited-dependency'
    assert names['OAI.Shared.twin']['import_closure_complete'] is False
    # A structure field is generated, not declared; the catalog report checks its parent type.
    assert names['OAI.A.Data.x']['search'] == 'not-declared-in-visited-modules'
    assert names['OAI.A.absent']['search'] == 'not-declared-in-visited-modules'
    assert names['Nat.succ_le']['search'] == 'outside-searched-namespace'


def test_only_names_in_the_searched_namespace_are_searched():
    tree = {**TREE, A_DEEP: TREE[A_DEEP] + 'theorem _root_.Nat.helper : True := trivial\n'
                            'namespace OAI.A\nprivate theorem secret : True := trivial\nend OAI.A\n'}
    cites = {A: ['Nat.helper', '_private.OAI.Alg.A.Deep.0.OAI.A.secret']}
    _, selection = walk_and_select(tree, cites)
    assert selection['names']['Nat.helper']['search'] == 'outside-searched-namespace'
    assert selection['modules'][A_DEEP]['cited_names'] == ['_private.OAI.Alg.A.Deep.0.OAI.A.secret']
    _, selection = walk_and_select(tree, cites, namespace='')
    assert selection['modules'][A_DEEP]['cited_names'] == ['Nat.helper', '_private.OAI.Alg.A.Deep.0.OAI.A.secret']


def test_a_module_is_scanned_only_when_it_spells_every_component_of_a_searched_name():
    tree = {**TREE, A_MID: TREE[A_MID] + '-- OAI.A.deep is mentioned only in this comment\n'}
    walk, _ = walk_and_select(tree, {A: ['OAI.A.deep']})
    # A_DEEP declares the name; A_MID spells it only in a comment, which is masked.
    assert walk['counts']['modules_scanned'] == 1 and walk['declares']['OAI.A.deep'][0]['module'] == A_DEEP


def test_a_declaration_visited_only_through_another_reading_is_not_imported():
    walk, selection = walk_and_select(cites={A: ['OAI.Shared.twin'], B: ['OAI.B.main']})
    assert selection['names']['OAI.Shared.twin']['search'] == 'declared-only-in-modules-not-imported'
    assert selection['modules'] == {}
    assert selection['names']['OAI.B.main']['search'] == 'declared-in-solution-module'


def test_two_visible_declarations_are_ambiguous_and_not_selected():
    tree = {**TREE, A_MID: TREE[A_MID] + 'import OAI.Alg.B.Basic\nimport OAI.Alg.C.Basic\n'}
    walk, selection = walk_and_select(tree, cites={A: ['OAI.Shared.twin']})
    assert selection['names']['OAI.Shared.twin']['search'] == 'ambiguous-in-visible-modules'
    assert selection['modules'] == {}


def test_unusable_modules_are_recorded_with_their_reason():
    tree = {**TREE, A_MID: "import OAI.Alg.A.Deep\nimport OAI.Alg.A.Bad\nimport OAI.Alg.A.Odd\nimport OAI.Alg.A.Kappa₁\n"
                           "import OAI.Alg.A.Lp'\n", 'OAI.Alg.A.Kappa₁': '', "OAI.Alg.A.Lp'": '',
            'OAI.Alg.A.Bad': 'import X Y\n', 'OAI.Alg.A.Odd': 'theorem stray : True := trivial\n'}
    walk, selection = walk_and_select(tree, statuses={'OAI.Alg.A.Odd': 'unreadable-source'})
    assert walk['unused'] == {'OAI.Alg.A.Bad': 'unreadable-header', 'OAI.Alg.A.Odd': 'unreadable-source',
                              'OAI.Alg.B.Gone': 'missing-file'}
    # Upstream module names include Kappa₁ and IntegralDensityMeasureLp'; both map to file paths.
    assert {'OAI.Alg.A.Kappa₁', "OAI.Alg.A.Lp'"} <= set(walk['headers'])
    assert selection['incomplete_closures'][A] == ['unreadable-header', 'unreadable-source']
    assert selection['names']['OAI.A.deep']['import_closure_complete'] is False


@pytest.mark.parametrize('root', ['OAI..Gap', 'OAI.Alg/A', 'OAI.«Quoted»', 'OAI.λx', ''])
def test_a_root_that_is_not_a_module_name_is_never_resolved_to_a_path(root):
    walk = walk_imports([root], {}, lambda m: pytest.fail('load called for ' + m), {'OAI.A.deep'})
    assert walk['unused'] == {root: 'unsupported-module-name'} and walk['counts']['modules_visited'] == 0


def test_a_candidate_module_that_fails_to_index_is_reported():
    tree = {**TREE, A_DEEP: 'namespace OAI.A\ntheorem deep : True := (trivial\nend OAI.A\n'}
    walk, selection = walk_and_select(tree)
    assert A_DEEP in walk['failed'] and walk['unindexed']['OAI.A.deep'] == [A_DEEP]
    assert selection['names']['OAI.A.deep']['search'] == 'candidate-module-not-indexed'
    assert A_DEEP not in selection['modules']


def test_a_solution_module_that_failed_to_index_is_not_reported_as_declaring_nothing():
    broken = {**TREE, A: TREE[A].replace('theorem main : True := trivial', 'theorem main : True := (trivial\ntheorem own : True := trivial')}
    known = {m: broken[m] for m in CITES}; base = build_index(known)
    assert A in base['failed_modules']
    walk = walk_imports(sorted(CITES), known, loader(broken), {'OAI.A.own'}, failed_known=base['failed_modules'])
    assert walk['failed'] == {A: base['failed_modules'][A]} and walk['unindexed'] == {'OAI.A.own': [A]}
    assert walk['counts']['modules_scanned'] == 0
    selection = select_dependencies(walk, {A: {'OAI.A.own'}}, base)
    assert selection['names']['OAI.A.own']['search'] == 'candidate-module-not-indexed'
    # Without the bundled index's failures, the name would read as declared nowhere.
    walk = walk_imports(sorted(CITES), known, loader(broken), {'OAI.A.own'})
    assert select_dependencies(walk, {A: {'OAI.A.own'}}, base)['names']['OAI.A.own']['search'] == 'not-declared-in-visited-modules'


def test_visit_caps_are_logged_and_recorded():
    messages = []
    walk, selection = walk_and_select(caps={'max_visited_modules': 2}, log=messages.append)
    assert walk['caps_hit'] == ['max_visited_modules'] and walk['counts']['modules_visited'] == 2
    capped = {m for m, r in walk['unused'].items() if r == 'not-visited-cap'}
    assert capped and capped.isdisjoint(walk['headers'])
    assert len(messages) == 1 and 'max_visited_modules=2' in messages[0]
    assert any('not-visited-cap' in r for r in selection['incomplete_closures'].values())
    walk, _ = walk_and_select(caps={'max_seconds': 0})
    assert walk['caps_hit'] == ['max_seconds'] and walk['counts']['modules_visited'] == 0
    walk, _ = walk_and_select(caps={'max_read_bytes': 1})
    assert walk['caps_hit'] == ['max_read_bytes'] and walk['counts']['modules_visited'] == 1


def test_selection_caps_keep_the_most_useful_modules_and_record_the_rest():
    messages = []
    cites = {**CITES, B: ['OAI.Shared.twin', 'OAI.Shared.extra']}
    tree = {**TREE, B_BASIC: TREE[B_BASIC].replace('end OAI.Shared', 'theorem extra : True := trivial\nend OAI.Shared')}
    _, selection = walk_and_select(tree, cites, caps={'max_selected_modules': 1}, log=messages.append)
    assert list(selection['modules']) == [B_BASIC]  # Two cited names; the others resolve one each.
    assert selection['dropped'] == {A_DEEP: 'max_selected_modules', C_BASIC: 'max_selected_modules'}
    assert selection['names']['OAI.A.deep']['search'] == 'dropped-by-selection-cap'
    assert selection['caps_hit'] == ['max_selected_modules'] and len(messages) == 1
    _, selection = walk_and_select(caps={'max_selected_bytes': len(TREE[A_DEEP])})
    assert list(selection['modules']) == [A_DEEP]
    assert selection['dropped'] == {B_BASIC: 'max_selected_bytes', C_BASIC: 'max_selected_bytes'}


@pytest.mark.parametrize('caps', [{'max_modules': 3}, {'max_visited_modules': -1}, {'max_read_bytes': True},
                                  {'max_selected_modules': None}, {'max_seconds': '5'}, {'max_selected_bytes': 1.5},
                                  {'max_read_bytes': float('nan')}, {'max_seconds': float('nan')},
                                  {'max_seconds': float('inf')}])
def test_invalid_caps_are_rejected(caps):
    # A NaN bound would compare false forever and silently disable its cap.
    with pytest.raises(ValueError):
        walk_and_select(caps=caps)


def test_a_fractional_time_bound_is_accepted():
    walk, _ = walk_and_select(caps={'max_seconds': 3600.5})
    assert walk['caps']['max_seconds'] == 3600.5 and walk['caps_hit'] == []


@pytest.mark.parametrize('value', ['{"max_modules": 3}', '[1]', 'not json', 'NaN', '{"max_visited_modules": -1}',
                                   '{"max_seconds": "5"}', '{"max_read_bytes": NaN}'])
def test_the_catalog_command_rejects_invalid_caps_before_building(tmp_path, value):
    from proofreader.finding_catalog import main
    with pytest.raises(SystemExit):
        main(['--upstream', str(tmp_path), '--lean', str(tmp_path), '--statements', str(tmp_path), '--proofs', str(tmp_path),
              '--output', str(tmp_path/'site'), '--dependency-caps', value])
    assert not (tmp_path/'site').exists()


def test_the_catalog_build_rejects_an_invalid_cap_before_writing_output(tmp_path):
    with pytest.raises(ValueError, match='cited dependency cap'):
        make_site(tmp_path, caps={'max_selected_modules': -1})
    assert not (tmp_path/'site').exists()


def test_pruned_header_records_keep_every_reachable_bundled_module():
    walk, selection = walk_and_select()
    bundled = {**SOLUTIONS, **{m: TREE[m] for m in selection['modules']}}
    full = build_index(bundled, walk['headers'])
    pruned = build_index(bundled, reachable_headers(walk['headers'], sorted(CITES), set(bundled)))
    assert set(pruned['header_imports']) == {A_MID, A_LOOP} and set(full['header_imports']) == {A_MID, A_LOOP, 'OAI.Alg.A.Leaf'}
    for root in CITES:
        assert closure(full, root) & set(bundled) == closure(pruned, root) & set(bundled)
    assert closure(pruned, A) & set(bundled) == {A, A_DEEP}
    assert closure(pruned, A, recorded=False) == {A}


# The catalog build


def record(theorem, heads):
    def frame(i, path, head, children):
        return {'id': i, 'path': path, 'statement': 'True', 'role': 'application' if children else 'named',
                'head': head, 'context': [], 'children': children, 'premises': [], 'objects': [], 'budget_cut': False}
    frames = [frame(0, [], heads[0], list(range(1, len(heads))))]
    frames += [frame(i, [0]*(i-1)+[1], h, []) for i, h in enumerate(heads[1:], 1)]
    return {'schema': 'proofreader.narrative/v1', 'theorem': theorem, 'lean_version': '4.34.1', 'axioms': [],
            'statement': 'True', 'judgements_checked': len(frames), 'formula_backend': 'Lean pretty-printer', 'frames': frames}


def ident(module):
    return sha256((module+'\0'+THEOREMS[module]).encode()).hexdigest()[:24]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value) if isinstance(value, bytes) else path.write_text(value if isinstance(value, str) else json.dumps(value))


def make_site(tmp_path, tree=TREE, *, inventory='all', name='site', caps=None):
    """Synthetic configurations A, B and C, each with one synthetic consistency-check reading."""
    from proofreader.narrative import Snapshot
    upstream = tmp_path/'upstream'; lean = upstream/'lean'; proofs = tmp_path/'proofs'; statements = tmp_path/'statements'
    if not upstream.exists():
        statements.mkdir()
        write(upstream/'CONTENTS.md', '**001. Cited dependencies.** Synthetic.\n')
        write(upstream/'LICENSE', 'Example public license')
        write(lean/'docs/001.md', '# Cited dependencies\n\n'+''.join(f'[{k}](../ComparatorChallenges/{k}.lean)\n' for k in 'ABC'))
        for key, module in zip('ABC', THEOREMS):
            write(lean/f'ComparatorChallenges/{key}.json', {'challenge_module': 'ComparatorChallenges.'+key,
                  'solution_module': module, 'theorem_names': [THEOREMS[module]]})
            write(lean/f'ComparatorChallenges/{key}.lean', '-- comparison specification\n')
        for module, text in tree.items():
            write(lean/(module.replace('.', '/')+'.lean'), text)
        rows = []
        for module in THEOREMS:
            rec = record(THEOREMS[module], CITES[module]); directory = proofs/'targets'/ident(module)
            snapshot = Snapshot(rec); driver = '-- synthetic consistency fixture, not executed\n'
            stdout = 'PR_NARRATIVE:'+json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(',', ':'))+'\n'
            write(directory/'Extract.lean', driver); write(directory/'snapshot.json', rec); write(directory/'stdout.txt', stdout)
            write(directory/'receipt.json', {'status': 'passed', 'schema': 'proofreader.narrative-receipt/v1',
                  'theorem': rec['theorem'], 'module': module, 'lean_version': '4.34.1',
                  'selected_judgements': rec['judgements_checked'], 'backend': 'native',
                  'all_selected_judgements_kernel_checked': True, 'path_linkage_checked_in_lean': True,
                  'snapshot_sha256': snapshot.sha256, 'source_sha256': digest(driver.encode())})
            write(directory/'run.json', {'status': 'passed', 'exit_code': 0, 'stdout': stdout})
            rows.append({'id': ident(module), 'module': module, 'name': rec['theorem'], 'kind': 'theorem',
                         'status': 'reading-generated', 'directory': 'targets/'+ident(module), 'kernel_checked': True,
                         'snapshot_sha256': snapshot.sha256, 'selected_judgements': rec['judgements_checked'],
                         'source_sha256': digest(tree[module].encode())})
        write(proofs/'proofs.json', {'schema': 'leanglish.finding-proof-shard/v1', 'upstream_commit': PIN,
                                     'expected_targets': len(rows), 'targets': rows})
        entries = [{'path': p.relative_to(upstream).as_posix(), 'sha256': digest(p.read_bytes())}
                   for p in sorted(upstream.rglob('*')) if p.is_file()]
        write(upstream/'acquisition.json', {'repository': 'openai/math', 'commit': PIN, 'fetched': entries})
    entries = [{'path': p.relative_to(upstream).as_posix(), 'sha256': digest(p.read_bytes())}
               for p in sorted(lean.rglob('*')) if p.is_file()]
    path = None
    if inventory != 'none':
        path = tmp_path/(name+'-inventory.json')
        write(path, inventory(entries) if callable(inventory) else entries)
    site = tmp_path/name
    return site, build(upstream, lean, [statements], [proofs], site, source_inventory=path, dependency_caps=caps)


def links_of(site, module):
    return json.loads((site/'proofs'/ident(module)/'links.json').read_text())['names']


def test_catalog_bundles_cited_dependency_sources_and_passes_audit(tmp_path):
    site, summary = make_site(tmp_path)
    assert not summary['rendering_failures'] and summary['solution_source_modules'] == 3
    assert summary['cited_dependency_source_modules'] == 3
    a, b, c = links_of(site, A), links_of(site, B), links_of(site, C)
    assert a['OAI.A.deep'] == {'status': 'source', 'href': f'../../sources/{source_name(A_DEEP)}#L3', 'module': A_DEEP,
                               'line': 3, 'basis': 'imported-via-recorded-headers'}
    # One name, two environments: each reading links to the declaration its module imports.
    assert b['OAI.Shared.twin'] == {'status': 'source', 'href': f'../../sources/{source_name(B_BASIC)}#L3',
                                    'module': B_BASIC, 'line': 3, 'basis': 'imported-bundled-module'}
    assert c['OAI.Shared.twin']['module'] == C_BASIC and c['OAI.Shared.twin']['line'] == 4
    assert a['OAI.Shared.twin'] == {'status': 'unresolved', 'reason': 'not-visibly-imported'}
    assert a['OAI.A.Data.x'] == {'status': 'unresolved', 'reason': 'not-in-declaration-index'}
    index = json.loads((site/'evidence/declaration-index.json').read_text())
    assert index['schema'] == 'leanglish.declaration-index/v2' and set(index['header_imports']) == {A_MID, A_LOOP}
    assert len(index['ambiguous']['OAI.Shared.twin']) == 2 and 'OAI.Alg.Z.Unused' not in json.dumps(index)
    report = json.loads((site/'evidence/cited-dependency-sources.json').read_text())
    assert report['source_hashes_checked'] is True and report['caps'] == CAPS and report['caps_hit'] == []
    assert report['names']['OAI.A.deep'] == {'link': 'source', 'module': A_DEEP, 'basis': 'imported-via-recorded-headers',
                                             'search': 'declared-in-cited-dependency', 'citing_modules': 1,
                                             'import_closure_complete': True}
    assert report['names']['OAI.A.Data.x'] == {'link': 'unresolved', 'reason': 'not-in-declaration-index',
                                               'search': 'parent-type-in-bundled-source', 'citing_modules': 1,
                                               'import_closure_complete': True}
    # Every cited name keeps its final status and reason.
    cited = {n for m in THEOREMS for n in links_of(site, m)}
    assert set(report['names']) == cited and all(v['search'] != 'not-searched' for v in report['names'].values())
    assert report['modules_not_used'] == {'OAI.Alg.B.Gone': 'missing-file'}
    assert report['modules'][A_DEEP]['sha256'] == digest(TREE[A_DEEP].encode())
    assert summary['cited_dependency_sources']['counts'] == report['counts']
    page = (site/'sources'/source_name(A_DEEP)).read_text()
    assert 'Cited dependency source · exact source · not an English translation' in page
    assert re.search(r'id="L3"><a href="#L3">3</a> theorem deep', page)
    assert 'imports it through 1 intermediate module.' in page and '<details>' in page
    assert 'imports it directly.' in (site/'sources'/source_name(B_BASIC)).read_text()
    assert 'Cited dependency source' not in (site/'sources'/source_name(A)).read_text()
    assert (site/'originals'/(A_DEEP.replace('.', '/')+'.lean')).read_text() == TREE[A_DEEP]
    assert not (site/'sources'/source_name(A_MID)).exists()
    result = audit(site)
    assert result['passed'], result['errors']
    assert result['source_pages'] == 6 and result['cited_dependency_source_pages'] == 3
    coverage = (site/'coverage.html').read_text()
    assert '<td>Cited dependency source modules included</td><td>3</td>' in coverage
    assert 'evidence/cited-dependency-sources.json' in coverage


def test_catalog_build_is_deterministic(tmp_path):
    first, _ = make_site(tmp_path, name='first')
    second, _ = make_site(tmp_path, name='second')
    files = sorted(p.relative_to(first) for p in first.rglob('*') if p.is_file())
    assert files == sorted(p.relative_to(second) for p in second.rglob('*') if p.is_file())
    assert all((first/p).read_bytes() == (second/p).read_bytes() for p in files)


@pytest.mark.parametrize('change,unused', [
    (lambda rows: [r for r in rows if not r['path'].endswith('A/Deep.lean')], {A_DEEP: 'unverified-source'}),
    (lambda rows: [dict(r, sha256='0'*64) if r['path'].endswith('A/Mid.lean') else r for r in rows], {A_MID: 'unverified-source'}),
])
def test_an_unverified_file_is_never_bundled_or_followed(tmp_path, change, unused):
    site, summary = make_site(tmp_path, inventory=change)
    report = json.loads((site/'evidence/cited-dependency-sources.json').read_text())
    assert report['modules_not_used'] == {**unused, 'OAI.Alg.B.Gone': 'missing-file'}
    assert set(report['modules']) == {B_BASIC, C_BASIC} and summary['cited_dependency_source_modules'] == 2
    assert not (site/'sources'/source_name(A_DEEP)).exists() and not (site/'originals/OAI/Alg/A/Deep.lean').exists()
    assert links_of(site, A)['OAI.A.deep'] == {'status': 'unresolved', 'reason': 'not-in-declaration-index'}
    assert report['names']['OAI.A.deep']['search'] == 'not-declared-in-visited-modules'
    assert report['names']['OAI.A.deep']['import_closure_complete'] is False
    assert audit(site)['passed']


def test_a_module_file_that_resolves_outside_the_tree_is_never_read(tmp_path):
    make_site(tmp_path, name='first')
    outside = tmp_path/'outside.lean'; outside.write_text(TREE[A_DEEP])
    deep = tmp_path/'upstream/lean/OAI/Alg/A/Deep.lean'; deep.unlink(); deep.symlink_to(outside)
    site, summary = make_site(tmp_path, name='second')
    report = json.loads((site/'evidence/cited-dependency-sources.json').read_text())
    assert report['modules_not_used'] == {A_DEEP: 'path-outside-tree', 'OAI.Alg.B.Gone': 'missing-file'}
    assert A_DEEP not in report['modules'] and not (site/'sources'/source_name(A_DEEP)).exists()
    assert links_of(site, A)['OAI.A.deep'] == {'status': 'unresolved', 'reason': 'not-in-declaration-index'}


def test_without_an_inventory_the_report_says_hashes_were_not_checked(tmp_path):
    site, summary = make_site(tmp_path, inventory='none')
    assert summary['cited_dependency_source_modules'] == 3 and summary['source_hashes_checked'] is False
    assert json.loads((site/'evidence/cited-dependency-sources.json').read_text())['source_hashes_checked'] is False


def test_catalog_caps_are_recorded_in_coverage(tmp_path, capsys):
    site, summary = make_site(tmp_path, caps={'max_selected_modules': 1})
    assert summary['cited_dependency_source_modules'] == 1
    assert summary['cited_dependency_sources']['caps_hit'] == ['max_selected_modules']
    assert 'max_selected_modules=1' in capsys.readouterr().err
    assert '<td>Cited dependency caps reached</td><td>max_selected_modules</td>' in (site/'coverage.html').read_text()
    assert audit(site)['passed']


def test_audit_rejects_a_changed_or_missing_dependency_source(tmp_path):
    site, _ = make_site(tmp_path)
    (site/'originals/OAI/Alg/A/Deep.lean').write_text('namespace OAI.A\ntheorem other : True := trivial\nend OAI.A\n')
    assert {'module': A_DEEP, 'error': 'cited dependency source does not match its record'} in audit(site)['errors']
    (site/'sources'/source_name(B_BASIC)).unlink()
    with pytest.raises(ValueError, match='Source module inventory mismatch'):
        audit(site)


def test_audit_rejects_a_dependency_record_that_escapes_the_site(tmp_path):
    site, _ = make_site(tmp_path)
    path = site/'evidence/cited-dependency-sources.json'; report = json.loads(path.read_text())
    report['modules'] = {'OAI.Alg.A.Deep/../../x' if m == A_DEEP else m: v for m, v in report['modules'].items()}
    path.write_text(json.dumps(report))
    assert any(e.get('error') == 'malformed cited dependency record' for e in audit(site)['errors'])


pw = pytest.importorskip('playwright.sync_api')


def test_offline_navigation_reaches_a_cited_dependency_line(tmp_path):
    """Real file:// navigation inside the generated synthetic catalog."""
    site, _ = make_site(tmp_path)
    executable = shutil.which('chromium') or shutil.which('google-chrome')
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(executable_path=executable, headless=True, args=['--no-sandbox']) if executable else p.chromium.launch(headless=True)
        except Exception as exc:
            if os.environ.get('PROOFREADER_REQUIRE_BROWSER') == '1': pytest.fail(f'Browser CI requires Chromium: {exc}')
            pytest.skip(f'Browser unavailable: {exc}')
        page = browser.new_page(); errors = []; page.on('pageerror', lambda e: errors.append(str(e)))
        try:
            page.goto((site/'proofs'/ident(A)/'reader.html').as_uri())
        except Exception as exc:  # pragma: no cover - depends on local browser policy
            browser.close(); pytest.skip(f'Browser policy blocks file navigation: {exc}')
        link = page.locator('#dependencies a[data-citation="OAI.A.deep"]')
        assert link.get_attribute('href') == f'../../sources/{source_name(A_DEEP)}#L3'
        link.click(); page.wait_for_load_state()
        assert page.url.endswith(f'/sources/{source_name(A_DEEP)}#L3')
        assert page.locator('#L3').inner_text().endswith('theorem deep : True := trivial')
        assert page.locator('.eyebrow').text_content().startswith('Cited dependency source')
        browser.close()
        assert not errors, errors
