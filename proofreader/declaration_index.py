"""Conservative lexical index of Lean declarations, used only for navigation links.

This reads trusted source text; it does not elaborate Lean. A full name is
recorded only when its namespace nesting and declaration header were read
without guessing. Anonymous instances, generated names (structure projections,
constructors, ``to_additive`` and ``_proof_`` auxiliaries) and quoted
identifiers are reported, never linked. A module whose scopes or brackets do
not balance contributes no names at all.

A citation link is attached only when the cited Lean name provably denotes the
target: the target module is the citing module or is reachable from it through
recorded import headers, and it is the only indexed declaration of that name so
reachable. Lean forbids one name twice in one environment, so that reachability
fixes the constant. A link is a navigation aid outside the deterministic
reading; it is not evidence that a citation was checked, explained, or
faithfully rendered.

The catalog can also bundle cited dependency modules. ``walk_imports`` follows
import headers from the solution modules through the project tree, and
``select_dependencies`` keeps only modules that declare a cited name and are
visibly imported by a citing module. Both read source text only; every module
they could not use, and every cap they hit, is recorded with its reason.
"""
from __future__ import annotations
from bisect import bisect_right
from collections import deque
import math
import re
import time
from typing import Any, Callable

from .model import walk_steps

SCHEMA = 'leanglish.declaration-index/v2'
LINKS_SCHEMA = 'leanglish.citation-links/v1'
DEPENDENCY_SCHEMA = 'leanglish.cited-dependency-sources/v1'
DECLARATIONS = frozenset('theorem lemma def abbrev instance structure class inductive opaque axiom'.split())
MODIFIERS = frozenset('private protected noncomputable partial unsafe nonrec scoped local'.split())
# Tokens that are never a section, namespace or declaration name.
KEYWORDS = DECLARATIONS | MODIFIERS | frozenset((
    'namespace section end mutual example deriving import open export variable universe in where '
    'attribute set_option notation infix infixl infixr prefix postfix macro macro_rules syntax '
    'elab elab_rules initialize omit include alias irreducible_def by fun').split())
LINE_BREAKS = '\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029'
OPEN, CLOSE = '([{⟨⦃', ')]}⟩⦄'
_ATOM = r"(?:«[^»\n]*»|(?![λΠΣ])[^\W\d][\w'!?]*)"
IDENT = re.compile(_ATOM+r'(?:\.'+_ATOM+r')*')
TOKEN = re.compile(r'@\[|['+re.escape(OPEN+CLOSE)+r']|'+IDENT.pattern+r'|\S')
CHAR = re.compile(r"'(?:\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F]{1,6}\}|.)|[^\\'\n])'")
RAW = re.compile(r'r(#*)"')
# mask() only acts where a comment, string, raw string or character literal can open.
SPECIAL = re.compile(r"""--|/-|"|(?<![\w'!?])(?:r(?=#*")|')""")
STRING_BODY = re.compile(r'(?:[^"\\]|\\[\s\S])*"')
KEEP_BREAKS = re.compile('[^'+re.escape(LINE_BREAKS)+']')
# A declaration name must end at a binder, a colon, a universe list or whitespace.
NAME_END = re.compile(r'(?:\s|[(\[{⦃:]|\.\{|\Z)')
READING_HREF, SOURCE_HREF = '../{}/reader.html', '../../sources/{}#L{}'
SAFE_HREF = re.compile(r'\.\./(?:[a-f0-9]{24}/reader\.html|\.\./sources/[a-f0-9]{24}\.html#L[1-9][0-9]*)')
STATUSES = ('reading', 'source', 'unresolved')
REASONS = ('ambiguous-in-bundled-source', 'not-visibly-imported', 'this-reading',
           'compiler-generated-auxiliary', 'not-in-declaration-index')
# Lean-generated auxiliaries (abstracted proofs, matchers) have no source declaration.
AUXILIARY = re.compile(r"\.(?:_proof|proof|match)_\d+(?:_\d+)*$")
HEADER_WORDS = frozenset(('prelude', 'module', 'public', 'meta'))
PRIVATE = re.compile(r'_private\.(?:[^.]+\.)+?0\.(.+)\Z')
# Module names that map to a file path without escaping: unquoted identifier
# components (Lean allows file names such as Kappa₁ and Lp'), never a separator.
MODULE_NAME = re.compile(r"(?![λΠΣ])[^\W\d][\w'!?]*(?:\.(?![λΠΣ])[^\W\d][\w'!?]*)*\Z")
# An unquoted identifier atom. Each component of a name that scan() indexes is one.
ATOM = re.compile(r"(?![λΠΣ])[^\W\d][\w'!?]*")
TYPE_KINDS = frozenset(('structure', 'class', 'inductive', 'class inductive'))
UNUSED = ('missing-file', 'unverified-source', 'unreadable-source', 'unreadable-header',
          'unsupported-module-name', 'path-outside-tree', 'not-visited-cap')
# Deterministic default bounds; a time bound is opt-in because hitting it depends on the machine.
CAPS = {'max_visited_modules': 100_000, 'max_read_bytes': 1_200_000_000, 'max_seconds': None,
        'max_selected_modules': 3_000, 'max_selected_bytes': 40_000_000}


def mask(source: str) -> str:
    """Blank comments, string and character literals, then syntax quotations.

    Offsets and every line break are preserved, so positions in the result are
    positions in the source. Unterminated comments or strings raise ValueError.
    """
    n = len(source); i = last = 0; pieces: list[str] = []
    def blank(text: str, a: int, b: int) -> None:
        nonlocal last
        pieces.extend((text[last:a], KEEP_BREAKS.sub(' ', text[a:b]))); last = b
    # Jump between the only characters that can open a comment or literal.
    while (m := SPECIAL.search(source, i)) is not None:
        i = m.start(); c = source[i]
        if source.startswith('--', i):
            j = source.find('\n', i); j = n if j < 0 else j
            blank(source, i, j); i = j
        elif source.startswith('/-', i):
            depth, j = 1, i+2
            while depth:
                a, b = source.find('/-', j), source.find('-/', j)
                if b < 0: raise ValueError('Unterminated block comment')
                if 0 <= a < b: depth, j = depth+1, a+2
                else: depth, j = depth-1, b+2
            blank(source, i, j); i = j
        elif c in '"r':
            if c == 'r':
                m = RAW.match(source, i); end = '"'+m[1]
                j = source.find(end, m.end())
                if j < 0: raise ValueError('Unterminated raw string literal')
                j += len(end)
            else:
                body = STRING_BODY.match(source, i+1)
                if body is None: raise ValueError('Unterminated string literal')
                j = body.end()
            blank(source, i, j); i = j
        elif (char := CHAR.match(source, i)) is not None:
            j = char.end(); blank(source, i, j); i = j
        else:
            i += 1
    text = ''.join(pieces)+source[last:]; pieces, last = [], 0
    # Syntax quotations can contain command keywords that declare nothing here.
    for m in re.finditer(r'`\(', text):
        if m.start() < last: continue
        depth, j = 1, m.end()
        while j < n and depth:
            depth += {'(':1, ')':-1}.get(text[j], 0); j += 1
        if depth: raise ValueError('Unterminated syntax quotation')
        blank(text, m.start(), j)
    return ''.join(pieces)+text[last:]


def _lines(source: str) -> Callable[[int], int]:
    # Same numbering as the source pages, which use str.splitlines().
    starts, k = [], 0
    for line in source.splitlines(keepends=True):
        starts.append(k); k += len(line)
    return lambda pos: bisect_right(starts, pos) if starts else 1


def _name(token: str | None) -> bool:
    return token is not None and IDENT.fullmatch(token) is not None and token not in KEYWORDS and '«' not in token


def header_imports(source: str) -> list[str]:
    """The imports of a module header, read without scanning the module body.

    Agrees with scan() wherever both succeed. An import that is not followed by
    one readable module name and then a line break or comment raises ValueError,
    as does an unterminated comment in the header: a dependency is never guessed.
    """
    return _header(source)[0]


def _header(source: str) -> tuple[list[str], int]:
    """Header imports and the offset after the last one, where commands can start."""
    n, out, body = len(source), [], 0
    def skip(i: int, *, lines: bool = True) -> int:
        while i < n:
            if source[i] in LINE_BREAKS and not lines: return i
            if source[i].isspace(): i += 1
            elif source.startswith('--', i):
                j = source.find('\n', i); i = n if j < 0 else j
            elif source.startswith('/-', i):
                depth, i = 1, i+2
                while depth:
                    a, b = source.find('/-', i), source.find('-/', i)
                    if b < 0: raise ValueError('Unterminated block comment in the module header')
                    depth, i = (depth+1, a+2) if 0 <= a < b else (depth-1, b+2)
            else: return i
        return i
    i = skip(0)
    while (m := IDENT.match(source, i)) is not None:
        if m[0] in HEADER_WORDS:
            i = skip(m.end()); continue
        if m[0] != 'import': break
        name = IDENT.match(source, skip(m.end()))
        if name is not None and name[0] == 'all':
            name = IDENT.match(source, skip(name.end()))
        end = skip(name.end(), lines=False) if name is not None else 0
        if name is None or not _name(name[0]) or (end < n and source[end] not in LINE_BREAKS):
            raise ValueError('Unsupported import syntax in the module header')
        out.append(name[0]); body = name.end(); i = skip(end)
    return out, body


def scan(source: str, module: str) -> dict:
    """Declarations and imports of one module. Raises ValueError on unbalanced scopes."""
    text = mask(source); line = _lines(source)
    toks = [(m.group(), m.start(), m.end()) for m in TOKEN.finditer(text)]
    found, skipped, imports, scopes, stack, pending = [], [], [], [], [], []
    header, prev = True, None
    def same_line(k: int, i: int) -> bool:
        return k < len(toks) and line(toks[k][1]) == line(toks[i][1])
    i = 0
    while i < len(toks):
        t, start, end = toks[i]
        if t == '@[' or (len(t) == 1 and t in OPEN):
            stack.append(t); i += 1; continue
        if len(t) == 1 and t in CLOSE:
            if not stack or OPEN.index(stack[-1][-1]) != CLOSE.index(t):
                raise ValueError(f'Unbalanced bracket at line {line(start)}')
            stack.pop()
            if not stack: prev = t
            i += 1; continue
        if stack:
            i += 1; continue
        if header:
            k = i+1+(i+1 < len(toks) and toks[i+1][0] == 'all')
            if t == 'import' and k < len(toks) and _name(toks[k][0]):
                imports.append(toks[k][0]); i = k+1; continue
            if t not in {'prelude', 'module', 'public', 'meta'}: header = False
        if t in KEYWORDS and start and text[start-1] in '.`':
            # A name literal (`instance) or dot notation (.structure, x.1.end) is a term, not a command.
            pending, prev = [], text[start-1]+t; i += 1; continue
        if t in MODIFIERS:
            pending.append(t); prev = t; i += 1; continue
        if t == 'namespace':
            if not _name(toks[i+1][0] if i+1 < len(toks) else None) or '_root_' in toks[i+1][0]:
                raise ValueError(f'Unrecognized namespace at line {line(start)}')
            scopes += [('namespace', part) for part in toks[i+1][0].split('.')]
            pending, prev = [], t; i += 2; continue
        if t in {'section', 'end', 'mutual'}:
            named = t != 'mutual' and same_line(i+1, i) and _name(toks[i+1][0])
            parts = toks[i+1][0].split('.') if named else ['']
            if t == 'section':
                scopes += [('section', part) for part in parts]
            elif t == 'mutual':
                scopes.append(('mutual', ''))
            elif not named and scopes and scopes[-1][0] == 'mutual':
                scopes.pop()
            else:
                closing = scopes[len(scopes)-len(parts):] if len(parts) <= len(scopes) else None
                if not closing or [p for _, p in closing] != parts or any(k == 'mutual' for k, _ in closing) or (not named and closing[0][0] != 'section'):
                    raise ValueError(f'Unmatched end at line {line(start)}')
                del scopes[len(scopes)-len(parts):]
            pending, prev = [], t; i += 2 if named else 1; continue
        if t in DECLARATIONS and not (t == 'instance' and prev == 'deriving'):
            kind, j = t, i+1
            if t == 'class' and j < len(toks) and toks[j][0] in {'inductive', 'abbrev'}:
                kind, j = 'class '+toks[j][0], j+1
            if t == 'instance' and j+1 < len(toks) and toks[j][0] == '(' and toks[j+1][0] == 'priority':
                depth = 0
                while j < len(toks):
                    depth += (toks[j][0] in OPEN) - (toks[j][0] in CLOSE); j += 1
                    if not depth: break
            name = toks[j][0] if j < len(toks) else None
            row = {'module': module, 'line': line(start), 'kind': kind}
            if _name(name) and NAME_END.match(text, toks[j][2]):
                namespace = '.'.join(p for k, p in scopes if k == 'namespace')
                full = name[7:] if name.startswith('_root_.') else (namespace+'.'+name if namespace else name)
                if 'private' in pending:
                    full = '_private.'+module+'.0.'+full
                found.append({**row, 'name': full, 'private': 'private' in pending})
            else:
                anonymous = t == 'instance' and (name in {':', '[', '{', '(', '⦃', 'where'} or name is None)
                reason = 'anonymous-instance' if anonymous else 'quoted-identifier' if name and '«' in name else 'unrecognized-header'
                skipped.append({**row, 'reason': reason})
            pending, prev = [], t; i += 1; continue
        if t == 'example':
            skipped.append({'module': module, 'line': line(start), 'kind': t, 'reason': 'anonymous-example'})
        pending, prev = [], t; i += 1
    if stack: raise ValueError('Unclosed bracket at end of module')
    return {'declarations': found, 'skipped': skipped, 'imports': imports}


def build_index(sources: dict[str, str], headers: dict[str, list[str]] | None = None) -> dict:
    """Index bundled modules. A duplicate full name is listed under ``ambiguous``.

    ``headers`` holds the import headers of further modules that were read only
    for reachability (``header_imports``); they contribute no names. A module
    indexed here keeps the imports that scan() read.
    """
    seen: dict[str, list[dict]] = {}; skipped, failed, imports = [], {}, {}
    for module in sorted(sources):
        try:
            result = scan(sources[module], module)
        except ValueError as exc:
            failed[module] = str(exc); continue
        imports[module] = sorted(set(result['imports']))
        skipped += result['skipped']
        for d in result['declarations']:
            seen.setdefault(d['name'], []).append({k: d[k] for k in ('module', 'line', 'kind')})
    reasons: dict[str, int] = {}
    for s in skipped: reasons[s['reason']] = reasons.get(s['reason'], 0)+1
    return {'schema': SCHEMA, 'method': 'lexical-source-scan', 'elaborated': False,
            'modules': len(sources), 'modules_indexed': len(imports), 'failed_modules': failed,
            'names': {n: v[0] for n, v in sorted(seen.items()) if len(v) == 1},
            'ambiguous': {n: v for n, v in sorted(seen.items()) if len(v) > 1},
            'skipped_declarations': dict(sorted(reasons.items())), 'imports': imports,
            'header_imports': {m: sorted(set(v)) for m, v in sorted((headers or {}).items()) if m not in imports}}


def closure(index: dict, module: str, *, recorded: bool = True) -> set[str]:
    """The module plus every module visibly reachable through import headers.

    The headers are those of indexed modules and, unless ``recorded`` is false,
    the header-only records of modules read for reachability.
    """
    graphs = (index['imports'], index.get('header_imports', {}) if recorded else {})
    done, todo = set(), [module]
    while todo:
        m = todo.pop()
        if m in done: continue
        done.add(m)
        edges = graphs[0][m] if m in graphs[0] else graphs[1].get(m, [])
        todo += [x for x in edges if x in graphs[0] or x in graphs[1]]
    return done


def cited_names(document) -> list[str]:
    names = set()
    for d in document.declarations:
        names |= set(d.dependencies)
        for s in walk_steps(d.steps): names |= set(s.references)
    return sorted(n for n in names if isinstance(n, str) and n)


def reading_map(readings: dict[tuple[str, str], str]) -> dict[str, list[tuple[str, str]]]:
    """(module, theorem) -> proof identifier, regrouped by theorem name."""
    out: dict[str, list[tuple[str, str]]] = {}
    for (module, name), ident in sorted(readings.items()): out.setdefault(name, []).append((module, ident))
    return out


def citation_links(document, module: str, index: dict, readings: dict[str, list[tuple[str, str]]],
                   source_page: Callable[[str], str]) -> dict:
    """Resolve each cited name of one reading in ``module``.

    ``readings`` comes from reading_map. A bundled reading of the same constant
    is preferred, then its declaration line on a bundled source page. Several
    visible readings of one name denote one constant; the citing module's own
    reading, else the first module name, is chosen deterministically. A source
    line is used only when it is the one indexed declaration of the name that
    the citing module can see; two visible declarations make it ambiguous.
    """
    reach = closure(index, module); own = {d.name for d in document.declarations}
    names = {}; bundled = None
    def basis(m: str) -> str:
        nonlocal bundled
        if m == module: return 'same-module'
        bundled = closure(index, module, recorded=False) if bundled is None else bundled
        return 'imported-bundled-module' if m in bundled else 'imported-via-recorded-headers'
    for name in cited_names(document):
        here = sorted((m != module, m, ident) for m, ident in readings.get(name, [])
                      if m in reach and not (m == module and name in own))
        entries = [index['names'][name]] if name in index['names'] else index['ambiguous'].get(name, [])
        visible = [e for e in entries if e['module'] in reach]
        source = ({'href': SOURCE_HREF.format(source_page(visible[0]['module']), visible[0]['line']),
                   'module': visible[0]['module'], 'line': visible[0]['line']}
                  if len(visible) == 1 else None)
        if here:
            _, m, ident = here[0]
            names[name] = {'status': 'reading', 'href': READING_HREF.format(ident), 'module': m,
                           'basis': basis(m), **({'source': source} if source else {})}
        elif source:
            names[name] = {'status': 'source', **source, 'basis': basis(source['module'])}
        else:
            # State only what the bundle shows: a known but unreachable target comes
            # before name-shape guesses, and "not indexed" is not "not declared".
            others = [m for m, _ in readings.get(name, []) if not (m == module and name in own)]
            reason = ('ambiguous-in-bundled-source' if len(visible) > 1 else
                      'not-visibly-imported' if entries or others else
                      'this-reading' if name in own else
                      'compiler-generated-auxiliary' if AUXILIARY.search(name) else
                      'not-in-declaration-index')
            names[name] = {'status': 'unresolved', 'reason': reason}
    counts = {s: sum(v['status'] == s for v in names.values()) for s in STATUSES}
    return {'schema': LINKS_SCHEMA, 'module': module, 'names': names, 'counts': counts,
            'scope': 'Navigation aid outside the checked reading. A link identifies the exact Lean name in a '
                     'bundled reading or source line; it does not certify that the citation was explained.'}


def validate_links(links: Any) -> dict:
    """Reject anything but relative catalog targets before a page embeds the links."""
    if (not isinstance(links, dict) or links.get('schema') != LINKS_SCHEMA or
            not isinstance(links.get('names'), dict) or len(links['names']) > 100_000):
        raise ValueError('Unsupported citation links')
    for name, v in links['names'].items():
        if not isinstance(name, str) or not name or not isinstance(v, dict) or v.get('status') not in STATUSES:
            raise ValueError('Invalid citation link entry')
        if v['status'] == 'unresolved':
            if 'href' in v or 'source' in v: raise ValueError('An unresolved citation cannot carry a link')
            if v.get('reason') not in REASONS: raise ValueError('An unresolved citation needs a stated reason')
            continue
        source = v.get('source', {})
        if not isinstance(source, dict): raise ValueError('Invalid citation source')
        for href in (v.get('href'), source.get('href')):
            if href is not None and (not isinstance(href, str) or not SAFE_HREF.fullmatch(href)):
                raise ValueError('Citation link is not a relative catalog target')
        if not isinstance(v.get('href'), str):
            raise ValueError('A resolved citation needs a link')
    return links


def summarize(payloads: list[dict], index: dict) -> dict:
    """Catalog-wide citation accounting; every cited name keeps its denominator."""
    pairs = {s: 0 for s in STATUSES}; reasons: dict[str, int] = {}; best: dict[str, int] = {}; bases: dict[str, int] = {}
    for p in payloads:
        for name, v in p['names'].items():
            pairs[v['status']] += 1
            if v['status'] == 'unresolved': reasons[v['reason']] = reasons.get(v['reason'], 0)+1
            else: bases[v.get('basis', 'unrecorded')] = bases.get(v.get('basis', 'unrecorded'), 0)+1
            best[name] = min(best.get(name, 2), STATUSES.index(v['status']))
    def names(selected):
        return {'cited': len(selected), **{'linked_to_'+s if s != 'unresolved' else s: sum(best[n] == k for n in selected)
                                            for k, s in enumerate(STATUSES)}}
    return {'schema': 'leanglish.citation-links-summary/v1', 'readings': len(payloads),
            'readings_linking_another_reading': sum(p['counts']['reading'] > 0 for p in payloads),
            'names': names(list(best)), 'project_names': names([n for n in best if n.startswith('OAI.')]),
            'name_status_rule': 'best link from any citing reading; a name can stay unresolved in a reading that cannot see its declaration',
            'citations': {'total': sum(pairs.values()), 'linked_to_reading': pairs['reading'],
                          'linked_to_source': pairs['source'], 'unresolved': pairs['unresolved'],
                          'unresolved_by_reason': dict(sorted(reasons.items())),
                          'linked_by_import_basis': dict(sorted(bases.items()))},
            'index': {k: index[k] for k in ('method', 'elaborated', 'modules', 'modules_indexed', 'skipped_declarations')} |
                     {'failed_modules': len(index['failed_modules']), 'names_indexed': len(index['names']),
                      'ambiguous_names': len(index['ambiguous']),
                      'header_only_modules': len(index.get('header_imports', {}))},
            'links_in_checked_reading': False, 'citations_checked': False}


def searched_components(name: str, namespace: str = 'OAI.') -> list[str] | None:
    """The components a source must spell to declare ``name``, if the walk searches for it.

    A private name drops Lean's ``_private.<module>.0.`` prefix. Only names in
    ``namespace`` whose components are unquoted identifiers are searched.
    """
    if (m := PRIVATE.match(name)) is not None: name = m[1]
    parts = name.split('.')
    return parts if name.startswith(namespace) and all(ATOM.fullmatch(p) for p in parts) else None


def validate_caps(caps: dict | None) -> dict:
    """CAPS with ``caps`` applied. Counts and byte bounds are non-negative integers;
    ``max_seconds`` is None or a finite non-negative number. Anything else raises."""
    if caps is not None and not isinstance(caps, dict): raise ValueError('Cited dependency caps must be an object')
    merged = {**CAPS, **(caps or {})}
    def valid(k: str, v: Any) -> bool:
        if k == 'max_seconds' and v is None: return True
        number = (int, float) if k == 'max_seconds' else (int,)
        return not isinstance(v, bool) and isinstance(v, number) and math.isfinite(v) and v >= 0
    if set(merged) != set(CAPS) or not all(valid(k, v) for k, v in merged.items()):
        raise ValueError('Unknown or invalid cited dependency cap')
    return merged


def walk_imports(roots: list[str], known: dict[str, str], load: Callable[[str], tuple[str | None, str]],
                 wanted: set[str], *, prefix: str = 'OAI.', namespace: str = 'OAI.', caps: dict | None = None,
                 failed_known: dict[str, str] | None = None, log: Callable[[str], None] | None = None) -> dict:
    """Follow import headers breadth-first from ``roots`` through ``prefix`` modules.

    ``known`` maps modules already bundled to their text; they are traversed but
    not scanned. ``failed_known`` lists the known modules that the bundled index
    could not read, with the error; a wanted name that such a module spells is
    recorded as unindexed there. ``load(module)`` returns ``(text, 'read')`` or
    ``(None, reason)`` with a reason from UNUSED. Imports outside ``prefix`` are
    counted, not followed.

    The walk searches for the ``wanted`` names in ``namespace``. A visited module
    is scanned only when the comment-free text after its imports has every
    component of such a name as an identifier atom; a declaration that scan()
    indexes spells each component in a namespace or name token there, so none is
    skipped. Other names are not searched (``outside-searched-namespace``).
    """
    caps = validate_caps(caps); start = time.monotonic(); failed_known = failed_known or {}
    wanted = {n for n in wanted if searched_components(n, namespace)}
    last: dict[str, list[tuple[str, frozenset[str]]]] = {}
    for n in sorted(wanted):
        parts = searched_components(n, namespace); last.setdefault(parts[-1], []).append((n, frozenset(parts)))
    headers, unused, declares, unindexed, failed, sizes = {}, {}, {}, {}, {}, {}
    external: set[str] = set(); hit: list[str] = []; read = scanned = visited = 0
    frontier = sorted(set(roots)); seen = set(frontier)
    while frontier:
        following: set[str] = set()
        for m in frontier:
            if m in known:
                text = known[m]
            else:
                if not MODULE_NAME.fullmatch(m):
                    unused[m] = 'unsupported-module-name'; continue
                over = [k for k, v in (('max_visited_modules', visited), ('max_read_bytes', read),
                                       ('max_seconds', time.monotonic()-start)) if caps[k] is not None and v >= caps[k]]
                if over:
                    unused[m] = 'not-visited-cap'
                    for k in over:
                        if k not in hit:
                            hit.append(k)
                            if log: log(f'Cited dependency walk stopped at {k}={caps[k]}; unvisited modules are recorded')
                    continue
                text, why = load(m); visited += 1
                if text is None:
                    unused[m] = why if why in UNUSED else 'unreadable-source'; continue
                size = len(text.encode('utf-8')); read += size; sizes[m] = size
            try:
                imports, body = _header(text)
            except ValueError:
                unused[m] = 'unreadable-header'; continue
            headers[m] = imports
            if m in known and m not in failed_known: candidates = []
            else:
                # Declarations and namespaces follow the header; comments and literals declare nothing.
                try: atoms = set(ATOM.findall(mask(text), body))
                except ValueError: atoms = set(ATOM.findall(text, body))  # scan() fails on it too.
                candidates = [n for a in atoms & last.keys() for n, parts in last[a] if parts <= atoms]
            if m in known and m in failed_known:
                # The bundled index already failed on this module; its names stay unknown, not absent.
                failed[m] = failed_known[m]
                for n in sorted(candidates): unindexed.setdefault(n, []).append(m)
            elif candidates:
                scanned += 1
                try:
                    rows = scan(text, m)['declarations']
                except ValueError as exc:
                    failed[m] = str(exc)
                    for n in sorted(candidates): unindexed.setdefault(n, []).append(m)
                    rows = []
                for d in rows:
                    if d['name'] in wanted:
                        declares.setdefault(d['name'], []).append({k: d[k] for k in ('module', 'line', 'kind')})
            for x in imports:
                if not x.startswith(prefix): external.add(x)
                elif x not in seen: seen.add(x); following.add(x)
        frontier = sorted(following)
    return {'headers': headers, 'unused': dict(sorted(unused.items())), 'declares': declares,
            'unindexed': unindexed, 'failed': dict(sorted(failed.items())), 'sizes': sizes,
            'caps': caps, 'caps_hit': hit, 'prefix': prefix, 'namespace': namespace,
            'counts': {'roots': len(set(roots)), 'modules_visited': visited, 'bytes_read': read,
                       'modules_scanned': scanned, 'modules_failed_to_index': len(failed),
                       'external_imports': len(external)}}


def reachable_headers(headers: dict[str, list[str]], roots: list[str], targets: set[str]) -> dict[str, list[str]]:
    """The header records of modules on some import path from ``roots`` to ``targets``.

    Every target that a root reaches through ``headers`` is still reached through
    the result, so pruning the other records changes no citation link.
    """
    forward: set[str] = set(); todo = [r for r in roots if r in headers]
    while todo:
        m = todo.pop()
        if m not in forward: forward.add(m); todo += [x for x in headers[m] if x in headers]
    reverse: dict[str, list[str]] = {}
    for m in forward:
        for x in headers[m]:
            if x in forward: reverse.setdefault(x, []).append(m)
    back: set[str] = set(); todo = [t for t in targets if t in forward]
    while todo:
        m = todo.pop()
        if m not in back: back.add(m); todo += reverse.get(m, [])
    return {m: headers[m] for m in sorted(back)}


def _paths(graph: dict[str, list[str]], root: str) -> dict[str, str | None]:
    """Breadth-first parents from ``root`` over modules whose header was read."""
    parent: dict[str, str | None] = {root: None}; todo = deque([root])
    while todo:
        m = todo.popleft()
        for x in graph.get(m, []):
            if x in graph and x not in parent: parent[x] = m; todo.append(x)
    return parent


def select_dependencies(walk: dict, citing: dict[str, set[str]], base: dict, *,
                        log: Callable[[str], None] | None = None) -> dict:
    """Choose the dependency modules to bundle and record each cited name's search outcome.

    ``citing`` maps each solution module to the names its bundled readings cite;
    ``base`` is the index of the bundled solution modules. A module is selected
    when, for some citing module that imports it, it holds the only visible
    declaration of a cited name. Selection caps keep the modules that resolve
    the most names; the rest are recorded as dropped, never silently omitted.
    """
    caps, graph, solution = walk['caps'], walk['headers'], set(base['imports'])
    pairs: dict[str, set[tuple[str, str]]] = {}; outcome: dict[str, dict] = {}; via: dict[str, list[str]] = {}
    incomplete: dict[str, list[str]] = {}
    def declared(name: str) -> list[dict]:
        return ([base['names'][name]] if name in base['names'] else base['ambiguous'].get(name, [])) + walk['declares'].get(name, [])
    for root in sorted(citing):
        parent = _paths(graph, root) if root in graph else {root: None}
        gaps = sorted({walk['unused'][x] for m in parent for x in graph.get(m, []) if x in walk['unused']} |
                      ({walk['unused'][root]} if root in walk['unused'] else set()))
        if gaps: incomplete[root] = gaps
        for name in sorted(citing[root]):
            entries = declared(name)
            visible = [e for e in entries if e['module'] in parent]
            o = outcome.setdefault(name, {'declared': bool(entries), 'visible': set(), 'ambiguous': False,
                                          'citing_modules': 0, 'complete': True})
            o['citing_modules'] += 1; o['complete'] = o['complete'] and not gaps
            if len(visible) > 1: o['ambiguous'] = True
            elif visible:
                target = visible[0]['module']; o['visible'].add(target)
                if target not in solution:
                    pairs.setdefault(target, set()).add((root, name))
                    if target not in via:
                        path, m = [], target
                        while m is not None: path.append(m); m = parent[m]
                        via[target] = path[::-1]
    selected, dropped, total, hit = [], {}, 0, list(walk['caps_hit'])
    for module in sorted(pairs, key=lambda d: (-len({n for _, n in pairs[d]}), d)):
        size = walk['sizes'][module]
        cap = ('max_selected_modules' if len(selected) >= caps['max_selected_modules'] else
               'max_selected_bytes' if total+size > caps['max_selected_bytes'] else None)
        if cap is None:
            selected.append(module); total += size; continue
        dropped[module] = cap
        if cap not in hit:
            hit.append(cap)
            if log: log(f'Cited dependency selection reached {cap}={caps[cap]}; dropped modules are recorded')
    chosen = set(selected); names = {}
    for name, o in sorted(outcome.items()):
        found = o['visible']
        search = ('declared-in-solution-module' if found & solution else
                  'declared-in-cited-dependency' if found & chosen else
                  'dropped-by-selection-cap' if found else
                  'ambiguous-in-visible-modules' if o['ambiguous'] else
                  'declared-only-in-modules-not-imported' if o['declared'] else
                  'outside-searched-namespace' if searched_components(name, walk['namespace']) is None else
                  'candidate-module-not-indexed' if name in walk['unindexed'] else
                  'not-declared-in-visited-modules')
        names[name] = {'search': search, 'citing_modules': o['citing_modules'], 'import_closure_complete': o['complete']}
    modules = {m: {'bytes': walk['sizes'][m], 'cited_names': sorted({n for _, n in pairs[m]}),
                   'citing_modules': sorted({r for r, _ in pairs[m]}), 'import_path': via[m]} for m in selected}
    return {'modules': modules, 'dropped': dict(sorted(dropped.items())), 'names': names,
            'incomplete_closures': incomplete, 'caps_hit': hit, 'selected_bytes': total}


def dependency_report(walk: dict, selection: dict, payloads: list[dict], index: dict, *, hashes_checked: bool) -> dict:
    """The evidence record for cited dependency sources, with every cited name's final status.

    A name that no visited module declares is marked ``parent-type-in-bundled-source``
    when, for a citing reading, the name without its last component is a
    structure, class or inductive type indexed in a bundled module it imports.
    """
    best: dict[str, dict] = {}; reach: dict[str, set[str]] = {}; typed: set[str] = set()
    for p in payloads:
        for name, v in p['names'].items():
            if v['status'] == 'unresolved' and '.' in name and name not in typed:
                parent = name.rsplit('.', 1)[0]
                entries = [index['names'][parent]] if parent in index['names'] else index['ambiguous'].get(parent, [])
                if any(e['kind'] in TYPE_KINDS for e in entries):
                    seen = reach.setdefault(p['module'], closure(index, p['module']))
                    if any(e['kind'] in TYPE_KINDS and e['module'] in seen for e in entries): typed.add(name)
            rank = STATUSES.index(v['status'])
            if name not in best or rank < best[name][0]:
                best[name] = (rank, {'link': v['status'], **({'reason': v['reason']} if v['status'] == 'unresolved'
                                                             else {'module': v['module'], 'basis': v['basis']})})
    searched = selection['names']
    names = {n: {**v, **searched.get(n, {'search': 'not-searched'})} for n, (_, v) in sorted(best.items())}
    for n in typed & names.keys():
        if names[n]['search'] == 'not-declared-in-visited-modules': names[n]['search'] = 'parent-type-in-bundled-source'
    def tally(key: str, project: bool = False) -> dict[str, int]:
        rows = [v[key] for n, v in names.items() if not project or n.startswith('OAI.')]
        return {k: rows.count(k) for k in sorted(set(rows))}
    unused: dict[str, int] = {}
    for reason in walk['unused'].values(): unused[reason] = unused.get(reason, 0)+1
    return {'schema': DEPENDENCY_SCHEMA, 'method': 'lexical-import-headers-and-declarations', 'elaborated': False,
            'followed_import_prefix': walk['prefix'], 'searched_name_namespace': walk['namespace'],
            'source_hashes_checked': hashes_checked,
            'caps': walk['caps'], 'caps_hit': selection['caps_hit'],
            'counts': {**walk['counts'], 'modules_not_used': dict(sorted(unused.items())),
                       'selected_modules': len(selection['modules']), 'selected_bytes': selection['selected_bytes'],
                       'dropped_by_selection_cap': len(selection['dropped']),
                       'citing_modules_with_incomplete_closure': len(selection['incomplete_closures'])},
            'names_by_link': tally('link'), 'names_by_search': tally('search'),
            'project_names_by_search': tally('search', True),
            'modules': selection['modules'], 'dropped': selection['dropped'],
            'modules_not_used': walk['unused'], 'modules_failed_to_index': walk['failed'],
            'incomplete_closures': selection['incomplete_closures'], 'names': names,
            'scope': 'Lexical selection of bundled source pages. A cited dependency page is the exact upstream '
                     'file; it is not an English explanation, and a link to it does not check the citation.'}
