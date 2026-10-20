"""Conservative lexical index of Lean declarations, used only for navigation links.

This reads trusted source text; it does not elaborate Lean. A full name is
recorded only when its namespace nesting and declaration header were read
without guessing. Anonymous instances, generated names (structure projections,
constructors, ``to_additive`` and ``_proof_`` auxiliaries), quoted identifiers
and duplicate names are reported, never linked. A module whose scopes or
brackets do not balance contributes no names at all.

A citation link is attached only when the cited Lean name provably denotes the
target: the target module is the citing module or is reachable from it through
the import headers of bundled modules. Lean forbids one name twice in one
environment, so that reachability fixes the constant. A link is a navigation
aid outside the deterministic reading; it is not evidence that a citation was
checked, explained, or faithfully rendered.
"""
from __future__ import annotations
from bisect import bisect_right
import re
from typing import Any, Callable

from .model import walk_steps

SCHEMA = 'leanglish.declaration-index/v1'
LINKS_SCHEMA = 'leanglish.citation-links/v1'
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
# A declaration name must end at a binder, a colon, a universe list or whitespace.
NAME_END = re.compile(r'(?:\s|[(\[{⦃:]|\.\{|\Z)')
READING_HREF, SOURCE_HREF = '../{}/reader.html', '../../sources/{}#L{}'
SAFE_HREF = re.compile(r'\.\./(?:[a-f0-9]{24}/reader\.html|\.\./sources/[a-f0-9]{24}\.html#L[1-9][0-9]*)')
STATUSES = ('reading', 'source', 'unresolved')
# Lean-generated auxiliaries (abstracted proofs, matchers) have no source declaration.
AUXILIARY = re.compile(r"\.(?:_proof|proof|match)_\d+(?:_\d+)*$")


def _is_ident_char(c: str) -> bool:
    return c.isalnum() or c in "_'!?"


def mask(source: str) -> str:
    """Blank comments, string and character literals, then syntax quotations.

    Offsets and every line break are preserved, so positions in the result are
    positions in the source. Unterminated comments or strings raise ValueError.
    """
    out = list(source); n = len(source); i = 0
    def blank(a: int, b: int) -> None:
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
        elif c == '"' or (c == 'r' and (i == 0 or not _is_ident_char(source[i-1])) and RAW.match(source, i)):
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
        elif c == "'" and (i == 0 or not _is_ident_char(source[i-1])) and CHAR.match(source, i):
            j = CHAR.match(source, i).end(); blank(i, j); i = j
        else:
            i += 1
    text = ''.join(out)
    # Syntax quotations can contain command keywords that declare nothing here.
    for m in list(re.finditer(r'`\(', text)):
        if out[m.start()] != '`': continue
        depth, j = 1, m.end()
        while j < n and depth:
            depth += {'(':1, ')':-1}.get(out[j], 0); j += 1
        if depth: raise ValueError('Unterminated syntax quotation')
        blank(m.start(), j)
    return ''.join(out)


def _lines(source: str) -> Callable[[int], int]:
    # Same numbering as the source pages, which use str.splitlines().
    starts, k = [], 0
    for line in source.splitlines(keepends=True):
        starts.append(k); k += len(line)
    return lambda pos: bisect_right(starts, pos) if starts else 1


def _name(token: str | None) -> bool:
    return token is not None and IDENT.fullmatch(token) is not None and token not in KEYWORDS and '«' not in token


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


def build_index(sources: dict[str, str]) -> dict:
    """Index bundled modules. Duplicate full names are ambiguous and never linked."""
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
            'skipped_declarations': dict(sorted(reasons.items())), 'imports': imports}


def closure(index: dict, module: str) -> set[str]:
    """The module plus every bundled module visibly reachable through import headers."""
    done, todo = set(), [module]
    while todo:
        m = todo.pop()
        if m in done: continue
        done.add(m); todo += [x for x in index['imports'].get(m, []) if x in index['imports']]
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
    reading, else the first module name, is chosen deterministically.
    """
    reach = closure(index, module); own = {d.name for d in document.declarations}
    names = {}
    for name in cited_names(document):
        here = sorted((m != module, m, ident) for m, ident in readings.get(name, [])
                      if m in reach and not (m == module and name in own))
        entry = index['names'].get(name)
        source = ({'href': SOURCE_HREF.format(source_page(entry['module']), entry['line']),
                   'module': entry['module'], 'line': entry['line']}
                  if entry and entry['module'] in reach else None)
        if here:
            _, m, ident = here[0]
            names[name] = {'status': 'reading', 'href': READING_HREF.format(ident), 'module': m,
                           'basis': 'same-module' if m == module else 'imported-bundled-module',
                           **({'source': source} if source else {})}
        elif source:
            names[name] = {'status': 'source', **source,
                           'basis': 'same-module' if source['module'] == module else 'imported-bundled-module'}
        else:
            reason = ('ambiguous-in-bundled-source' if name in index['ambiguous'] else
                      'compiler-generated-auxiliary' if AUXILIARY.search(name) else
                      'not-visibly-imported' if entry or name in readings else
                      'not-declared-in-bundled-source')
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
        hrefs = [v.get('href'), (v.get('source') or {}).get('href')] if v['status'] != 'unresolved' else []
        if v['status'] == 'unresolved' and ('href' in v or 'source' in v):
            raise ValueError('An unresolved citation cannot carry a link')
        for href in hrefs:
            if href is not None and (not isinstance(href, str) or not SAFE_HREF.fullmatch(href)):
                raise ValueError('Citation link is not a relative catalog target')
        if v['status'] != 'unresolved' and not isinstance(v.get('href'), str):
            raise ValueError('A resolved citation needs a link')
    return links


def summarize(payloads: list[dict], index: dict) -> dict:
    """Catalog-wide citation accounting; every cited name keeps its denominator."""
    pairs = {s: 0 for s in STATUSES}; reasons: dict[str, int] = {}; best: dict[str, int] = {}
    for p in payloads:
        for name, v in p['names'].items():
            pairs[v['status']] += 1
            if v['status'] == 'unresolved': reasons[v['reason']] = reasons.get(v['reason'], 0)+1
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
                          'unresolved_by_reason': dict(sorted(reasons.items()))},
            'index': {k: index[k] for k in ('method', 'elaborated', 'modules', 'modules_indexed', 'skipped_declarations')} |
                     {'failed_modules': len(index['failed_modules']), 'names_indexed': len(index['names']),
                      'ambiguous_names': len(index['ambiguous'])},
            'links_in_checked_reading': False, 'citations_checked': False}
