"""Companion heading conventions and preservation checks for the style revision.

These tests are not a style-quality score, an AI-text detector, or a mathematical
verification method. The proof-content hashes below pin the reviewed PR6 text.
"""
from __future__ import annotations

from hashlib import sha256
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "docs/companion"
SPEC = importlib.util.spec_from_file_location("editorial_companion_builder", HERE / "build.py")
assert SPEC is not None and SPEC.loader is not None
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)


class HeadingInventory(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.headings = []
        self.links = []
        self.tags = []
        self.active = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append(tag)
        if tag in {"h1", "h2", "h3", "title"} or (tag == "a" and attrs.get("href", "").startswith("#")):
            self.active.append((tag, attrs, []))

    def handle_data(self, data):
        for _, _, parts in self.active:
            parts.append(data)

    def handle_endtag(self, tag):
        if self.active and self.active[-1][0] == tag:
            item_tag, attrs, parts = self.active.pop()
            item = (item_tag, attrs, " ".join("".join(parts).split()))
            (self.links if tag == "a" else self.headings).append(item)


def parse(text):
    inventory = HeadingInventory()
    inventory.feed(text)
    inventory.close()
    return inventory


def digest(data):
    return sha256(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    path = tmp_path_factory.mktemp("editorial-companion") / "index.html"
    BUILDER.build(path)
    return path.read_text()


def test_standard_section_names():
    headings = BUILDER.load_headings()
    assert headings["page"] == "Bézout frame theorem"
    assert headings["statement"] == "Statement"
    assert headings["definitions"] == "Definitions and lemmas"
    assert headings["proof"] == "Proof"
    assert headings["example"] == "Integer examples"
    assert headings["evidence"] == "Verification"
    assert all(not title.endswith(".") for title in headings.values())


def test_page_contents_and_inspector_use_the_same_titles(built):
    headings = BUILDER.load_headings()
    doc = parse(built)
    assert [text for tag, _, text in doc.headings if tag == "h1"] == [headings["page"]]
    assert [text for tag, _, text in doc.headings if tag == "title"] == [headings["page"] + " | Leanglish"]
    by_id = {attrs["id"]: text for _, attrs, text in doc.headings if "id" in attrs}
    ids = {"statement": "theorem-title", "definitions": "definitions-title", "proof": "proof-title",
           "example": "example-title", "why": "why-title", "evidence": "evidence-title"}
    ids.update({f"step-{i}": f"title-step-{i}" for i in range(1, 7)})
    for key, identity in ids.items():
        assert by_id[identity] == headings[key]
    data = json.loads(re.search(r'<script id="companion-data" type="application/json">(.*?)</script>', built, re.S)[1])
    for section in data["sections"]:
        assert section["title"] == headings[section["id"]]
        if section["id"].startswith("step-"):
            links = [text for _, attrs, text in doc.links if attrs["href"] == "#" + section["id"]]
            assert links == [section["title"]]
    assert all(text for _, _, text in doc.headings), "Do not ship empty headings"
    assert "__HEADING_" not in built


def test_removed_caption_patterns_do_not_return(built):
    # Only authored headings/labels are in scope, not quoted examples in the
    # style guide, mathematical vocabulary, source code, or archived releases.
    headings = "\n".join(text for _, _, text in parse(built).headings)
    for phrase in ("with the algebra visible", "with its record attached", "A COMPLETE ARGUMENT", "WHY THIS FITS"):
        assert phrase.casefold() not in headings.casefold()
    assert 'class="step-kind"' not in built
    assert 'class="definition-hint"' not in built


def test_formula_inventory_is_unchanged(built):
    # From PR6 head 5c2070494814f109038f3d589807443725b1f4f6. The generated page
    # embeds scripts and a downloadable reader, so compare the authored template.
    text = (HERE / "template.html").read_text()
    formulas = re.findall(r'data-math="([^"]*)"', text)
    assert len(formulas) == 63
    assert digest(formulas) == "6b13ae132455eaeed81a71467f0c392407e3dd74e693e0741575180a49cfa686"


def test_all_six_proof_bodies_are_unchanged():
    text = (HERE / "template.html").read_text()
    bodies = re.findall(r'<section class="proof-step".*?<div class="step-body">(.*?)</div></section>', text, re.S)
    # Only source-button wording changed within these blocks.
    bodies = [re.sub(r'<button\b[^>]*>.*?</button>', '', body, flags=re.S) for body in bodies]
    assert len(bodies) == 6
    assert digest(bodies) == "f032dad160f38eb099dd0be3c2ffd0fbe50bb3954619b709eaed594832ef30d8"


def test_new_headings_do_not_change_source_correspondence():
    expected = [
        ("statement", [11, 13], list(range(6)), 0),
        ("step-1", [15, 18], list(range(6, 24)), 17),
        ("step-2", [19, 29], list(range(24, 52)) + [84, 85], 40),
        ("step-3", [30, 34], list(range(52, 63)), 53),
        ("step-4", [35, 36], list(range(63, 70)), 67),
        ("step-5", [37, 41], list(range(70, 79)), 70),
        ("step-6", [42, 44], list(range(79, 84)), 79),
    ]
    assert [(s["id"], s["lines"], s["frames"], s["focus"]) for s in BUILDER.SECTIONS] == expected


@pytest.mark.parametrize("mutation", ["missing", "extra", "array", "duplicate"])
def test_invalid_heading_inventory_is_rejected(tmp_path, mutation):
    data = BUILDER.load_headings()
    path = tmp_path / "headings.json"
    if mutation == "missing":
        data.pop("proof")
    elif mutation == "extra":
        data["unexpected"] = "Unexpected"
    elif mutation == "array":
        data = list(data.values())
    elif mutation == "duplicate":
        path.write_text(json.dumps(data)[:-1] + ',"proof":"Other title"}')
        with pytest.raises(ValueError, match="Duplicate companion heading"):
            BUILDER.load_headings(path)
        return
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="exactly the named page sections"):
        BUILDER.load_headings(path)


@pytest.mark.parametrize("bad", ["", " Proof", "Proof ", "Proof\n", "Pro\tof", "Pro\x00of", "Pro\u200bof", 7, None, ["Proof"]])
def test_empty_nontext_or_invisible_headings_are_rejected(tmp_path, bad):
    data = BUILDER.load_headings()
    data["proof"] = bad
    path = tmp_path / "headings.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="single-line text"):
        BUILDER.load_headings(path)


def test_heading_text_is_escaped_not_interpreted_as_html(monkeypatch, tmp_path):
    headings = BUILDER.load_headings()
    headings["page"] = '<img src=x onerror="alert(1)"> & Bézout'
    monkeypatch.setattr(BUILDER, "load_headings", lambda: headings)
    output = tmp_path / "index.html"
    BUILDER.build(output)
    parsed = parse(output.read_text())
    assert "img" not in parsed.tags
    assert [text for tag, _, text in parsed.headings if tag == "h1"] == [headings["page"]]


def test_agent_handoffs_include_the_editorial_policy():
    tasks = json.loads((ROOT / "agents/tasks.json").read_text())["tasks"]
    assert tasks
    assert all(task["context"].count("docs/STYLE.md") == 1 for task in tasks)
    assert "docs/STYLE.md" in (ROOT / "AGENTS.md").read_text()


def test_technical_vocabulary_is_not_a_banned_word_list(tmp_path):
    headings = BUILDER.load_headings()
    headings["page"] = "Exact sequences and complete lattices"
    path = tmp_path / "headings.json"
    path.write_text(json.dumps(headings))
    assert BUILDER.load_headings(path)["page"] == headings["page"]
