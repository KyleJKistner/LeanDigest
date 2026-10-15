"""Public-facing research preview regressions and failure-accounting safeguards."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_research_preview import build, checked_relative, page, source_link

COMMIT = "4fd28f74a0bc1701b60e6a29804f0b533078fdeb"
RUN = "38792262410"


def test_source_url_frozen_and_safe():
    assert source_link("OAI.Algebra.AffineCancellation.BezoutFrame").endswith("/lean/OAI/Algebra/AffineCancellation/BezoutFrame.lean")
    assert COMMIT not in source_link("OAI.Algebra.AffineCancellation.BezoutFrame")
    for invalid in ("OAI...", "OAI.X/../../secret", "Other.Foo", "OAI.Foo<script>"):
        with pytest.raises(ValueError):
            source_link(invalid)


def test_artifact_path_traversal_and_symlink_fail_closed(tmp_path):
    p = tmp_path / "attempts/a/proofs/xyz/reader.html"
    p.parent.mkdir(parents=True)
    p.write_text("<!doctype html>")
    assert checked_relative(tmp_path, "attempts/a/proofs/xyz/reader.html") == p
    for bad in ("../../etc/passwd", "/etc/passwd", "attempts/a/proofs/xyz/missing.html", "..\\secret.html", "./"):
        with pytest.raises(ValueError):
            checked_relative(tmp_path, bad)
    link = p.parent / "symlink.html"
    link.symlink_to(p)
    with pytest.raises(ValueError):
        checked_relative(tmp_path, "attempts/a/proofs/xyz/symlink.html")


def example(tmp_path):
    raw = tmp_path / "source"
    proof = raw / "attempts/r/proofs/entry"
    proof.mkdir(parents=True)
    (proof / "reader.html").write_text("<!doctype html><title>Example</title>")
    (proof / "proof.txt").write_text("Leanglish · OAI.Test.Module.example\n\nLet x be a real number.\nThen x = x.\n\nProof.\n")
    snap = {"theorem": "OAI.Test.Module.example", "frames": [{"id": 0}]}
    (proof / "snapshot.json").write_text(json.dumps(snap))
    receipt = {"theorem": snap["theorem"], "status": "passed", "all_selected_judgements_kernel_checked": True,
               "path_linkage_checked_in_lean": True, "receipt_authenticated": False, "english_formally_verified": False}
    (proof / "receipt.json").write_text(json.dumps(receipt))
    module = "OAI.Test.Module"
    row = {"name": snap["theorem"], "kind":"theorem", "status": "rendered", "rendered":True,
           "kernel_checked":True, "path_checked":True, "unexpanded_steps": 0, "frames":1,
           "reader":"attempts/r/proofs/entry/reader.html"}
    summ = {"whole_openai_corpus_coverage":False,"certified_english_proofs":0,
            "rendered":1,"kernel_checked":1,"declarations_with_gaps":0,"unexpanded_steps":0,
            "total_candidates":1,"modules_complete":1,"modules_expected":1}
    batch={"schema":"leanglish.narrative-batch/v1", "summary":summ,
           "modules":[{"module":module,"status":"complete","expected":1,"errors":[],"rows":[row]}]}
    (raw / "batch.json").write_text(json.dumps(batch))
    return raw, batch, proof


def test_smoke_preview_build_is_offline(tmp_path):
    raw,_,_=example(tmp_path)
    out=tmp_path / "public"
    manifest=build(raw,out,commit=COMMIT,run_id=RUN)
    assert len(manifest["proofs"])==1
    assert manifest["summary"]["total_candidates"]==1
    assert (out / manifest["proofs"][0]["page"]).read_text() == '<!doctype html><title>Example</title>'
    html=(out / "index.html").read_text()
    assert 'Leanglish' in html and 'No recorded fallbacks' in html
    assert 'OpenAI mathematics release' in html
    assert manifest["formal_english_certification"] is False
    assert manifest["independent_human_readability_study"] is False


def test_fail_closed_on_inventory_disagreement(tmp_path):
    raw,batch,_=example(tmp_path)
    for mutator in [
        lambda x:x["summary"].update(rendered=2),
        lambda x:x["summary"].update(unexpanded_steps=99),
        lambda x:x["summary"].update(declarations_with_gaps=1),
        lambda x:x["summary"].update(total_candidates=0),
        lambda x:x["summary"].update(certified_english_proofs=1),
        lambda x:x["modules"][0]["rows"][0].update(path_checked=False),
    ]:
        case=copy.deepcopy(batch);mutator(case)
        (raw / "batch.json").write_text(json.dumps(case))
        with pytest.raises(ValueError):
            build(raw,tmp_path / "public",commit=COMMIT,run_id=RUN)


def test_receipt_and_snapshot_identity_must_agree(tmp_path):
    raw,batch,proof=example(tmp_path)
    recpath=proof/"receipt.json";r=json.loads(recpath.read_text());r["theorem"]="Another.theorem"
    recpath.write_text(json.dumps(r))
    with pytest.raises(ValueError):
        build(raw,tmp_path / "public",commit=COMMIT,run_id=RUN)


def test_no_outside_overwrite(tmp_path):
    raw,_,_=example(tmp_path)
    with pytest.raises(ValueError):
        build(raw, raw/"site", commit=COMMIT,run_id=RUN)


def test_html_escaping_untrusted_theorem_names():
    entries=[{"name":"OAI.Bad.<script>alert(1)</script>","title":"<script>alert(1)</script>",
            "module":"OAI.Bad", "area":"Bad", "source":"https://example.org", "page":"proofs/example.html",
            "status":"Incomplete explanation","frames":5,"gaps":1,"statement":"<img src=x onerror=alert(1)>"}]
    modules=[{"name":"OAI.Bad","status":"complete","expected":1,"errors":[],"source":"https://example.org"}]
    summary={"kernel_checked":1,"declarations_with_gaps":1,"modules_complete":1,"modules_expected":1,"total_candidates":1}
    rendered=page(entries,modules,summary,commit=COMMIT,run_id=RUN)
    assert '&lt;script&gt;alert(1)&lt;/script&gt;' in rendered
    assert '&lt;img src=x onerror=alert(1)&gt;' in rendered
    assert '<script>alert(1)</script>' not in rendered
    assert '<img src=x onerror=alert(1)>' not in rendered


def test_revision_identifiers_cannot_be_guessed():
    with pytest.raises(ValueError):
        page([{"name":"x"}],[],{"total_candidates":None},commit="HEAD",run_id="latest")
