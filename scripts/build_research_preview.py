#!/usr/bin/env python3
"""Build an offline, shareable Leanglish research preview from an observed run.

No Lean execution, downloads, network requests, or LLM calls. The input batch
and proof bundles must already exist. Failure counts and missing denominators
are copied faithfully, rather than recomputed from successful proof pages.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path
import re
import shutil
import sys

PIN = "1581d4cbdd69a0faf34b2089614fe2a814316a6a"
REPOSITORY = "https://github.com/KyleJKistner/LeanDigest"
UPSTREAM = f"https://github.com/openai/math/blob/{PIN}/lean/"
PAGES = {"index.html", "manifest.json", "README.txt"}


def digest(b: bytes) -> str:
    return sha256(b).hexdigest()


def checked_relative(root: Path, rel: str) -> Path:
    if not isinstance(rel, str) or not rel or "\\" in rel:
        raise ValueError("Invalid artifact path")
    relpath = Path(rel)
    if relpath.is_absolute() or ".." in relpath.parts or relpath.suffix != ".html":
        raise ValueError("Artifact must be a relative HTML path")
    candidate = root / relpath
    if candidate.is_symlink() or not candidate.is_file() or not candidate.resolve().is_relative_to(root.resolve()):
        raise ValueError("Missing, symlinked or escaping proof HTML")
    if candidate.name != "reader.html" or "proofs" not in relpath.parts:
        raise ValueError("Unexpected proof artifact layout")
    return candidate


def label_module(module: str) -> str:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[0] == "OAI" else parts[0]


def source_link(module: str) -> str:
    if not re.fullmatch(r"OAI(?:\.[A-Za-z0-9_]+)+", module):
        raise ValueError("Invalid original OpenAI module")
    return UPSTREAM + module.replace(".", "/") + ".lean"


def concise(name: str) -> str:
    return name.rsplit(".", 1)[-1].replace("_", " ")


def proof_intro(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    prelude = [line.strip() for line in lines[1:60] if line.strip()]
    statement = next((line[5:] for line in prelude if line.startswith("Then ")), "")
    return statement[:500] if statement else "Inspect the exact Lean theorem statement in the proof reader."


def load_rows(batch: dict, source_dir: Path, output_dir: Path) -> tuple[list[dict], list[dict]]:
    modules = batch.get("modules")
    if not isinstance(modules, list) or not modules or any(not isinstance(m, dict) for m in modules):
        raise ValueError("Malformed module inventory")
    entries = []
    module_summary = []
    seen_names = set()
    for module in modules:
        module_name = module["module"]
        link = source_link(module_name)
        rows = module.get("rows", [])
        if not isinstance(rows, list):
            raise ValueError("Malformed declaration outcomes")
        module_summary.append({"name": module_name, "status": module.get("status", "unknown"),
                               "expected": module.get("expected"), "errors": module.get("errors", []),
                               "source": link})
        for row in rows:
            name = row["name"]
            if name in seen_names:
                raise ValueError("Repeated declaration across modules")
            seen_names.add(name)
            if not row.get("rendered"):
                continue
            if not row.get("kernel_checked") or not row.get("path_checked"):
                raise ValueError("Refusing to publish a rendering as checked without source-path checking")
            page = checked_relative(source_dir, row["reader"])
            directory = page.parent
            proof_path = directory / "proof.txt"
            snapshot_path = directory / "snapshot.json"
            receipt_path = directory / "receipt.json"
            if any(not p.is_file() or p.is_symlink() for p in (proof_path, snapshot_path, receipt_path)):
                raise ValueError("Missing readable proof, source snapshot, or receipt")
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if snapshot.get("theorem") != name or receipt.get("theorem") != name:
                raise ValueError("A proof/receipt identity does not match its inventory row")
            if not (receipt.get("status") == "passed" and
                    receipt.get("all_selected_judgements_kernel_checked") is True and
                    receipt.get("path_linkage_checked_in_lean") is True and
                    receipt.get("receipt_authenticated") is False and
                    receipt.get("english_formally_verified") is False):
                raise ValueError("Receipt does not accurately describe the trusted evidence boundary")
            if int(row["frames"]) != len(snapshot.get("frames", [])):
                raise ValueError("Narrative frame count changed")
            n = int(row["unexpanded_steps"])
            if n < 0:
                raise ValueError("Invalid explanation gap count")
            proof_id = digest(name.encode("utf-8"))[:20]
            public = f"proofs/{proof_id}.html"
            destination = output_dir / public
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(page, destination)
            entries.append({
                "name": name, "title": concise(name), "module": module_name,
                "area": label_module(module_name), "source": link, "page": public,
                "status": "No recorded fallbacks" if n == 0 else "Incomplete explanation",
                "frames": int(row["frames"]), "gaps": n, "statement": proof_intro(proof_path),
                "html_sha256": digest(destination.read_bytes()),
                "snapshot_sha256": digest(snapshot_path.read_bytes()),
                "receipt_sha256": digest(receipt_path.read_bytes()),
            })
    return entries, module_summary


CSS = r"""
:root {color-scheme:light;--ink:#1d292e;--muted:#5a6a72;--line:#dfe4e4;--bg:#f8f9f6;--card:#fff;--accent:#125950;--wash:#ebf3ef}
* {box-sizing:border-box}[hidden]{display:none!important}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.57 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
a{color:#155e59;text-underline-offset:3px}a:hover{color:#0a3d38}button,input,select{font:inherit}button:focus-visible,a:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid #16796c;outline-offset:3px}
.shell{max-width:1140px;margin:auto;padding:0 28px}.top{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:22px 0;border-bottom:1px solid var(--line)}.mark{font-family:Georgia,'Times New Roman',serif;font-size:25px;font-weight:700;letter-spacing:-.03em;text-decoration:none;color:var(--ink)}.navlinks{display:flex;gap:20px;flex-wrap:wrap;font-size:14px}.navlinks a{text-decoration:none;color:var(--muted)}.eyebrow{color:var(--accent);font-weight:700;font-size:12px;letter-spacing:.12em;text-transform:uppercase}.hero{padding:74px 0 55px;max-width:865px}.hero h1{font:normal clamp(40px,6vw,70px)/1.06 Georgia,'Times New Roman',serif;letter-spacing:-.045em;margin:17px 0}.hero p{max-width:735px;font-size:19px;color:var(--muted);line-height:1.65}.hero .actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:27px}.action{display:inline-flex;align-items:center;justify-content:center;text-decoration:none;border:1px solid var(--line);border-radius:9px;padding:12px 20px;font-size:14px;font-weight:650;color:var(--ink);background:var(--card)}.action.primary{background:var(--accent);color:white;border-color:var(--accent)}.action:hover{filter:brightness(.96)}
.notice{border-left:3px solid #b3853e;padding:15px 20px;background:#f6f0e6;margin:0 0 42px;color:#514838;font-size:14px}.notice strong{color:#3d382c}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:13px;padding-bottom:65px}.metric{border:1px solid var(--line);background:var(--card);border-radius:12px;padding:17px 20px}.metric b{display:block;font-size:30px;font-weight:600;font-variant-numeric:tabular-nums;line-height:1.25}.metric span{font-size:12px;line-height:1.55;color:var(--muted);display:block;margin-top:7px}
section{padding:35px 0 60px;border-top:1px solid var(--line)}section h2{font:normal 34px/1.2 Georgia,'Times New Roman',serif;letter-spacing:-.025em;margin:0 0 13px}section .sub{color:var(--muted);max-width:775px;margin:0 0 24px}.featured{display:grid;grid-template-columns:2fr 1fr;gap:21px;padding:27px;border:1px solid #b6d0c5;background:#edf5f0;border-radius:14px}.featured h3{font:normal 27px/1.26 Georgia,'Times New Roman',serif;margin:8px 0 12px}.featured p{max-width:600px;margin:9px 0;color:#3d5751}.featured aside{border-left:1px solid #bfd4c9;padding-left:20px;font-size:14px;color:#36514a}.featured aside b{display:block;margin-top:12px}.featured .action{margin-top:10px}
.controls{display:flex;gap:12px;flex-wrap:wrap;margin:23px 0 15px}.controls input{min-width:230px;flex:1}.controls input,.controls select{border:1px solid #cbd7d6;border-radius:9px;background:white;padding:11px 13px;min-height:44px;color:var(--ink)}.count{color:var(--muted);font-size:13px;padding:3px 0 18px}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:13px}.item{background:#fff;border:1px solid var(--line);border-radius:11px;padding:20px;min-width:0;display:flex;flex-direction:column;gap:10px}.item h3{font:normal 20px/1.3 Georgia,'Times New Roman',serif;margin:1px 0;overflow-wrap:anywhere}.item .module{color:var(--muted);font-size:12px;overflow-wrap:anywhere}.item .statement{font-size:14px;line-height:1.5;color:#455359;overflow-wrap:anywhere;margin:0}.item .foot{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:auto;padding-top:7px;font-size:13px}.status{display:inline-flex;border:1px solid #d3dddd;border-radius:100px;padding:2px 10px;color:#49625b;font-size:11px;font-weight:600}.status.needs{border-color:#e2d8c5;color:#775b32}.item .foot a:first-of-type{margin-left:auto;font-weight:700;text-decoration:none}.small{font-size:12px;color:var(--muted)}.error{border:1px solid #e6d5cf;border-radius:10px;padding:18px;background:#fff9f7;margin:10px 0}.error b{display:block;overflow-wrap:anywhere}.error code{overflow-wrap:anywhere;font-size:12px}
.method{display:grid;grid-template-columns:1fr 1fr;gap:26px}.method p,.method li{color:#4f6067;font-size:15px}.method h3{font-size:16px;margin-top:0}.code{border:1px solid var(--line);border-radius:9px;background:#fff;padding:16px 18px;white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;color:#304d4a}.footer{border-top:1px solid var(--line);padding:28px 0 45px;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;color:var(--muted);font-size:13px}.skip{position:absolute;top:-100px;left:0;padding:12px;background:white}.skip:focus{top:0}
@media(max-width:730px){.shell{padding:0 17px}.hero{padding:48px 0 35px}.hero p{font-size:17px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr));padding-bottom:38px}.cards,.featured,.method{grid-template-columns:1fr}.featured aside{border-left:0;border-top:1px solid #bfd4c9;padding:12px 0 0}.top{align-items:flex-start}.navlinks{gap:12px;justify-content:flex-end}.controls>*{width:100%;flex:1}section{padding:30px 0 40px}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""

JS = r"""
(()=>{'use strict';
const input=document.getElementById('search');
const area=document.getElementById('area');
const completeness=document.getElementById('completeness');
const cards=[...document.querySelectorAll('[data-proof-card]')];
const count=document.getElementById('shown-count');
const clean=s=>(s||'').normalize('NFKD').toLowerCase();
function filter(){const q=clean(input.value.trim());let n=0;
  for(const node of cards){const match=(!q||clean(node.dataset.search).includes(q))&&
    (area.value==='all'||node.dataset.area===area.value)&&
    (completeness.value==='all'||(completeness.value==='zero'?node.dataset.gaps==='0':node.dataset.gaps!=='0'));
    node.hidden=!match;if(match)n++;
  }count.textContent=n+' of '+cards.length+' proof readings';}
for(const element of [input,area,completeness]) element.addEventListener('input',filter);
filter();
})();
"""


def page(entries: list[dict], modules: list[dict], summary: dict, *, commit: str, run_id: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not re.fullmatch(r"\d+", run_id):
        raise ValueError("Expected immutable release provenance")
    by_gap = sorted(entries, key=lambda x: (x["gaps"], -x["frames"], x["name"]))
    featured = next((e for e in by_gap if e["name"].endswith("BezoutFrame.exists_frame")), by_gap[0])
    expected = summary["total_candidates"]
    if expected is not None and (type(expected) is not int or expected < len(entries)):
        raise ValueError("Invalid complete-denominator claim")
    areas = sorted({e["area"] for e in entries})
    def esc(x): return escape(str(x), quote=True)
    options = ''.join(f'<option value="{esc(a)}">{esc(a)}</option>' for a in areas)
    cards = []
    for e in by_gap:
        status = 'No recorded fallback steps' if e['gaps'] == 0 else f'{e["gaps"]} unexpanded steps'
        cards.append(f'''<article class="item" data-proof-card data-area="{esc(e['area'])}" data-gaps="{e['gaps']}" data-search="{esc(e['name']+' '+e['module']+' '+e['statement'])}">
          <div class="module">{esc(e['area'])} · {esc(e['module'])}</div>
          <h3>{esc(e['title'])}</h3><p class="statement">{esc(e['statement'])}</p>
          <div class="foot"><span class="status {'needs' if e['gaps'] else ''}">{esc(status)}</span><span class="small">{e['frames']} checked frames</span>
          <a href="{esc(e['page'])}">Read proof ↗</a><a href="{esc(e['source'])}" target="_blank" rel="noopener noreferrer" aria-label="Original source for {esc(e['title'])}">Source</a></div>
        </article>''')
    problems = []
    for m in modules:
        if m['status'] != 'complete':
            errors = '; '.join(m['errors'][:3]) if m['errors'] else 'Module was not completed.'
            problems.append(f'<div class="error"><b>{esc(m["name"])}</b>Build or extraction failed: {esc(errors)}. The candidate denominator for this module remains unknown. <a href="{esc(m["source"])}" target="_blank" rel="noopener noreferrer">Original source</a></div>')
    prefix = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
    prefix += '<meta name="description" content="Leanglish is an experimental, deterministic reading interface for Lean proofs from the OpenAI mathematics release.">'
    prefix += '<title>Leanglish — read the OpenAI mathematics proofs</title><style>'+CSS+'</style></head><body>'
    start = f'''<a class="skip" href="#proofs">Skip to proof catalog</a>
    <div class="shell"><header class="top"><a class="mark" href="index.html">Leanglish<span style="color:#13705f">.</span></a><nav class="navlinks" aria-label="Main navigation"><a href="#proofs">Proof catalog</a><a href="#method">How it works</a><a href="{REPOSITORY}/tree/{commit}" target="_blank" rel="noopener noreferrer">GitHub ↗</a></nav></header>
    <main><div class="hero"><div class="eyebrow">Experimental research preview · OpenAI mathematics release</div>
    <h1>Formal proofs.<br>Mathematical English.</h1>
    <p>Leanglish translates Lean proof structure into expandable mathematical arguments, without an LLM in the rendering pipeline. Inspect the statement, follow the reasoning, and open the checked evidence when you need it.</p>
    <div class="actions"><a class="action primary" href="{esc(featured['page'])}">Read the Bézout-frame proof ↗</a><a class="action" href="#proofs">Explore {len(entries)} proof readings</a></div></div>
    <div class="notice" role="note"><strong>Research preview, not an English proof certification.</strong> These are source-bound readings generated from selected Lean declarations. English fidelity and readability have not been formally verified; named imported lemmas and low-level transformations may remain unexplained. Checking observations are reproducible but unsigned.</div>
    <div class="metrics" aria-label="Observed extraction results"><div class="metric"><b>{summary['kernel_checked']}</b><span>Selected declarations with native Lean checking observations</span></div><div class="metric"><b>{len(entries)}</b><span>Offline proof readers available</span></div><div class="metric"><b>{summary['declarations_with_gaps']}</b><span>Readings with explicitly unexpanded steps</span></div><div class="metric"><b>{summary['modules_complete']}/{summary['modules_expected']}</b><span>Selected source modules completed; total denominator {'unknown' if expected is None else expected}</span></div></div>
    <section id="example"><div class="eyebrow">Featured walkthrough</div><h2>Bézout-frame existence</h2><div class="featured"><div><h3>From a gcd identity to explicit witnesses</h3>
    <p>Given <i>xy = z(z + 1)</i> over a Euclidean domain, construct four elements satisfying a system of equations. The reading shows the zero-gcd case, the Bézout coefficients, the cancellation argument and the witnesses.</p>
    <p>This is the most complete explanatory example in the selected sample; all 86 selected frames are accounted for without recorded fallback steps. Imported lemma proofs are still external dependencies.</p>
    <a class="action primary" href="{esc(featured['page'])}">Open interactive argument</a></div><aside><b>Formal evidence</b>86 selected judgements, in the frozen Lean 4.34.1 environment.<b>Explanation</b>Source-bound deterministic rendering, with expandable details.<b>Limit</b>No formal interpretation of natural-language sentences.</aside></div></section>
    <section id="proofs"><div class="eyebrow">Frozen research snapshot</div><h2>Browse the extracted proofs</h2>
    <p class="sub">Each proof page opens locally without a Lean installation. Search by theorem, subject or statement. “No recorded fallbacks” does not mean every imported dependency is explained.</p>
    <div class="controls"><input id="search" type="search" aria-label="Search theorem names and statements" placeholder="Search theorem or statement…" autocomplete="off"><select id="area" aria-label="Filter by field"><option value="all">All subject areas</option>{options}</select>
    <select id="completeness" aria-label="Filter by explanation completeness"><option value="all">All explanation depths</option><option value="zero">No recorded fallbacks</option><option value="gaps">Contains unexpanded steps</option></select></div>
    <div class="count" id="shown-count" role="status" aria-live="polite"></div><div class="cards" id="cards">{''.join(cards)}</div></section>
    <section id="method"><div class="eyebrow">Method and reproducibility</div><h2>What was actually checked?</h2><div class="method"><div><h3>The evidence chain</h3><p>The fixed OpenAI source revision and Lean dependency pins feed native theorem extraction. Lean type-checks selected intermediate claims and compares the recorded paths with the original proof expression. Deterministic rules render the reading and expose explicit fallbacks.</p>
    <p>Source parsing, Lean’s pretty-printer and English templates form the trusted presentation boundary. Neither fluent prose nor an apparently complete expansion proves semantic equivalence of the English.</p></div>
    <div><h3>Try Leanglish on your own Lean project</h3><div class="code">git clone {REPOSITORY}.git<br>cd LeanDigest<br>python -m pip install .<br>python -m leanglish narrative-demo -o proof.html<br>python -m leanglish serve</div><p class="small">Batch extraction runs Lean code: use a trusted/disposable Lean environment and explicitly opt in. The reader itself has no execution endpoint.</p></div></div>
    <h3>Known missing module</h3>{''.join(problems) if problems else '<p>No failed modules in this selected slice.</p>'}
    <p class="small">Frozen OpenAI commit <a href="https://github.com/openai/math/tree/{PIN}/lean" target="_blank" rel="noopener noreferrer">{PIN[:12]}</a>. Leanglish source commit <a href="{REPOSITORY}/commit/{commit}" target="_blank" rel="noopener noreferrer">{commit[:12]}</a>. GitHub Actions <a href="{REPOSITORY}/actions/runs/{run_id}" target="_blank" rel="noopener noreferrer">run {run_id}</a>. Source links are to the original repository. The selected sample is not representative of whole-corpus coverage.</p></section>
    </main><footer class="footer"><span>Leanglish · open research preview · {len(entries)} selected readings</span><span><a href="manifest.json">Machine-readable evidence manifest</a> · <a href="{REPOSITORY}">Repository</a></span></footer></div>
    <script>{JS}</script></body></html>'''
    return prefix+start


def build(batch_dir: Path, out: Path, *, commit: str, run_id: str) -> dict:
    batch_dir = batch_dir.resolve()
    if not (batch_dir / "batch.json").is_file():
        raise ValueError("No batch.json in source directory")
    out = out.resolve()
    if out == batch_dir or out.is_relative_to(batch_dir) or batch_dir.is_relative_to(out):
        raise ValueError("Use separate source and destination directories")
    out.mkdir(parents=True, exist_ok=True)
    batch = json.loads((batch_dir / "batch.json").read_text(encoding="utf-8"))
    if batch.get("schema") != "leanglish.narrative-batch/v1":
        raise ValueError("Unsupported batch format")
    summary = batch.get("summary")
    if not isinstance(summary, dict) or summary.get("whole_openai_corpus_coverage") is not False or summary.get("certified_english_proofs") != 0:
        raise ValueError("Unrecognized or misleading reported coverage")
    entries, modules = load_rows(batch, batch_dir, out)
    if not entries or summary.get("rendered") != len(entries) or summary.get("kernel_checked") != len(entries):
        raise ValueError("The inventory and published reader pages disagree")
    if summary.get("declarations_with_gaps") != sum(e["gaps"] > 0 for e in entries):
        raise ValueError("Explanation-gap counts do not reconcile")
    if summary.get("unexpanded_steps") != sum(e["gaps"] for e in entries):
        raise ValueError("Unexpanded-step totals do not reconcile")
    (out / "index.html").write_text(page(entries, modules, summary, commit=commit, run_id=run_id), encoding="utf-8")
    manifest = {"schema":"leanglish.research-preview/v1", "generated_by":"deterministic standard-library site builder",
                "source_commit":commit,"openai_commit":PIN,"github_run_id":run_id,
                "summary":summary,"proofs":entries,"modules":modules,
                "formal_english_certification":False,"independent_human_readability_study":False,
                "index_sha256":digest((out/"index.html").read_bytes())}
    (out/"manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2)+"\n", encoding="utf-8")
    (out/"README.txt").write_text("Leanglish research preview — open index.html in a modern browser.\n"
             "All proof pages work offline. Source checking observations are unsigned.\n"
             "No English equivalence certification or human readability claim is made.\n",
             encoding="utf-8")
    return manifest


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch",type=Path,required=True,help="Directory with frozen batch.json and attempts")
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--source-commit",required=True)
    parser.add_argument("--run-id",required=True)
    args=parser.parse_args(argv)
    try:
        result=build(args.batch,args.output,commit=args.source_commit,run_id=args.run_id)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        parser.exit(2,"Leanglish preview error: "+str(exc)+"\n")
    print(json.dumps({"page":"index.html","proofs":len(result["proofs"]),"summary":result["summary"]},indent=2))
    return 0


if __name__=="__main__":
    sys.exit(main())
