"""Build binding and real offline browser behavior for the curated companion.

These tests inspect the shipped evidence and UI; they do not execute Lean or
formally certify the English proof. The native reproduction has its own gate.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil

import pytest

HERE = Path(__file__).resolve().parents[2] / "docs/companion"
spec = importlib.util.spec_from_file_location("companion_builder", HERE / "build.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
EVIDENCE = Path(os.environ.get("LEANDIGEST_COMPANION_EVIDENCE_ROOT", builder.EVIDENCE))


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    path = tmp_path_factory.mktemp("bezout-companion") / "index.html"
    manifest = builder.build(path, EVIDENCE)
    return path, manifest


def test_build_reproduces_and_binds_fresh_native_evidence(built, tmp_path):
    path, manifest = built
    second = tmp_path / "index.html"
    assert builder.build(second, EVIDENCE) == manifest
    assert second.read_bytes() == path.read_bytes()
    assert path.read_bytes() == (HERE / "index.html").read_bytes(), "Regenerate the committed companion after changing its inputs"
    assert manifest == json.loads((HERE / "build-manifest.json").read_text())
    assert sha256(path.read_bytes()).hexdigest() == manifest["index_sha256"]
    assert manifest["snapshot_sha256"] == builder.SNAPSHOT_SHA256
    assert manifest["recorded_frames"] == 86
    assert manifest["curated_prose_formally_verified"] is False
    assert manifest["lean_executed_by_build"] is False
    assert manifest["network_requests_by_build"] is False
    embedded = json.loads(re.search(r'<script id="companion-data" type="application/json">(.*?)</script>', path.read_text(), re.S)[1])
    assert embedded["receipt"]["backend"] == "native"
    assert embedded["receipt"]["snapshot_sha256"] == manifest["snapshot_sha256"]
    assert embedded["native_record"]["checks"]["repeat_snapshot_exact"] == "passed"
    assert embedded["native_record"]["historical_comparison"]["snapshot_exact"] == "failed"
    assert embedded["receipt"]["exact_openai_project_replayed"] is False
    assert sorted(frame for section in embedded["sections"] for frame in section["frames"]) == list(range(86))


def test_builder_rejects_changed_original_source(monkeypatch, tmp_path):
    changed = tmp_path / "changed.lean"
    changed.write_bytes(builder.SOURCE.read_bytes() + b"\n-- changed\n")
    monkeypatch.setattr(builder, "SOURCE", changed)
    with pytest.raises(ValueError, match="Original source changed"):
        builder.build(tmp_path / "index.html", EVIDENCE)


@pytest.mark.parametrize("mutation", ["receipt", "context", "reading", "failed_control", "truthy_flag", "wrong_version", "wrong_mathlib"])
def test_builder_rejects_mismatched_or_failed_evidence(tmp_path, mutation):
    evidence = tmp_path / "evidence"
    shutil.copytree(EVIDENCE / "current", evidence / "current")
    shutil.copyfile(EVIDENCE / "observation.json", evidence / "observation.json")
    if mutation == "receipt":
        path = evidence / "current/receipt.json"
        value = json.loads(path.read_text())
        value["snapshot_sha256"] = "0" * 64
        path.write_text(json.dumps(value))
    elif mutation == "context":
        path = evidence / "current/Context.lean"
        path.write_text(path.read_text() + "\n-- changed\n")
    elif mutation == "reading":
        path = evidence / "current/reading.json"
        value = json.loads(path.read_text())
        value["title"] = "Changed reading"
        path.write_text(json.dumps(value))
    elif mutation == "truthy_flag":
        path = evidence / "current/receipt.json"
        value = json.loads(path.read_text())
        value["all_selected_judgements_kernel_checked"] = "true"
        path.write_text(json.dumps(value))
    else:
        path = evidence / "observation.json"
        value = json.loads(path.read_text())
        if mutation == "wrong_version":
            value["lean_version"] = "4.34.0"
        elif mutation == "wrong_mathlib":
            value["mathlib_commit"] = "0" * 40
        else:
            value["checks"]["wrong_claim_rejected"] = "failed"
        path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        builder.build(tmp_path / "index.html", evidence)


@pytest.fixture(scope="module")
def browser():
    pw = pytest.importorskip("playwright.sync_api")
    executable = shutil.which("chromium") or shutil.which("google-chrome")
    with pw.sync_playwright() as p:
        try:
            browser = p.chromium.launch(executable_path=executable, headless=True, args=["--no-sandbox"]) if executable else p.chromium.launch(headless=True)
        except Exception as exc:
            if os.environ.get("PROOFREADER_REQUIRE_BROWSER") == "1":
                pytest.fail(f"Browser CI requires Chromium: {exc}")
            pytest.skip(f"Browser unavailable: {exc}")
        yield browser
        browser.close()


@pytest.fixture
def page(browser, built):
    page = browser.new_page(viewport={"width": 1440, "height": 960})
    errors, network = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: network.append(request.url) if request.url.startswith(("http:", "https:")) else None)
    page.goto(built[0].as_uri())
    assert page.locator("html").get_attribute("data-companion-ready") == "true"
    yield page
    assert not errors, errors
    assert not network, "The companion must work without remote service/CDN requests"
    page.close()


def test_math_statement_and_complete_six_step_argument(page):
    assert page.locator(".proof-step").count() == 6
    assert page.locator("[data-math]").count() == page.locator("math").count()
    assert page.locator(".target-equations [data-math]").evaluate_all("nodes => nodes.map(n => n.dataset.math)") == ["ab=x", "dc=y", "db=z", "ac-db=1"]
    theorem = page.locator("#theorem").inner_text()
    assert "Euclidean domain" in theorem
    assert "No assumption says" in theorem and "nonzero" in theorem
    assert page.locator('#step-1 [data-math="(a,d,b,c)=(1,y,0,1)."] math').count() == 1
    assert "surrounding explanation is not certified" in page.locator(".proof-intro").inner_text()
    assert "Fourteen passages" in page.locator(".proof-intro").inner_text()
    assert "two explicitly substituted imports" in page.locator(".evidence-grid").inner_text()
    assert "full OAI" in page.locator(".scope-note").inner_text()


@pytest.mark.parametrize("section", builder.SECTIONS, ids=lambda value: value["id"])
def test_every_source_button_selects_exact_lines_claim_and_context(page, section):
    button = page.locator(f'[data-section="{section["id"]}"]').first
    button.click()
    assert page.locator("#evidence-dialog").is_visible()
    assert page.locator("#evidence-dialog-title").inner_text() == section["title"]
    lines = page.locator("#dialog-source .highlighted").evaluate_all("nodes => nodes.map(n => Number(n.dataset.line))")
    assert lines == list(range(section["lines"][0], section["lines"][1] + 1))
    source_lines = page.locator("#dialog-source .source-code").all_text_contents()
    assert "\n".join(source_lines) == builder.SOURCE.read_text()
    page.locator("#evidence-tab-frames").click()
    assert page.locator("#frame-select").input_value() == str(section["focus"])
    page.locator("#evidence-panel-frames > details > summary").click()
    frame = json.loads(page.locator("#frame-raw").inner_text())
    assert frame["id"] == section["focus"]
    assert page.locator("#frame-statement").inner_text() == frame["statement"]
    context = "\n".join(f'{item["name"]} : {item["type"]}' for item in frame["context"]) or "(empty local context)"
    assert page.locator("#frame-context").inner_text() == context
    snapshot = builder.Snapshot.read(EVIDENCE / "current/snapshot.json")
    assert frame == snapshot.frames[section["focus"]]
    assert [int(value) for value in page.locator("#frame-select option").evaluate_all("nodes => nodes.map(n => n.value)")] == section["frames"]
    page.keyboard.press("Escape")
    assert page.locator("#evidence-dialog").is_hidden()
    assert button.evaluate("node => document.activeElement === node")


def test_evidence_tabs_keyboard_and_fresh_run_record(page):
    page.locator('#step-2 [data-section="step-2"]').click()
    assert page.locator("#evidence-tab-source").evaluate("node => document.activeElement === node")
    page.keyboard.press("ArrowRight")
    assert page.locator("#evidence-tab-frames").get_attribute("aria-selected") == "true"
    page.locator("#frame-select").select_option("38")
    assert page.locator("#frame-domain-section").is_visible()
    assert "s : R" in page.locator("#frame-domain").inner_text()
    page.locator("#evidence-tab-frames").focus()
    page.keyboard.press("End")
    assert page.locator("#evidence-tab-receipt").get_attribute("aria-selected") == "true"
    record = json.loads(page.locator("#dialog-receipt").inner_text())
    assert record["receipt"]["snapshot_sha256"] == builder.SNAPSHOT_SHA256
    assert record["observation"]["checks"]["wrong_path_rejected"] == "passed"
    assert record["observation"]["checks"]["wrong_claim_rejected"] == "passed"
    page.keyboard.press("Home")
    assert page.locator("#evidence-tab-source").get_attribute("aria-selected") == "true"


@pytest.mark.parametrize("case,witnesses", [("ordinary", "3,2,4,3"), ("zero", "1,7,0,1"), ("negative", "-3,1,2,-1")])
def test_exact_integer_examples_exercise_both_branches_and_signs(page, case, witnesses):
    page.locator(f'[data-example="{case}"]').click()
    assert page.locator("#example-output").get_attribute("data-case") == case
    assert page.locator("#example-output").get_attribute("data-witnesses") == witnesses
    assert page.locator("#example-output").get_attribute("data-hypothesis-checked") == "true"
    assert page.locator('.example-check[data-checked="true"]').count() == 4
    assert page.locator('.example-options [aria-pressed="true"]').count() == 1
    if case == "zero":
        assert "no cancellation by zero" in page.locator(".example-note").inner_text()


def test_downloaded_reader_has_fresh_snapshot_and_original_source_is_exact(page, tmp_path):
    page.locator(".provenance-details summary").click()
    with page.expect_download() as download_info:
        page.locator('[data-download="source"]').click()
    original = tmp_path / download_info.value.suggested_filename
    download_info.value.save_as(original)
    assert original.read_bytes() == builder.SOURCE.read_bytes()
    with page.expect_download() as download_info:
        page.locator('[data-download="reader"]').click()
    reader = tmp_path / download_info.value.suggested_filename
    download_info.value.save_as(reader)
    page.goto(reader.as_uri())
    assert page.locator("#qualified-name").inner_text() == builder.THEOREM
    assert builder.SNAPSHOT_SHA256 in reader.read_text()
    assert "dad8ef23a231904f37b73979f8284ea3662ffe8f8cd30c79066856f2095b4dd7" not in reader.read_text()


def test_mobile_does_not_overflow_and_can_inspect_final_claim(page):
    page.set_viewport_size({"width": 390, "height": 844})
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")
    page.locator('#step-6 [data-section="step-6"]').click()
    assert page.locator("#evidence-dialog").is_visible()
    page.locator("#evidence-tab-frames").click()
    assert "= 1" in page.locator("#frame-statement").inner_text()
    assert page.locator("#frame-select").input_value() == "79"
    assert page.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth")


def test_heading_labels_match_the_editorial_inventory(page):
    headings = builder.load_headings()
    assert page.locator("h1").inner_text() == headings["page"]
    assert page.locator("#proof-title").inner_text() == headings["proof"]
    assert page.locator("#evidence-title").inner_text() == headings["evidence"]
    for number in range(1, 7):
        section = f"step-{number}"
        assert page.locator(f"#title-{section}").inner_text() == headings[section]
        assert page.locator(f'.contents a[href="#{section}"]').inner_text() == headings[section]
        page.locator(f'#{section} [data-section="{section}"]').click()
        assert page.locator("#evidence-dialog-title").inner_text() == headings[section]
        page.keyboard.press("Escape")


def test_source_checked_sentence_text_matches_the_native_utf8_in_the_browser(page):
    from proofreader.source_text import load_cancellations
    records = load_cancellations()['sentences']
    panels = page.locator('.checked-cancellation')
    assert panels.count() == 2
    for index, frame in enumerate([40, 53]):
        panel = page.locator(f'.checked-cancellation[data-source-frame="{frame}"]')
        panel.locator('summary').click()
        paragraph = panel.locator('.checked-sentence')
        assert paragraph.is_visible()
        text = paragraph.text_content()
        assert text == records[index]['text']
        assert text.encode('utf-8') == bytes(records[index]['utf8'])
    assert 'surrounding explanation is not certified' in page.locator('.proof-intro').inner_text()
    assert 'Fourteen passages' in page.locator('.proof-intro').inner_text()


def test_equation_and_witness_text_and_exact_frame_selection(page):
    from proofreader.equation_text import FRAMES, load_equations
    records = load_equations()
    panels = page.locator('.checked-equations')
    assert panels.count() == 6
    for panel in panels.all():
        panel.locator('summary').click()
    assert page.locator('.checked-calculation').count() == 12
    for kind, frames in FRAMES.items():
        for frame, record in zip(frames, records[kind]):
            row = page.locator(f'.checked-calculation[data-kind="{kind}"][data-source-frame="{frame}"]')
            assert row.locator('.checked-equation-text').text_content() == record['text']
            assert row.locator('.checked-equation-text').text_content().encode('utf-8') == bytes(record['utf8'])
            row.locator('button').click()
            assert page.locator('#evidence-tab-frames').get_attribute('aria-selected') == 'true'
            assert page.locator('#frame-select').input_value() == str(frame)
            assert 'hg' in page.locator('#frame-context').inner_text()
            assert page.locator('#frame-checked-text').text_content() == record['text']
            expected_context = '\n'.join(f"[{c['binder_index']}] {c['name']} : {c['type']}" +
                ('' if c['value'] is None else ' := '+c['value']) for c in record['context'])
            assert page.locator('#frame-checked-context').text_content() == expected_context
            assert json.loads(page.locator('#frame-checked-record').text_content()) == record
            page.keyboard.press('Escape')
    assert 'surrounding explanation is not certified' in page.locator('.proof-intro').inner_text()


def test_expanded_calculations_fit_the_mobile_view(page):
    page.set_viewport_size({'width':390,'height':844})
    for panel in page.locator('.checked-equations').all():
        panel.locator('summary').click()
    assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')
    last = page.locator('.checked-calculation[data-source-frame="79"]')
    last.locator('button').click()
    assert page.locator('#frame-select').input_value() == '79'
    assert page.locator('#evidence-dialog').is_visible()
    assert page.evaluate('document.documentElement.scrollWidth <= document.documentElement.clientWidth')


def test_checked_text_download_retains_source_context_and_full_proof_limit(page, tmp_path):
    page.locator('.provenance-details summary').click()
    with page.expect_download() as pending:
        page.locator('[data-download="checked-text"]').click()
    output = tmp_path/pending.value.suggested_filename
    pending.value.save_as(output)
    data = json.loads(output.read_text())
    assert len(data['cancellations']['sentences']) == 2
    assert len(data['calculations']['equations']) == 10
    assert len(data['calculations']['witnesses']) == 2
    assert data['calculations']['observation']['complete_english_proof_certified'] is False
    assert all(row['context'] for kind in ['equations','witnesses'] for row in data['calculations'][kind])
