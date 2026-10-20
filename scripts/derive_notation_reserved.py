#!/usr/bin/env python3
"""Derive proofreader/data/notation-reserved.json from a Mathlib checkout.

  python scripts/derive_notation_reserved.py MATHLIB_CHECKOUT --revision COMMIT

The data file lists the Mathlib names that a shortened project name in a
reading may not start with (docs/NOTATION.md, Collision rules). The checkout is
read as text, never built or executed.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from proofreader.notation import LIBRARY, NAME, RESERVED_DATA  # noqa: E402

MODIFIERS = r'(?:@\[[^\]]*\]\s*)*(?:(?:public|private|protected|noncomputable|nonrec|partial|unsafe|scoped|local|meta)\s+)*'
TERM_KINDS = ('def', 'abbrev', 'structure', 'class', 'inductive', 'class inductive', 'opaque', 'irreducible_def', 'axiom')
DECLARATION = re.compile('^'+MODIFIERS+r'(class\s+inductive|theorem|lemma|def|abbrev|structure|class|inductive|'
                         r'opaque|axiom|instance|irreducible_def|alias)\s+([^\s(:{\[⦃]+)')
SCOPE = re.compile('^'+MODIFIERS+r'(namespace|section|mutual|end)\b[ \t]*(\S*)')


def code_lines(text: str) -> Iterable[str]:
    """Source lines with (nested) block comments, line comments and string literals blanked."""
    depth = 0
    for line in text.splitlines():
        out, i = [], 0
        while i < len(line):
            if line.startswith('/-', i):
                depth += 1; i += 2
            elif depth and line.startswith('-/', i):
                depth -= 1; i += 2
            elif depth:
                i += 1
            elif line.startswith('--', i):
                break
            elif line[i] == '"':
                j = i+1
                while j < len(line) and line[j] != '"':
                    j += 2 if line[j] == '\\' else 1
                out.append('""'); i = j+1
            else:
                out.append(line[i]); i += 1
        yield ''.join(out)


def derive(mathlib: Path, revision: str) -> dict:
    """Mathlib names that a shortened project name must not repeat, read lexically.

    Every ``.lean`` file under ``mathlib/Mathlib`` is scanned for ``namespace``,
    ``section``, ``mutual`` and ``end`` lines and for declaration headers. A
    definition, structure, class, inductive type, opaque constant or axiom that
    is not private is kept when it is at the root (``Path``, ``LocallyFinite``)
    or directly inside a LIBRARY namespace (``MeasureTheory.Integrable``, shown
    as ``Integrable``). Theorems, instances and aliases are not kept. The scan
    does not elaborate Lean, so generated names (``to_additive``, structure
    fields) are missing.
    """
    root: set[str] = set(); library: dict[str, set[str]] = {ns: set() for ns in LIBRARY}
    for p in sorted((mathlib/'Mathlib').rglob('*.lean')):
        stack: list[str | None] = []
        for line in code_lines(p.read_text(encoding='utf-8', errors='replace')):
            m = SCOPE.match(line)
            if m:
                if m[1] == 'end':
                    stack = stack[:-1]
                else:
                    stack.append(m[2] if m[1] == 'namespace' else None)
                continue
            m = DECLARATION.match(line)
            if (not m or re.sub(r'\s+', ' ', m[1]) not in TERM_KINDS
                    or 'private' in re.sub(r'@\[[^\]]*\]', '', line[:m.start(1)]).split()):
                continue
            full = m[2][len('_root_.'):] if m[2].startswith('_root_.') else '.'.join([x for x in stack if x]+[m[2]])
            if not NAME.fullmatch(full):
                continue
            parts = full.split('.')
            if len(parts) == 1:
                root.add(full)
            elif len(parts) == 2 and parts[0] in library:
                library[parts[0]].add(parts[1])
    return {'schema': 'leanglish.notation-reserved/v1',
            'description': 'Mathlib definitions, structures, classes, inductive types, opaque constants and axioms '
                           'at the root or directly inside an opened library namespace, read lexically from the '
                           'source. A shortened name in a reading may not start with one of them; see docs/NOTATION.md.',
            'source': {'repository': 'https://github.com/leanprover-community/mathlib4', 'revision': revision},
            'derivation': 'python scripts/derive_notation_reserved.py MATHLIB_CHECKOUT --revision COMMIT',
            'root': sorted(root), 'library': {ns: sorted(v) for ns, v in library.items()}}


def main(argv: list[str] | None = None) -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument('mathlib', type=Path, help='a Mathlib checkout (the directory containing Mathlib/)')
    a.add_argument('--revision', required=True, help='the checkout commit, recorded in the data file')
    a.add_argument('-o', '--output', type=Path, default=RESERVED_DATA)
    args = a.parse_args(argv)
    data = derive(args.mathlib, args.revision)
    args.output.write_text(json.dumps(data, indent=0, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f"{len(data['root'])} root names; "+', '.join(f'{ns} {len(v)}' for ns, v in data['library'].items()))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
