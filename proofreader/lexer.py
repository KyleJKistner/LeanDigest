"""Small lossless Lean-aware lexer, NOT a replacement for Lean's extensible parser.

Offsets are Python Unicode code points. LSP UTF-16 conversion is explicit below.
Comments, raw strings, quoted identifiers and character literals are recognized
so that source text cannot masquerade as a theorem or a trust warning.
"""
from __future__ import annotations
from dataclasses import dataclass
import bisect
import re


@dataclass(frozen=True)
class Token:
    text: str
    kind: str
    start: int
    end: int
    line: int
    column: int


@dataclass
class Lexed:
    source: str
    tokens: list[Token]
    comments: list[Token]
    diagnostics: list[str]
    line_starts: list[int]

    def position(self, offset: int) -> tuple[int, int]:
        line = bisect.bisect_right(self.line_starts, offset) - 1
        return line + 1, offset - self.line_starts[line]

    def lsp_position(self, offset: int) -> dict[str, int]:
        line, col = self.position(offset)
        prefix = self.source[self.line_starts[line - 1]:offset]
        return {"line": line - 1, "character": len(prefix.encode("utf-16-le")) // 2}

    def code_mask(self) -> str:
        chars = list(self.source)
        # Mask comments and literal contents, preserve offsets and newlines.
        for token in self.comments + [t for t in self.tokens if t.kind in {"string", "char"}]:
            for i in range(token.start, token.end):
                if chars[i] not in "\r\n":
                    chars[i] = " "
        return "".join(chars)


MULTI = sorted(["<;>", ":=", "=>", "->", "<-", "::", "..", "...", "<|", "|>", "@[", "⟨", "⟩", "≤", "≥", "≠", "∧", "∨", "↔", "→", "←", "∀", "∃", "⊢"], key=len, reverse=True)


def identifier_start(c: str) -> bool:
    return c.isalpha() or c == "_"


def identifier_part(c: str) -> bool:
    return c.isalnum() or c in "_'₀₁₂₃₄₅₆₇₈₉ᵢⱼₖₗₘₙₚₛₜₓᵤᵥᵦᵧᵨᵩᵪ"


def lex(source: str) -> Lexed:
    tokens: list[Token] = []
    comments: list[Token] = []
    diagnostics: list[str] = []
    starts = [0] + [m.end() for m in re.finditer("\n", source)]
    n, i = len(source), 0

    def emit(start: int, end: int, kind: str) -> None:
        line = bisect.bisect_right(starts, start) - 1
        t = Token(source[start:end], kind, start, end, line + 1, start - starts[line])
        (comments if kind == "comment" else tokens).append(t)

    while i < n:
        if source[i].isspace():
            i += 1
            continue
        start = i
        if source.startswith("--", i):
            i = source.find("\n", i)
            if i < 0:
                i = n
            emit(start, i, "comment")
            continue
        if source.startswith("/-", i):
            depth, i = 1, i + 2
            while i < n and depth:
                if source.startswith("/-", i):
                    depth, i = depth + 1, i + 2
                elif source.startswith("-/", i):
                    depth, i = depth - 1, i + 2
                else:
                    i += 1
            if depth:
                diagnostics.append(f"Unterminated block comment at offset {start}.")
            emit(start, i, "comment")
            continue
        raw = re.match(r'r(#+)?"', source[i:])
        if raw:
            hashes = raw.group(1) or ""
            delim = '"' + hashes
            i += len(raw.group(0))
            end = source.find(delim, i)
            if end == -1:
                diagnostics.append(f"Unterminated raw string at offset {start}.")
                i = n
            else:
                i = end + len(delim)
            emit(start, i, "string")
            continue
        if source[i] == '"':
            i += 1
            closed = False
            while i < n:
                if source[i] == "\\":
                    i = min(n, i + 2)
                elif source[i] == '"':
                    i += 1
                    closed = True
                    break
                else:
                    i += 1
            if not closed:
                diagnostics.append(f"Unterminated string at offset {start}.")
            emit(start, i, "string")
            continue
        if source[i] == "«":
            end = source.find("»", i + 1)
            i = n if end < 0 else end + 1
            if end < 0:
                diagnostics.append(f"Unterminated quoted identifier at offset {start}.")
            emit(start, i, "identifier")
            continue
        if source[i] == "'":
            char_match = re.match(r"'(?:\\(?:u\{[0-9A-Fa-f]+\}|x[0-9A-Fa-f]{2}|.)|[^'\\\n])'", source[i:])
            if char_match:
                i += len(char_match.group())
                emit(start, i, "char")
                continue
        if identifier_start(source[i]):
            i += 1
            while i < n:
                if identifier_part(source[i]):
                    i += 1
                elif source[i] == "." and i + 1 < n and (identifier_start(source[i + 1]) or source[i + 1].isdigit()):
                    i += 1
                else:
                    break
            emit(start, i, "identifier")
            continue
        if source[i].isdigit():
            i += 1
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            emit(start, i, "number")
            continue
        matched = next((op for op in MULTI if source.startswith(op, i)), None)
        i += len(matched) if matched else 1
        emit(start, i, "symbol")
    return Lexed(source, tokens, comments, diagnostics, starts)


def balanced_split(text: str, delimiter: str) -> list[str]:
    """Split on an exact token only outside balanced delimiters and literals."""
    tokens = lex(text).tokens
    stack: list[str] = []
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩", "@[": "]"}
    cuts: list[tuple[int, int]] = []
    for t in tokens:
        if t.text in pairs:
            stack.append(pairs[t.text])
        elif stack and t.text == stack[-1]:
            stack.pop()
        elif not stack and t.text == delimiter:
            cuts.append((t.start, t.end))
    output, last = [], 0
    for a, b in cuts:
        output.append(text[last:a].strip())
        last = b
    output.append(text[last:].strip())
    return output
