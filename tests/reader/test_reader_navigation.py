"""Offline Chromium navigation checks; synthetic fixtures are not Lean evidence.

The retained-data check at the end uses the shipped reader records. These tests
exercise navigation and the source/context display, never Lean execution or the
truth or completeness of an English explanation.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
from urllib.parse import parse_qs, quote, urlencode, urlsplit

import pytest

from proofreader.model import Declaration, Document, Span, Step, walk_steps
from proofreader.render import html_document, load_document

pw = pytest.importorskip("playwright.sync_api")

ROOT = Path(__file__).resolve().parents[2]
FIRST = "first proof: α /?&"
SECOND = "second proof: β /?&"
SHARED_STEP = "shared step: δ /?&"
NESTED_STEP = "first only: nested /?&"


@pytest.fixture(scope="module")
def browser():
    executable = shutil.which("chromium") or shutil.which("google-chrome")
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                executable_path=executable, headless=True, args=["--no-sandbox"]
            ) if executable else p.chromium.launch(headless=True)
        except Exception as exc:
            if os.environ.get("PROOFREADER_REQUIRE_BROWSER") == "1":
                pytest.fail(f"Browser CI requires Chromium: {exc}")
            pytest.skip(f"Browser unavailable: {exc}")
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    errors = []
    network = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: network.append(request.url)
            if request.url.startswith(("http:", "https:")) else None)
    yield page
    assert not errors, errors
    assert not network, "The offline reader must make no service/CDN requests."
    page.close()


@pytest.fixture
def reading():
    """Hand-authored reading IR with reused IDs in different proof scopes."""
    first_gap = Step(
        id=SHARED_STEP, rule="unexpanded", text="First scope needs an explanation.",
        source="first_exact_source", conclusion="FirstClaim", evidence="typed-export",
        context=[{"name": "h_first", "type": "FirstScope"}], fallback=True,
    )
    nested_gap = Step(
        id=NESTED_STEP, rule="application", text="A second unexplained inference.",
        conclusion="RecordedClaimOnly", evidence="typed-export", fallback=True,
    )
    first = Declaration(
        id=FIRST, name="Review.first", kind="theorem", file="fixture.lean",
        statement="FirstClaim", source="theorem first : FirstClaim := first_proof",
        span=Span(0, 1, 1, 1), evidence="typed-export",
        steps=[Step(id="branch", rule="case", text="Work in the first scope.",
                    children=[first_gap, Step(id="inner", rule="claim", text="An inner claim.",
                                              children=[nested_gap])])],
    )
    second = Declaration(
        id=SECOND, name="Review.second", kind="theorem", file="fixture.lean",
        statement="SecondClaim", source="theorem second : SecondClaim := second_proof",
        span=Span(1, 2, 2, 2), evidence="source",
        steps=[Step(id=SHARED_STEP, rule="unexpanded", text="Second scope needs an explanation.",
                    source="second_exact_source", conclusion="SecondClaim",
                    context=[{"name": "h_second", "type": "SecondScope"}], fallback=True)],
    )
    plain = Declaration(
        id="plain", name="Review.plain", kind="theorem", file="fixture.lean",
        statement="True", source="theorem plain : True := by trivial",
        span=Span(2, 3, 3, 3), evidence="typed-export",
        steps=[Step(id="plain-step", rule="given", text="Use the recorded assumption.")],
    )
    return Document(title="Synthetic navigation fixture", files=[{"path": "fixture.lean"}],
                    declarations=[first, second, plain],
                    provenance={"fixture": True, "lean_execution": "not performed"})


def open_file(page, tmp_path, reading, *, params=None, fragment=""):
    path = tmp_path / "reader.html"
    path.write_text(html_document(reading), encoding="utf-8")
    url = path.as_uri() + ("?" + urlencode(params) if params else "")
    page.goto(url + fragment)
    return path


def query(page):
    return {key: values[0] for key, values in parse_qs(urlsplit(page.url).query).items()}


def test_gap_queue_opens_ancestors_crosses_proofs_and_has_bounds(page, tmp_path, reading):
    open_file(page, tmp_path, reading)
    assert page.locator("#gap-position").inner_text() == "3 explanation gaps"
    assert page.locator("#gap-prev").is_disabled()
    page.locator("#gap-next").click()
    assert page.locator("#gap-position").inner_text() == "Gap 1 of 3"
    assert page.locator("#proof-steps details[open]").count() == 1
    assert page.locator("#inspector-source").inner_text() == "first_exact_source"
    assert "h_first : FirstScope" in page.locator("#inspector-context").inner_text()
    assert "step 1.1" in page.locator("#inspector-location").inner_text()
    assert page.locator("#gap-prev").is_disabled()

    page.locator("#gap-next").click()
    assert page.locator("#gap-position").inner_text() == "Gap 2 of 3"
    assert page.locator("#proof-steps details[open]").count() == 2
    assert page.locator(".selected-step").get_attribute("data-step-id") == NESTED_STEP
    assert "step 1.2.1" in page.locator("#inspector-location").inner_text()
    page.locator("#gap-next").click()
    assert page.locator("#qualified-name").inner_text() == "Review.second"
    assert page.locator("#inspector-source").inner_text() == "second_exact_source"
    assert "h_second : SecondScope" in page.locator("#inspector-context").inner_text()
    assert "h_first" not in page.locator("#inspector-context").inner_text()
    assert page.locator("#gap-position").inner_text() == "Gap 3 of 3"
    assert page.locator("#gap-next").is_disabled()
    page.locator("#gap-prev").click()
    assert page.locator("#qualified-name").inner_text() == "Review.first"
    assert page.locator(".selected-step").get_attribute("data-step-id") == NESTED_STEP


def test_gap_queue_respects_search_filters_and_empty_results(page, tmp_path, reading):
    open_file(page, tmp_path, reading)
    page.locator('[data-filter="typed"]').click()
    assert page.locator("#gap-position").inner_text() == "2 explanation gaps"
    page.locator("#gap-next").click()
    page.locator("#gap-next").click()
    assert page.locator("#gap-next").is_disabled()
    assert page.locator("#qualified-name").inner_text() == "Review.first"
    page.locator("#search").fill("Review.second")
    assert page.locator("#empty").is_visible()
    assert page.locator("#inspector").is_hidden()
    assert "declaration" not in query(page) and "step" not in query(page)
    page.locator('[data-filter="all"]').click()
    assert page.locator("#qualified-name").inner_text() == "Review.second"
    assert page.locator("#declaration-list [aria-current=true]").count() == 1
    assert page.locator("#gap-position").inner_text() == "1 explanation gap"
    page.locator("#gap-next").click()
    assert page.locator("#gap-position").inner_text() == "Gap 1 of 1"
    assert page.locator("#gap-prev").is_disabled()
    assert page.locator("#gap-next").is_disabled()


def test_step_link_and_reload_retain_declaration_step_tab_and_filter(page, tmp_path, reading):
    open_file(page, tmp_path, reading, params={"session": "offline"})
    page.locator('[data-filter="typed"]').click()
    page.locator("#search").fill("Review.first")
    page.locator("#gap-next").click()
    page.locator("#inspector-show-source").click()
    expected = {"session": "offline", "declaration": FIRST, "step": SHARED_STEP,
                "filter": "typed", "q": "Review.first", "tab": "source"}
    assert query(page) == expected
    assert page.locator("#inspector-link").get_attribute("href") == page.url
    page.reload()
    assert query(page) == expected
    assert page.locator("#qualified-name").inner_text() == "Review.first"
    assert page.locator("#tab-source").get_attribute("aria-selected") == "true"
    assert page.locator("#exact-source").is_visible()
    assert page.locator("#inspector-source").inner_text() == "first_exact_source"
    assert "h_first : FirstScope" in page.locator("#inspector-context").inner_text()
    assert page.locator("#gap-position").inner_text() == "Gap 1 of 2"


def test_back_forward_restore_actual_step_scope_and_tab(page, tmp_path, reading):
    open_file(page, tmp_path, reading, params={"declaration": FIRST, "step": NESTED_STEP})
    page.locator("#gap-next").click()
    page.locator("#tab-source").click()
    page.go_back()
    pw.expect(page.locator("#tab-reading")).to_have_attribute("aria-selected", "true")
    assert page.locator("#inspector-source").inner_text() == "second_exact_source"
    page.go_back()
    pw.expect(page.locator("#qualified-name")).to_have_text("Review.first")
    assert page.locator(".selected-step").get_attribute("data-step-id") == NESTED_STEP
    page.go_forward()
    pw.expect(page.locator("#qualified-name")).to_have_text("Review.second")
    assert page.locator(".selected-step").get_attribute("data-step-id") == SHARED_STEP
    assert "h_second" in page.locator("#inspector-context").inner_text()


def test_legacy_fragment_and_missing_step_fail_without_selecting_other_proof(page, tmp_path, reading):
    path = open_file(page, tmp_path, reading, fragment="#" + quote(SECOND, safe=""))
    assert page.locator("#qualified-name").inner_text() == "Review.second"
    assert query(page)["declaration"] == SECOND
    assert not urlsplit(page.url).fragment
    page.goto(path.as_uri() + "?" + urlencode({"declaration": SECOND, "step": NESTED_STEP}))
    assert page.locator("#qualified-name").inner_text() == "Review.second"
    assert page.locator("#inspector").is_hidden()
    assert "step" not in query(page)
    assert "not present in this proof" in page.locator("#toast").inner_text()
    page.goto(path.as_uri() + "#%E0%A4")
    assert page.locator("#qualified-name").inner_text() == "Review.first"
    assert "malformed" in page.locator("#toast").inner_text()


def test_keyboard_tabs_inspection_and_focus_return(page, tmp_path, reading):
    open_file(page, tmp_path, reading)
    page.locator("#tab-reading").focus()
    page.keyboard.press("ArrowRight")
    pw.expect(page.locator("#tab-source")).to_be_focused()
    assert page.locator("#tab-source").get_attribute("aria-controls") == "panel-source"
    assert page.locator("#tab-reading").get_attribute("tabindex") == "-1"
    page.keyboard.press("End")
    pw.expect(page.locator("#tab-audit")).to_be_focused()
    page.keyboard.press("Home")
    pw.expect(page.locator("#tab-reading")).to_be_focused()
    page.locator("#gap-next").focus()
    page.keyboard.press("Enter")
    pw.expect(page.locator("#inspector-title")).to_be_focused()
    page.keyboard.press("Escape")
    assert page.locator("#inspector").is_hidden()
    pw.expect(page.locator(".selected-step > .step-header > .step-inspect")).to_be_focused()
    assert page.locator("#gap-position").inner_text() == "Gap 1 of 3"


def test_recorded_claim_is_not_presented_as_exact_source(page, tmp_path, reading):
    open_file(page, tmp_path, reading, params={"declaration": FIRST, "step": NESTED_STEP})
    assert page.locator("#inspector-source").inner_text() == "No exact source text is attached to this step."
    assert page.locator("#inspector-conclusion").inner_text() == "RecordedClaimOnly"
    assert "No local context entries are attached" in page.locator("#inspector-context").inner_text()
    assert page.locator("#inspector-gap").is_visible()
    assert "not counted as explained" in page.locator("#inspector-gap").inner_text()


def test_imported_reading_does_not_advertise_a_link_to_different_embedded_data(page, tmp_path, reading):
    open_file(page, tmp_path, reading)
    embedded_url = page.url
    imported = copy.deepcopy(reading.to_dict())
    imported["title"] = "Different imported reading"
    imported["declarations"][0]["id"] = "imported-proof"
    page.locator("#import-file").set_input_files({"name": "different.json", "mimeType": "application/json",
                                                "buffer": json.dumps(imported).encode()})
    pw.expect(page.locator("#library-title")).to_have_text(imported["title"])
    page.locator("#gap-next").click()
    assert page.locator("#inspector-link").is_hidden()
    assert page.locator("#inspector-link-note").is_visible()
    assert page.url == embedded_url
    page.reload()
    assert page.locator("#library-title").inner_text() == reading.title
    page.locator("#gap-next").click()
    assert page.locator("#inspector-link").is_visible()
    assert page.locator("#inspector-link-note").is_hidden()


@pytest.mark.parametrize("duplicate", ["declaration", "step"])
def test_ambiguous_ids_rejected_without_replacing_open_document(page, tmp_path, reading, duplicate):
    open_file(page, tmp_path, reading)
    bad = copy.deepcopy(reading.to_dict())
    if duplicate == "declaration":
        bad["declarations"][1]["id"] = FIRST
    else:
        bad["declarations"][0]["steps"].append(copy.deepcopy(bad["declarations"][0]["steps"][0]))
    page.locator("#import-file").set_input_files({"name": "ambiguous.json", "mimeType": "application/json",
                                                "buffer": json.dumps(bad).encode()})
    pw.expect(page.locator("#toast")).to_contain_text("duplicate")
    assert page.locator("#library-title").inner_text() == reading.title
    assert page.locator("#gap-position").inner_text() == "3 explanation gaps"
    page.locator("#gap-next").click()
    assert page.locator("#inspector-source").inner_text() == "first_exact_source"


def test_no_flagged_gaps_does_not_claim_completeness_and_mobile_fits(page, tmp_path, reading):
    page.set_viewport_size({"width": 390, "height": 844})
    open_file(page, tmp_path, reading, params={"declaration": "plain", "q": "Review.plain"})
    assert page.locator("#gap-position").inner_text() == "No explicitly flagged gaps"
    assert "does not establish a complete proof explanation" in page.locator("#gap-scope").inner_text()
    assert page.locator("#gap-next").is_disabled() and page.locator("#gap-prev").is_disabled()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#search").fill("Review.first")
    page.locator("#gap-next").click()
    assert page.locator("#inspector").is_visible()
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    page.locator("#inspector-gap-next").click()
    assert page.locator("#inspector-gap-position").inner_text() == "Gap 2 of 2"
    assert page.locator("#inspector-gap-next").is_disabled()
    page.locator("#inspector-gap-prev").click()
    assert page.locator("#inspector-gap-position").inner_text() == "Gap 1 of 2"


def test_retained_reading_gap_navigation_matches_proof_and_original_source(page, tmp_path):
    """Retained records, not a fresh Lean run or an English-completeness result."""
    reading = load_document((ROOT / "proofreader/data/reader-demo.json").read_bytes())
    expected = [(d, s) for d in reading.declarations for s in walk_steps(d.steps) if s.fallback]
    assert expected, "The retained fixture should exercise actual unexpanded steps."
    open_file(page, tmp_path, reading)
    for index, (declaration, step) in enumerate(expected, 1):
        page.locator("#gap-next").click()
        assert page.locator("#qualified-name").inner_text() == declaration.name
        assert query(page)["step"] == step.id
        assert page.locator("#gap-position").inner_text() == f"Gap {index} of {len(expected)}"
        assert page.locator("#inspector-text").inner_text() == step.text
        if step.source:
            assert page.locator("#inspector-source").text_content() == step.source
    assert page.locator("#gap-next").is_disabled()
