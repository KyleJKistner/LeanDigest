"""Conservative source indexing and structured outlines.

This is intentionally evidence='source': Lean syntax is extensible and a
lexical outline must never be presented as an elaborated or checked proof.
Every unsupported step retains its exact source and an explicit fallback.
"""
from __future__ import annotations
import re
from bisect import bisect_left
from pathlib import PurePosixPath
from .lexer import Token, lex, balanced_split
from .model import Declaration, Document, Span, Step, digest, walk_steps

DECLARATIONS = {"theorem", "lemma", "def", "abbrev", "example", "instance", "axiom", "opaque", "structure", "inductive"}
COMMANDS = DECLARATIONS | {"import", "namespace", "section", "end", "variable", "variables", "open", "include", "omit", "set_option", "attribute", "notation", "local", "scoped", "syntax", "macro", "macro_rules", "elab", "elab_rules", "initialize", "builtin_initialize", "export", "mutual", "universe", "universes"}
MODIFIERS = {"private", "protected", "noncomputable", "unsafe", "partial", "nonrec"}
TRUST_TOKENS = {
    "sorry": "The source contains an admitted proof (`sorry`).",
    "admit": "The source contains an admitted proof (`admit`).",
    "axiom": "This declaration introduces an axiom rather than proving it.",
    "native_decide": "This source uses native_decide; inspect the compiled proof's axiom dependencies.",
    "implemented_by": "An implementation replacement is present; review the execution trust boundary.",
}
TYPE_GLOSSES = {
    "ℕ": "a natural number", "Nat": "a natural number", "ℤ": "an integer", "Int": "an integer",
    "ℚ": "a rational number", "Rat": "a rational number", "ℝ": "a real number", "Real": "a real number",
    "ℂ": "a complex number", "Complex": "a complex number", "Prop": "a proposition",
}


def _span(source: str, start: int, end: int) -> Span:
    l = source.count("\n", 0, start) + 1
    el = source.count("\n", 0, max(start, end - 1)) + 1
    col = start - (source.rfind("\n", 0, start) + 1)
    return Span(start, end, l, el, col)


def _command_candidates(source: str) -> list[tuple[Token, int]]:
    lx = lex(source)
    by_line: dict[int, list[Token]] = {}
    for t in lx.tokens:
        by_line.setdefault(t.line, []).append(t)
    result: list[tuple[Token, int]] = []
    for line_tokens in by_line.values():
        i = 0
        # Skip same-line attributes and modifiers, but not arbitrary terms.
        while i < len(line_tokens):
            if line_tokens[i].text == "@[":
                nesting, i = 1, i + 1
                while i < len(line_tokens) and nesting:
                    nesting += int(line_tokens[i].text in {"[", "@["})
                    nesting -= int(line_tokens[i].text == "]")
                    i += 1
            elif line_tokens[i].text in MODIFIERS:
                i += 1
            else:
                break
        if i < len(line_tokens) and line_tokens[i].text in COMMANDS:
            result.append((line_tokens[i], line_tokens[0].start))
        elif i < len(line_tokens) and line_tokens[i].text == "#":
            result.append((line_tokens[i], line_tokens[0].start))
    # Commands in indented declaration bodies are not module commands.
    kept: list[tuple[Token, int]] = []
    active_indent: int | None = None
    for t, start in result:
        indent = len(source[:start].rsplit("\n", 1)[-1])
        if active_indent is not None and indent > active_indent:
            continue
        kept.append((t, start))
        active_indent = indent if t.text in DECLARATIONS else None
    return kept


def _top_assignment(text: str) -> tuple[str, str, int]:
    tokens = lex(text).tokens
    stack: list[str] = []
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩"}
    for t in tokens:
        if t.text in pairs:
            stack.append(pairs[t.text])
        elif stack and t.text == stack[-1]:
            stack.pop()
        elif not stack and t.text == ":=":
            return text[:t.start].strip(), text[t.end:].strip(), t.end
    return text.strip(), "", len(text)


def _parameters(signature: str) -> tuple[list[dict[str, str]], str]:
    tokens = lex(signature).tokens
    params: list[dict[str, str]] = []
    stack: list[Token] = []
    pairs = {"(": ")", "[": "]", "{": "}"}
    top_colon = None
    for t in tokens:
        if t.text in pairs:
            stack.append(t)
        elif stack and t.text == pairs[stack[-1].text]:
            opening = stack.pop()
            if not stack:
                inside = signature[opening.end:t.start].strip()
                parts = balanced_split(inside, ":")
                if len(parts) >= 2:
                    params.append({"names": parts[0], "type": ":".join(parts[1:]), "binder": opening.text})
                elif opening.text == "[":
                    params.append({"names": "", "type": inside, "binder": "["})
        elif not stack and t.text == ":" and top_colon is None:
            top_colon = t.end
            break
    return params, signature[top_colon:].strip() if top_colon is not None else signature


def _refs(text: str) -> list[str]:
    ignored = {"by", "only", "at", "with", "using", "fun", "let", "in", "show", "from", "calc", "this", "case", "if", "then", "else", "True", "False"}
    return sorted({t.text for t in lex(text).tokens if t.kind == "identifier" and t.text not in ignored and not t.text.startswith("_")})


def _display_list(argument: str) -> str:
    return argument.strip() or "the available hypotheses and definitions"


def classify_step(code: str) -> tuple[str, str, list[str], bool, str]:
    """Return an instruction-level rendering; never infer hidden tactic goals."""
    s = code.strip()
    # Remove a goal bullet but retain its source as the provenance.
    s = re.sub(r"^[·•]\s*", "", s)
    if not s:
        return "block", "Consider the following subproof.", [], False, ""
    # Combinators change sequencing and goal scope. Do not flatten them.
    if any(t.text in {"<;>", ";"} for t in lex(s).tokens):
        return "tactic-combinator", "A compound tactic is used here; expand the original step to inspect its scope.", _refs(s), True, "Compound tactic scope is not reconstructed in source mode."
    if s.startswith("|"):
        case, _, tail = s[1:].partition("=>")
        return "case", f"Case {case.strip()}.", [], False, tail.strip()
    head_match = re.match(r"([\w!?]+)(?:\s+|$)(.*)", s, re.S)
    if not head_match:
        return "unclassified", "This step has no source-level English template yet.", _refs(s), True, "Its exact source is retained; it is not counted as explained."
    op, arg = head_match.group(1), head_match.group(2).strip()
    if op == "by":
        return "block", "Proceed with the following proof.", [], False, arg
    if op in {"intro", "intros"}:
        return "introduce", f"Introduce {_display_list(arg)} as arbitrary objects or assumptions, according to the goal.", [], False, "Source mode does not know which introduced names denote objects and which denote hypotheses."
    if op in {"rintro", "rintros"}:
        return "introduce-pattern", f"Introduce and unpack the objects or assumptions with pattern {arg}.", [], False, ""
    if op == "classical":
        return "classical", "Work in classical logic for the following proof.", [], False, "The actual classical axioms used must be obtained from the elaborated proof, not inferred from this command."
    if op == "exact_mod_cast":
        return "cast-transfer", f"Use {arg}, transferring the statement across the relevant numeric coercions.", _refs(arg), False, "The coercion identities are not reconstructed in source mode."
    if op in {"exact", "exact?"}:
        if op.endswith("?"):
            return "proof-search", "Search for a proof of the current claim.", [], False, "The selected proof is available only after elaboration."
        return "use-proof", f"Use the proof {arg} to establish the current claim.", _refs(arg), False, ""
    if op in {"apply", "refine"}:
        return "apply", f"Apply {arg}; prove any premises that remain.", _refs(arg), False, ""
    if op in {"rw", "rwa", "rewrite"}:
        return "rewrite", f"Rewrite using {_display_list(arg)}." + (" Then discharge the resulting goal by assumption." if op == "rwa" else ""), _refs(arg), False, ""
    if op in {"simp", "simpa", "dsimp", "simp_all"}:
        label = "Simplify by unfolding definitions" if op == "dsimp" else "Simplify"
        return "simplify", f"{label} using {_display_list(arg)}." + (" Use the resulting proof for the current claim." if op == "simpa" else ""), _refs(arg), False, "The actual rewrite set is not inferred from the tactic name."
    if op in {"have", "suffices", "let"}:
        before, body, _ = _top_assignment(arg)
        prefix = {"have": "Establish the intermediate claim", "suffices": "It is sufficient to establish", "let": "Define"}[op]
        sentence = f"{prefix} {before}."
        if op == "let" and body and not body.startswith("by"):
            sentence = f"Set {before} := {body}."
        return "intermediate" if op != "let" else "let", sentence, _refs(body) if body and not body.startswith("by") else [], False, body
    if op in {"obtain", "rcases", "cases"}:
        return "cases", f"Split or unpack {arg} into the following cases or witnesses.", _refs(arg.split(" with ")[0]), False, ""
    if op == "by_cases":
        parts = balanced_split(arg, ":")
        condition = ":".join(parts[1:]).strip() if len(parts) > 1 else arg
        name = f" Denote the relevant case assumption by {parts[0].strip()}." if len(parts) > 1 else ""
        return "cases", f"Distinguish whether {condition} holds or fails." + name, [], False, ""
    if op == "by_contra":
        return "contradiction", f"Argue by contradiction, introducing {arg or 'the negation of the goal'}.", [], False, ""
    if op == "induction":
        return "induction", f"Proceed by induction on {arg.removesuffix('with').strip()}.", _refs(arg), False, ""
    if op == "case":
        return "case", f"Case {arg.partition('=>')[0].strip()}.", [], False, arg.partition("=>")[2].strip()
    if op in {"constructor", "left", "right"}:
        text = {"constructor": "Apply a constructor and establish its remaining components.", "left": "Establish the left alternative.", "right": "Establish the right alternative."}[op]
        return "constructor", text, [], False, ""
    if op in {"use", "exists"}:
        return "witness", f"Choose {arg} as the witness; verify the required property.", _refs(arg), False, ""
    if op == "subst":
        return "substitute", f"Substitute using the equality involving {arg}.", [], False, ""
    if op in {"change", "show"}:
        return "change-goal", f"Express the current claim as {arg}.", [], False, "Definitional equivalence must be checked by Lean."
    if op == "unfold":
        return "unfold", f"Unfold the definitions {_display_list(arg)}.", _refs(arg), False, ""
    if op in {"ext", "funext"}:
        return "extensionality", f"Reduce the equality to pointwise equality{(' at ' + arg) if arg else ''}.", [], False, ""
    if op == "calc":
        return "calculation", "Use the following chain of equalities or inequalities.", [], False, arg
    if op in {"ring", "ring_nf", "linarith", "nlinarith", "omega", "norm_num", "positivity", "norm_cast", "field_simp", "decide", "native_decide", "aesop", "tauto", "grind"}:
        descriptions = {
            "ring": "Verify the polynomial identity by ring normalization.",
            "ring_nf": "Normalize the polynomial expressions.",
            "linarith": "Use linear arithmetic on the available facts.",
            "nlinarith": "Use nonlinear arithmetic normalization and arithmetic consequences.",
            "omega": "Use integer or natural-number arithmetic reasoning.",
            "norm_num": "Normalize the numerical expressions.",
            "positivity": "Establish positivity or nonnegativity.",
            "norm_cast": "Normalize the casts between number systems.",
            "field_simp": "Clear denominators, retaining the required side conditions.",
            "decide": "Evaluate the decidable proposition.",
            "native_decide": "Evaluate the decidable proposition with native compilation.",
        }
        return "automation", descriptions.get(op, f"Use the automated procedure {op} on the current goals."), _refs(arg), False, "This identifies the method, not the internal mathematical derivation. Automation expansion requires typed extraction."
    if op in {"rfl", "assumption", "contradiction", "trivial"}:
        text = {"rfl": "The two expressions are equal by computation or reflexivity.", "assumption": "The current claim is among the available assumptions.", "contradiction": "The available assumptions yield a contradiction.", "trivial": "Discharge the current elementary goal."}[op]
        return op, text, [], False, ""
    if op in {"sorry", "admit"}:
        return "admission", "This claim is admitted here, not proved.", [], True, "This prevents any claim of a complete checked proof."
    if op in {"all_goals", "any_goals", "first", "try", "repeat", "focus", "next"}:
        return "control-flow", f"This step controls which goals are processed ({op}); inspect its source and nested scope.", _refs(arg), True, "Not flattened or counted as a mathematical explanation."
    return "unclassified", "This step has no source-level English template yet.", _refs(s), True, "Its exact source is retained; it is not counted as explained."


def _proof_steps(body: str, absolute: int, whole: str, decl_id: str) -> list[Step]:
    """Losslessly partition source by logical lines, then preserve layout nesting."""
    lx = lex(body)
    line_groups: dict[int, list[Token]] = {}
    for t in lx.tokens:
        line_groups.setdefault(t.line, []).append(t)
    if not line_groups:
        return []
    groups = list(line_groups.values())
    items: list[tuple[int, Step]] = []
    k, serial = 0, 0
    while k < len(groups):
        group = groups[k]
        start = group[0].start
        # Combine lines with unmatched bracket nesting (including term arguments).
        nesting = 0
        end = group[-1].end
        while True:
            for t in groups[k]:
                if t.text in {"(", "[", "{", "⟨"}:
                    nesting += 1
                elif t.text in {")", "]", "}", "⟩"}:
                    nesting -= 1
            end = groups[k][-1].end
            if nesting <= 0 or k + 1 == len(groups):
                break
            k += 1
        code = body[start:end]
        # Skip the outer `by` token but handle single-line `by exact ...`.
        if code.strip() == "by":
            k += 1
            continue
        if code.startswith("by "):
            start += 3
            code = code[3:]
        indent = group[0].column
        bullet = re.match(r"^[·•]\s*", code)
        if bullet:
            serial += 1
            wrapper = Step(f"{decl_id}:s{serial}", "case", "Subcase.", code,
                           _span(whole, absolute + start, absolute + end))
            items.append((indent, wrapper))
            removed = bullet.end()
            start += removed
            indent += removed
            code = code[removed:]
            if not code.strip():
                k += 1
                continue
        serial += 1
        rule, text, refs, fallback, detail = classify_step(code)
        step = Step(f"{decl_id}:s{serial}", rule, text, code, _span(whole, absolute + start, absolute + end), references=refs, fallback=fallback, detail=detail)
        items.append((indent, step))
        # Inline case / have bodies retain their own explicit child rendering.
        tail = ""
        if rule in {"case", "intermediate", "let"}:
            if rule == "case":
                _, sep, tail = code.partition("=>")
                if not sep:
                    tail = ""
            else:
                _, tail, _ = _top_assignment(code)
            tail = tail.strip()
            if tail.startswith("by "):
                tail = tail[3:].strip()
            elif tail == "by":
                tail = ""
            if tail:
                # Term RHSs and tactic RHSs are different: exact term fallback is explicit.
                r, txt, rs, fb, dt = classify_step(tail)
                if fb and rule in {"intermediate", "let"}:
                    r, txt, rs, fb = "term", f"Use the supplied term {tail}.", _refs(tail), False
                tail_at = whole.find(tail, absolute + start, absolute + end)
                child_span = _span(whole, tail_at, tail_at + len(tail)) if tail_at >= 0 else step.span
                step.children.append(Step(f"{step.id}:inline", r, txt, tail, child_span, references=rs, fallback=fb, detail=dt))
        k += 1
    roots: list[Step] = []
    stack: list[tuple[int, Step]] = []
    for indent, step in items:
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if stack:
            stack[-1][1].children.append(step)
        else:
            roots.append(step)
        stack.append((indent, step))
    def attach_cases(nodes: list[Step]) -> list[Step]:
        # Lean's `| case` clauses and bullet goals often share the parent's
        # indentation. Group only explicit case nodes, never arbitrary tactics.
        grouped: list[Step] = []
        for node in nodes:
            node.children = attach_cases(node.children)
            if node.rule == "case" and grouped and grouped[-1].rule in {"cases", "induction", "apply", "constructor"}:
                grouped[-1].children.append(node)
            else:
                grouped.append(node)
        return grouped
    return attach_cases(roots)


def parse_source(source: str, file: str = "Input.lean") -> Document:
    if "\x00" in source:
        raise ValueError("NUL bytes are not accepted in Lean source.")
    if len(source.encode("utf-8")) > 32_000_000:
        raise ValueError("Source exceeds the 32 MB per-file limit.")
    file = str(PurePosixPath(file.replace("\\", "/")))
    lx = lex(source)
    commands = _command_candidates(source)
    token_starts = [t.start for t in lx.tokens]
    declarations: list[Declaration] = []
    frames: list[dict] = [{"kind": "root", "name": "", "variables": []}]
    imports: list[str] = []
    warnings = list(lx.diagnostics)
    for i, (cmd, start) in enumerate(commands):
        end = commands[i + 1][1] if i + 1 < len(commands) else len(source)
        segment = source[cmd.end:end].strip()
        # Remove comments without changing token-level source interpretation.
        seg_tokens = lx.tokens[bisect_left(token_starts, cmd.end):bisect_left(token_starts, end)]
        if cmd.text == "namespace":
            name = seg_tokens[0].text if seg_tokens else ""
            frames.append({"kind": "namespace", "name": name, "variables": []})
            continue
        if cmd.text == "section":
            frames.append({"kind": "section", "name": seg_tokens[0].text if seg_tokens else "", "variables": []})
            continue
        if cmd.text == "end":
            if len(frames) > 1:
                frames.pop()
            else:
                warnings.append(f"Unmatched end at line {cmd.line}.")
            continue
        if cmd.text in {"variable", "variables"}:
            clean = " ".join(t.text for t in seg_tokens)
            frames[-1]["variables"].append(clean)
            continue
        if cmd.text == "import":
            imports.extend(t.text for t in seg_tokens if t.kind == "identifier")
            continue
        if cmd.text in {"macro", "macro_rules", "elab", "elab_rules", "syntax"}:
            warnings.append(f"Custom syntax or elaboration at line {cmd.line}; source indexing may miss generated declarations.")
        if cmd.text not in DECLARATIONS:
            continue
        tokens = seg_tokens
        if cmd.text == "example" or not tokens or tokens[0].text in {"(", "{", "[", ":"}:
            short = f"{cmd.text}@{cmd.line}"
            sig_start = cmd.end
        else:
            short = tokens[0].text
            sig_start = tokens[0].end
        namespace = ".".join(f["name"] for f in frames if f["kind"] == "namespace" and f["name"])
        if short.startswith("_root_."):
            name = short[len("_root_."):]
        else:
            name = f"{namespace}.{short}" if namespace else short
        raw = source[start:end].rstrip()
        signature, _, assign_end = _top_assignment(source[sig_start:end])
        # Comments adjacent to the next command do not belong to the signature.
        signature = signature.strip()
        params, proposition = _parameters(signature)
        identity = digest(f"{file}\0{name}\0{start}")[:20]
        body_start = sig_start + assign_end
        body = source[body_start:end]
        decl = Declaration(identity, name, cmd.text, file, proposition, raw, _span(source, start, end), parameters=params)
        decl.context = [v for frame in frames for v in frame["variables"]]
        decl.steps = _proof_steps(body, body_start, source, identity) if cmd.text not in {"axiom", "structure", "inductive"} else []
        token_words = {t.text for t in lx.tokens[bisect_left(token_starts, start):bisect_left(token_starts, end)] if t.kind == "identifier"}
        decl.warnings = [message for token, message in TRUST_TOKENS.items() if token in token_words]
        if cmd.text == "axiom":
            decl.warnings.append("This declaration introduces an axiom rather than proving it.")
        if "private" in source[start:cmd.start]:
            decl.warnings.append("Private declaration: its elaborated internal name must be obtained from Lean.")
        if "debug.skipKernelTC" in token_words:
            decl.warnings.append("Kernel-check bypass option appears in the source; no verified status is permitted.")
        decl.dependencies = sorted({r for s in walk_steps(decl.steps) for r in s.references if r != name})
        prior_comments = [c for c in lx.comments if c.end <= start and source[c.end:start].strip() == ""]
        if prior_comments and prior_comments[-1].text.startswith("/--"):
            decl.docstring = prior_comments[-1].text[3:-2].strip()
        decl.axes = {"discovery": "source-candidate", "statement": "source-not-elaborated", "proof": "source-outline", "english_fidelity": "not-certified"}
        declarations.append(decl)
    if len(frames) > 1:
        warnings.append("Unclosed namespace or section, or unsupported source layout.")
    file_info = {"path": file, "sha256": digest(source), "source": source, "imports": sorted(set(imports)), "byte_count": len(source.encode()), "discovery": "heuristic"}
    return Document(PurePosixPath(file).stem, [file_info], declarations, warnings, {"mode": "source", "trust": "not-elaborated", "pipeline_model_calls": 0})


def merge_documents(documents: list[Document], title: str = "ProofReader") -> Document:
    paths: set[str] = set()
    files, declarations, warnings = [], [], []
    for document in documents:
        for file in document.files:
            if file["path"] in paths:
                raise ValueError(f"Duplicate source path: {file['path']}")
            paths.add(file["path"])
            files.append(file)
        declarations.extend(document.declarations)
        warnings.extend(document.warnings)
    return Document(title, sorted(files, key=lambda f: f["path"]), sorted(declarations, key=lambda d: (d.file, d.span.start)), sorted(set(warnings)), {"mode": "source", "pipeline_model_calls": 0})
