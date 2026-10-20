"""Offline HTML and Markdown exports. Displayed text is never executed as markup."""
from __future__ import annotations
from dataclasses import fields
import html
import json
import re
from pathlib import Path
from typing import Any
from . import __version__
from .branding import PRODUCT_NAME, TAGLINE
from .model import Document, Declaration, Span, Step, SCHEMA, report

ASSETS = Path(__file__).parent / "web"


def load_document(data: str | bytes | dict[str, Any]) -> Document:
    """Load our own versioned IR, not a proof certificate. No imported trust claim is verified."""
    if isinstance(data, (str, bytes)):
        if len(data) > 128_000_000: raise ValueError("Reading document exceeds the size limit")
        from .kernel_io import strict_json
        data = strict_json(data)
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("Unsupported reading document schema")
    budget = [0]
    def span(s):
        if not isinstance(s, dict): raise ValueError("Missing source span")
        values = {k: s[k] for k in ("start", "end", "line", "end_line")}
        if any(type(x) is not int or x < 0 for x in values.values()): raise ValueError("Invalid source span")
        if values["end"] < values["start"]: raise ValueError("Reversed source span")
        return Span(**values, column=s.get("column", 0))
    def step(s, depth=0):
        budget[0] += 1
        if depth > 180 or budget[0] > 200_000: raise ValueError("Reading tree exceeds the size budget")
        if not isinstance(s, dict): raise ValueError("Invalid reading step")
        known = {f.name for f in fields(Step)} - {"children", "span"}
        kwargs = {k:v for k,v in s.items() if k in known}
        for k in ("id", "rule", "text"):
            if not isinstance(kwargs.get(k), str): raise ValueError(f"Invalid step {k}")
        return Step(**kwargs, span=span(s["span"]) if s.get("span") else None,
                    children=[step(c, depth+1) for c in s.get("children", [])])
    declarations = []
    for d in data.get("declarations", []):
        known = {f.name for f in fields(Declaration)} - {"span", "steps"}
        kw = {k:v for k,v in d.items() if k in known}
        for k in ("id", "name", "kind", "file", "statement", "source"):
            if not isinstance(kw.get(k), str): raise ValueError(f"Invalid declaration {k}")
        declarations.append(Declaration(**kw, span=span(d["span"]), steps=[step(s) for s in d.get("steps", [])]))
    known = {f.name for f in fields(Document)} - {"declarations"}
    return Document(**{k:v for k,v in data.items() if k in known}, declarations=declarations)


def embedded_json(data: Any) -> str:
    # Do not permit HTML's script terminator or JS line separators inside the data island.
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def html_document(document: Document, coverage: dict | None = None, links: dict | None = None) -> str:
    """Citation links, when given, are a separate data island outside the checked reading."""
    template = (ASSETS / "index.html").read_text(encoding="utf-8")
    if links is not None:
        from .declaration_index import validate_links
        validate_links(links)
    values = {
        "__PRODUCT_NAME__": html.escape(PRODUCT_NAME),
        "__TAGLINE__": html.escape(TAGLINE),
        "__VERSION__": html.escape(__version__),
        "__TITLE__": html.escape(document.title),
        "/*__STYLE__*/": (ASSETS / "style.css").read_text(encoding="utf-8"),
        "/*__APP__*/": (ASSETS / "app.js").read_text(encoding="utf-8"),
        "__DOCUMENT_DATA__": embedded_json({"document": document.to_dict(), "coverage": coverage if coverage is not None else report(document)}),
        "<!--__LINKS__-->": "" if links is None else '<script id="proofreader-links" type="application/json">'+embedded_json(links)+"</script>",
    }
    # One pass over the trusted template: untrusted marker-looking text is not reprocessed.
    return re.sub("|".join(re.escape(k) for k in values), lambda m: values[m.group(0)], template)


def write_html(document: Document, destination: Path | str, coverage: dict | None = None, links: dict | None = None) -> Path:
    p = Path(destination); p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html_document(document, coverage, links), encoding="utf-8")
    return p


def markdown_document(document: Document) -> str:
    out = [f"# {document.title}", "", "Evidence-labelled reading view. Source outlines are not checked English proofs.", ""]
    for d in document.declarations:
        out += [f"## {d.name}", "", f"Evidence: `{d.evidence}`. English fidelity: **not certified**.", "", "### Statement", "", "```lean", d.statement, "```", ""]
        if d.parameters:
            out += ["Parameters: " + "; ".join(p.get("text") or f"`{p['names']} : {p['type']}`" for p in d.parameters), ""]
        for warning in d.warnings: out += [f"> {warning}", ""]
        def add(steps, depth=0):
            for s in steps:
                line = f" (source lines {s.span.line}–{s.span.end_line})" if s.span else ""
                out.append("  "*depth + "- " + ("[UNEXPANDED] " if s.fallback else "") + s.text + line)
                if s.conclusion and s.conclusion not in s.text:
                    out.append("  "*(depth+1) + s.conclusion)
                add(s.children, depth+1)
        add(d.steps)
        out += ["", "<details><summary>Exact supplied source</summary>", "", "````lean", d.source, "````", "", "</details>", ""]
    return "\n".join(out)
